import os
import sys
from pathlib import Path

from docker_cli.commands import remove

# This import is necessary for the fixtures to be visible to the test files.
# Importing fixtures directly into a file can cause some non-trivial problems with
# dependencies, since a fixture that depends on other fixtures will not automatically
# import them.
from .fixtures import *
from .utils import image_tag_prefix


def pytest_sessionstart(session):
    # Navigate to the test folder path in order to make use of tests that require for
    # a dockerfile to be in the local directory, regardless of where tests are being
    # run from.
    os.chdir(Path(__file__).parent)

    # Set the system to look for files in the repository root path so it can see the
    # docker_cli module without having to install it.
    sys.path.insert(0, str(Path(__file__).parents[1]))


def pytest_sessionfinish(session, exitstatus):
    # session.config.workerinput is "None" in the master session.
    # This means that this line of code will only run once in pytest-xdist,
    # when all other test sessions have completed.
    if getattr(session.config, "workerinput", None) is None:
        remove(tags=[f"{image_tag_prefix()}*"], force=True, quiet=True)
