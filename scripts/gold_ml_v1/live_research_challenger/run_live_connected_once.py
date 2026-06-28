from __future__ import annotations

import run_live_once as base
from live_execution_deal_safe import process_execution_cycle

base.process_execution_cycle = process_execution_cycle

if __name__ == "__main__":
    raise SystemExit(base.main())
