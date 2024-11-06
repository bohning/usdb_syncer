"""Utilities for managing dynamically loaded add-ons."""

import importlib
import pkgutil
import sys

from usdb_syncer import utils
from usdb_syncer.logger import logger


def load_all() -> None:
    sys.path.append(str(utils.AppPaths.addons))
    for _, mod, is_pkg in pkgutil.iter_modules([str(utils.AppPaths.addons)]):
        importlib.import_module(mod)
        logger.debug(f"Imported add-on {'package' if is_pkg else 'module'} '{mod}'.")
