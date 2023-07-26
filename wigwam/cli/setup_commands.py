import argparse
from pathlib import Path

from ..setup_commands import (
    setup_all,
    setup_conda_dev,
    setup_conda_runtime,
    setup_cuda_dev,
    setup_cuda_runtime,
    setup_init,
)
from ._utils import add_tag_argument, help_formatter
from .defaults import default_dev_reqs_file, default_run_reqs_file


def init_setup_parsers(subparsers: argparse._SubParsersAction, prefix: str) -> None:
    """
    Augment an argument parser with setup commands.

    Parameters
    -------
    parser : argparse.ArgumentParser
        The parser to add setup commands to.
    prefix : str
        The image tag prefix.
    """

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
        help="The CUDA version.",
        metavar="VERSION",
    )
    cuda_run_parse.add_argument(
        "--cuda-repo",
        default="rhel8",
        type=str,
        help="The name of the CUDA repository for this distro "
        '(e.g. "rhel8", "ubuntu2004".)',
        metavar="REPO_NAME",
    )

    setup_parser = subparsers.add_parser(
        "setup", help="Docker image setup commands.", formatter_class=help_formatter
    )

    setup_subparsers = setup_parser.add_subparsers(
        dest="setup_subcommand", required=True
    )

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
        f'have tags: "{prefix}-[TAG]-*".',
    )
    setup_all_parser.add_argument(
        "--base",
        "-b",
        default="oraclelinux:8.4",
        type=str,
        help="The name of the parent Docker image.",
    )
    setup_all_parser.add_argument(
        "--runtime-env-file",
        default=default_run_reqs_file,
        type=Path,
        help="The location of the runtime requirements file. Can be a pip-style "
        "requirements.txt file, a conda-style environment.yml file, or a lockfile.",
    )
    setup_all_parser.add_argument(
        "--dev-env-file",
        default=default_dev_reqs_file,
        type=Path,
        help="The location of the dev requirements file. Can be a pip-style "
        "requirements.txt file, a conda-style environment.yml file, or a lockfile.",
    )
    setup_all_parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        default=False,
        help="If used, output informational messages upon completion.",
    )
    setup_all_parser.add_argument(
        "--no-cuda",
        action="store_true",
        default=False,
        help="If used, skip CUDA image generation steps.",
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
        help="The name of the parent Docker image.",
    )
    add_tag_argument(parser=setup_init_parser, default="init")

    setup_cuda_parser = setup_subparsers.add_parser(
        "cuda",
        help="Set up a CUDA image. Designate dev or runtime.",
        formatter_class=help_formatter,
    )

    cuda_subparsers = setup_cuda_parser.add_subparsers(
        dest="cuda_subcommand", required=True
    )
    setup_cuda_runtime_parser = cuda_subparsers.add_parser(
        "runtime",
        parents=[setup_parse, cuda_run_parse, no_cache_parse],
        help="Set up the CUDA runtime image.",
        formatter_class=help_formatter,
    )
    add_tag_argument(parser=setup_cuda_runtime_parser, default="cuda-runtime")

    setup_cuda_dev_parser = cuda_subparsers.add_parser(
        "dev",
        parents=[setup_parse, no_cache_parse],
        help="Set up the CUDA dev image.",
        formatter_class=help_formatter,
    )
    setup_cuda_dev_parser.add_argument(
        "--cuda-version",
        "-c",
        default="11.4",
        type=str,
        help="The CUDA version.",
        metavar="VERSION",
    )
    add_tag_argument(parser=setup_cuda_dev_parser, default="cuda-dev")

    setup_conda_parser = setup_subparsers.add_parser(
        "conda",
        help="Set up a conda environment image. Designate dev or runtime.",
        formatter_class=help_formatter,
    )

    conda_subparsers = setup_conda_parser.add_subparsers(
        dest="conda_subcommand", required=True
    )
    setup_conda_runtime_parser = conda_subparsers.add_parser(
        "runtime",
        parents=[setup_parse, no_cache_parse],
        help="Set up the runtime conda environment image",
        formatter_class=help_formatter,
    )
    setup_conda_runtime_parser.add_argument(
        "--env-file",
        default=default_run_reqs_file,
        type=Path,
        help="The location of the runtime requirements file. Can be a pip-style "
        "requirements.txt file, a conda-style environment.yml file, or a lockfile.",
    )
    add_tag_argument(parser=setup_conda_runtime_parser, default="conda-runtime")

    setup_conda_dev_parser = conda_subparsers.add_parser(
        "dev",
        parents=[setup_parse, no_cache_parse],
        help="Set up the dev conda environment image",
        formatter_class=help_formatter,
    )
    setup_conda_dev_parser.add_argument(
        "--env-file",
        default=default_dev_reqs_file,
        type=Path,
        help="The location of the dev requirements file. Can be a pip-style "
        "requirements.txt file, a conda-style environment.yml file, or a lockfile.",
    )
    add_tag_argument(parser=setup_conda_dev_parser, default="conda-dev")


def run_setup(args: argparse.Namespace) -> None:
    setup_subcommand: str = args.setup_subcommand
    del args.setup_subcommand
    if setup_subcommand == "all":
        setup_all(**vars(args))
    elif setup_subcommand == "init":
        setup_init(**vars(args))
    elif setup_subcommand == "cuda":
        cuda_subcommand = args.cuda_subcommand
        del args.cuda_subcommand
        if cuda_subcommand == "runtime":
            setup_cuda_runtime(**vars(args))
        elif cuda_subcommand == "dev":
            setup_cuda_dev(**vars(args))
    elif setup_subcommand == "conda":
        conda_subcommand = args.conda_subcommand
        del args.conda_subcommand
        if conda_subcommand == "runtime":
            setup_conda_runtime(**vars(args))
        elif conda_subcommand == "dev":
            setup_conda_dev(**vars(args))
