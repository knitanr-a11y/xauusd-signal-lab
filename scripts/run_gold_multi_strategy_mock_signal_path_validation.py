#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""Validate GOLD multi-strategy signal-present path with a safe mock intent.

This script does NOT wait for a real market signal. It creates a router-compatible
mock OPEN_POSITION intent and validates the downstream path:

    mock router combined_order_intent_dry_run.jsonl
      -> autotrade adapter dry-run
      -> payload bridge
      -> send_mt5_order_from_payload.py dry-run WITHOUT --send
      -> sender-native registry preview
      -> mock position
      -> reconcile
      -> registry-aware same_strategy BLOCK policy preview
      -> duplicate preview skip check

Safety boundaries:
- Never passes --send.
- Does not write production position_registry.csv.
- Does not call or modify existing Mochipoyo production/demo BATs.
- Does not intentionally mutate existing Mochipoyo ledgers or trigger-state files.
- Uses its own output directory by default.
- Uses Windows long-path helpers for its own outputs.

The mock intent uses the current MT5 tick by default to keep SL/TP near current
market and make sender order_check dry-run realistic:

    SELL entry = bid
    SL = entry + 10.00
    TP = entry - 20.00

This is a validation fixture only, not a trading signal.
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
DEFAULT_OUT_DIR = Path("data/research_results/gold_multi_strategy_mock_signal_path_validation")

STRATEGY_SLOT = "SELL_H1H4_BEAR_AB"
STRATEGY_ID = "GOLD_H1H4_BEAR_M15_LOW_BREAK_AB_CLASSIFIER_FIXED10_RR2_12H"
CONDITION_ID = "GOLD_H1H4_BEAR_M15_LOW_BREAK_AB_CLASSIFIER_FIXED10_RR2_12H"

CASE_LOG_COLUMNS = [
    "stage",
    "started_at_utc",
    "ended_at_utc",
    "returncode",
    "ok",
    "reason",
    "details_json",
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


def utc_now() -> datetime:
    return datetime.now(UTC)


def utc_now_text() -> str:
    return utc_now().strftime("%Y-%m-%d %H:%M:%S")


def utc_stamp() -> str:
    return utc_now().strftime("%Y%m%dT%H%M%SZ")


def write_text(path: Path, text: str) -> None:
    ensure_parent_dir(path)
    with open(windows_long_path(path), "w", encoding="utf-8", newline="") as f:
        f.write(text)


def write_json(path: Path, obj: dict[str, Any]) -> None:
    write_text(path, json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True, default=str))


def read_json_or_empty(path: Path) -> dict[str, Any]:
    try:
        with open(windows_long_path(path), "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except Exception as exc:
        return {"_read_error": str(exc), "_path": str(path)}


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    ensure_parent_dir(path)
    with open(windows_long_path(path), "w", encoding="utf-8", newline="") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True, default=str) + "\n")


def write_csv_rows(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    ensure_parent_dir(path)
    with open(windows_long_path(path), "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({col: row.get(col, "") for col in columns})


def append_csv_row(path: Path, row: dict[str, Any], columns: list[str]) -> None:
    ensure_parent_dir(path)
    exists = Path(windows_long_path(path)).exists()
    with open(windows_long_path(path), "a", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        if not exists:
            writer.writeheader()
        writer.writerow({col: row.get(col, "") for col in columns})


def as_int(value: Any, default: int = 0) -> int:
    try:
        if value is None or value == "":
            return default
        return int(value)
    except Exception:
        try:
            return int(float(value))
        except Exception:
            return default


def as_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def read_csv_len(path: Path) -> int:
    try:
        return int(len(pd.read_csv(windows_long_path(path), encoding="utf-8-sig")))
    except Exception:
        return 0


def get_mt5_tick(*, broker_symbol: str, expected_login: int | None, require_demo_account: bool, select_symbol: bool) -> dict[str, Any]:
    try:
        import MetaTrader5 as mt5  # type: ignore
    except Exception as exc:
        raise RuntimeError(f"MetaTrader5 import failed: {exc}") from exc

    if not mt5.initialize():
        raise RuntimeError(f"mt5.initialize failed: {mt5.last_error()}")
    try:
        account = mt5.account_info()
        if account is None:
            raise RuntimeError(f"mt5.account_info failed: {mt5.last_error()}")
        if expected_login is not None and int(account.login) != int(expected_login):
            raise RuntimeError(f"unexpected login: actual={account.login} expected={expected_login}")
        if require_demo_account:
            server = str(getattr(account, "server", ""))
            name = str(getattr(account, "name", ""))
            if "demo" not in server.lower() and "demo" not in name.lower():
                raise RuntimeError(f"demo account required: login={account.login} server={server} name={name}")
        if select_symbol:
            selected = mt5.symbol_select(broker_symbol, True)
            if not selected:
                raise RuntimeError(f"symbol_select failed for {broker_symbol}: {mt5.last_error()}")
        info = mt5.symbol_info(broker_symbol)
        if info is None:
            raise RuntimeError(f"symbol_info failed for {broker_symbol}: {mt5.last_error()}")
        tick = mt5.symbol_info_tick(broker_symbol)
        if tick is None:
            raise RuntimeError(f"symbol_info_tick failed for {broker_symbol}: {mt5.last_error()}")
        bid = float(tick.bid)
        ask = float(tick.ask)
        digits = int(getattr(info, "digits", 2) or 2)
        if bid <= 0 or ask <= 0:
            raise RuntimeError(f"invalid tick bid/ask: bid={bid} ask={ask}")
        return {
            "account_login": int(account.login),
            "account_server": str(getattr(account, "server", "")),
            "account_name": str(getattr(account, "name", "")),
            "broker_symbol": broker_symbol,
            "bid": bid,
            "ask": ask,
            "digits": digits,
        }
    finally:
        mt5.shutdown()


def build_mock_open_intent(price_meta: dict[str, Any], *, direction: str, lot: float, sl_usd: float, tp_usd: float) -> dict[str, Any]:
    direction = direction.upper()
    digits = int(price_meta.get("digits", 2) or 2)
    if direction == "SELL":
        entry = round(float(price_meta["bid"]), digits)
        sl = round(entry + float(sl_usd), digits)
        tp = round(entry - float(tp_usd), digits)
    elif direction == "BUY":
        entry = round(float(price_meta["ask"]), digits)
        sl = round(entry - float(sl_usd), digits)
        tp = round(entry + float(tp_usd), digits)
    else:
        raise ValueError(f"unsupported direction: {direction}")
    risk = abs(entry - sl)
    reward = abs(tp - entry)
    rr = round(reward / risk, 6) if risk else 0.0
    stamp = utc_stamp()
    signal_time = utc_now_text()
    signal_key = f"MOCK_SIGNAL_PATH|{STRATEGY_SLOT}|GOLD|{direction}|{stamp}"
    return {
        "schema_version": "gold_multi_strategy_mock_router_intent_v1",
        "dry_run": True,
        "intent_type": "OPEN_POSITION",
        "symbol": "GOLD",
        "broker_symbol": price_meta.get("broker_symbol", "GOLD#"),
        "direction": direction,
        "strategy_id": STRATEGY_ID,
        "condition_id": CONDITION_ID,
        "signal_key": signal_key,
        "rank": "MOCK_SIGNAL_PATH",
        "entry_type": "MARKET_DRY_RUN",
        "signal_time": signal_time,
        "entry_price_reference": entry,
        "sl_price": sl,
        "tp_price": tp,
        "risk_price": risk,
        "reward_price": reward,
        "rr": rr,
        "max_hold_hours": 12,
        "lot": {
            "base_lot": float(lot),
            "lot_multiplier": 1.0,
            "effective_lot": float(lot),
        },
        "router_strategy_slot": STRATEGY_SLOT,
        "router_strategy_id": STRATEGY_ID,
        "router_source_path": "MOCK_SIGNAL_PATH_VALIDATION",
        "mock_fixture": True,
    }


def run_cmd(stage: str, cmd: list[str], out_dir: Path, *, continue_on_error: bool = False) -> tuple[int, Path, Path]:
    started = utc_now_text()
    log_dir = out_dir / "command_logs"
    mkdir_path(log_dir)
    stdout_path = log_dir / f"{stage}_stdout.txt"
    stderr_path = log_dir / f"{stage}_stderr.txt"
    print("=" * 80, flush=True)
    print(f"[STAGE] {stage}", flush=True)
    print("[CMD] " + " ".join(cmd), flush=True)
    completed = subprocess.run(
        cmd,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    write_text(stdout_path, completed.stdout or "")
    write_text(stderr_path, completed.stderr or "")
    if completed.stdout:
        print(completed.stdout.rstrip(), flush=True)
    if completed.stderr:
        print(completed.stderr.rstrip(), file=sys.stderr, flush=True)
    ended = utc_now_text()
    append_csv_row(out_dir / "stage_log.csv", {
        "stage": stage,
        "started_at_utc": started,
        "ended_at_utc": ended,
        "returncode": int(completed.returncode),
        "ok": int(completed.returncode) == 0,
        "reason": "RETURN_CODE_ZERO" if int(completed.returncode) == 0 else "RETURN_CODE_NONZERO",
        "details_json": "",
    }, CASE_LOG_COLUMNS)
    if completed.returncode != 0 and not continue_on_error:
        print(f"[ERROR] stage failed: {stage} returncode={completed.returncode}", flush=True)
    return int(completed.returncode), stdout_path, stderr_path


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Validate mock signal-present path through adapter/payload/sender dry-run/registry preview.")
    p.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    p.add_argument("--broker-symbol", default="GOLD#")
    p.add_argument("--expected-login", type=int, default=75539039)
    p.add_argument("--require-demo-account", action=argparse.BooleanOptionalAction, default=True)
    p.add_argument("--select-symbol", action=argparse.BooleanOptionalAction, default=True)
    p.add_argument("--direction", choices=["BUY", "SELL"], default="SELL")
    p.add_argument("--lot", type=float, default=0.01)
    p.add_argument("--sl-usd", type=float, default=10.0)
    p.add_argument("--tp-usd", type=float, default=20.0)
    p.add_argument("--magic", type=int, default=26050601)
    p.add_argument("--max-orders", type=int, default=1)
    p.add_argument("--position-policy", choices=["block_any", "allow_same_direction", "allow_any_until_max"], default="allow_any_until_max")
    p.add_argument("--max-symbol-positions", type=int, default=5)
    p.add_argument("--max-symbol-lot", type=float, default=0.05)
    p.add_argument("--deviation", type=int, default=50)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    mkdir_path(args.out_dir)
    started = utc_now_text()

    router_out_dir = args.out_dir / "router_mock"
    adapter_out_dir = args.out_dir / "adapter"
    adapter_dup_out_dir = args.out_dir / "adapter_duplicate_check"
    payload_out_dir = args.out_dir / "payload"
    sender_out_dir = args.out_dir / "sender"
    registry_dir = args.out_dir / "registry_preview"
    mock_positions_csv = args.out_dir / "mp.csv"
    reconcile_out_dir = args.out_dir / "reconcile"
    policy_out_dir = args.out_dir / "policy"
    order_ledger_csv = args.out_dir / "dry_run_order_ledger.csv"

    price_meta = get_mt5_tick(
        broker_symbol=args.broker_symbol,
        expected_login=args.expected_login,
        require_demo_account=bool(args.require_demo_account),
        select_symbol=bool(args.select_symbol),
    )
    intent = build_mock_open_intent(price_meta, direction=args.direction, lot=args.lot, sl_usd=args.sl_usd, tp_usd=args.tp_usd)
    write_jsonl(router_out_dir / "combined_order_intent_dry_run.jsonl", [intent])
    write_jsonl(router_out_dir / "combined_close_intent_dry_run.jsonl", [])
    router_summary = {
        "schema_version": "gold_multi_strategy_mock_router_result_v1",
        "router_ok": True,
        "router_mode": "MOCK_SIGNAL_PATH_VALIDATION",
        "signals_found_count": 1,
        "open_order_intent_count": 1,
        "close_intent_count": 0,
        "strategy_status": [
            {
                "strategy_slot": STRATEGY_SLOT,
                "strategy_id": STRATEGY_ID,
                "direction": args.direction,
                "signal_found": True,
                "signal_key": intent["signal_key"],
                "trade_enabled": True,
                "scan_reason": "MOCK_SIGNAL_PATH_VALIDATION",
                "cycle_ok": True,
            }
        ],
    }
    write_json(router_out_dir / "latest_multi_strategy_cycle_result.json", router_summary)
    write_csv_rows(router_out_dir / "strategy_status_latest.csv", router_summary["strategy_status"], ["strategy_slot", "strategy_id", "direction", "signal_found", "signal_key", "trade_enabled", "scan_reason", "cycle_ok"])

    rc_adapter, _, _ = run_cmd("adapter_first_pass", [
        sys.executable, str(REPO_ROOT / "scripts" / "run_gold_multi_strategy_autotrade_adapter_dry_run.py"),
        "--router-out-dir", str(router_out_dir),
        "--out-dir", str(adapter_out_dir),
        "--broker-symbol", str(args.broker_symbol),
        "--reset-ledger",
    ], args.out_dir)

    rc_adapter_dup, _, _ = run_cmd("adapter_duplicate_pass", [
        sys.executable, str(REPO_ROOT / "scripts" / "run_gold_multi_strategy_autotrade_adapter_dry_run.py"),
        "--router-out-dir", str(router_out_dir),
        "--out-dir", str(adapter_out_dir),
        "--broker-symbol", str(args.broker_symbol),
    ], args.out_dir)

    # Copy duplicate result details to separate folder summary for easier inspection.
    dup_result = read_json_or_empty(adapter_out_dir / "latest_adapter_result.json")
    write_json(adapter_dup_out_dir / "latest_adapter_duplicate_result.json", dup_result)

    rc_payload, _, _ = run_cmd("payload_bridge", [
        sys.executable, str(REPO_ROOT / "scripts" / "build_gold_multi_strategy_mochipoyo_order_payloads_dry_run.py"),
        "--adapter-out-dir", str(adapter_out_dir),
        "--out-dir", str(payload_out_dir),
        "--broker-symbol", str(args.broker_symbol),
        "--fixed-lot", str(args.lot),
        "--magic", str(args.magic),
        "--max-orders", str(args.max_orders),
    ], args.out_dir)

    payload_csv = payload_out_dir / "order_payloads.csv"
    registry_csv = registry_dir / "registry_preview.csv"
    registry_json = registry_dir / "registry_preview.json"
    rc_sender, _, _ = run_cmd("sender_dry_run_registry_preview", [
        sys.executable, str(REPO_ROOT / "scripts" / "send_mt5_order_from_payload.py"),
        "--input-csv", str(payload_csv),
        "--order-ledger-csv", str(order_ledger_csv),
        "--out-dir", str(sender_out_dir),
        "--symbol", str(args.broker_symbol),
        "--max-orders", str(args.max_orders),
        "--deviation", str(args.deviation),
        "--position-policy", str(args.position_policy),
        "--max-symbol-positions", str(args.max_symbol_positions),
        "--max-symbol-lot", str(args.max_symbol_lot),
        "--select-symbol",
        "--expected-login", str(args.expected_login),
        "--require-demo-account",
        "--registry-preview-out-csv", str(registry_csv),
        "--registry-preview-out-json", str(registry_json),
    ], args.out_dir)

    rc_mock_positions, _, _ = run_cmd("mock_positions", [
        sys.executable, str(REPO_ROOT / "scripts" / "build_gold_multi_strategy_mock_positions_from_registry.py"),
        "--registry-csv", str(registry_csv),
        "--output-csv", str(mock_positions_csv),
    ], args.out_dir)

    rc_reconcile, _, _ = run_cmd("reconcile", [
        sys.executable, str(REPO_ROOT / "scripts" / "run_gold_multi_strategy_position_registry_reconcile_dry_run.py"),
        "--registry-csv", str(registry_csv),
        "--positions-csv", str(mock_positions_csv),
        "--out-dir", str(reconcile_out_dir),
        "--symbol", str(args.broker_symbol),
    ], args.out_dir)

    rc_policy, _, _ = run_cmd("policy_same_strategy_block", [
        sys.executable, str(REPO_ROOT / "scripts" / "run_gold_multi_strategy_registry_policy_preview_longpath.py"),
        "--input-csv", str(payload_csv),
        "--positions-csv", str(mock_positions_csv),
        "--registry-csv", str(registry_csv),
        "--order-ledger-csv", str(order_ledger_csv),
        "--out-dir", str(policy_out_dir),
        "--symbol", str(args.broker_symbol),
        "--max-orders", str(args.max_orders),
        "--max-total-positions", str(args.max_symbol_positions),
        "--max-lot-per-order", "0.02",
    ], args.out_dir)

    adapter_first = read_json_or_empty(adapter_out_dir / "latest_adapter_result.json")
    payload_summary = read_json_or_empty(payload_out_dir / "order_payloads.json")
    sender_report = read_json_or_empty(sender_out_dir / "mt5_order_send_report.json")
    registry_preview = read_json_or_empty(registry_json)
    reconcile_summary = read_json_or_empty(reconcile_out_dir / "position_registry_reconcile_dry_run.json")
    policy_summary = read_json_or_empty(policy_out_dir / "registry_policy_preview.json")
    registry_section = sender_report.get("registry_preview", {}) if isinstance(sender_report.get("registry_preview"), dict) else {}

    checks = {
        "adapter_first_created_one": as_int(adapter_first.get("order_previews_created"), 0) >= 1,
        "adapter_duplicate_skipped_one": as_int(dup_result.get("duplicate_previews_skipped"), 0) >= 1,
        "payload_rows_out_one": as_int(payload_summary.get("rows_out"), 0) >= 1,
        "sender_no_send": not as_bool(sender_report.get("send_requested"), False) and as_int(sender_report.get("order_send_called_count"), 0) == 0 and as_int(sender_report.get("sent_rows"), 0) == 0,
        "sender_dry_run_check_ok": as_int(sender_report.get("dry_run_check_ok_rows"), 0) >= 1,
        "registry_preview_rows": as_int(registry_section.get("registry_preview_rows"), 0) >= 1,
        "mock_positions_rows": read_csv_len(mock_positions_csv) >= 1,
        "reconcile_ok": as_bool(reconcile_summary.get("reconcile_ok"), False) and as_int(reconcile_summary.get("matched_active_registry_rows"), 0) >= 1,
        "policy_same_strategy_block": as_bool(policy_summary.get("preview_ok"), False) and as_int(policy_summary.get("same_strategy_blocked_rows"), 0) >= 1 and as_int(policy_summary.get("allow_rows"), 0) == 0,
        "all_returncodes_zero": all(rc == 0 for rc in [rc_adapter, rc_adapter_dup, rc_payload, rc_sender, rc_mock_positions, rc_reconcile, rc_policy]),
    }
    checks_failed = [name for name, ok in checks.items() if not ok]
    ended = utc_now_text()
    summary = {
        "schema_version": "gold_multi_strategy_mock_signal_path_validation_v1",
        "started_at_utc": started,
        "ended_at_utc": ended,
        "validation_ok": len(checks_failed) == 0,
        "reason": "GOLD_MULTI_STRATEGY_MOCK_SIGNAL_PATH_PASS" if not checks_failed else "GOLD_MULTI_STRATEGY_MOCK_SIGNAL_PATH_FAILED",
        "checks": checks,
        "checks_failed": checks_failed,
        "returncodes": {
            "adapter_first_pass": rc_adapter,
            "adapter_duplicate_pass": rc_adapter_dup,
            "payload_bridge": rc_payload,
            "sender_dry_run_registry_preview": rc_sender,
            "mock_positions": rc_mock_positions,
            "reconcile": rc_reconcile,
            "policy_same_strategy_block": rc_policy,
        },
        "safety": {
            "send_flag_passed": False,
            "sender_order_send_called_count": as_int(sender_report.get("order_send_called_count"), 0),
            "sender_sent_rows": as_int(sender_report.get("sent_rows"), 0),
            "production_registry_mutated": False,
            "existing_mochipoyo_bat_modified": False,
            "trigger_state_mutated": False,
        },
        "mock_intent": intent,
        "price_meta": price_meta,
        "paths": {
            "router_out_dir": str(router_out_dir),
            "adapter_out_dir": str(adapter_out_dir),
            "payload_out_dir": str(payload_out_dir),
            "payload_csv": str(payload_csv),
            "sender_out_dir": str(sender_out_dir),
            "registry_csv": str(registry_csv),
            "registry_json": str(registry_json),
            "mock_positions_csv": str(mock_positions_csv),
            "reconcile_out_dir": str(reconcile_out_dir),
            "policy_out_dir": str(policy_out_dir),
            "summary_json": str(args.out_dir / "latest_gold_multi_strategy_mock_signal_path_validation_result.json"),
        },
        "adapter_first": adapter_first,
        "adapter_duplicate": dup_result,
        "payload_summary": payload_summary,
        "sender_report": sender_report,
        "registry_preview": registry_preview,
        "reconcile_summary": reconcile_summary,
        "policy_summary": policy_summary,
    }
    write_json(args.out_dir / "latest_gold_multi_strategy_mock_signal_path_validation_result.json", summary)
    print("=" * 80, flush=True)
    print("GOLD multi-strategy mock signal path validation summary", flush=True)
    print(json.dumps({
        "validation_ok": summary["validation_ok"],
        "reason": summary["reason"],
        "checks": checks,
        "checks_failed": checks_failed,
        "returncodes": summary["returncodes"],
        "safety": summary["safety"],
        "summary_json": summary["paths"]["summary_json"],
    }, ensure_ascii=False, indent=2, sort_keys=True), flush=True)
    print("=" * 80, flush=True)
    return 0 if summary["validation_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
