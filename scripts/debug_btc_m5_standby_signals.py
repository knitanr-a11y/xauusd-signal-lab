from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Any

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
from run_live_btc_mtf_notifier_from_csv import detect_btc_scalp_m5_reentry_standby
from search_btc_mtf_extra_edges import add_indicators, join_context
from search_btc_mtf_extra_edges_livecsv import read_ohlc_live_csv

DEFAULT_OUT_CSV = PROJECT_ROOT / "data" / "results" / "btc_m5_standby_debug.csv"


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


def find_next_confirmed_signal(
    df: pd.DataFrame,
    *,
    start_idx: int,
    side: str,
    lookahead_bars: int,
    exclude_entry_hours: set[int],
) -> tuple[int | None, dict[str, Any] | None]:
    end_idx = min(len(df) - 1, start_idx + lookahead_bars)
    for idx in range(start_idx + 1, end_idx + 1):
        signal = detect_btc_scalp_m5_reentry_filtered(df.iloc[idx], exclude_entry_hours=exclude_entry_hours)
        if signal is not None and str(signal.get("side")) == side:
            return idx, signal
    return None, None


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        pd.DataFrame().to_csv(path, index=False, encoding="utf-8-sig")
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def summarize(rows: list[dict[str, Any]]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    total = len(df)
    converted = int(df["converted_to_signal"].sum())
    by_side = []
    for side, g in df.groupby("side"):
        by_side.append(
            {
                "side": side,
                "standby_count": len(g),
                "converted_count": int(g["converted_to_signal"].sum()),
                "conversion_rate": float(g["converted_to_signal"].mean()),
            }
        )
    summary_rows = [
        {
            "side": "ALL",
            "standby_count": total,
            "converted_count": converted,
            "conversion_rate": float(converted / total) if total else 0.0,
        }
    ] + by_side
    return pd.DataFrame(summary_rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="Debug BTC M5 standby notifications and conversion to confirmed signals.")
    parser.add_argument("--m5-csv", type=Path, default=DEFAULT_M5_CSV)
    parser.add_argument("--m15-csv", type=Path, default=DEFAULT_M15_CSV)
    parser.add_argument("--h1-csv", type=Path, default=DEFAULT_H1_CSV)
    parser.add_argument("--h4-csv", type=Path, default=DEFAULT_H4_CSV)
    parser.add_argument("--scan-recent-bars", type=int, default=3000)
    parser.add_argument("--lookahead-bars", type=int, default=3)
    parser.add_argument("--bar-offset", type=int, default=1)
    parser.add_argument("--exclude-entry-hours", default="8,13,20,21")
    parser.add_argument("--out-csv", type=Path, default=DEFAULT_OUT_CSV)
    parser.add_argument("--last", type=int, default=30)
    args = parser.parse_args()

    m5_csv = resolve_path(args.m5_csv)
    m15_csv = resolve_path(args.m15_csv)
    h1_csv = resolve_path(args.h1_csv)
    h4_csv = resolve_path(args.h4_csv)
    out_csv = resolve_path(args.out_csv)
    exclude_entry_hours = parse_int_set(args.exclude_entry_hours)

    df = load_m5_context(m5_csv, m15_csv, h1_csv, h4_csv)
    end_idx = len(df) - 1 - args.bar_offset
    start_idx = max(300, end_idx - args.scan_recent_bars + 1)

    rows: list[dict[str, Any]] = []
    confirmed_count = 0
    for idx in range(start_idx, end_idx + 1):
        row = df.iloc[idx]
        confirmed = detect_btc_scalp_m5_reentry_filtered(row, exclude_entry_hours=exclude_entry_hours)
        if confirmed is not None:
            confirmed_count += 1
            continue
        standby = detect_btc_scalp_m5_reentry_standby(row, exclude_entry_hours=exclude_entry_hours)
        if standby is None:
            continue
        side = str(standby.get("side"))
        next_idx, next_signal = find_next_confirmed_signal(
            df,
            start_idx=idx,
            side=side,
            lookahead_bars=args.lookahead_bars,
            exclude_entry_hours=exclude_entry_hours,
        )
        converted = next_idx is not None
        rows.append(
            {
                "idx": int(idx),
                "time": time_str(row.get("time")),
                "entry_time_proxy": time_str(row.get("entry_time_proxy")),
                "entry_hour": None if pd.isna(row.get("entry_hour")) else int(row.get("entry_hour")),
                "side": side,
                "standby_met_conditions": " / ".join(standby.get("standby_met_conditions", [])),
                "standby_missing_conditions": " / ".join(standby.get("standby_missing_conditions", [])),
                "converted_to_signal": bool(converted),
                "signal_idx": int(next_idx) if next_idx is not None else "",
                "signal_time": time_str(df.iloc[next_idx].get("time")) if next_idx is not None else "",
                "bars_until_signal": int(next_idx - idx) if next_idx is not None else "",
                "signal_strategy_label": next_signal.get("strategy_label") if next_signal is not None else "",
            }
        )

    write_csv(out_csv, rows)
    summary = summarize(rows)

    print("Project root:", PROJECT_ROOT)
    print("M5 CSV:", m5_csv)
    print("M15 CSV:", m15_csv)
    print("H1 CSV:", h1_csv)
    print("H4 CSV:", h4_csv)
    print("Rows:", len(df))
    print("Scan range:", start_idx, "to", end_idx)
    print("Scan recent bars:", args.scan_recent_bars)
    print("Lookahead bars:", args.lookahead_bars)
    print("Exclude entry hours:", sorted(exclude_entry_hours))
    print("Confirmed signals in scan:", confirmed_count)
    print("Standby signals in scan:", len(rows))
    print("Saved CSV:", out_csv)

    print("\nSummary:")
    print(summary.to_string(index=False) if not summary.empty else "No standby signals.")

    print(f"\nLast {args.last} standby rows:")
    if rows:
        display = pd.DataFrame(rows).tail(args.last)
        print(display.to_string(index=False))
    else:
        print("No standby signals.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
