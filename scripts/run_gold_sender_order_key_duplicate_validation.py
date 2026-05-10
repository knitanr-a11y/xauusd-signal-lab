#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""Validate sender blocks duplicate order_key without using symbol-wide block_any.

Purpose:
- GOLD integration policy allows multiple GOLD positions when they are generated
  by different strategy/signal/order keys.
- The sender must therefore be used with allow_any_until_max for the new
  multi-strategy path, while duplicate prevention must happen through order_key.
- This validation pre-populates the sender order ledger with a fixture order_key,
  then sends a payload with the same order_key in NO-SEND mode.
- PASS means the sender does not call order_send and the duplicate order_key is
  not treated as a valid dry-run order_check row.

Safety:
- NO --send is passed.
- order_send_called_count must remain 0.
- sent_rows must remain 0.
- position-policy is allow_any_until_max, not block_any.
- production registry is never written.
- This is not a strategy signal; it is a sender duplicate-key contract validation.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT_DIR = Path("data/r/gold_sender_order_key_duplicate_validation")
SUMMARY_FILENAME = "latest_gold_sender_order_key_duplicate_validation_result.json"

PAYLOAD_COLUMNS = [
    "payload_key",
    "order_key",
    "signal_key",
    "broker_symbol",
    "symbol",
    "direction",
    "lot",
    "entry_price_reference",
    "sl_price",
    "tp_price",
    "magic_number",
    "strategy_key",
    "strategy_alias",
    "strategy_id",
    "condition_id",
    "router_strategy_slot",
    "router_strategy_id",
    "candidate_rank",
    "source",
    "fixture_note",
]

LEDGER_COLUMNS = [
    "created_at_utc",
    "order_key",
    "payload_key",
    "signal_key",
    "broker_symbol",
    "symbol",
    "direction",
    "lot",
    "order_status",
    "order_send_called",
    "order_send_ok",
    "source",
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


def ensure_parent_dir(path: Path) -> None:
    Path(windows_long_path(path.parent)).mkdir(parents=True, exist_ok=True)


def write_text(path: Path, text: str) -> None:
    ensure_parent_dir(path)
    with open(windows_long_path(path), "w", encoding="utf-8", newline="") as f:
        f.write(text)


def write_json(path: Path, obj: dict[str, Any]) -> None:
    write_text(path, json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True, default=str))


def write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    ensure_parent_dir(path)
    with open(windows_long_path(path), "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({col: row.get(col, "") for col in columns})


def read_json_or_empty(path: Path) -> dict[str, Any]:
    try:
        with open(windows_long_path(path), "r", encoding="utf-8") as f:
            obj = json.load(f)
        return obj if isinstance(obj, dict) else {}
    except Exception as exc:
        return {"_read_error": str(exc), "_path": str(path)}


def read_csv_or_empty(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(windows_long_path(path), encoding="utf-8-sig")
    except Exception:
        return pd.DataFrame()


def utc_now_text() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")


def safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None or value == "":
            return default
        return int(value)
    except Exception:
        try:
            return int(float(value))
        except Exception:
            return default


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except Exception:
        return default


def build_fixture(order_key: str, *, symbol: str, direction: str, lot: float) -> dict[str, Any]:
    payload_key = f"{order_key}_PAYLOAD"
    signal_key = f"{order_key}_SIGNAL"
    return {
        "payload_key": payload_key,
        "order_key": order_key,
        "signal_key": signal_key,
        "broker_symbol": symbol,
        "symbol": symbol.replace("#", ""),
        "direction": direction,
        "lot": lot,
        "entry_price_reference": 4700.0,
        "sl_price": 1.0 if direction.upper() == "BUY" else 9999.0,
        "tp_price": 9999.0 if direction.upper() == "BUY" else 1.0,
        "magic_number": 26050607,
        "strategy_key": "BUY_C_ENV_RR2_72H" if direction.upper() == "BUY" else "SELL_H1H4_BEAR_AB",
        "strategy_alias": "BUY_C" if direction.upper() == "BUY" else "SELL_AB",
        "strategy_id": "GOLD_SENDER_ORDER_KEY_DUPLICATE_VALIDATION_FIXTURE",
        "condition_id": "GOLD_SENDER_ORDER_KEY_DUPLICATE_VALIDATION_FIXTURE",
        "router_strategy_slot": "DUPLICATE_VALIDATION",
        "router_strategy_id": "GOLD_SENDER_ORDER_KEY_DUPLICATE_VALIDATION_FIXTURE",
        "candidate_rank": "FIXTURE",
        "source": "gold_sender_order_key_duplicate_validation_fixture",
        "fixture_note": "Validate duplicate order_key is blocked by sender order ledger; no --send.",
    }


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Validate GOLD sender duplicate order_key behavior in no-send mode.")
    p.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    p.add_argument("--symbol", default="GOLD#")
    p.add_argument("--direction", choices=["BUY", "SELL"], default="BUY")
    p.add_argument("--lot", type=float, default=0.01)
    p.add_argument("--expected-login", type=int, default=75539039)
    p.add_argument("--require-demo-account", action=argparse.BooleanOptionalAction, default=True)
    p.add_argument("--deviation", type=int, default=100)
    p.add_argument("--max-symbol-positions", type=int, default=20)
    p.add_argument("--max-symbol-lot", type=float, default=1.0)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    order_key = f"GOLD_DUPLICATE_ORDER_KEY_VALIDATION_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}"

    payload_csv = args.out_dir / "payload" / "gold_duplicate_order_key_payload.csv"
    order_ledger_csv = args.out_dir / "gold_duplicate_order_key_order_ledger.csv"
    sender_out_dir = args.out_dir / "sender_no_send"
    registry_preview_csv = args.out_dir / "registry_preview" / "registry_preview.csv"
    registry_preview_json = args.out_dir / "registry_preview" / "registry_preview.json"
    stdout_log = args.out_dir / "command_logs" / "sender_stdout.txt"
    stderr_log = args.out_dir / "command_logs" / "sender_stderr.txt"
    summary_json = args.out_dir / SUMMARY_FILENAME

    payload = build_fixture(order_key, symbol=str(args.symbol), direction=str(args.direction), lot=float(args.lot))
    existing_ledger_row = {
        "created_at_utc": utc_now_text(),
        "order_key": order_key,
        "payload_key": payload["payload_key"],
        "signal_key": payload["signal_key"],
        "broker_symbol": args.symbol,
        "symbol": str(args.symbol).replace("#", ""),
        "direction": args.direction,
        "lot": float(args.lot),
        "order_status": "PREEXISTING_SENT_FIXTURE",
        "order_send_called": True,
        "order_send_ok": True,
        "source": "prepopulated_duplicate_guard_fixture",
    }
    write_csv(payload_csv, [payload], PAYLOAD_COLUMNS)
    write_csv(order_ledger_csv, [existing_ledger_row], LEDGER_COLUMNS)

    cmd = [
        sys.executable,
        str(REPO_ROOT / "scripts" / "send_mt5_order_from_payload.py"),
        "--input-csv", str(payload_csv),
        "--order-ledger-csv", str(order_ledger_csv),
        "--out-dir", str(sender_out_dir),
        "--symbol", str(args.symbol),
        "--max-orders", "1",
        "--deviation", str(args.deviation),
        "--position-policy", "allow_any_until_max",
        "--max-symbol-positions", str(args.max_symbol_positions),
        "--max-symbol-lot", str(args.max_symbol_lot),
        "--select-symbol",
        "--expected-login", str(args.expected_login),
        "--registry-preview-out-csv", str(registry_preview_csv),
        "--registry-preview-out-json", str(registry_preview_json),
    ]
    if args.require_demo_account:
        cmd.append("--require-demo-account")

    print("=" * 80, flush=True)
    print("GOLD sender order_key duplicate validation - NO SEND", flush=True)
    print("This is not a strategy signal. It validates order_key duplicate guard.", flush=True)
    print(f"order_key={order_key}", flush=True)
    print("[CMD] " + " ".join(cmd), flush=True)
    print("=" * 80, flush=True)

    completed = subprocess.run(cmd, cwd=str(REPO_ROOT), text=True, encoding="utf-8", errors="replace", capture_output=True)
    print(completed.stdout or "", end="", flush=True)
    print(completed.stderr or "", end="", flush=True)
    write_text(stdout_log, completed.stdout or "")
    write_text(stderr_log, completed.stderr or "")

    sender_report = read_json_or_empty(sender_out_dir / "mt5_order_send_report.json")
    rows_out = safe_int(sender_report.get("rows_out"), 0)
    sent_rows = safe_int(sender_report.get("sent_rows"), 0)
    order_send_called_count = safe_int(sender_report.get("order_send_called_count"), 0)
    dry_run_check_ok_rows = safe_int(sender_report.get("dry_run_check_ok_rows"), 0)
    blocked_position_policy_rows = safe_int(sender_report.get("blocked_position_policy_rows"), 0)
    error_rows = safe_int(sender_report.get("error_rows"), 0)

    result_csv_candidates = list(sender_out_dir.glob("*.csv"))
    result_rows = pd.DataFrame()
    for candidate in result_csv_candidates:
        df = read_csv_or_empty(candidate)
        if not df.empty and "order_status" in df.columns:
            result_rows = df
            break

    order_status_values = result_rows["order_status"].astype(str).tolist() if not result_rows.empty and "order_status" in result_rows.columns else []
    validation_errors_text = " ".join(result_rows.get("validation_errors", pd.Series(dtype=str)).fillna("").astype(str).tolist()) if not result_rows.empty else ""
    stdout_text = completed.stdout or ""
    duplicate_detected = (
        any("DUP" in s.upper() or "EXIST" in s.upper() for s in order_status_values)
        or "duplicate" in stdout_text.lower()
        or "order_key" in validation_errors_text.lower()
        or "duplicate" in validation_errors_text.lower()
        or "existing" in validation_errors_text.lower()
    )

    # Accept returncode 0 or 1 here: implementations may classify duplicate as a
    # controlled skip or as a local validation error. The invariant is that it is
    # not treated as a successful dry-run order_check and never sends.
    validation_ok = bool(
        rows_out == 1
        and order_send_called_count == 0
        and sent_rows == 0
        and dry_run_check_ok_rows == 0
        and blocked_position_policy_rows == 0
        and duplicate_detected
    )

    summary = {
        "schema_version": "gold_sender_order_key_duplicate_validation_v1",
        "validation_time_utc": utc_now_text(),
        "validation_ok": validation_ok,
        "reason": "GOLD_SENDER_ORDER_KEY_DUPLICATE_VALIDATION_PASS" if validation_ok else "GOLD_SENDER_ORDER_KEY_DUPLICATE_VALIDATION_FAILED",
        "order_key": order_key,
        "sender_returncode": int(completed.returncode),
        "sender_rows_out": rows_out,
        "sender_dry_run_check_ok_rows": dry_run_check_ok_rows,
        "sender_error_rows": error_rows,
        "sender_blocked_position_policy_rows": blocked_position_policy_rows,
        "sender_order_send_called_count": order_send_called_count,
        "sender_sent_rows": sent_rows,
        "order_status_values": order_status_values,
        "duplicate_detected": duplicate_detected,
        "position_policy": "allow_any_until_max",
        "safety": {
            "send_flag_passed": False,
            "position_policy_block_any_used": False,
            "order_send_called_count": order_send_called_count,
            "sent_rows": sent_rows,
            "production_registry_mutated": False,
            "existing_mochipoyo_ledgers_mutated": False,
            "trigger_state_mutated": False,
        },
        "paths": {
            "payload_csv": str(payload_csv),
            "order_ledger_csv": str(order_ledger_csv),
            "sender_out_dir": str(sender_out_dir),
            "registry_preview_csv": str(registry_preview_csv),
            "registry_preview_json": str(registry_preview_json),
            "stdout_log": str(stdout_log),
            "stderr_log": str(stderr_log),
            "summary_json": str(summary_json),
        },
    }
    write_json(summary_json, summary)

    print("=" * 80, flush=True)
    print("GOLD sender order_key duplicate validation summary", flush=True)
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True, default=str), flush=True)
    print("=" * 80, flush=True)
    return 0 if validation_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
