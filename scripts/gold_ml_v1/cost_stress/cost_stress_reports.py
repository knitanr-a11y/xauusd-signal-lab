from __future__ import annotations

import math
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from cost_stress_contract import BRIDGE, RAW, Scenario

BRIDGE_BASELINE_SCENARIO = "BASELINE_EXACT_CORE_ONLY"
BRIDGE_BLOCKER = "PRE_2023_INDICATOR_STATE_AND_PRICE_FIELDS_UNAVAILABLE_FOR_EXACT_COST_REPLAY"


def metrics(frame: pd.DataFrame) -> dict[str, Any]:
    ordered = frame.sort_values("decision_close_time", kind="mergesort")
    values = pd.to_numeric(ordered["r_value_stressed"], errors="raise").astype(float)
    positive = float(values[values > 0].sum())
    negative = float(-values[values < 0].sum())
    if negative > 0:
        profit_factor = positive / negative
        state = "FINITE"
    elif positive > 0:
        profit_factor = math.inf
        state = "INFINITE_NO_LOSS"
    else:
        profit_factor = math.nan
        state = "UNDEFINED_NO_GAIN_OR_LOSS"
    equity = values.cumsum().to_numpy(float)
    peaks = np.maximum.accumulate(np.r_[0.0, equity])
    drawdown = peaks[1:] - equity if len(equity) else np.array([], dtype=float)
    return {
        "trade_count": int(len(values)),
        "wins": int((values > 0).sum()),
        "win_rate": float((values > 0).mean()) if len(values) else math.nan,
        "profit_factor": float(profit_factor),
        "profit_factor_state": state,
        "mean_r": float(values.mean()) if len(values) else math.nan,
        "median_r": float(values.median()) if len(values) else math.nan,
        "total_r": float(values.sum()),
        "max_drawdown_r": float(drawdown.max()) if len(drawdown) else 0.0,
        "first_decision_close_time": ordered["decision_close_time"].iloc[0] if len(ordered) else None,
        "last_decision_close_time": ordered["decision_close_time"].iloc[-1] if len(ordered) else None,
    }


def worst_periods(frame: pd.DataFrame) -> dict[str, Any]:
    temp = frame[["decision_close_time", "r_value_stressed"]].copy()
    temp["year"] = pd.to_datetime(temp["decision_close_time"]).dt.year
    temp["month"] = pd.to_datetime(temp["decision_close_time"]).dt.to_period("M").astype(str)
    years = temp.groupby("year")["r_value_stressed"].agg(["mean", "sum"])
    months = temp.groupby("month")["r_value_stressed"].agg(["mean", "sum"])
    worst_year = years["mean"].idxmin()
    worst_month = months["mean"].idxmin()
    return {
        "worst_year": int(worst_year),
        "worst_year_mean_r": float(years.loc[worst_year, "mean"]),
        "worst_year_total_r": float(years.loc[worst_year, "sum"]),
        "worst_month": str(worst_month),
        "worst_month_mean_r": float(months.loc[worst_month, "mean"]),
        "worst_month_total_r": float(months.loc[worst_month, "sum"]),
    }


def gate_status(item: dict[str, Any], gate: dict[str, Any]) -> str:
    profit_factor = float(item["profit_factor"])
    profit_factor_ok = math.isinf(profit_factor) or (
        math.isfinite(profit_factor) and profit_factor >= float(gate["minimum_profit_factor"])
    )
    passed = (
        int(item["trade_count"]) >= int(gate["minimum_trade_count"])
        and profit_factor_ok
        and float(item["mean_r"]) > float(gate["minimum_mean_r_exclusive"])
    )
    return "PASS" if passed else "FAIL"


def candidate_summary(trades: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    baseline_id = config["scenario_grid"]["baseline_scenario_id"]
    gate = config["stress_gate"]
    for keys, frame in trades.groupby(
        ["candidate_id", "lineage_id", "population", "scenario_id"], sort=True
    ):
        candidate_id, lineage_id, population, scenario_id = keys
        first = frame.iloc[0]
        item = {
            "candidate_id": candidate_id,
            "lineage_id": lineage_id,
            "population": population,
            "scenario_id": scenario_id,
            "spread_multiplier": float(first["spread_multiplier"]),
            "slippage_points_per_side": int(first["slippage_points_per_side"]),
            **metrics(frame),
            **worst_periods(frame),
            "stress_replay_status": "CALCULATED_EXACT_M1_REPLAY",
            "blocker": "",
        }
        item["stress_gate_status"] = gate_status(item, gate)
        rows.append(item)
    result = pd.DataFrame(rows)
    baseline = result[result["scenario_id"] == baseline_id][
        [
            "candidate_id",
            "population",
            "mean_r",
            "median_r",
            "profit_factor",
            "total_r",
            "max_drawdown_r",
        ]
    ].rename(
        columns={
            "mean_r": "baseline_mean_r",
            "median_r": "baseline_median_r",
            "profit_factor": "baseline_profit_factor",
            "total_r": "baseline_total_r",
            "max_drawdown_r": "baseline_max_drawdown_r",
        }
    )
    result = result.merge(
        baseline,
        on=["candidate_id", "population"],
        how="left",
        validate="many_to_one",
    )
    for name in ("mean_r", "median_r", "total_r", "max_drawdown_r"):
        result[f"delta_{name}_vs_baseline"] = result[name] - result[f"baseline_{name}"]
    result["delta_profit_factor_vs_baseline"] = (
        result["profit_factor"] - result["baseline_profit_factor"]
    )
    return result.sort_values(
        ["population", "candidate_id", "spread_multiplier", "slippage_points_per_side"],
        kind="mergesort",
    )


def bridge_trade_audit(registry: pd.DataFrame) -> pd.DataFrame:
    bridge = registry[registry["trade_core_source"] == BRIDGE].copy()
    bridge["population"] = BRIDGE
    bridge["scenario_id"] = BRIDGE_BASELINE_SCENARIO
    bridge["spread_multiplier"] = np.nan
    bridge["slippage_points_per_side"] = np.nan
    bridge["baseline_r"] = pd.to_numeric(bridge["r_value"], errors="raise").astype(float)
    bridge["r_value_stressed"] = bridge["baseline_r"]
    bridge["stress_replay_status"] = "NOT_CALCULATED_AUDIT_ONLY"
    bridge["blocker"] = BRIDGE_BLOCKER
    return bridge


def bridge_candidate_summary(bridge_trades: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for keys, frame in bridge_trades.groupby(
        ["candidate_id", "lineage_id", "population", "scenario_id"], sort=True
    ):
        candidate_id, lineage_id, population, scenario_id = keys
        item = {
            "candidate_id": candidate_id,
            "lineage_id": lineage_id,
            "population": population,
            "scenario_id": scenario_id,
            "spread_multiplier": np.nan,
            "slippage_points_per_side": np.nan,
            **metrics(frame),
            **worst_periods(frame),
            "stress_replay_status": "NOT_CALCULATED_AUDIT_ONLY",
            "blocker": BRIDGE_BLOCKER,
            "stress_gate_status": "NOT_ELIGIBLE_AUDIT_ONLY",
        }
        for name in ("mean_r", "median_r", "profit_factor", "total_r", "max_drawdown_r"):
            item[f"baseline_{name}"] = item[name]
            item[f"delta_{name}_vs_baseline"] = 0.0
        rows.append(item)
    return pd.DataFrame(rows).sort_values(["candidate_id"], kind="mergesort")


def year_summary(trades: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    work = trades.copy()
    work["year"] = pd.to_datetime(work["decision_close_time"]).dt.year
    rows: list[dict[str, Any]] = []
    for keys, frame in work.groupby(
        ["candidate_id", "lineage_id", "population", "scenario_id", "year"], sort=True
    ):
        candidate_id, lineage_id, population, scenario_id, year = keys
        first = frame.iloc[0]
        rows.append(
            {
                "candidate_id": candidate_id,
                "lineage_id": lineage_id,
                "population": population,
                "scenario_id": scenario_id,
                "year": int(year),
                "spread_multiplier": float(first["spread_multiplier"]),
                "slippage_points_per_side": int(first["slippage_points_per_side"]),
                **metrics(frame),
                "stress_replay_status": "CALCULATED_EXACT_M1_REPLAY",
                "blocker": "",
            }
        )
    result = pd.DataFrame(rows)
    baseline_id = config["scenario_grid"]["baseline_scenario_id"]
    baseline = result[result["scenario_id"] == baseline_id][
        ["candidate_id", "population", "year", "mean_r", "total_r", "profit_factor"]
    ].rename(
        columns={
            "mean_r": "baseline_mean_r",
            "total_r": "baseline_total_r",
            "profit_factor": "baseline_profit_factor",
        }
    )
    result = result.merge(
        baseline,
        on=["candidate_id", "population", "year"],
        how="left",
        validate="many_to_one",
    )
    result["delta_mean_r_vs_baseline"] = result["mean_r"] - result["baseline_mean_r"]
    result["delta_total_r_vs_baseline"] = result["total_r"] - result["baseline_total_r"]
    result["delta_profit_factor_vs_baseline"] = (
        result["profit_factor"] - result["baseline_profit_factor"]
    )
    return result.sort_values(
        ["population", "candidate_id", "scenario_id", "year"], kind="mergesort"
    )


def bridge_year_summary(bridge_trades: pd.DataFrame) -> pd.DataFrame:
    work = bridge_trades.copy()
    work["year"] = pd.to_datetime(work["decision_close_time"]).dt.year
    rows: list[dict[str, Any]] = []
    for keys, frame in work.groupby(
        ["candidate_id", "lineage_id", "population", "scenario_id", "year"], sort=True
    ):
        candidate_id, lineage_id, population, scenario_id, year = keys
        item = {
            "candidate_id": candidate_id,
            "lineage_id": lineage_id,
            "population": population,
            "scenario_id": scenario_id,
            "year": int(year),
            "spread_multiplier": np.nan,
            "slippage_points_per_side": np.nan,
            **metrics(frame),
            "stress_replay_status": "NOT_CALCULATED_AUDIT_ONLY",
            "blocker": BRIDGE_BLOCKER,
        }
        item["baseline_mean_r"] = item["mean_r"]
        item["baseline_total_r"] = item["total_r"]
        item["baseline_profit_factor"] = item["profit_factor"]
        item["delta_mean_r_vs_baseline"] = 0.0
        item["delta_total_r_vs_baseline"] = 0.0
        item["delta_profit_factor_vs_baseline"] = 0.0
        rows.append(item)
    return pd.DataFrame(rows).sort_values(["candidate_id", "year"], kind="mergesort")


def lineage_summary(candidate: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    groups = ["lineage_id", "population", "scenario_id"]
    for keys, frame in candidate.groupby(groups, sort=True):
        lineage_id, population, scenario_id = keys
        finite = (
            pd.to_numeric(frame["profit_factor"], errors="coerce")
            .replace([np.inf, -np.inf], np.nan)
            .dropna()
        )
        first = frame.iloc[0]
        rows.append(
            {
                "lineage_id": lineage_id,
                "population": population,
                "scenario_id": scenario_id,
                "spread_multiplier": first.get("spread_multiplier", np.nan),
                "slippage_points_per_side": first.get("slippage_points_per_side", np.nan),
                "candidate_count": int(len(frame)),
                "candidate_ids": "|".join(sorted(frame["candidate_id"].astype(str))),
                "aggregation_contract": "NO_TRADE_POOLING_CANDIDATE_LEVEL_RANGES_ONLY",
                "min_trade_count_per_candidate": int(frame["trade_count"].min()),
                "max_trade_count_per_candidate": int(frame["trade_count"].max()),
                "min_win_rate": float(frame["win_rate"].min()),
                "median_win_rate": float(frame["win_rate"].median()),
                "max_win_rate": float(frame["win_rate"].max()),
                "min_profit_factor_finite": float(finite.min()) if len(finite) else math.nan,
                "median_profit_factor_finite": float(finite.median()) if len(finite) else math.nan,
                "max_profit_factor_finite": float(finite.max()) if len(finite) else math.nan,
                "infinite_profit_factor_candidates": int(
                    np.isinf(pd.to_numeric(frame["profit_factor"], errors="coerce")).sum()
                ),
                "min_mean_r": float(frame["mean_r"].min()),
                "median_mean_r": float(frame["mean_r"].median()),
                "max_mean_r": float(frame["mean_r"].max()),
                "candidate_gate_pass": int((frame["stress_gate_status"] == "PASS").sum()),
                "candidate_gate_fail": int((frame["stress_gate_status"] == "FAIL").sum()),
                "bridge_gate_not_eligible": int(
                    (frame["stress_gate_status"] == "NOT_ELIGIBLE_AUDIT_ONLY").sum()
                ),
                "stress_replay_status": first.get("stress_replay_status", ""),
                "blocker": first.get("blocker", ""),
            }
        )
    return pd.DataFrame(rows).sort_values(
        ["population", "lineage_id", "scenario_id"], kind="mergesort"
    )


def overall_gate(candidate: pd.DataFrame, scenario_count: int) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for candidate_id, frame in candidate[candidate["population"] == RAW].groupby(
        "candidate_id", sort=True
    ):
        if len(frame) != scenario_count:
            raise RuntimeError(f"Scenario count mismatch: {candidate_id}")
        passed = int((frame["stress_gate_status"] == "PASS").sum())
        failed = int((frame["stress_gate_status"] == "FAIL").sum())
        rows.append(
            {
                "candidate_id": candidate_id,
                "scenario_count": scenario_count,
                "scenario_pass_count": passed,
                "scenario_fail_count": failed,
                "candidate_overall_stress_gate": "PASS" if passed == scenario_count else "FAIL",
                "automatic_promotion": False,
                "automatic_registration": False,
            }
        )
    return pd.DataFrame(rows)


def json_clean(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): json_clean(item) for key, item in value.items()}
    if isinstance(value, list):
        return [json_clean(item) for item in value]
    if isinstance(value, (pd.Timestamp, datetime)):
        return value.isoformat(sep=" ")
    if isinstance(value, np.generic):
        value = value.item()
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def records(frame: pd.DataFrame) -> list[dict[str, Any]]:
    return [json_clean(item) for item in frame.to_dict(orient="records")]


def write_csvs(
    output: Path,
    trade_audit: pd.DataFrame,
    candidate: pd.DataFrame,
    year: pd.DataFrame,
    lineage: pd.DataFrame,
    gate: pd.DataFrame,
) -> None:
    trade_audit.to_csv(output / "cost_stress_trade_level.csv", index=False)
    candidate[candidate.population == RAW].to_csv(
        output / "candidate_cost_stress_raw_reconstructed.csv", index=False
    )
    candidate[candidate.population == BRIDGE].to_csv(
        output / "candidate_cost_stress_warmup_bridge_exact.csv", index=False
    )
    year[year.population == RAW].to_csv(
        output / "year_cost_stress_raw_reconstructed.csv", index=False
    )
    year[year.population == BRIDGE].to_csv(
        output / "year_cost_stress_warmup_bridge_exact.csv", index=False
    )
    lineage[lineage.population == RAW].to_csv(
        output / "lineage_cost_stress_raw_reconstructed.csv", index=False
    )
    lineage[lineage.population == BRIDGE].to_csv(
        output / "lineage_cost_stress_warmup_bridge_exact.csv", index=False
    )
    gate.to_csv(output / "candidate_overall_gate_raw_reconstructed.csv", index=False)


def write_text_summary(
    output: Path,
    config_path: Path,
    config_hash: str,
    backup: Path | None,
    scenarios: list[Scenario],
    checks: int,
    registry: pd.DataFrame,
    candidate: pd.DataFrame,
    gate: pd.DataFrame,
) -> None:
    passes = int((gate.candidate_overall_stress_gate == "PASS").sum())
    fails = int((gate.candidate_overall_stress_gate == "FAIL").sum())
    lines = [
        "GOLD_ML_V1 COST STRESS - RAW_RECONSTRUCTED PRIMARY / WARMUP_BRIDGE_EXACT SEPARATE",
        "run_status=PASS",
        "exit_code=0",
        f"run_time_local={datetime.now().isoformat(timespec='seconds')}",
        f"config={config_path}",
        f"config_sha256={config_hash}",
        f"previous_output_backup={backup or ''}",
        "audit_only=true",
        "new_exploration=false",
        "live_ready=false",
        "automatic_promotion=false",
        "automatic_registration=false",
        f"scenario_count={len(scenarios)}",
        f"raw_baseline_parity_checks={checks}",
        f"raw_reconstructed_rows={int((registry.trade_core_source == RAW).sum())}",
        f"warmup_bridge_exact_rows={int((registry.trade_core_source == BRIDGE).sum())}",
        f"candidate_overall_stress_gate_pass={passes}",
        f"candidate_overall_stress_gate_fail={fails}",
        "bridge_stress_replay=NOT_CALCULATED_AUDIT_ONLY",
        f"bridge_blocker={BRIDGE_BLOCKER}",
        "runner_pass_meaning=validation_and_RAW_report_generation_completed; candidate gate FAIL is preserved",
        "next_automatic_action=NONE",
        "blocker=Fresh prospective confirmation remains required",
        "",
        "Frozen RAW scenarios:",
    ]
    lines.extend(
        f"- {item.scenario_id}: spread={item.spread_multiplier:.1f}x; slippage={item.slippage_points_per_side} points/side"
        for item in scenarios
    )
    lines.extend(
        [
            "",
            "Candidate overall RAW gate:",
            gate.to_csv(index=False).strip(),
            "",
            "RAW candidate/scenario results:",
        ]
    )
    raw_columns = [
        "candidate_id",
        "scenario_id",
        "trade_count",
        "win_rate",
        "profit_factor",
        "profit_factor_state",
        "mean_r",
        "median_r",
        "worst_year",
        "worst_month",
        "delta_mean_r_vs_baseline",
        "stress_gate_status",
    ]
    lines.append(candidate[candidate.population == RAW][raw_columns].to_csv(index=False).strip())
    lines.extend(
        [
            "",
            "WARMUP_BRIDGE_EXACT baseline core audit:",
            candidate[candidate.population == BRIDGE].to_csv(index=False).strip(),
            "",
            "Caveats:",
            "- WARMUP_BRIDGE_EXACT is separate and never eligible for promotion or live use.",
            "- Bridge exact cost replay is not fabricated when price/risk state is unavailable.",
            "- Candidate membership is fixed; this does not discover suppressed alternative entries.",
            "- Same-lineage metrics are not pooled and PF/profit are not summed.",
            "- PASS does not authorize registration, prospective use, Discord, MT5 orders or live activation.",
        ]
    )
    (output / "LATEST_RUN_SUMMARY.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
