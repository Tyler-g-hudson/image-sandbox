from __future__ import annotations

import json
import os
import shutil
import tempfile
from abc import ABC, abstractmethod
from contextlib import contextmanager
from subprocess import CalledProcessError
from typing import (Any, Dict, Iterator, List, Mapping, Optional, Sequence,
                    Tuple)

from ._bind_mount import BindMount
from ._docker_cmake import install_prefix
from ._image import Image


class Workflow(ABC):
    @abstractmethod
    def get_command(self, runconfig: os.PathLike[str] | str) -> str:
        ...


class GenericSASWorkflow(Workflow):
    def __init__(self, module: str) -> None:
        self.module = module

    def get_command(self, runconfig: os.PathLike[str] | str) -> str:
        return f"python -m nisar.workflows.{self.module} {runconfig}"


class InSARWorkflow(GenericSASWorkflow):
    def get_command(self, runconfig: os.PathLike[str] | str) -> str:
        return super().get_command(runconfig) + " -- restart"


class TextRunconfigWorkflow(GenericSASWorkflow):
    def get_command(self, runconfig: os.PathLike[str] | str) -> str:
        return f"python -m nisar.workflows.{self.module} @{runconfig}"


class SoilMoistureWorkflow(GenericSASWorkflow):
    def get_command(self, runconfig: os.PathLike[str] | str) -> str:
        return f"micromamba run -n SoilMoisture NISAR_SM_SAS {runconfig}"


def get_workflow_object(workflow_name: str) -> Workflow:
    """
    Returns a Workflow object given the name of the workflow.

    Parameters
    ----------
    workflow_name : str
        The name of the workflow.

    Returns
    -------
    Workflow
        The associated Workflow object.

    Raises
    ------
    ValueError
        If the given workflow name is not recognized.
    """
    if workflow_name in ["gslc", "gcov", "insar"]:
        return GenericSASWorkflow(workflow_name)
    elif workflow_name == "rslc":
        return GenericSASWorkflow("focus")
    elif workflow_name == "insar":
        return InSARWorkflow(workflow_name)
    elif workflow_name in ["el_edge", "el_null"]:
        return TextRunconfigWorkflow(workflow_name)
    else:
        raise ValueError(f"Workflow {workflow_name} not recognized")


def get_test_info(
    workflow_name: str,
    test_name: str,
    filename: str = "workflowtests.json"
) -> Tuple[Dict[str, str | List[str] | Dict[str, str]], str]:
    """
    Get test data from the given file.

    Parameters
    ----------
    workflow_name : str
        The name of the workflow in the test file.
    test_name : str
        The name of the test under the given workflow.
    file : str, optional
        The name of the test. Defaults to "workflowtests.json".

    Returns
    -------
    Tuple[Dict[str, str | List[str] | Dict[str, str]], str]
        A dictionary representing information about the test.

    Raises:
    -------
    ValueError:
        If the workflow is not found, or the supplied test is not a test under the
        given workflow.
    """
    with open(filename) as file:
        file_dict = json.load(fp=file)

    if workflow_name not in file_dict:
        raise ValueError(f"Workflow {workflow_name} not found.")
    workflow_dict = file_dict[workflow_name]

    if test_name not in workflow_dict["tests"]:
        raise ValueError(f"Test {test_name} not found in workflow {workflow_name}")
    test_type = workflow_dict["type"]
    if not isinstance(test_type, str):
        raise ValueError("\"type\" field of workflow in given test database returned "
                         f"{type(test_name)}, expected string.")
    return workflow_dict["tests"][test_name], test_type


@contextmanager
def workflow_mounts(
    workflow_name: str,
    test: str,
    runconfig: str,
    input_files: Mapping[str, os.PathLike[str] | str],
    output_dir: str,
    scratch_dir: Optional[str],
    runconfig_dir: str = "runconfig"
) -> Iterator[List[BindMount]]:
    """A context manager that generates a list of workflow bind mounts.

    If any mount is temporary on the host side, it will delete it automatically
    on context exit.

    Parameters
    ----------
    workflow_name : str
        The name of the workflow.
    test : str
        The name of the test.
    runconfig : str
        The path to the runconfig.
    input_files : Mapping[str, os.PathLike[str]  |  str]
        A mapping connecting input datasets to their host file location.
    output_dir : str
        The host output directory.
    scratch_dir : str, optional
        The host scratch directory. If None, a temp directory will be generated.
    runconfig_dir : str, optional
        The location of the directory in which runconfigs are held.

    Returns
    -------
    List[BindMount]
        The generated bind mounts.

    Yields
    ------
    Iterator[List[BindMount]]
        The generated bind mounts.

    Raises
    ------
    ValueError
        If the runconfig is not found at the expected location.
    """

    # If the output directory doesn't exist on the host, make it.
    if not os.path.isdir(f"{output_dir}/{workflow_name}/{test}"):
        os.makedirs(f"{output_dir}/{workflow_name}/{test}")
    # Create the output directory bind mount, place it in the bind mounts basic list.
    # This list will be copied and used for all tests that are run.
    bind_mounts = [
        BindMount(
            image_mount_point=f"{install_prefix()}/output/{workflow_name}",
            host_mount_point=os.path.abspath(f"{output_dir}/{workflow_name}"),
            permissions="rw"
        )
    ]

    # If requested, add a local mount for the scratch directories.
    # Otherwise, add a temporary one so the docker container can get rw permissions.
    temp_scratch: bool = scratch_dir is None

    if temp_scratch:
        # Create the temp scratch file
        host_scratch_dir: str = tempfile.mkdtemp()
    else:
        # Create the scratch file if it doesn't already exist
        if not os.path.isdir(f"{scratch_dir}/{workflow_name}/{test}"):
            os.makedirs(f"{scratch_dir}/{workflow_name}/{test}")
        assert isinstance(scratch_dir, str)
        host_scratch_dir = os.path.abspath(scratch_dir)

    # Create the scratch file bind mount
    bind_mounts.append(BindMount(
        image_mount_point=f"{install_prefix()}/scratch/{workflow_name}",
        host_mount_point=host_scratch_dir,
        permissions="rw"
    ))

    # Add the runconfig mount to the install prefix directory
    runconfig_lookup_path: str = f"{runconfig_dir}/{workflow_name}"
    # Get the runconfig path on the host and image
    runconfig_host_path = os.path.abspath(f"{runconfig_lookup_path}/{runconfig}")
    runconfig_image_path = f"{install_prefix()}/{runconfig}"
    # If the runconfig doesn't exist at the expected location, this is an error
    if not os.path.isfile(runconfig_host_path):
        raise ValueError(
            f"Runconfig {runconfig} not found at {runconfig_host_path}."
        )

    # Create the runconfig file bind mount
    bind_mounts.append(BindMount(
        host_mount_point=runconfig_host_path,
        image_mount_point=runconfig_image_path,
        permissions="ro"
    ))

    # Create input files
    for repo in input_files:
        host_path = os.path.abspath(input_files[repo])
        image_path = f"{install_prefix()}/input/{repo}"
        bind_mounts.append(BindMount(
            image_mount_point=image_path,
            host_mount_point=host_path,
            permissions="ro"
        ))

    try:
        yield bind_mounts
    finally:
        # If a temporary scratch file was created, remove it.
        if temp_scratch:
            shutil.rmtree(host_scratch_dir)


def run_series_workflow(
    image: Image,
    main_test_name: str,
    output_dir: str,
    input_dirs: Mapping[str, str],
    scratch_dir: Optional[str],
    output_subdir: str,
    test_series_info: Sequence[Mapping[str, Any]]
) -> None:
    for test_info in test_series_info:
        workflow_name = test_info["workflow"]
        if workflow_name == "series":
            subseries_info = test_info["series"]
            run_series_workflow(
                image=image,
                main_test_name=main_test_name,
                output_dir=output_dir,
                input_dirs=input_dirs,
                scratch_dir=scratch_dir,
                output_subdir=output_subdir,
                test_series_info=subseries_info
            )
            continue
        if workflow_name == "parallel":
            continue
        runconfig = test_info["runconfig"]
        runconfig_location = f"runconfig/{main_test_name}"

        # Determine the location of the subtest output directory.
        directory_structure = [output_dir, workflow_name]
        # If the test is tagged, this tag will be a subdirectory under the test
        # directory.
        if "tag" in test_info.keys():
            directory_structure.append(test_info["tag"])
        test_output_dir = "/".join(directory_structure)
        # If this location doesn't exist, create it.
        if not os.path.isdir(test_output_dir):
            os.makedirs(test_output_dir)

        # Setup workflow mounts. Automatically generates and removes temporary files
        # if necessary.
        with workflow_mounts(
            workflow_name=workflow_name,
            test=main_test_name,
            runconfig=runconfig,
            input_files=input_dirs,
            output_dir=output_dir,
            scratch_dir=scratch_dir,
            runconfig_dir=runconfig_location
        ) as bind_mounts:
            # Run the workflow.
            run_workflow(
                workflow_img=image,
                workflow_name=workflow_name,
                runconfig=runconfig,
                bind_mounts=bind_mounts
            )

    """
    - runner image
    - output file location
    - scratch file location?
    - input file locations
    - overall test output file local path
    - series or parallel list
        - tests,
            - workflow
            - ?tag
            - runconfig
        - recurse series or parallel list ^

    output files @:
        {output_loc}/{overall workflow name}/{test_name}/{sub_workflow_name}/?{tag}
    initially build directory:
        {output_loc}/{overall workflow name}/{test_name}/
    ^^^^^^^^^^^^ MOUNT THIS DIRECTORY AS THE OUTPUT DIRECTORY ^^^^^^^^^^^^
    -   DO THIS PRIOR TO CALLING THIS FUNCTION
    -   Can recursively add deeper folders in case of nested parallels and series?
        -   This sounds like it could get unnecessarily complicated. If people want to
            do things like this, they should use tags instead.
    For each test, build subdirectory prior to test run:
        /{sub_workflow_name}/?{tag}
    """
    ...


def run_workflow(
    workflow_img: Image,
    workflow_name: str,
    runconfig: str,
    bind_mounts: Sequence[BindMount]
) -> None:
    """Runs a workflow test on the given image.

    Parameters
    ----------
    workflow_img : Image
        The image to run the test on.
    workflow_name : str
        The name of the workflow.
    runconfig : str
        The location of the runconfig.
    bind_mounts : Sequence[BindMount]
        The set of bind mounts to run on this test.

    Raises
    ------
    CalledProcessError
        If the workflow fails.
    """

    # Get the test command.
    workflow_obj: Workflow = get_workflow_object(workflow_name=workflow_name)
    command = workflow_obj.get_command(runconfig=runconfig)

    # Run the test on the image.
    try:
        workflow_img.run(command, bind_mounts=bind_mounts, host_user=True)
    except CalledProcessError as err:
        print(f"Workflow test failed with message with stderr:\n{err.stderr}")
