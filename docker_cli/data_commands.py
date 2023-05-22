import json
import os
import threading
from pathlib import Path
from subprocess import DEVNULL, PIPE, list2cmdline, run
from typing import Dict, Iterable, List

from ._bind_mount import BindMount
from ._image import Image
from ._search import filtered_file_search, names_only_search, search_file


def data_search(
    file: os.PathLike[str] | str,
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
    List[Dict[str, str | Dict[str, str]]]
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
    file: os.PathLike[str] | str,
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
    file: os.PathLike[str] | str,
    tags: Iterable[Iterable[str]],
    names: Iterable[str],
    mount: os.PathLike[str] | str,
    all: bool = False,
    no_cache: bool = False,
    verbose_stderr: bool = False,
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
        If true, return all of the items in the database. Defaults to False.
    no_cache : bool, optional
        If true, return all of the items from the local cache before reinstalling.
        Defaults to False.
    verbose_stderr : bool, optional
        If true, suppress stderr output during fetch. Defaults to False.
    """
    rover_image = Image("rover")
    image_mount_loc = rover_image.run(
        command="echo $MOUNT_LOCATION", stdout=PIPE
    ).strip()

    # Acquire the path of the mount on the host
    host_mount_path = Path(mount)
    # If it isn't already a directory, create it
    if not host_mount_path.is_dir():
        cmd = ["mkdir", "-p", mount]
        run(cmd, check=True)
    host_mount_abspath = host_mount_path.resolve()

    # Build the host bind mount object
    mount_point = BindMount(
        src=host_mount_abspath,
        dst=image_mount_loc,
        permissions="rw",
    )

    # Find the locations of the data in the database
    data_values = data_search(
        file=file, tags=tags, names=names, fields=["name", "url", "files"], all=all
    )

    # Construct the set of tasks to fetch each data item.
    tasks: List[threading.Thread] = []

    for data_item in data_values:
        tasks.append(
            threading.Thread(
                target=_request_data_item,
                args=(data_item, mount_point, no_cache, verbose_stderr),
                name=f"{data_item}_DOWNLOADER",
            )
        )

    # Begin performing each of the fetch tasks.
    for task in tasks:
        task.start()
    # Await completion.
    for task in tasks:
        task.join()


def _request_data_item(
    data_item: Dict[str, str | Dict[str, str]],
    mount_point: BindMount,
    no_cache: bool,
    verbose_stderr: bool,
) -> None:
    """
    Given a description of a data item, use a given image to fetch and cache its files.

    Parameters
    ----------
    data_item : Dict[str, str | Dict[str, str]]
        A dictionary description of a data repository.
    rover_image : Image
        A Docker image with the Rover program.
    mount : os.PathLike[str]
        The location of the cache on the local machine.
    no_cache : bool, optional
        If true, return all of the items from the local cache before reinstalling.
        Defaults to False.
    verbose_stderr : bool, optional
        If true, suppress stderr output during fetch. Defaults to False.

    Returns
    -------
    asyncio.Task
        The async task associated with fetching the data.
    """
    rover_image = Image("rover")
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

    # Construct the command to be run.
    cmd = ["python", "-m", "rover", "fetch", "--repo", repo, "--url", url]
    if no_cache:
        cmd += ["--no-cache"]
    cmd += ["-f"]
    for kvp in file_kvps:
        assert isinstance(kvp, str)
        cmd += [kvp]

    command = list2cmdline(cmd)

    stderr = None if verbose_stderr else DEVNULL

    # Run the request on the rover image.
    rover_image.run(
        command=command, host_user=True, bind_mounts=[mount_point], stderr=stderr
    )
