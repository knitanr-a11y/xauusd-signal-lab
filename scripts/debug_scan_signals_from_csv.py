from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path
from typing import Any

import pandas as pd

from build_latest_signal_payload_from_csv import (
    PROJECT_ROOT,
    add_indicators,
    detect_signal,
    join_h1,
    read_ohlc,
    resolve_path,
)


def signal_item(idx: int, row: pd.Series, signal: dict[str, Any]) -> dict[str, Any]:
    item: dict[str, Any] = {
        "idx": int(idx),
        "time": row.get("time").strftime("%Y-%m-%d %H:%M:%S") if pd.notna(row.get("time")) else "",
        "strategy_label": signal.get("strategy_label"),
        "signal_model": signal.get("signal_model"),
        "portfolio_rank": signal.get("portfolio_rank"),
        "side": signal.get("side"),
        "rr": signal.get("rr"),
        "risk_atr": signal.get("risk_atr"),
    }
    if signal.get("abc_source"):
        item["abc_source"] = signal.get("abc_source")
    return item


def format_item(item: dict[str, Any]) -> str:
    abc = f" abc_source={item['abc_source']}" if item.get("abc_source") else ""
    return (
        f"idx={item['idx']} time={item['time']} "
        f"label={item['strategy_label']} model={item['signal_model']} "
        f"rank={item['portfolio_rank']} side={item['side']} "
        f"rr={item['rr']} risk_atr={item['risk_atr']}" + abc
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Debug-print all detected signals from M15/H1 CSV using the live detector.")
    parser.add_argument("--symbol", choices=["GOLD", "BTC"], required=True)
    parser.add_argument("--m15-csv", type=Path, required=True)
    parser.add_argument("--h1-csv", type=Path, required=True)
    parser.add_argument("--scan-recent-bars", type=int, default=3000)
    parser.add_argument("--bar-offset", type=int, default=1)
    parser.add_argument("--filter-label", default=None, help="Only print matching strategy_label, e.g. GOLD_ABC_V3")
    parser.add_argument("--filter-rank", default=None, help="Only print matching portfolio_rank, e.g. GOLD_ABC")
    parser.add_argument("--last", type=int, default=0, help="Print only last N matching signals. 0 means print all.")
    args = parser.parse_args()

    m15_csv = resolve_path(args.m15_csv)
    h1_csv = resolve_path(args.h1_csv)

    m15 = add_indicators(read_ohlc(m15_csv))
    h1 = add_indicators(read_ohlc(h1_csv))
    df = join_h1(m15, h1)
    if len(df) < 250:
        raise ValueError("Not enough rows. Need at least about 250 M15 bars for indicators.")

    end_idx = len(df) - 1 - args.bar_offset
    if end_idx < 220:
        raise ValueError(f"Selected end_idx too early for indicators: end_idx={end_idx}")
    start_idx = max(220, end_idx - args.scan_recent_bars + 1)

    found: list[dict[str, Any]] = []
    for idx in range(start_idx, end_idx + 1):
        row = df.iloc[idx]
        signal = detect_signal(args.symbol, row)
        if signal is None:
            continue
        item = signal_item(idx, row, signal)
        found.append(item)

    label_counts = Counter(str(x.get("strategy_label")) for x in found)
    rank_counts = Counter(str(x.get("portfolio_rank")) for x in found)

    filtered = found
    if args.filter_label:
        filtered = [x for x in filtered if str(x.get("strategy_label")) == args.filter_label]
    if args.filter_rank:
        filtered = [x for x in filtered if str(x.get("portfolio_rank")) == args.filter_rank]
    if args.last and args.last > 0:
        filtered_to_print = filtered[-args.last:]
    else:
        filtered_to_print = filtered

    print("Project root:", PROJECT_ROOT)
    print("Symbol:", args.symbol)
    print("M15 CSV:", m15_csv)
    print("H1 CSV:", h1_csv)
    print("Rows:", len(df))
    print("Scan range:", start_idx, "to", end_idx)
    print("Scan recent bars:", args.scan_recent_bars)
    print("All signals found:", len(found))
    print("Filtered signals:", len(filtered))
    print("Strategy label counts:")
    for label, count in sorted(label_counts.items()):
        print(f"  {label}: {count}")
    print("Portfolio rank counts:")
    for rank, count in sorted(rank_counts.items()):
        print(f"  {rank}: {count}")

    print("\nSignals:")
    if not filtered_to_print:
        print("  No matching signals.")
    else:
        for item in filtered_to_print:
            print("  " + format_item(item))

    if found:
        print("\nLast signal:")
        print("  " + format_item(found[-1]))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
