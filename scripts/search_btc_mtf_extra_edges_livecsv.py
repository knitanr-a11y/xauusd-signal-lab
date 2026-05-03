from __future__ import annotations

from pathlib import Path

import pandas as pd

import search_btc_mtf_extra_edges as base


def read_ohlc_live_csv(path: Path) -> pd.DataFrame:
    """Read MQL5-exported OHLC CSV robustly.

    The improved MQL5 exporter writes time with seconds:
      2026.05.03 00:00:00

    Some older research CSV files used minute precision:
      2026.05.03 00:00

    This wrapper accepts both formats and then delegates the rest of the search logic
    to scripts/search_btc_mtf_extra_edges.py by monkey-patching its read_ohlc().
    """
    path = base.resolve_path(path)
    if not path.exists():
        raise FileNotFoundError(path)

    df = pd.read_csv(path).copy()
    required = ["time", "open", "high", "low", "close"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns in {path}: {missing}")

    time_text = df["time"].astype(str).str.strip()
    parsed = pd.to_datetime(time_text, format="%Y.%m.%d %H:%M:%S", errors="coerce")
    if parsed.isna().mean() > 0.5:
        parsed = pd.to_datetime(time_text, format="%Y.%m.%d %H:%M", errors="coerce")
    if parsed.isna().mean() > 0.5:
        parsed = pd.to_datetime(time_text, errors="coerce")

    df["time"] = parsed
    bad_rate = float(df["time"].isna().mean()) if len(df) else 1.0
    if bad_rate > 0.5:
        sample = time_text.head(5).tolist()
        raise ValueError(f"Could not parse time column in {path}. bad_rate={bad_rate:.2%}, sample={sample}")

    df = df.dropna(subset=["time"]).sort_values("time", kind="mergesort").reset_index(drop=True)
    for col in ["open", "high", "low", "close", "volume", "tick_volume", "spread", "real_volume"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    if "spread" not in df.columns:
        df["spread"] = 0.0
    return df


base.read_ohlc = read_ohlc_live_csv


if __name__ == "__main__":
    raise SystemExit(base.main())
