#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GOLD V3 Stage242 - fixed Stage199 bridge + Stage234 coordinator supervisor.

This replaces Stage241 after the Stage240 SyntaxError fix.
It imports Stage199 frozen logic and writes latest_state before calling Stage234.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import signal
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd

import gold_v3_199_scalp_filtered_v1_ohlc_recomputed_freeze_audit as s199

STAGE = "GOLD_V3_242_STAGE199_FIXED_BRIDGE_AND_DEMO_COORDINATOR_SUPERVISOR"
READY_DECISION = "STAGE242_STAGE199_FIXED_BRIDGE_AND_DEMO_COORDINATOR_SUPERVISOR_READY"
BLOCKED_DECISION = "STAGE242_STAGE199_FIXED_BRIDGE_AND_DEMO_COORDINATOR_SUPERVISOR_BLOCKED"
TERMINAL_HASH = "2FA8A7E69CED7DC259B1AD86A247F675"

OFF_FLAGS = {
    "stage242_direct_discord_webhook_called": False,
    "stage242_direct_mt5_order_send_called": False,
    "stage242_direct_order_placed": False,
    "position_close_called": False,
    "position_modify_called": False,
    "real_account_allowed": False,
    "final_live_enabled": False,
    "payload_activation_enabled": False,
    "live_hook_enabled": False,
    "autotrade_enabled": False,
    "no_signal_order_allowed": False,
    "no_signal_discord_notify": False,
    "source_csv_mutated": False,
    "contract_mutated": False,
    "candidate_pool_removed": False,
    "f002_exclusion_bypassed": False,
    "open_asof_allowed": False,
    "theoretical_result_used_as_input": False,
    "actual_execution_used_as_input": False,
}

CYCLE_COLUMNS = [
    "created_at_utc", "stage", "cycle_index", "bridge_return_code", "stage234_return_code",
    "runtime_queue_rows_seen", "bridge_tail", "stage234_tail",
]

STATE_LEDGER_COLUMNS = [
    "created_at_utc", "latest_closed_m15_dt", "selected_family", "final_route", "signal_id",
    "short_signal_id", "strategy_role", "candidate_id", "direction", "entry_price",
    "tp_usd", "sl_usd", "horizon_m5_bars", "abc_candidate_id", "scalp_candidate_id", "reason",
]

_INTERRUPTED = False


def _handle_signal(signum: int, frame: Any) -> None:
    global _INTERRUPTED
    _INTERRUPTED = True


signal.signal(signal.SIGINT, _handle_signal)
signal.signal(signal.SIGTERM, _handle_signal)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def json_safe(v: Any) -> Any:
    if isinstance(v, (str, int, bool)) or v is None:
        return v
    if isinstance(v, float):
        return v if math.isfinite(v) else None
    if isinstance(v, (pd.Timestamp, datetime)):
        return str(v)
    if isinstance(v, dict):
        return {str(k): json_safe(val) for k, val in v.items()}
    if isinstance(v, (list, tuple)):
        return [json_safe(x) for x in v]
    try:
        if pd.isna(v):
            return None
    except Exception:
        pass
    return str(v)


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(json_safe(payload), ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def read_csv_rows(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def append_csv(path: Path, row: Dict[str, Any], columns: List[str]) -> None:
    exists = path.exists()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        if not exists:
            w.writeheader()
        w.writerow(json_safe(row))


def append_csv_rows(path: Path, rows: List[Dict[str, Any]], columns: List[str]) -> None:
    exists = path.exists()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        if not exists:
            w.writeheader()
        for r in rows:
            w.writerow(json_safe(r))


def fmt_dt(v: Any) -> str:
    if v is None or str(v).lower() in {"", "nat", "nan", "none"}:
        return ""
    return pd.Timestamp(v).strftime("%Y-%m-%d %H:%M:%S")


def clean_str(v: Any) -> str:
    if v is None:
        return ""
    s = str(v).strip()
    return "" if s.lower() in {"nan", "nat", "none"} else s


def num_or_none(v: Any) -> float | None:
    try:
        x = float(v)
        return x if math.isfinite(x) else None
    except Exception:
        return None


def side_from_direction(direction: str) -> str:
    d = str(direction).upper().strip()
    if d in {"LONG", "BUY"}:
        return "BUY"
    if d in {"SHORT", "SELL"}:
        return "SELL"
    return ""


def short_hash(text: str) -> str:
    return "G3S" + hashlib.sha256(text.encode("utf-8")).hexdigest()[:20].upper()


def build_signal_id(dt: str, family: str, candidate_id: str, direction: str) -> str:
    compact = dt.replace("-", "").replace(":", "").replace(" ", "_")
    return f"GOLDV3_199_{compact}_{family}_{candidate_id}_{direction}".replace("__", "_")


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


def paths(data_dir: Path) -> Dict[str, Path]:
    root = data_dir / "FX_OUTPUTS" / "gold_v3"
    out = root / "242"
    work = out / "stage199_fixed_bridge_and_demo_coordinator_supervisor"
    retention = root / "217" / "staging_retention"
    runtime = root / "runtime"
    return {
        "root": root,
        "out": out,
        "work": work,
        "selected": root / "193" / "gold_v3_193_scalping_selected_profit_stack_watchlist.csv",
        "latest_state": retention / "latest_state.json",
        "trade_ledger": retention / "trade_signal_ledger.csv",
        "no_signal": retention / "no_signal_counter.csv",
        "runtime_queue": runtime / "alert_only_queue.csv",
        "state_ledger": work / "stage242_latest_state_ledger.csv",
        "cycle_ledger": work / "stage242_cycle_ledger.csv",
        "latest_preview": work / "stage242_latest_preview.json",
        "summary": work / "stage242_summary.json",
        "decision": work / "stage242_decision.csv",
        "paste": out / "paste_me.txt",
        "kill_switch": root / "KILL_SWITCH_STAGE242.txt",
        "stage234_kill_switch": root / "KILL_SWITCH_STAGE234.txt",
        "stage233_kill_switch": root / "KILL_SWITCH_STAGE233.txt",
    }


def existing_signal_ids(path: Path) -> set[str]:
    return {str(r.get("signal_id") or "") for r in read_csv_rows(path) if r.get("signal_id")}


def load_inputs(data_dir: Path, p: Dict[str, Path]) -> Tuple[pd.DataFrame, Dict[str, pd.DataFrame], List[str]]:
    blockers: List[str] = []
    selected = s199.read_csv_any(p["selected"])
    if selected.empty:
        blockers.append(f"missing_stage193_selected_watchlist: {p['selected']}")
        return selected, {}, blockers
    frames: Dict[str, pd.DataFrame] = {}
    for tf in ["m15", "m5", "h1", "h4", "d1"]:
        df, diag = s199.s177.combine(tf, data_dir)
        frames[tf] = df
        if df.empty:
            blockers.append(f"missing_ohlc_{tf}")
    return selected, frames, blockers


def build_features(frames: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    return s199.s177.base.merge_features(
        frames["m15"], frames["h1"], frames["h4"], frames["d1"]
    ).sort_values("dt").reset_index(drop=True)


def abc_latest_signal(feat: pd.DataFrame) -> Dict[str, Any]:
    if feat.empty:
        return {"has_signal": False}
    latest_dt = pd.Timestamp(feat["dt"].iloc[-1])
    choices: List[Dict[str, Any]] = []
    for c in s199.ABC_CANDIDATES:
        mask, problems = s199.s179.literal_rule_mask(c["rule"], feat)
        if problems or mask is None or len(mask) != len(feat):
            continue
        hit = bool(pd.Series(mask).iloc[-1])
        if not hit:
            continue
        row = feat.iloc[-1]
        choices.append({
            "has_signal": True,
            "family": "ABC",
            "strategy_role": "DAYTRADE_PRIMARY_ABC",
            "candidate_id": c["candidate_id"],
            "direction": c["direction"],
            "entry_price": num_or_none(row.get("m15_close")),
            "tp_usd": float(c["tp"]),
            "sl_usd": float(c["sl"]),
            "horizon_m5_bars": int(c["horizon_m5"]),
            "priority_score": 5000.0 - float(c["priority"]),
            "rule": c["rule"],
            "dt": latest_dt,
        })
    if not choices:
        return {"has_signal": False}
    return sorted(choices, key=lambda x: float(x.get("priority_score") or 0), reverse=True)[0]


def scalp_latest_signal(feat: pd.DataFrame, selected: pd.DataFrame) -> Dict[str, Any]:
    if feat.empty or selected.empty:
        return {"has_signal": False}
    priority = s199.selected_priority(selected)
    _tail, info = s199.latest_snapshot(feat, selected, priority)
    cid = clean_str(info.get("candidate_id"))
    sig = clean_str(info.get("priority_signal"))
    if not cid or sig == "NO_SIGNAL":
        return {"has_signal": False}
    return {
        "has_signal": True,
        "family": "SCALP",
        "strategy_role": "SCALP_SECONDARY_WATCHLIST",
        "candidate_id": cid,
        "direction": clean_str(info.get("direction") or sig),
        "entry_price": num_or_none(info.get("m15_close")),
        "tp_usd": num_or_none(info.get("tp")),
        "sl_usd": num_or_none(info.get("sl")),
        "horizon_m5_bars": int(num_or_none(info.get("horizon_m5")) or 0),
        "priority_score": num_or_none(info.get("priority_score")),
        "dt": info.get("dt"),
    }


def select_state(latest_dt: str, abc: Dict[str, Any], scalp: Dict[str, Any]) -> Dict[str, Any]:
    if abc.get("has_signal"):
        selected = dict(abc)
        selected["selected_family"] = "ABC_PRIMARY"
        selected["final_route"] = "ABC_PRIMARY_SIGNAL"
        selected["reason"] = "ABC_PRIMARY_SELECTED_OVER_SCALP_SECONDARY"
    elif scalp.get("has_signal"):
        selected = dict(scalp)
        selected["selected_family"] = "SCALP_SECONDARY"
        selected["final_route"] = "SCALP_SECONDARY_SIGNAL"
        selected["reason"] = "SCALP_SECONDARY_SELECTED_NO_ABC_PRIMARY"
    else:
        selected = {
            "has_signal": False,
            "selected_family": "NO_SIGNAL",
            "final_route": "NO_SIGNAL",
            "strategy_role": "",
            "candidate_id": "",
            "direction": "",
            "entry_price": None,
            "tp_usd": None,
            "sl_usd": None,
            "horizon_m5_bars": None,
            "reason": "NO_STAGE199_ABC_OR_SCALP_SIGNAL_ON_LATEST_CLOSED_M15",
        }
    selected["latest_closed_m15_dt"] = latest_dt
    selected["entry_dt"] = latest_dt if selected.get("has_signal") else ""
    if selected.get("has_signal"):
        direction = side_from_direction(str(selected.get("direction", "")))
        selected["direction"] = direction
        sid = build_signal_id(latest_dt, selected["selected_family"], str(selected["candidate_id"]), direction)
        selected["signal_id"] = sid
        selected["short_signal_id"] = short_hash(sid)
    else:
        selected["signal_id"] = ""
        selected["short_signal_id"] = ""
    return selected


def make_latest_state(selected: Dict[str, Any], abc: Dict[str, Any], scalp: Dict[str, Any]) -> Dict[str, Any]:
    state = {
        "stage": STAGE,
        "created_at_utc": utc_now_iso(),
        "symbol": "GOLD#",
        "source_symbol_basis": "XAUUSD/GOLD# OHLC bridge",
        "detector_source_stage": "GOLD_V3_199_SCALP_FILTERED_V1_OHLC_RECOMPUTED_FREEZE_AUDIT_ONLY",
        "detector_source_file": "scripts/gold_v3_runtime/gold_v3_199_scalp_filtered_v1_ohlc_recomputed_freeze_audit.py",
        "filtered_scalp_id": s199.FILTERED_SCALP_ID,
        "abc_role": "PRIMARY",
        "scalp_role": "SECONDARY_WATCHLIST",
        "latest_closed_m15_dt": selected.get("latest_closed_m15_dt", ""),
        "entry_dt": selected.get("entry_dt", ""),
        "final_route": selected.get("final_route", "NO_SIGNAL"),
        "signal_id": selected.get("signal_id", ""),
        "short_signal_id": selected.get("short_signal_id", ""),
        "strategy_role": selected.get("strategy_role", ""),
        "candidate_id": selected.get("candidate_id", ""),
        "direction": selected.get("direction", ""),
        "entry_price": selected.get("entry_price"),
        "tp_usd": selected.get("tp_usd"),
        "sl_usd": selected.get("sl_usd"),
        "horizon_m5_bars": selected.get("horizon_m5_bars"),
        "selected_family": selected.get("selected_family", "NO_SIGNAL"),
        "selection_reason": selected.get("reason", ""),
        "abc_has_signal": bool(abc.get("has_signal")),
        "abc_candidate_id": abc.get("candidate_id", ""),
        "abc_direction": side_from_direction(str(abc.get("direction", ""))) if abc.get("has_signal") else "",
        "abc_entry_price": abc.get("entry_price"),
        "abc_tp_usd": abc.get("tp_usd"),
        "abc_sl_usd": abc.get("sl_usd"),
        "abc_horizon_m5_bars": abc.get("horizon_m5_bars"),
        "scalp_has_signal": bool(scalp.get("has_signal")),
        "scalp_candidate_id": scalp.get("candidate_id", ""),
        "scalp_direction": side_from_direction(str(scalp.get("direction", ""))) if scalp.get("has_signal") else "",
        "scalp_entry_price": scalp.get("entry_price"),
        "scalp_tp_usd": scalp.get("tp_usd"),
        "scalp_sl_usd": scalp.get("sl_usd"),
        "scalp_horizon_m5_bars": scalp.get("horizon_m5_bars"),
        "csv_latest_row_contract": "CLOSED",
        "timestamp_basis": "CSV_MT5_NO_JST_CONVERSION",
        "stage199_imported": True,
    }
    state.update(OFF_FLAGS)
    return state


def run_bridge(data_dir: Path, p: Dict[str, Path]) -> Tuple[int, str, Dict[str, Any]]:
    summary: Dict[str, Any] = {
        "step": STAGE,
        "created_at_utc": utc_now_iso(),
        "output_dir": str(p["out"]),
        "work_dir": str(p["work"]),
        "selected_watchlist_exists": p["selected"].exists(),
        "stage199_file_imported": True,
        "latest_state_written": False,
        "trade_ledger_appended": False,
        "no_signal_counter_appended": False,
        "csv_latest_row_contract": "CLOSED",
    }
    summary.update(OFF_FLAGS)
    blockers: List[str] = []
    state: Dict[str, Any] = {}
    try:
        selected, frames, input_blockers = load_inputs(data_dir, p)
        blockers.extend(input_blockers)
        if not blockers:
            feat = build_features(frames)
            if feat.empty:
                blockers.append("feature_frame_empty")
            else:
                latest_dt = fmt_dt(feat["dt"].iloc[-1])
                abc = abc_latest_signal(feat)
                scalp = scalp_latest_signal(feat, selected)
                selected_state = select_state(latest_dt, abc, scalp)
                state = make_latest_state(selected_state, abc, scalp)
                write_json(p["latest_state"], state)
                summary["latest_state_written"] = True
                if state.get("signal_id"):
                    if state["signal_id"] not in existing_signal_ids(p["trade_ledger"]):
                        append_csv(p["trade_ledger"], state, STATE_LEDGER_COLUMNS)
                        summary["trade_ledger_appended"] = True
                else:
                    append_csv(p["no_signal"], {
                        "created_at_utc": utc_now_iso(),
                        "latest_closed_m15_dt": state.get("latest_closed_m15_dt"),
                        "final_route": "NO_SIGNAL",
                        "reason": state.get("selection_reason"),
                        "stage": STAGE,
                    }, ["created_at_utc", "latest_closed_m15_dt", "final_route", "reason", "stage"])
                    summary["no_signal_counter_appended"] = True
                append_csv(p["state_ledger"], state, STATE_LEDGER_COLUMNS)
                write_json(p["latest_preview"], {"state": state})
                summary.update({
                    "latest_closed_m15_dt": state.get("latest_closed_m15_dt"),
                    "final_route": state.get("final_route"),
                    "signal_id": state.get("signal_id"),
                    "short_signal_id": state.get("short_signal_id"),
                    "selected_family": state.get("selected_family"),
                    "strategy_role": state.get("strategy_role"),
                    "candidate_id": state.get("candidate_id"),
                    "direction": state.get("direction"),
                    "entry_price": state.get("entry_price"),
                    "tp_usd": state.get("tp_usd"),
                    "sl_usd": state.get("sl_usd"),
                    "horizon_m5_bars": state.get("horizon_m5_bars"),
                    "abc_has_signal": state.get("abc_has_signal"),
                    "abc_candidate_id": state.get("abc_candidate_id"),
                    "scalp_has_signal": state.get("scalp_has_signal"),
                    "scalp_candidate_id": state.get("scalp_candidate_id"),
                })
    except Exception as exc:
        blockers.append(f"EXCEPTION: {type(exc).__name__}: {exc}")
    summary["blockers"] = blockers
    summary["blocker_count"] = len(blockers)
    summary["status"] = "READY" if not blockers else "BLOCKED"
    summary["ready"] = not blockers
    summary["decision"] = "STAGE242_BRIDGE_READY" if not blockers else "STAGE242_BRIDGE_BLOCKED"
    write_json(p["summary"], summary)
    append_csv(p["decision"], summary, [
        "created_at_utc", "step", "status", "ready", "decision", "latest_closed_m15_dt",
        "final_route", "signal_id", "selected_family", "candidate_id", "direction", "blocker_count",
    ])
    text = " ".join([
        f"bridge_status={summary['status']}",
        f"latest_closed_m15_dt={summary.get('latest_closed_m15_dt')}",
        f"final_route={summary.get('final_route')}",
        f"selected_family={summary.get('selected_family')}",
        f"signal_id={summary.get('signal_id')}",
        f"blockers={blockers}",
    ])
    return (0 if not blockers else 2), text, summary


def run_cmd(args: List[str], timeout: int) -> Tuple[int, str]:
    result = subprocess.run(args, cwd=str(repo_root()), capture_output=True, text=True, timeout=timeout)
    text = result.stdout or ""
    if result.stderr:
        text += "\n" + result.stderr
    return result.returncode, text[-3000:]


def kill_state(p: Dict[str, Path]) -> Dict[str, bool]:
    return {
        "kill_switch_present": p["kill_switch"].exists(),
        "stage234_kill_switch_present": p["stage234_kill_switch"].exists(),
        "stage233_kill_switch_present": p["stage233_kill_switch"].exists(),
    }


def validate(summary: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], List[str]]:
    checks: List[Dict[str, Any]] = []
    def add(cid: str, passed: bool, details: str) -> None:
        checks.append({"check_id": cid, "passed": bool(passed), "details": details})
    add("S242001", summary.get("stage234_script_exists") is True, "Stage234 coordinator exists")
    add("S242002", int(summary.get("failed_bridge_count") or 0) == 0, f"failed_bridge_count={summary.get('failed_bridge_count')}")
    add("S242003", int(summary.get("failed_stage234_count") or 0) == 0, f"failed_stage234_count={summary.get('failed_stage234_count')}")
    add("S242004", all(summary.get(k) is False for k in OFF_FLAGS.keys()), "restricted flags OFF")
    return checks, [f"{c['check_id']}: {c['details']}" for c in checks if not c["passed"]]


def write_paste(path: Path, summary: Dict[str, Any], checks: List[Dict[str, Any]]) -> None:
    lines = ["GOLD V3 242 PASTE_ME_STAGE199_FIXED_BRIDGE_AND_DEMO_COORDINATOR_SUPERVISOR"]
    keys = [
        "step", "status", "ready", "decision", "created_at_utc", "updated_at_utc", "continuous_mode",
        "cycle_count_completed", "bridge_success_count", "stage234_success_count", "failed_bridge_count",
        "failed_stage234_count", "runtime_queue_exists_last", "runtime_queue_rows_last", "interrupted",
        "stop_reason", "kill_switch_present", "stage234_kill_switch_present", "stage233_kill_switch_present",
        "last_bridge_final_route", "last_bridge_selected_family", "last_bridge_signal_id", "blocker_count",
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
    lines.append("Stage242 fixes the Stage240 SyntaxError by using a corrected Stage199 bridge. It updates latest_state from Stage199 ABC PRIMARY + SCALP SECONDARY logic, then calls Stage234.")
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
    if summary.get("interrupted"):
        summary["stop_reason"] = "INTERRUPTED"
    elif summary.get("kill_switch_present"):
        summary["stop_reason"] = "KILL_SWITCH_PRESENT"
    elif summary.get("stage234_kill_switch_present"):
        summary["stop_reason"] = "STAGE234_KILL_SWITCH_PRESENT"
    elif summary.get("stage233_kill_switch_present"):
        summary["stop_reason"] = "STAGE233_KILL_SWITCH_PRESENT"
    elif int(summary.get("failed_bridge_count") or 0) > 0:
        summary["stop_reason"] = "BRIDGE_FAILURE"
    elif int(summary.get("failed_stage234_count") or 0) > 0:
        summary["stop_reason"] = "STAGE234_FAILURE"
    else:
        summary["stop_reason"] = "RUNNING_OR_NOT_STARTED"
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
    data_dir = s199.gy.mt5_files_dir(args.mt5_files_dir) if args.mt5_files_dir else mql5_files_dir()
    p = paths(data_dir)
    p["out"].mkdir(parents=True, exist_ok=True)
    p["work"].mkdir(parents=True, exist_ok=True)
    stage234 = repo_root() / "scripts" / "gold_v3_runtime" / "gold_v3_234_discord_and_demo_order_loop_coordinator.py"
    summary: Dict[str, Any] = {
        "step": STAGE,
        "created_at_utc": utc_now_iso(),
        "updated_at_utc": utc_now_iso(),
        "continuous_mode": args.cycles == 0,
        "cycle_count_completed": 0,
        "stage234_script_exists": stage234.exists(),
        "bridge_success_count": 0,
        "stage234_success_count": 0,
        "failed_bridge_count": 0,
        "failed_stage234_count": 0,
        "runtime_queue_exists_last": p["runtime_queue"].exists(),
        "runtime_queue_rows_last": len(read_csv_rows(p["runtime_queue"])),
        "interrupted": False,
        "stop_reason": "RUNNING_OR_NOT_STARTED",
        "last_bridge_final_route": "",
        "last_bridge_selected_family": "",
        "last_bridge_signal_id": "",
        "output_files": {
            "cycle_ledger_csv": str(p["cycle_ledger"]),
            "latest_state_json": str(p["latest_state"]),
            "state_ledger_csv": str(p["state_ledger"]),
            "summary_json": str(p["summary"]),
            "paste_me": str(p["paste"]),
            "kill_switch_stage242": str(p["kill_switch"]),
        },
    }
    summary.update(OFF_FLAGS)
    refresh(summary, p)
    if not stage234.exists():
        return 2
    try:
        cycle = 0
        while True:
            summary["interrupted"] = bool(_INTERRUPTED)
            summary.update(kill_state(p))
            if _INTERRUPTED or summary.get("kill_switch_present") or summary.get("stage234_kill_switch_present") or summary.get("stage233_kill_switch_present"):
                break
            if args.cycles > 0 and cycle >= args.cycles:
                break
            cycle += 1
            c_bridge, t_bridge, bridge_summary = run_bridge(data_dir, p)
            if c_bridge == 0:
                summary["bridge_success_count"] += 1
            else:
                summary["failed_bridge_count"] += 1
            summary["last_bridge_final_route"] = bridge_summary.get("final_route", "")
            summary["last_bridge_selected_family"] = bridge_summary.get("selected_family", "")
            summary["last_bridge_signal_id"] = bridge_summary.get("signal_id", "")
            c234, t234 = 999, "SKIPPED_BRIDGE_FAILED"
            if c_bridge == 0:
                c234, t234 = run_cmd([sys.executable, str(stage234), "--cycles", "1"], timeout=420)
                if c234 == 0:
                    summary["stage234_success_count"] += 1
                else:
                    summary["failed_stage234_count"] += 1
            summary["cycle_count_completed"] = cycle
            qrows = read_csv_rows(p["runtime_queue"])
            append_csv_rows(p["cycle_ledger"], [{
                "created_at_utc": utc_now_iso(),
                "stage": STAGE,
                "cycle_index": cycle,
                "bridge_return_code": c_bridge,
                "stage234_return_code": c234,
                "runtime_queue_rows_seen": len(qrows),
                "bridge_tail": str(t_bridge)[-800:],
                "stage234_tail": str(t234).replace("\r", " ").replace("\n", " ")[-800:],
            }], CYCLE_COLUMNS)
            refresh(summary, p)
            if c_bridge != 0 or c234 != 0:
                break
    except KeyboardInterrupt:
        summary["interrupted"] = True
    except Exception as exc:
        summary.setdefault("blockers", [])
        summary["blockers"].append(f"EXCEPTION: {type(exc).__name__}: {exc}")
    summary["interrupted"] = summary.get("interrupted") or bool(_INTERRUPTED)
    refresh(summary, p)
    print(f"Stage242 status: {summary['status']}")
    print(f"decision: {summary['decision']}")
    print(f"cycle_count_completed: {summary['cycle_count_completed']}")
    print(f"bridge_success_count: {summary['bridge_success_count']}")
    print(f"stage234_success_count: {summary['stage234_success_count']}")
    print(f"runtime_queue_rows_last: {summary['runtime_queue_rows_last']}")
    print(f"last_bridge_final_route: {summary.get('last_bridge_final_route')}")
    print(f"last_bridge_selected_family: {summary.get('last_bridge_selected_family')}")
    print(f"paste_me: {p['paste']}")
    return 0 if not summary.get("blockers") else 2


if __name__ == "__main__":
    raise SystemExit(main())
