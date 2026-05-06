#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

TF_MINUTES = {"M1": 1, "M5": 5, "M15": 15, "M30": 30, "H1": 60, "H4": 240, "D1": 1440}


def tf_minutes(tf: str) -> int:
    tf = tf.upper()
    if tf not in TF_MINUTES:
        raise ValueError(f"unsupported timeframe: {tf}")
    return TF_MINUTES[tf]


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
        raise RuntimeError(f"missing columns in {path}: {missing}; columns={list(df.columns)}")
    df["time"] = pd.to_datetime(df["time"], errors="coerce")
    for c in ["open", "high", "low", "close", "tick_volume", "spread"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(subset=required).sort_values("time", kind="mergesort")
    df = df.drop_duplicates(subset=["time"], keep="last").reset_index(drop=True)
    return df


def ema(s: pd.Series, span: int) -> pd.Series:
    return s.ewm(span=span, adjust=False, min_periods=span).mean()


def add_context_ema(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["ema20"] = ema(out["close"], 20)
    out["ema30"] = ema(out["close"], 30)
    out["ema40"] = ema(out["close"], 40)
    bull = (out["ema20"] > out["ema30"]) & (out["ema30"] > out["ema40"])
    bear = (out["ema20"] < out["ema30"]) & (out["ema30"] < out["ema40"])
    out["ema_order"] = np.where(bull, "BULL", np.where(bear, "BEAR", "MIXED"))
    return out


def add_macd(df: pd.DataFrame, fast: int = 6, slow: int = 13, signal: int = 4) -> pd.DataFrame:
    out = df.copy()
    out["macd"] = ema(out["close"], fast) - ema(out["close"], slow)
    out["macd_signal"] = ema(out["macd"], signal)
    out["macd_hist"] = out["macd"] - out["macd_signal"]
    return out


def rci_series(close: pd.Series, period: int) -> pd.Series:
    arr = close.to_numpy(dtype=float)
    res = np.full(len(arr), np.nan)
    t_rank = np.arange(1, period + 1, dtype=float)
    denom = period * (period * period - 1)
    for i in range(period - 1, len(arr)):
        w = arr[i - period + 1 : i + 1]
        if np.isnan(w).any():
            continue
        p_rank = pd.Series(w).rank(method="average").to_numpy(dtype=float)
        d = t_rank - p_rank
        res[i] = (1.0 - 6.0 * np.sum(d * d) / denom) * 100.0
    return pd.Series(res, index=close.index)


def add_rci(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for p in (9, 14, 18):
        out[f"rci{p}"] = rci_series(out["close"], p)
    return out


def add_close_time(df: pd.DataFrame, tf: str, name: str) -> pd.DataFrame:
    out = df.copy()
    out[name] = pd.to_datetime(out["time"], errors="coerce") + pd.to_timedelta(tf_minutes(tf), unit="m")
    return out


def confirmed_join(base: pd.DataFrame, context: pd.DataFrame, base_tf: str, context_tf: str) -> pd.DataFrame:
    b = add_close_time(base, base_tf, "base_close_time").sort_values("base_close_time")
    c = add_close_time(context, context_tf, "context_close_time").sort_values("context_close_time")
    c = c[["time", "context_close_time", "ema20", "ema30", "ema40", "ema_order"]].rename(columns={"time": "context_time"})
    out = pd.merge_asof(b, c, left_on="base_close_time", right_on="context_close_time", direction="backward")
    return out.sort_values("time", kind="mergesort").reset_index(drop=True)


def raw_pivots(df: pd.DataFrame, depth: int) -> pd.DataFrame:
    highs = df["high"].to_numpy(dtype=float)
    lows = df["low"].to_numpy(dtype=float)
    rows = []
    for i in range(depth, len(df) - depth):
        if highs[i] == np.nanmax(highs[i - depth : i + depth + 1]):
            rows.append({"idx": i, "kind": "HIGH", "price": highs[i]})
        if lows[i] == np.nanmin(lows[i - depth : i + depth + 1]):
            rows.append({"idx": i, "kind": "LOW", "price": lows[i]})
    return pd.DataFrame(rows)


def deviation_threshold(price: float, deviation: float, mode: str, point_size: float) -> float:
    if mode == "price":
        return deviation
    if mode == "percent":
        return abs(price) * deviation / 100.0
    if mode == "points":
        return deviation * point_size
    raise ValueError(mode)


def zigzag_pivots(df: pd.DataFrame, depth: int, deviation: float, mode: str, point_size: float, backstep: int) -> pd.DataFrame:
    rp = raw_pivots(df, depth)
    if rp.empty:
        return rp
    rp = rp.sort_values(["idx", "kind"], kind="mergesort").reset_index(drop=True)
    kept = []
    for r in rp.to_dict("records"):
        if not kept:
            kept.append(r)
            continue
        last = kept[-1]
        gap = int(r["idx"]) - int(last["idx"])
        if r["kind"] == last["kind"]:
            if r["kind"] == "HIGH" and float(r["price"]) > float(last["price"]):
                kept[-1] = r
            elif r["kind"] == "LOW" and float(r["price"]) < float(last["price"]):
                kept[-1] = r
            continue
        if gap < backstep:
            continue
        move = abs(float(r["price"]) - float(last["price"]))
        if move >= deviation_threshold(float(last["price"]), deviation, mode, point_size):
            kept.append(r)
    out = pd.DataFrame(kept).sort_values("idx", kind="mergesort").reset_index(drop=True)
    out["confirm_idx"] = out["idx"].astype(int) + depth
    out = out[out["confirm_idx"] < len(df)].reset_index(drop=True)
    return out


def fnum(v) -> float:
    try:
        x = float(v)
    except Exception:
        return float("nan")
    return x if math.isfinite(x) else float("nan")


def rci_count(row: pd.Series, direction: str, upper: float, lower: float) -> int:
    vals = [fnum(row.get("rci9")), fnum(row.get("rci14")), fnum(row.get("rci18"))]
    if direction == "BUY":
        return sum(v <= lower for v in vals if math.isfinite(v))
    return sum(v >= upper for v in vals if math.isfinite(v))


def div_kinds(prev_price: float, price: float, prev_macd: float, macd: float, kind: str) -> list[str]:
    if not all(math.isfinite(x) for x in [prev_price, price, prev_macd, macd]):
        return []
    out = []
    if kind == "LOW":
        if price < prev_price and macd > prev_macd:
            out.append("regular_bullish")
        if price > prev_price and macd < prev_macd:
            out.append("hidden_bullish")
    else:
        if price > prev_price and macd < prev_macd:
            out.append("regular_bearish")
        if price < prev_price and macd > prev_macd:
            out.append("hidden_bearish")
    return out


def scan(args) -> pd.DataFrame:
    base = add_rci(add_macd(read_ohlc_csv(Path(args.base_csv))))
    context = add_context_ema(read_ohlc_csv(Path(args.context_csv)))
    joined = confirmed_join(base, context, args.base_tf, args.context_tf)
    piv = zigzag_pivots(joined, args.zigzag_depth, args.zigzag_deviation, args.zigzag_deviation_mode, args.point_size, args.zigzag_backstep)

    rows = []
    prev_by_kind = {}
    for p in piv.to_dict("records"):
        kind = p["kind"]
        prev = prev_by_kind.get(kind)
        prev_by_kind[kind] = p
        if prev is None:
            continue

        pidx = int(p["idx"])
        previdx = int(prev["idx"])
        cidx = int(p["confirm_idx"])
        prow = joined.iloc[pidx]
        prevrow = joined.iloc[previdx]
        sig = joined.iloc[cidx]

        direction = "BUY" if kind == "LOW" else "SELL"
        want_order = "BULL" if direction == "BUY" else "BEAR"
        if str(sig.get("ema_order")) != want_order:
            continue
        zone_count = rci_count(sig, direction, args.rci_upper, args.rci_lower)
        if zone_count < args.rci_min_count:
            continue

        kinds = div_kinds(float(prev["price"]), float(p["price"]), fnum(prevrow.get("macd")), fnum(prow.get("macd")), kind)
        for setup in kinds:
            if args.regular_only and not setup.startswith("regular"):
                continue
            if args.hidden_only and not setup.startswith("hidden"):
                continue
            rows.append({
                "symbol": args.symbol,
                "context_tf": args.context_tf,
                "base_tf": args.base_tf,
                "signal_time": sig["time"],
                "signal_close_time": sig["base_close_time"],
                "direction": direction,
                "setup_type": setup,
                "pivot_kind": kind,
                "prev_pivot_time": prevrow["time"],
                "pivot_time": prow["time"],
                "pivot_confirmed_at": sig["time"],
                "prev_pivot_price": float(prev["price"]),
                "pivot_price": float(p["price"]),
                "prev_pivot_macd": fnum(prevrow.get("macd")),
                "pivot_macd": fnum(prow.get("macd")),
                "signal_macd": fnum(sig.get("macd")),
                "signal_macd_signal": fnum(sig.get("macd_signal")),
                "signal_macd_hist": fnum(sig.get("macd_hist")),
                "rci9": fnum(sig.get("rci9")),
                "rci14": fnum(sig.get("rci14")),
                "rci18": fnum(sig.get("rci18")),
                "rci_zone_count": zone_count,
                "context_time": sig.get("context_time"),
                "context_close_time": sig.get("context_close_time"),
                "context_ema20": fnum(sig.get("ema20")),
                "context_ema30": fnum(sig.get("ema30")),
                "context_ema40": fnum(sig.get("ema40")),
                "context_ema_order": sig.get("ema_order"),
                "base_open": fnum(sig.get("open")),
                "base_high": fnum(sig.get("high")),
                "base_low": fnum(sig.get("low")),
                "base_close": fnum(sig.get("close")),
                "zigzag_depth": args.zigzag_depth,
                "zigzag_deviation": args.zigzag_deviation,
                "zigzag_deviation_mode": args.zigzag_deviation_mode,
                "zigzag_backstep": args.zigzag_backstep,
            })
    return pd.DataFrame(rows)


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--base-csv", required=True)
    p.add_argument("--context-csv", required=True)
    p.add_argument("--base-tf", required=True, choices=sorted(TF_MINUTES))
    p.add_argument("--context-tf", required=True, choices=sorted(TF_MINUTES))
    p.add_argument("--symbol", default="UNKNOWN")
    p.add_argument("--output-csv", required=True)
    p.add_argument("--summary-json", default=None)
    p.add_argument("--zigzag-depth", type=int, default=5)
    p.add_argument("--zigzag-deviation", type=float, default=3.0)
    p.add_argument("--zigzag-deviation-mode", choices=["price", "percent", "points"], default="price")
    p.add_argument("--zigzag-backstep", type=int, default=2)
    p.add_argument("--point-size", type=float, default=0.01)
    p.add_argument("--rci-upper", type=float, default=80.0)
    p.add_argument("--rci-lower", type=float, default=-80.0)
    p.add_argument("--rci-min-count", type=int, default=2)
    p.add_argument("--regular-only", action="store_true")
    p.add_argument("--hidden-only", action="store_true")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    if args.regular_only and args.hidden_only:
        raise SystemExit("--regular-only and --hidden-only cannot be used together")
    out = scan(args)
    out_path = Path(args.output_csv)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(out_path, index=False, encoding="utf-8-sig")
    summary_path = Path(args.summary_json) if args.summary_json else out_path.with_suffix(".summary.json")
    summary = {"signals": int(len(out)), "output_csv": str(out_path)}
    if len(out):
        summary["by_direction"] = out["direction"].value_counts().to_dict()
        summary["by_setup_type"] = out["setup_type"].value_counts().to_dict()
        summary["first_signal_time"] = str(out["signal_time"].min())
        summary["last_signal_time"] = str(out["signal_time"].max())
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print("scan_mochipoyo_divergence_candidates")
    print("confirmed_time_join: context_close_time <= base_close_time")
    print(f"signals: {len(out)}")
    print(f"output_csv: {out_path}")
    print(f"summary_json: {summary_path}")
    if len(out):
        print("by_direction:")
        print(out["direction"].value_counts().to_string())
        print("by_setup_type:")
        print(out["setup_type"].value_counts().to_string())
    print("done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
