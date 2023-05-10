from __future__ import annotations

import os
import re
import shutil
import tempfile
from pathlib import Path
from shlex import split
from subprocess import DEVNULL, PIPE, run
from textwrap import dedent
from typing import Dict, Iterable, List, Optional, Sequence

from ._bind_mount import BindMount
from ._docker_cmake import (
    build_prefix,
    cmake_build_dockerfile,
    cmake_config_dockerfile,
    cmake_install_dockerfile,
    install_prefix,
)
from ._docker_distrib import distrib_dockerfile
from ._docker_git import git_clone_dockerfile
from ._docker_mamba import mamba_lockfile_command
from ._image import Image
from ._utils import is_conda_pkg_name, test_image, universal_tag_prefix


def clone(tag: str, base: str, repo: str, branch: str = "", no_cache: bool = False):
    """
    Builds a docker image containing the requested Git repository.

    .. note:
        With this image, the workdir is moved to the github repo's root directory.

    Parameters
    ----------
    tag : str
        The image tag.
    base : str
        The base image tag.
    repo : str
        The name of the Git repo (in [USER]/[REPO_NAME] format)
    branch : str
        The branch of the Git repo. Defaults to "".
    no_cache : bool, optional
        Run Docker build with no cache if True. Defaults to False.

    Returns
    -------
    Image
        The generated image.
    """

    # Check that the repo pattern matches the given repo string.
    github_repo_pattern = re.compile(
        pattern=r"^(?P<user>[a-zA-Z0-9-]+)\/(?P<repo>[a-zA-Z0-9-]+)$", flags=re.I
    )
    github_repo_match = re.match(github_repo_pattern, repo)
    if not github_repo_match:
        raise ValueError(
            f"Malformed GitHub repo name: {repo} - "
            "Please use form [USER]/[REPO_NAME]."
        )
    match_dict = github_repo_match.groupdict()
    repo_name = match_dict["repo"]

    prefix = universal_tag_prefix()
    img_tag = tag if tag.startswith(prefix) else f"{prefix}-{tag}"

    header, body = git_clone_dockerfile(
        git_repo=repo, repo_branch=branch, folder_name=repo_name
    )

    dockerfile = f"{header}\n\nFROM {base}\n\n{body}"

    return Image.build(tag=img_tag, dockerfile_string=dockerfile, no_cache=no_cache)


def insert(tag: str, base: str, path: str, no_cache: bool = False):
    """
    Builds a docker image with the contents of the given path copied onto it.

    The directory path on the image has the same name as the topmost directory
    of the given path. e.g. giving path "/tmp/dir/subdir" will result in the contents of
    this path being saved in "/subdir" on the generated image.

    Parameters
    ----------
    tag : str
        The image tag.
    base : str
        The base image tag.
    path : str
        The path to be copied.
    no_cache : bool, optional
        Run Docker build with no cache if True. Defaults to False.

    Returns
    -------
    Image
        The generated image.
    """

    prefix = universal_tag_prefix()
    img_tag = tag if tag.startswith(prefix) else f"{prefix}-{tag}"

    # The absolute path of the given file will be the build context.
    # This is necessary because otherwise docker may be unable to find the files.
    path_absolute = os.path.abspath(path)
    # Additionally, the top directory of the given path will be the name of the
    # directory in the image.
    if os.path.isdir(path):
        target_dir = os.path.basename(path_absolute)
    else:
        target_dir = os.path.basename(os.path.dirname(path_absolute))

    # This dockerfile is very simple, we can make it right here.
    dockerfile = dedent(
        f"""
        FROM {base}

        COPY --chown=$DEFAULT_GID:$DEFAULT_UID --chmod=755 . "/{target_dir}/"

        WORKDIR "/{target_dir}"
        USER $DEFAULT_USER
        """
    ).strip()

    # Build the image with the context at the absolute path of the given path.
    return Image.build(
        tag=img_tag,
        context=path_absolute,
        dockerfile_string=dockerfile,
        no_cache=no_cache,
    )


def configure(
    tag: str, base: str, build_type: str, no_cuda: bool, no_cache: bool = False
) -> Image:
    """
    Produces an image with CMAKE configured.

    Parameters
    ----------
    tag : str
        The image tag.
    base : str
        The base image tag.
    build_type : str
        The type of CMAKE build.
    no_cuda : bool
        If True, build without CUDA.
    no_cache : bool, optional
        Run Docker build with no cache if True. Defaults to False.

    Returns
    -------
    Image
        The generated image.
    """
    dockerfile: str = cmake_config_dockerfile(
        base=base,
        build_type=build_type,
        with_cuda=not no_cuda,
    )

    prefix = universal_tag_prefix()
    img_tag = tag if tag.startswith(prefix) else f"{prefix}-{tag}"
    return Image.build(tag=img_tag, dockerfile_string=dockerfile, no_cache=no_cache)


def compile(tag: str, base: str, no_cache: bool = False) -> Image:
    """
    Produces an image with the working directory compiled.

    Parameters
    ----------
    tag : str
        The image tag.
    base : str
        The base image tag.
    no_cache : bool, optional
        Run Docker build with no cache if True. Defaults to False.

    Returns
    -------
    Image
        The generated image.
    """
    dockerfile: str = cmake_build_dockerfile(base=base)

    prefix = universal_tag_prefix()
    img_tag = tag if tag.startswith(prefix) else f"{prefix}-{tag}"
    return Image.build(tag=img_tag, dockerfile_string=dockerfile, no_cache=no_cache)


def install(tag: str, base: str, no_cache: bool = False) -> Image:
    """
    Produces an image with the compiled working directory code installed.

    .. note:
        With this image, the workdir is moved to $BUILD_PREFIX.

    Parameters
    ----------
    tag : str
        The image tag.
    base : str
        The base image tag.
    no_cache : bool, optional
        Run Docker build with no cache if True. Defaults to False.

    Returns
    -------
    Image
        The generated image.
    """
    image: Image = Image(base)

    is_64_bit = test_image(image=image, expression='"$BUILD_PREFIX/lib64"')

    if is_64_bit:
        lib = "lib64"
    else:
        lib = "lib"

    dockerfile: str = cmake_install_dockerfile(base=base, ld_lib=lib)

    prefix = universal_tag_prefix()
    img_tag = tag if tag.startswith(prefix) else f"{prefix}-{tag}"
    return Image.build(tag=img_tag, dockerfile_string=dockerfile, no_cache=no_cache)


def build_all(
    tag: str,
    base: str,
    copy_path: str,
    repo: Optional[str],
    build_type: str,
    no_cuda: bool,
    no_cache: bool = False,
    branch: str = "",
) -> Dict[str, Image]:
    """
    Fully compiles and builds a Git repo with cmake.

    Parameters
    ----------
    tag : str
        The image tag prefix.
    base : str
        The base image tag.
    copy_path : str
        The path to be copied. If used, no repo will be downloaded.
    repo : str
        The name of the Git repo, in [USER]/[REPO_NAME] format
    build_type : str
        The CMAKE build type
    no_cuda : bool
        If True, build without CUDA.
    no_cache : bool, optional
        Run Docker build with no cache if True. Defaults to False.
    branch : str
        The branch of the Git repo. Defaults to "".

    Returns
    -------
    Dict[str, Image]
        A dict of images produced by this process.
    """
    
    prefix = universal_tag_prefix()

    images: Dict[str, Image] = {}

    # If the user has indicated a path to copy, the code should copy that.
    # Otherwise, the code should fetch a git repository.
    is_insert = copy_path is not None

    initial_tag: str = ""
    if is_insert:
        path_absolute = os.path.abspath(copy_path)
        if os.path.isdir(copy_path):
            top_dir = os.path.basename(path_absolute)
        else:
            top_dir = os.path.basename(os.path.dirname(path_absolute))

        insert_tag = f"{prefix}-{tag}-file-{top_dir}"
        insert_image = insert(
            base=base,
            tag=insert_tag,
            path=copy_path,
            no_cache=no_cache,
        )
        images[insert_tag] = insert_image
        initial_tag = insert_tag
    else:
        git_repo_tag = f"{prefix}-{tag}-git-repo"
        assert repo is not None
        git_repo_image = clone(
            base=base,
            tag=git_repo_tag,
            repo=repo,
            branch=branch,
            no_cache=no_cache,
        )
        images[git_repo_tag] = git_repo_image
        initial_tag = git_repo_tag

    configure_tag = f"{prefix}-{tag}-configured"
    configure_image = configure(
        tag=configure_tag,
        base=initial_tag,
        build_type=build_type,
        no_cuda=no_cuda,
        no_cache=no_cache,
    )
    images[configure_tag] = configure_image

    build_tag = f"{prefix}-{tag}-built"
    build_image = compile(tag=build_tag, base=configure_tag, no_cache=no_cache)
    images[build_tag] = build_image

    install_tag = f"{prefix}-{tag}-installed"
    install_image = install(tag=install_tag, base=build_tag, no_cache=no_cache)
    images[install_tag] = install_image

    return images


def distributable(tag: str, base: str, source_tag: str) -> Image:
    """
    Produces a distributable image.

    Parameters
    ----------
    tag : str
        The image tag.
    base : str
        The base image tag.
    source_tag : str
        The tag of the source image from which to acquire the install directory.

    Returns
    -------
    Image
        The generated image.
    """
    base_image: Image = Image(base)

    is_64_bit = test_image(image=base_image, expression='"$BUILD_PREFIX/lib64"')

    if is_64_bit:
        lib = "lib64"
    else:
        lib = "lib"

    dockerfile = distrib_dockerfile(
        base=base,
        source_tag=source_tag,
        source_path=install_prefix(),
        distrib_path=install_prefix(),
        ld_lib=lib,
    )

    return Image.build(tag=tag, dockerfile_string=dockerfile, no_cache=True)


def test(
    tag: str,
    logfile: os.PathLike[str] | str,
    compress_output: bool,
    quiet_fail: bool,
) -> None:
    """
    Run all ctests from the docker image work directory.

    Parameters
    ----------
    tag : str
        The tag of the image to test.
    logfile : os.PathLike[str] | str
        The name of the XML test output file.
    compress_output : bool
        If True, compress the output of the test.
    quiet_fail : bool
        If True, don't output on failure.
    """
    host_volume_path = "./Testing/Temps"
    image_volume_path = "/tmp/Testing"
    image: Image = Image(tag)

    test_cmd = ["(", "ctest"]

    # Add arguments
    if not compress_output:
        test_cmd += ["--no-compress-output"]
    if not quiet_fail:
        test_cmd += ["--output-on-failure"]

    test_cmd += ["-T", "Test", "||", "true", ")"]
    file_cmd = [
        "cp",
        f"{build_prefix()}/Testing/*/Test.xml",
        f"{image_volume_path}/{logfile}",
    ]

    cmd = test_cmd + ["&&"] + file_cmd

    host_vol_abspath = Path(host_volume_path).resolve()
    host_vol_abspath.parent.mkdir(parents=True, exist_ok=True)

    bind_mount = BindMount(
        src=image_volume_path,
        dst=host_vol_abspath,
        permissions="rw",
    )

    command = " ".join(cmd)
    image.run(command=command, host_user=True, bind_mounts=[bind_mount])


def dropin(tag: str) -> None:
    """
    Initiates a drop-in session on an image.

    Parameters
    ----------
    tag : str
        The tag or ID of the image.
    """
    image: Image = Image(tag)

    image.drop_in()


def remove(
    tags: Iterable[str],
    force: bool = False,
    verbose: bool = False,
    ignore_prefix: bool = False,
) -> None:
    """
    Remove all Docker images that match a given tag or wildcard pattern.

    This tag or wildcard will take the form [UNIVERSAL PREFIX]-[tag or wildcard] if the
    prefix does not already match this.

    Parameters
    ----------
    tags : Iterable[str]
        An iterable of tags or wildcards to be removed.
    force : bool, optional
        Whether or not to force the removal. Defaults to False.
    verbose : bool, optional
        Whether or not to print output for removals verbosely. Defaults to False.
    ignore_prefix: bool, optional
        Whether or not to ignore the universal prefix and only use the tag or wildcard.
        Use with caution, as this will remove ALL images matching the wildcard.
        e.g. ``remove(["*"], ignore_prefix = True)`` will remove all images.
    """
    force_arg = "--force " if force else ""

    # The None below corresponds to printing outputs to the console. DEVNULL causes the
    # outputs to be discarded.
    output = None if verbose else DEVNULL

    # Search for and delete all images matching each tag or wildcard.
    for tag in tags:
        prefix = universal_tag_prefix()
        search = tag if (tag.startswith(prefix) or ignore_prefix) else f"{prefix}-{tag}"
        if verbose:
            print(f"Attempting removal for tag: {search}")

        # Search for all images whose name matches this tag, acquire a list
        search_command = split(f'docker images --filter=reference="{search}" -q')
        search_result = run(search_command, text=True, stdout=PIPE, stderr=output)
        # An empty return indicates that no such images were found. Skip to the next.
        if search_result.stdout == "":
            if verbose:
                print(f"No images found matching pattern {search}. Proceeding.")
            continue
        # The names come in a list delimited by newlines. Reform this to be delimited
        # by spaces to use with `Docker rmi`.
        search_result_str = search_result.stdout.replace("\n", " ")

        # Remove all images in the list
        command = split(f"docker rmi {force_arg}{search_result_str}")
        run(command, stdout=output, stderr=output)
    if verbose:
        print("Docker removal process completed.")


def make_lockfile(
    tag: str, file: os.PathLike[str] | str, env_name: str = "base"
) -> None:
    """
    Makes a lockfile from an image.

    ..warning:
        This function only works for images that have an environment set up.

    Parameters
    ----------
    tag : str
        The tag of the image
    file : os.PathLike[str] | str
        The file to be output to.
    env_name: str
        The name of the environment. Defaults to "base".
    """
    cmd: str = mamba_lockfile_command(env_name=env_name)
    image: Image = Image(tag)
    lockfile: str = image.run(command=cmd, stdout=PIPE)
    assert isinstance(lockfile, str)

    # Split the lockfile into two parts - initial lines and conda package lines.
    lockfile_list: List[str] = lockfile.split("\n")
    conda_package_filter = filter(is_conda_pkg_name, lockfile_list)
    other_lines_filter = filter(
        lambda line: not is_conda_pkg_name(line) and line != "", lockfile_list
    )
    lockfile_conda_packages: List[str] = list(conda_package_filter)
    lockfile_other_lines: List[str] = list(other_lines_filter)

    # Sort the conda packages, then join the parts back together.
    lockfile_conda_packages.sort()
    lockfile_list = lockfile_other_lines + lockfile_conda_packages
    lockfile = "\n".join(lockfile_list) + "\n"

    with open(file, mode="w") as f:
        f.write(lockfile)
