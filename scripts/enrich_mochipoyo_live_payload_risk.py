#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Enrich Mochipoyo live dry-run payloads with SL/TP/risk fields.

Primary use:
- GOLD strict payloads currently do not contain SL/TP.
- BTC strict payloads already contain spread-aware fields, but this script can
  recompute/fill missing values if needed.

This script does not send Discord messages.
"""
from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path

import numpy as np
import pandas as pd

TOUCH_TF_BY_BASE_TF = {
    "M1": "M1",
    "M5": "M1",
    "M15": "M5",
    "H1": "M5",
}

DEFAULT_LOOKBACK_BY_PAIR = {
    # GOLD
    "GOLD_H1_M1_SCALP": 60,
    "GOLD_H4_M5_SCALP": 120,
    "GOLD_H4_M15_DAYTRADE": 96,
    "GOLD_D1_H1_DAYTRADE": 288,
    # BTC
    "BTC_M15_M1_SUPER_SCALP": 60,
    "BTC_H1_M5_SCALP": 120,
    "BTC_H4_M15_DAYTRADE": 96,
    "BTC_D1_H1_DAYTRADE": 288,
}


def sniff_sep(path: Path) -> str:
    sample = path.read_text(encoding="utf-8-sig", errors="replace")[:4096]
    try:
        return csv.Sniffer().sniff(sample, delimiters=";,\t,").delimiter
    except csv.Error:
        return ";" if sample.count(";") >= sample.count(",") else ","


def read_ohlc_csv(path: str, tf: str) -> pd.DataFrame:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"OHLC CSV not found: {p}")
    df = pd.read_csv(p, sep=sniff_sep(p), encoding="utf-8-sig")
    df.columns = [str(c).strip().lower() for c in df.columns]
    df = df.rename(columns={"datetime": "time", "timestamp": "time", "tickvolume": "tick_volume"})
    required = ["time", "open", "high", "low", "close"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise RuntimeError(f"missing columns in {p}: {missing}; columns={list(df.columns)}")
    df["time"] = pd.to_datetime(df["time"], errors="coerce")
    for c in ["open", "high", "low", "close", "spread", "tick_volume"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(subset=required).sort_values("time").drop_duplicates("time", keep="last").reset_index(drop=True)
    df["touch_tf"] = tf
    return df


def mode_spread_points(df: pd.DataFrame) -> float:
    if "spread" not in df.columns:
        return float("nan")
    s = pd.to_numeric(df["spread"], errors="coerce").dropna()
    s = s[s > 0]
    if s.empty:
        return float("nan")
    return float(s.mode().iloc[0])


def lower_bound_index(times: pd.Series, t: pd.Timestamp) -> int:
    return int(np.searchsorted(times.to_numpy(dtype="datetime64[ns]"), np.datetime64(t), side="left"))


def finite_float(value: object) -> float:
    try:
        x = float(value)  # type: ignore[arg-type]
    except Exception:
        return float("nan")
    return x if math.isfinite(x) else float("nan")


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


def infer_risk_for_row(
    row: pd.Series,
    symbol: str,
    touch_data: dict[str, pd.DataFrame],
    rr: float,
    min_stop_distance: float,
    spread_points: float,
    point_size: float,
) -> dict[str, object]:
    base_tf = infer_base_tf(row)
    pair_name = str(row.get("pair_name", ""))
    direction = str(row.get("direction", "")).upper()
    entry_price = finite_float(row.get("entry_price"))
    entry_time = pd.to_datetime(row.get("entry_time"), errors="coerce")
    touch_tf = choose_touch_tf(base_tf)
    touch = touch_data.get(touch_tf)
    if touch is None or touch.empty or pd.isna(entry_time) or not math.isfinite(entry_price):
        return {"live_risk_status": "NO_TOUCH_DATA_OR_ENTRY"}
    entry_idx = lower_bound_index(touch["time"], pd.Timestamp(entry_time))
    if entry_idx <= 0:
        return {"live_risk_status": "NO_HISTORY"}
    lookback = DEFAULT_LOOKBACK_BY_PAIR.get(pair_name, 96)
    hist = touch.iloc[max(0, entry_idx - lookback):entry_idx]
    if hist.empty:
        return {"live_risk_status": "EMPTY_HISTORY"}

    if direction == "BUY":
        sl_price = float(hist["low"].min())
        risk = entry_price - sl_price
    elif direction == "SELL":
        sl_price = float(hist["high"].max())
        risk = sl_price - entry_price
    else:
        return {"live_risk_status": "INVALID_DIRECTION"}

    sl_method = "swing"
    if not math.isfinite(risk) or risk <= 0:
        return {"live_risk_status": "INVALID_SWING_RISK"}
    if risk < min_stop_distance:
        risk = min_stop_distance
        sl_price = entry_price - risk if direction == "BUY" else entry_price + risk
        sl_method = "min_stop_distance"

    tp_price = entry_price + rr * risk if direction == "BUY" else entry_price - rr * risk
    out = {
        "live_risk_status": "OK",
        "touch_tf": touch_tf,
        "sl_method": sl_method,
        "rr": rr,
        "sl_price": sl_price,
        "tp_price": tp_price,
        "risk_distance": risk,
        "gross_sl_distance_price": risk,
        "gross_tp_distance_price": rr * risk,
    }

    if symbol.upper() == "BTC":
        spread_price = spread_points * point_size if math.isfinite(spread_points) else float("nan")
        spread_to_sl = spread_price / risk if math.isfinite(spread_price) and risk > 0 else float("nan")
        spread_to_tp = spread_price / (rr * risk) if math.isfinite(spread_price) and risk > 0 and rr > 0 else float("nan")
        net_sl = risk + spread_price if math.isfinite(spread_price) else float("nan")
        net_tp = rr * risk - spread_price if math.isfinite(spread_price) else float("nan")
        effective_rr = net_tp / net_sl if math.isfinite(net_tp) and math.isfinite(net_sl) and net_sl > 0 else float("nan")
        out.update({
            "mode_spread_points": spread_points,
            "mode_spread_price": spread_price,
            "spread_to_sl_ratio": spread_to_sl,
            "spread_to_tp_ratio": spread_to_tp,
            "net_sl_after_spread_price": net_sl,
            "net_tp_after_spread_price": net_tp,
            "effective_rr_after_spread": effective_rr,
        })
    return out


def update_btc_spread_caution(df: pd.DataFrame, threshold: float) -> pd.DataFrame:
    if "caution_labels" not in df.columns or "spread_to_sl_ratio" not in df.columns:
        return df
    out = df.copy()
    for idx in out.index:
        labels = str(out.at[idx, "caution_labels"] or "NONE")
        try:
            spr = float(out.at[idx, "spread_to_sl_ratio"])
        except Exception:
            continue
        parts = [] if labels == "NONE" else [x for x in labels.split(";") if x]
        if spr > threshold and "SPREAD_TO_SL_HIGH" not in parts:
            parts.append("SPREAD_TO_SL_HIGH")
        out.at[idx, "caution_labels"] = ";".join(parts) if parts else "NONE"
    return out


def main() -> int:
    p = argparse.ArgumentParser(description="Enrich Mochipoyo live dry-run payloads with SL/TP/risk fields.")
    p.add_argument("--input-csv", required=True)
    p.add_argument("--output-csv", required=True)
    p.add_argument("--symbol", choices=["GOLD", "BTC"], required=True)
    p.add_argument("--m1-csv", required=True)
    p.add_argument("--m5-csv", required=True)
    p.add_argument("--rr", type=float, default=1.2)
    p.add_argument("--min-stop-distance", type=float, default=None)
    p.add_argument("--btc-point-size", type=float, default=0.01)
    p.add_argument("--btc-spread-points", type=float, default=0.0)
    p.add_argument("--btc-spread-caution-threshold", type=float, default=0.07)
    args = p.parse_args()

    symbol = args.symbol.upper()
    min_stop_distance = args.min_stop_distance
    if min_stop_distance is None:
        min_stop_distance = 1.0 if symbol == "GOLD" else 50.0

    df = pd.read_csv(args.input_csv, encoding="utf-8-sig")
    if "entry_time" in df.columns:
        df["entry_time"] = pd.to_datetime(df["entry_time"], errors="coerce")
    touch_data = {
        "M1": read_ohlc_csv(args.m1_csv, "M1"),
        "M5": read_ohlc_csv(args.m5_csv, "M5"),
    }

    spread_points = float("nan")
    if symbol == "BTC":
        if args.btc_spread_points > 0:
            spread_points = float(args.btc_spread_points)
        else:
            spread_points = mode_spread_points(touch_data["M1"])
            if not math.isfinite(spread_points):
                spread_points = mode_spread_points(touch_data["M5"])

    metrics = [
        infer_risk_for_row(
            row,
            symbol=symbol,
            touch_data=touch_data,
            rr=args.rr,
            min_stop_distance=float(min_stop_distance),
            spread_points=spread_points,
            point_size=args.btc_point_size,
        )
        for _, row in df.iterrows()
    ]
    met = pd.DataFrame(metrics, index=df.index)
    out = df.copy()
    for c in met.columns:
        out[c] = met[c]
    if symbol == "BTC":
        out = update_btc_spread_caution(out, args.btc_spread_caution_threshold)

    output = Path(args.output_csv)
    output.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(output, index=False, encoding="utf-8-sig")

    status_counts = out.get("live_risk_status", pd.Series(dtype=str)).astype(str).value_counts().to_dict()
    print("enrich_mochipoyo_live_payload_risk")
    print(f"symbol: {symbol}")
    print(f"input_rows: {len(df)}")
    print(f"output_csv: {output}")
    print(f"status_counts: {status_counts}")
    if symbol == "BTC":
        print(f"mode_spread_points: {spread_points}")
        if "spread_to_sl_ratio" in out.columns:
            print(f"avg_spread_to_sl_ratio: {pd.to_numeric(out['spread_to_sl_ratio'], errors='coerce').mean()}")
            print(f"avg_effective_rr_after_spread: {pd.to_numeric(out['effective_rr_after_spread'], errors='coerce').mean()}")
    print("done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
