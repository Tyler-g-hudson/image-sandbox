from __future__ import annotations

import argparse

from ..commands import dropin, make_lockfile, remove, test
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
        "--force", "-f", action="store_true", help="Force the image removal."
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
        help=f"Ignore the {prefix} prefix. CAUTION: Using wildcards with this "
        "argument can result in unintended removal of Docker images. Use "
        "with caution.",
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
