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

EXPECTED_STATUS = "GOLD_V3_325_ASOF_MEMBERSHIP_ROUTER_REPLAY_COMPLETE"
EXPECTED_DECISION = "ASOF_RELATIVE_MEMBERSHIP_ROUTER_RESEARCH_LEAD_FOUND"
EXPECTED_POLICY = "RELATIVE_TRAILING_MEAN_R_N2"
EXPECTED_LANE = "BALANCED_OR_PREMIUM"
SELECTION_YEARS = (2024, 2025)
DISPLAY_ONLY_YEAR = 2026
TOL = 1e-12

SCENARIOS: dict[str, dict[str, Any]] = {
    "BASELINE_CONTINUOUS_TAKE_ALL": {
        "reset": None,
        "warmup_take": True,
        "observation_delay_candidates": 0,
    },
    "ANNUAL_RESET_TAKE_ALL": {
        "reset": "year",
        "warmup_take": True,
        "observation_delay_candidates": 0,
    },
    "SEMIANNUAL_RESET_TAKE_ALL": {
        "reset": "halfyear",
        "warmup_take": True,
        "observation_delay_candidates": 0,
    },
    "QUARTERLY_RESET_TAKE_ALL": {
        "reset": "quarter",
        "warmup_take": True,
        "observation_delay_candidates": 0,
    },
    "CONTINUOUS_WARMUP_SKIP": {
        "reset": None,
        "warmup_take": False,
        "observation_delay_candidates": 0,
    },
    "CONTINUOUS_DELAY_1_CANDIDATE": {
        "reset": None,
        "warmup_take": True,
        "observation_delay_candidates": 1,
    },
    "CONTINUOUS_DELAY_2_CANDIDATES": {
        "reset": None,
        "warmup_take": True,
        "observation_delay_candidates": 2,
    },
}

REQUIRED_OPERATIONAL_SCENARIOS = (
    "ANNUAL_RESET_TAKE_ALL",
    "SEMIANNUAL_RESET_TAKE_ALL",
    "CONTINUOUS_WARMUP_SKIP",
    "CONTINUOUS_DELAY_1_CANDIDATE",
    "CONTINUOUS_DELAY_2_CANDIDATES",
)

OPERATIONAL_GATE = {
    "minimum_profit_factor": 1.25,
    "minimum_total_r_exclusive": 0.0,
    "maximum_drawdown_r": 3.5,
    "minimum_each_selection_year_total_r_exclusive": 0.0,
}

STATE_DEPENDENCE_THRESHOLDS = {
    "minimum_quarterly_reset_win_rate_drop": 0.10,
    "minimum_quarterly_reset_drawdown_increase_r": 1.0,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage325-json", required=True)
    parser.add_argument("--stage324-timeline", required=True)
    parser.add_argument("--stage325-selected", required=True)
    parser.add_argument("--stage325-trace", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--scenario-csv", required=True)
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


def parse_bool_column(frame: pd.DataFrame, column: str) -> None:
    if frame[column].dtype == bool:
        return
    parsed = frame[column].astype(str).str.lower().map(
        {"true": True, "false": False}
    )
    if parsed.isna().any():
        raise ValueError(f"BOOLEAN_PARSE_FAILED: {column}")
    frame[column] = parsed


def assign_router_group(row: pd.Series) -> str:
    if bool(row.premium):
        return "PREMIUM_INVOLVED"
    if bool(row.balanced):
        return "BALANCED_WITHOUT_PREMIUM"
    raise ValueError("SOURCE_TRADE_HAS_NO_ROUTER_GROUP")


def reset_period(dt: pd.Timestamp, reset: str | None) -> Any:
    if reset is None:
        return None
    if reset == "year":
        return int(dt.year)
    if reset == "halfyear":
        return (int(dt.year), 1 if int(dt.month) <= 6 else 2)
    if reset == "quarter":
        return (int(dt.year), (int(dt.month) - 1) // 3 + 1)
    raise ValueError(f"UNKNOWN_RESET_MODE: {reset}")


def simulate(
    source: pd.DataFrame,
    scenario_name: str,
    scenario: dict[str, Any],
    r_column: str,
    pnl_column: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    histories: dict[str, list[float]] = {
        "PREMIUM_INVOLVED": [],
        "BALANCED_WITHOUT_PREMIUM": [],
    }
    queue: list[tuple[str, float]] = []
    previous_period: Any = None
    taken_rows: list[dict[str, Any]] = []
    trace_rows: list[dict[str, Any]] = []

    reset_mode = scenario["reset"]
    warmup_take = bool(scenario["warmup_take"])
    delay = int(scenario["observation_delay_candidates"])

    for _, row in source.iterrows():
        entry_dt = pd.Timestamp(row.entry_dt)
        current_period = reset_period(entry_dt, reset_mode)
        if reset_mode is not None and previous_period is not None:
            if current_period != previous_period:
                histories = {
                    "PREMIUM_INVOLVED": [],
                    "BALANCED_WITHOUT_PREMIUM": [],
                }
                queue = []
        previous_period = current_period

        while len(queue) > delay:
            group, observed_r = queue.pop(0)
            histories[group].append(observed_r)

        group = str(row.router_group)
        other = (
            "BALANCED_WITHOUT_PREMIUM"
            if group == "PREMIUM_INVOLVED"
            else "PREMIUM_INVOLVED"
        )
        group_history_count = len(histories[group])
        other_history_count = len(histories[other])
        group_score: float | None = None
        other_score: float | None = None

        if group_history_count < 2 or other_history_count < 2:
            take = warmup_take
            reason = "WARMUP_TAKE_ALL" if take else "WARMUP_SKIP"
        else:
            group_score = float(np.mean(histories[group][-2:]))
            other_score = float(np.mean(histories[other][-2:]))
            take = group_score >= other_score
            reason = (
                "GROUP_SCORE_GE_OTHER" if take else "GROUP_SCORE_LT_OTHER"
            )

        trace_rows.append(
            {
                "scenario_name": scenario_name,
                "cost_view": r_column,
                "entry_dt": entry_dt,
                "exit_dt": pd.Timestamp(row.exit_dt),
                "entry_year": int(entry_dt.year),
                "router_group": group,
                "take": bool(take),
                "decision_reason": reason,
                "group_score_before_entry": group_score,
                "other_group_score_before_entry": other_score,
                "group_history_count_before_entry": group_history_count,
                "other_history_count_before_entry": other_history_count,
                "observation_delay_candidates": delay,
                "reset_mode": reset_mode or "continuous",
                "warmup_take": warmup_take,
            }
        )

        if take:
            item = row.to_dict()
            item["stage326_scenario"] = scenario_name
            item["spread_adjusted_r"] = float(row[r_column])
            item["spread_adjusted_pnl"] = float(row[pnl_column])
            taken_rows.append(item)

        queue.append((group, float(row[r_column])))

    taken = pd.DataFrame(taken_rows)
    if not taken.empty:
        taken = taken.sort_values(["entry_dt", "exit_dt"], kind="mergesort")
    trace = pd.DataFrame(trace_rows)
    return taken, trace


def compare_selected_parity(
    rebuilt: pd.DataFrame,
    expected: pd.DataFrame,
) -> dict[str, Any]:
    key = ["pair", "direction", "exit_profile", "entry_dt"]
    left = rebuilt.sort_values(key, kind="mergesort").reset_index(drop=True)
    right = expected.sort_values(key, kind="mergesort").reset_index(drop=True)
    keys_equal = bool(left[key].equals(right[key]))
    if not keys_equal:
        raise ValueError("BASELINE_SELECTED_ENTRY_KEYS_MISMATCH")
    if len(left) != len(right):
        raise ValueError("BASELINE_SELECTED_TRADE_COUNT_MISMATCH")
    pnl_diff = float(
        np.max(
            np.abs(
                pd.to_numeric(left.spread_adjusted_pnl, errors="raise").to_numpy(float)
                - pd.to_numeric(right.spread_adjusted_pnl, errors="raise").to_numpy(float)
            )
        )
    )
    r_diff = float(
        np.max(
            np.abs(
                pd.to_numeric(left.spread_adjusted_r, errors="raise").to_numpy(float)
                - pd.to_numeric(right.spread_adjusted_r, errors="raise").to_numpy(float)
            )
        )
    )
    if pnl_diff > TOL or r_diff > TOL:
        raise ValueError(
            "BASELINE_SELECTED_NUMERIC_PARITY_FAILED: "
            f"max_pnl_diff={pnl_diff} max_r_diff={r_diff}"
        )
    return {
        "entry_keys_equal": keys_equal,
        "trade_count": int(len(left)),
        "max_pnl_diff": pnl_diff,
        "max_r_diff": r_diff,
    }


def max_optional_diff(left: pd.Series, right: pd.Series) -> float:
    left_values = pd.to_numeric(left, errors="coerce").to_numpy(float)
    right_values = pd.to_numeric(right, errors="coerce").to_numpy(float)
    if not np.array_equal(np.isnan(left_values), np.isnan(right_values)):
        raise ValueError("BASELINE_TRACE_NAN_PATTERN_MISMATCH")
    finite = ~(np.isnan(left_values) | np.isnan(right_values))
    if not bool(finite.any()):
        return 0.0
    return float(np.max(np.abs(left_values[finite] - right_values[finite])))


def compare_trace_parity(
    rebuilt: pd.DataFrame,
    expected: pd.DataFrame,
) -> dict[str, Any]:
    left = rebuilt.sort_values("entry_dt", kind="mergesort").reset_index(drop=True)
    right = expected.sort_values("entry_dt", kind="mergesort").reset_index(drop=True)
    if len(left) != len(right):
        raise ValueError("BASELINE_TRACE_COUNT_MISMATCH")
    exact_columns = [
        "entry_dt",
        "router_group",
        "take",
        "decision_reason",
    ]
    for column in exact_columns:
        if not bool(left[column].equals(right[column])):
            raise ValueError(f"BASELINE_TRACE_EXACT_MISMATCH: {column}")
    group_score_diff = max_optional_diff(
        left.group_score_before_entry,
        right.group_score_before_entry,
    )
    other_score_diff = max_optional_diff(
        left.other_group_score_before_entry,
        right.other_group_score_before_entry,
    )
    if group_score_diff > TOL or other_score_diff > TOL:
        raise ValueError(
            "BASELINE_TRACE_SCORE_PARITY_FAILED: "
            f"group={group_score_diff} other={other_score_diff}"
        )
    return {
        "row_count": int(len(left)),
        "exact_columns_equal": True,
        "max_group_score_diff": group_score_diff,
        "max_other_score_diff": other_score_diff,
    }


def build_record(
    source: pd.DataFrame,
    scenario_name: str,
    scenario: dict[str, Any],
) -> tuple[dict[str, Any], pd.DataFrame, pd.DataFrame]:
    taken_1p0, trace_1p0 = simulate(
        source,
        scenario_name,
        scenario,
        "stress_r_1p0x",
        "stress_pnl_1p0x",
    )
    taken_1p5, trace_1p5 = simulate(
        source,
        scenario_name,
        scenario,
        "stress_r_1p5x",
        "stress_pnl_1p5x",
    )
    selection_1p0 = taken_1p0[
        taken_1p0.entry_dt.dt.year.isin(SELECTION_YEARS)
    ].copy()
    selection_1p5 = taken_1p5[
        taken_1p5.entry_dt.dt.year.isin(SELECTION_YEARS)
    ].copy()
    record = {
        "scenario_name": scenario_name,
        "scenario_definition": scenario,
        "selection_2024_2025": summarize(selection_1p0),
        "selection_2024_2025_cost_1p5x": summarize(selection_1p5),
        "yearly": yearly(taken_1p0),
        "yearly_cost_1p5x": yearly(taken_1p5),
    }
    combined_trace = pd.concat([trace_1p0, trace_1p5], ignore_index=True)
    return record, taken_1p0, combined_trace


def pf_number(summary: dict[str, Any]) -> float:
    value = summary.get("spread_adjusted_profit_factor")
    return float("inf") if value is None else float(value)


def operational_checks(record: dict[str, Any]) -> dict[str, bool]:
    checks: dict[str, bool] = {}
    for suffix, summary_key, yearly_key in (
        ("1p0x", "selection_2024_2025", "yearly"),
        ("1p5x", "selection_2024_2025_cost_1p5x", "yearly_cost_1p5x"),
    ):
        summary = record[summary_key]
        yearly_rows = record[yearly_key]
        checks[f"{suffix}_minimum_profit_factor"] = (
            pf_number(summary) >= float(OPERATIONAL_GATE["minimum_profit_factor"])
        )
        checks[f"{suffix}_minimum_total_r"] = (
            float(summary["spread_adjusted_total_r"])
            > float(OPERATIONAL_GATE["minimum_total_r_exclusive"])
        )
        checks[f"{suffix}_maximum_drawdown_r"] = (
            float(summary["spread_adjusted_max_drawdown_r"])
            <= float(OPERATIONAL_GATE["maximum_drawdown_r"])
        )
        checks[f"{suffix}_each_selection_year_positive"] = all(
            float(yearly_rows[str(year)]["spread_adjusted_total_r"])
            > float(
                OPERATIONAL_GATE[
                    "minimum_each_selection_year_total_r_exclusive"
                ]
            )
            for year in SELECTION_YEARS
        )
    return checks


def main() -> int:
    args = parse_args()
    stage325_json_path = Path(args.stage325_json).expanduser().resolve()
    stage324_timeline_path = Path(args.stage324_timeline).expanduser().resolve()
    stage325_selected_path = Path(args.stage325_selected).expanduser().resolve()
    stage325_trace_path = Path(args.stage325_trace).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()
    scenario_path = Path(args.scenario_csv).expanduser().resolve()
    decision_trace_path = Path(args.decision_trace_csv).expanduser().resolve()

    stage325 = json.loads(stage325_json_path.read_text(encoding="utf-8"))
    if stage325.get("status") != EXPECTED_STATUS:
        raise ValueError(f"STAGE325_STATUS_UNEXPECTED: {stage325.get('status')}")
    if stage325.get("decision") != EXPECTED_DECISION:
        raise ValueError(f"STAGE325_DECISION_UNEXPECTED: {stage325.get('decision')}")
    if stage325.get("selected", {}).get("policy_name") != EXPECTED_POLICY:
        raise ValueError("STAGE325_SELECTED_POLICY_UNEXPECTED")
    if stage325.get("research_contract", {}).get("selected_lane") != EXPECTED_LANE:
        raise ValueError("STAGE325_SELECTED_LANE_UNEXPECTED")

    expected_timeline_sha = stage325.get("source", {}).get(
        "stage324_timeline_sha256"
    )
    actual_timeline_sha = sha256_file(stage324_timeline_path)
    if expected_timeline_sha != actual_timeline_sha:
        raise ValueError("STAGE324_TIMELINE_SHA_MISMATCH")
    expected_selected_sha = stage325.get("outputs", {}).get(
        "selected_trades_sha256"
    )
    actual_selected_sha = sha256_file(stage325_selected_path)
    if expected_selected_sha != actual_selected_sha:
        raise ValueError("STAGE325_SELECTED_SHA_MISMATCH")
    expected_trace_sha = stage325.get("outputs", {}).get(
        "decision_trace_sha256"
    )
    actual_trace_sha = sha256_file(stage325_trace_path)
    if expected_trace_sha != actual_trace_sha:
        raise ValueError("STAGE325_TRACE_SHA_MISMATCH")

    source = pd.read_csv(stage324_timeline_path, encoding="utf-8-sig")
    selected_expected = pd.read_csv(stage325_selected_path, encoding="utf-8-sig")
    trace_expected = pd.read_csv(stage325_trace_path, encoding="utf-8-sig")

    required_source = {
        "pair",
        "direction",
        "exit_profile",
        "entry_dt",
        "exit_dt",
        "balanced",
        "premium",
        "stress_pnl_1p0x",
        "stress_r_1p0x",
        "stress_pnl_1p5x",
        "stress_r_1p5x",
    }
    missing = sorted(required_source - set(source.columns))
    if missing:
        raise ValueError(f"STAGE324_TIMELINE_COLUMNS_MISSING: {missing}")
    for frame in (source, selected_expected, trace_expected):
        for column in ("entry_dt", "exit_dt"):
            if column in frame.columns:
                frame[column] = pd.to_datetime(frame[column], errors="raise")
    for column in ("balanced", "premium"):
        parse_bool_column(source, column)
    parse_bool_column(trace_expected, "take")

    source = source.sort_values(["entry_dt", "exit_dt"], kind="mergesort").reset_index(drop=True)
    if len(source) > 1:
        current = source.entry_dt.iloc[1:].reset_index(drop=True)
        previous_exit = source.exit_dt.iloc[:-1].reset_index(drop=True)
        if bool((current < previous_exit).any()):
            raise ValueError("STAGE324_TIMELINE_OVERLAP")
    source["router_group"] = source.apply(assign_router_group, axis=1)

    baseline_record, baseline_taken, baseline_trace_both = build_record(
        source,
        "BASELINE_CONTINUOUS_TAKE_ALL",
        SCENARIOS["BASELINE_CONTINUOUS_TAKE_ALL"],
    )
    baseline_trace = baseline_trace_both[
        baseline_trace_both.cost_view.eq("stress_r_1p0x")
    ].copy()
    selected_parity = compare_selected_parity(
        baseline_taken,
        selected_expected,
    )
    trace_parity = compare_trace_parity(
        baseline_trace,
        trace_expected,
    )

    records: list[dict[str, Any]] = []
    all_traces: list[pd.DataFrame] = []
    baseline_take_map = baseline_trace.set_index("entry_dt")["take"]
    for scenario_name, scenario in SCENARIOS.items():
        if scenario_name == "BASELINE_CONTINUOUS_TAKE_ALL":
            record = baseline_record
            trace = baseline_trace_both
        else:
            record, _, trace = build_record(source, scenario_name, scenario)
        trace_1p0 = trace[trace.cost_view.eq("stress_r_1p0x")].copy()
        trace_1p0["baseline_take"] = trace_1p0.entry_dt.map(baseline_take_map)
        trace_1p0["take_differs_from_baseline"] = (
            trace_1p0.take != trace_1p0.baseline_take
        )
        record["selection_take_disagreement_count_vs_baseline"] = int(
            trace_1p0[
                trace_1p0.entry_year.isin(SELECTION_YEARS)
            ].take_differs_from_baseline.sum()
        )
        record["display_2026_take_disagreement_count_vs_baseline"] = int(
            trace_1p0[
                trace_1p0.entry_year.eq(DISPLAY_ONLY_YEAR)
            ].take_differs_from_baseline.sum()
        )
        records.append(record)
        all_traces.append(trace)

    record_map = {record["scenario_name"]: record for record in records}
    required_results: dict[str, Any] = {}
    all_required_pass = True
    for scenario_name in REQUIRED_OPERATIONAL_SCENARIOS:
        checks = operational_checks(record_map[scenario_name])
        passed = bool(all(checks.values()))
        all_required_pass = all_required_pass and passed
        required_results[scenario_name] = {
            "pass": passed,
            "checks": checks,
        }

    baseline_selection = record_map["BASELINE_CONTINUOUS_TAKE_ALL"][
        "selection_2024_2025"
    ]
    quarterly_selection = record_map["QUARTERLY_RESET_TAKE_ALL"][
        "selection_2024_2025"
    ]
    win_rate_drop = float(
        baseline_selection["win_rate"] - quarterly_selection["win_rate"]
    )
    drawdown_increase = float(
        quarterly_selection["spread_adjusted_max_drawdown_r"]
        - baseline_selection["spread_adjusted_max_drawdown_r"]
    )
    state_dependence_checks = {
        "quarterly_reset_win_rate_drop": win_rate_drop
        >= float(
            STATE_DEPENDENCE_THRESHOLDS[
                "minimum_quarterly_reset_win_rate_drop"
            ]
        ),
        "quarterly_reset_drawdown_increase": drawdown_increase
        >= float(
            STATE_DEPENDENCE_THRESHOLDS[
                "minimum_quarterly_reset_drawdown_increase_r"
            ]
        ),
    }
    state_dependence_detected = bool(any(state_dependence_checks.values()))

    if all_required_pass and state_dependence_detected:
        decision = "ROUTER_OPERATIONALLY_ROBUST_BUT_REQUIRES_PERSISTENT_STATE"
    elif all_required_pass:
        decision = "ROUTER_OPERATIONALLY_ROBUST"
    else:
        decision = "ROUTER_OPERATIONAL_ROBUSTNESS_NOT_SUPPORTED"

    flat_rows: list[dict[str, Any]] = []
    for record in records:
        selection = record["selection_2024_2025"]
        selection_1p5 = record["selection_2024_2025_cost_1p5x"]
        display = record["yearly"][str(DISPLAY_ONLY_YEAR)]
        flat_rows.append(
            {
                "scenario_name": record["scenario_name"],
                "reset_mode": record["scenario_definition"]["reset"] or "continuous",
                "warmup_take": record["scenario_definition"]["warmup_take"],
                "observation_delay_candidates": record["scenario_definition"][
                    "observation_delay_candidates"
                ],
                "trades_2024_2025": selection["trades"],
                "win_rate_2024_2025": selection["win_rate"],
                "profit_factor_2024_2025": selection[
                    "spread_adjusted_profit_factor"
                ],
                "total_r_2024_2025": selection["spread_adjusted_total_r"],
                "max_drawdown_r_2024_2025": selection[
                    "spread_adjusted_max_drawdown_r"
                ],
                "trades_2024": record["yearly"]["2024"]["trades"],
                "total_r_2024": record["yearly"]["2024"][
                    "spread_adjusted_total_r"
                ],
                "trades_2025": record["yearly"]["2025"]["trades"],
                "total_r_2025": record["yearly"]["2025"][
                    "spread_adjusted_total_r"
                ],
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
                "selection_take_disagreement_count_vs_baseline": record[
                    "selection_take_disagreement_count_vs_baseline"
                ],
                "trades_2026_display_only": display["trades"],
                "win_rate_2026_display_only": display["win_rate"],
                "profit_factor_2026_display_only": display[
                    "spread_adjusted_profit_factor"
                ],
                "total_r_2026_display_only": display[
                    "spread_adjusted_total_r"
                ],
                "max_drawdown_r_2026_display_only": display[
                    "spread_adjusted_max_drawdown_r"
                ],
                "display_2026_take_disagreement_count_vs_baseline": record[
                    "display_2026_take_disagreement_count_vs_baseline"
                ],
            }
        )
    scenario_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(flat_rows).to_csv(
        scenario_path,
        index=False,
        encoding="utf-8-sig",
    )
    all_trace = pd.concat(all_traces, ignore_index=True)
    all_trace.to_csv(
        decision_trace_path,
        index=False,
        encoding="utf-8-sig",
    )

    output = {
        "status": "GOLD_V3_326_ROUTER_STATE_AND_LATENCY_ROBUSTNESS_AUDIT_COMPLETE",
        "mode": "AUDIT_ONLY_FIXED_ROUTER_OPERATIONAL_STRESS",
        "decision": decision,
        "source": {
            "stage325_json": str(stage325_json_path),
            "stage325_json_sha256": sha256_file(stage325_json_path),
            "stage324_timeline": str(stage324_timeline_path),
            "stage324_timeline_sha256": actual_timeline_sha,
            "stage325_selected": str(stage325_selected_path),
            "stage325_selected_sha256": actual_selected_sha,
            "stage325_trace": str(stage325_trace_path),
            "stage325_trace_sha256": actual_trace_sha,
        },
        "research_contract": {
            "fixed_policy": EXPECTED_POLICY,
            "selected_lane": EXPECTED_LANE,
            "selection_years": list(SELECTION_YEARS),
            "display_only_year": DISPLAY_ONLY_YEAR,
            "selection_gate_does_not_use_2026": True,
            "fixed_scenarios": SCENARIOS,
            "required_operational_scenarios": list(
                REQUIRED_OPERATIONAL_SCENARIOS
            ),
            "operational_gate": OPERATIONAL_GATE,
            "state_dependence_thresholds": STATE_DEPENDENCE_THRESHOLDS,
            "new_raw_feature_thresholds_added": False,
            "router_policy_retuned": False,
            "numeric_tolerance": TOL,
        },
        "baseline_parity": {
            "selected_trades": selected_parity,
            "decision_trace": trace_parity,
        },
        "operational_gate": {
            "pass": all_required_pass,
            "scenario_results": required_results,
        },
        "state_dependence": {
            "detected": state_dependence_detected,
            "checks": state_dependence_checks,
            "selection_win_rate_drop_under_quarterly_reset": win_rate_drop,
            "selection_drawdown_increase_r_under_quarterly_reset": drawdown_increase,
        },
        "scenarios": records,
        "interpretation": {
            "purpose": (
                "Stage325 found a high-win-rate N2 router. Stage326 tests whether the "
                "same fixed policy survives realistic state resets, warmup handling, "
                "and one- or two-candidate observation delays."
            ),
            "persistent_state_note": (
                "If state dependence is detected, the router must persist both subgroup "
                "histories across sessions and restarts. Quarterly state resets are not "
                "equivalent to the audited policy."
            ),
            "limits": (
                "This is historical successor research. The 2026 rows remain display "
                "only, no policy is promoted automatically, and Stage319 remains frozen."
            ),
        },
        "outputs": {
            "result_json": str(output_path),
            "scenario_csv": str(scenario_path),
            "decision_trace_csv": str(decision_trace_path),
            "scenario_sha256": sha256_file(scenario_path),
            "decision_trace_sha256": sha256_file(decision_trace_path),
        },
        "promotion": {
            "performed": False,
            "stage319_contract": "UNCHANGED_FROZEN",
            "stage314_contract": "UNCHANGED_ACTIVE",
            "stage325_result": "UNCHANGED_RETAINED",
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
