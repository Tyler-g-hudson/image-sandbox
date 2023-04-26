import argparse
import sys
from typing import Sequence

from .._utils import universal_tag_prefix
from ._utils import help_formatter
from .build_commands import build_command_names, init_build_parsers, run_build
from .data_commands import init_data_parsers, run_data
from .setup_commands import init_setup_parsers, run_setup
from .util_commands import init_util_parsers, run_util


def initialize_parser() -> argparse.ArgumentParser:
    """
    Create a top-level argument parser.

    Returns
    -------
    argparse.ArgumentParser
        The parser.
    """
    prefix = universal_tag_prefix()

    parser = argparse.ArgumentParser(prog=__package__, formatter_class=help_formatter)

    # Add arguments
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_setup_parsers(subparsers, prefix)
    init_build_parsers(subparsers, prefix)
    init_data_parsers(subparsers)
    init_util_parsers(subparsers, prefix)

    return parser


def main(args: Sequence[str] = sys.argv[1:]):
    parser = initialize_parser()
    args_parsed = parser.parse_args(args)
    command: str = args_parsed.command
    del args_parsed.command
    if command == "setup":
        run_setup(args_parsed)
    elif command == "data":
        run_data(args_parsed)
    elif command in build_command_names():
        run_build(args_parsed, command)
    else:
        run_util(args_parsed, command)
