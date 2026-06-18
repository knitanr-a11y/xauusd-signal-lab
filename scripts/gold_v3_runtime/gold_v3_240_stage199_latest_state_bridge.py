#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GOLD V3 Stage240 - Stage199 latest_state bridge.

Uses Stage199 frozen logic as source:
- ABC remains PRIMARY and is emitted as DAYTRADE_PRIMARY_ABC.
- SCALP_ONE_POSITION_FILTERED_V1_OHLC_RECOMPUTED remains SECONDARY and is emitted as SCALP_SECONDARY_WATCHLIST.

Stage240 itself does not send Discord and does not call MT5. It only writes the
Stage217 staging latest_state that Stage227 already consumes.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

import numpy as np
import pandas as pd

import gold_v3_199_scalp_filtered_v1_ohlc_recomputed_freeze_audit as s199

STEP = "GOLD_V3_240_STAGE199_ABC_PRIMARY_SCALP_SECONDARY_LATEST_STATE_BRIDGE"
READY_DECISION = "STAGE240_STAGE199_LATEST_STATE_BRIDGE_READY"
BLOCKED_DECISION = "STAGE240_STAGE199_LATEST_STATE_BRIDGE_BLOCKED"

OFF_FLAGS: Dict[str, bool] = {
    "stage240_direct_discord_webhook_called": False,
    "stage240_direct_mt5_order_send_called": False,
    "stage240_direct_order_placed": False,
    "position_close_called": False,
    "position_modify_called": False,
    "real_account_allowed": False,
    "final_live_enabled": False,
    "payload_activation_enabled": False,
    "live_hook_enabled": False,
    "autotrade_enabled": False,
    "no_signal_discord_notify": False,
    "no_signal_order_allowed": False,
    "source_csv_mutated": False,
    "contract_mutated": False,
    "candidate_pool_removed": False,
    "f002_exclusion_bypassed": False,
    "open_asof_allowed": False,
    "theoretical_result_used_as_input": False,
    "actual_execution_used_as_input": False,
}

LEDGER_COLUMNS = [
    "created_at_utc", "latest_closed_m15_dt", "selected_family", "final_route", "signal_id",
    "short_signal_id", "strategy_role", "candidate_id", "direction", "entry_price",
    "tp_usd", "sl_usd", "horizon_m5_bars", "abc_candidate_id", "scalp_candidate_id",
    "reason",
]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def json_safe(v: Any) -> Any:
    if isinstance(v, (str, int, float, bool)) or v is None:
        if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
            return None
        return v
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


def append_csv(path: Path, row: Dict[str, Any], columns: List[str]) -> None:
    exists = path.exists()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        if not exists:
            writer.writeheader()
        writer.writerow(json_safe(row))


def read_csv_rows(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def existing_signal_ids(path: Path) -> set[str]:
    return {str(r.get("signal_id") or "") for r in read_csv_rows(path) if r.get("signal_id")}


def fmt_dt(v: Any) -> str:
    if v is None or str(v) in {"", "NaT", "nan"}:
        return ""
    try:
        return pd.Timestamp(v).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return str(v)


def clean_str(v: Any) -> str:
    if v is None:
        return ""
    s = str(v).strip()
    return "" if s.lower() in {"nan", "nat", "none"} else s


def num_or_none(v: Any) -> float | None:
    try:
        x = float(v)
        if math.isfinite(x):
            return x
    except Exception:
        return None
    return None


def short_hash(text: str) -> str:
    return "G3S" + hashlib.sha256(text.encode("utf-8")).hexdigest()[:20].upper()


def side_from_direction(direction: str) -> str:
    d = direction.upper().strip()
    if d in {"LONG", "BUY"}:
        return "BUY"
    if d in {"SHORT", "SELL"}:
        return "SELL"
    return ""


def build_signal_id(dt: str, family: str, candidate_id: str, direction: str) -> str:
    compact = dt.replace("-", "").replace(":", "").replace(" ", "_")
    return f"GOLDV3_199_{compact}_{family}_{candidate_id}_{direction}".replace("__", "_")


def paths(data_dir: Path) -> Dict[str, Path]:
    root = data_dir / "FX_OUTPUTS" / "gold_v3"
    out = root / "240"
    work = out / "stage199_latest_state_bridge"
    retention = root / "217" / "staging_retention"
    return {
        "root": root,
        "out": out,
        "work": work,
        "selected": root / "193" / "gold_v3_193_scalping_selected_profit_stack_watchlist.csv",
        "latest_state": retention / "latest_state.json",
        "trade_ledger": retention / "trade_signal_ledger.csv",
        "no_signal": retention / "no_signal_counter.csv",
        "summary": work / "stage240_summary.json",
        "decision": work / "stage240_decision.csv",
        "latest_preview": work / "stage240_latest_preview.json",
        "ledger": work / "stage240_latest_state_ledger.csv",
        "paste": out / "paste_me.txt",
    }


def load_stage199_inputs(data_dir: Path, p: Dict[str, Path]) -> Tuple[pd.DataFrame, Dict[str, pd.DataFrame], List[Dict[str, Any]], List[Dict[str, Any]]]:
    blockers: List[Dict[str, Any]] = []
    selected = s199.read_csv_any(p["selected"])
    if selected.empty:
        blockers.append({"id": "missing_stage193_selected_watchlist", "path": str(p["selected"])})
    frames: Dict[str, pd.DataFrame] = {}
    source_rows: List[Dict[str, Any]] = []
    if not blockers:
        for tf in ["m15", "m5", "h1", "h4", "d1"]:
            frames[tf], diag = s199.s177.combine(tf, data_dir)
            source_rows.extend(diag)
            if frames[tf].empty:
                blockers.append({"id": "missing_ohlc", "tf": tf})
    return selected, frames, source_rows, blockers


def build_features(frames: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    return s199.s177.base.merge_features(frames["m15"], frames["h1"], frames["h4"], frames["d1"]).sort_values("dt").reset_index(drop=True)


def abc_latest_snapshot(feat: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any], List[Dict[str, Any]]]:
    rows: List[pd.DataFrame] = []
    problems: List[Dict[str, Any]] = []
    for c in s199.ABC_CANDIDATES:
        mask, rule_problems = s199.s179.literal_rule_mask(c["rule"], feat)
        if rule_problems:
            problems.append({"candidate_id": c["candidate_id"], "problems": rule_problems})
            continue
        m = feat.loc[mask, ["dt", "m15_close", "h1_atr14", "d1_dist_close_atr28", "h4_body_atr14"]].copy()
        if m.empty:
            continue
        m = m.rename(columns={"m15_close": "entry_price"})
        m["candidate_id"] = c["candidate_id"]
        m["family"] = "ABC"
        m["strategy_role"] = "DAYTRADE_PRIMARY_ABC"
        m["direction"] = c["direction"]
        m["tp_usd"] = float(c["tp"])
        m["sl_usd"] = float(c["sl"])
        m["horizon_m5_bars"] = int(c["horizon_m5"])
        m["priority_score"] = 5000.0 - float(c["priority"])
        m["rule"] = c["rule"]
        rows.append(m)
    tail = feat[["dt", "m15_close", "h1_atr14", "d1_dist_close_atr28", "h4_body_atr14"]].tail(96).copy()
    if not rows:
        tail["abc_signal"] = "NO_SIGNAL"
        tail["candidate_id"] = ""
        return tail, tail.iloc[-1].to_dict() if not tail.empty else {}, problems
    det = pd.concat(rows, ignore_index=True)
    picked = det[det["dt"].isin(set(pd.to_datetime(tail["dt")))].sort_values(["dt", "priority_score"], ascending=[True, False]).drop_duplicates("dt", keep="first")
    merged = tail.merge(picked[["dt", "candidate_id", "family", "strategy_role", "direction", "tp_usd", "sl_usd", "horizon_m5_bars", "priority_score", "entry_price", "rule"]], on="dt", how="left")
    merged["abc_signal"] = np.where(merged["candidate_id"].notna(), merged["direction"].astype(str), "NO_SIGNAL")
    return merged, merged.iloc[-1].to_dict() if not merged.empty else {}, problems


def scalp_from_latest_info(info: Dict[str, Any]) -> Dict[str, Any]:
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
    }


def abc_from_latest_info(info: Dict[str, Any]) -> Dict[str, Any]:
    cid = clean_str(info.get("candidate_id"))
    sig = clean_str(info.get("abc_signal"))
    if not cid or sig == "NO_SIGNAL":
        return {"has_signal": False}
    return {
        "has_signal": True,
        "family": "ABC",
        "strategy_role": "DAYTRADE_PRIMARY_ABC",
        "candidate_id": cid,
        "direction": clean_str(info.get("direction") or sig),
        "entry_price": num_or_none(info.get("entry_price") or info.get("m15_close")),
        "tp_usd": num_or_none(info.get("tp_usd")),
        "sl_usd": num_or_none(info.get("sl_usd")),
        "horizon_m5_bars": int(num_or_none(info.get("horizon_m5_bars")) or 0),
        "priority_score": num_or_none(info.get("priority_score")),
        "rule": clean_str(info.get("rule")),
    }


def select_runtime_state(latest_dt: str, abc: Dict[str, Any], scalp: Dict[str, Any]) -> Dict[str, Any]:
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


def make_latest_state(selected: Dict[str, Any], abc: Dict[str, Any], scalp: Dict[str, Any], detector_meta: Dict[str, Any]) -> Dict[str, Any]:
    state = {
        "stage": STEP,
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
        "stage199_imported": detector_meta.get("stage199_imported", True),
    }
    state.update(OFF_FLAGS)
    return state


def validate(summary: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], List[str]]:
    checks: List[Dict[str, Any]] = []
    def add(cid: str, passed: bool, details: str) -> None:
        checks.append({"check_id": cid, "passed": bool(passed), "details": details})
    add("L240001", summary.get("selected_watchlist_exists") is True, "Stage193 selected watchlist exists")
    add("L240002", summary.get("stage199_file_imported") is True, "Stage199 module imported")
    add("L240003", summary.get("latest_state_written") is True, "latest_state.json written")
    add("L240004", summary.get("latest_closed_m15_dt") not in {None, ""}, f"latest_closed_m15_dt={summary.get('latest_closed_m15_dt')}")
    add("L240005", summary.get("final_route") in {"NO_SIGNAL", "ABC_PRIMARY_SIGNAL", "SCALP_SECONDARY_SIGNAL"}, f"final_route={summary.get('final_route')}")
    add("L240006", all(summary.get(k) is False for k in OFF_FLAGS.keys()), "restricted flags OFF")
    add("L240007", summary.get("csv_latest_row_contract") == "CLOSED" and summary.get("open_asof_allowed") is False, "CSV latest row CLOSED, open/as-of prohibited")
    blockers = [f"{c['check_id']}: {c['details']}" for c in checks if not c["passed"]]
    return checks, blockers


def write_paste(path: Path, summary: Dict[str, Any], checks: List[Dict[str, Any]]) -> None:
    lines = ["GOLD V3 240 PASTE_ME_STAGE199_ABC_PRIMARY_SCALP_SECONDARY_LATEST_STATE_BRIDGE"]
    keys = [
        "step", "status", "ready", "decision", "created_at_utc", "output_dir", "work_dir",
        "selected_watchlist_exists", "stage199_file_imported", "latest_closed_m15_dt", "final_route",
        "signal_id", "short_signal_id", "selected_family", "strategy_role", "candidate_id", "direction",
        "entry_price", "tp_usd", "sl_usd", "horizon_m5_bars", "abc_has_signal", "abc_candidate_id",
        "scalp_has_signal", "scalp_candidate_id", "latest_state_written", "trade_ledger_appended",
        "no_signal_counter_appended", "blocker_count",
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
    lines.append("Stage240 used Stage199 frozen logic. ABC is PRIMARY; SCALP_FILTERED_V1 is SECONDARY/WATCHLIST. Stage240 itself did not send Discord and did not call MT5.")
    lines.append("")
    lines.append("BLOCKERS")
    if summary.get("blockers"):
        lines.extend(summary["blockers"])
    else:
        lines.append("NO_BLOCKERS")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mt5-files-dir", default="")
    args = ap.parse_args()

    data_dir = s199.gy.mt5_files_dir(args.mt5_files_dir)
    p = paths(data_dir)
    p["out"].mkdir(parents=True, exist_ok=True)
    p["work"].mkdir(parents=True, exist_ok=True)
    p["latest_state"].parent.mkdir(parents=True, exist_ok=True)

    summary: Dict[str, Any] = {
        "step": STEP,
        "created_at_utc": utc_now_iso(),
        "output_dir": str(p["out"]),
        "work_dir": str(p["work"]),
        "selected_watchlist_exists": p["selected"].exists(),
        "stage199_file_imported": True,
        "latest_state_written": False,
        "trade_ledger_appended": False,
        "no_signal_counter_appended": False,
        "csv_latest_row_contract": "CLOSED",
        "output_files": {
            "latest_state_json": str(p["latest_state"]),
            "trade_signal_ledger_csv": str(p["trade_ledger"]),
            "no_signal_counter_csv": str(p["no_signal"]),
            "summary_json": str(p["summary"]),
            "decision_csv": str(p["decision"]),
            "latest_preview_json": str(p["latest_preview"]),
            "ledger_csv": str(p["ledger"]),
            "paste_me": str(p["paste"]),
        },
    }
    summary.update(OFF_FLAGS)
    blockers: List[str] = []
    state: Dict[str, Any] = {}
    try:
        selected, frames, source_rows, input_blockers = load_stage199_inputs(data_dir, p)
        if input_blockers:
            blockers.extend([json.dumps(b, ensure_ascii=False, sort_keys=True) for b in input_blockers])
        else:
            feat = build_features(frames)
            if feat.empty:
                blockers.append("feature_frame_empty")
            else:
                priority = s199.selected_priority(selected)
                scalp_tail, scalp_info = s199.latest_snapshot(feat, selected, priority)
                abc_tail, abc_info, abc_problems = abc_latest_snapshot(feat)
                if abc_problems:
                    blockers.append(json.dumps({"abc_rule_problems": abc_problems[:5]}, ensure_ascii=False, sort_keys=True))
                latest_dt = fmt_dt(feat["dt"].iloc[-1])
                abc_sig = abc_from_latest_info(abc_info)
                scalp_sig = scalp_from_latest_info(scalp_info)
                selected_state = select_runtime_state(latest_dt, abc_sig, scalp_sig)
                state = make_latest_state(selected_state, abc_sig, scalp_sig, {"stage199_imported": True})
                write_json(p["latest_state"], state)
                summary["latest_state_written"] = True
                if state.get("signal_id"):
                    if state["signal_id"] not in existing_signal_ids(p["trade_ledger"]):
                        append_csv(p["trade_ledger"], state, LEDGER_COLUMNS)
                        summary["trade_ledger_appended"] = True
                else:
                    append_csv(p["no_signal"], {
                        "created_at_utc": utc_now_iso(),
                        "latest_closed_m15_dt": state.get("latest_closed_m15_dt"),
                        "final_route": "NO_SIGNAL",
                        "reason": state.get("selection_reason"),
                        "stage": STEP,
                    }, ["created_at_utc", "latest_closed_m15_dt", "final_route", "reason", "stage"])
                    summary["no_signal_counter_appended"] = True
                write_json(p["latest_preview"], {"state": state, "abc_latest": abc_sig, "scalp_latest": scalp_sig})
                append_csv(p["ledger"], state, LEDGER_COLUMNS)
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

    checks, validation_blockers = validate(summary)
    blockers.extend(validation_blockers)
    summary["blockers"] = blockers
    summary["blocker_count"] = len(blockers)
    summary["status"] = "READY" if not blockers else "BLOCKED"
    summary["ready"] = not blockers
    summary["decision"] = READY_DECISION if not blockers else BLOCKED_DECISION
    summary["validation_checks"] = checks
    write_json(p["summary"], summary)
    append_csv(p["decision"], summary, ["created_at_utc", "step", "status", "ready", "decision", "latest_closed_m15_dt", "final_route", "signal_id", "selected_family", "candidate_id", "direction", "blocker_count"])
    write_paste(p["paste"], summary, checks)

    print(f"Stage240 status: {summary['status']}")
    print(f"decision: {summary['decision']}")
    print(f"latest_closed_m15_dt: {summary.get('latest_closed_m15_dt')}")
    print(f"final_route: {summary.get('final_route')}")
    print(f"selected_family: {summary.get('selected_family')}")
    print(f"signal_id: {summary.get('signal_id')}")
    print(f"paste_me: {p['paste']}")
    if blockers:
        print("BLOCKERS:")
        for b in blockers:
            print(f"- {b}")
        return 2
    print("NO_BLOCKERS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
