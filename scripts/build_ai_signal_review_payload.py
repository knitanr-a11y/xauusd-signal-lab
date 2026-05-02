from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_ENRICHED_CASES_CSV = PROJECT_ROOT / "data" / "results" / "ai_cases" / "xm_kiwami_gold_abc_v3_balanced_ai_cases_enriched.csv"
DEFAULT_OUT_DIR = PROJECT_ROOT / "data" / "results" / "ai_reviews"

# These columns are valid in historical cases as labels, but must not be used as current-signal inputs.
FUTURE_LABEL_COLUMNS = {
    "case_type",
    "case_reason",
    "result",
    "r",
    "exit_time",
    "exit_reason",
    "bars_held",
}

CURRENT_SIGNAL_COLUMNS = [
    "combined_signal_source",
    "side",
    "signal_time",
    "entry_time",
    "jst_entry_time",
    "jst_entry_month",
    "jst_entry_hour",
    "entry_price",
    "sl",
    "tp",
    "risk",
    "entry_risk_atr_ratio",
    "m15_spread_points",
    "m15_spread_price",
    "entry_spread_price_atr_ratio",
    "h1_feature_time",
    "h1_open",
    "h1_high",
    "h1_low",
    "h1_close",
    "h1_ema_alignment",
    "h1_close_ema20_gap_atr",
    "h1_ema20_ema50_gap_atr",
    "h1_ema50_ema200_gap_atr",
    "h1_close_position_20",
    "h1_range20_atr",
    "h1_macd_hist",
    "h1_macd_hist_delta",
    "m15_feature_time",
    "m15_open",
    "m15_high",
    "m15_low",
    "m15_close",
    "m15_ema_alignment",
    "m15_close_ema20_gap_atr",
    "m15_ema20_ema50_gap_atr",
    "m15_ema50_ema200_gap_atr",
    "m15_close_position_20",
    "m15_range20_atr",
    "m15_body_ratio",
    "m15_upper_wick_ratio",
    "m15_lower_wick_ratio",
    "m15_macd_line",
    "m15_macd_signal",
    "m15_macd_hist",
    "m15_macd_hist_delta",
    "side_matches_h1_ema",
    "side_matches_m15_ema",
    "macd_hist_supports_side",
    "macd_hist_delta_supports_side",
]

HISTORICAL_CASE_COLUMNS = [
    "case_type",
    "case_reason",
    "combined_signal_source",
    "side",
    "signal_time",
    "entry_time",
    "jst_entry_time",
    "jst_entry_hour",
    "entry_price",
    "sl",
    "tp",
    "risk",
    "entry_risk_atr_ratio",
    "m15_spread_points",
    "m15_spread_price",
    "entry_spread_price_atr_ratio",
    "h1_ema_alignment",
    "h1_close_ema20_gap_atr",
    "h1_range20_atr",
    "m15_ema_alignment",
    "m15_close_ema20_gap_atr",
    "m15_range20_atr",
    "m15_body_ratio",
    "m15_upper_wick_ratio",
    "m15_lower_wick_ratio",
    "m15_macd_hist",
    "m15_macd_hist_delta",
    "side_matches_h1_ema",
    "side_matches_m15_ema",
    "macd_hist_supports_side",
    "macd_hist_delta_supports_side",
    "result",
    "r",
    "exit_reason",
    "bars_held",
]

NUMERIC_SIMILARITY_COLUMNS = [
    "entry_risk_atr_ratio",
    "entry_spread_price_atr_ratio",
    "h1_close_ema20_gap_atr",
    "h1_range20_atr",
    "m15_close_ema20_gap_atr",
    "m15_range20_atr",
    "m15_body_ratio",
    "m15_upper_wick_ratio",
    "m15_lower_wick_ratio",
    "m15_macd_hist",
    "m15_macd_hist_delta",
]

CATEGORICAL_SIMILARITY_COLUMNS = [
    "h1_ema_alignment",
    "m15_ema_alignment",
    "side_matches_h1_ema",
    "side_matches_m15_ema",
    "macd_hist_supports_side",
    "macd_hist_delta_supports_side",
]


def to_jsonable(value: Any) -> Any:
    if pd.isna(value):
        return None
    if isinstance(value, pd.Timestamp):
        return value.isoformat(sep=" ")
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None if math.isnan(value) else str(value)
    return value


def row_to_dict(row: pd.Series, columns: list[str]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for col in columns:
        if col in row.index:
            out[col] = to_jsonable(row[col])
    return out


def prepare_cases(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    df = pd.read_csv(path)
    for col in ["signal_time", "entry_time", "jst_entry_time", "exit_time", "h1_feature_time", "m15_feature_time"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
    if "case_type" not in df.columns:
        raise ValueError("enriched cases CSV must contain case_type")
    if "combined_signal_source" not in df.columns:
        raise ValueError("enriched cases CSV must contain combined_signal_source")
    if "side" not in df.columns:
        raise ValueError("enriched cases CSV must contain side")
    return df.reset_index(drop=True)


def numeric_distance(current: pd.Series, other: pd.Series) -> float:
    dist = 0.0
    count = 0
    for col in NUMERIC_SIMILARITY_COLUMNS:
        if col not in current.index or col not in other.index:
            continue
        a = current[col]
        b = other[col]
        if pd.isna(a) or pd.isna(b):
            continue
        scale = max(abs(float(a)), abs(float(b)), 1.0)
        dist += min(abs(float(a) - float(b)) / scale, 3.0)
        count += 1
    return dist / count if count else 999.0


def categorical_bonus(current: pd.Series, other: pd.Series) -> float:
    score = 0.0
    for col in CATEGORICAL_SIMILARITY_COLUMNS:
        if col in current.index and col in other.index and not pd.isna(current[col]) and not pd.isna(other[col]):
            if str(current[col]) == str(other[col]):
                score -= 0.08
            else:
                score += 0.08
    return score


def hour_distance(current: pd.Series, other: pd.Series) -> float:
    if "jst_entry_hour" not in current.index or "jst_entry_hour" not in other.index:
        return 0.0
    if pd.isna(current["jst_entry_hour"]) or pd.isna(other["jst_entry_hour"]):
        return 0.0
    a = int(current["jst_entry_hour"])
    b = int(other["jst_entry_hour"])
    raw = abs(a - b)
    wrapped = min(raw, 24 - raw)
    return wrapped / 12.0


def similarity_score(current: pd.Series, other: pd.Series) -> float:
    score = numeric_distance(current, other)
    score += categorical_bonus(current, other)
    score += 0.20 * hour_distance(current, other)
    return float(score)


def select_similar_cases(
    cases: pd.DataFrame,
    current: pd.Series,
    case_type: str,
    limit: int,
) -> pd.DataFrame:
    source = str(current.get("combined_signal_source", ""))
    side = str(current.get("side", ""))

    candidates = cases[cases["case_type"] == case_type].copy()
    if candidates.empty:
        return candidates

    # Primary filter: same model and same side.
    same_model_side = candidates[
        (candidates["combined_signal_source"].astype(str) == source)
        & (candidates["side"].astype(str) == side)
    ].copy()

    if len(same_model_side) >= max(1, limit):
        candidates = same_model_side
    else:
        # Fallback: same model OR same side, but keep lower relevance visible.
        candidates = candidates[
            (candidates["combined_signal_source"].astype(str) == source)
            | (candidates["side"].astype(str) == side)
        ].copy()

    if candidates.empty:
        return candidates

    candidates["similarity_score"] = candidates.apply(lambda row: similarity_score(current, row), axis=1)
    return candidates.sort_values("similarity_score", kind="mergesort").head(limit).reset_index(drop=True)


def build_prompt_text() -> str:
    return """You are evaluating a trading signal for XAUUSD/GOLD.

Important rules:
- The rule-based signal already passed the backtest logic. Treat it as having baseline expectancy.
- Do not make the final trade decision. Provide risk review only.
- First compare the current signal to similar winning historical cases.
- Then compare it to similar losing historical cases.
- Do not over-penalize the signal just because one losing case has a shared feature.
- Return JSON only.
- Use only current_signal_snapshot for the current signal. Historical case result/r/exit fields are labels only.
- For spread, use entry_spread_price_atr_ratio. Do not use deprecated point/ATR ratios.
- Do not output skip_candidate unless winning_pattern_match is low and losing_pattern_similarity is high with multiple supporting reasons.

Required output JSON schema:
{
  "winning_pattern_match": "high | medium | low",
  "losing_pattern_similarity": "high | medium | low",
  "final_risk_label": "normal | caution | strong_caution | skip_candidate",
  "evidence_for_entry": ["..."],
  "evidence_against_entry": ["..."],
  "closest_win_case_notes": ["..."],
  "closest_loss_case_notes": ["..."],
  "human_checkpoints": ["..."],
  "do_not_use_as_final_trade_decision": true
}
"""


def build_payload(
    cases: pd.DataFrame,
    current_index: int,
    win_limit: int,
    loss_limit: int,
) -> dict[str, Any]:
    if current_index < 0 or current_index >= len(cases):
        raise IndexError(f"current-index out of range: {current_index}. rows={len(cases)}")

    current = cases.iloc[current_index]
    similar_wins = select_similar_cases(cases, current, "win_pattern", win_limit)
    similar_losses = select_similar_cases(cases, current, "loss_pattern", loss_limit)

    current_signal = row_to_dict(current, CURRENT_SIGNAL_COLUMNS)
    leaked = sorted([col for col in FUTURE_LABEL_COLUMNS if col in current_signal])
    if leaked:
        raise RuntimeError(f"current signal leaked future/label columns: {leaked}")

    payload = {
        "metadata": {
            "project": "xauusd-signal-lab",
            "broker_profile": "XM KIWAMI",
            "symbol": "GOLD# / goldsharp",
            "preset": "xm_kiwami_gold_abc_v3",
            "mode": "shadow_review_payload_example",
            "current_case_source_row": int(current_index),
            "warning": "This payload is for AI risk review, not final trade execution.",
        },
        "ai_task": build_prompt_text(),
        "current_signal_snapshot": current_signal,
        "similar_winning_cases": [row_to_dict(row, HISTORICAL_CASE_COLUMNS) for _, row in similar_wins.iterrows()],
        "similar_losing_cases": [row_to_dict(row, HISTORICAL_CASE_COLUMNS) for _, row in similar_losses.iterrows()],
        "guardrails": {
            "respect_rule_based_signal_expectancy": True,
            "do_not_use_historical_labels_as_current_features": True,
            "skip_candidate_requires_multiple_strong_reasons": True,
            "caution_does_not_mean_skip": True,
            "output_json_only": True,
        },
    }
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Build an AI review payload for one signal snapshot.")
    parser.add_argument("--cases-csv", type=Path, default=DEFAULT_ENRICHED_CASES_CSV)
    parser.add_argument("--current-index", type=int, default=0, help="Row index from enriched cases to use as sample current signal.")
    parser.add_argument("--win-limit", type=int, default=5)
    parser.add_argument("--loss-limit", type=int, default=5)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    args = parser.parse_args()

    cases_csv = args.cases_csv if args.cases_csv.is_absolute() else PROJECT_ROOT / args.cases_csv
    out_dir = args.out_dir if args.out_dir.is_absolute() else PROJECT_ROOT / args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    cases = prepare_cases(cases_csv)
    payload = build_payload(cases, args.current_index, args.win_limit, args.loss_limit)

    out_json = out_dir / f"ai_signal_review_payload_row_{args.current_index}.json"
    out_prompt = out_dir / f"ai_signal_review_prompt_row_{args.current_index}.txt"

    out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    out_prompt.write_text(
        payload["ai_task"]
        + "\n\nPAYLOAD_JSON:\n"
        + json.dumps(payload, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )

    current = payload["current_signal_snapshot"]
    print("Cases loaded:", len(cases), cases_csv)
    print("Current row:", args.current_index)
    print("Current model/side/time:", current.get("combined_signal_source"), current.get("side"), current.get("jst_entry_time"))
    print("Similar win cases:", len(payload["similar_winning_cases"]))
    print("Similar loss cases:", len(payload["similar_losing_cases"]))
    print("Saved JSON:", out_json)
    print("Saved prompt:", out_prompt)

    print("\nCurrent signal snapshot preview:")
    preview_cols = [
        "combined_signal_source",
        "side",
        "jst_entry_hour",
        "entry_risk_atr_ratio",
        "entry_spread_price_atr_ratio",
        "h1_ema_alignment",
        "m15_ema_alignment",
        "side_matches_h1_ema",
        "side_matches_m15_ema",
        "macd_hist_supports_side",
        "macd_hist_delta_supports_side",
    ]
    for col in preview_cols:
        print(f"  {col}: {current.get(col)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
