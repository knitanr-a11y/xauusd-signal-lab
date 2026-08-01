from __future__ import annotations

from pathlib import Path
from typing import Any

from . import source_audit

_CACHE: dict[str, dict[str, Any]] = {}
_ORIGINAL_INSPECT = source_audit.inspect_csv


def _cached_inspect(path: Path) -> dict[str, Any]:
    key = str(Path(path).resolve())
    if key not in _CACHE:
        _CACHE[key] = _ORIGINAL_INSPECT(Path(path))
    return _CACHE[key]


source_audit.inspect_csv = _cached_inspect


if __name__ == "__main__":
    raise SystemExit(source_audit.main())
