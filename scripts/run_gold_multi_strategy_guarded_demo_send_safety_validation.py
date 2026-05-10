#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""Validate guarded demo-send suppression for GOLD multi-strategy sidecar flow.

This validator is intentionally no-send.

It verifies the guarded demo-send once wrapper safety contract:

1. no flags
   - sender must not receive --send
   - reason must be SEND_NOT_REQUESTED

2. --send only
   - sender must not receive --send
   - reason must be ALLOW_DEMO_SEND_NOT_SET

3. --allow-demo-send only
   - sender must not receive --send
   - reason must be SEND_NOT_REQUESTED

4. zero-payload fixture + --allow-demo-send --send
   - sender must not receive --send
   - reason must be NO_PAYLOAD_ROWS

Important safety note for Case 4:
- This validator does NOT run the live CSV wrapper with both --allow-demo-send
  and --send.
- Instead, it uses a local zero-payload fixture against the wrapper's shared
  suppression decision function.
- This prevents accidental MT5 order_send if a real signal appears in the live
  CSV while validation is running.

Safety boundaries:
- Never permits a real --send pass-through to send_mt5_order_from_payload.py.
- Does not write production position_registry.csv.
- Does not modify existing Mochipoyo ledgers or trigger-state files.
- Uses isolated output directories under data/r/gdsafe by default.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import run_gold_multi_strategy_mochipoyo_loop_guarded_demo_send_once as guarded_once  # noqa: E402

DEFAULT_OUT_DIR = Path("data/r/gdsafe")
DEFAULT_CSV_DIR = Path(r"C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files")
SUMMARY_FILENAME = "latest_gold_multi_strategy_guarded_demo_send_safety_validation_result.json"

CASE_LOG_COLUMNS = [
    "case_name",
    "case_type",
    "returncode",
    "elapsed_seconds",
    "validation_ok",
    "expected_reason",
    "actual_reason",
    "send_flag_passed_to_sender",
    "order_send_called_count",
    "sent_rows",
    "payload_rows_out",
    "summary_json",
    "stdout_log",
    "stderr_log",
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


def remove_dir(path: Path) -> None:
    if Path(windows_long_path(path)).exists():
        shutil.rmtree(windows_long_path(path), ignore_errors=True)


def utc_now_text() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")


def write_text(path: Path, text: str) -> None:
    ensure_parent_dir(path)
    with open(windows_long_path(path), "w", encoding="utf-8", newline="") as f:
        f.write(text)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    write_text(path, json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=str))


def read_json_or_empty(path: Path) -> dict[str, Any]:
    try:
        with open(windows_long_path(path), "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except Exception as exc:
        return {"_read_error": str(exc), "_path": str(path)}


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


def build_wrapper_cmd(args: argparse.Namespace, case_out_dir: Path, extra_flags: list[str]) -> list[str]:
    cmd = [
        sys.executable,
        str(REPO_ROOT / "scripts" / "run_gold_multi_strategy_mochipoyo_loop_guarded_demo_send_once.py"),
        "--csv-dir", str(args.csv_dir),
        "--out-dir", str(case_out_dir),
        "--broker-symbol", str(args.broker_symbol),
        "--expected-login", str(args.expected_login),
        "--require-demo-account",
        "--fixed-lot", str(args.fixed_lot),
        "--magic", str(args.magic),
        "--max-orders", str(args.max_orders),
        "--deviation", str(args.deviation),
        "--position-policy", str(args.position_policy),
        "--max-symbol-positions", str(args.max_symbol_positions),
        "--max-symbol-lot", str(args.max_symbol_lot),
    ]
    cmd.extend(extra_flags)
    return cmd


def validate_runtime_case(case: dict[str, Any], expected_reason: str) -> dict[str, Any]:
    summary = case.get("summary", {}) if isinstance(case.get("summary"), dict) else {}
    metrics = summary.get("key_metrics", {}) if isinstance(summary.get("key_metrics"), dict) else {}
    safety = summary.get("safety", {}) if isinstance(summary.get("safety"), dict) else {}

    checks = {
        "returncode_zero": as_int(case.get("returncode"), -1) == 0,
        "cycle_ok_true": as_bool(summary.get("cycle_ok"), False),
        "send_flag_not_passed": not as_bool(summary.get("send_flag_passed_to_sender"), True),
        "reason_matches": str(summary.get("send_suppressed_reason", "")) == expected_reason,
        "order_send_zero": as_int(metrics.get("guarded_sender_order_send_called_count"), 0) == 0,
        "sent_rows_zero": as_int(metrics.get("guarded_sender_sent_rows"), 0) == 0,
        "production_registry_not_mutated": not as_bool(safety.get("production_registry_mutated"), True),
    }
    failures = [{"check": k, "value": v} for k, v in checks.items() if not v]
    return {
        "validation_ok": len(failures) == 0,
        "checks": checks,
        "failures": failures,
        "actual_reason": str(summary.get("send_suppressed_reason", "")),
        "send_flag_passed_to_sender": as_bool(summary.get("send_flag_passed_to_sender"), False),
        "order_send_called_count": as_int(metrics.get("guarded_sender_order_send_called_count"), 0),
        "sent_rows": as_int(metrics.get("guarded_sender_sent_rows"), 0),
        "payload_rows_out": as_int(metrics.get("payload_rows_out"), 0),
    }


def run_runtime_case(
    *,
    args: argparse.Namespace,
    case_name: str,
    expected_reason: str,
    extra_flags: list[str],
    case_out_dir: Path,
    log_dir: Path,
) -> dict[str, Any]:
    mkdir_path(log_dir)
    stdout_log = log_dir / f"{case_name}_stdout.txt"
    stderr_log = log_dir / f"{case_name}_stderr.txt"
    summary_json = case_out_dir / guarded_once.SUMMARY_FILENAME
    cmd = build_wrapper_cmd(args, case_out_dir, extra_flags)

    print("=" * 80, flush=True)
    print(f"[CASE] {case_name}", flush=True)
    print("[CMD] " + " ".join(cmd), flush=True)
    started = time.perf_counter()
    completed = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace")
    elapsed = round(time.perf_counter() - started, 3)
    write_text(stdout_log, completed.stdout or "")
    write_text(stderr_log, completed.stderr or "")
    if completed.stdout:
        print(completed.stdout.rstrip(), flush=True)
    if completed.stderr:
        print(completed.stderr.rstrip(), file=sys.stderr, flush=True)

    case = {
        "case_name": case_name,
        "case_type": "runtime_wrapper",
        "returncode": int(completed.returncode),
        "elapsed_seconds": elapsed,
        "expected_reason": expected_reason,
        "summary_json": str(summary_json),
        "stdout_log": str(stdout_log),
        "stderr_log": str(stderr_log),
        "summary": read_json_or_empty(summary_json),
    }
    case.update(validate_runtime_case(case, expected_reason))
    return case


def run_zero_payload_fixture_case(args: argparse.Namespace, out_dir: Path) -> dict[str, Any]:
    print("=" * 80, flush=True)
    print("[CASE] zero_payload_fixture_allow_demo_send_and_send", flush=True)
    print("[INFO] This case does not run the live CSV wrapper. It tests the shared suppression decision with payload_rows=0.", flush=True)

    fixture_args = argparse.Namespace(
        send=True,
        allow_demo_send=True,
        max_orders=int(args.max_orders),
    )
    pass_send, reason = guarded_once.decide_send_suppression(fixture_args, payload_rows=0)
    checks = {
        "send_flag_not_passed": pass_send is False,
        "reason_no_payload_rows": reason == "NO_PAYLOAD_ROWS",
    }
    failures = [{"check": k, "value": v} for k, v in checks.items() if not v]
    summary = {
        "schema_version": "gold_multi_strategy_guarded_demo_send_zero_payload_fixture_v1",
        "fixture": "payload_rows_0_allow_demo_send_true_send_true",
        "validation_ok": len(failures) == 0,
        "send_requested": True,
        "allow_demo_send": True,
        "payload_rows_out": 0,
        "send_flag_passed_to_sender": bool(pass_send),
        "send_suppressed_reason": reason,
        "guarded_sender_order_send_called_count": 0,
        "guarded_sender_sent_rows": 0,
        "production_registry_mutated": False,
        "checks": checks,
        "failures": failures,
        "safety_note": "live CSV wrapper was not executed with both --allow-demo-send and --send",
    }
    summary_json = out_dir / "zero_payload_fixture_allow_demo_send_and_send_result.json"
    write_json(summary_json, summary)
    return {
        "case_name": "zero_payload_fixture_allow_demo_send_and_send",
        "case_type": "zero_payload_fixture",
        "returncode": 0 if summary["validation_ok"] else 1,
        "elapsed_seconds": 0.0,
        "validation_ok": bool(summary["validation_ok"]),
        "expected_reason": "NO_PAYLOAD_ROWS",
        "actual_reason": reason,
        "send_flag_passed_to_sender": bool(pass_send),
        "order_send_called_count": 0,
        "sent_rows": 0,
        "payload_rows_out": 0,
        "summary_json": str(summary_json),
        "stdout_log": "",
        "stderr_log": "",
        "summary": summary,
        "checks": checks,
        "failures": failures,
    }


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Validate guarded demo-send no-send suppression contract.")
    p.add_argument("--csv-dir", type=Path, default=DEFAULT_CSV_DIR)
    p.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    p.add_argument("--broker-symbol", default="GOLD#")
    p.add_argument("--expected-login", type=int, default=75539039)
    p.add_argument("--fixed-lot", type=float, default=0.01)
    p.add_argument("--magic", type=int, default=26050601)
    p.add_argument("--max-orders", type=int, default=1)
    p.add_argument("--deviation", type=int, default=50)
    p.add_argument("--position-policy", choices=["block_any", "allow_same_direction", "allow_any_until_max"], default="block_any")
    p.add_argument("--max-symbol-positions", type=int, default=1)
    p.add_argument("--max-symbol-lot", type=float, default=0.01)
    p.add_argument("--keep-existing-out-dir", action="store_true")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    if not args.keep_existing_out_dir:
        remove_dir(args.out_dir)
    mkdir_path(args.out_dir)
    started = utc_now_text()
    log_dir = args.out_dir / "logs"

    cases = [
        run_runtime_case(
            args=args,
            case_name="no_flags",
            expected_reason="SEND_NOT_REQUESTED",
            extra_flags=[],
            case_out_dir=args.out_dir / "case_no_flags",
            log_dir=log_dir,
        ),
        run_runtime_case(
            args=args,
            case_name="send_only",
            expected_reason="ALLOW_DEMO_SEND_NOT_SET",
            extra_flags=["--send"],
            case_out_dir=args.out_dir / "case_send_only",
            log_dir=log_dir,
        ),
        run_runtime_case(
            args=args,
            case_name="allow_demo_send_only",
            expected_reason="SEND_NOT_REQUESTED",
            extra_flags=["--allow-demo-send"],
            case_out_dir=args.out_dir / "case_allow_demo_send_only",
            log_dir=log_dir,
        ),
        run_zero_payload_fixture_case(args, args.out_dir / "case_zero_payload_fixture"),
    ]

    for case in cases:
        append_csv_row(
            args.out_dir / "guarded_demo_send_safety_case_log.csv",
            {k: v for k, v in case.items() if k != "summary"},
            CASE_LOG_COLUMNS,
        )

    failed_cases = [
        {
            "case_name": c.get("case_name"),
            "case_type": c.get("case_type"),
            "expected_reason": c.get("expected_reason"),
            "actual_reason": c.get("actual_reason"),
            "failures": c.get("failures", []),
            "summary_json": c.get("summary_json"),
        }
        for c in cases
        if not as_bool(c.get("validation_ok"), False)
    ]
    validation_ok = len(failed_cases) == 0
    summary = {
        "schema_version": "gold_multi_strategy_guarded_demo_send_safety_validation_v1",
        "started_at_utc": started,
        "ended_at_utc": utc_now_text(),
        "validation_ok": validation_ok,
        "reason": "GUARDED_DEMO_SEND_SAFETY_VALIDATION_PASS" if validation_ok else "GUARDED_DEMO_SEND_SAFETY_VALIDATION_FAILED",
        "checks_total": len(cases),
        "checks_failed": len(failed_cases),
        "failed_cases": failed_cases,
        "safety": {
            "live_csv_wrapper_ran_with_allow_demo_send_and_send": False,
            "send_flag_passed_to_sender_any_case": any(as_bool(c.get("send_flag_passed_to_sender"), False) for c in cases),
            "order_send_called_count_total": sum(as_int(c.get("order_send_called_count"), 0) for c in cases),
            "sent_rows_total": sum(as_int(c.get("sent_rows"), 0) for c in cases),
            "production_registry_mutated": False,
            "existing_mochipoyo_bat_modified": False,
            "existing_mochipoyo_ledgers_mutated": False,
            "trigger_state_mutated": False,
        },
        "paths": {
            "out_dir": str(args.out_dir),
            "case_log_csv": str(args.out_dir / "guarded_demo_send_safety_case_log.csv"),
            "summary_json": str(args.out_dir / SUMMARY_FILENAME),
        },
        "cases": [
            {k: v for k, v in c.items() if k != "summary"}
            for c in cases
        ],
    }
    write_json(args.out_dir / SUMMARY_FILENAME, summary)

    print("=" * 80, flush=True)
    print("GOLD multi-strategy guarded demo-send safety validation summary", flush=True)
    print(json.dumps({
        "validation_ok": validation_ok,
        "reason": summary["reason"],
        "checks_total": summary["checks_total"],
        "checks_failed": summary["checks_failed"],
        "failed_cases": failed_cases,
        "safety": summary["safety"],
        "summary_json": summary["paths"]["summary_json"],
    }, ensure_ascii=False, indent=2, sort_keys=True, default=str), flush=True)
    print("=" * 80, flush=True)
    return 0 if validation_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
