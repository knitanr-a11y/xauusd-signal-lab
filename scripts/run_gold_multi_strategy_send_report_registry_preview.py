#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build registry preview from an existing guarded demo send-cycle report.

This script is sender-adjacent but still dry-run / preview-only.

Purpose:
- Read latest_multi_strategy_demo_autotrade_send_cycle_result.json produced by
  scripts/run_gold_multi_strategy_demo_autotrade_send_cycle.py.
- Locate the order_payloads.csv that the send cycle used.
- Extract MT5/send report metadata when available.
- Fall back to explicit synthetic ticket values when the report is no-send/dry-run/no-ticket.
- Build preview position_registry rows.
- Reconcile against a provided positions snapshot/mock CSV.
- Run registry-aware policy preview.
- Write one combined summary JSON/CSV.

Safety:
- No MetaTrader5 import.
- No mt5.order_check.
- No mt5.order_send.
- No real sender modification.
- No existing Mochipoyo ledger mutation.
- No trigger-state mutation.
- No production registry mutation by default.

This script does not run the guarded send cycle itself. It only reads a report that already exists.
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

SCHEMA_VERSION = "gold_multi_strategy_send_report_registry_preview_v1"

DEFAULT_SEND_REPORT_JSON = Path("data/research_results/gold_multi_strategy_demo_autotrade_send_cycle/latest_multi_strategy_demo_autotrade_send_cycle_result.json")
DEFAULT_POSITIONS_CSV = Path("data/research_results/gold_multi_strategy_position_policy_preflight/mock_positions_same_strategy_buy_c.csv")
DEFAULT_OUT_DIR = Path("data/research_results/gold_multi_strategy_send_report_registry_preview")
DEFAULT_ORDER_LEDGER_CSV = Path("data/research_results/gold_multi_strategy_mochipoyo_payload_bridge_dry_run/dry_run_order_ledger.csv")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Registry preview from existing guarded demo send-cycle report. No order_send/order_check.")
    p.add_argument("--send-report-json", type=Path, default=DEFAULT_SEND_REPORT_JSON)
    p.add_argument("--positions-csv", type=Path, default=DEFAULT_POSITIONS_CSV)
    p.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    p.add_argument("--order-ledger-csv", type=Path, default=DEFAULT_ORDER_LEDGER_CSV)
    p.add_argument("--symbol", default="GOLD#")
    p.add_argument("--max-orders", type=int, default=1)
    p.add_argument("--max-total-positions", type=int, default=5)
    p.add_argument("--max-lot-per-order", type=float, default=0.02)
    p.add_argument("--fallback-position-ticket-start", type=int, default=990001)
    p.add_argument("--fallback-order-ticket-start", type=int, default=880001)
    p.add_argument("--fallback-deal-ticket-start", type=int, default=770001)
    p.add_argument("--fallback-account-login", type=int, default=75539039)
    p.add_argument("--fallback-account-server", default="XMTrading-MT5 3")
    p.add_argument("--position-status", default="ACTIVE")
    p.add_argument("--python-exe", default=sys.executable)
    p.add_argument("--allow-registry-inconsistency", action="store_true")
    p.add_argument("--continue-on-step-error", action="store_true")
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


def path_exists(path: Path) -> bool:
    try:
        return Path(windows_long_path(path)).exists()
    except Exception:
        return path.exists()


def read_json(path: Path) -> dict[str, Any]:
    if not path_exists(path):
        return {}
    try:
        return json.loads(Path(windows_long_path(path)).read_text(encoding="utf-8"))
    except Exception as e:
        return {"_read_error": repr(e), "_path": str(path)}


def write_json(path: Path, obj: dict[str, Any]) -> None:
    Path(windows_long_path(path.parent)).mkdir(parents=True, exist_ok=True)
    Path(windows_long_path(path)).write_text(
        json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True, default=str),
        encoding="utf-8",
    )


def write_summary_csv(path: Path, summary: dict[str, Any]) -> None:
    row = {
        "cycle_time_utc": summary.get("cycle_time_utc", ""),
        "cycle_ok": summary.get("cycle_ok", False),
        "reason": summary.get("reason", ""),
        "send_report_json": summary.get("send_report_json", ""),
        "payload_csv": summary.get("payload_csv", ""),
        "payload_rows": summary.get("payload_rows", 0),
        "ticket_source": summary.get("send_metadata", {}).get("ticket_source", ""),
        "position_ticket_start": summary.get("send_metadata", {}).get("position_ticket_start", ""),
        "order_ticket_start": summary.get("send_metadata", {}).get("order_ticket_start", ""),
        "deal_ticket_start": summary.get("send_metadata", {}).get("deal_ticket_start", ""),
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
    Path(windows_long_path(path.parent)).mkdir(parents=True, exist_ok=True)
    pd.DataFrame([row]).to_csv(windows_long_path(path), index=False, encoding="utf-8-sig")


def read_csv_len(path: Path) -> int:
    if not path_exists(path):
        return 0
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
        "stdout_tail": proc.stdout[-8000:],
        "stderr_tail": proc.stderr[-8000:],
    }


def script_path(name: str) -> str:
    return str(Path("scripts") / name)


def as_int(value: Any, default: int) -> int:
    try:
        if value is None or value == "":
            return int(default)
        return int(float(value))
    except Exception:
        return int(default)


def as_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    text = str(value)
    return text if text else default


def extract_payload_csv(send_report: dict[str, Any]) -> Path:
    payload_out_dir = as_str(send_report.get("payload_out_dir"))
    if payload_out_dir:
        return Path(payload_out_dir) / "order_payloads.csv"
    bridge = send_report.get("payload_bridge_result", {})
    if isinstance(bridge, dict):
        for key in ["output_csv", "order_payloads_csv", "payload_csv"]:
            if bridge.get(key):
                return Path(str(bridge[key]))
    return Path("data/research_results/gold_multi_strategy_mochipoyo_payload_bridge_send/order_payloads.csv")


def first_result_row(mt5_report: dict[str, Any]) -> dict[str, Any]:
    rows = mt5_report.get("results")
    if isinstance(rows, list) and rows:
        first = rows[0]
        if isinstance(first, dict):
            return first
    rows = mt5_report.get("records")
    if isinstance(rows, list) and rows:
        first = rows[0]
        if isinstance(first, dict):
            return first
    return {}


def extract_account(send_report: dict[str, Any], args: argparse.Namespace) -> tuple[int, str]:
    mt5_report = send_report.get("mt5_report", {})
    if not isinstance(mt5_report, dict):
        mt5_report = {}
    account_info = mt5_report.get("account_info", {})
    if not isinstance(account_info, dict):
        account_info = {}
    key_metrics = send_report.get("key_metrics", {})
    if not isinstance(key_metrics, dict):
        key_metrics = {}
    login = as_int(account_info.get("login", key_metrics.get("mt5_account_login")), args.fallback_account_login)
    server = as_str(account_info.get("server", key_metrics.get("mt5_account_server")), args.fallback_account_server)
    return login, server


def extract_tickets(send_report: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    mt5_report = send_report.get("mt5_report", {})
    if not isinstance(mt5_report, dict):
        mt5_report = {}
    row = first_result_row(mt5_report)
    ticket_keys_position = ["position_ticket", "position", "position_id", "ticket"]
    ticket_keys_order = ["order_ticket", "order", "order_id"]
    ticket_keys_deal = ["deal_ticket", "deal", "deal_id"]

    def pick(keys: list[str], fallback: int) -> tuple[int, str]:
        for key in keys:
            if key in row and row.get(key) not in [None, "", 0, "0"]:
                return as_int(row.get(key), fallback), f"mt5_report.results[0].{key}"
            if key in mt5_report and mt5_report.get(key) not in [None, "", 0, "0"]:
                return as_int(mt5_report.get(key), fallback), f"mt5_report.{key}"
        return int(fallback), "fallback"

    position_ticket, position_source = pick(ticket_keys_position, args.fallback_position_ticket_start)
    order_ticket, order_source = pick(ticket_keys_order, args.fallback_order_ticket_start)
    deal_ticket, deal_source = pick(ticket_keys_deal, args.fallback_deal_ticket_start)
    used_fallback = any(src == "fallback" for src in [position_source, order_source, deal_source])
    return {
        "position_ticket_start": position_ticket,
        "order_ticket_start": order_ticket,
        "deal_ticket_start": deal_ticket,
        "position_ticket_source": position_source,
        "order_ticket_source": order_source,
        "deal_ticket_source": deal_source,
        "ticket_source": "mt5_report" if not used_fallback else "fallback_or_partial",
        "used_fallback_ticket": bool(used_fallback),
    }


def safe_send_metrics(send_report: dict[str, Any]) -> dict[str, Any]:
    key = send_report.get("key_metrics", {})
    if not isinstance(key, dict):
        key = {}
    mt5 = send_report.get("mt5_report", {})
    if not isinstance(mt5, dict):
        mt5 = {}
    return {
        "source_cycle_ok": bool(send_report.get("cycle_ok", False)),
        "source_send_enabled": bool(send_report.get("send_enabled", False)),
        "source_send_requested": bool(send_report.get("send_requested", False)),
        "source_safe_send_guard_ok": bool(send_report.get("safe_send_guard_ok", False)),
        "source_payload_rows_out": as_int(key.get("payload_rows_out"), 0),
        "source_mt5_order_send_called_count": as_int(key.get("mt5_order_send_called_count", mt5.get("order_send_called_count")), 0),
        "source_mt5_sent_rows": as_int(key.get("mt5_sent_rows", mt5.get("sent_rows")), 0),
        "source_mt5_blocked_position_policy_rows": as_int(key.get("mt5_blocked_position_policy_rows", mt5.get("blocked_position_policy_rows")), 0),
        "source_mt5_status_summary": as_str(key.get("mt5_status_summary"), ""),
    }


def finish(summary: dict[str, Any], summary_json: Path, summary_csv: Path, reason: str, code: int) -> int:
    summary["cycle_ok"] = code == 0
    summary["reason"] = reason
    write_json(summary_json, summary)
    write_summary_csv(summary_csv, summary)
    print("run_gold_multi_strategy_send_report_registry_preview")
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True, default=str))
    return code


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


def main() -> int:
    args = parse_args()
    Path(windows_long_path(args.out_dir)).mkdir(parents=True, exist_ok=True)
    now = utc_now_text()
    summary_json = args.out_dir / "send_report_registry_preview_summary.json"
    summary_csv = args.out_dir / "send_report_registry_preview_summary.csv"
    registry_preview_csv = args.out_dir / "position_registry_from_send_report_preview.csv"
    registry_preview_json = args.out_dir / "position_registry_from_send_report_preview.json"
    reconcile_csv = args.out_dir / "position_registry_reconcile_from_send_report.csv"
    reconcile_json = args.out_dir / "position_registry_reconcile_from_send_report.json"
    positions_snapshot_csv = args.out_dir / "position_registry_reconcile_positions_snapshot_from_send_report.csv"
    policy_preview_csv = args.out_dir / "registry_policy_preview_from_send_report.csv"
    policy_preview_json = args.out_dir / "registry_policy_preview_from_send_report.json"
    policy_reconcile_csv = args.out_dir / "registry_policy_preview_reconcile_from_send_report.csv"

    send_report_exists = path_exists(args.send_report_json)
    send_report = read_json(args.send_report_json)
    payload_csv = extract_payload_csv(send_report)
    payload_rows = read_csv_len(payload_csv)
    login, server = extract_account(send_report, args)
    tickets = extract_tickets(send_report, args)
    source_metrics = safe_send_metrics(send_report)

    summary: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "cycle_time_utc": now,
        "cycle_ok": False,
        "reason": "STARTED",
        "send_report_json": str(args.send_report_json),
        "send_report_exists": bool(send_report_exists),
        "payload_csv": str(payload_csv),
        "payload_rows": int(payload_rows),
        "positions_csv": str(args.positions_csv),
        "out_dir": str(args.out_dir),
        "source_send_cycle_metrics": source_metrics,
        "send_metadata": {
            "account_login": login,
            "account_server": server,
            **tickets,
        },
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
        "steps": [],
    }

    if not send_report_exists:
        return finish(summary, summary_json, summary_csv, "SEND_REPORT_NOT_FOUND", 2)
    if payload_rows <= 0:
        return finish(summary, summary_json, summary_csv, "NO_PAYLOAD_ROWS_IN_SEND_REPORT_PAYLOAD_CSV", 0)

    build_cmd = [
        args.python_exe,
        script_path("build_gold_multi_strategy_position_registry_from_payload_preview.py"),
        "--input-csv", str(payload_csv),
        "--out-dir", str(args.out_dir),
        "--output-csv", str(registry_preview_csv),
        "--output-json", str(registry_preview_json),
        "--max-rows", str(args.max_orders),
        "--account-login", str(login),
        "--account-server", str(server),
        "--position-ticket-start", str(tickets["position_ticket_start"]),
        "--order-ticket-start", str(tickets["order_ticket_start"]),
        "--deal-ticket-start", str(tickets["deal_ticket_start"]),
        "--position-status", str(args.position_status),
        "--sender-report-json", str(args.send_report_json),
        "--notes", "generated from guarded demo send-cycle report; no order_send in this wrapper",
    ]
    step = run_step("build_registry_from_send_report_payload", build_cmd)
    summary["steps"].append(step)
    if not step["ok"] and not args.continue_on_step_error:
        return finish(summary, summary_json, summary_csv, "BUILD_REGISTRY_FROM_SEND_REPORT_FAILED", 10)

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
    step = run_step("registry_reconcile_from_send_report", reconcile_cmd)
    summary["steps"].append(step)
    if not step["ok"] and not args.continue_on_step_error:
        return finish(summary, summary_json, summary_csv, "RECONCILE_FROM_SEND_REPORT_FAILED", 11)

    policy_cmd = [
        args.python_exe,
        script_path("run_gold_multi_strategy_registry_policy_preview.py"),
        "--input-csv", str(payload_csv),
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
    step = run_step("registry_policy_preview_from_send_report", policy_cmd)
    summary["steps"].append(step)
    if not step["ok"] and not args.continue_on_step_error:
        return finish(summary, summary_json, summary_csv, "POLICY_PREVIEW_FROM_SEND_REPORT_FAILED", 12)

    registry_builder = read_json(registry_preview_json)
    reconcile = read_json(reconcile_json)
    policy_preview = read_json(policy_preview_json)
    cycle_ok = all(bool(step.get("ok")) for step in summary["steps"]) and bool(policy_preview.get("preview_ok", False))
    summary.update({
        "cycle_ok": bool(cycle_ok),
        "reason": "SEND_REPORT_REGISTRY_PREVIEW_EVALUATED" if cycle_ok else "SEND_REPORT_REGISTRY_PREVIEW_COMPLETED_WITH_ERRORS",
        "registry_builder": registry_builder,
        "reconcile": reconcile,
        "policy_preview": policy_preview,
    })
    write_json(summary_json, summary)
    write_summary_csv(summary_csv, summary)

    print("run_gold_multi_strategy_send_report_registry_preview")
    print(json.dumps({k: v for k, v in summary.items() if k != "steps"}, ensure_ascii=False, indent=2, sort_keys=True, default=str))
    print_step_table(summary["steps"])
    print(f"summary_json: {summary_json}")
    print(f"summary_csv: {summary_csv}")
    print("done")
    return 0 if cycle_ok else 1


def print_step_table(steps: list[dict[str, Any]]) -> None:
    if not steps:
        print("[INFO] no child steps executed")
        return
    df = pd.DataFrame([{ "name": s.get("name"), "ok": s.get("ok"), "returncode": s.get("returncode") } for s in steps])
    print(df.to_string(index=False))


if __name__ == "__main__":
    raise SystemExit(main())
