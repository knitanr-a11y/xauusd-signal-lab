#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""Validate sender preserves payload lot for GOLD multi-strategy.

Purpose:
- Prevent regression where SELL_H1H4_BEAR_AB CORE_AB_CONFIRM should be 0.02 lot
  but the sender or payload path silently falls back to 0.01.
- This script creates a synthetic GOLD# SELL payload with lot=0.02 and sends it
  through send_mt5_order_from_payload.py in NO-SEND mode.
- It expects the sender output/report to keep lot=0.02.

Safety:
- NO --send is passed.
- order_send_called_count must remain 0.
- sent_rows must remain 0.
- production registry is never written.
- This is not a strategy signal; it is a payload/sender contract validation.

Important fixture detail:
- The sender validates SL/TP against the *current* MT5 bid/ask, not the fixture
  entry_price_reference. Therefore this validation uses a deliberately wide
  SELL fixture by default: sl=9999.0 and tp=1.0. That keeps local price relation
  validation valid even when GOLD is around normal broker quote ranges.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT_DIR = Path("data/r/gold_sender_lot_passthrough_validation")
SUMMARY_FILENAME = "latest_gold_sender_lot_passthrough_validation_result.json"

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


def approx_equal(a: Any, b: Any, eps: float = 1e-9) -> bool:
    return abs(safe_float(a) - safe_float(b)) <= eps


def read_csv_lot_values(path: Path) -> list[float]:
    if not path.exists():
        return []
    try:
        df = pd.read_csv(windows_long_path(path), encoding="utf-8-sig")
    except Exception:
        return []
    if "lot" not in df.columns:
        return []
    return [safe_float(v) for v in df["lot"].dropna().tolist()]


def discover_sender_lot_values(sender_out_dir: Path, order_ledger_csv: Path) -> tuple[list[float], list[str]]:
    """Find sender result lot values across known sender output names.

    The sender has evolved across iterations, so this validation should not depend
    on one hard-coded result CSV filename. It reads every CSV under sender_out_dir
    and the order ledger, then returns all lot values it finds.
    """
    paths: list[Path] = []
    if sender_out_dir.exists():
        paths.extend(sorted(sender_out_dir.glob("*.csv")))
        paths.extend(sorted((sender_out_dir / "reports").glob("*.csv")) if (sender_out_dir / "reports").exists() else [])
    paths.append(order_ledger_csv)
    values: list[float] = []
    sources: list[str] = []
    for p in paths:
        vals = read_csv_lot_values(p)
        if vals:
            values.extend(vals)
            sources.append(str(p))
    return values, sources


def parse_stdout_lot_values(stdout: str, expected_symbol: str, expected_direction: str) -> list[float]:
    """Fallback parser for the compact table printed by send_mt5_order_from_payload.py."""
    values: list[float] = []
    for line in stdout.splitlines():
        if expected_symbol not in line or expected_direction.upper() not in line.upper():
            continue
        match = re.search(rf"\b{re.escape(expected_direction.upper())}\s+([0-9]+(?:\.[0-9]+)?)\b", line.upper())
        if match:
            values.append(safe_float(match.group(1)))
    return values


def build_fixture_payload(*, lot: float, symbol: str, direction: str, entry: float, sl: float, tp: float) -> dict[str, Any]:
    now = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    key_base = f"GOLD_LOT_PASSTHROUGH_{symbol}_{direction}_{lot}_{now}"
    return {
        "payload_key": f"{key_base}_PAYLOAD",
        "order_key": f"{key_base}_ORDER",
        "signal_key": f"{key_base}_SIGNAL",
        "broker_symbol": symbol,
        "symbol": symbol.replace("#", ""),
        "direction": direction,
        "lot": lot,
        "entry_price_reference": entry,
        "sl_price": sl,
        "tp_price": tp,
        "magic_number": 26050606,
        "strategy_key": "SELL_H1H4_BEAR_AB",
        "strategy_alias": "SELL_AB",
        "strategy_id": "GOLD_H1H4_BEAR_M15_LOW_BREAK_AB_CLASSIFIER_FIXED10_RR2_12H",
        "condition_id": "GOLD_H1H4_BEAR_M15_LOW_BREAK_AB_CORE_AB_CONFIRM",
        "router_strategy_slot": "SELL_H1H4_BEAR_AB",
        "router_strategy_id": "GOLD_H1H4_BEAR_M15_LOW_BREAK_AB_CLASSIFIER_FIXED10_RR2_12H",
        "candidate_rank": "CORE_AB_CONFIRM",
        "source": "gold_sender_lot_passthrough_validation_fixture",
        "fixture_note": "Validate sender preserves lot=0.02 for CORE_AB_CONFIRM; no --send.",
    }


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Validate GOLD sender lot passthrough in no-send mode.")
    p.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    p.add_argument("--symbol", default="GOLD#")
    p.add_argument("--direction", choices=["BUY", "SELL"], default="SELL")
    p.add_argument("--lot", type=float, default=0.02)
    p.add_argument("--entry-price", type=float, default=4700.0)
    p.add_argument("--sl-price", type=float, default=9999.0)
    p.add_argument("--tp-price", type=float, default=1.0)
    p.add_argument("--expected-login", type=int, default=75539039)
    p.add_argument("--require-demo-account", action=argparse.BooleanOptionalAction, default=True)
    p.add_argument("--deviation", type=int, default=100)
    p.add_argument("--position-policy", choices=["block_any", "allow_same_direction", "allow_any_until_max"], default="allow_any_until_max")
    p.add_argument("--max-symbol-positions", type=int, default=20)
    p.add_argument("--max-symbol-lot", type=float, default=1.0)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    mkdir_path(args.out_dir)
    payload_csv = args.out_dir / "payload" / "gold_sender_lot_passthrough_payload.csv"
    order_ledger_csv = args.out_dir / "gold_sender_lot_passthrough_order_ledger.csv"
    sender_out_dir = args.out_dir / "sender_no_send"
    registry_preview_csv = args.out_dir / "registry_preview" / "registry_preview.csv"
    registry_preview_json = args.out_dir / "registry_preview" / "registry_preview.json"
    summary_json = args.out_dir / SUMMARY_FILENAME
    stdout_log = args.out_dir / "command_logs" / "sender_stdout.txt"
    stderr_log = args.out_dir / "command_logs" / "sender_stderr.txt"

    payload = build_fixture_payload(
        lot=float(args.lot),
        symbol=str(args.symbol),
        direction=str(args.direction),
        entry=float(args.entry_price),
        sl=float(args.sl_price),
        tp=float(args.tp_price),
    )
    write_csv(payload_csv, [payload], PAYLOAD_COLUMNS)

    cmd = [
        sys.executable,
        str(REPO_ROOT / "scripts" / "send_mt5_order_from_payload.py"),
        "--input-csv", str(payload_csv),
        "--order-ledger-csv", str(order_ledger_csv),
        "--out-dir", str(sender_out_dir),
        "--symbol", str(args.symbol),
        "--max-orders", "1",
        "--deviation", str(args.deviation),
        "--position-policy", str(args.position_policy),
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
    print("GOLD sender lot passthrough validation - NO SEND", flush=True)
    print("This is not a strategy signal. It validates payload lot -> sender lot preservation.", flush=True)
    print(f"payload_lot={args.lot} symbol={args.symbol} direction={args.direction}", flush=True)
    print(f"fixture_prices entry={args.entry_price} sl={args.sl_price} tp={args.tp_price}", flush=True)
    print("[CMD] " + " ".join(cmd), flush=True)
    print("=" * 80, flush=True)

    completed = subprocess.run(cmd, cwd=str(REPO_ROOT), text=True, encoding="utf-8", errors="replace", capture_output=True)
    if completed.stdout:
        print(completed.stdout, end="", flush=True)
    if completed.stderr:
        print(completed.stderr, end="", flush=True)
    write_text(stdout_log, completed.stdout or "")
    write_text(stderr_log, completed.stderr or "")

    sender_report = read_json_or_empty(sender_out_dir / "mt5_order_send_report.json")
    rows_out = safe_int(sender_report.get("rows_out"), 0)
    sent_rows = safe_int(sender_report.get("sent_rows"), 0)
    order_send_called_count = safe_int(sender_report.get("order_send_called_count"), 0)
    error_rows = safe_int(sender_report.get("error_rows"), 0)
    dry_run_check_ok_rows = safe_int(sender_report.get("dry_run_check_ok_rows"), 0)

    sender_lot_values, sender_lot_sources = discover_sender_lot_values(sender_out_dir, order_ledger_csv)
    if not sender_lot_values:
        sender_lot_values = parse_stdout_lot_values(completed.stdout or "", str(args.symbol), str(args.direction))
        if sender_lot_values:
            sender_lot_sources = [str(stdout_log)]

    registry_lot_values = read_csv_lot_values(registry_preview_csv)

    sender_lot_ok = bool(sender_lot_values and all(approx_equal(v, args.lot) for v in sender_lot_values))
    registry_lot_ok = bool((not registry_lot_values) or all(approx_equal(v, args.lot) for v in registry_lot_values))
    validation_ok = bool(
        completed.returncode == 0
        and rows_out == 1
        and order_send_called_count == 0
        and sent_rows == 0
        and sender_lot_ok
        and registry_lot_ok
        and error_rows == 0
    )

    summary = {
        "schema_version": "gold_sender_lot_passthrough_validation_v2_safe_sell_fixture",
        "validation_time_utc": utc_now_text(),
        "validation_ok": validation_ok,
        "reason": "GOLD_SENDER_LOT_PASSTHROUGH_VALIDATION_PASS" if validation_ok else "GOLD_SENDER_LOT_PASSTHROUGH_VALIDATION_FAILED",
        "payload_lot": float(args.lot),
        "sender_lot_values": sender_lot_values,
        "sender_lot_sources": sender_lot_sources,
        "registry_lot_values": registry_lot_values,
        "sender_lot_ok": sender_lot_ok,
        "registry_lot_ok": registry_lot_ok,
        "sender_returncode": int(completed.returncode),
        "sender_rows_out": rows_out,
        "sender_dry_run_check_ok_rows": dry_run_check_ok_rows,
        "sender_error_rows": error_rows,
        "sender_order_send_called_count": order_send_called_count,
        "sender_sent_rows": sent_rows,
        "fixture_prices": {
            "entry_price_reference": float(args.entry_price),
            "sl_price": float(args.sl_price),
            "tp_price": float(args.tp_price),
            "note": "SELL defaults intentionally use very wide SL/TP so sender validates against current bid.",
        },
        "safety": {
            "send_flag_passed": False,
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
    print("GOLD sender lot passthrough validation summary", flush=True)
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True, default=str), flush=True)
    print("=" * 80, flush=True)
    return 0 if validation_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
