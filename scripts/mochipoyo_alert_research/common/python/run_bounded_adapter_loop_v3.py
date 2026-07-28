from __future__ import annotations

import bounded_csv_journal_integrity as journal_integrity

journal_integrity.install_verified_adapter_hooks()

import m9v_bounded_start_bootstrap
import run_bounded_adapter_loop as runner

runner.BUILDERS["M9V"] = m9v_bounded_start_bootstrap.build_m9v_runner


if __name__ == "__main__":
    raise SystemExit(runner.main())
