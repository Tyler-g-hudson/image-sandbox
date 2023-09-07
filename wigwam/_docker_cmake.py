from textwrap import dedent

from ._defaults import build_prefix, install_prefix, src_prefix
from ._docker_mamba import micromamba_docker_lines


def cmake_config_dockerfile(base: str, build_type: str, with_cuda: bool = True) -> str:
    """
    Creates a Dockerfile for configuring CMake Build.

    Parameters
    ----------
    base : str
        The base image tag.
    build_type : str
        The CMake build type. See
        `here <https://cmake.org/cmake/help/latest/variable/CMAKE_BUILD_TYPE.html>`_
        for possible values.
    with_cuda : bool, optional
        Whether or not to use CUDA in the build. Defaults to True.

    Returns
    -------
    dockerfile : str
        The generated Dockerfile.
    """
    # Listing the additional arguments and then joining them later, because I have
    # a feeling there may be additional cmake arguments to add in the future, and this
    # keeps that process simple.
    additional_args = []
    if with_cuda:
        additional_args += ["-D WITH_CUDA=YES"]
    else:
        additional_args += ["-D WITH_CUDA=NO"]
    cmake_extra_args = " ".join(additional_args)

    # Begin constructing the dockerfile with the initial FROM line.
    dockerfile: str = f"FROM {base}\n\n"

    # Activate the micromamba user and environment.
    dockerfile += micromamba_docker_lines() + "\n\n"
    dockerfile += dedent(
        f"""
            ENV INSTALL_PREFIX {str(install_prefix())}
            ENV BUILD_PREFIX {str(build_prefix())}
            ENV PYTHONPATH $INSTALL_PREFIX/packages:$PYTHONPATH

            RUN cmake \\
                -S {src_prefix()}
                -B $BUILD_PREFIX \\
                -G Ninja \\
                -D ISCE3_FETCH_DEPS=NO \\
                -D CMAKE_BUILD_TYPE={build_type} \\
                -D CMAKE_INSTALL_PREFIX=$INSTALL_PREFIX \\
                -D CMAKE_PREFIX_PATH=$MAMBA_ROOT_PREFIX \\
                {cmake_extra_args}
        """
    ).strip()

    return dockerfile


def cmake_build_dockerfile(base: str) -> str:
    """
    Creates a dockerfile for compiling with CMAKE.

    Parameters
    ----------
    base : str
        The base image tag.

    Returns
    -------
    dockerfile: str
        The generated Dockerfile.
    """
    # Begin constructing the dockerfile with the initial FROM line.
    dockerfile = f"FROM {base}\n\n"

    # Run as the $MAMBA_USER and activate the micromamba environment.
    dockerfile += f"{micromamba_docker_lines()}\n\n"

    # build the project.
    dockerfile += "RUN cmake --build $BUILD_PREFIX --parallel"

    return dockerfile


def cmake_install_dockerfile(base: str, ld_lib: str) -> str:
    """
    Creates a dockerfile for installing with CMAKE.

    Parameters
    ----------
    base : str
        The base image tag.
    ld_lib : str
        The name of the linking library file (e.g. "lib" or "lib64".)

    Returns
    -------
    dockerfile: str
        The generated Dockerfile.
    """
    # Begin constructing the dockerfile with the initial FROM line.
    dockerfile = f"FROM {base}\n\n"

    # Run as the $MAMBA_USER and activate the micromamba environment.
    dockerfile += f"{micromamba_docker_lines()}\n\n"

    # Install the project and set the appropriate permissions at the target directory.
    dockerfile += dedent(
        f"""
            USER root
            RUN cmake --build $BUILD_PREFIX --target install --parallel
            RUN chmod -R 755 $BUILD_PREFIX

            USER $MAMBA_USER
            RUN mkdir /tmp/Testing

            ENV LD_LIBRARY_PATH $LD_LIBRARY_PATH:$INSTALL_PREFIX/{ld_lib}
            WORKDIR $BUILD_PREFIX
        """
    ).strip()

    return dockerfile
