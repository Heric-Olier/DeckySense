"""Plugin version reader.

Decky reads the plugin version from package.json (NOT plugin.json).
Lives at the package root so the updater and the RPC layer share one
source of truth. Cached because it is read on every update check;
call ``read_version.cache_clear()`` after installing a new release so
the fresh version is picked up without a process restart.
"""

from __future__ import annotations

import json
import pathlib
from functools import lru_cache

# Layout: py_modules/deckysense/version.py -> plugin root is 3 levels up.
_PACKAGE_JSON = pathlib.Path(__file__).resolve().parent.parent.parent / "package.json"


@lru_cache(maxsize=1)
def read_version() -> str:
    # Never raise: a missing/malformed package.json must not break RPCs.
    try:
        return str(json.loads(_PACKAGE_JSON.read_text(encoding="utf-8"))["version"])
    except (OSError, ValueError, KeyError):
        return "unknown"
