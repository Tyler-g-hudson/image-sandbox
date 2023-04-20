from __future__ import annotations

import io
import os
from shlex import split
from subprocess import DEVNULL, CalledProcessError, run
from sys import stdin
from typing import Any, List, Iterable, Optional, Type, TypeVar, Union, overload

from ._bind_mount import BindMount
from ._exceptions import CommandNotFoundError, DockerBuildError, ImageNotFoundError


class Image:
    """
    A Docker image.

    Holds a reference to a given Docker image and provides
    an interface by which to interact with that image.

    Capabilities include:
    -   Building Docker images from dockerfiles or Dockerfile-formatted strings
        via :func:`~docker_cli.Image.build`.
    -   Running commands in containers built from the image using
        :func:`~docker_cli.Image.run`.
    -   Inspecting properties of the given image.
    """

    Self = TypeVar("Self", bound="Image")

    def __init__(self, name_or_id: str):
        """
        Initialize a new Image object.

        Parameters
        ----------
        name_or_id : str
            A name or ID by which to find this image using 'docker inspect'.
        """
        self._id = get_image_id(name_or_id)

    @overload
    @classmethod
    def build(
        cls: Type[Self],
        tag: str,
        *,
        dockerfile: Union[str, os.PathLike[str]],
        context: Union[str, os.PathLike[str]] = ...,
        stdout: Any = ...,
        stderr: Any = ...,
        network: str = ...,
        no_cache: bool = ...,
    ) -> Self:
        """
        Build a new image from a Dockerfile.

        Build a Dockerfile at the given path with the given name, then
        return the associated Image instance.

        Parameters
        ----------
        tag : str
            A name for the image.
        dockerfile : os.PathLike
            The path of the Dockerfile to build directory.
        context : os.PathLike, optional
            The build context. Defaults to ".".
        stdout : io.TextIOBase or special value, optional
            For a description of valid values, see :func:`subprocess.run`.
        stderr : io.TextIOBase or special value, optional
            For a description of valid values, see :func:`subprocess.run`.
        network : str, optional
            The name of the network. Defaults to "host".
        no_cache : bool, optional
            A boolean designating whether or not the Docker build should use
            the cache. Defaults to False.

        Returns
        -------
        Image
            The created image.

        Raises
        -------
        DockerBuildError
            If the Docker build command fails.
        ValueError
            If both `dockerfile` and `dockerfile_string` are defined.
        """
        ...

    @overload
    @classmethod
    def build(
        cls: Type[Self],
        tag: str,
        *,
        dockerfile_string: str,
        context: Union[str, os.PathLike[str]] = ...,
        stdout: Any = ...,
        stderr: Any = ...,
        network: str = ...,
        no_cache: bool = ...,
    ) -> Self:
        """
        Builds a new image from a string in Dockerfile syntax.

        Parameters
        ----------
        tag : str
            A name for the image.
        dockerfile_string : str
            A Dockerfile-formatted string.
        context : os.PathLike, optional
            The build context. Defaults to ".".
        stdout : io.TextIOBase or special value, optional
            For a description of valid values, see :func:`subprocess.run`.
        stderr : io.TextIOBase or special value, optional
            For a description of valid values, see :func:`subprocess.run`.
        network : str, optional
            The name of the network. Defaults to "host".
        no_cache : bool, optional
            A boolean designating whether or not the Docker build should use
            the cache. Defaults to False.

        Returns
        -------
        Image
            The created Image.

        Raises
        -------
        DockerBuildError
            If the Docker build command fails.
        ValueError
            If both `Dockerfile` and `dockerfile_string` are defined.
        """
        ...

    @classmethod
    def build(
        cls,
        tag,
        *,
        dockerfile=None,
        dockerfile_string=None,
        context=".",
        stdout=None,
        stderr=None,
        network="host",
        no_cache=False,
    ):
        if dockerfile is not None and dockerfile_string is not None:
            raise ValueError(
                "Both dockerfile and dockerfile_string passed as arguments."
            )

        # Build with Dockerfile if dockerfile_string is None
        dockerfile_build = dockerfile_string is None

        context_str = os.fspath(".") if context is None else os.fspath(context)
        cmd = ["docker", "build", f"--network={network}", context_str, f"-t={tag}"]

        if no_cache:
            cmd += ["--no-cache"]

        if dockerfile_build:
            # If a Dockerfile path is given, include it.
            # Else, Docker build will default to "./Dockerfile"
            if dockerfile is not None:
                cmd += [f"--file={os.fspath(dockerfile)}"]
            stdin = None
        else:
            cmd += ["-f-"]
            stdin = dockerfile_string

        try:
            run(
                cmd,
                text=True,
                stdout=stdout,  # type: ignore
                stderr=stderr,  # type: ignore
                input=stdin,
                check=True,
            )
        except CalledProcessError as err:
            if dockerfile_build:
                raise DockerBuildError(
                    message=f"Dockerfile {tag} at {dockerfile} failed to build."
                ) from err
            else:
                raise DockerBuildError(
                    f"String dockerfile {tag} failed to build."
                ) from err

        return cls(tag)

    def _inspect(self, format: Optional[str] = None) -> str:
        """
        Use 'docker inspect' to retrieve a piece of information about the
        image.

        Parameters
        ----------
        format : str, optional
            The value to be requested by the --format argument, or None.
            Defaults to None.

        Returns
        -------
        str
            The string returned by the 'docker inspect' command.
        """
        cmd = ["docker", "inspect"]
        if format:
            cmd += [f"-f={format}"]
        cmd += [self._id]

        inspect_result = run(cmd, capture_output=True, text=True, check=True)

        output_text = inspect_result.stdout
        return output_text

    def run(
        self,
        command: str,
        *,
        stdout: io.TextIOBase | int | None = None,
        stderr: io.TextIOBase | int | None = None,
        interactive: bool = False,
        network: str = "host",
        check: bool = True,
        host_user: bool = False,
        mounts: Iterable[BindMount] | None = None
    ) -> str:
        """
        Run the given command on a container.

        .. warning::
            This method does not work correctly if the image built does not have
            bash installed.

        Parameters
        ----------
        cmd : str
            The desired command, in Unix shell syntax.
        stdout : io.TextIOBase or special value, optional
            For a description of valid values, see :func:`subprocess.run`.
        stderr : io.TextIOBase or special value, optional
            For a description of valid values, see :func:`subprocess.run`.
        interactive : bool, optional
            A boolean describing whether or not to run this command in
            interactive mode or not. Defaults to False.
        network : str, optional
            The name of the network. Defaults to "host".
        check: bool, optional
            If True, check for CalledProcessErrors on non-zero return codes. Defualts
            to True.
        host_user: bool, optional
            If True, run the command as the user on the host machine, else run as the
            default user. Defaults to False.
        mounts : Iterable[BindMount], optional
            A list of mount descriptions to apply to the run command.

        Returns
        -------
        str, optional
            The output of the process, if `stdout` == PIPE.

        Raises
        -------
        CommandNotFoundError:
            When a command is attempted that is not recognized on the image.
        """

        cmd = ["docker", "run", f"--network={network}", "--rm"]
        if host_user:
            cmd += ["-u", f"{os.getuid()}:{os.getgid()}"]
        if mounts is not None:
            for mount in mounts:
                cmd += ["-v", f"{mount.mount_string()}"]
        if interactive:
            cmd += ["-i"]
            if stdin.isatty():
                cmd += ["--tty"]  # pragma: no cover
        cmd += [self._id, "bash"]
        cmd += ["-ci"] if interactive else ["-c"]
        cmd += split(f"'{command}'")

        try:
            result = run(
                cmd,
                text=True,
                stdout=stdout,  # type: ignore
                stderr=stderr,  # type: ignore
                check=check,
            )
        except CalledProcessError as err:
            if err.returncode == 127:
                raise CommandNotFoundError(split(command)[0]) from err
            else:
                raise
        return result.stdout

    def drop_in(self, network: str = "host") -> None:
        """
        Start a drop-in session on a disposable container.

        .. warning::
            This method does not work correctly if the image built does not have
            bash installed.

        Parameters
        ----------
        network : str, optional
            The name of the network. Defaults to "host".

        Raises
        -------
        CommandNotFoundError:
            When bash is not recognized on the image.
        """
        self.run(   # pragma: no cover
            "bash",
            interactive=True,
            network=network,
            check=False,
            host_user=True
        )

    def check_command_availability(self, commands: Iterable[str]) -> List[str]:
        """
        Determines which of the commands in a list are present on the image.

        Parameters
        ----------
        commands : Iterable[str]
            The commands to be checked.

        Returns
        -------
        Iterable[str]
            The names of all commands in `commands` that were present on the
            image.
        """
        return list(filter(self.has_command, commands))

    def has_command(self, command: str) -> bool:
        """
        Checks to see if the image has a command.

        Parameters
        ----------
        command : str
            The name of the command (e.g. "curl", "echo").

        Returns
        -------
        bool
            True if the command is present, False if not.
        """
        try:
            self.run(f"command -v {command}", stdout=DEVNULL)
        except CalledProcessError as err:
            # "command -v {cmd}" returns 0 if the command is found, else 1.
            # Thus, the CalledProcessError exception means return False
            # if err.returncode == 1.
            # In other cases, the error still needs to be thrown.
            if err.returncode == 1:
                return False
            else:
                raise  # pragma: no cover
        else:
            return True

    @property
    def tags(self) -> List[str]:
        """List[str]: The Repo Tags held on this Docker image."""
        return self._inspect(format="{{.RepoTags}}").strip("][\n").split(", ")

    @property
    def id(self) -> str:
        """str: This image's ID."""
        return self._id

    def __repr__(self) -> str:
        """Returns a string representation of the Image."""
        return f"Image(id={self._id}, tags={self.tags})"

    def __eq__(self, other: Any) -> bool:
        """
        Evaluates equality of an Image with another object.

        Parameters
        ----------
        other : object
            Another object to which this image will be compared.

        Returns
        -------
        bool
            True if other is an Image with the same ID as this one, False
            otherwise.
        """
        if not isinstance(self, type(other)):
            return False
        return self._id == other._id


def get_image_id(name_or_id: str) -> str:
    """
    Acquires the ID of a Docker image with the given name or ID.

    Parameters
    ----------
    name_or_id : str
        The image name or ID.

    Returns
    -------
    str
        The ID of the given Docker image.

    Raises
    -------
    ValueError
        If `name_or_id` is not a string
    """
    if not isinstance(name_or_id, str):
        raise ValueError(f"name_or_id given as {type(name_or_id)}. Expected string.")
    command = "docker inspect -f={{.Id}} " + name_or_id
    try:
        process = run(split(command), capture_output=True, text=True, check=True)
    except CalledProcessError as err:
        # The Docker command will return with value 1 if the image was not found.
        # This should be raised as a more specific ImageNotFoundError. Any other
        # non-zero return code should be raised as a CalledProcessError.
        if err.returncode == 1:
            raise ImageNotFoundError(name_or_id) from err
        else:
            raise  # pragma: no cover
    process_stdout = process.stdout.strip()
    return process_stdout
