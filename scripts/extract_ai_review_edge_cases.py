from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_MERGED_CSV = PROJECT_ROOT / "data" / "results" / "ai_reviews" / "ai_review_outcomes_merged_latest.csv"
DEFAULT_OUT_DIR = PROJECT_ROOT / "data" / "results" / "ai_reviews"

IMPORTANT_COLUMNS = [
    "source_row",
    "signal_id",
    "recorded_at",
    "case_type",
    "final_risk_label",
    "winning_pattern_match",
    "losing_pattern_similarity",
    "result",
    "r",
    "signal_model",
    "case_model",
    "side",
    "case_side",
    "jst_entry_time",
    "jst_entry_hour",
    "entry_price",
    "sl",
    "tp",
    "risk",
    "entry_risk_atr_ratio",
    "entry_spread_price_atr_ratio",
    "h1_ema_alignment",
    "m15_ema_alignment",
    "side_matches_h1_ema",
    "side_matches_m15_ema",
    "macd_hist_supports_side",
    "macd_hist_delta_supports_side",
    "h1_close_ema20_gap_atr",
    "h1_range20_atr",
    "m15_close_ema20_gap_atr",
    "m15_range20_atr",
    "m15_body_ratio",
    "m15_upper_wick_ratio",
    "m15_lower_wick_ratio",
    "m15_macd_hist",
    "m15_macd_hist_delta",
    "evidence_for_entry",
    "evidence_against_entry",
    "human_checkpoints",
    "actual_result",
    "actual_r",
    "actual_exit_reason",
    "notes",
]


def read_merged(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    df = pd.read_csv(path)
    if df.empty:
        raise ValueError(f"Merged outcome CSV is empty: {path}")
    required = ["final_risk_label", "result", "r"]
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"Merged outcome CSV missing required columns: {missing}")
    df["r"] = pd.to_numeric(df["r"], errors="coerce")
    return df


def safe_select(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    available = [col for col in columns if col in df.columns]
    return df[available].copy()


def summarize(df: pd.DataFrame, title: str) -> None:
    print("\n" + "=" * 120)
    print(title)
    print("=" * 120)
    print("rows:", len(df))
    if df.empty:
        return
    wins = int((df["result"] == "win").sum()) if "result" in df.columns else 0
    losses = int((df["result"] == "loss").sum()) if "result" in df.columns else 0
    total_r = float(df["r"].sum()) if "r" in df.columns else 0.0
    print("wins:", wins)
    print("losses:", losses)
    print("total_r:", total_r)

    group_cols = [col for col in ["case_type", "signal_model", "case_model", "side", "case_side", "winning_pattern_match", "losing_pattern_similarity"] if col in df.columns]
    for col in group_cols:
        print(f"\nBy {col}:")
        print(df.groupby(col, dropna=False).size().to_string())

    preview_cols = [
        col
        for col in [
            "source_row",
            "case_type",
            "final_risk_label",
            "winning_pattern_match",
            "losing_pattern_similarity",
            "result",
            "r",
            "signal_model",
            "case_model",
            "side",
            "case_side",
            "jst_entry_time",
            "entry_risk_atr_ratio",
            "entry_spread_price_atr_ratio",
            "h1_ema_alignment",
            "m15_ema_alignment",
            "side_matches_h1_ema",
            "side_matches_m15_ema",
            "macd_hist_supports_side",
            "macd_hist_delta_supports_side",
        ]
        if col in df.columns
    ]
    print("\nPreview:")
    print(df[preview_cols].to_string(index=False))


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract AI review edge cases for manual inspection.")
    parser.add_argument("--merged-csv", type=Path, default=DEFAULT_MERGED_CSV)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    args = parser.parse_args()

    merged_csv = args.merged_csv if args.merged_csv.is_absolute() else PROJECT_ROOT / args.merged_csv
    out_dir = args.out_dir if args.out_dir.is_absolute() else PROJECT_ROOT / args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    df = read_merged(merged_csv)

    normal_losses = df[(df["final_risk_label"] == "normal") & (df["result"] == "loss")].copy()
    caution_wins = df[(df["final_risk_label"] == "caution") & (df["result"] == "win")].copy()
    caution_losses = df[(df["final_risk_label"] == "caution") & (df["result"] == "loss")].copy()
    normal_wins = df[(df["final_risk_label"] == "normal") & (df["result"] == "win")].copy()

    outputs = {
        "ai_review_normal_losses.csv": normal_losses,
        "ai_review_caution_wins.csv": caution_wins,
        "ai_review_caution_losses.csv": caution_losses,
        "ai_review_normal_wins.csv": normal_wins,
    }

    for filename, part in outputs.items():
        path = out_dir / filename
        safe_select(part, IMPORTANT_COLUMNS).to_csv(path, index=False, encoding="utf-8-sig")
        print("Saved:", path, "rows=", len(part))

    summary_rows = [
        {"bucket": "normal_losses", "rows": len(normal_losses), "total_r": float(normal_losses["r"].sum()) if not normal_losses.empty else 0.0},
        {"bucket": "caution_wins", "rows": len(caution_wins), "total_r": float(caution_wins["r"].sum()) if not caution_wins.empty else 0.0},
        {"bucket": "caution_losses", "rows": len(caution_losses), "total_r": float(caution_losses["r"].sum()) if not caution_losses.empty else 0.0},
        {"bucket": "normal_wins", "rows": len(normal_wins), "total_r": float(normal_wins["r"].sum()) if not normal_wins.empty else 0.0},
    ]
    summary_df = pd.DataFrame(summary_rows)
    summary_path = out_dir / "ai_review_edge_case_summary.csv"
    summary_df.to_csv(summary_path, index=False, encoding="utf-8-sig")
    print("Saved:", summary_path)

    print("\nInput:", merged_csv)
    print("Total rows:", len(df))
    summarize(normal_losses, "NORMAL BUT LOSS")
    summarize(caution_wins, "CAUTION BUT WIN")
    summarize(caution_losses, "CAUTION AND LOSS")
    summarize(normal_wins, "NORMAL AND WIN")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
