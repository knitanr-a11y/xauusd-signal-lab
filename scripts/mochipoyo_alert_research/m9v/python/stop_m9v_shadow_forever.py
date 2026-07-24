from __future__ import annotations

import os
from pathlib import Path


def main() -> int:
    local_root = Path(os.environ.get("LOCALAPPDATA", "")) / "xauusd_signal_lab" / "mochipoyo_alert_research"
    stop = local_root / "m9v_runtime" / "STOP_M9V_SHADOW_LOOP"
    stop.parent.mkdir(parents=True, exist_ok=True)
    stop.write_text("STOP\n", encoding="utf-8")
    print(f"[M9V STOP REQUESTED] {stop}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
