#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DataFrame risk enricher for the Mochipoyo minimal scanner.

This module is the function-oriented counterpart of
scripts/enrich_mochipoyo_live_payload_risk.py.

Design choices:
- No Discord sending.
- No order execution.
- DataFrame in -> DataFrame out.
- GOLD uses live_risk_status.
- BTC uses btc_live_risk_status and requires spread-aware fields.

The underlying SL/TP logic intentionally mirrors enrich_mochipoyo_live_payload_risk.py:
- touch_tf: M5 base -> M1, M15/H1 base -> M5
- SL: previous swing high/low over pair-specific lookback
- TP: fixed RR from risk distance
- min stop distance fallback
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Mapping

import numpy as np
import pandas as pd

try:
    from scripts.mochipoyo_candidate_normalizer import ensure_normalized_columns, split_risk_ok_ng
except ModuleNotFoundError:
    from mochipoyo_candidate_normalizer import ensure_normalized_columns, split_risk_ok_ng  # type: ignore

TOUCH_TF_BY_BASE_TF: dict[str, str] = {
    "M1": "M1",
    "M5": "M1",
    "M15": "M5",
    "H1": "M5",
}

DEFAULT_LOOKBACK_BY_PAIR: dict[str, int] = {
    "GOLD_H1_M1_SCALP": 60,
    "GOLD_H4_M5_SCALP": 120,
    "GOLD_H4_M15_DAYTRADE": 96,
    "GOLD_D1_H1_DAYTRADE": 288,
    "BTC_M15_M1_SUPER_SCALP": 60,
    "BTC_H1_M5_SCALP": 120,
    "BTC_H4_M15_DAYTRADE": 96,
    "BTC_D1_H1_DAYTRADE": 288,
}

BTC_REQUIRED_SPREAD_COLUMNS: list[str] = [
    "current_spread_points",
    "current_spread_price",
    "mode_spread_points",
    "mode_spread_price",
    "effective_spread_price",
    "spread_to_sl_ratio",
    "spread_to_tp_ratio",
    "net_sl_after_spread_price",
    "net_tp_after_spread_price",
    "effective_rr_after_spread",
]


@dataclass(frozen=True)
class RiskEnrichConfig:
    rr: float = 1.2
    gold_min_stop_distance: float = 1.0
    btc_min_stop_distance: float = 50.0
    btc_point_size: float = 0.01
    btc_spread_caution_threshold: float = 0.07


def finite_float(value: object) -> float:
    try:
        x = float(value)  # type: ignore[arg-type]
    except Exception:
        return float("nan")
    return x if math.isfinite(x) else float("nan")


def lower_bound_index(times: pd.Series, t: pd.Timestamp) -> int:
    return int(np.searchsorted(times.to_numpy(dtype="datetime64[ns]"), np.datetime64(t), side="left"))


def mode_spread_points(df: pd.DataFrame) -> float:
    if "spread" not in df.columns:
        return float("nan")
    s = pd.to_numeric(df["spread"], errors="coerce").dropna()
    s = s[s > 0]
    if s.empty:
        return float("nan")
    return float(s.mode().iloc[0])


def latest_spread_points_before_or_at(df: pd.DataFrame, t: pd.Timestamp) -> float:
    if df.empty or "spread" not in df.columns or "time" not in df.columns or pd.isna(t):
        return float("nan")
    work = df[["time", "spread"]].copy()
    work["time"] = pd.to_datetime(work["time"], errors="coerce")
    work["spread"] = pd.to_numeric(work["spread"], errors="coerce")
    work = work.dropna(subset=["time", "spread"]).sort_values("time")
    work = work[(work["spread"] > 0) & (work["time"] <= pd.Timestamp(t))]
    if work.empty:
        return float("nan")
    return finite_float(work.iloc[-1]["spread"])


def infer_base_tf(row: pd.Series) -> str:
    if "base_tf" in row.index and pd.notna(row.get("base_tf")):
        return str(row.get("base_tf")).upper()
    pair = str(row.get("pair_name", ""))
    if "_M1_" in pair or pair.endswith("_M1_SCALP"):
        return "M1"
    if "_M5_" in pair or pair.endswith("_M5_SCALP"):
        return "M5"
    if "_M15_" in pair or pair.endswith("_M15_DAYTRADE"):
        return "M15"
    if "_H1_" in pair or pair.endswith("_H1_DAYTRADE"):
        return "H1"
    return "M15"


def choose_touch_tf(base_tf: str) -> str:
    return TOUCH_TF_BY_BASE_TF.get(str(base_tf).upper(), "M5")


def _prepare_touch_df(df: pd.DataFrame, tf: str) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    out = df.copy()
    if "time" not in out.columns:
        raise RuntimeError(f"touch dataframe {tf} is missing time column")
    for col in ["time"]:
        out[col] = pd.to_datetime(out[col], errors="coerce")
    for col in ["open", "high", "low", "close", "spread", "tick_volume"]:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")
    required = ["time", "high", "low"]
    out = out.dropna(subset=required).sort_values("time").drop_duplicates("time", keep="last").reset_index(drop=True)
    out["touch_tf"] = tf
    return out


def prepare_touch_data(touch_data: Mapping[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    return {str(tf).upper(): _prepare_touch_df(df, str(tf).upper()) for tf, df in touch_data.items() if df is not None}


def _base_risk_for_row(
    row: pd.Series,
    *,
    symbol: str,
    touch_data: Mapping[str, pd.DataFrame],
    rr: float,
    min_stop_distance: float,
) -> dict[str, object]:
    base_tf = infer_base_tf(row)
    pair_name = str(row.get("pair_name", ""))
    direction = str(row.get("direction", "")).upper()
    entry_price = finite_float(row.get("entry_price"))
    entry_time = pd.to_datetime(row.get("entry_time"), errors="coerce")
    touch_tf = choose_touch_tf(base_tf)
    touch = touch_data.get(touch_tf)
    if touch is None or touch.empty or pd.isna(entry_time) or not math.isfinite(entry_price):
        return {"risk_calc_status": "NO_TOUCH_DATA_OR_ENTRY", "touch_tf": touch_tf}
    entry_idx = lower_bound_index(touch["time"], pd.Timestamp(entry_time))
    if entry_idx <= 0:
        return {"risk_calc_status": "NO_HISTORY", "touch_tf": touch_tf}
    lookback = DEFAULT_LOOKBACK_BY_PAIR.get(pair_name, 96)
    hist = touch.iloc[max(0, entry_idx - lookback):entry_idx]
    if hist.empty:
        return {"risk_calc_status": "EMPTY_HISTORY", "touch_tf": touch_tf}

    if direction == "BUY":
        sl_price = float(hist["low"].min())
        risk = entry_price - sl_price
    elif direction == "SELL":
        sl_price = float(hist["high"].max())
        risk = sl_price - entry_price
    else:
        return {"risk_calc_status": "INVALID_DIRECTION", "touch_tf": touch_tf}

    sl_method = "swing"
    if not math.isfinite(risk) or risk <= 0:
        return {"risk_calc_status": "INVALID_SWING_RISK", "touch_tf": touch_tf}
    if risk < min_stop_distance:
        risk = min_stop_distance
        sl_price = entry_price - risk if direction == "BUY" else entry_price + risk
        sl_method = "min_stop_distance"

    tp_price = entry_price + rr * risk if direction == "BUY" else entry_price - rr * risk
    return {
        "risk_calc_status": "OK",
        "touch_tf": touch_tf,
        "sl_method": sl_method,
        "rr": rr,
        "sl_price": sl_price,
        "tp_price": tp_price,
        "risk_distance": risk,
        "reward_distance": rr * risk,
        "gross_sl_distance_price": risk,
        "gross_tp_distance_price": rr * risk,
    }


def _btc_spread_metrics(
    row: pd.Series,
    *,
    risk: float,
    rr: float,
    touch_data: Mapping[str, pd.DataFrame],
    point_size: float,
) -> dict[str, object]:
    entry_time = pd.to_datetime(row.get("entry_time"), errors="coerce")
    spread_source = touch_data.get("M1")
    if spread_source is None or spread_source.empty:
        spread_source = touch_data.get("M5")
    current_points = latest_spread_points_before_or_at(spread_source if spread_source is not None else pd.DataFrame(), pd.Timestamp(entry_time))
    mode_points = mode_spread_points(spread_source if spread_source is not None else pd.DataFrame())
    effective_points = current_points if math.isfinite(current_points) else mode_points
    current_price = current_points * point_size if math.isfinite(current_points) else float("nan")
    mode_price = mode_points * point_size if math.isfinite(mode_points) else float("nan")
    effective_price = effective_points * point_size if math.isfinite(effective_points) else float("nan")

    spread_to_sl = effective_price / risk if math.isfinite(effective_price) and risk > 0 else float("nan")
    spread_to_tp = effective_price / (rr * risk) if math.isfinite(effective_price) and risk > 0 and rr > 0 else float("nan")
    net_sl = risk + effective_price if math.isfinite(effective_price) else float("nan")
    net_tp = rr * risk - effective_price if math.isfinite(effective_price) else float("nan")
    effective_rr = net_tp / net_sl if math.isfinite(net_tp) and math.isfinite(net_sl) and net_sl > 0 else float("nan")
    return {
        "current_spread_points": current_points,
        "current_spread_price": current_price,
        "mode_spread_points": mode_points,
        "mode_spread_price": mode_price,
        "effective_spread_price": effective_price,
        "spread_to_sl_ratio": spread_to_sl,
        "spread_to_tp_ratio": spread_to_tp,
        "net_sl_after_spread_price": net_sl,
        "net_tp_after_spread_price": net_tp,
        "effective_rr_after_spread": effective_rr,
    }


def _btc_spread_ready(row: Mapping[str, Any]) -> bool:
    for col in BTC_REQUIRED_SPREAD_COLUMNS:
        if col not in row:
            return False
        if not math.isfinite(finite_float(row.get(col))):
            return False
    return True


def infer_risk_for_row(
    row: pd.Series,
    *,
    touch_data: Mapping[str, pd.DataFrame],
    config: RiskEnrichConfig,
) -> dict[str, object]:
    symbol = str(row.get("symbol", "")).upper()
    min_stop = config.btc_min_stop_distance if symbol == "BTC" else config.gold_min_stop_distance
    out = _base_risk_for_row(
        row,
        symbol=symbol,
        touch_data=touch_data,
        rr=config.rr,
        min_stop_distance=min_stop,
    )
    calc_status = str(out.get("risk_calc_status", ""))
    if symbol == "BTC":
        if calc_status == "OK":
            out.update(_btc_spread_metrics(row, risk=finite_float(out.get("risk_distance")), rr=config.rr, touch_data=touch_data, point_size=config.btc_point_size))
            out["btc_live_risk_status"] = "OK" if _btc_spread_ready(out) else "SPREAD_FIELDS_NOT_READY"
            if out["btc_live_risk_status"] != "OK":
                out["risk_reject_reason"] = "BTC_SPREAD_FIELDS_NOT_READY"
        else:
            out["btc_live_risk_status"] = calc_status
            out["risk_reject_reason"] = calc_status
        out["live_risk_status"] = pd.NA
    else:
        out["live_risk_status"] = "OK" if calc_status == "OK" else calc_status
        out["btc_live_risk_status"] = pd.NA
        if calc_status != "OK":
            out["risk_reject_reason"] = calc_status
    return out


def update_btc_spread_caution(df: pd.DataFrame, threshold: float) -> pd.DataFrame:
    if "caution_labels" not in df.columns or "spread_to_sl_ratio" not in df.columns:
        return df
    out = df.copy()
    for idx in out.index:
        labels = str(out.at[idx, "caution_labels"] or "NONE")
        spr = finite_float(out.at[idx, "spread_to_sl_ratio"])
        parts = [] if labels == "NONE" else [x for x in labels.split(";") if x]
        if math.isfinite(spr) and spr > threshold and "SPREAD_TO_SL_HIGH" not in parts:
            parts.append("SPREAD_TO_SL_HIGH")
        out.at[idx, "caution_labels"] = ";".join(parts) if parts else "NONE"
    return out


def enrich_candidates_risk(
    df: pd.DataFrame,
    *,
    touch_data: Mapping[str, pd.DataFrame],
    config: RiskEnrichConfig | None = None,
) -> pd.DataFrame:
    """Return normalized candidates enriched with GOLD/BTC risk fields."""
    config = config or RiskEnrichConfig()
    if df.empty:
        return ensure_normalized_columns(df.copy())
    prepared_touch = prepare_touch_data(touch_data)
    work = df.copy()
    metrics = [infer_risk_for_row(row, touch_data=prepared_touch, config=config) for _, row in work.iterrows()]
    met = pd.DataFrame(metrics, index=work.index)
    out = work.copy()
    for col in met.columns:
        out[col] = met[col]

    # Canonical risk_status remains useful for existing comparison/split code.
    # Under B案, BTC also exposes btc_live_risk_status separately.
    if "btc_live_risk_status" in out.columns:
        btc_mask = out.get("symbol", pd.Series([pd.NA] * len(out), index=out.index)).astype("string").str.upper() == "BTC"
        out.loc[btc_mask, "risk_status"] = out.loc[btc_mask, "btc_live_risk_status"]
    if "live_risk_status" in out.columns:
        gold_mask = out.get("symbol", pd.Series([pd.NA] * len(out), index=out.index)).astype("string").str.upper() != "BTC"
        out.loc[gold_mask, "risk_status"] = out.loc[gold_mask, "live_risk_status"]

    out = update_btc_spread_caution(out, config.btc_spread_caution_threshold)
    return ensure_normalized_columns(out)


def split_live_risk_ok_ng(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split enriched candidates using GOLD live_risk_status and BTC btc_live_risk_status."""
    if df.empty:
        return df.copy(), df.copy()
    symbol = df.get("symbol", pd.Series([pd.NA] * len(df), index=df.index)).astype("string").str.upper()
    live_status = df.get("live_risk_status", pd.Series([pd.NA] * len(df), index=df.index)).astype("string").str.upper()
    btc_status = df.get("btc_live_risk_status", pd.Series([pd.NA] * len(df), index=df.index)).astype("string").str.upper()
    gold_ok = (symbol != "BTC") & (live_status == "OK")
    btc_ok = (symbol == "BTC") & (btc_status == "OK")
    return df.loc[gold_ok | btc_ok].copy(), df.loc[~(gold_ok | btc_ok)].copy()


__all__ = [
    "BTC_REQUIRED_SPREAD_COLUMNS",
    "DEFAULT_LOOKBACK_BY_PAIR",
    "RiskEnrichConfig",
    "TOUCH_TF_BY_BASE_TF",
    "choose_touch_tf",
    "enrich_candidates_risk",
    "finite_float",
    "infer_base_tf",
    "infer_risk_for_row",
    "mode_spread_points",
    "prepare_touch_data",
    "split_live_risk_ok_ng",
]
