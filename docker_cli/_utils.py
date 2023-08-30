import io
import random
import re
from contextlib import contextmanager
from shlex import split
from string import ascii_lowercase, digits
from subprocess import DEVNULL, CalledProcessError, run
from threading import Lock
from typing import Generator, Optional, Tuple

from ._image import Image
from ._package_manager import (
    PackageManager,
    get_package_manager,
    get_supported_package_managers,
)
from ._url_reader import URLReader, get_supported_url_readers, get_url_reader
from .defaults import universal_tag_prefix


@contextmanager
def temp_image(
    base: str,
    stdout: Optional[io.TextIOBase] = None,
    stderr: Optional[io.TextIOBase] = None,
) -> Generator[Image, None, None]:
    """
    Generates a temporary image while the context manager is active, then deletes it.

    Parameters
    ----------
    base : str
        The tag or ID by which the base image can be found.
    stdout : io.TextIOBase, optional
        A file-like object to redirect stdout to. If None, no redirection will
        occur. Defaults to None.
    stderr : io.TextIOBase, optional
        A file-like object to redirect stderr to. If None, no redirection will
        occur. Defaults to None.

    Yields
    -------
    temp : Image
        The temporary Image.

    Raises
    ------
    ValueError
        If the image is not recognized.
    """
    # This image is generated using "FROM {base}" in a Dockerfile instead of just
    # building from the base image directly, because building from a dockerfile
    # inherently pulls from the internet if the base image isn't already present on
    # the local environment. This ensures that, if the image exists anywhere accessible,
    # it will be found automatically without the need for additional logic.
    tag = f"{universal_tag_prefix()}-temp-{generate_random_string(k=10)}"
    try:
        temp: Image = Image.build(  # type: ignore
            tag=tag,
            dockerfile_string=f"FROM {base}",
            stdout=stdout,
            stderr=stderr,
        )
    except CalledProcessError:
        raise ValueError(f"Image not found: {base}")

    try:
        yield temp
    finally:
        run(split(f"docker rmi {tag}"), stdout=DEVNULL, stderr=DEVNULL)


def image_command_check(
    image: Image,
    configure: bool = False,
) -> Tuple[PackageManager, URLReader, str]:
    """
    Determine what relevant commands are present on an image.

    Determines what package manager and URL reader are on the image, and
    returns a set of initial lines to install a URL reader if none is present.

    Parameters
    ----------
    image: Image
        The image to test.
    configure : bool
        Add configuration commands to the returned string if True. Defaults to False.

    Returns
    -------
    package_manager : PackageManager
        The Package Manager object.
    url_reader : URLReader
        The URL Reader object.
    config_commands : str
        Any install and configuration lines required by the Dockerfile.
    """

    package_mgr = _package_manager_check(image=image)

    if configure:
        init_lines: str = "RUN " + str(package_mgr.generate_configure_command()) + "\n"
    else:
        init_lines = ""

    url_program = _url_reader_check(image=image)
    if url_program is None:
        url_program, url_init = _get_reader_install_lines(package_mgr=package_mgr)
        init_lines += url_init

    if not image.has_command("tar"):
        init_lines += "RUN " + package_mgr.generate_install_command(["tar"])

    return package_mgr, url_program, init_lines


def parse_cuda_info(cuda_version: str) -> Tuple[int, int]:
    """
    Turns a CUDA version string into a major and minor version.

    Parameters
    ----------
    cuda_version : str
        The version string, in "<major>.<minor>" format.

    Returns
    -------
    major_ver : int
        The major version.
    minor_ver : int
        The minor version.

    Raises
    ------
    ValueError
        If the input string does not encode a valid CUDA version number.
    """
    cuda_ver_pattern = re.compile(r"^(?P<major>[0-9]+)\." r"(?P<minor>[0-9]+)$")
    cuda_ver_match = re.match(cuda_ver_pattern, cuda_version)
    if not cuda_ver_match:
        raise ValueError(f"Malformed CUDA version: {cuda_version}")
    cuda_ver_match_groups = cuda_ver_match.groupdict()

    cuda_major: int = int(cuda_ver_match_groups["major"])
    cuda_minor: int = int(cuda_ver_match_groups["minor"])

    return (cuda_major, cuda_minor)


def is_conda_pkg_name(line: str) -> bool:
    """
    Returns True if a line appears to be an Anaconda package URL.

    Used for filtering lockfiles.

    Parameters
    ----------
    line : str
        The line.

    Returns
    -------
    bool
        True if the line appears to be an Anaconda package URL, false otherwise.
    """
    conda_pkg_pattern = re.compile(r"^https:\/\/conda.anaconda.org\/\S*$")
    return re.match(conda_pkg_pattern, line) is not None


def test_image(image: Image, expression: str) -> bool:
    """
    Runs a test expression on an image.

    Parameters
    ----------
    image : Image
        The image.
    expression : str
        The expression.

    Returns
    -------
    bool
        True if "test" returned with status 0, False otherwise.
    """
    try:
        image.run(f"test -d {expression}")
        return True
    except CalledProcessError as err:
        if err.returncode == 1:
            return False
        else:
            raise


def _package_manager_check(image: Image) -> PackageManager:
    """
    Returns the package manager present on an image.

    Parameters
    ----------
    base : Image
        The image.

    Returns
    -------
    PackageManager
        The package manager.
    """
    for name in get_supported_package_managers():
        if image.has_command(name):
            return get_package_manager(name)
    raise ValueError("No recognized package manager found on parent image.")


def _url_reader_check(image: Image) -> Optional[URLReader]:
    """
    Return the URL reader on a given image, or None if there is none present.

    Parameters
    ----------
    base : Image
        The image.
    package_mgr : PackageManager
        The images package manager.

    Returns
    -------
    url_reader : URLReader
        The installed URL reader, if one exists.
    """
    for name in get_supported_url_readers():
        if image.has_command(name):
            return get_url_reader(name)
    return None


def _get_reader_install_lines(package_mgr: PackageManager) -> Tuple[URLReader, str]:
    """
    Return a URL Reader and a string to install it.

    Parameters
    ----------
    base : Image
        The image.
    package_mgr : PackageManager
        The images package manager.

    Returns
    -------
    url_reader : URLReader
        The URL reader
    install_command : str
        a string to install the URL reader.
    """
    init_lines = (
        "RUN "
        + str(
            package_mgr.generate_install_command(
                targets=["wget"],
            )
        )
        + "\n"
    )
    url_program = get_url_reader("wget")

    return url_program, init_lines


def generate_random_string(k: int = 10) -> str:
    """
    Generates random, threadsafe strings of lowercase letters and digits.

    Parameters
    ----------
    k : int, optional
        The length of the string to be generated. Defaults to 10.

    Returns
    -------
    str
        The random string.
    """

    # `lock` is initialized just once (when the Python module is first loaded).
    # Every invocation of the function will use the same lock instance.
    def helper(lock: Lock = Lock()) -> str:
        with lock:
            return "".join(random.choices(ascii_lowercase + digits, k=k))

    return helper()
