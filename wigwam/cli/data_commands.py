import argparse
from pathlib import Path

from .._defaults import default_workflowdata_path, default_workflowtest_path
from ..data_commands import data_fetch, data_search
from ._utils import help_formatter


def init_data_parsers(subparsers: argparse._SubParsersAction) -> None:
    """
    Augment an argument parser with setup commands.

    Parameters
    -------
    parser : argparse.ArgumentParser
        The parser to add setup commands to.
    prefix : str
        The image tag prefix.
    """
    search_params = argparse.ArgumentParser(add_help=False)
    search_params.add_argument(
        "--data-file",
        "-f",
        type=Path,
        default=default_workflowdata_path(),
        metavar="FILENAME",
        help="The filename of the repository metadata file.",
    )
    search_params.add_argument(
        "--tags",
        "-t",
        nargs="+",
        action="append",
        default=[],
        metavar="TAG",
        help="A set of data repository tags. Can be used multiple times.",
    )
    search_params.add_argument(
        "--names",
        "-n",
        nargs="+",
        default=[],
        metavar="NAME",
        help="A set of data repository names.",
    )
    search_params.add_argument(
        "--all",
        "-a",
        action="store_true",
        default=False,
        help="If used, get all repositories. Other search parameters will be ignored.",
    )

    data_parser = subparsers.add_parser(
        "data", help="Perform data operations.", formatter_class=help_formatter
    )
    data_subparsers = data_parser.add_subparsers(dest="data_subcommand")

    search_parser = data_subparsers.add_parser(
        "search",
        parents=[search_params],
        help="Search a file for repository metadata.",
        formatter_class=help_formatter,
    )
    search_parser.add_argument(
        "--fields",
        nargs="+",
        default=[],
        metavar="FIELD",
        help="The metadata fields to be returned.",
    )

    fetch_parser = data_subparsers.add_parser(
        "fetch",
        parents=[search_params],
        help="Acquire repository data.",
        formatter_class=help_formatter,
    )
    fetch_parser.add_argument(
        "--tests",
        nargs="+",
        metavar="WORKFLOW:TEST",
        help="A set of tests to download the inputs for.",
    )
    fetch_parser.add_argument(
        "--test_file",
        type=Path,
        default=default_workflowtest_path(),
        metavar="TEST_FILE",
        help="The location of the workflow test description file.",
    )
    fetch_parser.add_argument(
        "--cache",
        "-c",
        type=Path,
        default=Path("./cache"),
        metavar="CACHE_LOCATION",
        required=True,
        help="The location to cache the repository to.",
    )
    fetch_parser.add_argument(
        "--no-cache",
        action="store_true",
        default=False,
        help="If used, delete and reinstall all requested items.",
    )
    fetch_parser.add_argument(
        "--verbose-stderr",
        action="store_true",
        default=False,
        help="If used, print verbose error output.",
    )


def run_data(args: argparse.Namespace) -> None:
    data_subcommand = args.data_subcommand
    del args.data_subcommand
    if data_subcommand == "search":
        data_search(**vars(args))
    elif data_subcommand == "fetch":
        data_fetch(**vars(args))
