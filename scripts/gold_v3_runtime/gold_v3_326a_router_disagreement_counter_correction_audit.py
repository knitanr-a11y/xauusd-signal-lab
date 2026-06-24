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

EXPECTED_STATUS = "GOLD_V3_326_ROUTER_STATE_AND_LATENCY_ROBUSTNESS_AUDIT_COMPLETE"
EXPECTED_DECISION = "ROUTER_OPERATIONALLY_ROBUST_BUT_REQUIRES_PERSISTENT_STATE"
BASELINE_SCENARIO = "BASELINE_CONTINUOUS_TAKE_ALL"
SELECTION_YEARS = (2024, 2025)
DISPLAY_ONLY_YEAR = 2026
TOL = 1e-12


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage326-json", required=True)
    parser.add_argument("--stage326-scenarios", required=True)
    parser.add_argument("--stage326-trace", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--corrected-scenarios-csv", required=True)
    parser.add_argument("--corrected-trace-csv", required=True)
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


def parse_bool(series: pd.Series, column_name: str) -> pd.Series:
    if series.dtype == bool:
        return series
    parsed = series.astype(str).str.lower().map({"true": True, "false": False})
    if parsed.isna().any():
        raise ValueError(f"BOOLEAN_PARSE_FAILED: {column_name}")
    return parsed.astype(bool)


def main() -> int:
    args = parse_args()
    stage326_json_path = Path(args.stage326_json).expanduser().resolve()
    scenario_path = Path(args.stage326_scenarios).expanduser().resolve()
    trace_path = Path(args.stage326_trace).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()
    corrected_scenario_path = Path(args.corrected_scenarios_csv).expanduser().resolve()
    corrected_trace_path = Path(args.corrected_trace_csv).expanduser().resolve()

    report = json.loads(stage326_json_path.read_text(encoding="utf-8"))
    if report.get("status") != EXPECTED_STATUS:
        raise ValueError(f"STAGE326_STATUS_UNEXPECTED: {report.get('status')}")
    if report.get("decision") != EXPECTED_DECISION:
        raise ValueError(f"STAGE326_DECISION_UNEXPECTED: {report.get('decision')}")
    if report.get("operational_gate", {}).get("pass") is not True:
        raise ValueError("STAGE326_OPERATIONAL_GATE_NOT_PASS")
    if report.get("state_dependence", {}).get("detected") is not True:
        raise ValueError("STAGE326_STATE_DEPENDENCE_NOT_DETECTED")

    expected_scenario_sha = report.get("outputs", {}).get("scenario_sha256")
    actual_scenario_sha = sha256_file(scenario_path)
    if expected_scenario_sha != actual_scenario_sha:
        raise ValueError(
            "STAGE326_SCENARIO_SHA_MISMATCH: "
            f"expected={expected_scenario_sha} actual={actual_scenario_sha}"
        )
    expected_trace_sha = report.get("outputs", {}).get("decision_trace_sha256")
    actual_trace_sha = sha256_file(trace_path)
    if expected_trace_sha != actual_trace_sha:
        raise ValueError(
            "STAGE326_TRACE_SHA_MISMATCH: "
            f"expected={expected_trace_sha} actual={actual_trace_sha}"
        )

    scenarios = pd.read_csv(scenario_path, encoding="utf-8-sig")
    trace = pd.read_csv(trace_path, encoding="utf-8-sig")

    required_scenario_columns = {
        "scenario_name",
        "selection_take_disagreement_count_vs_baseline",
        "display_2026_take_disagreement_count_vs_baseline",
    }
    missing_scenario = sorted(required_scenario_columns - set(scenarios.columns))
    if missing_scenario:
        raise ValueError(f"STAGE326_SCENARIO_COLUMNS_MISSING: {missing_scenario}")

    required_trace_columns = {
        "scenario_name",
        "cost_view",
        "entry_dt",
        "entry_year",
        "take",
    }
    missing_trace = sorted(required_trace_columns - set(trace.columns))
    if missing_trace:
        raise ValueError(f"STAGE326_TRACE_COLUMNS_MISSING: {missing_trace}")

    trace["entry_dt"] = pd.to_datetime(trace["entry_dt"], errors="raise")
    trace["take"] = parse_bool(trace["take"], "take")
    trace_1p0 = trace[trace["cost_view"].eq("stress_r_1p0x")].copy()

    baseline = trace_1p0[
        trace_1p0["scenario_name"].eq(BASELINE_SCENARIO)
    ][["entry_dt", "take"]].copy()
    if baseline.empty:
        raise ValueError("BASELINE_TRACE_EMPTY")
    if baseline["entry_dt"].duplicated().any():
        raise ValueError("BASELINE_TRACE_ENTRY_DT_DUPLICATED")
    baseline = baseline.rename(columns={"take": "baseline_take"})

    corrected_trace = trace_1p0.merge(
        baseline,
        how="left",
        on="entry_dt",
        validate="many_to_one",
    )
    if corrected_trace["baseline_take"].isna().any():
        raise ValueError("BASELINE_TAKE_LOOKUP_MISSING")
    corrected_trace["baseline_take"] = parse_bool(
        corrected_trace["baseline_take"],
        "baseline_take",
    )
    corrected_trace["take_differs_from_baseline"] = (
        corrected_trace["take"] != corrected_trace["baseline_take"]
    )

    corrected_counts: dict[str, dict[str, int]] = {}
    for scenario_name, group in corrected_trace.groupby("scenario_name", sort=True):
        differs = group["take_differs_from_baseline"]
        selection_mask = group["entry_year"].isin(SELECTION_YEARS)
        display_mask = group["entry_year"].eq(DISPLAY_ONLY_YEAR)
        corrected_counts[str(scenario_name)] = {
            "selection_2024_2025": int((differs & selection_mask).sum()),
            "display_2026": int((differs & display_mask).sum()),
            "all_period": int(differs.sum()),
        }

    if BASELINE_SCENARIO not in corrected_counts:
        raise ValueError("BASELINE_SCENARIO_NOT_FOUND")
    baseline_counts = corrected_counts[BASELINE_SCENARIO]
    if baseline_counts != {
        "selection_2024_2025": 0,
        "display_2026": 0,
        "all_period": 0,
    }:
        raise ValueError(f"BASELINE_DISAGREEMENT_NOT_ZERO: {baseline_counts}")

    original_counts: dict[str, dict[str, int]] = {}
    corrected_scenarios = scenarios.copy()
    for index, row in corrected_scenarios.iterrows():
        scenario_name = str(row["scenario_name"])
        if scenario_name not in corrected_counts:
            raise ValueError(f"SCENARIO_MISSING_FROM_TRACE: {scenario_name}")
        original_counts[scenario_name] = {
            "selection_2024_2025": int(
                row["selection_take_disagreement_count_vs_baseline"]
            ),
            "display_2026": int(
                row["display_2026_take_disagreement_count_vs_baseline"]
            ),
        }
        corrected_scenarios.at[
            index,
            "selection_take_disagreement_count_vs_baseline",
        ] = corrected_counts[scenario_name]["selection_2024_2025"]
        corrected_scenarios.at[
            index,
            "display_2026_take_disagreement_count_vs_baseline",
        ] = corrected_counts[scenario_name]["display_2026"]

    metric_columns = [
        column
        for column in scenarios.columns
        if column
        not in {
            "selection_take_disagreement_count_vs_baseline",
            "display_2026_take_disagreement_count_vs_baseline",
        }
    ]
    if not scenarios[metric_columns].equals(corrected_scenarios[metric_columns]):
        raise ValueError("NON_COUNTER_SCENARIO_METRIC_CHANGED")

    corrected_scenario_path.parent.mkdir(parents=True, exist_ok=True)
    corrected_scenarios.to_csv(
        corrected_scenario_path,
        index=False,
        encoding="utf-8-sig",
    )
    corrected_trace = corrected_trace.sort_values(
        ["scenario_name", "entry_dt"],
        kind="mergesort",
    )
    corrected_trace.to_csv(
        corrected_trace_path,
        index=False,
        encoding="utf-8-sig",
    )

    correction_detected = any(
        original_counts[name]["selection_2024_2025"]
        != corrected_counts[name]["selection_2024_2025"]
        or original_counts[name]["display_2026"]
        != corrected_counts[name]["display_2026"]
        for name in original_counts
    )
    if not correction_detected:
        raise ValueError("NO_COUNTER_CORRECTION_WAS_NEEDED")

    output = {
        "status": "GOLD_V3_326A_ROUTER_DISAGREEMENT_COUNTER_CORRECTION_COMPLETE",
        "mode": "AUDIT_ONLY_REPORTING_COUNTER_CORRECTION",
        "decision": "STAGE326_CORE_DECISION_CONFIRMED_REPORTING_COUNTER_CORRECTED",
        "source": {
            "stage326_json": str(stage326_json_path),
            "stage326_json_sha256": sha256_file(stage326_json_path),
            "stage326_scenarios": str(scenario_path),
            "stage326_scenarios_sha256": actual_scenario_sha,
            "stage326_trace": str(trace_path),
            "stage326_trace_sha256": actual_trace_sha,
        },
        "root_cause": {
            "type": "PANDAS_COLUMN_METHOD_NAME_COLLISION",
            "detail": (
                "The Stage326 reporting expression used DataFrame.take attribute syntax. "
                "Because 'take' is also a pandas DataFrame method, every comparison was "
                "reported as different. Bracket column access is required."
            ),
            "affected_fields_only": [
                "selection_take_disagreement_count_vs_baseline",
                "display_2026_take_disagreement_count_vs_baseline",
            ],
            "operational_metrics_affected": False,
            "operational_gate_affected": False,
            "state_dependence_classification_affected": False,
        },
        "stage326_core_confirmation": {
            "status": report["status"],
            "decision": report["decision"],
            "operational_gate_pass": True,
            "state_dependence_detected": True,
            "baseline_selected_trade_parity": report["baseline_parity"][
                "selected_trades"
            ],
            "baseline_decision_trace_parity": report["baseline_parity"][
                "decision_trace"
            ],
        },
        "original_counts": original_counts,
        "corrected_counts": corrected_counts,
        "expected_corrected_selection_counts": {
            "BASELINE_CONTINUOUS_TAKE_ALL": 0,
            "ANNUAL_RESET_TAKE_ALL": 4,
            "SEMIANNUAL_RESET_TAKE_ALL": 6,
            "QUARTERLY_RESET_TAKE_ALL": 10,
            "CONTINUOUS_WARMUP_SKIP": 4,
            "CONTINUOUS_DELAY_1_CANDIDATE": 3,
            "CONTINUOUS_DELAY_2_CANDIDATES": 6,
        },
        "expected_corrected_display_2026_counts": {
            "BASELINE_CONTINUOUS_TAKE_ALL": 0,
            "ANNUAL_RESET_TAKE_ALL": 3,
            "SEMIANNUAL_RESET_TAKE_ALL": 3,
            "QUARTERLY_RESET_TAKE_ALL": 6,
            "CONTINUOUS_WARMUP_SKIP": 0,
            "CONTINUOUS_DELAY_1_CANDIDATE": 1,
            "CONTINUOUS_DELAY_2_CANDIDATES": 2,
        },
        "research_contract": {
            "selection_years": list(SELECTION_YEARS),
            "display_only_year": DISPLAY_ONLY_YEAR,
            "numeric_tolerance": TOL,
            "no_candidate_selection": True,
            "no_threshold_change": True,
            "no_source_metric_recalculation": True,
        },
        "outputs": {
            "result_json": str(output_path),
            "corrected_scenarios_csv": str(corrected_scenario_path),
            "corrected_trace_csv": str(corrected_trace_path),
            "corrected_scenarios_sha256": sha256_file(corrected_scenario_path),
            "corrected_trace_sha256": sha256_file(corrected_trace_path),
        },
        "promotion": {
            "performed": False,
            "stage319_contract": "UNCHANGED_FROZEN",
            "stage314_contract": "UNCHANGED_ACTIVE",
            "stage326_decision": "CONFIRMED_UNCHANGED",
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
