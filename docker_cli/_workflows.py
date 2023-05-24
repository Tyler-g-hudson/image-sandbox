from __future__ import annotations

import json
import os
import shutil
import tempfile
from abc import ABC, abstractmethod
from contextlib import contextmanager
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


@contextmanager
def workflow_mounts(
    workflow_name: str,
    test: Optional[str],
    test_params: WorkflowParams,
    *,
    runconfig: str,
    runconfig_dir: str = "runconfig"
) -> Iterator[List[BindMount]]:
    """A context manager that generates a list of workflow bind mounts.

    If any mount is temporary on the host side, it will delete it automatically
    on context exit.

    Parameters
    ----------
    workflow_name : str
        The name of the workflow.
    test : str, optional
        The name of the test. If None is given, then a test subdirectory will not be
        added to the output and scratch directories.
    test_params: WorkflowParams
        The workflow parameters object containing information about the file mount
        locations on the host.
    runconfig : str
        The path to the runconfig.
    runconfig_dir : str, optional
        The location of the directory in which runconfigs are held.
        Default is "runconfig".

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
    input_dict: Dict[str, Path] = dict(test_params.input_dict)
    output_dir: Path = test_params.output_dir
    scratch_dir: Optional[Path] = test_params.scratch_dir
    runconfig_path: Path = Path(runconfig_dir)
    install_path: Path = Path(install_prefix())

    test_subdir = Path(workflow_name)/test if test is not None else Path(workflow_name)
    # If the output directory doesn't exist on the host, make it.
    if not os.path.isdir(str(output_dir/test_subdir)):
        os.makedirs(str(output_dir/test_subdir))
    # Create the output directory bind mount, place it in the bind mounts basic list.
    # This list will be copied and used for all tests that are run.
    bind_mounts = [
        BindMount(
            image_mount_point=str(install_path/"output"),
            host_mount_point=str((output_dir).absolute()),
            permissions="rw"
        )
    ]

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
    bind_mounts.append(BindMount(
        host_mount_point=str(runconfig_host_path),
        image_mount_point=str(runconfig_image_path),
        permissions="ro"
    ))

    # Create input files
    for repo in input_dict:
        host_path = input_dict[repo].absolute()
        image_path = install_path/"input"/repo
        bind_mounts.append(BindMount(
            image_mount_point=str(image_path),
            host_mount_point=str(host_path),
            permissions="ro"
        ))

    try:
        # If requested, add a local mount for the scratch directories.
        # Otherwise, add a temporary one so the docker container can get rw permissions.
        temp_scratch: bool = scratch_dir is None

        if temp_scratch:
            # Create the temp scratch file
            host_scratch_dir: str = tempfile.mkdtemp()
        else:
            assert isinstance(scratch_dir, Path)
            # Create the scratch file if it doesn't already exist
            if not os.path.isdir(str(scratch_dir/test_subdir)):
                os.makedirs(str(scratch_dir/test_subdir))
            host_scratch_dir = str(scratch_dir.absolute())

        # Create the scratch file bind mount
        bind_mounts.append(BindMount(
            image_mount_point=str(install_path/"scratch"/workflow_name),
            host_mount_point=host_scratch_dir,
            permissions="rw"
        ))

        yield bind_mounts
    finally:
        # If a temporary scratch file was created, remove it.
        if temp_scratch:
            shutil.rmtree(host_scratch_dir)


def run_series_workflow(
    test_params: WorkflowParams,
    main_test_name: str,
    test_sequence_info: Sequence[Mapping[str, Any]]
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
    """
    for test_info in test_sequence_info:
        workflow_name = test_info["workflow"]

        # Get the location of the runconfig
        runconfig = test_info["runconfig"]
        runconfig_path = Path("runconfigs")/main_test_name

        # If the test is tagged, this tag will be a subdirectory under the test
        # directory. This is done by passing "test" into workflow_mounts.
        test_name = test_info["tag"] if "tag" in test_info.keys() else None

        test_msg: str = f"\nRunning workflow test: {main_test_name} {workflow_name} "
        if test_name is not None:
            test_msg += f"{test_name} "
        test_msg += f"on image: {test_params.image_tag}.\n"

        print(test_msg)
        # Run the workflow.
        run_workflow(
            test_params=test_params,
            workflow_name=workflow_name,
            test=test_name,
            runconfig=runconfig,
            runconfig_dir=str(runconfig_path)
        )


def run_workflow(
    test_params: WorkflowParams,
    workflow_name: str,
    test: Optional[str],
    runconfig: str,
    runconfig_dir: str = "runconfigs"
) -> None:
    """Runs a workflow test on the given image.

    Parameters
    ----------
    test_params : WorkflowParams
        The workflow parameter object containing the image and its host mount points.
    workflow_name : str
        The name of the workflow.
    test : str, optional
        The name of the test. If None is given, then a test subdirectory will not be
        added to the output and scratch directories.
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

    # Setup workflow mounts. Automatically generates and removes temporary files
    # if necessary.
    with workflow_mounts(
        workflow_name=workflow_name,
        test_params=test_params,
        test=test,
        runconfig=runconfig,
        runconfig_dir=runconfig_dir
    ) as bind_mounts:
        # Run the test on the image.
        try:
            test_params.image.run(command, bind_mounts=bind_mounts, host_user=True)
        except CalledProcessError as err:
            raise TestFailedError("Workflow test failed with stderr:\n" +
                                  err.stderr) from err


class WorkflowParams:
    """A data container holding parameters for a workflow."""

    def __init__(
        self,
        image: Image,
        image_tag: str,
        input_dict: Mapping[str, Path],
        output_dir: str | Path,
        scratch_dir: Optional[str | Path]
    ):
        # The image that the workflow is to be run on.
        self._image: Image = image
        # The tag of the above image.
        self._image_tag: str = image_tag
        # The mapping that connects the workflow inputs to its host locations.
        self._input_dict: Mapping[str,  Path] = input_dict
        # The output directory on the host.
        self._output_dir: Path = Path(output_dir).absolute()
        # The scratch directory on the host, or None if no scratch directory is
        # specified.
        if scratch_dir is not None:
            self._scratch_dir: Optional[Path] = Path(scratch_dir).absolute()
        else:
            self._scratch_dir = None

    # Properties
    @property
    def image(self) -> Image: return self._image

    @property
    def image_tag(self) -> str: return self._image_tag

    @property
    def input_dict(self) -> Mapping[str,  Path]: return self._input_dict

    @property
    def output_dir(self) -> Path: return self._output_dir

    @property
    def scratch_dir(self) -> Optional[Path]: return self._scratch_dir
