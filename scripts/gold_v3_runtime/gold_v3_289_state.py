#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stage289 resolved-only portfolio state and safe admission."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from gold_v3_289_live_features import GOLD_FILES, read_candles

COST = 0.60
TRADE_TIME_COLUMNS = ["decision_dt", "trigger_dt", "entry_dt", "exit_dt"]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def empty_observation_ledger() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "candidate_id", "source", "priority", "decision_dt", "trigger_dt",
            "entry_dt", "entry_price", "direction", "direction_num", "atr_entry",
            "tp_atr", "sl_atr", "max_holding_minutes", "tp_price", "sl_price",
            "status", "exit_dt", "exit_price", "exit_reason", "gross_pnl", "pnl",
        ]
    )


def load_trade_ledger(path: Path) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        return empty_observation_ledger()
    data = pd.read_csv(path, encoding="utf-8-sig")
    for column in TRADE_TIME_COLUMNS:
        if column in data:
            data[column] = pd.to_datetime(data[column], errors="coerce")
    for column in [
        "entry_price", "direction_num", "atr_entry", "tp_atr", "sl_atr",
        "max_holding_minutes", "tp_price", "sl_price", "exit_price",
        "gross_pnl", "pnl",
    ]:
        if column in data:
            data[column] = pd.to_numeric(data[column], errors="coerce")
    return data


def resolve_shadow_observations(ledger: pd.DataFrame, candle_dir: Path) -> pd.DataFrame:
    if ledger.empty:
        return ledger
    m1 = read_candles(
        candle_dir / GOLD_FILES["M1"], 30000,
        timeframe="M1", require_spread=True,
    )
    times = m1.time.to_numpy("datetime64[ns]")
    high = m1.high.to_numpy(float)
    low = m1.low.to_numpy(float)
    open_ = m1.open.to_numpy(float)
    latest_close = pd.Timestamp(m1.time.max()) + pd.Timedelta(minutes=1)
    result = ledger.copy()
    for index, row in result[result.status.astype(str).eq("OPEN")].iterrows():
        entry = pd.Timestamp(row.entry_dt)
        direction = int(row.direction_num)
        planned = entry + pd.Timedelta(minutes=int(row.max_holding_minutes))
        end_exclusive = min(planned, latest_close)
        start_idx = np.searchsorted(times, np.datetime64(entry), side="left")
        end_idx = np.searchsorted(times, np.datetime64(end_exclusive), side="left")
        exit_dt, exit_price, reason = pd.NaT, np.nan, ""
        for candle_index in range(start_idx, end_idx):
            hit_tp = high[candle_index] >= float(row.tp_price) if direction == 1 else low[candle_index] <= float(row.tp_price)
            hit_sl = low[candle_index] <= float(row.sl_price) if direction == 1 else high[candle_index] >= float(row.sl_price)
            if hit_sl or hit_tp:
                if hit_sl:
                    exit_price, reason = float(row.sl_price), "SL"
                else:
                    exit_price, reason = float(row.tp_price), "TP"
                exit_dt = pd.Timestamp(times[candle_index])
                break
        if pd.isna(exit_dt) and latest_close >= planned:
            candle_index = np.searchsorted(times, np.datetime64(planned), side="left")
            if candle_index < len(times):
                exit_dt = pd.Timestamp(times[candle_index])
                exit_price = float(open_[candle_index])
                reason = "TIME"
        if pd.notna(exit_dt):
            gross = direction * (exit_price - float(row.entry_price))
            result.loc[index, [
                "status", "exit_dt", "exit_price", "exit_reason", "gross_pnl", "pnl"
            ]] = ["CLOSED", exit_dt, exit_price, reason, gross, gross - COST]
    return result


def import_base_resolved(path: Path | None) -> pd.DataFrame:
    if path is None or not path.exists():
        return pd.DataFrame(columns=["entry_dt", "exit_dt", "pnl", "source"])
    data = pd.read_csv(path, encoding="utf-8-sig")
    required = {"entry_dt", "exit_dt", "pnl"}
    if not required.issubset(data.columns):
        raise ValueError(
            f"base resolved ledger missing {sorted(required - set(data.columns))}"
        )
    data["entry_dt"] = pd.to_datetime(data.entry_dt, errors="coerce")
    data["exit_dt"] = pd.to_datetime(data.exit_dt, errors="coerce")
    data["pnl"] = pd.to_numeric(data.pnl, errors="coerce")
    data = data.dropna(subset=["entry_dt", "exit_dt", "pnl"])
    if (data.exit_dt < data.entry_dt).any():
        raise ValueError("base resolved ledger contains exit_dt < entry_dt")
    data = data.drop_duplicates(["entry_dt", "exit_dt", "pnl"], keep="last")
    data["source"] = "BASE"
    return data[["entry_dt", "exit_dt", "pnl", "source"]].sort_values(
        ["exit_dt", "entry_dt"]
    ).reset_index(drop=True)


def state_at(time: pd.Timestamp, ledger: pd.DataFrame, base: pd.DataFrame) -> dict[str, Any]:
    """Use only state that was knowable and resolved by ``time``."""
    time = pd.Timestamp(time)
    if len(ledger):
        resolved_candidates = ledger[
            ledger.status.astype(str).eq("CLOSED")
            & pd.to_datetime(ledger.exit_dt, errors="coerce").le(time)
        ][["entry_dt", "exit_dt", "pnl", "source"]].copy()
    else:
        resolved_candidates = pd.DataFrame(
            columns=["entry_dt", "exit_dt", "pnl", "source"]
        )
    resolved_base = base[pd.to_datetime(base.exit_dt, errors="coerce").le(time)].copy()
    resolved = pd.concat([resolved_base, resolved_candidates], ignore_index=True)
    if len(resolved):
        resolved = resolved.sort_values(["exit_dt", "entry_dt"], kind="mergesort")
    values = (
        pd.to_numeric(resolved.pnl, errors="coerce").dropna().to_numpy(float)
        if len(resolved) else np.array([], float)
    )
    curve = np.cumsum(values)
    equity = float(values.sum()) if len(values) else 0.0
    peak = float(max(0.0, curve.max())) if len(curve) else 0.0
    candidate_losses = (
        resolved[(resolved.source != "BASE") & (resolved.pnl < 0)]
        if len(resolved) else pd.DataFrame()
    )
    last_loss = candidate_losses.exit_dt.max() if len(candidate_losses) else pd.NaT
    last_base = resolved[resolved.source == "BASE"].tail(1) if len(resolved) else pd.DataFrame()
    if len(ledger):
        entry_times = pd.to_datetime(ledger.entry_dt, errors="coerce")
        pending = ledger[
            ledger.status.astype(str).eq("OPEN") & entry_times.le(time)
        ]
        observed = ledger[
            ledger.source.isin(["STAGE280", "STAGE281", "STAGE286"])
            & entry_times.le(time)
        ]
    else:
        pending, observed = pd.DataFrame(), pd.DataFrame()
    last_candidate_entry = (
        pd.to_datetime(observed.entry_dt, errors="coerce").max()
        if len(observed) else pd.NaT
    )
    return {
        "equity": equity,
        "peak": peak,
        "dd": peak - equity,
        "last_candidate_loss_exit": last_loss,
        "last_base_exit": last_base.exit_dt.iloc[0] if len(last_base) else pd.NaT,
        "last_base_pnl": float(last_base.pnl.iloc[0]) if len(last_base) else np.nan,
        "pending_candidate_count": int(len(pending)),
        "last_candidate_entry": last_candidate_entry,
        "base_resolved_count": int((resolved.source == "BASE").sum()) if len(resolved) else 0,
    }


def evaluate_shadow_eligibility(
    candidates: pd.DataFrame,
    ledger: pd.DataFrame,
    base: pd.DataFrame,
    base_state_ready: bool = True,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if candidates.empty:
        return pd.DataFrame(), ledger
    existing = set(ledger.candidate_id.astype(str)) if len(ledger) else set()
    decisions: list[dict[str, Any]] = []
    current = ledger.copy()
    for row in candidates.sort_values(
        ["entry_dt", "priority", "candidate_id"]
    ).itertuples(index=False):
        if row.candidate_id in existing:
            continue
        time = pd.Timestamp(row.entry_dt)
        state = state_at(time, current, base)
        reasons: list[str] = []
        if not base_state_ready:
            reasons.append("BASE_PORTFOLIO_STATE_NOT_CONNECTED")
        if state["pending_candidate_count"] > 0:
            reasons.append("UNRESOLVED_CANDIDATE_ACTIVE")
        if row.source in {"STAGE280", "STAGE281"} and state["dd"] > 30.0:
            reasons.append("COMBINED_DD_ABOVE_30")
        if row.source == "STAGE286" and state["dd"] > 10.0:
            reasons.append("SHORT_DD_ABOVE_10")
        if (
            pd.notna(state["last_candidate_entry"])
            and time < pd.Timestamp(state["last_candidate_entry"]) + pd.Timedelta(hours=12)
        ):
            reasons.append("SHARED_12H_COOLDOWN")
        if row.source == "STAGE281":
            if state["base_resolved_count"] == 0:
                reasons.append("BASE_RESOLVED_STATE_MISSING")
            elif not (
                state["last_base_pnl"] < 0
                and pd.Timestamp(state["last_base_exit"]) <= time
                and time <= pd.Timestamp(state["last_base_exit"]) + pd.Timedelta(hours=72)
            ):
                reasons.append("NOT_AFTER_BASE_LOSS_WITHIN_72H")
        if (
            row.source == "STAGE286"
            and pd.notna(state["last_candidate_loss_exit"])
            and time < pd.Timestamp(state["last_candidate_loss_exit"]) + pd.Timedelta(hours=24)
        ):
            reasons.append("SHORT_24H_AFTER_CANDIDATE_LOSS")
        accepted = not reasons
        record = row._asdict()
        record.update(
            {
                "shadow_eligible": accepted,
                "reject_reasons": ";".join(reasons),
                "state_dd": state["dd"],
                "state_equity": state["equity"],
                "base_resolved_count": state["base_resolved_count"],
            }
        )
        decisions.append(record)
        existing.add(row.candidate_id)
        if accepted:
            tp = float(row.entry_price) + int(row.direction_num) * float(row.tp_atr) * float(row.atr_entry)
            sl = float(row.entry_price) - int(row.direction_num) * float(row.sl_atr) * float(row.atr_entry)
            trade = record.copy()
            trade.update(
                {
                    "tp_price": tp, "sl_price": sl, "status": "OPEN",
                    "exit_dt": pd.NaT, "exit_price": np.nan, "exit_reason": "",
                    "gross_pnl": np.nan, "pnl": np.nan,
                }
            )
            current = pd.concat([current, pd.DataFrame([trade])], ignore_index=True)
    return pd.DataFrame(decisions), current


def load_runtime_state(
    path: Path, latest_m5_time: pd.Timestamp, replay_existing: bool
) -> tuple[dict[str, Any], bool]:
    if path.exists():
        return read_json(path), False
    state = {
        "initialized_at_utc": utc_now(),
        "last_processed_m5_time": str(
            pd.Timestamp.min if replay_existing else pd.Timestamp(latest_m5_time)
        ),
        "bootstrap_mode": "REPLAY_EXISTING" if replay_existing else "LATEST_ONLY",
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    return state, True


def update_runtime_state(
    path: Path, state: dict[str, Any], latest_m5_time: pd.Timestamp
) -> None:
    updated = dict(state)
    updated["last_processed_m5_time"] = str(pd.Timestamp(latest_m5_time))
    updated["updated_at_utc"] = utc_now()
    path.write_text(json.dumps(updated, ensure_ascii=False, indent=2), encoding="utf-8")
