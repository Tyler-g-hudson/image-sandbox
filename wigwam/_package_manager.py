import textwrap
from abc import ABC, abstractmethod
from typing import Iterable, List


class PackageManager(ABC):
    """
    A Linux package manager

    Capabilities include:
    -   Providing string for generating installation and configuration of
        packages on the command line via:
    \t  -   :func:`~docker_cli.PackageManager.generate_install_command`
    \t  -   :func:`~docker_cli.PackageManager.generate_package_command`
    \t  -   :func:`~docker_cli.PackageManager.generate_configure_command`
    -   Returning an associated name and filetype
    """

    @staticmethod
    @abstractmethod
    def generate_install_command(targets: Iterable[str], *, clean: bool = True) -> str:
        """
        Returns an set of commands to install a list of target packages.

        Parameters
        ----------
        targets : Iterable[str]
            The install targets.
        clean : bool, optional
            Whether or not to add a clean command to the list.
            Defaults to True.

        Returns
        -------
        str
            The commands.
        """
        ...

    @staticmethod
    @abstractmethod
    def generate_local_install_command(
        target: str,
    ) -> str:
        """
        Returns a command to install a single local package.

        Uses the package tool underlying the package manager if one is
        available. (e.g. dpkg or rpm)

        Parameters
        ----------
        target : str
            The install target.

        Returns
        -------
        str
            The commands.
        """
        ...

    @staticmethod
    @abstractmethod
    def generate_configure_command() -> str:
        """
        Returns commands to configure and update the package manager.

        Returns
        -------
        str
            The commands.
        """
        ...

    @property
    @abstractmethod
    def name(self):
        """
        The package manager's command name.
        """
        ...

    @property
    @abstractmethod
    def file_type(self):
        """
        The file extension of package files associated with this package manager.
        """
        ...


class Yum(PackageManager):
    @staticmethod
    def generate_install_command(
        targets: Iterable[str],
        clean: bool = True,
    ) -> str:
        # " ".join() used here in lieu of shlex.join because shlex.join breaks
        # situations where an environment variable is referenced in one or more targets.
        retval = "yum install -y " + " ".join(targets)
        if clean:
            retval += " && yum clean all && rm -rf /var/cache/yum"
        return retval

    @staticmethod
    def generate_local_install_command(  # pragma: no cover
        target: str,
    ) -> str:
        return f"rpm -i {target}"

    @staticmethod
    def generate_configure_command() -> str:
        retval = textwrap.dedent(
            """
            yum update -y                                                       \\
              && echo 'skip_missing_names_on_install=False' >> /etc/yum.conf    \\
              && rm -rf /var/cache/yum
        """
        ).strip()
        return retval

    @property
    def name(self):
        return "yum"

    @property
    def file_type(self):  # pragma: no cover
        return "rpm"


class AptGet(PackageManager):
    @staticmethod
    def generate_install_command(
        targets: Iterable[str],
        clean: bool = True,
    ) -> str:
        # " ".join() used here in lieu of shlex.join because shlex.join breaks
        # situations where an environment variable is referenced in one or more targets.
        retval = "apt-get -y update && apt-get -y install " + " ".join(targets)
        if clean:
            retval += " && apt-get clean all"
        return retval

    @staticmethod
    def generate_local_install_command(  # pragma: no cover
        target: str,
    ) -> str:
        return f"dpkg -i {target}"

    @staticmethod
    def generate_configure_command() -> str:
        return "apt-get -y update && apt-get clean all"

    @property
    def name(self):
        return "apt-get"

    @property
    def file_type(self):  # pragma: no cover
        return "deb"


def get_package_manager(name: str) -> PackageManager:
    """
    Returns the PackageManager associated with a name.

    Parameters
    ----------
    name : str
        The name of the command.

    Returns
    -------
    PackageManager
        An associated PackageManager object.

    Raises
    ------
    ValueError
        When `name` does not correspond to a supported package manager.
    """
    if name == "apt-get":
        return AptGet()
    if name == "yum":
        return Yum()
    else:
        raise ValueError(f"Package manager '{name}' not recognized!")


def get_supported_package_managers() -> List[str]:
    """
    Returns a list of supported package managers.

    Returns
    -------
    List[str]
        The list.
    """
    return ["yum", "apt-get"]
