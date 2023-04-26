import json
import os
from pathlib import Path
from subprocess import PIPE, list2cmdline
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
    rover_image = Image("rover")
    image_mount_loc = rover_image.run(
        command="echo $MOUNT_LOCATION", stdout=PIPE
    ).strip()
    print(image_mount_loc)

    host_mount_abspath = Path(mount).resolve()
    print(host_mount_abspath)
    #

    mount_point = BindMount(
        src=host_mount_abspath,
        dst=image_mount_loc,
        permissions="rw",
    )

    data_values = data_search(
        file=file, tags=tags, names=names, fields=["name", "url", "files"], all=all
    )

    for data_item in data_values:
        repo = data_item["name"]
        assert isinstance(repo, str)
        url = data_item["url"]
        assert isinstance(url, str)

        # The below item is a dictionary of files and their hashes.
        files = data_item["files"]
        # Process them into List["[FILENAME]:[HASH]"] format.
        file_kvps = []
        for filename in files:
            assert isinstance(filename, str)
            assert isinstance(files, dict)
            hash = files[filename]
            assert isinstance(hash, str)
            file_kvps.append(f"{filename}:{hash}")

        cmd = ["python", "-m", "rover", "fetch", "--repo", repo, "--url", url]
        if no_cache:
            cmd += ["--no-cache"]
        cmd += ["-f"]
        for kvp in file_kvps:
            assert isinstance(kvp, str)
            cmd += [kvp]

        command = list2cmdline(cmd)
        print(command)
        rover_image.run(command=command, host_user=True, mounts=[mount_point])
