#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GOLD V3 Stage234 - Discord + MT5 DEMO order loop coordinator.

Coordinates existing approved stages:
- Stage227 runtime queue refresh
- Stage226 Discord alert-only once against runtime queue
- Stage233 MT5 DEMO order loop one cycle against runtime queue

Stage234 itself does not call a Discord webhook and does not call mt5.order_send.
It only orchestrates subprocesses and writes coordination output.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple


STAGE = "GOLD_V3_234_DISCORD_AND_DEMO_ORDER_LOOP_COORDINATOR"
DECISION_READY = "STAGE234_DISCORD_AND_DEMO_ORDER_LOOP_COORDINATOR_READY"
DECISION_BLOCKED = "STAGE234_DISCORD_AND_DEMO_ORDER_LOOP_COORDINATOR_BLOCKED"
TERMINAL_HASH = "2FA8A7E69CED7DC259B1AD86A247F675"

LEDGER_COLUMNS = [
    "created_at_utc",
    "stage",
    "cycle_index",
    "runtime_queue_exists",
    "runtime_queue_rows",
    "stage227_return_code",
    "stage226_return_code",
    "stage233_return_code",
    "stage226_tail",
    "stage233_tail",
]

OFF_FLAGS = {
    "stage234_direct_discord_webhook_called": False,
    "stage234_direct_mt5_order_send_called": False,
    "stage234_direct_order_placed": False,
    "position_close_called": False,
    "position_modify_called": False,
    "real_account_allowed": False,
    "final_live_enabled": False,
    "payload_activation_enabled": False,
    "no_signal_order_allowed": False,
    "unbounded_loop_allowed": False,
    "source_csv_mutated": False,
    "contract_mutated": False,
    "production_retention_mutated": False,
    "candidate_pool_removed": False,
    "f002_exclusion_bypassed": False,
    "open_asof_allowed": False,
    "theoretical_result_used_as_input": False,
    "actual_execution_used_as_input": False,
}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def mql5_files_dir() -> Path:
    env_value = os.environ.get("GOLD_V3_MQL5_FILES")
    if env_value:
        return Path(env_value).expanduser().resolve()
    appdata = os.environ.get("APPDATA")
    if appdata:
        return Path(appdata, "MetaQuotes", "Terminal", TERMINAL_HASH, "MQL5", "Files").resolve()
    return Path.cwd().resolve()


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def paths() -> Dict[str, Path]:
    files = mql5_files_dir()
    out = files / "FX_OUTPUTS" / "gold_v3" / "234"
    work = out / "discord_and_demo_order_loop_coordinator"
    runtime = files / "FX_OUTPUTS" / "gold_v3" / "runtime"
    return {
        "files": files,
        "out": out,
        "work": work,
        "runtime_queue": runtime / "alert_only_queue.csv",
        "cycle_ledger": work / "stage234_cycle_ledger.csv",
        "summary": work / "stage234_summary.json",
        "paste": out / "paste_me.txt",
        "kill_switch": files / "FX_OUTPUTS" / "gold_v3" / "KILL_SWITCH_STAGE234.txt",
        "stage233_kill_switch": files / "FX_OUTPUTS" / "gold_v3" / "KILL_SWITCH_STAGE233.txt",
    }


def json_safe(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(v) for v in value]
    return str(value)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(json_safe(payload), ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def read_csv_rows(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def append_csv_rows(path: Path, rows: List[Dict[str, Any]], fieldnames: List[str]) -> None:
    if not rows:
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("w", encoding="utf-8", newline="") as f:
                csv.DictWriter(f, fieldnames=fieldnames).writeheader()
        return
    exists = path.exists()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        if not exists:
            writer.writeheader()
        for row in rows:
            writer.writerow(row)


def run_cmd(args: List[str], timeout: int = 180) -> Tuple[int, str]:
    result = subprocess.run(args, cwd=str(repo_root()), capture_output=True, text=True, timeout=timeout)
    text = (result.stdout or "")
    if result.stderr:
        text += "\n" + result.stderr
    return result.returncode, text[-3000:]


def wait_until_boundary_plus_delay(delay_seconds: int) -> None:
    now = time.time()
    next_minute = int(now // 60) * 60 + 60
    target = next_minute + delay_seconds
    sleep_seconds = max(0, target - now)
    if sleep_seconds > 0:
        time.sleep(sleep_seconds)


def stage_paths() -> Dict[str, Path]:
    root = repo_root()
    return {
        "stage227": root / "scripts" / "gold_v3_runtime" / "gold_v3_227_alert_only_runtime_queue_binding_audit.py",
        "stage226": root / "scripts" / "gold_v3_runtime" / "gold_v3_226_demo_discord_alert_only_loop_restart_local.py",
        "stage233": root / "scripts" / "gold_v3_runtime" / "gold_v3_233_demo_order_loop_scalp_daytrade_001lot.py",
    }


def validate(summary: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], List[str]]:
    checks: List[Dict[str, Any]] = []

    def add(cid: str, passed: bool, details: str) -> None:
        checks.append({"check_id": cid, "passed": bool(passed), "details": details})

    add("C234001", summary.get("explicit_user_request_recorded") is True, "Stage234 requested after Stage233 READY")
    add("C234002", summary.get("bounded_cycle_count") <= summary.get("max_cycles_allowed"), f"bounded cycles={summary.get('bounded_cycle_count')}")
    add("C234003", summary.get("stage227_script_exists") is True, "Stage227 script exists")
    add("C234004", summary.get("stage226_script_exists") is True, "Stage226 script exists")
    add("C234005", summary.get("stage233_script_exists") is True, "Stage233 script exists")
    add("C234006", summary.get("kill_switch_present") is False, "Stage234 kill switch absent")
    add("C234007", summary.get("stage233_kill_switch_present") is False, "Stage233 kill switch absent")
    add("C234008", summary.get("stage234_direct_discord_webhook_called") is False and summary.get("stage234_direct_mt5_order_send_called") is False, "coordinator has no direct send/order call")
    add("C234009", summary.get("final_live_enabled") is False and summary.get("payload_activation_enabled") is False and summary.get("no_signal_order_allowed") is False, "restricted modes OFF")
    add("C234010", summary.get("cycle_count_completed") >= 1, f"cycle_count_completed={summary.get('cycle_count_completed')}")
    add("C234011", summary.get("failed_subprocess_count") == 0, f"failed_subprocess_count={summary.get('failed_subprocess_count')}")

    blockers = [f"{row['check_id']}: {row['details']}" for row in checks if not row["passed"]]
    return checks, blockers


def write_paste_me(path: Path, summary: Dict[str, Any], checks: List[Dict[str, Any]]) -> None:
    lines: List[str] = []
    lines.append("GOLD V3 234 PASTE_ME_DISCORD_AND_DEMO_ORDER_LOOP_COORDINATOR")
    keys = [
        "step", "status", "ready", "decision", "created_at_utc", "output_dir", "work_dir",
        "explicit_user_request_recorded", "bounded_cycle_count", "max_cycles_allowed", "cycle_count_completed",
        "stage227_script_exists", "stage226_script_exists", "stage233_script_exists",
        "runtime_queue_exists_last", "runtime_queue_rows_last",
        "stage227_success_count", "stage226_success_count", "stage233_success_count", "failed_subprocess_count",
        "kill_switch_present", "stage233_kill_switch_present", "blocker_count",
    ] + list(OFF_FLAGS.keys())
    for key in keys:
        lines.append(f"{key}: {summary.get(key)}")
    lines.append("")
    lines.append("OUTPUT_FILES")
    for k, v in summary.get("output_files", {}).items():
        lines.append(f"{k}: {v}")
    lines.append("")
    lines.append("VALIDATION_CHECKS")
    for check in checks:
        lines.append(f"{check['check_id']} | passed={check['passed']} | {check['details']}")
    lines.append("")
    lines.append("INTERPRETATION")
    lines.append("Stage234 coordinated Stage227 queue refresh, Stage226 Discord alert-only once, and Stage233 MT5 DEMO order-loop one-cycle against the same runtime queue. Stage234 itself did not call a Discord webhook or mt5.order_send directly.")
    lines.append("")
    lines.append("BLOCKERS")
    if summary.get("blockers"):
        lines.extend(summary["blockers"])
    else:
        lines.append("NO_BLOCKERS")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cycles", type=int, default=60)
    parser.add_argument("--delay-seconds", type=int, default=5)
    parser.add_argument("--wait-boundary", action="store_true")
    args = parser.parse_args()
    if args.cycles < 1:
        args.cycles = 1
    if args.cycles > 60:
        args.cycles = 60

    p = paths()
    sp = stage_paths()
    p["out"].mkdir(parents=True, exist_ok=True)
    p["work"].mkdir(parents=True, exist_ok=True)

    summary: Dict[str, Any] = {
        "step": STAGE,
        "created_at_utc": utc_now_iso(),
        "output_dir": str(p["out"]),
        "work_dir": str(p["work"]),
        "explicit_user_request_recorded": True,
        "bounded_cycle_count": args.cycles,
        "max_cycles_allowed": 60,
        "cycle_count_completed": 0,
        "stage227_script_exists": sp["stage227"].exists(),
        "stage226_script_exists": sp["stage226"].exists(),
        "stage233_script_exists": sp["stage233"].exists(),
        "runtime_queue_exists_last": p["runtime_queue"].exists(),
        "runtime_queue_rows_last": 0,
        "stage227_success_count": 0,
        "stage226_success_count": 0,
        "stage233_success_count": 0,
        "failed_subprocess_count": 0,
        "kill_switch_present": p["kill_switch"].exists(),
        "stage233_kill_switch_present": p["stage233_kill_switch"].exists(),
        "output_files": {
            "cycle_ledger_csv": str(p["cycle_ledger"]),
            "summary_json": str(p["summary"]),
            "paste_me": str(p["paste"]),
            "stage234_kill_switch": str(p["kill_switch"]),
            "stage233_kill_switch": str(p["stage233_kill_switch"]),
        },
    }
    summary.update(OFF_FLAGS)

    try:
        if not summary["stage227_script_exists"]:
            raise RuntimeError(f"Stage227 script missing: {sp['stage227']}")
        if not summary["stage226_script_exists"]:
            raise RuntimeError(f"Stage226 script missing: {sp['stage226']}")
        if not summary["stage233_script_exists"]:
            raise RuntimeError(f"Stage233 script missing: {sp['stage233']}")
        rows: List[Dict[str, Any]] = []
        for cycle_index in range(1, args.cycles + 1):
            if p["kill_switch"].exists():
                summary["kill_switch_present"] = True
                break
            if p["stage233_kill_switch"].exists():
                summary["stage233_kill_switch_present"] = True
                break
            if args.wait_boundary:
                wait_until_boundary_plus_delay(args.delay_seconds)

            stage227_code, stage227_tail = run_cmd([sys.executable, str(sp["stage227"])], timeout=180)
            if stage227_code == 0:
                summary["stage227_success_count"] += 1
            else:
                summary["failed_subprocess_count"] += 1

            runtime_queue_rows = read_csv_rows(p["runtime_queue"])
            summary["runtime_queue_exists_last"] = p["runtime_queue"].exists()
            summary["runtime_queue_rows_last"] = len(runtime_queue_rows)

            stage226_code, stage226_tail = run_cmd([
                sys.executable,
                str(sp["stage226"]),
                "--once",
                "--queue-csv",
                str(p["runtime_queue"]),
            ], timeout=240)
            if stage226_code == 0:
                summary["stage226_success_count"] += 1
            else:
                summary["failed_subprocess_count"] += 1

            stage233_code, stage233_tail = run_cmd([
                sys.executable,
                str(sp["stage233"]),
                "--cycles",
                "1",
            ], timeout=240)
            if stage233_code == 0:
                summary["stage233_success_count"] += 1
            else:
                summary["failed_subprocess_count"] += 1

            rows.append({
                "created_at_utc": utc_now_iso(),
                "stage": STAGE,
                "cycle_index": cycle_index,
                "runtime_queue_exists": p["runtime_queue"].exists(),
                "runtime_queue_rows": len(runtime_queue_rows),
                "stage227_return_code": stage227_code,
                "stage226_return_code": stage226_code,
                "stage233_return_code": stage233_code,
                "stage226_tail": stage226_tail.replace("\r", " ").replace("\n", " ")[-800:],
                "stage233_tail": stage233_tail.replace("\r", " ").replace("\n", " ")[-800:],
            })
            summary["cycle_count_completed"] += 1

            if stage227_code != 0 or stage226_code != 0 or stage233_code != 0:
                break

        append_csv_rows(p["cycle_ledger"], rows, LEDGER_COLUMNS)

    except Exception as exc:
        summary.setdefault("blockers", [])
        summary["blockers"].append(f"EXCEPTION: {type(exc).__name__}: {exc}")

    checks, validation_blockers = validate(summary)
    blockers = summary.get("blockers", []) + validation_blockers
    summary["validation_checks"] = checks
    summary["blockers"] = blockers
    summary["blocker_count"] = len(blockers)
    summary["status"] = "READY" if not blockers else "BLOCKED"
    summary["ready"] = not blockers
    summary["decision"] = DECISION_READY if not blockers else DECISION_BLOCKED
    write_json(p["summary"], summary)
    write_paste_me(p["paste"], summary, checks)

    print(f"Stage234 status: {summary['status']}")
    print(f"decision: {summary['decision']}")
    print(f"cycle_count_completed: {summary['cycle_count_completed']}")
    print(f"stage227_success_count: {summary['stage227_success_count']}")
    print(f"stage226_success_count: {summary['stage226_success_count']}")
    print(f"stage233_success_count: {summary['stage233_success_count']}")
    print(f"failed_subprocess_count: {summary['failed_subprocess_count']}")
    print(f"paste_me: {p['paste']}")
    if blockers:
        print("BLOCKERS:")
        for blocker in blockers:
            print(f"- {blocker}")
        return 2
    print("NO_BLOCKERS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
