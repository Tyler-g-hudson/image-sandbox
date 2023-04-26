from __future__ import annotations

import os
from textwrap import dedent
from typing import Tuple


def distrib_dockerfile(
    source_tag: str,
    source_path: os.PathLike[str] | str,
    distrib_path: os.PathLike[str] | str,
) -> Tuple[str, str]:
    """
    Returns a dockerfile for a distributable build.

    Parameters
    ----------
    source_tag : str
        The tag of the image on which the project is installed.
    source_path : os.PathLike[str] or str
        The installation path of the project on the source image.
    distrib_path : os.PathLike[str] or str
        The desired installation path on the distributable image.

    Returns
    -------
    header
        The generated dockerfile header.
    body
        The generated dockerfile body.
    """
    header = f"FROM {source_tag} as source"
    body = dedent(
        f"""
        USER root

        COPY --from=source {source_path} {distrib_path}

        USER $DEFAULT_USER
        WORKDIR /
        """
    ).strip()

    return header, body
