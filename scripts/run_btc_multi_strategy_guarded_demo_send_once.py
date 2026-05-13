#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""Guarded demo-send once wrapper for BTC multi-strategy sidecar flow.

Stage 1: run BTC multi-strategy dry-run cycle.  This builds order_payloads.csv
         but never calls MT5.
Stage 2: if payload rows exist, call send_mt5_order_from_payload.py in guarded
         mode.  Sender receives --send only when BOTH flags are present:

             --allow-demo-send
             --send

No-payload cycles are a normal safe waiting state.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CSV_DIR = Path(r"C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files")
DEFAULT_OUT_DIR = Path("data/research_results/btc_multi_strategy_guarded_demo_send_once")
SUMMARY_FILENAME = "latest_btc_multi_strategy_guarded_demo_send_once_result.json"

LOG_COLUMNS = [
    "cycle_start_utc", "cycle_end_utc", "cycle_ok", "cycle_ok_classification", "reason",
    "allow_demo_send", "send_requested", "send_flag_passed_to_sender", "send_suppressed_reason",
    "payload_rows_out", "guarded_sender_returncode", "guarded_sender_rows_out",
    "guarded_sender_dry_run_check_ok_rows", "guarded_sender_sent_rows", "guarded_sender_error_rows",
    "guarded_sender_order_send_called_count", "dry_run_cycle_returncode", "dry_run_cycle_ok",
    "dry_run_cycle_summary_json", "summary_json", "total_seconds",
]


def windows_long_path(path: str | Path) -> str:
    p = Path(path)
    if os.name != "nt":
        return str(p)
    text = str(p.resolve())
    if text.startswith("\\\\?\\"):
        return text
    if text.startswith("\\\\"):
        return "\\\\?\\UNC\\" + text.lstrip("\\")
    return "\\\\?\\" + text


def mkdir_path(path: Path) -> None:
    Path(windows_long_path(path)).mkdir(parents=True, exist_ok=True)


def ensure_parent_dir(path: Path) -> None:
    mkdir_path(path.parent)


def write_text(path: Path, text: str) -> None:
    ensure_parent_dir(path)
    with open(windows_long_path(path), "w", encoding="utf-8", newline="") as f:
        f.write(text)


def write_json(path: Path, obj: dict[str, Any]) -> None:
    write_text(path, json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True, default=str))


def read_json_or_empty(path: Path) -> dict[str, Any]:
    try:
        with open(windows_long_path(path), "r", encoding="utf-8") as f:
            obj = json.load(f)
        return obj if isinstance(obj, dict) else {}
    except FileNotFoundError:
        return {}
    except Exception as exc:
        return {"_read_error": str(exc), "_path": str(path)}


def append_csv_row(path: Path, row: dict[str, Any], columns: list[str]) -> None:
    ensure_parent_dir(path)
    df = pd.DataFrame([{col: row.get(col, "") for col in columns}])
    df.to_csv(windows_long_path(path), mode="a", header=not Path(windows_long_path(path)).exists(), index=False, encoding="utf-8-sig")


def payload_rows_count(path: Path) -> int:
    if not Path(windows_long_path(path)).exists():
        return 0
    try:
        return int(len(pd.read_csv(windows_long_path(path), encoding="utf-8-sig")))
    except Exception:
        return 0


def utc_now_text() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")


def safe_int(obj: dict[str, Any], key: str, default: int = 0) -> int:
    try:
        return int(obj.get(key, default) or 0)
    except Exception:
        try:
            return int(float(obj.get(key, default)))
        except Exception:
            return default


def safe_bool(obj: dict[str, Any], key: str, default: bool = False) -> bool:
    val = obj.get(key, default)
    if isinstance(val, bool):
        return val
    if val is None:
        return default
    return str(val).strip().lower() in {"true", "1", "yes", "y"}


def run_cmd(label: str, cmd: list[str], cwd: Path = REPO_ROOT) -> tuple[int, float]:
    print("=" * 80, flush=True)
    print(f"[STEP] {label}", flush=True)
    print("[CMD] " + " ".join(cmd), flush=True)
    started = time.perf_counter()
    completed = subprocess.run(cmd, cwd=str(cwd), text=True, encoding="utf-8", errors="replace")
    elapsed = round(time.perf_counter() - started, 3)
    print(f"[STEP] {label} returncode={completed.returncode} elapsed_seconds={elapsed}", flush=True)
    return int(completed.returncode), elapsed


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run guarded demo-send once wrapper for BTC multi-strategy sidecar flow.")
    p.add_argument("--csv-dir", type=Path, default=DEFAULT_CSV_DIR)
    p.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    p.add_argument("--csv-sep", default="auto")
    p.add_argument("--btc-m15-csv")
    p.add_argument("--btc-h1-csv")
    p.add_argument("--btc-h4-csv")
    p.add_argument("--btc-d1-csv")
    p.add_argument("--broker-symbol", default="BTCUSD#")
    p.add_argument("--expected-login", type=int, default=75539039)
    p.add_argument("--require-demo-account", action=argparse.BooleanOptionalAction, default=True)
    p.add_argument("--base-lot", type=float, default=0.01)
    p.add_argument("--spread-cost-usd", type=float, default=22.5)
    p.add_argument("--rr", type=float, default=2.0)
    p.add_argument("--horizon-hours", type=int, default=72)
    p.add_argument("--magic", type=int, default=26050604)
    p.add_argument("--max-orders", type=int, default=1)
    p.add_argument("--deviation", type=int, default=100)
    p.add_argument("--position-policy", choices=["block_any", "allow_same_direction", "allow_any_until_max"], default="allow_any_until_max")
    p.add_argument("--max-symbol-positions", type=int, default=20)
    p.add_argument("--max-symbol-lot", type=float, default=1.0)
    p.add_argument("--latest-confirmed-policy", choices=["last", "second_last"], default="last")
    p.add_argument("--live-lookback-bars", type=int, default=1)
    p.add_argument("--cooldown-bars-m15", type=int, default=16)
    p.add_argument("--allow-demo-send", action="store_true")
    p.add_argument("--send", action="store_true")
    p.add_argument("--enable-sell-early-low-break-trade", action=argparse.BooleanOptionalAction, default=False)
    return p.parse_args()


def build_dry_run_cmd(args: argparse.Namespace, dry_out_dir: Path) -> list[str]:
    cmd = [
        sys.executable, str(REPO_ROOT / "scripts" / "run_btc_multi_strategy_dry_run_cycle.py"),
        "--csv-dir", str(args.csv_dir), "--out-dir", str(dry_out_dir), "--csv-sep", str(args.csv_sep),
        "--broker-symbol", str(args.broker_symbol), "--base-lot", str(args.base_lot),
        "--spread-cost-usd", str(args.spread_cost_usd), "--rr", str(args.rr),
        "--horizon-hours", str(args.horizon_hours), "--magic", str(args.magic),
        "--latest-confirmed-policy", str(args.latest_confirmed_policy), "--live-lookback-bars", str(args.live_lookback_bars),
        "--max-payload-rows", str(args.max_orders), "--cooldown-bars-m15", str(args.cooldown_bars_m15),
    ]
    for arg_name, flag in [("btc_m15_csv", "--btc-m15-csv"), ("btc_h1_csv", "--btc-h1-csv"), ("btc_h4_csv", "--btc-h4-csv"), ("btc_d1_csv", "--btc-d1-csv")]:
        value = getattr(args, arg_name, None)
        if value:
            cmd.extend([flag, str(value)])
    cmd.append("--enable-sell-early-low-break-trade" if args.enable_sell_early_low_break_trade else "--no-enable-sell-early-low-break-trade")
    return cmd


def decide_send_suppression(args: argparse.Namespace, payload_rows: int) -> tuple[bool, str]:
    if not args.send:
        return False, "SEND_NOT_REQUESTED"
    if not args.allow_demo_send:
        return False, "ALLOW_DEMO_SEND_NOT_SET"
    if payload_rows <= 0:
        return False, "NO_PAYLOAD_ROWS"
    if payload_rows > int(args.max_orders):
        return False, f"PAYLOAD_ROWS_EXCEED_MAX_ORDERS payload_rows={payload_rows}; max_orders={args.max_orders}"
    if payload_rows > 1:
        return False, "INITIAL_GUARD_BLOCKS_MORE_THAN_ONE_PAYLOAD_ROW"
    return True, ""


def build_guarded_sender_cmd(args: argparse.Namespace, paths: dict[str, Path], *, pass_send: bool) -> list[str]:
    cmd = [
        sys.executable, str(REPO_ROOT / "scripts" / "send_mt5_order_from_payload.py"),
        "--input-csv", str(paths["payload_csv"]), "--order-ledger-csv", str(paths["guarded_order_ledger_csv"]),
        "--out-dir", str(paths["guarded_sender_out_dir"]), "--symbol", str(args.broker_symbol),
        "--max-orders", str(args.max_orders), "--deviation", str(args.deviation),
        "--position-policy", str(args.position_policy), "--max-symbol-positions", str(args.max_symbol_positions),
        "--max-symbol-lot", str(args.max_symbol_lot), "--select-symbol", "--expected-login", str(args.expected_login),
        "--registry-preview-out-csv", str(paths["registry_preview_csv"]),
        "--registry-preview-out-json", str(paths["registry_preview_json"]),
    ]
    if args.require_demo_account:
        cmd.append("--require-demo-account")
    if pass_send:
        cmd.append("--send")
    return cmd


def main() -> int:
    args = parse_args()
    started_perf = time.perf_counter()
    cycle_start = utc_now_text()
    mkdir_path(args.out_dir)

    paths = {
        "dry_out_dir": args.out_dir / "dry_run_stage",
        "payload_csv": args.out_dir / "dry_run_stage" / "payload" / "order_payloads.csv",
        "guarded_sender_out_dir": args.out_dir / "guarded_sender",
        "guarded_order_ledger_csv": args.out_dir / "guarded_demo_order_ledger.csv",
        "registry_preview_csv": args.out_dir / "registry_preview" / "registry_preview.csv",
        "registry_preview_json": args.out_dir / "registry_preview" / "registry_preview.json",
        "summary_json": args.out_dir / SUMMARY_FILENAME,
        "cycle_log_csv": args.out_dir / "btc_multi_strategy_guarded_demo_send_once_log.csv",
    }

    print("=" * 80, flush=True)
    print("BTC multi-strategy guarded demo-send ONCE wrapper", flush=True)
    print("Default is no-send. Sender receives --send only with BOTH --allow-demo-send and --send.", flush=True)
    print(f"csv_dir={args.csv_dir}", flush=True)
    print(f"out_dir={args.out_dir}", flush=True)
    print(f"allow_demo_send={args.allow_demo_send} send_requested={args.send}", flush=True)
    print("=" * 80, flush=True)

    dry_rc, dry_seconds = run_cmd("btc_dry_run_cycle", build_dry_run_cmd(args, paths["dry_out_dir"]))
    dry_summary = read_json_or_empty(paths["dry_out_dir"] / "latest_btc_multi_strategy_dry_run_cycle_result.json")
    dry_cycle_ok = bool(dry_rc == 0 and safe_bool(dry_summary, "cycle_ok", False))
    payload_rows = payload_rows_count(paths["payload_csv"])

    pass_send, suppressed_reason = decide_send_suppression(args, payload_rows)
    guarded_sender_rc: int | str = "SKIPPED"
    guarded_seconds = 0.0
    guarded_report: dict[str, Any] = {}

    if not dry_cycle_ok:
        guarded_sender_rc = "SKIPPED_DRY_RUN_FAILED"
        guarded_report = {"rows_out": 0, "dry_run_check_ok_rows": 0, "sent_rows": 0, "error_rows": 0, "order_send_called_count": 0, "reason": "DRY_RUN_CYCLE_FAILED"}
        print("[SAFETY] dry run cycle failed; guarded sender skipped", flush=True)
    elif payload_rows <= 0:
        guarded_sender_rc = "SKIPPED_NO_PAYLOAD_ROWS"
        guarded_report = {"rows_out": 0, "dry_run_check_ok_rows": 0, "sent_rows": 0, "error_rows": 0, "order_send_called_count": 0, "reason": "NO_PAYLOAD_ROWS"}
        print("[INFO] guarded sender skipped because payload rows are 0", flush=True)
    else:
        guarded_sender_rc, guarded_seconds = run_cmd("guarded_sender", build_guarded_sender_cmd(args, paths, pass_send=pass_send))
        guarded_report = read_json_or_empty(paths["guarded_sender_out_dir"] / "mt5_order_send_report.json")

    cycle_end = utc_now_text()
    sender_order_send_called_count = safe_int(guarded_report, "order_send_called_count", 0)
    sender_sent_rows = safe_int(guarded_report, "sent_rows", 0)
    sender_error_rows = safe_int(guarded_report, "error_rows", 0)
    sender_rows_out = safe_int(guarded_report, "rows_out", 0)
    sender_dry_run_ok = safe_int(guarded_report, "dry_run_check_ok_rows", 0)

    safe_no_payload_ok = bool(dry_cycle_ok and payload_rows == 0 and not pass_send and sender_order_send_called_count == 0 and sender_sent_rows == 0)
    dry_run_sender_ok = bool(dry_cycle_ok and payload_rows > 0 and not pass_send and guarded_sender_rc == 0 and sender_order_send_called_count == 0 and sender_sent_rows == 0 and sender_dry_run_ok >= 1)
    sent_ok = bool(dry_cycle_ok and payload_rows > 0 and pass_send and guarded_sender_rc == 0 and sender_order_send_called_count == 1 and sender_sent_rows == 1 and sender_error_rows == 0)
    cycle_ok = bool(safe_no_payload_ok or dry_run_sender_ok or sent_ok)
    cycle_ok_classification = "SAFE_NO_PAYLOAD_PASS" if safe_no_payload_ok else ("DRY_RUN_ORDER_CHECK_PASS" if dry_run_sender_ok else ("SENT_PASS" if sent_ok else "FAILED"))
    reason = "BTC_MULTI_STRATEGY_GUARDED_DEMO_SEND_ONCE_PASS" if cycle_ok else "BTC_MULTI_STRATEGY_GUARDED_DEMO_SEND_ONCE_FAILED"
    if safe_no_payload_ok:
        reason = "BTC_MULTI_STRATEGY_GUARDED_DEMO_SEND_ONCE_SAFE_NO_PAYLOAD_PASS"

    summary = {
        "schema_version": "btc_multi_strategy_guarded_demo_send_once_v1",
        "cycle_start_utc": cycle_start,
        "cycle_end_utc": cycle_end,
        "cycle_ok": bool(cycle_ok),
        "cycle_ok_classification": cycle_ok_classification,
        "reason": reason,
        "allow_demo_send": bool(args.allow_demo_send),
        "send_requested": bool(args.send),
        "send_flag_passed_to_sender": bool(pass_send),
        "send_suppressed_reason": suppressed_reason,
        "guards": {
            "expected_login": int(args.expected_login), "require_demo_account": bool(args.require_demo_account),
            "broker_symbol": str(args.broker_symbol), "base_lot": float(args.base_lot),
            "spread_cost_usd": float(args.spread_cost_usd), "max_orders": int(args.max_orders),
            "position_policy": str(args.position_policy), "max_symbol_positions": int(args.max_symbol_positions),
            "max_symbol_lot": float(args.max_symbol_lot), "deviation": int(args.deviation),
            "early_low_break_trade_enabled": bool(args.enable_sell_early_low_break_trade),
            "cooldown_bars_m15": int(args.cooldown_bars_m15),
        },
        "returncodes": {"dry_run_cycle": dry_rc, "guarded_sender": guarded_sender_rc},
        "key_metrics": {
            "dry_run_cycle_ok": dry_cycle_ok,
            "payload_rows_out": int(payload_rows),
            "guarded_sender_rows_out": sender_rows_out,
            "guarded_sender_dry_run_check_ok_rows": sender_dry_run_ok,
            "guarded_sender_sent_rows": sender_sent_rows,
            "guarded_sender_error_rows": sender_error_rows,
            "guarded_sender_order_send_called_count": sender_order_send_called_count,
        },
        "safety": {
            "dry_run_cycle_mt5_called": False, "guarded_sender_send_flag_passed": bool(pass_send),
            "production_registry_mutated": False, "existing_gold_bat_modified": False,
            "gold_ledgers_mutated": False, "trigger_state_mutated": False,
        },
        "timing": {"dry_run_cycle_seconds": dry_seconds, "guarded_sender_seconds": guarded_seconds, "total_seconds": round(time.perf_counter() - started_perf, 3)},
        "paths": {k: str(v) for k, v in paths.items()},
        "dry_run_summary": dry_summary,
        "guarded_sender_report": guarded_report,
    }
    write_json(paths["summary_json"], summary)
    row = {
        "cycle_start_utc": cycle_start, "cycle_end_utc": cycle_end, "cycle_ok": cycle_ok,
        "cycle_ok_classification": cycle_ok_classification, "reason": reason,
        "allow_demo_send": bool(args.allow_demo_send), "send_requested": bool(args.send),
        "send_flag_passed_to_sender": bool(pass_send), "send_suppressed_reason": suppressed_reason,
        "payload_rows_out": int(payload_rows), "guarded_sender_returncode": guarded_sender_rc,
        "guarded_sender_rows_out": sender_rows_out, "guarded_sender_dry_run_check_ok_rows": sender_dry_run_ok,
        "guarded_sender_sent_rows": sender_sent_rows, "guarded_sender_error_rows": sender_error_rows,
        "guarded_sender_order_send_called_count": sender_order_send_called_count,
        "dry_run_cycle_returncode": dry_rc, "dry_run_cycle_ok": dry_cycle_ok,
        "dry_run_cycle_summary_json": str(paths["dry_out_dir"] / "latest_btc_multi_strategy_dry_run_cycle_result.json"),
        "summary_json": str(paths["summary_json"]), "total_seconds": summary["timing"]["total_seconds"],
    }
    append_csv_row(paths["cycle_log_csv"], row, LOG_COLUMNS)

    print("=" * 80, flush=True)
    print("BTC multi-strategy guarded demo-send once summary", flush=True)
    print(json.dumps({
        "cycle_ok": cycle_ok, "cycle_ok_classification": cycle_ok_classification, "reason": reason,
        "allow_demo_send": bool(args.allow_demo_send), "send_requested": bool(args.send),
        "send_flag_passed_to_sender": bool(pass_send), "send_suppressed_reason": suppressed_reason,
        "key_metrics": summary["key_metrics"], "guards": summary["guards"], "summary_json": str(paths["summary_json"]),
    }, ensure_ascii=False, indent=2, sort_keys=True, default=str), flush=True)
    print("=" * 80, flush=True)
    return 0 if cycle_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
