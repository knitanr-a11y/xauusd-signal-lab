#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Run sender dry-run, then build sender-adjacent registry preview.

This is a one-command wrapper around the already validated pieces:

1. scripts/send_mt5_order_from_payload.py
2. scripts/build_gold_multi_strategy_sender_registry_preview_from_report.py

Safety:
- This wrapper never passes --send to send_mt5_order_from_payload.py.
- No production position_registry.csv mutation.
- No order ledger mutation by helper scripts.
- No trigger-state mutation.
- Existing sender script remains unchanged.

Purpose:
- Provide a disabled-by-default-like registry preview flow without directly modifying
  the real sender yet.

Important behavior:
- send_mt5_order_from_payload.py returns non-zero when rows are blocked by local
  validation or policy, even though it still writes a valid report/results pair.
- This wrapper should still run the registry-preview step in that case so the
  expected safe result can be observed: NO_ELIGIBLE_SENDER_ROWS.
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

SCHEMA_VERSION = "gold_multi_strategy_sender_dry_run_registry_preview_cycle_v1"

POSITION_POLICIES = ["block_any", "allow_same_direction", "allow_any_until_max"]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run sender dry-run then registry preview builder. Never calls order_send.")
    p.add_argument("--input-csv", required=True)
    p.add_argument("--order-ledger-csv", required=True)
    p.add_argument("--out-dir", required=True)
    p.add_argument("--symbol", default=None)
    p.add_argument("--max-orders", type=int, default=1)
    p.add_argument("--select-symbol", action="store_true")
    p.add_argument("--expected-login", type=int, default=None)
    p.add_argument("--require-demo-account", action="store_true")
    p.add_argument("--allow-live-account", action="store_true")
    p.add_argument("--position-policy", choices=POSITION_POLICIES, default="block_any")
    p.add_argument("--max-symbol-positions", type=int, default=1)
    p.add_argument("--max-symbol-lot", type=float, default=0.01)
    p.add_argument("--deviation", type=int, default=50)
    p.add_argument("--terminal-path", default=None)
    p.add_argument("--portable", action="store_true")
    p.add_argument("--sleep-seconds", type=float, default=0.5)
    p.add_argument("--registry-preview-position-status", default="ACTIVE")
    p.add_argument("--registry-preview-position-ticket-start", type=int, default=990001)
    p.add_argument("--registry-preview-order-ticket-start", type=int, default=880001)
    p.add_argument("--registry-preview-deal-ticket-start", type=int, default=770001)
    p.add_argument("--python-exe", default=sys.executable)
    p.add_argument(
        "--strict-sender-returncode",
        action="store_true",
        help="If set, stop when sender dry-run exits non-zero. Default continues when sender report/results exist.",
    )
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


def path_exists(path: Path) -> bool:
    try:
        return Path(windows_long_path(path)).exists()
    except Exception:
        return path.exists()


def utc_now_text() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")


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


def build_sender_cmd(args: argparse.Namespace, sender_out_dir: Path) -> list[str]:
    cmd = [
        args.python_exe,
        script_path("send_mt5_order_from_payload.py"),
        "--input-csv", str(args.input_csv),
        "--order-ledger-csv", str(args.order_ledger_csv),
        "--out-dir", str(sender_out_dir),
        "--max-orders", str(args.max_orders),
        "--position-policy", str(args.position_policy),
        "--max-symbol-positions", str(args.max_symbol_positions),
        "--max-symbol-lot", str(args.max_symbol_lot),
        "--deviation", str(args.deviation),
        "--sleep-seconds", str(args.sleep_seconds),
    ]
    if args.symbol:
        cmd += ["--symbol", str(args.symbol)]
    if args.select_symbol:
        cmd.append("--select-symbol")
    if args.expected_login is not None:
        cmd += ["--expected-login", str(args.expected_login)]
    if args.require_demo_account:
        cmd.append("--require-demo-account")
    if args.allow_live_account:
        cmd.append("--allow-live-account")
    if args.terminal_path:
        cmd += ["--terminal-path", str(args.terminal_path)]
    if args.portable:
        cmd.append("--portable")
    # Intentionally never append --send.
    return cmd


def build_registry_preview_cmd(args: argparse.Namespace, sender_out_dir: Path, registry_out_dir: Path) -> list[str]:
    return [
        args.python_exe,
        script_path("build_gold_multi_strategy_sender_registry_preview_from_report.py"),
        "--sender-out-dir", str(sender_out_dir),
        "--out-dir", str(registry_out_dir),
        "--position-ticket-start", str(args.registry_preview_position_ticket_start),
        "--order-ticket-start", str(args.registry_preview_order_ticket_start),
        "--deal-ticket-start", str(args.registry_preview_deal_ticket_start),
        "--position-status", str(args.registry_preview_position_status),
    ]


def sender_report_is_usable(sender_report_json: Path, sender_results_csv: Path) -> bool:
    return path_exists(sender_report_json) and path_exists(sender_results_csv)


def main() -> int:
    args = parse_args()
    out_dir = Path(args.out_dir)
    Path(windows_long_path(out_dir)).mkdir(parents=True, exist_ok=True)
    sender_out_dir = out_dir / "mt5_order_check_dry_run"
    registry_out_dir = out_dir / "sender_registry_preview"
    summary_json = out_dir / "sender_dry_run_registry_preview_cycle_summary.json"

    summary: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "cycle_time_utc": utc_now_text(),
        "cycle_ok": False,
        "reason": "STARTED",
        "input_csv": str(args.input_csv),
        "order_ledger_csv": str(args.order_ledger_csv),
        "out_dir": str(out_dir),
        "sender_out_dir": str(sender_out_dir),
        "registry_preview_out_dir": str(registry_out_dir),
        "send_requested": False,
        "strict_sender_returncode": bool(args.strict_sender_returncode),
        "safety": {
            "wrapper_passed_send_flag": False,
            "production_registry_mutated": False,
            "trigger_state_mutated": False,
            "existing_sender_modified": False,
        },
        "steps": [],
    }

    sender_cmd = build_sender_cmd(args, sender_out_dir)
    sender_step = run_step("sender_dry_run", sender_cmd)
    summary["steps"].append(sender_step)
    sender_report_json = sender_out_dir / "mt5_order_send_report.json"
    sender_results_csv = sender_out_dir / "mt5_order_send_results.csv"
    sender_report = read_json(sender_report_json)
    sender_outputs_exist = sender_report_is_usable(sender_report_json, sender_results_csv)
    summary["sender_report_json"] = str(sender_report_json)
    summary["sender_results_csv"] = str(sender_results_csv)
    summary["sender_outputs_exist"] = bool(sender_outputs_exist)
    summary["sender_metrics"] = {
        "rows_in": sender_report.get("rows_in", ""),
        "rows_out": sender_report.get("rows_out", ""),
        "dry_run_check_ok_rows": sender_report.get("dry_run_check_ok_rows", ""),
        "sent_rows": sender_report.get("sent_rows", ""),
        "blocked_position_policy_rows": sender_report.get("blocked_position_policy_rows", ""),
        "error_rows": sender_report.get("error_rows", ""),
        "order_send_called_count": sender_report.get("order_send_called_count", ""),
    }

    if (not sender_step["ok"]) and args.strict_sender_returncode:
        summary["reason"] = "SENDER_DRY_RUN_FAILED_STRICT"
        write_json(summary_json, summary)
        print("run_gold_multi_strategy_sender_dry_run_registry_preview_cycle")
        print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True, default=str))
        return 10

    if (not sender_step["ok"]) and (not sender_outputs_exist):
        summary["reason"] = "SENDER_DRY_RUN_FAILED_NO_REPORT"
        write_json(summary_json, summary)
        print("run_gold_multi_strategy_sender_dry_run_registry_preview_cycle")
        print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True, default=str))
        return 11

    preview_cmd = build_registry_preview_cmd(args, sender_out_dir, registry_out_dir)
    preview_step = run_step("sender_registry_preview_from_report", preview_cmd)
    summary["steps"].append(preview_step)
    preview_json = registry_out_dir / "sender_registry_preview.json"
    preview_csv = registry_out_dir / "sender_registry_preview.csv"
    preview_report = read_json(preview_json)
    summary["registry_preview_json"] = str(preview_json)
    summary["registry_preview_csv"] = str(preview_csv)
    summary["registry_preview_rows"] = preview_report.get("registry_preview_rows", read_csv_len(preview_csv))
    summary["registry_preview_reason"] = preview_report.get("reason", "")
    summary["registry_preview_ok"] = bool(preview_report.get("preview_ok", False))

    # A non-zero sender returncode is acceptable when the sender produced report/results
    # and preview builder confirms a valid safe outcome such as NO_ELIGIBLE_SENDER_ROWS.
    cycle_ok = bool(preview_step["ok"] and summary["registry_preview_ok"] and sender_outputs_exist)
    summary["cycle_ok"] = cycle_ok
    if cycle_ok and not sender_step["ok"]:
        summary["reason"] = "SENDER_DRY_RUN_BLOCKED_BUT_REGISTRY_PREVIEW_EVALUATED"
    elif cycle_ok:
        summary["reason"] = "SENDER_DRY_RUN_REGISTRY_PREVIEW_EVALUATED"
    else:
        summary["reason"] = "SENDER_DRY_RUN_REGISTRY_PREVIEW_COMPLETED_WITH_ERRORS"
    write_json(summary_json, summary)

    print("run_gold_multi_strategy_sender_dry_run_registry_preview_cycle")
    print(json.dumps({k: v for k, v in summary.items() if k != "steps"}, ensure_ascii=False, indent=2, sort_keys=True, default=str))
    if summary["steps"]:
        df = pd.DataFrame([{"name": s["name"], "ok": s["ok"], "returncode": s["returncode"]} for s in summary["steps"]])
        print(df.to_string(index=False))
    print(f"summary_json: {summary_json}")
    print("done")
    return 0 if cycle_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
