from __future__ import annotations

import m10w26_runtime_v2 as runtime_v2
import run_m10w26_private_snapshot as implementation

implementation.runtime = runtime_v2

if __name__ == "__main__":
    raise SystemExit(implementation.main())
