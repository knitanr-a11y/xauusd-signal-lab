#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import pandas as pd

LEDGER_COLUMNS = [
    "candidate_id","source","priority","decision_dt","trigger_dt","entry_dt",
    "reference_price","direction","direction_num","atr_entry","tp_atr","sl_atr",
    "tp_distance","sl_distance","max_holding_minutes","candidate_contract",
    "candidate_key","status","fill_dt","fill_price","tp_price","sl_price",
    "exit_dt","exit_price","exit_reason","pnl","reject_reasons",
]
UPDATE_COLUMNS = ["candidate_id","event_type","event_dt","price","pnl","reason"]
TIME_COLUMNS = ["decision_dt","trigger_dt","entry_dt","fill_dt","exit_dt"]
NUM_COLUMNS = [
    "priority","reference_price","direction_num","atr_entry","tp_atr","sl_atr",
    "tp_distance","sl_distance","max_holding_minutes","fill_price","tp_price",
    "sl_price","exit_price","pnl",
]


def load_bootstrap(path: Path) -> dict:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if data.get("status") != "GOLD_V3_292_SAFE_PORTFOLIO_BOOTSTRAP_READY":
        raise ValueError("invalid Stage292 bootstrap status")
    for key in ["asof","last_candidate_entry_dt","last_candidate_loss_exit_dt","last_base_exit_dt"]:
        data[key] = pd.Timestamp(data[key])
    return data


def empty_ledger() -> pd.DataFrame:
    return pd.DataFrame(columns=LEDGER_COLUMNS)


def load_ledger(path: Path) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        return empty_ledger()
    data = pd.read_csv(path, encoding="utf-8-sig")
    for column in TIME_COLUMNS:
        if column in data:
            data[column] = pd.to_datetime(data[column], errors="coerce")
    for column in NUM_COLUMNS:
        if column in data:
            data[column] = pd.to_numeric(data[column], errors="coerce")
    return data


def load_updates(path: Path) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame(columns=UPDATE_COLUMNS)
    data = pd.read_csv(path, encoding="utf-8-sig")
    missing = set(UPDATE_COLUMNS) - set(data.columns)
    if missing:
        raise ValueError(f"execution updates missing columns: {sorted(missing)}")
    data["event_type"] = data.event_type.astype(str).str.upper().str.strip()
    data["event_dt"] = pd.to_datetime(data.event_dt, errors="coerce")
    data["price"] = pd.to_numeric(data.price, errors="coerce")
    data["pnl"] = pd.to_numeric(data.pnl, errors="coerce")
    bad = sorted(set(data.event_type.dropna()) - {"FILLED","CANCELLED","CLOSED"})
    if bad:
        raise ValueError(f"unsupported execution event types: {bad}")
    return data.dropna(subset=["candidate_id","event_type","event_dt"]).sort_values(
        ["event_dt","candidate_id"], kind="mergesort"
    )


def apply_updates(ledger: pd.DataFrame, updates: pd.DataFrame, asof: pd.Timestamp):
    current = ledger.copy()
    applied = []
    if updates.empty:
        return current, pd.DataFrame()
    for row in updates[updates.event_dt <= pd.Timestamp(asof)].itertuples(index=False):
        hits = current.index[current.candidate_id.astype(str).eq(str(row.candidate_id))]
        if len(hits) != 1:
            continue
        index = hits[0]
        status = str(current.at[index,"status"])
        if row.event_type == "FILLED" and status == "PENDING_FILL":
            if not np.isfinite(float(row.price)):
                raise ValueError("FILLED requires price")
            direction = int(current.at[index,"direction_num"])
            tp = float(row.price) + direction * float(current.at[index,"tp_distance"])
            sl = float(row.price) - direction * float(current.at[index,"sl_distance"])
            current.loc[index,["status","fill_dt","fill_price","tp_price","sl_price"]] = [
                "OPEN",row.event_dt,float(row.price),tp,sl
            ]
        elif row.event_type == "CANCELLED" and status == "PENDING_FILL":
            current.loc[index,["status","exit_dt","exit_reason"]] = [
                "CANCELLED",row.event_dt,str(row.reason or "CANCELLED")
            ]
        elif row.event_type == "CLOSED" and status == "OPEN":
            if not np.isfinite(float(row.price)) or not np.isfinite(float(row.pnl)):
                raise ValueError("CLOSED requires price and pnl")
            current.loc[index,["status","exit_dt","exit_price","exit_reason","pnl"]] = [
                "CLOSED",row.event_dt,float(row.price),str(row.reason or "CLOSED"),float(row.pnl)
            ]
        else:
            continue
        applied.append({"candidate_id":row.candidate_id,"event_type":row.event_type,"event_dt":row.event_dt})
    return current, pd.DataFrame(applied)


def state_at(time: pd.Timestamp, ledger: pd.DataFrame, bootstrap: dict) -> dict:
    time = pd.Timestamp(time)
    equity = float(bootstrap["equity"])
    peak = float(bootstrap["peak"])
    last_candidate_entry = pd.Timestamp(bootstrap["last_candidate_entry_dt"])
    last_candidate_loss = pd.Timestamp(bootstrap["last_candidate_loss_exit_dt"])
    last_base_exit = pd.Timestamp(bootstrap["last_base_exit_dt"])
    last_base_pnl = float(bootstrap["last_base_pnl"])
    if len(ledger):
        closed = ledger[
            ledger.status.astype(str).eq("CLOSED")
            & pd.to_datetime(ledger.exit_dt, errors="coerce").le(time)
            & pd.to_datetime(ledger.exit_dt, errors="coerce").gt(bootstrap["asof"])
        ].sort_values(["exit_dt","entry_dt"], kind="mergesort")
        for row in closed.itertuples(index=False):
            equity += float(row.pnl)
            peak = max(peak, equity)
            if row.source != "BASE" and float(row.pnl) < 0:
                last_candidate_loss = max(last_candidate_loss, pd.Timestamp(row.exit_dt))
            if row.source == "BASE" and pd.Timestamp(row.exit_dt) >= last_base_exit:
                last_base_exit = pd.Timestamp(row.exit_dt)
                last_base_pnl = float(row.pnl)
        accepted = ledger[pd.to_datetime(ledger.entry_dt, errors="coerce").le(time)]
        additions = accepted[accepted.source.astype(str).ne("BASE")]
        if len(additions):
            last_candidate_entry = max(last_candidate_entry, pd.to_datetime(additions.entry_dt).max())
        active = ledger[
            ledger.status.astype(str).isin(["PENDING_FILL","OPEN"])
            & pd.to_datetime(ledger.entry_dt, errors="coerce").le(time)
        ]
    else:
        active = pd.DataFrame()
    return {
        "equity":equity,
        "peak":peak,
        "dd":peak-equity,
        "active_count":int(len(active)),
        "last_candidate_entry":last_candidate_entry,
        "last_candidate_loss_exit":last_candidate_loss,
        "last_base_exit":last_base_exit,
        "last_base_pnl":last_base_pnl,
    }


def overlaps_rollover(entry_dt: pd.Timestamp, holding_minutes: int) -> bool:
    start = pd.Timestamp(entry_dt)
    end = start + pd.Timedelta(minutes=int(holding_minutes))
    cursor = start.floor("h")
    while cursor <= end:
        if cursor.hour in {0,1}:
            return True
        cursor += pd.Timedelta(hours=1)
    return False


def evaluate_candidates(candidates: pd.DataFrame, ledger: pd.DataFrame, bootstrap: dict):
    if candidates.empty:
        return pd.DataFrame(), ledger
    current = ledger.copy()
    existing = set(current.candidate_id.astype(str)) if len(current) else set()
    decisions = []
    ordered = candidates.sort_values(["entry_dt","priority","candidate_id"], kind="mergesort")
    for row in ordered.itertuples(index=False):
        if str(row.candidate_id) in existing:
            continue
        state = state_at(row.entry_dt, current, bootstrap)
        reasons = []
        if state["active_count"] > 0:
            reasons.append("POSITION_OR_PENDING_SIGNAL_ACTIVE")
        if row.source == "BASE" and overlaps_rollover(row.entry_dt, row.max_holding_minutes):
            reasons.append("BASE_HOLD_OVERLAPS_SERVER_00_01")
        if row.source != "BASE":
            if state["dd"] > 30.0:
                reasons.append("COMBINED_DD_ABOVE_30")
            if pd.Timestamp(row.entry_dt) < state["last_candidate_entry"] + pd.Timedelta(hours=12):
                reasons.append("SHARED_12H_COOLDOWN")
        if row.source == "STAGE281":
            if not (
                state["last_base_pnl"] < 0
                and state["last_base_exit"] <= pd.Timestamp(row.entry_dt)
                and pd.Timestamp(row.entry_dt) <= state["last_base_exit"] + pd.Timedelta(hours=72)
            ):
                reasons.append("NOT_AFTER_RESOLVED_BASE_LOSS_WITHIN_72H")
        if row.source == "STAGE286":
            if state["dd"] > 10.0:
                reasons.append("SHORT_DD_ABOVE_10")
            if pd.Timestamp(row.entry_dt) < state["last_candidate_loss_exit"] + pd.Timedelta(hours=24):
                reasons.append("SHORT_24H_AFTER_CANDIDATE_LOSS")
        accepted = not reasons
        record = row._asdict()
        record.update({
            "final_signal":accepted,
            "reject_reasons":";".join(reasons),
            "state_equity":state["equity"],
            "state_peak":state["peak"],
            "state_dd":state["dd"],
        })
        decisions.append(record)
        existing.add(str(row.candidate_id))
        if accepted:
            trade = {column:record.get(column, np.nan) for column in LEDGER_COLUMNS}
            trade.update({
                "status":"PENDING_FILL","fill_dt":pd.NaT,"fill_price":np.nan,
                "tp_price":np.nan,"sl_price":np.nan,"exit_dt":pd.NaT,
                "exit_price":np.nan,"exit_reason":"","pnl":np.nan,
            })
            current = pd.concat([current, pd.DataFrame([trade])], ignore_index=True)
    return pd.DataFrame(decisions), current
