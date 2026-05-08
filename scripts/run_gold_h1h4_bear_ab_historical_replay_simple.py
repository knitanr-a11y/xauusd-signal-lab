#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Simple historical replay for GOLD bearish A/B classifier.

This avoids long Windows command-log paths. It replays one historical M15
close_time, writes signal_ledger/previews, then calls the M1 position monitor.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.research_gold_h1h4_bear_m15_low_break_ab_classifier import (  # noqa: E402
    CONDITION_FAMILY_ID,
    DIRECTION,
    LEDGER_COLUMNS,
    SYMBOL,
    add_indicators,
    attach_context,
    build_data_coverage,
    build_notification_text,
    build_payload,
    build_signal_candidates,
    build_signal_key,
    load_frames,
    write_csv,
)
from scripts.run_gold_h1h4_bear_ab_live_scan_once import (  # noqa: E402
    build_order_intent,
    compute_live_ab_flags,
    force_live_entry_fields,
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--csv-dir", type=Path, required=True)
    p.add_argument("--out-dir", type=Path, default=Path("data/research_results/gold_h1h4_bear_ab_historical_replay_simple"))
    p.add_argument("--as-of-m15-close-time", required=True)
    p.add_argument("--reset-out-dir", action="store_true")
    p.add_argument("--sl-usd", type=float, default=10.0)
    p.add_argument("--tp-usd", type=float, default=20.0)
    p.add_argument("--rr", type=float, default=2.0)
    p.add_argument("--horizon-hours", type=float, default=12.0)
    p.add_argument("--base-lot", type=float, default=0.10)
    p.add_argument("--core-lot-multiplier", type=float, default=2.0)
    p.add_argument("--standard-lot-multiplier", type=float, default=1.0)
    p.add_argument("--max-lot-per-trade", type=float, default=99.0)
    p.add_argument("--inbar-priority", choices=["SL", "TP"], default="SL")
    p.add_argument("--latest-confirmed-m1-policy", choices=["last", "second_last"], default="last")
    p.add_argument("--skip-monitor", action="store_true")
    return p.parse_args()


def now_utc() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")


def repo_abs(path: Path) -> Path:
    return path if path.is_absolute() else REPO_ROOT / path


def write_json(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def append_row(path: Path, row: dict, columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([{c: row.get(c, "") for c in columns}]).to_csv(path, mode="a", header=not path.exists(), index=False, encoding="utf-8-sig")


def main() -> int:
    args = parse_args()
    out_dir = repo_abs(args.out_dir)
    if args.reset_out_dir and out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    asof = pd.Timestamp(args.as_of_m15_close_time)
    print(f"[INFO] condition_family_id={CONDITION_FAMILY_ID}")
    print(f"[INFO] out_dir={out_dir}")
    print(f"[INFO] as_of_m15_close_time={asof}")

    frames = load_frames(args.csv_dir)
    write_csv(build_data_coverage(frames), out_dir / "data_coverage.csv")
    d1 = add_indicators(frames["D1"], "D1")
    h4 = add_indicators(frames["H4"], "H4")
    h1 = add_indicators(frames["H1"], "H1")
    m15 = add_indicators(frames["M15"], "M15")
    ctx = attach_context(m15, h1, h4, d1)
    write_csv(build_signal_candidates(ctx, args), out_dir / "historical_raw_candidates_backtest_style.csv")
    flags = compute_live_ab_flags(ctx)
    write_csv(flags[flags["rank"] != "NO_SIGNAL"], out_dir / "historical_live_flag_candidates.csv")

    target = flags[pd.to_datetime(flags["close_time"], errors="coerce").eq(asof)].copy()
    target = target[target["rank"] != "NO_SIGNAL"].copy()
    if target.empty:
        result = {"signal_found": False, "condition_family_id": CONDITION_FAMILY_ID, "as_of_m15_close_time": str(asof), "reason": "NO_SIGNAL_ON_AS_OF_M15_CLOSE_TIME"}
        write_json(out_dir / "latest_historical_replay_simple_result.json", result)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    priority = {"CORE_AB_CONFIRM": 100, "B_ONLY_SAFE": 50, "A_ONLY_OBSERVE": 10}
    target["priority"] = target["rank"].map(priority).fillna(0)
    row = force_live_entry_fields(target.sort_values("priority", ascending=False).iloc[0], args)
    payload = build_payload(row)
    intent = build_order_intent(row, dry_run=True)
    text = build_notification_text(payload)
    key = build_signal_key(row)
    scan_time = now_utc()

    result = {
        "scan_time_utc": scan_time,
        "condition_family_id": CONDITION_FAMILY_ID,
        "condition_id": str(row["condition_id"]),
        "signal_found": True,
        "rank": str(row["rank"]),
        "a_pass": bool(row["a_pass"]),
        "b_pass": bool(row["b_pass"]),
        "trade_enabled": bool(row["trade_enabled"]),
        "signal_key": key,
        "lot_multiplier": float(row["lot_multiplier"]),
        "effective_lot": float(row["effective_lot"]),
        "as_of_m15_close_time": str(asof),
    }
    write_json(out_dir / "latest_scan_result.json", result)
    write_json(out_dir / "latest_signal_payload.json", payload)
    write_json(out_dir / "order_intent_dry_run.json", intent)
    (out_dir / "notification_preview_latest.txt").write_text(text + "\n", encoding="utf-8")

    if bool(row["trade_enabled"]):
        ledger_row = {
            "created_at_utc": scan_time,
            "signal_key": key,
            "condition_family_id": CONDITION_FAMILY_ID,
            "condition_id": str(row["condition_id"]),
            "symbol": SYMBOL,
            "direction": DIRECTION,
            "rank": str(row["rank"]),
            "signal_group": str(row["signal_group"]),
            "signal_time": str(row["signal_time"]),
            "entry_time": str(row["entry_time"]),
            "entry_price_reference": float(row["entry_price"]),
            "sl_price": float(row["sl_price"]),
            "tp_price": float(row["tp_price"]),
            "risk_price": float(row["risk_price"]),
            "reward_price": float(row["reward_price"]),
            "rr": float(row["rr"]),
            "max_hold_hours": float(row["max_hold_hours"]),
            "a_pass": bool(row["a_pass"]),
            "b_pass": bool(row["b_pass"]),
            "trade_enabled": bool(row["trade_enabled"]),
            "base_lot": float(row["base_lot"]),
            "lot_multiplier": float(row["lot_multiplier"]),
            "effective_lot": float(row["effective_lot"]),
            "status": "DRY_RUN_SIGNAL_CREATED",
        }
        append_row(out_dir / "signal_ledger.csv", ledger_row, LEDGER_COLUMNS)

    print(text)

    monitor = {}
    rc: int | str = "SKIPPED"
    if not args.skip_monitor:
        cmd = [
            sys.executable,
            str(REPO_ROOT / "scripts" / "run_gold_h1h4_bear_ab_position_monitor_once.py"),
            "--csv-dir", str(args.csv_dir),
            "--out-dir", str(out_dir),
            "--max-hold-hours", str(args.horizon_hours),
            "--inbar-priority", str(args.inbar_priority),
            "--latest-confirmed-m1-policy", str(args.latest_confirmed_m1_policy),
        ]
        print("[CMD] " + " ".join(cmd))
        completed = subprocess.run(cmd, cwd=str(REPO_ROOT), text=True, encoding="utf-8", errors="replace")
        rc = completed.returncode
        p = out_dir / "latest_position_monitor_result.json"
        if p.exists():
            monitor = json.loads(p.read_text(encoding="utf-8"))

    final = {"cycle_ok": rc == 0 or rc == "SKIPPED", "position_monitor_returncode": rc, "historical_live_scan_result": result, "position_monitor_result": monitor}
    write_json(out_dir / "latest_historical_replay_simple_result.json", final)
    print(json.dumps(final, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if final["cycle_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
