from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

DEFAULT_CASES_CSV = PROJECT_ROOT / "data" / "results" / "ai_cases" / "xm_kiwami_gold_abc_v3_balanced_ai_cases.csv"
DEFAULT_M15_CSV = PROJECT_ROOT / "data" / "raw" / "xm_kiwami" / "goldsharp_m15.csv"
DEFAULT_H1_CSV = PROJECT_ROOT / "data" / "raw" / "xm_kiwami" / "goldsharp_h1.csv"
DEFAULT_OUT_CSV = PROJECT_ROOT / "data" / "results" / "ai_cases" / "xm_kiwami_gold_abc_v3_balanced_ai_cases_enriched.csv"
DEFAULT_README = PROJECT_ROOT / "data" / "results" / "ai_cases" / "xm_kiwami_gold_abc_v3_feature_notes.md"

MACD_FAST = 6
MACD_SLOW = 13
MACD_SIGNAL = 4


def read_ohlc(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)

    df = pd.read_csv(path)
    required = ["time", "open", "high", "low", "close"]
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"Missing columns in {path}: {missing}")

    df = df.copy()
    df["time"] = pd.to_datetime(df["time"], errors="coerce")
    df = df.dropna(subset=["time"]).sort_values("time", kind="mergesort").reset_index(drop=True)
    for col in ["open", "high", "low", "close", "volume", "spread"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def add_indicators(df: pd.DataFrame, prefix: str) -> pd.DataFrame:
    out = df.copy()

    close = out["close"]
    high = out["high"]
    low = out["low"]
    open_ = out["open"]

    out[f"{prefix}_ema20"] = close.ewm(span=20, adjust=False).mean()
    out[f"{prefix}_ema50"] = close.ewm(span=50, adjust=False).mean()
    out[f"{prefix}_ema200"] = close.ewm(span=200, adjust=False).mean()

    prev_close = close.shift(1)
    tr = pd.concat(
        [
            (high - low).abs(),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    out[f"{prefix}_atr14"] = tr.rolling(14, min_periods=1).mean()

    ema_fast = close.ewm(span=MACD_FAST, adjust=False).mean()
    ema_slow = close.ewm(span=MACD_SLOW, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    macd_signal = macd_line.ewm(span=MACD_SIGNAL, adjust=False).mean()
    macd_hist = macd_line - macd_signal

    out[f"{prefix}_macd_line"] = macd_line
    out[f"{prefix}_macd_signal"] = macd_signal
    out[f"{prefix}_macd_hist"] = macd_hist
    out[f"{prefix}_macd_hist_delta"] = macd_hist.diff()
    out[f"{prefix}_macd_hist_delta_abs"] = out[f"{prefix}_macd_hist_delta"].abs()

    body = (close - open_).abs()
    candle_range = (high - low).replace(0, pd.NA)
    upper_wick = high - pd.concat([open_, close], axis=1).max(axis=1)
    lower_wick = pd.concat([open_, close], axis=1).min(axis=1) - low

    out[f"{prefix}_candle_range"] = high - low
    out[f"{prefix}_body"] = body
    out[f"{prefix}_body_ratio"] = body / candle_range
    out[f"{prefix}_upper_wick"] = upper_wick
    out[f"{prefix}_lower_wick"] = lower_wick
    out[f"{prefix}_upper_wick_ratio"] = upper_wick / candle_range
    out[f"{prefix}_lower_wick_ratio"] = lower_wick / candle_range

    out[f"{prefix}_close_ema20_gap_atr"] = (close - out[f"{prefix}_ema20"]) / out[f"{prefix}_atr14"].replace(0, pd.NA)
    out[f"{prefix}_ema20_ema50_gap_atr"] = (out[f"{prefix}_ema20"] - out[f"{prefix}_ema50"]) / out[f"{prefix}_atr14"].replace(0, pd.NA)
    out[f"{prefix}_ema50_ema200_gap_atr"] = (out[f"{prefix}_ema50"] - out[f"{prefix}_ema200"]) / out[f"{prefix}_atr14"].replace(0, pd.NA)

    out[f"{prefix}_ema_alignment"] = "mixed"
    bullish = (out[f"{prefix}_ema20"] > out[f"{prefix}_ema50"]) & (out[f"{prefix}_ema50"] > out[f"{prefix}_ema200"])
    bearish = (out[f"{prefix}_ema20"] < out[f"{prefix}_ema50"]) & (out[f"{prefix}_ema50"] < out[f"{prefix}_ema200"])
    out.loc[bullish, f"{prefix}_ema_alignment"] = "bullish"
    out.loc[bearish, f"{prefix}_ema_alignment"] = "bearish"

    out[f"{prefix}_close_position_20"] = (close - low.rolling(20, min_periods=1).min()) / (
        high.rolling(20, min_periods=1).max() - low.rolling(20, min_periods=1).min()
    ).replace(0, pd.NA)

    out[f"{prefix}_range20_atr"] = (high.rolling(20, min_periods=1).max() - low.rolling(20, min_periods=1).min()) / out[
        f"{prefix}_atr14"
    ].replace(0, pd.NA)

    return out


def prepare_feature_frame(m15_path: Path, h1_path: Path) -> pd.DataFrame:
    m15 = add_indicators(read_ohlc(m15_path), "m15")
    h1 = add_indicators(read_ohlc(h1_path), "h1")

    h1_cols = [
        "time",
        "h1_open",
        "h1_high",
        "h1_low",
        "h1_close",
        "h1_spread",
        "h1_ema20",
        "h1_ema50",
        "h1_ema200",
        "h1_atr14",
        "h1_macd_line",
        "h1_macd_signal",
        "h1_macd_hist",
        "h1_macd_hist_delta",
        "h1_ema_alignment",
        "h1_close_ema20_gap_atr",
        "h1_ema20_ema50_gap_atr",
        "h1_ema50_ema200_gap_atr",
        "h1_close_position_20",
        "h1_range20_atr",
    ]

    h1 = h1.rename(columns={"open": "h1_open", "high": "h1_high", "low": "h1_low", "close": "h1_close", "spread": "h1_spread"})
    h1_subset = h1[[col for col in h1_cols if col in h1.columns]].copy()
    h1_subset = h1_subset.rename(columns={"time": "h1_feature_time"})

    m15 = m15.rename(
        columns={
            "open": "m15_open",
            "high": "m15_high",
            "low": "m15_low",
            "close": "m15_close",
            "spread": "m15_spread",
            "volume": "m15_volume",
        }
    )
    m15["m15_feature_time"] = m15["time"]

    merged = pd.merge_asof(
        m15.sort_values("time"),
        h1_subset.sort_values("h1_feature_time"),
        left_on="time",
        right_on="h1_feature_time",
        direction="backward",
    )
    return merged.sort_values("time", kind="mergesort").reset_index(drop=True)


def add_signal_derived_features(cases: pd.DataFrame) -> pd.DataFrame:
    out = cases.copy()
    out["entry_risk_atr_ratio"] = out["risk"] / out["m15_atr14"].replace(0, pd.NA)
    out["entry_spread_atr_ratio"] = out["m15_spread"] / out["m15_atr14"].replace(0, pd.NA)

    out["side_matches_h1_ema"] = "unknown"
    out.loc[(out["side"] == "BUY") & (out["h1_ema_alignment"] == "bullish"), "side_matches_h1_ema"] = "yes"
    out.loc[(out["side"] == "SELL") & (out["h1_ema_alignment"] == "bearish"), "side_matches_h1_ema"] = "yes"
    out.loc[(out["side"] == "BUY") & (out["h1_ema_alignment"] == "bearish"), "side_matches_h1_ema"] = "no"
    out.loc[(out["side"] == "SELL") & (out["h1_ema_alignment"] == "bullish"), "side_matches_h1_ema"] = "no"

    out["side_matches_m15_ema"] = "unknown"
    out.loc[(out["side"] == "BUY") & (out["m15_ema_alignment"] == "bullish"), "side_matches_m15_ema"] = "yes"
    out.loc[(out["side"] == "SELL") & (out["m15_ema_alignment"] == "bearish"), "side_matches_m15_ema"] = "yes"
    out.loc[(out["side"] == "BUY") & (out["m15_ema_alignment"] == "bearish"), "side_matches_m15_ema"] = "no"
    out.loc[(out["side"] == "SELL") & (out["m15_ema_alignment"] == "bullish"), "side_matches_m15_ema"] = "no"

    out["macd_hist_supports_side"] = "unknown"
    out.loc[(out["side"] == "BUY") & (out["m15_macd_hist"] > 0), "macd_hist_supports_side"] = "yes"
    out.loc[(out["side"] == "SELL") & (out["m15_macd_hist"] < 0), "macd_hist_supports_side"] = "yes"
    out.loc[(out["side"] == "BUY") & (out["m15_macd_hist"] < 0), "macd_hist_supports_side"] = "no"
    out.loc[(out["side"] == "SELL") & (out["m15_macd_hist"] > 0), "macd_hist_supports_side"] = "no"

    out["macd_hist_delta_supports_side"] = "unknown"
    out.loc[(out["side"] == "BUY") & (out["m15_macd_hist_delta"] > 0), "macd_hist_delta_supports_side"] = "yes"
    out.loc[(out["side"] == "SELL") & (out["m15_macd_hist_delta"] < 0), "macd_hist_delta_supports_side"] = "yes"
    out.loc[(out["side"] == "BUY") & (out["m15_macd_hist_delta"] < 0), "macd_hist_delta_supports_side"] = "no"
    out.loc[(out["side"] == "SELL") & (out["m15_macd_hist_delta"] > 0), "macd_hist_delta_supports_side"] = "no"

    return out


def write_feature_notes(path: Path) -> None:
    content = f"""# XM KIWAMI GOLD ABC v3 AI Case Feature Notes

This file explains the enriched AI case CSV.

## Output CSV

```text
data/results/ai_cases/xm_kiwami_gold_abc_v3_balanced_ai_cases_enriched.csv
```

## Important principle

The enriched columns are **pre-entry features**.
They are calculated from the signal candle or earlier market data, then joined to historical win/loss labels.

For future live evaluation:

- historical cases may include result/r/exit information as labels
- current signal snapshot must not include future result/r/exit information

## Indicator parameters

```text
ATR: 14-period simple rolling true range
EMA: 20 / 50 / 200
MACD: fast={MACD_FAST}, slow={MACD_SLOW}, signal={MACD_SIGNAL}
```

MACD parameters match the project discussion using fast EMA 6, slow EMA 13, signal 4.

## Main feature groups

### Risk/spread

```text
entry_risk_atr_ratio
entry_spread_atr_ratio
```

### H1 environment

```text
h1_ema_alignment
h1_close_ema20_gap_atr
h1_ema20_ema50_gap_atr
h1_ema50_ema200_gap_atr
h1_close_position_20
h1_range20_atr
```

### M15 environment

```text
m15_ema_alignment
m15_close_ema20_gap_atr
m15_ema20_ema50_gap_atr
m15_ema50_ema200_gap_atr
m15_close_position_20
m15_range20_atr
m15_body_ratio
m15_upper_wick_ratio
m15_lower_wick_ratio
```

### Direction support flags

```text
side_matches_h1_ema
side_matches_m15_ema
macd_hist_supports_side
macd_hist_delta_supports_side
```

## How AI should use this

1. Filter historical cases by same model and side first.
2. Compare current signal pre-entry features with win cases.
3. Compare current signal pre-entry features with loss cases.
4. Output both winning-pattern match and losing-pattern similarity.
5. Do not use the historical label columns as current-signal inputs.
"""
    path.write_text(content, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Add pre-entry market features to balanced AI cases.")
    parser.add_argument("--cases-csv", type=Path, default=DEFAULT_CASES_CSV)
    parser.add_argument("--m15-csv", type=Path, default=DEFAULT_M15_CSV)
    parser.add_argument("--h1-csv", type=Path, default=DEFAULT_H1_CSV)
    parser.add_argument("--out-csv", type=Path, default=DEFAULT_OUT_CSV)
    parser.add_argument("--notes", type=Path, default=DEFAULT_README)
    args = parser.parse_args()

    cases_csv = args.cases_csv if args.cases_csv.is_absolute() else PROJECT_ROOT / args.cases_csv
    m15_csv = args.m15_csv if args.m15_csv.is_absolute() else PROJECT_ROOT / args.m15_csv
    h1_csv = args.h1_csv if args.h1_csv.is_absolute() else PROJECT_ROOT / args.h1_csv
    out_csv = args.out_csv if args.out_csv.is_absolute() else PROJECT_ROOT / args.out_csv
    notes = args.notes if args.notes.is_absolute() else PROJECT_ROOT / args.notes

    for path in [cases_csv, m15_csv, h1_csv]:
        if not path.exists():
            raise FileNotFoundError(path)

    cases = pd.read_csv(cases_csv)
    if "signal_time" not in cases.columns:
        raise ValueError("cases CSV must contain signal_time")
    cases = cases.copy()
    cases["signal_time"] = pd.to_datetime(cases["signal_time"], errors="coerce")
    cases = cases.dropna(subset=["signal_time"]).sort_values("signal_time", kind="mergesort").reset_index(drop=True)

    features = prepare_feature_frame(m15_csv, h1_csv)

    enriched = pd.merge_asof(
        cases.sort_values("signal_time"),
        features.sort_values("time"),
        left_on="signal_time",
        right_on="time",
        direction="backward",
    )
    enriched = add_signal_derived_features(enriched)

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    enriched.to_csv(out_csv, index=False, encoding="utf-8-sig")
    write_feature_notes(notes)

    print("Cases loaded:", len(cases), cases_csv)
    print("M15 rows:", len(read_ohlc(m15_csv)), m15_csv)
    print("H1 rows:", len(read_ohlc(h1_csv)), h1_csv)
    print("Enriched rows:", len(enriched))
    print("Saved enriched cases:", out_csv)
    print("Saved notes:", notes)

    if "case_type" in enriched.columns:
        print("\nRows by case_type:")
        print(enriched.groupby("case_type").size().to_string())

    if "combined_signal_source" in enriched.columns:
        print("\nRows by source:")
        print(enriched.groupby("combined_signal_source").size().to_string())

    important = [
        "entry_risk_atr_ratio",
        "entry_spread_atr_ratio",
        "side_matches_h1_ema",
        "side_matches_m15_ema",
        "macd_hist_supports_side",
        "macd_hist_delta_supports_side",
    ]
    print("\nImportant feature preview:")
    preview_cols = [col for col in ["case_type", "combined_signal_source", "side", "jst_entry_time"] + important if col in enriched.columns]
    print(enriched[preview_cols].head(10).to_string(index=False))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
