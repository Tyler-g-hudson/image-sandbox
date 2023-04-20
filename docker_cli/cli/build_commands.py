import argparse
from typing import List

from ..commands import (
    build_all,
    clone,
    distributable,
    configure,
    compile,
    install,
    )
from ._utils import add_tag_argument, help_formatter


def init_build_parsers(subparsers: argparse._SubParsersAction, prefix: str) -> None:
    """
    Augment an argument parser with build commands.

    Parameters
    -------
    parser : argparse.ArgumentParser
        The parser to add setup commands to.
    prefix : str
        The image tag prefix.
    """
    clone_params = argparse.ArgumentParser(add_help=False)
    clone_params.add_argument(
        "--repo", type=str, metavar="GIT_REPO", default="isce-framework/isce3",
        help="The name of the GitHub repository to be installed. "
             'Default: "isce-framework/isce3"'
    )
    # This argument currently disabled as this code does not presently support git
    # branches.
    """clone_params.add_argument(
        "--branch", type=str, metavar="REPO_BRANCH", default="",
        help="The name of the branch to checkout. Defaults to \"\"."
    )"""

    build_type_choices = ["Release", "Debug", "RelWithDebInfo", "MinSizeRel"]
    config_params = argparse.ArgumentParser(add_help=False)
    config_params.add_argument(
        "--build-type", type=str, required=True, default="Release",
        metavar="DCMAKE_BUILD_TYPE",
        choices=build_type_choices,
        help="The --DCMAKE_BUILD_TYPE argument for CMAKE. Valid options are: " +
             f"{', '.join(build_type_choices)}. Defaults to \"Release\"."
    )
    config_params.add_argument(
        "--no-cuda", action="store_true", default=False,
        help="If used, the build configuration will not use CUDA."
    )

    setup_parse = argparse.ArgumentParser(add_help=False)
    setup_parse.add_argument(
        "--base",
        "-b",
        type=str,
        required=True,
        help="The name of the base Docker image.",
    )

    clone_parser = subparsers.add_parser(
        "clone", parents=[setup_parse, clone_params],
        help="Set up the GitHub repository image, in [USER]/[REPO_NAME] format.",
        formatter_class=help_formatter
    )
    add_tag_argument(parser=clone_parser, default="repo")

    config_parser = subparsers.add_parser(
        "config", parents=[setup_parse, config_params],
        help="Creates an image with a configured compiler.",
        formatter_class=help_formatter
    )
    add_tag_argument(parser=config_parser, default="configured")

    compile_parser = subparsers.add_parser(
        "compile", parents=[setup_parse],
        help="Creates an image with the project built.",
        formatter_class=help_formatter
    )
    add_tag_argument(parser=compile_parser, default="compiled")

    install_parser = subparsers.add_parser(
        "install", parents=[setup_parse],
        help="Creates an image with the project installed.",
        formatter_class=help_formatter
    )
    add_tag_argument(parser=install_parser, default="installed")

    parser_build_all = subparsers.add_parser(
        "build-all", parents=[setup_parse, config_params],
        help="Performs the complete compilation process, from initial GitHub checkout "
             "to installation.",
        formatter_class=help_formatter
    )
    parser_build_all.add_argument(
        "--base", "-b", type=str, default="setup-mamba-dev",
        help='The name of the parent docker image. Default is "setup-mamba-dev".'
    )
    parser_build_all.add_argument(
        "--tag", "-t", default="build", type=str,
        help='The sub-prefix of the docker images to be created. Generated images will '
        f'have tags fitting "{prefix}-[TAG]-*". Default: "build"'
    )
    parser_build_all.add_argument(
        "--copy-path", "-p", metavar="FILEPATH", type=str, default=None,
        help='The path to be copied to the image. If used, no github image will be '
             'copied. Defaults to None.'
    )

    distrib_parser = subparsers.add_parser(
        "distrib",
        help="Creates a distributable image.",
        formatter_class=help_formatter
    )
    distrib_parser.add_argument(
        "--tag", "-t", default="isce3", type=str,
        help='The complete tag of the docker image to be created. '
             'Default: "isce3"'
    )
    distrib_parser.add_argument(
        "--base", "-b", default="setup-mamba-runtime", type=str,
        help='The complete tag of the docker image to be created. '
             'Default: "setup-mamba-runtime"'
    )
    distrib_parser.add_argument(
        "--source-tag", "-s", default="build-installed", type=str,
        help="The tag or ID of the source image which has the project installed. "
        ' Defaults to "build-installed".'
    )


def build_command_names() -> List[str]:
    """Returns a list of all build command names."""
    return [
        "build-all",
        "insert",
        "clone",
        "config",
        "compile",
        "install",
        "distrib"
    ]


def run_build(args: argparse.Namespace, command: str) -> None:
    if command == "build-all":
        build_all(**vars(args))
    elif command == "clone":
        clone(**vars(args))
    elif command == "config":
        configure(**vars(args))
    elif command == "compile":
        compile(**vars(args))
    elif command == "install":
        install(**vars(args))
    elif command == "distrib":
        distributable(**vars(args))