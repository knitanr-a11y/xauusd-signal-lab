#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

YEARS = (2024, 2025, 2026)
SELECTION_YEARS = (2024, 2025)

FAMILIES = (
    "M5_H4|MOCHI_HIDDEN_PULLBACK|LONG|RR1_5",
    "M15_H4|MOCHI_HIDDEN_PULLBACK|LONG|RR1_5",
    "M15_H4|MOCHI_HIDDEN_PULLBACK|LONG|RR1_25",
    "M5_H4|MOCHI_EARLY_PULLBACK|SHORT|RR1_5",
    "M5_H4|SWEEP_RECLAIM_REVERSAL|SHORT|STRUCT_TARGET",
)

FILTER_PROFILES: dict[str, dict[str, Any]] = {
    "BASE": {},
    "QUALITY_GE_7_5": {"quality_min": 7.5},
    "QUALITY_GE_8_0": {"quality_min": 8.0},
    "QUALITY_GE_8_5": {"quality_min": 8.5},
    "ATR_RATIO_GE_1_0": {"atr_min": 1.0},
    "NO_ROUND_NUMBER": {"exclude_round_number": True},
    "RISK_ATR_LE_1_25": {"risk_atr_max": 1.25},
    "QUALITY_GE_8_AND_ATR_GE_1": {"quality_min": 8.0, "atr_min": 1.0},
    "QUALITY_GE_8_AND_NO_ROUND": {"quality_min": 8.0, "exclude_round_number": True},
    "ATR_GE_1_AND_NO_ROUND": {"atr_min": 1.0, "exclude_round_number": True},
    "EXTENSION_0_TO_0_8": {"extension_min": 0.0, "extension_max": 0.8},
    "QUALITY_GE_8_AND_EXT_0_TO_0_8": {
        "quality_min": 8.0,
        "extension_min": 0.0,
        "extension_max": 0.8,
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage311-json", required=True)
    parser.add_argument("--stage311-trades", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--selected-csv", required=True)
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def profit_factor(values: pd.Series) -> float | None:
    positive = float(values[values > 0].sum())
    negative = float(-values[values < 0].sum())
    if negative == 0.0:
        return None if positive > 0.0 else 0.0
    return positive / negative


def max_drawdown_r(values: pd.Series) -> float:
    if values.empty:
        return 0.0
    equity = values.cumsum()
    peak = equity.cummax().clip(lower=0.0)
    return float((peak - equity).max())


def largest_win_share(values: pd.Series) -> float:
    positives = values[values > 0]
    total = float(positives.sum())
    if total <= 0.0:
        return 0.0
    return float(positives.max() / total)


def max_consecutive_losses(values: pd.Series) -> int:
    best = 0
    current = 0
    for value in values:
        if float(value) < 0.0:
            current += 1
            best = max(best, current)
        else:
            current = 0
    return best


def summarize(frame: pd.DataFrame) -> dict[str, Any]:
    if frame.empty:
        return {
            "trades": 0,
            "wins": 0,
            "losses": 0,
            "win_rate": 0.0,
            "spread_adjusted_total_usd": 0.0,
            "spread_adjusted_profit_factor": 0.0,
            "spread_adjusted_total_r": 0.0,
            "spread_adjusted_max_drawdown_r": 0.0,
            "largest_win_share_of_positive_pnl": 0.0,
            "max_consecutive_losses": 0,
            "first_entry_dt": None,
            "last_exit_dt": None,
        }
    ordered = frame.sort_values(["entry_dt", "exit_dt"], kind="mergesort")
    pnl = ordered.spread_adjusted_pnl.astype(float)
    r_values = ordered.spread_adjusted_r.astype(float)
    wins = int((pnl > 0).sum())
    losses = int((pnl < 0).sum())
    return {
        "trades": int(len(ordered)),
        "wins": wins,
        "losses": losses,
        "win_rate": float(wins / len(ordered)),
        "spread_adjusted_total_usd": float(pnl.sum()),
        "spread_adjusted_profit_factor": profit_factor(pnl),
        "spread_adjusted_total_r": float(r_values.sum()),
        "spread_adjusted_max_drawdown_r": max_drawdown_r(r_values),
        "largest_win_share_of_positive_pnl": largest_win_share(pnl),
        "max_consecutive_losses": max_consecutive_losses(pnl),
        "first_entry_dt": str(ordered.entry_dt.min()),
        "last_exit_dt": str(ordered.exit_dt.max()),
    }


def pf_number(summary: dict[str, Any]) -> float:
    value = summary["spread_adjusted_profit_factor"]
    if value is None and summary["spread_adjusted_total_usd"] > 0.0:
        return float("inf")
    return float(value or 0.0)


def yearly(frame: pd.DataFrame) -> dict[str, Any]:
    return {
        str(year): summarize(frame[frame.entry_dt.dt.year.eq(year)])
        for year in YEARS
    }


def quarterly(frame: pd.DataFrame) -> dict[str, Any]:
    work = frame[frame.entry_dt.dt.year.isin(SELECTION_YEARS)].copy()
    if work.empty:
        return {}
    work["quarter"] = work.entry_dt.dt.to_period("Q").astype(str)
    return {
        quarter: summarize(part)
        for quarter, part in work.groupby("quarter", sort=True)
    }


def apply_profile(frame: pd.DataFrame, profile: dict[str, Any]) -> pd.DataFrame:
    result = frame.copy()
    if "quality_min" in profile:
        result = result[result.quality_score.ge(float(profile["quality_min"]))]
    if "atr_min" in profile:
        result = result[result.atr_ratio_signal.ge(float(profile["atr_min"]))]
    if "risk_atr_max" in profile:
        result = result[result.risk_atr.le(float(profile["risk_atr_max"]))]
    if profile.get("exclude_round_number"):
        result = result[~result.round_number_near.astype(bool)]
    if "extension_min" in profile:
        result = result[result.extension_atr_signal.ge(float(profile["extension_min"]))]
    if "extension_max" in profile:
        result = result[result.extension_atr_signal.le(float(profile["extension_max"]))]
    return result.copy()


def formal_gate(selection: dict[str, Any], by_year: dict[str, Any]) -> dict[str, Any]:
    minimum_count = min(int(by_year[str(year)]["trades"]) for year in SELECTION_YEARS)
    minimum_pf = min(pf_number(by_year[str(year)]) for year in SELECTION_YEARS)
    minimum_r = min(
        float(by_year[str(year)]["spread_adjusted_total_r"])
        for year in SELECTION_YEARS
    )
    passed = bool(
        selection["trades"] >= 30
        and minimum_count >= 10
        and minimum_pf >= 1.10
        and minimum_r > 0.0
        and pf_number(selection) >= 1.25
        and selection["spread_adjusted_total_r"] > 0.0
        and selection["spread_adjusted_max_drawdown_r"] <= 10.0
        and selection["largest_win_share_of_positive_pnl"] <= 0.40
    )
    robust_score = (
        10.0 * min(minimum_pf, 5.0)
        + float(selection["spread_adjusted_total_r"])
        + 0.05 * float(selection["trades"])
        - 0.75 * float(selection["spread_adjusted_max_drawdown_r"])
        - 5.0
        * max(0.0, float(selection["largest_win_share_of_positive_pnl"]) - 0.25)
    )
    return {
        "passed": passed,
        "minimum_year_count": minimum_count,
        "minimum_year_pf": minimum_pf,
        "minimum_year_r": minimum_r,
        "robust_score_2024_2025": float(robust_score),
    }


def stress_2026(summary: dict[str, Any]) -> dict[str, Any]:
    passed = bool(
        summary["trades"] >= 5
        and pf_number(summary) >= 1.10
        and summary["spread_adjusted_total_r"] > 0.0
        and summary["spread_adjusted_max_drawdown_r"] <= 6.0
    )
    return {
        "passed": passed,
        "clean_holdout": False,
        "reason": (
            "2026 outcomes were already visible in Stage311. This is an audit stress check, "
            "not a pristine holdout and not used to choose filters."
        ),
    }


def row_for_csv(frame: pd.DataFrame, family: str, profile_name: str) -> pd.DataFrame:
    result = frame.copy()
    result.insert(0, "stage312_profile", profile_name)
    result.insert(0, "stage312_family", family)
    for column in ("decision_dt", "entry_dt", "exit_dt"):
        if column in result.columns:
            result[column] = result[column].astype(str)
    return result


def main() -> int:
    args = parse_args()
    stage311_json = Path(args.stage311_json).expanduser().resolve()
    stage311_trades = Path(args.stage311_trades).expanduser().resolve()
    output = Path(args.output).expanduser().resolve()
    selected_csv = Path(args.selected_csv).expanduser().resolve()

    source = json.loads(stage311_json.read_text(encoding="utf-8"))
    if source.get("status") != "GOLD_V3_311_MOCHIPOYO_AND_INDEPENDENT_RESEARCH_READY":
        raise ValueError(f"STAGE311_STATUS_UNEXPECTED: {source.get('status')}")

    expected_sha = source.get("outputs", {}).get("all_trades_sha256")
    actual_sha = sha256_file(stage311_trades)
    if expected_sha and expected_sha != actual_sha:
        raise ValueError(
            f"STAGE311_TRADES_SHA_MISMATCH: expected={expected_sha} actual={actual_sha}"
        )

    trades = pd.read_csv(stage311_trades, encoding="utf-8-sig")
    required = {
        "family_key",
        "entry_dt",
        "exit_dt",
        "quality_score",
        "atr_ratio_signal",
        "extension_atr_signal",
        "round_number_near",
        "risk_price",
        "atr_entry",
        "spread_adjusted_pnl",
        "spread_adjusted_r",
    }
    missing = sorted(required - set(trades.columns))
    if missing:
        raise ValueError(f"STAGE311_TRADES_COLUMNS_MISSING: {missing}")

    trades["entry_dt"] = pd.to_datetime(trades.entry_dt, errors="raise")
    trades["exit_dt"] = pd.to_datetime(trades.exit_dt, errors="raise")
    trades["risk_atr"] = trades.risk_price / trades.atr_entry.replace(0.0, np.nan)

    evaluations: list[dict[str, Any]] = []
    selected_frames: dict[tuple[str, str], pd.DataFrame] = {}
    for family in FAMILIES:
        family_frame = trades[trades.family_key.eq(family)].copy()
        if family_frame.empty:
            continue
        for profile_name, profile in FILTER_PROFILES.items():
            filtered = apply_profile(family_frame, profile)
            selection_frame = filtered[
                filtered.entry_dt.dt.year.isin(SELECTION_YEARS)
            ].copy()
            selection_summary = summarize(selection_frame)
            yearly_summary = yearly(filtered)
            gate = formal_gate(selection_summary, yearly_summary)
            stress = stress_2026(yearly_summary["2026"])
            evaluations.append(
                {
                    "family_key": family,
                    "filter_profile": profile_name,
                    "filter_contract": profile,
                    "aggregate_all_years": summarize(filtered),
                    "selection_2024_2025": selection_summary,
                    "yearly": yearly_summary,
                    "quarterly_2024_2025": quarterly(filtered),
                    "formal_gate": gate,
                    "stress_2026": stress,
                }
            )
            selected_frames[(family, profile_name)] = filtered

    evaluations.sort(
        key=lambda row: (
            -int(row["formal_gate"]["passed"]),
            -float(row["formal_gate"]["robust_score_2024_2025"]),
            row["family_key"],
            row["filter_profile"],
        )
    )
    passing = [row for row in evaluations if row["formal_gate"]["passed"]]
    stress_supported = [row for row in passing if row["stress_2026"]["passed"]]
    best = passing[0] if passing else None

    selected_csv.parent.mkdir(parents=True, exist_ok=True)
    if best is not None:
        selected_frame = selected_frames[(best["family_key"], best["filter_profile"])]
        row_for_csv(selected_frame, best["family_key"], best["filter_profile"]).to_csv(
            selected_csv,
            index=False,
            encoding="utf-8-sig",
        )
    else:
        pd.DataFrame(
            columns=["stage312_family", "stage312_profile", "entry_dt", "exit_dt"]
        ).to_csv(selected_csv, index=False, encoding="utf-8-sig")

    report = {
        "status": "GOLD_V3_312_NEAR_MISS_REFINEMENT_COMPLETE",
        "mode": "AUDIT_ONLY_FIXED_GRID_REFINEMENT",
        "decision": (
            "RESEARCH_REFINEMENT_LEAD_FOUND"
            if passing
            else "NO_REFINED_RESEARCH_LEAD_FOUND"
        ),
        "source": {
            "stage311_json": str(stage311_json),
            "stage311_json_sha256": sha256_file(stage311_json),
            "stage311_trades": str(stage311_trades),
            "stage311_trades_sha256": actual_sha,
        },
        "selection_contract": {
            "selection_years": list(SELECTION_YEARS),
            "stress_year": 2026,
            "stress_year_is_not_pristine_holdout": True,
            "families": list(FAMILIES),
            "filter_profiles": FILTER_PROFILES,
            "formal_gate_unchanged_from_stage311": {
                "combined_trades": 30,
                "minimum_each_year": 10,
                "minimum_each_year_pf": 1.10,
                "minimum_each_year_r": "> 0",
                "combined_pf": 1.25,
                "combined_max_dd_r": 10.0,
                "largest_win_share": 0.40,
            },
        },
        "result_counts": {
            "evaluations": len(evaluations),
            "formal_passes": len(passing),
            "stress_supported_passes": len(stress_supported),
        },
        "best_research_lead": best,
        "formal_passes": passing,
        "stress_supported_passes": stress_supported,
        "leaderboard": evaluations,
        "interpretation": {
            "formal_pass_means": (
                "The fixed filter improves the Stage311 near-miss on 2024/2025 without changing "
                "the Stage311 gate. It remains research-only."
            ),
            "stress_failure_means": (
                "Do not promote. Keep the lead for further regime and rolling-window testing."
            ),
            "sweep_short_rule": (
                "A strong 2024/2025 result with 2026 collapse must be treated as regime-dependent, "
                "not as a production candidate."
            ),
        },
        "outputs": {
            "result_json": str(output),
            "selected_trades_csv": str(selected_csv),
            "selected_trades_sha256": sha256_file(selected_csv),
        },
        "promotion": {
            "performed": False,
            "stage307_candidate": "UNCHANGED_RETAINED",
            "stage292_candidate_pool_changed": False,
            "shadow_enabled": False,
        },
        "safety_flags": {
            "final_signal_changed": False,
            "mt5_order_enabled": False,
            "discord_enabled": False,
            "partial_close_enabled": False,
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
