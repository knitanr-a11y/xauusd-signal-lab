from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.backtest import summarize_trades

DEFAULT_TRADES_CSV = PROJECT_ROOT / "data" / "results" / "goldsharp_xm_kiwami_gold_abc_v3_backtest_trades.csv"
DEFAULT_OUT_DIR = PROJECT_ROOT / "data" / "results" / "ai_cases"

WIN_MONTHS = ["2025-07", "2025-08", "2025-09", "2025-10", "2026-01", "2026-02", "2026-04"]
LOSS_MONTHS = ["2025-03"]

CASE_COLUMNS = [
    "case_type",
    "case_reason",
    "combined_signal_source",
    "side",
    "signal_time",
    "entry_time",
    "jst_entry_time",
    "exit_time",
    "entry_price",
    "sl",
    "tp",
    "risk",
    "result",
    "r",
    "exit_reason",
    "bars_held",
    "jst_entry_month",
    "jst_entry_hour",
]


def normalize_source_col(df: pd.DataFrame) -> str:
    if "combined_signal_source" in df.columns:
        return "combined_signal_source"
    if "signal_source" in df.columns:
        return "signal_source"
    raise ValueError("source column not found. Expected combined_signal_source or signal_source.")


def prepare_trades(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()

    for col in ["signal_time", "entry_time", "exit_time", "jst_entry_time"]:
        if col in out.columns:
            out[col] = pd.to_datetime(out[col], errors="coerce")

    if "jst_entry_time" in out.columns:
        out["jst_entry_month"] = out["jst_entry_time"].dt.to_period("M").astype(str)
        out["jst_entry_hour"] = out["jst_entry_time"].dt.hour
        out["jst_entry_date"] = out["jst_entry_time"].dt.strftime("%Y-%m-%d")
    else:
        raise ValueError("jst_entry_time column not found.")

    return out


def summarize_grouped(trades: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
    if trades.empty:
        return pd.DataFrame()

    rows: list[dict[str, object]] = []
    for key, group in trades.groupby(group_cols, dropna=False):
        if not isinstance(key, tuple):
            key = (key,)
        summary = summarize_trades(group)
        for col, value in zip(group_cols, key):
            summary[col] = value
        rows.append(summary)

    if not rows:
        return pd.DataFrame()

    ordered = group_cols + [
        "trades",
        "closed_trades",
        "wins",
        "losses",
        "win_rate",
        "average_r",
        "total_r",
        "profit_factor",
        "max_consecutive_losses",
        "max_drawdown_r",
    ]
    return pd.DataFrame(rows)[ordered].reset_index(drop=True)


def pick_representative_wins(trades: pd.DataFrame, source_col: str, max_per_source: int) -> pd.DataFrame:
    wins = trades[trades["r"] > 0].copy()
    wins = wins[wins["jst_entry_month"].isin(WIN_MONTHS)].copy()
    if wins.empty:
        return wins

    # Prefer clean, not too quick/not too huge outliers. Keep diversity by source.
    wins["abs_risk_rank"] = wins["risk"].rank(method="first") if "risk" in wins.columns else 0
    selected: list[pd.DataFrame] = []

    for source, group in wins.groupby(source_col, dropna=False):
        group = group.sort_values(["jst_entry_month", "jst_entry_time"]).copy()
        # take a spread across the time span instead of only the first N
        if len(group) <= max_per_source:
            chosen = group
        else:
            idx = [round(i * (len(group) - 1) / (max_per_source - 1)) for i in range(max_per_source)]
            chosen = group.iloc[idx]
        selected.append(chosen)

    if not selected:
        return pd.DataFrame()

    out = pd.concat(selected, ignore_index=True)
    out["case_type"] = "win_pattern"
    out["case_reason"] = "Representative winning trade from strong/healthy months"
    return out


def pick_representative_losses(trades: pd.DataFrame, source_col: str, max_per_source: int) -> pd.DataFrame:
    losses = trades[trades["r"] < 0].copy()
    losses = losses[losses["jst_entry_month"].isin(LOSS_MONTHS)].copy()
    if losses.empty:
        return losses

    selected: list[pd.DataFrame] = []
    for source, group in losses.groupby(source_col, dropna=False):
        group = group.sort_values(["jst_entry_time"]).copy()
        chosen = group.head(max_per_source)
        selected.append(chosen)

    if not selected:
        return pd.DataFrame()

    out = pd.concat(selected, ignore_index=True)
    out["case_type"] = "loss_pattern"
    out["case_reason"] = "Representative losing trade from weak month 2025-03"
    return out


def safe_columns(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    available = [col for col in columns if col in df.columns]
    return df[available].copy()


def write_markdown_summary(
    path: Path,
    all_trades: pd.DataFrame,
    win_cases: pd.DataFrame,
    loss_cases: pd.DataFrame,
    source_col: str,
) -> None:
    overall = summarize_trades(all_trades)
    by_month = summarize_grouped(all_trades, ["jst_entry_month"])
    by_source = summarize_grouped(all_trades, [source_col])
    win_month_summary = summarize_grouped(all_trades[all_trades["jst_entry_month"].isin(WIN_MONTHS)], ["jst_entry_month"])
    loss_month_summary = summarize_grouped(all_trades[all_trades["jst_entry_month"].isin(LOSS_MONTHS)], ["jst_entry_month"])

    def df_md(df: pd.DataFrame) -> str:
        if df.empty:
            return "No data.\n"
        return df.to_markdown(index=False) + "\n"

    content = f"""# XM KIWAMI GOLD ABC v3 AI Case Summary

This file summarizes representative winning and losing cases for future AI-assisted signal review.

## Purpose

AI evaluation should not be biased only toward avoiding losses.  
The main comparison should be:

1. Is the current signal similar to past winning patterns?
2. Is the current signal also dangerously similar to past losing patterns?
3. Which side of the evidence is stronger?

## Base preset

```text
xm_kiwami_gold_abc_v3
```

## Overall backtest summary

```text
trades: {overall.get('trades')}
wins: {overall.get('wins')}
losses: {overall.get('losses')}
win_rate: {overall.get('win_rate')}
total_r: {overall.get('total_r')}
profit_factor: {overall.get('profit_factor')}
max_drawdown_r: {overall.get('max_drawdown_r')}
max_consecutive_losses: {overall.get('max_consecutive_losses')}
```

## Strong/healthy months used as win-pattern source

```text
{', '.join(WIN_MONTHS)}
```

{df_md(win_month_summary)}

## Weak months used as loss-pattern source

```text
{', '.join(LOSS_MONTHS)}
```

{df_md(loss_month_summary)}

## Summary by source

{df_md(by_source)}

## Representative win cases

Saved CSV:

```text
data/results/ai_cases/xm_kiwami_gold_abc_v3_win_cases.csv
```

Rows: {len(win_cases)}

## Representative loss cases

Saved CSV:

```text
data/results/ai_cases/xm_kiwami_gold_abc_v3_loss_cases.csv
```

Rows: {len(loss_cases)}

## Suggested AI prompt policy

```text
Evaluate the current signal by comparing it to both winning and losing historical cases.
Do not over-penalize the signal just because it shares one feature with a losing case.
First identify which winning cases it resembles, then identify losing-case risks.
Return:
- winning_pattern_match: high / medium / low
- losing_pattern_similarity: high / medium / low
- final_risk_label: normal / caution / strong_caution / skip_candidate
- evidence_for_entry
- evidence_against_entry
- human_checkpoints
```

## Full monthly summary

{df_md(by_month)}
"""
    path.write_text(content, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract balanced AI win/loss cases from XM KIWAMI GOLD ABC v3 trades.")
    parser.add_argument("--trades-csv", type=Path, default=DEFAULT_TRADES_CSV)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--max-win-per-source", type=int, default=8)
    parser.add_argument("--max-loss-per-source", type=int, default=6)
    args = parser.parse_args()

    trades_csv = args.trades_csv
    if not trades_csv.is_absolute():
        trades_csv = PROJECT_ROOT / trades_csv

    out_dir = args.out_dir
    if not out_dir.is_absolute():
        out_dir = PROJECT_ROOT / out_dir

    if not trades_csv.exists():
        print(f"Trades CSV not found: {trades_csv}")
        print("Run first:")
        print("python scripts/run_preset_backtest.py --preset xm_kiwami_gold_abc_v3 --data-dir data/raw/xm_kiwami --save")
        return 1

    out_dir.mkdir(parents=True, exist_ok=True)

    trades = pd.read_csv(trades_csv)
    trades = prepare_trades(trades)
    source_col = normalize_source_col(trades)

    win_cases = pick_representative_wins(trades, source_col=source_col, max_per_source=args.max_win_per_source)
    loss_cases = pick_representative_losses(trades, source_col=source_col, max_per_source=args.max_loss_per_source)

    win_cases_out = out_dir / "xm_kiwami_gold_abc_v3_win_cases.csv"
    loss_cases_out = out_dir / "xm_kiwami_gold_abc_v3_loss_cases.csv"
    combined_cases_out = out_dir / "xm_kiwami_gold_abc_v3_balanced_ai_cases.csv"
    summary_out = out_dir / "xm_kiwami_gold_abc_v3_ai_case_summary.md"

    win_cases_to_save = safe_columns(win_cases, CASE_COLUMNS)
    loss_cases_to_save = safe_columns(loss_cases, CASE_COLUMNS)
    combined = pd.concat([win_cases_to_save, loss_cases_to_save], ignore_index=True)

    win_cases_to_save.to_csv(win_cases_out, index=False, encoding="utf-8-sig")
    loss_cases_to_save.to_csv(loss_cases_out, index=False, encoding="utf-8-sig")
    combined.to_csv(combined_cases_out, index=False, encoding="utf-8-sig")
    write_markdown_summary(summary_out, trades, win_cases_to_save, loss_cases_to_save, source_col=source_col)

    print("Loaded:", trades_csv)
    print("Total trades:", len(trades))
    print("Win cases:", len(win_cases_to_save), "->", win_cases_out)
    print("Loss cases:", len(loss_cases_to_save), "->", loss_cases_out)
    print("Balanced cases:", len(combined), "->", combined_cases_out)
    print("Summary:", summary_out)

    print("\nWin cases by source:")
    if win_cases_to_save.empty:
        print("No win cases.")
    else:
        print(win_cases_to_save.groupby("combined_signal_source").size().to_string())

    print("\nLoss cases by source:")
    if loss_cases_to_save.empty:
        print("No loss cases.")
    else:
        print(loss_cases_to_save.groupby("combined_signal_source").size().to_string())

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
