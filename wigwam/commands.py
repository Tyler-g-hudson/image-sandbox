from __future__ import annotations

import os
import shlex
from collections.abc import Iterable
from pathlib import Path
from shlex import split
from subprocess import DEVNULL, PIPE, run

from ._bind_mount import BindMount
from ._docker_cmake import (
    cmake_build_dockerfile,
    cmake_config_dockerfile,
    cmake_install_dockerfile,
)
from ._docker_distrib import distrib_dockerfile
from ._docker_git import git_extract_dockerfile
from ._docker_insert import insert_dir_dockerfile
from ._docker_mamba import mamba_lockfile_command
from ._image import Image
from ._url_reader import URLReader
from ._utils import (
    get_libdir,
    image_command_check,
    is_conda_pkg_name,
    prefix_image_tag,
    temp_image,
)
from .defaults import build_prefix, install_prefix


def get_archive(
    tag: str,
    base: str,
    archive_url: str,
    dst_path: str | os.PathLike[str],
    url_reader: URLReader | None = None,
    no_cache: bool = False,
):
    """
    Builds a docker image containing the requested Git archive.

    .. note:
        With this image, the workdir is moved to `directory`.

    Parameters
    ----------
    tag : str
        The image tag.
    base : str
        The base image tag.
    archive_url : str
        The URL of the Git archive to add to the image. Must be a `tar.gz` file.
    dst_path : path-like
        The prefix of the directory that the archive will be copied to on the image.
    url_reader : URLReader | None, optional
        If given, will use the given URL reader to acquire the Git archive. If None,
        will check the base image and use whichever one it can find. Defaults to None.
    no_cache : bool, optional
        Run Docker build with no cache if True. Defaults to False.

    Returns
    -------
    Image
        The generated image.
    """
    img_tag = prefix_image_tag(tag)
    base_tag = prefix_image_tag(base)

    if url_reader is None:
        with temp_image(base_tag) as temp_img:
            _, url_reader, _ = image_command_check(temp_img)

    dockerfile = git_extract_dockerfile(
        base=base_tag,
        dst_path=dst_path,
        archive_url=archive_url,
        url_reader=url_reader,
    )

    return Image.build(tag=img_tag, dockerfile_string=dockerfile, no_cache=no_cache)


def copy_dir(
    tag: str,
    base: str,
    src_path: str | os.PathLike[str],
    dst_path: str | os.PathLike[str] | None = None,
    no_cache: bool = False,
):
    """
    Builds a Docker image with the contents of the given directory copied onto it.

    The directory path on the image has the same name as the topmost directory
    of the given path. e.g. giving path "/tmp/dir/subdir" will result in the contents of
    this path being saved in "/subdir" on the generated image.

    This Dockerfile also changes the working directory of the image to the copied
    directory.

    Parameters
    ----------
    tag : str
        The image tag.
    base : str
        The base image tag.
    src_path : path-like
        The prefix of the directory on the host machine to be copied.
    dst_path : path-like or None
        The prefix of the directory to copy to on the image, or None. If given, the
        contents of the source directory will be copied to the given path. If None, the
        target path will default to the base name of the path given by the `directory`
        argument. Defaults to None.
    no_cache : bool, optional
        Run Docker build with no cache if True. Defaults to False.

    Returns
    -------
    Image
        The generated image.
    """

    img_tag = prefix_image_tag(tag)

    dir_str = os.fspath(src_path)

    # The absolute path of the given directory will be the build context.
    # This is necessary because otherwise docker may be unable to find the directory if
    # the build context is at the current working directory.
    path_absolute = os.path.abspath(dir_str)

    if dst_path is None:
        # No argument was passed to target_path, so the lowest-level directory of the
        # input path will be the name of the directory in the image.
        if os.path.isdir(dir_str):
            target_dir = os.path.basename(path_absolute)
        else:
            raise ValueError(f"{dir_str} is not a valid directory on this machine.")
    else:
        target_dir = os.fspath(dst_path)

    # Generate the dockerfile. The source directory will be "." since the build context
    # will be at the source path when the image is built.
    base_tag = prefix_image_tag(base)
    dockerfile: str = insert_dir_dockerfile(
        base=base_tag,
        target_dir=target_dir,
        source_dir=".",
    )

    # Build the image with the context at the absolute path of the given path. This
    # allows a directory to be copied from anywhere that is visible to this user on
    # the machine, whereas a context at "." would be unable to see any directory that is
    # not downstream of the working directory from which the program is called.
    return Image.build(
        tag=img_tag,
        context=path_absolute,
        dockerfile_string=dockerfile,
        no_cache=no_cache,
    )


def configure_cmake(
    tag: str,
    base: str,
    build_type: str,
    no_cuda: bool = False,
    no_cache: bool = False,
) -> Image:
    """
    Produces an image with CMake configured.

    Parameters
    ----------
    tag : str
        The image tag.
    base : str
        The base image tag.
    build_type : str
        The CMake build type. See
        `here <https://cmake.org/cmake/help/latest/variable/CMAKE_BUILD_TYPE.html>`_
        for possible values.
    no_cuda : bool, optional
        If True, build without CUDA. Defaults to False.
    no_cache : bool, optional
        Run Docker build with no cache if True. Defaults to False.

    Returns
    -------
    Image
        The generated image.
    """
    base_tag = prefix_image_tag(base)

    dockerfile: str = cmake_config_dockerfile(
        base=base_tag,
        build_type=build_type,
        with_cuda=not no_cuda,
    )

    img_tag = prefix_image_tag(tag)
    return Image.build(tag=img_tag, dockerfile_string=dockerfile, no_cache=no_cache)


def compile_cmake(tag: str, base: str, no_cache: bool = False) -> Image:
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

    prefixed_tag: str = prefix_image_tag(tag)
    prefixed_base_tag: str = prefix_image_tag(base)

    dockerfile: str = cmake_build_dockerfile(base=prefixed_base_tag)

    return Image.build(
        tag=prefixed_tag,
        dockerfile_string=dockerfile,
        no_cache=no_cache,
    )


def cmake_install(tag: str, base: str, no_cache: bool = False) -> Image:
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
    prefixed_tag: str = prefix_image_tag(tag)
    prefixed_base_tag: str = prefix_image_tag(base)

    dockerfile: str = cmake_install_dockerfile(base=prefixed_base_tag)
    return Image.build(
        tag=prefixed_tag, dockerfile_string=dockerfile, no_cache=no_cache
    )


def make_distrib(tag: str, base: str, source_tag: str, no_cache: bool = False) -> Image:
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
    no_cache : bool, optional
        Run Docker build with no cache if True. Defaults to False.

    Returns
    -------
    Image
        The generated image.
    """

    prefixed_base_tag: str = prefix_image_tag(base)
    prefixed_source_tag: str = prefix_image_tag(source_tag)

    # Unlike with the CMake Install function, `libdir` can be checked directly on this
    # image because it has something at $INSTALL_PREFIX. Check the base tag for lib64 or
    # lib.
    libdir: str = get_libdir(prefixed_base_tag)

    dockerfile = distrib_dockerfile(
        base=prefixed_base_tag,
        source_tag=prefixed_source_tag,
        source_path=install_prefix(),
        distrib_path=install_prefix(),
        libdir=libdir,
    )

    return Image.build(tag=tag, dockerfile_string=dockerfile, no_cache=no_cache)


def build_all(
    tag: str,
    base: str,
    src_path: str | os.PathLike | None,
    archive_url: str | None,
    dst_path: str | os.PathLike,
    build_type: str,
    no_cuda: bool,
    no_cache: bool = False,
) -> dict[str, Image]:
    """
    Fully compiles and installs a CMake project.

    Parameters
    ----------
    tag : str
        The image tag prefix.
    base : str
        The base image tag.
    src_path : path-like or None
        The path to the source prefix on the host to copy to an image.
    archive_url : str or None
        The URL of the Git archive to install on an image. No archive will be installed
        if `copy_dir` is given.
    dst_path : str
        The path to place the contents of the Git archive or copied directory to.
    build_type : str
        The CMake build type. See
        `here <https://cmake.org/cmake/help/latest/variable/CMAKE_BUILD_TYPE.html>`_
        for possible values.
    no_cuda : bool
        If True, build without CUDA.
    no_cache : bool, optional
        Run Docker build with no cache if True. Defaults to False.

    Returns
    -------
    dict[str, Image]
        A dict of images produced by this process.
    """

    prefixed_tag: str = prefix_image_tag(tag)
    prefixed_base_tag: str = prefix_image_tag(base)

    images: dict[str, Image] = {}

    initial_tag: str = ""
    if src_path is not None:
        src_path = os.fspath(src_path)
        path_absolute = os.path.abspath(src_path)
        if os.path.isdir(src_path):
            top_dir = os.path.basename(path_absolute)
        else:
            raise ValueError(f"src_path must be a directory. Given value: {src_path}")

        insert_tag = f"{prefixed_tag}-file-{top_dir}"
        insert_image = copy_dir(
            base=prefixed_base_tag,
            tag=insert_tag,
            src_path=src_path,
            dst_path=dst_path,
            no_cache=no_cache,
        )
        images[insert_tag] = insert_image
        initial_tag = insert_tag
    else:
        git_repo_tag = f"{prefixed_tag}-git-repo"
        if archive_url is None:
            raise ValueError("Either archive_url or src_path must be passed.")

        git_repo_image = get_archive(
            base=prefixed_base_tag,
            tag=git_repo_tag,
            archive_url=archive_url,
            dst_path=dst_path,
            no_cache=no_cache,
        )
        images[git_repo_tag] = git_repo_image
        initial_tag = git_repo_tag

    configure_tag = f"{prefixed_tag}-configured"
    configure_image = configure_cmake(
        tag=configure_tag,
        base=initial_tag,
        build_type=build_type,
        no_cuda=no_cuda,
        no_cache=no_cache,
    )
    images[configure_tag] = configure_image

    build_tag = f"{prefixed_tag}-built"
    build_image = compile_cmake(
        tag=build_tag,
        base=configure_tag,
        no_cache=no_cache,
    )
    images[build_tag] = build_image

    install_tag = f"{prefixed_tag}-installed"
    install_image = cmake_install(
        tag=install_tag,
        base=build_tag,
        no_cache=no_cache,
    )
    images[install_tag] = install_image

    return images


def test(
    tag: str,
    output_xml: os.PathLike[str] | str,
    compress_output: bool,
    quiet_fail: bool,
) -> None:
    """
    Run all ctests from the Docker image work directory.

    Parameters
    ----------
    tag : str
        The tag of the image to test.
    output_xml : os.PathLike[str] | str
        The name of the XML test output file.
    compress_output : bool
        If True, compress the output of the test.
    quiet_fail : bool
        If True, don't generate verbose output on failure.
    """

    prefixed_tag: str = prefix_image_tag(tag)

    xml_filename = Path(output_xml).name

    image_volume_path = "/scratch/Testing"
    image = Image(prefixed_tag)

    move_cmd = ["cd", os.fspath(build_prefix())]
    test_cmd = ["(", "ctest"]

    # Add arguments
    if not compress_output:
        test_cmd += ["--no-compress-output"]
    if not quiet_fail:
        test_cmd += ["--output-on-failure"]

    # Note: as an alternative to copying the Test.xml file
    # from the default location to the specified output directory,
    # we could instead use `ctest --output-junit <file>`, although
    # this requires CMake>=3.21
    test_cmd += ["-T", "Test", "||", "true", ")"]
    file_cmd = [
        "cp",
        f"{build_prefix()}/Testing/*/Test.xml",
        f"{image_volume_path}/{xml_filename}",
    ]

    cmd = move_cmd + ["&&"] + test_cmd + ["&&"] + file_cmd

    command = shlex.join(cmd)

    host_volume_path = Path(output_xml).parent.resolve()
    host_volume_path.mkdir(parents=True, exist_ok=True)

    bind_mount = BindMount(
        src=host_volume_path,
        dst=image_volume_path,
        permissions="rw",
    )
    image.run(command=command, host_user=True, bind_mounts=[bind_mount])


def dropin(tag: str, default_user: bool = False, use_prefix: bool = True) -> None:
    """
    Initiates a drop-in session on an image.

    Parameters
    ----------
    tag : str
        The tag or ID of the image.
    default_user: bool, optional
        If True, run as the default user in the image. Else, run as the current user on
        the host machine. Defaults to False.
    """
    if use_prefix:
        tag = prefix_image_tag(tag)
    image: Image = Image(tag)

    image.drop_in(host_user=not default_user)


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
        if not ignore_prefix:
            tag = prefix_image_tag(tag)
        if verbose:
            print(f"Attempting removal for tag: {tag}")

        # Search for all images whose name matches this tag, acquire a list
        search_command = split(f'docker images --filter=reference="{tag}" -q')
        search_result = run(search_command, text=True, stdout=PIPE, stderr=output)
        # An empty return indicates that no such images were found. Skip to the next.
        if search_result.stdout == "":
            if verbose:
                print(f"No images found matching pattern {tag}. Proceeding.")
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
        The tag of the image.
    file : os.PathLike[str] | str
        The file to be output to.
    env_name: str
        The name of the environment. Defaults to "base".
    """
    cmd: str = mamba_lockfile_command(env_name=env_name)
    tag = prefix_image_tag(tag)
    image: Image = Image(tag)
    lockfile: str = image.run(command=cmd, stdout=PIPE)
    assert isinstance(lockfile, str)

    # Split the lockfile into two parts - initial lines and conda package lines.
    lockfile_list: list[str] = lockfile.split("\n")
    conda_package_filter = filter(is_conda_pkg_name, lockfile_list)
    other_lines_filter = filter(
        lambda line: not is_conda_pkg_name(line) and line != "", lockfile_list
    )
    lockfile_conda_packages: list[str] = list(conda_package_filter)
    lockfile_other_lines: list[str] = list(other_lines_filter)

    # Sort the conda packages, then join the parts back together.
    lockfile_conda_packages.sort()
    lockfile_list = lockfile_other_lines + lockfile_conda_packages
    lockfile = "\n".join(lockfile_list) + "\n"

    with open(file, mode="w") as f:
        f.write(lockfile)
