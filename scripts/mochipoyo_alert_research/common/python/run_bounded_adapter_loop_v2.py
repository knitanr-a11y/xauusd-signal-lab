from __future__ import annotations

import bounded_csv_journal_integrity as journal_integrity

journal_integrity.install_verified_adapter_hooks()

import run_bounded_adapter_loop as runner


if __name__ == "__main__":
    raise SystemExit(runner.main())
