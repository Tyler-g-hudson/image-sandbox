from __future__ import annotations

import textwrap
from abc import ABC, abstractmethod
from typing import Iterable, List

from ._package_manager import PackageManager, get_package_manager
from ._url_reader import URLReader, get_url_reader


class CUDADockerfileGenerator(ABC):
    """
    An abstract base class for CUDA Dockerfile generators.

    CUDA Dockerfile generators receive a CUDA version and base image, and can
    produce a Dockerfile that contains instructions for building CUDA on the
    given system.
    """

    def __init__(self, url_reader: URLReader):
        self.url_reader = url_reader

    def generate_runtime_dockerfile(
        self,
        cuda_ver_major: int,
        cuda_ver_minor: int,
        repo_ver: str,
        *,
        arch: str = "x86_64",
        nvidia_visible_devices: str = "all",
        nvidia_driver_capabilities: str = "compute,utility",
    ) -> str:
        """
        Generates a Dockerfile for the CUDA runtime image.

        Note that the `repo_ver` and `arch` arguments are intended to be those needed
        for finding the online repository to fetch at:
        `https://developer.download.nvidia.com/compute/cuda/repos/{repo_ver}/{arch}/`

        Parameters
        ----------
        cuda_ver_major : int
            The major CUDA version.
        cuda_ver_minor : int
            The minor CUDA version.
        repo_ver : str
            The name of the CUDA repository as hosted by the CUDA developers.
        arch : str
            The name of the architecture as hosted by the CUDA developers under the
            repository.
        nvidia_visible_devices : str, optional
            The value to set the NVIDIA_VISIBLE_DEVICES environment variable
            to. Defaults to "all". See
            https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/user-guide.html#gpu-enumeration
            for more info.
        nvidia_driver_capabilities : str, optional
            The value to set the NVIDIA_DRIVER_CAPABILITIES environment
            variable to. Defaults to "compute,utility". See
            https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/user-guide.html#driver-capabilities
            for more info.

        Returns
        -------
        str
            The generated Dockerfile body.

        Raises
        ------
        ValueError
            If the major CUDA version is below 11, the minimum supported
            version.
        """

        if cuda_ver_major < 11:
            raise ValueError(  # pragma: no cover
                "CUDA version below 11 requested. Only CUDA versions >= 11 "
                "are supported."
            )
        init_lines = self._generate_initial_lines(repo_ver, arch=arch)
        install_lines = self.generate_install_lines(
            build_targets=self._runtime_build_targets(
                cuda_ver_major=cuda_ver_major,
                cuda_ver_minor=cuda_ver_minor,
            )
        )

        version_name = f'"{cuda_ver_major}.{cuda_ver_minor}"'
        nvidia_req_cuda: str = f"cuda>={version_name}"

        retval = (
            "USER root\n\n"
            + init_lines
            + "\n\n"
            + textwrap.dedent(
                f"""
            ENV NVIDIA_VISIBLE_DEVICES {nvidia_visible_devices}
            ENV NVIDIA_DRIVER_CAPABILITIES {nvidia_driver_capabilities}
            ENV CUDA_VERSION {version_name}
            ENV NVIDIA_REQUIRE_CUDA {nvidia_req_cuda}
        """
            ).strip()
            + "\n\n"
            + install_lines
            + "USER $DEFAULT_USER"
        )

        return retval

    def generate_dev_dockerfile(self, cuda_ver_major: int, cuda_ver_minor: int) -> str:
        """
        Generates a Dockerfile for the CUDA dev image.

        Parameters
        ----------
        cuda_ver_major : int
            The major CUDA version.
        cuda_ver_minor : int
            The minor CUDA version.

        Returns
        -------
        str
            The generated Dockerfile body.
        """
        install_lines = self.generate_install_lines(
            build_targets=self._dev_build_targets(
                cuda_ver_major=cuda_ver_major,
                cuda_ver_minor=cuda_ver_minor,
            )
        )

        return textwrap.dedent(
            f"""
            USER root

            {install_lines}

            ENV CUDAHOSTCXX=x86_64-conda-linux-gnu-c++
            ENV CUDACXX=/usr/local/cuda-{cuda_ver_major}.{cuda_ver_minor}/bin/nvcc

            USER $DEFAULT_USER
        """
        ).strip()

    @abstractmethod
    def _generate_initial_lines(self, repo_ver: str, *, arch: str = "x86_64") -> str:
        """
        Generates the first lines of the CUDA install Dockerfile.

        These lines typically acquire the necessary CUDA repo and configure the
        image to install CUDA.

        Note that the `repo_ver` and `arch` arguments are intended to be those needed
        for finding the online repository to fetch at:
        `https://developer.download.nvidia.com/compute/cuda/repos/{repo_ver}/{arch}/`

        Parameters
        ----------
        repo_ver : str
            The name of the CUDA repository as hosted by the CUDA developers.
        arch : str
            The name of the architecture as hosted by the CUDA developers under the
            repository.

        Returns
        -------
        str
            The initial lines of the CUDA install Dockerfile.
        """
        ...

    @abstractmethod
    def generate_install_lines(self, build_targets: Iterable[str]) -> str:
        """
        Generates the install lines for the CUDA install Dockerfile.

        These lines typically use the package manager to install the given CUDA
        libraries and then clean the package manager cache.

        Parameters
        ----------
        build_targets : Iterable[str]
            The CUDA package targets to be installed.

        Returns
        -------
        str
            The install lines of the CUDA install Dockerfile.
        """
        ...

    @property
    def package_manager(self) -> PackageManager:
        """
        The package manager used by this Dockerfile generator.

        This ensures that all subclasses of this class will have a package manager
        property, but doesn't require the abstract base class to specify it.

        Raises
        ------
        AttributeError
            If no package manager is present on the object.
        """
        if not hasattr(self, "_package_manager"):
            raise AttributeError(  # pragma: no cover
                "Attribute 'package_manager' not found."
            )
        return getattr(self, "_package_manager")

    @abstractmethod
    def _runtime_build_targets(
        self, cuda_ver_major: int, cuda_ver_minor: int
    ) -> List[str]:
        """
        The set of targets to build onto the runtime image.

        Parameters
        ----------
        cuda_ver_major : int
            The major CUDA version.
        cuda_ver_minor : int
            The minor CUDA version.

        Returns
        -------
        List[str]
            A list of packages to install for the CUDA runtime build.
        """
        ...

    @abstractmethod
    def _dev_build_targets(self, cuda_ver_major: int, cuda_ver_minor: int) -> List[str]:
        """
        The set of targets to build onto the dev image.

        Parameters
        ----------
        cuda_ver_major : int
            The major CUDA version.
        cuda_ver_minor : int
            The minor CUDA version.

        Returns
        -------
        List[str]
            A list of packages to install for the CUDA dev build.
        """
        ...


class AptGetCUDADockerfileGen(CUDADockerfileGenerator):
    """
    A CUDA Dockerfile generator for Debian-based systems using `apt-get`.
    """

    def __init__(self, url_reader: URLReader):
        super().__init__(url_reader=url_reader)
        self._package_manager: PackageManager = get_package_manager("apt-get")

    def _generate_initial_lines(self, repo_ver: str, *, arch: str = "x86_64") -> str:
        cuda_repo_name = (
            "https://developer.download.nvidia.com/"
            f"compute/cuda/repos/{repo_ver}/{arch}/"
        )
        filename = "cuda-keyring_1.0-1_all.deb"
        read_section = self.url_reader.generate_read_command(
            target=f"{cuda_repo_name}" + filename,
            output_file=filename,
        )
        package_command_section = self.package_manager.generate_local_install_command(
            target=filename,
        )
        return textwrap.dedent(
            f"""
            RUN {read_section}
            RUN {package_command_section}
        """
        ).strip()

    def generate_install_lines(self, build_targets: Iterable[str]) -> str:
        install_section = self.package_manager.generate_install_command(
            targets=build_targets, clean=True
        )
        install_line = (
            f"RUN {self.package_manager.name} update \\\n && {install_section}"
        )
        return install_line

    def _runtime_build_targets(self, cuda_ver_major: int, cuda_ver_minor: int):
        cuda_package_ver: str = f"{cuda_ver_major}-{cuda_ver_minor}"
        return [
            f"cuda-cudart-{cuda_package_ver}",
            f"libcufft-{cuda_package_ver}",
        ]

    def _dev_build_targets(self, cuda_ver_major: int, cuda_ver_minor: int):
        cuda_package_ver: str = f"{cuda_ver_major}-{cuda_ver_minor}"
        return [
            f"cuda-cudart-dev-{cuda_package_ver}",
            f"cuda-nvcc-{cuda_package_ver}",
            f"libcufft-dev-{cuda_package_ver}",
        ]


class YumCUDADockerfileGen(CUDADockerfileGenerator):
    """
    A CUDA Dockerfile generator for RHEL-based systems using `yum`.
    """

    def __init__(self, url_reader: URLReader):
        super().__init__(url_reader=url_reader)
        self._package_manager: PackageManager = get_package_manager("yum")

    def _generate_initial_lines(self, repo_ver: str, *, arch: str = "x86_64") -> str:
        cuda_repo_name = (
            "https://developer.download.nvidia.com/"
            f"compute/cuda/repos/{repo_ver}/{arch}/"
        )
        cuda_repo = f"{cuda_repo_name}cuda-{repo_ver}.repo"
        return f"RUN yum-config-manager --add-repo {cuda_repo} \\\n && yum clean all"

    def generate_install_lines(self, build_targets: Iterable[str]) -> str:
        install_line = self.package_manager.generate_install_command(
            targets=build_targets, clean=True
        )
        return "RUN " + install_line

    def _runtime_build_targets(self, cuda_ver_major: int, cuda_ver_minor: int):
        cuda_package_ver: str = f"{cuda_ver_major}-{cuda_ver_minor}"
        return [
            f"cuda-cudart-{cuda_package_ver}",
            f"libcufft-{cuda_package_ver}",
        ]

    def _dev_build_targets(self, cuda_ver_major: int, cuda_ver_minor: int):
        cuda_package_ver: str = f"{cuda_ver_major}-{cuda_ver_minor}"
        return [
            f"cuda-cudart-devel-{cuda_package_ver}",
            f"cuda-nvcc-{cuda_package_ver}",
            f"libcufft-devel-{cuda_package_ver}",
            "rpm-build",
        ]


def get_cuda_dockerfile_generator(
    pkg_mgr: PackageManager | str, url_reader: URLReader
) -> CUDADockerfileGenerator:
    """
    Returns the appropriate Dockerfile generator for a system.

    Parameters
    ----------
    pkg_mgr : PackageManager or str
        The package manager in use by the image.
    url_reader : URLReader
        The URL reader (e.g. cURL, wget) in use by the image.

    Returns
    -------
    CUDADockerfileGenerator
        The instance of the selected CUDADockerfileGenerator.

    Raises
    ------
    ValueError
        If the package manager is not associated with any CUDADockerfileGenerator
        supported by this file.
    """
    if isinstance(pkg_mgr, PackageManager):
        name = pkg_mgr.name
    elif isinstance(pkg_mgr, str):
        name = pkg_mgr
    else:
        raise ValueError("pkg_mgr argument value must be a PackageManager or str.")
    if isinstance(url_reader, str):
        reader = get_url_reader(url_reader)
    elif isinstance(url_reader, URLReader):
        reader = url_reader
    else:
        raise ValueError("url_reader argument value must be a URLReader or str.")
    if name == "apt-get":
        return AptGetCUDADockerfileGen(url_reader=reader)
    elif name == "yum":
        return YumCUDADockerfileGen(url_reader=reader)
    else:
        raise ValueError(f"Unrecognized package manager: {name}")
