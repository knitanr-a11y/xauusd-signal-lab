from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_LEDGER_CSV = PROJECT_ROOT / "data" / "results" / "ai_reviews" / "ai_review_ledger.csv"
DEFAULT_CASES_CSV = PROJECT_ROOT / "data" / "results" / "ai_cases" / "xm_kiwami_gold_abc_v3_balanced_ai_cases_enriched.csv"
DEFAULT_OUT_DIR = PROJECT_ROOT / "data" / "results" / "ai_reviews"

SUMMARY_COLUMNS = [
    "group_by",
    "group_value",
    "reviews",
    "actual_trades",
    "actual_wins",
    "actual_losses",
    "actual_win_rate",
    "actual_total_r",
    "actual_average_r",
]


def read_ledger(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    df = pd.read_csv(path)
    if df.empty:
        raise ValueError(f"Ledger is empty: {path}")
    if "recorded_at" in df.columns:
        df["recorded_at"] = pd.to_datetime(df["recorded_at"], errors="coerce")
    required = ["signal_id", "source_row", "final_risk_label"]
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"Ledger missing required columns: {missing}")
    df["source_row"] = pd.to_numeric(df["source_row"], errors="coerce")
    return df


def read_cases(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    df = pd.read_csv(path)
    if df.empty:
        raise ValueError(f"Cases CSV is empty: {path}")
    required = ["case_type", "result", "r"]
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"Cases CSV missing required columns: {missing}")
    df = df.reset_index(drop=False).rename(columns={"index": "source_row"})
    df["source_row"] = df["source_row"].astype(int)
    df["r"] = pd.to_numeric(df["r"], errors="coerce")
    return df


def latest_per_signal(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if "recorded_at" in out.columns:
        out = out.sort_values(["signal_id", "recorded_at"], kind="mergesort")
    else:
        out = out.reset_index(drop=False).rename(columns={"index": "ledger_order"})
        out = out.sort_values(["signal_id", "ledger_order"], kind="mergesort")
    return out.groupby("signal_id", as_index=False, dropna=False).tail(1).reset_index(drop=True)


def merge_reviews_with_cases(ledger: pd.DataFrame, cases: pd.DataFrame) -> pd.DataFrame:
    ledger = ledger.copy()
    ledger = ledger.dropna(subset=["source_row"])
    ledger["source_row"] = ledger["source_row"].astype(int)

    case_cols = [
        "source_row",
        "case_type",
        "result",
        "r",
        "combined_signal_source",
        "side",
        "jst_entry_time",
        "entry_risk_atr_ratio",
        "entry_spread_price_atr_ratio",
    ]
    available_case_cols = [col for col in case_cols if col in cases.columns]
    merged = ledger.merge(cases[available_case_cols], on="source_row", how="left", suffixes=("", "_case"))

    if "combined_signal_source_case" in merged.columns:
        merged["case_model"] = merged["combined_signal_source_case"]
    elif "combined_signal_source" in merged.columns:
        merged["case_model"] = merged["combined_signal_source"]
    else:
        merged["case_model"] = merged.get("signal_model", "")

    if "side_case" in merged.columns:
        merged["case_side"] = merged["side_case"]
    elif "side" in merged.columns:
        merged["case_side"] = merged["side"]
    else:
        merged["case_side"] = ""

    return merged


def summarize_group(df: pd.DataFrame, group_by: str) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for value, group in df.groupby(group_by, dropna=False):
        actual = group[group["result"].isin(["win", "loss"])].copy()
        wins = int((actual["result"] == "win").sum())
        losses = int((actual["result"] == "loss").sum())
        total = int(len(actual))
        total_r = float(actual["r"].sum()) if total else 0.0
        rows.append(
            {
                "group_by": group_by,
                "group_value": value,
                "reviews": int(len(group)),
                "actual_trades": total,
                "actual_wins": wins,
                "actual_losses": losses,
                "actual_win_rate": wins / total if total else 0.0,
                "actual_total_r": total_r,
                "actual_average_r": total_r / total if total else 0.0,
            }
        )
    return pd.DataFrame(rows)[SUMMARY_COLUMNS].sort_values(["group_by", "group_value"], kind="mergesort")


def summarize_combo(df: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for key, group in df.groupby(group_cols, dropna=False):
        if not isinstance(key, tuple):
            key = (key,)
        actual = group[group["result"].isin(["win", "loss"])].copy()
        wins = int((actual["result"] == "win").sum())
        losses = int((actual["result"] == "loss").sum())
        total = int(len(actual))
        total_r = float(actual["r"].sum()) if total else 0.0
        row: dict[str, object] = {
            "reviews": int(len(group)),
            "actual_trades": total,
            "actual_wins": wins,
            "actual_losses": losses,
            "actual_win_rate": wins / total if total else 0.0,
            "actual_total_r": total_r,
            "actual_average_r": total_r / total if total else 0.0,
        }
        for col, value in zip(group_cols, key):
            row[col] = value
        rows.append(row)
    ordered = group_cols + [
        "reviews",
        "actual_trades",
        "actual_wins",
        "actual_losses",
        "actual_win_rate",
        "actual_total_r",
        "actual_average_r",
    ]
    if not rows:
        return pd.DataFrame(columns=ordered)
    return pd.DataFrame(rows)[ordered].sort_values(group_cols, kind="mergesort")


def print_table(title: str, df: pd.DataFrame) -> None:
    print("\n" + "=" * 120)
    print(title)
    print("=" * 120)
    if df.empty:
        print("No data.")
    else:
        print(df.to_string(index=False))


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze actual outcomes by AI review label.")
    parser.add_argument("--ledger-csv", type=Path, default=DEFAULT_LEDGER_CSV)
    parser.add_argument("--cases-csv", type=Path, default=DEFAULT_CASES_CSV)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--dedupe", choices=["latest", "none"], default="latest", help="Use latest row per signal_id to avoid old manual tests mixing in.")
    args = parser.parse_args()

    ledger_csv = args.ledger_csv if args.ledger_csv.is_absolute() else PROJECT_ROOT / args.ledger_csv
    cases_csv = args.cases_csv if args.cases_csv.is_absolute() else PROJECT_ROOT / args.cases_csv
    out_dir = args.out_dir if args.out_dir.is_absolute() else PROJECT_ROOT / args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    ledger = read_ledger(ledger_csv)
    raw_ledger_rows = len(ledger)
    if args.dedupe == "latest":
        ledger = latest_per_signal(ledger)

    cases = read_cases(cases_csv)
    merged = merge_reviews_with_cases(ledger, cases)

    merged_out = out_dir / "ai_review_outcomes_merged_latest.csv"
    summary_out = out_dir / "ai_review_outcomes_summary_latest.csv"
    combo_out = out_dir / "ai_review_outcomes_combo_summary_latest.csv"

    merged.to_csv(merged_out, index=False, encoding="utf-8-sig")

    summary_parts = []
    for col in ["final_risk_label", "winning_pattern_match", "losing_pattern_similarity", "case_type"]:
        if col in merged.columns:
            summary_parts.append(summarize_group(merged, col))
    summary = pd.concat(summary_parts, ignore_index=True) if summary_parts else pd.DataFrame(columns=SUMMARY_COLUMNS)
    summary.to_csv(summary_out, index=False, encoding="utf-8-sig")

    combo_parts = []
    for cols in [
        ["winning_pattern_match", "losing_pattern_similarity", "final_risk_label"],
        ["case_model", "case_side", "final_risk_label"],
        ["case_type", "final_risk_label"],
    ]:
        if all(col in merged.columns for col in cols):
            part = summarize_combo(merged, cols)
            part.insert(0, "group_by", " x ".join(cols))
            combo_parts.append(part)
    combo = pd.concat(combo_parts, ignore_index=True, sort=False) if combo_parts else pd.DataFrame()
    combo.to_csv(combo_out, index=False, encoding="utf-8-sig")

    print("Ledger:", ledger_csv)
    print("Raw ledger rows:", raw_ledger_rows)
    print("Used ledger rows:", len(ledger), f"dedupe={args.dedupe}")
    print("Cases:", cases_csv)
    print("Merged rows:", len(merged))
    print("Saved merged:", merged_out)
    print("Saved summary:", summary_out)
    print("Saved combo summary:", combo_out)

    print_table("SUMMARY BY FINAL RISK LABEL", summary[summary["group_by"] == "final_risk_label"] if not summary.empty else summary)
    print_table("SUMMARY BY CASE_TYPE x FINAL_RISK_LABEL", combo[combo["group_by"] == "case_type x final_risk_label"] if not combo.empty else combo)
    print_table(
        "SUMMARY BY WIN_MATCH x LOSS_SIM x FINAL_RISK_LABEL",
        combo[combo["group_by"] == "winning_pattern_match x losing_pattern_similarity x final_risk_label"] if not combo.empty else combo,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
