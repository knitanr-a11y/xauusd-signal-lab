#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

PRIMARY_FAMILY = "M5_H4|MOCHI_HIDDEN_PULLBACK|LONG|RR1_5"
SECONDARY_FAMILY = "M5_H4|MOCHI_EARLY_PULLBACK|SHORT|RR1_5"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage312-json", required=True)
    parser.add_argument("--stage311-trades", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--combined-csv", required=True)
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize_bool(series: pd.Series) -> pd.Series:
    if pd.api.types.is_bool_dtype(series):
        return series.fillna(False)
    return (
        series.astype(str)
        .str.strip()
        .str.lower()
        .isin({"true", "1", "yes", "y"})
    )


def profit_factor(values: pd.Series) -> float | None:
    positive = float(values[values > 0].sum())
    negative = float(-values[values < 0].sum())
    if negative == 0.0:
        return None if positive > 0.0 else 0.0
    return positive / negative


def pf_number(summary: dict[str, Any]) -> float:
    value = summary["spread_adjusted_profit_factor"]
    if value is None and summary["spread_adjusted_total_usd"] > 0.0:
        return float("inf")
    return float(value or 0.0)


def max_drawdown_r(values: pd.Series) -> float:
    if values.empty:
        return 0.0
    equity = values.cumsum()
    peak = equity.cummax().clip(lower=0.0)
    return float((peak - equity).max())


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
            "first_entry_dt": None,
            "last_exit_dt": None,
        }
    ordered = frame.sort_values(["entry_dt", "exit_dt"], kind="mergesort")
    pnl = ordered.spread_adjusted_pnl.astype(float)
    r_values = ordered.spread_adjusted_r.astype(float)
    positives = pnl[pnl > 0]
    positive_sum = float(positives.sum())
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
        "largest_win_share_of_positive_pnl": (
            float(positives.max() / positive_sum) if positive_sum > 0.0 else 0.0
        ),
        "first_entry_dt": str(ordered.entry_dt.min()),
        "last_exit_dt": str(ordered.exit_dt.max()),
    }


def yearly(frame: pd.DataFrame) -> dict[str, Any]:
    return {
        str(year): summarize(frame[frame.entry_dt.dt.year.eq(year)])
        for year in (2024, 2025, 2026)
    }


def quarterly(frame: pd.DataFrame) -> dict[str, Any]:
    work = frame.copy()
    work["quarter"] = work.entry_dt.dt.to_period("Q").astype(str)
    return {
        quarter: summarize(part)
        for quarter, part in work.groupby("quarter", sort=True)
    }


def one_position(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    ordered = frame.sort_values(
        ["entry_dt", "stage313_priority", "exit_dt", "stage313_candidate"],
        kind="mergesort",
    )
    accepted_rows: list[pd.Series] = []
    rejected_rows: list[pd.Series] = []
    active_exit: pd.Timestamp | None = None
    for _, row in ordered.iterrows():
        if active_exit is None or row.entry_dt >= active_exit:
            accepted_rows.append(row)
            active_exit = row.exit_dt
        else:
            rejected_rows.append(row)
    return pd.DataFrame(accepted_rows), pd.DataFrame(rejected_rows)


def overlap_diagnostics(left: pd.DataFrame, right: pd.DataFrame) -> dict[str, Any]:
    exact = set(left.entry_dt) & set(right.entry_dt)
    interval_pairs = 0
    left_with_overlap = 0
    for row in left.itertuples():
        mask = right.entry_dt.lt(row.exit_dt) & right.exit_dt.gt(row.entry_dt)
        count = int(mask.sum())
        interval_pairs += count
        if count:
            left_with_overlap += 1
    return {
        "exact_entry_overlap": int(len(exact)),
        "overlapping_interval_pairs": int(interval_pairs),
        "primary_trades_with_any_overlap": int(left_with_overlap),
    }


def rolling_six_months(frame: pd.DataFrame) -> list[dict[str, Any]]:
    if frame.empty:
        return []
    start = frame.entry_dt.min().to_period("M").to_timestamp()
    last = frame.entry_dt.max().to_period("M").to_timestamp()
    rows: list[dict[str, Any]] = []
    cursor = start
    while cursor <= last:
        end = cursor + pd.DateOffset(months=6)
        part = frame[frame.entry_dt.ge(cursor) & frame.entry_dt.lt(end)]
        if len(part) >= 3:
            rows.append(
                {
                    "start": str(cursor),
                    "end_exclusive": str(end),
                    "summary": summarize(part),
                }
            )
        cursor = cursor + pd.DateOffset(months=1)
    return rows


def rolling_diagnostics(windows: list[dict[str, Any]]) -> dict[str, Any]:
    if not windows:
        return {
            "window_count": 0,
            "positive_r_ratio": 0.0,
            "pf_ge_1_10_ratio": 0.0,
            "worst_window_r": 0.0,
        }
    positive = sum(
        row["summary"]["spread_adjusted_total_r"] > 0.0 for row in windows
    )
    pf_ok = sum(pf_number(row["summary"]) >= 1.10 for row in windows)
    return {
        "window_count": len(windows),
        "positive_r_ratio": float(positive / len(windows)),
        "pf_ge_1_10_ratio": float(pf_ok / len(windows)),
        "worst_window_r": float(
            min(row["summary"]["spread_adjusted_total_r"] for row in windows)
        ),
    }


def quarter_fragility(frame: pd.DataFrame) -> dict[str, Any]:
    selection = frame[frame.entry_dt.dt.year.isin([2024, 2025])].copy()
    by_quarter = quarterly(selection)
    positive_quarters = [
        (quarter, row)
        for quarter, row in by_quarter.items()
        if row["spread_adjusted_total_r"] > 0.0
    ]
    total_positive_r = sum(
        row["spread_adjusted_total_r"] for _, row in positive_quarters
    )
    best_quarter = max(
        by_quarter.items(),
        key=lambda item: item[1]["spread_adjusted_total_r"],
    )
    best_name = best_quarter[0]
    without_best = selection[
        selection.entry_dt.dt.to_period("Q").astype(str).ne(best_name)
    ]
    leave_one_out: dict[str, Any] = {}
    for quarter in by_quarter:
        part = selection[
            selection.entry_dt.dt.to_period("Q").astype(str).ne(quarter)
        ]
        leave_one_out[quarter] = summarize(part)
    return {
        "quarter_count": len(by_quarter),
        "positive_quarter_count": len(positive_quarters),
        "positive_quarter_ratio": (
            float(len(positive_quarters) / len(by_quarter)) if by_quarter else 0.0
        ),
        "best_quarter": best_name,
        "best_quarter_r": float(best_quarter[1]["spread_adjusted_total_r"]),
        "best_quarter_share_of_positive_quarter_r": (
            float(best_quarter[1]["spread_adjusted_total_r"] / total_positive_r)
            if total_positive_r > 0.0
            else 0.0
        ),
        "selection_without_best_quarter": summarize(without_best),
        "leave_one_quarter_out": leave_one_out,
    }


def adjacent_profile_stability(stage312: dict[str, Any]) -> dict[str, Any]:
    relevant = [
        row
        for row in stage312.get("leaderboard", [])
        if row.get("family_key") == PRIMARY_FAMILY
        and row.get("filter_profile")
        in {"BASE", "QUALITY_GE_7_5", "QUALITY_GE_8_0", "QUALITY_GE_8_5"}
    ]
    return {
        "profiles_checked": len(relevant),
        "formal_passes": sum(
            bool(row.get("formal_gate", {}).get("passed")) for row in relevant
        ),
        "profiles": [
            {
                "filter_profile": row.get("filter_profile"),
                "selection_trades": row.get("selection_2024_2025", {}).get("trades"),
                "selection_pf": row.get("selection_2024_2025", {}).get(
                    "spread_adjusted_profit_factor"
                ),
                "selection_r": row.get("selection_2024_2025", {}).get(
                    "spread_adjusted_total_r"
                ),
                "selection_dd_r": row.get("selection_2024_2025", {}).get(
                    "spread_adjusted_max_drawdown_r"
                ),
                "formal_pass": row.get("formal_gate", {}).get("passed"),
            }
            for row in relevant
        ],
    }


def main() -> int:
    args = parse_args()
    stage312_path = Path(args.stage312_json).expanduser().resolve()
    trades_path = Path(args.stage311_trades).expanduser().resolve()
    output = Path(args.output).expanduser().resolve()
    combined_csv = Path(args.combined_csv).expanduser().resolve()

    stage312 = json.loads(stage312_path.read_text(encoding="utf-8"))
    if stage312.get("status") != "GOLD_V3_312_NEAR_MISS_REFINEMENT_COMPLETE":
        raise ValueError(f"STAGE312_STATUS_UNEXPECTED: {stage312.get('status')}")

    expected_trades_sha = stage312.get("source", {}).get("stage311_trades_sha256")
    actual_trades_sha = sha256_file(trades_path)
    if expected_trades_sha and expected_trades_sha != actual_trades_sha:
        raise ValueError(
            f"STAGE311_TRADES_SHA_MISMATCH: expected={expected_trades_sha} actual={actual_trades_sha}"
        )

    trades = pd.read_csv(trades_path, encoding="utf-8-sig")
    trades["entry_dt"] = pd.to_datetime(trades.entry_dt, errors="raise")
    trades["exit_dt"] = pd.to_datetime(trades.exit_dt, errors="raise")
    trades["round_number_near"] = normalize_bool(trades.round_number_near)

    primary = trades[
        trades.family_key.eq(PRIMARY_FAMILY) & trades.quality_score.ge(8.0)
    ].copy()
    primary["stage313_candidate"] = "PRIMARY_FORMAL_PASS_LONG"
    primary["stage313_priority"] = 10

    secondary = trades[
        trades.family_key.eq(SECONDARY_FAMILY)
        & trades.atr_ratio_signal.ge(1.0)
        & (~trades.round_number_near)
    ].copy()
    secondary["stage313_candidate"] = "SECONDARY_LOW_FREQUENCY_SHORT"
    secondary["stage313_priority"] = 20

    merged_raw = pd.concat([primary, secondary], ignore_index=True)
    combined, rejected = one_position(merged_raw)

    combined_csv.parent.mkdir(parents=True, exist_ok=True)
    csv_frame = combined.copy()
    for column in ("decision_dt", "entry_dt", "exit_dt"):
        if column in csv_frame.columns:
            csv_frame[column] = csv_frame[column].astype(str)
    csv_frame.to_csv(combined_csv, index=False, encoding="utf-8-sig")

    primary_windows = rolling_six_months(primary)
    secondary_windows = rolling_six_months(secondary)
    combined_windows = rolling_six_months(combined)

    primary_fragility = quarter_fragility(primary)
    primary_yearly = yearly(primary)
    secondary_yearly = yearly(secondary)
    combined_yearly = yearly(combined)

    primary_retain = bool(
        stage312.get("best_research_lead", {}).get("formal_gate", {}).get("passed")
        and stage312.get("best_research_lead", {}).get("stress_2026", {}).get("passed")
        and primary_fragility["positive_quarter_ratio"] >= 0.50
        and primary_fragility["selection_without_best_quarter"][
            "spread_adjusted_total_r"
        ]
        > 0.0
        and rolling_diagnostics(primary_windows)["positive_r_ratio"] >= 0.50
    )

    secondary_watch = bool(
        all(
            secondary_yearly[str(year)]["trades"] >= 8
            and pf_number(secondary_yearly[str(year)]) >= 1.15
            and secondary_yearly[str(year)]["spread_adjusted_total_r"] > 0.0
            for year in (2024, 2025, 2026)
        )
        and summarize(secondary)["spread_adjusted_max_drawdown_r"] <= 8.0
        and rolling_diagnostics(secondary_windows)["positive_r_ratio"] >= 0.50
    )

    combined_watch = bool(
        all(
            combined_yearly[str(year)]["trades"] >= 15
            and pf_number(combined_yearly[str(year)]) >= 1.10
            and combined_yearly[str(year)]["spread_adjusted_total_r"] > 0.0
            for year in (2024, 2025, 2026)
        )
        and summarize(combined)["spread_adjusted_profit_factor"] is not None
        and pf_number(summarize(combined)) >= 1.25
        and summarize(combined)["spread_adjusted_max_drawdown_r"] <= 11.0
        and rolling_diagnostics(combined_windows)["positive_r_ratio"] >= 0.50
    )

    if combined_watch:
        decision = "DIVERSIFIED_RESEARCH_PORTFOLIO_WATCH_FOUND"
    elif secondary_watch:
        decision = "SECONDARY_LOW_FREQUENCY_RESEARCH_WATCH_FOUND"
    elif primary_retain:
        decision = "PRIMARY_RESEARCH_LEAD_RETAINED"
    else:
        decision = "NO_STABLE_RESEARCH_WATCH_FOUND"

    report = {
        "status": "GOLD_V3_313_FRAGILITY_AND_DIVERSIFICATION_AUDIT_COMPLETE",
        "mode": "AUDIT_ONLY_FIXED_CANDIDATE_STABILITY_REVIEW",
        "decision": decision,
        "source": {
            "stage312_json": str(stage312_path),
            "stage312_json_sha256": sha256_file(stage312_path),
            "stage311_trades": str(trades_path),
            "stage311_trades_sha256": actual_trades_sha,
        },
        "frozen_candidates": {
            "primary": {
                "family_key": PRIMARY_FAMILY,
                "filter": {"quality_min": 8.0},
                "selection_origin": "Stage312 only formal pass",
            },
            "secondary": {
                "family_key": SECONDARY_FAMILY,
                "filter": {"atr_ratio_min": 1.0, "exclude_round_number": True},
                "selection_origin": "Stage312 all-three-year positive low-frequency near miss",
            },
            "combined_policy": {
                "one_position": True,
                "preemption": False,
                "priority": [
                    "PRIMARY_FORMAL_PASS_LONG",
                    "SECONDARY_LOW_FREQUENCY_SHORT",
                ],
            },
        },
        "primary": {
            "aggregate": summarize(primary),
            "yearly": primary_yearly,
            "quarterly": quarterly(primary),
            "fragility": primary_fragility,
            "rolling_six_months": primary_windows,
            "rolling_diagnostics": rolling_diagnostics(primary_windows),
            "adjacent_profile_stability": adjacent_profile_stability(stage312),
            "research_retain_gate": primary_retain,
        },
        "secondary": {
            "aggregate": summarize(secondary),
            "yearly": secondary_yearly,
            "quarterly": quarterly(secondary),
            "rolling_six_months": secondary_windows,
            "rolling_diagnostics": rolling_diagnostics(secondary_windows),
            "research_watch_gate": secondary_watch,
            "formal_stage311_shortfall": {
                "selection_2024_2025_trades": int(
                    len(secondary[secondary.entry_dt.dt.year.isin([2024, 2025])])
                ),
                "2025_trades": int(
                    len(secondary[secondary.entry_dt.dt.year.eq(2025)])
                ),
                "reason": "sample count only; Stage311 required 30 combined and 10 in each year",
            },
        },
        "combined": {
            "raw_trades": int(len(merged_raw)),
            "accepted_trades": int(len(combined)),
            "rejected_overlap_trades": int(len(rejected)),
            "overlap": overlap_diagnostics(primary, secondary),
            "aggregate": summarize(combined),
            "yearly": combined_yearly,
            "quarterly": quarterly(combined),
            "rolling_six_months": combined_windows,
            "rolling_diagnostics": rolling_diagnostics(combined_windows),
            "research_portfolio_watch_gate": combined_watch,
        },
        "interpretation": {
            "primary": (
                "A formal Stage312 pass is rejected as robust when it fails 2026 stress, "
                "depends on one profitable quarter, or loses edge when the best quarter is removed."
            ),
            "secondary": (
                "The short track may be retained only as a low-frequency research watch because "
                "its weakness is sample count, not a negative year."
            ),
            "combined": (
                "A diversified watch is research-only because 2026 was already visible and no "
                "pristine holdout remains."
            ),
        },
        "outputs": {
            "result_json": str(output),
            "combined_trades_csv": str(combined_csv),
            "combined_trades_sha256": sha256_file(combined_csv),
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
