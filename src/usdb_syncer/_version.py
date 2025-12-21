"""For builds and bundles, this is replaced with the hardcoded release version."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("usdb_syncer")
except PackageNotFoundError:
    # syncer is not installed in the environment for some reason
    __version__ = "0.unknown"
