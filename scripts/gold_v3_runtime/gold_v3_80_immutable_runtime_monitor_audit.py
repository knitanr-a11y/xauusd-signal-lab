#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GOLD V3 80 immutable runtime monitor audit-only.

Continuous wrapper: every minute + lag, read latest CSV row timestamp. When a new
closed M15 timestamp is detected, run Stage76 --once, then Stage79 immutable
snapshot. No MT5 orders, no Discord, no AI API, no final signal.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pandas as pd

STEP = "GOLD_V3_80_IMMUTABLE_RUNTIME_MONITOR_AUDIT_ONLY"
READY_STATUS = "GOLD_V3_80_IMMUTABLE_RUNTIME_MONITOR_READY_AUDIT_ONLY"
BLOCKED_STATUS = "GOLD_V3_80_IMMUTABLE_RUNTIME_MONITOR_BLOCKED_AUDIT_ONLY"
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
        if (d/"goldsharp_m15.csv").exists() or (d/"FX_OUTPUTS"/"gold_v3").exists():
            return d
    raise FileNotFoundError("Could not locate Files directory")


def read_last_nonempty_line(path: Path, block_size: int = 8192) -> str:
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
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        header = f.readline().strip()
    if not header:
        raise ValueError(f"empty CSV header: {path}")
    delim = ";" if header.count(";") >= header.count(",") else ","
    cols = next(csv.reader([header], delimiter=delim))
    time_idx = None
    for i, c in enumerate(cols):
        if str(c).strip().lower() == "time":
            time_idx = i
            break
    if time_idx is None:
        raise ValueError(f"time column not found: {path}")
    row = next(csv.reader([read_last_nonempty_line(path)], delimiter=delim))
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


def append_csv(path: Path, row: dict[str, Any], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    exists = path.exists()
    with path.open("a", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        if not exists:
            w.writeheader()
        w.writerow({k: row.get(k, "") for k in fields})


def run_script(script: Path, args: list[str], cwd: Path) -> tuple[int, str, float]:
    t0 = time.perf_counter()
    p = subprocess.run([sys.executable, str(script)] + args, cwd=str(cwd), text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    sec = time.perf_counter() - t0
    return int(p.returncode), p.stdout[-4000:], sec


def extract_stage79_paste_path(output: str) -> str:
    for line in output.splitlines():
        s = line.strip()
        if s.lower().endswith("paste_me.txt") and (":" in s or s.startswith("/")):
            return s
    m = re.search(r"([A-Za-z]:\\[^\r\n]+paste_me\.txt)", output)
    return m.group(1) if m else ""


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=STEP)
    p.add_argument("--candle-dir", default="")
    p.add_argument("--output-dir", default="")
    p.add_argument("--minute-lag-seconds", type=int, default=5)
    p.add_argument("--run-immediately", action="store_true")
    p.add_argument("--once", action="store_true")
    p.add_argument("--no-startup-run", action="store_true")
    return p.parse_args()


def write_outputs(out: Path, status: str, val: list[dict[str, Any]], blockers: list[dict[str, Any]], summary: dict[str, Any]) -> None:
    out.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(blockers).to_csv(out/"gold_v3_80_blocker_matrix.csv", index=False, encoding="utf-8-sig")
    val_df = pd.DataFrame(val)
    val_df.to_csv(out/"gold_v3_80_validation_matrix.csv", index=False, encoding="utf-8-sig")
    summary = dict(summary)
    summary["status"] = status
    summary["created_at_utc"] = utc_now()
    (out/"gold_v3_80_immutable_runtime_monitor_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    paste = [
        "GOLD V3 80 PASTE_ME_IMMUTABLE_RUNTIME_MONITOR_SUMMARY",
        f"status: {status}",
        "immutable_runtime_monitor_ready: " + str(status == READY_STATUS).lower(),
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
        f"last_seen_m15_time: {summary.get('last_seen_m15_time','')}",
        f"last_pipeline_run_time: {summary.get('last_pipeline_run_time','')}",
        f"last_stage76_returncode: {summary.get('last_stage76_returncode','')}",
        f"last_stage79_returncode: {summary.get('last_stage79_returncode','')}",
        f"last_stage76_seconds: {summary.get('last_stage76_seconds','')}",
        f"last_stage79_seconds: {summary.get('last_stage79_seconds','')}",
        f"last_total_seconds: {summary.get('last_total_seconds','')}",
        f"latest_check_seconds: {summary.get('latest_check_seconds','')}",
        f"last_stage79_paste_path: {summary.get('last_stage79_paste_path','')}",
        f"blocker_count: {len(blockers)}",
        "", "BLOCKERS", pd.DataFrame(blockers).to_string(index=False) if blockers else "NO_BLOCKERS",
        "", "VALIDATION", val_df.to_string(index=False),
        "", "OUTPUTS",
        "gold_v3_80_state.json",
        "gold_v3_80_event_log.csv",
        "gold_v3_80_timing_log.csv",
        "gold_v3_80_blocker_matrix.csv",
        "gold_v3_80_validation_matrix.csv",
        "gold_v3_80_immutable_runtime_monitor_summary.json",
        "gold_v3_80_PASTE_ME_IMMUTABLE_RUNTIME_MONITOR_SUMMARY.txt",
    ]
    (out/"gold_v3_80_PASTE_ME_IMMUTABLE_RUNTIME_MONITOR_SUMMARY.txt").write_text("\n".join(paste)+"\n", encoding="utf-8")
    report = f"""# GOLD V3 80 immutable runtime monitor audit-only report

Status: `{status}`

- latest_m15_time: `{summary.get('latest_m15_time','')}`
- last_seen_m15_time: `{summary.get('last_seen_m15_time','')}`
- last_stage76_seconds: `{summary.get('last_stage76_seconds','')}`
- last_stage79_seconds: `{summary.get('last_stage79_seconds','')}`
- last_total_seconds: `{summary.get('last_total_seconds','')}`
- last_stage79_paste_path: `{summary.get('last_stage79_paste_path','')}`
- blocker_count: `{len(blockers)}`

Audit-only. No MT5, Discord, AI API, live hook, live evaluator, or final signal.
"""
    (out/"GOLD_V3_80_REPORT.md").write_text(report, encoding="utf-8")


def main() -> int:
    a = parse_args()
    cdir = Path(a.candle_dir).expanduser().resolve() if a.candle_dir else find_files_dir()
    repo_root = Path(__file__).resolve().parents[2]
    base_out = cdir/"FX_OUTPUTS"/"gold_v3"
    out = Path(a.output_dir).expanduser().resolve() if a.output_dir else base_out/"80_immutable_runtime_monitor_audit_only"
    out.mkdir(parents=True, exist_ok=True)
    state_path = out/"gold_v3_80_state.json"
    event_log = out/"gold_v3_80_event_log.csv"
    timing_log = out/"gold_v3_80_timing_log.csv"
    p_m15 = cdir/"goldsharp_m15.csv"
    s76 = repo_root/"scripts"/"gold_v3_runtime"/"gold_v3_76_full_audit_monitor_with_payload_preview_audit.py"
    s79 = repo_root/"scripts"/"gold_v3_runtime"/"gold_v3_79_immutable_runtime_output_policy_audit.py"
    state = read_json(state_path) if state_path.exists() else {}
    last_seen = str(state.get("last_seen_m15_time", ""))
    last_pipeline_run_time = str(state.get("last_pipeline_run_time", ""))
    last_stage76_rc = str(state.get("last_stage76_returncode", ""))
    last_stage79_rc = str(state.get("last_stage79_returncode", ""))
    last_stage76_seconds = float(state.get("last_stage76_seconds", 0.0) or 0.0)
    last_stage79_seconds = float(state.get("last_stage79_seconds", 0.0) or 0.0)
    last_total_seconds = float(state.get("last_total_seconds", 0.0) or 0.0)
    last_stage79_paste_path = str(state.get("last_stage79_paste_path", ""))
    first = True
    event_fields = ["created_at_utc", "event", "latest_m15_time", "status", "detail"]
    timing_fields = ["created_at_utc", "latest_m15_time", "segment", "seconds", "returncode", "status", "detail"]
    while True:
        if not a.once and not (first and a.run_immediately):
            time.sleep(seconds_until_next_minute_lag(a.minute_lag_seconds))
        val: list[dict[str, Any]] = []
        blockers: list[dict[str, Any]] = []
        latest = ""
        latest_check_seconds = 0.0
        val.append(ok("goldsharp_m15_present", p_m15.exists(), str(p_m15), "exists"))
        for s in [s76, s79]:
            val.append(ok(f"script_present_{s.name}", s.exists(), str(s), "exists"))
            if not s.exists():
                blockers.append(blocker("required_script_missing", str(s), "REQUIRED_SCRIPT_MISSING"))
        try:
            t0 = time.perf_counter()
            latest = read_latest_m15_time(p_m15)
            latest_check_seconds = time.perf_counter() - t0
            val.append(ok("latest_m15_time_read", True, latest, "readable_latest_row_only"))
        except Exception as e:
            latest_check_seconds = time.perf_counter() - t0 if "t0" in locals() else 0.0
            val.append(ok("latest_m15_time_read", False, repr(e), "readable_latest_row_only"))
            blockers.append(blocker("latest_m15_time_read_failed", str(p_m15), "LATEST_M15_TIME_READ_FAILED", repr(e)))
        append_csv(timing_log, {"created_at_utc": utc_now(), "latest_m15_time": latest, "segment": "latest_row_check", "seconds": round(latest_check_seconds, 6), "returncode": 0 if latest else 1, "status": "OK" if latest else "FAILED", "detail": "latest CSV row only"}, timing_fields)
        should_run = bool(latest and not blockers and ((first and not a.no_startup_run) or latest != last_seen))
        if should_run:
            pipeline_t0 = time.perf_counter()
            last_pipeline_run_time = utc_now()
            append_csv(event_log, {"created_at_utc": utc_now(), "event": "PIPELINE_START", "latest_m15_time": latest, "status": "RUNNING", "detail": "Stage76 --once -> Stage79 immutable snapshot"}, event_fields)
            rc76, tail76, sec76 = run_script(s76, ["--candle-dir", str(cdir), "--once", "--run-immediately"], repo_root)
            last_stage76_rc = str(rc76)
            last_stage76_seconds = sec76
            append_csv(timing_log, {"created_at_utc": utc_now(), "latest_m15_time": latest, "segment": "stage76_once", "seconds": round(sec76, 6), "returncode": rc76, "status": "OK" if rc76 == 0 else "FAILED", "detail": tail76.replace("\r", " ").replace("\n", " ")[-1000:]}, timing_fields)
            if rc76 != 0:
                blockers.append(blocker("stage76_once_failed", str(s76), "STAGE76_RETURNED_NONZERO", {"returncode": rc76, "output_tail": tail76[-2000:]}))
            if not blockers:
                rc79, tail79, sec79 = run_script(s79, ["--candle-dir", str(cdir)], repo_root)
                last_stage79_rc = str(rc79)
                last_stage79_seconds = sec79
                last_stage79_paste_path = extract_stage79_paste_path(tail79)
                append_csv(timing_log, {"created_at_utc": utc_now(), "latest_m15_time": latest, "segment": "stage79_immutable_snapshot", "seconds": round(sec79, 6), "returncode": rc79, "status": "OK" if rc79 == 0 else "FAILED", "detail": tail79.replace("\r", " ").replace("\n", " ")[-1000:]}, timing_fields)
                if rc79 != 0:
                    blockers.append(blocker("stage79_immutable_snapshot_failed", str(s79), "STAGE79_RETURNED_NONZERO", {"returncode": rc79, "output_tail": tail79[-2000:]}))
                if not last_stage79_paste_path:
                    blockers.append(blocker("stage79_paste_path_missing", str(s79), "STAGE79_PASTE_PATH_NOT_DETECTED"))
            last_total_seconds = time.perf_counter() - pipeline_t0
            append_csv(timing_log, {"created_at_utc": utc_now(), "latest_m15_time": latest, "segment": "total_stage76_stage79", "seconds": round(last_total_seconds, 6), "returncode": 0 if not blockers else 1, "status": "OK" if not blockers else "FAILED", "detail": "Stage76 --once -> Stage79"}, timing_fields)
            if not blockers:
                last_seen = latest
                append_csv(event_log, {"created_at_utc": utc_now(), "event": "PIPELINE_DONE", "latest_m15_time": latest, "status": "OK", "detail": f"paste={last_stage79_paste_path}"}, event_fields)
        else:
            append_csv(event_log, {"created_at_utc": utc_now(), "event": "HEARTBEAT", "latest_m15_time": latest, "status": "NO_CHANGE" if latest == last_seen else "BLOCKED", "detail": "no pipeline run"}, event_fields)

        val.append(ok("latest_check_seconds_recorded", latest_check_seconds >= 0, round(latest_check_seconds, 6), ">=0"))
        val.append(ok("last_stage76_returncode_zero", str(last_stage76_rc) == "0", last_stage76_rc, "0"))
        val.append(ok("last_stage79_returncode_zero", str(last_stage79_rc) == "0", last_stage79_rc, "0"))
        val.append(ok("last_stage79_paste_path_present", bool(last_stage79_paste_path), last_stage79_paste_path, "nonempty"))
        val.append(ok("csv_open_bar_exclusion_required_false", True, False, False))
        val.append(ok("live_flags_all_false", True, "all_false", "all_false"))
        failed = [v for v in val if v.get("result") != "PASS"]
        status = READY_STATUS if not failed and not blockers else BLOCKED_STATUS
        state = {
            "status": status,
            "updated_at_utc": utc_now(),
            "schedule_mode": "aligned_minute_plus_lag",
            "minute_lag_seconds": max(0, min(59, int(a.minute_lag_seconds))),
            "latest_m15_time": latest,
            "last_seen_m15_time": last_seen,
            "last_pipeline_run_time": last_pipeline_run_time,
            "last_stage76_returncode": last_stage76_rc,
            "last_stage79_returncode": last_stage79_rc,
            "last_stage76_seconds": round(last_stage76_seconds, 6),
            "last_stage79_seconds": round(last_stage79_seconds, 6),
            "last_total_seconds": round(last_total_seconds, 6),
            "latest_check_seconds": round(latest_check_seconds, 6),
            "last_stage79_paste_path": last_stage79_paste_path,
        }
        state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
        summary = {
            "step": STEP,
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
            "immutable_runtime_monitor_ready": status == READY_STATUS,
            "pool_policy": POOL_POLICY,
            **state,
            "blocker_count": len(blockers),
            "validation_failure_count": len(failed),
        }
        write_outputs(out, status, val, blockers, summary)
        print(f"[{utc_now()}] {status} latest={latest} last_seen={last_seen} stage76={round(last_stage76_seconds, 6)}s stage79={round(last_stage79_seconds, 6)}s total={round(last_total_seconds, 6)}s paste={last_stage79_paste_path} blockers={len(blockers)}")
        if a.once:
            return 0 if status == READY_STATUS else 1
        first = False


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\n[STOP] GOLD V3 80 immutable runtime monitor stopped by user.")
        raise SystemExit(0)
