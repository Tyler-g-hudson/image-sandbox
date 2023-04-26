import re
from textwrap import dedent

from ._docker_mamba import micromamba_docker_lines


def github_checkout_dockerfile(
    github_repo: str, repo_branch: str = "", git_url: str = "https://github.com"
) -> str:
    """
    Generates a dockerfile that has instructions to checkout a github repo.

    Parameters
    ----------
    github_repo : str
        The name of the github repo, in [USER]/[REPO_NAME] format.
    repo_branch : str, optional
        The branch to be checked out, if not Master. Defaults to "".

    Returns
    -------
    body : str
        The generated dockerfile body.
    """
    # Check that the repo pattern
    github_repo_pattern = re.compile(
        pattern=r"^(?P<user>[a-zA-Z0-9-]+)\/(?P<repo>[a-zA-Z0-9-]+)$", flags=re.I
    )
    github_repo_match = re.match(github_repo_pattern, github_repo)
    if not github_repo_match:
        raise ValueError(
            f"Malformed GitHub repo name: {github_repo} - "
            "Please use form [USER]/[REPO_NAME]."
        )
    repo_match_groups = github_repo_match.groupdict()
    repo_name = repo_match_groups["repo"]
    instruction = ["RUN", "git", "clone"]
    if repo_branch != "":
        instruction.extend(["--branch", repo_branch])

    url: str = git_url if git_url.endswith("/") else git_url + "/"
    instruction.extend([f"{url}{github_repo}"])

    body = (
        dedent(
            f"""
        USER root
        RUN mkdir /{repo_name}
        RUN chmod 777 /{repo_name}"""
        ).strip()
        + "\n"
        + micromamba_docker_lines()
        + "\n"
        + dedent(
            f"""
        {' '. join(instruction)}

        WORKDIR /{repo_name}/
        USER $DEFAULT_USER
    """
        ).strip()
        + "\n"
    )

    return body
