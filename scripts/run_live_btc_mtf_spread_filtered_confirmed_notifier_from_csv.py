from __future__ import annotations

from pathlib import Path

import pandas as pd

import run_live_btc_mtf_spread_filtered_notifier_from_csv as btc_live
from build_latest_btc_mtf_signal_payload_from_csv import build_m15_runner_df as _old_build_m15_runner_df
from build_latest_btc_mtf_signal_payload_from_csv import add_entry_hour
from confirmed_time_join import join_context_confirmed, join_h1_confirmed_for_btc_m15
from search_btc_mtf_extra_edges import add_indicators
from search_btc_mtf_extra_edges_livecsv import read_ohlc_live_csv


def load_contexts_confirmed(m5_csv: Path, m15_csv: Path, h1_csv: Path, h4_csv: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load BTC contexts with no higher-timeframe lookahead.

    MQL5 CSV stores candle open time. Context rows are joined by close time:
    - M5 row can use M15/H1/H4 only if their candle close time <= M5 close time.
    - M15 runner row can use H1 only if H1 close time <= M15 close time.
    """
    m5 = add_indicators(read_ohlc_live_csv(m5_csv))
    m15 = add_indicators(read_ohlc_live_csv(m15_csv))
    h1 = add_indicators(read_ohlc_live_csv(h1_csv))
    h4 = add_indicators(read_ohlc_live_csv(h4_csv))

    m5_ctx = join_context_confirmed(
        m5,
        base_tf="M5",
        contexts=[(m15, "m15", "M15"), (h1, "h1", "H1"), (h4, "h4", "H4")],
    )
    m5_ctx = add_entry_hour(m5_ctx)
    m15_runner_df = join_h1_confirmed_for_btc_m15(m15, h1)
    return m5_ctx, m15_runner_df


def main() -> int:
    btc_live.load_contexts = load_contexts_confirmed
    print("Confirmed-time join: BTC M5/M15 uses only context candles closed by the signal candle close time.")
    return btc_live.main()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nInterrupted by user. Exiting BTC confirmed spread-filtered notifier.")
        raise SystemExit(130)
