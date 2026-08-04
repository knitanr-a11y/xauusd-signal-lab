from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

import pandas as pd

from .common import (
    CANDIDATE_ID, CONTRACT_VERSION, FINAL_TARGET_USD, FIXED_SPREAD_USD,
    HORIZON_MINUTES, INITIAL_STOP_USD, PARTIAL_FRACTION, PARTIAL_TARGET_USD,
    RESEARCH_CUTOFF, REMAINDER_FRACTION, SELECTED_STATE_ACTIONS, half_year,
    now_utc, parse_timestamp, write_json,
)

STATE_FILENAME = "shadow_state.json"

def _new_resolution(entry_time: pd.Timestamp) -> dict[str, Any]:
    return {
        "status": "OPEN",
        "entry_time": str(entry_time),
        "last_bar_time": None,
        "partial_taken": False,
        "partial_time": None,
        "exit_time": None,
        "exit_reason": None,
        "pnl": None,
        "mfe": 0.0,
        "mae": 0.0,
        "last_close": None,
    }

def _initial_state(cursor: pd.Timestamp) -> dict[str, Any]:
    return {
        "candidate_id": CANDIDATE_ID,
        "contract_version": CONTRACT_VERSION,
        "formal_status": "PROSPECTIVE_SHADOW_RUNNING_OBSERVATION_ONLY",
        "created_at_utc": now_utc(),
        "updated_at_utc": now_utc(),
        "research_cutoff_signal_time": str(RESEARCH_CUTOFF),
        "last_processed_m15_time": str(cursor),
        "pending_signal": None,
        "open_trade_id": None,
        "trades": {},
        "episodes": {
            state: {
                "action": action,
                "armed": True,
                "absence_count": 2,
                "blocked_trade_id": None,
                "position_exited": True,
            }
            for state, action in SELECTED_STATE_ACTIONS.items()
        },
        "health": {
            "current_half_year": half_year(max(cursor, RESEARCH_CUTOFF)),
            "suspended": {},
            "checked_month_by_state": {},
        },
        "discord_queue": [],
        "statistics": {
            "accepted_entries": 0,
            "suppressed_open_position": 0,
            "suppressed_episode": 0,
            "suppressed_health": 0,
            "recovery_rows_skipped": 0,
        },
    }

def _state_path(root: Path) -> Path:
    return root / STATE_FILENAME

def _load_state(root: Path) -> dict[str, Any]:
    path = _state_path(root)
    if not path.exists():
        raise RuntimeError("Shadow is not bootstrapped. Run the bootstrap command first.")
    with path.open("r", encoding="utf-8") as handle:
        state = json.load(handle)
    if state.get("candidate_id") != CANDIDATE_ID or state.get("contract_version") != CONTRACT_VERSION:
        raise RuntimeError("Runtime state contract mismatch")
    return state

def _save_state(root: Path, state: dict[str, Any]) -> None:
    state["updated_at_utc"] = now_utc()
    write_json(_state_path(root), state)

def _direction(action: str) -> float:
    if action == "LONG":
        return 1.0
    if action == "SHORT":
        return -1.0
    raise ValueError(f"Unsupported action: {action}")

def _levels(raw_open: float, action: str) -> dict[str, float]:
    direction = _direction(action)
    entry = float(raw_open) + direction * FIXED_SPREAD_USD
    return {
        "raw_entry_open": float(raw_open),
        "entry_price": entry,
        "partial_tp_price": entry + direction * PARTIAL_TARGET_USD,
        "final_tp_price": entry + direction * FINAL_TARGET_USD,
        "sl_price": entry - direction * INITIAL_STOP_USD,
    }

def _bar_hit(row: Mapping[str, Any], action: str, level: float, favorable: bool) -> bool:
    if action == "LONG":
        return float(row["high"] if favorable else row["low"]) >= level if favorable else float(row["low"]) <= level
    return float(row["low"] if favorable else row["high"]) <= level if favorable else float(row["high"]) >= level

def _signed_move(price: float, entry: float, action: str) -> float:
    return _direction(action) * (float(price) - float(entry))

def _close_resolution(resolution: dict[str, Any], when: pd.Timestamp, reason: str, pnl: float) -> None:
    resolution["status"] = "CLOSED"
    resolution["exit_time"] = str(when)
    resolution["exit_reason"] = reason
    resolution["pnl"] = float(pnl)

def _advance_resolution(trade: Mapping[str, Any], resolution: dict[str, Any], bars: pd.DataFrame) -> None:
    if resolution.get("status") != "OPEN":
        return
    action = str(trade["action"])
    entry_time = pd.Timestamp(trade["entry_time"])
    entry = float(trade["entry_price"])
    partial_target = float(trade["partial_tp_price"])
    final_target = float(trade["final_tp_price"])
    stop = float(trade["sl_price"])
    horizon_end = entry_time + pd.Timedelta(minutes=HORIZON_MINUTES)
    last_bar = parse_timestamp(resolution.get("last_bar_time"))
    eligible = bars[bars["time"] >= entry_time]
    if last_bar is not None:
        eligible = eligible[eligible["time"] > last_bar]
    eligible = eligible.sort_values("time")
    for _, row in eligible.iterrows():
        bar_time = pd.Timestamp(row["time"])
        if bar_time >= horizon_end:
            break
        high_move = _signed_move(float(row["high"]), entry, action)
        low_move = _signed_move(float(row["low"]), entry, action)
        favorable = max(high_move, low_move)
        adverse = min(high_move, low_move)
        resolution["mfe"] = max(float(resolution.get("mfe", 0.0)), favorable)
        resolution["mae"] = min(float(resolution.get("mae", 0.0)), adverse)
        resolution["last_bar_time"] = str(bar_time)
        resolution["last_close"] = float(row["close"])

        if not resolution.get("partial_taken", False):
            # Same-bar ambiguity is fail-closed: the initial stop is checked first.
            if _bar_hit(row, action, stop, favorable=False):
                _close_resolution(resolution, bar_time, "SL", -INITIAL_STOP_USD)
                return
            if _bar_hit(row, action, final_target, favorable=True):
                _close_resolution(
                    resolution,
                    bar_time,
                    "FINAL_TP",
                    PARTIAL_FRACTION * PARTIAL_TARGET_USD + REMAINDER_FRACTION * FINAL_TARGET_USD,
                )
                resolution["partial_taken"] = True
                resolution["partial_time"] = str(bar_time)
                return
            if _bar_hit(row, action, partial_target, favorable=True):
                resolution["partial_taken"] = True
                resolution["partial_time"] = str(bar_time)
                # After partial profit, a same-bar return through entry is treated as BE.
                if _bar_hit(row, action, entry, favorable=False):
                    _close_resolution(resolution, bar_time, "PARTIAL_THEN_BE", PARTIAL_FRACTION * PARTIAL_TARGET_USD)
                    return
        else:
            if _bar_hit(row, action, entry, favorable=False):
                _close_resolution(resolution, bar_time, "BE", PARTIAL_FRACTION * PARTIAL_TARGET_USD)
                return
            if _bar_hit(row, action, final_target, favorable=True):
                _close_resolution(
                    resolution,
                    bar_time,
                    "FINAL_TP",
                    PARTIAL_FRACTION * PARTIAL_TARGET_USD + REMAINDER_FRACTION * FINAL_TARGET_USD,
                )
                return

    latest_time = pd.Timestamp(bars["time"].iloc[-1]) if not bars.empty else None
    if latest_time is not None and latest_time >= horizon_end:
        prior = bars[(bars["time"] >= entry_time) & (bars["time"] < horizon_end)].sort_values("time")
        if not prior.empty:
            last = prior.iloc[-1]
            close_move = _signed_move(float(last["close"]), entry, action)
            pnl = (
                PARTIAL_FRACTION * PARTIAL_TARGET_USD + REMAINDER_FRACTION * close_move
                if resolution.get("partial_taken", False)
                else close_move
            )
            _close_resolution(resolution, pd.Timestamp(last["time"]), "TIME", float(pnl))
