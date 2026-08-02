from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

import numpy as np
import pandas as pd

from .common import (
    CANDIDATE_ID, CONTRACT_VERSION, RESEARCH_CUTOFF, SELECTED_STATE_ACTIONS,
    append_csv, half_year, month_key, now_utc, parse_timestamp, sha256_text,
)
from .runtime_execution import (
    _advance_resolution, _direction, _initial_state, _levels, _new_resolution,
)

ENTRY_EVENTS_FILENAME = "entry_events.csv"
SUPPRESSION_EVENTS_FILENAME = "suppression_events.csv"
TRADE_RESULTS_FILENAME = "trade_results.csv"
HEALTH_DECISIONS_FILENAME = "health_decisions.csv"

def _refresh_episode_rearms(state: dict[str, Any]) -> None:
    for episode in state["episodes"].values():
        if not episode.get("armed", True) and episode.get("position_exited", False) and int(episode.get("absence_count", 0)) >= 2:
            episode["armed"] = True
            episode["blocked_trade_id"] = None

def _update_episode_absence(state: dict[str, Any], current_fine: str) -> None:
    for selected_state, episode in state["episodes"].items():
        if current_fine == selected_state:
            episode["absence_count"] = 0
        else:
            episode["absence_count"] = min(2, int(episode.get("absence_count", 0)) + 1)
    _refresh_episode_rearms(state)

def _result_row(trade: Mapping[str, Any]) -> dict[str, Any]:
    m1 = trade["m1"]
    m5 = trade["m5"]
    return {
        "trade_id": trade["trade_id"],
        "candidate_id": CANDIDATE_ID,
        "signal_time": trade["signal_time"],
        "entry_time": trade["entry_time"],
        "state": trade["state"],
        "action": trade["action"],
        "half_year": trade["half_year"],
        "month": trade["month"],
        "raw_entry_open": trade["raw_entry_open"],
        "entry_price": trade["entry_price"],
        "partial_tp_price": trade["partial_tp_price"],
        "final_tp_price": trade["final_tp_price"],
        "sl_price": trade["sl_price"],
        "m1_exit_time": m1["exit_time"],
        "m1_exit_reason": m1["exit_reason"],
        "m1_pnl": m1["pnl"],
        "m1_mfe": m1["mfe"],
        "m1_mae": m1["mae"],
        "m5_exit_time": m5["exit_time"],
        "m5_exit_reason": m5["exit_reason"],
        "m5_pnl": m5["pnl"],
        "m5_mfe": m5["mfe"],
        "m5_mae": m5["mae"],
        "finalized_at_utc": now_utc(),
    }

def _advance_trades(state: dict[str, Any], data: Mapping[str, pd.DataFrame], root: Path) -> None:
    for trade_id, trade in list(state["trades"].items()):
        _advance_resolution(trade, trade["m1"], data["M1"])
        _advance_resolution(trade, trade["m5"], data["M5"])
        if state.get("open_trade_id") == trade_id and trade["m1"].get("status") == "CLOSED":
            state["open_trade_id"] = None
            episode = state["episodes"].get(trade["state"])
            if episode is not None:
                episode["position_exited"] = True
        if trade["m1"].get("status") == "CLOSED" and trade["m5"].get("status") == "CLOSED" and not trade.get("finalized", False):
            append_csv(root / TRADE_RESULTS_FILENAME, _result_row(trade))
            trade["finalized"] = True
    _refresh_episode_rearms(state)

def _reset_half_year_if_needed(state: dict[str, Any], decision_time: pd.Timestamp) -> None:
    current = half_year(decision_time)
    health = state["health"]
    if health.get("current_half_year") != current:
        health["current_half_year"] = current
        health["suspended"] = {}
        health["checked_month_by_state"] = {}

def _health_decision(state: dict[str, Any], selected_state: str, action: str, decision_time: pd.Timestamp, root: Path) -> str:
    _reset_half_year_if_needed(state, decision_time)
    health = state["health"]
    current_month = month_key(decision_time)
    checked = health.setdefault("checked_month_by_state", {})
    if checked.get(selected_state) == current_month:
        return "ACTIVE_ALREADY_CHECKED"
    checked[selected_state] = current_month
    if selected_state in health.setdefault("suspended", {}):
        return "SUSPENDED_REMAINDER_OF_HALF"

    current_half = half_year(decision_time)
    resolved: list[Mapping[str, Any]] = []
    for trade in state["trades"].values():
        if trade.get("state") != selected_state or trade.get("action") != action or trade.get("half_year") != current_half:
            continue
        m1_exit = parse_timestamp(trade.get("m1", {}).get("exit_time"))
        m5_exit = parse_timestamp(trade.get("m5", {}).get("exit_time"))
        if m1_exit is None or m5_exit is None or m1_exit >= decision_time or m5_exit >= decision_time:
            continue
        resolved.append(trade)
    n = len(resolved)
    m1_net = float(sum(float(trade["m1"]["pnl"]) for trade in resolved)) if resolved else 0.0
    m5_net = float(sum(float(trade["m5"]["pnl"]) for trade in resolved)) if resolved else 0.0
    decision = "KEEP_ACTIVE"
    if n >= 10 and (m1_net <= 0.0 or m5_net <= 0.0):
        decision = "SUSPEND_REMAINDER_OF_HALF"
        health["suspended"][selected_state] = {
            "action": action,
            "effective_month": current_month,
            "resolved_n": n,
            "cum_m1_net": m1_net,
            "cum_m5_net": m5_net,
            "decision_time": str(decision_time),
        }
    append_csv(
        root / HEALTH_DECISIONS_FILENAME,
        {
            "decision_time": str(decision_time),
            "half_year": current_half,
            "month": current_month,
            "state": selected_state,
            "action": action,
            "resolved_n": n,
            "cum_m1_net": m1_net,
            "cum_m5_net": m5_net,
            "decision": decision,
        },
    )
    return decision

def _event_id(signal_time: pd.Timestamp, entry_time: pd.Timestamp, selected_state: str, action: str) -> str:
    return sha256_text(f"{CANDIDATE_ID}|{signal_time}|{entry_time}|{selected_state}|{action}")[:24]

def _accept_entry(
    state: dict[str, Any],
    signal: Mapping[str, Any],
    m1_row: Mapping[str, Any],
    root: Path,
) -> dict[str, Any]:
    signal_time = pd.Timestamp(signal["signal_time"])
    entry_time = pd.Timestamp(signal["entry_time"])
    selected_state = str(signal["state"])
    action = str(signal["action"])
    event_id = _event_id(signal_time, entry_time, selected_state, action)
    levels = _levels(float(m1_row["open"]), action)
    trade = {
        "trade_id": event_id,
        "event_id": event_id,
        "candidate_id": CANDIDATE_ID,
        "signal_time": str(signal_time),
        "entry_time": str(entry_time),
        "state": selected_state,
        "action": action,
        "half_year": half_year(entry_time),
        "month": month_key(entry_time),
        "created_at_utc": now_utc(),
        **levels,
        "state_components": signal.get("state_components", {}),
        "m1": _new_resolution(entry_time),
        "m5": _new_resolution(entry_time),
        "finalized": False,
    }
    state["trades"][event_id] = trade
    state["open_trade_id"] = event_id
    episode = state["episodes"][selected_state]
    episode["armed"] = False
    episode["absence_count"] = 0
    episode["blocked_trade_id"] = event_id
    episode["position_exited"] = False
    state["pending_signal"] = None
    state["statistics"]["accepted_entries"] = int(state["statistics"].get("accepted_entries", 0)) + 1
    health_status = "ACTIVE"
    event = {
        "event_id": event_id,
        "candidate_id": CANDIDATE_ID,
        "signal_time": str(signal_time),
        "entry_time": str(entry_time),
        "state": selected_state,
        "action": action,
        "health_status": health_status,
        **levels,
        "created_at_utc": now_utc(),
    }
    append_csv(root / ENTRY_EVENTS_FILENAME, event)
    state["discord_queue"].append(event)
    return event

def _process_pending(state: dict[str, Any], data: Mapping[str, pd.DataFrame], root: Path) -> dict[str, Any] | None:
    pending = state.get("pending_signal")
    if not isinstance(pending, dict):
        return None
    entry_time = pd.Timestamp(pending["entry_time"])
    exact = data["M1"][data["M1"]["time"] == entry_time]
    if not exact.empty:
        return _accept_entry(state, pending, exact.iloc[-1], root)
    later = data["M1"][data["M1"]["time"] > entry_time]
    if not later.empty:
        append_csv(
            root / SUPPRESSION_EVENTS_FILENAME,
            {
                "signal_time": pending["signal_time"],
                "entry_time": pending["entry_time"],
                "state": pending["state"],
                "action": pending["action"],
                "reason": "MISSING_EXACT_M1_ENTRY",
                "created_at_utc": now_utc(),
            },
        )
        state["pending_signal"] = None
    return None

def _state_components(row: Mapping[str, Any]) -> dict[str, Any]:
    keys = (
        "session_x",
        "htf",
        "vol",
        "mom",
        "exp",
        "cdir",
        "atr14",
        "vol_low_boundary",
        "vol_high_boundary",
        "momentum_z",
        "range_ratio",
        "body_fraction",
        "h1_close",
        "h1_ema20",
        "h1_ema50",
        "h4_close",
        "h4_ema20",
        "h4_ema50",
    )
    result: dict[str, Any] = {}
    for key in keys:
        value = row.get(key)
        if isinstance(value, (np.floating, np.integer)):
            value = value.item()
        result[key] = value
    return result

def _evaluate_row(state: dict[str, Any], row: Mapping[str, Any], root: Path) -> None:
    signal_time = pd.Timestamp(row["time"])
    fine = str(row["fine"])
    _update_episode_absence(state, fine)
    state["last_processed_m15_time"] = str(signal_time)
    if signal_time <= RESEARCH_CUTOFF:
        return
    action = SELECTED_STATE_ACTIONS.get(fine)
    if action is None:
        return
    entry_time = signal_time + pd.Timedelta(minutes=15)
    decision = _health_decision(state, fine, action, entry_time, root)
    if decision == "SUSPEND_REMAINDER_OF_HALF" or fine in state["health"].get("suspended", {}):
        state["statistics"]["suppressed_health"] = int(state["statistics"].get("suppressed_health", 0)) + 1
        append_csv(
            root / SUPPRESSION_EVENTS_FILENAME,
            {
                "signal_time": str(signal_time),
                "entry_time": str(entry_time),
                "state": fine,
                "action": action,
                "reason": "HEALTH_SUSPENDED",
                "created_at_utc": now_utc(),
            },
        )
        return
    if state.get("open_trade_id") is not None or state.get("pending_signal") is not None:
        state["statistics"]["suppressed_open_position"] = int(state["statistics"].get("suppressed_open_position", 0)) + 1
        append_csv(
            root / SUPPRESSION_EVENTS_FILENAME,
            {
                "signal_time": str(signal_time),
                "entry_time": str(entry_time),
                "state": fine,
                "action": action,
                "reason": "ONE_POSITION_NONOVERLAP",
                "created_at_utc": now_utc(),
            },
        )
        return
    episode = state["episodes"][fine]
    if not episode.get("armed", True):
        state["statistics"]["suppressed_episode"] = int(state["statistics"].get("suppressed_episode", 0)) + 1
        append_csv(
            root / SUPPRESSION_EVENTS_FILENAME,
            {
                "signal_time": str(signal_time),
                "entry_time": str(entry_time),
                "state": fine,
                "action": action,
                "reason": "EPISODE_NOT_REARMED",
                "created_at_utc": now_utc(),
            },
        )
        return
    state["pending_signal"] = {
        "signal_time": str(signal_time),
        "entry_time": str(entry_time),
        "state": fine,
        "action": action,
        "state_components": _state_components(row),
    }
