#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verify fresh sender registry policy full-cycle summary.json.

Purpose:
- Provide an independent read-only checker for the canonical dry-run BAT output.
- Fail loudly if safety or expected policy checks are not satisfied.

Safety:
- Read-only.
- No MetaTrader5 import.
- No order_check/order_send.
- No ledger/registry/trigger-state mutation.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

import pandas as pd

SCHEMA_VERSION = "gold_multi_strategy_fresh_sender_registry_policy_full_cycle_summary_verifier_v1"

DEFAULT_SUMMARY_JSON = Path("data/r/ff/summary.json")
DEFAULT_OUT_JSON = Path("data/r/ff/summary_verify.json")
DEFAULT_OUT_CSV = Path("data/r/ff/summary_verify_checks.csv")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Verify full-cycle dry-run summary.json. Read-only.")
    p.add_argument("--summary-json", type=Path, default=DEFAULT_SUMMARY_JSON)
    p.add_argument("--out-json", type=Path, default=DEFAULT_OUT_JSON)
    p.add_argument("--out-csv", type=Path, default=DEFAULT_OUT_CSV)
    p.add_argument("--require-cycle-ok", action="store_true", default=True)
    p.add_argument("--require-dry-run-check-ok-rows", type=int, default=1)
    p.add_argument("--require-registry-preview-rows", type=int, default=1)
    p.add_argument("--require-matched-active-registry-rows", type=int, default=1)
    p.add_argument("--require-same-strategy-blocked-rows", type=int, default=1)
    p.add_argument("--require-order-send-called-count", type=int, default=0)
    p.add_argument("--require-send-requested-false", action="store_true", default=True)
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


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(Path(windows_long_path(path)).read_text(encoding="utf-8"))


def write_json(path: Path, obj: dict[str, Any]) -> None:
    Path(windows_long_path(path.parent)).mkdir(parents=True, exist_ok=True)
    Path(windows_long_path(path)).write_text(
        json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True, default=str),
        encoding="utf-8",
    )


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    Path(windows_long_path(path.parent)).mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(windows_long_path(path), index=False, encoding="utf-8-sig")


def dig(obj: dict[str, Any], path: str, default: Any = None) -> Any:
    cur: Any = obj
    for part in path.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return default
    return cur


def as_int(value: Any, default: int = 0) -> int:
    try:
        if value is None or value == "":
            return default
        return int(float(value))
    except Exception:
        return default


def as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "ok"}
    return bool(value)


def check_row(name: str, actual: Any, expected: Any, ok: bool, detail: str = "") -> dict[str, Any]:
    return {
        "check_name": name,
        "ok": bool(ok),
        "actual": actual,
        "expected": expected,
        "detail": detail,
    }


def build_checks(summary: dict[str, Any], args: argparse.Namespace) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []

    cycle_ok = as_bool(summary.get("cycle_ok"))
    checks.append(check_row("cycle_ok", cycle_ok, True, cycle_ok is True))

    reason = str(summary.get("reason", ""))
    checks.append(check_row(
        "reason",
        reason,
        "FRESH_SENDER_REGISTRY_POLICY_FULL_CYCLE_PASS",
        reason == "FRESH_SENDER_REGISTRY_POLICY_FULL_CYCLE_PASS",
    ))

    send_requested = as_bool(summary.get("send_requested"))
    checks.append(check_row("send_requested_false", send_requested, False, send_requested is False))

    safety_paths = [
        "safety.wrapper_passed_send_flag",
        "safety.production_registry_mutated",
        "safety.trigger_state_mutated",
        "safety.existing_sender_modified",
        "safety.existing_bat_modified",
    ]
    for path in safety_paths:
        actual = as_bool(dig(summary, path, False))
        checks.append(check_row(path, actual, False, actual is False))

    sender_cycle_ok = as_bool(dig(summary, "sender_cycle.cycle_ok", False))
    checks.append(check_row("sender_cycle.cycle_ok", sender_cycle_ok, True, sender_cycle_ok is True))

    dry_run_rows = as_int(dig(summary, "sender_cycle.sender_metrics.dry_run_check_ok_rows", 0), 0)
    checks.append(check_row(
        "sender_cycle.sender_metrics.dry_run_check_ok_rows",
        dry_run_rows,
        f">={args.require_dry_run_check_ok_rows}",
        dry_run_rows >= int(args.require_dry_run_check_ok_rows),
    ))

    order_send_count = as_int(dig(summary, "sender_cycle.sender_metrics.order_send_called_count", 0), 0)
    checks.append(check_row(
        "sender_cycle.sender_metrics.order_send_called_count",
        order_send_count,
        int(args.require_order_send_called_count),
        order_send_count == int(args.require_order_send_called_count),
    ))

    sent_rows = as_int(dig(summary, "sender_cycle.sender_metrics.sent_rows", 0), 0)
    checks.append(check_row("sender_cycle.sender_metrics.sent_rows", sent_rows, 0, sent_rows == 0))

    error_rows = as_int(dig(summary, "sender_cycle.sender_metrics.error_rows", 0), 0)
    checks.append(check_row("sender_cycle.sender_metrics.error_rows", error_rows, 0, error_rows == 0))

    registry_preview_rows = as_int(dig(summary, "sender_cycle.registry_preview_rows", 0), 0)
    checks.append(check_row(
        "sender_cycle.registry_preview_rows",
        registry_preview_rows,
        f">={args.require_registry_preview_rows}",
        registry_preview_rows >= int(args.require_registry_preview_rows),
    ))

    mock_ok = as_bool(dig(summary, "mock_positions.build_ok", False))
    checks.append(check_row("mock_positions.build_ok", mock_ok, True, mock_ok is True))

    mock_rows = as_int(dig(summary, "mock_positions.rows_out", 0), 0)
    checks.append(check_row("mock_positions.rows_out", mock_rows, ">=1", mock_rows >= 1))

    reconcile_ok = as_bool(dig(summary, "reconcile.reconcile_ok", False))
    checks.append(check_row("reconcile.reconcile_ok", reconcile_ok, True, reconcile_ok is True))

    matched_rows = as_int(dig(summary, "reconcile.matched_active_registry_rows", 0), 0)
    checks.append(check_row(
        "reconcile.matched_active_registry_rows",
        matched_rows,
        f">={args.require_matched_active_registry_rows}",
        matched_rows >= int(args.require_matched_active_registry_rows),
    ))

    mismatch_rows = as_int(dig(summary, "reconcile.matched_with_mismatch_rows", 0), 0)
    checks.append(check_row("reconcile.matched_with_mismatch_rows", mismatch_rows, 0, mismatch_rows == 0))

    missing_rows = as_int(dig(summary, "reconcile.missing_position_rows", 0), 0)
    checks.append(check_row("reconcile.missing_position_rows", missing_rows, 0, missing_rows == 0))

    unregistered_rows = as_int(dig(summary, "reconcile.unregistered_position_rows", 0), 0)
    checks.append(check_row("reconcile.unregistered_position_rows", unregistered_rows, 0, unregistered_rows == 0))

    policy_ok = as_bool(dig(summary, "policy_preview.preview_ok", False))
    checks.append(check_row("policy_preview.preview_ok", policy_ok, True, policy_ok is True))

    same_strategy_rows = as_int(dig(summary, "policy_preview.same_strategy_blocked_rows", 0), 0)
    checks.append(check_row(
        "policy_preview.same_strategy_blocked_rows",
        same_strategy_rows,
        f">={args.require_same_strategy_blocked_rows}",
        same_strategy_rows >= int(args.require_same_strategy_blocked_rows),
    ))

    registry_inconsistency_rows = as_int(dig(summary, "policy_preview.registry_inconsistency_blocked_rows", 0), 0)
    checks.append(check_row(
        "policy_preview.registry_inconsistency_blocked_rows",
        registry_inconsistency_rows,
        0,
        registry_inconsistency_rows == 0,
    ))

    allow_rows = as_int(dig(summary, "policy_preview.allow_rows", 0), 0)
    checks.append(check_row("policy_preview.allow_rows", allow_rows, 0, allow_rows == 0))

    blocked_rows = as_int(dig(summary, "policy_preview.blocked_rows", 0), 0)
    checks.append(check_row("policy_preview.blocked_rows", blocked_rows, ">=1", blocked_rows >= 1))

    return checks


def console_json(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=True, indent=2, sort_keys=True, default=str)


def main() -> int:
    args = parse_args()
    if not path_exists(args.summary_json):
        result = {
            "schema_version": SCHEMA_VERSION,
            "verify_ok": False,
            "reason": "SUMMARY_JSON_NOT_FOUND",
            "summary_json": str(args.summary_json),
            "out_json": str(args.out_json),
            "out_csv": str(args.out_csv),
            "safety": safety_summary(),
            "checks": [],
        }
        write_json(args.out_json, result)
        write_csv(args.out_csv, [])
        print("verify_gold_multi_strategy_fresh_sender_registry_policy_full_cycle_summary")
        print(console_json(result))
        return 2

    summary = read_json(args.summary_json)
    checks = build_checks(summary, args)
    failed = [row for row in checks if not bool(row.get("ok"))]
    result = {
        "schema_version": SCHEMA_VERSION,
        "verify_ok": len(failed) == 0,
        "reason": "SUMMARY_VERIFY_PASS" if len(failed) == 0 else "SUMMARY_VERIFY_FAILED",
        "summary_json": str(args.summary_json),
        "out_json": str(args.out_json),
        "out_csv": str(args.out_csv),
        "checks_total": int(len(checks)),
        "checks_failed": int(len(failed)),
        "failed_check_names": [str(row.get("check_name")) for row in failed],
        "safety": safety_summary(),
        "checks": checks,
    }
    write_json(args.out_json, result)
    write_csv(args.out_csv, checks)
    print("verify_gold_multi_strategy_fresh_sender_registry_policy_full_cycle_summary")
    print(console_json({k: v for k, v in result.items() if k != "checks"}))
    if checks:
        df = pd.DataFrame(checks)
        print(df[["check_name", "ok", "actual", "expected"]].to_string(index=False))
    print(f"out_json: {args.out_json}")
    print(f"out_csv: {args.out_csv}")
    print("done")
    return 0 if result["verify_ok"] else 1


def safety_summary() -> dict[str, Any]:
    return {
        "read_only": True,
        "mt5_imported": False,
        "order_check_called": False,
        "order_send_called": False,
        "ledger_mutated": False,
        "registry_mutated": False,
        "trigger_state_mutated": False,
    }


if __name__ == "__main__":
    raise SystemExit(main())
