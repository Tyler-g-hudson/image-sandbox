import os
from textwrap import dedent
from typing import Union

from ._dockerfile import Dockerfile


def distrib_dockerfile(
    source_tag: str,
    source_path: Union[os.PathLike[str], str],
    distrib_path: Union[os.PathLike[str], str]
) -> Dockerfile:
    """
    Returns a dockerfile for a distributable build.

    Parameters
    ----------
    source_tag : str
        The tag of the image on which the project is installed.
    source_path : os.PathLike[str]
        The installation path of the project on the source image.
    distrib_path : os.PathLike[str]
        The desired installation path on the distributable image.

    Returns
    -------
    Dockerfile
        The generated dockerfile.
    """
    header = f"FROM {source_tag} as source"
    body = dedent(f"""
        USER root

        COPY --from=source {source_path} {distrib_path}

        USER $DEFAULT_USER
        WORKDIR /
        """).strip()

    return Dockerfile(header=header, body=body)
