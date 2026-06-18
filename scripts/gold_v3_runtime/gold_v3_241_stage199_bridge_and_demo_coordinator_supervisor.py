#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GOLD V3 Stage241 - Run Stage240 then Stage234 continuously."""
from __future__ import annotations

import argparse
import csv
import json
import os
import signal
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

STAGE = "GOLD_V3_241_STAGE199_BRIDGE_AND_DEMO_COORDINATOR_SUPERVISOR"
READY_DECISION = "STAGE241_STAGE199_BRIDGE_AND_DEMO_COORDINATOR_SUPERVISOR_READY"
BLOCKED_DECISION = "STAGE241_STAGE199_BRIDGE_AND_DEMO_COORDINATOR_SUPERVISOR_BLOCKED"
TERMINAL_HASH = "2FA8A7E69CED7DC259B1AD86A247F675"

LEDGER_COLUMNS = [
    "created_at_utc", "stage", "cycle_index", "stage240_return_code", "stage234_return_code",
    "runtime_queue_rows_seen", "stage240_tail", "stage234_tail",
]

OFF_FLAGS = {
    "stage241_direct_discord_webhook_called": False,
    "stage241_direct_mt5_order_send_called": False,
    "stage241_direct_order_placed": False,
    "position_close_called": False,
    "position_modify_called": False,
    "real_account_allowed": False,
    "final_live_enabled": False,
    "payload_activation_enabled": False,
    "no_signal_order_allowed": False,
    "source_csv_mutated": False,
    "contract_mutated": False,
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
    base = files / "FX_OUTPUTS" / "gold_v3"
    out = base / "241"
    work = out / "stage199_bridge_and_demo_coordinator_supervisor"
    runtime = base / "runtime"
    return {
        "base": base,
        "out": out,
        "work": work,
        "runtime_queue": runtime / "alert_only_queue.csv",
        "cycle_ledger": work / "stage241_cycle_ledger.csv",
        "summary": work / "stage241_summary.json",
        "paste": out / "paste_me.txt",
        "kill_switch": base / "KILL_SWITCH_STAGE241.txt",
        "stage240_kill_switch": base / "KILL_SWITCH_STAGE240.txt",
        "stage234_kill_switch": base / "KILL_SWITCH_STAGE234.txt",
        "stage233_kill_switch": base / "KILL_SWITCH_STAGE233.txt",
    }


def stage_paths() -> Dict[str, Path]:
    root = repo_root()
    return {
        "stage240": root / "scripts" / "gold_v3_runtime" / "gold_v3_240_stage199_latest_state_bridge.py",
        "stage234": root / "scripts" / "gold_v3_runtime" / "gold_v3_234_discord_and_demo_order_loop_coordinator.py",
    }


def read_csv_rows(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def append_csv(path: Path, rows: List[Dict[str, Any]], columns: List[str]) -> None:
    exists = path.exists()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        if not exists:
            writer.writeheader()
        for row in rows:
            writer.writerow(row)


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def run_cmd(args: List[str], timeout: int) -> Tuple[int, str]:
    result = subprocess.run(args, cwd=str(repo_root()), capture_output=True, text=True, timeout=timeout)
    text = result.stdout or ""
    if result.stderr:
        text += "\n" + result.stderr
    return result.returncode, text[-3000:]


def kill_state(p: Dict[str, Path]) -> Dict[str, bool]:
    return {
        "kill_switch_present": p["kill_switch"].exists(),
        "stage240_kill_switch_present": p["stage240_kill_switch"].exists(),
        "stage234_kill_switch_present": p["stage234_kill_switch"].exists(),
        "stage233_kill_switch_present": p["stage233_kill_switch"].exists(),
    }


def stop_reason(summary: Dict[str, Any]) -> str:
    if summary.get("interrupted"):
        return "INTERRUPTED"
    for key in ["kill_switch_present", "stage240_kill_switch_present", "stage234_kill_switch_present", "stage233_kill_switch_present"]:
        if summary.get(key):
            return key.upper()
    if int(summary.get("failed_stage240_count") or 0) > 0:
        return "STAGE240_FAILURE"
    if int(summary.get("failed_stage234_count") or 0) > 0:
        return "STAGE234_FAILURE"
    return "RUNNING_OR_NOT_STARTED"


def validate(summary: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], List[str]]:
    checks: List[Dict[str, Any]] = []
    def add(cid: str, passed: bool, details: str) -> None:
        checks.append({"check_id": cid, "passed": bool(passed), "details": details})
    add("S241001", summary.get("stage240_script_exists") is True, "Stage240 bridge exists")
    add("S241002", summary.get("stage234_script_exists") is True, "Stage234 coordinator exists")
    add("S241003", int(summary.get("failed_stage240_count") or 0) == 0, f"failed_stage240_count={summary.get('failed_stage240_count')}")
    add("S241004", int(summary.get("failed_stage234_count") or 0) == 0, f"failed_stage234_count={summary.get('failed_stage234_count')}")
    add("S241005", all(summary.get(k) is False for k in OFF_FLAGS.keys()), "restricted flags OFF")
    blockers = [f"{c['check_id']}: {c['details']}" for c in checks if not c["passed"]]
    return checks, blockers


def write_paste(path: Path, summary: Dict[str, Any], checks: List[Dict[str, Any]]) -> None:
    lines = ["GOLD V3 241 PASTE_ME_STAGE199_BRIDGE_AND_DEMO_COORDINATOR_SUPERVISOR"]
    keys = [
        "step", "status", "ready", "decision", "created_at_utc", "updated_at_utc", "continuous_mode",
        "cycle_count_completed", "stage240_success_count", "stage234_success_count", "failed_stage240_count",
        "failed_stage234_count", "runtime_queue_exists_last", "runtime_queue_rows_last", "interrupted", "stop_reason",
        "kill_switch_present", "stage240_kill_switch_present", "stage234_kill_switch_present", "stage233_kill_switch_present", "blocker_count",
    ] + list(OFF_FLAGS.keys())
    for k in keys:
        lines.append(f"{k}: {summary.get(k)}")
    lines.append("")
    lines.append("OUTPUT_FILES")
    for k, v in summary.get("output_files", {}).items():
        lines.append(f"{k}: {v}")
    lines.append("")
    lines.append("VALIDATION_CHECKS")
    for c in checks:
        lines.append(f"{c['check_id']} | passed={c['passed']} | {c['details']}")
    lines.append("")
    lines.append("INTERPRETATION")
    lines.append("Stage241 runs Stage240 first, then Stage234. Stage240 updates latest_state using Stage199 ABC PRIMARY + SCALP SECONDARY logic before Stage227 queue refresh.")
    lines.append("")
    lines.append("BLOCKERS")
    if summary.get("blockers"):
        lines.extend(summary["blockers"])
    else:
        lines.append("NO_BLOCKERS")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def refresh(summary: Dict[str, Any], p: Dict[str, Path]) -> None:
    summary.update(kill_state(p))
    summary["runtime_queue_exists_last"] = p["runtime_queue"].exists()
    summary["runtime_queue_rows_last"] = len(read_csv_rows(p["runtime_queue"]))
    summary["updated_at_utc"] = utc_now_iso()
    summary["stop_reason"] = stop_reason(summary)
    checks, blockers = validate(summary)
    summary["validation_checks"] = checks
    summary["blockers"] = blockers
    summary["blocker_count"] = len(blockers)
    summary["status"] = "READY" if not blockers else "BLOCKED"
    summary["ready"] = not blockers
    summary["decision"] = READY_DECISION if not blockers else BLOCKED_DECISION
    write_json(p["summary"], summary)
    write_paste(p["paste"], summary, checks)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cycles", type=int, default=0, help="0 means continuous")
    ap.add_argument("--mt5-files-dir", default="")
    args = ap.parse_args()
    if args.cycles < 0:
        args.cycles = 0
    p = paths()
    sp = stage_paths()
    p["out"].mkdir(parents=True, exist_ok=True)
    p["work"].mkdir(parents=True, exist_ok=True)
    summary: Dict[str, Any] = {
        "step": STAGE,
        "created_at_utc": utc_now_iso(),
        "updated_at_utc": utc_now_iso(),
        "continuous_mode": args.cycles == 0,
        "cycle_count_completed": 0,
        "stage240_script_exists": sp["stage240"].exists(),
        "stage234_script_exists": sp["stage234"].exists(),
        "stage240_success_count": 0,
        "stage234_success_count": 0,
        "failed_stage240_count": 0,
        "failed_stage234_count": 0,
        "runtime_queue_exists_last": p["runtime_queue"].exists(),
        "runtime_queue_rows_last": len(read_csv_rows(p["runtime_queue"])),
        "interrupted": False,
        "stop_reason": "RUNNING_OR_NOT_STARTED",
        "output_files": {
            "cycle_ledger_csv": str(p["cycle_ledger"]),
            "summary_json": str(p["summary"]),
            "paste_me": str(p["paste"]),
            "kill_switch_stage241": str(p["kill_switch"]),
        },
    }
    summary.update(OFF_FLAGS)
    refresh(summary, p)
    if not summary["stage240_script_exists"] or not summary["stage234_script_exists"]:
        return 2
    try:
        cycle = 0
        while True:
            summary["interrupted"] = bool(_INTERRUPTED)
            summary.update(kill_state(p))
            if _INTERRUPTED or any(summary.get(k) for k in ["kill_switch_present", "stage240_kill_switch_present", "stage234_kill_switch_present", "stage233_kill_switch_present"]):
                break
            if args.cycles > 0 and cycle >= args.cycles:
                break
            cycle += 1
            stage240_args = [sys.executable, str(sp["stage240"])]
            if args.mt5_files_dir:
                stage240_args += ["--mt5-files-dir", args.mt5_files_dir]
            c240, t240 = run_cmd(stage240_args, timeout=300)
            if c240 == 0:
                summary["stage240_success_count"] += 1
            else:
                summary["failed_stage240_count"] += 1
            c234, t234 = 999, "SKIPPED_STAGE240_FAILED"
            if c240 == 0:
                c234, t234 = run_cmd([sys.executable, str(sp["stage234"]), "--cycles", "1"], timeout=420)
                if c234 == 0:
                    summary["stage234_success_count"] += 1
                else:
                    summary["failed_stage234_count"] += 1
            summary["cycle_count_completed"] = cycle
            qrows = read_csv_rows(p["runtime_queue"])
            append_csv(p["cycle_ledger"], [{
                "created_at_utc": utc_now_iso(),
                "stage": STAGE,
                "cycle_index": cycle,
                "stage240_return_code": c240,
                "stage234_return_code": c234,
                "runtime_queue_rows_seen": len(qrows),
                "stage240_tail": t240.replace("\r", " ").replace("\n", " ")[-800:],
                "stage234_tail": t234.replace("\r", " ").replace("\n", " ")[-800:],
            }], LEDGER_COLUMNS)
            refresh(summary, p)
            if c240 != 0 or c234 != 0:
                break
    except KeyboardInterrupt:
        summary["interrupted"] = True
    except Exception as exc:
        summary.setdefault("blockers", [])
        summary["blockers"].append(f"EXCEPTION: {type(exc).__name__}: {exc}")
    summary["interrupted"] = summary.get("interrupted") or bool(_INTERRUPTED)
    refresh(summary, p)
    print(f"Stage241 status: {summary['status']}")
    print(f"decision: {summary['decision']}")
    print(f"cycle_count_completed: {summary['cycle_count_completed']}")
    print(f"stage240_success_count: {summary['stage240_success_count']}")
    print(f"stage234_success_count: {summary['stage234_success_count']}")
    print(f"runtime_queue_rows_last: {summary['runtime_queue_rows_last']}")
    print(f"paste_me: {p['paste']}")
    return 0 if not summary.get("blockers") else 2


if __name__ == "__main__":
    raise SystemExit(main())
