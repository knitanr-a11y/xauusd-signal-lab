#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""One-cycle sender-adjacent registry preview integration for GOLD multi-strategy.

This script is intentionally dry-run / preview-only.

Purpose:
- Take an existing order_payloads.csv candidate file.
- Simulate a successful send result with synthetic tickets.
- Build preview position_registry rows from the payload.
- Reconcile the preview registry against a provided positions snapshot/mock CSV.
- Run registry-aware policy preview using the generated registry.
- Write one combined summary JSON/CSV.

Safety:
- No MetaTrader5 import.
- No mt5.order_check.
- No mt5.order_send.
- No real sender modification.
- No existing Mochipoyo ledger mutation.
- No trigger-state mutation.
- No production registry mutation by default.

This is a sender-adjacent integration test, not an order sender.
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

SCHEMA_VERSION = "gold_multi_strategy_demo_send_registry_preview_cycle_v1"

DEFAULT_PAYLOAD_CSV = Path("data/research_results/gold_multi_strategy_mochipoyo_payload_bridge_dry_run/order_payloads.csv")
DEFAULT_POSITIONS_CSV = Path("data/research_results/gold_multi_strategy_position_policy_preflight/mock_positions_same_strategy_buy_c.csv")
DEFAULT_ORDER_LEDGER_CSV = Path("data/research_results/gold_multi_strategy_mochipoyo_payload_bridge_dry_run/dry_run_order_ledger.csv")
DEFAULT_OUT_DIR = Path("data/research_results/gold_multi_strategy_demo_send_registry_preview_cycle")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run one dry-run registry preview cycle. No order_send/order_check.")
    p.add_argument("--payload-csv", type=Path, default=DEFAULT_PAYLOAD_CSV)
    p.add_argument("--positions-csv", type=Path, default=DEFAULT_POSITIONS_CSV)
    p.add_argument("--order-ledger-csv", type=Path, default=DEFAULT_ORDER_LEDGER_CSV)
    p.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    p.add_argument("--symbol", default="GOLD#")
    p.add_argument("--max-orders", type=int, default=1)
    p.add_argument("--max-total-positions", type=int, default=5)
    p.add_argument("--max-lot-per-order", type=float, default=0.02)
    p.add_argument("--account-login", type=int, default=75539039)
    p.add_argument("--account-server", default="XMTrading-MT5 3")
    p.add_argument("--position-ticket-start", type=int, default=990001)
    p.add_argument("--order-ticket-start", type=int, default=880001)
    p.add_argument("--deal-ticket-start", type=int, default=770001)
    p.add_argument("--position-status", default="ACTIVE")
    p.add_argument("--python-exe", default=sys.executable)
    p.add_argument(
        "--allow-registry-inconsistency",
        action="store_true",
        help="Pass through to registry policy preview. Default blocks registry inconsistency.",
    )
    p.add_argument(
        "--continue-on-step-error",
        action="store_true",
        help="Write partial summary and continue when a child step fails. Default stops on first failure.",
    )
    return p.parse_args()


def utc_now_text() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")


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


def read_csv_len(path: Path) -> int:
    if not path.exists():
        return 0
    try:
        return int(len(pd.read_csv(windows_long_path(path), encoding="utf-8-sig")))
    except Exception:
        return 0


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        return {"json_read_error": repr(e), "path": str(path)}


def write_json(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True, default=str), encoding="utf-8")


def write_summary_csv(path: Path, summary: dict[str, Any]) -> None:
    row = {
        "cycle_time_utc": summary.get("cycle_time_utc", ""),
        "cycle_ok": summary.get("cycle_ok", False),
        "reason": summary.get("reason", ""),
        "payload_rows": summary.get("payload_rows", 0),
        "registry_rows_out_new": summary.get("registry_builder", {}).get("rows_out_new", ""),
        "reconcile_ok": summary.get("reconcile", {}).get("reconcile_ok", ""),
        "matched_active_registry_rows": summary.get("reconcile", {}).get("matched_active_registry_rows", ""),
        "missing_position_rows": summary.get("reconcile", {}).get("missing_position_rows", ""),
        "unregistered_position_rows": summary.get("reconcile", {}).get("unregistered_position_rows", ""),
        "policy_preview_ok": summary.get("policy_preview", {}).get("preview_ok", ""),
        "allow_rows": summary.get("policy_preview", {}).get("allow_rows", ""),
        "blocked_rows": summary.get("policy_preview", {}).get("blocked_rows", ""),
        "same_strategy_blocked_rows": summary.get("policy_preview", {}).get("same_strategy_blocked_rows", ""),
        "registry_inconsistency_blocked_rows": summary.get("policy_preview", {}).get("registry_inconsistency_blocked_rows", ""),
        "order_send_called_count": summary.get("safety", {}).get("order_send_called_count", 0),
        "order_check_called_count": summary.get("safety", {}).get("order_check_called_count", 0),
        "registry_mutated": summary.get("safety", {}).get("registry_mutated", False),
        "ledger_mutated": summary.get("safety", {}).get("ledger_mutated", False),
        "trigger_state_mutated": summary.get("safety", {}).get("trigger_state_mutated", False),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([row]).to_csv(windows_long_path(path), index=False, encoding="utf-8-sig")


def run_step(name: str, cmd: list[str], cwd: Path | None = None) -> dict[str, Any]:
    started = utc_now_text()
    proc = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
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
        "stdout_tail": proc.stdout[-8000:],
        "stderr_tail": proc.stderr[-8000:],
    }


def script_path(name: str) -> str:
    return str(Path("scripts") / name)


def main() -> int:
    args = parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    cycle_time = utc_now_text()

    registry_preview_csv = args.out_dir / "position_registry_from_payload_preview_cycle.csv"
    registry_preview_json = args.out_dir / "position_registry_from_payload_preview_cycle.json"
    reconcile_csv = args.out_dir / "position_registry_reconcile_cycle.csv"
    reconcile_json = args.out_dir / "position_registry_reconcile_cycle.json"
    positions_snapshot_csv = args.out_dir / "position_registry_reconcile_positions_snapshot_cycle.csv"
    policy_preview_csv = args.out_dir / "registry_policy_preview_cycle.csv"
    policy_preview_json = args.out_dir / "registry_policy_preview_cycle.json"
    policy_reconcile_csv = args.out_dir / "registry_policy_preview_reconcile_cycle.csv"
    summary_json = args.out_dir / "demo_send_registry_preview_cycle_summary.json"
    summary_csv = args.out_dir / "demo_send_registry_preview_cycle_summary.csv"

    payload_rows = read_csv_len(args.payload_csv)
    steps: list[dict[str, Any]] = []
    summary: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "cycle_time_utc": cycle_time,
        "cycle_ok": False,
        "reason": "STARTED",
        "payload_csv": str(args.payload_csv),
        "positions_csv": str(args.positions_csv),
        "order_ledger_csv": str(args.order_ledger_csv),
        "out_dir": str(args.out_dir),
        "payload_rows": payload_rows,
        "max_orders": int(args.max_orders),
        "symbol": args.symbol,
        "outputs": {
            "registry_preview_csv": str(registry_preview_csv),
            "registry_preview_json": str(registry_preview_json),
            "reconcile_csv": str(reconcile_csv),
            "reconcile_json": str(reconcile_json),
            "positions_snapshot_csv": str(positions_snapshot_csv),
            "policy_preview_csv": str(policy_preview_csv),
            "policy_preview_json": str(policy_preview_json),
            "policy_reconcile_csv": str(policy_reconcile_csv),
            "summary_json": str(summary_json),
            "summary_csv": str(summary_csv),
        },
        "safety": safety_summary(),
    }

    if payload_rows <= 0:
        summary.update({
            "cycle_ok": True,
            "reason": "NO_PAYLOAD_ROWS",
            "steps": steps,
            "registry_builder": {},
            "reconcile": {},
            "policy_preview": {},
        })
        write_json(summary_json, summary)
        write_summary_csv(summary_csv, summary)
        print("run_gold_multi_strategy_demo_send_registry_preview_cycle")
        print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True, default=str))
        return 0

    build_cmd = [
        args.python_exe,
        script_path("build_gold_multi_strategy_position_registry_from_payload_preview.py"),
        "--input-csv", str(args.payload_csv),
        "--out-dir", str(args.out_dir),
        "--output-csv", str(registry_preview_csv),
        "--output-json", str(registry_preview_json),
        "--max-rows", str(args.max_orders),
        "--account-login", str(args.account_login),
        "--account-server", str(args.account_server),
        "--position-ticket-start", str(args.position_ticket_start),
        "--order-ticket-start", str(args.order_ticket_start),
        "--deal-ticket-start", str(args.deal_ticket_start),
        "--position-status", str(args.position_status),
        "--sender-report-json", "SYNTHETIC_SEND_RESULT_FROM_DEMO_SEND_REGISTRY_PREVIEW_CYCLE",
        "--notes", "generated by demo send registry preview cycle; no real order_send",
    ]
    step = run_step("build_registry_from_payload_preview", build_cmd)
    steps.append(step)
    if not step["ok"] and not args.continue_on_step_error:
        return finish(summary, steps, summary_json, summary_csv, "BUILD_REGISTRY_PREVIEW_FAILED", 10)

    reconcile_cmd = [
        args.python_exe,
        script_path("run_gold_multi_strategy_position_registry_reconcile_dry_run.py"),
        "--registry-csv", str(registry_preview_csv),
        "--positions-csv", str(args.positions_csv),
        "--out-dir", str(args.out_dir),
        "--output-csv", str(reconcile_csv),
        "--output-json", str(reconcile_json),
        "--positions-snapshot-csv", str(positions_snapshot_csv),
        "--symbol", str(args.symbol),
    ]
    step = run_step("registry_reconcile_dry_run", reconcile_cmd)
    steps.append(step)
    if not step["ok"] and not args.continue_on_step_error:
        return finish(summary, steps, summary_json, summary_csv, "REGISTRY_RECONCILE_FAILED", 11)

    policy_cmd = [
        args.python_exe,
        script_path("run_gold_multi_strategy_registry_policy_preview.py"),
        "--input-csv", str(args.payload_csv),
        "--positions-csv", str(args.positions_csv),
        "--registry-csv", str(registry_preview_csv),
        "--order-ledger-csv", str(args.order_ledger_csv),
        "--out-dir", str(args.out_dir),
        "--output-csv", str(policy_preview_csv),
        "--output-json", str(policy_preview_json),
        "--reconcile-csv", str(policy_reconcile_csv),
        "--symbol", str(args.symbol),
        "--max-orders", str(args.max_orders),
        "--max-total-positions", str(args.max_total_positions),
        "--max-lot-per-order", str(args.max_lot_per_order),
    ]
    if args.allow_registry_inconsistency:
        policy_cmd.append("--allow-registry-inconsistency")
    step = run_step("registry_policy_preview", policy_cmd)
    steps.append(step)
    if not step["ok"] and not args.continue_on_step_error:
        return finish(summary, steps, summary_json, summary_csv, "REGISTRY_POLICY_PREVIEW_FAILED", 12)

    registry_builder = read_json(registry_preview_json)
    reconcile = read_json(reconcile_json)
    policy_preview = read_json(policy_preview_json)
    cycle_ok = all(step.get("ok") for step in steps) and bool(policy_preview.get("preview_ok", False))
    reason = "CYCLE_EVALUATED" if cycle_ok else "CYCLE_COMPLETED_WITH_ERRORS"
    summary.update({
        "cycle_ok": bool(cycle_ok),
        "reason": reason,
        "steps": steps,
        "registry_builder": registry_builder,
        "reconcile": reconcile,
        "policy_preview": policy_preview,
    })
    write_json(summary_json, summary)
    write_summary_csv(summary_csv, summary)

    print("run_gold_multi_strategy_demo_send_registry_preview_cycle")
    print(json.dumps({k: v for k, v in summary.items() if k not in {"steps"}}, ensure_ascii=False, indent=2, sort_keys=True, default=str))
    print_step_table(steps)
    print(f"summary_json: {summary_json}")
    print(f"summary_csv: {summary_csv}")
    print("done")
    return 0 if cycle_ok else 1


def finish(summary: dict[str, Any], steps: list[dict[str, Any]], summary_json: Path, summary_csv: Path, reason: str, code: int) -> int:
    summary.update({
        "cycle_ok": False,
        "reason": reason,
        "steps": steps,
    })
    write_json(summary_json, summary)
    write_summary_csv(summary_csv, summary)
    print("run_gold_multi_strategy_demo_send_registry_preview_cycle")
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True, default=str))
    return code


def print_step_table(steps: list[dict[str, Any]]) -> None:
    if not steps:
        print("[INFO] no child steps executed")
        return
    df = pd.DataFrame([{ "name": s.get("name"), "ok": s.get("ok"), "returncode": s.get("returncode") } for s in steps])
    print(df.to_string(index=False))


def safety_summary() -> dict[str, Any]:
    return {
        "mt5_imported": False,
        "order_check_called_count": 0,
        "order_send_called_count": 0,
        "registry_mutated": False,
        "ledger_mutated": False,
        "trigger_state_mutated": False,
        "real_sender_modified": False,
        "existing_bat_modified": False,
    }


if __name__ == "__main__":
    raise SystemExit(main())
