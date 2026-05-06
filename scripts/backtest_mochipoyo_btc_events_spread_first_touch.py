#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Backtest BTC Mochipoyo event candidates with spread-aware first-touch logic.

This is the BTC counterpart of the GOLD first-touch backtest, but BTC evaluation
must be based on net results after spread.

Assumptions:
- OHLC prices are treated as bid/mid-like chart prices from MT5 CSV.
- spread column is in points.
- spread_price = mode(spread_points) * point_size by default.
- For a WIN, net reward is reduced by spread_price.
- For a LOSS, actual risk includes spread_price and is normalized to -1R.
- effective_rr_after_spread = max(RR * gross_risk - spread_price, 0) / (gross_risk + spread_price).
- TIMEOUT is treated as 0R for both gross and net in this first validation pass.

No notification or AI review is performed.
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

TOUCH_TF_BY_BASE_TF = {
    "M1": "M1",
    "M5": "M1",
    "M15": "M5",
    "H1": "M5",
}

DEFAULT_HORIZON_BY_PAIR = {
    "BTC_M15_M1_SUPER_SCALP": 180,   # M1 bars = 3h
    "BTC_H1_M5_SCALP": 144,          # M1 bars = 2.4h because base M5 uses M1 touch
    "BTC_H4_M15_DAYTRADE": 192,      # M5 bars = 16h
    "BTC_D1_H1_DAYTRADE": 576,       # M5 bars = 48h
}

DEFAULT_SWING_LOOKBACK_BY_PAIR = {
    "BTC_M15_M1_SUPER_SCALP": 60,    # M1 bars = 1h
    "BTC_H1_M5_SCALP": 120,          # M1 bars = 2h
    "BTC_H4_M15_DAYTRADE": 96,       # M5 bars = 8h
    "BTC_D1_H1_DAYTRADE": 288,       # M5 bars = 24h
}


def sniff_sep(path: Path) -> str:
    sample = path.read_text(encoding="utf-8-sig", errors="replace")[:4096]
    try:
        return csv.Sniffer().sniff(sample, delimiters=";,\t,").delimiter
    except csv.Error:
        return ";" if sample.count(";") >= sample.count(",") else ","


def read_ohlc_csv(path: Path) -> pd.DataFrame:
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
    return TF_MINUTES[str(tf).upper()]


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


def mode_spread_points(df: pd.DataFrame) -> float:
    if "spread" not in df.columns:
        return float("nan")
    s = pd.to_numeric(df["spread"], errors="coerce").dropna()
    s = s[s > 0]
    if s.empty:
        return float("nan")
    return float(s.mode().iloc[0])


def choose_touch_tf(base_tf: str) -> str:
    return TOUCH_TF_BY_BASE_TF.get(str(base_tf).upper(), "M5")


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
) -> tuple[str, str, int, str, float, float]:
    entry_idx = lower_bound_index(touch["time"], entry_time)
    if entry_idx >= len(touch):
        return "NO_DATA", "", 0, "entry_after_data", float("nan"), float("nan")
    end_idx = min(len(touch), entry_idx + horizon_bars)
    future = touch.iloc[entry_idx:end_idx]
    if future.empty:
        return "NO_DATA", "", 0, "empty_future", float("nan"), float("nan")
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
                return "WIN", str(pd.Timestamp(time)), offset, "both_hit_tp_priority", max_fav, max_adv
            return "LOSS", str(pd.Timestamp(time)), offset, "both_hit_sl_priority", max_fav, max_adv
        if hit_tp:
            return "WIN", str(pd.Timestamp(time)), offset, "tp_first", max_fav, max_adv
        if hit_sl:
            return "LOSS", str(pd.Timestamp(time)), offset, "sl_first", max_fav, max_adv
    return "TIMEOUT", str(pd.Timestamp(future.iloc[-1]["time"])), len(future) - 1, "no_touch", max_fav, max_adv


def gross_net_r(outcome: str, rr: float, gross_risk: float, spread_price: float) -> tuple[float, float, float, float, float]:
    spread_to_sl = spread_price / gross_risk if gross_risk > 0 else float("nan")
    spread_to_tp = spread_price / (rr * gross_risk) if gross_risk > 0 and rr > 0 else float("nan")
    net_risk = gross_risk + spread_price
    net_reward = rr * gross_risk - spread_price
    effective_rr = net_reward / net_risk if net_risk > 0 else float("nan")
    if outcome == "WIN":
        return rr, effective_rr, spread_to_sl, spread_to_tp, effective_rr
    if outcome == "LOSS":
        return -1.0, -1.0, spread_to_sl, spread_to_tp, effective_rr
    return 0.0, 0.0, spread_to_sl, spread_to_tp, effective_rr


def max_drawdown_r(r_values: pd.Series) -> float:
    if r_values.empty:
        return 0.0
    eq = r_values.cumsum()
    peak = eq.cummax()
    return float((peak - eq).max())


def max_consecutive_losses(outcomes: pd.Series) -> int:
    cur = 0
    best = 0
    for x in outcomes.astype(str):
        if x == "LOSS":
            cur += 1
            best = max(best, cur)
        elif x == "WIN":
            cur = 0
    return best


def stats(df: pd.DataFrame, r_col: str) -> dict:
    wins = int((df["outcome"] == "WIN").sum())
    losses = int((df["outcome"] == "LOSS").sum())
    timeouts = int((df["outcome"] == "TIMEOUT").sum())
    no_data = int((df["outcome"] == "NO_DATA").sum())
    resolved = wins + losses
    gp = float(df.loc[df[r_col] > 0, r_col].sum())
    gl = float(-df.loc[df[r_col] < 0, r_col].sum())
    return {
        "trades": int(len(df)),
        "resolved": resolved,
        "wins": wins,
        "losses": losses,
        "timeouts": timeouts,
        "no_data": no_data,
        "win_rate": wins / resolved if resolved else None,
        "total_r": float(df[r_col].sum()),
        "avg_r": float(df[r_col].mean()) if len(df) else None,
        "pf": gp / gl if gl > 0 else None,
        "max_dd_r": max_drawdown_r(df[r_col]),
        "max_consecutive_losses": max_consecutive_losses(df["outcome"]),
    }


def grouped_stats(df: pd.DataFrame, keys: list[str], r_col: str) -> list[dict]:
    rows = []
    for key, g in df.groupby(keys, dropna=False, sort=True):
        if not isinstance(key, tuple):
            key = (key,)
        row = {k: v for k, v in zip(keys, key)}
        row.update(stats(g.sort_values("entry_time"), r_col))
        rows.append(row)
    return rows


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Backtest BTC Mochipoyo events with spread-aware first-touch logic.")
    p.add_argument("--events-csv", required=True)
    p.add_argument("--m1-csv", required=True)
    p.add_argument("--m5-csv", required=True)
    p.add_argument("--output-csv", required=True)
    p.add_argument("--summary-json", default=None)
    p.add_argument("--rr", type=float, default=1.2)
    p.add_argument("--point-size", type=float, default=0.01)
    p.add_argument("--pip-size", type=float, default=10.0)
    p.add_argument("--spread-points", type=float, default=0.0, help="Override spread points. If <=0, mode spread from M1/M5 is used.")
    p.add_argument("--min-stop-distance", type=float, default=50.0)
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
    m1_mode = mode_spread_points(touch_data["M1"])
    m5_mode = mode_spread_points(touch_data["M5"])
    if args.spread_points and args.spread_points > 0:
        spread_points = float(args.spread_points)
        spread_source = "override"
    elif math.isfinite(m1_mode):
        spread_points = m1_mode
        spread_source = "M1_mode"
    elif math.isfinite(m5_mode):
        spread_points = m5_mode
        spread_source = "M5_mode"
    else:
        spread_points = 0.0
        spread_source = "missing_spread_column_or_zero"
    spread_price = spread_points * args.point_size

    print("backtest_mochipoyo_btc_events_spread_first_touch")
    print(f"events: {len(events)}")
    print(f"M1 rows: {len(touch_data['M1'])} range={touch_data['M1']['time'].min()} -> {touch_data['M1']['time'].max()}")
    print(f"M5 rows: {len(touch_data['M5'])} range={touch_data['M5']['time'].min()} -> {touch_data['M5']['time'].max()}")
    print(f"spread_source: {spread_source}")
    print(f"mode_spread_points: {spread_points}")
    print(f"mode_spread_price: {spread_price}")

    rows = []
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
        sl_price, gross_risk, sl_method = swing_stop(touch, entry_idx, direction, entry_price, lookback, args.min_stop_distance, args.atr_mult_fallback)
        if not math.isfinite(gross_risk) or gross_risk <= 0:
            outcome, exit_time, bars_to_exit, exit_reason = "NO_DATA", "", 0, sl_method
            max_fav = max_adv = tp_price = float("nan")
            gross_r = net_r = spread_to_sl = spread_to_tp = effective_rr = float("nan")
        else:
            tp_price = entry_price + args.rr * gross_risk if direction == "BUY" else entry_price - args.rr * gross_risk
            outcome, exit_time, bars_to_exit, exit_reason, max_fav, max_adv = simulate_first_touch(
                touch, entry_time, direction, entry_price, sl_price, tp_price, horizon, args.inbar_priority
            )
            gross_r, net_r, spread_to_sl, spread_to_tp, effective_rr = gross_net_r(outcome, args.rr, gross_risk, spread_price)
        out = dict(row)
        out.update(
            {
                "touch_tf": touch_tf,
                "rr": args.rr,
                "spread_source": spread_source,
                "mode_spread_points": spread_points,
                "mode_spread_price": spread_price,
                "pip_size": args.pip_size,
                "sl_price": sl_price,
                "tp_price": tp_price,
                "gross_risk_distance_price": gross_risk,
                "sl_method": sl_method,
                "horizon_bars": horizon,
                "swing_lookback_bars": lookback,
                "outcome": outcome,
                "gross_r_result": gross_r,
                "net_r_after_spread": net_r,
                "exit_time": exit_time,
                "bars_to_exit": bars_to_exit,
                "exit_reason": exit_reason,
                "max_favorable_price_move": max_fav,
                "max_adverse_price_move": max_adv,
                "spread_to_sl_ratio": spread_to_sl,
                "spread_to_tp_ratio": spread_to_tp,
                "effective_rr_after_spread": effective_rr,
                "gross_tp_distance_price": args.rr * gross_risk if math.isfinite(gross_risk) else float("nan"),
                "gross_sl_distance_price": gross_risk,
                "net_tp_after_spread_price": args.rr * gross_risk - spread_price if math.isfinite(gross_risk) else float("nan"),
                "net_sl_after_spread_price": gross_risk + spread_price if math.isfinite(gross_risk) else float("nan"),
            }
        )
        rows.append(out)

    results = pd.DataFrame(rows)
    results["entry_month"] = pd.to_datetime(results["entry_time"]).dt.strftime("%Y-%m") if len(results) else ""
    output_csv = Path(args.output_csv)
    summary_json = Path(args.summary_json) if args.summary_json else output_csv.with_suffix(".summary.json")
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    summary_json.parent.mkdir(parents=True, exist_ok=True)
    results.to_csv(output_csv, index=False, encoding="utf-8-sig")

    gross = stats(results, "gross_r_result") if len(results) else {}
    net = stats(results, "net_r_after_spread") if len(results) else {}
    summary = {
        "input_events": int(len(results)),
        "output_csv": str(output_csv),
        "rr": args.rr,
        "inbar_priority": args.inbar_priority,
        "spread_source": spread_source,
        "mode_spread_points": spread_points,
        "mode_spread_price": spread_price,
        "pip_size": args.pip_size,
        "gross": gross,
        "net_after_spread": net,
        "avg_gross_tp_distance_price": float(results["gross_tp_distance_price"].mean()) if len(results) else None,
        "avg_gross_sl_distance_price": float(results["gross_sl_distance_price"].mean()) if len(results) else None,
        "avg_spread_price": spread_price,
        "avg_spread_to_sl_ratio": float(results["spread_to_sl_ratio"].replace([np.inf, -np.inf], np.nan).mean()) if len(results) else None,
        "avg_spread_to_tp_ratio": float(results["spread_to_tp_ratio"].replace([np.inf, -np.inf], np.nan).mean()) if len(results) else None,
        "avg_effective_rr_after_spread": float(results["effective_rr_after_spread"].replace([np.inf, -np.inf], np.nan).mean()) if len(results) else None,
        "net_by_pair": grouped_stats(results, ["pair_name"], "net_r_after_spread") if len(results) else [],
        "net_by_pair_rank_direction": grouped_stats(results, ["pair_name", "candidate_rank", "direction"], "net_r_after_spread") if len(results) else [],
        "net_by_month": grouped_stats(results, ["entry_month"], "net_r_after_spread") if len(results) else [],
    }
    summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"output_csv: {output_csv}")
    print(f"summary_json: {summary_json}")
    print("gross:")
    print(json.dumps(gross, ensure_ascii=False, indent=2))
    print("net_after_spread:")
    print(json.dumps(net, ensure_ascii=False, indent=2))
    print(f"avg_spread_to_sl_ratio: {summary['avg_spread_to_sl_ratio']}")
    print(f"avg_effective_rr_after_spread: {summary['avg_effective_rr_after_spread']}")
    print("done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
