from wigwam._docker_git import git_clone_dockerfile

from .utils import rough_dockerfile_validity_check


def test_git_dockerfile():
    """Performs a rough validity check of the Git dockerfile"""
    header, body = git_clone_dockerfile(git_repo="abc/def", repo_branch="ghi")

    dockerfile = f"{header}\n\nFROM %TEST_BASE%\n\n{body}"
    rough_dockerfile_validity_check(dockerfile=dockerfile)
