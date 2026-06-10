#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GOLD V3 72 live CSV update monitor audit-only.

Watches goldsharp_m15.csv latest closed row. When the latest timestamp changes,
runs Stage69 -> Stage70 -> Stage71 Python scripts directly and writes a stable
monitor snapshot.

No MT5 orders, no Discord, no AI API, no live hook, no final signal.
"""
from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

STEP = "GOLD_V3_72_LIVE_CSV_UPDATE_MONITOR_AUDIT_ONLY"
READY_STATUS = "GOLD_V3_72_LIVE_CSV_UPDATE_MONITOR_READY_AUDIT_ONLY"
BLOCKED_STATUS = "GOLD_V3_72_LIVE_CSV_UPDATE_MONITOR_BLOCKED_AUDIT_ONLY"
STAGE71_READY = "GOLD_V3_71_LIVE_CSV_SIGNAL_AUDIT_PIPELINE_PACKAGE_READY_AUDIT_ONLY"
CSV_CONTRACT = "open/in-progress candles are not written to CSV"
POOL_POLICY = "poolから外さない。rolling health gateに判断させる。"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def ok(check_id: str, passed: bool, observed: Any, expected: Any, severity: str = "BLOCKER") -> dict[str, Any]:
    return {"check_id": check_id, "result": "PASS" if passed else "FAIL", "observed": observed, "expected": expected, "severity": severity}


def blocker(blocker_id: str, artifact: str, reason: str, detail: Any = "") -> dict[str, Any]:
    return {"blocker_id": blocker_id, "artifact": artifact, "reason": reason, "detail": detail, "severity": "BLOCKER"}


def find_files_dir() -> Path:
    root = Path(__file__).resolve().parents[2]
    candidates = [Path.cwd(), Path.cwd() / "Files", root, root / "Files", root.parent, root.parent / "Files", root.parent.parent]
    for d in candidates:
        d = d.expanduser().resolve()
        if (d / "goldsharp_m15.csv").exists():
            return d
    raise FileNotFoundError("Could not locate Files directory with goldsharp_m15.csv")


def read_latest_m15_time(path: Path) -> str:
    df = pd.read_csv(path, encoding="utf-8-sig", usecols=lambda c: str(c).strip().lower() == "time")
    if df.empty:
        raise ValueError(f"empty CSV: {path}")
    col = df.columns[0]
    t = pd.to_datetime(df[col], errors="coerce").dropna()
    if t.empty:
        raise ValueError(f"no valid time values: {path}")
    return str(t.max())


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def append_event(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    exists = path.exists()
    fields = ["created_at_utc", "event", "latest_m15_time", "status", "detail"]
    with path.open("a", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        if not exists:
            w.writeheader()
        w.writerow({k: row.get(k, "") for k in fields})


def run_stage(script: Path, args: list[str], cwd: Path) -> tuple[int, str]:
    cmd = [sys.executable, str(script)] + args
    p = subprocess.run(cmd, cwd=str(cwd), text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return int(p.returncode), p.stdout[-4000:]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=STEP)
    p.add_argument("--candle-dir", default="")
    p.add_argument("--output-dir", default="")
    p.add_argument("--poll-seconds", type=int, default=30)
    p.add_argument("--once", action="store_true", help="run one monitor check and exit")
    p.add_argument("--no-startup-run", action="store_true", help="do not run pipeline on startup unless timestamp changes")
    return p.parse_args()


def write_common_outputs(out: Path, status: str, val: list[dict[str, Any]], blockers: list[dict[str, Any]], summary: dict[str, Any]) -> None:
    out.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(blockers).to_csv(out / "gold_v3_72_blocker_matrix.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(val).to_csv(out / "gold_v3_72_validation_matrix.csv", index=False, encoding="utf-8-sig")
    summary = dict(summary)
    summary["status"] = status
    summary["created_at_utc"] = utc_now()
    (out / "gold_v3_72_live_csv_update_monitor_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    paste = []
    paste.append("GOLD V3 72 PASTE_ME_LIVE_CSV_UPDATE_MONITOR_SUMMARY")
    paste.append(f"status: {status}")
    paste.append("live_csv_update_monitor_ready: " + str(status == READY_STATUS).lower())
    paste.append("live_ready: false")
    paste.append("contract_mutated: false")
    paste.append("manual_candidate_demotion_or_removal: false")
    paste.append("open_asof_allowed: false")
    paste.append("csv_contract: " + CSV_CONTRACT)
    paste.append("csv_open_bar_exclusion_required: false")
    paste.append("safety: audit_only=true, live_allowed=false, mt5=false, discord=false, ai_api=false, final_signal=false")
    paste.append("pool_policy: " + POOL_POLICY)
    paste.append(f"latest_m15_time: {summary.get('latest_m15_time','')}")
    paste.append(f"last_pipeline_run_time: {summary.get('last_pipeline_run_time','')}")
    paste.append(f"last_pipeline_returncode: {summary.get('last_pipeline_returncode','')}")
    paste.append(f"stage71_snapshot_m15_time: {summary.get('stage71_snapshot_m15_time','')}")
    paste.append(f"stage71_decision: {summary.get('stage71_decision','')}")
    paste.append(f"stage71_no_signal_reason: {summary.get('stage71_no_signal_reason','')}")
    paste.append(f"stage71_latest_condition_candidate_rows: {summary.get('stage71_latest_condition_candidate_rows','')}")
    paste.append(f"blocker_count: {len(blockers)}")
    paste.append("")
    paste.append("BLOCKERS")
    paste.append(pd.DataFrame(blockers).to_string(index=False) if blockers else "NO_BLOCKERS")
    paste.append("")
    paste.append("VALIDATION")
    paste.append(pd.DataFrame(val).to_string(index=False))
    paste.append("")
    paste.append("OUTPUTS")
    paste.append("gold_v3_72_monitor_state.json")
    paste.append("gold_v3_72_monitor_event_log.csv")
    paste.append("gold_v3_72_latest_pipeline_snapshot.csv")
    paste.append("gold_v3_72_latest_pipeline_snapshot.json")
    paste.append("gold_v3_72_blocker_matrix.csv")
    paste.append("gold_v3_72_validation_matrix.csv")
    paste.append("gold_v3_72_live_csv_update_monitor_summary.json")
    (out / "gold_v3_72_PASTE_ME_LIVE_CSV_UPDATE_MONITOR_SUMMARY.txt").write_text("\n".join(paste) + "\n", encoding="utf-8")
    report = f"""# GOLD V3 72 live CSV update monitor audit-only report

Status: `{status}`

- latest_m15_time: `{summary.get('latest_m15_time','')}`
- stage71_snapshot_m15_time: `{summary.get('stage71_snapshot_m15_time','')}`
- last_pipeline_run_time: `{summary.get('last_pipeline_run_time','')}`
- stage71_decision: `{summary.get('stage71_decision','')}`
- stage71_no_signal_reason: `{summary.get('stage71_no_signal_reason','')}`
- blocker_count: `{len(blockers)}`

Audit-only. No MT5, Discord, AI API, live hook, live evaluator, or final signal.
"""
    (out / "GOLD_V3_72_REPORT.md").write_text(report, encoding="utf-8")


def load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return read_json(path)
    except Exception:
        return {}


def main() -> int:
    a = parse_args()
    cdir = Path(a.candle_dir).expanduser().resolve() if a.candle_dir else find_files_dir()
    repo_root = Path(__file__).resolve().parents[2]
    base_out = cdir / "FX_OUTPUTS" / "gold_v3"
    out = Path(a.output_dir).expanduser().resolve() if a.output_dir else base_out / "72_live_csv_update_monitor_audit_only"
    out.mkdir(parents=True, exist_ok=True)
    event_log = out / "gold_v3_72_monitor_event_log.csv"
    state_path = out / "gold_v3_72_monitor_state.json"
    p_m15 = cdir / "goldsharp_m15.csv"
    scripts = [
        repo_root / "scripts" / "gold_v3_runtime" / "gold_v3_69_live_csv_condition_detector_audit.py",
        repo_root / "scripts" / "gold_v3_runtime" / "gold_v3_70_live_csv_signal_decision_preview_audit.py",
        repo_root / "scripts" / "gold_v3_runtime" / "gold_v3_71_live_csv_signal_audit_pipeline_package.py",
    ]
    state = load_state(state_path)
    last_seen = str(state.get("latest_m15_time", ""))
    persisted_last_run_time = str(state.get("last_pipeline_run_time", ""))
    persisted_last_returncode = str(state.get("last_pipeline_returncode", ""))

    first = True
    while True:
        val: list[dict[str, Any]] = []
        blockers: list[dict[str, Any]] = []
        val.append(ok("goldsharp_m15_present", p_m15.exists(), str(p_m15), "exists"))
        for s in scripts:
            val.append(ok(f"script_present_{s.name}", s.exists(), str(s), "exists"))
        latest = ""
        current_run_rc = ""
        current_run_time = ""
        stage71_decision = ""
        stage71_reason = ""
        stage71_rows = ""
        stage71_snapshot_time = ""
        try:
            latest = read_latest_m15_time(p_m15)
            val.append(ok("latest_m15_time_read", True, latest, "readable"))
        except Exception as e:
            val.append(ok("latest_m15_time_read", False, repr(e), "readable"))
            blockers.append(blocker("latest_m15_time_read_failed", str(p_m15), "LATEST_M15_TIME_READ_FAILED", repr(e)))
        missing_scripts = [str(s) for s in scripts if not s.exists()]
        if missing_scripts:
            blockers.append(blocker("required_script_missing", str(repo_root), "REQUIRED_SCRIPT_MISSING", missing_scripts))
        should_run = bool(latest and not blockers and ((first and not a.no_startup_run) or latest != last_seen))
        if should_run:
            append_event(event_log, {"created_at_utc": utc_now(), "event": "PIPELINE_START", "latest_m15_time": latest, "status": "RUNNING", "detail": "Stage69->70->71"})
            current_run_time = utc_now()
            for script in scripts:
                rci, outtxt = run_stage(script, ["--candle-dir", str(cdir)], repo_root)
                current_run_rc = str(rci)
                append_event(event_log, {"created_at_utc": utc_now(), "event": script.name, "latest_m15_time": latest, "status": "OK" if rci == 0 else "FAILED", "detail": outtxt.replace("\r", " ").replace("\n", " ")[-1000:]})
                if rci != 0:
                    blockers.append(blocker("pipeline_stage_failed", str(script), "PIPELINE_STAGE_RETURNED_NONZERO", {"returncode": rci, "output_tail": outtxt[-2000:]}))
                    break
            if not blockers:
                last_seen = latest
                persisted_last_run_time = current_run_time
                persisted_last_returncode = current_run_rc or "0"
                append_event(event_log, {"created_at_utc": utc_now(), "event": "PIPELINE_DONE", "latest_m15_time": latest, "status": "OK", "detail": "Stage69->70->71 completed"})
        else:
            append_event(event_log, {"created_at_utc": utc_now(), "event": "HEARTBEAT", "latest_m15_time": latest, "status": "NO_CHANGE" if latest == last_seen else "BLOCKED", "detail": "no pipeline run"})

        p71 = base_out / "71_live_csv_signal_audit_pipeline_package_audit_only" / "gold_v3_71_live_csv_signal_audit_pipeline_package_summary.json"
        p71_snap_csv = base_out / "71_live_csv_signal_audit_pipeline_package_audit_only" / "gold_v3_71_latest_signal_snapshot.csv"
        p71_snap_json = base_out / "71_live_csv_signal_audit_pipeline_package_audit_only" / "gold_v3_71_latest_signal_snapshot.json"
        if p71.exists():
            j71 = read_json(p71)
            stage71_decision = str(j71.get("decision", ""))
            stage71_reason = str(j71.get("no_signal_reason", ""))
            stage71_rows = str(j71.get("latest_condition_candidate_rows", ""))
            stage71_snapshot_time = str(j71.get("latest_closed_m15_time", ""))
            val.append(ok("stage71_summary_present", True, str(p71), "exists"))
            val.append(ok("stage71_ready", j71.get("status") == STAGE71_READY, j71.get("status"), STAGE71_READY))
        else:
            val.append(ok("stage71_summary_present", False, str(p71), "exists"))
            if should_run:
                blockers.append(blocker("stage71_summary_missing_after_pipeline", str(p71), "STAGE71_SUMMARY_MISSING_AFTER_PIPELINE"))
        if p71_snap_csv.exists():
            try:
                snap_df = pd.read_csv(p71_snap_csv, encoding="utf-8-sig")
                if not snap_df.empty and "latest_closed_m15_time" in snap_df.columns:
                    stage71_snapshot_time = str(snap_df["latest_closed_m15_time"].iloc[0])
                snap_df.to_csv(out / "gold_v3_72_latest_pipeline_snapshot.csv", index=False, encoding="utf-8-sig")
                if p71_snap_json.exists():
                    (out / "gold_v3_72_latest_pipeline_snapshot.json").write_text(p71_snap_json.read_text(encoding="utf-8"), encoding="utf-8")
                else:
                    (out / "gold_v3_72_latest_pipeline_snapshot.json").write_text(json.dumps(snap_df.iloc[0].to_dict(), ensure_ascii=False, indent=2, default=str), encoding="utf-8")
                val.append(ok("stage71_snapshot_copied", True, str(p71_snap_csv), "copied"))
            except Exception as e:
                val.append(ok("stage71_snapshot_copied", False, repr(e), "copied"))
                blockers.append(blocker("stage71_snapshot_copy_failed", str(p71_snap_csv), "SNAPSHOT_COPY_FAILED", repr(e)))
        elif should_run:
            val.append(ok("stage71_snapshot_present", False, str(p71_snap_csv), "exists"))
            blockers.append(blocker("stage71_snapshot_missing_after_pipeline", str(p71_snap_csv), "STAGE71_SNAPSHOT_MISSING_AFTER_PIPELINE"))
        snapshot_fresh = bool(latest and stage71_snapshot_time and str(latest) == str(stage71_snapshot_time))
        val.append(ok("stage71_snapshot_time_matches_latest_m15", snapshot_fresh, stage71_snapshot_time, latest))
        if not snapshot_fresh:
            blockers.append(blocker("stage71_snapshot_stale", str(p71_snap_csv), "STAGE71_SNAPSHOT_TIME_DOES_NOT_MATCH_LATEST_M15", {"latest_m15_time": latest, "stage71_snapshot_m15_time": stage71_snapshot_time}))
        val.append(ok("last_pipeline_run_time_recorded", bool(persisted_last_run_time), persisted_last_run_time, "nonempty"))
        val.append(ok("last_pipeline_returncode_zero", str(persisted_last_returncode) == "0", persisted_last_returncode, "0"))
        val.append(ok("latest_closed_time_present", latest != "", latest, "nonempty"))
        val.append(ok("csv_open_bar_exclusion_required_false", True, False, False))
        val.append(ok("live_flags_all_false", True, "all_false", "all_false"))
        failed = [v for v in val if v.get("result") != "PASS"]
        status = READY_STATUS if not failed and not blockers else BLOCKED_STATUS
        state = {
            "latest_m15_time": latest,
            "stage71_snapshot_m15_time": stage71_snapshot_time,
            "last_pipeline_run_time": persisted_last_run_time,
            "last_pipeline_returncode": persisted_last_returncode,
            "updated_at_utc": utc_now(),
            "status": status,
        }
        state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
        summary = {
            "step": STEP,
            "candle_dir": str(cdir),
            "output_dir": str(out),
            "audit_only": True,
            "live_allowed": False,
            "mt5_execution_enabled": False,
            "mt5_bat_created": False,
            "discord_live_enabled": False,
            "ai_api_called": False,
            "signals_generated": False,
            "final_signal_enabled": False,
            "contract_mutated": False,
            "manual_candidate_demotion_or_removal": False,
            "open_asof_allowed": False,
            "csv_contract": CSV_CONTRACT,
            "csv_open_bar_exclusion_required": False,
            "live_ready": False,
            "live_csv_update_monitor_ready": status == READY_STATUS,
            "pool_policy": POOL_POLICY,
            "latest_m15_time": latest,
            "stage71_snapshot_m15_time": stage71_snapshot_time,
            "last_pipeline_run_time": persisted_last_run_time,
            "last_pipeline_returncode": persisted_last_returncode,
            "stage71_decision": stage71_decision,
            "stage71_no_signal_reason": stage71_reason,
            "stage71_latest_condition_candidate_rows": stage71_rows,
            "poll_seconds": int(a.poll_seconds),
            "validation_failure_count": len(failed),
            "blocker_count": len(blockers),
        }
        write_common_outputs(out, status, val, blockers, summary)
        print(f"[{utc_now()}] {status} latest={latest} snapshot={stage71_snapshot_time} decision={stage71_decision} reason={stage71_reason} last_run={persisted_last_run_time} blockers={len(blockers)}")
        if a.once:
            return 0 if status == READY_STATUS else 1
        first = False
        time.sleep(max(5, int(a.poll_seconds)))


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\n[STOP] GOLD V3 72 monitor stopped by user.")
        raise SystemExit(0)
