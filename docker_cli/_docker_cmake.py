from textwrap import dedent

from ._docker_mamba import micromamba_docker_lines
from ._dockerfile import Dockerfile


def install_prefix() -> str:
    """
    Returns the build system's install prefix.

    Returns
    -------
    str
        The install prefix.
    """
    return "/app"


def build_prefix() -> str:
    """
    Returns the build system's build prefix.

    Returns
    -------
    str
        The build prefix.
    """
    return "/tmp/build"


def _cmake_config_dockerfile(
    build_type: str
) -> Dockerfile:
    """
    Creates a dockerfile for configuring CMAKE.

    Parameters
    ----------
    build_type : str
        The CMAKE build type.

    Returns
    -------
    Dockerfile
        The generated Dockerfile.
    """
    body = micromamba_docker_lines() + "\n\n" + dedent(f"""
        ENV INSTALL_PREFIX {install_prefix()}
        ENV BUILD_PREFIX {build_prefix()}
        ENV PYTHONPATH $INSTALL_PREFIX/packages:$PYTHONPATH

        RUN cmake \\
            -B $BUILD_PREFIX \\
            -G Ninja \\
            -DCMAKE_BUILD_TYPE={build_type} \\
            -DCMAKE_INSTALL_PREFIX=$INSTALL_PREFIX \\
            -DCMAKE_PREFIX_PATH=$MAMBA_ROOT_PREFIX \\
            .
    """).strip()

    dockerfile: Dockerfile = Dockerfile(body=body)
    return dockerfile


def _cmake_build_dockerfile() -> Dockerfile:
    """
    Creates a dockerfile for compiling with CMAKE.

    Returns
    -------
    Dockerfile
        The generated Dockerfile.
    """
    body = micromamba_docker_lines() + "\n\n" + \
        "RUN cmake --build $BUILD_PREFIX --parallel"

    dockerfile: Dockerfile = Dockerfile(body=body)
    return dockerfile


def _cmake_install_dockerfile(ld_lib: str) -> Dockerfile:
    """
    Creates a dockerfile for installing with CMAKE.

    Parameters
    ----------
    ld_lib : str
        The name of the linking library file (e.g. "lib" or "lib64".)

    Returns
    -------
    Dockerfile
        The generated Dockerfile.
    """
    body = micromamba_docker_lines() + "\n\n" + dedent(f"""
        USER root
        RUN cmake --build $BUILD_PREFIX --target install --parallel
        RUN chmod -R 777 $BUILD_PREFIX

        USER $MAMBA_USER
        RUN mkdir /tmp/Testing

        ENV LD_LIBRARY_PATH $LD_LIBRARY_PATH:$INSTALL_PREFIX/{ld_lib}
        WORKDIR $BUILD_PREFIX
    """).strip()

    dockerfile: Dockerfile = Dockerfile(body=body)
    return dockerfile
