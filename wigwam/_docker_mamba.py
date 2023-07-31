from __future__ import annotations

import shlex
import textwrap
from pathlib import Path
from typing import Iterable, Tuple, overload


def mamba_install_dockerfile(
    env_reqs_file: Path,
) -> Tuple[str, str]:
    """
    Creates and returns a Dockerfile for installing micromamba.

    Parameters
    ----------
    env_reqs_file : Path
        The path to the requirements file.

    Returns
    -------
    header : str
        The initial lines of the generated Dockerfile.
    body : str
        The generated Dockerfile body.
    """
    body = _mamba_install_body(env_reqs_file=env_reqs_file)
    header = _mamba_install_prefix()
    return header, body


def mamba_add_reqs_dockerfile(
    env_reqs_file: Path,
) -> str:
    """
    Creates a Dockerfile for adding micromamba environment specs.

    Parameters
    ----------
    env_reqs_file : Path
        The path to the requirements file, relative to the dockerfile context.

    Returns
    -------
    str
        The generated Dockerfile body.
    """
    return _mamba_reqs_command(
        reqs_file=env_reqs_file, command="install", channels=["conda-forge"]
    )


def mamba_add_packages_dockerfile(
    packages: Iterable[str], channels: Iterable[str] | None
) -> str:
    """
    Creates a dockerfile body for adding the given packages to a micromamba environment.

    Parameters
    ----------
    packages : Iterable[str]
        The set of packages to be added to the environment.
    channels: Iterable[str], optional
        Channels to look for packages in.

    Returns
    -------
    str
        The dockerfile body.
    """
    return _mamba_reqs_command(packages=packages, channels=channels, command="install")


def mamba_lockfile_command(
    env_name: str,
) -> str:
    """
    Returns a command to generate a lockfile with micromamba.

    Parameters
    ----------
    env_name : str
        The name of the environment for which a Dockerfile should be generated.

    Returns
    -------
    str
        The command.
    """
    cmd = f"micromamba env export --name {env_name} --explicit --no-md5"
    return cmd


def micromamba_docker_lines():
    return textwrap.dedent(
        """
        ARG MAMBA_DOCKERFILE_ACTIVATE=1

        USER $MAMBA_USER
        """
    ).strip()


@overload
def _mamba_reqs_command(
    command: str,
    *,
    channels: Iterable[str] | None,
    packages: Iterable[str],
    env_name: str | None = ...,
) -> str:
    ...


@overload
def _mamba_reqs_command(
    command: str,
    *,
    channels: Iterable[str] | None,
    reqs_file: Path,
    env_name: str | None = ...,
) -> str:
    ...


def _mamba_reqs_command(
    command, *, channels, reqs_file=None, packages=None, env_name=None
) -> str:
    if (reqs_file is not None) and (packages is not None):
        raise ValueError("Specfile and packages both given. Use only one.")
    if command not in ["install", "create"]:
        raise ValueError(
            "Improper value given for micromamba requirements installation. "
            'Please use one of "install" or "create".'
        )

    # If a name was given for the environment, an argument will be added to all
    # micromamba installation commands.
    if env_name is None:
        name_arg: str = ""
    else:
        name_arg = f" -n {env_name}"

    # Put together the channels argument
    if channels is not None:
        channels_arg = f" -c {shlex.join(channels)} --override-channels"

    # If a reqs_file is given, give the instructions for copying and installing a
    # requirements file.
    if reqs_file is not None:
        install_command = textwrap.dedent(
            f"""
            COPY {reqs_file} /tmp/reqs-file.txt
            RUN micromamba {command}{name_arg}{channels_arg} -y -f /tmp/reqs-file.txt \\
             && rm /tmp/reqs-file.txt \\
             && micromamba clean --all --yes
        """
        ).strip()
    # Otherwise packages were given, so give the instructions for installing the
    # packages.
    else:
        packages_str = shlex.join(packages)
        install_command = textwrap.dedent(
            f"""
            RUN micromamba {command}{name_arg}{channels_arg} -y {packages_str} \\
             && micromamba clean --all --yes
        """
        ).strip()

    # Assemble this command into a portion of a Dockerfile string.
    cmd: str = f"ARG MAMBA_DOCKERFILE_ACTIVATE=1\n\n{install_command}"

    return cmd


def _mamba_install_prefix():
    return "FROM mambaorg/micromamba:1.3.1 AS micromamba"


def _mamba_install_body(env_reqs_file: Path):
    # String variables to keep some of the COPY lines short
    bin = "/usr/local/bin/"
    activate_current_env = f"{bin}_activate_current_env.sh"
    dockerfile_shell = f"{bin}_dockerfile_shell.sh"
    entrypoint = f"{bin}_entrypoint.sh"
    initialize_user_account = f"{bin}_dockerfile_initialize_user_accounts.sh"
    setup_root_prefix = f"{bin}_dockerfile_setup_root_prefix.sh"

    # Adapted from: https://micromamba-docker.readthedocs.io/en/latest/advanced_usage.html#adding-micromamba-to-an-existing-docker-image     # noqa: E501
    body: str = (
        textwrap.dedent(
            f"""
        USER root

        # if your image defaults to a non-root user, then you may want to make
        # the next 3 ARG commands match the values in your image. You can get
        # the values by running: docker run --rm -it my/image id -a
        ENV MAMBA_USER=$DEFAULT_USER
        ENV MAMBA_USER_ID=$DEFAULT_UID
        ENV MAMBA_USER_GID=$DEFAULT_GID

        ENV MAMBA_ROOT_PREFIX="/opt/conda"
        ENV MAMBA_EXE="/bin/micromamba"

        COPY --from=micromamba "$MAMBA_EXE" "$MAMBA_EXE"
        COPY --from=micromamba {activate_current_env} {activate_current_env}
        COPY --from=micromamba {dockerfile_shell} {dockerfile_shell}
        COPY --from=micromamba {entrypoint} {entrypoint}
        COPY --from=micromamba {activate_current_env} {activate_current_env}
        COPY --from=micromamba {initialize_user_account} {initialize_user_account}
        COPY --from=micromamba {setup_root_prefix} {setup_root_prefix}

        RUN {initialize_user_account} \\
         && {setup_root_prefix}

        USER $MAMBA_USER

        SHELL ["{dockerfile_shell}"]

        ENTRYPOINT ["{entrypoint}"]
        # Optional: if you want to customize the ENTRYPOINT and have a conda
        # environment activated, then do this:
        # ENTRYPOINT ["{entrypoint}", "my_entrypoint_program"]

    """
        ).strip()
        + "\n"
    )
    body += _mamba_reqs_command(
        reqs_file=env_reqs_file, command="install", channels=["conda-forge"]
    )

    return body
