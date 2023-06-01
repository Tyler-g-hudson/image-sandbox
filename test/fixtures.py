"""This file contains all fixtures that are needed by multiple test files."""
from shlex import split
from subprocess import run
from textwrap import dedent
from typing import Iterator, Tuple

from pytest import fixture

from wigwam import Image, PackageManager, URLReader
from wigwam._utils import image_command_check, temp_image
from wigwam.setup_commands import setup_init

from .utils import determine_scope, generate_tag, remove_docker_image


@fixture(scope=determine_scope)
def image_tag():
    """
    Returns an image tag with a random suffix.

    Returns
    ------
    str
        An image tag
    """
    tag = generate_tag("temp")
    yield tag


@fixture(scope=determine_scope)
def image_id(image_tag):
    """
    Builds an image for testing and returns its ID.

    Yields
    ------
    str
        An image ID.
    """
    dockerfile = dedent(
        f"""
        FROM ubuntu

        RUN mkdir {image_tag}
    """
    ).strip()
    run(split(f"docker build . -t {image_tag} -f-"), text=True, input=dockerfile)
    inspect_process = run(
        split("docker inspect -f='{{.Id}}' " + image_tag),
        capture_output=True,
        text=True,
        check=True,
    )
    id = inspect_process.stdout.strip()
    yield id
    remove_docker_image(image_tag)


@fixture(scope=determine_scope, params=["ubuntu", "oraclelinux:8.4"])
def base_tag(request) -> str:
    """The tag of the base image."""
    return request.param


@fixture(scope=determine_scope)
def init_tag() -> str:
    """
    Returns an initialization image tag.

    Returns
    -------
    str
        The initialization image tag.
    """
    return generate_tag("base")


@fixture(scope=determine_scope)
def init_image(base_tag: str, init_tag: str) -> Iterator[Image]:
    """
    Yields an initialization image, then later deletes it.

    Parameters
    ----------
    init_tag : str
        The initialization image tag.
    init_base_tag : str
        The base image tag.

    Yields
    ------
    Iterator[Image]
        The initialization tag generator.
    """
    img, _, _ = setup_init(base=base_tag, tag=init_tag, no_cache=False)
    yield img
    remove_docker_image(init_tag)


@fixture(scope=determine_scope)
def base_properties(base_tag: str) -> Tuple[PackageManager, URLReader]:
    """
    Returns the package manager and URL reader needed for this CUDA test.

    Parameters
    ----------
    base_tag : str
        The base tag.

    Returns
    -------
    package_manager : PackageManager
        The package manager.
    url_reader : URLReader
        The URL reader.
    """
    with temp_image(base_tag) as temp_img:
        package_mgr, url_reader, _ = image_command_check(temp_img)
    return (package_mgr, url_reader)
