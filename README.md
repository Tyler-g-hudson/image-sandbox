# WIGWAM Interface Documentation & User Guide

# Table of Contents

_**[Functional Overview of WIGWAM 1](#_Toc137131679)**_

**[The End User's WIGWAM Use Case 1](#_Toc137131680)**

**[Setup, Compile, and Deploy: The ISCE3 Image Stack 1](#_Toc137131681)**

**[Search & Fetch Binary Artifact Data 1](#_Toc137131682)**

**[Run Workflows on Your Distributable Image 1](#_Toc137131683)**

**[A Note About Wigwams 1](#_Toc137131684)**

_**[Setup & Build Process - The Easy Way 2](#_Toc137131685)**_

**[Setup All: Build the ISCE3 Environment Image Stack 3](#_Toc137131686)**

**[Full-Compile: Acquire and Compile the ISCE3 Framework 3](#_Toc137131687)**

**[Test: Run Unit Tests (optional) 4](#_Toc137131688)**

**[Distributable: Create the ISCE3 Distributable Image 4](#_Toc137131689)**

_**[Data Repository Search & Fetch 5](#_Toc137131690)**_

**[Data Search: Searching the _workflowdata.json_ File 5](#_Toc137131691)**

[Example: Using multiple "--tags" arguments: 5](#_Toc137131692)

[Example: Using a non-default workflowdata file: 5](#_Toc137131693)

**[Data Fetch: Fetching Artifacts with Rover 5](#_Toc137131694)**

_**[Running Workflows 7](#_Toc137131695)**_

**[Workflow: Running Workflows 7](#_Toc137131696)**

**[The _workflowtests.json_ File 7](#_Toc137131697)**

_**[Useful Tools 8](#_Toc137131698)**_

**[The Command Line Help Option 8](#_Toc137131699)**

**[Drop-In Sessions 8](#_Toc137131700)**

**[Lockfile Generation Tool 8](#_Toc137131701)**

**[Image Removal Tool 8](#_Toc137131702)**

_**[Advanced Setup & Build Process 10](#_Toc137131703)**_

**[Setup Instructions 10](#_Toc137131704)**

[Setup Init: Build the ISCE3 Initial Image 10](#_Toc137131705)

[Setup Cuda Runtime: Build the ISCE3 Runtime CUDA Environment 10](#_Toc137131706)

[Setup Env Runtime: Build the ISCE3 Runtime Micromamba Environment 10](#_Toc137131707)

[Setup Cuda Dev: Build the ISCE3 Development CUDA Environment 11](#_Toc137131708)

[Setup Mamba Dev: Build the ISCE3 Development Runtime Environment 11](#_Toc137131709)

**[Clone & Insert: Repository Clone/Install Commands 11](#_Toc137131710)**

[Clone: Clone a Git repository onto a docker image 12](#_Toc137131711)

[Insert: Insert a local directory into a docker image 12](#_Toc137131712)

**[Config: Configuring CMake 12](#_Toc137131713)**

**[Compile: Compiling the Project 12](#_Toc137131714)**

**[Install: Installing ISCE3 13](#_Toc137131715)**

**[Test: Running Unit Tests 13](#_Toc137131716)**

**[Distributable: Creating the Final ISCE3 Distributable Image 13](#_Toc137131717)**

# Functional Overview of WIGWAM

WIGWAM is a python command line interface that enables the rapid and flexible production and management of ISCE3 docker images and artifacts. Its' name stands for:

_**WIGWAM: W**orkspace for **I**mage **G**eneration, **W**orkflows, and **A**rtifact **M**anagement_

## The End User's WIGWAM Use Case

The use case for WIGWAM by end users is to enable rapid deployment and testing of arbitrary iterations of ISCE3 images and workflows by developers and downstream users. Users should be able to flexibly deploy ISCE3 environments and repositories, rapidly acquire their data with minimum network usage, and run a range of tests on their images.

## Setup, Compile, and Deploy: The ISCE3 Image Stack

WIGWAM builds a series of ten images which sequentially prepare the environment, acquire the ISCE3 repository, compile & install it, and finally move the installed ISCE3 application into the slimmer runtime environment for distribution. This tool uses a prefixed naming convention for all images except the final deployable, which allows for simple grouping and removal of images with minimal risk to other images on your system.

## Search & Fetch Binary Artifact Data

WIGWAM uses a secondary open-source image called Rover to enable easy caching of binary artifacts from locations on the network.

## Run Workflows on Your Distributable Image

WIGWAM can be used to run single and multi-stage workflow tests for integration and end-to-end testing, with the purpose of simplifying workflow testing.

## A Note About Wigwams

The semi-nomadic ancestors of modern Algonquin peoples, who inhabited the North Atlantic, Great Lakes, and Upper Mississippi regions of North America, built quickly-constructable, semi-permanent domed or conical structures called Wigwams which acted as spaces for habitation and work at winter hunting camps. These structures were deployed seasonally and would be dismantled and rebuilt if they didn't survive the summer's disuse. It is in this spirit of rapid and flexible deployment that this interface is written and named. The writer of this interface is of Algonquin heritage and uses this name with respect for the ancestral dwelling that it references.

# Setup & Build Process - The Easy Way

The WIGWAM interface implements a three-command process for building the ISCE3 deliverable from some base image. The two primary base images supported and tested with this interface are called "ubuntu" and "oraclelinux:8.4" - more generally, WIGWAM may work with images that have either yum or apt-get installed by default and are supported by CUDA's "rhel8" or "ubuntu2004" offerings, but can be guaranteed not to work for any image that does not.

- setup all
- full-compile
  - (test)
- distributable

The three-step process of generating the ISCE3 distributable is as follows: The setup-all step, the full-compile step, and the distributable step. The setup-all step creates the stack of images which form the runtime and development environments for ISCE3 from some base image. The full-compile step takes in the final "dev environment" image produced by the last step and acquires and installs the ISCE3 repository in a stack of images. Finally, the deployable step copies the installed ISCE3 framework from its image generated by the full-compile step into the slimmer runtime environment image from the setup-all step to create a final, slim ISCE3 distributable image. These will be explained in further detail below.

For users who need to tailor a more specific build, this process is split into subcommands later in this document.

![](RackMultipart20230609-1-jii7u5_html_be10c76eda91177d.png)

_The ISCE3 Docker image stack, as implemented by WIGWAM. Colored boxes indicate processes, white boxes indicate Docker images produced by the system._

## Setup All: Build the ISCE3 Environment Image Stack

    python -m wigwam setup all
        --tag (-t) TAG
        --base (-b) BASE
        --cuda-version (-c) MAJOR.MINOR
        --cuda-repo REPO_NAME
        --runtime-env-file RUNTIME_SPECFILE
        --dev-env-file DEV_SPECFILE
        --no-cache

The setup-all step generates five images: An initialization image which contains a prepared environment with all the fundamental dependencies needed by the later steps, as well as a CUDA runtime environment, a micromamba runtime environment, a CUDA development environment, and a micromamba development environment - each built upon the prior. These steps create both the runtime environment which the installed ISCE3 application will be placed into and the development environment which it will be initially compiled upon.

**--tag:** The middle part of the image tag. The full tag of each image will be "wigwam-TAG-SUFFIX" with suffixes in order of generation: "init", "cuda-MAJOR-MINOR-runtime", "mamba-runtime", "cuda-MAJOR-MINOR-dev", "mamba-dev". Defaults to "setup".  
**--base:** The base image. Recommended and supported base images are "ubuntu" and "oraclelinux:8.4" - any base image not using yum or apt-get, or using operating systems not under the umbrella of CUDA "ubuntu2004" and "rhel8" repositories will fail. Defaults to "oraclelinux:8.4".	
**--cuda-version:** The cuda version, in MAJOR.MINOR format, e.g "11.0". Defaults to 11.4.	
**--cuda-repo:** The CUDA repository which contains binaries for the base image operating system. Supported repositories include "ubuntu2004" for the ubuntu base image and other images with the Ubuntu 20.04 distro installed, and "rhel8" for the oraclelinux:8.4 base image and others using Oracle Linux or yum. Defaults to "rhel8".	
**--runtime-env-file:** The path to the runtime environment specfile. WIGWAM supports regular requirements.txt files, environment.yml files, and lockfiles. Defaults to "runtime-spec-file.txt"	 
**--dev-env-file:** The path to the development environment specfile. WIGWAM supports regular requirements.txt files, environment.yml files, and lockfiles. Defaults to "dev-spec-file.txt"	 
**--no-cache:** Using this option causes the docker images to build with no cached steps. This may run slower, but can aid in debugging.

## Full-Compile: Acquire and Compile the ISCE3 Framework

    python -m wigwam full-compile
        --tag (-t) TAG
        --base (-b) BASE
        --copy-path (-p) ISCE3_FILEPATH
        --repo GIT_REPO
        --build-type CMAKE_BUILD_TYPE
        --no-cuda

The full-compile step generates four images: Either a git repo image or a local ISCE3 repo image, followed by CMake configuration, ISCE3 build, and ISCE3 installed images. The repo images intake the ISCE3 codebase from either the head of a remote Git repository or from a local file, and the CMake images configure CMake, build ISCE3, and then install it to the "/app" folder on the image. All images in this step are built without the cache.

**--tag:** The middle part of the image tag. The full tag of each image will be "wigwam-TAG-SUFFIX" with suffixes in order of generation: either "git-repo" or "file-{FILEPATH\_TOP\_FOLDER}" (e.g. "file-isce3"), followed by "configured", "built", and "installed". Defaults to "build".		
**--base:** The full tag (including "wigwam-") of the ISCE3 mamba development environment image generated by the setup-all step. This is the base image for the stack of images generated by the full-compile step.	
**--copy-path:** The location of a local ISCE3 repository, if generating a local repository image. If used, this will ignore all git repo commands and use the local path instead.	
**--repo:** A git repository to download if the copy-path option was not used. Should be in "user/repository" format. Defaults to "isce-framework/isce3".	
**--build-type:** The CMake build type; one of "Release", "Debug", "RelWithDebInfo", "MinSizeRel". Defaults to "Release".	
**--no-cuda:** If used, this option will instruct CMake to configure and compile without using CUDA bindings.

## Test: Run Optional Unit Tests

    python -m wigwam test IMAGE_TAG
        --logfile (-l) LOGFILE_PATH
        --compress-output
        --quiet-fail

Once the ISCE3 framework is installed to an image, the installed ctest unit tests can be run on it.

**IMAGE\_TAG:** The name of the image on which the tests will be run. This image must have ISCE3 installed in its working directory.  
**--logfile:** The desired path of an output file, in .xml format. Defaults to "Test.xml".  
**--compress-output:** If used, will compress the ctest outputs.  
**--quiet-fail:** If used, will output less verbosely on unit test failure.

## Distributable: Create the ISCE3 Distributable Image

    python -m wigwam distributable
        --base (-b) BASE_TAG
        --source-tag (-s) SOURCE_TAG
        --tag (-t) IMAGE_TAG

The final step of the process is to build the ISCE3 deliverable. This image takes in the mamba runtime image as its base, copies the installed ISCE3 application from the CMake installed image as a "source", and names this new runtime ISCE3 installation as the distributable image. It is the only image generated by this system which doesn't possess the "wigwam" prefix.

**--base:** The tag of the base image. This should be the tag of the mamba runtime image generated in the setup-all step.	
**--source-tag:** The tag of the image on which ISCE3 has been installed to the development environment. This should be the final "installed" tag generated by the full-compile step.	
**--tag:** The tag of the image to be generated. Will not be prefixed with "wigwam-". this is the ISCE3 distributable image.

# Data Repository Search & Fetch

WIGWAM provides functionality for local caching of data artifacts with minimal network overhead. It performs this task by searching a local JSON key-value store called a _workflowdata.json_ file for data repository information, and then requesting for any data which is not present in the user's local cache.

## Data Search: Searching the _workflowdata.json_ File

    python -m wigwam data search
        --tags (-t) TAG [TAG ...]
        --names (-n) NAME [NAME ...]
        --file (-f) FILENAME
        --all (-a)
        --fields FIELD [FIELD ...]

Prior to data fetching, WIGWAM provides a search utility which enables users to pre-check their tag and name search terms and see which data is returned. This will search the terms input by the user and print the set of data objects found in the data file that fit those terms. This can be used to prevent accidentally downloading too much data while attempting a data fetch.

**--tags:** A set of tags to search for, separated by spaces - the search will return any data object that has all the provided tags. This argument can be used multiple times - if --tags is used more than once, the search function will find any objects that fit all the tags given by any of the --tags arguments. Example will be given below.  
**--names:** A set of data object names to return, given by the names of the repositories. Useful if one or several data objects with easily accessible names are needed.  
**--file:** The location of the workflowdata.json file in the filesystem. Defaults to "workflowdata.json" in the current working directory.  
**--all:** Prints every data object in the file. Ignores all tag and name arguments.  
**--fields:** The set of fields to be returned. If used, will limit the fields that are printed as part of the data object. e.g., using "--fields name url" will only return the names and URLs of the found data objects, and omit their "tags" and "files" fields.

### Example: Using multiple "--tags" arguments:

An example user wants to search for all data objects that either have both "insar" and "sanjoaquin" tags or both "nisar" and "rslc" tags. They have their file at the default location with the default name and only want to see the names and tags of the returned objects. They will input the following:

	python -m wigwam data search -t insar sanjoaquin -t nisar rslc

### Example: Using a non-default workflowdata file:

The user has a workflowdata file called "testing\_workflowdata.json" held in a file at "./temp/testing". To search using this workflowdata file, they will input the following:

	python -m wigwam data search -t [tags] -f temp/testing/testing\_workflowdata.json

## Data Fetch: Fetching Artifacts with Rover

    python -m wigwam data fetch
        --tags (-t) TAG [TAG ...]
        --names (-n) NAME [NAME ...]
        --cache (-c) CACHE\_LOCATION
        --file (-f) FILENAME
        --all (-a)
        --no-cache
        --verbose-stderr

To acquire one or more data repositories from an online artifact server, the user can use a set of search options like those of the above search command, and provide a download location to cache the desired files. Repositories already present in the data store can be checked against for validity and will not redownload if they are already present unless an option is given to do so. When several repositories are requested, they will be downloaded in parallel.

The "wigwam data fetch" command receives a cache location and places data repositories to subfiles within this location. So, if the user requests "DATA\_A" and "DATA\_B" to be cached to "./cache" then WIGWAM will download these repositories to subdirectories "./cache/DATA\_A" and "./cache/DATA\_B".

This command will check your local docker images for an image called "Rover" and automatically download it from dockerhub if it does not exist. Rover is a dockerized utility that enables parallel caching of data repositories in the manner implemented by this system.

### Arguments in Detail

**--tags:** A set of tags to search for, separated by spaces - the search will return any data object that has all the provided tags. This argument can be used multiple times - if --tags is used more than once, the search function will find any objects that fit all the tags given by any of the --tags arguments. Example given in the data search section.  
**--names:** A set of data object names to return, given by the names of the repositories. Useful if one or several data objects with easily accessible names are needed.  
**--cache:** Where to cache the data files to. Defaults to "./cache".  
**--file:** The location of the workflowdata.json file in the filesystem. Defaults to "workflowdata.json" in the current working directory.  
**--all:** Use with caution. Downloads every data object in the file. Ignores all tag and name arguments.  
**--no-cache:** When used, all data items requested will be deleted and re-downloaded from the cache if they are already present.  
**--verbose-stderr:** Prints out more detailed error output.

# Running Workflows

WIGWAM provides a command line utility for running workflows. These include singular workflow tests or multi-workflow test series in which each step may rely on data used by a prior step. Data about these workflows is held in a _workflowtests.json_ file, which, like its workflowdata counterpart, holds all the information necessary to identify and run each test. Workflow runconfigs must be held in a specific directory structure described in a subsection below.

## Workflow: Running Workflows

    python -m wigwam workflow WORKFLOW_NAME TEST_NAME
        --image IMAGE_TAG
        --input-dirs (-i) INPUT_FILEPATH ...
        --cache-dirs (-c) CACHE_DIR ...
        --output-dir (-o) OUTPUT_DIRECTORY
        --scratch-dir (-s) SCRATCH_DIRECTORY
        --test-file WORKFLOWTESTS_FILEPATH

**WORKFLOW\_NAME:** The name of the workflow, e.g., rslc, gslc, gcov, insar.  
**TEST\_NAME:** The name of the subtest to run on the workflow (see workflowtests.json section below)  
**--image:** The tag of the image on which to run the tests, usually the ISCE3 distributable image.  
**--input-dirs:** A list of input repository directories. If only one repository is needed by the test, this can be a single path. If several are needed and the repository names are labeled in the subtest definition in workflowtests.json, they must be given in [LABEL]:[PATH] format, e.g., "ref:test\_data/ref\_data". This argument is optional.  
**--cache-dirs:** The locations of a set of data caches as structured by the "wigwam data fetch" command. WIGWAM will search for all listed input repositories by the subdirectory bearing their name in the data caches if all inputs are not specified by the --input-dirs argument. All caches will be searched in order until the files are all found, followed by the default cache location at "./cache". If no input directories or cache directories are specified, only the default cache location will be searched.  
**--output-dir:** The location of the directory to which workflow outputs will be written. For single-workflow tests, files will be written at "[output-dir]/[workflow\_name]/[test\_name]". For workflows that run multiple sub-workflows, files will be written to "[output-dir]/[workflow\_name]/[test\_name]/[sub\_workflow\_name]".  
**--scratch-dir:** The optional location where scratch files will be written. If not given, scratch files will be written to a temporary file on the host machine and then discarded at the end of testing. Scratch subdirectories follow the same pattern as output subdirectories.  
**--test-file:** The location of the test data file, defaults to "workflowtests.json" (see workflowtests.json section below)

### The _workflowtests.json_ File

Most users of the workflowtests.json file will only need to know the name of their desired workflow and any subtest they want to run on it. The file can be used to cross-reference which input repositories need to be acquired using "wigwam data fetch".

# Useful Tools

## The Command Line Help Option

WIGWAM implements the **--help** and **-h** option for all subcommands in the style typical of most command line interfaces. Users are encouraged to make frequent use of this option to ensure that all required command line arguments are entered and to help navigate the subcommand structure of the interface when not referencing this document.

## Drop-In Sessions

python -m wigwam dropin IMAGE\_TAG

When debugging and developing, it can be useful to open a bash shell on an image and navigate within the generated container. WIGWAM contains a simple tool for this:

**IMAGE\_TAG:** The name of any docker image on your system and it will open a bash session within a container on the image. Note that the shell will typically give certain warnings like "I have no name!" – this is expected, as the host user is not necessarily reflected in the image, and should not substantially impair the user.

## Lockfile Generation Tool

    python -m wigwam lockfile
        --tag IMAGE\_TAG (-t)
        --file FILENAME (-f)
        --env-name ENVIRONMENT

When changing the ISCE3 dependency set, users may need to generate new lockfiles (also called specfiles) to enable controlled and rapid installation of the environment without need for solving by an environment manager such as mamba or conda. This interface enables this in the following way:

**--tag:** The tag of the image.  
**--file:** The desired path and filename of the lockfile e.g., "relative/path/to/lockfile.txt".  
**--env-name:** The name of the micromamba environment on the image to create a lockfile for and can be left blank for use with the default environment.

## Image Removal Tool

    python -m wigwam remove {IMAGE\_TAG\_OR\_WILDCARD, ...}
        --force (-f)
        --quiet (-q)
        --ignore-prefix [!]

Since WIGWAM produces large numbers of docker images, it exposes a simple tool for removing docker images created by the system:

Docker images generated by this system all come with "wigwam-" as a prefix on their tag. This command permits removal of several images at a time using wildcard characters from the command line, simplifying the removal of intermediate images generated by the system.

**IMAGE\_TAG\_OR\_WILDCARD ...:** Contains one or more image tags, which may include wildcards. Wildcard characters "\*" and "?" must be prefixed with a backslash ("\*" and "\?") to avoid unpredictable behavior due to how the shell interprets these characters. If the image tags don't already contain the prefix, the prefix will be added to the start of each before the search for images to delete is initiated.

For instance: python -m wigwam remove \* searches for and removes all images with the format "wigwam-\*" - that is to say, all non-deployable images generated by WIGWAM.

**--force:** enables the force-deletion of images, which may be necessary in cases where image deletion fails due to some policy of the docker program.  
**--quiet:** enables silent deletion of images without excess print outputs.  
**--ignore-prefix:**** To be used with extreme caution.** It removes the prefix from the search, enabling the deletion of deployable images and those not generated by WIGWAM. Careless use can result in the unintended deletion of any or all other docker images present on your system.

# Advanced Setup & Build Process

For users with specific needs, the Setup All and Full-Compile instructions can be decomposed into further groups of instructions which together form the full ISCE3 image generation process. Users may find it helpful to use these sub-instructions to perform all or part of the process of building ISCE3 docker images.

## Setup Instructions

The Setup instruction contains five primary subcommands which all generate one image apiece, and each represent one of the steps implemented in the broader Setup All command.

### Setup Init: Build the ISCE3 Initial Image

    python -m wigwam setup init
        --tag (-t) TAG
        --base (-b) BASE
        --no-cache

This step creates an initial image with a few basic environment parameters and dependencies set in place which are necessary for the upcoming steps.

**--tag:** The part of the image tag that follows the prefix. Default is "init".  
**--base:** The base image. Recommended and supported base images are "ubuntu" and "oraclelinux:8.4" - any base image not using yum or apt-get, or using operating systems not under the umbrella of CUDA "ubuntu2004" and "rhel8" repositories will fail at some point later in the process. Defaults to "oraclelinux:8.4".  
**--no-cache:** Using this option causes the docker images to build with no cached steps. This may run slower, but can aid in debugging.

### Setup Cuda Runtime: Build the ISCE3 Runtime CUDA Environment

    python -m wigwam setup cuda runtime
        --tag (-t) TAG
        --base (-b) BASE
        --cuda-version (-c) MAJOR.MINOR
        --cuda-repo REPO\_NAME
        --no-cache

This step creates an image with the runtime CUDA dependencies installed on it. It should be built directly from the init image, or an image that was created from the init image.

**--tag:** The part of the image tag that follows the prefix. Default is "cuda-runtime".  
**--base:** The base image. Recommended to base this image on the init image or some image created from it.  
**--cuda-version:** The cuda version, in MAJOR.MINOR format, e.g "11.0". Defaults to 11.4.  
**--cuda-repo:** The CUDA repository which contains binaries for the base image operating system. Supported repositories include "ubuntu2004" for the ubuntu base image and other images with the Ubuntu 20.04 distro installed, and "rhel8" for the oraclelinux:8.4 base image and others using Oracle Linux or yum. Defaults to "rhel8".  
**--no-cache:** Using this option causes the docker images to build with no cached steps. This may run slower, but can aid in debugging.

### Setup Env Runtime: Build the ISCE3 Runtime Micromamba Environment

    python -m wigwam setup env runtime
        --tag (-t) TAG
        --base (-b) BASE
        --env-file ENV\_SPECFILE
        --no-cache

This step creates an image with the runtime micromamba environment installed on it. It is recommended to base this image on the CUDA runtime image or, if CUDA is not to be used for this build, on the init image or some image based on it.

**--tag:** The part of the image tag that follows the prefix. Default is "env-runtime".  
**--base:** The base image. Recommended to base this image on the init image or some image created from it.  
**--env-file:** The path to the runtime environment specfile. WIGWAM supports regular requirements.txt files, environment.yml files, and lockfiles. Defaults to 'spec-file.txt".  
**--no-cache:** Using this option causes the docker images to build with no cached steps. This may run slower, but can aid in debugging.


### Setup Cuda Dev: Build the ISCE3 Development CUDA Environment

    python -m wigwam setup cuda dev
        --tag (-t) TAG
        --base (-b) BASE
        --no-cache

This step creates an image with the development CUDA dependencies installed on it. It is recommended to base this image on the environment runtime image.

**--tag:** The part of the image tag that follows the prefix. Default is "cuda-dev".  
**--base:** The base image. Recommended and supported base images are "ubuntu" and "oraclelinux:8.4" - any base image not using yum or apt-get, or using operating systems not under the umbrella of CUDA "ubuntu2004" and "rhel8" repositories will fail at some point later in the process. Defaults to "oraclelinux:8.4".  
**--no-cache:** Using this option causes the docker images to build with no cached steps. This may run slower, but can aid in debugging.

### Setup Mamba Dev: Build the ISCE3 Development Runtime Environment

    python -m wigwam setup env runtime
        --tag (-t) TAG
        --base (-b) BASE
        --env-file ENV\_SPECFILE
        --no-cache

This step creates an image with the development micromamba dependencies added to the environment. It is recommended to base this image on the CUDA dev image or, if CUDA is not to be used for this build, on the runtime environment image.

**--tag:** The part of the image tag that follows the prefix. Default is "env-dev".  
**--base:** The base image. Recommended to base this image on the init image or some image created from it.  
**--env-file:** The path to the development environment specfile. WIGWAM supports regular requirements.txt files, environment.yml files, and lockfiles. Defaults to 'spec-file.txt".  
**--no-cache:** Using this option causes the docker images to build with no cached steps. This may run slower, but can aid in debugging.

## Clone & Insert: Repository Clone/Install Commands

This step of the build takes one of two forms - either acquiring a git repository's head and placing it onto an image, or placing a copy of your local repository on the image. There are two different commands to handle these cases: Clone and Insert.

### Clone: Clone a Git repository onto a docker image

    python -m wigwam clone
        --tag (-t) TAG
        --base (-b) BASE
        --repo GIT\_REPO

Acquires a Git repo and places it onto a dev image at "/[REPO\_NAME]", and places the work directory in this directory.

**--tag:** The part of the image tag that follows the prefix. Default is "repo".  
**--base:** The full tag of the image upon this one will be based. Recommended is the dev environment image.  
**--repo:** A git repository to download. Should be in "user/repository" format. Defaults to "isce-framework/isce3".

### Insert: Insert a local directory into a docker image

    python -m wigwam insert
        --tag (-t) TAG
        --base (-b) BASE
        --path (-p) PATH

Acquires a directory from the local machine and places it at "/[DIRECTORY\_NAME]" on a new image, and places the work directory of the image in this directory. The primary use of this command is to place a local copy of an ISCE3 repository onto an image for installation.

**--tag:** The part of the image tag that follows the prefix. Default is "filecopy".  
**--base:** The full tag of the image upon this one will be based. Recommended is the dev environment image.  
**--path:** The location of the directory to be copied onto the image.

## Config: Configuring CMake

    python -m wigwam config
        --tag (-t) TAG
        --base (-b) BASE
        --build-type CMAKE\_BUILD\_TYPE
        --no-cuda

Builds an image which has cmake configured and prepared for build and installation.

**--tag:** The part of the image tag that follows the prefix. Default is "configured".  
**--base:** The full tag (including "wigwam-") of the ISCE3 image which has a repository copied to it and in which the work directory is set to that copy's root directory, as output by the clone and insert instructions.  
**--build-type:** The CMake build type; one of "Release", "Debug", "RelWithDebInfo", "MinSizeRel". Defaults to "Release".  
**--no-cuda:** If used, this option will instruct CMake to configure and compile without using CUDA bindings.

## Compile: Compiling the Project

	python -m wigwam compile
        --tag (-t) TAG
        --base (-b) BASE

Builds an image which has ISCE3 built but not yet installed.

**--tag:** The part of the image tag that follows the prefix. Default is "compiled".  
**--base:** The full tag (including "wigwam-") of the ISCE3 image in which the work directory is in an ISCE3 repository and CMake is configured for install.

## Install: Installing ISCE3

    python -m wigwam install
        --tag (-t) TAG
        --base (-b) BASE

Builds an image which has ISCE3 installed to the "/app" directory which has also been set to the working directory.

**--tag:** The part of the image tag that follows the prefix. Default is "installed".  
**--base:** The full tag (including "wigwam-") of the ISCE3 image in which the work directory is in an ISCE3 repository and the project is built.

## Final Commands

See the [Test section above.](#Test-Run-Optional-Unit-Tests)

See the [Distributable section above.](#Distributable)