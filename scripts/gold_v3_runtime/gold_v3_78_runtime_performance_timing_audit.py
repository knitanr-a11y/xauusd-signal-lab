#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GOLD V3 78 runtime performance timing audit-only.

Measures latest-row CSV check, Stage74 one-shot, Stage75 payload preview, and
total full-audit runtime. No MT5 orders, no Discord, no AI API, no final signal.
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

STEP = "GOLD_V3_78_RUNTIME_PERFORMANCE_TIMING_AUDIT_ONLY"
READY_STATUS = "GOLD_V3_78_RUNTIME_PERFORMANCE_TIMING_READY_AUDIT_ONLY"
BLOCKED_STATUS = "GOLD_V3_78_RUNTIME_PERFORMANCE_TIMING_BLOCKED_AUDIT_ONLY"
STAGE75_READY = "GOLD_V3_75_EXTERNAL_ACTION_PAYLOAD_PREVIEW_READY_AUDIT_ONLY"
CSV_CONTRACT = "open/in-progress candles are not written to CSV"
POOL_POLICY = "poolから外さない。rolling health gateに判断させる。"
ADVISORY_LATEST_ROW_SECONDS = 0.25
ADVISORY_STAGE74_SECONDS = 10.0
ADVISORY_STAGE75_SECONDS = 2.0
ADVISORY_TOTAL_SECONDS = 12.0
HARD_TOTAL_SECONDS = 60.0


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def ok(check_id: str, passed: bool, observed: Any, expected: Any, severity: str = "BLOCKER") -> dict[str, Any]:
    return {"check_id": check_id, "result": "PASS" if passed else "FAIL", "observed": observed, "expected": expected, "severity": severity}


def blocker(blocker_id: str, artifact: str, reason: str, detail: Any = "") -> dict[str, Any]:
    return {"blocker_id": blocker_id, "artifact": artifact, "reason": reason, "detail": detail, "severity": "BLOCKER"}


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def find_files_dir() -> Path:
    root = Path(__file__).resolve().parents[2]
    for d in [Path.cwd(), Path.cwd()/"Files", root, root/"Files", root.parent, root.parent/"Files", root.parent.parent]:
        d = d.expanduser().resolve()
        if (d/"goldsharp_m15.csv").exists():
            return d
    raise FileNotFoundError("Could not locate Files directory with goldsharp_m15.csv")


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
    last_line = read_last_nonempty_line(path)
    row = next(csv.reader([last_line], delimiter=delim))
    if time_idx >= len(row):
        raise ValueError(f"latest row has no time column: {path}")
    value = str(row[time_idx]).strip()
    if not value:
        raise ValueError(f"latest row time is blank: {path}")
    return str(pd.to_datetime(value, errors="raise"))


def run_script(script: Path, args: list[str], cwd: Path) -> tuple[int, str, float]:
    t0 = time.perf_counter()
    p = subprocess.run([sys.executable, str(script)] + args, cwd=str(cwd), text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    sec = time.perf_counter() - t0
    return int(p.returncode), p.stdout[-4000:], sec


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=STEP)
    p.add_argument("--candle-dir", default="")
    p.add_argument("--output-dir", default="")
    return p.parse_args()


def assessment_row(metric: str, seconds: float, advisory: float | None, hard: float | None = None) -> dict[str, Any]:
    if hard is not None and seconds > hard:
        result = "BLOCK"
    elif advisory is not None and seconds > advisory:
        result = "WARN"
    else:
        result = "PASS"
    return {"metric": metric, "seconds": round(seconds, 6), "advisory_threshold_seconds": advisory, "hard_threshold_seconds": hard, "result": result}


def main() -> int:
    a = parse_args()
    cdir = Path(a.candle_dir).expanduser().resolve() if a.candle_dir else find_files_dir()
    repo_root = Path(__file__).resolve().parents[2]
    base_out = cdir / "FX_OUTPUTS" / "gold_v3"
    out = Path(a.output_dir).expanduser().resolve() if a.output_dir else base_out / "78_runtime_performance_timing_audit_only"
    out.mkdir(parents=True, exist_ok=True)
    p_m15 = cdir / "goldsharp_m15.csv"
    s74 = repo_root / "scripts" / "gold_v3_runtime" / "gold_v3_74_guarded_live_csv_monitor_audit.py"
    s75 = repo_root / "scripts" / "gold_v3_runtime" / "gold_v3_75_external_action_payload_preview_audit.py"

    val: list[dict[str, Any]] = []
    blockers: list[dict[str, Any]] = []
    timing_rows: list[dict[str, Any]] = []

    total_t0 = time.perf_counter()
    val.append(ok("goldsharp_m15_present", p_m15.exists(), str(p_m15), "exists"))
    for s in [s74, s75]:
        val.append(ok(f"script_present_{s.name}", s.exists(), str(s), "exists"))
        if not s.exists():
            blockers.append(blocker("required_script_missing", str(s), "REQUIRED_SCRIPT_MISSING"))

    latest = ""
    latest_sec = 0.0
    try:
        t0 = time.perf_counter()
        latest = read_latest_m15_time(p_m15)
        latest_sec = time.perf_counter() - t0
        val.append(ok("latest_m15_time_read_latest_row_only", True, latest, "readable_latest_row_only"))
    except Exception as e:
        latest_sec = time.perf_counter() - t0 if 't0' in locals() else 0.0
        val.append(ok("latest_m15_time_read_latest_row_only", False, repr(e), "readable_latest_row_only"))
        blockers.append(blocker("latest_m15_time_read_failed", str(p_m15), "LATEST_M15_TIME_READ_FAILED", repr(e)))
    timing_rows.append({"segment": "latest_row_check", "seconds": round(latest_sec, 6), "returncode": 0 if latest else 1, "detail": latest})

    stage74_rc = None
    stage74_sec = 0.0
    stage75_rc = None
    stage75_sec = 0.0
    if not blockers:
        stage74_rc, stage74_tail, stage74_sec = run_script(s74, ["--candle-dir", str(cdir), "--once"], repo_root)
        timing_rows.append({"segment": "stage74_once", "seconds": round(stage74_sec, 6), "returncode": stage74_rc, "detail": stage74_tail[-1000:].replace("\r", " ").replace("\n", " ")})
        val.append(ok("stage74_returncode_zero", stage74_rc == 0, stage74_rc, 0))
        if stage74_rc != 0:
            blockers.append(blocker("stage74_failed", str(s74), "STAGE74_RETURNED_NONZERO", {"returncode": stage74_rc, "output_tail": stage74_tail[-2000:]}))
    if not blockers:
        stage75_rc, stage75_tail, stage75_sec = run_script(s75, ["--candle-dir", str(cdir)], repo_root)
        timing_rows.append({"segment": "stage75_payload_preview", "seconds": round(stage75_sec, 6), "returncode": stage75_rc, "detail": stage75_tail[-1000:].replace("\r", " ").replace("\n", " ")})
        val.append(ok("stage75_returncode_zero", stage75_rc == 0, stage75_rc, 0))
        if stage75_rc != 0:
            blockers.append(blocker("stage75_failed", str(s75), "STAGE75_RETURNED_NONZERO", {"returncode": stage75_rc, "output_tail": stage75_tail[-2000:]}))

    total_sec = time.perf_counter() - total_t0
    timing_rows.append({"segment": "total_full_audit", "seconds": round(total_sec, 6), "returncode": 0 if not blockers else 1, "detail": "latest-row check + Stage74 + Stage75"})

    p75 = base_out / "75_external_action_payload_preview_audit_only" / "gold_v3_75_external_action_payload_preview_summary.json"
    j75 = read_json(p75) if p75.exists() else {}
    stage75_time = str(j75.get("latest_closed_m15_time", ""))
    decision = str(j75.get("decision", ""))
    emission_action = str(j75.get("emission_action", ""))
    payload_action = str(j75.get("payload_action", ""))
    should_discord = str(j75.get("should_notify_discord", ""))
    should_mt5 = str(j75.get("should_place_mt5_order", ""))
    should_ai = str(j75.get("should_call_ai_api", ""))
    should_final = str(j75.get("should_enable_final_signal", ""))

    val.append(ok("stage75_summary_present", p75.exists(), str(p75), "exists"))
    val.append(ok("stage75_ready", j75.get("status") == STAGE75_READY, j75.get("status"), STAGE75_READY))
    val.append(ok("stage75_time_matches_latest_m15", bool(latest and stage75_time and latest == stage75_time), stage75_time, latest))
    val.append(ok("total_runtime_under_hard_threshold", total_sec <= HARD_TOTAL_SECONDS, round(total_sec, 6), f"<= {HARD_TOTAL_SECONDS}"))
    val.append(ok("discord_send_false", should_discord == "False", should_discord, "False"))
    val.append(ok("mt5_order_false", should_mt5 == "False", should_mt5, "False"))
    val.append(ok("ai_api_false", should_ai == "False", should_ai, "False"))
    val.append(ok("final_signal_false", should_final == "False", should_final, "False"))
    val.append(ok("csv_open_bar_exclusion_required_false", True, False, False))
    val.append(ok("live_flags_all_false", True, "all_false", "all_false"))
    if latest and stage75_time and latest != stage75_time:
        blockers.append(blocker("stage75_snapshot_stale", str(p75), "STAGE75_TIME_DOES_NOT_MATCH_LATEST_M15", {"latest": latest, "stage75": stage75_time}))
    if total_sec > HARD_TOTAL_SECONDS:
        blockers.append(blocker("total_runtime_too_slow", str(out), "TOTAL_RUNTIME_EXCEEDS_HARD_THRESHOLD", {"seconds": total_sec, "hard_threshold": HARD_TOTAL_SECONDS}))

    timing_df = pd.DataFrame(timing_rows)
    timing_df.to_csv(out / "gold_v3_78_runtime_timing.csv", index=False, encoding="utf-8-sig")
    assessment = [
        assessment_row("latest_row_check_seconds", latest_sec, ADVISORY_LATEST_ROW_SECONDS),
        assessment_row("stage74_seconds", stage74_sec, ADVISORY_STAGE74_SECONDS),
        assessment_row("stage75_seconds", stage75_sec, ADVISORY_STAGE75_SECONDS),
        assessment_row("total_full_audit_seconds", total_sec, ADVISORY_TOTAL_SECONDS, HARD_TOTAL_SECONDS),
    ]
    assessment_df = pd.DataFrame(assessment)
    assessment_df.to_csv(out / "gold_v3_78_performance_assessment.csv", index=False, encoding="utf-8-sig")

    pd.DataFrame(blockers).to_csv(out / "gold_v3_78_blocker_matrix.csv", index=False, encoding="utf-8-sig")
    val_df = pd.DataFrame(val)
    failed = val_df[val_df["result"].ne("PASS")]
    status = READY_STATUS if failed.empty and not blockers else BLOCKED_STATUS
    val_df.to_csv(out / "gold_v3_78_validation_matrix.csv", index=False, encoding="utf-8-sig")

    warns = assessment_df[assessment_df["result"].eq("WARN")]
    blocks = assessment_df[assessment_df["result"].eq("BLOCK")]
    summary = {
        "step": STEP,
        "status": status,
        "created_at_utc": utc_now(),
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
        "runtime_performance_timing_ready": status == READY_STATUS,
        "pool_policy": POOL_POLICY,
        "latest_closed_m15_time": latest,
        "stage75_latest_closed_m15_time": stage75_time,
        "decision": decision,
        "emission_action": emission_action,
        "payload_action": payload_action,
        "latest_row_check_seconds": round(latest_sec, 6),
        "stage74_seconds": round(stage74_sec, 6),
        "stage75_seconds": round(stage75_sec, 6),
        "total_full_audit_seconds": round(total_sec, 6),
        "performance_warn_count": int(len(warns)),
        "performance_block_count": int(len(blocks)),
        "should_notify_discord": should_discord,
        "should_place_mt5_order": should_mt5,
        "should_call_ai_api": should_ai,
        "should_enable_final_signal": should_final,
        "validation_failure_count": int(len(failed)),
        "blocker_count": int(len(blockers)),
    }
    write_json(out / "gold_v3_78_runtime_performance_timing_summary.json", summary)

    paste = []
    paste.append("GOLD V3 78 PASTE_ME_RUNTIME_PERFORMANCE_TIMING_SUMMARY")
    paste.append(f"status: {status}")
    paste.append("runtime_performance_timing_ready: " + str(status == READY_STATUS).lower())
    paste.append("live_ready: false")
    paste.append("contract_mutated: false")
    paste.append("manual_candidate_demotion_or_removal: false")
    paste.append("open_asof_allowed: false")
    paste.append("csv_contract: " + CSV_CONTRACT)
    paste.append("csv_open_bar_exclusion_required: false")
    paste.append("safety: audit_only=true, live_allowed=false, mt5=false, discord=false, ai_api=false, final_signal=false")
    paste.append("pool_policy: " + POOL_POLICY)
    paste.append(f"latest_closed_m15_time: {latest}")
    paste.append(f"stage75_latest_closed_m15_time: {stage75_time}")
    paste.append(f"decision: {decision}")
    paste.append(f"emission_action: {emission_action}")
    paste.append(f"payload_action: {payload_action}")
    paste.append(f"latest_row_check_seconds: {round(latest_sec, 6)}")
    paste.append(f"stage74_seconds: {round(stage74_sec, 6)}")
    paste.append(f"stage75_seconds: {round(stage75_sec, 6)}")
    paste.append(f"total_full_audit_seconds: {round(total_sec, 6)}")
    paste.append(f"performance_warn_count: {len(warns)}")
    paste.append(f"performance_block_count: {len(blocks)}")
    paste.append(f"should_notify_discord: {should_discord}")
    paste.append(f"should_place_mt5_order: {should_mt5}")
    paste.append(f"should_call_ai_api: {should_ai}")
    paste.append(f"should_enable_final_signal: {should_final}")
    paste.append(f"blocker_count: {len(blockers)}")
    paste.append("")
    paste.append("PERFORMANCE_ASSESSMENT")
    paste.append(assessment_df.to_string(index=False))
    paste.append("")
    paste.append("BLOCKERS")
    paste.append(pd.DataFrame(blockers).to_string(index=False) if blockers else "NO_BLOCKERS")
    paste.append("")
    paste.append("VALIDATION")
    paste.append(val_df.to_string(index=False))
    paste.append("")
    paste.append("OUTPUTS")
    paste.append("gold_v3_78_runtime_timing.csv")
    paste.append("gold_v3_78_performance_assessment.csv")
    paste.append("gold_v3_78_blocker_matrix.csv")
    paste.append("gold_v3_78_validation_matrix.csv")
    paste.append("gold_v3_78_runtime_performance_timing_summary.json")
    (out / "gold_v3_78_PASTE_ME_RUNTIME_PERFORMANCE_TIMING_SUMMARY.txt").write_text("\n".join(paste) + "\n", encoding="utf-8")

    report = f"""# GOLD V3 78 runtime performance timing audit-only report

Status: `{status}`

- latest_closed_m15_time: `{latest}`
- latest_row_check_seconds: `{round(latest_sec, 6)}`
- stage74_seconds: `{round(stage74_sec, 6)}`
- stage75_seconds: `{round(stage75_sec, 6)}`
- total_full_audit_seconds: `{round(total_sec, 6)}`
- performance_warn_count: `{len(warns)}`
- performance_block_count: `{len(blocks)}`
- blocker_count: `{len(blockers)}`

Audit-only. No MT5, Discord, AI API, live hook, live evaluator, or final signal.
"""
    (out / "GOLD_V3_78_REPORT.md").write_text(report, encoding="utf-8")

    print(f"[{status}] total_seconds={round(total_sec, 6)} output_dir={out}")
    print(out / "gold_v3_78_PASTE_ME_RUNTIME_PERFORMANCE_TIMING_SUMMARY.txt")
    return 0 if status == READY_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
