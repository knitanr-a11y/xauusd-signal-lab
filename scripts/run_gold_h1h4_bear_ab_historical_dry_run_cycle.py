#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""Historical dry-run replay cycle for GOLD bearish A/B classifier.

Purpose
-------
This script validates the positive/signal path without waiting for a live signal.
It replays a specific historical M15 close_time as if it were the latest confirmed
M15 bar, writes the same dedicated SELL dry-run artifacts, then runs the M1
position monitor once.

This is test/research only.
It does not send Discord messages, place MT5 orders, update Mochipoyo state,
write Mochipoyo ledgers, or write existing autotrade order-intent files.

Recommended separate output directory:
    data/research_results/gold_h1h4_bear_ab_historical_replay

Example known target from research:
    python scripts\run_gold_h1h4_bear_ab_historical_dry_run_cycle.py ^
      --csv-dir "C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files" ^
      --out-dir data\research_results\gold_h1h4_bear_ab_historical_replay ^
      --as-of-m15-close-time "2026-04-28 08:15:00"

Why close_time 08:15?
    The signal bar is M15 time 08:00, and the confirmed close_time is 08:15.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

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

DEFAULT_OUT_DIR = Path("data/research_results/gold_h1h4_bear_ab_historical_replay")

LOG_COLUMNS = [
    "scan_time_utc",
    "condition_family_id",
    "condition_id",
    "csv_dir",
    "as_of_m15_close_time",
    "target_m15_bar_time",
    "signal_found",
    "rank",
    "a_pass",
    "b_pass",
    "trade_enabled",
    "duplicate",
    "signal_key",
    "reason",
]

CYCLE_LOG_COLUMNS = [
    "cycle_start_utc",
    "cycle_end_utc",
    "condition_family_id",
    "csv_dir",
    "out_dir",
    "as_of_m15_close_time",
    "signal_found",
    "rank",
    "a_pass",
    "b_pass",
    "trade_enabled",
    "duplicate",
    "signal_key",
    "position_monitor_returncode",
    "cycle_ok",
    "monitor_signals_monitored",
    "monitor_close_intent_created",
    "monitor_reason",
    "monitor_open_unresolved",
    "monitor_tp_touched",
    "monitor_sl_touched",
    "monitor_time_exit_required",
    "monitor_no_m1_path",
    "monitor_stdout_log",
    "monitor_stderr_log",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Replay one historical M15 close_time through GOLD bearish A/B dry-run lifecycle.")
    parser.add_argument("--csv-dir", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--as-of-m15-close-time", type=str, required=True, help="Historical confirmed M15 close_time, e.g. '2026-04-28 08:15:00'.")
    parser.add_argument("--sl-usd", type=float, default=10.0)
    parser.add_argument("--tp-usd", type=float, default=20.0)
    parser.add_argument("--rr", type=float, default=2.0)
    parser.add_argument("--horizon-hours", type=float, default=12.0)
    parser.add_argument("--base-lot", type=float, default=0.10)
    parser.add_argument("--core-lot-multiplier", type=float, default=2.0)
    parser.add_argument("--standard-lot-multiplier", type=float, default=1.0)
    parser.add_argument("--max-lot-per-trade", type=float, default=99.0)
    parser.add_argument("--inbar-priority", choices=["SL", "TP"], default="SL")
    parser.add_argument("--latest-confirmed-m1-policy", choices=["last", "second_last"], default="last")
    parser.add_argument("--observe-only-ledger", action="store_true", help="Also ledger A_ONLY_OBSERVE rows. Default ledgers only trade-enabled signals.")
    parser.add_argument("--reset-out-dir", action="store_true", help="Delete the output directory before replay. Use only for isolated historical test outputs.")
    parser.add_argument("--skip-monitor", action="store_true", help="Only build historical signal artifacts; do not run M1 position monitor.")
    return parser.parse_args()


def utc_now_text() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")


def utc_stamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%d_%H%M%S")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def append_csv_row(path: Path, row: dict[str, Any], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([{col: row.get(col, "") for col in columns}]).to_csv(
        path,
        mode="a",
        header=not path.exists(),
        index=False,
        encoding="utf-8-sig",
    )


def read_csv_or_empty(path: Path, columns: list[str] | None = None) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=columns or [])
    return pd.read_csv(path, encoding="utf-8-sig")


def read_json_or_empty(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"_read_error": str(exc), "_path": str(path)}


def ensure_ledger_columns(path: Path) -> pd.DataFrame:
    df = read_csv_or_empty(path, LEDGER_COLUMNS)
    for col in LEDGER_COLUMNS:
        if col not in df.columns:
            df[col] = ""
    return df[LEDGER_COLUMNS].copy()


def resolve_output_path(path: Path) -> Path:
    """Resolve output paths relative to the repository root.

    The script is normally executed from the repository root, but making this
    explicit prevents FileNotFoundError when subprocess logging uses relative
    paths after a reset-out-dir operation.
    """
    return path if path.is_absolute() else REPO_ROOT / path


def run_position_monitor(args: argparse.Namespace, log_dir: Path) -> tuple[int, Path, Path]:
    log_dir_abs = resolve_output_path(log_dir)
    log_dir_abs.mkdir(parents=True, exist_ok=True)

    cmd = [
        sys.executable,
        str(REPO_ROOT / "scripts" / "run_gold_h1h4_bear_ab_position_monitor_once.py"),
        "--csv-dir",
        str(args.csv_dir),
        "--out-dir",
        str(args.out_dir),
        "--max-hold-hours",
        str(args.horizon_hours),
        "--inbar-priority",
        str(args.inbar_priority),
        "--latest-confirmed-m1-policy",
        str(args.latest_confirmed_m1_policy),
    ]
    print("[INFO] running position_monitor")
    print("[CMD] " + " ".join(cmd))
    completed = subprocess.run(
        cmd,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    stamp = utc_stamp()
    stdout_path = log_dir_abs / f"historical_replay_{stamp}_position_monitor_stdout.txt"
    stderr_path = log_dir_abs / f"historical_replay_{stamp}_position_monitor_stderr.txt"
    stdout_path.parent.mkdir(parents=True, exist_ok=True)
    stdout_path.write_text(completed.stdout or "", encoding="utf-8")
    stderr_path.write_text(completed.stderr or "", encoding="utf-8")
    if completed.stdout:
        print(completed.stdout.rstrip())
    if completed.stderr:
        print(completed.stderr.rstrip(), file=sys.stderr)
    print(f"[INFO] position_monitor returncode={completed.returncode}")
    return int(completed.returncode), stdout_path, stderr_path


def select_historical_signal(live_flags: pd.DataFrame, as_of_close_time: pd.Timestamp) -> pd.DataFrame:
    target = live_flags[pd.to_datetime(live_flags["close_time"], errors="coerce") == as_of_close_time].copy()
    target = target[target["rank"] != "NO_SIGNAL"].copy()
    if target.empty:
        return target
    priority = {"CORE_AB_CONFIRM": 100, "B_ONLY_SAFE": 50, "A_ONLY_OBSERVE": 10}
    target["priority"] = target["rank"].map(priority).fillna(0)
    return target.sort_values(["priority", "close_time"], ascending=[False, True], kind="mergesort")


def main() -> int:
    args = parse_args()
    if args.reset_out_dir and args.out_dir.exists():
        shutil.rmtree(args.out_dir)
    args.out_dir.mkdir(parents=True, exist_ok=True)

    cycle_start = utc_now_text()
    as_of_close_time = pd.Timestamp(args.as_of_m15_close_time)
    result_path = args.out_dir / "latest_scan_result.json"
    ledger_path = args.out_dir / "signal_ledger.csv"
    live_log_path = args.out_dir / "historical_live_scan_log.csv"
    cycle_result_path = args.out_dir / "latest_historical_dry_run_cycle_result.json"
    cycle_log_path = args.out_dir / "historical_dry_run_cycle_log.csv"
    command_log_dir = args.out_dir / "historical_dry_run_command_logs"
    resolve_output_path(command_log_dir).mkdir(parents=True, exist_ok=True)

    print(f"[INFO] condition_family_id={CONDITION_FAMILY_ID}")
    print(f"[INFO] csv_dir={args.csv_dir}")
    print(f"[INFO] out_dir={args.out_dir}")
    print(f"[INFO] as_of_m15_close_time={as_of_close_time}")

    frames = load_frames(args.csv_dir)
    write_csv(build_data_coverage(frames), args.out_dir / "data_coverage.csv")

    d1 = add_indicators(frames["D1"], "D1")
    h4 = add_indicators(frames["H4"], "H4")
    h1 = add_indicators(frames["H1"], "H1")
    m15 = add_indicators(frames["M15"], "M15")
    m15_ctx = attach_context(m15, h1, h4, d1)

    # Keep both the backtest-style candidates and live-flag candidates for comparison.
    raw_backtest_style = build_signal_candidates(m15_ctx, args)
    write_csv(raw_backtest_style, args.out_dir / "historical_raw_candidates_backtest_style.csv")
    live_flags = compute_live_ab_flags(m15_ctx)
    write_csv(live_flags[live_flags["rank"] != "NO_SIGNAL"].copy(), args.out_dir / "historical_live_flag_candidates.csv")

    selected = select_historical_signal(live_flags, as_of_close_time)
    scan_time = utc_now_text()
    if selected.empty:
        m15_match = m15[pd.to_datetime(m15["close_time"], errors="coerce") == as_of_close_time].copy()
        target_bar_time = "" if m15_match.empty else str(pd.Timestamp(m15_match.iloc[0]["time"]))
        result = {
            "scan_time_utc": scan_time,
            "condition_family_id": CONDITION_FAMILY_ID,
            "condition_id": "",
            "csv_dir": str(args.csv_dir),
            "as_of_m15_close_time": str(as_of_close_time),
            "target_m15_bar_time": target_bar_time,
            "signal_found": False,
            "rank": "",
            "a_pass": False,
            "b_pass": False,
            "trade_enabled": False,
            "duplicate": False,
            "signal_key": "",
            "reason": "NO_SIGNAL_ON_AS_OF_M15_CLOSE_TIME" if not m15_match.empty else "AS_OF_M15_CLOSE_TIME_NOT_FOUND",
        }
        write_json(result_path, result)
        append_csv_row(live_log_path, result, LOG_COLUMNS)
        monitor_result = {}
        monitor_rc: int | str = "SKIPPED"
        stdout_path = Path("")
        stderr_path = Path("")
        cycle_ok = True
    else:
        signal_row = force_live_entry_fields(selected.iloc[0], args)
        signal_key = build_signal_key(signal_row)
        payload = build_payload(signal_row)
        intent = build_order_intent(signal_row, dry_run=True)
        text = build_notification_text(payload)

        should_ledger = bool(signal_row.get("trade_enabled", False)) or bool(args.observe_only_ledger)
        ledger = ensure_ledger_columns(ledger_path)
        duplicate = signal_key in set(ledger["signal_key"].astype(str)) if not ledger.empty else False

        result = {
            "scan_time_utc": scan_time,
            "condition_family_id": CONDITION_FAMILY_ID,
            "condition_id": str(signal_row.get("condition_id", "")),
            "csv_dir": str(args.csv_dir),
            "as_of_m15_close_time": str(as_of_close_time),
            "target_m15_bar_time": str(signal_row.get("time", "")),
            "signal_found": True,
            "rank": str(signal_row.get("rank", "")),
            "a_pass": bool(signal_row.get("a_pass", False)),
            "b_pass": bool(signal_row.get("b_pass", False)),
            "trade_enabled": bool(signal_row.get("trade_enabled", False)),
            "duplicate": bool(duplicate),
            "signal_key": signal_key,
            "reason": "DUPLICATE_SIGNAL_KEY" if duplicate else ("NEW_HISTORICAL_DRY_RUN_SIGNAL_CREATED" if should_ledger else "OBSERVE_ONLY_SIGNAL_NOT_LEDGERED"),
            "lot_multiplier": float(signal_row.get("lot_multiplier", 0.0)),
            "effective_lot": float(signal_row.get("effective_lot", 0.0)),
        }

        write_json(result_path, result)
        write_json(args.out_dir / "latest_signal_payload.json", payload)
        write_json(args.out_dir / "order_intent_dry_run.json", intent)
        (args.out_dir / "notification_preview_latest.txt").write_text(text + "\n", encoding="utf-8")
        append_csv_row(live_log_path, result, LOG_COLUMNS)

        if should_ledger and not duplicate:
            ledger_row = {
                "created_at_utc": scan_time,
                "signal_key": signal_key,
                "condition_family_id": CONDITION_FAMILY_ID,
                "condition_id": str(signal_row.get("condition_id", "")),
                "symbol": SYMBOL,
                "direction": DIRECTION,
                "rank": str(signal_row.get("rank", "")),
                "signal_group": str(signal_row.get("signal_group", "")),
                "signal_time": str(signal_row.get("signal_time", "")),
                "entry_time": str(signal_row.get("entry_time", "")),
                "entry_price_reference": float(signal_row.get("entry_price", 0.0)),
                "sl_price": float(signal_row.get("sl_price", 0.0)),
                "tp_price": float(signal_row.get("tp_price", 0.0)),
                "risk_price": float(signal_row.get("risk_price", 0.0)),
                "reward_price": float(signal_row.get("reward_price", 0.0)),
                "rr": float(signal_row.get("rr", 2.0)),
                "max_hold_hours": float(signal_row.get("max_hold_hours", 12.0)),
                "a_pass": bool(signal_row.get("a_pass", False)),
                "b_pass": bool(signal_row.get("b_pass", False)),
                "trade_enabled": bool(signal_row.get("trade_enabled", False)),
                "base_lot": float(signal_row.get("base_lot", 0.0)),
                "lot_multiplier": float(signal_row.get("lot_multiplier", 0.0)),
                "effective_lot": float(signal_row.get("effective_lot", 0.0)),
                "status": "DRY_RUN_SIGNAL_CREATED" if bool(signal_row.get("trade_enabled", False)) else "OBSERVE_ONLY_SIGNAL",
            }
            append_csv_row(ledger_path, ledger_row, LEDGER_COLUMNS)

        print(f"[INFO] historical signal_found rank={result['rank']} duplicate={duplicate} trade_enabled={result['trade_enabled']}")
        print(text)

        if args.skip_monitor:
            monitor_result = {}
            monitor_rc = "SKIPPED"
            stdout_path = Path("")
            stderr_path = Path("")
            cycle_ok = True
        else:
            monitor_rc, stdout_path, stderr_path = run_position_monitor(args, command_log_dir)
            monitor_result = read_json_or_empty(args.out_dir / "latest_position_monitor_result.json")
            cycle_ok = int(monitor_rc) == 0

    cycle_end = utc_now_text()
    cycle_row = {
        "cycle_start_utc": cycle_start,
        "cycle_end_utc": cycle_end,
        "condition_family_id": CONDITION_FAMILY_ID,
        "csv_dir": str(args.csv_dir),
        "out_dir": str(args.out_dir),
        "as_of_m15_close_time": str(as_of_close_time),
        "signal_found": result.get("signal_found", ""),
        "rank": result.get("rank", ""),
        "a_pass": result.get("a_pass", ""),
        "b_pass": result.get("b_pass", ""),
        "trade_enabled": result.get("trade_enabled", ""),
        "duplicate": result.get("duplicate", ""),
        "signal_key": result.get("signal_key", ""),
        "position_monitor_returncode": monitor_rc,
        "cycle_ok": bool(cycle_ok),
        "monitor_signals_monitored": monitor_result.get("signals_monitored", ""),
        "monitor_close_intent_created": monitor_result.get("close_intent_created", ""),
        "monitor_reason": monitor_result.get("reason", ""),
        "monitor_open_unresolved": monitor_result.get("open_unresolved", ""),
        "monitor_tp_touched": monitor_result.get("tp_touched", ""),
        "monitor_sl_touched": monitor_result.get("sl_touched", ""),
        "monitor_time_exit_required": monitor_result.get("time_exit_required", ""),
        "monitor_no_m1_path": monitor_result.get("no_m1_path", ""),
        "monitor_stdout_log": str(stdout_path) if stdout_path else "",
        "monitor_stderr_log": str(stderr_path) if stderr_path else "",
    }
    append_csv_row(cycle_log_path, cycle_row, CYCLE_LOG_COLUMNS)

    cycle_payload = {
        "schema_version": "gold_h1h4_bear_ab_classifier_historical_dry_run_cycle_v1",
        "cycle_start_utc": cycle_start,
        "cycle_end_utc": cycle_end,
        "condition_family_id": CONDITION_FAMILY_ID,
        "csv_dir": str(args.csv_dir),
        "out_dir": str(args.out_dir),
        "as_of_m15_close_time": str(as_of_close_time),
        "cycle_ok": bool(cycle_ok),
        "historical_live_scan_result": result,
        "position_monitor_returncode": monitor_rc,
        "position_monitor_result": monitor_result,
        "outputs": {
            "latest_scan_result": str(result_path),
            "historical_live_scan_log": str(live_log_path),
            "signal_ledger": str(ledger_path),
            "latest_historical_dry_run_cycle_result": str(cycle_result_path),
            "historical_dry_run_cycle_log": str(cycle_log_path),
            "monitor_stdout_log": str(stdout_path) if stdout_path else "",
            "monitor_stderr_log": str(stderr_path) if stderr_path else "",
        },
    }
    write_json(cycle_result_path, cycle_payload)
    print("[INFO] historical dry-run cycle completed")
    print(json.dumps(cycle_payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if cycle_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
