import re
from typing import List

from wigwam._utils import generate_random_string, universal_tag_prefix


def image_tag_prefix() -> str:
    """
    The prefix of all image tags used in testing.

    Returns
    -------
    str
        The prefix.
    """
    uni_prefix = universal_tag_prefix()
    return f"{uni_prefix}-pytest"


def generate_tag(name: str) -> str:
    """
    Generates a testing tag name.

    Parameters
    ----------
    name : str
        A specifier for what type of image is being built.

    Returns
    -------
    str
        The tag.
    """
    return f"{image_tag_prefix()}-{name}-{generate_random_string(k=10)}"


def determine_scope(fixture_name, config) -> str:
    """
    Sets the scope of certain fixtures.

    Currently always returns "function." This is because bugs appear if different scopes
    are used. However, in the ideal case, parallel tests would have "function" scope
    while serial tests would have a wider scope like "session" to avoid re-creating
    identical Docker images over and over.

    Parameters
    ----------
    fixture_name
        The name of the fixture.
        NOTE: Do not remove, this is required by pytest.
    config
        A pytest internal object.

    Returns
    -------
    Optional[str]
        The scope name or None.
    """

    # XXX: This uses "function" scope at all times but serial tests would theoretically
    # run faster if they had a wider scope. Presently this is necessary to prevent
    # errors but the whole system would be faster in serial if "session" was used.
    if hasattr(config.option, "numprocesses"):
        if config.option.numprocesses in ["auto", "logical"]:
            return "function"
    return "function"


def remove_docker_image(tag_or_id: str):
    """
    Idiot-proof removal of a Docker image.

    NOTE: currently commented out. Docker images are removed en masse at the end of
    testing.
    This function remains because it would be preferable to use it over removing images
    en masse if the option presents, but currently doing so would be too buggy.

    Added because a missed word in a `Docker image rm` command resulted in difficult
    debugging of a Docker image being produced and not removed by the test suite.
    Best to ensure this is done the same way every time.

    Parameters
    ----------
    tag : str
        The tag or ID of the image.
    """
    # run(split(f"Docker image rm --no-prune {tag_or_id}"))
    pass


def rough_dockerfile_validity_check(dockerfile: str) -> None:
    """
    Performs a coarse check to see if a Dockerfile is valid.

    For the purposes of this check, validity is determined by stripping all comments,
    leading and trailing whitespace lines, and empty lines. Lines ending in backslashes
    are then concatenated together, and each line is checked for an initial instruction.

    This checker does NOT check if anything following the initial instruction name
    is valid, or if the Dockerfile can actually build.

    Parameters
    ----------
    dockerfile : str
        The Dockerfile

    Raises
    ------
    ValueError
    -   If the Dockerfile is empty.
    -   If the Dockerfile does not contain anything but whitespace and comments.
    -   If an ONBUILD instruction appears without any text following it.
    -   If non-commented text is found in the Dockerfile that is not preceded by a
        Dockerfile instruction keyword.
    """
    comment_pattern: re.Pattern = re.compile(
        r"^(?P<instruction>[^#]*)(?P<comment>#.*)?$"
    )

    onbuild_pattern: re.Pattern = re.compile(r"^(?:onbuild\s+)", re.IGNORECASE)
    lines: List[str] = dockerfile.split("\n")
    stripped_lines: List[str] = []

    # Remove comments... Wait, no, not this one!
    # Also remove the ONBUILD instruction or raise an exception if it's not followed
    # by something.
    for line in lines:
        comment_results = re.match(comment_pattern, line)
        assert isinstance(comment_results, re.Match)
        comment_groups = comment_results.groupdict()
        instruction = comment_groups["instruction"].strip()
        # Also get rid of the ONBUILD instruction and any following whitespace, since
        # it will be followed by another instruction.
        if re.match(onbuild_pattern, instruction) is not None:
            instruction = re.sub(onbuild_pattern, "", instruction)
            if instruction == "":
                raise ValueError("Dockerfile includes empty ONBUILD instruction.")
        if not instruction == "":
            stripped_lines.append(instruction)

    if len(stripped_lines) == 0:
        raise ValueError(
            "Dockerfile was empty or contained only whitespace and comments."
        )

    # Append all lines that have a backslash at the end into each other.
    lines = stripped_lines
    complete_lines = []
    index = 0
    # do
    while True:
        this_line = lines[index]
        while this_line.endswith("\\"):
            index += 1
            if index == len(lines):
                break
            this_line = this_line[:-1] + " " + lines[index]
        complete_lines.append(this_line)
        # while index < len(lines)
        index += 1
        if index >= len(lines):
            break

    # Check that each line begins with an instruction.
    # The regex should match a line beginning with any of the following, followed by
    # a string, or only "HEALTHCHECK"
    dockerfile_instructions = "|".join(
        [
            "FROM",
            "RUN",
            "CMD",
            "ENTRYPOINT",
            "WORKDIR",
            "USER",
            "LABEL",
            "ARG",
            "SHELL",
            "EXPOSE",
            "ENV",
            "COPY",
            "ADD",
            "VOLUME",
        ]
    )
    instruction_match_string = rf"^(?:{dockerfile_instructions})\s+.+|^HEALTHCHECK$"
    instruction_match_pattern = re.compile(instruction_match_string, re.IGNORECASE)

    for line in complete_lines:
        matches = re.match(instruction_match_pattern, line)
        if matches is None:
            raise ValueError(f'Dockerfile line "{line}" does not appear to be valid.')
