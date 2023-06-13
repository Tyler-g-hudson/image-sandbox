import argparse

from .._defaults import universal_tag_prefix


def add_tag_argument(parser: argparse.ArgumentParser, default: str) -> None:
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
        f'with "{prefix}-".',
    )


# Use a custom help message formatter to improve readability by increasing the
# indentation of parameter descriptions to accommodate longer parameter names.
# This formatter also includes argument defaults automatically in the help string.
def help_formatter(prog):
    return argparse.ArgumentDefaultsHelpFormatter(prog, max_help_position=60)
