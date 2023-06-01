from pathlib import Path
from typing import Iterator, Tuple

from pytest import fixture, mark

from wigwam import Image
from wigwam._docker_mamba import mamba_add_reqs_dockerfile, mamba_install_dockerfile

from .utils import (
    determine_scope,
    generate_tag,
    remove_docker_image,
    rough_dockerfile_validity_check,
)


@fixture(scope=determine_scope)
def mamba_runtime_dockerfile() -> Tuple[str, str]:
    """
    Returns a runtime Dockerfile for mamba.

    Returns
    -------
    header : str
        The Dockerfile header.
    body : str
        The Dockerfile body.
    """
    return mamba_install_dockerfile(env_reqs_file=Path("test-runtime-lock-file.txt"))


@fixture(scope=determine_scope)
def mamba_runtime_tag() -> Iterator[str]:
    """
    Returns a mamba runtime image tag.

    Returns
    -------
    str
        The tag.
    """
    yield generate_tag("mamba-runtime")


@fixture(scope=determine_scope)
def mamba_runtime_image(
    mamba_runtime_dockerfile: Tuple[str, str],
    init_tag: str,
    mamba_runtime_tag: str,
    init_image: Image,  # type: ignore
) -> Iterator[Image]:
    """
    Yields a Mamba runtime image.

    Parameters
    ----------
    mamba_runtime_dockerfile : str
        The mamba runtime Dockerfile.
    init_tag : str
        The initialization image tag.
    mamba_runtime_tag : str
        The mamba runtime tag.
    init_image : Image
        Unused; ensures the initialization image has been built.

    Yields
    ------
    Iterator[Image]
        The mamba runtime image generator.
    """
    header, body = mamba_runtime_dockerfile

    dockerfile = f"{header}\n\nFROM {init_tag}\n\n{body}"
    img = Image.build(tag=mamba_runtime_tag, dockerfile_string=dockerfile)
    yield img
    remove_docker_image(mamba_runtime_tag)


@fixture(scope=determine_scope)
def mamba_dev_dockerfile() -> str:
    """
    Returns a mamba dev Dockerfile.

    Returns
    -------
    str
        The Dockerfile body.
    """
    return mamba_add_reqs_dockerfile(env_reqs_file=Path("test-dev-lock-file.txt"))


@fixture(scope=determine_scope)
def mamba_dev_tag() -> Iterator[str]:
    """
    Returns an image tag for the mamba dev image.

    Returns
    -------
    str
        The tag.
    """
    yield generate_tag("mamba-dev")


@fixture(scope=determine_scope)
def mamba_dev_image(
    mamba_dev_dockerfile: str,
    mamba_runtime_tag: str,
    mamba_dev_tag: str,
    mamba_runtime_image: Image,  # type: ignore
) -> Iterator[Image]:
    """
    Returns a mamba dev image.

    Parameters
    ----------
    mamba_dev_dockerfile : str
        The Dockerfile body for the image.
    mamba_runtime_tag : str
        The runtime image tag.
    mamba_dev_tag : str
        The dev image tag.
    mamba_runtime_image : Image
        Unused. Ensures the runtime image has been built.

    Yields
    ------
    Iterator[Image]
        The mamba dev image generator.
    """
    dockerfile = f"FROM {mamba_runtime_tag}\n\n{mamba_dev_dockerfile}"
    img = Image.build(tag=mamba_dev_tag, dockerfile_string=dockerfile)
    yield img
    remove_docker_image(mamba_dev_tag)


@mark.mamba
class TestMambaGenerators:
    """Test the mamba environment Dockerfile generators"""

    @mark.dockerfiles
    def test_mamba_install_dockerfile(self, mamba_runtime_dockerfile: Tuple[str, str]):
        """Tests the mamba_install_dockerfile function."""
        header, body = mamba_runtime_dockerfile
        dockerfile_string = f"{header}\n\nFROM %TEST_IMAGE%\n\n{body}"

        rough_dockerfile_validity_check(dockerfile_string)

    @mark.dockerfiles
    def test_mamba_add_specs_dockerfile(self, mamba_dev_dockerfile: str):
        """Tests the mamba_install_dockerfile function."""
        dockerfile_string = f"FROM %TEST_IMAGE%\n\n{mamba_dev_dockerfile}"

        rough_dockerfile_validity_check(dockerfile_string)

    @mark.images
    class TestMambaImages:
        def test_mamba_runtime_build(self, mamba_runtime_image: Image):
            """Tests that the runtime build correctly functions."""
            mamba_runtime_image.run("python")

        def test_mamba_dev_build(self, mamba_dev_image: Image):
            """Tests that the runtime build correctly functions."""
            mamba_dev_image.run('python -c "import scipy"')
