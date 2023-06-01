from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class BindMount:
    """A Docker bind mount."""

    src: str | os.PathLike[str]
    """
    str or os.PathLike[str] :
        The path to the file or directory on the Docker daemon host.
    """

    dst: str | os.PathLike[str]
    """
    str or os.PathLike[str] :
        The path where the file or directory is mounted in the container.
    """

    permissions: str = "rw"
    """str : The bind mount permissions -- 'ro' for readonly, 'rw' for read/write."""

    def __post_init__(self):
        if self.permissions not in ("ro", "rw"):
            raise ValueError(
                f"permissions must be 'ro' or 'rw', got {self.permissions!r}"
            )

    def mount_string(self) -> str:
        """Returns a string describing the mount."""
        return f"{self.src}:{self.dst}:{self.permissions}"
