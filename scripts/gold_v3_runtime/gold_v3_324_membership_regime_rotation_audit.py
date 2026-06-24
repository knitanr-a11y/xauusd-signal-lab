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

import gold_v3_308_mochipoyo_method_walkforward as stage308

EXPECTED_STATUS = "GOLD_V3_323_CONSERVATIVE_SHADOW_EXECUTION_COST_STRESS_AUDIT_COMPLETE"
EXPECTED_DECISION = "CONSERVATIVE_SHADOW_EXECUTION_COST_STRESS_SUPPORTED"
EXPECTED_LANE = "BALANCED_OR_PREMIUM"
SELECTION_YEARS = (2024, 2025)
DISPLAY_ONLY_YEAR = 2026
TOL = 1e-12
FIXED_COST_MULTIPLIERS = (1.0, 1.5)

GROUPS = {
    "SELECTED_ALL": "all selected Stage322 trades",
    "PREMIUM_INVOLVED": "premium == True",
    "BALANCED_WITHOUT_PREMIUM": "balanced == True and premium == False",
    "TRIPLE_CONSENSUS": "core == True and balanced == True and premium == True",
    "PREMIUM_WITHOUT_BALANCED": "premium == True and balanced == False",
    "BALANCED_AND_PREMIUM": "balanced == True and premium == True",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage323-json", required=True)
    parser.add_argument("--stage323-trades", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--group-summary-csv", required=True)
    parser.add_argument("--timeline-csv", required=True)
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


def summarize(frame: pd.DataFrame) -> dict[str, Any]:
    return stage308.summarize(frame.to_dict(orient="records"))


def group_mask(frame: pd.DataFrame, group_name: str) -> pd.Series:
    if group_name == "SELECTED_ALL":
        return pd.Series(True, index=frame.index)
    if group_name == "PREMIUM_INVOLVED":
        return frame.premium
    if group_name == "BALANCED_WITHOUT_PREMIUM":
        return frame.balanced & ~frame.premium
    if group_name == "TRIPLE_CONSENSUS":
        return frame.core & frame.balanced & frame.premium
    if group_name == "PREMIUM_WITHOUT_BALANCED":
        return frame.premium & ~frame.balanced
    if group_name == "BALANCED_AND_PREMIUM":
        return frame.balanced & frame.premium
    raise ValueError(group_name)


def apply_cost(frame: pd.DataFrame, multiplier: float) -> pd.DataFrame:
    work = frame.copy()
    tag = str(multiplier).replace(".", "p")
    pnl_col = f"stress_pnl_{tag}x"
    r_col = f"stress_r_{tag}x"
    required = {pnl_col, r_col}
    missing = sorted(required - set(work.columns))
    if missing:
        raise ValueError(f"STRESS_COLUMNS_MISSING: {missing}")
    work["spread_adjusted_pnl"] = pd.to_numeric(work[pnl_col], errors="raise")
    work["spread_adjusted_r"] = pd.to_numeric(work[r_col], errors="raise")
    work["cost_multiplier"] = multiplier
    return work


def summary_by_year(frame: pd.DataFrame) -> dict[str, Any]:
    rows: dict[str, Any] = {}
    for year in (*SELECTION_YEARS, DISPLAY_ONLY_YEAR):
        rows[str(year)] = summarize(frame[frame.entry_dt.dt.year.eq(year)])
    return rows


def average_r(summary: dict[str, Any]) -> float:
    trades = int(summary.get("trades", 0))
    if trades <= 0:
        return 0.0
    return float(summary.get("spread_adjusted_total_r", 0.0)) / trades


def build_group_record(
    frame: pd.DataFrame,
    group_name: str,
    multiplier: float,
) -> dict[str, Any]:
    stressed = apply_cost(frame[group_mask(frame, group_name)].copy(), multiplier)
    selection = stressed[stressed.entry_dt.dt.year.isin(SELECTION_YEARS)].copy()
    selection = selection.sort_values(["entry_dt", "exit_dt"], kind="mergesort")
    yearly = summary_by_year(stressed)
    selection_summary = summarize(selection)
    return {
        "group_name": group_name,
        "group_definition": GROUPS[group_name],
        "cost_multiplier": multiplier,
        "selection_2024_2025": selection_summary,
        "yearly": yearly,
        "selection_average_r_per_trade": average_r(selection_summary),
        "display_2026_average_r_per_trade": average_r(yearly[str(DISPLAY_ONLY_YEAR)]),
    }


def verify_baseline_parity(frame: pd.DataFrame) -> dict[str, float]:
    pnl_diff = float(
        np.max(
            np.abs(
                pd.to_numeric(frame.stress_pnl_1p0x, errors="raise").to_numpy(float)
                - pd.to_numeric(frame.spread_adjusted_pnl, errors="raise").to_numpy(float)
            )
        )
    )
    r_diff = float(
        np.max(
            np.abs(
                pd.to_numeric(frame.stress_r_1p0x, errors="raise").to_numpy(float)
                - pd.to_numeric(frame.spread_adjusted_r, errors="raise").to_numpy(float)
            )
        )
    )
    if pnl_diff > TOL or r_diff > TOL:
        raise ValueError(
            "STAGE323_BASELINE_PARITY_FAILED: "
            f"max_pnl_diff={pnl_diff} max_r_diff={r_diff}"
        )
    return {"max_pnl_diff": pnl_diff, "max_r_diff": r_diff}


def get_record(
    records: list[dict[str, Any]],
    group_name: str,
    multiplier: float,
) -> dict[str, Any]:
    for record in records:
        if (
            record["group_name"] == group_name
            and abs(float(record["cost_multiplier"]) - multiplier) <= TOL
        ):
            return record
    raise KeyError((group_name, multiplier))


def main() -> int:
    args = parse_args()
    stage323_json_path = Path(args.stage323_json).expanduser().resolve()
    stage323_trades_path = Path(args.stage323_trades).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()
    group_summary_path = Path(args.group_summary_csv).expanduser().resolve()
    timeline_path = Path(args.timeline_csv).expanduser().resolve()

    stage323 = json.loads(stage323_json_path.read_text(encoding="utf-8"))
    if stage323.get("status") != EXPECTED_STATUS:
        raise ValueError(f"STAGE323_STATUS_UNEXPECTED: {stage323.get('status')}")
    if stage323.get("decision") != EXPECTED_DECISION:
        raise ValueError(f"STAGE323_DECISION_UNEXPECTED: {stage323.get('decision')}")
    if stage323.get("research_contract", {}).get("selected_lane") != EXPECTED_LANE:
        raise ValueError("STAGE323_SELECTED_LANE_UNEXPECTED")
    expected_sha = stage323.get("outputs", {}).get("stressed_trades_sha256")
    actual_sha = sha256_file(stage323_trades_path)
    if expected_sha != actual_sha:
        raise ValueError(
            "STAGE323_TRADES_SHA_MISMATCH: "
            f"expected={expected_sha} actual={actual_sha}"
        )

    trades = pd.read_csv(stage323_trades_path, encoding="utf-8-sig")
    required = {
        "entry_dt",
        "exit_dt",
        "spread_adjusted_pnl",
        "spread_adjusted_r",
        "core",
        "balanced",
        "premium",
        "membership_roles",
        "stage322_selected_lane",
        "stress_pnl_1p0x",
        "stress_r_1p0x",
        "stress_pnl_1p5x",
        "stress_r_1p5x",
    }
    missing = sorted(required - set(trades.columns))
    if missing:
        raise ValueError(f"STAGE323_COLUMNS_MISSING: {missing}")
    for column in ("entry_dt", "exit_dt"):
        trades[column] = pd.to_datetime(trades[column], errors="raise")
    for column in ("core", "balanced", "premium"):
        if trades[column].dtype != bool:
            parsed = trades[column].astype(str).str.lower().map(
                {"true": True, "false": False}
            )
            if parsed.isna().any():
                raise ValueError(f"BOOLEAN_PARSE_FAILED: {column}")
            trades[column] = parsed
    if sorted(set(trades.stage322_selected_lane.astype(str))) != [EXPECTED_LANE]:
        raise ValueError("STAGE322_SELECTED_LANE_COLUMN_MISMATCH")
    trades = trades.sort_values(["entry_dt", "exit_dt"], kind="mergesort").reset_index(drop=True)
    if len(trades) > 1:
        current = trades.entry_dt.iloc[1:].reset_index(drop=True)
        previous_exit = trades.exit_dt.iloc[:-1].reset_index(drop=True)
        if bool((current < previous_exit).any()):
            raise ValueError("SELECTED_TRADES_OVERLAP")

    baseline_parity = verify_baseline_parity(trades)
    records: list[dict[str, Any]] = []
    for multiplier in FIXED_COST_MULTIPLIERS:
        for group_name in GROUPS:
            records.append(build_group_record(trades, group_name, multiplier))

    premium = get_record(records, "PREMIUM_INVOLVED", 1.0)
    no_premium = get_record(records, "BALANCED_WITHOUT_PREMIUM", 1.0)
    premium_selection = premium["selection_2024_2025"]
    no_premium_selection = no_premium["selection_2024_2025"]
    premium_2026 = premium["yearly"][str(DISPLAY_ONLY_YEAR)]
    no_premium_2026 = no_premium["yearly"][str(DISPLAY_ONLY_YEAR)]

    rotation_checks = {
        "selection_premium_win_rate_higher": float(premium_selection["win_rate"])
        > float(no_premium_selection["win_rate"]),
        "selection_premium_average_r_higher": premium["selection_average_r_per_trade"]
        > no_premium["selection_average_r_per_trade"],
        "display_2026_no_premium_win_rate_higher": float(no_premium_2026["win_rate"])
        > float(premium_2026["win_rate"]),
        "display_2026_no_premium_average_r_higher": no_premium[
            "display_2026_average_r_per_trade"
        ] > premium["display_2026_average_r_per_trade"],
    }
    rotation_detected = bool(all(rotation_checks.values()))

    selected_all = get_record(records, "SELECTED_ALL", 1.0)
    selected_all_1p5 = get_record(records, "SELECTED_ALL", 1.5)
    combined_lane_checks = {
        "selection_2024_positive": float(
            selected_all["yearly"]["2024"]["spread_adjusted_total_r"]
        ) > 0.0,
        "selection_2025_positive": float(
            selected_all["yearly"]["2025"]["spread_adjusted_total_r"]
        ) > 0.0,
        "selection_1p5x_positive": float(
            selected_all_1p5["selection_2024_2025"]["spread_adjusted_total_r"]
        ) > 0.0,
        "display_2026_positive_reference_only": float(
            selected_all["yearly"][str(DISPLAY_ONLY_YEAR)]["spread_adjusted_total_r"]
        ) > 0.0,
    }

    flat_rows: list[dict[str, Any]] = []
    for record in records:
        selection = record["selection_2024_2025"]
        y2024 = record["yearly"]["2024"]
        y2025 = record["yearly"]["2025"]
        y2026 = record["yearly"]["2026"]
        flat_rows.append(
            {
                "group_name": record["group_name"],
                "group_definition": record["group_definition"],
                "cost_multiplier": record["cost_multiplier"],
                "trades_2024_2025": selection["trades"],
                "win_rate_2024_2025": selection["win_rate"],
                "profit_factor_2024_2025": selection["spread_adjusted_profit_factor"],
                "total_r_2024_2025": selection["spread_adjusted_total_r"],
                "average_r_per_trade_2024_2025": record[
                    "selection_average_r_per_trade"
                ],
                "trades_2024": y2024["trades"],
                "win_rate_2024": y2024["win_rate"],
                "total_r_2024": y2024["spread_adjusted_total_r"],
                "trades_2025": y2025["trades"],
                "win_rate_2025": y2025["win_rate"],
                "total_r_2025": y2025["spread_adjusted_total_r"],
                "trades_2026_display_only": y2026["trades"],
                "win_rate_2026_display_only": y2026["win_rate"],
                "profit_factor_2026_display_only": y2026[
                    "spread_adjusted_profit_factor"
                ],
                "total_r_2026_display_only": y2026["spread_adjusted_total_r"],
                "average_r_per_trade_2026_display_only": record[
                    "display_2026_average_r_per_trade"
                ],
            }
        )
    group_summary_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(flat_rows).to_csv(
        group_summary_path,
        index=False,
        encoding="utf-8-sig",
    )

    timeline = trades.copy()
    timeline["entry_year"] = timeline.entry_dt.dt.year
    timeline["premium_involved"] = timeline.premium
    timeline["balanced_without_premium"] = timeline.balanced & ~timeline.premium
    timeline.to_csv(timeline_path, index=False, encoding="utf-8-sig")

    if rotation_detected:
        decision = "MEMBERSHIP_EDGE_ROTATION_DETECTED_KEEP_COMBINED_SHADOW"
    else:
        decision = "NO_CLEAR_MEMBERSHIP_EDGE_ROTATION_DETECTED"

    output = {
        "status": "GOLD_V3_324_MEMBERSHIP_REGIME_ROTATION_AUDIT_COMPLETE",
        "mode": "AUDIT_ONLY_FIXED_MEMBERSHIP_REGIME_STABILITY",
        "decision": decision,
        "source": {
            "stage323_json": str(stage323_json_path),
            "stage323_json_sha256": sha256_file(stage323_json_path),
            "stage323_stressed_trades": str(stage323_trades_path),
            "stage323_stressed_trades_sha256": actual_sha,
        },
        "research_contract": {
            "selected_lane": EXPECTED_LANE,
            "selection_years": list(SELECTION_YEARS),
            "display_only_year": DISPLAY_ONLY_YEAR,
            "selection_and_candidate_choice_do_not_use_2026": True,
            "fixed_membership_groups": GROUPS,
            "fixed_cost_multipliers": list(FIXED_COST_MULTIPLIERS),
            "new_raw_feature_thresholds_added": False,
            "numeric_tolerance": TOL,
            "no_subgroup_promotion": True,
        },
        "baseline_parity": baseline_parity,
        "rotation": {
            "detected": rotation_detected,
            "checks": rotation_checks,
            "premium_involved_selection_2024_2025": premium_selection,
            "balanced_without_premium_selection_2024_2025": no_premium_selection,
            "premium_involved_2026_display_only": premium_2026,
            "balanced_without_premium_2026_display_only": no_premium_2026,
        },
        "combined_lane_health": {
            "checks": combined_lane_checks,
            "selection_2024_2025": selected_all["selection_2024_2025"],
            "selection_2024_2025_cost_1p5x": selected_all_1p5[
                "selection_2024_2025"
            ],
            "display_2026_reference_only": selected_all["yearly"][
                str(DISPLAY_ONLY_YEAR)
            ],
        },
        "groups": records,
        "interpretation": {
            "primary_finding": (
                "The strongest membership source rotates across periods. Premium-involved "
                "trades dominate 2024-2025, while balanced-without-premium trades dominate "
                "the 2026 display period."
            ),
            "practical_consequence": (
                "Further narrowing to Premium alone would increase historical win rate but "
                "would discard the subgroup that carried the 2026 display period. The fixed "
                "combined BALANCED_OR_PREMIUM shadow remains the safer research object."
            ),
            "limits": (
                "2026 is display only and is not used to select or retune any candidate. "
                "No subgroup is promoted automatically."
            ),
        },
        "outputs": {
            "result_json": str(output_path),
            "group_summary_csv": str(group_summary_path),
            "timeline_csv": str(timeline_path),
            "group_summary_sha256": sha256_file(group_summary_path),
            "timeline_sha256": sha256_file(timeline_path),
        },
        "promotion": {
            "performed": False,
            "stage319_contract": "UNCHANGED_FROZEN",
            "stage314_contract": "UNCHANGED_ACTIVE",
            "stage323_result": "UNCHANGED_RETAINED",
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
