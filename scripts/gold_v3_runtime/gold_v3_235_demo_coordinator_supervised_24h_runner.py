#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GOLD V3 Stage235 - Demo coordinator supervised 24H runner.

Calls Stage234 once per minute for up to 1440 cycles.
Stage235 itself does not call Discord webhook and does not call mt5.order_send.
This is bounded 24-hour DEMO supervision, not unbounded autotrade.
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


STAGE = "GOLD_V3_235_DEMO_COORDINATOR_SUPERVISED_24H_RUNNER"
DECISION_READY = "STAGE235_DEMO_COORDINATOR_SUPERVISED_24H_RUNNER_READY"
DECISION_BLOCKED = "STAGE235_DEMO_COORDINATOR_SUPERVISED_24H_RUNNER_BLOCKED"
TERMINAL_HASH = "2FA8A7E69CED7DC259B1AD86A247F675"
HARD_MAX_CYCLES = 1440

LEDGER_COLUMNS = [
    "created_at_utc",
    "stage",
    "cycle_index",
    "stage234_return_code",
    "stage234_tail",
    "runtime_queue_rows_seen",
    "cycle_started_utc",
    "cycle_finished_utc",
]

OFF_FLAGS = {
    "stage235_direct_discord_webhook_called": False,
    "stage235_direct_mt5_order_send_called": False,
    "stage235_direct_order_placed": False,
    "position_close_called": False,
    "position_modify_called": False,
    "real_account_allowed": False,
    "final_live_enabled": False,
    "payload_activation_enabled": False,
    "no_signal_order_allowed": False,
    "unbounded_autotrade_allowed": False,
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
    out = files / "FX_OUTPUTS" / "gold_v3" / "235"
    work = out / "demo_coordinator_supervised_24h_runner"
    runtime = files / "FX_OUTPUTS" / "gold_v3" / "runtime"
    return {
        "files": files,
        "out": out,
        "work": work,
        "runtime_queue": runtime / "alert_only_queue.csv",
        "cycle_ledger": work / "stage235_cycle_ledger.csv",
        "summary": work / "stage235_summary.json",
        "paste": out / "paste_me.txt",
        "kill_switch": files / "FX_OUTPUTS" / "gold_v3" / "KILL_SWITCH_STAGE235.txt",
        "stage234_kill_switch": files / "FX_OUTPUTS" / "gold_v3" / "KILL_SWITCH_STAGE234.txt",
        "stage233_kill_switch": files / "FX_OUTPUTS" / "gold_v3" / "KILL_SWITCH_STAGE233.txt",
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
    now = time.time()
    next_minute = int(now // 60) * 60 + 60
    target = next_minute + delay_seconds
    sleep_seconds = max(0, target - now)
    if sleep_seconds > 0:
        time.sleep(sleep_seconds)


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


def validate(summary: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], List[str]]:
    checks: List[Dict[str, Any]] = []

    def add(cid: str, passed: bool, details: str) -> None:
        checks.append({"check_id": cid, "passed": bool(passed), "details": details})

    add("R235001", summary.get("stage234_script_exists") is True, "Stage234 script exists")
    add("R235002", 1 <= int(summary.get("bounded_cycle_count") or 0) <= HARD_MAX_CYCLES, f"bounded_cycle_count={summary.get('bounded_cycle_count')}")
    add("R235003", summary.get("unbounded_autotrade_allowed") is False, "not unbounded")
    add("R235004", summary.get("stage235_direct_discord_webhook_called") is False and summary.get("stage235_direct_mt5_order_send_called") is False, "Stage235 has no direct webhook/order call")
    add("R235005", summary.get("final_live_enabled") is False and summary.get("payload_activation_enabled") is False and summary.get("no_signal_order_allowed") is False, "restricted modes OFF")
    add("R235006", summary.get("kill_switch_present") is False, "Stage235 kill switch absent at final summary")
    add("R235007", summary.get("stage234_kill_switch_present") is False, "Stage234 kill switch absent at final summary")
    add("R235008", summary.get("stage233_kill_switch_present") is False, "Stage233 kill switch absent at final summary")
    add("R235009", int(summary.get("cycle_count_completed") or 0) >= 1, f"cycle_count_completed={summary.get('cycle_count_completed')}")
    add("R235010", int(summary.get("failed_stage234_count") or 0) == 0, f"failed_stage234_count={summary.get('failed_stage234_count')}")

    blockers = [f"{row['check_id']}: {row['details']}" for row in checks if not row["passed"]]
    return checks, blockers


def write_paste_me(path: Path, summary: Dict[str, Any], checks: List[Dict[str, Any]]) -> None:
    lines: List[str] = []
    lines.append("GOLD V3 235 PASTE_ME_DEMO_COORDINATOR_SUPERVISED_24H_RUNNER")
    keys = [
        "step", "status", "ready", "decision", "created_at_utc", "output_dir", "work_dir",
        "stage234_script_exists", "bounded_cycle_count", "hard_max_cycles", "cycle_count_completed",
        "stage234_success_count", "failed_stage234_count", "runtime_queue_exists_last", "runtime_queue_rows_last",
        "kill_switch_present", "stage234_kill_switch_present", "stage233_kill_switch_present", "blocker_count",
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
    lines.append("Stage235 supervised Stage234 once per minute for a bounded 24-hour maximum. Stage235 itself did not call a Discord webhook or mt5.order_send directly. This is DEMO-only bounded supervision, not unbounded final live.")
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
    parser.add_argument("--cycles", type=int, default=HARD_MAX_CYCLES)
    parser.add_argument("--delay-seconds", type=int, default=5)
    parser.add_argument("--no-wait-boundary", action="store_true")
    args = parser.parse_args()

    if args.cycles < 1:
        args.cycles = 1
    if args.cycles > HARD_MAX_CYCLES:
        args.cycles = HARD_MAX_CYCLES

    p = paths()
    script = stage234_script()
    p["out"].mkdir(parents=True, exist_ok=True)
    p["work"].mkdir(parents=True, exist_ok=True)

    summary: Dict[str, Any] = {
        "step": STAGE,
        "created_at_utc": utc_now_iso(),
        "output_dir": str(p["out"]),
        "work_dir": str(p["work"]),
        "stage234_script_exists": script.exists(),
        "bounded_cycle_count": args.cycles,
        "hard_max_cycles": HARD_MAX_CYCLES,
        "cycle_count_completed": 0,
        "stage234_success_count": 0,
        "failed_stage234_count": 0,
        "runtime_queue_exists_last": p["runtime_queue"].exists(),
        "runtime_queue_rows_last": 0,
        "kill_switch_present": p["kill_switch"].exists(),
        "stage234_kill_switch_present": p["stage234_kill_switch"].exists(),
        "stage233_kill_switch_present": p["stage233_kill_switch"].exists(),
        "output_files": {
            "cycle_ledger_csv": str(p["cycle_ledger"]),
            "summary_json": str(p["summary"]),
            "paste_me": str(p["paste"]),
            "stage235_kill_switch": str(p["kill_switch"]),
            "stage234_kill_switch": str(p["stage234_kill_switch"]),
            "stage233_kill_switch": str(p["stage233_kill_switch"]),
        },
    }
    summary.update(OFF_FLAGS)

    rows: List[Dict[str, Any]] = []
    try:
        if not script.exists():
            raise RuntimeError(f"Stage234 script missing: {script}")

        for cycle_index in range(1, args.cycles + 1):
            summary["kill_switch_present"] = p["kill_switch"].exists()
            summary["stage234_kill_switch_present"] = p["stage234_kill_switch"].exists()
            summary["stage233_kill_switch_present"] = p["stage233_kill_switch"].exists()
            if summary["kill_switch_present"] or summary["stage234_kill_switch_present"] or summary["stage233_kill_switch_present"]:
                break

            if not args.no_wait_boundary:
                wait_until_boundary_plus_delay(args.delay_seconds)

            cycle_started = utc_now_iso()
            code, tail = run_stage234_once(script)
            cycle_finished = utc_now_iso()

            queue_rows = read_csv_rows(p["runtime_queue"])
            summary["runtime_queue_exists_last"] = p["runtime_queue"].exists()
            summary["runtime_queue_rows_last"] = len(queue_rows)

            if code == 0:
                summary["stage234_success_count"] += 1
            else:
                summary["failed_stage234_count"] += 1

            rows.append({
                "created_at_utc": utc_now_iso(),
                "stage": STAGE,
                "cycle_index": cycle_index,
                "stage234_return_code": code,
                "stage234_tail": tail.replace("\r", " ").replace("\n", " ")[-1200:],
                "runtime_queue_rows_seen": len(queue_rows),
                "cycle_started_utc": cycle_started,
                "cycle_finished_utc": cycle_finished,
            })
            append_csv_rows(p["cycle_ledger"], rows[-1:], LEDGER_COLUMNS)

            summary["cycle_count_completed"] += 1
            if code != 0:
                break

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

    print(f"Stage235 status: {summary['status']}")
    print(f"decision: {summary['decision']}")
    print(f"cycle_count_completed: {summary['cycle_count_completed']}")
    print(f"stage234_success_count: {summary['stage234_success_count']}")
    print(f"failed_stage234_count: {summary['failed_stage234_count']}")
    print(f"runtime_queue_rows_last: {summary['runtime_queue_rows_last']}")
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
