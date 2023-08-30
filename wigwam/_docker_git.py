from textwrap import dedent

from ._docker_mamba import micromamba_docker_lines


def git_clone_dockerfile(
    base: str,
    git_repo: str,
    repo_branch: str = "",  # currently unused. # type: ignore
    git_url: str = "https://github.com",
    folder_name: str = "repo",
) -> str:
    """
    Returns a dockerfile-formatted string with instructions to clone a git repository.

    NOTE for reviewers: Branch checkout is currently disabled.
    Adding branch functionality with this method would require including git in the
    image if it is not already there, and also pulling in the `.git` info which I
    believe the ADD command does not include by default. The options as I see them are:
    -   Remove branching altogether, if acceptable
    -   Add git and the `.git` folder to the images
    -   Use a different method of adding git repositories to images.

    Parameters
    ----------
    base : str
        The base image tag.
    git_repo : str
        The user and name of the git repostiory.
    repo_branch : str, optional
        The name of the branch to checkout. Defaults to "". Currently disabled.
    git_url : _type_, optional
        The URL to get the git repository from. Defaults to "https://github.com/".
    folder_name : str, optional
        The name of the folder to store the repository in. Defaults to "repo".

    Returns
    -------
    header : str
        The generated dockerfile header.
    body : str
        The generated dockerfile body.
    """

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

        WORKDIR /{folder_name}/
        USER $DEFAULT_USER
    """
        ).strip()
        + "\n"
    )

    # This header enables the dockerfile to use the ADD command for a git repo.
    # REVIEWERS: I believe this is an experimental syntax and may not be stable.
    header = "# syntax=docker/dockerfile:1-labs"

    # Return the generated body plus a header
    return f"{header}\n\nFROM{base}\n\n{body}"


def git_clone_command(
    git_repo: str,
    repo_branch: str = "",
    git_url: str = "https://github.com/",
    target_location: str = ".",
) -> str:
    """
    Returns a shell command to clone a git repository using HTTPS.

    NOTE: This function is currently unused. The best method to acquire a git repository
    is currently unclear, so it is in the codebase as an alternative to the ADD method
    currently in use.

    Parameters
    ----------
    git_repo : str
        The user and name of the git repostiory.
    repo_branch : str, optional
        The name of the branch to checkout. Defaults to "".
    git_url : str, optional
        The URL to get the git repository from. Defaults to "https://github.com/".
    target_location : str, optional
        The name of the folder to store the repository in. Defaults to ".".

    Returns
    -------
    str
        the command.
    """
    instruction = "git clone"
    if repo_branch != "":
        instruction += f" --branch={repo_branch}"

    instruction += f" {git_url}{git_repo}.git {target_location}"
    return instruction
