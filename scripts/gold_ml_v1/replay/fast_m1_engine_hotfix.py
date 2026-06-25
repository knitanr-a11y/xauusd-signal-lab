from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


POINT = 0.01
NANOSECONDS_PER_MINUTE = 60_000_000_000


def evaluate_fast_m1_no_infinity(
    self: Any,
    decision: pd.Timestamp,
    atr: float,
    horizon_hours: int,
) -> dict[str, Any] | None:
    """Evaluate a LONG trade without converting infinity to an integer.

    Frozen behavior:
    - exact M1 entry is required;
    - dynamic spread is paid at entry;
    - same-M1 TP/SL collision is SL-first;
    - when neither TP nor SL is hit, exit at the last available M1 close
      strictly inside the wall-clock horizon.
    """
    if not np.isfinite(atr) or atr <= 0:
        return None

    decision = pd.Timestamp(decision)
    start = int(np.searchsorted(self.times, decision.value, side="left"))
    if start >= len(self.times) or int(self.times[start]) != decision.value:
        return None

    horizon_end = decision + pd.Timedelta(hours=horizon_hours)
    if horizon_end > self.latest_close:
        return None

    end = int(np.searchsorted(self.times, horizon_end.value, side="left"))
    if end <= start:
        return None

    entry = float(self.opens[start] + self.spreads[start] * POINT)
    sl = entry - atr
    tp = entry + atr

    sl_hits = np.flatnonzero(self.lows[start:end] <= sl)
    tp_hits = np.flatnonzero(self.highs[start:end] >= tp)

    has_sl = len(sl_hits) > 0
    has_tp = len(tp_hits) > 0

    if has_sl and (not has_tp or int(sl_hits[0]) <= int(tp_hits[0])):
        idx = start + int(sl_hits[0])
        return {
            "entry_time": decision,
            "entry_price": entry,
            "exit_time": pd.Timestamp(self.times[idx]),
            "exit_price": float(sl),
            "r_value": -1.0,
            "outcome": "SL",
        }

    if has_tp:
        idx = start + int(tp_hits[0])
        return {
            "entry_time": decision,
            "entry_price": entry,
            "exit_time": pd.Timestamp(self.times[idx]),
            "exit_price": float(tp),
            "r_value": 1.0,
            "outcome": "TP",
        }

    idx = end - 1
    exit_price = float(self.closes[idx])
    r_value = (exit_price - entry) / atr
    return {
        "entry_time": decision,
        "entry_price": entry,
        "exit_time": pd.Timestamp(self.times[idx] + NANOSECONDS_PER_MINUTE),
        "exit_price": exit_price,
        "r_value": float(r_value),
        "outcome": "TIME_POS" if r_value > 0 else ("TIME_NEG" if r_value < 0 else "TIME_ZERO"),
    }
