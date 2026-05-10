#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Run a full safe fresh-payload sender-registry-policy validation cycle.

Validated chain wrapped into one command:

1. Build fresh MT5-tick-based sender-valid payload.
2. Run send_mt5_order_from_payload.py dry-run + sender registry preview cycle.
3. Build mock positions from the generated registry preview.
4. Reconcile registry preview with mock positions.
5. Run registry-aware policy preview and confirm same_strategy BLOCK path.

Safety:
- This wrapper never passes --send.
- It does not write production position_registry.csv.
- It does not mutate existing Mochipoyo ledgers.
- It does not mutate trigger-state files.
- It does not modify existing BAT files.
- It only reads MT5 tick/account/symbol metadata via the fresh-payload builder and
  order_check via the sender dry-run. It never calls mt5.order_send.

Windows path note:
- send_mt5_order_from_payload.py still uses a plain Path.mkdir for its out-dir.
- Therefore this wrapper intentionally uses very short work subdirectories:
  f / c / r / p, and short summary filenames.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

SCHEMA_VERSION = "gold_multi_strategy_fresh_sender_registry_policy_full_cycle_v1"
POSITION_POLICIES = ["block_any", "allow_same_direction", "allow_any_until_max"]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Full safe fresh sender-registry-policy validation cycle. Never sends orders.")
    p.add_argument("--out-dir", required=True)
    p.add_argument("--broker-symbol", default="GOLD#")
    p.add_argument("--symbol", default="GOLD")
    p.add_argument("--direction", choices=["BUY", "SELL"], default="SELL")
    p.add_argument("--lot", type=float, default=0.01)
    p.add_argument("--sl-distance", type=float, default=10.0)
    p.add_argument("--tp-distance", type=float, default=20.0)
    p.add_argument("--expected-login", type=int, default=75539039)
    p.add_argument("--require-demo-account", action="store_true")
    p.add_argument("--allow-live-account", action="store_true")
    p.add_argument("--select-symbol", action="store_true")
    p.add_argument("--terminal-path", default=None)
    p.add_argument("--portable", action="store_true")
    p.add_argument("--position-policy", choices=POSITION_POLICIES, default="allow_any_until_max")
    p.add_argument("--max-orders", type=int, default=1)
    p.add_argument("--max-symbol-positions", type=int, default=5)
    p.add_argument("--max-symbol-lot", type=float, default=0.05)
    p.add_argument("--max-total-positions", type=int, default=5)
    p.add_argument("--max-lot-per-order", type=float, default=0.02)
    p.add_argument("--position-ticket-start", type=int, default=990001)
    p.add_argument("--order-ticket-start", type=int, default=880001)
    p.add_argument("--deal-ticket-start", type=int, default=770001)
    p.add_argument("--position-status", default="ACTIVE")
    p.add_argument("--python-exe", default=sys.executable)
    return p.parse_args()


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


def utc_now_text() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")


def console_json(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=True, indent=2, sort_keys=True, default=str)


def safe_print(text: Any) -> None:
    print(str(text).encode("ascii", errors="backslashreplace").decode("ascii"))


def write_json(path: Path, obj: dict[str, Any]) -> None:
    Path(windows_long_path(path.parent)).mkdir(parents=True, exist_ok=True)
    Path(windows_long_path(path)).write_text(
        json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True, default=str),
        encoding="utf-8",
    )


def read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(Path(windows_long_path(path)).read_text(encoding="utf-8"))
    except Exception:
        return {}


def read_csv_len(path: Path) -> int:
    try:
        return int(len(pd.read_csv(windows_long_path(path), encoding="utf-8-sig")))
    except Exception:
        return 0


def run_step(name: str, cmd: list[str]) -> dict[str, Any]:
    started = utc_now_text()
    proc = subprocess.run(
        cmd,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=False,
    )
    return {
        "name": name,
        "started_at_utc": started,
        "finished_at_utc": utc_now_text(),
        "returncode": int(proc.returncode),
        "ok": proc.returncode == 0,
        "cmd": cmd,
        "stdout_tail": proc.stdout[-12000:],
        "stderr_tail": proc.stderr[-12000:],
    }


def script_path(name: str) -> str:
    return str(Path("scripts") / name)


def add_common_mt5_args(cmd: list[str], args: argparse.Namespace) -> list[str]:
    if args.expected_login is not None:
        cmd += ["--expected-login", str(args.expected_login)]
    if args.require_demo_account:
        cmd.append("--require-demo-account")
    if args.allow_live_account:
        cmd.append("--allow-live-account")
    if args.select_symbol:
        cmd.append("--select-symbol")
    if args.terminal_path:
        cmd += ["--terminal-path", str(args.terminal_path)]
    if args.portable:
        cmd.append("--portable")
    return cmd


def stop(summary: dict[str, Any], summary_json: Path, reason: str, code: int) -> int:
    summary["reason"] = reason
    write_json(summary_json, summary)
    safe_print("run_gold_multi_strategy_fresh_sender_registry_policy_full_cycle")
    safe_print(console_json(summary))
    return code


def main() -> int:
    args = parse_args()
    out_dir = Path(args.out_dir)
    Path(windows_long_path(out_dir)).mkdir(parents=True, exist_ok=True)

    # Keep these deliberately short. The real sender still uses plain Path.mkdir.
    fresh_dir = out_dir / "f"
    cycle_dir = out_dir / "c"
    reconcile_dir = out_dir / "r"
    policy_dir = out_dir / "p"
    mock_positions_csv = out_dir / "mp.csv"
    summary_json = out_dir / "summary.json"

    payload_csv = fresh_dir / "order_payloads.csv"
    order_ledger_csv = fresh_dir / "dry_run_order_ledger.csv"
    registry_csv = cycle_dir / "sender_registry_preview" / "sender_registry_preview.csv"

    summary: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "cycle_time_utc": utc_now_text(),
        "cycle_ok": False,
        "reason": "STARTED",
        "out_dir": str(out_dir),
        "fresh_payload_csv": str(payload_csv),
        "order_ledger_csv": str(order_ledger_csv),
        "registry_csv": str(registry_csv),
        "mock_positions_csv": str(mock_positions_csv),
        "reconcile_out_dir": str(reconcile_dir),
        "policy_out_dir": str(policy_dir),
        "send_requested": False,
        "safety": {
            "wrapper_passed_send_flag": False,
            "production_registry_mutated": False,
            "trigger_state_mutated": False,
            "existing_sender_modified": False,
            "existing_bat_modified": False,
        },
        "steps": [],
    }

    fresh_cmd = [
        args.python_exe,
        script_path("build_gold_multi_strategy_fresh_sender_valid_payload_from_mt5_tick.py"),
        "--out-dir", str(fresh_dir),
        "--broker-symbol", str(args.broker_symbol),
        "--symbol", str(args.symbol),
        "--direction", str(args.direction),
        "--lot", str(args.lot),
        "--sl-distance", str(args.sl_distance),
        "--tp-distance", str(args.tp_distance),
    ]
    fresh_cmd = add_common_mt5_args(fresh_cmd, args)
    fresh_step = run_step("build_fresh_sender_valid_payload", fresh_cmd)
    summary["steps"].append(fresh_step)
    fresh_summary = read_json(fresh_dir / "fresh_sender_valid_payload_summary.json")
    summary["fresh_payload"] = {
        "build_ok": fresh_summary.get("build_ok", False),
        "reason": fresh_summary.get("reason", ""),
        "rows_out": fresh_summary.get("rows_out", 0),
        "price_meta": fresh_summary.get("price_meta", {}),
        "order_key": fresh_summary.get("order_key", ""),
    }
    if not fresh_step["ok"]:
        return stop(summary, summary_json, "FRESH_PAYLOAD_BUILD_FAILED", 10)

    cycle_cmd = [
        args.python_exe,
        script_path("run_gold_multi_strategy_sender_dry_run_registry_preview_cycle.py"),
        "--input-csv", str(payload_csv),
        "--order-ledger-csv", str(order_ledger_csv),
        "--out-dir", str(cycle_dir),
        "--symbol", str(args.broker_symbol),
        "--max-orders", str(args.max_orders),
        "--position-policy", str(args.position_policy),
        "--max-symbol-positions", str(args.max_symbol_positions),
        "--max-symbol-lot", str(args.max_symbol_lot),
        "--registry-preview-position-ticket-start", str(args.position_ticket_start),
        "--registry-preview-order-ticket-start", str(args.order_ticket_start),
        "--registry-preview-deal-ticket-start", str(args.deal_ticket_start),
        "--registry-preview-position-status", str(args.position_status),
    ]
    cycle_cmd = add_common_mt5_args(cycle_cmd, args)
    cycle_step = run_step("sender_dry_run_registry_preview_cycle", cycle_cmd)
    summary["steps"].append(cycle_step)
    cycle_summary = read_json(cycle_dir / "sender_dry_run_registry_preview_cycle_summary.json")
    summary["sender_cycle"] = {
        "cycle_ok": cycle_summary.get("cycle_ok", False),
        "reason": cycle_summary.get("reason", ""),
        "sender_metrics": cycle_summary.get("sender_metrics", {}),
        "registry_preview_rows": cycle_summary.get("registry_preview_rows", 0),
        "registry_preview_reason": cycle_summary.get("registry_preview_reason", ""),
    }
    if not cycle_step["ok"]:
        return stop(summary, summary_json, "SENDER_REGISTRY_PREVIEW_CYCLE_FAILED", 20)

    mock_cmd = [
        args.python_exe,
        script_path("build_gold_multi_strategy_mock_positions_from_registry.py"),
        "--registry-csv", str(registry_csv),
        "--output-csv", str(mock_positions_csv),
    ]
    mock_step = run_step("build_mock_positions_from_registry", mock_cmd)
    summary["steps"].append(mock_step)
    mock_summary = read_json(mock_positions_csv.with_suffix(".json"))
    summary["mock_positions"] = {
        "build_ok": mock_summary.get("build_ok", False),
        "reason": mock_summary.get("reason", ""),
        "rows_out": mock_summary.get("rows_out", read_csv_len(mock_positions_csv)),
    }
    if not mock_step["ok"]:
        return stop(summary, summary_json, "MOCK_POSITIONS_BUILD_FAILED", 30)

    reconcile_cmd = [
        args.python_exe,
        script_path("run_gold_multi_strategy_position_registry_reconcile_dry_run.py"),
        "--registry-csv", str(registry_csv),
        "--positions-csv", str(mock_positions_csv),
        "--out-dir", str(reconcile_dir),
        "--symbol", str(args.broker_symbol),
    ]
    reconcile_step = run_step("reconcile_registry_with_mock_positions", reconcile_cmd)
    summary["steps"].append(reconcile_step)
    reconcile_summary = read_json(reconcile_dir / "position_registry_reconcile_dry_run.json")
    summary["reconcile"] = {
        "reconcile_ok": reconcile_summary.get("reconcile_ok", False),
        "reason": reconcile_summary.get("reason", ""),
        "matched_active_registry_rows": reconcile_summary.get("matched_active_registry_rows", 0),
        "matched_with_mismatch_rows": reconcile_summary.get("matched_with_mismatch_rows", 0),
        "missing_position_rows": reconcile_summary.get("missing_position_rows", 0),
        "unregistered_position_rows": reconcile_summary.get("unregistered_position_rows", 0),
        "status_counts": reconcile_summary.get("status_counts", {}),
    }
    if not reconcile_step["ok"]:
        return stop(summary, summary_json, "RECONCILE_FAILED", 40)

    policy_cmd = [
        args.python_exe,
        script_path("run_gold_multi_strategy_registry_policy_preview_longpath.py"),
        "--input-csv", str(payload_csv),
        "--positions-csv", str(mock_positions_csv),
        "--registry-csv", str(registry_csv),
        "--order-ledger-csv", str(order_ledger_csv),
        "--out-dir", str(policy_dir),
        "--symbol", str(args.broker_symbol),
        "--max-orders", str(args.max_orders),
        "--max-total-positions", str(args.max_total_positions),
        "--max-lot-per-order", str(args.max_lot_per_order),
    ]
    policy_step = run_step("registry_policy_preview", policy_cmd)
    summary["steps"].append(policy_step)
    policy_summary = read_json(policy_dir / "registry_policy_preview.json")
    summary["policy_preview"] = {
        "preview_ok": policy_summary.get("preview_ok", False),
        "reason": policy_summary.get("reason", ""),
        "rows_in": policy_summary.get("rows_in", 0),
        "rows_out": policy_summary.get("rows_out", 0),
        "allow_rows": policy_summary.get("allow_rows", 0),
        "blocked_rows": policy_summary.get("blocked_rows", 0),
        "same_strategy_blocked_rows": policy_summary.get("same_strategy_blocked_rows", 0),
        "opposite_direction_blocked_rows": policy_summary.get("opposite_direction_blocked_rows", 0),
        "registry_inconsistency_blocked_rows": policy_summary.get("registry_inconsistency_blocked_rows", 0),
        "reconcile_status_counts": policy_summary.get("reconcile_status_counts", {}),
    }
    if not policy_step["ok"]:
        return stop(summary, summary_json, "POLICY_PREVIEW_FAILED", 50)

    cycle_ok = bool(
        summary["fresh_payload"].get("build_ok")
        and summary["sender_cycle"].get("cycle_ok")
        and int(summary["sender_cycle"].get("sender_metrics", {}).get("dry_run_check_ok_rows", 0)) >= 1
        and int(summary["sender_cycle"].get("registry_preview_rows", 0)) >= 1
        and summary["mock_positions"].get("build_ok")
        and summary["reconcile"].get("reconcile_ok")
        and int(summary["reconcile"].get("matched_active_registry_rows", 0)) >= 1
        and int(summary["reconcile"].get("matched_with_mismatch_rows", 0)) == 0
        and summary["policy_preview"].get("preview_ok")
        and int(summary["policy_preview"].get("same_strategy_blocked_rows", 0)) >= 1
        and int(summary["policy_preview"].get("registry_inconsistency_blocked_rows", 0)) == 0
    )
    summary["cycle_ok"] = cycle_ok
    summary["reason"] = "FRESH_SENDER_REGISTRY_POLICY_FULL_CYCLE_PASS" if cycle_ok else "FRESH_SENDER_REGISTRY_POLICY_FULL_CYCLE_FAILED_EXPECTATIONS"
    write_json(summary_json, summary)

    safe_print("run_gold_multi_strategy_fresh_sender_registry_policy_full_cycle")
    safe_print(console_json({k: v for k, v in summary.items() if k != "steps"}))
    step_df = pd.DataFrame([{"name": s["name"], "ok": s["ok"], "returncode": s["returncode"]} for s in summary["steps"]])
    safe_print(step_df.to_string(index=False))
    safe_print(f"summary_json: {summary_json}")
    safe_print("done")
    return 0 if cycle_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
