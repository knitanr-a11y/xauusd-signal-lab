#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Read-only Stage289 monitor using contractually closed live candle CSVs."""
from __future__ import annotations
import argparse, json
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
from gold_v3_289_live_features import EXTERNAL_FILES, GOLD_FILES, read_candles
from gold_v3_289_candidates import detect_candidates

READY = "GOLD_V3_289_LIVE_CANDLE_ML_SAFE_SHADOW_READY_AUDIT_ONLY"
PARTIAL = "GOLD_V3_289_LIVE_CANDLE_ML_SAFE_SHADOW_PARTIAL_AUDIT_ONLY"
BLOCKED = "GOLD_V3_289_LIVE_CANDLE_ML_SAFE_SHADOW_BLOCKED_AUDIT_ONLY"
CSV_CONTRACT = "open/in-progress candles are not written to CSV; latest row is closed"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--candle-dir", required=True)
    p.add_argument("--output-dir", required=True)
    p.add_argument("--lookback-hours", type=int, default=96)
    return p.parse_args()


def main() -> int:
    a = parse_args()
    cdir = Path(a.candle_dir).expanduser().resolve()
    out = Path(a.output_dir).expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)
    blockers = []
    checks = []
    for tf, name in GOLD_FILES.items():
        ok = (cdir / name).exists()
        checks.append({"check": f"{tf}_closed_csv_present", "passed": ok, "path": str(cdir / name)})
        if not ok:
            blockers.append(f"MISSING_{name}")
    external_ready = all((cdir / name).exists() for name in EXTERNAL_FILES.values())
    checks.append({"check": "stage286_external_m15_present", "passed": external_ready, "path": ",".join(EXTERNAL_FILES.values())})
    if blockers:
        candidates, meta = pd.DataFrame(), {}
        status = BLOCKED
    else:
        try:
            candidates, meta = detect_candidates(cdir, a.lookback_hours)
            status = READY if external_ready else PARTIAL
        except Exception as exc:
            candidates, meta = pd.DataFrame(), {}
            blockers.append(f"DETECTION_ERROR:{exc!r}")
            status = BLOCKED
    candidates.to_csv(out / "gold_v3_289_detected_live_candle_candidates.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(checks).to_csv(out / "gold_v3_289_validation.csv", index=False, encoding="utf-8-sig")
    latest_m5 = ""
    if (cdir / GOLD_FILES["M5"]).exists():
        latest_m5 = str(pd.Timestamp(read_candles(cdir / GOLD_FILES["M5"], 4).time.max()))
    summary = {
        "status": status,
        "ready": status == READY,
        "created_at_utc": utc_now(),
        "csv_contract": CSV_CONTRACT,
        "csv_open_bar_exclusion_required": False,
        "source_csv_mutated": False,
        "manual_candidate_queue_used": False,
        "audit_only": True,
        "live_ready": False,
        "mt5_execution_enabled": False,
        "discord_live_enabled": False,
        "final_signal_enabled": False,
        "external_short_ready": external_ready,
        "latest_m5_time": latest_m5,
        "detected_candidate_count": int(len(candidates)),
        "blockers": blockers,
        **meta,
    }
    (out / "gold_v3_289_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "GOLD V3 289 PASTE_ME_LIVE_CANDLE_ML_SAFE_SHADOW",
        f"status: {status}",
        f"ready: {str(status == READY).lower()}",
        "live_ready: false",
        "source_csv_mutated: false",
        "manual_candidate_queue_used: false",
        "open_asof_allowed: false",
        f"csv_contract: {CSV_CONTRACT}",
        "csv_open_bar_exclusion_required: false",
        "safety: audit_only=true, mt5=false, discord=false, final_signal=false",
        f"latest_m5_time: {latest_m5}",
        f"stage286_external_live_m15_ready: {str(external_ready).lower()}",
        f"detected_candidate_count: {len(candidates)}",
        f"blocker_count: {len(blockers)}",
        "",
        "BLOCKERS",
        *(blockers if blockers else ["NO_BLOCKERS"]),
        "",
        "OUTPUTS",
        "gold_v3_289_detected_live_candle_candidates.csv",
        "gold_v3_289_validation.csv",
        "gold_v3_289_summary.json",
    ]
    (out / "paste_me.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(out / "paste_me.txt")
    return 0 if status in {READY, PARTIAL} else 1


if __name__ == "__main__":
    raise SystemExit(main())
