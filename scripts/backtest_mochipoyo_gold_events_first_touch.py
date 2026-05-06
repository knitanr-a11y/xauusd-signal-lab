#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Backtest GOLD Mochipoyo event candidates with conservative first-touch logic.

Input:
- event CSV produced by scripts/filter_mochipoyo_candidate_events.py
- GOLD M1 and M5 OHLC CSVs

Output:
- trade-level CSV with first-touch outcome
- summary JSON with pair/rank/direction/month stats and DD

Design choices for the first validation pass:
- H1 x M1 scalp is judged on M1 bars.
- Other GOLD pairs are judged on M5 bars.
- Entry is the event CSV entry_time / entry_price.
- SL is based on the recent swing high/low before entry on the touch timeframe.
- TP is entry +/- RR * risk_distance.
- If TP and SL touch in the same candle, SL wins by default.
- Outcome bars start at or after entry_time. No pre-entry future data is used.

This script does not send notifications and does not adopt signals.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


TF_MINUTES = {"M1": 1, "M5": 5, "M15": 15, "H1": 60, "H4": 240, "D1": 1440}

DEFAULT_TOUCH_TF_BY_BASE_TF = {
    "M1": "M1",
    "M5": "M5",
    "M15": "M5",
    "H1": "M5",
}

DEFAULT_HORIZON_BY_PAIR = {
    "GOLD_H1_M1_SCALP": 180,        # M1 bars = 3h
    "GOLD_H4_M5_SCALP": 96,         # M5 bars = 8h
    "GOLD_H4_M15_DAYTRADE": 192,    # M5 bars = 16h
    "GOLD_D1_H1_DAYTRADE": 576,     # M5 bars = 48h
}

DEFAULT_SWING_LOOKBACK_BY_PAIR = {
    "GOLD_H1_M1_SCALP": 60,         # 60 minutes
    "GOLD_H4_M5_SCALP": 48,         # 4h
    "GOLD_H4_M15_DAYTRADE": 96,     # 8h
    "GOLD_D1_H1_DAYTRADE": 288,     # 24h
}


def sniff_sep(path: Path) -> str:
    sample = path.read_text(encoding="utf-8-sig", errors="replace")[:4096]
    try:
        return csv.Sniffer().sniff(sample, delimiters=";,\t,").delimiter
    except csv.Error:
        return ";" if sample.count(";") >= sample.count(",") else ","


def read_ohlc_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    df = pd.read_csv(path, sep=sniff_sep(path), encoding="utf-8-sig")
    df.columns = [str(c).strip().lower() for c in df.columns]
    df = df.rename(columns={"datetime": "time", "date": "time", "timestamp": "time", "tickvolume": "tick_volume"})
    required = ["time", "open", "high", "low", "close"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise RuntimeError(f"missing required columns in {path}: {missing}; columns={list(df.columns)}")
    df["time"] = pd.to_datetime(df["time"], errors="coerce")
    for c in ["open", "high", "low", "close", "tick_volume", "spread", "real_volume"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(subset=required)
    df = df.sort_values("time", kind="mergesort").drop_duplicates(subset=["time"], keep="last")
    return df.reset_index(drop=True)


def tf_minutes(tf: str) -> int:
    key = str(tf).upper()
    if key not in TF_MINUTES:
        raise ValueError(f"unsupported tf: {tf}")
    return TF_MINUTES[key]


def add_close_time(df: pd.DataFrame, tf: str) -> pd.DataFrame:
    out = df.copy()
    out["close_time"] = out["time"] + pd.to_timedelta(tf_minutes(tf), unit="m")
    return out


def atr14(df: pd.DataFrame) -> pd.Series:
    prev_close = df["close"].shift(1)
    tr = pd.concat(
        [
            (df["high"] - df["low"]).abs(),
            (df["high"] - prev_close).abs(),
            (df["low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.rolling(14, min_periods=14).mean()


def prepare_touch_df(path: Path, tf: str) -> pd.DataFrame:
    df = add_close_time(read_ohlc_csv(path), tf)
    df["atr14"] = atr14(df)
    return df


def finite_float(value: Any) -> float:
    try:
        x = float(value)
    except Exception:
        return float("nan")
    return x if math.isfinite(x) else float("nan")


def choose_touch_tf(base_tf: str) -> str:
    return DEFAULT_TOUCH_TF_BY_BASE_TF.get(str(base_tf).upper(), "M5")


def lower_bound_index(times: pd.Series, t: pd.Timestamp) -> int:
    return int(np.searchsorted(times.to_numpy(dtype="datetime64[ns]"), np.datetime64(t), side="left"))


def swing_stop(
    touch: pd.DataFrame,
    entry_idx: int,
    direction: str,
    entry_price: float,
    lookback: int,
    min_stop_distance: float,
    atr_mult_fallback: float,
) -> tuple[float, float, str]:
    start = max(0, entry_idx - lookback)
    hist = touch.iloc[start:entry_idx]
    if hist.empty:
        return float("nan"), float("nan"), "no_history"

    if direction == "BUY":
        raw_sl = float(hist["low"].min())
        risk = entry_price - raw_sl
    else:
        raw_sl = float(hist["high"].max())
        risk = raw_sl - entry_price

    method = "swing"
    atr = finite_float(touch.iloc[max(0, entry_idx - 1)].get("atr14"))
    fallback_risk = atr * atr_mult_fallback if math.isfinite(atr) and atr > 0 else float("nan")

    if not math.isfinite(risk) or risk <= 0:
        if math.isfinite(fallback_risk) and fallback_risk > 0:
            risk = fallback_risk
            raw_sl = entry_price - risk if direction == "BUY" else entry_price + risk
            method = "atr_fallback_invalid_swing"
        else:
            return float("nan"), float("nan"), "invalid_swing_no_atr"

    if risk < min_stop_distance:
        risk = min_stop_distance
        raw_sl = entry_price - risk if direction == "BUY" else entry_price + risk
        method = "min_stop_distance"

    return raw_sl, risk, method


def simulate_first_touch(
    touch: pd.DataFrame,
    entry_time: pd.Timestamp,
    direction: str,
    entry_price: float,
    sl_price: float,
    tp_price: float,
    horizon_bars: int,
    inbar_priority: str,
) -> tuple[str, float, str, int, str, float, float]:
    entry_idx = lower_bound_index(touch["time"], entry_time)
    if entry_idx >= len(touch):
        return "NO_DATA", 0.0, "", 0, "entry_after_data", float("nan"), float("nan")

    end_idx = min(len(touch), entry_idx + horizon_bars)
    future = touch.iloc[entry_idx:end_idx]
    if future.empty:
        return "NO_DATA", 0.0, "", 0, "empty_future", float("nan"), float("nan")

    max_fav = 0.0
    max_adv = 0.0
    for offset, bar in enumerate(future.itertuples(index=False), start=0):
        high = float(getattr(bar, "high"))
        low = float(getattr(bar, "low"))
        time = getattr(bar, "time")
        if direction == "BUY":
            hit_tp = high >= tp_price
            hit_sl = low <= sl_price
            max_fav = max(max_fav, high - entry_price)
            max_adv = max(max_adv, entry_price - low)
        else:
            hit_tp = low <= tp_price
            hit_sl = high >= sl_price
            max_fav = max(max_fav, entry_price - low)
            max_adv = max(max_adv, high - entry_price)

        if hit_tp and hit_sl:
            if inbar_priority.upper() == "TP":
                return "WIN", 1.0, str(pd.Timestamp(time)), offset, "both_hit_tp_priority", max_fav, max_adv
            return "LOSS", -1.0, str(pd.Timestamp(time)), offset, "both_hit_sl_priority", max_fav, max_adv
        if hit_tp:
            return "WIN", 1.0, str(pd.Timestamp(time)), offset, "tp_first", max_fav, max_adv
        if hit_sl:
            return "LOSS", -1.0, str(pd.Timestamp(time)), offset, "sl_first", max_fav, max_adv

    return "TIMEOUT", 0.0, str(pd.Timestamp(future.iloc[-1]["time"])), len(future) - 1, "no_touch", max_fav, max_adv


def max_drawdown_r(r_values: pd.Series) -> float:
    if r_values.empty:
        return 0.0
    eq = r_values.cumsum()
    peak = eq.cummax()
    dd = peak - eq
    return float(dd.max()) if len(dd) else 0.0


def max_consecutive_losses(outcomes: pd.Series) -> int:
    max_run = 0
    cur = 0
    for x in outcomes.astype(str):
        if x == "LOSS":
            cur += 1
            max_run = max(max_run, cur)
        elif x == "WIN":
            cur = 0
    return max_run


def summary_group(df: pd.DataFrame, keys: list[str]) -> list[dict]:
    rows = []
    for key, g in df.groupby(keys, dropna=False):
        if not isinstance(key, tuple):
            key = (key,)
        wins = int((g["outcome"] == "WIN").sum())
        losses = int((g["outcome"] == "LOSS").sum())
        timeouts = int((g["outcome"] == "TIMEOUT").sum())
        resolved = wins + losses
        gross_profit = float(g.loc[g["r_result"] > 0, "r_result"].sum())
        gross_loss = float(-g.loc[g["r_result"] < 0, "r_result"].sum())
        pf = gross_profit / gross_loss if gross_loss > 0 else None
        item = {k: v for k, v in zip(keys, key)}
        item.update(
            {
                "trades": int(len(g)),
                "resolved": resolved,
                "wins": wins,
                "losses": losses,
                "timeouts": timeouts,
                "win_rate_resolved": wins / resolved if resolved > 0 else None,
                "total_r": float(g["r_result"].sum()),
                "avg_r": float(g["r_result"].mean()) if len(g) else None,
                "pf": pf,
                "max_dd_r": max_drawdown_r(g["r_result"]),
                "max_consecutive_losses": max_consecutive_losses(g["outcome"]),
            }
        )
        rows.append(item)
    return rows


def build_summary(df: pd.DataFrame, output_csv: Path, args: argparse.Namespace) -> dict:
    wins = int((df["outcome"] == "WIN").sum())
    losses = int((df["outcome"] == "LOSS").sum())
    timeouts = int((df["outcome"] == "TIMEOUT").sum())
    no_data = int((df["outcome"] == "NO_DATA").sum())
    resolved = wins + losses
    gross_profit = float(df.loc[df["r_result"] > 0, "r_result"].sum())
    gross_loss = float(-df.loc[df["r_result"] < 0, "r_result"].sum())
    pf = gross_profit / gross_loss if gross_loss > 0 else None
    work = df.copy()
    work["entry_month"] = pd.to_datetime(work["entry_time"]).dt.strftime("%Y-%m")
    return {
        "input_events": int(len(df)),
        "output_csv": str(output_csv),
        "rr": args.rr,
        "inbar_priority": args.inbar_priority,
        "wins": wins,
        "losses": losses,
        "timeouts": timeouts,
        "no_data": no_data,
        "resolved": resolved,
        "win_rate_resolved": wins / resolved if resolved > 0 else None,
        "total_r": float(df["r_result"].sum()),
        "avg_r": float(df["r_result"].mean()) if len(df) else None,
        "pf": pf,
        "max_dd_r": max_drawdown_r(df["r_result"]),
        "max_consecutive_losses": max_consecutive_losses(df["outcome"]),
        "by_pair": summary_group(work, ["pair_name"]),
        "by_pair_rank": summary_group(work, ["pair_name", "candidate_rank"]),
        "by_direction": summary_group(work, ["direction"]),
        "by_month": summary_group(work, ["entry_month"]),
    }


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Backtest GOLD Mochipoyo events with first-touch logic.")
    p.add_argument("--events-csv", required=True)
    p.add_argument("--m1-csv", required=True)
    p.add_argument("--m5-csv", required=True)
    p.add_argument("--output-csv", required=True)
    p.add_argument("--summary-json", default=None)
    p.add_argument("--rr", type=float, default=1.2)
    p.add_argument("--min-stop-distance", type=float, default=1.0)
    p.add_argument("--atr-mult-fallback", type=float, default=0.8)
    p.add_argument("--inbar-priority", choices=["SL", "TP"], default="SL")
    p.add_argument("--max-events", type=int, default=0)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    events = pd.read_csv(args.events_csv, encoding="utf-8-sig")
    if args.max_events and args.max_events > 0:
        events = events.head(args.max_events).copy()
    events["entry_time"] = pd.to_datetime(events["entry_time"], errors="coerce")
    events["entry_price"] = pd.to_numeric(events["entry_price"], errors="coerce")
    events = events.dropna(subset=["entry_time", "entry_price", "direction", "pair_name", "base_tf"])
    events = events.sort_values("entry_time", kind="mergesort").reset_index(drop=True)

    touch_data = {
        "M1": prepare_touch_df(Path(args.m1_csv), "M1"),
        "M5": prepare_touch_df(Path(args.m5_csv), "M5"),
    }
    print("backtest_mochipoyo_gold_events_first_touch")
    print(f"events: {len(events)}")
    print(f"M1 rows: {len(touch_data['M1'])} range={touch_data['M1']['time'].min()} -> {touch_data['M1']['time'].max()}")
    print(f"M5 rows: {len(touch_data['M5'])} range={touch_data['M5']['time'].min()} -> {touch_data['M5']['time'].max()}")

    result_rows = []
    for row in events.to_dict("records"):
        pair = str(row.get("pair_name"))
        base_tf = str(row.get("base_tf")).upper()
        direction = str(row.get("direction")).upper()
        entry_time = pd.Timestamp(row["entry_time"])
        entry_price = finite_float(row.get("entry_price"))
        touch_tf = choose_touch_tf(base_tf)
        touch = touch_data[touch_tf]
        entry_idx = lower_bound_index(touch["time"], entry_time)
        lookback = DEFAULT_SWING_LOOKBACK_BY_PAIR.get(pair, 96)
        horizon = DEFAULT_HORIZON_BY_PAIR.get(pair, 192)
        sl_price, risk_distance, sl_method = swing_stop(
            touch,
            entry_idx,
            direction,
            entry_price,
            lookback,
            args.min_stop_distance,
            args.atr_mult_fallback,
        )
        if not math.isfinite(risk_distance) or risk_distance <= 0:
            outcome = "NO_DATA"
            r_result = 0.0
            exit_time = ""
            bars_to_exit = 0
            exit_reason = sl_method
            max_fav = float("nan")
            max_adv = float("nan")
            tp_price = float("nan")
        else:
            tp_price = entry_price + args.rr * risk_distance if direction == "BUY" else entry_price - args.rr * risk_distance
            outcome, unit_r, exit_time, bars_to_exit, exit_reason, max_fav, max_adv = simulate_first_touch(
                touch,
                entry_time,
                direction,
                entry_price,
                sl_price,
                tp_price,
                horizon,
                args.inbar_priority,
            )
            r_result = args.rr if outcome == "WIN" else (-1.0 if outcome == "LOSS" else 0.0)

        out = dict(row)
        out.update(
            {
                "touch_tf": touch_tf,
                "rr": args.rr,
                "sl_price": sl_price,
                "tp_price": tp_price,
                "risk_distance": risk_distance,
                "sl_method": sl_method,
                "horizon_bars": horizon,
                "swing_lookback_bars": lookback,
                "outcome": outcome,
                "r_result": r_result,
                "exit_time": exit_time,
                "bars_to_exit": bars_to_exit,
                "exit_reason": exit_reason,
                "max_favorable_price_move": max_fav,
                "max_adverse_price_move": max_adv,
                "max_favorable_r": max_fav / risk_distance if math.isfinite(max_fav) and math.isfinite(risk_distance) and risk_distance > 0 else float("nan"),
                "max_adverse_r": max_adv / risk_distance if math.isfinite(max_adv) and math.isfinite(risk_distance) and risk_distance > 0 else float("nan"),
            }
        )
        result_rows.append(out)

    results = pd.DataFrame(result_rows)
    output_csv = Path(args.output_csv)
    summary_json = Path(args.summary_json) if args.summary_json else output_csv.with_suffix(".summary.json")
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    summary_json.parent.mkdir(parents=True, exist_ok=True)
    results.to_csv(output_csv, index=False, encoding="utf-8-sig")
    summary = build_summary(results, output_csv, args)
    summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"output_csv: {output_csv}")
    print(f"summary_json: {summary_json}")
    print(f"wins: {summary['wins']}")
    print(f"losses: {summary['losses']}")
    print(f"timeouts: {summary['timeouts']}")
    print(f"win_rate_resolved: {summary['win_rate_resolved']}")
    print(f"total_r: {summary['total_r']}")
    print(f"pf: {summary['pf']}")
    print(f"max_dd_r: {summary['max_dd_r']}")
    print(f"max_consecutive_losses: {summary['max_consecutive_losses']}")
    print("done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
