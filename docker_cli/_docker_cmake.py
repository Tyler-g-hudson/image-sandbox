from textwrap import dedent

from ._docker_mamba import micromamba_docker_lines


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


def cmake_config_dockerfile(build_type: str) -> str:
    """
    Creates a dockerfile for configuring CMAKE.

    Parameters
    ----------
    build_type : str
        The CMAKE build type.

    Returns
    -------
    str
        The generated Dockerfile body.
    """
    body = (
        micromamba_docker_lines()
        + "\n\n"
        + dedent(
            f"""
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
    """
        ).strip()
    )

    return body


def cmake_build_dockerfile() -> str:
    """
    Creates a dockerfile for compiling with CMAKE.

    Returns
    -------
    str
        The generated Dockerfile body.
    """
    body = (
        micromamba_docker_lines()
        + "\n\n"
        + "RUN cmake --build $BUILD_PREFIX --parallel"
    )

    return body


def cmake_install_dockerfile(ld_lib: str) -> str:
    """
    Creates a dockerfile for installing with CMAKE.

    Parameters
    ----------
    ld_lib : str
        The name of the linking library file (e.g. "lib" or "lib64".)

    Returns
    -------
    str
        The generated Dockerfile body.
    """
    body = (
        micromamba_docker_lines()
        + "\n\n"
        + dedent(
            f"""
        USER root
        RUN cmake --build $BUILD_PREFIX --target install --parallel
        RUN chmod -R 777 $BUILD_PREFIX

        USER $MAMBA_USER
        RUN mkdir /tmp/Testing

        ENV LD_LIBRARY_PATH $LD_LIBRARY_PATH:$INSTALL_PREFIX/{ld_lib}
        WORKDIR $BUILD_PREFIX
    """
        ).strip()
    )

    return body
