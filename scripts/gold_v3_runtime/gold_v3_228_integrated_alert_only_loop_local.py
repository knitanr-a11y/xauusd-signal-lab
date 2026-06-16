#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GOLD V3 Stage228 - Integrated Alert-Only Loop LOCAL

This wrapper runs:
1. Stage227 runtime queue refresh
2. Stage226 local loop once, using the refreshed runtime queue

Stage226 handles the minute+5 seconds timing.
Stage228 itself does not implement webhook logic or order logic.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


STAGE = "GOLD_V3_228_QUEUE_REFRESH_AND_ALERT_ONLY_LOOP_INTEGRATED_LOCAL"
DECISION_READY = "STAGE228_QUEUE_REFRESH_AND_ALERT_ONLY_LOOP_READY_LOCAL"
DECISION_BLOCKED = "STAGE228_QUEUE_REFRESH_AND_ALERT_ONLY_LOOP_BLOCKED_LOCAL"
TERMINAL_HASH = "2FA8A7E69CED7DC259B1AD86A247F675"

RUNTIME_COLUMNS = [
    "cycle_id",
    "stage227_return_code",
    "stage226_return_code",
    "runtime_queue_csv",
    "created_stage",
    "created_at_utc",
]

OFF_FLAGS: Dict[str, bool] = {
    "mt5_order_enabled": False,
    "real_account_enabled": False,
    "actual_order_import_enabled": False,
    "payload_activation_enabled": False,
    "live_hook_enabled": False,
    "final_live_enabled": False,
    "autotrade_enabled": False,
    "no_signal_notify": False,
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


def default_mql5_files_dir() -> Path:
    env_value = os.environ.get("GOLD_V3_MQL5_FILES")
    if env_value:
        return Path(env_value).expanduser().resolve()

    appdata = os.environ.get("APPDATA")
    if appdata:
        return Path(
            appdata,
            "MetaQuotes",
            "Terminal",
            TERMINAL_HASH,
            "MQL5",
            "Files",
        ).resolve()

    return (Path.cwd() / "_GOLD_V3_LOCAL_MQL5_FILES").resolve()


def paths() -> Dict[str, Path]:
    repo_root = Path(__file__).resolve().parents[2]
    files = default_mql5_files_dir()
    out = files / "FX_OUTPUTS" / "gold_v3" / "228"
    work = out / "integrated_alert_only_loop"
    runtime_queue = files / "FX_OUTPUTS" / "gold_v3" / "runtime" / "alert_only_queue.csv"

    return {
        "repo_root": repo_root,
        "out": out,
        "work": work,
        "runtime_queue": runtime_queue,
        "stage227_script": repo_root / "scripts" / "gold_v3_runtime" / "gold_v3_227_alert_only_runtime_queue_binding_audit.py",
        "stage226_script": repo_root / "scripts" / "gold_v3_runtime" / "gold_v3_226_demo_discord_alert_only_loop_restart_local.py",
        "runtime_log": work / "integrated_runtime_log.csv",
        "status_json": work / "integrated_status.json",
        "paste_me": out / "paste_me.txt",
    }


def append_csv(path: Path, row: Dict[str, Any], columns: List[str]) -> None:
    exists = path.exists()
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        if not exists:
            writer.writeheader()
        writer.writerow(row)


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def run_cmd(repo_root: Path, args: List[str]) -> int:
    result = subprocess.run(args, cwd=str(repo_root))
    return int(result.returncode)


def validate(status: Dict[str, Any]) -> tuple[List[Dict[str, Any]], List[str]]:
    checks: List[Dict[str, Any]] = []

    def add(cid: str, passed: bool, details: str) -> None:
        checks.append({"check_id": cid, "passed": bool(passed), "details": details})

    add("W228001", status.get("stage227_script_exists") is True, status.get("stage227_script"))
    add("W228002", status.get("stage226_script_exists") is True, status.get("stage226_script"))
    add("W228003", status.get("runtime_queue_path_set") is True, status.get("runtime_queue"))
    add("W228004", status.get("cycles_completed", 0) >= 1, f"cycles_completed={status.get('cycles_completed')}")
    add("W228005", status.get("last_stage227_return_code") == 0, f"stage227_rc={status.get('last_stage227_return_code')}")
    add("W228006", status.get("last_stage226_return_code") == 0, f"stage226_rc={status.get('last_stage226_return_code')}")
    add("W228007", status.get("csv_latest_row_contract") == "CLOSED" and status.get("open_asof_allowed") is False, "CSV latest row CLOSED; no open/as-of")
    add("W228008", status.get("timestamp_basis") == "MT5_CSV", "MT5/CSV timestamp basis")
    add("W228009", all(status.get(k) is False for k in OFF_FLAGS.keys()), "restricted flags remain OFF")

    blockers = [f"{row['check_id']}: {row['details']}" for row in checks if not row["passed"]]
    return checks, blockers


def write_paste_me(path: Path, status: Dict[str, Any], checks: List[Dict[str, Any]]) -> None:
    lines: List[str] = []
    lines.append("GOLD V3 228 PASTE_ME_INTEGRATED_ALERT_ONLY_LOOP_WRAPPER_LOCAL")

    for key in [
        "step",
        "status",
        "ready",
        "decision",
        "created_at_utc",
        "updated_at_utc",
        "output_dir",
        "work_dir",
        "cycles_completed",
        "last_stage227_return_code",
        "last_stage226_return_code",
        "runtime_queue",
        "stage227_script_exists",
        "stage226_script_exists",
        "blocker_count",
    ] + list(OFF_FLAGS.keys()):
        lines.append(f"{key}: {status.get(key)}")

    lines.append("")
    lines.append("OUTPUT_FILES")
    for k, v in status.get("output_files", {}).items():
        lines.append(f"{k}: {v}")

    lines.append("")
    lines.append("VALIDATION_CHECKS")
    for check in checks:
        lines.append(f"{check['check_id']} | passed={check['passed']} | {check['details']}")

    lines.append("")
    lines.append("INTERPRETATION")
    lines.append("Stage228 wrapper ran Stage227 queue refresh and Stage226 local loop once per cycle.")
    lines.append("Stage228 itself does not implement delivery logic or order actions.")

    lines.append("")
    lines.append("BLOCKERS")
    if status.get("blockers"):
        lines.extend(status["blockers"])
    else:
        lines.append("NO_BLOCKERS")

    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true", help="Run one integrated wrapper cycle and exit.")
    parser.add_argument("--max-cycles", type=int, default=0, help="0 means run until stopped.")
    args = parser.parse_args()

    p = paths()
    p["out"].mkdir(parents=True, exist_ok=True)
    p["work"].mkdir(parents=True, exist_ok=True)

    status: Dict[str, Any] = {
        "step": STAGE,
        "created_at_utc": utc_now_iso(),
        "updated_at_utc": utc_now_iso(),
        "output_dir": str(p["out"]),
        "work_dir": str(p["work"]),
        "runtime_queue": str(p["runtime_queue"]),
        "runtime_queue_path_set": True,
        "stage227_script": str(p["stage227_script"]),
        "stage226_script": str(p["stage226_script"]),
        "stage227_script_exists": p["stage227_script"].exists(),
        "stage226_script_exists": p["stage226_script"].exists(),
        "cycles_completed": 0,
        "last_stage227_return_code": None,
        "last_stage226_return_code": None,
        "csv_latest_row_contract": "CLOSED",
        "timestamp_basis": "MT5_CSV",
        "output_files": {
            "integrated_runtime_log_csv": str(p["runtime_log"]),
            "integrated_status_json": str(p["status_json"]),
        },
    }
    status.update(OFF_FLAGS)

    cycle = 0

    while True:
        cycle += 1
        created_at = utc_now_iso()

        rc227 = run_cmd(
            p["repo_root"],
            [sys.executable, str(p["stage227_script"])],
        )

        rc226 = run_cmd(
            p["repo_root"],
            [
                sys.executable,
                str(p["stage226_script"]),
                "--once",
                "--queue-csv",
                str(p["runtime_queue"]),
            ],
        )

        status["cycles_completed"] = cycle
        status["last_stage227_return_code"] = rc227
        status["last_stage226_return_code"] = rc226
        status["updated_at_utc"] = utc_now_iso()

        append_csv(
            p["runtime_log"],
            {
                "cycle_id": cycle,
                "stage227_return_code": rc227,
                "stage226_return_code": rc226,
                "runtime_queue_csv": str(p["runtime_queue"]),
                "created_stage": STAGE,
                "created_at_utc": created_at,
            },
            RUNTIME_COLUMNS,
        )

        checks, blockers = validate(status)
        status["validation_checks"] = checks
        status["blockers"] = blockers
        status["blocker_count"] = len(blockers)
        status["status"] = "READY" if not blockers else "BLOCKED"
        status["ready"] = not blockers
        status["decision"] = DECISION_READY if not blockers else DECISION_BLOCKED

        write_json(p["status_json"], status)
        write_paste_me(p["paste_me"], status, checks)

        print(f"[Stage228] cycle={cycle} stage227_rc={rc227} stage226_rc={rc226}")
        print(f"[Stage228] paste_me: {p['paste_me']}")

        if blockers:
            return 2

        if args.once:
            return 0

        if args.max_cycles > 0 and cycle >= args.max_cycles:
            return 0


if __name__ == "__main__":
    raise SystemExit(main())