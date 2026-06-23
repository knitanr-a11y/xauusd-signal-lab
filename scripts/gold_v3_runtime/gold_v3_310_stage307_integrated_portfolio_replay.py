#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd

STAGE309_ID = "GOLD_V3_STAGE307_TOP_REV_LONG_ANY_P90"
STAGE309_PRIORITY = 15
EXISTING_PORTFOLIO_NAMES = (
    "gold_v3_stage286_short_selected_portfolio_trades.csv",
    "gold_v3_stage284_balanced_portfolio_trades.csv",
    "gold_v3_stage284_selected_portfolio_trades.csv",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candle-dir", required=True)
    parser.add_argument("--existing-portfolio-csv", default="")
    parser.add_argument("--stage309-registry", default="")
    parser.add_argument("--stage309-trades", default="")
    parser.add_argument("--output", default="")
    parser.add_argument("--accepted-csv", default="")
    parser.add_argument("--rejected-csv", default="")
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_csv(path: Path) -> pd.DataFrame:
    last_error: Exception | None = None
    for encoding in ("utf-8-sig", "utf-8", "cp932"):
        try:
            return pd.read_csv(path, encoding=encoding)
        except Exception as exc:  # pragma: no cover - fallback diagnostics
            last_error = exc
    raise RuntimeError(f"CSV_READ_FAILED: {path}: {last_error}")


def find_column(frame: pd.DataFrame, candidates: Iterable[str]) -> str | None:
    lookup = {str(column).strip().lower(): str(column) for column in frame.columns}
    for candidate in candidates:
        key = candidate.strip().lower()
        if key in lookup:
            return lookup[key]
    return None


def discover_existing_portfolio(candle_dir: Path) -> tuple[Path | None, list[str]]:
    search_root = candle_dir.parent
    diagnostics: list[str] = []
    for name in EXISTING_PORTFOLIO_NAMES:
        matches = sorted(search_root.rglob(name))
        diagnostics.extend(str(path) for path in matches)
        if matches:
            return matches[-1], diagnostics

    fallback = sorted(search_root.rglob("*stage28*portfolio*trades*.csv"))
    diagnostics.extend(str(path) for path in fallback)
    if fallback:
        preferred = [
            path
            for path in fallback
            if "286" in path.name and "selected" in path.name.lower()
        ]
        return (preferred[-1] if preferred else fallback[-1]), diagnostics
    return None, diagnostics


def normalize_source(value: Any) -> str:
    text = str(value if value is not None else "UNKNOWN").strip().upper()
    if not text or text == "NAN":
        return "UNKNOWN"
    if "BASE" in text:
        return "BASE"
    if "280" in text:
        return "STAGE280"
    if "281" in text:
        return "STAGE281"
    if "286" in text or "SHORT" in text:
        return "STAGE286"
    if "307" in text or "309" in text:
        return "STAGE307_TOP"
    return text


def source_priority(source: str) -> int:
    return {
        "BASE": 0,
        "STAGE280": 10,
        "STAGE307_TOP": STAGE309_PRIORITY,
        "STAGE281": 20,
        "STAGE286": 60,
    }.get(source, 40)


def normalize_existing(frame: pd.DataFrame, path: Path) -> tuple[pd.DataFrame, dict[str, Any]]:
    original_rows = len(frame)
    portfolio_col = find_column(frame, ("portfolio", "portfolio_name", "variant"))
    portfolio_filter = None
    if portfolio_col is not None:
        values = frame[portfolio_col].astype(str).str.upper()
        for preferred in ("PLUS_STRICT_SAFE", "SAFE", "SELECTED", "BALANCED"):
            mask = values.eq(preferred)
            if mask.any():
                frame = frame.loc[mask].copy()
                portfolio_filter = preferred
                break

    entry_col = find_column(
        frame,
        ("entry_dt", "entry_time", "entry_datetime", "planned_entry_dt", "entry"),
    )
    exit_col = find_column(
        frame,
        ("exit_dt", "exit_time", "exit_datetime", "resolved_dt", "close_dt", "exit"),
    )
    pnl_col = find_column(
        frame,
        (
            "spread_adjusted_pnl",
            "net_pnl",
            "pnl_usd",
            "net_profit_usd",
            "realized_pnl_usd",
            "result_usd",
            "pnl",
            "profit_usd",
            "profit",
            "net_profit",
            "realized_pnl",
        ),
    )
    entry_price_col = find_column(frame, ("entry_price", "reference_price", "open_price"))
    exit_price_col = find_column(frame, ("exit_price", "close_price"))
    direction_num_col = find_column(frame, ("direction_num", "side_num", "sign"))
    direction_col = find_column(frame, ("direction", "side"))
    r_col = find_column(frame, ("spread_adjusted_r", "net_r", "pnl_r", "r"))
    source_col = find_column(
        frame,
        ("source", "candidate_source", "stage", "candidate_type", "candidate_contract"),
    )
    candidate_id_col = find_column(frame, ("candidate_id", "trade_id", "id", "candidate_key"))
    priority_col = find_column(frame, ("priority", "candidate_priority"))

    missing = []
    if entry_col is None:
        missing.append("entry timestamp")
    if exit_col is None:
        missing.append("exit timestamp")
    if pnl_col is None and not (
        entry_price_col and exit_price_col and (direction_num_col or direction_col)
    ):
        missing.append("PnL or entry/exit/direction")
    if missing:
        raise ValueError(
            "EXISTING_PORTFOLIO_SCHEMA_UNSUPPORTED: "
            + ", ".join(missing)
            + f"; columns={list(frame.columns)}"
        )

    work = pd.DataFrame(index=frame.index)
    work["entry_dt"] = pd.to_datetime(frame[entry_col], errors="coerce")
    work["exit_dt"] = pd.to_datetime(frame[exit_col], errors="coerce")

    if pnl_col is not None:
        work["pnl_usd"] = pd.to_numeric(frame[pnl_col], errors="coerce")
        pnl_derivation = pnl_col
    else:
        entry_price = pd.to_numeric(frame[entry_price_col], errors="coerce")
        exit_price = pd.to_numeric(frame[exit_price_col], errors="coerce")
        if direction_num_col is not None:
            direction_num = pd.to_numeric(frame[direction_num_col], errors="coerce")
        else:
            direction_text = frame[direction_col].astype(str).str.upper()
            direction_num = direction_text.map(
                {"LONG": 1.0, "BUY": 1.0, "SHORT": -1.0, "SELL": -1.0}
            )
        work["pnl_usd"] = direction_num * (exit_price - entry_price)
        pnl_derivation = "direction*(exit_price-entry_price)"

    if r_col is not None:
        work["pnl_r"] = pd.to_numeric(frame[r_col], errors="coerce")
    else:
        work["pnl_r"] = np.nan

    if source_col is not None:
        work["source"] = frame[source_col].map(normalize_source)
    else:
        work["source"] = "EXISTING"

    if candidate_id_col is not None:
        candidate_ids = frame[candidate_id_col].astype(str)
    else:
        candidate_ids = pd.Series("", index=frame.index, dtype=str)
    generated = (
        "EXISTING|"
        + work["source"].astype(str)
        + "|"
        + work["entry_dt"].astype(str)
        + "|"
        + work.index.astype(str)
    )
    work["candidate_id"] = candidate_ids.where(
        candidate_ids.str.len().gt(0) & candidate_ids.ne("nan"), generated
    )

    if priority_col is not None:
        supplied_priority = pd.to_numeric(frame[priority_col], errors="coerce")
        work["contract_priority"] = supplied_priority.where(
            supplied_priority.notna(), work.source.map(source_priority)
        )
    else:
        work["contract_priority"] = work.source.map(source_priority)

    work["origin"] = "EXISTING"
    before_drop = len(work)
    work = work.dropna(subset=["entry_dt", "exit_dt", "pnl_usd"]).copy()
    work = work[work.exit_dt.ge(work.entry_dt)].copy()
    work = work.sort_values(
        ["entry_dt", "exit_dt", "candidate_id"], kind="mergesort"
    ).drop_duplicates("candidate_id", keep="first")
    work = work.reset_index(drop=True)

    metadata = {
        "path": str(path),
        "original_rows": int(original_rows),
        "portfolio_filter": portfolio_filter,
        "filtered_rows_before_normalization": int(before_drop),
        "normalized_rows": int(len(work)),
        "dropped_rows": int(before_drop - len(work)),
        "entry_column": entry_col,
        "exit_column": exit_col,
        "pnl_derivation": pnl_derivation,
        "r_column": r_col,
        "source_column": source_col,
        "candidate_id_column": candidate_id_col,
        "priority_column": priority_col,
        "columns": list(frame.columns),
    }
    return work, metadata


def normalize_stage309(frame: pd.DataFrame) -> pd.DataFrame:
    required = {
        "candidate_id",
        "entry_dt",
        "exit_dt",
        "spread_adjusted_pnl",
        "spread_adjusted_r",
    }
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"STAGE309_TRADES_SCHEMA_MISSING: {missing}")
    work = pd.DataFrame()
    work["candidate_id"] = frame.candidate_id.astype(str)
    work["source"] = "STAGE307_TOP"
    work["origin"] = "STAGE309"
    work["entry_dt"] = pd.to_datetime(frame.entry_dt, errors="raise")
    work["exit_dt"] = pd.to_datetime(frame.exit_dt, errors="raise")
    work["pnl_usd"] = pd.to_numeric(frame.spread_adjusted_pnl, errors="raise")
    work["pnl_r"] = pd.to_numeric(frame.spread_adjusted_r, errors="raise")
    work["contract_priority"] = STAGE309_PRIORITY
    if "ml_score" in frame.columns:
        work["ml_score"] = pd.to_numeric(frame.ml_score, errors="coerce")
    else:
        work["ml_score"] = np.nan
    return work.sort_values(
        ["entry_dt", "exit_dt", "candidate_id"], kind="mergesort"
    ).reset_index(drop=True)


def profit_factor(values: pd.Series) -> float | None:
    positive = float(values[values > 0].sum())
    negative = float(-values[values < 0].sum())
    if negative == 0.0:
        return None if positive > 0 else 0.0
    return positive / negative


def max_drawdown(values: pd.Series) -> float:
    if values.empty:
        return 0.0
    equity = values.cumsum()
    peak = equity.cummax().clip(lower=0.0)
    return float((peak - equity).max())


def summarize(frame: pd.DataFrame) -> dict[str, Any]:
    if frame.empty:
        return {
            "trades": 0,
            "wins": 0,
            "losses": 0,
            "flats": 0,
            "win_rate": 0.0,
            "total_usd": 0.0,
            "avg_usd": 0.0,
            "profit_factor": 0.0,
            "max_drawdown_usd": 0.0,
            "first_entry_dt": None,
            "last_exit_dt": None,
            "source_counts": {},
        }
    ordered = frame.sort_values(["exit_dt", "entry_dt"], kind="mergesort")
    values = ordered.pnl_usd.astype(float)
    wins = int((values > 0).sum())
    losses = int((values < 0).sum())
    flats = int((values == 0).sum())
    return {
        "trades": int(len(ordered)),
        "wins": wins,
        "losses": losses,
        "flats": flats,
        "win_rate": float(wins / len(ordered)),
        "total_usd": float(values.sum()),
        "avg_usd": float(values.mean()),
        "profit_factor": profit_factor(values),
        "max_drawdown_usd": max_drawdown(values),
        "first_entry_dt": str(ordered.entry_dt.min()),
        "last_exit_dt": str(ordered.exit_dt.max()),
        "source_counts": {
            str(key): int(value)
            for key, value in ordered.source.value_counts().sort_index().items()
        },
    }


def yearly_summary(frame: pd.DataFrame) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for year in (2024, 2025, 2026):
        result[str(year)] = summarize(frame[frame.entry_dt.dt.year.eq(year)])
    return result


def replay(
    baseline: pd.DataFrame,
    addition: pd.DataFrame,
    policy: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    existing = baseline.copy()
    new = addition.copy()
    if policy == "EXISTING_FIRST":
        existing["replay_priority"] = 0
        new["replay_priority"] = 50
    elif policy == "CONTRACT_PRIORITY_STAGE309_15":
        existing["replay_priority"] = existing.contract_priority.astype(int)
        new["replay_priority"] = STAGE309_PRIORITY
    elif policy == "BASE_FIRST_STAGE309_BEFORE_ADDITIONS":
        existing["replay_priority"] = np.where(
            existing.source.eq("BASE"), 0, existing.contract_priority.clip(lower=20)
        )
        new["replay_priority"] = 10
    else:
        raise ValueError(policy)

    combined = pd.concat([existing, new], ignore_index=True, sort=False)
    combined = combined.sort_values(
        ["entry_dt", "replay_priority", "candidate_id"], kind="mergesort"
    ).reset_index(drop=True)

    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    active_until = pd.Timestamp.min
    blocker_id: str | None = None
    blocker_source: str | None = None
    for row in combined.to_dict("records"):
        entry_dt = pd.Timestamp(row["entry_dt"])
        exit_dt = pd.Timestamp(row["exit_dt"])
        if entry_dt < active_until:
            row["rejection_reason"] = "ACTIVE_POSITION_OVERLAP"
            row["blocked_by_candidate_id"] = blocker_id
            row["blocked_by_source"] = blocker_source
            rejected.append(row)
            continue
        row["rejection_reason"] = None
        row["blocked_by_candidate_id"] = None
        row["blocked_by_source"] = None
        accepted.append(row)
        active_until = exit_dt
        blocker_id = str(row["candidate_id"])
        blocker_source = str(row["source"])

    return pd.DataFrame(accepted), pd.DataFrame(rejected)


def overlap_diagnostics(
    baseline: pd.DataFrame,
    addition: pd.DataFrame,
) -> dict[str, Any]:
    exact_entries = set(baseline.entry_dt) & set(addition.entry_dt)
    interval_overlap_count = 0
    addition_with_overlap: set[str] = set()
    baseline_sorted = baseline.sort_values("entry_dt")
    for row in addition.itertuples():
        mask = baseline_sorted.entry_dt.lt(row.exit_dt) & baseline_sorted.exit_dt.gt(
            row.entry_dt
        )
        count = int(mask.sum())
        interval_overlap_count += count
        if count:
            addition_with_overlap.add(str(row.candidate_id))
    return {
        "exact_entry_timestamp_count": int(len(exact_entries)),
        "overlapping_interval_pairs": int(interval_overlap_count),
        "stage309_trades_with_any_existing_overlap": int(len(addition_with_overlap)),
        "stage309_trades_without_existing_overlap": int(
            len(addition) - len(addition_with_overlap)
        ),
    }


def policy_result(
    baseline: pd.DataFrame,
    addition: pd.DataFrame,
    policy: str,
) -> tuple[dict[str, Any], pd.DataFrame, pd.DataFrame]:
    accepted, rejected = replay(baseline, addition, policy)
    accepted_new = accepted[accepted.origin.eq("STAGE309")].copy()
    accepted_existing = accepted[accepted.origin.eq("EXISTING")].copy()
    rejected_new = (
        rejected[rejected.origin.eq("STAGE309")].copy()
        if not rejected.empty
        else rejected.copy()
    )
    rejected_existing = (
        rejected[rejected.origin.eq("EXISTING")].copy()
        if not rejected.empty
        else rejected.copy()
    )
    baseline_summary = summarize(baseline)
    combined_summary = summarize(accepted)
    incremental_summary = summarize(accepted_new)
    pf_base = baseline_summary["profit_factor"]
    pf_combined = combined_summary["profit_factor"]
    pf_floor = max(1.20, 0.95 * float(pf_base or 0.0))
    yearly_new = yearly_summary(accepted_new)
    worst_year_new = min(
        yearly_new[year]["total_usd"] for year in ("2025", "2026")
    )
    incremental_pf = incremental_summary["profit_factor"]
    incremental_pf_value = (
        float("inf")
        if incremental_pf is None and incremental_summary["total_usd"] > 0
        else float(incremental_pf or 0.0)
    )
    passed = bool(
        incremental_summary["trades"] >= 12
        and incremental_summary["win_rate"] >= 0.52
        and incremental_pf_value >= 1.30
        and incremental_summary["total_usd"] > 0.0
        and float(pf_combined or 0.0) >= pf_floor
        and combined_summary["max_drawdown_usd"]
        <= baseline_summary["max_drawdown_usd"]
        + max(15.0, 0.15 * baseline_summary["max_drawdown_usd"])
        and worst_year_new > -10.0
    )
    result = {
        "policy": policy,
        "integrated_pass": passed,
        "baseline": baseline_summary,
        "combined": combined_summary,
        "incremental_stage309": incremental_summary,
        "yearly_combined": yearly_summary(accepted),
        "yearly_incremental_stage309": yearly_new,
        "accepted_existing": int(len(accepted_existing)),
        "accepted_stage309": int(len(accepted_new)),
        "rejected_existing": int(len(rejected_existing)),
        "rejected_stage309": int(len(rejected_new)),
        "profit_factor_floor": float(pf_floor),
        "drawdown_allowance_usd": float(
            max(15.0, 0.15 * baseline_summary["max_drawdown_usd"])
        ),
        "worst_year_incremental_usd": float(worst_year_new),
    }
    accepted["policy"] = policy
    if not rejected.empty:
        rejected["policy"] = policy
    return result, accepted, rejected


def common_coverage(
    baseline: pd.DataFrame,
    addition: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.Timestamp]:
    baseline_max = pd.Timestamp(baseline.exit_dt.max())
    addition_max = pd.Timestamp(addition.exit_dt.max())
    common_asof = min(baseline_max, addition_max)
    return (
        baseline[baseline.exit_dt.le(common_asof)].copy(),
        addition[addition.exit_dt.le(common_asof)].copy(),
        common_asof,
    )


def json_safe_frame(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    for column in ("entry_dt", "exit_dt"):
        if column in result.columns:
            result[column] = result[column].astype(str)
    return result


def main() -> int:
    args = parse_args()
    candle_dir = Path(args.candle_dir).expanduser().resolve()
    registry_path = (
        Path(args.stage309_registry).expanduser().resolve()
        if args.stage309_registry
        else candle_dir / "stage309_stage307_top_candidate_registry.json"
    )
    stage309_trades_path = (
        Path(args.stage309_trades).expanduser().resolve()
        if args.stage309_trades
        else candle_dir / "stage309_stage307_top_candidate_trades.csv"
    )
    output = (
        Path(args.output).expanduser().resolve()
        if args.output
        else candle_dir / "stage310_stage307_integrated_portfolio_replay.json"
    )
    accepted_csv = (
        Path(args.accepted_csv).expanduser().resolve()
        if args.accepted_csv
        else candle_dir / "stage310_stage307_integrated_accepted.csv"
    )
    rejected_csv = (
        Path(args.rejected_csv).expanduser().resolve()
        if args.rejected_csv
        else candle_dir / "stage310_stage307_integrated_rejected.csv"
    )

    discovery_diagnostics: list[str] = []
    if args.existing_portfolio_csv:
        existing_path = Path(args.existing_portfolio_csv).expanduser().resolve()
    else:
        existing_path, discovery_diagnostics = discover_existing_portfolio(candle_dir)
        if existing_path is None:
            report = {
                "status": "GOLD_V3_310_BLOCKED_EXISTING_PORTFOLIO_NOT_FOUND",
                "mode": "AUDIT_ONLY_INTEGRATED_REPLAY",
                "searched_root": str(candle_dir.parent),
                "expected_names": list(EXISTING_PORTFOLIO_NAMES),
                "discovery_matches": discovery_diagnostics,
                "promotion": {"performed": False},
            }
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(
                json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 2

    if not registry_path.exists() or not stage309_trades_path.exists():
        raise FileNotFoundError(
            f"STAGE309_OUTPUT_MISSING: registry={registry_path.exists()} trades={stage309_trades_path.exists()}"
        )
    if not existing_path.exists():
        raise FileNotFoundError(existing_path)

    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    if registry.get("status") != "GOLD_V3_309_STAGE307_TOP_RESEARCH_CANDIDATE_REGISTERED":
        raise ValueError(f"STAGE309_NOT_REGISTERED: {registry.get('status')}")
    if not bool(registry.get("parity", {}).get("passed")):
        raise ValueError("STAGE309_PARITY_NOT_PASSED")
    expected_trade_sha = str(registry["outputs"]["trades_sha256"])
    actual_trade_sha = sha256_file(stage309_trades_path)
    if actual_trade_sha != expected_trade_sha:
        raise ValueError(
            f"STAGE309_TRADES_SHA_MISMATCH: expected={expected_trade_sha} actual={actual_trade_sha}"
        )

    existing_raw = read_csv(existing_path)
    existing, existing_meta = normalize_existing(existing_raw, existing_path)
    stage309_raw = read_csv(stage309_trades_path)
    stage309 = normalize_stage309(stage309_raw)
    if len(stage309) != 92:
        raise ValueError(f"STAGE309_TRADE_COUNT_MISMATCH: {len(stage309)}")

    baseline_self_accepted, baseline_self_rejected = replay(
        existing,
        existing.iloc[0:0].copy(),
        "CONTRACT_PRIORITY_STAGE309_15",
    )
    baseline_already_non_overlapping = len(baseline_self_rejected) == 0
    baseline = baseline_self_accepted.copy()

    common_baseline, common_stage309, common_asof = common_coverage(
        baseline, stage309
    )
    policies = (
        "EXISTING_FIRST",
        "CONTRACT_PRIORITY_STAGE309_15",
        "BASE_FIRST_STAGE309_BEFORE_ADDITIONS",
    )
    policy_results: list[dict[str, Any]] = []
    accepted_outputs: list[pd.DataFrame] = []
    rejected_outputs: list[pd.DataFrame] = []
    for policy in policies:
        result, accepted, rejected = policy_result(
            common_baseline,
            common_stage309,
            policy,
        )
        policy_results.append(result)
        accepted_outputs.append(accepted)
        if not rejected.empty:
            rejected_outputs.append(rejected)

    contract_result = next(
        row
        for row in policy_results
        if row["policy"] == "CONTRACT_PRIORITY_STAGE309_15"
    )
    integrated_pass = bool(contract_result["integrated_pass"])

    accepted_all = pd.concat(accepted_outputs, ignore_index=True, sort=False)
    rejected_all = (
        pd.concat(rejected_outputs, ignore_index=True, sort=False)
        if rejected_outputs
        else pd.DataFrame()
    )
    accepted_csv.parent.mkdir(parents=True, exist_ok=True)
    json_safe_frame(accepted_all).to_csv(
        accepted_csv, index=False, encoding="utf-8-sig"
    )
    rejected_csv.parent.mkdir(parents=True, exist_ok=True)
    json_safe_frame(rejected_all).to_csv(
        rejected_csv, index=False, encoding="utf-8-sig"
    )

    report = {
        "status": (
            "GOLD_V3_310_STAGE307_INTEGRATED_REPLAY_PASS"
            if integrated_pass
            else "GOLD_V3_310_STAGE307_INTEGRATED_REPLAY_NO_PASS"
        ),
        "mode": "AUDIT_ONLY_INTEGRATED_ONE_POSITION_REPLAY",
        "decision": (
            "APPROVE_STAGE307_TOP_FOR_SHADOW_WIRING_DESIGN"
            if integrated_pass
            else "KEEP_STAGE307_TOP_RESEARCH_ONLY"
        ),
        "candidate_id": STAGE309_ID,
        "inputs": {
            "existing_portfolio_csv": str(existing_path),
            "existing_portfolio_sha256": sha256_file(existing_path),
            "stage309_registry": str(registry_path),
            "stage309_registry_sha256": sha256_file(registry_path),
            "stage309_trades": str(stage309_trades_path),
            "stage309_trades_sha256": actual_trade_sha,
        },
        "existing_portfolio_normalization": existing_meta,
        "baseline_self_replay": {
            "raw_normalized_trades": int(len(existing)),
            "accepted_trades": int(len(baseline)),
            "rejected_overlap_trades": int(len(baseline_self_rejected)),
            "already_non_overlapping": baseline_already_non_overlapping,
        },
        "coverage": {
            "baseline_first_entry": str(baseline.entry_dt.min()),
            "baseline_last_exit": str(baseline.exit_dt.max()),
            "stage309_first_entry": str(stage309.entry_dt.min()),
            "stage309_last_exit": str(stage309.exit_dt.max()),
            "common_asof_inclusive": str(common_asof),
            "common_baseline_trades": int(len(common_baseline)),
            "common_stage309_trades": int(len(common_stage309)),
            "primary_decision_uses_common_coverage": True,
        },
        "overlap": overlap_diagnostics(common_baseline, common_stage309),
        "standalone": {
            "baseline_common": summarize(common_baseline),
            "stage309_common": summarize(common_stage309),
            "baseline_full": summarize(baseline),
            "stage309_full": summarize(stage309),
        },
        "policies": policy_results,
        "primary_policy": "CONTRACT_PRIORITY_STAGE309_15",
        "primary_gate": {
            "minimum_incremental_stage309_trades": 12,
            "minimum_incremental_win_rate": 0.52,
            "minimum_incremental_profit_factor": 1.30,
            "minimum_incremental_total_usd": 0.0,
            "combined_profit_factor_floor": "max(1.20, baseline PF * 0.95)",
            "combined_dd_allowance": "baseline DD + max(15 USD, baseline DD * 0.15)",
            "worst_2025_2026_incremental_usd": -10.0,
        },
        "outputs": {
            "accepted_csv": str(accepted_csv),
            "accepted_sha256": sha256_file(accepted_csv),
            "rejected_csv": str(rejected_csv),
            "rejected_sha256": sha256_file(rejected_csv),
        },
        "next_stage": {
            "stage": 311,
            "task_if_pass": "design frozen Stage307 live scorer and audit-only shadow candidate output without changing Stage292 production admission",
            "task_if_no_pass": "retain Stage307 candidate offline and inspect overlap blockers; do not weaken the gate automatically",
        },
        "promotion": {
            "performed": False,
            "production_stage280": "UNCHANGED_BLOCKED",
            "stage281": "UNCHANGED",
            "stage286": "UNCHANGED",
            "stage292_candidate_pool_changed": False,
            "shadow_enabled": False,
        },
        "safety_flags": {
            "final_signal_changed": False,
            "mt5_order_enabled": False,
            "discord_enabled": False,
            "partial_close_enabled": False,
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
