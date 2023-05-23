class CommandNotFoundError(Exception):
    """Raised when a command is attempted but not found."""

    def __init__(self, command_name: str):
        """
        Raise this exception when a command is attempted but not found.

        Parameters
        ----------
        command_name : str
            The name of the command.
        """
        self.command_name = command_name
        super().__init__(
            f"Command '{self.command_name}' was run, but is not "
            "present on the Docker image."
        )


class DockerBuildError(Exception):
    """Raised when a Docker image fails to build"""


class ImageNotFoundError(Exception):
    """
    Raised when attempting to create an image using a tag or ID that does not
    exist.
    """

    def __init__(self, tag_or_id: str):
        """
        Raise this exception when unable to find an image.

        Parameters
        ----------
        tag_or_id : str
            The tag or ID of the image.
        """
        self.tag_or_id = tag_or_id
        super().__init__(f'Docker image "{tag_or_id}" not found.')


class TestFailedError(Exception):
    """Raised when a test fails."""

    def __init__(self, message: str = ""):
        super().__init__(message)
