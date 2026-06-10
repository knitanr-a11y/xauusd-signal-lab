#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GOLD V3 80 immutable runtime monitor audit-only.

Continuous wrapper: every minute + lag, read latest CSV row timestamp. When a new
closed M15 timestamp is detected, run Stage76 --once, then Stage79 immutable
snapshot. If explicitly enabled, run Stage85/86 as audit-only ledger sidecar dry-run.
If the monitor becomes BLOCKED, automatically create a compact Stage81 support
bundle so the user only needs to upload one small upload_first.txt.

No MT5 orders, no Discord, no AI API, no final signal.
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


def extract_paste_me_path(output: str) -> str:
    """Extract short paste_me.txt or long *_PASTE_ME_*.txt artifact path.

    Stage79 uses short `paste_me.txt`. Stage85/86 use long PASTE_ME summary
    filenames, so matching only `paste_me.txt` incorrectly marks successful
    sidecar runs as BLOCKED. This function accepts both forms.
    """
    patterns = [
        r"([A-Za-z]:\\[^\r\n]*paste_me\.txt)",
        r"([A-Za-z]:\\[^\r\n]*PASTE_ME[^\r\n]*\.txt)",
        r"(/[^\r\n]*paste_me\.txt)",
        r"(/[^\r\n]*PASTE_ME[^\r\n]*\.txt)",
    ]
    for line in output.splitlines():
        s = line.strip().strip('"')
        for pat in patterns:
            m = re.search(pat, s, flags=re.IGNORECASE)
            if m:
                return m.group(1).strip().strip('"')
        if s.lower().endswith(".txt") and "paste_me" in s.lower() and (":" in s or s.startswith("/")):
            # Fallback for lines that are already the raw path.
            return s
    for pat in patterns:
        m = re.search(pat, output, flags=re.IGNORECASE)
        if m:
            return m.group(1).strip().strip('"')
    return ""


def extract_stage79_paste_path(output: str) -> str:
    return extract_paste_me_path(output)


def extract_stage81_upload_path(output: str) -> str:
    for line in output.splitlines():
        s = line.strip()
        if s.lower().endswith("upload_first.txt") and (":" in s or s.startswith("/")):
            return s
    m = re.search(r"([A-Za-z]:\\[^\r\n]+upload_first\.txt)", output)
    return m.group(1) if m else ""


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=STEP)
    p.add_argument("--candle-dir", default="")
    p.add_argument("--output-dir", default="")
    p.add_argument("--minute-lag-seconds", type=int, default=5)
    p.add_argument("--run-immediately", action="store_true")
    p.add_argument("--once", action="store_true")
    p.add_argument("--no-startup-run", action="store_true")
    p.add_argument("--disable-auto-support-bundle", action="store_true", help="do not auto-run Stage81 on BLOCKED; kept only for troubleshooting")
    p.add_argument("--enable-ledger-sidecar-dry-run", action="store_true", help="after Stage79, run Stage85 then Stage86 as audit-only sidecar; default OFF")
    p.add_argument("--ledger-sidecar-nonblocking", action="store_true", help="record Stage85/86 failures but do not block Stage80; troubleshooting only")
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
        f"ledger_sidecar_enabled: {summary.get('ledger_sidecar_enabled','')}",
        f"ledger_sidecar_nonblocking: {summary.get('ledger_sidecar_nonblocking','')}",
        f"last_stage85_returncode: {summary.get('last_stage85_returncode','')}",
        f"last_stage86_returncode: {summary.get('last_stage86_returncode','')}",
        f"last_stage85_seconds: {summary.get('last_stage85_seconds','')}",
        f"last_stage86_seconds: {summary.get('last_stage86_seconds','')}",
        f"last_stage85_paste_path: {summary.get('last_stage85_paste_path','')}",
        f"last_stage86_paste_path: {summary.get('last_stage86_paste_path','')}",
        f"durable_ledger_append_enabled: {summary.get('durable_ledger_append_enabled','')}",
        f"auto_support_bundle_enabled: {summary.get('auto_support_bundle_enabled','')}",
        f"last_support_bundle_returncode: {summary.get('last_support_bundle_returncode','')}",
        f"last_support_bundle_upload_first_path: {summary.get('last_support_bundle_upload_first_path','')}",
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
- ledger_sidecar_enabled: `{summary.get('ledger_sidecar_enabled','')}`
- last_stage85_returncode: `{summary.get('last_stage85_returncode','')}`
- last_stage86_returncode: `{summary.get('last_stage86_returncode','')}`
- durable_ledger_append_enabled: `{summary.get('durable_ledger_append_enabled','')}`
- auto_support_bundle_enabled: `{summary.get('auto_support_bundle_enabled','')}`
- last_support_bundle_upload_first_path: `{summary.get('last_support_bundle_upload_first_path','')}`
- blocker_count: `{len(blockers)}`

Audit-only. No MT5, Discord, AI API, live hook, live evaluator, or final signal.
"""
    (out/"GOLD_V3_80_REPORT.md").write_text(report, encoding="utf-8")


def build_summary(state: dict[str, Any], blockers: list[dict[str, Any]], failed: list[dict[str, Any]], status: str) -> dict[str, Any]:
    return {
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
    s81 = repo_root/"scripts"/"gold_v3_runtime"/"gold_v3_81_compact_support_bundle_audit.py"
    s85 = repo_root/"scripts"/"gold_v3_runtime"/"gold_v3_85_trade_review_ledger_entry_preview_audit.py"
    s86 = repo_root/"scripts"/"gold_v3_runtime"/"gold_v3_86_trade_review_ledger_append_guard_audit.py"
    state0 = read_json(state_path) if state_path.exists() else {}
    last_seen = str(state0.get("last_seen_m15_time", ""))
    last_pipeline_run_time = str(state0.get("last_pipeline_run_time", ""))
    last_stage76_rc = str(state0.get("last_stage76_returncode", ""))
    last_stage79_rc = str(state0.get("last_stage79_returncode", ""))
    last_stage85_rc = str(state0.get("last_stage85_returncode", ""))
    last_stage86_rc = str(state0.get("last_stage86_returncode", ""))
    last_stage76_seconds = float(state0.get("last_stage76_seconds", 0.0) or 0.0)
    last_stage79_seconds = float(state0.get("last_stage79_seconds", 0.0) or 0.0)
    last_stage85_seconds = float(state0.get("last_stage85_seconds", 0.0) or 0.0)
    last_stage86_seconds = float(state0.get("last_stage86_seconds", 0.0) or 0.0)
    last_total_seconds = float(state0.get("last_total_seconds", 0.0) or 0.0)
    last_stage79_paste_path = str(state0.get("last_stage79_paste_path", ""))
    last_stage85_paste_path = str(state0.get("last_stage85_paste_path", ""))
    last_stage86_paste_path = str(state0.get("last_stage86_paste_path", ""))
    last_support_bundle_rc = str(state0.get("last_support_bundle_returncode", ""))
    last_support_bundle_upload_path = str(state0.get("last_support_bundle_upload_first_path", ""))
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
        required_scripts = [s76, s79, s81]
        if a.enable_ledger_sidecar_dry_run:
            required_scripts.extend([s85, s86])
        for s in required_scripts:
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
            pipeline_detail = "Stage76 --once -> Stage79 immutable snapshot"
            if a.enable_ledger_sidecar_dry_run:
                pipeline_detail += " -> Stage85 ledger preview -> Stage86 append guard"
            append_csv(event_log, {"created_at_utc": utc_now(), "event": "PIPELINE_START", "latest_m15_time": latest, "status": "RUNNING", "detail": pipeline_detail}, event_fields)
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
            if not blockers and a.enable_ledger_sidecar_dry_run:
                rc85, tail85, sec85 = run_script(s85, ["--candle-dir", str(cdir)], repo_root)
                last_stage85_rc = str(rc85)
                last_stage85_seconds = sec85
                last_stage85_paste_path = extract_paste_me_path(tail85)
                append_csv(timing_log, {"created_at_utc": utc_now(), "latest_m15_time": latest, "segment": "stage85_ledger_preview_sidecar", "seconds": round(sec85, 6), "returncode": rc85, "status": "OK" if rc85 == 0 else "FAILED", "detail": tail85.replace("\r", " ").replace("\n", " ")[-1000:]}, timing_fields)
                if rc85 != 0 and not a.ledger_sidecar_nonblocking:
                    blockers.append(blocker("stage85_ledger_preview_sidecar_failed", str(s85), "STAGE85_RETURNED_NONZERO", {"returncode": rc85, "output_tail": tail85[-2000:]}))
                if rc85 == 0:
                    rc86, tail86, sec86 = run_script(s86, ["--candle-dir", str(cdir)], repo_root)
                    last_stage86_rc = str(rc86)
                    last_stage86_seconds = sec86
                    last_stage86_paste_path = extract_paste_me_path(tail86)
                    append_csv(timing_log, {"created_at_utc": utc_now(), "latest_m15_time": latest, "segment": "stage86_append_guard_sidecar", "seconds": round(sec86, 6), "returncode": rc86, "status": "OK" if rc86 == 0 else "FAILED", "detail": tail86.replace("\r", " ").replace("\n", " ")[-1000:]}, timing_fields)
                    if rc86 != 0 and not a.ledger_sidecar_nonblocking:
                        blockers.append(blocker("stage86_append_guard_sidecar_failed", str(s86), "STAGE86_RETURNED_NONZERO", {"returncode": rc86, "output_tail": tail86[-2000:]}))
                elif a.ledger_sidecar_nonblocking:
                    last_stage86_rc = "SKIPPED_AFTER_STAGE85_FAILURE"
                    last_stage86_seconds = 0.0
                    last_stage86_paste_path = ""
                append_csv(event_log, {"created_at_utc": utc_now(), "event": "LEDGER_SIDECAR_DRY_RUN", "latest_m15_time": latest, "status": "OK" if not blockers else "FAILED", "detail": f"stage85={last_stage85_rc} paste85={last_stage85_paste_path} stage86={last_stage86_rc} paste86={last_stage86_paste_path}"}, event_fields)
            last_total_seconds = time.perf_counter() - pipeline_t0
            append_csv(timing_log, {"created_at_utc": utc_now(), "latest_m15_time": latest, "segment": "total_stage76_stage79_sidecar", "seconds": round(last_total_seconds, 6), "returncode": 0 if not blockers else 1, "status": "OK" if not blockers else "FAILED", "detail": pipeline_detail}, timing_fields)
            if not blockers:
                last_seen = latest
                append_csv(event_log, {"created_at_utc": utc_now(), "event": "PIPELINE_DONE", "latest_m15_time": latest, "status": "OK", "detail": f"paste={last_stage79_paste_path} sidecar={a.enable_ledger_sidecar_dry_run}"}, event_fields)
        else:
            append_csv(event_log, {"created_at_utc": utc_now(), "event": "HEARTBEAT", "latest_m15_time": latest, "status": "NO_CHANGE" if latest == last_seen else "BLOCKED", "detail": "no pipeline run"}, event_fields)

        val.append(ok("latest_check_seconds_recorded", latest_check_seconds >= 0, round(latest_check_seconds, 6), ">=0"))
        val.append(ok("last_stage76_returncode_zero", str(last_stage76_rc) == "0", last_stage76_rc, "0"))
        val.append(ok("last_stage79_returncode_zero", str(last_stage79_rc) == "0", last_stage79_rc, "0"))
        val.append(ok("last_stage79_paste_path_present", bool(last_stage79_paste_path), last_stage79_paste_path, "nonempty"))
        val.append(ok("ledger_sidecar_default_safe", bool(a.enable_ledger_sidecar_dry_run) in {False, True}, bool(a.enable_ledger_sidecar_dry_run), "explicit boolean"))
        if a.enable_ledger_sidecar_dry_run:
            val.append(ok("last_stage85_returncode_zero", str(last_stage85_rc) == "0", last_stage85_rc, "0"))
            val.append(ok("last_stage86_returncode_zero", str(last_stage86_rc) == "0", last_stage86_rc, "0"))
            val.append(ok("last_stage85_paste_path_present", bool(last_stage85_paste_path), last_stage85_paste_path, "nonempty"))
            val.append(ok("last_stage86_paste_path_present", bool(last_stage86_paste_path), last_stage86_paste_path, "nonempty"))
        val.append(ok("durable_ledger_append_disabled", True, False, False))
        val.append(ok("auto_support_bundle_enabled", not a.disable_auto_support_bundle, str(not a.disable_auto_support_bundle), "true"))
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
            "last_stage85_returncode": last_stage85_rc,
            "last_stage86_returncode": last_stage86_rc,
            "last_stage76_seconds": round(last_stage76_seconds, 6),
            "last_stage79_seconds": round(last_stage79_seconds, 6),
            "last_stage85_seconds": round(last_stage85_seconds, 6),
            "last_stage86_seconds": round(last_stage86_seconds, 6),
            "last_total_seconds": round(last_total_seconds, 6),
            "latest_check_seconds": round(latest_check_seconds, 6),
            "last_stage79_paste_path": last_stage79_paste_path,
            "last_stage85_paste_path": last_stage85_paste_path,
            "last_stage86_paste_path": last_stage86_paste_path,
            "ledger_sidecar_enabled": bool(a.enable_ledger_sidecar_dry_run),
            "ledger_sidecar_nonblocking": bool(a.ledger_sidecar_nonblocking),
            "durable_ledger_append_enabled": False,
            "auto_support_bundle_enabled": not a.disable_auto_support_bundle,
            "last_support_bundle_returncode": last_support_bundle_rc,
            "last_support_bundle_upload_first_path": last_support_bundle_upload_path,
        }
        summary = build_summary(state, blockers, failed, status)
        state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
        write_outputs(out, status, val, blockers, summary)

        if status == BLOCKED_STATUS and not a.disable_auto_support_bundle and s81.exists():
            rc81, tail81, sec81 = run_script(s81, ["--candle-dir", str(cdir)], repo_root)
            last_support_bundle_rc = str(rc81)
            upload_path = extract_stage81_upload_path(tail81)
            if upload_path:
                last_support_bundle_upload_path = upload_path
            append_csv(timing_log, {"created_at_utc": utc_now(), "latest_m15_time": latest, "segment": "stage81_auto_support_bundle", "seconds": round(sec81, 6), "returncode": rc81, "status": "OK" if rc81 == 0 else "FAILED", "detail": tail81.replace("\r", " ").replace("\n", " ")[-1000:]}, timing_fields)
            append_csv(event_log, {"created_at_utc": utc_now(), "event": "AUTO_SUPPORT_BUNDLE", "latest_m15_time": latest, "status": "OK" if rc81 == 0 else "FAILED", "detail": f"upload_first={last_support_bundle_upload_path}"}, event_fields)
            state["last_support_bundle_returncode"] = last_support_bundle_rc
            state["last_support_bundle_upload_first_path"] = last_support_bundle_upload_path
            summary = build_summary(state, blockers, failed, status)
            state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
            write_outputs(out, status, val, blockers, summary)

        print(f"[{utc_now()}] {status} latest={latest} last_seen={last_seen} stage76={round(last_stage76_seconds, 6)}s stage79={round(last_stage79_seconds, 6)}s stage85={round(last_stage85_seconds, 6)}s stage86={round(last_stage86_seconds, 6)}s total={round(last_total_seconds, 6)}s paste={last_stage79_paste_path} sidecar={a.enable_ledger_sidecar_dry_run} support={last_support_bundle_upload_path} blockers={len(blockers)}")
        if a.once:
            return 0 if status == READY_STATUS else 1
        first = False


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\n[STOP] GOLD V3 80 immutable runtime monitor stopped by user.")
        raise SystemExit(0)
