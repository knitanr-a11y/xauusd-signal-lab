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
import gold_v3_320_short_cycle_robustness_audit as stage320

EXPECTED_STATUS = "GOLD_V3_320_SHORT_CYCLE_ROBUSTNESS_AUDIT_COMPLETE"
EXPECTED_DECISION = "IMMEDIATE_ROBUST_CORE_BALANCED_AND_PREMIUM_FOUND"
EXPECTED_PROFILES = {
    "CORE": "ATR_STEADY_1_10_TO_1_45",
    "BALANCED": "CONSENSUS_OR_ATR_STEADY_AND_RANGE",
    "PREMIUM": "TREND_FLOW_COMPRESSION_GE_0_95",
}
SELECTION_YEARS = (2024, 2025)
DISPLAY_ONLY_YEAR = 2026
TOL = 1e-12
RNG_SEED = 321

LANES = {
    "CORE": "core",
    "BALANCED": "balanced",
    "PREMIUM": "premium",
    "CORE_OR_BALANCED": "core | balanced",
    "CORE_OR_PREMIUM": "core | premium",
    "BALANCED_OR_PREMIUM": "balanced | premium",
    "ANY_OF_THREE": "core | balanced | premium",
    "AT_LEAST_TWO_OF_THREE": "membership_count >= 2",
    "ALL_THREE": "membership_count == 3",
}

SHADOW_GATE = {
    "minimum_selection_trades": 20,
    "minimum_each_selection_year_trades": 8,
    "minimum_selection_win_rate": 0.62,
    "minimum_profit_factor": 1.50,
    "minimum_total_r_exclusive": 0.0,
    "maximum_drawdown_r": 4.0,
    "maximum_largest_winner_share": 0.35,
    "minimum_leave_one_quarter_out_total_r_exclusive": 0.0,
    "minimum_rolling_6m_positive_ratio": 0.90,
    "minimum_iid_bootstrap_positive_r_probability": 0.90,
    "minimum_quarter_block_bootstrap_positive_r_probability": 0.80,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage320-json", required=True)
    parser.add_argument("--core-csv", required=True)
    parser.add_argument("--balanced-csv", required=True)
    parser.add_argument("--premium-csv", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--leaderboard-csv", required=True)
    parser.add_argument("--selected-shadow-csv", required=True)
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


def load_csv(path: Path, expected_profile: str) -> pd.DataFrame:
    frame = pd.read_csv(path, encoding="utf-8-sig")
    required = {
        "pair",
        "direction",
        "exit_profile",
        "entry_dt",
        "exit_dt",
        "entry_price",
        "sl_price",
        "tp_price",
        "exit_price",
        "spread_adjusted_pnl",
        "spread_adjusted_r",
        "profile_name",
    }
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"SOURCE_COLUMNS_MISSING: {missing}")
    for column in ("entry_dt", "exit_dt"):
        frame[column] = pd.to_datetime(frame[column], errors="raise")
    observed = sorted(set(frame.profile_name.astype(str)))
    if observed != [expected_profile]:
        raise ValueError(
            f"SOURCE_PROFILE_UNEXPECTED: expected={expected_profile} actual={observed}"
        )
    return frame


def verify_sources(
    result: dict[str, Any],
    result_path: Path,
    paths: dict[str, Path],
) -> dict[str, str]:
    if result.get("status") != EXPECTED_STATUS:
        raise ValueError(f"STAGE320_STATUS_UNEXPECTED: {result.get('status')}")
    if result.get("decision") != EXPECTED_DECISION:
        raise ValueError(f"STAGE320_DECISION_UNEXPECTED: {result.get('decision')}")
    outputs = result.get("outputs", {})
    expected_hashes = {
        "core": outputs.get("core_trades_sha256"),
        "balanced": outputs.get("balanced_challenger_trades_sha256"),
        "premium": outputs.get("premium_trades_sha256"),
    }
    actual_hashes = {key: sha256_file(path) for key, path in paths.items()}
    for key in expected_hashes:
        if expected_hashes[key] != actual_hashes[key]:
            raise ValueError(
                f"STAGE320_SOURCE_SHA_MISMATCH: {key} "
                f"expected={expected_hashes[key]} actual={actual_hashes[key]}"
            )
    return {"stage320_json": sha256_file(result_path), **actual_hashes}


def same_numeric(group: pd.DataFrame, column: str) -> None:
    values = pd.to_numeric(group[column], errors="coerce")
    finite = values.dropna()
    if finite.empty:
        return
    if values.isna().any():
        raise ValueError(f"DUPLICATE_OPTIONAL_PARITY_FAILED: {column}")
    if float(finite.max() - finite.min()) > TOL:
        raise ValueError(
            f"DUPLICATE_NUMERIC_PARITY_FAILED: {column} "
            f"spread={float(finite.max() - finite.min())}"
        )


def build_master(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    key = ["pair", "direction", "exit_profile", "entry_dt"]
    tagged: list[pd.DataFrame] = []
    for role, frame in frames.items():
        item = frame.copy()
        item["membership_role"] = role
        tagged.append(item)
    combined = pd.concat(tagged, ignore_index=True)
    rows: list[dict[str, Any]] = []
    for _, group in combined.groupby(key, sort=True, dropna=False):
        for column in ("pair", "direction", "exit_profile", "entry_dt", "exit_dt"):
            if group[column].nunique(dropna=False) != 1:
                raise ValueError(f"DUPLICATE_EXACT_PARITY_FAILED: {column}")
        for column in (
            "entry_price",
            "sl_price",
            "tp_price",
            "exit_price",
            "spread_adjusted_pnl",
            "spread_adjusted_r",
        ):
            same_numeric(group, column)
        ordered = group.sort_values(
            ["membership_role", "profile_name"],
            kind="mergesort",
        )
        row = ordered.iloc[0].to_dict()
        memberships = sorted(set(group.membership_role.astype(str)))
        row.update(
            {
                "core": "CORE" in memberships,
                "balanced": "BALANCED" in memberships,
                "premium": "PREMIUM" in memberships,
                "membership_count": len(memberships),
                "membership_roles": "+".join(memberships),
            }
        )
        rows.append(row)
    master = pd.DataFrame(rows).sort_values(["entry_dt", "exit_dt"], kind="mergesort")
    if len(master) > 1:
        current = master.entry_dt.iloc[1:].reset_index(drop=True)
        prior_exit = master.exit_dt.iloc[:-1].reset_index(drop=True)
        if bool((current < prior_exit).any()):
            raise ValueError("SOURCE_UNION_HAS_OVERLAPPING_POSITIONS")
    return master.reset_index(drop=True)


def lane_mask(master: pd.DataFrame, lane: str) -> pd.Series:
    if lane == "CORE":
        return master.core
    if lane == "BALANCED":
        return master.balanced
    if lane == "PREMIUM":
        return master.premium
    if lane == "CORE_OR_BALANCED":
        return master.core | master.balanced
    if lane == "CORE_OR_PREMIUM":
        return master.core | master.premium
    if lane == "BALANCED_OR_PREMIUM":
        return master.balanced | master.premium
    if lane == "ANY_OF_THREE":
        return master.core | master.balanced | master.premium
    if lane == "AT_LEAST_TWO_OF_THREE":
        return master.membership_count >= 2
    if lane == "ALL_THREE":
        return master.membership_count == 3
    raise ValueError(lane)


def selection_summary(frame: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any], dict[str, Any]]:
    selected = frame[frame.entry_dt.dt.year.isin(SELECTION_YEARS)].copy()
    selected = selected.sort_values(["entry_dt", "exit_dt"], kind="mergesort")
    summary = stage320.summary_rows(selected)
    yearly = stage308.yearly_summary(frame.to_dict(orient="records"))
    return selected, summary, yearly


def shadow_gate(
    summary: dict[str, Any],
    yearly: dict[str, Any],
    leave_one_out: dict[str, Any],
    rolling: dict[str, Any],
    iid: dict[str, Any],
    block: dict[str, Any],
) -> dict[str, Any]:
    year_counts = [int(yearly[str(year)]["trades"]) for year in SELECTION_YEARS]
    checks = {
        "minimum_selection_trades": int(summary["trades"])
        >= int(SHADOW_GATE["minimum_selection_trades"]),
        "minimum_each_selection_year_trades": min(year_counts, default=0)
        >= int(SHADOW_GATE["minimum_each_selection_year_trades"]),
        "minimum_selection_win_rate": float(summary["win_rate"])
        >= float(SHADOW_GATE["minimum_selection_win_rate"]),
        "minimum_profit_factor": stage320.pf_number(summary)
        >= float(SHADOW_GATE["minimum_profit_factor"]),
        "minimum_total_r": float(summary["spread_adjusted_total_r"])
        > float(SHADOW_GATE["minimum_total_r_exclusive"]),
        "maximum_drawdown_r": float(summary["spread_adjusted_max_drawdown_r"])
        <= float(SHADOW_GATE["maximum_drawdown_r"]),
        "maximum_largest_winner_share": float(
            summary["largest_win_share_of_positive_pnl"]
        ) <= float(SHADOW_GATE["maximum_largest_winner_share"]),
        "minimum_leave_one_quarter_out_total_r": float(
            leave_one_out["minimum_total_r"]
        ) > float(SHADOW_GATE["minimum_leave_one_quarter_out_total_r_exclusive"]),
        "minimum_rolling_6m_positive_ratio": float(
            rolling["positive_total_r_ratio"]
        ) >= float(SHADOW_GATE["minimum_rolling_6m_positive_ratio"]),
        "minimum_iid_bootstrap_positive_r_probability": float(
            iid["positive_total_r_probability"]
        ) >= float(SHADOW_GATE["minimum_iid_bootstrap_positive_r_probability"]),
        "minimum_quarter_block_bootstrap_positive_r_probability": float(
            block["positive_total_r_probability"]
        ) >= float(
            SHADOW_GATE["minimum_quarter_block_bootstrap_positive_r_probability"]
        ),
    }
    return {"pass": bool(all(checks.values())), "checks": checks}


def lane_score(row: dict[str, Any]) -> float:
    summary = row["selection_2024_2025"]
    return float(
        100.0 * float(summary["win_rate"])
        + 3.0 * min(stage320.pf_number(summary), 5.0)
        + 0.25 * float(summary["trades"])
        + float(summary["spread_adjusted_total_r"])
        - float(summary["spread_adjusted_max_drawdown_r"])
        + 5.0 * float(row["iid_trade_bootstrap"]["positive_total_r_probability"])
        + 2.0 * float(row["quarter_block_bootstrap"]["positive_total_r_probability"])
    )


def main() -> int:
    args = parse_args()
    result_path = Path(args.stage320_json).expanduser().resolve()
    paths = {
        "core": Path(args.core_csv).expanduser().resolve(),
        "balanced": Path(args.balanced_csv).expanduser().resolve(),
        "premium": Path(args.premium_csv).expanduser().resolve(),
    }
    output_path = Path(args.output).expanduser().resolve()
    leaderboard_path = Path(args.leaderboard_csv).expanduser().resolve()
    selected_path = Path(args.selected_shadow_csv).expanduser().resolve()

    result = json.loads(result_path.read_text(encoding="utf-8"))
    hashes = verify_sources(result, result_path, paths)
    frames = {
        "CORE": load_csv(paths["core"], EXPECTED_PROFILES["CORE"]),
        "BALANCED": load_csv(paths["balanced"], EXPECTED_PROFILES["BALANCED"]),
        "PREMIUM": load_csv(paths["premium"], EXPECTED_PROFILES["PREMIUM"]),
    }
    master = build_master(frames)

    leaderboard: list[dict[str, Any]] = []
    lane_frames: dict[str, pd.DataFrame] = {}
    for ordinal, lane in enumerate(LANES):
        frame = master[lane_mask(master, lane)].copy()
        frame["portfolio_lane"] = lane
        lane_frames[lane] = frame
        selection, summary, yearly = selection_summary(frame)
        leave_one_out = stage320.leave_one_quarter_out(selection)
        rolling = stage320.rolling_six_months(selection)
        iid = stage320.iid_bootstrap(selection, RNG_SEED + ordinal * 11)
        block = stage320.quarter_block_bootstrap(selection, RNG_SEED + ordinal * 17)
        permutation = stage320.permutation_drawdown(selection, RNG_SEED + ordinal * 23)
        lower, upper = stage320.wilson_interval(
            int(summary["wins"]), int(summary["trades"])
        )
        gate = shadow_gate(summary, yearly, leave_one_out, rolling, iid, block)
        row = {
            "portfolio_lane": lane,
            "lane_definition": LANES[lane],
            "all_period": stage320.summary_rows(frame),
            "selection_2024_2025": summary,
            "yearly": yearly,
            "leave_one_active_quarter_out": leave_one_out,
            "rolling_6m": rolling,
            "iid_trade_bootstrap": iid,
            "quarter_block_bootstrap": block,
            "permutation_drawdown": permutation,
            "win_rate_wilson_95": {"lower": lower, "upper": upper},
            "shadow_gate": gate,
            "stress_2026_display_only": yearly[str(DISPLAY_ONLY_YEAR)],
        }
        row["lane_score_2024_2025_only"] = lane_score(row)
        leaderboard.append(row)

    passes = [row for row in leaderboard if row["shadow_gate"]["pass"]]
    passes.sort(
        key=lambda row: (
            -float(row["lane_score_2024_2025_only"]),
            -int(row["selection_2024_2025"]["trades"]),
            row["portfolio_lane"],
        )
    )
    selected = passes[0] if passes else None
    selected_lane = selected["portfolio_lane"] if selected else None

    leaderboard.sort(
        key=lambda row: (
            -int(row["shadow_gate"]["pass"]),
            -float(row["lane_score_2024_2025_only"]),
            row["portfolio_lane"],
        )
    )
    flat_rows: list[dict[str, Any]] = []
    for row in leaderboard:
        summary = row["selection_2024_2025"]
        stress = row["stress_2026_display_only"]
        flat_rows.append(
            {
                "portfolio_lane": row["portfolio_lane"],
                "lane_definition": row["lane_definition"],
                "shadow_gate_pass": row["shadow_gate"]["pass"],
                "lane_score_2024_2025_only": row["lane_score_2024_2025_only"],
                "trades_2024_2025": summary["trades"],
                "win_rate_2024_2025": summary["win_rate"],
                "profit_factor_2024_2025": summary["spread_adjusted_profit_factor"],
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
                "permutation_dd_p95": row["permutation_drawdown"]["drawdown_p95"],
                "wilson_win_rate_lower_95": row["win_rate_wilson_95"]["lower"],
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
    if selected_lane is None:
        pd.DataFrame(columns=["portfolio_lane"]).to_csv(
            selected_path, index=False, encoding="utf-8-sig"
        )
    else:
        lane_frames[selected_lane].to_csv(
            selected_path, index=False, encoding="utf-8-sig"
        )

    overlap = {
        "core_balanced": int((master.core & master.balanced).sum()),
        "core_premium": int((master.core & master.premium).sum()),
        "balanced_premium": int((master.balanced & master.premium).sum()),
        "all_three": int((master.membership_count == 3).sum()),
        "core_only": int((master.core & ~master.balanced & ~master.premium).sum()),
        "balanced_only": int((master.balanced & ~master.core & ~master.premium).sum()),
        "premium_only": int((master.premium & ~master.core & ~master.balanced).sum()),
    }
    if selected is not None:
        decision = "IMMEDIATE_ROBUST_SHADOW_PORTFOLIO_FOUND"
    else:
        decision = "NO_ROBUST_SHADOW_PORTFOLIO_FOUND"
    report = {
        "status": "GOLD_V3_321_ROBUST_PROFILE_PORTFOLIO_OVERLAP_AUDIT_COMPLETE",
        "mode": "AUDIT_ONLY_IMMEDIATE_FIXED_PROFILE_COMBINATION_RESEARCH",
        "decision": decision,
        "source": {
            "stage320_json": str(result_path),
            "stage320_json_sha256": hashes["stage320_json"],
            "core_csv": str(paths["core"]),
            "core_sha256": hashes["core"],
            "balanced_csv": str(paths["balanced"]),
            "balanced_sha256": hashes["balanced"],
            "premium_csv": str(paths["premium"]),
            "premium_sha256": hashes["premium"],
        },
        "research_contract": {
            "selection_years": list(SELECTION_YEARS),
            "display_only_year": DISPLAY_ONLY_YEAR,
            "selection_and_ranking_do_not_use_2026": True,
            "new_raw_feature_thresholds_added": False,
            "fixed_stage320_profiles_only": EXPECTED_PROFILES,
            "fixed_logical_lanes": LANES,
            "duplicate_numeric_tolerance": TOL,
            "one_position_source_union_verified": True,
            "shadow_gate": SHADOW_GATE,
        },
        "overlap": overlap,
        "search": {
            "master_unique_trade_count": int(len(master)),
            "lane_count": len(leaderboard),
            "shadow_pass_count": len(passes),
        },
        "selected_shadow_portfolio": selected,
        "leaderboard": leaderboard,
        "interpretation": {
            "purpose": (
                "This stage immediately tests whether already-fixed robust profiles "
                "work better as a shadow portfolio. It does not wait for Stage319."
            ),
            "limits": (
                "Logical unions and intersections remain historical research. They "
                "cannot replace the frozen Stage319 future-only contract or change "
                "production state automatically."
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
            "stage317_research_watch": "UNCHANGED_RETAINED",
            "stage318_research_result": "UNCHANGED_RETAINED",
            "stage320_result": "UNCHANGED_RETAINED",
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
        json.dumps(json_safe(report), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(json_safe(report), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
