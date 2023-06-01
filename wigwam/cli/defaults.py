from pathlib import Path

# Acquire the location of defaults relative to the module
module_location: Path = Path(__file__).parents[2]
default_run_reqs_file: Path = module_location / "env_files" / "lock-runtime.txt"
default_dev_reqs_file: Path = module_location / "env_files" / "lock-dev.txt"
