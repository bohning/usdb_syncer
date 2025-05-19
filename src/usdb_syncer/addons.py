"""Utilities for managing dynamically loaded add-ons."""

import importlib
import pkgutil
import sys

from usdb_syncer import utils
from usdb_syncer.logger import logger


def load_all() -> None:
    addons_path = utils.AppPaths.addons
    sys.path.append(str(addons_path))

    # Search for zip files in the addons directory and add them to the path
    zip_files = [str(z) for z in addons_path.glob("*.zip")]
    for zip_file in zip_files:
        sys.path.append(zip_file)

    # Import everything
    for _, mod, is_pkg in pkgutil.iter_modules([*zip_files, str(addons_path)]):
        importlib.import_module(mod)
        logger.debug(f"Imported add-on {'package' if is_pkg else 'module'} '{mod}'.")
