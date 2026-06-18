#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GOLD V3 Stage236 - Demo coordinator continuous supervisor.

Calls Stage234 once per minute until kill switch, Ctrl+C, or Stage234 failure.
Stage236 itself does not call Discord webhook and does not call mt5.order_send.
This is DEMO-only continuous time supervision, not final live.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple


STAGE = "GOLD_V3_236_DEMO_COORDINATOR_CONTINUOUS_SUPERVISOR"
DECISION_READY = "STAGE236_DEMO_COORDINATOR_CONTINUOUS_SUPERVISOR_READY"
DECISION_BLOCKED = "STAGE236_DEMO_COORDINATOR_CONTINUOUS_SUPERVISOR_BLOCKED"
TERMINAL_HASH = "2FA8A7E69CED7DC259B1AD86A247F675"

LEDGER_COLUMNS = [
    "created_at_utc",
    "stage",
    "cycle_index",
    "stage234_return_code",
    "stage234_tail",
    "runtime_queue_rows_seen",
    "cycle_started_utc",
    "cycle_finished_utc",
    "stop_reason_after_cycle",
]

OFF_FLAGS = {
    "stage236_direct_discord_webhook_called": False,
    "stage236_direct_mt5_order_send_called": False,
    "stage236_direct_order_placed": False,
    "position_close_called": False,
    "position_modify_called": False,
    "real_account_allowed": False,
    "final_live_enabled": False,
    "payload_activation_enabled": False,
    "no_signal_order_allowed": False,
    "source_csv_mutated": False,
    "contract_mutated": False,
    "production_retention_mutated": False,
    "candidate_pool_removed": False,
    "f002_exclusion_bypassed": False,
    "open_asof_allowed": False,
    "theoretical_result_used_as_input": False,
    "actual_execution_used_as_input": False,
}

_INTERRUPTED = False


def _handle_signal(signum: int, frame: Any) -> None:
    global _INTERRUPTED
    _INTERRUPTED = True


signal.signal(signal.SIGINT, _handle_signal)
signal.signal(signal.SIGTERM, _handle_signal)


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
    out = files / "FX_OUTPUTS" / "gold_v3" / "236"
    work = out / "demo_coordinator_continuous_supervisor"
    runtime = files / "FX_OUTPUTS" / "gold_v3" / "runtime"
    base = files / "FX_OUTPUTS" / "gold_v3"
    return {
        "files": files,
        "out": out,
        "work": work,
        "runtime_queue": runtime / "alert_only_queue.csv",
        "cycle_ledger": work / "stage236_cycle_ledger.csv",
        "summary": work / "stage236_summary.json",
        "paste": out / "paste_me.txt",
        "kill_switch": base / "KILL_SWITCH_STAGE236.txt",
        "stage235_kill_switch": base / "KILL_SWITCH_STAGE235.txt",
        "stage234_kill_switch": base / "KILL_SWITCH_STAGE234.txt",
        "stage233_kill_switch": base / "KILL_SWITCH_STAGE233.txt",
    }


def stage234_script() -> Path:
    return repo_root() / "scripts" / "gold_v3_runtime" / "gold_v3_234_discord_and_demo_order_loop_coordinator.py"


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


def wait_until_boundary_plus_delay(delay_seconds: int) -> None:
    global _INTERRUPTED
    now = time.time()
    next_minute = int(now // 60) * 60 + 60
    target = next_minute + delay_seconds
    while not _INTERRUPTED:
        remaining = target - time.time()
        if remaining <= 0:
            return
        time.sleep(min(1.0, remaining))


def run_stage234_once(script: Path, timeout: int = 240) -> Tuple[int, str]:
    result = subprocess.run(
        [sys.executable, str(script), "--cycles", "1"],
        cwd=str(repo_root()),
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    text = result.stdout or ""
    if result.stderr:
        text += "\n" + result.stderr
    return result.returncode, text[-3000:]


def kill_switch_state(p: Dict[str, Path]) -> Dict[str, bool]:
    return {
        "kill_switch_present": p["kill_switch"].exists(),
        "stage235_kill_switch_present": p["stage235_kill_switch"].exists(),
        "stage234_kill_switch_present": p["stage234_kill_switch"].exists(),
        "stage233_kill_switch_present": p["stage233_kill_switch"].exists(),
    }


def stop_reason_from_state(summary: Dict[str, Any]) -> str:
    if summary.get("interrupted"):
        return "INTERRUPTED"
    if summary.get("kill_switch_present"):
        return "KILL_SWITCH_STAGE236"
    if summary.get("stage235_kill_switch_present"):
        return "KILL_SWITCH_STAGE235"
    if summary.get("stage234_kill_switch_present"):
        return "KILL_SWITCH_STAGE234"
    if summary.get("stage233_kill_switch_present"):
        return "KILL_SWITCH_STAGE233"
    if int(summary.get("failed_stage234_count") or 0) > 0:
        return "STAGE234_FAILURE"
    if int(summary.get("bounded_cycle_count") or 0) > 0 and int(summary.get("cycle_count_completed") or 0) >= int(summary.get("bounded_cycle_count") or 0):
        return "BOUND_CYCLE_COMPLETED"
    return "RUNNING_OR_NOT_STARTED"


def validate(summary: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], List[str]]:
    checks: List[Dict[str, Any]] = []

    def add(cid: str, passed: bool, details: str) -> None:
        checks.append({"check_id": cid, "passed": bool(passed), "details": details})

    add("C236001", summary.get("stage234_script_exists") is True, "Stage234 script exists")
    add("C236002", int(summary.get("bounded_cycle_count") or 0) >= 0, "0 means continuous")
    add("C236003", summary.get("stage236_direct_discord_webhook_called") is False and summary.get("stage236_direct_mt5_order_send_called") is False, "Stage236 has no direct webhook/order call")
    add("C236004", summary.get("final_live_enabled") is False and summary.get("payload_activation_enabled") is False and summary.get("no_signal_order_allowed") is False, "restricted modes OFF")
    add("C236005", int(summary.get("failed_stage234_count") or 0) == 0, f"failed_stage234_count={summary.get('failed_stage234_count')}")
    add("C236006", int(summary.get("cycle_count_completed") or 0) >= 0, f"cycle_count_completed={summary.get('cycle_count_completed')}")

    blockers = [f"{row['check_id']}: {row['details']}" for row in checks if not row["passed"]]
    return checks, blockers


def write_paste_me(path: Path, summary: Dict[str, Any], checks: List[Dict[str, Any]]) -> None:
    lines: List[str] = []
    lines.append("GOLD V3 236 PASTE_ME_DEMO_COORDINATOR_CONTINUOUS_SUPERVISOR")
    keys = [
        "step", "status", "ready", "decision", "created_at_utc", "updated_at_utc", "output_dir", "work_dir",
        "stage234_script_exists", "continuous_mode", "bounded_cycle_count", "cycle_count_completed",
        "stage234_success_count", "failed_stage234_count", "runtime_queue_exists_last", "runtime_queue_rows_last",
        "interrupted", "stop_reason", "kill_switch_present", "stage235_kill_switch_present", "stage234_kill_switch_present", "stage233_kill_switch_present", "blocker_count",
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
    lines.append("Stage236 supervises Stage234 continuously. Stage236 itself does not call a Discord webhook or mt5.order_send directly. Time is continuous until kill switch, Ctrl+C, bounded-cycle override, or Stage234 failure. Risk gates remain in Stage233.")
    lines.append("")
    lines.append("BLOCKERS")
    if summary.get("blockers"):
        lines.extend(summary["blockers"])
    else:
        lines.append("NO_BLOCKERS")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def refresh_status(summary: Dict[str, Any], p: Dict[str, Path], checks: List[Dict[str, Any]] | None = None) -> None:
    summary.update(kill_switch_state(p))
    summary["runtime_queue_exists_last"] = p["runtime_queue"].exists()
    summary["runtime_queue_rows_last"] = len(read_csv_rows(p["runtime_queue"]))
    summary["updated_at_utc"] = utc_now_iso()
    summary["stop_reason"] = stop_reason_from_state(summary)
    if checks is None:
        checks, blockers = validate(summary)
    else:
        _, blockers = validate(summary)
    summary["validation_checks"] = checks
    summary["blockers"] = blockers
    summary["blocker_count"] = len(blockers)
    summary["status"] = "READY" if not blockers else "BLOCKED"
    summary["ready"] = not blockers
    summary["decision"] = DECISION_READY if not blockers else DECISION_BLOCKED
    write_json(p["summary"], summary)
    write_paste_me(p["paste"], summary, checks)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cycles", type=int, default=0, help="0 means continuous until kill switch/Ctrl+C/failure")
    parser.add_argument("--delay-seconds", type=int, default=5)
    parser.add_argument("--no-wait-boundary", action="store_true")
    args = parser.parse_args()

    if args.cycles < 0:
        args.cycles = 0

    p = paths()
    script = stage234_script()
    p["out"].mkdir(parents=True, exist_ok=True)
    p["work"].mkdir(parents=True, exist_ok=True)

    summary: Dict[str, Any] = {
        "step": STAGE,
        "created_at_utc": utc_now_iso(),
        "updated_at_utc": utc_now_iso(),
        "output_dir": str(p["out"]),
        "work_dir": str(p["work"]),
        "stage234_script_exists": script.exists(),
        "continuous_mode": args.cycles == 0,
        "bounded_cycle_count": args.cycles,
        "cycle_count_completed": 0,
        "stage234_success_count": 0,
        "failed_stage234_count": 0,
        "runtime_queue_exists_last": p["runtime_queue"].exists(),
        "runtime_queue_rows_last": 0,
        "interrupted": False,
        "stop_reason": "RUNNING_OR_NOT_STARTED",
        "output_files": {
            "cycle_ledger_csv": str(p["cycle_ledger"]),
            "summary_json": str(p["summary"]),
            "paste_me": str(p["paste"]),
            "stage236_kill_switch": str(p["kill_switch"]),
            "stage235_kill_switch": str(p["stage235_kill_switch"]),
            "stage234_kill_switch": str(p["stage234_kill_switch"]),
            "stage233_kill_switch": str(p["stage233_kill_switch"]),
        },
    }
    summary.update(OFF_FLAGS)
    summary.update(kill_switch_state(p))
    refresh_status(summary, p)

    if not script.exists():
        summary.setdefault("blockers", []).append(f"EXCEPTION: Stage234 script missing: {script}")
        refresh_status(summary, p)
        return 2

    try:
        cycle_index = 0
        while True:
            summary["interrupted"] = bool(_INTERRUPTED)
            summary.update(kill_switch_state(p))
            if _INTERRUPTED or summary["kill_switch_present"] or summary["stage235_kill_switch_present"] or summary["stage234_kill_switch_present"] or summary["stage233_kill_switch_present"]:
                break
            if args.cycles > 0 and cycle_index >= args.cycles:
                break

            if not args.no_wait_boundary:
                wait_until_boundary_plus_delay(args.delay_seconds)
                if _INTERRUPTED:
                    break

            cycle_index += 1
            cycle_started = utc_now_iso()
            code, tail = run_stage234_once(script)
            cycle_finished = utc_now_iso()

            queue_rows = read_csv_rows(p["runtime_queue"])
            if code == 0:
                summary["stage234_success_count"] += 1
            else:
                summary["failed_stage234_count"] += 1

            summary["cycle_count_completed"] = cycle_index
            summary["runtime_queue_exists_last"] = p["runtime_queue"].exists()
            summary["runtime_queue_rows_last"] = len(queue_rows)

            ledger_row = {
                "created_at_utc": utc_now_iso(),
                "stage": STAGE,
                "cycle_index": cycle_index,
                "stage234_return_code": code,
                "stage234_tail": tail.replace("\r", " ").replace("\n", " ")[-1200:],
                "runtime_queue_rows_seen": len(queue_rows),
                "cycle_started_utc": cycle_started,
                "cycle_finished_utc": cycle_finished,
                "stop_reason_after_cycle": stop_reason_from_state(summary),
            }
            append_csv_rows(p["cycle_ledger"], [ledger_row], LEDGER_COLUMNS)
            refresh_status(summary, p)

            if code != 0:
                break

    except KeyboardInterrupt:
        summary["interrupted"] = True
    except Exception as exc:
        summary.setdefault("blockers", [])
        summary["blockers"].append(f"EXCEPTION: {type(exc).__name__}: {exc}")

    summary["interrupted"] = summary.get("interrupted") or bool(_INTERRUPTED)
    refresh_status(summary, p)

    print(f"Stage236 status: {summary['status']}")
    print(f"decision: {summary['decision']}")
    print(f"cycle_count_completed: {summary['cycle_count_completed']}")
    print(f"stage234_success_count: {summary['stage234_success_count']}")
    print(f"failed_stage234_count: {summary['failed_stage234_count']}")
    print(f"runtime_queue_rows_last: {summary['runtime_queue_rows_last']}")
    print(f"stop_reason: {summary['stop_reason']}")
    print(f"paste_me: {p['paste']}")
    if summary.get("blockers"):
        print("BLOCKERS:")
        for blocker in summary["blockers"]:
            print(f"- {blocker}")
        return 2
    print("NO_BLOCKERS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
