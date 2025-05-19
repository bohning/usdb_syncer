"""For builds and bundles, this is replaced with the hardcoded release version."""

import dunamai as _dunamai

__version__ = _dunamai.Version.from_git().serialize()
