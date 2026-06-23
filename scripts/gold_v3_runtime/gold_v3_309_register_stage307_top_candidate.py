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

import gold_v3_304_stage280_approximate_walkforward_backtest as metrics_base
import gold_v3_306_stage280_candidate_pool_expansion as stage306
import gold_v3_307_stage280_multimodel_candidate_expansion as stage307
from gold_v3_298_stage280_model_variant_diagnostic import prepare
from gold_v3_299_stage280_wick_weight_diagnostic import target_series

CONTRACT_PATH = (
    Path(__file__).resolve().parent
    / "models"
    / "gold_v3_309"
    / "stage307_top_research_candidate_contract.json"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candle-dir", required=True)
    parser.add_argument("--output", default="")
    parser.add_argument("--trades-csv", default="")
    parser.add_argument("--point-size", type=float, default=0.01)
    return parser.parse_args()


def load_contract() -> dict[str, Any]:
    if not CONTRACT_PATH.exists():
        raise FileNotFoundError(CONTRACT_PATH)
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_frozen_market(
    candle_dir: Path,
    *,
    latest_m1_time: pd.Timestamp,
    latest_m5_time: pd.Timestamp,
) -> dict[str, Any]:
    market = stage306.build_market(candle_dir)
    m5 = market["m5"].loc[
        market["m5"].time.le(latest_m5_time)
    ].copy().reset_index(drop=True)
    m1 = market["m1"].loc[
        market["m1"].time.le(latest_m1_time)
    ].copy().reset_index(drop=True)
    if m5.empty or m1.empty:
        raise ValueError("FROZEN_MARKET_EMPTY")
    if pd.Timestamp(m5.time.max()) != latest_m5_time:
        raise ValueError(
            f"FROZEN_M5_CUTOFF_MISSING: expected={latest_m5_time} actual={m5.time.max()}"
        )
    if pd.Timestamp(m1.time.max()) != latest_m1_time:
        raise ValueError(
            f"FROZEN_M1_CUTOFF_MISSING: expected={latest_m1_time} actual={m1.time.max()}"
        )

    m5_range = (m5.high - m5.low).to_numpy(float)
    m5_body = np.divide(
        (m5.close - m5.open).to_numpy(float),
        m5_range,
        out=np.zeros(len(m5), dtype=float),
        where=m5_range > 0,
    )
    frozen = {
        "m5": m5,
        "m5_time": m5.time.to_numpy("datetime64[ns]"),
        "m5_open": m5.open.to_numpy(float),
        "m5_high": m5.high.to_numpy(float),
        "m5_low": m5.low.to_numpy(float),
        "m5_close": m5.close.to_numpy(float),
        "m5_spread": m5.spread.to_numpy(float),
        "m5_body": m5_body,
        "m5_ema20": m5.close.ewm(span=20, adjust=False).mean().to_numpy(float),
        "m1": m1,
        "m1_time": m1.time.to_numpy("datetime64[ns]"),
        "m1_high": m1.high.to_numpy(float),
        "m1_low": m1.low.to_numpy(float),
        "m1_close": m1.close.to_numpy(float),
    }
    return frozen


def precompute_frozen_outcomes(
    ctx: pd.DataFrame,
    candle_dir: Path,
    point_size: float,
    source_snapshot: dict[str, Any],
) -> tuple[dict[int, dict[str, Any]], dict[str, Any]]:
    latest_m1_time = pd.Timestamp(source_snapshot["latest_m1_time_inclusive"])
    latest_m5_time = pd.Timestamp(source_snapshot["latest_m5_time_inclusive"])
    context_time_max = pd.Timestamp(source_snapshot["context_time_max_inclusive"])
    market = build_frozen_market(
        candle_dir,
        latest_m1_time=latest_m1_time,
        latest_m5_time=latest_m5_time,
    )
    rows = ctx[
        ctx.h4_trend.eq(-1)
        & ctx.time.ge("2025-01-01")
        & ctx.time.lt("2027-01-01")
        & ctx.time.le(context_time_max)
    ]
    outcomes: dict[int, dict[str, Any]] = {}
    for context_index, row in rows.iterrows():
        result = stage306.simulate(
            pd.Timestamp(row.time),
            float(row.atr_prev),
            stage307.ANCHOR_FAMILY,
            market,
            point_size,
        )
        if result is not None:
            outcomes[int(context_index)] = result
    metadata = {
        "frozen_source_snapshot": True,
        "h4_down_test_rows": int(len(rows)),
        "triggered_and_resolved_rows": int(len(outcomes)),
        "latest_m1_time": str(market["m1"].time.max()),
        "latest_m5_time": str(market["m5"].time.max()),
        "context_time_max_inclusive": str(context_time_max),
        "point_size": float(point_size),
    }
    return outcomes, metadata


def reconstruct_candidate_trades(
    models: dict[str, dict[int, dict[str, Any]]],
    outcomes: dict[int, dict[str, Any]],
    selected_models: tuple[str, ...],
    rule: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    combined: list[dict[str, Any]] = []
    yearly: dict[str, Any] = {}

    for year in stage307.YEARS:
        raw: list[dict[str, Any]] = []
        selected_triggered_raw = 0
        for context_index, template in outcomes.items():
            if pd.Timestamp(template["decision_dt"]).year != year:
                continue
            values = {
                model_name: models[model_name][year]["percentile_by_index"].get(
                    context_index, 0.0
                )
                for model_name in selected_models
            }
            passed, ensemble_score = stage307.rule_result(rule, values)
            if not passed:
                continue
            selected_triggered_raw += 1
            trade = dict(template)
            trade["candidate_id"] = "GOLD_V3_STAGE307_TOP_REV_LONG_ANY_P90"
            trade["ml_score"] = float(ensemble_score)
            trade["ensemble_score"] = float(ensemble_score)
            trade["source_model"] = max(values, key=values.get)
            trade["model_percentiles"] = values
            trade["context_index"] = int(context_index)
            trade["year"] = int(year)
            raw.append(trade)

        portfolio = stage307.one_position(raw)
        yearly[str(year)] = {
            "selected_triggered_raw": int(selected_triggered_raw),
            "standalone_non_overlap": metrics_base.summarize_trades(portfolio),
        }
        combined.extend(portfolio)

    combined = sorted(
        combined,
        key=lambda row: (
            pd.Timestamp(row["entry_dt"]),
            pd.Timestamp(row["decision_dt"]),
        ),
    )
    return combined, yearly


def compare_value(
    path: str,
    actual: Any,
    expected: Any,
    tolerance: float,
) -> dict[str, Any]:
    if isinstance(expected, bool):
        passed = actual is expected
        difference = None
    elif isinstance(expected, int) and not isinstance(expected, bool):
        passed = int(actual) == expected
        difference = int(actual) - expected
    elif isinstance(expected, float):
        actual_value = float(actual)
        passed = math.isclose(
            actual_value,
            expected,
            rel_tol=0.0,
            abs_tol=tolerance,
        )
        difference = actual_value - expected
    else:
        passed = actual == expected
        difference = None
    return {
        "field": path,
        "expected": expected,
        "actual": actual,
        "difference": difference,
        "passed": bool(passed),
    }


def validate_parity(
    contract: dict[str, Any],
    aggregate: dict[str, Any],
    yearly: dict[str, Any],
) -> dict[str, Any]:
    tolerance = float(contract["parity_tolerance"])
    checks: list[dict[str, Any]] = []

    for key, expected in contract["expected_aggregate"].items():
        checks.append(
            compare_value(
                f"aggregate.{key}",
                aggregate.get(key),
                expected,
                tolerance,
            )
        )

    for year, expected_fields in contract["expected_yearly"].items():
        actual_metrics = yearly[year]["standalone_non_overlap"]
        for key, expected in expected_fields.items():
            checks.append(
                compare_value(
                    f"yearly.{year}.{key}",
                    actual_metrics.get(key),
                    expected,
                    tolerance,
                )
            )

    failed = [check for check in checks if not check["passed"]]
    return {
        "tolerance": tolerance,
        "passed": not failed,
        "check_count": len(checks),
        "failed_count": len(failed),
        "failed_checks": failed,
        "checks": checks,
    }


def csv_safe_rows(trades: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for trade in trades:
        row = dict(trade)
        row["model_percentiles"] = json.dumps(
            row.get("model_percentiles", {}),
            ensure_ascii=False,
            sort_keys=True,
        )
        for key in ("decision_dt", "trigger_dt", "entry_dt", "exit_dt"):
            if key in row:
                row[key] = str(pd.Timestamp(row[key]))
        rows.append(row)
    return rows


def main() -> int:
    args = parse_args()
    candle_dir = Path(args.candle_dir).expanduser().resolve()
    output = (
        Path(args.output).expanduser().resolve()
        if args.output
        else candle_dir / "stage309_stage307_top_candidate_registry.json"
    )
    trades_csv = (
        Path(args.trades_csv).expanduser().resolve()
        if args.trades_csv
        else output.with_name("stage309_stage307_top_candidate_trades.csv")
    )

    contract = load_contract()
    selected_models = tuple(contract["models"])
    rule = str(contract["rule"])
    expected_key = "+".join(selected_models) + "|" + rule
    if expected_key != contract["source_ensemble_key"]:
        raise ValueError(
            "CONTRACT_ENSEMBLE_KEY_MISMATCH: "
            f"derived={expected_key} contract={contract['source_ensemble_key']}"
        )
    expected_point_size = float(
        contract["execution_contract"]["spread_point_size"]
    )
    if not math.isclose(
        float(args.point_size),
        expected_point_size,
        rel_tol=0.0,
        abs_tol=1e-15,
    ):
        raise ValueError(
            f"POINT_SIZE_MISMATCH: expected={expected_point_size} actual={args.point_size}"
        )

    context_time_max = pd.Timestamp(
        contract["source_snapshot"]["context_time_max_inclusive"]
    )
    ctx, features = prepare(candle_dir)
    eligible = ctx[
        ctx.h4_trend.ne(0) & ctx.time.le(context_time_max)
    ].copy()
    target = target_series(eligible)
    models, model_contracts = stage307.fit_models(eligible, features, target)
    outcomes, outcome_meta = precompute_frozen_outcomes(
        eligible,
        candle_dir,
        float(args.point_size),
        contract["source_snapshot"],
    )

    candidate_trades, yearly = reconstruct_candidate_trades(
        models,
        outcomes,
        selected_models,
        rule,
    )
    aggregate = metrics_base.summarize_trades(candidate_trades)
    parity = validate_parity(contract, aggregate, yearly)

    output.parent.mkdir(parents=True, exist_ok=True)
    trades_csv.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(csv_safe_rows(candidate_trades)).to_csv(
        trades_csv,
        index=False,
        encoding="utf-8-sig",
    )

    selected_model_contracts = [
        item for item in model_contracts if item["name"] in selected_models
    ]
    registered = bool(parity["passed"])
    report = {
        "status": (
            "GOLD_V3_309_STAGE307_TOP_RESEARCH_CANDIDATE_REGISTERED"
            if registered
            else "GOLD_V3_309_STAGE307_TOP_RESEARCH_CANDIDATE_BLOCKED_PARITY"
        ),
        "mode": "AUDIT_ONLY_RESEARCH_CANDIDATE_REGISTRY",
        "decision": (
            "REGISTER_STAGE307_TOP_FOR_INTEGRATED_REPLAY"
            if registered
            else "BLOCK_REGISTRATION_UNTIL_EXACT_PARITY_RECOVERED"
        ),
        "candidate_pool": (
            [
                {
                    "candidate_id": contract["candidate_id"],
                    "candidate_state": "REGISTERED_FOR_INTEGRATED_REPLAY",
                    "ensemble_key": contract["source_ensemble_key"],
                    "models": list(selected_models),
                    "rule": rule,
                    "execution_contract": contract["execution_contract"],
                    "source_snapshot": contract["source_snapshot"],
                    "aggregate": aggregate,
                    "yearly": yearly,
                    "source_robust_score": contract["source_robust_score"],
                }
            ]
            if registered
            else []
        ),
        "parity": parity,
        "source_contract": contract,
        "selected_model_contracts": selected_model_contracts,
        "outcome_precompute": outcome_meta,
        "outputs": {
            "registry_json": str(output),
            "trades_csv": str(trades_csv),
            "contract_path": str(CONTRACT_PATH),
            "contract_sha256": sha256_file(CONTRACT_PATH),
            "trades_sha256": sha256_file(trades_csv),
        },
        "stage308_review": {
            "uploaded_result_decision": "NO_MOCHIPOYO_CANDIDATE_PASSED",
            "uploaded_pass_count": 0,
            "registered_from_stage308": False,
            "reason": "Retain Stage308 for rule refinement; none of its 96 families or 40 pools passed the declared gates.",
        },
        "next_stage": {
            "stage": 310,
            "task": "integrated one-position overlap, priority and drawdown replay against existing Stage292 research candidates",
            "automatic_production_promotion": False,
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
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    return 0 if registered else 3


if __name__ == "__main__":
    raise SystemExit(main())
