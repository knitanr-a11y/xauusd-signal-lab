from __future__ import annotations

from pathlib import Path

import run_m9v_shadow_forever_safe as legacy

legacy.ONE_SHOT = Path(__file__).resolve().parent / "run_m9v_shadow_once_v2.py"

if __name__ == "__main__":
    raise SystemExit(legacy.main())
