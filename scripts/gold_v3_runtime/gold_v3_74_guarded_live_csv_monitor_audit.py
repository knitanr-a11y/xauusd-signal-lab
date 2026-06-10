#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GOLD V3 74 guarded live CSV monitor audit-only.

Watches goldsharp_m15.csv latest closed row. When the latest timestamp changes,
runs Stage69 -> Stage70 -> Stage71 -> Stage73 Python scripts directly and writes
a stable guarded monitor snapshot.

Critical: Stage73 is called with --stage71-dir so it consumes the freshly generated
Stage71 latest closed snapshot, not any older Stage72 wrapper snapshot.

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

STEP = "GOLD_V3_74_GUARDED_LIVE_CSV_MONITOR_AUDIT_ONLY"
READY_STATUS = "GOLD_V3_74_GUARDED_LIVE_CSV_MONITOR_READY_AUDIT_ONLY"
BLOCKED_STATUS = "GOLD_V3_74_GUARDED_LIVE_CSV_MONITOR_BLOCKED_AUDIT_ONLY"
STAGE73_READY = "GOLD_V3_73_SIGNAL_EMISSION_GUARD_READY_AUDIT_ONLY"
CSV_CONTRACT = "open/in-progress candles are not written to CSV"
POOL_POLICY = "poolから外さない。rolling health gateに判断させる。"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def ok(check_id: str, passed: bool, observed: Any, expected: Any, severity: str = "BLOCKER") -> dict[str, Any]:
    return {"check_id": check_id, "result": "PASS" if passed else "FAIL", "observed": observed, "expected": expected, "severity": severity}


def blocker(blocker_id: str, artifact: str, reason: str, detail: Any = "") -> dict[str, Any]:
    return {"blocker_id": blocker_id, "artifact": artifact, "reason": reason, "detail": detail, "severity": "BLOCKER"}


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def find_files_dir() -> Path:
    root = Path(__file__).resolve().parents[2]
    for d in [Path.cwd(), Path.cwd()/"Files", root, root/"Files", root.parent, root.parent/"Files", root.parent.parent]:
        d = d.expanduser().resolve()
        if (d/"goldsharp_m15.csv").exists():
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


def append_event(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["created_at_utc", "event", "latest_m15_time", "status", "detail"]
    exists = path.exists()
    with path.open("a", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        if not exists:
            w.writeheader()
        w.writerow({k: row.get(k, "") for k in fields})


def run_script(script: Path, args: list[str], cwd: Path) -> tuple[int, str]:
    p = subprocess.run([sys.executable, str(script)] + args, cwd=str(cwd), text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return int(p.returncode), p.stdout[-4000:]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=STEP)
    p.add_argument("--candle-dir", default="")
    p.add_argument("--output-dir", default="")
    p.add_argument("--poll-seconds", type=int, default=30)
    p.add_argument("--once", action="store_true")
    p.add_argument("--no-startup-run", action="store_true")
    return p.parse_args()


def write_outputs(out: Path, status: str, val: list[dict[str, Any]], blockers: list[dict[str, Any]], summary: dict[str, Any]) -> None:
    out.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(blockers).to_csv(out/"gold_v3_74_blocker_matrix.csv", index=False, encoding="utf-8-sig")
    val_df = pd.DataFrame(val)
    val_df.to_csv(out/"gold_v3_74_validation_matrix.csv", index=False, encoding="utf-8-sig")
    summary = dict(summary)
    summary["status"] = status
    summary["created_at_utc"] = utc_now()
    (out/"gold_v3_74_guarded_live_csv_monitor_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    paste = [
        "GOLD V3 74 PASTE_ME_GUARDED_LIVE_CSV_MONITOR_SUMMARY",
        f"status: {status}",
        "guarded_live_csv_monitor_ready: " + str(status == READY_STATUS).lower(),
        "live_ready: false",
        "contract_mutated: false",
        "manual_candidate_demotion_or_removal: false",
        "open_asof_allowed: false",
        "csv_contract: " + CSV_CONTRACT,
        "csv_open_bar_exclusion_required: false",
        "safety: audit_only=true, live_allowed=false, mt5=false, discord=false, ai_api=false, final_signal=false",
        "pool_policy: " + POOL_POLICY,
        f"latest_m15_time: {summary.get('latest_m15_time','')}",
        f"last_guarded_pipeline_run_time: {summary.get('last_guarded_pipeline_run_time','')}",
        f"last_guarded_pipeline_returncode: {summary.get('last_guarded_pipeline_returncode','')}",
        f"stage73_latest_closed_m15_time: {summary.get('stage73_latest_closed_m15_time','')}",
        f"stage73_source_stage: {summary.get('stage73_source_stage','')}",
        f"decision: {summary.get('decision','')}",
        f"no_signal_reason: {summary.get('no_signal_reason','')}",
        f"emission_action: {summary.get('emission_action','')}",
        f"should_notify_discord: {summary.get('should_notify_discord','')}",
        f"should_place_mt5_order: {summary.get('should_place_mt5_order','')}",
        f"should_call_ai_api: {summary.get('should_call_ai_api','')}",
        f"should_enable_final_signal: {summary.get('should_enable_final_signal','')}",
        f"blocker_count: {len(blockers)}",
        "", "BLOCKERS", pd.DataFrame(blockers).to_string(index=False) if blockers else "NO_BLOCKERS",
        "", "VALIDATION", val_df.to_string(index=False),
        "", "OUTPUTS",
        "gold_v3_74_monitor_state.json",
        "gold_v3_74_monitor_event_log.csv",
        "gold_v3_74_latest_guarded_snapshot.csv",
        "gold_v3_74_latest_guarded_snapshot.json",
        "gold_v3_74_blocker_matrix.csv",
        "gold_v3_74_validation_matrix.csv",
        "gold_v3_74_guarded_live_csv_monitor_summary.json",
    ]
    (out/"gold_v3_74_PASTE_ME_GUARDED_LIVE_CSV_MONITOR_SUMMARY.txt").write_text("\n".join(paste)+"\n", encoding="utf-8")
    report = f"""# GOLD V3 74 guarded live CSV monitor audit-only report

Status: `{status}`

- latest_m15_time: `{summary.get('latest_m15_time','')}`
- stage73_latest_closed_m15_time: `{summary.get('stage73_latest_closed_m15_time','')}`
- stage73_source_stage: `{summary.get('stage73_source_stage','')}`
- decision: `{summary.get('decision','')}`
- emission_action: `{summary.get('emission_action','')}`
- should_notify_discord: `{summary.get('should_notify_discord','')}`
- should_place_mt5_order: `{summary.get('should_place_mt5_order','')}`
- blocker_count: `{len(blockers)}`

Audit-only. No MT5, Discord, AI API, live hook, live evaluator, or final signal.
"""
    (out/"GOLD_V3_74_REPORT.md").write_text(report, encoding="utf-8")


def main() -> int:
    a = parse_args()
    cdir = Path(a.candle_dir).expanduser().resolve() if a.candle_dir else find_files_dir()
    repo_root = Path(__file__).resolve().parents[2]
    base_out = cdir/"FX_OUTPUTS"/"gold_v3"
    out = Path(a.output_dir).expanduser().resolve() if a.output_dir else base_out/"74_guarded_live_csv_monitor_audit_only"
    out.mkdir(parents=True, exist_ok=True)
    state_path = out/"gold_v3_74_monitor_state.json"
    event_log = out/"gold_v3_74_monitor_event_log.csv"
    p_m15 = cdir/"goldsharp_m15.csv"
    s69 = repo_root/"scripts"/"gold_v3_runtime"/"gold_v3_69_live_csv_condition_detector_audit.py"
    s70 = repo_root/"scripts"/"gold_v3_runtime"/"gold_v3_70_live_csv_signal_decision_preview_audit.py"
    s71 = repo_root/"scripts"/"gold_v3_runtime"/"gold_v3_71_live_csv_signal_audit_pipeline_package.py"
    s73 = repo_root/"scripts"/"gold_v3_runtime"/"gold_v3_73_signal_emission_guard_audit.py"
    scripts = [s69, s70, s71, s73]
    state = read_json(state_path) if state_path.exists() else {}
    last_seen = str(state.get("latest_m15_time", ""))
    last_run_time = str(state.get("last_guarded_pipeline_run_time", ""))
    last_rc = str(state.get("last_guarded_pipeline_returncode", ""))
    first = True
    while True:
        val: list[dict[str, Any]] = []
        blockers: list[dict[str, Any]] = []
        latest = ""
        stage73_time = ""
        stage73_source_stage = ""
        decision = ""
        reason = ""
        action = ""
        should_discord = ""
        should_mt5 = ""
        should_ai = ""
        should_final = ""
        val.append(ok("goldsharp_m15_present", p_m15.exists(), str(p_m15), "exists"))
        for s in scripts:
            val.append(ok(f"script_present_{s.name}", s.exists(), str(s), "exists"))
            if not s.exists():
                blockers.append(blocker("required_script_missing", str(s), "REQUIRED_SCRIPT_MISSING"))
        try:
            latest = read_latest_m15_time(p_m15)
            val.append(ok("latest_m15_time_read", True, latest, "readable"))
        except Exception as e:
            val.append(ok("latest_m15_time_read", False, repr(e), "readable"))
            blockers.append(blocker("latest_m15_time_read_failed", str(p_m15), "LATEST_M15_TIME_READ_FAILED", repr(e)))
        should_run = bool(latest and not blockers and ((first and not a.no_startup_run) or latest != last_seen))
        if should_run:
            append_event(event_log, {"created_at_utc": utc_now(), "event": "GUARDED_PIPELINE_START", "latest_m15_time": latest, "status": "RUNNING", "detail": "Stage69->70->71->73(stage71 input)"})
            last_run_time = utc_now()
            last_rc = ""
            pipeline = [
                (s69, ["--candle-dir", str(cdir)]),
                (s70, ["--candle-dir", str(cdir)]),
                (s71, ["--candle-dir", str(cdir)]),
                (s73, ["--candle-dir", str(cdir), "--stage71-dir", str(base_out/"71_live_csv_signal_audit_pipeline_package_audit_only")]),
            ]
            for script, argsx in pipeline:
                rc, tail = run_script(script, argsx, repo_root)
                last_rc = str(rc)
                append_event(event_log, {"created_at_utc": utc_now(), "event": script.name, "latest_m15_time": latest, "status": "OK" if rc == 0 else "FAILED", "detail": tail.replace("\r", " ").replace("\n", " ")[-1000:]})
                if rc != 0:
                    blockers.append(blocker("guarded_pipeline_stage_failed", str(script), "PIPELINE_STAGE_RETURNED_NONZERO", {"returncode": rc, "output_tail": tail[-2000:]}))
                    break
            if not blockers:
                last_seen = latest
                last_rc = last_rc or "0"
                append_event(event_log, {"created_at_utc": utc_now(), "event": "GUARDED_PIPELINE_DONE", "latest_m15_time": latest, "status": "OK", "detail": "Stage69->70->71->73(stage71 input) completed"})
        else:
            append_event(event_log, {"created_at_utc": utc_now(), "event": "HEARTBEAT", "latest_m15_time": latest, "status": "NO_CHANGE" if latest == last_seen else "BLOCKED", "detail": "no guarded pipeline run"})

        p73_summary = base_out/"73_signal_emission_guard_audit_only"/"gold_v3_73_signal_emission_guard_summary.json"
        p73_decision = base_out/"73_signal_emission_guard_audit_only"/"gold_v3_73_emission_decision.csv"
        if p73_summary.exists():
            j73 = read_json(p73_summary)
            stage73_time = str(j73.get("latest_closed_m15_time", ""))
            stage73_source_stage = str(j73.get("source_stage", ""))
            decision = str(j73.get("decision", ""))
            reason = str(j73.get("no_signal_reason", ""))
            action = str(j73.get("emission_action", ""))
            should_discord = str(j73.get("should_notify_discord", ""))
            should_mt5 = str(j73.get("should_place_mt5_order", ""))
            should_ai = str(j73.get("should_call_ai_api", ""))
            should_final = str(j73.get("should_enable_final_signal", ""))
            val.append(ok("stage73_summary_present", True, str(p73_summary), "exists"))
            val.append(ok("stage73_ready", j73.get("status") == STAGE73_READY, j73.get("status"), STAGE73_READY))
            val.append(ok("stage73_source_stage_is_stage71", stage73_source_stage == "stage71", stage73_source_stage, "stage71"))
        else:
            val.append(ok("stage73_summary_present", False, str(p73_summary), "exists"))
            if should_run:
                blockers.append(blocker("stage73_summary_missing_after_pipeline", str(p73_summary), "STAGE73_SUMMARY_MISSING_AFTER_PIPELINE"))
        if p73_decision.exists():
            ddf = pd.read_csv(p73_decision, encoding="utf-8-sig")
            ddf.to_csv(out/"gold_v3_74_latest_guarded_snapshot.csv", index=False, encoding="utf-8-sig")
            (out/"gold_v3_74_latest_guarded_snapshot.json").write_text(json.dumps(ddf.iloc[0].to_dict(), ensure_ascii=False, indent=2, default=str), encoding="utf-8")
            val.append(ok("stage73_emission_decision_copied", True, str(p73_decision), "copied"))
        elif should_run:
            val.append(ok("stage73_emission_decision_present", False, str(p73_decision), "exists"))
            blockers.append(blocker("stage73_emission_decision_missing_after_pipeline", str(p73_decision), "STAGE73_DECISION_MISSING_AFTER_PIPELINE"))
        val.append(ok("stage73_time_matches_latest_m15", bool(latest and stage73_time and latest == stage73_time), stage73_time, latest))
        if not (latest and stage73_time and latest == stage73_time):
            blockers.append(blocker("stage73_snapshot_stale", str(p73_summary), "STAGE73_TIME_DOES_NOT_MATCH_LATEST_M15", {"latest": latest, "stage73": stage73_time, "source_stage": stage73_source_stage}))
        val.append(ok("last_guarded_pipeline_run_time_recorded", bool(last_run_time), last_run_time, "nonempty"))
        val.append(ok("last_guarded_pipeline_returncode_zero", str(last_rc) == "0", last_rc, "0"))
        val.append(ok("discord_notification_false", should_discord == "False", should_discord, "False"))
        val.append(ok("mt5_order_false", should_mt5 == "False", should_mt5, "False"))
        val.append(ok("ai_api_false", should_ai == "False", should_ai, "False"))
        val.append(ok("final_signal_false", should_final == "False", should_final, "False"))
        val.append(ok("csv_open_bar_exclusion_required_false", True, False, False))
        val.append(ok("live_flags_all_false", True, "all_false", "all_false"))
        failed = [v for v in val if v.get("result") != "PASS"]
        status = READY_STATUS if not failed and not blockers else BLOCKED_STATUS
        state = {"latest_m15_time": latest, "stage73_latest_closed_m15_time": stage73_time, "stage73_source_stage": stage73_source_stage, "last_guarded_pipeline_run_time": last_run_time, "last_guarded_pipeline_returncode": last_rc, "updated_at_utc": utc_now(), "status": status}
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
            "guarded_live_csv_monitor_ready": status == READY_STATUS,
            "pool_policy": POOL_POLICY,
            "latest_m15_time": latest,
            "stage73_latest_closed_m15_time": stage73_time,
            "stage73_source_stage": stage73_source_stage,
            "last_guarded_pipeline_run_time": last_run_time,
            "last_guarded_pipeline_returncode": last_rc,
            "decision": decision,
            "no_signal_reason": reason,
            "emission_action": action,
            "should_notify_discord": should_discord,
            "should_place_mt5_order": should_mt5,
            "should_call_ai_api": should_ai,
            "should_enable_final_signal": should_final,
            "poll_seconds": int(a.poll_seconds),
            "validation_failure_count": len(failed),
            "blocker_count": len(blockers),
        }
        write_outputs(out, status, val, blockers, summary)
        print(f"[{utc_now()}] {status} latest={latest} stage73={stage73_time} source={stage73_source_stage} decision={decision} action={action} blockers={len(blockers)}")
        if a.once:
            return 0 if status == READY_STATUS else 1
        first = False
        time.sleep(max(5, int(a.poll_seconds)))


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\n[STOP] GOLD V3 74 guarded monitor stopped by user.")
        raise SystemExit(0)
