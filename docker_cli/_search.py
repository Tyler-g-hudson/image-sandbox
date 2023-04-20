import fnmatch
import json
import re

from typing import Dict, Iterable, List, Optional, Union


def names_only_search(
        tags: Iterable[Optional[Iterable[str]]] = [],
        names: Iterable[Optional[str]] = [],
        filename: str = "workflowdata.json"
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
    filename : str, optional
        The name of the file to search. Defaults to "workflowdata.json".

    Returns
    -------
    List[str]
        The "name" fields of all accepted items.
    """
    items: List[Dict[str, Union[str, List[str]]]] = search_file(
        tags=tags,
        names=names,
        filename=filename
    )
    name_list: List[str] = []
    for item in items:
        assert isinstance(item["name"], str)
        name_list.append(item["name"])

    return name_list


def filtered_file_search(
    fields: Iterable[str],
    tags: Iterable[Optional[Iterable[str]]] = [],
    names: Iterable[Optional[str]] = [],
    filename: str = "workflowdata.json"
) -> List[Dict[str, Union[str, List[str]]]]:
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
    filename : str, optional
        The name of the file to search. Defaults to "workflowdata.json".

    Returns
    -------
    List[Dict[str, Union[str, List[str]]]]
        The list of items accepted by the search, with filtered tags.
    """
    items: List[Dict[str, Union[str, List[str]]]] = search_file(
        tags=tags, names=names, filename=filename
    )
    return_items: List[Dict[str, Union[str, List[str]]]] = []
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
    filename: str = "workflowdata.json"
) -> List[Dict[str, Union[str, List[str]]]]:
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
    filename : str, optional
        The name of the file to search. Defaults to "workflowdata.json".

    Returns
    -------
    List[Dict[str, Union[str, List[str]]]]
        The list of items accepted by the search.
    """
    with open(file=filename) as file:
        json_dict = json.load(file)

    data: List[Dict[str, Union[str, List[str]]]] = json_dict["data"]
    items: List[Dict[str, Union[str, List[str]]]] = list(
        filter(
            lambda x: _accept_item(x, tags, names),
            data
        )
    )

    return items


def _accept_item(
    item_dict: Dict[str, Union[str, List[str]]],
    tags: Iterable[Optional[Iterable[str]]],
    names: Iterable[Optional[str]]
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
    item_name = item_dict["name"]
    for name in names:
        match_object = re.match(fnmatch.translate(name), item_name)
        return True if match_object is not None else False

    item_tags = item_dict["tags"]
    for tag_list in tags:
        assert tag_list is not None # MyPy complains without this line
        if all(tag in item_tags for tag in tag_list):
            return True

    return False
