from __future__ import annotations

import argparse
import csv
import json
import math
import sqlite3
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from alert_trigger_signature_audit import (
    DecisionSample,
    TriggerSignatureContractError,
    build_decision_samples,
)

CONTRACT_VERSION = "MOCHIPOYO_M7B_FROZEN_TRIGGER_KERNEL_VALIDATION_V1"


class FrozenKernelContractError(RuntimeError):
    pass


def iso_z(value: datetime) -> str:
    return value.strftime("%Y-%m-%dT%H:%M:%SZ")


def _finite_float(value: Any, *, label: str) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise FrozenKernelContractError(f"non-finite {label}")
    return result


def _load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise FrozenKernelContractError(f"cannot load JSON: {path}") from exc
    if not isinstance(payload, dict):
        raise FrozenKernelContractError(f"JSON root must be an object: {path}")
    return payload


def load_and_validate_manifest(path: Path) -> dict[str, Any]:
    manifest = _load_json(path)
    if manifest.get("contract_version") != "MOCHIPOYO_M7B_FROZEN_TRIGGER_KERNEL_V1":
        raise FrozenKernelContractError("unexpected frozen-kernel manifest version")
    if manifest.get("audit_only") is not True:
        raise FrozenKernelContractError("manifest must remain audit-only")
    for field in (
        "entry_gate_enabled",
        "discord_send",
        "mt5_order",
        "live_ready",
        "final_signal",
        "historical_scan_approved",
        "cross_timeframe_scan_approved",
    ):
        if manifest.get(field) is not False:
            raise FrozenKernelContractError(f"manifest safety field must be false: {field}")

    kernels = manifest.get("kernels")
    if not isinstance(kernels, list) or not kernels:
        raise FrozenKernelContractError("manifest kernels must be a non-empty list")
    ids: set[str] = set()
    for kernel in kernels:
        if not isinstance(kernel, dict):
            raise FrozenKernelContractError("each kernel must be an object")
        kernel_id = str(kernel.get("kernel_id", ""))
        if not kernel_id or kernel_id in ids:
            raise FrozenKernelContractError(f"invalid or duplicate kernel_id: {kernel_id}")
        ids.add(kernel_id)
        if kernel.get("status") != "FROZEN_AUDIT_ONLY":
            raise FrozenKernelContractError(f"kernel is not frozen audit-only: {kernel_id}")
        if kernel.get("eligible_state") not in ("IDLE", "ACTIVE_LONG", "ACTIVE_SHORT"):
            raise FrozenKernelContractError(f"invalid eligible_state: {kernel_id}")
        if kernel.get("target_transition") not in (
            "PRIMARY_LONG",
            "PRIMARY_SHORT",
            "LONG_EXIT",
            "SHORT_EXIT",
        ):
            raise FrozenKernelContractError(f"invalid target_transition: {kernel_id}")
        conditions = kernel.get("conditions")
        if not isinstance(conditions, list) or not conditions:
            raise FrozenKernelContractError(f"kernel conditions missing: {kernel_id}")
        for condition in conditions:
            if condition.get("operator") not in ("==", ">=", "<="):
                raise FrozenKernelContractError(f"unsupported operator in {kernel_id}")
    required = {"CORE-L0", "KERNEL-L1", "CORE-S0", "KERNEL-S1", "EXIT-L0", "EXIT-S0"}
    if ids != required:
        raise FrozenKernelContractError(
            f"manifest kernel IDs must be exactly {sorted(required)}; got {sorted(ids)}"
        )
    return manifest


def _matches_condition(features: dict[str, Any], condition: dict[str, Any]) -> bool:
    feature = str(condition["feature"])
    value = features.get(feature)
    if value is None:
        return False
    operator = str(condition["operator"])
    target = condition["value"]
    if operator == "==":
        return value == target
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    numeric = _finite_float(value, label=feature)
    threshold = _finite_float(target, label=f"{feature} threshold")
    if operator == ">=":
        return numeric >= threshold
    if operator == "<=":
        return numeric <= threshold
    raise FrozenKernelContractError(f"unsupported operator: {operator}")


def matches_kernel(sample: DecisionSample, kernel: dict[str, Any]) -> bool:
    if sample.state_before != kernel["eligible_state"]:
        return False
    return all(_matches_condition(sample.features, item) for item in kernel["conditions"])


def _ema_pair_gaps_bps(features: dict[str, Any]) -> tuple[float | None, float | None]:
    values = (
        features.get("close_minus_ema20_bps"),
        features.get("close_minus_ema30_bps"),
        features.get("close_minus_ema40_bps"),
    )
    if any(value is None for value in values):
        return None, None
    c20, c30, c40 = (_finite_float(value, label="EMA distance") for value in values)
    return c30 - c20, c40 - c30


def _derived_alignment(features: dict[str, Any]) -> str:
    gap20_30, gap30_40 = _ema_pair_gaps_bps(features)
    if gap20_30 is None or gap30_40 is None:
        return "UNKNOWN"
    if gap20_30 > 0.0 and gap30_40 > 0.0:
        return "BULLISH_STACK"
    if gap20_30 < 0.0 and gap30_40 < 0.0:
        return "BEARISH_STACK"
    return "MIXED"


def _sample_identity(sample: DecisionSample) -> dict[str, Any]:
    return {
        "raw_alert_id": sample.raw_alert_id,
        "ticker": sample.ticker,
        "decision_time_utc": iso_z(sample.decision_time_utc),
        "selected_server_open": sample.selected_server_open.strftime("%Y.%m.%d %H:%M:%S"),
        "state_before": sample.state_before,
        "actual_transition": sample.transition,
    }


def _diagnostic_features(sample: DecisionSample) -> dict[str, Any]:
    gap20_30, gap30_40 = _ema_pair_gaps_bps(sample.features)
    keys = (
        "rci9",
        "rci9_delta1",
        "rci9_turn_up",
        "rci9_turn_down",
        "ema_alignment",
        "ema20_slope_3_bars_bps",
        "ema30_slope_3_bars_bps",
        "ema40_slope_3_bars_bps",
        "ema_spread_atr",
        "current_open_minus_ema20_atr",
        "current_open_minus_ema40_atr",
        "macd_zero_proximity_atr",
        "bars_since_last_event",
        "previous_transition",
    )
    output = {key: sample.features.get(key) for key in keys}
    output["ema20_minus_ema30_bps"] = gap20_30
    output["ema30_minus_ema40_bps"] = gap30_40
    output["derived_strict_alignment"] = _derived_alignment(sample.features)
    return output


def evaluate_kernel(
    samples: list[DecisionSample], kernel: dict[str, Any]
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    eligible = [row for row in samples if row.state_before == kernel["eligible_state"]]
    target = str(kernel["target_transition"])
    positives = [row for row in eligible if row.transition == target]
    no_events = [row for row in eligible if row.transition == "NO_EVENT"]
    matched = [row for row in eligible if matches_kernel(row, kernel)]
    matched_positive = [row for row in matched if row.transition == target]
    no_event_false_positives = [row for row in matched if row.transition == "NO_EVENT"]
    event_collisions = [row for row in matched if row.transition not in (target, "NO_EVENT")]

    event_rows = []
    for row in positives:
        did_match = matches_kernel(row, kernel)
        event_rows.append(
            {
                "kernel_id": kernel["kernel_id"],
                "target_transition": target,
                **_sample_identity(row),
                "classification": "TRUE_POSITIVE" if did_match else "FALSE_NEGATIVE",
                "kernel_matched": did_match,
                **_diagnostic_features(row),
            }
        )
    false_positive_rows = [
        {
            "kernel_id": kernel["kernel_id"],
            "target_transition": target,
            **_sample_identity(row),
            "classification": "NO_EVENT_FALSE_POSITIVE",
            **_diagnostic_features(row),
        }
        for row in no_event_false_positives
    ]
    collision_rows = [
        {
            "kernel_id": kernel["kernel_id"],
            "target_transition": target,
            **_sample_identity(row),
            "classification": "OTHER_GENUINE_EVENT_COLLISION",
            **_diagnostic_features(row),
        }
        for row in event_collisions
    ]

    positive_total = len(positives)
    matched_positive_count = len(matched_positive)
    matched_total = len(matched)
    summary = {
        "kernel_id": kernel["kernel_id"],
        "target_transition": target,
        "eligible_state": kernel["eligible_state"],
        "scope": "ALL",
        "eligible_decision_count": len(eligible),
        "positive_total": positive_total,
        "matched_positive": matched_positive_count,
        "false_negative": positive_total - matched_positive_count,
        "no_event_eligible": len(no_events),
        "no_event_false_positive": len(no_event_false_positives),
        "other_event_collision": len(event_collisions),
        "matched_total": matched_total,
        "precision_including_event_collisions": (
            matched_positive_count / matched_total if matched_total else 0.0
        ),
        "event_recall": (
            matched_positive_count / positive_total if positive_total else 0.0
        ),
        "no_event_false_positive_rate": (
            len(no_event_false_positives) / len(no_events) if no_events else 0.0
        ),
        "conditions": kernel["conditions"],
    }
    return summary, event_rows, false_positive_rows, collision_rows


def _scope_summary(
    samples: list[DecisionSample], kernel: dict[str, Any], ticker: str
) -> dict[str, Any]:
    summary, _, _, _ = evaluate_kernel(
        [row for row in samples if row.ticker == ticker], kernel
    )
    summary["scope"] = ticker
    return summary


def build_cross_symbol_audit(
    samples: list[DecisionSample], kernels: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    tickers = sorted({row.ticker for row in samples})
    if tickers != ["BTCUSD", "XAUUSD"]:
        raise FrozenKernelContractError(f"unexpected ticker set for M7B: {tickers}")
    output = []
    for kernel in kernels:
        by_ticker = {ticker: _scope_summary(samples, kernel, ticker) for ticker in tickers}
        for source in tickers:
            target = next(ticker for ticker in tickers if ticker != source)
            source_summary = by_ticker[source]
            target_summary = by_ticker[target]
            output.append(
                {
                    "kernel_id": kernel["kernel_id"],
                    "target_transition": kernel["target_transition"],
                    "source_symbol": source,
                    "validation_symbol": target,
                    "formula_changed_between_symbols": False,
                    "threshold_refit_between_symbols": False,
                    "source_positive_total": source_summary["positive_total"],
                    "source_matched_positive": source_summary["matched_positive"],
                    "source_event_recall": source_summary["event_recall"],
                    "source_no_event_false_positive": source_summary["no_event_false_positive"],
                    "validation_positive_total": target_summary["positive_total"],
                    "validation_matched_positive": target_summary["matched_positive"],
                    "validation_event_recall": target_summary["event_recall"],
                    "validation_no_event_false_positive": target_summary["no_event_false_positive"],
                }
            )
    return output


def build_false_positive_clusters(
    false_positive_rows: list[dict[str, Any]], *, max_gap_minutes: int
) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in false_positive_rows:
        grouped[(str(row["kernel_id"]), str(row["ticker"]))].append(row)
    output = []
    for (kernel_id, ticker), rows in sorted(grouped.items()):
        ordered = sorted(rows, key=lambda item: str(item["decision_time_utc"]))
        clusters: list[list[dict[str, Any]]] = []
        for row in ordered:
            current_time = datetime.strptime(
                str(row["decision_time_utc"]), "%Y-%m-%dT%H:%M:%SZ"
            )
            if not clusters:
                clusters.append([row])
                continue
            previous_time = datetime.strptime(
                str(clusters[-1][-1]["decision_time_utc"]), "%Y-%m-%dT%H:%M:%SZ"
            )
            gap_minutes = (current_time - previous_time).total_seconds() / 60.0
            if gap_minutes <= max_gap_minutes:
                clusters[-1].append(row)
            else:
                clusters.append([row])
        for index, members in enumerate(clusters, start=1):
            start = datetime.strptime(
                str(members[0]["decision_time_utc"]), "%Y-%m-%dT%H:%M:%SZ"
            )
            end = datetime.strptime(
                str(members[-1]["decision_time_utc"]), "%Y-%m-%dT%H:%M:%SZ"
            )
            output.append(
                {
                    "kernel_id": kernel_id,
                    "ticker": ticker,
                    "cluster_gap_minutes": max_gap_minutes,
                    "cluster_id": f"{kernel_id}-{ticker}-{max_gap_minutes}m-{index:03d}",
                    "cluster_start_utc": iso_z(start),
                    "cluster_end_utc": iso_z(end),
                    "false_positive_count": len(members),
                    "span_minutes": (end - start).total_seconds() / 60.0,
                    "member_decision_times_utc": "|".join(
                        str(item["decision_time_utc"]) for item in members
                    ),
                }
            )
    return output


def _near_stack_matches(
    sample: DecisionSample, *, direction: str, tolerance_bps: float
) -> bool:
    if sample.state_before != "IDLE":
        return False
    gap20_30, gap30_40 = _ema_pair_gaps_bps(sample.features)
    if gap20_30 is None or gap30_40 is None:
        return False
    if direction == "LONG":
        return bool(sample.features.get("rci9_turn_up")) and (
            gap20_30 > -tolerance_bps and gap30_40 > -tolerance_bps
        )
    if direction == "SHORT":
        return bool(sample.features.get("rci9_turn_down")) and (
            gap20_30 < tolerance_bps and gap30_40 < tolerance_bps
        )
    raise FrozenKernelContractError(f"unsupported direction: {direction}")


def _custom_summary(
    samples: list[DecisionSample], *, target: str, predicate: Any
) -> dict[str, Any]:
    eligible = [row for row in samples if row.state_before == "IDLE"]
    positives = [row for row in eligible if row.transition == target]
    no_events = [row for row in eligible if row.transition == "NO_EVENT"]
    matched = [row for row in eligible if predicate(row)]
    matched_positive = sum(1 for row in matched if row.transition == target)
    return {
        "positive_total": len(positives),
        "matched_positive": matched_positive,
        "event_recall": matched_positive / len(positives) if positives else 0.0,
        "no_event_eligible": len(no_events),
        "no_event_false_positive": sum(
            1 for row in matched if row.transition == "NO_EVENT"
        ),
        "other_event_collision": sum(
            1 for row in matched if row.transition not in (target, "NO_EVENT")
        ),
    }


def build_sensitivity_audit(
    samples: list[DecisionSample],
    manifest: dict[str, Any],
    kernels_by_id: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    output = []
    sensitivity = manifest.get("sensitivity_diagnostics", {})
    for tolerance in sensitivity.get("ema_tolerance_bps", []):
        tolerance_value = _finite_float(tolerance, label="EMA tolerance")
        for direction, target, kernel_id in (
            ("LONG", "PRIMARY_LONG", "KERNEL-L1"),
            ("SHORT", "PRIMARY_SHORT", "KERNEL-S1"),
        ):
            summary = _custom_summary(
                samples,
                target=target,
                predicate=lambda row, d=direction, t=tolerance_value: _near_stack_matches(
                    row, direction=d, tolerance_bps=t
                ),
            )
            output.append(
                {
                    "diagnostic_family": "EMA_ALIGNMENT_TOLERANCE",
                    "kernel_id": kernel_id,
                    "target_transition": target,
                    "parameter": "ema_pair_gap_tolerance_bps",
                    "value": tolerance_value,
                    "formula_promoted": False,
                    **summary,
                }
            )

    for kernel_id, thresholds_key in (
        ("EXIT-L0", "long_exit_rci9_thresholds"),
        ("EXIT-S0", "short_exit_rci9_thresholds"),
    ):
        base = kernels_by_id[kernel_id]
        for threshold in sensitivity.get(thresholds_key, []):
            threshold_value = _finite_float(threshold, label=thresholds_key)
            variant = json.loads(json.dumps(base))
            variant["conditions"] = [
                {
                    "feature": "rci9",
                    "operator": ">=" if kernel_id == "EXIT-L0" else "<=",
                    "value": threshold_value,
                }
            ]
            summary, _, _, _ = evaluate_kernel(samples, variant)
            output.append(
                {
                    "diagnostic_family": "EXIT_RCI9_THRESHOLD",
                    "kernel_id": kernel_id,
                    "target_transition": base["target_transition"],
                    "parameter": "rci9_threshold",
                    "value": threshold_value,
                    "formula_promoted": False,
                    "positive_total": summary["positive_total"],
                    "matched_positive": summary["matched_positive"],
                    "event_recall": summary["event_recall"],
                    "no_event_eligible": summary["no_event_eligible"],
                    "no_event_false_positive": summary["no_event_false_positive"],
                    "other_event_collision": summary["other_event_collision"],
                }
            )
    return output


def build_ema_residual_audit(
    samples: list[DecisionSample], kernels_by_id: dict[str, dict[str, Any]]
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    output = []
    alignment_mismatch_count = 0
    near_cross_event_count = 0
    for row in samples:
        if row.state_before != "IDLE":
            continue
        recorded = str(row.features.get("ema_alignment"))
        derived = _derived_alignment(row.features)
        if recorded != derived:
            alignment_mismatch_count += 1
        gap20_30, gap30_40 = _ema_pair_gaps_bps(row.features)
        near_cross = (
            gap20_30 is not None
            and gap30_40 is not None
            and min(abs(gap20_30), abs(gap30_40)) <= 2.0
        )
        if row.transition in ("PRIMARY_LONG", "PRIMARY_SHORT") and near_cross:
            near_cross_event_count += 1

        if row.transition == "PRIMARY_LONG":
            core = matches_kernel(row, kernels_by_id["CORE-L0"])
            strict = matches_kernel(row, kernels_by_id["KERNEL-L1"])
            category = (
                "CORE_MATCH_STRICT_MISS"
                if core and not strict
                else "STRICT_MATCH"
                if strict
                else "CORE_MISS"
            )
        elif row.transition == "PRIMARY_SHORT":
            core = matches_kernel(row, kernels_by_id["CORE-S0"])
            strict = matches_kernel(row, kernels_by_id["KERNEL-S1"])
            category = (
                "CORE_MATCH_STRICT_MISS"
                if core and not strict
                else "STRICT_MATCH"
                if strict
                else "CORE_MISS"
            )
        elif row.transition == "NO_EVENT":
            long_aligned = recorded == "BULLISH_STACK"
            short_aligned = recorded == "BEARISH_STACK"
            long_turn = bool(row.features.get("rci9_turn_up"))
            short_turn = bool(row.features.get("rci9_turn_down"))
            if long_aligned and not long_turn:
                output.append(
                    {
                        "audit_category": "ALIGNED_NO_EVENT_WITHOUT_RCI9_TURN",
                        "direction": "LONG",
                        **_sample_identity(row),
                        **_diagnostic_features(row),
                    }
                )
            if short_aligned and not short_turn:
                output.append(
                    {
                        "audit_category": "ALIGNED_NO_EVENT_WITHOUT_RCI9_TURN",
                        "direction": "SHORT",
                        **_sample_identity(row),
                        **_diagnostic_features(row),
                    }
                )
            continue
        else:
            continue

        output.append(
            {
                "audit_category": category,
                "direction": "LONG" if row.transition == "PRIMARY_LONG" else "SHORT",
                **_sample_identity(row),
                "near_ema_cross_within_2bps": near_cross,
                **_diagnostic_features(row),
            }
        )

    return output, {
        "recorded_vs_derived_alignment_mismatch_count": alignment_mismatch_count,
        "primary_event_near_ema_cross_within_2bps_count": near_cross_event_count,
        "tradingview_ema_values_available": False,
        "tradingview_mt5_direct_numeric_comparison_performed": False,
        "interpretation": (
            "M7B can audit MT5 EMA stack margins and near-cross sensitivity, but cannot "
            "measure a direct TradingView-vs-MT5 EMA numeric difference without exported "
            "TradingView EMA values."
        ),
    }


def build_jackknife_audit(
    samples: list[DecisionSample], kernels: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    output = []
    for kernel in kernels:
        target = str(kernel["target_transition"])
        positives = [
            row
            for row in samples
            if row.state_before == kernel["eligible_state"] and row.transition == target
        ]
        recalls = []
        for held_out in positives:
            reduced = [row for row in samples if row is not held_out]
            summary, _, _, _ = evaluate_kernel(reduced, kernel)
            recalls.append(float(summary["event_recall"]))
            output.append(
                {
                    "kernel_id": kernel["kernel_id"],
                    "target_transition": target,
                    "held_out_raw_alert_id": held_out.raw_alert_id,
                    "held_out_ticker": held_out.ticker,
                    "held_out_decision_time_utc": iso_z(held_out.decision_time_utc),
                    "remaining_positive_total": summary["positive_total"],
                    "remaining_matched_positive": summary["matched_positive"],
                    "remaining_event_recall": summary["event_recall"],
                    "formula_refit": False,
                }
            )
        if positives:
            output.append(
                {
                    "kernel_id": kernel["kernel_id"],
                    "target_transition": target,
                    "held_out_raw_alert_id": "SUMMARY",
                    "held_out_ticker": "ALL",
                    "held_out_decision_time_utc": None,
                    "remaining_positive_total": len(positives) - 1,
                    "remaining_matched_positive": None,
                    "remaining_event_recall": None,
                    "jackknife_recall_min": min(recalls),
                    "jackknife_recall_max": max(recalls),
                    "formula_refit": False,
                }
            )
    return output


def decide_m7c(
    summaries_by_id: dict[str, dict[str, Any]],
    ticker_summaries: dict[str, dict[str, dict[str, Any]]],
    ema_summary: dict[str, Any],
    manifest: dict[str, Any],
) -> dict[str, Any]:
    criteria = manifest.get("m7c_pass_criteria", {})
    reasons = []
    if ema_summary["recorded_vs_derived_alignment_mismatch_count"] != 0:
        reasons.append("EMA categorical alignment disagrees with derived pair-gap ordering")

    for kernel_id in ("KERNEL-L1", "KERNEL-S1"):
        summary = summaries_by_id[kernel_id]
        min_recall = float(criteria.get("minimum_primary_kernel_recall", 0.70))
        if summary["event_recall"] < min_recall:
            reasons.append(f"{kernel_id} recall below {min_recall:.2f}")
        if summary["other_event_collision"] != 0:
            reasons.append(f"{kernel_id} collides with another genuine event class")
        for ticker, ticker_summary in ticker_summaries[kernel_id].items():
            if ticker_summary["positive_total"] > 0 and ticker_summary["matched_positive"] == 0:
                reasons.append(f"{kernel_id} has zero matched positives in {ticker}")

    for core_id, kernel_id in (("CORE-L0", "KERNEL-L1"), ("CORE-S0", "KERNEL-S1")):
        core = summaries_by_id[core_id]
        kernel = summaries_by_id[kernel_id]
        if kernel["no_event_false_positive"] > core["no_event_false_positive"]:
            reasons.append(f"{kernel_id} increases no-event false positives versus {core_id}")
        allowed_extra_misses = int(criteria.get("maximum_extra_missed_events_vs_core", 1))
        if kernel["false_negative"] > core["false_negative"] + allowed_extra_misses:
            reasons.append(f"{kernel_id} loses too many genuine events versus {core_id}")

    min_exit_recall = float(criteria.get("minimum_exit_core_recall", 0.70))
    for kernel_id in ("EXIT-L0", "EXIT-S0"):
        if summaries_by_id[kernel_id]["event_recall"] < min_exit_recall:
            reasons.append(f"{kernel_id} recall below {min_exit_recall:.2f}")

    passed = not reasons
    return {
        "decision": "PASS" if passed else "BLOCKED",
        "next_stage": (
            "M7C_PROSPECTIVE_SHADOW_REPRODUCTION_AUDIT_ONLY" if passed else None
        ),
        "scope_of_pass": (
            "Approval to start prospective shadow comparison only. No historical scan, "
            "entry gate, Discord, MT5 order, live-ready, or final signal approval."
            if passed
            else "M7C prospective shadow remains blocked."
        ),
        "criteria": criteria,
        "blocking_reasons": reasons,
    }


def audit_frozen_trigger_kernels(
    connection: sqlite3.Connection,
    *,
    mt5_files_root: Path,
    built_at_utc: str,
    manifest: dict[str, Any],
) -> dict[str, Any]:
    samples, coverage = build_decision_samples(
        connection,
        mt5_files_root=mt5_files_root,
        built_at_utc=built_at_utc,
    )
    kernels = list(manifest["kernels"])
    kernels_by_id = {str(item["kernel_id"]): item for item in kernels}

    summaries = []
    event_rows = []
    false_positive_rows = []
    collision_rows = []
    summaries_by_id = {}
    ticker_summaries = {}
    tickers = sorted({row.ticker for row in samples})

    for kernel in kernels:
        summary, events, false_positives, collisions = evaluate_kernel(samples, kernel)
        summaries.append(summary)
        event_rows.extend(events)
        false_positive_rows.extend(false_positives)
        collision_rows.extend(collisions)
        summaries_by_id[str(kernel["kernel_id"])] = summary
        ticker_summaries[str(kernel["kernel_id"])] = {
            ticker: _scope_summary(samples, kernel, ticker) for ticker in tickers
        }

    cluster_rows = build_false_positive_clusters(
        false_positive_rows, max_gap_minutes=15
    ) + build_false_positive_clusters(false_positive_rows, max_gap_minutes=30)
    cross_symbol_rows = build_cross_symbol_audit(samples, kernels)
    sensitivity_rows = build_sensitivity_audit(samples, manifest, kernels_by_id)
    ema_rows, ema_summary = build_ema_residual_audit(samples, kernels_by_id)
    jackknife_rows = build_jackknife_audit(samples, kernels)
    decision = decide_m7c(
        summaries_by_id, ticker_summaries, ema_summary, manifest
    )

    return {
        "status": decision["decision"],
        "stage": "M7B_FROZEN_TRIGGER_KERNEL_VALIDATION_AUDIT_ONLY",
        "contract_version": CONTRACT_VERSION,
        "built_at_utc": built_at_utc,
        "audit_only": True,
        "dry_run": True,
        "database_write_performed": False,
        "csv_input_modified": False,
        "genuine_alert_labels_used": True,
        "no_event_controls_used": True,
        "controls_outside_verified_observation_window_used": False,
        "alert_bar_ohlc_used": False,
        "closed_m15_features_only": True,
        "future_fields_used": False,
        "trade_outcome_fields_used": False,
        "exact_proprietary_condition_claimed": False,
        "independent_proxy_only": True,
        "historical_candidate_extraction_approved": False,
        "cross_timeframe_candidate_extraction_approved": False,
        "entry_gate_enabled": False,
        "discord_send": False,
        "mt5_order": False,
        "live_ready": False,
        "final_signal": False,
        "manifest": manifest,
        **coverage,
        "decision_sample_count": len(samples),
        "event_decision_count": sum(row.transition != "NO_EVENT" for row in samples),
        "no_event_decision_count": sum(row.transition == "NO_EVENT" for row in samples),
        "kernel_summaries": summaries,
        "ticker_kernel_summaries": ticker_summaries,
        "event_audit_rows": event_rows,
        "no_event_false_positive_rows": false_positive_rows,
        "other_event_collision_rows": collision_rows,
        "false_positive_cluster_rows": cluster_rows,
        "cross_symbol_rows": cross_symbol_rows,
        "sensitivity_rows": sensitivity_rows,
        "ema_residual_rows": ema_rows,
        "ema_residual_summary": ema_summary,
        "jackknife_rows": jackknife_rows,
        "rejected_artifacts": manifest.get("rejected_artifacts", []),
        "m7c_decision": decision,
    }


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = []
    seen = set()
    for row in rows:
        for key in row:
            if key not in seen:
                seen.add(key)
                fieldnames.append(key)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(path)


def write_outputs(output_dir: Path, report: dict[str, Any]) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "report": output_dir / "latest_frozen_trigger_kernel_validation.json",
        "event_audit": output_dir / "latest_frozen_trigger_event_audit.csv",
        "false_positives": output_dir / "latest_frozen_trigger_false_positives.csv",
        "event_collisions": output_dir / "latest_frozen_trigger_event_collisions.csv",
        "clusters": output_dir / "latest_frozen_trigger_false_positive_clusters.csv",
        "cross_symbol": output_dir / "latest_frozen_trigger_cross_symbol.csv",
        "sensitivity": output_dir / "latest_frozen_trigger_sensitivity.csv",
        "ema_residuals": output_dir / "latest_frozen_trigger_ema_residuals.csv",
        "jackknife": output_dir / "latest_frozen_trigger_jackknife.csv",
    }
    report_payload = dict(report)
    report_payload["output_paths"] = {key: str(value) for key, value in paths.items()}
    temporary = paths["report"].with_suffix(".json.tmp")
    temporary.write_text(
        json.dumps(report_payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    temporary.replace(paths["report"])
    write_csv(paths["event_audit"], report["event_audit_rows"])
    write_csv(paths["false_positives"], report["no_event_false_positive_rows"])
    write_csv(paths["event_collisions"], report["other_event_collision_rows"])
    write_csv(paths["clusters"], report["false_positive_cluster_rows"])
    write_csv(paths["cross_symbol"], report["cross_symbol_rows"])
    write_csv(paths["sensitivity"], report["sensitivity_rows"])
    write_csv(paths["ema_residuals"], report["ema_residual_rows"])
    write_csv(paths["jackknife"], report["jackknife_rows"])
    return {key: str(value) for key, value in paths.items()}


def _utc_now_text() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="M7B frozen Mochipoyo trigger-kernel validation (audit-only)."
    )
    parser.add_argument("--database", required=True, type=Path)
    parser.add_argument("--mt5-files-root", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--built-at-utc", default=_utc_now_text())
    args = parser.parse_args()

    manifest = load_and_validate_manifest(args.manifest)
    connection = sqlite3.connect(args.database)
    connection.row_factory = sqlite3.Row
    try:
        report = audit_frozen_trigger_kernels(
            connection,
            mt5_files_root=args.mt5_files_root,
            built_at_utc=args.built_at_utc,
            manifest=manifest,
        )
    except (FrozenKernelContractError, TriggerSignatureContractError) as exc:
        raise SystemExit(f"M7B fail-closed: {exc}") from exc
    finally:
        connection.close()
    paths = write_outputs(args.output_dir, report)
    print(
        json.dumps(
            {
                "status": report["status"],
                "m7c_decision": report["m7c_decision"],
                "outputs": paths,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
