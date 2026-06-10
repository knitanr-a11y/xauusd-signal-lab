#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GOLD V3 76 full audit monitor with payload preview audit-only.

Watches goldsharp_m15.csv latest closed row. On an aligned schedule
(default: every minute at second=05), reads only the latest CSV row. When the
latest timestamp changes, runs Stage74 one-shot, then Stage75 payload preview,
and writes a final monitor summary.

No MT5 orders, no Discord, no AI API, no live hook, no final signal.
"""
from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pandas as pd

STEP = "GOLD_V3_76_FULL_AUDIT_MONITOR_WITH_PAYLOAD_PREVIEW_AUDIT_ONLY"
READY_STATUS = "GOLD_V3_76_FULL_AUDIT_MONITOR_WITH_PAYLOAD_PREVIEW_READY_AUDIT_ONLY"
BLOCKED_STATUS = "GOLD_V3_76_FULL_AUDIT_MONITOR_WITH_PAYLOAD_PREVIEW_BLOCKED_AUDIT_ONLY"
STAGE75_READY = "GOLD_V3_75_EXTERNAL_ACTION_PAYLOAD_PREVIEW_READY_AUDIT_ONLY"
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


def read_last_nonempty_line(path: Path, block_size: int = 8192) -> str:
    """Read the last non-empty line without loading the whole CSV."""
    with path.open("rb") as f:
        f.seek(0, 2)
        pos = f.tell()
        data = b""
        while pos > 0:
            step = min(block_size, pos)
            pos -= step
            f.seek(pos)
            data = f.read(step) + data
            lines = data.splitlines()
            if len(lines) >= 2 or pos == 0:
                for line in reversed(lines):
                    if line.strip():
                        return line.decode("utf-8-sig", errors="replace")
    raise ValueError(f"no non-empty lines: {path}")


def read_latest_m15_time(path: Path) -> str:
    """Read the latest closed M15 timestamp from the latest CSV row.

    CSV contract: open/in-progress candles are not written to CSV, so the latest
    row is the latest closed row. This function intentionally does not skip the
    latest row.
    """
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        header = f.readline().strip()
    if not header:
        raise ValueError(f"empty CSV header: {path}")
    delim = ";" if header.count(";") >= header.count(",") else ","
    header_cols = next(csv.reader([header], delimiter=delim))
    time_idx = None
    for i, c in enumerate(header_cols):
        if str(c).strip().lower() == "time":
            time_idx = i
            break
    if time_idx is None:
        raise ValueError(f"time column not found: {path}")
    last_line = read_last_nonempty_line(path)
    if last_line.strip() == header.strip():
        raise ValueError(f"CSV has header only: {path}")
    row = next(csv.reader([last_line], delimiter=delim))
    if time_idx >= len(row):
        raise ValueError(f"latest row has no time column: {path}")
    value = str(row[time_idx]).strip()
    if not value:
        raise ValueError(f"latest row time is blank: {path}")
    return str(pd.to_datetime(value, errors="raise"))


def seconds_until_next_minute_lag(lag_seconds: int) -> float:
    lag = max(0, min(59, int(lag_seconds)))
    now = datetime.now()
    target = now.replace(second=lag, microsecond=0)
    if now >= target:
        target = (now + timedelta(minutes=1)).replace(second=lag, microsecond=0)
    return max(0.1, (target - now).total_seconds())


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
    p.add_argument("--poll-seconds", type=int, default=30, help="legacy fallback value kept for compatibility; aligned minute scheduling is used by default")
    p.add_argument("--minute-lag-seconds", type=int, default=5, help="run each loop at every minute second=N; default N=5")
    p.add_argument("--run-immediately", action="store_true", help="run the first check immediately, then align to minute+lag")
    p.add_argument("--once", action="store_true")
    p.add_argument("--no-startup-run", action="store_true")
    return p.parse_args()


def write_outputs(out: Path, status: str, val: list[dict[str, Any]], blockers: list[dict[str, Any]], summary: dict[str, Any]) -> None:
    out.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(blockers).to_csv(out/"gold_v3_76_blocker_matrix.csv", index=False, encoding="utf-8-sig")
    val_df = pd.DataFrame(val)
    val_df.to_csv(out/"gold_v3_76_validation_matrix.csv", index=False, encoding="utf-8-sig")
    summary = dict(summary)
    summary["status"] = status
    summary["created_at_utc"] = utc_now()
    (out/"gold_v3_76_full_audit_monitor_with_payload_preview_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    paste = [
        "GOLD V3 76 PASTE_ME_FULL_AUDIT_MONITOR_WITH_PAYLOAD_PREVIEW_SUMMARY",
        f"status: {status}",
        "full_audit_monitor_with_payload_preview_ready: " + str(status == READY_STATUS).lower(),
        "live_ready: false",
        "contract_mutated: false",
        "manual_candidate_demotion_or_removal: false",
        "open_asof_allowed: false",
        "csv_contract: " + CSV_CONTRACT,
        "csv_open_bar_exclusion_required: false",
        "safety: audit_only=true, live_allowed=false, mt5=false, discord=false, ai_api=false, final_signal=false",
        "pool_policy: " + POOL_POLICY,
        f"schedule_mode: {summary.get('schedule_mode','')}",
        f"minute_lag_seconds: {summary.get('minute_lag_seconds','')}",
        f"latest_m15_time: {summary.get('latest_m15_time','')}",
        f"last_full_audit_run_time: {summary.get('last_full_audit_run_time','')}",
        f"last_full_audit_returncode: {summary.get('last_full_audit_returncode','')}",
        f"stage75_latest_closed_m15_time: {summary.get('stage75_latest_closed_m15_time','')}",
        f"decision: {summary.get('decision','')}",
        f"emission_action: {summary.get('emission_action','')}",
        f"payload_action: {summary.get('payload_action','')}",
        f"should_notify_discord: {summary.get('should_notify_discord','')}",
        f"should_place_mt5_order: {summary.get('should_place_mt5_order','')}",
        f"should_call_ai_api: {summary.get('should_call_ai_api','')}",
        f"should_enable_final_signal: {summary.get('should_enable_final_signal','')}",
        f"blocker_count: {len(blockers)}",
        "", "BLOCKERS", pd.DataFrame(blockers).to_string(index=False) if blockers else "NO_BLOCKERS",
        "", "VALIDATION", val_df.to_string(index=False),
        "", "OUTPUTS",
        "gold_v3_76_monitor_state.json",
        "gold_v3_76_monitor_event_log.csv",
        "gold_v3_76_latest_payload_preview.csv",
        "gold_v3_76_latest_payload_preview.json",
        "gold_v3_76_blocker_matrix.csv",
        "gold_v3_76_validation_matrix.csv",
        "gold_v3_76_full_audit_monitor_with_payload_preview_summary.json",
    ]
    (out/"gold_v3_76_PASTE_ME_FULL_AUDIT_MONITOR_WITH_PAYLOAD_PREVIEW_SUMMARY.txt").write_text("\n".join(paste)+"\n", encoding="utf-8")
    report = f"""# GOLD V3 76 full audit monitor with payload preview audit-only report

Status: `{status}`

- schedule_mode: `{summary.get('schedule_mode','')}`
- minute_lag_seconds: `{summary.get('minute_lag_seconds','')}`
- latest_m15_time: `{summary.get('latest_m15_time','')}`
- stage75_latest_closed_m15_time: `{summary.get('stage75_latest_closed_m15_time','')}`
- decision: `{summary.get('decision','')}`
- emission_action: `{summary.get('emission_action','')}`
- payload_action: `{summary.get('payload_action','')}`
- should_notify_discord: `{summary.get('should_notify_discord','')}`
- should_place_mt5_order: `{summary.get('should_place_mt5_order','')}`
- blocker_count: `{len(blockers)}`

Audit-only. No MT5, Discord, AI API, live hook, live evaluator, or final signal.
"""
    (out/"GOLD_V3_76_REPORT.md").write_text(report, encoding="utf-8")


def main() -> int:
    a = parse_args()
    cdir = Path(a.candle_dir).expanduser().resolve() if a.candle_dir else find_files_dir()
    repo_root = Path(__file__).resolve().parents[2]
    base_out = cdir/"FX_OUTPUTS"/"gold_v3"
    out = Path(a.output_dir).expanduser().resolve() if a.output_dir else base_out/"76_full_audit_monitor_with_payload_preview_audit_only"
    out.mkdir(parents=True, exist_ok=True)
    state_path = out/"gold_v3_76_monitor_state.json"
    event_log = out/"gold_v3_76_monitor_event_log.csv"
    p_m15 = cdir/"goldsharp_m15.csv"
    s74 = repo_root/"scripts"/"gold_v3_runtime"/"gold_v3_74_guarded_live_csv_monitor_audit.py"
    s75 = repo_root/"scripts"/"gold_v3_runtime"/"gold_v3_75_external_action_payload_preview_audit.py"
    state = read_json(state_path) if state_path.exists() else {}
    last_seen = str(state.get("latest_m15_time", ""))
    last_run_time = str(state.get("last_full_audit_run_time", ""))
    last_rc = str(state.get("last_full_audit_returncode", ""))
    first = True
    while True:
        if not a.once and not (first and a.run_immediately):
            sleep_s = seconds_until_next_minute_lag(a.minute_lag_seconds)
            time.sleep(sleep_s)
        val: list[dict[str, Any]] = []
        blockers: list[dict[str, Any]] = []
        latest = ""
        stage75_time = ""
        decision = ""
        emission_action = ""
        payload_action = ""
        should_discord = ""
        should_mt5 = ""
        should_ai = ""
        should_final = ""
        val.append(ok("goldsharp_m15_present", p_m15.exists(), str(p_m15), "exists"))
        for s in [s74, s75]:
            val.append(ok(f"script_present_{s.name}", s.exists(), str(s), "exists"))
            if not s.exists():
                blockers.append(blocker("required_script_missing", str(s), "REQUIRED_SCRIPT_MISSING"))
        try:
            latest = read_latest_m15_time(p_m15)
            val.append(ok("latest_m15_time_read", True, latest, "readable_latest_row_only"))
        except Exception as e:
            val.append(ok("latest_m15_time_read", False, repr(e), "readable_latest_row_only"))
            blockers.append(blocker("latest_m15_time_read_failed", str(p_m15), "LATEST_M15_TIME_READ_FAILED", repr(e)))
        should_run = bool(latest and not blockers and ((first and not a.no_startup_run) or latest != last_seen))
        if should_run:
            append_event(event_log, {"created_at_utc": utc_now(), "event": "FULL_AUDIT_START", "latest_m15_time": latest, "status": "RUNNING", "detail": "Stage74 --once -> Stage75"})
            last_run_time = utc_now()
            last_rc = ""
            pipeline = [
                (s74, ["--candle-dir", str(cdir), "--once"]),
                (s75, ["--candle-dir", str(cdir)]),
            ]
            for script, argsx in pipeline:
                rc, tail = run_script(script, argsx, repo_root)
                last_rc = str(rc)
                append_event(event_log, {"created_at_utc": utc_now(), "event": script.name, "latest_m15_time": latest, "status": "OK" if rc == 0 else "FAILED", "detail": tail.replace("\r", " ").replace("\n", " ")[-1000:]})
                if rc != 0:
                    blockers.append(blocker("full_audit_stage_failed", str(script), "PIPELINE_STAGE_RETURNED_NONZERO", {"returncode": rc, "output_tail": tail[-2000:]}))
                    break
            if not blockers:
                last_seen = latest
                last_rc = last_rc or "0"
                append_event(event_log, {"created_at_utc": utc_now(), "event": "FULL_AUDIT_DONE", "latest_m15_time": latest, "status": "OK", "detail": "Stage74 --once -> Stage75 completed"})
        else:
            append_event(event_log, {"created_at_utc": utc_now(), "event": "HEARTBEAT", "latest_m15_time": latest, "status": "NO_CHANGE" if latest == last_seen else "BLOCKED", "detail": "no full audit run"})

        p75 = base_out/"75_external_action_payload_preview_audit_only"/"gold_v3_75_external_action_payload_preview_summary.json"
        p75_csv = base_out/"75_external_action_payload_preview_audit_only"/"gold_v3_75_payload_preview.csv"
        if p75.exists():
            j75 = read_json(p75)
            stage75_time = str(j75.get("latest_closed_m15_time", ""))
            decision = str(j75.get("decision", ""))
            emission_action = str(j75.get("emission_action", ""))
            payload_action = str(j75.get("payload_action", ""))
            should_discord = str(j75.get("should_notify_discord", ""))
            should_mt5 = str(j75.get("should_place_mt5_order", ""))
            should_ai = str(j75.get("should_call_ai_api", ""))
            should_final = str(j75.get("should_enable_final_signal", ""))
            val.append(ok("stage75_summary_present", True, str(p75), "exists"))
            val.append(ok("stage75_ready", j75.get("status") == STAGE75_READY, j75.get("status"), STAGE75_READY))
        else:
            val.append(ok("stage75_summary_present", False, str(p75), "exists"))
            if should_run:
                blockers.append(blocker("stage75_summary_missing_after_pipeline", str(p75), "STAGE75_SUMMARY_MISSING_AFTER_PIPELINE"))
        if p75_csv.exists():
            ddf = pd.read_csv(p75_csv, encoding="utf-8-sig")
            ddf.to_csv(out/"gold_v3_76_latest_payload_preview.csv", index=False, encoding="utf-8-sig")
            (out/"gold_v3_76_latest_payload_preview.json").write_text(json.dumps(ddf.iloc[0].to_dict(), ensure_ascii=False, indent=2, default=str), encoding="utf-8")
            val.append(ok("stage75_payload_preview_copied", True, str(p75_csv), "copied"))
        elif should_run:
            val.append(ok("stage75_payload_preview_present", False, str(p75_csv), "exists"))
            blockers.append(blocker("stage75_payload_preview_missing_after_pipeline", str(p75_csv), "STAGE75_PAYLOAD_PREVIEW_MISSING_AFTER_PIPELINE"))
        val.append(ok("stage75_time_matches_latest_m15", bool(latest and stage75_time and latest == stage75_time), stage75_time, latest))
        if not (latest and stage75_time and latest == stage75_time):
            blockers.append(blocker("stage75_snapshot_stale", str(p75), "STAGE75_TIME_DOES_NOT_MATCH_LATEST_M15", {"latest": latest, "stage75": stage75_time}))
        val.append(ok("last_full_audit_run_time_recorded", bool(last_run_time), last_run_time, "nonempty"))
        val.append(ok("last_full_audit_returncode_zero", str(last_rc) == "0", last_rc, "0"))
        val.append(ok("payload_action_deterministic", payload_action in {"SUPPRESS_NO_SIGNAL_PAYLOAD", "SUPPRESS_DUPLICATE_PAYLOAD", "BUILD_AUDIT_PAYLOAD_PREVIEW"}, payload_action, "deterministic"))
        val.append(ok("discord_send_false", should_discord == "False", should_discord, "False"))
        val.append(ok("mt5_order_false", should_mt5 == "False", should_mt5, "False"))
        val.append(ok("ai_api_false", should_ai == "False", should_ai, "False"))
        val.append(ok("final_signal_false", should_final == "False", should_final, "False"))
        val.append(ok("csv_open_bar_exclusion_required_false", True, False, False))
        val.append(ok("live_flags_all_false", True, "all_false", "all_false"))
        failed = [v for v in val if v.get("result") != "PASS"]
        status = READY_STATUS if not failed and not blockers else BLOCKED_STATUS
        state = {"latest_m15_time": latest, "stage75_latest_closed_m15_time": stage75_time, "last_full_audit_run_time": last_run_time, "last_full_audit_returncode": last_rc, "updated_at_utc": utc_now(), "status": status, "schedule_mode": "aligned_minute_plus_lag", "minute_lag_seconds": max(0, min(59, int(a.minute_lag_seconds)))}
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
            "full_audit_monitor_with_payload_preview_ready": status == READY_STATUS,
            "pool_policy": POOL_POLICY,
            "schedule_mode": "aligned_minute_plus_lag",
            "minute_lag_seconds": max(0, min(59, int(a.minute_lag_seconds))),
            "latest_m15_time": latest,
            "stage75_latest_closed_m15_time": stage75_time,
            "last_full_audit_run_time": last_run_time,
            "last_full_audit_returncode": last_rc,
            "decision": decision,
            "emission_action": emission_action,
            "payload_action": payload_action,
            "should_notify_discord": should_discord,
            "should_place_mt5_order": should_mt5,
            "should_call_ai_api": should_ai,
            "should_enable_final_signal": should_final,
            "legacy_poll_seconds": int(a.poll_seconds),
            "validation_failure_count": len(failed),
            "blocker_count": len(blockers),
        }
        write_outputs(out, status, val, blockers, summary)
        print(f"[{utc_now()}] {status} schedule=minute+{max(0, min(59, int(a.minute_lag_seconds)))}s latest={latest} stage75={stage75_time} decision={decision} payload={payload_action} blockers={len(blockers)}")
        if a.once:
            return 0 if status == READY_STATUS else 1
        first = False


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\n[STOP] GOLD V3 76 full audit monitor stopped by user.")
        raise SystemExit(0)
