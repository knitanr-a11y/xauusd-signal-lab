#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""GOLD multi-strategy case-matrix validation.

This validator runs the currently safe dry-run verification cases that connect
GOLD BUY/SELL signal work toward the Mochipoyo-compatible flow.

Case A:
    Independent GOLD multi-strategy Mochipoyo-loop dry-run wrapper.
    Validates live CSV -> BUY/SELL router -> adapter -> payload bridge -> sender
    dry-run path. This is usually a no-signal live-cycle validation.

Case B:
    Sender-native registry preview hook validation.
    Validates fresh payload -> sender dry-run -> registry preview -> mock
    position -> reconcile -> registry-aware same_strategy BLOCK.

Case C:
    Mock signal-present path validation.
    Creates a mock router OPEN_POSITION intent and validates adapter -> payload
    -> sender dry-run -> registry preview -> mock position -> reconcile ->
    same_strategy BLOCK -> duplicate preview skip.

Case D:
    Minute-aligned one-cycle dry-run validation.
    Validates that the independent dry-run runner is configured for the
    Mochipoyo-style cadence: every 1 minute at second 02.

Safety boundaries:
- Does not pass --send itself.
- Calls only safe dry-run / validation BATs.
- Does not write production position_registry.csv.
- Does not modify existing Mochipoyo production/demo BATs.
- Does not intentionally mutate existing Mochipoyo ledgers or trigger-state.
- Uses Windows long-path helpers for its own summary/log outputs.
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

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT_DIR = Path("data/research_results/gold_multi_strategy_case_matrix_validation")

CASE_LOG_COLUMNS = [
    "case_id",
    "case_name",
    "started_at_utc",
    "ended_at_utc",
    "returncode",
    "case_ok",
    "reason",
    "summary_json",
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


def utc_now_text() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")


def write_text(path: Path, text: str) -> None:
    ensure_parent_dir(path)
    with open(windows_long_path(path), "w", encoding="utf-8", newline="") as f:
        f.write(text)


def read_json_or_empty(path: Path) -> dict[str, Any]:
    try:
        with open(windows_long_path(path), "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except Exception as exc:
        return {"_read_error": str(exc), "_path": str(path)}


def write_json(path: Path, obj: dict[str, Any]) -> None:
    write_text(path, json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True, default=str))


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


def run_bat(case_id: str, bat_path: Path, *, out_dir: Path) -> dict[str, Any]:
    started = utc_now_text()
    log_dir = out_dir / "command_logs"
    mkdir_path(log_dir)
    stdout_path = log_dir / f"{case_id}_stdout.txt"
    stderr_path = log_dir / f"{case_id}_stderr.txt"
    cmd = ["cmd.exe", "/c", str(bat_path)]
    print("=" * 80, flush=True)
    print(f"[CASE] {case_id}", flush=True)
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
    print(f"[CASE] {case_id} returncode={completed.returncode}", flush=True)
    return {
        "case_id": case_id,
        "started_at_utc": started,
        "ended_at_utc": ended,
        "returncode": int(completed.returncode),
        "stdout_path": str(stdout_path),
        "stderr_path": str(stderr_path),
    }


def validate_loop_dry_run() -> tuple[bool, str, dict[str, Any], Path]:
    summary_path = REPO_ROOT / "data" / "research_results" / "gold_multi_strategy_mochipoyo_loop_dry_run" / "latest_gold_multi_strategy_mochipoyo_loop_dry_run_result.json"
    summary = read_json_or_empty(summary_path)
    if not summary:
        return False, "LOOP_SUMMARY_MISSING", summary, summary_path
    if summary.get("_read_error"):
        return False, "LOOP_SUMMARY_READ_ERROR", summary, summary_path
    safety = summary.get("safety", {}) if isinstance(summary.get("safety"), dict) else {}
    metrics = summary.get("key_metrics", {}) if isinstance(summary.get("key_metrics"), dict) else {}
    checks = {
        "cycle_ok": as_bool(summary.get("cycle_ok")),
        "send_flag_false": not as_bool(safety.get("send_flag_passed"), False),
        "order_send_zero": as_int(safety.get("sender_order_send_called_count"), 0) == 0,
        "sent_rows_zero": as_int(safety.get("sender_sent_rows"), 0) == 0,
        "router_ok": as_bool(metrics.get("router_ok")),
        "adapter_ok": as_bool(metrics.get("adapter_ok")),
        "bridge_ok": as_bool(metrics.get("bridge_ok")),
        "sender_stage_ok": as_bool(metrics.get("sender_stage_ok")),
    }
    failed = [k for k, v in checks.items() if not v]
    details = {"summary": summary, "checks": checks, "failed": failed}
    return len(failed) == 0, "LOOP_DRY_RUN_PASS" if not failed else "LOOP_DRY_RUN_FAILED", details, summary_path


def validate_sender_native_registry_policy() -> tuple[bool, str, dict[str, Any], Path]:
    sender_report_path = REPO_ROOT / "data" / "r" / "sender_hook" / "sender" / "mt5_order_send_report.json"
    registry_preview_path = REPO_ROOT / "data" / "r" / "sender_hook" / "registry_preview.json"
    policy_preview_path = REPO_ROOT / "data" / "r" / "sender_hook" / "p" / "registry_policy_preview.json"
    sender_report = read_json_or_empty(sender_report_path)
    registry_preview = read_json_or_empty(registry_preview_path)
    policy_preview = read_json_or_empty(policy_preview_path)
    registry_section = sender_report.get("registry_preview", {}) if isinstance(sender_report.get("registry_preview"), dict) else {}
    checks = {
        "sender_report_exists": bool(sender_report),
        "send_requested_false": not as_bool(sender_report.get("send_requested"), False),
        "order_send_zero": as_int(sender_report.get("order_send_called_count"), 0) == 0,
        "sent_rows_zero": as_int(sender_report.get("sent_rows"), 0) == 0,
        "preview_enabled": as_bool(registry_section.get("preview_enabled"), False),
        "registry_preview_rows": as_int(registry_section.get("registry_preview_rows"), 0) >= 1,
        "policy_preview_ok": as_bool(policy_preview.get("preview_ok"), False),
        "same_strategy_blocked": as_int(policy_preview.get("same_strategy_blocked_rows"), 0) >= 1,
        "blocked_rows": as_int(policy_preview.get("blocked_rows"), 0) >= 1,
        "allow_rows_zero": as_int(policy_preview.get("allow_rows"), 0) == 0,
        "registry_inconsistency_zero": as_int(policy_preview.get("registry_inconsistency_blocked_rows"), 0) == 0,
    }
    failed = [k for k, v in checks.items() if not v]
    details = {
        "sender_report_path": str(sender_report_path),
        "registry_preview_path": str(registry_preview_path),
        "policy_preview_path": str(policy_preview_path),
        "sender_report": sender_report,
        "registry_preview": registry_preview,
        "policy_preview": policy_preview,
        "checks": checks,
        "failed": failed,
    }
    return len(failed) == 0, "SENDER_NATIVE_REGISTRY_POLICY_PASS" if not failed else "SENDER_NATIVE_REGISTRY_POLICY_FAILED", details, policy_preview_path


def validate_mock_signal_path() -> tuple[bool, str, dict[str, Any], Path]:
    summary_path = REPO_ROOT / "data" / "research_results" / "gold_multi_strategy_mock_signal_path_validation" / "latest_gold_multi_strategy_mock_signal_path_validation_result.json"
    summary = read_json_or_empty(summary_path)
    if not summary:
        return False, "MOCK_SIGNAL_SUMMARY_MISSING", summary, summary_path
    if summary.get("_read_error"):
        return False, "MOCK_SIGNAL_SUMMARY_READ_ERROR", summary, summary_path
    checks_obj = summary.get("checks", {}) if isinstance(summary.get("checks"), dict) else {}
    safety = summary.get("safety", {}) if isinstance(summary.get("safety"), dict) else {}
    checks = {
        "validation_ok": as_bool(summary.get("validation_ok"), False),
        "all_embedded_checks_true": all(as_bool(v, False) for v in checks_obj.values()) if checks_obj else False,
        "checks_failed_empty": len(summary.get("checks_failed", [])) == 0 if isinstance(summary.get("checks_failed", []), list) else False,
        "send_flag_false": not as_bool(safety.get("send_flag_passed"), False),
        "order_send_zero": as_int(safety.get("sender_order_send_called_count"), 0) == 0,
        "sent_rows_zero": as_int(safety.get("sender_sent_rows"), 0) == 0,
        "production_registry_false": not as_bool(safety.get("production_registry_mutated"), False),
        "existing_mochipoyo_bat_false": not as_bool(safety.get("existing_mochipoyo_bat_modified"), False),
        "trigger_state_false": not as_bool(safety.get("trigger_state_mutated"), False),
    }
    failed = [k for k, v in checks.items() if not v]
    details = {"summary": summary, "checks": checks, "failed": failed}
    return len(failed) == 0, "MOCK_SIGNAL_PATH_PASS" if not failed else "MOCK_SIGNAL_PATH_FAILED", details, summary_path


def validate_minute_aligned_dry_run() -> tuple[bool, str, dict[str, Any], Path]:
    summary_path = REPO_ROOT / "data" / "research_results" / "gold_multi_strategy_mochipoyo_loop_dry_run_aligned" / "latest_gold_multi_strategy_mochipoyo_loop_dry_run_aligned_result.json"
    summary = read_json_or_empty(summary_path)
    if not summary:
        return False, "MINUTE_ALIGNED_SUMMARY_MISSING", summary, summary_path
    if summary.get("_read_error"):
        return False, "MINUTE_ALIGNED_SUMMARY_READ_ERROR", summary, summary_path
    safety = summary.get("safety", {}) if isinstance(summary.get("safety"), dict) else {}
    last_cycle = summary.get("last_cycle", {}) if isinstance(summary.get("last_cycle"), dict) else {}
    checks = {
        "loop_ok": as_bool(summary.get("loop_ok"), False),
        "cycles_run_at_least_one": as_int(summary.get("cycles_run"), 0) >= 1,
        "failed_cycles_zero": as_int(summary.get("failed_cycles"), 0) == 0,
        "interval_minutes_one": as_int(summary.get("interval_minutes"), 0) == 1,
        "offset_seconds_two": as_int(summary.get("offset_seconds"), -1) == 2,
        "last_cycle_ok": as_bool(last_cycle.get("cycle_ok"), False),
        "last_cycle_order_send_zero": as_int(last_cycle.get("sender_order_send_called_count"), 0) == 0,
        "last_cycle_sent_rows_zero": as_int(last_cycle.get("sender_sent_rows"), 0) == 0,
        "send_flag_false": not as_bool(safety.get("send_flag_passed_by_this_runner"), False),
        "production_registry_false": not as_bool(safety.get("production_registry_mutated_by_this_runner"), False),
        "existing_mochipoyo_bat_false": not as_bool(safety.get("existing_mochipoyo_bat_modified_by_this_runner"), False),
    }
    failed = [k for k, v in checks.items() if not v]
    details = {"summary": summary, "checks": checks, "failed": failed}
    return len(failed) == 0, "MINUTE_ALIGNED_DRY_RUN_PASS" if not failed else "MINUTE_ALIGNED_DRY_RUN_FAILED", details, summary_path


def add_case(cases: list[dict[str, Any]], *, case_run: dict[str, Any], case_name: str, ok: bool, reason: str, summary_path: Path, details: dict[str, Any], out_dir: Path) -> None:
    details_json = out_dir / f"{case_run['case_id']}_details.json"
    case = {
        **case_run,
        "case_name": case_name,
        "case_ok": bool(case_run["returncode"] == 0 and ok),
        "reason": reason if case_run["returncode"] == 0 else f"BAT_RETURNCODE_{case_run['returncode']}_{reason}",
        "summary_json": str(summary_path),
        "details_json": str(details_json),
        "details": details,
    }
    write_json(details_json, details)
    append_csv_row(out_dir / "case_matrix_log.csv", case, CASE_LOG_COLUMNS)
    cases.append(case)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run GOLD multi-strategy safe case-matrix validation.")
    p.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    p.add_argument("--skip-loop", action="store_true")
    p.add_argument("--skip-sender-registry", action="store_true")
    p.add_argument("--skip-mock-signal", action="store_true")
    p.add_argument("--skip-minute-aligned", action="store_true")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    mkdir_path(args.out_dir)
    started = utc_now_text()
    cases: list[dict[str, Any]] = []

    if not args.skip_loop:
        case_run = run_bat("case_a_mochipoyo_loop_dry_run", REPO_ROOT / "scripts" / "run_gold_multi_strategy_mochipoyo_loop_dry_run.bat", out_dir=args.out_dir)
        ok, reason, details, summary_path = validate_loop_dry_run()
        add_case(cases, case_run=case_run, case_name="Mochipoyo-loop dry-run wrapper", ok=ok, reason=reason, summary_path=summary_path, details=details, out_dir=args.out_dir)

    if not args.skip_sender_registry:
        case_run = run_bat("case_b_sender_native_registry_policy", REPO_ROOT / "scripts" / "run_gold_multi_strategy_sender_native_registry_preview_hook_validation.bat", out_dir=args.out_dir)
        ok, reason, details, summary_path = validate_sender_native_registry_policy()
        add_case(cases, case_run=case_run, case_name="Sender-native registry preview and policy BLOCK", ok=ok, reason=reason, summary_path=summary_path, details=details, out_dir=args.out_dir)

    if not args.skip_mock_signal:
        case_run = run_bat("case_c_mock_signal_path", REPO_ROOT / "scripts" / "run_gold_multi_strategy_mock_signal_path_validation.bat", out_dir=args.out_dir)
        ok, reason, details, summary_path = validate_mock_signal_path()
        add_case(cases, case_run=case_run, case_name="Mock signal-present adapter/payload/sender/registry path", ok=ok, reason=reason, summary_path=summary_path, details=details, out_dir=args.out_dir)

    if not args.skip_minute_aligned:
        case_run = run_bat("case_d_minute_aligned_dry_run", REPO_ROOT / "scripts" / "run_gold_multi_strategy_mochipoyo_loop_dry_run_aligned.bat", out_dir=args.out_dir)
        ok, reason, details, summary_path = validate_minute_aligned_dry_run()
        add_case(cases, case_run=case_run, case_name="Minute-aligned one-cycle dry-run timing", ok=ok, reason=reason, summary_path=summary_path, details=details, out_dir=args.out_dir)

    ended = utc_now_text()
    checks_total = len(cases)
    checks_failed = sum(1 for case in cases if not bool(case.get("case_ok")))
    summary = {
        "schema_version": "gold_multi_strategy_case_matrix_validation_v3",
        "started_at_utc": started,
        "ended_at_utc": ended,
        "case_matrix_ok": checks_failed == 0,
        "reason": "GOLD_MULTI_STRATEGY_CASE_MATRIX_PASS" if checks_failed == 0 else "GOLD_MULTI_STRATEGY_CASE_MATRIX_FAILED",
        "checks_total": checks_total,
        "checks_failed": checks_failed,
        "safety": {
            "send_flag_passed_by_this_validator": False,
            "production_registry_mutated_by_this_validator": False,
            "existing_mochipoyo_bat_modified_by_this_validator": False,
        },
        "cases": [
            {k: v for k, v in case.items() if k != "details"}
            for case in cases
        ],
        "outputs": {
            "summary_json": str(args.out_dir / "latest_gold_multi_strategy_case_matrix_validation_result.json"),
            "case_matrix_log_csv": str(args.out_dir / "case_matrix_log.csv"),
        },
    }
    write_json(args.out_dir / "latest_gold_multi_strategy_case_matrix_validation_result.json", summary)
    print("=" * 80)
    print("GOLD multi-strategy case matrix validation summary")
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True, default=str))
    print("=" * 80)
    return 0 if summary["case_matrix_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
