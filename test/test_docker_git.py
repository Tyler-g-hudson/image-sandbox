from pytest import raises

from docker_cli._docker_git import git_clone_dockerfile

from .utils import rough_dockerfile_validity_check


def test_github_dockerfile():
    """Performs a rough validity check of the GitHub dockerfile"""
    body: str = git_clone_dockerfile(git_repo="abc/def", repo_branch="ghi")

    dockerfile = f"FROM %TEST_BASE%\n\n{body}"
    rough_dockerfile_validity_check(dockerfile=dockerfile)


def test_github_dockerfile_error():
    """Ensures that the github checkout dockerfile raises an error when given a bad
    name."""
    with raises(ValueError):
        git_clone_dockerfile(git_repo="abc", repo_branch="ghi")
