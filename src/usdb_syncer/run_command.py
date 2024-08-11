"""Functions for running commands on the local machine."""

import subprocess
from pathlib import Path

from usdb_syncer.logger import Log


def run_command(
    command: str, directory: Path, logger: Log, timeout: float | None = None
) -> int:
    """
    Run a command on the local machine. The placeholder $dir$ in the command will be replaced with the specified directory.
    The working directory will be set to the parent of the provided directory.

    Parameters:
        command (str): The command to run. The placeholder $dir$ will be replaced with the directory.
        directory (Path): The directory to replace $dir$ with. Intended to be the directory of the song.
        logger (Log): The logger to use for logging messages.

    Returns:
        int: The return code of the command. Returns 0 if there is no command to run.
    """
    if command == "":
        logger.debug("No command set to to run.")
        return 0

    logger.info("Running custom command.")

    # Build the command
    parts = command.split(" ")
    args = []
    for arg in parts:
        if arg.count("$dir$") > 0:
            logger.debug(f"Replacing $dir$ with {directory}.")
            arg = arg.replace("$dir$", str(directory))
        args.append(arg)

    logger.debug(
        f'Running custom command "{" ".join(args)}" in "{directory.parent}".'
    )  # e.g Running command "echo hello" in "/home/user/songs".

    try:
        p = subprocess.run(
            args=args, cwd=directory.parent, shell=True, check=True, timeout=timeout
        )
    except ValueError:
        logger.error("Custom command is invalid.")
        return 1
    except OSError:
        logger.error(
            "Running custom command failed because a shell could not be invoked."
        )
        return 1
    except subprocess.TimeoutExpired:
        logger.error("Custom command timed out.")
        return 1
    except subprocess.CalledProcessError as e:
        logger.error(
            f"Custom command failed while running with error code: {e.returncode}"
        )
        return e.returncode

    logger.info("Custom command ran successfully.")
    return p.returncode
