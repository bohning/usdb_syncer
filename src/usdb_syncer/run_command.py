"""Functions for running commands on the local machine."""

import subprocess
from pathlib import Path

from usdb_syncer.logger import Log


def run_command(command: str, directory: Path, logger: Log) -> int:
    """Run a command on the local machine.

    Parameters:
        command: the command to run. $dir$ will be replaced with the directory.
        directory: the directory to run the command in
        logger: the logger to use

    Returns:
        the return code of the command
    """
    logger.info("Running supplied command.")

    args: list[str] = []

    # Insert directory where $dir$ is found in the command
    args = command.split(" ")
    if "$dir$" in command:
        args[args.index("$dir$")] = str(directory)

    logger.debug(f"Running command '{args}' in '{directory}'.")

    p = subprocess.run(args=args, cwd=directory, shell=True)

    if p.returncode != 0:
        logger.error(f"Command failed with return code {p.returncode}")
    return p.returncode
