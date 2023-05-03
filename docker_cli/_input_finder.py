from __future__ import annotations

import json
import os
from typing import Dict, List, Mapping, Optional, Sequence, Tuple


def get_input_files_for_test(
    workflow_name: str,
    test_name: str,
    input_dirs: Sequence[str],
    cache_dirs: Sequence[str],
    file: str = "workflowtests.json"
) -> Dict[str, os.PathLike[str] | str]:
    """
    Associates the input repositories needed by a given test with their locations.

    Parameters
    ----------
    workflow_name : str
        The name of the workflow for the test.
    test_name : str
        The name of the test.
    input_dirs : Sequence[str]
        The list of input directories in [PATH] or [LABEL]:[PATH] format.
    cache_dirs : Sequence[str]
        The list of cache directories.
    file : str, optional
        The filename of the workflow test database. Defaults to "workflowtests.json".

    Returns
    -------
    Dict[str, str]
        A dictionary in {input_repository:path} format.
    """
    labels_to_dirs = input_dict_parse(input_dirs)

    print("LABELS_TO_DIRS:")
    print(json.dumps(input_dirs, indent=2))

    test_info = get_test(
        workflow_name=workflow_name,
        test_name=test_name,
        filename=file
    )

    print("\nTEST_INFO:")
    print(json.dumps(test_info, indent=2))

    req_repos, label_repo_dict = generate_search_tables(test_info)

    print("\nREQUIRED_REPOSITORIES:")
    print(json.dumps(req_repos, indent=2))
    print("\nLABEL_REPO_DICT:")
    print(json.dumps(label_repo_dict, indent=2))

    inputs_to_paths = search_for_inputs(
        required_repositories=req_repos,
        label_repo_dict=label_repo_dict,
        cache_dirs=cache_dirs,
        input_dirs=labels_to_dirs
    )

    print("\nINPUTS_TO_PATHS:")
    print(json.dumps(inputs_to_paths, indent=2))

    return inputs_to_paths


def search_for_inputs(
    required_repositories: Sequence[str],
    label_repo_dict: Mapping[str, str],
    cache_dirs: Sequence[os.PathLike[str] | str],
    input_dirs: Optional[str | Mapping[str, os.PathLike[str] | str]] = None
) -> Dict[str, os.PathLike[str] | str]:
    """
    Finds the locations of all needed input repositories.

    Parameters
    ----------
    required_repositories : Sequence[str]
        The repositories needed.
    label_repo_dict : Mapping[str, str]
        The set of labels assigned to the repositories.
    cache_dirs : Sequence[os.PathLike[str], str]
        The list of cache directories provided.
    input_dirs : str | Mapping[str, os.PathLike[str]], optional
        The directory or set of labeled directories provided.

    Returns
    -------
    Dict[str, os.PathLike[str]]
        A dictionary relating the needed repositories to their paths.

    Raises
    ------
    ValueError
        If an unlabeled input dir was supplied when multiple labeled repositories
        are required.
    """
    # If an unlabeled input directory is given, there should only be one needed input.
    # If there are more needed inputs, this constitutes an error.
    if isinstance(input_dirs, str):
        if len(required_repositories) == 1:
            return {required_repositories[0]: input_dirs}
        raise ValueError("Unlabeled input directories only allowed for tests with "
                         "only one input.")

    # The dictionary to be output: Maps repositories to their paths.
    inputs_to_paths: Dict[str, os.PathLike[str] | str] = {}
    # A copy of the list of repositories being searched for, to be checked in case
    # a repository was not found.
    unmatched_repositories: List[str] = []
    unmatched_repositories.extend(required_repositories)

    if input_dirs is not None:
        # A list of the paths provided by the user, to be checked to ensure values that
        # are passed are all used.
        unmatched_input_dir_paths: List[os.PathLike[str] | str] = \
            list(input_dirs.values())

        # Check the user's provided labels for validity.
        accepted_labels = list(
            filter(
                lambda label: _in_labels(label_repo_dict, label), input_dirs.keys()
            )
        )

        # For all of the labels identified, update the output dict and other lists.
        for label in accepted_labels:
            repo = label_repo_dict[label]
            if repo not in unmatched_repositories:
                raise ValueError(f"Repository {repo} referenced twice.")
            path = input_dirs[label]
            inputs_to_paths[repo] = path
            unmatched_input_dir_paths.remove(path)
            unmatched_repositories.remove(repo)

        # If the user provided more input directory paths than requested, this is an
        # error.
        if len(unmatched_input_dir_paths) > 0:
            raise ValueError("Supplied input directory was not matched to a label or "
                             "repository name.")

    # Search in the cache dirs for the given repo names.
    for cache_dir in cache_dirs:
        found_repos = list(
            filter(
                lambda repo: (_in_cache(cache_dir, repo)), unmatched_repositories
            )
        )
        for repo in found_repos:
            unmatched_repositories.remove(repo)
            inputs_to_paths[repo] = f"{cache_dir}/{repo}"
        if len(unmatched_repositories) == 0:
            break

    # Check to see if repositories were not found. If so, error.
    if len(unmatched_repositories) > 0:
        unmatched_repositories_str = ", ".join(unmatched_repositories)
        raise ValueError(f"Required repositories not found in supplied locations: "
                         f"{unmatched_repositories_str}")

    return inputs_to_paths


def _in_labels(
    labeled_dict: Mapping[str, str],
    label: str
) -> bool:
    """
    Determines if a label is in a labeled dict. Errors if not.

    Parameters
    ----------
    labeled_dict : Dict[str, str]
        A dictionary whose keys are labels.
    label : str
        A label.

    Returns
    -------
    bool
        True if no error.

    Raises
    ------
    ValueError
        If the label is not found.
    """
    is_in_labels = label in labeled_dict
    if not is_in_labels:
        raise ValueError(f"Label {label} was not expected.")
    return True


def _in_cache(
    cache_dir: os.PathLike[str] | str,
    repo_name: str
) -> bool:
    """
    Determines if a repository directory is in a given cache.

    Parameters
    ----------
    cache_dir : os.PathLike[str] | str
        The path to the cache directory.
    repo_name : str
        The name of the repository.

    Returns
    -------
    bool
        True if the repository name exists as a subdirectory in the first level of the
        cache directory.
    """
    expected_dir = os.path.join(cache_dir, repo_name)
    return os.path.isdir(expected_dir)


def get_test(
    workflow_name: str,
    test_name: str,
    filename: str = "workflowtests.json"
) -> Dict[str, str | List[str] | Dict[str, str]]:
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
    Dict[str, str | List[str] | Dict[str, str]]
        A dictionary representing information about the test.
    """
    with open(filename) as file:
        file_dict = json.load(fp=file)
    workflow_dict = file_dict[workflow_name]
    return workflow_dict["tests"][test_name]


def generate_search_tables(
    test_dict: Mapping[str, str | List[str] | Mapping[str, str]]
) -> Tuple[List[str], Dict[str, str]]:
    """
    Generates the search tables for the given test information.

    Parameters
    ----------
    test_dict : Mapping[str, str  |  List[str]  |  Mapping[str, str]]
        A dictionary representing information about a test.

    Returns
    -------
    Tuple[List[str], Dict[str, str]]
        The list of repositories associated with the test inputs, and a dictionary of
        labels for those repositories in {label:repository} format.
    """
    inputs = test_dict["inputs"]
    input_label_dict: Dict[str, str] = {}

    if isinstance(inputs, dict):
        input_repositories: List[str] = list(inputs.values())
        for label in inputs:
            repo_name = inputs[label]
            input_label_dict[label] = repo_name
            input_label_dict[repo_name] = repo_name
        return input_repositories, input_label_dict

    if isinstance(inputs, str):
        input_repositories = [inputs]
    else:
        input_repositories = list(inputs)

    for input in input_repositories:
        input_label_dict[input] = input

    return input_repositories, input_label_dict


def input_dict_parse(
    kvp_strings: Sequence[str]
) -> Dict[str, os.PathLike[str] | str] | str:
    """
    Splits a set of strings into key-value pairs in a dictionary.

    Parameters
    ----------
    kvp_strings : Sequence[str]
        The set of strings to be parsed. Should be in "[PATH]" or "[LABEL]:[PATH]"
        format. Should only be in "[PATH]" format if len(kvp_strings) == 1.

    Returns
    -------
    Dict[str, str] | str
        A dictionary containing the key-value pairs of input directory labels and paths,
        or a single string containing the path of the sole input directory.

    Raises
    ------
    ValueError
        If a given string is improperly formatted.
    """
    length = len(kvp_strings)
    ret_dict = {}
    # Populate the above dictionary with each of the strings.
    for kvp in kvp_strings:
        key, value = check_input_kvp(kvp)
        if key == value:
            # This will happen if the user passes in [PATH].
            if length == 1:
                # Praise be unto MyPy. I lay this sacrifice before it so that it may
                # be appeased upon the day of my pre-commit.
                assert isinstance(value, str)
                return value
            ValueError("Unlabeled input directories only allowed for tests with only "
                       "one input.")
        ret_dict[key] = value

    return ret_dict


def check_input_kvp(kvp_str: str) -> Tuple[str, os.PathLike[str] | str]:
    """
    Checks an input directory key-value pair string and returns the key and value.

    Parameters
    ----------
    kvp_str : str
        A key-value pair string in format [PATH] or [LABEL]:[PATH].

    Returns
    -------
    Tuple[str, str]
        The key and value. If [PATH] was given, these are the same.

    Raises
    ------
    ValueError
        If an empty string or one with too many ":" separators is passed.
    """
    string_kvp = kvp_str.strip()
    if len(string_kvp) == 0:
        raise ValueError("An empty string is not a valid file reference.")

    kvp = string_kvp.split(":")
    # If the length of the split string is not 1 or 2, then the string was empty or
    # too many ":" characters were used. Reject this string.
    if len(kvp) > 2:
        raise ValueError(f"{kvp_str} is not a valid file reference.")

    # If the string splits into two, the key is the first split string and the value is
    # the second one.
    if len(kvp) == 2:
        return kvp[0], kvp[1]
    # If only one string is returned, then the key and value are the same.
    else:
        return kvp[0], kvp[0]


this_test = get_input_files_for_test(
    "insar", "insar_UAVSAR_Snjoaq_14511_18034-014_18044-015_143",
    input_dirs=["ref:./test"],
    cache_dirs=["./mnt"]
)
