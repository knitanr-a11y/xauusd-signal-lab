#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from gold_v3_291_stage286_external_live import detect_stage286_candidates

READY = "GOLD_V3_291_STAGE286_EXTERNAL_LIVE_M15_READY"
BLOCKED = "GOLD_V3_291_STAGE286_EXTERNAL_LIVE_M15_BLOCKED"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace(
        "+00:00", "Z"
    )


def save_csv(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    frame.to_csv(temp, index=False, encoding="utf-8-sig")
    temp.replace(path)


def save_json(value: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    temp.replace(path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Validate US100/US500 closed M15 files and detect Stage286 "
            "strict SHORT live candidates."
        )
    )
    parser.add_argument("--candle-dir", required=True)
    parser.add_argument("--output-dir", default="")
    parser.add_argument("--lookback-hours", type=int, default=96)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    candle_dir = Path(args.candle_dir).expanduser().resolve()
    output_dir = (
        Path(args.output_dir).expanduser().resolve()
        if args.output_dir
        else candle_dir
        / "FX_OUTPUTS"
        / "gold_v3"
        / "291_stage286_external_live_m15"
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        candidates, snapshot, meta = detect_stage286_candidates(
            candle_dir, lookback_hours=args.lookback_hours
        )
        checks = pd.DataFrame(meta.pop("checks"))
        latest_live = (
            candidates[candidates.is_latest_live_trigger.astype(bool)].copy()
            if len(candidates)
            else pd.DataFrame()
        )
        summary = {
            "status": READY,
            "ready": True,
            "created_at_utc": now_utc(),
            **meta,
            "latest_condition_pass": bool(
                snapshot.iloc[-1].stage286_condition_pass
            )
            if len(snapshot)
            else False,
            "latest_live_candidate": bool(len(latest_live)),
            "mt5_order_enabled": False,
            "discord_enabled": False,
        }
        save_csv(
            checks,
            output_dir / "gold_v3_291_external_m15_validation.csv",
        )
        save_csv(
            snapshot,
            output_dir / "gold_v3_291_stage286_latest_gate_snapshot.csv",
        )
        save_csv(
            candidates,
            output_dir / "gold_v3_291_stage286_live_candidates.csv",
        )
        save_csv(
            latest_live,
            output_dir / "gold_v3_291_stage286_latest_live_candidate.csv",
        )
        save_json(summary, output_dir / "gold_v3_291_summary.json")
        print(json.dumps(summary, ensure_ascii=False, indent=2, default=str))
        return 0
    except Exception as exc:
        summary = {
            "status": BLOCKED,
            "ready": False,
            "created_at_utc": now_utc(),
            "error": repr(exc),
            "mt5_order_enabled": False,
            "discord_enabled": False,
        }
        save_csv(
            pd.DataFrame(),
            output_dir / "gold_v3_291_stage286_latest_live_candidate.csv",
        )
        save_json(summary, output_dir / "gold_v3_291_summary.json")
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
