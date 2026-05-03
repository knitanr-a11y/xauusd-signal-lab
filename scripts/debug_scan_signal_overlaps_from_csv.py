from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path
from typing import Any

import pandas as pd

from build_latest_signal_payload_from_csv import (
    PROJECT_ROOT,
    add_indicators,
    detect_btc_runner,
    detect_gold_abc,
    detect_gold_extra,
    join_h1,
    read_ohlc,
    resolve_path,
)


def signal_to_item(signal: dict[str, Any]) -> dict[str, Any]:
    item: dict[str, Any] = {
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


def detect_signal_candidates(symbol: str, row: pd.Series) -> list[dict[str, Any]]:
    """Return all signal candidates for the selected bar.

    The normal payload builder chooses one final signal per bar using priority rules.
    This debug scanner intentionally keeps all candidates so overlapping conditions can be reviewed.
    """
    if symbol == "BTC":
        runner = detect_btc_runner(row)
        return [runner] if runner is not None else []

    candidates: list[dict[str, Any]] = []
    abc = detect_gold_abc(row)
    if abc is not None:
        candidates.append(abc)
    extra = detect_gold_extra(row)
    if extra is not None:
        candidates.append(extra)
    return candidates


def format_candidate(candidate: dict[str, Any]) -> str:
    abc = f" abc_source={candidate['abc_source']}" if candidate.get("abc_source") else ""
    return (
        f"{candidate.get('strategy_label')} "
        f"model={candidate.get('signal_model')} "
        f"rank={candidate.get('portfolio_rank')} "
        f"side={candidate.get('side')} "
        f"rr={candidate.get('rr')} risk_atr={candidate.get('risk_atr')}" + abc
    )


def format_bar(item: dict[str, Any]) -> str:
    overlap_flag = "OVERLAP" if item["candidate_count"] >= 2 else "single"
    labels = "+".join(str(x.get("strategy_label")) for x in item["candidates"])
    return f"idx={item['idx']} time={item['time']} {overlap_flag} count={item['candidate_count']} labels={labels}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Debug-print signal overlaps from M15/H1 CSV using live detector components.")
    parser.add_argument("--symbol", choices=["GOLD", "BTC"], required=True)
    parser.add_argument("--m15-csv", type=Path, required=True)
    parser.add_argument("--h1-csv", type=Path, required=True)
    parser.add_argument("--scan-recent-bars", type=int, default=3000)
    parser.add_argument("--bar-offset", type=int, default=1)
    parser.add_argument("--only-overlaps", action="store_true", help="Print only bars with 2 or more signal candidates.")
    parser.add_argument("--last", type=int, default=0, help="Print only last N matching bars. 0 means print all.")
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

    bars: list[dict[str, Any]] = []
    candidate_counts: Counter[str] = Counter()
    overlap_pair_counts: Counter[str] = Counter()

    for idx in range(start_idx, end_idx + 1):
        row = df.iloc[idx]
        candidates = detect_signal_candidates(args.symbol, row)
        if not candidates:
            continue
        candidate_items = [signal_to_item(x) for x in candidates]
        for candidate in candidate_items:
            candidate_counts[str(candidate.get("strategy_label"))] += 1
        if len(candidate_items) >= 2:
            pair_key = "+".join(str(x.get("strategy_label")) for x in candidate_items)
            overlap_pair_counts[pair_key] += 1
        bars.append(
            {
                "idx": int(idx),
                "time": row.get("time").strftime("%Y-%m-%d %H:%M:%S") if pd.notna(row.get("time")) else "",
                "candidate_count": len(candidate_items),
                "candidates": candidate_items,
            }
        )

    filtered = [x for x in bars if x["candidate_count"] >= 2] if args.only_overlaps else bars
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
    print("Bars with any signal candidate:", len(bars))
    print("Bars with overlaps:", sum(1 for x in bars if x["candidate_count"] >= 2))
    print("Printed bars:", len(filtered_to_print))

    print("\nCandidate label counts:")
    if candidate_counts:
        for label, count in sorted(candidate_counts.items()):
            print(f"  {label}: {count}")
    else:
        print("  No candidates.")

    print("\nOverlap pair counts:")
    if overlap_pair_counts:
        for pair, count in sorted(overlap_pair_counts.items()):
            print(f"  {pair}: {count}")
    else:
        print("  No overlaps.")

    print("\nBars:")
    if not filtered_to_print:
        print("  No matching bars.")
    for item in filtered_to_print:
        print("  " + format_bar(item))
        for candidate in item["candidates"]:
            print("    - " + format_candidate(candidate))

    if bars:
        print("\nLast bar with any candidate:")
        last_bar = bars[-1]
        print("  " + format_bar(last_bar))
        for candidate in last_bar["candidates"]:
            print("    - " + format_candidate(candidate))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
