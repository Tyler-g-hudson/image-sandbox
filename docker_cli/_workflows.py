from __future__ import annotations

import json
import os
from abc import ABC, abstractmethod
from typing import Dict, List, Tuple


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
