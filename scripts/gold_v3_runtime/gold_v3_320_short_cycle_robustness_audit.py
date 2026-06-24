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

EXPECTED_STAGE318_STATUS = (
    "GOLD_V3_318_MOCHIPOYO_HIGH_CONFIDENCE_REFINEMENT_COMPLETE"
)
EXPECTED_STAGE318_DECISION = "MOCHIPOYO_HIGHER_WIN_RATE_PRIMARY_FOUND"
SELECTION_YEARS = (2024, 2025)
DISPLAY_ONLY_YEAR = 2026
BOOTSTRAP_ITERATIONS = 10000
PERMUTATION_ITERATIONS = 5000
RNG_SEED = 320

ROBUSTNESS_GATE = {
    "minimum_selection_trades": 14,
    "minimum_each_selection_year_trades": 6,
    "minimum_each_selection_year_total_r_exclusive": 0.0,
    "minimum_profit_factor": 1.50,
    "minimum_total_r_exclusive": 0.0,
    "maximum_drawdown_r": 4.0,
    "maximum_largest_winner_share": 0.35,
    "minimum_leave_one_quarter_out_total_r_exclusive": 0.0,
    "minimum_rolling_6m_positive_ratio": 0.90,
    "minimum_iid_bootstrap_positive_r_probability": 0.90,
    "minimum_quarter_block_bootstrap_positive_r_probability": 0.80,
}

CORE_MIN_TRADES = 20
BALANCED_MIN_TRADES = 16
PREMIUM_MIN_TRADES = 14


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage318-json", required=True)
    parser.add_argument("--stage318-all-profiles", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--leaderboard-csv", required=True)
    parser.add_argument("--core-csv", required=True)
    parser.add_argument("--balanced-csv", required=True)
    parser.add_argument("--premium-csv", required=True)
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


def pf_number(summary: dict[str, Any]) -> float:
    value = summary.get("spread_adjusted_profit_factor")
    if value is None and float(summary.get("spread_adjusted_total_usd", 0.0)) > 0.0:
        return float("inf")
    return float(value or 0.0)


def wilson_interval(wins: int, trades: int, z: float = 1.959963984540054) -> tuple[float, float]:
    if trades <= 0:
        return 0.0, 0.0
    p = wins / trades
    denominator = 1.0 + z * z / trades
    center = (p + z * z / (2.0 * trades)) / denominator
    margin = (
        z
        * math.sqrt((p * (1.0 - p) + z * z / (4.0 * trades)) / trades)
        / denominator
    )
    return max(0.0, center - margin), min(1.0, center + margin)


def summary_rows(frame: pd.DataFrame) -> dict[str, Any]:
    return stage308.summarize(frame.to_dict(orient="records"))


def quarterly_metrics(frame: pd.DataFrame) -> list[dict[str, Any]]:
    work = frame.copy()
    work["quarter"] = work.entry_dt.dt.to_period("Q").astype(str)
    output: list[dict[str, Any]] = []
    for quarter, group in work.groupby("quarter", sort=True):
        output.append({"quarter": quarter, **summary_rows(group)})
    return output


def leave_one_quarter_out(frame: pd.DataFrame) -> dict[str, Any]:
    work = frame.copy()
    work["quarter"] = work.entry_dt.dt.to_period("Q").astype(str)
    rows: list[dict[str, Any]] = []
    for quarter in sorted(work.quarter.unique()):
        summary = summary_rows(work[work.quarter != quarter])
        rows.append({"excluded_quarter": quarter, **summary})
    if not rows:
        return {
            "rows": [],
            "minimum_total_r": 0.0,
            "minimum_profit_factor": 0.0,
            "all_total_r_positive": False,
        }
    return {
        "rows": rows,
        "minimum_total_r": float(
            min(row["spread_adjusted_total_r"] for row in rows)
        ),
        "minimum_profit_factor": float(min(pf_number(row) for row in rows)),
        "all_total_r_positive": bool(
            all(float(row["spread_adjusted_total_r"]) > 0.0 for row in rows)
        ),
    }


def rolling_six_months(frame: pd.DataFrame) -> dict[str, Any]:
    if frame.empty:
        return {
            "rows": [],
            "eligible_window_count": 0,
            "positive_total_r_ratio": 0.0,
            "minimum_total_r": 0.0,
            "minimum_profit_factor": 0.0,
        }
    first_month = frame.entry_dt.min().to_period("M")
    last_month = frame.entry_dt.max().to_period("M")
    rows: list[dict[str, Any]] = []
    for period in pd.period_range(first_month, last_month, freq="M"):
        start = period.start_time
        end = start + pd.DateOffset(months=6)
        group = frame[(frame.entry_dt >= start) & (frame.entry_dt < end)]
        if len(group) < 3:
            continue
        rows.append(
            {
                "start_month": str(period),
                "end_exclusive": str(end),
                **summary_rows(group),
            }
        )
    if not rows:
        return {
            "rows": [],
            "eligible_window_count": 0,
            "positive_total_r_ratio": 0.0,
            "minimum_total_r": 0.0,
            "minimum_profit_factor": 0.0,
        }
    positive_ratio = sum(
        float(row["spread_adjusted_total_r"]) > 0.0 for row in rows
    ) / len(rows)
    return {
        "rows": rows,
        "eligible_window_count": len(rows),
        "positive_total_r_ratio": float(positive_ratio),
        "minimum_total_r": float(
            min(row["spread_adjusted_total_r"] for row in rows)
        ),
        "minimum_profit_factor": float(min(pf_number(row) for row in rows)),
    }


def iid_bootstrap(frame: pd.DataFrame, seed: int) -> dict[str, Any]:
    r_values = pd.to_numeric(frame.spread_adjusted_r, errors="raise").to_numpy(float)
    pnl_values = pd.to_numeric(
        frame.spread_adjusted_pnl, errors="raise"
    ).to_numpy(float)
    trades = len(frame)
    if trades == 0:
        return {
            "iterations": BOOTSTRAP_ITERATIONS,
            "positive_total_r_probability": 0.0,
            "total_r_p05": 0.0,
            "total_r_median": 0.0,
            "total_r_p95": 0.0,
            "win_rate_p05": 0.0,
            "win_rate_median": 0.0,
            "win_rate_p95": 0.0,
        }
    rng = np.random.default_rng(seed)
    indices = rng.integers(
        0,
        trades,
        size=(BOOTSTRAP_ITERATIONS, trades),
    )
    sampled_r = r_values[indices].sum(axis=1)
    sampled_wr = (pnl_values[indices] > 0.0).mean(axis=1)
    return {
        "iterations": BOOTSTRAP_ITERATIONS,
        "positive_total_r_probability": float((sampled_r > 0.0).mean()),
        "total_r_p05": float(np.quantile(sampled_r, 0.05)),
        "total_r_median": float(np.quantile(sampled_r, 0.50)),
        "total_r_p95": float(np.quantile(sampled_r, 0.95)),
        "win_rate_p05": float(np.quantile(sampled_wr, 0.05)),
        "win_rate_median": float(np.quantile(sampled_wr, 0.50)),
        "win_rate_p95": float(np.quantile(sampled_wr, 0.95)),
    }


def quarter_block_bootstrap(frame: pd.DataFrame, seed: int) -> dict[str, Any]:
    work = frame.copy()
    work["quarter"] = work.entry_dt.dt.to_period("Q").astype(str)
    quarter_totals = (
        work.groupby("quarter", sort=True).spread_adjusted_r.sum().to_numpy(float)
    )
    count = len(quarter_totals)
    if count == 0:
        return {
            "iterations": BOOTSTRAP_ITERATIONS,
            "active_quarter_count": 0,
            "positive_total_r_probability": 0.0,
            "total_r_p05": 0.0,
            "total_r_median": 0.0,
            "total_r_p95": 0.0,
        }
    rng = np.random.default_rng(seed)
    indices = rng.integers(
        0,
        count,
        size=(BOOTSTRAP_ITERATIONS, count),
    )
    sampled = quarter_totals[indices].sum(axis=1)
    return {
        "iterations": BOOTSTRAP_ITERATIONS,
        "active_quarter_count": count,
        "positive_total_r_probability": float((sampled > 0.0).mean()),
        "total_r_p05": float(np.quantile(sampled, 0.05)),
        "total_r_median": float(np.quantile(sampled, 0.50)),
        "total_r_p95": float(np.quantile(sampled, 0.95)),
    }


def permutation_drawdown(frame: pd.DataFrame, seed: int) -> dict[str, Any]:
    values = pd.to_numeric(frame.spread_adjusted_r, errors="raise").to_numpy(float)
    if len(values) == 0:
        return {
            "iterations": PERMUTATION_ITERATIONS,
            "drawdown_p50": 0.0,
            "drawdown_p95": 0.0,
            "drawdown_max": 0.0,
        }
    rng = np.random.default_rng(seed)
    drawdowns = np.empty(PERMUTATION_ITERATIONS, dtype=float)
    for index in range(PERMUTATION_ITERATIONS):
        ordered = rng.permutation(values)
        equity = np.cumsum(ordered)
        peak = np.maximum.accumulate(np.maximum(equity, 0.0))
        drawdowns[index] = float(np.max(peak - equity))
    return {
        "iterations": PERMUTATION_ITERATIONS,
        "drawdown_p50": float(np.quantile(drawdowns, 0.50)),
        "drawdown_p95": float(np.quantile(drawdowns, 0.95)),
        "drawdown_max": float(drawdowns.max()),
    }


def robustness_gate(
    summary: dict[str, Any],
    yearly: dict[str, Any],
    leave_one_out: dict[str, Any],
    rolling: dict[str, Any],
    iid: dict[str, Any],
    block: dict[str, Any],
) -> dict[str, Any]:
    year_counts = [int(yearly[str(year)]["trades"]) for year in SELECTION_YEARS]
    year_r = [
        float(yearly[str(year)]["spread_adjusted_total_r"])
        for year in SELECTION_YEARS
    ]
    checks = {
        "minimum_selection_trades": int(summary["trades"])
        >= int(ROBUSTNESS_GATE["minimum_selection_trades"]),
        "minimum_each_selection_year_trades": min(year_counts, default=0)
        >= int(ROBUSTNESS_GATE["minimum_each_selection_year_trades"]),
        "minimum_each_selection_year_total_r": min(year_r, default=0.0)
        > float(
            ROBUSTNESS_GATE["minimum_each_selection_year_total_r_exclusive"]
        ),
        "minimum_profit_factor": pf_number(summary)
        >= float(ROBUSTNESS_GATE["minimum_profit_factor"]),
        "minimum_total_r": float(summary["spread_adjusted_total_r"])
        > float(ROBUSTNESS_GATE["minimum_total_r_exclusive"]),
        "maximum_drawdown_r": float(summary["spread_adjusted_max_drawdown_r"])
        <= float(ROBUSTNESS_GATE["maximum_drawdown_r"]),
        "maximum_largest_winner_share": float(
            summary["largest_win_share_of_positive_pnl"]
        )
        <= float(ROBUSTNESS_GATE["maximum_largest_winner_share"]),
        "minimum_leave_one_quarter_out_total_r": float(
            leave_one_out["minimum_total_r"]
        )
        > float(
            ROBUSTNESS_GATE[
                "minimum_leave_one_quarter_out_total_r_exclusive"
            ]
        ),
        "minimum_rolling_6m_positive_ratio": float(
            rolling["positive_total_r_ratio"]
        )
        >= float(ROBUSTNESS_GATE["minimum_rolling_6m_positive_ratio"]),
        "minimum_iid_bootstrap_positive_r_probability": float(
            iid["positive_total_r_probability"]
        )
        >= float(
            ROBUSTNESS_GATE["minimum_iid_bootstrap_positive_r_probability"]
        ),
        "minimum_quarter_block_bootstrap_positive_r_probability": float(
            block["positive_total_r_probability"]
        )
        >= float(
            ROBUSTNESS_GATE[
                "minimum_quarter_block_bootstrap_positive_r_probability"
            ]
        ),
    }
    return {"pass": bool(all(checks.values())), "checks": checks}


def robust_score(row: dict[str, Any]) -> float:
    summary = row["selection_2024_2025"]
    iid = row["iid_trade_bootstrap"]
    rolling = row["rolling_6m"]
    return float(
        100.0 * float(summary["win_rate"])
        + 2.0 * min(pf_number(summary), 5.0)
        + 0.30 * float(summary["trades"])
        + float(summary["spread_adjusted_total_r"])
        - 0.75 * float(summary["spread_adjusted_max_drawdown_r"])
        + 5.0 * float(iid["positive_total_r_probability"])
        + 2.0 * float(rolling["positive_total_r_ratio"])
    )


def select_best(
    rows: list[dict[str, Any]],
    minimum_trades: int,
    *,
    exclude_profiles: set[str] | None = None,
) -> dict[str, Any] | None:
    excluded = exclude_profiles or set()
    candidates = [
        row
        for row in rows
        if row["robustness_gate"]["pass"]
        and int(row["selection_2024_2025"]["trades"]) >= minimum_trades
        and row["profile_name"] not in excluded
    ]
    candidates.sort(
        key=lambda row: (
            -float(row["robust_score_2024_2025_only"]),
            -int(row["selection_2024_2025"]["trades"]),
            row["profile_name"],
        )
    )
    return candidates[0] if candidates else None


def write_profile_rows(
    path: Path,
    all_profiles: pd.DataFrame,
    profile_name: str | None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if profile_name is None:
        pd.DataFrame(columns=["profile_name"]).to_csv(
            path,
            index=False,
            encoding="utf-8-sig",
        )
        return
    selected = all_profiles[all_profiles.profile_name.eq(profile_name)].copy()
    selected.to_csv(path, index=False, encoding="utf-8-sig")


def main() -> int:
    args = parse_args()
    stage318_json_path = Path(args.stage318_json).expanduser().resolve()
    all_profiles_path = Path(args.stage318_all_profiles).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()
    leaderboard_csv = Path(args.leaderboard_csv).expanduser().resolve()
    core_csv = Path(args.core_csv).expanduser().resolve()
    balanced_csv = Path(args.balanced_csv).expanduser().resolve()
    premium_csv = Path(args.premium_csv).expanduser().resolve()

    stage318 = json.loads(stage318_json_path.read_text(encoding="utf-8"))
    if stage318.get("status") != EXPECTED_STAGE318_STATUS:
        raise ValueError(f"STAGE318_STATUS_UNEXPECTED: {stage318.get('status')}")
    if stage318.get("decision") != EXPECTED_STAGE318_DECISION:
        raise ValueError(f"STAGE318_DECISION_UNEXPECTED: {stage318.get('decision')}")
    expected_sha = stage318.get("outputs", {}).get("all_profiles_sha256")
    actual_sha = sha256_file(all_profiles_path)
    if expected_sha != actual_sha:
        raise ValueError(
            "STAGE318_ALL_PROFILES_SHA_MISMATCH: "
            f"expected={expected_sha} actual={actual_sha}"
        )

    all_profiles = pd.read_csv(all_profiles_path, encoding="utf-8-sig")
    required = {
        "profile_name",
        "entry_dt",
        "exit_dt",
        "spread_adjusted_pnl",
        "spread_adjusted_r",
    }
    missing = sorted(required - set(all_profiles.columns))
    if missing:
        raise ValueError(f"STAGE318_ALL_PROFILES_COLUMNS_MISSING: {missing}")
    for column in ("entry_dt", "exit_dt"):
        all_profiles[column] = pd.to_datetime(
            all_profiles[column],
            errors="raise",
        )

    fixed_profiles = list(stage318["research_contract"]["fixed_profiles"])
    observed_profiles = sorted(set(all_profiles.profile_name.astype(str)))
    if sorted(fixed_profiles) != observed_profiles:
        raise ValueError(
            "STAGE318_PROFILE_SET_MISMATCH: "
            f"expected={sorted(fixed_profiles)} actual={observed_profiles}"
        )

    leaderboard: list[dict[str, Any]] = []
    for ordinal, profile_name in enumerate(fixed_profiles):
        full = all_profiles[all_profiles.profile_name.eq(profile_name)].copy()
        selection = full[full.entry_dt.dt.year.isin(SELECTION_YEARS)].copy()
        selection = selection.sort_values(["entry_dt", "exit_dt"], kind="mergesort")
        rows = full.to_dict(orient="records")
        selection_summary = summary_rows(selection)
        yearly = stage308.yearly_summary(rows)
        quarters = quarterly_metrics(selection)
        leave_one_out = leave_one_quarter_out(selection)
        rolling = rolling_six_months(selection)
        iid = iid_bootstrap(selection, RNG_SEED + ordinal * 11)
        block = quarter_block_bootstrap(selection, RNG_SEED + ordinal * 17)
        permutation = permutation_drawdown(selection, RNG_SEED + ordinal * 23)
        lower, upper = wilson_interval(
            int(selection_summary["wins"]),
            int(selection_summary["trades"]),
        )
        gate = robustness_gate(
            selection_summary,
            yearly,
            leave_one_out,
            rolling,
            iid,
            block,
        )
        active_quarter_positive_ratio = (
            sum(float(row["spread_adjusted_total_r"]) > 0.0 for row in quarters)
            / len(quarters)
            if quarters
            else 0.0
        )
        item = {
            "profile_name": profile_name,
            "all_period": summary_rows(full),
            "selection_2024_2025": selection_summary,
            "yearly": yearly,
            "active_quarters": quarters,
            "active_quarter_positive_ratio": float(
                active_quarter_positive_ratio
            ),
            "leave_one_active_quarter_out": leave_one_out,
            "rolling_6m": rolling,
            "iid_trade_bootstrap": iid,
            "quarter_block_bootstrap": block,
            "permutation_drawdown": permutation,
            "win_rate_wilson_95": {
                "lower": float(lower),
                "upper": float(upper),
            },
            "robustness_gate": gate,
            "stress_2026_display_only": yearly[str(DISPLAY_ONLY_YEAR)],
        }
        item["robust_score_2024_2025_only"] = robust_score(item)
        leaderboard.append(item)

    robust_passes = [row for row in leaderboard if row["robustness_gate"]["pass"]]
    core = select_best(leaderboard, CORE_MIN_TRADES)
    balanced = select_best(
        leaderboard,
        BALANCED_MIN_TRADES,
        exclude_profiles={core["profile_name"]} if core else set(),
    )
    premium_candidates = [
        row
        for row in leaderboard
        if row["robustness_gate"]["pass"]
        and int(row["selection_2024_2025"]["trades"]) >= PREMIUM_MIN_TRADES
    ]
    premium_candidates.sort(
        key=lambda row: (
            -float(row["selection_2024_2025"]["win_rate"]),
            -float(row["robust_score_2024_2025_only"]),
            row["profile_name"],
        )
    )
    premium = premium_candidates[0] if premium_candidates else None

    leaderboard.sort(
        key=lambda row: (
            -int(row["robustness_gate"]["pass"]),
            -float(row["robust_score_2024_2025_only"]),
            row["profile_name"],
        )
    )

    leaderboard_csv.parent.mkdir(parents=True, exist_ok=True)
    flat_rows: list[dict[str, Any]] = []
    for row in leaderboard:
        summary = row["selection_2024_2025"]
        flat_rows.append(
            {
                "profile_name": row["profile_name"],
                "robustness_pass": row["robustness_gate"]["pass"],
                "robust_score_2024_2025_only": row[
                    "robust_score_2024_2025_only"
                ],
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
                "permutation_dd_p95": row["permutation_drawdown"][
                    "drawdown_p95"
                ],
                "wilson_win_rate_lower_95": row["win_rate_wilson_95"]["lower"],
                "wilson_win_rate_upper_95": row["win_rate_wilson_95"]["upper"],
                "trades_2026_display_only": row[
                    "stress_2026_display_only"
                ]["trades"],
                "win_rate_2026_display_only": row[
                    "stress_2026_display_only"
                ]["win_rate"],
                "total_r_2026_display_only": row[
                    "stress_2026_display_only"
                ]["spread_adjusted_total_r"],
            }
        )
    pd.DataFrame(flat_rows).to_csv(
        leaderboard_csv,
        index=False,
        encoding="utf-8-sig",
    )

    core_name = core["profile_name"] if core else None
    balanced_name = balanced["profile_name"] if balanced else None
    premium_name = premium["profile_name"] if premium else None
    write_profile_rows(core_csv, all_profiles, core_name)
    write_profile_rows(balanced_csv, all_profiles, balanced_name)
    write_profile_rows(premium_csv, all_profiles, premium_name)

    if core is not None and balanced is not None and premium is not None:
        decision = "IMMEDIATE_ROBUST_CORE_BALANCED_AND_PREMIUM_FOUND"
    elif core is not None:
        decision = "IMMEDIATE_ROBUST_CORE_ONLY_FOUND"
    else:
        decision = "NO_IMMEDIATE_ROBUST_PROFILE_FOUND"

    report = {
        "status": "GOLD_V3_320_SHORT_CYCLE_ROBUSTNESS_AUDIT_COMPLETE",
        "mode": "AUDIT_ONLY_IMMEDIATE_HISTORICAL_ROBUSTNESS",
        "decision": decision,
        "source": {
            "stage318_json": str(stage318_json_path),
            "stage318_json_sha256": sha256_file(stage318_json_path),
            "stage318_all_profiles_csv": str(all_profiles_path),
            "stage318_all_profiles_sha256": actual_sha,
        },
        "research_contract": {
            "selection_years": list(SELECTION_YEARS),
            "display_only_year": DISPLAY_ONLY_YEAR,
            "selection_and_ranking_do_not_use_2026": True,
            "new_trading_thresholds_added": False,
            "fixed_stage318_profiles_only": fixed_profiles,
            "bootstrap_iterations": BOOTSTRAP_ITERATIONS,
            "permutation_iterations": PERMUTATION_ITERATIONS,
            "random_seed": RNG_SEED,
            "robustness_gate": ROBUSTNESS_GATE,
            "core_minimum_trades": CORE_MIN_TRADES,
            "balanced_minimum_trades": BALANCED_MIN_TRADES,
            "premium_minimum_trades": PREMIUM_MIN_TRADES,
        },
        "search": {
            "profile_count": len(leaderboard),
            "robust_pass_count": len(robust_passes),
        },
        "selected": {
            "core": core,
            "balanced_challenger": balanced,
            "premium": premium,
        },
        "leaderboard": leaderboard,
        "interpretation": {
            "purpose": (
                "This stage does not wait for future candles. It immediately tests "
                "the already-fixed Stage318 profiles through chronological slices, "
                "leave-one-quarter-out analysis, bootstrap resampling, and order-risk "
                "permutation."
            ),
            "limits": (
                "These tests reuse historical trades and therefore cannot replace "
                "Stage319 future-only evidence. They can reject fragile profiles and "
                "identify the best short-cycle shadow candidates now."
            ),
        },
        "outputs": {
            "result_json": str(output_path),
            "leaderboard_csv": str(leaderboard_csv),
            "core_trades_csv": str(core_csv),
            "balanced_challenger_trades_csv": str(balanced_csv),
            "premium_trades_csv": str(premium_csv),
            "leaderboard_sha256": sha256_file(leaderboard_csv),
            "core_trades_sha256": sha256_file(core_csv),
            "balanced_challenger_trades_sha256": sha256_file(balanced_csv),
            "premium_trades_sha256": sha256_file(premium_csv),
        },
        "promotion": {
            "performed": False,
            "stage319_contract": "UNCHANGED_FROZEN",
            "stage314_contract": "UNCHANGED_ACTIVE",
            "stage317_research_watch": "UNCHANGED_RETAINED",
            "stage318_research_result": "UNCHANGED_RETAINED",
            "stage315_independent_research": "UNCHANGED",
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
