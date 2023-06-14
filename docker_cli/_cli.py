import argparse
import sys
import textwrap
from typing import Sequence

from ._utils import universal_tag_prefix
from .commands import dropin, make_lockfile, remove
from .setup_commands import (
    setup_all,
    setup_conda_add,
    setup_conda_dev,
    setup_conda_runtime,
    setup_cuda_dev,
    setup_cuda_runtime,
    setup_init,
)


def setup_parser() -> argparse.ArgumentParser:
    """
    Create a top-level argument parser.

    Returns
    -------
    argparse.ArgumentParser
        The parser.
    """
    prefix = universal_tag_prefix()

    def help_formatter(prog):
        return argparse.HelpFormatter(prog, max_help_position=60)

    parser = argparse.ArgumentParser(prog=__package__, formatter_class=help_formatter)

    # Additional parsers for shared commands
    setup_parse = argparse.ArgumentParser(add_help=False)
    setup_parse.add_argument(
        "--base",
        "-b",
        type=str,
        required=True,
        help="The name of the base Docker image.",
    )

    no_cache_parse = argparse.ArgumentParser(add_help=False)
    no_cache_parse.add_argument(
        "--no-cache",
        action="store_true",
        help="Run Docker build with no cache if used.",
    )

    cuda_run_parse = argparse.ArgumentParser(add_help=False)
    cuda_run_parse.add_argument(
        "--cuda-version",
        "-c",
        default="11.4",
        type=str,
        help='The CUDA version. Default: "11.4"',
        metavar="VERSION",
    )
    cuda_run_parse.add_argument(
        "--cuda-repo",
        default="rhel8",
        type=str,
        help="The name of the CUDA repository for this distro "
        '(e.g. "rhel8", "ubuntu2004".) Default: "rhel8"',
        metavar="REPO_NAME",
    )

    conda_parse = argparse.ArgumentParser(add_help=False)
    conda_parse.add_argument(
        "--env-file",
        default="spec-file.txt",
        type=str,
        help='The location of the spec-file. Default: "spec-file.txt"',
    )

    # Add arguments
    subparsers = parser.add_subparsers(dest="command")

    setup_parser = subparsers.add_parser(
        "setup", help="Docker image setup commands.", formatter_class=help_formatter
    )

    setup_subparsers = setup_parser.add_subparsers(dest="setup_subcommand")

    setup_all_parser = setup_subparsers.add_parser(
        "all",
        parents=[cuda_run_parse, no_cache_parse],
        help="Set up the full Docker image stack.",
        formatter_class=help_formatter,
    )
    setup_all_parser.add_argument(
        "--tag",
        "-t",
        default="setup",
        type=str,
        help="The sub-prefix of the Docker images to be created. Generated images will "
        f'have tags: "{prefix}-[TAG]-*". Default: "setup"',
    )
    setup_all_parser.add_argument(
        "--base",
        "-b",
        default="oraclelinux:8.4",
        type=str,
        help='The name of the parent Docker image. Default: "oraclelinux:8.4"',
    )
    setup_all_parser.add_argument(
        "--runtime-env-file",
        default="runtime-spec-file.txt",
        type=str,
        help='The location of the runtime spec-file. Default: "runtime-spec-file.txt"',
    )
    setup_all_parser.add_argument(
        "--dev-env-file",
        default="dev-spec-file.txt",
        type=str,
        help='The location of the dev spec-file. Default: "dev-spec-file.txt"',
    )

    setup_init_parser = setup_subparsers.add_parser(
        "init",
        parents=[no_cache_parse],
        help="Set up the configuration image.",
        formatter_class=help_formatter,
    )
    setup_init_parser.add_argument(
        "--base",
        "-b",
        default="oraclelinux:8.4",
        type=str,
        required=True,
        help='The name of the parent Docker image. Default: "oraclelinux:8.4"',
    )
    _add_tag_argument(parser=setup_init_parser, default="init")

    setup_cuda_parser = setup_subparsers.add_parser(
        "cuda",
        help="Set up a CUDA image. Designate dev or runtime.",
        formatter_class=help_formatter,
    )

    cuda_subparsers = setup_cuda_parser.add_subparsers(dest="cuda_subcommand")
    setup_cuda_runtime_parser = cuda_subparsers.add_parser(
        "runtime",
        parents=[setup_parse, cuda_run_parse, no_cache_parse],
        help="Set up the CUDA runtime image.",
        formatter_class=help_formatter,
    )
    _add_tag_argument(parser=setup_cuda_runtime_parser, default="cuda-runtime")

    setup_cuda_dev_parser = cuda_subparsers.add_parser(
        "dev",
        parents=[setup_parse, no_cache_parse],
        help="Set up the CUDA dev image.",
        formatter_class=help_formatter,
    )
    _add_tag_argument(parser=setup_cuda_dev_parser, default="cuda-dev")

    setup_conda_parser = setup_subparsers.add_parser(
        "conda",
        help="Set up the runtime environment image. " "Designate dev or runtime.",
        formatter_class=help_formatter,
    )

    conda_subparsers = setup_conda_parser.add_subparsers(dest="conda_subcommand")
    setup_conda_runtime_parser = conda_subparsers.add_parser(
        "runtime",
        parents=[setup_parse, conda_parse, no_cache_parse],
        help="Set up the runtime conda environment image",
        formatter_class=help_formatter,
    )
    _add_tag_argument(parser=setup_conda_runtime_parser, default="conda-runtime")

    setup_conda_dev_parser = conda_subparsers.add_parser(
        "dev",
        parents=[setup_parse, conda_parse, no_cache_parse],
        help="Set up the runtime conda environment image",
        formatter_class=help_formatter,
    )
    _add_tag_argument(parser=setup_conda_dev_parser, default="conda-dev")

    # This command has been commented out due to buggy implementation, but may
    # later be recovered once a better implementation has been found.
    """setup_conda_add_parser = conda_subparsers.add_parser(
        "add",
        parents=[setup_parse, no_cache_parse],
        help="Set up the runtime conda environment image",
        formatter_class=help_formatter,
    )
    setup_conda_add_parser.add_argument(
        "packages",
        nargs="+",
        help="A list of conda packages to add to the environment.",
    )
    setup_conda_add_parser.add_argument(
        "--channels",
        "-c",
        nargs="+",
        help="A list of channels to look for conda packages in.",
    )
    _add_tag_argument(parser=setup_conda_add_parser, default="conda-pkgs")"""

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
        "--quiet", "-q", action="store_true", help="Run the removal quietly."
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
        help="The name of the environment used to create the dockerfile. Defaults to "
        '"base".',
    )

    return parser


def main(args: Sequence[str] = sys.argv[1:]):
    parser = setup_parser()
    args_parsed = parser.parse_args(args)
    command: str = args_parsed.command
    if command is None:
        insufficient_subcommands_message(
            subcommand="The docker_cli program", command_str="docker_cli"
        )
    command = command.lower()
    del args_parsed.command
    if command == "setup":
        setup_subcommand: str = args_parsed.setup_subcommand
        if setup_subcommand is None:
            insufficient_subcommands_message(
                subcommand='"setup"', command_str="docker_cli setup"
            )
        setup_subcommand = setup_subcommand.lower()
        del args_parsed.setup_subcommand
        if setup_subcommand == "all":
            images = setup_all(**vars(args_parsed))
            print("IMAGES GENERATED:")
            for image_tag in images:
                print(textwrap.indent(image_tag, "\t"))
        elif setup_subcommand == "init":
            setup_init(**vars(args_parsed))
        elif setup_subcommand == "cuda":
            cuda_subcommand = args_parsed.cuda_subcommand
            if cuda_subcommand is None:
                insufficient_subcommands_message(
                    subcommand='"setup cuda"', command_str="docker_cli setup cuda"
                )
            cuda_subcommand = cuda_subcommand.lower()
            del args_parsed.cuda_subcommand
            if cuda_subcommand == "runtime":
                setup_cuda_runtime(**vars(args_parsed))
            elif cuda_subcommand == "dev":
                setup_cuda_dev(**vars(args_parsed))
        elif setup_subcommand == "conda":
            conda_subcommand = args_parsed.conda_subcommand
            if conda_subcommand is None:
                insufficient_subcommands_message(
                    subcommand='"setup env"', command_str="docker_cli setup env"
                )
            del args_parsed.conda_subcommand
            if conda_subcommand == "runtime":
                setup_conda_runtime(**vars(args_parsed))
            elif conda_subcommand == "dev":
                setup_conda_dev(**vars(args_parsed))
            elif conda_subcommand == "add":
                setup_conda_add(**vars(args_parsed))
        else:
            insufficient_subcommands_message(
                subcommand='"docker_cli"', command_str="docker_cli"
            )
    elif command == "dropin":
        dropin(**vars(args_parsed))
    elif command == "remove":
        remove(**vars(args_parsed))
    elif command == "lockfile":
        make_lockfile(**vars(args_parsed))


def insufficient_subcommands_message(subcommand: str, command_str: str) -> None:
    """
    Print an error string when an incomplete set of commands is given.

    Parameters
    ----------
    subcommand : str
        The subcommand name.
    command_str : str
        The full command string up to the subcommand (e.g. "docker_cli build")
    """
    print(f"\n  {subcommand} requires further subcommands!")
    print(f'  For more info: "{command_str} -h"\n')
    exit(1)


def _add_tag_argument(parser: argparse.ArgumentParser, default: str) -> None:
    """
    Adds a tag argument to a parser with a given default.

    Parameters
    ----------
    parser : argparse.ArgumentParser
        The parser.
    default : str
        The default tag name.
    """
    prefix = universal_tag_prefix()
    parser.add_argument(
        "--tag",
        "-t",
        default=default,
        type=str,
        help="The tag of the Docker image to be created. This tag will be prefixed "
        f'with "{prefix}-". Default: "{default}"',
    )
