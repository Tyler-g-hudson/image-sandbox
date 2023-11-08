from __future__ import annotations

import fnmatch
import json
import re
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from .defaults import default_workflowdata_path


def names_only_search(
    tags: Iterable[Optional[Iterable[str]]] = [],
    names: Iterable[Optional[str]] = [],
    filename: Path = default_workflowdata_path(),
    all: bool = False,
) -> List[str]:
    """
    Searches a JSON file for items, returns their names.

    Parameters
    ----------
    tags : Iterable[Iterable[str]], optional
        An iterator of iterators of tags. The inner iterator is used to find the
        items that intersect all tags within the iterator. The outer iterator accepts
        the union of all items accepted by all inner iterators. Defaults to [].
    names : Iterable[str], optional
        The names to be matched. Defaults to [].
    filename : Path, optional
        The name of the file to search. Defaults to the default workflowdata path.
    all : bool, optional
        If True, ignores other options and returns all items in the file.
        Defaults to False.

    Returns
    -------
    List[str]
        The "name" fields of all accepted items.
    """
    # Search the data file for applicable data.
    items: List[Dict[str, str | Dict[str, str]]] = search_file(
        tags=tags, names=names, filename=filename, all=all
    )
    # Get the set of names associated with that data and return it.
    name_list: List[str] = []
    for item in items:
        assert isinstance(item["name"], str)
        name_list.append(item["name"])

    return name_list


def filtered_file_search(
    fields: Iterable[str],
    tags: Iterable[Optional[Iterable[str]]] = [],
    names: Iterable[Optional[str]] = [],
    filename: Path = default_workflowdata_path(),
    all: bool = False,
) -> List[Dict[str, str | Dict[str, str]]]:
    """
    Searches a JSON file, returns accepted items with only the given fields.

    Parameters
    ----------
    fields : Iterable[str]
        The set of tags to be returned.
    tags : Iterable[Iterable[str]], optional
        An iterator of iterators of tags. The inner iterator is used to find the
        items that intersect all tags within the iterator. The outer iterator accepts
        the union of all items accepted by all inner iterators. Defaults to [].
    names : Iterable[str], optional
        The names to be matched. Defaults to [].
    filename : Path, optional
        The name of the file to search. Defaults to the default workflowdata path.
    all : bool, optional
        If True, ignores other options and returns all items in the file.
        Defaults to False.

    Returns
    -------
    List[Dict[str, str or List[str]]]
        The list of items accepted by the search, with filtered tags.
    """
    # Search the data file for applicable data.
    items: List[Dict[str, str | Dict[str, str]]] = search_file(
        tags=tags, names=names, filename=filename, all=all
    )

    # Get the values at each returned item associated with the given filter.
    return_items: List[Dict[str, str | Dict[str, str]]] = []
    for item in items:
        # The item is a dict. Get all of the desired fields from it.
        new_item = {}
        for key in item:
            if key in fields:
                new_item[key] = item[key]
        return_items.append(new_item)

    return return_items


def search_file(
    tags: Iterable[Optional[Iterable[str]]] = [],
    names: Iterable[Optional[str]] = [],
    filename: Path = default_workflowdata_path(),
    all: bool = False,
) -> List[Dict[str, str | Dict[str, str]]]:
    """
    Return the list of unique objects in a JSON file that have given tags or name.

    This search accepts the union of any item identified by name or containing all of
    any set of tags given.

    Parameters
    ----------
    tags : Iterable[Iterable[str]], optional
        An iterator of iterators of tags. The inner iterator is used to find the
        items that intersect all tags within the iterator. The outer iterator accepts
        the union of all items accepted by all inner iterators. Defaults to [].
    names : Iterable[str], optional
        The names to be matched. Defaults to [].
    filename : Path, optional
        The name of the file to search. Defaults to the default workflowdata path.
    all : bool, optional
        If True, ignores other options and returns all items in the file.
        Defaults to False.

    Returns
    -------
    List[Dict[str, str or List[str]]]
        The list of items accepted by the search.
    """

    # Open the data file and load it into a JSON dictionary object.
    with open(file=str(filename)) as file:
        json_dict = json.load(file)

    # Get everything held underneath the "data" key on the dictionary.
    data: List[Dict[str, str | Dict[str, str]]] = json_dict["data"]
    # If every item was requested, return everything.
    if all:
        return data

    # Otherwise, filter out only the accepted items using the _accept_item function.
    items: List[Dict[str, str | Dict[str, str]]] = list(
        filter(lambda x: _accept_item(x, tags, names), data)
    )
    return items


def _accept_item(
    item_dict: Dict[str, str | Dict[str, str]],
    tags: Iterable[Optional[Iterable[str]]],
    names: Iterable[Optional[str]],
) -> bool:
    """
    Accepts or rejects an item.

    Parameters
    ----------
    item_dict :
        The dictionary item to be accepted or rejected.
    tags : Iterable[Iterable[str]]
        The set of sets of tags to be used as search terms.
    names : Iterable[str]
        The set of names to be used as search terms.

    Returns
    -------
    bool
        True if:
        -   The name of the item matches one of the names given.
        -   The tags on the item are a superset of any of the sets of tags given.
        Else False.
    """
    # Get the name of the item. This name should be a string.
    item_name = item_dict["name"]
    assert isinstance(item_name, str)
    # For each name in the names list, check if it matches this one. If so, return True.
    for name in names:
        assert isinstance(name, str)
        # Check for the name using a wildcard check.
        match_object = re.match(fnmatch.translate(name), item_name)
        if match_object is not None:
            return True

    # Get the tags of the item.
    item_tags = item_dict["tags"]
    # For each tag list in the overall set of lists,
    for tag_list in tags:
        assert tag_list is not None  # MyPy complains without this line
        # Match if the item contains each tag in the list.
        if all(tag in item_tags for tag in tag_list):
            return True

    # If neither of the above returned True, reject the item.
    return False