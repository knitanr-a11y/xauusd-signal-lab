from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Callable

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_LEDGER_CSV = PROJECT_ROOT / "data" / "results" / "ai_reviews" / "ai_review_case_db_test_001_ledger.csv"
DEFAULT_OUT_CSV = PROJECT_ROOT / "data" / "results" / "ai_reviews" / "ai_review_filter_rule_summary.csv"
DEFAULT_DETAIL_CSV = PROJECT_ROOT / "data" / "results" / "ai_reviews" / "ai_review_filter_rule_detail.csv"

RuleFunc = Callable[[pd.DataFrame], pd.Series]


def resolve_path(path: Path) -> Path:
    return path if path.is_absolute() else PROJECT_ROOT / path


def read_ledger(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    df = pd.read_csv(path)
    if df.empty:
        raise ValueError(f"Ledger is empty: {path}")

    required = [
        "source_row",
        "signal_model",
        "side",
        "winning_pattern_match",
        "losing_pattern_similarity",
        "final_risk_label",
        "actual_result",
        "actual_r",
    ]
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"Ledger missing required columns: {missing}")

    if "recorded_at" in df.columns:
        df["recorded_at"] = pd.to_datetime(df["recorded_at"], errors="coerce")
    else:
        df["recorded_at"] = pd.NaT

    df["source_row"] = pd.to_numeric(df["source_row"], errors="coerce")
    df["actual_r_num"] = pd.to_numeric(df["actual_r"], errors="coerce")

    for col in ["signal_model", "side", "winning_pattern_match", "losing_pattern_similarity", "final_risk_label", "actual_result"]:
        df[col] = df[col].astype(str).str.strip()

    df = df.dropna(subset=["source_row"]).copy()
    df["source_row"] = df["source_row"].astype(int)
    return df


def dedupe_latest_by_source_row(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["_ledger_order"] = range(len(out))
    out = out.sort_values(["source_row", "recorded_at", "_ledger_order"], kind="mergesort")
    return out.groupby("source_row", as_index=False, dropna=False).tail(1).drop(columns=["_ledger_order"]).reset_index(drop=True)


def profit_factor(r: pd.Series) -> float | None:
    wins = r[r > 0]
    losses = r[r < 0]
    gross_win = float(wins.sum()) if len(wins) else 0.0
    gross_loss_abs = float(abs(losses.sum())) if len(losses) else 0.0
    if gross_loss_abs <= 0:
        return None
    return gross_win / gross_loss_abs


def max_consecutive_losses(results: pd.Series) -> int:
    max_streak = 0
    streak = 0
    for value in results.astype(str).str.lower():
        if value == "loss":
            streak += 1
            max_streak = max(max_streak, streak)
        else:
            streak = 0
    return max_streak


def summarize_selection(df: pd.DataFrame, selected: pd.DataFrame, *, rule_name: str, description: str) -> dict[str, object]:
    r = selected["actual_r_num"].dropna()
    wins = int((r > 0).sum())
    losses = int((r < 0).sum())
    total = int(len(r))
    total_r = float(r.sum()) if total else 0.0
    all_count = int(len(df))
    all_r = df["actual_r_num"].dropna()
    all_total_r = float(all_r.sum()) if len(all_r) else 0.0

    return {
        "rule_name": rule_name,
        "description": description,
        "selected_count": int(len(selected)),
        "selected_with_actual_r": total,
        "coverage": int(len(selected)) / all_count if all_count else None,
        "wins": wins,
        "losses": losses,
        "win_rate": wins / total if total else None,
        "total_r": total_r,
        "avg_r": total_r / total if total else None,
        "pf": profit_factor(r),
        "max_consecutive_losses": max_consecutive_losses(selected["actual_result"]) if len(selected) else 0,
        "all_total_r": all_total_r,
        "r_vs_all": total_r - all_total_r,
        "excluded_count": all_count - int(len(selected)),
        "excluded_total_r": all_total_r - total_r,
    }


def build_rules() -> list[tuple[str, str, RuleFunc]]:
    return [
        (
            "all_trades",
            "全AIレビュー対象を採用。AIフィルターなしの基準値。",
            lambda d: pd.Series(True, index=d.index),
        ),
        (
            "normal_only",
            "final_risk_label が normal のみ採用。高信頼通知候補。",
            lambda d: d["final_risk_label"].eq("normal"),
        ),
        (
            "normal_or_high_win_match",
            "normal または winning_pattern_match=high を採用。AIが勝ちパターン類似を高く見たものを重視。",
            lambda d: d["final_risk_label"].eq("normal") | d["winning_pattern_match"].eq("high"),
        ),
        (
            "high_win_match_only",
            "winning_pattern_match=high のみ採用。final_risk_label が caution でも勝ち類似が強ければ採用。",
            lambda d: d["winning_pattern_match"].eq("high"),
        ),
        (
            "exclude_loss_similarity_high",
            "losing_pattern_similarity=high を除外。それ以外を採用。",
            lambda d: ~d["losing_pattern_similarity"].eq("high"),
        ),
        (
            "exclude_medium_high_caution",
            "medium/high/caution を除外。それ以外を採用。少数だが悪かった組み合わせの検証用。",
            lambda d: ~(
                d["winning_pattern_match"].eq("medium")
                & d["losing_pattern_similarity"].eq("high")
                & d["final_risk_label"].eq("caution")
            ),
        ),
        (
            "normal_or_high_caution",
            "normal、または high/medium/caution を採用。高信頼normalと勝ち類似highのcautionだけを残す。",
            lambda d: d["final_risk_label"].eq("normal")
            | (
                d["winning_pattern_match"].eq("high")
                & d["losing_pattern_similarity"].eq("medium")
                & d["final_risk_label"].eq("caution")
            ),
        ),
        (
            "not_strong_caution",
            "strong_caution 以外を採用。強注意だけを除外した場合。",
            lambda d: ~d["final_risk_label"].eq("strong_caution"),
        ),
        (
            "source_side_best_seen",
            "現時点で強めの source/side を採用: A SELL, B BUY, B SELL, C BUY, C2 SELL。A BUYだけ除外する検証。",
            lambda d: (
                (d["signal_model"].eq("A") & d["side"].eq("SELL"))
                | (d["signal_model"].eq("B") & d["side"].eq("BUY"))
                | (d["signal_model"].eq("B") & d["side"].eq("SELL"))
                | (d["signal_model"].eq("C") & d["side"].eq("BUY"))
                | (d["signal_model"].eq("C2") & d["side"].eq("SELL"))
            ),
        ),
        (
            "source_side_best_seen_and_ai_high_or_normal",
            "強めの source/side の中で normal または winning_pattern_match=high のみ採用。かなり絞る検証。",
            lambda d: (
                (
                    (d["signal_model"].eq("A") & d["side"].eq("SELL"))
                    | (d["signal_model"].eq("B") & d["side"].eq("BUY"))
                    | (d["signal_model"].eq("B") & d["side"].eq("SELL"))
                    | (d["signal_model"].eq("C") & d["side"].eq("BUY"))
                    | (d["signal_model"].eq("C2") & d["side"].eq("SELL"))
                )
                & (d["final_risk_label"].eq("normal") | d["winning_pattern_match"].eq("high"))
            ),
        ),
    ]


def apply_rules(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    summary_rows: list[dict[str, object]] = []
    detail_rows: list[dict[str, object]] = []

    for rule_name, description, func in build_rules():
        mask = func(df).fillna(False)
        selected = df[mask].copy()
        summary_rows.append(summarize_selection(df, selected, rule_name=rule_name, description=description))

        for _, row in selected.iterrows():
            detail_rows.append(
                {
                    "rule_name": rule_name,
                    "source_row": row.get("source_row"),
                    "signal_model": row.get("signal_model"),
                    "side": row.get("side"),
                    "jst_entry_time": row.get("jst_entry_time", ""),
                    "winning_pattern_match": row.get("winning_pattern_match"),
                    "losing_pattern_similarity": row.get("losing_pattern_similarity"),
                    "final_risk_label": row.get("final_risk_label"),
                    "actual_result": row.get("actual_result"),
                    "actual_r": row.get("actual_r_num"),
                }
            )

    summary = pd.DataFrame(summary_rows)
    summary = summary.sort_values(["total_r", "pf", "selected_count"], ascending=[False, False, False], kind="mergesort")
    detail = pd.DataFrame(detail_rows)
    return summary, detail


def write_csv(path: Path, df: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig", quoting=csv.QUOTE_MINIMAL)


def print_table(title: str, df: pd.DataFrame) -> None:
    print("\n" + "=" * 120)
    print(title)
    print("=" * 120)
    if df.empty:
        print("No data.")
        return
    print(df.to_string(index=False))


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze virtual trade adoption rules from AI review ledger.")
    parser.add_argument("--ledger-csv", type=Path, default=DEFAULT_LEDGER_CSV)
    parser.add_argument("--out-csv", type=Path, default=DEFAULT_OUT_CSV)
    parser.add_argument("--detail-csv", type=Path, default=DEFAULT_DETAIL_CSV)
    parser.add_argument("--dedupe", choices=["source_row", "none"], default="source_row")
    args = parser.parse_args()

    ledger_csv = resolve_path(args.ledger_csv)
    out_csv = resolve_path(args.out_csv)
    detail_csv = resolve_path(args.detail_csv)

    raw = read_ledger(ledger_csv)
    df = dedupe_latest_by_source_row(raw) if args.dedupe == "source_row" else raw.copy()
    df = df.dropna(subset=["actual_r_num"]).copy()
    df = df.sort_values("source_row", kind="mergesort").reset_index(drop=True)

    summary, detail = apply_rules(df)
    write_csv(out_csv, summary)
    write_csv(detail_csv, detail)

    all_source_rows = sorted(df["source_row"].astype(int).unique().tolist())
    missing_in_0_215 = [i for i in range(216) if i not in set(all_source_rows)]

    print("Ledger:", ledger_csv)
    print("Raw ledger rows:", len(raw))
    print("Used rows:", len(df), f"dedupe={args.dedupe}")
    print("Source row min/max:", min(all_source_rows) if all_source_rows else None, max(all_source_rows) if all_source_rows else None)
    print("Missing source_rows in 0-215:", missing_in_0_215)
    print("Saved rule summary:", out_csv)
    print("Saved rule detail:", detail_csv)

    display_cols = [
        "rule_name",
        "selected_count",
        "coverage",
        "wins",
        "losses",
        "win_rate",
        "total_r",
        "avg_r",
        "pf",
        "max_consecutive_losses",
        "excluded_count",
        "excluded_total_r",
    ]
    print_table("AI REVIEW VIRTUAL FILTER RULE SUMMARY", summary[display_cols])

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
