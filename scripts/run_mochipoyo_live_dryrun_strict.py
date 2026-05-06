#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Strict dry-run live scanner for Mochipoyo GOLD/BTC fixed-preset candidates.

Compared with run_mochipoyo_live_dryrun.py, this version enforces the known
validated slice universe before applying fixed filters.

This prevents broad filter names such as total_score>=10.0 or base_score>=4.0
from matching unvalidated pairs/ranks during live dry-run.

For BTC, this strict scanner also enriches payload rows with live SL/TP and
spread-aware risk metrics:
- mode_spread_points / mode_spread_price
- sl_price / tp_price
- gross_sl_distance_price / gross_tp_distance_price
- spread_to_sl_ratio
- effective_rr_after_spread

No Discord send. No AI review. Ledger only.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# Reuse the already-tested helpers from the base dry-run script.
from run_mochipoyo_live_dryrun import (  # type: ignore
    DEFAULT_BTC_OUT_PREFIX,
    DEFAULT_BTC_PAIRS_JSON,
    DEFAULT_BTC_PRESET_JSON,
    DEFAULT_GOLD_OUT_PREFIX,
    DEFAULT_GOLD_PAIRS_JSON,
    DEFAULT_GOLD_PRESET_JSON,
    SymbolConfig,
    append_ledger,
    apply_fixed_preset,
    build_scan_cmd,
    ensure_selected_slice,
    load_preset,
    recent_filter,
    run_cmd,
    to_payload_rows,
)

DEFAULT_ALLOWED_SLICES = {
    "GOLD": [
        "GOLD_H4_M5_SCALP|B|SELL",
        "GOLD_H4_M15_DAYTRADE|B|SELL",
        "GOLD_D1_H1_DAYTRADE|B|BUY",
        "GOLD_D1_H1_DAYTRADE|A|BUY",
        "GOLD_H4_M5_SCALP|A|SELL",
        "GOLD_H4_M15_DAYTRADE|B|BUY",
    ],
    "BTC": [
        "BTC_H4_M15_DAYTRADE|A|BUY",
        "BTC_H4_M15_DAYTRADE|A|SELL",
    ],
}

TOUCH_TF_BY_BASE_TF = {
    "M1": "M1",
    "M5": "M1",
    "M15": "M5",
    "H1": "M5",
}

SWING_LOOKBACK_BY_PAIR = {
    "BTC_M15_M1_SUPER_SCALP": 60,
    "BTC_H1_M5_SCALP": 120,
    "BTC_H4_M15_DAYTRADE": 96,
    "BTC_D1_H1_DAYTRADE": 288,
}


def parse_allowed_slices(text: str | None, symbol: str) -> list[str]:
    if text is None or not str(text).strip():
        return list(DEFAULT_ALLOWED_SLICES[symbol])
    return [x.strip() for x in str(text).split(",") if x.strip()]


def apply_allowed_slices(events: pd.DataFrame, allowed_slices: list[str]) -> pd.DataFrame:
    work = ensure_selected_slice(events)
    if not allowed_slices:
        return work.iloc[0:0].copy()
    return work[work["selected_slice"].astype(str).isin(set(allowed_slices))].copy()


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


def choose_touch_tf(base_tf: str) -> str:
    return TOUCH_TF_BY_BASE_TF.get(str(base_tf).upper(), "M5")


def infer_btc_live_risk_for_row(
    row: pd.Series,
    touch_data: dict[str, pd.DataFrame],
    spread_points: float,
    point_size: float,
    rr: float,
    min_stop_distance: float,
) -> dict[str, object]:
    base_tf = str(row.get("base_tf", "M15")).upper()
    pair_name = str(row.get("pair_name", ""))
    direction = str(row.get("direction", "")).upper()
    entry_price = finite_float(row.get("entry_price"))
    entry_time = pd.to_datetime(row.get("entry_time"), errors="coerce")
    touch_tf = choose_touch_tf(base_tf)
    touch = touch_data.get(touch_tf)
    if touch is None or touch.empty or pd.isna(entry_time) or not math.isfinite(entry_price):
        return {"btc_live_risk_status": "NO_TOUCH_DATA_OR_ENTRY"}

    entry_idx = lower_bound_index(touch["time"], pd.Timestamp(entry_time))
    if entry_idx <= 0:
        return {"btc_live_risk_status": "NO_HISTORY"}

    lookback = SWING_LOOKBACK_BY_PAIR.get(pair_name, 96)
    start = max(0, entry_idx - lookback)
    hist = touch.iloc[start:entry_idx]
    if hist.empty:
        return {"btc_live_risk_status": "EMPTY_HISTORY"}

    if direction == "BUY":
        sl_price = float(hist["low"].min())
        gross_risk = entry_price - sl_price
    elif direction == "SELL":
        sl_price = float(hist["high"].max())
        gross_risk = sl_price - entry_price
    else:
        return {"btc_live_risk_status": "INVALID_DIRECTION"}

    sl_method = "swing"
    if not math.isfinite(gross_risk) or gross_risk <= 0:
        return {"btc_live_risk_status": "INVALID_SWING_RISK"}
    if gross_risk < min_stop_distance:
        gross_risk = min_stop_distance
        sl_price = entry_price - gross_risk if direction == "BUY" else entry_price + gross_risk
        sl_method = "min_stop_distance"

    tp_price = entry_price + rr * gross_risk if direction == "BUY" else entry_price - rr * gross_risk
    spread_price = spread_points * point_size if math.isfinite(spread_points) else float("nan")
    spread_to_sl = spread_price / gross_risk if math.isfinite(spread_price) and gross_risk > 0 else float("nan")
    spread_to_tp = spread_price / (rr * gross_risk) if math.isfinite(spread_price) and gross_risk > 0 and rr > 0 else float("nan")
    net_sl = gross_risk + spread_price if math.isfinite(spread_price) else float("nan")
    net_tp = rr * gross_risk - spread_price if math.isfinite(spread_price) else float("nan")
    effective_rr = net_tp / net_sl if math.isfinite(net_tp) and math.isfinite(net_sl) and net_sl > 0 else float("nan")

    return {
        "btc_live_risk_status": "OK",
        "touch_tf": touch_tf,
        "sl_method": sl_method,
        "rr": rr,
        "mode_spread_points": spread_points,
        "mode_spread_price": spread_price,
        "sl_price": sl_price,
        "tp_price": tp_price,
        "gross_sl_distance_price": gross_risk,
        "gross_tp_distance_price": rr * gross_risk,
        "net_sl_after_spread_price": net_sl,
        "net_tp_after_spread_price": net_tp,
        "spread_to_sl_ratio": spread_to_sl,
        "spread_to_tp_ratio": spread_to_tp,
        "effective_rr_after_spread": effective_rr,
    }


def enrich_btc_live_risk(df: pd.DataFrame, cfg: SymbolConfig, args: argparse.Namespace) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    if not cfg.m1_csv or not cfg.m5_csv:
        out = df.copy()
        out["btc_live_risk_status"] = "MISSING_M1_OR_M5_CSV"
        return out
    touch_data = {
        "M1": read_ohlc_csv(cfg.m1_csv, "M1"),
        "M5": read_ohlc_csv(cfg.m5_csv, "M5"),
    }
    if args.btc_spread_points > 0:
        spread_points = float(args.btc_spread_points)
    else:
        spread_points = mode_spread_points(touch_data["M1"])
        if not math.isfinite(spread_points):
            spread_points = mode_spread_points(touch_data["M5"])
    out = df.copy()
    metrics = [
        infer_btc_live_risk_for_row(
            row,
            touch_data,
            spread_points=spread_points,
            point_size=args.btc_point_size,
            rr=args.btc_rr,
            min_stop_distance=args.btc_min_stop_distance,
        )
        for _, row in out.iterrows()
    ]
    met = pd.DataFrame(metrics, index=out.index)
    for c in met.columns:
        out[c] = met[c]
    return out


def run_symbol_strict(cfg: SymbolConfig, args: argparse.Namespace, allowed_slices: list[str]) -> dict:
    out_prefix = Path(cfg.out_prefix)
    out_prefix.parent.mkdir(parents=True, exist_ok=True)
    candidates_csv = out_prefix.with_name(out_prefix.name + "_candidates.csv")
    events_csv = out_prefix.with_name(out_prefix.name + "_events.csv")
    allowed_events_csv = out_prefix.with_name(out_prefix.name + "_allowed_events.csv")
    fixed_csv = out_prefix.with_name(out_prefix.name + "_fixed_matches.csv")
    payload_csv = out_prefix.with_name(out_prefix.name + "_payloads.csv")

    run_cmd(build_scan_cmd(args.python, cfg, candidates_csv), dry_run_commands=args.print_commands_only)
    run_cmd(
        [args.python, "scripts/filter_mochipoyo_candidate_events.py", "--input-csv", str(candidates_csv), "--output-csv", str(events_csv)],
        dry_run_commands=args.print_commands_only,
    )
    if args.print_commands_only:
        return {"symbol": cfg.symbol, "printed_commands_only": True, "allowed_slices": allowed_slices}

    events = pd.read_csv(events_csv, encoding="utf-8-sig")
    if "entry_time" in events.columns:
        events["entry_time"] = pd.to_datetime(events["entry_time"], errors="coerce")
    events = ensure_selected_slice(events)

    allowed_events = apply_allowed_slices(events, allowed_slices)
    allowed_events.to_csv(allowed_events_csv, index=False, encoding="utf-8-sig")

    preset = load_preset(cfg.preset_json)
    fixed = apply_fixed_preset(allowed_events, preset)
    fixed.to_csv(fixed_csv, index=False, encoding="utf-8-sig")
    recent = recent_filter(fixed, args.scan_recent_events)
    if cfg.symbol == "BTC":
        recent = enrich_btc_live_risk(recent, cfg, args)
    payloads = to_payload_rows(recent, cfg, preset)
    payloads.to_csv(payload_csv, index=False, encoding="utf-8-sig")
    ledger_added, ledger_duplicate_existing, ledger_duplicate_within_batch = append_ledger(payloads, Path(args.ledger_csv))

    risk_ok = int((payloads.get("btc_live_risk_status", pd.Series(dtype=str)).astype(str) == "OK").sum()) if cfg.symbol == "BTC" and len(payloads) else None
    risk_bad = int(len(payloads) - risk_ok) if risk_ok is not None else None

    return {
        "symbol": cfg.symbol,
        "candidates_csv": str(candidates_csv),
        "events_csv": str(events_csv),
        "allowed_events_csv": str(allowed_events_csv),
        "fixed_csv": str(fixed_csv),
        "payload_csv": str(payload_csv),
        "allowed_slices": allowed_slices,
        "events_rows": int(len(events)),
        "allowed_events_rows": int(len(allowed_events)),
        "fixed_match_rows": int(len(fixed)),
        "payload_rows": int(len(payloads)),
        "btc_live_risk_ok_rows": risk_ok,
        "btc_live_risk_bad_rows": risk_bad,
        "ledger_added_rows": int(ledger_added),
        "ledger_duplicate_existing_rows": int(ledger_duplicate_existing),
        "ledger_duplicate_within_batch_rows": int(ledger_duplicate_within_batch),
    }


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run strict Mochipoyo live dry-run scanner with allowed slice gating.")
    p.add_argument("--symbols", default="GOLD,BTC", help="Comma-separated symbols: GOLD,BTC")
    p.add_argument("--ledger-csv", default="data/results/mochipoyo/live_dryrun/mochipoyo_live_dryrun_strict_ledger.csv")
    p.add_argument("--scan-recent-events", type=int, default=20)
    p.add_argument("--python", default=sys.executable)
    p.add_argument("--print-commands-only", action="store_true")
    p.add_argument("--gold-allowed-slices", default=None, help="Comma-separated override. Default uses validated GOLD slices.")
    p.add_argument("--btc-allowed-slices", default=None, help="Comma-separated override. Default uses BTC H4/M15 A BUY/SELL only.")
    p.add_argument("--btc-rr", type=float, default=1.2)
    p.add_argument("--btc-point-size", type=float, default=0.01)
    p.add_argument("--btc-spread-points", type=float, default=0.0, help="Override BTC spread points. If <=0, use M1 mode then M5 mode.")
    p.add_argument("--btc-min-stop-distance", type=float, default=50.0)

    p.add_argument("--gold-pairs-json", default=DEFAULT_GOLD_PAIRS_JSON)
    p.add_argument("--gold-preset-json", default=DEFAULT_GOLD_PRESET_JSON)
    p.add_argument("--gold-out-prefix", default=DEFAULT_GOLD_OUT_PREFIX.replace("gold_mochipoyo_live_dryrun", "gold_mochipoyo_live_dryrun_strict"))
    p.add_argument("--gold-m1-csv")
    p.add_argument("--gold-m5-csv")
    p.add_argument("--gold-m15-csv")
    p.add_argument("--gold-h1-csv")
    p.add_argument("--gold-h4-csv")
    p.add_argument("--gold-d1-csv")

    p.add_argument("--btc-pairs-json", default=DEFAULT_BTC_PAIRS_JSON)
    p.add_argument("--btc-preset-json", default=DEFAULT_BTC_PRESET_JSON)
    p.add_argument("--btc-out-prefix", default=DEFAULT_BTC_OUT_PREFIX.replace("btc_mochipoyo_live_dryrun", "btc_mochipoyo_live_dryrun_strict"))
    p.add_argument("--btc-m1-csv")
    p.add_argument("--btc-m5-csv")
    p.add_argument("--btc-m15-csv")
    p.add_argument("--btc-h1-csv")
    p.add_argument("--btc-h4-csv")
    p.add_argument("--btc-d1-csv")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    requested = {s.strip().upper() for s in args.symbols.split(",") if s.strip()}
    jobs: list[tuple[SymbolConfig, list[str]]] = []

    if "GOLD" in requested:
        jobs.append((
            SymbolConfig(
                "GOLD", args.gold_pairs_json, args.gold_preset_json, args.gold_out_prefix,
                args.gold_m1_csv, args.gold_m5_csv, args.gold_m15_csv, args.gold_h1_csv, args.gold_h4_csv, args.gold_d1_csv,
            ),
            parse_allowed_slices(args.gold_allowed_slices, "GOLD"),
        ))
    if "BTC" in requested:
        jobs.append((
            SymbolConfig(
                "BTC", args.btc_pairs_json, args.btc_preset_json, args.btc_out_prefix,
                args.btc_m1_csv, args.btc_m5_csv, args.btc_m15_csv, args.btc_h1_csv, args.btc_h4_csv, args.btc_d1_csv,
            ),
            parse_allowed_slices(args.btc_allowed_slices, "BTC"),
        ))
    if not jobs:
        raise RuntimeError("No valid symbols requested. Use --symbols GOLD,BTC")

    results = []
    for cfg, allowed in jobs:
        print("=" * 80)
        print(f"RUN STRICT SYMBOL: {cfg.symbol}")
        print("allowed_slices:")
        for s in allowed:
            print(f"  - {s}")
        results.append(run_symbol_strict(cfg, args, allowed))

    summary_path = Path(args.ledger_csv).with_suffix(".summary.json")
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary = {"mode": "STRICT_DRY_RUN_NO_DISCORD_NO_AI", "results": results, "ledger_csv": args.ledger_csv}
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print("=" * 80)
    print("run_mochipoyo_live_dryrun_strict")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"summary_json: {summary_path}")
    print("done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
