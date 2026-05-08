#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""One-cycle GOLD multi-strategy demo autotrade send runner.

This is the first real DEMO order-send bridge for the isolated multi-strategy
BUY/SELL router flow.

Pipeline:

1. run_gold_multi_strategy_dry_run_cycle.py
2. run_gold_multi_strategy_autotrade_adapter_dry_run.py
3. build_gold_multi_strategy_mochipoyo_order_payloads_dry_run.py
4. send_mt5_order_from_payload.py WITH --send, but only when --enable-demo-send is provided
5. write combined send-cycle result/log

Important safety boundaries:
- This script is DEMO-only by default via --expected-login and --require-demo-account.
- This script defaults to broker_symbol=GOLD#, fixed_lot=0.01, max_orders=1.
- This script defaults to position_policy=block_any, max_symbol_positions=1, max_symbol_lot=0.01.
- This script does NOT modify existing Mochipoyo BAT files.
- This script does NOT write to existing Mochipoyo notification ledgers or trigger-state CSVs.
- This script does NOT execute close intents. It only handles open order payloads.
- This script refuses to pass --send unless --enable-demo-send is explicitly provided.

Expected behavior:
- No signal: no payload, MT5 send stage skipped, no order.
- Existing GOLD# position: block_any should block before order_send.
- No existing GOLD# position + valid payload: at most one 0.01 lot demo market order.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

DEFAULT_OUT_DIR = Path("data/research_results/gold_multi_strategy_demo_autotrade_send_cycle")
DEFAULT_ROUTER_OUT_DIR = Path("data/research_results/gold_multi_strategy_dry_run")
DEFAULT_BUY_OUT_DIR = Path("data/research_results/gold_c_env_rr2_72h_live_scan")
DEFAULT_SELL_OUT_DIR = Path("data/research_results/gold_h1h4_bear_ab_live_loop")
DEFAULT_ADAPTER_OUT_DIR = Path("data/research_results/gold_multi_strategy_autotrade_adapter_send_preview")
DEFAULT_PAYLOAD_OUT_DIR = Path("data/research_results/gold_multi_strategy_mochipoyo_payload_bridge_send")
DEFAULT_MT5_SEND_OUT_DIR = DEFAULT_PAYLOAD_OUT_DIR / "mt5_order_send"
DEFAULT_ORDER_LEDGER_CSV = DEFAULT_PAYLOAD_OUT_DIR / "demo_send_order_ledger.csv"

CYCLE_LOG_COLUMNS = [
    "cycle_start_utc",
    "cycle_end_utc",
    "cycle_ok",
    "send_enabled",
    "send_requested",
    "safe_send_guard_ok",
    "csv_dir",
    "out_dir",
    "router_out_dir",
    "adapter_out_dir",
    "payload_out_dir",
    "mt5_send_out_dir",
    "router_returncode",
    "adapter_returncode",
    "payload_bridge_returncode",
    "mt5_send_returncode",
    "router_ok",
    "adapter_ok",
    "bridge_ok",
    "router_mode",
    "signals_found_count",
    "open_order_intent_count",
    "close_intent_count",
    "order_intents_read",
    "close_intents_read",
    "order_previews_created",
    "close_previews_created",
    "duplicate_previews_skipped",
    "adapter_rejects",
    "payload_rows_in",
    "payload_rows_out",
    "valid_order_payloads",
    "payload_rejects",
    "mt5_rows_out",
    "mt5_dry_run_check_ok_rows",
    "mt5_blocked_position_policy_rows",
    "mt5_order_send_called_count",
    "mt5_sent_rows",
    "mt5_error_rows",
    "mt5_position_policy",
    "mt5_account_login",
    "mt5_account_server",
    "mt5_account_name",
    "mt5_status_summary",
    "latest_cycle_result_json",
]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run one GOLD multi-strategy DEMO autotrade send cycle.")
    p.add_argument("--csv-dir", type=Path, required=True)
    p.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    p.add_argument("--router-out-dir", type=Path, default=DEFAULT_ROUTER_OUT_DIR)
    p.add_argument("--buy-out-dir", type=Path, default=DEFAULT_BUY_OUT_DIR)
    p.add_argument("--sell-out-dir", type=Path, default=DEFAULT_SELL_OUT_DIR)
    p.add_argument("--adapter-out-dir", type=Path, default=DEFAULT_ADAPTER_OUT_DIR)
    p.add_argument("--payload-out-dir", type=Path, default=DEFAULT_PAYLOAD_OUT_DIR)
    p.add_argument("--mt5-send-out-dir", type=Path, default=DEFAULT_MT5_SEND_OUT_DIR)
    p.add_argument("--order-ledger-csv", type=Path, default=DEFAULT_ORDER_LEDGER_CSV)
    p.add_argument("--broker-symbol", type=str, default="GOLD#")
    p.add_argument("--fixed-lot", type=float, default=0.01)
    p.add_argument("--magic", type=int, default=26050601)
    p.add_argument("--expected-login", type=int, default=75539039)
    p.add_argument("--select-symbol", action="store_true", default=True)
    p.add_argument("--no-select-symbol", action="store_false", dest="select_symbol")
    p.add_argument("--require-demo-account", action="store_true", default=True)
    p.add_argument("--no-require-demo-account", action="store_false", dest="require_demo_account")
    p.add_argument("--position-policy", choices=["block_any", "allow_same_direction", "allow_any_until_max"], default="block_any")
    p.add_argument("--max-symbol-positions", type=int, default=1)
    p.add_argument("--max-symbol-lot", type=float, default=0.01)
    p.add_argument("--max-orders", type=int, default=1)
    p.add_argument("--deviation", type=int, default=50)
    p.add_argument("--latest-confirmed-policy", choices=["last", "second_last"], default="last")
    p.add_argument("--latest-confirmed-m5-policy", choices=["last", "second_last"], default="last")
    p.add_argument("--latest-confirmed-m1-policy", choices=["last", "second_last"], default="last")
    p.add_argument("--skip-router", action="store_true", help="Use existing router outputs instead of running router. Useful only for controlled tests.")
    p.add_argument("--reset-adapter-ledger", action="store_true", help="Pass --reset-ledger to adapter stage.")
    p.add_argument("--treat-position-block-as-safe", action="store_true", default=True)
    p.add_argument("--fail-on-position-block", action="store_false", dest="treat_position_block_as_safe")
    p.add_argument("--continue-on-stage-error", action="store_true")
    p.add_argument("--enable-demo-send", action="store_true", help="Required to pass --send to send_mt5_order_from_payload.py.")
    return p.parse_args()


def utc_now_text() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")


def read_json_or_empty(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"_read_error": str(exc), "_path": str(path)}


def write_json(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def append_csv_row(path: Path, row: dict[str, Any], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([{col: row.get(col, "") for col in columns}]).to_csv(
        path,
        mode="a",
        header=not path.exists(),
        index=False,
        encoding="utf-8-sig",
    )


def run_cmd(cmd: list[str]) -> int:
    print("[CMD] " + " ".join(cmd), flush=True)
    completed = subprocess.run(cmd, cwd=str(REPO_ROOT), text=True, encoding="utf-8", errors="replace")
    return int(completed.returncode)


def build_router_cmd(args: argparse.Namespace) -> list[str]:
    return [
        sys.executable,
        str(REPO_ROOT / "scripts" / "run_gold_multi_strategy_dry_run_cycle.py"),
        "--csv-dir", str(args.csv_dir),
        "--router-out-dir", str(args.router_out_dir),
        "--buy-out-dir", str(args.buy_out_dir),
        "--sell-out-dir", str(args.sell_out_dir),
        "--latest-confirmed-policy", str(args.latest_confirmed_policy),
        "--latest-confirmed-m5-policy", str(args.latest_confirmed_m5_policy),
        "--latest-confirmed-m1-policy", str(args.latest_confirmed_m1_policy),
        "--continue-on-strategy-error",
    ]


def build_adapter_cmd(args: argparse.Namespace) -> list[str]:
    cmd = [
        sys.executable,
        str(REPO_ROOT / "scripts" / "run_gold_multi_strategy_autotrade_adapter_dry_run.py"),
        "--router-out-dir", str(args.router_out_dir),
        "--out-dir", str(args.adapter_out_dir),
        "--broker-symbol", str(args.broker_symbol),
    ]
    if args.reset_adapter_ledger:
        cmd.append("--reset-ledger")
    return cmd


def build_payload_bridge_cmd(args: argparse.Namespace) -> list[str]:
    return [
        sys.executable,
        str(REPO_ROOT / "scripts" / "build_gold_multi_strategy_mochipoyo_order_payloads_dry_run.py"),
        "--adapter-out-dir", str(args.adapter_out_dir),
        "--out-dir", str(args.payload_out_dir),
        "--broker-symbol", str(args.broker_symbol),
        "--fixed-lot", str(args.fixed_lot),
        "--magic", str(args.magic),
        "--max-orders", str(args.max_orders),
    ]


def payload_rows_count(path: Path) -> int:
    if not path.exists():
        return 0
    try:
        df = pd.read_csv(path, encoding="utf-8-sig")
    except Exception:
        return 0
    return int(len(df))


def build_mt5_send_cmd(args: argparse.Namespace) -> list[str] | None:
    input_csv = args.payload_out_dir / "order_payloads.csv"
    if payload_rows_count(input_csv) <= 0:
        return None
    cmd = [
        sys.executable,
        str(REPO_ROOT / "scripts" / "send_mt5_order_from_payload.py"),
        "--input-csv", str(input_csv),
        "--order-ledger-csv", str(args.order_ledger_csv),
        "--out-dir", str(args.mt5_send_out_dir),
        "--symbol", str(args.broker_symbol),
        "--max-orders", str(args.max_orders),
        "--deviation", str(args.deviation),
        "--position-policy", str(args.position_policy),
        "--max-symbol-positions", str(args.max_symbol_positions),
        "--max-symbol-lot", str(args.max_symbol_lot),
    ]
    if args.select_symbol:
        cmd.append("--select-symbol")
    if args.expected_login is not None:
        cmd.extend(["--expected-login", str(args.expected_login)])
    if args.require_demo_account:
        cmd.append("--require-demo-account")
    if args.enable_demo_send:
        cmd.append("--send")
    return cmd


def int_value(obj: dict[str, Any], key: str, default: int = 0) -> int:
    try:
        return int(obj.get(key, default) or 0)
    except Exception:
        return default


def bool_value(obj: dict[str, Any], key: str, default: bool = False) -> bool:
    val = obj.get(key, default)
    if isinstance(val, bool):
        return val
    return str(val).lower() in {"true", "1", "yes", "y"}


def summarize_mt5_status(report: dict[str, Any]) -> str:
    rows = report.get("results", [])
    if not isinstance(rows, list) or not rows:
        return "NO_MT5_ROWS"
    statuses = []
    for row in rows:
        if isinstance(row, dict):
            statuses.append(str(row.get("order_status", "")))
    return ",".join(statuses) if statuses else "NO_MT5_STATUS"


def safety_guard_ok(args: argparse.Namespace) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if not args.enable_demo_send:
        errors.append("--enable-demo-send is required for real demo send cycle")
    if int(args.expected_login) != 75539039:
        errors.append(f"expected_login must be 75539039 for first send cycle: {args.expected_login}")
    if not args.require_demo_account:
        errors.append("--require-demo-account must remain enabled")
    if str(args.broker_symbol) != "GOLD#":
        errors.append(f"broker_symbol must be GOLD# for first send cycle: {args.broker_symbol}")
    if float(args.fixed_lot) != 0.01:
        errors.append(f"fixed_lot must be 0.01 for first send cycle: {args.fixed_lot}")
    if str(args.position_policy) != "block_any":
        errors.append(f"position_policy must be block_any for first send cycle: {args.position_policy}")
    if int(args.max_symbol_positions) != 1:
        errors.append(f"max_symbol_positions must be 1 for first send cycle: {args.max_symbol_positions}")
    if float(args.max_symbol_lot) != 0.01:
        errors.append(f"max_symbol_lot must be 0.01 for first send cycle: {args.max_symbol_lot}")
    if int(args.max_orders) != 1:
        errors.append(f"max_orders must be 1 for first send cycle: {args.max_orders}")
    return len(errors) == 0, errors


def main() -> int:
    args = parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    cycle_start = utc_now_text()
    guard_ok, guard_errors = safety_guard_ok(args)
    print(f"[INFO] cycle_start_utc={cycle_start}")
    print(f"[INFO] out_dir={args.out_dir}")
    print(f"[INFO] enable_demo_send={args.enable_demo_send}")
    if not guard_ok:
        result = {
            "schema_version": "gold_multi_strategy_demo_autotrade_send_cycle_v1",
            "cycle_start_utc": cycle_start,
            "cycle_end_utc": utc_now_text(),
            "cycle_ok": False,
            "send_enabled": bool(args.enable_demo_send),
            "safe_send_guard_ok": False,
            "guard_errors": guard_errors,
            "message": "Refused to run send cycle because mandatory demo-send safety guards failed.",
        }
        latest_path = args.out_dir / "latest_multi_strategy_demo_autotrade_send_cycle_result.json"
        write_json(latest_path, result)
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return 2

    router_rc: int | str = "SKIPPED"
    if not args.skip_router:
        router_rc = run_cmd(build_router_cmd(args))
        if router_rc != 0 and not args.continue_on_stage_error:
            print("[ERROR] router stage failed", flush=True)
    else:
        print("[INFO] router stage skipped; using existing router outputs", flush=True)

    adapter_rc: int | str = "SKIPPED"
    if router_rc == 0 or router_rc == "SKIPPED" or args.continue_on_stage_error:
        adapter_rc = run_cmd(build_adapter_cmd(args))
        if adapter_rc != 0 and not args.continue_on_stage_error:
            print("[ERROR] adapter stage failed", flush=True)

    bridge_rc: int | str = "SKIPPED"
    if adapter_rc == 0 or args.continue_on_stage_error:
        bridge_rc = run_cmd(build_payload_bridge_cmd(args))
        if bridge_rc != 0 and not args.continue_on_stage_error:
            print("[ERROR] payload bridge stage failed", flush=True)

    mt5_rc: int | str = "SKIPPED_NO_PAYLOAD_ROWS"
    mt5_cmd = build_mt5_send_cmd(args)
    if mt5_cmd is not None and (bridge_rc == 0 or args.continue_on_stage_error):
        mt5_rc = run_cmd(mt5_cmd)
    elif mt5_cmd is None:
        print("[INFO] MT5 send stage skipped because order_payloads.csv has no rows", flush=True)

    router_result = read_json_or_empty(args.router_out_dir / "latest_multi_strategy_cycle_result.json")
    adapter_result = read_json_or_empty(args.adapter_out_dir / "latest_adapter_result.json")
    bridge_result = read_json_or_empty(args.payload_out_dir / "order_payloads.json")
    mt5_report = read_json_or_empty(args.mt5_send_out_dir / "mt5_order_send_report.json")

    mt5_order_send_called = int_value(mt5_report, "order_send_called_count", 0)
    mt5_sent_rows = int_value(mt5_report, "sent_rows", 0)
    mt5_blocked_policy = int_value(mt5_report, "blocked_position_policy_rows", 0)
    mt5_error_rows = int_value(mt5_report, "error_rows", 0)
    mt5_rows_out = int_value(mt5_report, "rows_out", 0)
    send_requested = bool_value(mt5_report, "send_requested", False)

    mt5_stage_ok = True
    if isinstance(mt5_rc, int) and mt5_rc != 0:
        if args.treat_position_block_as_safe and mt5_blocked_policy > 0 and mt5_order_send_called == 0 and mt5_sent_rows == 0:
            mt5_stage_ok = True
        else:
            mt5_stage_ok = False
    stage_returncodes_ok = (
        (router_rc == 0 or router_rc == "SKIPPED")
        and adapter_rc == 0
        and bridge_rc == 0
        and mt5_stage_ok
    )
    cycle_ok = bool(stage_returncodes_ok and guard_ok)
    cycle_end = utc_now_text()

    summary = {
        "schema_version": "gold_multi_strategy_demo_autotrade_send_cycle_v1",
        "cycle_start_utc": cycle_start,
        "cycle_end_utc": cycle_end,
        "cycle_ok": cycle_ok,
        "send_enabled": bool(args.enable_demo_send),
        "send_requested": bool(send_requested),
        "safe_send_guard_ok": bool(guard_ok),
        "guard_errors": guard_errors,
        "treat_position_block_as_safe": bool(args.treat_position_block_as_safe),
        "csv_dir": str(args.csv_dir),
        "out_dir": str(args.out_dir),
        "router_out_dir": str(args.router_out_dir),
        "adapter_out_dir": str(args.adapter_out_dir),
        "payload_out_dir": str(args.payload_out_dir),
        "mt5_send_out_dir": str(args.mt5_send_out_dir),
        "order_ledger_csv": str(args.order_ledger_csv),
        "returncodes": {
            "router": router_rc,
            "adapter": adapter_rc,
            "payload_bridge": bridge_rc,
            "mt5_send": mt5_rc,
        },
        "router_result": router_result,
        "adapter_result": adapter_result,
        "payload_bridge_result": bridge_result,
        "mt5_report": mt5_report,
        "key_metrics": {
            "router_ok": router_result.get("router_ok", ""),
            "adapter_ok": adapter_result.get("adapter_ok", ""),
            "bridge_ok": bridge_result.get("bridge_ok", ""),
            "router_mode": router_result.get("router_mode", ""),
            "signals_found_count": int_value(router_result, "signals_found_count", 0),
            "open_order_intent_count": int_value(router_result, "open_order_intent_count", 0),
            "close_intent_count": int_value(router_result, "close_intent_count", 0),
            "order_intents_read": int_value(adapter_result, "order_intents_read", 0),
            "close_intents_read": int_value(adapter_result, "close_intents_read", 0),
            "order_previews_created": int_value(adapter_result, "order_previews_created", 0),
            "close_previews_created": int_value(adapter_result, "close_previews_created", 0),
            "duplicate_previews_skipped": int_value(adapter_result, "duplicate_previews_skipped", 0),
            "adapter_rejects": int_value(adapter_result, "rejects", 0),
            "payload_rows_in": int_value(bridge_result, "rows_in", 0),
            "payload_rows_out": int_value(bridge_result, "rows_out", 0),
            "valid_order_payloads": int_value(bridge_result, "valid_order_payloads", 0),
            "payload_rejects": int_value(bridge_result, "rejects", 0),
            "mt5_rows_out": mt5_rows_out,
            "mt5_dry_run_check_ok_rows": int_value(mt5_report, "dry_run_check_ok_rows", 0),
            "mt5_blocked_position_policy_rows": mt5_blocked_policy,
            "mt5_order_send_called_count": mt5_order_send_called,
            "mt5_sent_rows": mt5_sent_rows,
            "mt5_error_rows": mt5_error_rows,
            "mt5_position_policy": mt5_report.get("position_policy", ""),
            "mt5_account_login": mt5_report.get("account_info", {}).get("login", "") if isinstance(mt5_report.get("account_info"), dict) else "",
            "mt5_account_server": mt5_report.get("account_info", {}).get("server", "") if isinstance(mt5_report.get("account_info"), dict) else "",
            "mt5_account_name": mt5_report.get("account_info", {}).get("name", "") if isinstance(mt5_report.get("account_info"), dict) else "",
            "mt5_status_summary": summarize_mt5_status(mt5_report),
        },
    }

    latest_path = args.out_dir / "latest_multi_strategy_demo_autotrade_send_cycle_result.json"
    log_path = args.out_dir / "multi_strategy_demo_autotrade_send_cycle_log.csv"
    write_json(latest_path, summary)
    metrics = summary["key_metrics"]
    append_csv_row(log_path, {
        "cycle_start_utc": cycle_start,
        "cycle_end_utc": cycle_end,
        "cycle_ok": cycle_ok,
        "send_enabled": bool(args.enable_demo_send),
        "send_requested": bool(send_requested),
        "safe_send_guard_ok": bool(guard_ok),
        "csv_dir": str(args.csv_dir),
        "out_dir": str(args.out_dir),
        "router_out_dir": str(args.router_out_dir),
        "adapter_out_dir": str(args.adapter_out_dir),
        "payload_out_dir": str(args.payload_out_dir),
        "mt5_send_out_dir": str(args.mt5_send_out_dir),
        "router_returncode": router_rc,
        "adapter_returncode": adapter_rc,
        "payload_bridge_returncode": bridge_rc,
        "mt5_send_returncode": mt5_rc,
        "latest_cycle_result_json": str(latest_path),
        **metrics,
    }, CYCLE_LOG_COLUMNS)

    print("[INFO] multi-strategy demo autotrade send cycle completed")
    print(json.dumps({
        "cycle_ok": cycle_ok,
        "send_enabled": bool(args.enable_demo_send),
        "send_requested": bool(send_requested),
        "safe_send_guard_ok": bool(guard_ok),
        "returncodes": summary["returncodes"],
        "key_metrics": metrics,
        "latest_cycle_result_json": str(latest_path),
        "cycle_log": str(log_path),
    }, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if cycle_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
