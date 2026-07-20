from __future__ import annotations

import csv
import json
import math
import sqlite3
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from alert_trigger_signature_audit import (
    AlertEvent,
    TriggerSignatureContractError,
    flatten_features,
    floor_15,
    read_alert_events,
    transition_for,
    validate_event_roles,
    validate_upstream_coverage,
)
from feature_snapshot_builder import MINIMUM_WARMUP_BARS, build_feature_payload, load_indicator_series
from mt5_csv_contract import FILE_MAP, parse_utc

STAGE = "M7C_PROSPECTIVE_SHADOW_REPRODUCTION_AUDIT_ONLY"
CONTRACT_VERSION = "MOCHIPOYO_M7C_PROSPECTIVE_SHADOW_V1"
TIMEFRAME = "M15"
SUPPORTED = ("PRIMARY_LONG", "PRIMARY_SHORT", "LONG_EXIT", "SHORT_EXIT")
REENTRIES = ("REENTRY_LONG", "REENTRY_SHORT")


class M7CContractError(RuntimeError):
    pass


class M7CUpstreamStaleError(M7CContractError):
    pass


@dataclass(frozen=True)
class SourceTransition:
    raw_alert_id: int
    ticker: str
    decision_time_utc: datetime
    transition: str
    state_before: str
    state_after: str
    event_role: str


@dataclass(frozen=True)
class ProxySignal:
    ticker: str
    decision_time_utc: datetime
    transition: str
    kernel_id: str
    state_before: str
    state_after: str
    features: dict[str, Any]


def iso_z(value: datetime) -> str:
    return value.strftime("%Y-%m-%dT%H:%M:%SZ")


def load_manifest(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise M7CContractError(f"cannot read M7C manifest: {path}") from exc
    if value.get("contract_version") != CONTRACT_VERSION or value.get("stage") != STAGE:
        raise M7CContractError("unexpected M7C manifest")
    if set(value.get("selected_kernels", {})) != set(SUPPORTED):
        raise M7CContractError("M7C selected kernels are incomplete")
    for key in (
        "audit_only",
        "historical_scan_approved",
        "cross_timeframe_scan_approved",
        "entry_gate_enabled",
        "discord_send",
        "mt5_order",
        "live_ready",
        "final_signal",
    ):
        expected = key == "audit_only"
        if value.get(key) is not expected:
            raise M7CContractError(f"unsafe M7C manifest flag: {key}")
    return value


def _matches(features: dict[str, Any], conditions: list[dict[str, Any]]) -> bool:
    for condition in conditions:
        value = features.get(str(condition["feature"]))
        if value is None:
            return False
        operator = str(condition["operator"])
        target = condition["value"]
        if operator == "==" and value != target:
            return False
        if operator == ">=" and (isinstance(value, bool) or float(value) < float(target)):
            return False
        if operator == "<=" and (isinstance(value, bool) or float(value) > float(target)):
            return False
        if operator not in ("==", ">=", "<="):
            raise M7CContractError(f"unsupported frozen operator: {operator}")
    return True


def _validate_upstream(connection: sqlite3.Connection) -> dict[str, int]:
    try:
        return validate_upstream_coverage(connection)
    except TriggerSignatureContractError as exc:
        if "stale relative to raw alerts" in str(exc):
            raise M7CUpstreamStaleError(str(exc)) from exc
        raise M7CContractError(str(exc)) from exc


def replay(events: list[AlertEvent]) -> list[SourceTransition]:
    grouped: dict[str, list[AlertEvent]] = defaultdict(list)
    for event in events:
        grouped[event.ticker].append(event)
    result: list[SourceTransition] = []
    for ticker, rows in sorted(grouped.items()):
        state = "IDLE"
        for event in sorted(rows, key=lambda row: (row.bar_time_utc, row.fired_at_utc, row.raw_id)):
            before = state
            try:
                transition, state = transition_for(event, before)
            except TriggerSignatureContractError as exc:
                raise M7CContractError(str(exc)) from exc
            result.append(
                SourceTransition(
                    event.raw_id,
                    ticker,
                    floor_15(event.bar_time_utc),
                    transition,
                    before,
                    state,
                    event.event_role,
                )
            )
    return sorted(result, key=lambda row: (row.decision_time_utc, row.ticker, row.raw_alert_id))


def bootstrap(
    events: list[AlertEvent], manifest: dict[str, Any]
) -> tuple[dict[str, str], dict[str, float], list[SourceTransition]]:
    start = parse_utc(str(manifest["prospective_start_utc"]))
    pre = [event for event in events if floor_15(event.bar_time_utc) <= start]
    post = [event for event in events if floor_15(event.bar_time_utc) > start]
    transitions = replay(pre)
    states: dict[str, str] = {}
    latest_ids: dict[str, int] = {}
    ids: dict[str, list[int]] = defaultdict(list)
    for row in transitions:
        states[row.ticker] = row.state_after
        latest_ids[row.ticker] = row.raw_alert_id
        ids[row.ticker].append(row.raw_alert_id)

    offsets: dict[str, float] = {}
    for ticker, contract in sorted(manifest["bootstrap"].items()):
        expected_ids = [int(value) for value in contract["expected_pre_start_raw_alert_ids"]]
        if ids.get(ticker, []) != expected_ids:
            raise M7CContractError(
                f"delayed/new pre-start events changed {ticker} bootstrap: "
                f"{ids.get(ticker, [])} != {expected_ids}"
            )
        if states.get(ticker) != str(contract["state_at_start"]):
            raise M7CContractError(f"bootstrap state changed for {ticker}")
        if latest_ids.get(ticker) != int(contract["latest_raw_alert_id"]):
            raise M7CContractError(f"bootstrap latest raw ID changed for {ticker}")
        offsets[ticker] = float(contract["offset_hours"])

    for event in post:
        expected = offsets.get(event.ticker)
        if expected is None or abs(float(event.selected_offset_hours) - expected) > 1e-9:
            raise M7CContractError(
                f"DST_SEGMENT_REVIEW_REQUIRED for {event.ticker}: "
                f"{event.selected_offset_hours} != {expected}"
            )
    return states, offsets, replay(events)


def _decision_features(
    series: Any,
    selected_index: int,
    current_index: int,
    ticker: str,
    offset: float,
    decision_time: datetime,
    built_at_utc: str,
) -> dict[str, Any]:
    selected = series.bars[selected_index]
    current = series.bars[current_index]
    payload = build_feature_payload(
        series,
        selected_index=selected_index,
        ticker=ticker,
        timeframe=TIMEFRAME,
        source_filename=FILE_MAP[ticker][TIMEFRAME],
        decision_time_utc=decision_time,
        selected_utc_close=decision_time,
        selected_offset_hours=offset,
        built_at_utc=built_at_utc,
    )
    features = flatten_features(series, selected_index, payload)
    atr = float(payload["volatility"]["atr14"])
    if not math.isfinite(atr) or atr <= 0:
        raise M7CContractError("invalid ATR14")
    features["current_open_minus_ema20_atr"] = (
        current.open_price - float(payload["ema"]["ema20"])
    ) / atr
    features["current_open_minus_ema40_atr"] = (
        current.open_price - float(payload["ema"]["ema40"])
    ) / atr
    denominator = max(abs(selected.close_price), 1e-12)
    features["ema20_minus_ema30_bps"] = (
        float(payload["ema"]["ema20"]) - float(payload["ema"]["ema30"])
    ) / denominator * 10000.0
    features["ema30_minus_ema40_bps"] = (
        float(payload["ema"]["ema30"]) - float(payload["ema"]["ema40"])
    ) / denominator * 10000.0
    return features


def build_proxy(
    mt5_root: Path,
    manifest: dict[str, Any],
    states: dict[str, str],
    offsets: dict[str, float],
    built_at_utc: str,
) -> tuple[list[dict[str, Any]], list[ProxySignal], dict[str, str], dict[str, datetime | None]]:
    start = parse_utc(str(manifest["prospective_start_utc"]))
    latest_allowed = floor_15(parse_utc(built_at_utc))
    decisions: list[dict[str, Any]] = []
    signals: list[ProxySignal] = []
    latest: dict[str, datetime | None] = {}

    for ticker in sorted(states):
        state = states[ticker]
        offset = offsets[ticker]
        series = load_indicator_series(mt5_root / FILE_MAP[ticker][TIMEFRAME])
        latest[ticker] = None
        for current_index in range(1, len(series.bars)):
            selected_index = current_index - 1
            if selected_index + 1 < MINIMUM_WARMUP_BARS:
                continue
            current = series.bars[current_index]
            decision_time = current.server_open - timedelta(hours=offset)
            if decision_time <= start or decision_time > latest_allowed:
                continue
            selected = series.bars[selected_index]
            closed_at = selected.server_open - timedelta(hours=offset) + timedelta(minutes=15)
            if closed_at > decision_time:
                raise M7CContractError(f"causal cutoff violation for {ticker}")
            features = _decision_features(
                series, selected_index, current_index, ticker, offset, decision_time, built_at_utc
            )
            before = state
            emitted = "NO_SIGNAL"
            kernel_id = ""
            conflict = False
            if before == "IDLE":
                long_rule = manifest["selected_kernels"]["PRIMARY_LONG"]
                short_rule = manifest["selected_kernels"]["PRIMARY_SHORT"]
                long_match = _matches(features, list(long_rule["conditions"]))
                short_match = _matches(features, list(short_rule["conditions"]))
                if long_match and short_match:
                    emitted, conflict = "AMBIGUOUS_PRIMARY", True
                elif long_match:
                    emitted, kernel_id, state = "PRIMARY_LONG", str(long_rule["kernel_id"]), "ACTIVE_LONG"
                elif short_match:
                    emitted, kernel_id, state = "PRIMARY_SHORT", str(short_rule["kernel_id"]), "ACTIVE_SHORT"
            elif before == "ACTIVE_LONG":
                rule = manifest["selected_kernels"]["LONG_EXIT"]
                if _matches(features, list(rule["conditions"])):
                    emitted, kernel_id, state = "LONG_EXIT", str(rule["kernel_id"]), "IDLE"
            elif before == "ACTIVE_SHORT":
                rule = manifest["selected_kernels"]["SHORT_EXIT"]
                if _matches(features, list(rule["conditions"])):
                    emitted, kernel_id, state = "SHORT_EXIT", str(rule["kernel_id"]), "IDLE"
            else:
                raise M7CContractError(f"invalid proxy state: {before}")

            decisions.append(
                {
                    "ticker": ticker,
                    "decision_time_utc": iso_z(decision_time),
                    "selected_server_open": selected.server_open.strftime("%Y.%m.%d %H:%M:%S"),
                    "current_server_open": current.server_open.strftime("%Y.%m.%d %H:%M:%S"),
                    "state_before": before,
                    "emitted_transition": emitted,
                    "kernel_id": kernel_id,
                    "state_after": state,
                    "ambiguous_primary_conflict": conflict,
                    "rci9": features.get("rci9"),
                    "rci9_delta1": features.get("rci9_delta1"),
                    "rci9_turn_up": features.get("rci9_turn_up"),
                    "rci9_turn_down": features.get("rci9_turn_down"),
                    "ema_alignment": features.get("ema_alignment"),
                    "ema20_minus_ema30_bps": features.get("ema20_minus_ema30_bps"),
                    "ema30_minus_ema40_bps": features.get("ema30_minus_ema40_bps"),
                }
            )
            if emitted in SUPPORTED:
                signals.append(
                    ProxySignal(ticker, decision_time, emitted, kernel_id, before, state, features)
                )
            latest[ticker] = decision_time
        states[ticker] = state

    decisions.sort(key=lambda row: (row["decision_time_utc"], row["ticker"]))
    signals.sort(key=lambda row: (row.decision_time_utc, row.ticker, row.transition))
    return decisions, signals, states, latest


def compare(
    sources: list[SourceTransition],
    signals: list[ProxySignal],
    latest: dict[str, datetime | None],
    built_at_utc: str,
    manifest: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    grace = int(manifest["matching"]["source_arrival_grace_minutes"])
    finalized_cutoff = parse_utc(built_at_utc) - timedelta(minutes=grace)
    used: set[int] = set()
    comparisons: list[dict[str, Any]] = []

    for source in sources:
        base = {
            "raw_alert_id": source.raw_alert_id,
            "ticker": source.ticker,
            "source_decision_time_utc": iso_z(source.decision_time_utc),
            "source_transition": source.transition,
            "source_state_before": source.state_before,
            "source_state_after": source.state_after,
            "event_role": source.event_role,
        }
        if source.transition in REENTRIES:
            comparisons.append({**base, "classification": "UNSUPPORTED_REENTRY_NOT_SCORED"})
            continue
        if source.transition not in SUPPORTED:
            raise M7CContractError(f"unexpected source transition: {source.transition}")
        if latest.get(source.ticker) is None or source.decision_time_utc > latest[source.ticker]:
            comparisons.append({**base, "classification": "PENDING_CSV_COVERAGE"})
            continue

        candidates: list[tuple[int, int, int, ProxySignal]] = []
        for index, signal in enumerate(signals):
            if index in used or signal.ticker != source.ticker or signal.transition != source.transition:
                continue
            delta = int(round((signal.decision_time_utc - source.decision_time_utc).total_seconds() / 900))
            if abs(delta) <= 1:
                candidates.append((abs(delta), delta, index, signal))
        candidates.sort(key=lambda row: (row[0], abs(row[1]), row[3].decision_time_utc))
        if candidates:
            _, delta, index, signal = candidates[0]
            used.add(index)
            classification = "EXACT_MATCH" if delta == 0 else "EARLY_1_BAR" if delta == -1 else "LATE_1_BAR"
            comparisons.append(
                {
                    **base,
                    "classification": classification,
                    "proxy_decision_time_utc": iso_z(signal.decision_time_utc),
                    "proxy_transition": signal.transition,
                    "proxy_kernel_id": signal.kernel_id,
                    "bar_delta": delta,
                }
            )
            continue

        wrong = [
            signal
            for index, signal in enumerate(signals)
            if index not in used
            and signal.ticker == source.ticker
            and abs((signal.decision_time_utc - source.decision_time_utc).total_seconds()) <= 900
        ]
        if wrong:
            signal = min(
                wrong,
                key=lambda row: abs((row.decision_time_utc - source.decision_time_utc).total_seconds()),
            )
            comparisons.append(
                {
                    **base,
                    "classification": "WRONG_TRANSITION_NEARBY",
                    "proxy_decision_time_utc": iso_z(signal.decision_time_utc),
                    "proxy_transition": signal.transition,
                    "proxy_kernel_id": signal.kernel_id,
                }
            )
        else:
            comparisons.append({**base, "classification": "MISSED"})

    extras: list[dict[str, Any]] = []
    for index, signal in enumerate(signals):
        if index in used:
            continue
        finalized = signal.decision_time_utc <= finalized_cutoff
        extras.append(
            {
                "ticker": signal.ticker,
                "proxy_decision_time_utc": iso_z(signal.decision_time_utc),
                "proxy_transition": signal.transition,
                "proxy_kernel_id": signal.kernel_id,
                "proxy_state_before": signal.state_before,
                "proxy_state_after": signal.state_after,
                "classification": (
                    "FINALIZED_EXTRA_PROXY_SIGNAL"
                    if finalized
                    else "PENDING_SOURCE_ARRIVAL_GRACE"
                ),
                "source_arrival_grace_minutes": grace,
                "rci9": signal.features.get("rci9"),
                "ema_alignment": signal.features.get("ema_alignment"),
            }
        )

    comparisons.sort(key=lambda row: (row["source_decision_time_utc"], row["ticker"], row["raw_alert_id"]))
    extras.sort(key=lambda row: (row["proxy_decision_time_utc"], row["ticker"]))
    scored = [
        row for row in comparisons
        if row["classification"] not in ("UNSUPPORTED_REENTRY_NOT_SCORED", "PENDING_CSV_COVERAGE")
    ]
    exact = sum(row["classification"] == "EXACT_MATCH" for row in scored)
    within = sum(
        row["classification"] in ("EXACT_MATCH", "EARLY_1_BAR", "LATE_1_BAR")
        for row in scored
    )
    summary = {
        "supported_source_event_count": sum(row.transition in SUPPORTED for row in sources),
        "scored_source_event_count": len(scored),
        "pending_csv_source_event_count": sum(
            row["classification"] == "PENDING_CSV_COVERAGE" for row in comparisons
        ),
        "unsupported_reentry_count": sum(row.transition in REENTRIES for row in sources),
        "exact_match_count": exact,
        "within_one_bar_match_count": within,
        "missed_count": sum(row["classification"] == "MISSED" for row in scored),
        "wrong_transition_nearby_count": sum(
            row["classification"] == "WRONG_TRANSITION_NEARBY" for row in scored
        ),
        "exact_recall": exact / len(scored) if scored else None,
        "within_one_bar_recall": within / len(scored) if scored else None,
        "finalized_extra_proxy_signal_count": sum(
            row["classification"] == "FINALIZED_EXTRA_PROXY_SIGNAL" for row in extras
        ),
        "pending_grace_proxy_signal_count": sum(
            row["classification"] == "PENDING_SOURCE_ARRIVAL_GRACE" for row in extras
        ),
    }
    return comparisons, extras, summary


def readiness(comparisons: list[dict[str, Any]], manifest: dict[str, Any]) -> dict[str, Any]:
    gates = manifest["review_gates"]
    scored = [
        row for row in comparisons
        if row["source_transition"] in SUPPORTED and row["classification"] != "PENDING_CSV_COVERAGE"
    ]
    by_ticker: dict[str, int] = defaultdict(int)
    by_transition: dict[str, int] = defaultdict(int)
    for row in scored:
        by_ticker[row["ticker"]] += 1
        by_transition[row["source_transition"]] += 1
    checks = {
        "minimum_supported_source_events": len(scored)
        >= int(gates["formal_minimum_supported_source_events"]),
        "minimum_btc_supported_events": by_ticker["BTCUSD"]
        >= int(gates["formal_minimum_supported_events_per_ticker"]),
        "minimum_xau_supported_events": by_ticker["XAUUSD"]
        >= int(gates["formal_minimum_supported_events_per_ticker"]),
        "minimum_primary_long_events": by_transition["PRIMARY_LONG"]
        >= int(gates["formal_minimum_events_per_primary_direction"]),
        "minimum_primary_short_events": by_transition["PRIMARY_SHORT"]
        >= int(gates["formal_minimum_events_per_primary_direction"]),
        "minimum_exit_events": by_transition["LONG_EXIT"] + by_transition["SHORT_EXIT"]
        >= int(gates["formal_minimum_exit_events"]),
    }
    return {
        "supported_source_events_observed": len(scored),
        "by_ticker": dict(sorted(by_ticker.items())),
        "by_transition": dict(sorted(by_transition.items())),
        "operational_checkpoint_reached": len(scored) >= int(gates["operational_checkpoint_events"]),
        "interim_checkpoint_reached": len(scored) >= int(gates["interim_checkpoint_events"]),
        "formal_review_requirements": checks,
        "formal_review_state": (
            "READY_FOR_MANUAL_REPRODUCTION_REVIEW"
            if all(checks.values())
            else "INSUFFICIENT_FORWARD_SAMPLE"
        ),
        "automatic_reproduction_claim": False,
    }


def audit_m7c(
    connection: sqlite3.Connection,
    *,
    mt5_files_root: Path,
    manifest: dict[str, Any],
    built_at_utc: str,
) -> dict[str, Any]:
    upstream = _validate_upstream(connection)
    events = read_alert_events(connection)
    validate_event_roles(events)
    states, offsets, all_source = bootstrap(events, manifest)
    decisions, signals, final_states, latest = build_proxy(
        mt5_files_root, manifest, dict(states), offsets, built_at_utc
    )
    start = parse_utc(str(manifest["prospective_start_utc"]))
    source_after = [row for row in all_source if row.decision_time_utc > start]
    comparisons, extras, summary = compare(
        source_after, signals, latest, built_at_utc, manifest
    )
    signal_rows = [
        {
            "ticker": row.ticker,
            "proxy_decision_time_utc": iso_z(row.decision_time_utc),
            "proxy_transition": row.transition,
            "proxy_kernel_id": row.kernel_id,
            "state_before": row.state_before,
            "state_after": row.state_after,
            "rci9": row.features.get("rci9"),
            "rci9_delta1": row.features.get("rci9_delta1"),
            "rci9_turn_up": row.features.get("rci9_turn_up"),
            "rci9_turn_down": row.features.get("rci9_turn_down"),
            "ema_alignment": row.features.get("ema_alignment"),
        }
        for row in signals
    ]
    return {
        "status": "COLLECTING",
        "stage": STAGE,
        "contract_version": CONTRACT_VERSION,
        "built_at_utc": built_at_utc,
        "audit_only": True,
        "dry_run": True,
        "database_write_performed": False,
        "csv_input_modified": False,
        "prospective_start_utc": manifest["prospective_start_utc"],
        "historical_pre_start_decisions_scored": False,
        "alert_bar_high_low_close_used": False,
        "closed_m15_features_only": True,
        "current_m15_open_only": True,
        "future_fields_used": False,
        "trade_outcome_fields_used": False,
        "formula_refit_performed": False,
        "reentry_rule_used": False,
        "entry_gate_enabled": False,
        "discord_send": False,
        "mt5_order": False,
        "live_ready": False,
        "final_signal": False,
        "manifest": manifest,
        "upstream_coverage": upstream,
        "bootstrap_states": states,
        "proxy_final_states": final_states,
        "offset_hours": offsets,
        "latest_proxy_decision_utc": {
            ticker: None if value is None else iso_z(value) for ticker, value in latest.items()
        },
        "proxy_decision_count": len(decisions),
        "proxy_signal_count": len(signal_rows),
        "new_source_event_count": len(source_after),
        "comparison_summary": summary,
        "readiness": readiness(comparisons, manifest),
        "proxy_decision_rows": decisions,
        "proxy_signal_rows": signal_rows,
        "source_event_comparison_rows": comparisons,
        "extra_proxy_signal_rows": extras,
    }


def atomic_write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with temporary.open("w", encoding="utf-8-sig", newline="") as handle:
        if fields:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
        else:
            handle.write("")
    temporary.replace(path)


def write_outputs(output_dir: Path, report: dict[str, Any]) -> dict[str, str]:
    paths = {
        "report": output_dir / "latest_m7c_prospective_shadow.json",
        "proxy_decisions": output_dir / "latest_m7c_proxy_decisions.csv",
        "proxy_signals": output_dir / "latest_m7c_proxy_signals.csv",
        "source_comparisons": output_dir / "latest_m7c_source_event_comparisons.csv",
        "extra_proxy_signals": output_dir / "latest_m7c_extra_proxy_signals.csv",
    }
    decisions = list(report.pop("proxy_decision_rows"))
    signals = list(report.pop("proxy_signal_rows"))
    comparisons = list(report.pop("source_event_comparison_rows"))
    extras = list(report.pop("extra_proxy_signal_rows"))
    report["output_paths"] = {key: str(value) for key, value in paths.items()}
    atomic_write_json(paths["report"], report)
    write_csv(paths["proxy_decisions"], decisions)
    write_csv(paths["proxy_signals"], signals)
    write_csv(paths["source_comparisons"], comparisons)
    write_csv(paths["extra_proxy_signals"], extras)
    return {key: str(value) for key, value in paths.items()}
