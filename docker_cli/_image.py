import io
import os
from shlex import split
from subprocess import DEVNULL, PIPE, CalledProcessError, run
from sys import stdin
from typing import (Any, Iterable, List, Optional, Type, TypeVar, Union,
                    overload)

from . import CommandNotFoundError, DockerBuildError, ImageNotFoundError


class Image:
    """
    A docker image.

    Holds a reference to a given docker image and provides
    an interface by which to interact with that image.

    Capabilities include:
    -   Building docker images from dockerfiles or dockerfile-formatted strings
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
            A name or ID by which to find this image using docker inspect.

        Raises
        ----------
        CalledProcessError
            Via :func:`~docker_cli.get_image_id`.
        """
        self._id = get_image_id(name_or_id)

    @overload
    @classmethod
    def build(
        cls: Type[Self],
        tag: str,
        *,
        context: Union[str, os.PathLike[str]],
        dockerfile: Optional[os.PathLike[str]],
        stdout: Optional[io.TextIOBase],
        stderr: Optional[io.TextIOBase],
        network: str,
        no_cache: bool
    ) -> Self:
        """
        Build a new image from a dockerfile.

        Build a Dockerfile at the given path with the given name, then
        return the associated Image instance.

        Parameters
        ----------
        tag : str
            A name for the image.
        context : os.PathLike, optional
            The build context. Defaults to ".".
        dockerfile : os.PathLike, optional
            The path of the Dockerfile to build, relative to the `context`
            directory. Defaults to None.
        stdout : io.TextIOBase or special value, optional
            For a description of valid values, see :func:`subprocess.run`.
        stderr : io.TextIOBase or special value, optional
            For a description of valid values, see :func:`subprocess.run`.
        network : str, optional
            The name of the network. Defaults to "host".
        no-cache : bool, optional
            A boolean designating whether or not the docker build should use
            the cache.

        Returns
        -------
        Image
            The created image.

        Raises
        -------
        CalledProcessError
            If the docker build command fails.
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
        context: Union[str, os.PathLike[str]],
        dockerfile_string: str,
        stdout: Optional[io.TextIOBase],
        stderr: Optional[io.TextIOBase],
        network: str,
        no_cache: bool
    ) -> Self:
        """
        Builds a new image from a string in dockerfile syntax.

        Parameters
        ----------
        tag : str
            A name for the image.
        context : os.PathLike, optional
            The build context. Defaults to ".".
        dockerfile_string : str
            A Dockerfile-formatted string.
        stdout : io.TextIOBase or special value, optional
            For a description of valid values, see :func:`subprocess.run`.
        stderr : io.TextIOBase or special value, optional
            For a description of valid values, see :func:`subprocess.run`.
        network : str, optional
            The name of the network. Defaults to "host".
        no-cache : bool, optional
            A boolean designating whether or not the docker build should use
            the cache.

        Returns
        -------
        Image
            The created Image.

        Raises
        -------
        CalledProcessError
            If the docker build command fails.
        ValueError
            If both `dockerfile` and `dockerfile_string` are defined.
        """
        ...

    @classmethod
    def build(
        cls,
        tag,
        *,
        context=".",
        dockerfile=None,
        dockerfile_string=None,
        stdout=None,
        stderr=None,
        network="host",
        no_cache=True
    ):
        if dockerfile is not None and dockerfile_string is not None:
            raise ValueError(
                "Both dockerfile and dockerfile_string passed as arguments."
            )

        # Build with dockerfile if dockerfile_string is None
        dockerfile_build = dockerfile_string is None

        context_str = os.fspath(".") if context is None else os.fspath(context)
        cmd = [
            "docker",
            "build",
            f"--network={network}",
            context_str,
            "-t",
            tag
        ]

        if no_cache:
            cmd += ["--no-cache"]

        if dockerfile_build:
            # If a dockerfile path is given, include it.
            # Else, docker build will default to "./Dockerfile"
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
                check=True
            )
        except CalledProcessError as err:
            if dockerfile_build:
                raise DockerBuildError(tag, dockerfile) from err
            else:
                raise DockerBuildError(tag, dockerfile_string) from err

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
            The string returned by the docker inspect command.

        Raises
        -------
        CalledProcessError
            If the docker inspect command fails.
        """
        cmd = ["docker", "inspect"]
        if format:
            cmd += [f"-f={format}"]
        cmd += [self._id]

        inspect_result = run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )

        output_text = inspect_result.stdout
        return output_text

    def run(
        self,
        command: str,
        *,
        stdout: Optional[Union[io.TextIOBase, int]] = None,
        stderr: Optional[Union[io.TextIOBase, int]] = None,
        interactive: bool = False,
        network: str = "host"
    ):
        """
        Run the given command on a container.

        .. warning::
            This method does not work correctly if the image built does not have
            bash installed.

        Parameters
        ----------
        cmd : str
            The desired command, in linux command format.
        stdout : io.TextIOBase or special value, optional
            For a description of valid values, see :func:`subprocess.run`.
        stderr : io.TextIOBase or special value, optional
            For a description of valid values, see :func:`subprocess.run`.
        interactive : bool, optional
            A boolean describing whether or not to run this command in
            interactive mode or not. Defaults to True.
        network : str, optional
            The name of the network. Defaults to "host".

        Returns
        -------
        str, optional
            The output of the process, if `stdout` == PIPE.

        Raises
        -------
        CalledProcessError
            If the docker run command fails.
        CommandNotFoundOnImageError:
            When a command is attempted that is not recognized on the image.
        """
        cmd = ["docker", "run", f"--network={network}", "--rm"]
        if interactive:
            cmd += ["-i"]
            if stdin.isatty():
                cmd += ["--tty"]
        cmd += [self._id, "bash"]
        cmd += ["-ci"] if interactive else ["-c"]
        cmd += split(f"'{command}'")

        try:
            result = run(
                cmd,
                text=True,
                stdout=stdout,  # type: ignore
                stderr=stderr,  # type: ignore
                check=True
            )
            retval = result.stdout
        except CalledProcessError as err:
            if err.returncode == 127:
                raise CommandNotFoundError(err, split(command)[0]) from err
            else:
                raise err from err
        return retval

    def drop_in(
            self,
            network: str = "host"
    ):
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
        CalledProcessError
            If the docker run command fails.
        CommandNotFoundOnImageError:
            When bash is not recognized on the image.
        """
        cmd = ["docker", "run", f"--network={network}", "--rm", "-i"]
        if stdin.isatty():
            cmd += ["--tty"]
        cmd += [self._id, "bash"]

        try:
            run(
                cmd,
                text=True,
                check=True
            )
        except CalledProcessError as err:
            if err.returncode == 127:
                raise CommandNotFoundError(err, "bash") from err
            else:
                print(f"Drop-in session exited with code {err.returncode}.")
                return
        print("Drop-in session exited with code 0.")

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

        Raises
        -------
        CalledProcessError
            If the docker inspect command fails with a return value != 1.
        """
        return list(filter(self.has_command, commands))

    def has_command(self, command: str) -> bool:
        """
        Checks to see if the image has a command.

        Parameters
        ----------
        command : str
            The name of the command (e.g. "curl", "echo")

        Returns
        -------
        bool
            True if the command is present, False if not.

        Raises
        ------
        CalledProcessError
            When the command check returns with any value other than 0 or 1.
        """
        try:
            self.run(
                f"command -v {command}",
                stdout=PIPE,
                stderr=DEVNULL
            )
        except CalledProcessError as err:
            # "command -v {cmd}" returns 0 if the command is found, else 1.
            # Thus, the CalledProcessError exception means return False
            # if err.returncode == 1.
            # In other cases, the error still needs to be thrown.
            if err.returncode == 1:
                return False
            else:
                raise err from err
        else:
            return True

    @property
    def tags(self) -> List[str]:
        """List[str]: The Repo Tags held on this docker image."""
        return self._inspect(format="{{.RepoTags}}").strip('][\n').split(', ')

    @property
    def id(self) -> str:
        """str: This image's ID."""
        return self._id

    def __repr__(self) -> str:
        """
        Returns a string representation of the Image.

        Returns
        -------
        str
            A string representation of the Image.
        """
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
    Acquires the ID of a docker image with the given name or ID.

    Parameters
    ----------
    name_or_id : str
        The image name or ID.

    Returns
    -------
    str
        The ID of the given docker image.

    Raises
    -------
    CalledProcessError
        If the docker inspect command fails.
    ValueError
        If `name_or_id` is not a string
    """
    if not isinstance(name_or_id, str):
        raise ValueError(
            f"name_or_id given as {type(name_or_id)}. Expected string."
        )
    command = "docker inspect -f={{.Id}} " + name_or_id
    try:
        process = run(
            split(command),
            capture_output=True,
            text=True,
            check=True
        )
    except CalledProcessError as err:
        raise ImageNotFoundError(tag_or_id=name_or_id) from err
    process_stdout = process.stdout.strip()
    return process_stdout
