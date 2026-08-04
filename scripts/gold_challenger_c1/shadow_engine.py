from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

import pandas as pd

from .shadow_common import FIXED_SPREAD, HORIZON_M1, STOP, TARGET, append_csv, now_utc, parse_dt
from .v19_readonly import V19View


def default_state() -> dict[str, Any]:
    return {
        "candidate_id": "GOLD_CHALLENGER_C1_V2_DATA_V3",
        "contract_version": "2026-08-01-prospective-shadow-v1",
        "mode": "OBSERVATION_ONLY_PROSPECTIVE_SHADOW",
        "activated": False,
        "activated_at_utc": None,
        "baseline_decision_dt": None,
        "last_processed_decision_dt": None,
        "last_seen_m1_dt": None,
        "last_closed_exit_idx": -1,
        "open_trade": None,
        "counters": {
            "accepted_trades": 0,
            "closed_trades": 0,
            "suppressed_v19_priority": 0,
            "suppressed_challenger_open": 0,
            "recovery_replay_not_traded": 0,
            "v19_preempts": 0,
            "invalid_gap": 0,
        },
        "last_iteration_utc": None,
        "last_error": None,
    }


def _entry_prices(side: str, bid_open: float) -> tuple[float, float, float]:
    if side == "LONG":
        entry = bid_open + FIXED_SPREAD
        return entry, entry + TARGET, entry - STOP
    entry = bid_open
    return entry, entry - TARGET, entry + STOP


def _mark_to_market_pnl(side: str, entry: float, bid_open: float) -> tuple[float, float]:
    if side == "LONG":
        return bid_open - entry, bid_open
    exit_price = bid_open + FIXED_SPREAD
    return entry - exit_price, exit_price


def _close_trade(
    state: dict[str, Any], root: Path, trade: Mapping[str, Any], exit_idx: int,
    exit_dt: pd.Timestamp, exit_price: float | None, pnl: float | None, reason: str,
) -> None:
    append_csv(
        root / "outputs" / "shadow_trade_ledger.csv",
        {
            **{str(key): value for key, value in trade.items()},
            "exit_idx": exit_idx,
            "exit_dt": exit_dt,
            "exit_price": exit_price,
            "pnl": pnl,
            "exit_reason": reason,
            "closed_at_utc": now_utc(),
        },
    )
    state["open_trade"] = None
    state["last_closed_exit_idx"] = max(int(state.get("last_closed_exit_idx", -1)), int(exit_idx))
    state["counters"]["closed_trades"] += 1
    if reason == "V19_PREEMPT":
        state["counters"]["v19_preempts"] += 1
    if reason == "INVALID_M1_GAP":
        state["counters"]["invalid_gap"] += 1


def process_open_trade(state: dict[str, Any], root: Path, m1: pd.DataFrame, v19: V19View) -> None:
    trade = state.get("open_trade")
    if not isinstance(trade, dict) or not trade:
        return
    entry_idx = int(trade["entry_idx"])
    if entry_idx < 0 or entry_idx >= len(m1):
        raise RuntimeError("Open Challenger trade entry_idx is outside the current M1 union")
    entry_dt = pd.Timestamp(trade["entry_dt"])
    if pd.Timestamp(m1.time.iloc[entry_idx]) != entry_dt:
        raise RuntimeError("Open Challenger trade entry_idx no longer maps to entry_dt")
    start = max(entry_idx, int(trade.get("last_checked_idx", entry_idx - 1)) + 1)
    side = str(trade["side"])
    entry, tp, sl = float(trade["entry_price"]), float(trade["tp_price"]), float(trade["sl_price"])
    for index in range(start, len(m1)):
        timestamp = pd.Timestamp(m1.time.iloc[index])
        bid_open = float(m1.open.iloc[index])
        if index > entry_idx and pd.Timestamp(m1.time.iloc[index - 1]) + pd.Timedelta(minutes=1) != timestamp:
            _, exit_price = _mark_to_market_pnl(side, entry, bid_open)
            _close_trade(state, root, trade, index, timestamp, exit_price, None, "INVALID_M1_GAP")
            return
        if index == entry_idx + HORIZON_M1:
            pnl, exit_price = _mark_to_market_pnl(side, entry, bid_open)
            _close_trade(state, root, trade, index, timestamp, exit_price, pnl, "TIME")
            return
        if timestamp > entry_dt and v19.entry_at(timestamp):
            pnl, exit_price = _mark_to_market_pnl(side, entry, bid_open)
            _close_trade(state, root, trade, index, timestamp, exit_price, pnl, "V19_PREEMPT")
            return
        high, low = float(m1.high.iloc[index]), float(m1.low.iloc[index])
        if side == "LONG":
            if low <= sl:
                _close_trade(state, root, trade, index, timestamp, sl, -STOP, "SL")
                return
            if high >= tp:
                _close_trade(state, root, trade, index, timestamp, tp, TARGET, "TP")
                return
        else:
            if high >= sl - FIXED_SPREAD:
                _close_trade(state, root, trade, index, timestamp, sl, -STOP, "SL")
                return
            if low <= tp - FIXED_SPREAD:
                _close_trade(state, root, trade, index, timestamp, tp, TARGET, "TP")
                return
        trade["last_checked_idx"] = index
    state["open_trade"] = trade


def _candidate_row(row: Mapping[str, Any], status: str, reason: str) -> dict[str, Any]:
    candidate_id = row.get("candidate_id")
    return {
        "candidate_id": None if pd.isna(candidate_id) else int(candidate_id),
        "origin_id": int(row["origin_id"]),
        "decision_dt": pd.Timestamp(row["decision_dt"]),
        "entry_idx": int(row["entry_idx"]),
        "chosen_side": str(row["chosen_side"]),
        "chosen_rank": float(row["chosen_rank"]),
        "wave_state": str(row["wave_state"]),
        "status": status,
        "reason": reason,
        "entry_price": None,
        "tp_price": None,
        "sl_price": None,
        "recorded_at_utc": now_utc(),
    }


def process_new_decisions(
    state: dict[str, Any], root: Path, timeline: pd.DataFrame, m1: pd.DataFrame,
    v19: V19View, allow_new_entries: bool,
) -> None:
    last = parse_dt(state.get("last_processed_decision_dt"))
    if last is None:
        raise RuntimeError("Activated state has no last_processed_decision_dt")
    new_rows = timeline[pd.to_datetime(timeline.decision_dt) > last].copy().sort_values("decision_dt")
    if new_rows.empty:
        return
    latest = pd.Timestamp(new_rows.decision_dt.iloc[-1])
    if v19.last_processed is None or v19.last_processed < latest:
        raise RuntimeError(f"V19_NOT_CAUGHT_UP: v19={v19.last_processed} challenger={latest}")
    exact_single = len(new_rows) == 1 and pd.Timestamp(new_rows.decision_dt.iloc[0]) - last == pd.Timedelta(minutes=15)
    if not allow_new_entries or not exact_single:
        for row in new_rows.to_dict("records"):
            if bool(row.get("event_onset")):
                append_csv(root / "outputs" / "shadow_candidate_ledger.csv", _candidate_row(row, "NOT_TRADED", "RECOVERY_REPLAY_NOT_TRADED"))
                state["counters"]["recovery_replay_not_traded"] += 1
        state["last_processed_decision_dt"] = latest
        return
    row = new_rows.iloc[0].to_dict()
    decision = pd.Timestamp(row["decision_dt"])
    state["last_processed_decision_dt"] = decision
    if not bool(row.get("event_onset")):
        return
    if pd.Timestamp(m1.time.iloc[-1]) != decision:
        append_csv(root / "outputs" / "shadow_candidate_ledger.csv", _candidate_row(row, "NOT_TRADED", "RECOVERY_REPLAY_NOT_TRADED_STALE_M1_CURSOR"))
        state["counters"]["recovery_replay_not_traded"] += 1
        return
    entry_idx = int(row["entry_idx"])
    if entry_idx < 0 or entry_idx >= len(m1) or pd.Timestamp(m1.time.iloc[entry_idx]) != decision:
        raise RuntimeError("Candidate entry mapping does not match the frozen M1 timestamp contract")
    if int(state.get("last_closed_exit_idx", -1)) >= entry_idx:
        append_csv(root / "outputs" / "shadow_candidate_ledger.csv", _candidate_row(row, "SUPPRESSED", "CHALLENGER_SAME_M1_BUSY"))
        state["counters"]["suppressed_challenger_open"] += 1
        return
    if isinstance(state.get("open_trade"), dict) and state["open_trade"]:
        append_csv(root / "outputs" / "shadow_candidate_ledger.csv", _candidate_row(row, "SUPPRESSED", "CHALLENGER_OPEN"))
        state["counters"]["suppressed_challenger_open"] += 1
        return
    if v19.open_at(decision) or v19.entry_at(decision):
        append_csv(root / "outputs" / "shadow_candidate_ledger.csv", _candidate_row(row, "SUPPRESSED", "V19_PRIORITY"))
        state["counters"]["suppressed_v19_priority"] += 1
        return
    side = str(row["chosen_side"])
    entry, tp, sl = _entry_prices(side, float(m1.open.iloc[entry_idx]))
    trade = {
        "candidate_id": int(row["candidate_id"]),
        "origin_id": int(row["origin_id"]),
        "decision_dt": decision,
        "entry_dt": decision,
        "entry_idx": entry_idx,
        "side": side,
        "chosen_rank": float(row["chosen_rank"]),
        "wave_state": str(row["wave_state"]),
        "entry_price": entry,
        "tp_price": tp,
        "sl_price": sl,
        "last_checked_idx": entry_idx - 1,
        "accepted_at_utc": now_utc(),
    }
    state["open_trade"] = trade
    state["counters"]["accepted_trades"] += 1
    candidate_record = _candidate_row(row, "ACCEPTED", "NEW_CONTINUOUS_EVENT")
    candidate_record.update({"entry_price": entry, "tp_price": tp, "sl_price": sl})
    append_csv(root / "outputs" / "shadow_candidate_ledger.csv", candidate_record)
    process_open_trade(state, root, m1, v19)
