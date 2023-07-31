from __future__ import annotations

import argparse

from ..commands import dropin, make_lockfile, remove, test, workflow
from ._utils import help_formatter


def init_util_parsers(subparsers: argparse._SubParsersAction, prefix: str) -> None:
    """
    Create a top-level argument parser.

    Parameters
    -------
    parser : argparse.ArgumentParser
        The parser to add setup commands to.
    prefix : str
        The image tag prefix.
    """

    dropin_parser = subparsers.add_parser(
        "dropin", help="Start a drop-in session.", formatter_class=help_formatter
    )
    dropin_parser.add_argument(
        "tag", metavar="IMAGE_TAG", type=str, help="The tag or ID of the desired image."
    )

    remove_parser = subparsers.add_parser(
        "remove",
        help=f"Remove all Docker images beginning with {prefix}-[IMAGE_TAG] for each "
        "image tag provided.",
        formatter_class=help_formatter,
    )
    remove_parser.add_argument(
        "--force",
        "-f",
        action="store_true",
        help=f"Ignore the {prefix} prefix. CAUTION: Using wildcards with this "
        "argument can result in unintended removal of docker images. Use "
        "with caution.",
    )
    remove_parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Run the removal with verbose output and error messages.",
    )
    remove_parser.add_argument(
        "--ignore-prefix",
        action="store_true",
        help=f'An image tag or wildcard. Will be prefixed with "{prefix}" '
        "if not already prefixed. Wildcard characters * and ? should be escaped "
        "with backslashes as \\* and \\?. Improper use may cause unpredictable "
        "removal behavior due to shell interpretation of wildcards.",
    )
    remove_parser.add_argument(
        "tags",
        metavar="IMAGE_TAG",
        type=str,
        nargs="+",
        help=f"An image tag or wildcard. Will be prefixed with {prefix} "
        "if not already prefixed.",
    )

    lockfile_parser = subparsers.add_parser(
        "lockfile",
        help="Produce a lockfile for the image.",
        formatter_class=help_formatter,
    )
    lockfile_parser.add_argument(
        "--tag",
        "-t",
        metavar="IMAGE_TAG",
        type=str,
        help="The tag or ID of the desired image.",
    )
    lockfile_parser.add_argument(
        "--file",
        "-f",
        metavar="FILENAME",
        type=str,
        help="The name of the output file.",
    )
    lockfile_parser.add_argument(
        "--env-name",
        metavar="ENVIRONMENT",
        type=str,
        default="base",
        help="The name of the environment used to create the Dockerfile.",
    )

    workflow_parser = subparsers.add_parser(
        "workflow",
        help="Run workflow tests on an image.",
        formatter_class=help_formatter,
    )
    workflow_parser.add_argument(
        "workflow_name", metavar="WORKFLOW", type=str, help="The name of the workflow."
    )
    workflow_parser.add_argument(
        "test",
        metavar="TEST",
        type=str,
        help="The name or alias of the test on the given workflow.",
    )
    workflow_parser.add_argument(
        "--image",
        metavar="IMAGE_TAG",
        type=str,
        default="isce3",
        help='The tag or ID of the image used for testing. Defaults to "isce3".',
    )
    workflow_parser.add_argument(
        "--output-dir",
        "-o",
        type=str,
        required=True,
        help="The location to mount output files to.",
    )
    workflow_parser.add_argument(
        "--test-file",
        type=str,
        default="workflowtests.json",
        help="The location of the test info data file. Defaults to workflowtests.json.",
    )
    workflow_parser.add_argument(
        "--input-dirs",
        "-i",
        nargs="+",
        default=[],
        help="The directory of the test input repositories, "
        "in [PATH] or [LABEL]:[PATH] format.",
    )
    workflow_parser.add_argument(
        "--cache-dirs",
        "-c",
        nargs="+",
        default=[],
        help="The location of a file cache.",
    )
    workflow_parser.add_argument(
        "--scratch-dir",
        "-s",
        type=str,
        default=None,
        help="The location to mount scratch files to, if desired.",
    )

    return


def run_util(args: argparse.Namespace, command: str) -> None:
    if command == "dropin":
        dropin(**vars(args))
    elif command == "remove":
        remove(**vars(args))
    elif command == "lockfile":
        make_lockfile(**vars(args))
    elif command == "test":
        test(**vars(args))
    elif command == "workflow":
        workflow(**vars(args))
