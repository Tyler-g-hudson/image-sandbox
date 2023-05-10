from textwrap import dedent
from typing import Iterable, List

from ._docker_mamba import micromamba_docker_lines


def git_clone_dockerfile(
    git_repo: str,
    repo_branch: str = "",
    git_url: str = "https://github.com",
    repo_name: str = "",
) -> str:
    target_folder = "repo" if repo_name == "" else repo_name

    instruction: Iterable[str] = git_clone_command(
        git_repo=git_repo,
        repo_branch=repo_branch,
        git_url=git_url,
        target_location=target_folder,
    ) + ["&&", "rm", "-rf", f"/{target_folder}/.git*"]

    body = (
        dedent(
            f"""
        USER root
        RUN mkdir /{target_folder}
        RUN chmod 777 /{target_folder}"""
        ).strip()
        + "\n"
        + micromamba_docker_lines()
        + "\n"
        + dedent(
            f"""
        ADD {git_url}/{git_repo}.git /{target_folder}/
        # RUN {' '. join(instruction)}

        WORKDIR /{target_folder}/
        USER $DEFAULT_USER
    """
        ).strip()
        + "\n"
    )
    return body


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
