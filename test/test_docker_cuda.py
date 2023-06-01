from typing import Iterator, Tuple

from pytest import fixture, mark

from wigwam import Image
from wigwam._docker_cuda import (
    AptGetCUDADockerfileGen,
    CUDADockerfileGenerator,
    YumCUDADockerfileGen,
    get_cuda_dockerfile_generator,
)
from wigwam._package_manager import AptGet, PackageManager, Yum
from wigwam._url_reader import Curl, URLReader, Wget

from .utils import (
    determine_scope,
    generate_tag,
    remove_docker_image,
    rough_dockerfile_validity_check,
)


@mark.cuda
def test_get_cuda_dockerfile_generator():
    """Tests that the get_cuda_dockerfile_generator returns the right generator."""
    gen: CUDADockerfileGenerator = get_cuda_dockerfile_generator(AptGet(), Curl())
    assert isinstance(gen, AptGetCUDADockerfileGen)
    assert isinstance(gen.url_reader, Curl)

    gen = get_cuda_dockerfile_generator(Yum(), Wget())
    assert isinstance(gen, YumCUDADockerfileGen)
    assert isinstance(gen.url_reader, Wget)


@fixture(scope=determine_scope)
def cuda_repo_ver(base_tag: str) -> str:
    """The basic information about the CUDA Dockerfile or image to be generated."""
    if base_tag == "ubuntu":
        return "ubuntu2004"
    if base_tag == "oraclelinux:8.4":
        return "rhel8"
    else:
        raise ValueError(f"Unknown base tag: {base_tag}")


@fixture(scope=determine_scope)
def cuda_version() -> Tuple[int, int]:
    """Returns two integers that represent CUDA major and minor versions.

    Returns
    -------
    cuda_ver_major : int
        The CUDA major version.
    cuda_ver_minor : int
        The CUDA minor version.
    """
    return (11, 4)


@fixture(scope=determine_scope)
def cuda_generator(
    base_properties: Tuple[PackageManager, URLReader]
) -> CUDADockerfileGenerator:
    """
    Returns the CUDADockerfileGenerator needed for this CUDA test.

    Parameters
    ----------
    base_properties : Tuple[PackageManager, URLReader]
        The package manager and URL reader.

    Returns
    -------
    CUDADockerfileGenerator
        The Dockerfile generator.
    """
    package_mgr, url_reader = base_properties
    gen = get_cuda_dockerfile_generator(pkg_mgr=package_mgr, url_reader=url_reader)
    return gen


@fixture(scope=determine_scope)
def cuda_runtime_dockerfile(
    cuda_generator: CUDADockerfileGenerator,
    cuda_repo_ver: str,
    cuda_version: Tuple[int, int],
) -> str:
    """
    Returns a runtime Dockerfile for CUDA.

    Returns
    -------
    str
        The Dockerfile body.
    """
    cuda_ver_major, cuda_ver_minor = cuda_version
    dockerfile: str = cuda_generator.generate_runtime_dockerfile(
        cuda_ver_major=cuda_ver_major,
        cuda_ver_minor=cuda_ver_minor,
        repo_ver=cuda_repo_ver,
    )
    return dockerfile


@fixture(scope=determine_scope)
def cuda_runtime_tag() -> Iterator[str]:
    """
    Returns a CUDA runtime image tag.

    Returns
    -------
    str
        The tag.
    """
    yield generate_tag("cuda-runtime")


@fixture(scope=determine_scope)
def cuda_runtime_image(
    cuda_runtime_dockerfile: str,
    init_tag: str,
    cuda_runtime_tag: str,
    init_image: Image,  # type: ignore
) -> Iterator[Image]:
    """
    Yields a CUDA runtime image.

    Parameters
    ----------
    cuda_runtime_dockerfile : str
        The CUDA runtime Dockerfile.
    init_tag : str
        The initialization image tag.
    cuda_runtime_tag : str
        The CUDA runtime tag.
    init_image : Image
        Unused; ensures the initialization image has been built.

    Yields
    ------
    Iterator[Image]
        The CUDA runtime image generator.
    """
    dockerfile = f"FROM {init_tag}\n\n{cuda_runtime_dockerfile}"
    img = Image.build(tag=cuda_runtime_tag, dockerfile_string=dockerfile)
    yield img
    remove_docker_image(cuda_runtime_tag)


@fixture(scope=determine_scope)
def cuda_dev_dockerfile(
    cuda_generator: CUDADockerfileGenerator,
    cuda_version: Tuple[int, int],
) -> str:
    """
    Returns a CUDA dev Dockerfile.

    Returns
    -------
    str
        The Dockerfile body.
    """
    cuda_ver_major, cuda_ver_minor = cuda_version
    dockerfile = cuda_generator.generate_dev_dockerfile(cuda_ver_major, cuda_ver_minor)
    return dockerfile


@fixture(scope=determine_scope)
def cuda_dev_tag() -> Iterator[str]:
    """
    Returns an image tag for the CUDA dev image.

    Returns
    -------
    str
        The tag.
    """
    yield generate_tag("cuda-dev")


@fixture(scope=determine_scope)
def cuda_dev_image(
    cuda_dev_dockerfile: str,
    cuda_runtime_tag: str,
    cuda_dev_tag: str,
    cuda_runtime_image: Image,  # type: ignore
) -> Iterator[Image]:
    """
    Returns a CUDA dev image.

    Parameters
    ----------
    cuda_dev_dockerfile : str
        The Dockerfile for the image.
    cuda_runtime_tag : str
        The runtime image tag.
    cuda_dev_tag : str
        The dev image tag.
    cuda_runtime_image : Image
        Unused. Ensures the runtime image has been built.

    Yields
    ------
    Iterator[Image]
        The CUDA dev image generator.
    """
    dockerfile: str = f"FROM {cuda_runtime_tag}\n\n{cuda_dev_dockerfile}"
    img = Image.build(tag=cuda_dev_tag, dockerfile_string=dockerfile)
    yield img
    remove_docker_image(cuda_dev_tag)


@mark.cuda
class TestCudaGen:
    """Tests the CUDADockerfileGenerator classes."""

    def test_init(
        self,
        cuda_generator: CUDADockerfileGenerator,
        base_properties: Tuple[PackageManager, URLReader],
    ):
        """Tests the constructor."""
        pkg_mgr, url_reader = base_properties
        assert isinstance(cuda_generator.package_manager, type(pkg_mgr))
        assert cuda_generator.url_reader == url_reader

    def test_generate_install_lines(
        self,
        cuda_generator: CUDADockerfileGenerator,
        base_properties: Tuple[PackageManager, URLReader],
    ):
        """Tests the generation of CUDA install lines."""
        pkg_mgr, _ = base_properties
        dummy_installs = ["a", "b", "c", "d", "e"]
        install_return = cuda_generator.generate_install_lines(
            build_targets=dummy_installs
        )
        apt_get_install = pkg_mgr.generate_install_command(
            targets=dummy_installs,
        )
        assert apt_get_install in install_return
        rough_dockerfile_validity_check(install_return)

    @mark.dockerfiles
    def test_generate_runtime_dockerfile(
        self, cuda_generator: CUDADockerfileGenerator, cuda_repo_ver: str
    ):
        """Tests the generation of a runtime CUDA Dockerfile."""
        dockerfile: str = cuda_generator.generate_runtime_dockerfile(
            cuda_ver_major=11, cuda_ver_minor=4, repo_ver=cuda_repo_ver
        )
        assert isinstance(dockerfile, str)

        dockerfile = f"FROM %DUMMY_BASE%\n\n{dockerfile}"

        rough_dockerfile_validity_check(dockerfile)

    @mark.dockerfiles
    def test_generate_dev_dockerfile(
        self,
        cuda_generator: CUDADockerfileGenerator,
        cuda_version: Tuple[int, int],
    ):
        """Tests the generation of a dev CUDA Dockerfile."""
        cuda_ver_major, cuda_ver_minor = cuda_version
        dockerfile: str = cuda_generator.generate_dev_dockerfile(
            cuda_ver_major,
            cuda_ver_minor,
        )
        assert isinstance(dockerfile, str)

        dockerfile = f"FROM %DUMMY_BASE%\n\n{dockerfile}"

        rough_dockerfile_validity_check(dockerfile)

    @mark.images
    class TestCUDAImages:
        def test_cuda_runtime_build(self, cuda_runtime_image: Image):
            """Tests that the runtime build correctly functions."""
            cuda_runtime_image.run("nvidia-smi")

        def test_cuda_dev_build(self, cuda_dev_image: Image):
            """Tests that the runtime build correctly functions."""
            cuda_dev_image.run("nvidia-smi")
