from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from build_latest_btc_mtf_signal_payload_from_csv import (
    DEFAULT_H1_CSV,
    DEFAULT_H4_CSV,
    DEFAULT_M15_CSV,
    DEFAULT_M5_CSV,
    add_entry_hour,
    detect_btc_scalp_m5_reentry_filtered,
    parse_int_set,
    resolve_path,
)
from build_latest_signal_payload_from_csv import PROJECT_ROOT
from search_btc_mtf_extra_edges import add_indicators, join_context
from search_btc_mtf_extra_edges_livecsv import read_ohlc_live_csv

DEFAULT_OUT_SUMMARY = PROJECT_ROOT / "data" / "results" / "btc_m5_standby_variant_summary.csv"
DEFAULT_OUT_EVENTS = PROJECT_ROOT / "data" / "results" / "btc_m5_standby_variant_events.csv"


def row_number(row: pd.Series, key: str) -> float:
    try:
        value = float(row.get(key, np.nan))
    except Exception:
        return float("nan")
    return value if np.isfinite(value) else float("nan")


def time_str(value: Any) -> str:
    if pd.isna(value):
        return ""
    return pd.Timestamp(value).strftime("%Y-%m-%d %H:%M:%S")


def load_m5_context(m5_csv: Path, m15_csv: Path, h1_csv: Path, h4_csv: Path) -> pd.DataFrame:
    m5 = add_indicators(read_ohlc_live_csv(m5_csv))
    m15 = add_indicators(read_ohlc_live_csv(m15_csv))
    h1 = add_indicators(read_ohlc_live_csv(h1_csv))
    h4 = add_indicators(read_ohlc_live_csv(h4_csv))
    m5_ctx = join_context(m5, [(m15, "m15"), (h1, "h1"), (h4, "h4")])
    return add_entry_hour(m5_ctx)


def condition_state(row: pd.Series, side: str) -> dict[str, bool]:
    side = side.upper()
    if side == "BUY":
        return {
            "direction_ok": row_number(row, "h1_ema20") > row_number(row, "h1_ema50") and (row_number(row, "h1_macd_hist") > 0 or row_number(row, "h1_macd_delta3") > 0),
            "m15_ok": row_number(row, "m15_close") >= row_number(row, "m15_ema20") - 0.25 * row_number(row, "m15_atr14") and row_number(row, "m15_macd_delta3") > -0.02,
            "not_extended": abs(row_number(row, "close_change_6_atr")) <= 1.60,
            "gap_ok": -0.20 <= row_number(row, "close_ema8_gap_atr") <= 0.70,
            "ema8_reclaim": row_number(row, "low") <= row_number(row, "ema8") + 0.30 * row_number(row, "atr14") and row_number(row, "close") > row_number(row, "ema8"),
            "macd_reaccel": row_number(row, "macd_delta") > 0 and row_number(row, "macd_delta3") > 0,
            "rci_turn": row_number(row, "rci9") <= 30 and row_number(row, "rci9_delta") > 0 and row_number(row, "rci26") >= -75,
            "rci_zone": row_number(row, "rci9") <= 30 and row_number(row, "rci26") >= -75,
            "rci_delta_turn": row_number(row, "rci9_delta") > 0,
            "macd_near": row_number(row, "macd_delta3") > -0.02,
            "ema8_near": abs(row_number(row, "close_ema8_gap_atr")) <= 0.20 or row_number(row, "low") <= row_number(row, "ema8") + 0.30 * row_number(row, "atr14"),
        }
    return {
        "direction_ok": row_number(row, "h1_ema20") < row_number(row, "h1_ema50") and (row_number(row, "h1_macd_hist") < 0 or row_number(row, "h1_macd_delta3") < 0),
        "m15_ok": row_number(row, "m15_close") <= row_number(row, "m15_ema20") + 0.25 * row_number(row, "m15_atr14") and row_number(row, "m15_macd_delta3") < 0.02,
        "not_extended": abs(row_number(row, "close_change_6_atr")) <= 1.60,
        "gap_ok": -0.70 <= row_number(row, "close_ema8_gap_atr") <= 0.20,
        "ema8_reclaim": row_number(row, "high") >= row_number(row, "ema8") - 0.30 * row_number(row, "atr14") and row_number(row, "close") < row_number(row, "ema8"),
        "macd_reaccel": row_number(row, "macd_delta") < 0 and row_number(row, "macd_delta3") < 0,
        "rci_turn": row_number(row, "rci9") >= -30 and row_number(row, "rci9_delta") < 0 and row_number(row, "rci26") <= 75,
        "rci_zone": row_number(row, "rci9") >= -30 and row_number(row, "rci26") <= 75,
        "rci_delta_turn": row_number(row, "rci9_delta") < 0,
        "macd_near": row_number(row, "macd_delta3") < 0.02,
        "ema8_near": abs(row_number(row, "close_ema8_gap_atr")) <= 0.20 or row_number(row, "high") >= row_number(row, "ema8") - 0.30 * row_number(row, "atr14"),
    }


def variant_hit(row: pd.Series, side: str, variant: str) -> tuple[bool, str]:
    s = condition_state(row, side)
    base_ok = s["direction_ok"] and s["m15_ok"] and s["not_extended"] and s["gap_ok"]
    if not base_ok:
        return False, "base_not_ok"

    if variant == "current_any_2_of_3":
        trigger = [s["ema8_reclaim"], s["macd_reaccel"], s["rci_turn"]]
        return sum(bool(x) for x in trigger) == 2, missing_desc(s)

    if variant == "wait_rci_delta_only":
        ok = s["ema8_reclaim"] and s["macd_reaccel"] and s["rci_zone"] and not s["rci_delta_turn"]
        return ok, "waiting_rci_delta_turn"

    if variant == "wait_macd_only":
        ok = s["ema8_reclaim"] and s["rci_turn"] and s["macd_near"] and not s["macd_reaccel"]
        return ok, "waiting_macd_reaccel"

    if variant == "wait_ema8_only":
        ok = s["macd_reaccel"] and s["rci_turn"] and s["ema8_near"] and not s["ema8_reclaim"]
        return ok, "waiting_ema8_reclaim"

    if variant == "strict_rci_zone_and_2_of_3":
        trigger = [s["ema8_reclaim"], s["macd_reaccel"], s["rci_delta_turn"]]
        ok = s["rci_zone"] and sum(bool(x) for x in trigger) == 2
        return ok, missing_desc(s)

    raise ValueError(f"Unknown variant: {variant}")


def missing_desc(s: dict[str, bool]) -> str:
    names = []
    if not s["ema8_reclaim"]:
        names.append("ema8_reclaim")
    if not s["macd_reaccel"]:
        names.append("macd_reaccel")
    if not s["rci_turn"]:
        if s.get("rci_zone") and not s.get("rci_delta_turn"):
            names.append("rci_delta_turn")
        elif not s.get("rci_zone") and s.get("rci_delta_turn"):
            names.append("rci_zone")
        else:
            names.append("rci_turn")
    return "+".join(names) if names else ""


def next_confirmed(df: pd.DataFrame, *, idx: int, side: str, lookahead: int, exclude_entry_hours: set[int]) -> tuple[int | None, dict[str, Any] | None]:
    end = min(len(df) - 1, idx + lookahead)
    for j in range(idx + 1, end + 1):
        signal = detect_btc_scalp_m5_reentry_filtered(df.iloc[j], exclude_entry_hours=exclude_entry_hours)
        if signal is not None and str(signal.get("side")) == side:
            return j, signal
    return None, None


def write_csv(path: Path, df: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig", quoting=csv.QUOTE_MINIMAL)


def main() -> int:
    parser = argparse.ArgumentParser(description="Search BTC M5 standby condition variants and conversion rates.")
    parser.add_argument("--m5-csv", type=Path, default=DEFAULT_M5_CSV)
    parser.add_argument("--m15-csv", type=Path, default=DEFAULT_M15_CSV)
    parser.add_argument("--h1-csv", type=Path, default=DEFAULT_H1_CSV)
    parser.add_argument("--h4-csv", type=Path, default=DEFAULT_H4_CSV)
    parser.add_argument("--scan-recent-bars", type=int, default=3000)
    parser.add_argument("--lookahead-bars", type=int, default=3)
    parser.add_argument("--bar-offset", type=int, default=1)
    parser.add_argument("--exclude-entry-hours", default="8,13,20,21")
    parser.add_argument("--out-summary", type=Path, default=DEFAULT_OUT_SUMMARY)
    parser.add_argument("--out-events", type=Path, default=DEFAULT_OUT_EVENTS)
    parser.add_argument("--last", type=int, default=40)
    args = parser.parse_args()

    m5_csv = resolve_path(args.m5_csv)
    m15_csv = resolve_path(args.m15_csv)
    h1_csv = resolve_path(args.h1_csv)
    h4_csv = resolve_path(args.h4_csv)
    out_summary = resolve_path(args.out_summary)
    out_events = resolve_path(args.out_events)
    exclude_entry_hours = parse_int_set(args.exclude_entry_hours)

    df = load_m5_context(m5_csv, m15_csv, h1_csv, h4_csv)
    end_idx = len(df) - 1 - args.bar_offset
    start_idx = max(300, end_idx - args.scan_recent_bars + 1)

    variants = [
        "current_any_2_of_3",
        "strict_rci_zone_and_2_of_3",
        "wait_rci_delta_only",
        "wait_macd_only",
        "wait_ema8_only",
    ]
    events: list[dict[str, Any]] = []
    confirmed_count = 0

    for idx in range(start_idx, end_idx + 1):
        row = df.iloc[idx]
        confirmed = detect_btc_scalp_m5_reentry_filtered(row, exclude_entry_hours=exclude_entry_hours)
        if confirmed is not None:
            confirmed_count += 1
            continue
        for side in ["BUY", "SELL"]:
            for variant in variants:
                hit, reason = variant_hit(row, side, variant)
                if not hit:
                    continue
                next_idx, next_signal = next_confirmed(df, idx=idx, side=side, lookahead=args.lookahead_bars, exclude_entry_hours=exclude_entry_hours)
                converted = next_idx is not None
                events.append(
                    {
                        "variant": variant,
                        "idx": int(idx),
                        "time": time_str(row.get("time")),
                        "entry_time_proxy": time_str(row.get("entry_time_proxy")),
                        "entry_hour": None if pd.isna(row.get("entry_hour")) else int(row.get("entry_hour")),
                        "side": side,
                        "reason": reason,
                        "converted_to_signal": bool(converted),
                        "signal_idx": int(next_idx) if next_idx is not None else "",
                        "signal_time": time_str(df.iloc[next_idx].get("time")) if next_idx is not None else "",
                        "bars_until_signal": int(next_idx - idx) if next_idx is not None else "",
                    }
                )

    events_df = pd.DataFrame(events)
    if not events_df.empty:
        summary = (
            events_df.groupby(["variant", "side"], dropna=False)
            .agg(
                standby_count=("variant", "size"),
                converted_count=("converted_to_signal", "sum"),
                conversion_rate=("converted_to_signal", "mean"),
            )
            .reset_index()
            .sort_values(["conversion_rate", "standby_count"], ascending=[False, False], kind="mergesort")
        )
        all_summary = (
            events_df.groupby(["variant"], dropna=False)
            .agg(
                standby_count=("variant", "size"),
                converted_count=("converted_to_signal", "sum"),
                conversion_rate=("converted_to_signal", "mean"),
            )
            .reset_index()
        )
        all_summary.insert(1, "side", "ALL")
        summary = pd.concat([all_summary, summary], ignore_index=True).sort_values(["conversion_rate", "standby_count"], ascending=[False, False], kind="mergesort")
    else:
        summary = pd.DataFrame(columns=["variant", "side", "standby_count", "converted_count", "conversion_rate"])

    write_csv(out_events, events_df)
    write_csv(out_summary, summary)

    print("Project root:", PROJECT_ROOT)
    print("Rows:", len(df))
    print("Scan range:", start_idx, "to", end_idx)
    print("Scan recent bars:", args.scan_recent_bars)
    print("Lookahead bars:", args.lookahead_bars)
    print("Exclude entry hours:", sorted(exclude_entry_hours))
    print("Confirmed signals in scan:", confirmed_count)
    print("Standby variant events:", len(events_df))
    print("Saved summary:", out_summary)
    print("Saved events:", out_events)

    print("\nVariant summary:")
    print(summary.to_string(index=False) if not summary.empty else "No events.")

    print(f"\nLast {args.last} events:")
    print(events_df.tail(args.last).to_string(index=False) if not events_df.empty else "No events.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
