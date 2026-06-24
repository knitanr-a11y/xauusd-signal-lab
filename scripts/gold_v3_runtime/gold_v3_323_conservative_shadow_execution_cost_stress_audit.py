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

EXPECTED_STATUS = "GOLD_V3_322_WIN_RATE_FIRST_SHADOW_SELECTION_AUDIT_COMPLETE"
EXPECTED_DECISION = "WIN_RATE_FIRST_CONSERVATIVE_SHADOW_SELECTED"
EXPECTED_LANE = "BALANCED_OR_PREMIUM"
SELECTION_YEARS = (2024, 2025)
DISPLAY_ONLY_YEAR = 2026
TOL = 1e-12
COST_MULTIPLIERS = (1.0, 1.25, 1.5, 2.0, 3.0)

EXECUTION_STRESS_GATE = {
    "cost_1_5x_minimum_profit_factor": 1.50,
    "cost_1_5x_minimum_total_r_exclusive": 0.0,
    "cost_1_5x_maximum_drawdown_r": 4.0,
    "cost_1_5x_minimum_each_selection_year_total_r_exclusive": 0.0,
    "cost_2_0x_minimum_profit_factor": 1.25,
    "cost_2_0x_minimum_total_r_exclusive": 0.0,
    "cost_3_0x_minimum_total_r_exclusive": 0.0,
    "maximum_largest_winner_share": 0.35,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage322-json", required=True)
    parser.add_argument("--stage322-selected", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--scenario-csv", required=True)
    parser.add_argument("--stressed-trades-csv", required=True)
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


def apply_cost(frame: pd.DataFrame, multiplier: float) -> pd.DataFrame:
    work = frame.copy()
    work["cost_multiplier"] = multiplier
    work["stress_spread_cost"] = (
        pd.to_numeric(work.entry_spread_price, errors="raise") * multiplier
    )
    work["stress_pnl"] = (
        pd.to_numeric(work.gross_pnl, errors="raise") - work.stress_spread_cost
    )
    work["stress_r"] = work.stress_pnl / pd.to_numeric(
        work.risk_price, errors="raise"
    )
    work["spread_adjusted_pnl"] = work.stress_pnl
    work["spread_adjusted_r"] = work.stress_r
    return work


def verify_baseline_parity(frame: pd.DataFrame) -> dict[str, float]:
    rebuilt = apply_cost(frame, 1.0)
    pnl_diff = float(
        np.max(
            np.abs(
                rebuilt.stress_pnl.to_numpy(float)
                - pd.to_numeric(frame.spread_adjusted_pnl, errors="raise").to_numpy(float)
            )
        )
    )
    r_diff = float(
        np.max(
            np.abs(
                rebuilt.stress_r.to_numpy(float)
                - pd.to_numeric(frame.spread_adjusted_r, errors="raise").to_numpy(float)
            )
        )
    )
    if pnl_diff > TOL or r_diff > TOL:
        raise ValueError(
            "BASELINE_COST_PARITY_FAILED: "
            f"max_pnl_diff={pnl_diff} max_r_diff={r_diff}"
        )
    return {"max_pnl_diff": pnl_diff, "max_r_diff": r_diff}


def consecutive_losses(frame: pd.DataFrame) -> int:
    longest = 0
    current = 0
    for value in pd.to_numeric(frame.spread_adjusted_pnl, errors="raise"):
        if value < 0.0:
            current += 1
            longest = max(longest, current)
        else:
            current = 0
    return longest


def contribution_table(frame: pd.DataFrame, column: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for value, group in frame.groupby(column, sort=True, dropna=False):
        rows.append({"group": str(value), **summarize(group)})
    return rows


def scenario_record(frame: pd.DataFrame, multiplier: float) -> dict[str, Any]:
    stressed = apply_cost(frame, multiplier)
    selection = stressed[stressed.entry_dt.dt.year.isin(SELECTION_YEARS)].copy()
    selection = selection.sort_values(["entry_dt", "exit_dt"], kind="mergesort")
    selection_summary = summarize(selection)
    yearly_summary = yearly(stressed)
    return {
        "cost_multiplier": multiplier,
        "selection_2024_2025": selection_summary,
        "yearly": yearly_summary,
        "display_only_2026": yearly_summary[str(DISPLAY_ONLY_YEAR)],
        "maximum_consecutive_losses_selection": consecutive_losses(selection),
        "membership_roles_selection": contribution_table(selection, "membership_roles"),
        "profile_name_selection": contribution_table(selection, "profile_name"),
    }


def get_scenario(rows: list[dict[str, Any]], multiplier: float) -> dict[str, Any]:
    for row in rows:
        if abs(float(row["cost_multiplier"]) - multiplier) <= TOL:
            return row
    raise KeyError(multiplier)


def main() -> int:
    args = parse_args()
    stage322_json_path = Path(args.stage322_json).expanduser().resolve()
    selected_path = Path(args.stage322_selected).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()
    scenario_path = Path(args.scenario_csv).expanduser().resolve()
    stressed_trades_path = Path(args.stressed_trades_csv).expanduser().resolve()

    stage322 = json.loads(stage322_json_path.read_text(encoding="utf-8"))
    if stage322.get("status") != EXPECTED_STATUS:
        raise ValueError(f"STAGE322_STATUS_UNEXPECTED: {stage322.get('status')}")
    if stage322.get("decision") != EXPECTED_DECISION:
        raise ValueError(f"STAGE322_DECISION_UNEXPECTED: {stage322.get('decision')}")
    if stage322.get("selected_lane") != EXPECTED_LANE:
        raise ValueError(f"STAGE322_LANE_UNEXPECTED: {stage322.get('selected_lane')}")
    expected_sha = stage322.get("outputs", {}).get("selected_shadow_trades_sha256")
    actual_sha = sha256_file(selected_path)
    if expected_sha != actual_sha:
        raise ValueError(
            "STAGE322_SELECTED_SHA_MISMATCH: "
            f"expected={expected_sha} actual={actual_sha}"
        )

    trades = pd.read_csv(selected_path, encoding="utf-8-sig")
    required = {
        "entry_dt",
        "exit_dt",
        "gross_pnl",
        "spread_adjusted_pnl",
        "spread_adjusted_r",
        "entry_spread_price",
        "risk_price",
        "membership_roles",
        "profile_name",
        "stage322_selected_lane",
    }
    missing = sorted(required - set(trades.columns))
    if missing:
        raise ValueError(f"STAGE322_SELECTED_COLUMNS_MISSING: {missing}")
    trades["entry_dt"] = pd.to_datetime(trades.entry_dt, errors="raise")
    trades["exit_dt"] = pd.to_datetime(trades.exit_dt, errors="raise")
    if sorted(set(trades.stage322_selected_lane.astype(str))) != [EXPECTED_LANE]:
        raise ValueError("STAGE322_SELECTED_LANE_COLUMN_MISMATCH")
    trades = trades.sort_values(["entry_dt", "exit_dt"], kind="mergesort").reset_index(drop=True)
    if len(trades) > 1:
        if bool((trades.entry_dt.iloc[1:].reset_index(drop=True) < trades.exit_dt.iloc[:-1].reset_index(drop=True)).any()):
            raise ValueError("SELECTED_TRADES_OVERLAP")

    parity = verify_baseline_parity(trades)
    scenarios = [scenario_record(trades, multiplier) for multiplier in COST_MULTIPLIERS]

    one5 = get_scenario(scenarios, 1.5)
    two0 = get_scenario(scenarios, 2.0)
    three0 = get_scenario(scenarios, 3.0)
    one5_summary = one5["selection_2024_2025"]
    two0_summary = two0["selection_2024_2025"]
    three0_summary = three0["selection_2024_2025"]
    one5_years = one5["yearly"]

    checks = {
        "baseline_parity": parity["max_pnl_diff"] <= TOL and parity["max_r_diff"] <= TOL,
        "cost_1_5x_minimum_profit_factor": float(one5_summary["spread_adjusted_profit_factor"] or 0.0)
        >= float(EXECUTION_STRESS_GATE["cost_1_5x_minimum_profit_factor"]),
        "cost_1_5x_minimum_total_r": float(one5_summary["spread_adjusted_total_r"])
        > float(EXECUTION_STRESS_GATE["cost_1_5x_minimum_total_r_exclusive"]),
        "cost_1_5x_maximum_drawdown_r": float(one5_summary["spread_adjusted_max_drawdown_r"])
        <= float(EXECUTION_STRESS_GATE["cost_1_5x_maximum_drawdown_r"]),
        "cost_1_5x_each_selection_year_positive": all(
            float(one5_years[str(year)]["spread_adjusted_total_r"])
            > float(EXECUTION_STRESS_GATE["cost_1_5x_minimum_each_selection_year_total_r_exclusive"])
            for year in SELECTION_YEARS
        ),
        "cost_2_0x_minimum_profit_factor": float(two0_summary["spread_adjusted_profit_factor"] or 0.0)
        >= float(EXECUTION_STRESS_GATE["cost_2_0x_minimum_profit_factor"]),
        "cost_2_0x_minimum_total_r": float(two0_summary["spread_adjusted_total_r"])
        > float(EXECUTION_STRESS_GATE["cost_2_0x_minimum_total_r_exclusive"]),
        "cost_3_0x_minimum_total_r": float(three0_summary["spread_adjusted_total_r"])
        > float(EXECUTION_STRESS_GATE["cost_3_0x_minimum_total_r_exclusive"]),
        "maximum_largest_winner_share": float(one5_summary["largest_win_share_of_positive_pnl"])
        <= float(EXECUTION_STRESS_GATE["maximum_largest_winner_share"]),
    }
    gate_pass = bool(all(checks.values()))

    scenario_rows: list[dict[str, Any]] = []
    for row in scenarios:
        summary = row["selection_2024_2025"]
        stress = row["display_only_2026"]
        scenario_rows.append(
            {
                "cost_multiplier": row["cost_multiplier"],
                "trades_2024_2025": summary["trades"],
                "win_rate_2024_2025": summary["win_rate"],
                "profit_factor_2024_2025": summary["spread_adjusted_profit_factor"],
                "total_usd_2024_2025": summary["spread_adjusted_total_usd"],
                "total_r_2024_2025": summary["spread_adjusted_total_r"],
                "max_drawdown_r_2024_2025": summary["spread_adjusted_max_drawdown_r"],
                "largest_winner_share_2024_2025": summary["largest_win_share_of_positive_pnl"],
                "max_consecutive_losses_2024_2025": row["maximum_consecutive_losses_selection"],
                "trades_2026_display_only": stress["trades"],
                "win_rate_2026_display_only": stress["win_rate"],
                "profit_factor_2026_display_only": stress["spread_adjusted_profit_factor"],
                "total_r_2026_display_only": stress["spread_adjusted_total_r"],
                "max_drawdown_r_2026_display_only": stress["spread_adjusted_max_drawdown_r"],
            }
        )
    scenario_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(scenario_rows).to_csv(scenario_path, index=False, encoding="utf-8-sig")

    stressed_wide = trades.copy()
    for multiplier in COST_MULTIPLIERS:
        stressed = apply_cost(trades, multiplier)
        tag = str(multiplier).replace(".", "p")
        stressed_wide[f"stress_pnl_{tag}x"] = stressed.stress_pnl
        stressed_wide[f"stress_r_{tag}x"] = stressed.stress_r
    stressed_wide.to_csv(stressed_trades_path, index=False, encoding="utf-8-sig")

    decision = (
        "CONSERVATIVE_SHADOW_EXECUTION_COST_STRESS_SUPPORTED"
        if gate_pass
        else "CONSERVATIVE_SHADOW_EXECUTION_COST_STRESS_NOT_SUPPORTED"
    )
    output = {
        "status": "GOLD_V3_323_CONSERVATIVE_SHADOW_EXECUTION_COST_STRESS_AUDIT_COMPLETE",
        "mode": "AUDIT_ONLY_FIXED_SELECTED_SHADOW_EXECUTION_COST_STRESS",
        "decision": decision,
        "source": {
            "stage322_json": str(stage322_json_path),
            "stage322_json_sha256": sha256_file(stage322_json_path),
            "stage322_selected_trades": str(selected_path),
            "stage322_selected_trades_sha256": actual_sha,
        },
        "research_contract": {
            "selected_lane": EXPECTED_LANE,
            "selection_years": list(SELECTION_YEARS),
            "display_only_year": DISPLAY_ONLY_YEAR,
            "selection_and_gate_do_not_use_2026": True,
            "cost_multiplier_definition": "gross_pnl - multiplier * entry_spread_price",
            "fixed_cost_multipliers": list(COST_MULTIPLIERS),
            "new_raw_feature_thresholds_added": False,
            "numeric_tolerance": TOL,
            "execution_stress_gate": EXECUTION_STRESS_GATE,
        },
        "baseline_parity": parity,
        "gate": {"pass": gate_pass, "checks": checks},
        "scenarios": scenarios,
        "interpretation": {
            "purpose": (
                "This stage immediately tests whether the exact Stage322 conservative "
                "shadow survives materially worse spread costs. It does not tune entries."
            ),
            "limits": (
                "Spread multiplication is an execution-cost stress test, not a substitute "
                "for unseen future evidence. Stage319 remains frozen and unchanged."
            ),
        },
        "outputs": {
            "result_json": str(output_path),
            "scenario_csv": str(scenario_path),
            "stressed_trades_csv": str(stressed_trades_path),
            "scenario_sha256": sha256_file(scenario_path),
            "stressed_trades_sha256": sha256_file(stressed_trades_path),
        },
        "promotion": {
            "performed": False,
            "stage319_contract": "UNCHANGED_FROZEN",
            "stage314_contract": "UNCHANGED_ACTIVE",
            "stage322_result": "UNCHANGED_RETAINED",
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
