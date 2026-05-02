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
DEFAULT_POINT_SIZE = 0.01  # XM KIWAMI GOLD# usually uses 0.01 price units per spread point.


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
    out[f"{prefix}_macd_hist_delta_3"] = macd_hist - macd_hist.shift(3)
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
    out[f"{prefix}_upper_wick_ratio_3"] = out[f"{prefix}_upper_wick_ratio"].rolling(3, min_periods=1).mean()
    out[f"{prefix}_lower_wick_ratio_3"] = out[f"{prefix}_lower_wick_ratio"].rolling(3, min_periods=1).mean()

    out[f"{prefix}_close_change_1"] = close.diff()
    out[f"{prefix}_close_change_3"] = close - close.shift(3)
    out[f"{prefix}_close_change_3_atr"] = out[f"{prefix}_close_change_3"] / out[f"{prefix}_atr14"].replace(0, pd.NA)

    rolling_high_5 = high.rolling(5, min_periods=1).max()
    rolling_low_5 = low.rolling(5, min_periods=1).min()
    out[f"{prefix}_pullback_from_high_5_atr"] = (rolling_high_5 - close) / out[f"{prefix}_atr14"].replace(0, pd.NA)
    out[f"{prefix}_rebound_from_low_5_atr"] = (close - rolling_low_5) / out[f"{prefix}_atr14"].replace(0, pd.NA)
    out[f"{prefix}_close_vs_prev_high_atr"] = (close - high.shift(1)) / out[f"{prefix}_atr14"].replace(0, pd.NA)
    out[f"{prefix}_close_vs_prev_low_atr"] = (close - low.shift(1)) / out[f"{prefix}_atr14"].replace(0, pd.NA)

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


def add_spread_price_columns(df: pd.DataFrame, *, prefix: str, point_size: float) -> pd.DataFrame:
    out = df.copy()
    spread_col = f"{prefix}_spread"
    if spread_col not in out.columns:
        return out
    out[f"{prefix}_spread_points"] = out[spread_col]
    out[f"{prefix}_spread_point_size"] = point_size
    out[f"{prefix}_spread_price"] = out[f"{prefix}_spread_points"] * point_size
    return out


def prepare_feature_frame(m15_path: Path, h1_path: Path, *, point_size: float) -> pd.DataFrame:
    m15 = add_indicators(read_ohlc(m15_path), "m15")
    h1 = add_indicators(read_ohlc(h1_path), "h1")

    h1 = h1.rename(columns={"open": "h1_open", "high": "h1_high", "low": "h1_low", "close": "h1_close", "spread": "h1_spread"})
    h1 = add_spread_price_columns(h1, prefix="h1", point_size=point_size)

    h1_cols = [
        "time",
        "h1_open",
        "h1_high",
        "h1_low",
        "h1_close",
        "h1_spread",
        "h1_spread_points",
        "h1_spread_point_size",
        "h1_spread_price",
        "h1_ema20",
        "h1_ema50",
        "h1_ema200",
        "h1_atr14",
        "h1_macd_line",
        "h1_macd_signal",
        "h1_macd_hist",
        "h1_macd_hist_delta",
        "h1_macd_hist_delta_3",
        "h1_ema_alignment",
        "h1_close_ema20_gap_atr",
        "h1_ema20_ema50_gap_atr",
        "h1_ema50_ema200_gap_atr",
        "h1_close_position_20",
        "h1_range20_atr",
        "h1_close_change_3_atr",
        "h1_pullback_from_high_5_atr",
        "h1_rebound_from_low_5_atr",
        "h1_upper_wick_ratio_3",
        "h1_lower_wick_ratio_3",
    ]
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
    m15 = add_spread_price_columns(m15, prefix="m15", point_size=point_size)
    m15["m15_feature_time"] = m15["time"]

    merged = pd.merge_asof(
        m15.sort_values("time"),
        h1_subset.sort_values("h1_feature_time"),
        left_on="time",
        right_on="h1_feature_time",
        direction="backward",
    )
    return merged.sort_values("time", kind="mergesort").reset_index(drop=True)


def set_direction_flag(out: pd.DataFrame, flag_col: str, source_col: str) -> None:
    out[flag_col] = "unknown"
    out.loc[(out["side"] == "BUY") & (out[source_col] > 0), flag_col] = "yes"
    out.loc[(out["side"] == "SELL") & (out[source_col] < 0), flag_col] = "yes"
    out.loc[(out["side"] == "BUY") & (out[source_col] < 0), flag_col] = "no"
    out.loc[(out["side"] == "SELL") & (out[source_col] > 0), flag_col] = "no"


def add_signal_derived_features(cases: pd.DataFrame) -> pd.DataFrame:
    out = cases.copy()
    out["entry_risk_atr_ratio"] = out["risk"] / out["m15_atr14"].replace(0, pd.NA)

    if "m15_spread" in out.columns:
        out["entry_spread_points_atr_ratio_deprecated"] = out["m15_spread"] / out["m15_atr14"].replace(0, pd.NA)
    if "m15_spread_price" in out.columns:
        out["entry_spread_price_atr_ratio"] = out["m15_spread_price"] / out["m15_atr14"].replace(0, pd.NA)

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

    set_direction_flag(out, "m15_macd_hist_supports_side", "m15_macd_hist")
    set_direction_flag(out, "m15_macd_hist_delta_supports_side", "m15_macd_hist_delta")
    set_direction_flag(out, "m15_macd_hist_delta3_supports_side", "m15_macd_hist_delta_3")
    set_direction_flag(out, "h1_macd_hist_supports_side", "h1_macd_hist")
    set_direction_flag(out, "h1_macd_hist_delta_supports_side", "h1_macd_hist_delta")
    set_direction_flag(out, "h1_macd_hist_delta3_supports_side", "h1_macd_hist_delta_3")

    # Backward compatible aliases used by existing scripts/payloads.
    out["macd_hist_supports_side"] = out["m15_macd_hist_supports_side"]
    out["macd_hist_delta_supports_side"] = out["m15_macd_hist_delta_supports_side"]

    out["m15_recent_pushback_against_side"] = "unknown"
    buy_pushback = (
        ((out.get("m15_upper_wick_ratio_3") > 0.35) | (out.get("m15_pullback_from_high_5_atr") > 0.60) | (out.get("m15_close_change_3_atr") < -0.25))
        & (out["side"] == "BUY")
    )
    sell_pushback = (
        ((out.get("m15_lower_wick_ratio_3") > 0.35) | (out.get("m15_rebound_from_low_5_atr") > 0.60) | (out.get("m15_close_change_3_atr") > 0.25))
        & (out["side"] == "SELL")
    )
    out.loc[buy_pushback | sell_pushback, "m15_recent_pushback_against_side"] = "yes"
    out.loc[~(buy_pushback | sell_pushback), "m15_recent_pushback_against_side"] = "no"

    out["m15_recent_momentum_supports_side"] = "unknown"
    buy_momentum = (out["side"] == "BUY") & (out["m15_close_change_3_atr"] > 0) & (out["m15_macd_hist_delta_3"] > 0)
    sell_momentum = (out["side"] == "SELL") & (out["m15_close_change_3_atr"] < 0) & (out["m15_macd_hist_delta_3"] < 0)
    out.loc[buy_momentum | sell_momentum, "m15_recent_momentum_supports_side"] = "yes"
    out.loc[~(buy_momentum | sell_momentum), "m15_recent_momentum_supports_side"] = "no"

    return out


def write_feature_notes(path: Path, *, point_size: float) -> None:
    content = f"""# XM KIWAMI GOLD ABC v3 AI Case Feature Notes

This file explains the enriched AI case CSV.

## Output CSV

```text
data/results/ai_cases/xm_kiwami_gold_abc_v3_balanced_ai_cases_enriched.csv
```

## Important principle

The enriched columns are **pre-entry features**. They are calculated from the signal candle or earlier market data, then joined to historical win/loss labels.

Historical cases may include result/r/exit information as labels. Current signal snapshots must not include future result/r/exit information.

## Indicator parameters

```text
ATR: 14-period simple rolling true range
EMA: 20 / 50 / 200
MACD: fast={MACD_FAST}, slow={MACD_SLOW}, signal={MACD_SIGNAL}
spread point size: {point_size}
```

## Spread columns

Use these columns for spread:

```text
m15_spread_points
m15_spread_point_size
m15_spread_price
entry_spread_price_atr_ratio
```

Do not use:

```text
entry_spread_points_atr_ratio_deprecated
```

## Main feature groups

### Risk/spread

```text
entry_risk_atr_ratio
m15_spread_points
m15_spread_price
entry_spread_price_atr_ratio
```

### H1 environment

```text
h1_ema_alignment
h1_close_ema20_gap_atr
h1_ema20_ema50_gap_atr
h1_ema50_ema200_gap_atr
h1_close_position_20
h1_range20_atr
h1_macd_hist_supports_side
h1_macd_hist_delta_supports_side
h1_macd_hist_delta3_supports_side
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
m15_upper_wick_ratio_3
m15_lower_wick_ratio_3
m15_close_change_3_atr
m15_pullback_from_high_5_atr
m15_rebound_from_low_5_atr
m15_recent_pushback_against_side
m15_recent_momentum_supports_side
```

### Direction support flags

```text
side_matches_h1_ema
side_matches_m15_ema
m15_macd_hist_supports_side
m15_macd_hist_delta_supports_side
m15_macd_hist_delta3_supports_side
h1_macd_hist_supports_side
h1_macd_hist_delta_supports_side
h1_macd_hist_delta3_supports_side
```

Backward-compatible aliases:

```text
macd_hist_supports_side = m15_macd_hist_supports_side
macd_hist_delta_supports_side = m15_macd_hist_delta_supports_side
```

## Why these features were added

A normal-rated losing sample showed that M15 EMA/MACD alignment alone is not enough.
The added H1 MACD and recent pushback features help the AI detect cases where the signal looks clean but the broader or very recent momentum is weakening.
"""
    path.write_text(content, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Add pre-entry market features to balanced AI cases.")
    parser.add_argument("--cases-csv", type=Path, default=DEFAULT_CASES_CSV)
    parser.add_argument("--m15-csv", type=Path, default=DEFAULT_M15_CSV)
    parser.add_argument("--h1-csv", type=Path, default=DEFAULT_H1_CSV)
    parser.add_argument("--out-csv", type=Path, default=DEFAULT_OUT_CSV)
    parser.add_argument("--notes", type=Path, default=DEFAULT_README)
    parser.add_argument("--point-size", type=float, default=DEFAULT_POINT_SIZE, help="Price units per MT5 spread point. GOLD# default: 0.01")
    args = parser.parse_args()

    cases_csv = args.cases_csv if args.cases_csv.is_absolute() else PROJECT_ROOT / args.cases_csv
    m15_csv = args.m15_csv if args.m15_csv.is_absolute() else PROJECT_ROOT / args.m15_csv
    h1_csv = args.h1_csv if args.h1_csv.is_absolute() else PROJECT_ROOT / args.h1_csv
    out_csv = args.out_csv if args.out_csv.is_absolute() else PROJECT_ROOT / args.out_csv
    notes = args.notes if args.notes.is_absolute() else PROJECT_ROOT / args.notes

    if args.point_size <= 0:
        raise ValueError("--point-size must be positive")

    for path in [cases_csv, m15_csv, h1_csv]:
        if not path.exists():
            raise FileNotFoundError(path)

    cases = pd.read_csv(cases_csv)
    if "signal_time" not in cases.columns:
        raise ValueError("cases CSV must contain signal_time")
    cases = cases.copy()
    cases["signal_time"] = pd.to_datetime(cases["signal_time"], errors="coerce")
    cases = cases.dropna(subset=["signal_time"]).sort_values("signal_time", kind="mergesort").reset_index(drop=True)

    features = prepare_feature_frame(m15_csv, h1_csv, point_size=args.point_size)

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
    write_feature_notes(notes, point_size=args.point_size)

    print("Cases loaded:", len(cases), cases_csv)
    print("M15 rows:", len(read_ohlc(m15_csv)), m15_csv)
    print("H1 rows:", len(read_ohlc(h1_csv)), h1_csv)
    print("Point size:", args.point_size)
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
        "entry_spread_price_atr_ratio",
        "side_matches_h1_ema",
        "side_matches_m15_ema",
        "m15_macd_hist_supports_side",
        "m15_macd_hist_delta_supports_side",
        "m15_macd_hist_delta3_supports_side",
        "h1_macd_hist_supports_side",
        "h1_macd_hist_delta_supports_side",
        "h1_macd_hist_delta3_supports_side",
        "m15_recent_pushback_against_side",
        "m15_recent_momentum_supports_side",
    ]
    print("\nImportant feature preview:")
    preview_cols = [col for col in ["case_type", "combined_signal_source", "side", "jst_entry_time"] + important if col in enriched.columns]
    print(enriched[preview_cols].head(10).to_string(index=False))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
