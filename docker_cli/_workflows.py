from __future__ import annotations

import json
import os
import shutil
import tempfile
from abc import ABC, abstractmethod
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from subprocess import CalledProcessError
from typing import (Any, Dict, Iterator, List, Mapping, Optional, Sequence,
                    Tuple)

from ._bind_mount import BindMount
from ._docker_cmake import install_prefix
from ._exceptions import TestFailedError
from ._image import Image


class Workflow(ABC):
    """A workflow handler. Abstract."""

    @abstractmethod
    def get_command(self, runconfig: os.PathLike[str] | str) -> str:
        ...


class GenericSASWorkflow(Workflow):
    """A handler for typical SAS workflows."""

    def __init__(self, module: str) -> None:
        self.module = module

    def get_command(self, runconfig: os.PathLike[str] | str) -> str:
        return f"python -m nisar.workflows.{self.module} {runconfig}"


class InSARWorkflow(GenericSASWorkflow):
    """A handler for the InSAR workflow."""

    def get_command(self, runconfig: os.PathLike[str] | str) -> str:
        return super().get_command(runconfig) + " -- restart"


class TextRunconfigWorkflow(GenericSASWorkflow):
    """A handler for workflows whose runconfig is a text file."""

    def get_command(self, runconfig: os.PathLike[str] | str) -> str:
        return f"python -m nisar.workflows.{self.module} @{runconfig}"


class SoilMoistureWorkflow(GenericSASWorkflow):
    """A handler for the SoilMoisture workflow."""

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
) -> Tuple[Dict[str, str | List[Dict[str, str]] | Dict[str, str]], str]:
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


def workflow_mounts(
    test_params: WorkflowParams,
) -> List[BindMount]:
    """Generates a list of workflow bind mounts.

    Parameters
    ----------
    test_params: WorkflowParams
        The workflow parameters object containing information about the file mount
        locations on the host.

    Returns
    -------
    List[BindMount]
        The generated bind mounts.
    """
    input_dict: Dict[str, Path] = dict(test_params.input_dict)
    output_dir: Path = test_params.output_dir
    scratch_dir: Path = test_params.scratch_dir
    install_path: Path = Path(install_prefix())

    # Create the output directory bind mount, place it in the bind mounts basic list.
    # This list will be copied and used for all tests that are run.
    bind_mounts = [
        BindMount(
            image_mount_point=str(install_path/"output"),
            host_mount_point=str((output_dir).absolute()),
            permissions="rw"
        )
    ]

    # Create input files
    for repo in input_dict:
        host_path = input_dict[repo].absolute()
        image_path = install_path/"input"/repo
        bind_mounts.append(BindMount(
            image_mount_point=str(image_path),
            host_mount_point=str(host_path),
            permissions="ro"
        ))

    # Create the scratch file bind mount
    bind_mounts.append(BindMount(
        image_mount_point=str(install_path/"scratch"),
        host_mount_point=str(scratch_dir.absolute()),
        permissions="rw"
    ))

    return bind_mounts


@contextmanager
def prepare_scratch_dir(
    scratch_dir: Optional[str]
) -> Iterator[Path]:
    """
    A context manager that returns a scratch directory absolute path.

    If none is given, generates a temporary one, and deletes it on exit.

    Parameters
    ----------
    scratch_dir : Optional[Path]
        The location of the scratch directory, or None if a temp directory is desired.

    Returns
    -------
    Path
        An absolute path to a scratch directory.

    Yields
    ------
    Iterator[Path]
        An absolute path to a scratch directory.
    """
    # If requested, add a path to the scratch directory.
    # Otherwise, create a temporary one so the docker container can get rw permissions.
    temp_scratch: bool = scratch_dir is None

    try:
        if temp_scratch:
            # Create the temp scratch file
            return_dir: Path = Path(tempfile.mkdtemp()).absolute()
        else:
            assert isinstance(scratch_dir, str)
            return_dir = Path(scratch_dir).absolute()

        yield return_dir

    finally:
        # If a temporary scratch file was created, remove it.
        if temp_scratch:
            shutil.rmtree(str(return_dir))


def prepare_subdirectories(
    workflow_name: str,
    test: Optional[str],
    test_params: WorkflowParams
) -> None:
    """
    Generates output and scratch subdirectories for a workflow test.

    Parameters
    ----------
    workflow_name : str
        The name of this workflow.
    test : Optional[str]
        The name of this subtest, if it exists.
    test_params : WorkflowParams
        The test parameters.
    """
    test_subdir = Path(workflow_name)/test if test is not None else Path(workflow_name)
    output_dir: Path = test_params.output_dir/test_subdir
    scratch_dir: Path = test_params.scratch_dir/test_subdir

    # If the output directory doesn't exist on the host, make it.
    if not os.path.isdir(str(output_dir)):
        os.makedirs(str(output_dir))

    # Create the scratch file if it doesn't already exist
    if not os.path.isdir(str(scratch_dir)):
        os.makedirs(str(scratch_dir))


def prepare_runconfig(
    workflow_name: str,
    runconfig: str,
    runconfig_dir: str = "runconfigs"
) -> BindMount:
    """
    Checks for a local runconfig for a given test and returns a bind mount for it.

    Parameters
    ----------
    workflow_name : str
        The name of the workflow.
    runconfig : str
        The name of the runconfig.
    runconfig_dir : str, optional
        The name of the directory on the system to search for runconfigs.
        Defaults to "runconfigs".

    Returns
    -------
    BindMount
        A BindMount object with the local and container locations of the runconfig, in
        read-only mode.

    Raises
    ------
    ValueError
        If the given runconfig could not be found.
    """
    runconfig_path: Path = Path(runconfig_dir)
    install_path: Path = Path(install_prefix())

    # Add the runconfig mount to the install prefix directory
    runconfig_lookup_path: Path = runconfig_path/workflow_name
    # Get the runconfig path on the host and image
    runconfig_host_path: Path = (runconfig_lookup_path/runconfig).absolute()
    runconfig_image_path: Path = install_path/runconfig
    # If the runconfig doesn't exist at the expected location, this is an error
    if not os.path.isfile(str(runconfig_host_path)):
        raise ValueError(
            f"Runconfig {runconfig} not found at {str(runconfig_host_path)}."
        )

    # Create the runconfig file bind mount
    return BindMount(
        host_mount_point=str(runconfig_host_path),
        image_mount_point=str(runconfig_image_path),
        permissions="ro"
    )


def run_series_workflow(
    test_params: WorkflowParams,
    main_test_name: str,
    test_sequence_info: Sequence[Mapping[str, Any]],
    bind_mounts: Sequence[BindMount]
) -> None:
    """
    Run a series of workflow tests in order.

    Parameters
    ----------
    test_params : WorkflowParams
        The workflow parameter object containing the image and its host mount points.
    main_test_name : str
        The name of the overall workflow test that the series is running on.
    test_series_info : Sequence[Mapping[str, Any]]
        A sequence of information dictionaries which contain information about subtests
        to be run in series.
    bind_mounts : Sequence[BindMount]
        The basic file binds associated with this test, including the input, output,
        and scratch directories.
    """
    for test_info in test_sequence_info:
        workflow_name = test_info["workflow"]

        # Get the location of the runconfig
        runconfig = test_info["runconfig"]
        runconfig_path = Path("runconfigs")/main_test_name

        # If the test is tagged, this tag will be a subdirectory under the test
        # directory. This is done by passing "test" into workflow_mounts.
        test_name = test_info["label"] if "label" in test_info.keys() else None

        # Print a message announcing the running of this workflow.
        test_msg: str = f"\nRunning workflow: {main_test_name} {workflow_name} "
        if test_name is not None:
            test_msg += f"{test_name} "
        test_msg += f"on image: {test_params.image_tag}.\n"
        print(test_msg)

        # Run the workflow.
        run_workflow(
            test_params=test_params,
            workflow_name=workflow_name,
            test=test_name,
            basic_mounts=bind_mounts,
            runconfig=runconfig,
            runconfig_dir=str(runconfig_path)
        )


def run_workflow(
    test_params: WorkflowParams,
    workflow_name: str,
    test: Optional[str],
    basic_mounts: Sequence[BindMount],
    runconfig: str,
    runconfig_dir: str = "runconfigs"
) -> None:
    """
    Runs a workflow test on the given image.

    Parameters
    ----------
    test_params : WorkflowParams
        The workflow parameter object containing the image and its host mount points.
    workflow_name : str
        The name of the workflow.
    test : str, optional
        The name of the test. If None is given, then a test subdirectory will not be
        added to the output and scratch directories.
    basic_mounts : Sequence[BindMount]
        The basic file binds associated with this test, including the input, output,
        and scratch directories.
    runconfig : str
        The location of the runconfig.
    runconfig_dir : str, optional
        The location of the directory in which runconfigs are held.
        Default is "runconfig".

    Raises
    ------
    CalledProcessError
        If the workflow fails.
    """

    # Get the test command.
    workflow_obj: Workflow = get_workflow_object(workflow_name=workflow_name)
    command = workflow_obj.get_command(runconfig=runconfig)

    mounts: List[BindMount] = [prepare_runconfig(
        workflow_name=workflow_name,
        runconfig=runconfig,
        runconfig_dir=runconfig_dir
    )] + list(basic_mounts)

    prepare_subdirectories(
        workflow_name=workflow_name, test=test, test_params=test_params
    )

    for mount in mounts:
        print(mount.mount_string())
    print()

    # Run the test on the image.
    try:
        test_params.image.run(command, bind_mounts=mounts, host_user=True)
    except CalledProcessError as err:
        raise TestFailedError("Workflow test failed with stderr:\n" +
                              str(err.stderr)) from err


@dataclass(frozen=True)
class WorkflowParams:
    """A data container holding parameters for a workflow."""

    # The image that the workflow will be run on.
    image: Image
    # The tag of the above image.
    image_tag: str
    # A mapping of input data repositories to their host paths.
    input_dict: Mapping[str, Path]
    # The host location of the output directory for the workflow.
    output_dir: Path
    # The host location of the scratch directory for the workflow.
    scratch_dir: Path
