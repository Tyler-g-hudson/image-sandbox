from pytest import raises

from docker_cli import Dockerfile
from docker_cli._docker_github import github_checkout_dockerfile

from .utils import rough_dockerfile_validity_check


def test_github_dockerfile():
    """Performs a rough validity check of the GitHub dockerfile"""
    dockerfile: Dockerfile = github_checkout_dockerfile(
        github_repo="abc/def", repo_branch="ghi"
    )
    rough_dockerfile_validity_check(dockerfile=dockerfile.full_dockerfile(parent="a"))


def test_github_dockerfile_error():
    """Ensures that the github checkout dockerfile raises an error when given a bad
    name."""
    with raises(ValueError):
        github_checkout_dockerfile(
            github_repo="abc", repo_branch="ghi"
        )
