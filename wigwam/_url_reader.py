import os
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Union


class URLReader(ABC):
    """
    A program that accesses URLs.

    Examples of such programs are cURL and wget.
    Capabilities include:
    -   Generating a command to access a URL via
            :func:`~docker_cli.URLReader.generate_read_command`
    -   Returning the name of the program.
    """

    @staticmethod
    @abstractmethod
    def generate_read_command(
        target: str,
        *,
        output_file: Optional[Union[str, os.PathLike[str]]] = None,
    ) -> str:
        """
        Returns a set of commands to read a URL.

        Parameters
        ----------
        target : str
            The target URL.
        output_file : os.PathLike, optional
            The file to redirect the URL contents to. If None, the URL contents
            will go to stdout. Defaults to None.

        Returns
        -------
        str
            The commands.
        """
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Returns the name of the command.

        Returns
        -------
        str
            The command name.
        """
        ...


class Wget(URLReader):
    @staticmethod
    def generate_read_command(
        target: str,
        *,
        output_file: Optional[Union[os.PathLike[str], str]] = None,
    ) -> str:
        retval = f"wget {target}"
        if output_file is not None:
            retval += f" -O {os.fspath(output_file)}"
        return retval

    @property
    def name(self) -> str:  # pragma: no cover
        return "wget"


class Curl(URLReader):
    @staticmethod
    def generate_read_command(
        target: str,
        *,
        output_file: Optional[Union[os.PathLike[str], str]] = None,
    ) -> str:
        retval = f"curl --ssl {target}"
        if output_file is not None:
            retval += f" -o {os.fspath(output_file)}"
        return retval

    @property
    def name(self) -> str:  # pragma: no cover
        return "curl"


def get_url_reader(name: str) -> URLReader:
    """
    Returns the URLReader associated with a command name.

    Parameters
    ----------
    name : str
        The command name.

    Returns
    -------
    URLReader
        The associated URLReader instance.

    Raises
    ------
    ValueError
        When `name` does not correspond to a supported URL reader.
    """
    url_readers: Dict[str, URLReader] = {"curl": Curl(), "wget": Wget()}
    try:
        return url_readers[name]
    except KeyError as err:
        raise ValueError(f"URL Reader {name} not recognized!") from err


def get_supported_url_readers() -> List[str]:
    """
    Returns a list of supported URL readers.

    Returns
    -------
    List[str]
        The list.
    """
    return ["curl", "wget"]
