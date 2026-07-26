from __future__ import annotations

import sys
from pathlib import Path

THIS = Path(__file__).resolve()
if str(THIS.parent) not in sys.path:
    sys.path.insert(0, str(THIS.parent))

import m10p2_guarded_runtime as g

r = g.impl


def main() -> int:
    try:
        local_root, root, _ = r.env()
        contract = r.js(r.CONTRACT)
        r.valid(contract)

        runtime_dir, runtime_path, state_path, lock_path = r.runtime_paths(local_root)
        if runtime_path.exists() or state_path.exists() or lock_path.exists():
            print("[M10P2 BLOCKED] M10P2 runtime/state/lock already exists.")
            print("[SAFE] Do not rerun BAT01 or delete runtime files. Send this output to ChatGPT.")
            return 2

        m10p_path = local_root / "m10p_runtime" / "m10p_runtime_manifest.json"
        if not m10p_path.is_file():
            print(f"[M10P2 BLOCKED] M10P runtime anchor missing: {m10p_path}")
            return 2
        m10p = r.js(m10p_path)
        if (
            m10p.get("stage") != "M10P_C056_G013_FRESH_PROSPECTIVE_SHADOW"
            or m10p.get("runtime_contract_version") != "M10P_RUNTIME_V1_APPEND_SAFE_PREFIX"
            or m10p.get("reset_allowed") is not False
        ):
            print("[M10P2 BLOCKED] M10P runtime anchor is unsafe or unexpected.")
            return 2

        snapshots = r.current_feed_snapshots(root)
        latest = {tf: r.pt(str(item["last_server_open"])) for tf, item in snapshots.items()}
        latest_m1 = latest["M1"]
        m10p_start = r.pt(str(m10p["prospective_start_server_time"]))

        print(f"[M10P2 CHECK] latest CLOSED M1 = {r.ft(latest_m1)}")
        print(f"[M10P2 CHECK] M10P frozen start = {r.ft(m10p_start)}")

        health = g.observed_feed_health(root, snapshots)
        for tf in ("M5", "M15", "H1", "H4", "D1"):
            row = health[tf]
            print(
                f"[M10P2 FEED] {tf} last={row['last_server_open']} "
                f"observed_m1_bars={row['observed_m1_bars_after_tf']} "
                f"limit={row['allowed_observed_m1_bars']} "
                f"wall_lag={row['wall_lag_seconds']}s"
            )

        if latest_m1 <= m10p_start:
            print("[M10P2 WAIT] No newer CLOSED M1 exists yet.")
            print("[SAFE] No M10P2 runtime/start was created. Keep all monitors running unchanged.")
            print("[NEXT] Run this readiness check again only after the live GOLD CSV advances.")
            return 3

        print("[M10P2 READY] A newer CLOSED M1 exists and observed-trading-time feed health passed.")
        print("[SAFE] This readiness check did not create or modify any runtime/start/state.")
        return 0
    except Exception as exc:
        print(f"[M10P2 BLOCKED] {type(exc).__name__}: {exc}")
        print("[SAFE] No M10P2 runtime/start was intentionally created or modified.")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
