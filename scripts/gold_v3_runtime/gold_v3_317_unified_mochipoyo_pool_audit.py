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

YEARS = (2024, 2025, 2026)
TOL = 1e-12

FILTER_NAMES = (
    "BASE",
    "QUALITY_GE_7_5",
    "QUALITY_GE_8_0",
    "QUALITY_GE_8_5",
    "ATR_RATIO_GE_1_0",
    "NO_ROUND_NUMBER",
    "RISK_ATR_LE_1_25",
    "QUALITY_GE_8_AND_ATR_GE_1",
    "QUALITY_GE_8_AND_NO_ROUND",
    "ATR_GE_1_AND_NO_ROUND",
    "EXTENSION_0_TO_0_8",
    "QUALITY_GE_8_AND_EXT_0_TO_0_8",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage316-json", required=True)
    parser.add_argument("--stage311-trades", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--all-candidates-csv", required=True)
    parser.add_argument("--selected-csv", required=True)
    parser.add_argument("--stage313-trades", default="")
    parser.add_argument("--top", type=int, default=250)
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


def filter_mask(frame: pd.DataFrame, name: str) -> pd.Series:
    if name == "BASE":
        return pd.Series(True, index=frame.index)
    if name == "QUALITY_GE_7_5":
        return frame.quality_score >= 7.5
    if name == "QUALITY_GE_8_0":
        return frame.quality_score >= 8.0
    if name == "QUALITY_GE_8_5":
        return frame.quality_score >= 8.5
    if name == "ATR_RATIO_GE_1_0":
        return frame.atr_ratio_signal >= 1.0
    if name == "NO_ROUND_NUMBER":
        return ~frame.round_number_near
    if name == "RISK_ATR_LE_1_25":
        return frame.risk_atr <= 1.25
    if name == "QUALITY_GE_8_AND_ATR_GE_1":
        return (frame.quality_score >= 8.0) & (frame.atr_ratio_signal >= 1.0)
    if name == "QUALITY_GE_8_AND_NO_ROUND":
        return (frame.quality_score >= 8.0) & (~frame.round_number_near)
    if name == "ATR_GE_1_AND_NO_ROUND":
        return (frame.atr_ratio_signal >= 1.0) & (~frame.round_number_near)
    if name == "EXTENSION_0_TO_0_8":
        return frame.extension_atr_signal.between(0.0, 0.8)
    if name == "QUALITY_GE_8_AND_EXT_0_TO_0_8":
        return (
            (frame.quality_score >= 8.0)
            & frame.extension_atr_signal.between(0.0, 0.8)
        )
    raise ValueError(name)


def assert_duplicate_parity(group: pd.DataFrame) -> None:
    if len(group) <= 1:
        return
    for column in ("decision_dt", "entry_dt", "exit_dt", "direction_num"):
        if group[column].nunique(dropna=False) != 1:
            raise ValueError(
                f"POOLED_DUPLICATE_EXACT_PARITY_FAILED: {column}"
            )
    for column in (
        "entry_price",
        "sl_price",
        "tp_price",
        "exit_price",
        "risk_price",
        "spread_adjusted_pnl",
        "spread_adjusted_r",
    ):
        values = pd.to_numeric(group[column], errors="raise")
        if float(values.max() - values.min()) > TOL:
            raise ValueError(
                f"POOLED_DUPLICATE_NUMERIC_PARITY_FAILED: {column} "
                f"spread={float(values.max() - values.min())}"
            )


def pooled_rows(frame: pd.DataFrame) -> pd.DataFrame:
    rows: list[pd.Series] = []
    keys = ["pair", "direction", "exit_profile", "entry_dt"]
    for _, group in frame.groupby(keys, sort=True, dropna=False):
        assert_duplicate_parity(group)
        ordered = group.sort_values(
            ["quality_score", "track"],
            ascending=[False, True],
            kind="mergesort",
        )
        row = ordered.iloc[0].copy()
        tracks = sorted(set(group.track.astype(str)))
        row["pooled_tracks"] = "+".join(tracks)
        row["pooled_track_count"] = len(tracks)
        row["quality_score"] = float(group.quality_score.max())
        rows.append(row)
    result = pd.DataFrame(rows)
    return result.sort_values(
        ["pair", "direction", "exit_profile", "entry_dt"],
        kind="mergesort",
    ).reset_index(drop=True)


def one_position(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return frame.copy()
    ordered = frame.sort_values(
        ["entry_dt", "exit_dt", "pooled_tracks"],
        kind="mergesort",
    )
    accepted: list[pd.Series] = []
    active_exit: pd.Timestamp | None = None
    for _, row in ordered.iterrows():
        if active_exit is None or pd.Timestamp(row.entry_dt) >= active_exit:
            accepted.append(row)
            active_exit = pd.Timestamp(row.exit_dt)
    return pd.DataFrame(accepted)


def load_reference(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=["entry_dt", "exit_dt"])
    frame = pd.read_csv(path, encoding="utf-8-sig")
    if not {"entry_dt", "exit_dt"}.issubset(frame.columns):
        return pd.DataFrame(columns=["entry_dt", "exit_dt"])
    frame["entry_dt"] = pd.to_datetime(frame.entry_dt, errors="coerce")
    frame["exit_dt"] = pd.to_datetime(frame.exit_dt, errors="coerce")
    return frame.dropna(subset=["entry_dt", "exit_dt"])


def robust_sort_key(row: dict[str, Any]) -> tuple[Any, ...]:
    gate = row["gate"]
    stress = row["stress_2026"]
    return (
        -int(gate["research_pass"]),
        -float(gate["robust_score_2024_2025_only"]),
        -int(stress["positive_r"]),
        row["candidate_key"],
    )


def main() -> int:
    args = parse_args()
    stage316_path = Path(args.stage316_json).expanduser().resolve()
    stage311_path = Path(args.stage311_trades).expanduser().resolve()
    output = Path(args.output).expanduser().resolve()
    all_candidates_csv = Path(args.all_candidates_csv).expanduser().resolve()
    selected_csv = Path(args.selected_csv).expanduser().resolve()
    stage313_path = (
        Path(args.stage313_trades).expanduser().resolve()
        if args.stage313_trades
        else stage311_path.parent / "stage313_diversified_research_watch_trades.csv"
    )

    stage316 = json.loads(stage316_path.read_text(encoding="utf-8"))
    if stage316.get("status") != (
        "GOLD_V3_316_CONTEXTUAL_MOCHIPOYO_ENTRY_RESEARCH_COMPLETE"
    ):
        raise ValueError(f"STAGE316_STATUS_UNEXPECTED: {stage316.get('status')}")
    expected_stage311_sha = stage316.get("outputs", {}).get(
        "stage311_baseline_sha256"
    )
    actual_stage311_sha = sha256_file(stage311_path)
    if expected_stage311_sha and expected_stage311_sha != actual_stage311_sha:
        raise ValueError(
            "STAGE311_BASELINE_SHA_MISMATCH: "
            f"expected={expected_stage311_sha} actual={actual_stage311_sha}"
        )

    source = pd.read_csv(stage311_path, encoding="utf-8-sig")
    required = {
        "category",
        "pair",
        "track",
        "direction",
        "direction_num",
        "exit_profile",
        "decision_dt",
        "entry_dt",
        "exit_dt",
        "quality_score",
        "round_number_near",
        "atr_ratio_signal",
        "extension_atr_signal",
        "risk_price",
        "atr_entry",
        "spread_adjusted_pnl",
        "spread_adjusted_r",
    }
    missing = sorted(required - set(source.columns))
    if missing:
        raise ValueError(f"STAGE311_REQUIRED_COLUMNS_MISSING: {missing}")

    for column in ("decision_dt", "entry_dt", "exit_dt"):
        source[column] = pd.to_datetime(source[column], errors="raise")
    source["round_number_near"] = normalize_bool(source.round_number_near)
    source["risk_atr"] = pd.to_numeric(
        source.risk_price, errors="raise"
    ) / pd.to_numeric(source.atr_entry, errors="raise").replace(0.0, np.nan)

    source = source[
        source.category.eq("MOCHIPOYO")
        & source.exit_profile.isin(["RR1_25", "RR1_5"])
        & source.entry_dt.dt.year.isin(YEARS)
    ].copy()
    pooled = pooled_rows(source)

    candidate_trades: dict[str, pd.DataFrame] = {}
    leaderboard: list[dict[str, Any]] = []
    base_contracts = pooled[
        ["pair", "direction", "exit_profile"]
    ].drop_duplicates()
    for contract in base_contracts.itertuples(index=False):
        base = pooled[
            pooled.pair.eq(contract.pair)
            & pooled.direction.eq(contract.direction)
            & pooled.exit_profile.eq(contract.exit_profile)
        ].copy()
        for profile in FILTER_NAMES:
            filtered = base[filter_mask(base, profile)].copy()
            portfolio = one_position(filtered)
            rows = portfolio.to_dict(orient="records")
            development, yearly, gate = (
                stage311.development_confirmation_metrics(rows)
            )
            candidate_key = "|".join(
                [
                    str(contract.pair),
                    "MOCHI_UNION",
                    str(contract.direction),
                    str(contract.exit_profile),
                    profile,
                ]
            )
            candidate_trades[candidate_key] = portfolio
            accepted_selection = portfolio[
                portfolio.entry_dt.dt.year.isin([2024, 2025])
            ]
            track_membership: dict[str, int] = {}
            for value in accepted_selection.pooled_tracks.astype(str):
                for track in value.split("+"):
                    track_membership[track] = track_membership.get(track, 0) + 1
            y2026 = yearly["2026"]
            stress = {
                "display_only": True,
                "clean_holdout": False,
                "trades": int(y2026["trades"]),
                "profit_factor": y2026["spread_adjusted_profit_factor"],
                "total_r": float(y2026["spread_adjusted_total_r"]),
                "max_drawdown_r": float(
                    y2026["spread_adjusted_max_drawdown_r"]
                ),
                "positive_r": bool(
                    y2026["trades"] >= 5
                    and float(y2026["spread_adjusted_total_r"]) > 0.0
                ),
            }
            leaderboard.append(
                {
                    "candidate_key": candidate_key,
                    "pair": contract.pair,
                    "direction": contract.direction,
                    "exit_profile": contract.exit_profile,
                    "filter_profile": profile,
                    "raw_filtered_trades": int(len(filtered)),
                    "accepted_trades": int(len(portfolio)),
                    "development_confirmation": development,
                    "yearly": yearly,
                    "gate": gate,
                    "stress_2026": stress,
                    "selection_track_membership": track_membership,
                    "pooled_track_union": sorted(track_membership),
                }
            )

    leaderboard.sort(key=robust_sort_key)
    passing = [row for row in leaderboard if row["gate"]["research_pass"]]
    best_selection = passing[0] if passing else None
    stress_supported = [
        row
        for row in passing
        if row["stress_2026"]["positive_r"]
    ]
    stress_supported.sort(
        key=lambda row: (
            -float(row["gate"]["robust_score_2024_2025_only"]),
            row["candidate_key"],
        )
    )
    best_stress_watch = stress_supported[0] if stress_supported else None

    selected_key = (
        best_stress_watch["candidate_key"]
        if best_stress_watch is not None
        else (
            best_selection["candidate_key"]
            if best_selection is not None
            else None
        )
    )
    selected = (
        candidate_trades[selected_key].copy()
        if selected_key is not None
        else pd.DataFrame()
    )

    all_rows: list[dict[str, Any]] = []
    for key, frame in candidate_trades.items():
        for row in frame.to_dict(orient="records"):
            item = dict(row)
            item["candidate_key"] = key
            all_rows.append(item)

    all_candidates_csv.parent.mkdir(parents=True, exist_ok=True)
    if all_rows:
        pd.DataFrame(stage311.csv_safe_rows(all_rows)).to_csv(
            all_candidates_csv,
            index=False,
            encoding="utf-8-sig",
        )
    else:
        pd.DataFrame(columns=["candidate_key"]).to_csv(
            all_candidates_csv,
            index=False,
            encoding="utf-8-sig",
        )

    selected_csv.parent.mkdir(parents=True, exist_ok=True)
    if not selected.empty:
        pd.DataFrame(
            stage311.csv_safe_rows(selected.to_dict(orient="records"))
        ).to_csv(
            selected_csv,
            index=False,
            encoding="utf-8-sig",
        )
    else:
        pd.DataFrame(columns=["candidate_key"]).to_csv(
            selected_csv,
            index=False,
            encoding="utf-8-sig",
        )

    reference = load_reference(stage313_path)
    overlap = stage311.overlap_diagnostics(
        selected.to_dict(orient="records") if not selected.empty else [],
        reference,
    )

    if best_stress_watch is not None:
        decision = "UNIFIED_MOCHIPOYO_STRESS_SUPPORTED_RESEARCH_WATCH_FOUND"
    elif best_selection is not None:
        decision = "UNIFIED_MOCHIPOYO_SELECTION_LEAD_FOUND_STRESS_NOT_SUPPORTED"
    else:
        decision = "NO_UNIFIED_MOCHIPOYO_RESEARCH_LEAD_FOUND"

    report = {
        "status": "GOLD_V3_317_UNIFIED_MOCHIPOYO_POOL_AUDIT_COMPLETE",
        "mode": "AUDIT_ONLY_POOLED_ALERT_FAMILY_RESEARCH",
        "decision": decision,
        "source": {
            "stage316_json": str(stage316_path),
            "stage316_json_sha256": sha256_file(stage316_path),
            "stage316_decision": stage316.get("decision"),
            "stage311_trades": str(stage311_path),
            "stage311_trades_sha256": actual_stage311_sha,
        },
        "research_contract": {
            "selection_years": [2024, 2025],
            "display_only_year": 2026,
            "selection_does_not_use_2026": True,
            "pooled_tracks": sorted(set(source.track.astype(str))),
            "duplicate_signal_parity_tolerance": TOL,
            "dedup_key": ["pair", "direction", "exit_profile", "entry_dt"],
            "dedup_quality_rule": "maximum quality score across matching Mochipoyo tracks",
            "one_position": True,
            "preemption": False,
            "exit_profiles": ["RR1_25", "RR1_5"],
            "filter_profiles_reused_without_new_thresholds": list(FILTER_NAMES),
            "stage311_gate_unchanged": True,
        },
        "search": {
            "source_rows": int(len(source)),
            "pooled_unique_trade_rows": int(len(pooled)),
            "candidate_count": len(leaderboard),
            "research_pass_count": len(passing),
            "balanced_pass_count": sum(
                bool(row["gate"]["balanced_pass"]) for row in leaderboard
            ),
            "stress_positive_pass_count": len(stress_supported),
        },
        "best_selection_lead_2024_2025_only": best_selection,
        "best_stress_supported_research_watch": best_stress_watch,
        "selected_output_candidate_key": selected_key,
        "selected_overlap_with_stage313": overlap,
        "passing_candidates": passing[: int(args.top)],
        "leaderboard": leaderboard[: int(args.top)],
        "interpretation": {
            "stage316": (
                "Stage316 stacked a strict original alert with strict delayed "
                "confirmation and fragmented 88 trades into 56 families. "
                "Stage317 tests the same method as one alert family instead."
            ),
            "pooling": (
                "Different Mochipoyo labels are treated as descriptions of the "
                "same underlying pullback/resumption method. Exact duplicate "
                "entries must have outcome parity before pooling."
            ),
            "stress": (
                "2026 is visible and therefore display-only. A positive 2026 "
                "result may support a research watch but cannot establish a "
                "clean holdout or production readiness."
            ),
        },
        "outputs": {
            "result_json": str(output),
            "all_candidates_csv": str(all_candidates_csv),
            "selected_trades_csv": str(selected_csv),
            "all_candidates_sha256": sha256_file(all_candidates_csv),
            "selected_trades_sha256": sha256_file(selected_csv),
        },
        "promotion": {
            "performed": False,
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
