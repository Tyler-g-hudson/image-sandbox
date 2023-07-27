from textwrap import dedent
from typing import Iterable, List, Tuple

from ._docker_mamba import micromamba_docker_lines


def git_clone_dockerfile(
    git_repo: str,
    repo_branch: str = "",
    git_url: str = "https://github.com",
    folder_name: str = "repo",
) -> Tuple[str, str]:
    """_summary_

    Parameters
    ----------
    git_repo : str
        The user and name of the git repostiory.
    repo_branch : str, optional
        The name of the branch to checkout. Defaults to "".
    git_url : _type_, optional
        The URL holding the git repository. Defaults to "https://github.com".
    folder_name : str, optional
        The name of the folder to store the repository in. Defaults to "repo".

    Returns
    -------
    header : str
        The generated dockerfile header.
    body : str
        The generated dockerfile body.
    """

    instruction: Iterable[str] = git_clone_command(
        git_repo=git_repo,
        repo_branch=repo_branch,
        git_url=git_url,
        target_location=folder_name,
    ) + ["&&", "rm", "-rf", f"/{folder_name}/.git*"]

    # Dockerfile preparation:
    # Prepare the repository file, ensure proper ownership and permissions.
    body = (
        dedent(
            f"""
        USER root

        RUN mkdir /{folder_name}
        RUN chown -R $MAMBA_USER_ID:$MAMBA_USER_GID /{folder_name}
        RUN chmod -R 755 /{folder_name}

    """
        ).strip()
        + "\n"
    )

    # Activate Micromamba
    body += micromamba_docker_lines() + "\n"

    # Add the git repo, move workdir to it, and change user back to default
    body += (
        dedent(
            f"""
        ADD {git_url}/{git_repo}.git /{folder_name}/
        # RUN {' '. join(instruction)}

        WORKDIR /{folder_name}/
        USER $DEFAULT_USER
    """
        ).strip()
        + "\n"
    )

    header = "# syntax=docker/dockerfile:1-labs"
    # Return the generated body plus a header
    return header, body


def git_clone_command(
    git_repo: str,
    repo_branch: str = "",
    git_url: str = "https://github.com/",
    target_location: str = ".",
) -> List[str]:
    instruction = ["git", "clone"]
    if repo_branch != "":
        instruction.append(f"--branch={repo_branch}")

    instruction += [f"{git_url}{git_repo}.git", target_location]
    return instruction
