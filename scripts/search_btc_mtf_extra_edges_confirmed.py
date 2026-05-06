from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

import search_btc_mtf_extra_edges as base
from confirmed_time_join import join_context_confirmed
from search_btc_mtf_extra_edges_livecsv import read_ohlc_live_csv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIRMED_SUMMARY = PROJECT_ROOT / "data" / "results" / "btc_mtf_extra_edge_summary_confirmed_join.csv"
DEFAULT_CONFIRMED_TRADES = PROJECT_ROOT / "data" / "results" / "btc_mtf_extra_edge_trades_confirmed_join.csv"


def infer_base_tf(df: pd.DataFrame) -> str:
    if df.empty or "time" not in df.columns or len(df) < 3:
        return "M15"
    diff_min = pd.to_datetime(df["time"], errors="coerce").sort_values().diff().dropna().dt.total_seconds().median() / 60.0
    if diff_min <= 7:
        return "M5"
    if diff_min <= 20:
        return "M15"
    if diff_min <= 80:
        return "H1"
    if diff_min <= 300:
        return "H4"
    return "M15"


def tf_from_prefix(prefix: str) -> str:
    key = str(prefix).lower()
    if key == "m5":
        return "M5"
    if key == "m15":
        return "M15"
    if key == "h1":
        return "H1"
    if key == "h4":
        return "H4"
    raise ValueError(f"Unsupported context prefix for confirmed join: {prefix}")


def confirmed_join_context_adapter(base_df: pd.DataFrame, contexts: list[tuple[pd.DataFrame, str]]) -> pd.DataFrame:
    base_tf = infer_base_tf(base_df)
    confirmed_contexts = [(ctx, prefix, tf_from_prefix(prefix)) for ctx, prefix in contexts]
    return join_context_confirmed(base_df, base_tf=base_tf, contexts=confirmed_contexts)


def ensure_default_confirmed_outputs() -> None:
    # Keep original backtest/scan outputs intact unless the caller explicitly overrides them.
    argv = sys.argv
    if "--out-summary" not in argv:
        argv.extend(["--out-summary", str(DEFAULT_CONFIRMED_SUMMARY)])
    if "--out-trades" not in argv:
        argv.extend(["--out-trades", str(DEFAULT_CONFIRMED_TRADES)])


def main() -> int:
    base.read_ohlc = read_ohlc_live_csv
    base.join_context = confirmed_join_context_adapter
    ensure_default_confirmed_outputs()
    print("Confirmed-time BTC MTF revalidation enabled.")
    print("MQL5 live CSV reader enabled: accepts YYYY.MM.DD HH:MM:SS time format.")
    print("Context features are joined only when context_close_time <= base_close_time.")
    print("Default output summary:", DEFAULT_CONFIRMED_SUMMARY)
    print("Default output trades :", DEFAULT_CONFIRMED_TRADES)
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())
