from __future__ import annotations

import sys
from pathlib import Path

THIS = Path(__file__).resolve()
COMMON = THIS.parents[2] / "common" / "python"
if str(COMMON) not in sys.path:
    sys.path.insert(0, str(COMMON))

import bounded_csv_journal_integrity as journal_integrity

journal_integrity.install_verified_adapter_hooks()

import migrate_bounded_csv_source_adapter as migration


if __name__ == "__main__":
    raise SystemExit(migration.main())
