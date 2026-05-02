from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_EDGE_CSV = PROJECT_ROOT / "data" / "results" / "ai_reviews" / "ai_review_caution_wins.csv"
DEFAULT_ALL_MERGED_CSV = PROJECT_ROOT / "data" / "results" / "ai_reviews" / "ai_review_outcomes_merged_latest.csv"
DEFAULT_OUT_DIR = PROJECT_ROOT / "data" / "results" / "ai_reviews"

BUCKET_RULE_COLUMNS = [
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
    "jst_entry_hour",
    "entry_risk_atr_ratio",
    "entry_spread_price_atr_ratio",
    "h1_ema_alignment",
    "m15_ema_alignment",
    "side_matches_h1_ema",
    "side_matches_m15_ema",
    "h1_macd_hist_supports_side",
    "h1_macd_hist_delta_supports_side",
    "h1_macd_hist_delta3_supports_side",
    "m15_macd_hist_supports_side",
    "m15_macd_hist_delta_supports_side",
    "m15_macd_hist_delta3_supports_side",
    "m15_recent_pushback_against_side",
    "m15_recent_momentum_supports_side",
    "m15_close_change_3_atr",
    "m15_pullback_from_high_5_atr",
    "m15_rebound_from_low_5_atr",
    "m15_upper_wick_ratio_3",
    "m15_lower_wick_ratio_3",
    "evidence_for_entry",
    "evidence_against_entry",
    "human_checkpoints",
]


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    df = pd.read_csv(path)
    if df.empty:
        return df
    for col in ["r", "entry_risk_atr_ratio", "entry_spread_price_atr_ratio", "m15_close_change_3_atr", "m15_pullback_from_high_5_atr", "m15_rebound_from_low_5_atr", "m15_upper_wick_ratio_3", "m15_lower_wick_ratio_3"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def safe_bool_eq(row: pd.Series, col: str, value: str) -> bool:
    return str(row.get(col, "")).lower() == value


def classify_caution_quality(row: pd.Series) -> tuple[str, str]:
    """Classify caution wins into actionable sub-buckets.

    The labels are intentionally conservative. They are not trade decisions.
    """
    win_match = str(row.get("winning_pattern_match", ""))
    loss_sim = str(row.get("losing_pattern_similarity", ""))

    h1_ema_ok = safe_bool_eq(row, "side_matches_h1_ema", "yes")
    m15_ema_ok = safe_bool_eq(row, "side_matches_m15_ema", "yes")
    h1_macd_ok = safe_bool_eq(row, "h1_macd_hist_supports_side", "yes") or safe_bool_eq(row, "h1_macd_hist_delta3_supports_side", "yes")
    m15_macd_ok = safe_bool_eq(row, "m15_macd_hist_supports_side", "yes") or safe_bool_eq(row, "m15_macd_hist_delta3_supports_side", "yes")
    pushback = safe_bool_eq(row, "m15_recent_pushback_against_side", "yes")
    momentum_ok = safe_bool_eq(row, "m15_recent_momentum_supports_side", "yes")

    risk_atr = row.get("entry_risk_atr_ratio")
    risk_ok = pd.notna(risk_atr) and float(risk_atr) <= 3.0
    risk_high = pd.notna(risk_atr) and float(risk_atr) >= 4.0

    # Tier 1: AI was cautious, but the setup is mostly aligned and the caution is likely mild.
    if win_match == "high" and loss_sim in {"low", "medium"} and h1_ema_ok and m15_ema_ok and (h1_macd_ok or m15_macd_ok) and not pushback and risk_ok:
        return "caution_but_tradeable_like", "High win match, not high loss similarity, EMA aligned, no recent pushback, risk/ATR not high."

    # Tier 2: likely still okay, but needs a human checkpoint.
    if win_match == "high" and loss_sim in {"low", "medium"} and h1_ema_ok and m15_ema_ok and not risk_high:
        reasons = []
        if pushback:
            reasons.append("recent pushback exists")
        if not h1_macd_ok:
            reasons.append("H1 MACD support is weak")
        if not m15_macd_ok:
            reasons.append("M15 MACD support is weak")
        if not momentum_ok:
            reasons.append("recent 3-candle momentum is not clearly supportive")
        reason = "; ".join(reasons) if reasons else "Mostly aligned but AI still found caution evidence."
        return "caution_needs_checkpoint", reason

    # Tier 3: caution is probably meaningful even though the trade won historically.
    if loss_sim == "medium" or risk_high or pushback or not h1_ema_ok or not m15_ema_ok:
        reasons = []
        if loss_sim == "medium":
            reasons.append("loss similarity is medium")
        if risk_high:
            reasons.append("risk/ATR is high")
        if pushback:
            reasons.append("recent pushback exists")
        if not h1_ema_ok:
            reasons.append("H1 EMA is not aligned")
        if not m15_ema_ok:
            reasons.append("M15 EMA is not aligned")
        return "caution_meaningful_but_won", "; ".join(reasons)

    return "caution_unclassified", "Did not match a specific caution sub-pattern."


def add_caution_bucket(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    out = df.copy()
    classified = out.apply(classify_caution_quality, axis=1)
    out["caution_bucket"] = [x[0] for x in classified]
    out["caution_bucket_reason"] = [x[1] for x in classified]
    return out


def safe_select(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    cols = [col for col in columns if col in df.columns]
    return df[cols].copy()


def summarize_bucket(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["caution_bucket", "rows", "wins", "losses", "total_r", "avg_r"])
    rows = []
    for bucket, group in df.groupby("caution_bucket", dropna=False):
        wins = int((group.get("result") == "win").sum()) if "result" in group.columns else 0
        losses = int((group.get("result") == "loss").sum()) if "result" in group.columns else 0
        total_r = float(group["r"].sum()) if "r" in group.columns else 0.0
        rows.append(
            {
                "caution_bucket": bucket,
                "rows": len(group),
                "wins": wins,
                "losses": losses,
                "total_r": total_r,
                "avg_r": total_r / len(group) if len(group) else 0.0,
            }
        )
    return pd.DataFrame(rows).sort_values(["caution_bucket"], kind="mergesort")


def summarize_feature_counts(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["feature", "value", "rows"])
    rows = []
    features = [
        "winning_pattern_match",
        "losing_pattern_similarity",
        "case_model",
        "case_side",
        "side_matches_h1_ema",
        "side_matches_m15_ema",
        "h1_macd_hist_supports_side",
        "h1_macd_hist_delta3_supports_side",
        "m15_macd_hist_supports_side",
        "m15_macd_hist_delta3_supports_side",
        "m15_recent_pushback_against_side",
        "m15_recent_momentum_supports_side",
    ]
    for feature in features:
        if feature not in df.columns:
            continue
        for value, group in df.groupby(feature, dropna=False):
            rows.append({"feature": feature, "value": value, "rows": len(group)})
    return pd.DataFrame(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze caution-winning AI review cases.")
    parser.add_argument("--caution-wins-csv", type=Path, default=DEFAULT_EDGE_CSV)
    parser.add_argument("--merged-csv", type=Path, default=DEFAULT_ALL_MERGED_CSV, help="Optional full merged file for comparing caution wins/losses.")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    args = parser.parse_args()

    caution_wins_csv = args.caution_wins_csv if args.caution_wins_csv.is_absolute() else PROJECT_ROOT / args.caution_wins_csv
    merged_csv = args.merged_csv if args.merged_csv.is_absolute() else PROJECT_ROOT / args.merged_csv
    out_dir = args.out_dir if args.out_dir.is_absolute() else PROJECT_ROOT / args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    caution_wins = add_caution_bucket(read_csv(caution_wins_csv))

    detailed_out = out_dir / "ai_review_caution_wins_bucketed.csv"
    summary_out = out_dir / "ai_review_caution_wins_bucket_summary.csv"
    feature_counts_out = out_dir / "ai_review_caution_wins_feature_counts.csv"

    output_cols = ["caution_bucket", "caution_bucket_reason"] + BUCKET_RULE_COLUMNS
    safe_select(caution_wins, output_cols).to_csv(detailed_out, index=False, encoding="utf-8-sig")
    summary = summarize_bucket(caution_wins)
    feature_counts = summarize_feature_counts(caution_wins)
    summary.to_csv(summary_out, index=False, encoding="utf-8-sig")
    feature_counts.to_csv(feature_counts_out, index=False, encoding="utf-8-sig")

    print("Input caution wins:", caution_wins_csv)
    print("Rows:", len(caution_wins))
    print("Saved bucketed detail:", detailed_out)
    print("Saved bucket summary:", summary_out)
    print("Saved feature counts:", feature_counts_out)

    print("\nSUMMARY BY CAUTION BUCKET")
    print(summary.to_string(index=False) if not summary.empty else "No data.")

    print("\nFEATURE COUNTS")
    print(feature_counts.to_string(index=False) if not feature_counts.empty else "No data.")

    if merged_csv.exists():
        merged = read_csv(merged_csv)
        caution_all = merged[merged["final_risk_label"] == "caution"].copy() if "final_risk_label" in merged.columns else pd.DataFrame()
        if not caution_all.empty:
            print("\nCAUTION ALL OUTCOME CHECK")
            print(
                caution_all.groupby(["result"], dropna=False).agg(
                    rows=("result", "size"),
                    total_r=("r", "sum"),
                ).reset_index().to_string(index=False)
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
