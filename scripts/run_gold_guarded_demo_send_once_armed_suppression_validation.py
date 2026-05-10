#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""Validate GOLD guarded demo send-once armed runner suppression cases.

This validation intentionally does NOT run the armed --allow-demo-send --send case.

Cases:
1. no flags
2. --send only
3. --allow-demo-send only

Expected for every case:
- cycle_ok=true
- send_flag_passed_to_sender=false
- sender_order_send_called_count=0
- sender_sent_rows=0
- production registry not mutated

Purpose:
- Prove the armed GOLD runner remains safe unless both explicit flags are present.
- Keep the real send case for a separate, explicit user-approved action after
  market conditions and open positions are reviewed.
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

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT_DIR = Path("data/r/gold_guarded_demo_send_once_armed_suppression_validation")
SUMMARY_FILENAME = "latest_gold_guarded_demo_send_once_armed_suppression_validation_result.json"


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
    except Exception as exc:
        return {"_read_error": str(exc), "_path": str(path)}


def utc_now_text() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")


def as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


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


def run_case(case_name: str, extra_args: list[str], out_dir: Path) -> dict[str, Any]:
    case_out = out_dir / case_name
    mkdir_path(case_out)
    cmd = [
        sys.executable,
        str(REPO_ROOT / "scripts" / "run_gold_multi_strategy_guarded_demo_send_once_armed.py"),
        "--out-dir",
        str(case_out),
    ] + extra_args
    completed = subprocess.run(
        cmd,
        cwd=str(REPO_ROOT),
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
    )
    stdout_log = out_dir / "command_logs" / f"{case_name}_stdout.txt"
    stderr_log = out_dir / "command_logs" / f"{case_name}_stderr.txt"
    write_text(stdout_log, completed.stdout or "")
    write_text(stderr_log, completed.stderr or "")
    summary_path = case_out / "latest_gold_multi_strategy_guarded_demo_send_once_armed_result.json"
    summary = read_json_or_empty(summary_path)
    safety = summary.get("safety", {}) if isinstance(summary.get("safety"), dict) else {}
    validation_ok = bool(
        completed.returncode == 0
        and as_bool(summary.get("cycle_ok"), False)
        and not as_bool(summary.get("send_flag_passed_to_sender"), True)
        and as_int(summary.get("sender_order_send_called_count"), as_int(safety.get("order_send_called_count"), 999)) == 0
        and as_int(summary.get("sender_sent_rows"), as_int(safety.get("sent_rows"), 999)) == 0
        and not as_bool(safety.get("production_registry_mutated"), True)
    )
    return {
        "case_name": case_name,
        "extra_args": extra_args,
        "returncode": int(completed.returncode),
        "validation_ok": validation_ok,
        "cycle_ok": as_bool(summary.get("cycle_ok"), False),
        "reason": summary.get("reason", ""),
        "mode": summary.get("mode", ""),
        "send_requested": as_bool(summary.get("send_requested"), False),
        "allow_demo_send": as_bool(summary.get("allow_demo_send"), False),
        "send_flag_passed_to_sender": as_bool(summary.get("send_flag_passed_to_sender"), False),
        "send_suppressed_reason": summary.get("send_suppressed_reason", ""),
        "sender_invoked": as_bool(summary.get("sender_invoked"), False),
        "sender_order_send_called_count": as_int(summary.get("sender_order_send_called_count"), as_int(safety.get("order_send_called_count"), 0)),
        "sender_sent_rows": as_int(summary.get("sender_sent_rows"), as_int(safety.get("sent_rows"), 0)),
        "sender_dry_run_check_ok_rows": as_int(summary.get("sender_dry_run_check_ok_rows"), 0),
        "sender_error_rows": as_int(summary.get("sender_error_rows"), 0),
        "production_registry_mutated": as_bool(safety.get("production_registry_mutated"), False),
        "summary_json": str(summary_path),
        "stdout_log": str(stdout_log),
        "stderr_log": str(stderr_log),
    }


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Validate GOLD guarded armed suppression cases without executing send.")
    p.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    mkdir_path(args.out_dir)
    cases = [
        run_case("no_flags", [], args.out_dir),
        run_case("send_only", ["--send"], args.out_dir),
        run_case("allow_only", ["--allow-demo-send"], args.out_dir),
    ]
    failed = [c for c in cases if not c["validation_ok"]]
    validation_ok = not failed
    summary = {
        "schema_version": "gold_guarded_demo_send_once_armed_suppression_validation_v1",
        "validation_time_utc": utc_now_text(),
        "validation_ok": validation_ok,
        "reason": "GOLD_GUARDED_DEMO_SEND_ONCE_ARMED_SUPPRESSION_VALIDATION_PASS" if validation_ok else "GOLD_GUARDED_DEMO_SEND_ONCE_ARMED_SUPPRESSION_VALIDATION_FAILED",
        "cases_total": len(cases),
        "cases_failed": len(failed),
        "cases": cases,
        "safety": {
            "allow_and_send_case_executed": False,
            "order_send_called_count": sum(as_int(c.get("sender_order_send_called_count"), 0) for c in cases),
            "sent_rows": sum(as_int(c.get("sender_sent_rows"), 0) for c in cases),
            "production_registry_mutated": False,
        },
        "outputs": {
            "summary_json": str(args.out_dir / SUMMARY_FILENAME),
        },
    }
    write_json(args.out_dir / SUMMARY_FILENAME, summary)
    print("=" * 80, flush=True)
    print("GOLD guarded demo send-once armed suppression validation", flush=True)
    print(json.dumps({
        "validation_ok": validation_ok,
        "reason": summary["reason"],
        "cases_total": len(cases),
        "cases_failed": len(failed),
        "order_send_called_count": summary["safety"]["order_send_called_count"],
        "sent_rows": summary["safety"]["sent_rows"],
        "allow_and_send_case_executed": False,
        "summary_json": str(args.out_dir / SUMMARY_FILENAME),
        "cases": cases,
    }, ensure_ascii=False, indent=2, sort_keys=True, default=str), flush=True)
    print("=" * 80, flush=True)
    return 0 if validation_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
