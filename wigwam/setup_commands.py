from __future__ import annotations

from pathlib import Path
from textwrap import dedent, indent
from typing import Dict, Optional, Tuple

from ._defaults import universal_tag_prefix
from ._docker_cuda import CUDADockerfileGenerator, get_cuda_dockerfile_generator
from ._docker_mamba import mamba_add_reqs_dockerfile, mamba_install_dockerfile
from ._image import Image
from ._package_manager import PackageManager
from ._url_reader import URLReader, get_url_reader
from ._utils import (
    image_command_check,
    parse_cuda_info,
    temp_image,
    universal_tag_prefix,
)


def setup_init(
    base: str, tag: str, no_cache: bool
) -> Tuple[Image, PackageManager, URLReader]:
    """
    Set up the initial configuration image.

    Parameters
    ----------
    base : str
        The name of the image upon this one will be based.
    tag : str
        The tag of the image to be built.
    no_cache : bool
        Run Docker build with no cache if True.

    Returns
    -------
    image : Image
        The generated image.
    package_mgr : PackageManager
        The package manager present on the image.
    url_reader : URLReader
        The URL Reader present on the image.
    """
    with temp_image(base) as temp_img:
        package_mgr, url_reader, dockerfile = image_command_check(temp_img, True)

    dockerfile = (
        f"FROM {base}\n\n"
        + dockerfile
        + "\n"
        + dedent(
            """
        ENV DEFAULT_GROUP defaultgroup
        ENV DEFAULT_USER defaultuser
        ENV DEFAULT_GID 1000
        ENV DEFAULT_UID 1000

        RUN groupadd -g $DEFAULT_GID $DEFAULT_GROUP
        RUN useradd -g $DEFAULT_GID -u $DEFAULT_UID -m $DEFAULT_USER

        RUN chmod -R 777 /tmp
        """
        ).strip()
    )

    prefix = universal_tag_prefix()
    img_tag = tag if tag.startswith(prefix) else f"{prefix}-{tag}"

    image = Image.build(tag=img_tag, dockerfile_string=dockerfile, no_cache=no_cache)

    return (image, package_mgr, url_reader)


def setup_cuda_runtime(
    base: str,
    tag: str,
    no_cache: bool,
    cuda_version: str,
    cuda_repo: str,
    package_manager: Optional[PackageManager] = None,
    url_reader: Optional[URLReader] = None,
    arch: str = "x86_64",
) -> Image:
    """
    Build the CUDA runtime image.

    Parameters
    ----------
    base : str
        The name of the image upon this one will be based.
    tag : str
        The tag of the image to be built.
    no_cache : bool
        Run Docker build with no cache if True.
    cuda_version : str
        The CUDA version.
    cuda_repo : str
        The name of the CUDA repository for this distro.
        (e.g. 'rhel8', 'ubuntu2004')
    package_manager : PackageManager or None, optional
        The package manager in use by the base image. Defaults to None.
    url_reader : URLReader or None, optional
        The URL reader in use by the base image. Defaults to None.
    arch : str
        The computer architecture to use. Defaults to "x86_64".

    Returns
    -------
    Image
        The generated image.

    Raises
    -------
    ValueError
        If one of package_manager and url_reader is defined, but not both.
    """
    if (package_manager is not None) and (url_reader is not None):
        package_mgr = package_manager
        url_program = url_reader
        init_lines = ""
    elif (package_manager is not None) or (url_reader is not None):
        # It would be possible to have a user call this knowing only one of the URL
        # reader or package manager, but this use case is not present anywhere in the
        # current codebase, and implementing both possibilities of package_manager XOR
        # url_reader would require additional complexity that is not currently
        # necessary.
        raise ValueError(
            "Either both package_manager and url_reader must both be defined, "
            "or neither."
        )
    else:
        with temp_image(base) as temp_img:
            package_mgr, url_program, init_lines = image_command_check(temp_img)
    cuda_major, cuda_minor = parse_cuda_info(cuda_version=cuda_version)

    cuda_gen: CUDADockerfileGenerator = get_cuda_dockerfile_generator(
        pkg_mgr=package_mgr, url_reader=url_program
    )

    body = cuda_gen.generate_runtime_dockerfile(
        cuda_ver_major=cuda_major,
        cuda_ver_minor=cuda_minor,
        repo_ver=cuda_repo,
        arch=arch,
    )

    dockerfile = f"FROM {base}\n\n{init_lines}\n\n{body}"

    prefix = universal_tag_prefix()
    img_tag = tag if tag.startswith(prefix) else f"{prefix}-{tag}"
    return Image.build(tag=img_tag, dockerfile_string=dockerfile, no_cache=no_cache)


def setup_cuda_dev(
    base: str,
    tag: str,
    no_cache: bool,
    cuda_version: str,
    package_manager: Optional[PackageManager] = None,
    url_reader: Optional[URLReader] = None,
) -> Image:
    """
    Builds the CUDA dev image.

    Parameters
    ----------
    base : str
        The name of the image upon this one will be based.
    tag : str
        The tag of the image to be built.
    no_cache : bool
        Run Docker build with no cache if True.
    cuda_version: str
        The CUDA version, in "<major>.<minor>" format.
    package_manager : PackageManager
        The package manager in use by the base image.
    url_reader : URLReader
        The URL reader in use by the base image.

    Returns
    -------
    Image
        The generated image.

    Raises
    -------
    ValueError
        If one of package_manager and url_reader is defined, but not both.
    """
    with temp_image(base) as temp_img:
        if (package_manager is not None) and (url_reader is not None):
            package_mgr = package_manager
            url_program = url_reader
            init_lines = ""
        elif (package_manager is not None) or (url_reader is not None):
            raise ValueError(
                "Either both package_manager and url_reader must both be "
                "defined or neither."
            )
        else:
            package_mgr, url_program, init_lines = image_command_check(temp_img)
    cuda_major, cuda_minor = parse_cuda_info(cuda_version=cuda_version)

    if isinstance(url_reader, str):
        reader: URLReader = get_url_reader(url_program)
    else:
        reader = url_reader  # type: ignore
    cuda_gen: CUDADockerfileGenerator = get_cuda_dockerfile_generator(
        pkg_mgr=package_mgr, url_reader=reader
    )
    body = cuda_gen.generate_dev_dockerfile(
        cuda_ver_major=cuda_major, cuda_ver_minor=cuda_minor
    )

    dockerfile = f"FROM {base}\n\n{init_lines}\n\n{body}"

    prefix = universal_tag_prefix()
    img_tag = tag if tag.startswith(prefix) else f"{prefix}-{tag}"

    return Image.build(tag=img_tag, dockerfile_string=dockerfile, no_cache=no_cache)


def setup_conda_runtime(
    base: str,
    tag: str,
    no_cache: bool,
    env_file: Path,
) -> Image:
    """
    Builds the Conda runtime environment image with micromamba.

    Parameters
    ----------
    base : str
        The name of the image upon this one will be based.
    tag : str
        The tag of the image to be built.
    no_cache : bool
        Run Docker build with no cache if True.
    env_file : Path
        The location of the runtime environment requirements file.

    Returns
    -------
    Image
        The generated image.
    """
    # Set the context at the parent of the given environment file.
    env_file_absolute = env_file.resolve()
    context = env_file_absolute.parent

    # Get the path to the environment file, relative to the context.
    env_file_relative = env_file_absolute.relative_to(context)

    header, body = mamba_install_dockerfile(env_reqs_file=Path(env_file_relative))
    dockerfile = f"{header}\n\nFROM {base}\n\n{body}"

    prefix = universal_tag_prefix()
    img_tag = tag if tag.startswith(prefix) else f"{prefix}-{tag}"

    return Image.build(
        tag=img_tag,
        dockerfile_string=dockerfile,
        no_cache=no_cache,
        context=context,
    )


def setup_conda_dev(base: str, tag: str, no_cache: bool, env_file: Path) -> Image:
    """
    Set up the development environment.

    Parameters
    ----------
    base : str
        The name of the image upon this one will be based.
    tag : str
        The tag of the image to be built.
    no_cache : bool
        Run Docker build with no cache if True.
    env_file : Path
        The location of the dev environment requirements file.

    Returns
    -------
    Image
        The generated image.
    """
    # Set the context at the parent of the given environment file.
    env_file_absolute = env_file.resolve()
    context = env_file_absolute.parent

    # Get the path to the environment file, relative to the context.
    env_file_relative = env_file.relative_to(context)

    body = mamba_add_reqs_dockerfile(env_reqs_file=Path(env_file_relative))

    prefix = universal_tag_prefix()
    img_tag = tag if tag.startswith(prefix) else f"{prefix}-{tag}"

    dockerfile = f"FROM {base}\n\n{body}"

    return Image.build(
        tag=img_tag,
        dockerfile_string=dockerfile,
        no_cache=no_cache,
        context=context,
    )


def setup_all(
    base: str,
    tag: str,
    no_cache: bool,
    cuda_version: str,
    cuda_repo: str,
    runtime_env_file: Path,
    dev_env_file: Path,
    verbose: bool = False,
) -> Dict[str, Image]:
    """
    Builds the entire Docker image stack.

    Parameters
    ----------
    base : str
        The name of the image upon this one will be based.
    tag : str
        The tag of the image to be built.
    no_cache : bool
        Run Docker build with no cache if True.
    cuda_version : str
        The CUDA version.
    cuda_repo : str
        The name of the CUDA repository for this distro.
        (e.g. 'rhel8', 'ubuntu2004')
    runtime_env_file : Path
        The location of the runtime environment requirements file.
    dev_env_file : Path
        The location of the dev environment requirements file.
    verbose : bool, optional
        If True, output informational messages upon completion. Defaults to False.

    Returns
    -------
    Dict[str, Image]
        A dictionary of all images generated, indexed by tag.
    """
    prefix = universal_tag_prefix()
    cuda_major, cuda_minor = parse_cuda_info(cuda_version=cuda_version)

    images: Dict[str, Image] = {}

    # Build the initial image and append it to the image list
    base_image_tag = f"{prefix}-{tag}-init"
    base_image, package_mgr, url_program = setup_init(
        base=base, tag=base_image_tag, no_cache=no_cache
    )
    images[base_image_tag] = base_image

    # Build the CUDA runtime image and append it to the image list
    cuda_run_tag = f"{prefix}-{tag}-cuda-" + f"{cuda_major}-{cuda_minor}-runtime"
    cuda_run_image = setup_cuda_runtime(
        base=base_image_tag,
        tag=cuda_run_tag,
        no_cache=no_cache,
        cuda_version=cuda_version,
        cuda_repo=cuda_repo,
        package_manager=package_mgr,
        url_reader=url_program,
    )
    images[cuda_run_tag] = cuda_run_image

    # Build the Mamba runtime image and append it to the image list
    mamba_run_tag = f"{prefix}-{tag}-mamba-runtime"
    mamba_run_image = setup_conda_runtime(
        base=cuda_run_tag,
        tag=mamba_run_tag,
        no_cache=no_cache,
        env_file=runtime_env_file,
    )
    images[mamba_run_tag] = mamba_run_image

    # Build the CUDA dev image and append it to the image list
    cuda_dev_tag = f"{prefix}-{tag}-cuda-" + f"{cuda_major}-{cuda_minor}-dev"
    cuda_dev_image = setup_cuda_dev(
        base=mamba_run_tag,
        tag=cuda_dev_tag,
        no_cache=no_cache,
        cuda_version=cuda_version,
        package_manager=package_mgr,
        url_reader=url_program,
    )
    images[cuda_dev_tag] = cuda_dev_image

    # Build the Mamba dev image and append it to the image list
    mamba_dev_tag = f"{prefix}-{tag}-mamba-dev"
    mamba_dev_image = setup_conda_dev(
        base=cuda_dev_tag, tag=mamba_dev_tag, no_cache=no_cache, env_file=dev_env_file
    )
    images[mamba_dev_tag] = mamba_dev_image

    if verbose:
        print("IMAGES GENERATED:")
        for image_tag in images:
            print(indent(image_tag, "\t"))

    return images
