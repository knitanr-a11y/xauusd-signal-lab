from __future__ import annotations

from pathlib import Path

import run_live_gold_notifier_from_csv as gold_live
from confirmed_time_join import join_h1_confirmed_for_gold_m15
from search_btc_mtf_extra_edges_livecsv import read_ohlc_live_csv


def load_gold_context_confirmed(m15_csv: Path, h1_csv: Path):
    """Load GOLD live context with no higher-timeframe lookahead.

    MQL5 CSV stores candle open time. H1 features are only usable after the H1 candle
    has closed. For each M15 row, this joins the latest H1 row whose
    h1_close_time <= m15_close_time.
    """
    m15 = gold_live.add_indicators(read_ohlc_live_csv(m15_csv))
    h1 = gold_live.add_indicators(read_ohlc_live_csv(h1_csv))
    return join_h1_confirmed_for_gold_m15(m15, h1)


def main() -> int:
    gold_live.load_gold_context = load_gold_context_confirmed
    print("Confirmed-time join: GOLD M15 uses only H1 candles closed by the M15 close time.")
    return gold_live.main()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nInterrupted by user. Exiting GOLD confirmed notifier.")
        raise SystemExit(130)
