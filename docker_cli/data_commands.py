import json
import os
from pathlib import Path
from subprocess import PIPE, list2cmdline, run
from typing import Dict, Iterable, List, Union

from ._bind_mount import BindMount
from ._image import Image
from ._search import filtered_file_search, names_only_search, search_file


def data_search(
    file: Union[os.PathLike[str], str],
    tags: Iterable[Iterable[str]],
    names: Iterable[str],
    fields: Iterable[str],
    all: bool = False,
) -> List[Dict[str, Union[str, Dict[str, str]]]]:
    """
    Query a file database for items.

    Parameters
    ----------
    file : os.PathLike[str]
        The name of the database file.
    tags : Iterable[Iterable[str]]
        A set of sets of tags - this function will return the union of items that have
        all of any of the sets of tags passed in.
    names : Iterable[str]
        A list of names of data items to return.
    fields : Iterable[str]
        The set of fields to be returned on the data items. This should be a strict
        subset of the fields present on the items. Fields not included in this parameter
        will be filtered from the items prior to returning them.
    all : bool, optional
        If true, return all of the items in the database. Defaults to False

    Returns
    -------
    List[Dict[str, Union[str, Dict[str, str]]]]
        The items returned by the query, in dictionary format.
    """
    if all:
        if (any(True for _ in names)) or (any(True for _ in tags)):
            print("'all' cannot be used in conjunction with 'tags' or 'names'.")
            exit()

    if fields == []:
        return search_file(tags=tags, names=names, filename=file, all=all)

    filtered_search = filtered_file_search(
        fields=fields, names=names, tags=tags, filename=file, all=all
    )

    print(json.dumps(filtered_search, indent=2))

    return filtered_search


def data_names(
    file: Union[os.PathLike[str], str],
    tags: Iterable[Iterable[str]],
    names: Iterable[str],
    all: bool = False,
) -> List[str]:
    """
    Query a database file and return the names of all data items that match the query.

    Parameters
    ----------
    file : os.PathLike[str]
        The name of the database file.
    tags : Iterable[Iterable[str]]
        A set of sets of tags - this function will return the union of items that have
        all of any of the sets of tags passed in.
    names : Iterable[str]
        A list of names of data items to return.
    all : bool, optional
        If true, return all of the items in the database. Defaults to False

    Returns
    -------
    List[str]
        A list of the names of items that were returned by the query.
    """
    if all:
        if (any(True for _ in names)) or (any(True for _ in tags)):
            print("'all' cannot be used in conjunction with 'tags' or 'names'.")
            exit()

    return names_only_search(tags=tags, names=names, filename=file, all=all)


def data_fetch(
    file: Union[os.PathLike[str], str],
    tags: Iterable[Iterable[str]],
    names: Iterable[str],
    mount: Union[os.PathLike[str], str],
    all: bool = False,
    no_cache: bool = False,
) -> None:
    """
    Fetch and cache the set of items that were returned by a query on a database file.

    Parameters
    ----------
    file : os.PathLike[str]
        The name of the database file.
    tags : Iterable[Iterable[str]]
        A set of sets of tags - this function will return the union of items that have
        all of any of the sets of tags passed in.
    names : Iterable[str]
        A list of names of data items to return.
    mount : os.PathLike[str]
        The location of the cache on the local machine.
    all : bool, optional
        If true, return all of the items in the database. Defaults to False
    no_cache : bool, optional
        If true, return all of the items from the local cache before reinstalling.
        Defaults to False
    """
    rover_image = Image("rover")
    image_mount_loc = rover_image.run(
        command="echo $MOUNT_LOCATION", stdout=PIPE
    ).strip()

    host_mount_path = Path(mount)
    if not host_mount_path.is_dir():
        cmd = ["mkdir", "-p", mount]
        run(cmd, check=True)
    host_mount_abspath = host_mount_path.resolve()

    mount_point = BindMount(
        src=host_mount_abspath,
        dst=image_mount_loc,
        permissions="rw",
    )

    data_values = data_search(
        file=file, tags=tags, names=names, fields=["name", "url", "files"], all=all
    )

    for data_item in data_values:
        _request_data_item(
            data_item=data_item,
            rover_image=rover_image,
            mount_point=mount_point,
            no_cache=no_cache
        )


def _request_data_item(
    data_item: Dict[str, Union[str, Dict[str, str]]],
    rover_image: Image,
    mount_point: Mount,
    no_cache: bool
) -> None:
    """
    Given a description of a data item, use a given image to fetch and cache its files.

    Parameters
    ----------
    data_item : Dict[str, Union[str, Dict[str, str]]]
        A dictionary description of a data repository.
    rover_image : Image
        A Docker image with the Rover program.
    mount : os.PathLike[str]
        The location of the cache on the local machine.
    no_cache : bool, optional
        If true, return all of the items from the local cache before reinstalling.
        Defaults to False
    """
    repo = data_item["name"]
    assert isinstance(repo, str)
    url = data_item["url"]
    assert isinstance(url, str)

    # The below item is a dictionary of files and their hashes.
    files = data_item["files"]
    # Process them into List["[FILENAME]=[HASH]"] format.
    file_kvps = []
    for filename in files:
        assert isinstance(filename, str)
        assert isinstance(files, dict)
        hash = files[filename]
        assert isinstance(hash, str)
        file_kvps.append(f"{filename}={hash}")

    cmd = ["python", "-m", "rover", "fetch", "--repo", repo, "--url", url]
    if no_cache:
        cmd += ["--no-cache"]
    cmd += ["-f"]
    for kvp in file_kvps:
        assert isinstance(kvp, str)
        cmd += [kvp]

    command = list2cmdline(cmd)
    rover_image.run(command=command, host_user=True, mounts=[mount_point])
