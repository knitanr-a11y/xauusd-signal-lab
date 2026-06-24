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

EXPECTED_STATUS = "GOLD_V3_324_MEMBERSHIP_REGIME_ROTATION_AUDIT_COMPLETE"
EXPECTED_DECISION = "MEMBERSHIP_EDGE_ROTATION_DETECTED_KEEP_COMBINED_SHADOW"
EXPECTED_LANE = "BALANCED_OR_PREMIUM"
SELECTION_YEARS = (2024, 2025)
DISPLAY_ONLY_YEAR = 2026
TOL = 1e-12

POLICIES: dict[str, dict[str, Any]] = {
    "STATIC_COMBINED": {"kind": "static"},
    "RELATIVE_TRAILING_MEAN_R_N2": {"kind": "relative_trailing", "window": 2},
    "RELATIVE_TRAILING_MEAN_R_N3": {"kind": "relative_trailing", "window": 3},
    "RELATIVE_TRAILING_MEAN_R_N4": {"kind": "relative_trailing", "window": 4},
    "RELATIVE_TRAILING_MEAN_R_N5": {"kind": "relative_trailing", "window": 5},
    "EWMA_RELATIVE_R_A030_MIN2": {"kind": "ewma_relative", "alpha": 0.30, "min_obs": 2},
    "EWMA_RELATIVE_R_A050_MIN2": {"kind": "ewma_relative", "alpha": 0.50, "min_obs": 2},
    "EWMA_RELATIVE_R_A070_MIN2": {"kind": "ewma_relative", "alpha": 0.70, "min_obs": 2},
    "GROUP_POSITIVE_TRAILING_MEAN_R_N2": {"kind": "group_positive", "window": 2},
    "GROUP_POSITIVE_TRAILING_MEAN_R_N3": {"kind": "group_positive", "window": 3},
}

LEAD_GATE = {
    "minimum_selection_trades": 14,
    "minimum_each_selection_year_trades": 6,
    "minimum_selection_win_rate": 0.75,
    "minimum_selection_profit_factor": 3.0,
    "minimum_selection_total_r_exclusive": 0.0,
    "maximum_selection_drawdown_r": 2.0,
    "minimum_each_selection_year_total_r_exclusive": 0.0,
    "cost_1p5x_minimum_selection_trades": 14,
    "cost_1p5x_minimum_selection_win_rate": 0.75,
    "cost_1p5x_minimum_profit_factor": 3.0,
    "cost_1p5x_minimum_total_r_exclusive": 0.0,
    "cost_1p5x_maximum_drawdown_r": 2.0,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage324-json", required=True)
    parser.add_argument("--stage324-timeline", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--leaderboard-csv", required=True)
    parser.add_argument("--selected-trades-csv", required=True)
    parser.add_argument("--decision-trace-csv", required=True)
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


def yearly(frame: pd.DataFrame) -> dict[str, Any]:
    return stage308.yearly_summary(frame.to_dict(orient="records"))


def ewma(values: list[float], alpha: float) -> float:
    score = float(values[0])
    for value in values[1:]:
        score = alpha * float(value) + (1.0 - alpha) * score
    return float(score)


def assign_group(row: pd.Series) -> str:
    premium = bool(row.premium)
    balanced = bool(row.balanced)
    if premium:
        return "PREMIUM_INVOLVED"
    if balanced:
        return "BALANCED_WITHOUT_PREMIUM"
    raise ValueError("SELECTED_TRADE_HAS_NO_ROUTER_GROUP")


def policy_decision(
    policy: dict[str, Any],
    group_name: str,
    histories: dict[str, list[float]],
) -> tuple[bool, str, float | None, float | None]:
    other = (
        "BALANCED_WITHOUT_PREMIUM"
        if group_name == "PREMIUM_INVOLVED"
        else "PREMIUM_INVOLVED"
    )
    kind = str(policy["kind"])
    if kind == "static":
        return True, "STATIC_TAKE_ALL", None, None
    if kind == "relative_trailing":
        window = int(policy["window"])
        if len(histories[group_name]) < window or len(histories[other]) < window:
            return True, "WARMUP_TAKE_ALL", None, None
        group_score = float(np.mean(histories[group_name][-window:]))
        other_score = float(np.mean(histories[other][-window:]))
        return (
            group_score >= other_score,
            "GROUP_SCORE_GE_OTHER" if group_score >= other_score else "GROUP_SCORE_LT_OTHER",
            group_score,
            other_score,
        )
    if kind == "ewma_relative":
        min_obs = int(policy["min_obs"])
        if len(histories[group_name]) < min_obs or len(histories[other]) < min_obs:
            return True, "WARMUP_TAKE_ALL", None, None
        alpha = float(policy["alpha"])
        group_score = ewma(histories[group_name], alpha)
        other_score = ewma(histories[other], alpha)
        return (
            group_score >= other_score,
            "GROUP_EWMA_GE_OTHER" if group_score >= other_score else "GROUP_EWMA_LT_OTHER",
            group_score,
            other_score,
        )
    if kind == "group_positive":
        window = int(policy["window"])
        if len(histories[group_name]) < window:
            return True, "WARMUP_TAKE_ALL", None, None
        group_score = float(np.mean(histories[group_name][-window:]))
        return (
            group_score > 0.0,
            "GROUP_SCORE_POSITIVE" if group_score > 0.0 else "GROUP_SCORE_NONPOSITIVE",
            group_score,
            None,
        )
    raise ValueError(f"UNKNOWN_POLICY_KIND: {kind}")


def simulate_policy(
    source: pd.DataFrame,
    policy_name: str,
    policy: dict[str, Any],
    r_column: str,
    pnl_column: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    histories: dict[str, list[float]] = {
        "PREMIUM_INVOLVED": [],
        "BALANCED_WITHOUT_PREMIUM": [],
    }
    taken_rows: list[dict[str, Any]] = []
    trace_rows: list[dict[str, Any]] = []

    previous_exit: pd.Timestamp | None = None
    for _, row in source.iterrows():
        entry_dt = pd.Timestamp(row.entry_dt)
        exit_dt = pd.Timestamp(row.exit_dt)
        if previous_exit is not None and entry_dt < previous_exit:
            raise ValueError("ASOF_ROUTER_SOURCE_OVERLAP")
        group_name = str(row.router_group)
        take, reason, group_score, other_score = policy_decision(
            policy, group_name, histories
        )
        trace_rows.append(
            {
                "policy_name": policy_name,
                "entry_dt": entry_dt,
                "exit_dt": exit_dt,
                "entry_year": int(entry_dt.year),
                "router_group": group_name,
                "take": bool(take),
                "decision_reason": reason,
                "group_score_before_entry": group_score,
                "other_group_score_before_entry": other_score,
                "premium_history_count_before_entry": len(
                    histories["PREMIUM_INVOLVED"]
                ),
                "balanced_without_premium_history_count_before_entry": len(
                    histories["BALANCED_WITHOUT_PREMIUM"]
                ),
            }
        )
        if take:
            item = row.to_dict()
            item["router_policy"] = policy_name
            item["router_group"] = group_name
            item["router_decision_reason"] = reason
            item["spread_adjusted_r"] = float(row[r_column])
            item["spread_adjusted_pnl"] = float(row[pnl_column])
            taken_rows.append(item)

        histories[group_name].append(float(row[r_column]))
        previous_exit = exit_dt

    taken = pd.DataFrame(taken_rows)
    if not taken.empty:
        taken = taken.sort_values(["entry_dt", "exit_dt"], kind="mergesort")
    trace = pd.DataFrame(trace_rows)
    return taken, trace


def average_r(summary: dict[str, Any]) -> float:
    trades = int(summary.get("trades", 0))
    if trades <= 0:
        return 0.0
    return float(summary.get("spread_adjusted_total_r", 0.0)) / trades


def evaluate_policy(
    source: pd.DataFrame,
    policy_name: str,
    policy: dict[str, Any],
) -> tuple[dict[str, Any], pd.DataFrame, pd.DataFrame]:
    taken_1p0, trace_1p0 = simulate_policy(
        source,
        policy_name,
        policy,
        "stress_r_1p0x",
        "stress_pnl_1p0x",
    )
    taken_1p5, _ = simulate_policy(
        source,
        policy_name,
        policy,
        "stress_r_1p5x",
        "stress_pnl_1p5x",
    )

    selection_1p0 = taken_1p0[
        taken_1p0.entry_dt.dt.year.isin(SELECTION_YEARS)
    ].copy()
    selection_1p5 = taken_1p5[
        taken_1p5.entry_dt.dt.year.isin(SELECTION_YEARS)
    ].copy()
    summary_1p0 = summarize(selection_1p0)
    summary_1p5 = summarize(selection_1p5)
    yearly_1p0 = yearly(taken_1p0)
    yearly_1p5 = yearly(taken_1p5)

    checks = {
        "non_static_policy": policy_name != "STATIC_COMBINED",
        "minimum_selection_trades": int(summary_1p0["trades"])
        >= int(LEAD_GATE["minimum_selection_trades"]),
        "minimum_each_selection_year_trades": min(
            int(yearly_1p0[str(year)]["trades"]) for year in SELECTION_YEARS
        ) >= int(LEAD_GATE["minimum_each_selection_year_trades"]),
        "minimum_selection_win_rate": float(summary_1p0["win_rate"])
        >= float(LEAD_GATE["minimum_selection_win_rate"]),
        "minimum_selection_profit_factor": float(
            summary_1p0["spread_adjusted_profit_factor"] or 0.0
        ) >= float(LEAD_GATE["minimum_selection_profit_factor"]),
        "minimum_selection_total_r": float(summary_1p0["spread_adjusted_total_r"])
        > float(LEAD_GATE["minimum_selection_total_r_exclusive"]),
        "maximum_selection_drawdown_r": float(
            summary_1p0["spread_adjusted_max_drawdown_r"]
        ) <= float(LEAD_GATE["maximum_selection_drawdown_r"]),
        "minimum_each_selection_year_total_r": all(
            float(yearly_1p0[str(year)]["spread_adjusted_total_r"])
            > float(LEAD_GATE["minimum_each_selection_year_total_r_exclusive"])
            for year in SELECTION_YEARS
        ),
        "cost_1p5x_minimum_selection_trades": int(summary_1p5["trades"])
        >= int(LEAD_GATE["cost_1p5x_minimum_selection_trades"]),
        "cost_1p5x_minimum_selection_win_rate": float(summary_1p5["win_rate"])
        >= float(LEAD_GATE["cost_1p5x_minimum_selection_win_rate"]),
        "cost_1p5x_minimum_profit_factor": float(
            summary_1p5["spread_adjusted_profit_factor"] or 0.0
        ) >= float(LEAD_GATE["cost_1p5x_minimum_profit_factor"]),
        "cost_1p5x_minimum_total_r": float(summary_1p5["spread_adjusted_total_r"])
        > float(LEAD_GATE["cost_1p5x_minimum_total_r_exclusive"]),
        "cost_1p5x_maximum_drawdown_r": float(
            summary_1p5["spread_adjusted_max_drawdown_r"]
        ) <= float(LEAD_GATE["cost_1p5x_maximum_drawdown_r"]),
    }
    gate_pass = bool(all(checks.values()))

    record = {
        "policy_name": policy_name,
        "policy_definition": policy,
        "selection_2024_2025": summary_1p0,
        "selection_2024_2025_cost_1p5x": summary_1p5,
        "yearly": yearly_1p0,
        "yearly_cost_1p5x": yearly_1p5,
        "selection_average_r_per_trade": average_r(summary_1p0),
        "display_2026": yearly_1p0[str(DISPLAY_ONLY_YEAR)],
        "display_2026_cost_1p5x": yearly_1p5[str(DISPLAY_ONLY_YEAR)],
        "lead_gate": {"pass": gate_pass, "checks": checks},
    }
    return record, taken_1p0, trace_1p0


def ranking_key(row: dict[str, Any]) -> tuple[Any, ...]:
    summary = row["selection_2024_2025"]
    return (
        -float(summary["win_rate"]),
        -float(summary["spread_adjusted_profit_factor"] or 0.0),
        float(summary["spread_adjusted_max_drawdown_r"]),
        -float(summary["spread_adjusted_total_r"]),
        -int(summary["trades"]),
        row["policy_name"],
    )


def main() -> int:
    args = parse_args()
    stage324_json_path = Path(args.stage324_json).expanduser().resolve()
    timeline_path = Path(args.stage324_timeline).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()
    leaderboard_path = Path(args.leaderboard_csv).expanduser().resolve()
    selected_trades_path = Path(args.selected_trades_csv).expanduser().resolve()
    decision_trace_path = Path(args.decision_trace_csv).expanduser().resolve()

    stage324 = json.loads(stage324_json_path.read_text(encoding="utf-8"))
    if stage324.get("status") != EXPECTED_STATUS:
        raise ValueError(f"STAGE324_STATUS_UNEXPECTED: {stage324.get('status')}")
    if stage324.get("decision") != EXPECTED_DECISION:
        raise ValueError(f"STAGE324_DECISION_UNEXPECTED: {stage324.get('decision')}")
    if stage324.get("research_contract", {}).get("selected_lane") != EXPECTED_LANE:
        raise ValueError("STAGE324_SELECTED_LANE_UNEXPECTED")
    expected_sha = stage324.get("outputs", {}).get("timeline_sha256")
    actual_sha = sha256_file(timeline_path)
    if expected_sha != actual_sha:
        raise ValueError(
            "STAGE324_TIMELINE_SHA_MISMATCH: "
            f"expected={expected_sha} actual={actual_sha}"
        )

    source = pd.read_csv(timeline_path, encoding="utf-8-sig")
    required = {
        "entry_dt",
        "exit_dt",
        "core",
        "balanced",
        "premium",
        "stage322_selected_lane",
        "stress_pnl_1p0x",
        "stress_r_1p0x",
        "stress_pnl_1p5x",
        "stress_r_1p5x",
        "spread_adjusted_pnl",
        "spread_adjusted_r",
    }
    missing = sorted(required - set(source.columns))
    if missing:
        raise ValueError(f"STAGE324_TIMELINE_COLUMNS_MISSING: {missing}")
    for column in ("entry_dt", "exit_dt"):
        source[column] = pd.to_datetime(source[column], errors="raise")
    for column in ("core", "balanced", "premium"):
        if source[column].dtype != bool:
            parsed = source[column].astype(str).str.lower().map(
                {"true": True, "false": False}
            )
            if parsed.isna().any():
                raise ValueError(f"BOOLEAN_PARSE_FAILED: {column}")
            source[column] = parsed
    if sorted(set(source.stage322_selected_lane.astype(str))) != [EXPECTED_LANE]:
        raise ValueError("STAGE322_SELECTED_LANE_COLUMN_MISMATCH")
    source = source.sort_values(["entry_dt", "exit_dt"], kind="mergesort").reset_index(drop=True)
    if len(source) > 1:
        current = source.entry_dt.iloc[1:].reset_index(drop=True)
        previous_exit = source.exit_dt.iloc[:-1].reset_index(drop=True)
        if bool((current < previous_exit).any()):
            raise ValueError("STAGE324_TIMELINE_OVERLAP")

    baseline_pnl_diff = float(
        np.max(
            np.abs(
                pd.to_numeric(source.stress_pnl_1p0x, errors="raise").to_numpy(float)
                - pd.to_numeric(source.spread_adjusted_pnl, errors="raise").to_numpy(float)
            )
        )
    )
    baseline_r_diff = float(
        np.max(
            np.abs(
                pd.to_numeric(source.stress_r_1p0x, errors="raise").to_numpy(float)
                - pd.to_numeric(source.spread_adjusted_r, errors="raise").to_numpy(float)
            )
        )
    )
    if baseline_pnl_diff > TOL or baseline_r_diff > TOL:
        raise ValueError("STAGE324_TIMELINE_BASELINE_PARITY_FAILED")

    source["router_group"] = source.apply(assign_group, axis=1)
    if not bool(source.router_group.isin(
        ["PREMIUM_INVOLVED", "BALANCED_WITHOUT_PREMIUM"]
    ).all()):
        raise ValueError("ROUTER_GROUP_ASSIGNMENT_FAILED")

    records: list[dict[str, Any]] = []
    taken_map: dict[str, pd.DataFrame] = {}
    trace_map: dict[str, pd.DataFrame] = {}
    for policy_name, policy in POLICIES.items():
        record, taken, trace = evaluate_policy(source, policy_name, policy)
        records.append(record)
        taken_map[policy_name] = taken
        trace_map[policy_name] = trace

    passing = [record for record in records if record["lead_gate"]["pass"]]
    passing.sort(key=ranking_key)
    selected = passing[0] if passing else None
    selected_policy = selected["policy_name"] if selected else None

    records.sort(
        key=lambda row: (
            -int(row["lead_gate"]["pass"]),
            *ranking_key(row),
        )
    )

    flat_rows: list[dict[str, Any]] = []
    for row in records:
        selection = row["selection_2024_2025"]
        selection_1p5 = row["selection_2024_2025_cost_1p5x"]
        display = row["display_2026"]
        flat_rows.append(
            {
                "policy_name": row["policy_name"],
                "lead_gate_pass": row["lead_gate"]["pass"],
                "trades_2024_2025": selection["trades"],
                "win_rate_2024_2025": selection["win_rate"],
                "profit_factor_2024_2025": selection[
                    "spread_adjusted_profit_factor"
                ],
                "total_r_2024_2025": selection["spread_adjusted_total_r"],
                "max_drawdown_r_2024_2025": selection[
                    "spread_adjusted_max_drawdown_r"
                ],
                "trades_2024": row["yearly"]["2024"]["trades"],
                "trades_2025": row["yearly"]["2025"]["trades"],
                "cost_1p5x_trades_2024_2025": selection_1p5["trades"],
                "cost_1p5x_win_rate_2024_2025": selection_1p5["win_rate"],
                "cost_1p5x_profit_factor_2024_2025": selection_1p5[
                    "spread_adjusted_profit_factor"
                ],
                "cost_1p5x_total_r_2024_2025": selection_1p5[
                    "spread_adjusted_total_r"
                ],
                "cost_1p5x_max_drawdown_r_2024_2025": selection_1p5[
                    "spread_adjusted_max_drawdown_r"
                ],
                "trades_2026_display_only": display["trades"],
                "win_rate_2026_display_only": display["win_rate"],
                "profit_factor_2026_display_only": display[
                    "spread_adjusted_profit_factor"
                ],
                "total_r_2026_display_only": display["spread_adjusted_total_r"],
                "max_drawdown_r_2026_display_only": display[
                    "spread_adjusted_max_drawdown_r"
                ],
            }
        )
    leaderboard_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(flat_rows).to_csv(
        leaderboard_path, index=False, encoding="utf-8-sig"
    )

    if selected_policy is None:
        pd.DataFrame(columns=["router_policy"]).to_csv(
            selected_trades_path, index=False, encoding="utf-8-sig"
        )
        pd.DataFrame(columns=["policy_name"]).to_csv(
            decision_trace_path, index=False, encoding="utf-8-sig"
        )
        decision = "NO_ASOF_MEMBERSHIP_ROUTER_RESEARCH_LEAD_FOUND"
    else:
        taken_map[selected_policy].to_csv(
            selected_trades_path, index=False, encoding="utf-8-sig"
        )
        trace_map[selected_policy].to_csv(
            decision_trace_path, index=False, encoding="utf-8-sig"
        )
        decision = "ASOF_RELATIVE_MEMBERSHIP_ROUTER_RESEARCH_LEAD_FOUND"

    static = next(row for row in records if row["policy_name"] == "STATIC_COMBINED")
    comparison = None
    if selected is not None:
        comparison = {
            "selected_policy": selected_policy,
            "selection_win_rate_improvement": float(
                selected["selection_2024_2025"]["win_rate"]
                - static["selection_2024_2025"]["win_rate"]
            ),
            "selection_profit_factor_improvement": float(
                selected["selection_2024_2025"]["spread_adjusted_profit_factor"]
                - static["selection_2024_2025"]["spread_adjusted_profit_factor"]
            ),
            "selection_trade_retention_ratio": float(
                selected["selection_2024_2025"]["trades"]
                / static["selection_2024_2025"]["trades"]
            ),
            "selection_total_r_retention_ratio": float(
                selected["selection_2024_2025"]["spread_adjusted_total_r"]
                / static["selection_2024_2025"]["spread_adjusted_total_r"]
            ),
            "display_2026_used_for_selection": False,
        }

    output = {
        "status": "GOLD_V3_325_ASOF_MEMBERSHIP_ROUTER_REPLAY_COMPLETE",
        "mode": "AUDIT_ONLY_RESOLVED_ONLY_ASOF_MEMBERSHIP_ROUTER_RESEARCH",
        "decision": decision,
        "source": {
            "stage324_json": str(stage324_json_path),
            "stage324_json_sha256": sha256_file(stage324_json_path),
            "stage324_timeline": str(timeline_path),
            "stage324_timeline_sha256": actual_sha,
        },
        "research_contract": {
            "selected_lane": EXPECTED_LANE,
            "selection_years": list(SELECTION_YEARS),
            "display_only_year": DISPLAY_ONLY_YEAR,
            "selection_and_ranking_do_not_use_2026": True,
            "fixed_policies": POLICIES,
            "router_information_source": (
                "all prior candidate outcomes after their exits; skipped candidates remain "
                "shadow-observed and are never used before resolution"
            ),
            "strict_asof_order": True,
            "new_raw_feature_thresholds_added": False,
            "numeric_tolerance": TOL,
            "lead_gate": LEAD_GATE,
        },
        "baseline_parity": {
            "max_pnl_diff": baseline_pnl_diff,
            "max_r_diff": baseline_r_diff,
        },
        "search": {
            "policy_count": len(POLICIES),
            "lead_pass_count": len(passing),
        },
        "selected": selected,
        "selected_vs_static": comparison,
        "leaderboard": records,
        "interpretation": {
            "purpose": (
                "Stage324 found that the stronger membership subgroup changes by period. "
                "Stage325 tests a fixed, resolved-only router that decides from prior "
                "closed candidate outcomes instead of permanently favoring one subgroup."
            ),
            "limits": (
                "This is still historical successor research. The 2026 replay is display "
                "only, no policy is promoted automatically, and Stage319 remains frozen."
            ),
        },
        "outputs": {
            "result_json": str(output_path),
            "leaderboard_csv": str(leaderboard_path),
            "selected_trades_csv": str(selected_trades_path),
            "decision_trace_csv": str(decision_trace_path),
            "leaderboard_sha256": sha256_file(leaderboard_path),
            "selected_trades_sha256": sha256_file(selected_trades_path),
            "decision_trace_sha256": sha256_file(decision_trace_path),
        },
        "promotion": {
            "performed": False,
            "stage319_contract": "UNCHANGED_FROZEN",
            "stage314_contract": "UNCHANGED_ACTIVE",
            "stage324_result": "UNCHANGED_RETAINED",
            "stage307_candidate": "UNCHANGED_RETAINED",
            "stage292_candidate_pool_changed": False,
        },
        "safety_flags": {
            "historical_trade_registry_only": True,
            "resolved_only_router_history": True,
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
