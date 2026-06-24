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

EXPECTED_STATUS = "GOLD_V3_321_ROBUST_PROFILE_PORTFOLIO_OVERLAP_AUDIT_COMPLETE"
EXPECTED_DECISION = "IMMEDIATE_ROBUST_SHADOW_PORTFOLIO_FOUND"
EXPECTED_SELECTED_SOURCE_LANE = "ANY_OF_THREE"
SELECTION_YEARS = (2024, 2025)
DISPLAY_ONLY_YEAR = 2026
MINIMUM_SELECTION_TRADES = 20
TOL = 1e-12


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage321-json", required=True)
    parser.add_argument("--stage321-selected", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--leaderboard-csv", required=True)
    parser.add_argument("--selected-csv", required=True)
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    if isinstance(value, pd.Timestamp):
        return str(value)
    if isinstance(value, np.generic):
        value = value.item()
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def lane_mask(frame: pd.DataFrame, lane: str) -> pd.Series:
    if lane == "CORE":
        return frame.core
    if lane == "BALANCED":
        return frame.balanced
    if lane == "PREMIUM":
        return frame.premium
    if lane == "CORE_OR_BALANCED":
        return frame.core | frame.balanced
    if lane == "CORE_OR_PREMIUM":
        return frame.core | frame.premium
    if lane == "BALANCED_OR_PREMIUM":
        return frame.balanced | frame.premium
    if lane == "ANY_OF_THREE":
        return frame.core | frame.balanced | frame.premium
    if lane == "AT_LEAST_TWO_OF_THREE":
        return frame.membership_count >= 2
    if lane == "ALL_THREE":
        return frame.membership_count == 3
    raise ValueError(f"UNKNOWN_LANE: {lane}")


def metric_value(row: dict[str, Any], key: str) -> float:
    value = row["selection_2024_2025"].get(key)
    if value is None:
        if key == "spread_adjusted_profit_factor":
            return float("inf")
        return 0.0
    return float(value)


def ranking_key(row: dict[str, Any]) -> tuple[Any, ...]:
    summary = row["selection_2024_2025"]
    return (
        -float(summary["win_rate"]),
        -metric_value(row, "spread_adjusted_profit_factor"),
        float(summary["spread_adjusted_max_drawdown_r"]),
        -float(row["leave_one_active_quarter_out"]["minimum_total_r"]),
        -float(summary["spread_adjusted_total_r"]),
        -int(summary["trades"]),
        row["portfolio_lane"],
    )


def exact_same_entries(left: pd.DataFrame, right: pd.DataFrame) -> bool:
    key = ["pair", "direction", "exit_profile", "entry_dt"]
    left_keys = left[key].sort_values(key, kind="mergesort").reset_index(drop=True)
    right_keys = right[key].sort_values(key, kind="mergesort").reset_index(drop=True)
    return bool(left_keys.equals(right_keys))


def main() -> int:
    args = parse_args()
    stage321_json_path = Path(args.stage321_json).expanduser().resolve()
    stage321_selected_path = Path(args.stage321_selected).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()
    leaderboard_path = Path(args.leaderboard_csv).expanduser().resolve()
    selected_path = Path(args.selected_csv).expanduser().resolve()

    report321 = json.loads(stage321_json_path.read_text(encoding="utf-8"))
    if report321.get("status") != EXPECTED_STATUS:
        raise ValueError(f"STAGE321_STATUS_UNEXPECTED: {report321.get('status')}")
    if report321.get("decision") != EXPECTED_DECISION:
        raise ValueError(f"STAGE321_DECISION_UNEXPECTED: {report321.get('decision')}")
    selected_source = report321.get("selected_shadow_portfolio", {})
    if selected_source.get("portfolio_lane") != EXPECTED_SELECTED_SOURCE_LANE:
        raise ValueError(
            "STAGE321_SELECTED_SOURCE_LANE_UNEXPECTED: "
            f"{selected_source.get('portfolio_lane')}"
        )
    expected_selected_sha = report321.get("outputs", {}).get(
        "selected_shadow_trades_sha256"
    )
    actual_selected_sha = sha256_file(stage321_selected_path)
    if expected_selected_sha != actual_selected_sha:
        raise ValueError(
            "STAGE321_SELECTED_SHA_MISMATCH: "
            f"expected={expected_selected_sha} actual={actual_selected_sha}"
        )

    trades = pd.read_csv(stage321_selected_path, encoding="utf-8-sig")
    required = {
        "pair",
        "direction",
        "exit_profile",
        "entry_dt",
        "exit_dt",
        "spread_adjusted_pnl",
        "spread_adjusted_r",
        "core",
        "balanced",
        "premium",
        "membership_count",
    }
    missing = sorted(required - set(trades.columns))
    if missing:
        raise ValueError(f"STAGE321_SELECTED_COLUMNS_MISSING: {missing}")
    for column in ("entry_dt", "exit_dt"):
        trades[column] = pd.to_datetime(trades[column], errors="raise")
    for column in ("core", "balanced", "premium"):
        if trades[column].dtype != bool:
            trades[column] = trades[column].astype(str).str.lower().map(
                {"true": True, "false": False}
            )
            if trades[column].isna().any():
                raise ValueError(f"BOOLEAN_PARSE_FAILED: {column}")

    passing_rows = [
        row
        for row in report321.get("leaderboard", [])
        if row.get("shadow_gate", {}).get("pass")
        and int(row["selection_2024_2025"]["trades"])
        >= MINIMUM_SELECTION_TRADES
    ]
    passing_rows.sort(key=ranking_key)
    if not passing_rows:
        raise ValueError("NO_STAGE321_PASSING_LANE_WITH_MINIMUM_SAMPLE")
    selected = passing_rows[0]
    selected_lane = str(selected["portfolio_lane"])

    selected_trades = trades[lane_mask(trades, selected_lane)].copy()
    selected_trades["stage322_selected_lane"] = selected_lane
    selected_trades = selected_trades.sort_values(
        ["entry_dt", "exit_dt"], kind="mergesort"
    )

    any_frame = trades[lane_mask(trades, "ANY_OF_THREE")].copy()
    core_premium_frame = trades[lane_mask(trades, "CORE_OR_PREMIUM")].copy()
    balanced_premium_frame = trades[
        lane_mask(trades, "BALANCED_OR_PREMIUM")
    ].copy()
    redundancy = {
        "balanced_only_trade_count": int(
            (trades.balanced & ~trades.core & ~trades.premium).sum()
        ),
        "any_of_three_equals_core_or_premium": exact_same_entries(
            any_frame, core_premium_frame
        ),
        "balanced_is_subset_of_core_or_premium": bool(
            (~trades.balanced | trades.core | trades.premium).all()
        ),
        "broad_extra_trade_count_over_balanced_or_premium": int(
            len(core_premium_frame) - len(balanced_premium_frame)
        ),
    }

    flat_rows: list[dict[str, Any]] = []
    for rank, row in enumerate(passing_rows, start=1):
        summary = row["selection_2024_2025"]
        stress = row["stress_2026_display_only"]
        flat_rows.append(
            {
                "rank_win_rate_first": rank,
                "portfolio_lane": row["portfolio_lane"],
                "lane_definition": row["lane_definition"],
                "trades_2024_2025": summary["trades"],
                "win_rate_2024_2025": summary["win_rate"],
                "profit_factor_2024_2025": summary[
                    "spread_adjusted_profit_factor"
                ],
                "total_r_2024_2025": summary["spread_adjusted_total_r"],
                "max_drawdown_r_2024_2025": summary[
                    "spread_adjusted_max_drawdown_r"
                ],
                "minimum_leave_one_quarter_out_r": row[
                    "leave_one_active_quarter_out"
                ]["minimum_total_r"],
                "rolling_6m_positive_ratio": row["rolling_6m"][
                    "positive_total_r_ratio"
                ],
                "iid_bootstrap_positive_r_probability": row[
                    "iid_trade_bootstrap"
                ]["positive_total_r_probability"],
                "quarter_block_positive_r_probability": row[
                    "quarter_block_bootstrap"
                ]["positive_total_r_probability"],
                "trades_2026_display_only": stress["trades"],
                "win_rate_2026_display_only": stress["win_rate"],
                "profit_factor_2026_display_only": stress[
                    "spread_adjusted_profit_factor"
                ],
                "total_r_2026_display_only": stress["spread_adjusted_total_r"],
                "max_drawdown_r_2026_display_only": stress[
                    "spread_adjusted_max_drawdown_r"
                ],
            }
        )
    leaderboard_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(flat_rows).to_csv(
        leaderboard_path, index=False, encoding="utf-8-sig"
    )
    selected_trades.to_csv(selected_path, index=False, encoding="utf-8-sig")

    broad = next(
        row
        for row in report321["leaderboard"]
        if row["portfolio_lane"] == "ANY_OF_THREE"
    )
    conservative = next(
        row
        for row in report321["leaderboard"]
        if row["portfolio_lane"] == "BALANCED_OR_PREMIUM"
    )
    comparison = {
        "broad_lane": "ANY_OF_THREE",
        "conservative_lane": "BALANCED_OR_PREMIUM",
        "selection_2024_2025": {
            "broad": broad["selection_2024_2025"],
            "conservative": conservative["selection_2024_2025"],
            "win_rate_difference_conservative_minus_broad": float(
                conservative["selection_2024_2025"]["win_rate"]
                - broad["selection_2024_2025"]["win_rate"]
            ),
            "profit_factor_difference_conservative_minus_broad": float(
                conservative["selection_2024_2025"][
                    "spread_adjusted_profit_factor"
                ]
                - broad["selection_2024_2025"][
                    "spread_adjusted_profit_factor"
                ]
            ),
            "total_r_difference_conservative_minus_broad": float(
                conservative["selection_2024_2025"]["spread_adjusted_total_r"]
                - broad["selection_2024_2025"]["spread_adjusted_total_r"]
            ),
        },
        "display_only_2026": {
            "broad": broad["stress_2026_display_only"],
            "conservative": conservative["stress_2026_display_only"],
            "used_for_selection": False,
        },
    }

    output = {
        "status": "GOLD_V3_322_WIN_RATE_FIRST_SHADOW_SELECTION_AUDIT_COMPLETE",
        "mode": "AUDIT_ONLY_FIXED_LANE_WIN_RATE_FIRST_SELECTION",
        "decision": "WIN_RATE_FIRST_CONSERVATIVE_SHADOW_SELECTED",
        "source": {
            "stage321_json": str(stage321_json_path),
            "stage321_json_sha256": sha256_file(stage321_json_path),
            "stage321_selected_trades": str(stage321_selected_path),
            "stage321_selected_trades_sha256": actual_selected_sha,
        },
        "research_contract": {
            "selection_years": list(SELECTION_YEARS),
            "display_only_year": DISPLAY_ONLY_YEAR,
            "selection_and_ranking_do_not_use_2026": True,
            "minimum_selection_trades": MINIMUM_SELECTION_TRADES,
            "new_raw_feature_thresholds_added": False,
            "eligible_lanes_are_stage321_shadow_gate_passes_only": True,
            "ranking_priority": [
                "highest_selection_win_rate",
                "highest_selection_profit_factor",
                "lowest_selection_drawdown",
                "highest_leave_one_quarter_out_minimum_r",
                "highest_selection_total_r",
                "highest_selection_trade_count",
                "stable_lane_name",
            ],
            "duplicate_numeric_tolerance_inherited": TOL,
        },
        "redundancy_audit": redundancy,
        "selected": selected,
        "selected_lane": selected_lane,
        "selected_trade_count_all_period": int(len(selected_trades)),
        "broad_vs_conservative": comparison,
        "ranking": passing_rows,
        "interpretation": {
            "why_selected": (
                "The user requested higher win rate. Among Stage321 lanes that already "
                "passed the same robustness gate and retained at least 20 selection "
                "trades, selection win rate is the primary objective. When win rate "
                "ties, PF is preferred before total R."
            ),
            "redundancy_note": (
                "Balanced has no unique trade outside Core or Premium. Therefore "
                "ANY_OF_THREE is effectively CORE_OR_PREMIUM, not three independent "
                "diversifying sources."
            ),
            "limits": (
                "This is still historical shadow research. It does not replace or "
                "rewrite the Stage319 frozen future-only contract."
            ),
        },
        "outputs": {
            "result_json": str(output_path),
            "leaderboard_csv": str(leaderboard_path),
            "selected_shadow_trades_csv": str(selected_path),
            "leaderboard_sha256": sha256_file(leaderboard_path),
            "selected_shadow_trades_sha256": sha256_file(selected_path),
        },
        "promotion": {
            "performed": False,
            "stage319_contract": "UNCHANGED_FROZEN",
            "stage314_contract": "UNCHANGED_ACTIVE",
            "stage321_result": "UNCHANGED_RETAINED",
            "stage307_candidate": "UNCHANGED_RETAINED",
            "stage292_candidate_pool_changed": False,
        },
        "safety_flags": {
            "historical_trade_registry_only": True,
            "closed_candles_only": True,
            "final_signal_changed": False,
            "mt5_order_enabled": False,
            "discord_enabled": False,
            "partial_close_enabled": False,
        },
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(json_safe(output), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(json_safe(output), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
