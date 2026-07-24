from __future__ import annotations

import run_m9v_shadow_once as legacy
import m9v_core_v2 as core

legacy.core = core

if __name__ == "__main__":
    raise SystemExit(legacy.main())
