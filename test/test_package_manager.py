from typing import List

from pytest import mark

from wigwam import Image
from wigwam._package_manager import PackageManager
from wigwam._utils import _package_manager_check


@mark.images
def test_generate_install_command(init_image: Image):
    """
    Installs and checks for a package using the package manager.

    XXX: This test takes a long time to run.

    Parameters
    ----------
    init_image : Image
        The image to test on, already pre-configured.
    """
    pkg_manager: PackageManager = _package_manager_check(init_image)

    # since Yum and Apt-Get have their own package names, this messy little
    # implementation detail (or something analogous) is necessary.
    target: List[str] = {"yum": ["python39-pip"], "apt-get": ["python3-pip"]}[
        pkg_manager.name
    ]

    install_cmd = pkg_manager.generate_install_command(targets=target, clean=True)
    test_cmd = "pip3 -v"

    # Yum and Apt-Get will give DIFFERENT ERROR CODES (100 or 2) on failure.
    init_image.run(" && ".join([install_cmd, test_cmd]))


@mark.images
def unused_test_generate_package_command():
    """Problem: Package commands like wget and dpkg are very idiosyncratic and it's
    hard to find ones that don't have dependencies.

    The former problem is workable but the latter doesn't seem to be.

    Maybe pre-install some dependencies first and then use the package command?

    Not a high priority but could be worth it in the end."""
    pass


@mark.images
def test_generate_configure_command(image_id: str):
    """
    Tests the configure command generation on an image.

    Parameters
    ----------
    image_id : str
        The ID of a sample image.
    """
    img: Image = Image(image_id)
    package_mgr: PackageManager = _package_manager_check(img)
    config_cmd: str = str(package_mgr.generate_configure_command())

    # Not too much to check here, just run the command and make sure it doesn't break
    # Theoretically, ensuring that an install command after this doesn't break would
    # test it; I'm not sure how to do this without it taking disruptively long as is the
    # problem with the install_command test.
    img.run(config_cmd)
