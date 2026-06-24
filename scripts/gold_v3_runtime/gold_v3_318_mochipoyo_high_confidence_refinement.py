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
import gold_v3_311_mochipoyo_and_independent_candidate_research as stage311

SELECTION_YEARS = (2024, 2025)
DISPLAY_ONLY_YEAR = 2026
EXPECTED_STAGE317_STATUS = "GOLD_V3_317_UNIFIED_MOCHIPOYO_POOL_AUDIT_COMPLETE"
EXPECTED_STAGE317_KEY = "M5_H4|MOCHI_UNION|SHORT|RR1_5|ATR_GE_1_AND_NO_ROUND"

PROFILE_NAMES = (
    "BASE",
    "ATR_STEADY_1_10_TO_1_45",
    "ACTIVE_RANGE_0_70_TO_1_05",
    "TREND_FLOW_COMPRESSION_GE_0_95",
    "ATR_STEADY_AND_ACTIVE_RANGE",
    "ATR_STEADY_AND_FLOW",
    "CONSENSUS_2PLUS",
    "CONSENSUS_OR_ATR_STEADY_AND_RANGE",
    "CONSENSUS_OR_ATR_STEADY_AND_FLOW",
)

PRIMARY_GATE = {
    "minimum_selection_trades": 20,
    "minimum_each_selection_year_trades": 8,
    "minimum_selection_win_rate": 0.60,
    "minimum_win_rate_improvement": 0.04,
    "minimum_each_selection_year_win_rate": 0.55,
    "minimum_profit_factor": 1.35,
    "minimum_total_r": 0.0,
    "minimum_base_r_retention": 0.70,
    "maximum_drawdown_vs_base_multiplier": 1.00,
    "maximum_largest_win_share": 0.35,
}

SPARSE_GATE = {
    "minimum_selection_trades": 12,
    "minimum_each_selection_year_trades": 5,
    "minimum_selection_win_rate": 0.68,
    "minimum_each_selection_year_win_rate": 0.60,
    "minimum_profit_factor": 1.50,
    "minimum_total_r": 0.0,
    "maximum_drawdown_vs_base_multiplier": 1.00,
    "maximum_largest_win_share": 0.35,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage317-json", required=True)
    parser.add_argument("--stage317-selected", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--all-profiles-csv", required=True)
    parser.add_argument("--primary-csv", required=True)
    parser.add_argument("--sparse-csv", required=True)
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


def normalize_bool(series: pd.Series) -> pd.Series:
    if pd.api.types.is_bool_dtype(series):
        return series.fillna(False)
    return (
        series.astype(str)
        .str.strip()
        .str.lower()
        .isin({"true", "1", "yes", "y"})
    )


def profile_mask(frame: pd.DataFrame, name: str) -> pd.Series:
    atr_steady = frame.atr_ratio_signal.between(1.10, 1.45)
    active_range = frame.range_atr_signal.between(0.70, 1.05)
    trend_flow = frame.compression_ratio_signal >= 0.95
    consensus = frame.pooled_track_count >= 2

    if name == "BASE":
        return pd.Series(True, index=frame.index)
    if name == "ATR_STEADY_1_10_TO_1_45":
        return atr_steady
    if name == "ACTIVE_RANGE_0_70_TO_1_05":
        return active_range
    if name == "TREND_FLOW_COMPRESSION_GE_0_95":
        return trend_flow
    if name == "ATR_STEADY_AND_ACTIVE_RANGE":
        return atr_steady & active_range
    if name == "ATR_STEADY_AND_FLOW":
        return atr_steady & trend_flow
    if name == "CONSENSUS_2PLUS":
        return consensus
    if name == "CONSENSUS_OR_ATR_STEADY_AND_RANGE":
        return consensus | (atr_steady & active_range)
    if name == "CONSENSUS_OR_ATR_STEADY_AND_FLOW":
        return consensus | (atr_steady & trend_flow)
    raise ValueError(name)


def pf_value(summary: dict[str, Any]) -> float:
    value = summary.get("spread_adjusted_profit_factor")
    if value is None and float(summary.get("spread_adjusted_total_usd", 0.0)) > 0.0:
        return float("inf")
    return float(value or 0.0)


def selection_metrics(rows: list[dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any]]:
    selection = [
        row
        for row in rows
        if pd.Timestamp(row["entry_dt"]).year in SELECTION_YEARS
    ]
    yearly = stage308.yearly_summary(rows)
    return stage308.summarize(selection), yearly


def gate_check(
    selection: dict[str, Any],
    yearly: dict[str, Any],
    base_selection: dict[str, Any],
    gate: dict[str, Any],
    *,
    require_improvement: bool,
) -> dict[str, Any]:
    selection_trades = int(selection["trades"])
    selection_win_rate = float(selection["win_rate"])
    yearly_counts = [int(yearly[str(year)]["trades"]) for year in SELECTION_YEARS]
    yearly_win_rates = [
        float(yearly[str(year)]["win_rate"]) for year in SELECTION_YEARS
    ]
    base_win_rate = float(base_selection["win_rate"])
    base_total_r = float(base_selection["spread_adjusted_total_r"])
    total_r = float(selection["spread_adjusted_total_r"])
    base_dd = float(base_selection["spread_adjusted_max_drawdown_r"])
    dd = float(selection["spread_adjusted_max_drawdown_r"])
    largest_share = float(selection["largest_win_share_of_positive_pnl"])
    pf = pf_value(selection)

    checks = {
        "minimum_selection_trades": selection_trades
        >= int(gate["minimum_selection_trades"]),
        "minimum_each_selection_year_trades": min(yearly_counts, default=0)
        >= int(gate["minimum_each_selection_year_trades"]),
        "minimum_selection_win_rate": selection_win_rate
        >= float(gate["minimum_selection_win_rate"]),
        "minimum_each_selection_year_win_rate": min(yearly_win_rates, default=0.0)
        >= float(gate["minimum_each_selection_year_win_rate"]),
        "minimum_profit_factor": pf >= float(gate["minimum_profit_factor"]),
        "minimum_total_r": total_r > float(gate["minimum_total_r"]),
        "maximum_drawdown_vs_base": dd
        <= base_dd * float(gate["maximum_drawdown_vs_base_multiplier"]),
        "maximum_largest_win_share": largest_share
        <= float(gate["maximum_largest_win_share"]),
    }
    if "minimum_base_r_retention" in gate:
        retention = total_r / base_total_r if base_total_r > 0.0 else 0.0
        checks["minimum_base_r_retention"] = retention >= float(
            gate["minimum_base_r_retention"]
        )
    else:
        retention = None
    if require_improvement:
        improvement = selection_win_rate - base_win_rate
        checks["minimum_win_rate_improvement"] = improvement >= float(
            gate["minimum_win_rate_improvement"]
        )
    else:
        improvement = selection_win_rate - base_win_rate

    return {
        "pass": bool(all(checks.values())),
        "checks": checks,
        "selection_win_rate": selection_win_rate,
        "base_win_rate": base_win_rate,
        "win_rate_improvement": improvement,
        "base_r_retention": retention,
        "minimum_year_count": min(yearly_counts, default=0),
        "minimum_year_win_rate": min(yearly_win_rates, default=0.0),
        "profit_factor": pf,
    }


def write_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if rows:
        pd.DataFrame(stage311.csv_safe_rows(rows)).to_csv(
            path,
            index=False,
            encoding="utf-8-sig",
        )
    else:
        pd.DataFrame(columns=["profile_name"]).to_csv(
            path,
            index=False,
            encoding="utf-8-sig",
        )


def main() -> int:
    args = parse_args()
    stage317_json_path = Path(args.stage317_json).expanduser().resolve()
    stage317_selected_path = Path(args.stage317_selected).expanduser().resolve()
    output = Path(args.output).expanduser().resolve()
    all_profiles_csv = Path(args.all_profiles_csv).expanduser().resolve()
    primary_csv = Path(args.primary_csv).expanduser().resolve()
    sparse_csv = Path(args.sparse_csv).expanduser().resolve()

    stage317 = json.loads(stage317_json_path.read_text(encoding="utf-8"))
    if stage317.get("status") != EXPECTED_STAGE317_STATUS:
        raise ValueError(f"STAGE317_STATUS_UNEXPECTED: {stage317.get('status')}")
    if stage317.get("selected_output_candidate_key") != EXPECTED_STAGE317_KEY:
        raise ValueError(
            "STAGE317_SELECTED_KEY_UNEXPECTED: "
            f"{stage317.get('selected_output_candidate_key')}"
        )
    expected_sha = stage317.get("outputs", {}).get("selected_trades_sha256")
    actual_sha = sha256_file(stage317_selected_path)
    if expected_sha != actual_sha:
        raise ValueError(
            "STAGE317_SELECTED_SHA_MISMATCH: "
            f"expected={expected_sha} actual={actual_sha}"
        )

    source = pd.read_csv(stage317_selected_path, encoding="utf-8-sig")
    required = {
        "pair",
        "direction",
        "exit_profile",
        "entry_dt",
        "exit_dt",
        "spread_adjusted_pnl",
        "spread_adjusted_r",
        "atr_ratio_signal",
        "range_atr_signal",
        "compression_ratio_signal",
        "pooled_track_count",
        "round_number_near",
    }
    missing = sorted(required - set(source.columns))
    if missing:
        raise ValueError(f"STAGE317_SELECTED_COLUMNS_MISSING: {missing}")

    for column in ("entry_dt", "exit_dt"):
        source[column] = pd.to_datetime(source[column], errors="raise")
    source["round_number_near"] = normalize_bool(source.round_number_near)
    if not source.pair.eq("M5_H4").all():
        raise ValueError("STAGE317_SELECTED_PAIR_NOT_M5_H4")
    if not source.direction.eq("SHORT").all():
        raise ValueError("STAGE317_SELECTED_DIRECTION_NOT_SHORT")
    if not source.exit_profile.eq("RR1_5").all():
        raise ValueError("STAGE317_SELECTED_EXIT_NOT_RR1_5")
    if source.round_number_near.any():
        raise ValueError("STAGE317_SELECTED_CONTAINS_ROUND_NUMBER_NEAR")
    if (source.atr_ratio_signal < 1.0).any():
        raise ValueError("STAGE317_SELECTED_CONTAINS_ATR_RATIO_BELOW_1")

    source_rows = source.to_dict(orient="records")
    base_selection, base_yearly = selection_metrics(source_rows)
    base_full = stage308.summarize(source_rows)

    profile_rows: dict[str, list[dict[str, Any]]] = {}
    leaderboard: list[dict[str, Any]] = []
    for name in PROFILE_NAMES:
        filtered = source[profile_mask(source, name)].copy()
        rows = filtered.to_dict(orient="records")
        profile_rows[name] = rows
        selection, yearly = selection_metrics(rows)
        primary = gate_check(
            selection,
            yearly,
            base_selection,
            PRIMARY_GATE,
            require_improvement=True,
        )
        sparse = gate_check(
            selection,
            yearly,
            base_selection,
            SPARSE_GATE,
            require_improvement=False,
        )
        stress = yearly[str(DISPLAY_ONLY_YEAR)]
        leaderboard.append(
            {
                "profile_name": name,
                "all_period": stage308.summarize(rows),
                "selection_2024_2025": selection,
                "yearly": yearly,
                "primary_gate": primary,
                "sparse_gate": sparse,
                "stress_2026": {
                    "display_only": True,
                    "clean_holdout": False,
                    "trades": int(stress["trades"]),
                    "win_rate": float(stress["win_rate"]),
                    "profit_factor": stress["spread_adjusted_profit_factor"],
                    "total_r": float(stress["spread_adjusted_total_r"]),
                    "max_drawdown_r": float(
                        stress["spread_adjusted_max_drawdown_r"]
                    ),
                },
            }
        )

    primary_passes = [row for row in leaderboard if row["primary_gate"]["pass"]]
    primary_passes.sort(
        key=lambda row: (
            -float(row["primary_gate"]["selection_win_rate"]),
            -int(row["selection_2024_2025"]["trades"]),
            -float(row["primary_gate"]["profit_factor"]),
            row["profile_name"],
        )
    )
    sparse_passes = [
        row
        for row in leaderboard
        if row["sparse_gate"]["pass"] and row["profile_name"] != "BASE"
    ]
    sparse_passes.sort(
        key=lambda row: (
            -float(row["sparse_gate"]["selection_win_rate"]),
            -int(row["selection_2024_2025"]["trades"]),
            -float(row["sparse_gate"]["profit_factor"]),
            row["profile_name"],
        )
    )

    primary_selected = primary_passes[0] if primary_passes else None
    sparse_selected = sparse_passes[0] if sparse_passes else None
    primary_name = primary_selected["profile_name"] if primary_selected else None
    sparse_name = sparse_selected["profile_name"] if sparse_selected else None

    all_csv_rows: list[dict[str, Any]] = []
    for name, rows in profile_rows.items():
        for row in rows:
            item = dict(row)
            item["profile_name"] = name
            all_csv_rows.append(item)
    write_rows(all_profiles_csv, all_csv_rows)
    write_rows(primary_csv, profile_rows.get(primary_name, []))
    write_rows(sparse_csv, profile_rows.get(sparse_name, []))

    if primary_selected is not None:
        decision = "MOCHIPOYO_HIGHER_WIN_RATE_PRIMARY_FOUND"
    elif sparse_selected is not None:
        decision = "MOCHIPOYO_ONLY_SPARSE_HIGH_CONFIDENCE_FOUND"
    else:
        decision = "NO_RELIABLE_HIGHER_WIN_RATE_REFINEMENT_FOUND"

    leaderboard.sort(
        key=lambda row: (
            -int(row["primary_gate"]["pass"]),
            -int(row["sparse_gate"]["pass"]),
            -float(row["selection_2024_2025"]["win_rate"]),
            -int(row["selection_2024_2025"]["trades"]),
            row["profile_name"],
        )
    )

    report = {
        "status": "GOLD_V3_318_MOCHIPOYO_HIGH_CONFIDENCE_REFINEMENT_COMPLETE",
        "mode": "AUDIT_ONLY_FIXED_STAGE317_SUBSET_RESEARCH",
        "decision": decision,
        "source": {
            "stage317_json": str(stage317_json_path),
            "stage317_json_sha256": sha256_file(stage317_json_path),
            "stage317_selected_csv": str(stage317_selected_path),
            "stage317_selected_sha256": actual_sha,
            "stage317_candidate_key": EXPECTED_STAGE317_KEY,
        },
        "research_contract": {
            "selection_years": list(SELECTION_YEARS),
            "display_only_year": DISPLAY_ONLY_YEAR,
            "selection_does_not_use_2026": True,
            "base_entry_exit_contract_changed": False,
            "target": "raise win rate without discarding most of Stage317 edge",
            "fixed_profiles": list(PROFILE_NAMES),
            "primary_gate": PRIMARY_GATE,
            "sparse_gate": SPARSE_GATE,
            "primary_selection_uses_2024_2025_only": True,
            "sparse_selection_uses_2024_2025_only": True,
        },
        "base_stage317": {
            "all_period": base_full,
            "selection_2024_2025": base_selection,
            "yearly": base_yearly,
        },
        "search": {
            "source_trades": int(len(source)),
            "profile_count": len(leaderboard),
            "primary_pass_count": len(primary_passes),
            "sparse_pass_count": len(sparse_passes),
        },
        "primary_high_confidence": primary_selected,
        "premium_sparse_watch": sparse_selected,
        "leaderboard": leaderboard,
        "interpretation": {
            "primary": (
                "The primary gate requires at least 20 selection trades, at least "
                "8 trades in each selection year, at least a four-point win-rate "
                "improvement over Stage317, PF and R preservation, and no worse DD."
            ),
            "sparse": (
                "The sparse gate is reported separately and cannot replace the "
                "primary candidate because its sample is intentionally smaller."
            ),
            "future": (
                "2026 is already visible. Any pass remains research-only and must "
                "be frozen into a new prospective watch before operational use."
            ),
        },
        "outputs": {
            "result_json": str(output),
            "all_profiles_csv": str(all_profiles_csv),
            "primary_selected_csv": str(primary_csv),
            "sparse_selected_csv": str(sparse_csv),
            "all_profiles_sha256": sha256_file(all_profiles_csv),
            "primary_selected_sha256": sha256_file(primary_csv),
            "sparse_selected_sha256": sha256_file(sparse_csv),
        },
        "promotion": {
            "performed": False,
            "stage317_research_watch": "UNCHANGED_RETAINED",
            "stage314_prospective_watch": "UNCHANGED_ACTIVE",
            "stage315_independent_research": "UNCHANGED",
            "stage307_candidate": "UNCHANGED_RETAINED",
            "stage292_candidate_pool_changed": False,
        },
        "safety_flags": {
            "closed_candles_only": True,
            "final_signal_changed": False,
            "mt5_order_enabled": False,
            "discord_enabled": False,
            "partial_close_enabled": False,
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(json_safe(report), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(json_safe(report), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
