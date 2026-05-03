from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.enrich_xm_kiwami_gold_abc_v3_ai_cases import (  # noqa: E402
    DEFAULT_H1_CSV,
    DEFAULT_M15_CSV,
    DEFAULT_POINT_SIZE,
    add_signal_derived_features,
    prepare_feature_frame,
    read_ohlc,
)

DEFAULT_TRADES_CSV = PROJECT_ROOT / "data" / "results" / "goldsharp_xm_kiwami_gold_abc_v3_backtest_trades.csv"
DEFAULT_OUT_CSV = PROJECT_ROOT / "data" / "results" / "ai_cases" / "xm_kiwami_gold_abc_v3_all_ai_cases_enriched.csv"
DEFAULT_NOTES = PROJECT_ROOT / "data" / "results" / "ai_cases" / "xm_kiwami_gold_abc_v3_all_ai_case_db_notes.md"


COLUMN_ALIASES = {
    "combined_signal_source": ["combined_signal_source", "signal_source", "source", "model", "strategy"],
    "signal_time": ["signal_time", "entry_time", "time", "open_time"],
    "side": ["side", "direction", "type"],
    "r": ["r", "R", "result_r", "profit_r"],
    "result": ["result", "outcome", "trade_result"],
}


def find_column(df: pd.DataFrame, names: list[str]) -> str | None:
    lower_map = {str(col).lower(): col for col in df.columns}
    for name in names:
        if name in df.columns:
            return name
        lowered = name.lower()
        if lowered in lower_map:
            return str(lower_map[lowered])
    return None


def ensure_standard_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()

    for standard, aliases in COLUMN_ALIASES.items():
        if standard in out.columns:
            continue
        found = find_column(out, aliases)
        if found is not None and found != standard:
            out[standard] = out[found]

    missing = [col for col in ["signal_time", "side"] if col not in out.columns]
    if missing:
        raise ValueError(f"Trades CSV missing required columns or aliases: {missing}. columns={list(out.columns)}")

    if "combined_signal_source" not in out.columns:
        out["combined_signal_source"] = "unknown"

    out["signal_time"] = pd.to_datetime(out["signal_time"], errors="coerce")
    if "entry_time" in out.columns:
        out["entry_time"] = pd.to_datetime(out["entry_time"], errors="coerce")
    else:
        out["entry_time"] = out["signal_time"]

    out = out.dropna(subset=["signal_time"]).sort_values("signal_time", kind="mergesort").reset_index(drop=True)
    out["side"] = out["side"].astype(str).str.upper().str.strip()
    out["combined_signal_source"] = out["combined_signal_source"].astype(str).str.strip()

    if "r" in out.columns:
        out["r"] = pd.to_numeric(out["r"], errors="coerce")
    else:
        raise ValueError("Trades CSV must contain r/R/result_r/profit_r column for AI labels.")

    if "result" not in out.columns:
        out["result"] = "unknown"
    out["result"] = out["result"].astype(str).str.lower().str.strip()
    out.loc[out["r"] > 0, "result"] = "win"
    out.loc[out["r"] < 0, "result"] = "loss"
    out.loc[out["r"] == 0, "result"] = out.loc[out["r"] == 0, "result"].replace({"unknown": "breakeven", "": "breakeven"})

    out["case_type"] = "other_pattern"
    out.loc[out["result"] == "win", "case_type"] = "win_pattern"
    out.loc[out["result"] == "loss", "case_type"] = "loss_pattern"

    if "case_reason" not in out.columns:
        out["case_reason"] = "all_trade_case_db"

    # jst_* columns are often already present in backtest output. Create them if missing.
    if "jst_entry_time" not in out.columns:
        out["jst_entry_time"] = out["entry_time"]
    else:
        out["jst_entry_time"] = pd.to_datetime(out["jst_entry_time"], errors="coerce")

    if "jst_entry_month" not in out.columns:
        out["jst_entry_month"] = pd.to_datetime(out["jst_entry_time"], errors="coerce").dt.to_period("M").astype(str)
    if "jst_entry_hour" not in out.columns:
        out["jst_entry_hour"] = pd.to_datetime(out["jst_entry_time"], errors="coerce").dt.hour

    numeric_cols = ["entry_price", "sl", "tp", "risk", "bars_held"]
    for col in numeric_cols:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")

    if "risk" not in out.columns:
        if {"entry_price", "sl"}.issubset(out.columns):
            out["risk"] = (out["entry_price"] - out["sl"]).abs()
        else:
            raise ValueError("Trades CSV must contain risk, or both entry_price and sl.")

    out["source_trade_row"] = out.index.astype(int)
    return out


def build_all_case_db(
    *,
    trades_csv: Path,
    m15_csv: Path,
    h1_csv: Path,
    out_csv: Path,
    notes: Path,
    point_size: float,
) -> pd.DataFrame:
    if not trades_csv.exists():
        raise FileNotFoundError(trades_csv)
    for path in [m15_csv, h1_csv]:
        if not path.exists():
            raise FileNotFoundError(path)

    trades_raw = pd.read_csv(trades_csv)
    trades = ensure_standard_columns(trades_raw)
    features = prepare_feature_frame(m15_csv, h1_csv, point_size=point_size)

    enriched = pd.merge_asof(
        trades.sort_values("signal_time"),
        features.sort_values("time"),
        left_on="signal_time",
        right_on="time",
        direction="backward",
    )
    enriched = add_signal_derived_features(enriched)
    enriched = enriched.reset_index(drop=True)
    enriched["ai_case_db_row"] = enriched.index.astype(int)

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    enriched.to_csv(out_csv, index=False, encoding="utf-8-sig")
    write_notes(notes, trades_csv=trades_csv, out_csv=out_csv, rows=len(enriched), point_size=point_size)
    return enriched


def write_notes(path: Path, *, trades_csv: Path, out_csv: Path, rows: int, point_size: float) -> None:
    content = f"""# XM KIWAMI GOLD ABC v3 All AI Case DB

This file documents the all-trade AI case database.

## Source

```text
{trades_csv.relative_to(PROJECT_ROOT) if trades_csv.is_relative_to(PROJECT_ROOT) else trades_csv}
```

## Output

```text
{out_csv.relative_to(PROJECT_ROOT) if out_csv.is_relative_to(PROJECT_ROOT) else out_csv}
```

## Rows

```text
{rows}
```

## Important concept

This is a local AI case database. It is not sent to OpenAI in full every time.

Live/shadow workflow:

1. Current signal appears.
2. Python calculates the same pre-entry features.
3. Python searches this local case DB for similar win/loss cases.
4. Only the nearest win cases and nearest loss cases are sent to AI.

## Spread point size

```text
{point_size}
```

## Labels

`result`, `r`, `exit_reason`, `bars_held`, and `case_type` are historical labels.
They may be used for historical cases, but must not be used as current-signal input.
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def print_summary(enriched: pd.DataFrame) -> None:
    print("\nRows:", len(enriched))
    if "result" in enriched.columns:
        print("\nRows by result:")
        print(enriched.groupby("result", dropna=False).size().to_string())
    if "case_type" in enriched.columns:
        print("\nRows by case_type:")
        print(enriched.groupby("case_type", dropna=False).size().to_string())
    if "combined_signal_source" in enriched.columns:
        print("\nRows by source:")
        print(enriched.groupby("combined_signal_source", dropna=False).size().to_string())
    if {"combined_signal_source", "side", "result"}.issubset(enriched.columns):
        print("\nRows by source/side/result:")
        print(enriched.groupby(["combined_signal_source", "side", "result"], dropna=False).size().to_string())

    if "r" in enriched.columns:
        total_r = float(pd.to_numeric(enriched["r"], errors="coerce").sum())
        print("\nTotal R:", total_r)

    preview_cols = [
        "ai_case_db_row",
        "source_trade_row",
        "case_type",
        "combined_signal_source",
        "side",
        "jst_entry_time",
        "result",
        "r",
        "entry_risk_atr_ratio",
        "entry_spread_price_atr_ratio",
        "side_matches_h1_ema",
        "side_matches_m15_ema",
        "h1_macd_hist_supports_side",
        "m15_macd_hist_supports_side",
        "m15_recent_pushback_against_side",
        "m15_recent_momentum_supports_side",
    ]
    preview_cols = [col for col in preview_cols if col in enriched.columns]
    print("\nPreview:")
    print(enriched[preview_cols].head(20).to_string(index=False))


def main() -> int:
    parser = argparse.ArgumentParser(description="Build all-trade enriched AI case DB for XM KIWAMI GOLD ABC v3.")
    parser.add_argument("--trades-csv", type=Path, default=DEFAULT_TRADES_CSV)
    parser.add_argument("--m15-csv", type=Path, default=DEFAULT_M15_CSV)
    parser.add_argument("--h1-csv", type=Path, default=DEFAULT_H1_CSV)
    parser.add_argument("--out-csv", type=Path, default=DEFAULT_OUT_CSV)
    parser.add_argument("--notes", type=Path, default=DEFAULT_NOTES)
    parser.add_argument("--point-size", type=float, default=DEFAULT_POINT_SIZE)
    args = parser.parse_args()

    trades_csv = args.trades_csv if args.trades_csv.is_absolute() else PROJECT_ROOT / args.trades_csv
    m15_csv = args.m15_csv if args.m15_csv.is_absolute() else PROJECT_ROOT / args.m15_csv
    h1_csv = args.h1_csv if args.h1_csv.is_absolute() else PROJECT_ROOT / args.h1_csv
    out_csv = args.out_csv if args.out_csv.is_absolute() else PROJECT_ROOT / args.out_csv
    notes = args.notes if args.notes.is_absolute() else PROJECT_ROOT / args.notes

    enriched = build_all_case_db(
        trades_csv=trades_csv,
        m15_csv=m15_csv,
        h1_csv=h1_csv,
        out_csv=out_csv,
        notes=notes,
        point_size=args.point_size,
    )

    print("Trades:", trades_csv)
    print("M15 rows:", len(read_ohlc(m15_csv)), m15_csv)
    print("H1 rows:", len(read_ohlc(h1_csv)), h1_csv)
    print("Saved all AI case DB:", out_csv)
    print("Saved notes:", notes)
    print_summary(enriched)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
