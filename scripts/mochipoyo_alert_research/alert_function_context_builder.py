from __future__ import annotations

import json
import math
import sqlite3
from collections import defaultdict
from datetime import timedelta
from typing import Any, Iterable

from mt5_csv_contract import parse_utc

CONTEXT_CONTRACT_VERSION = "MOCHIPOYO_M6B_FUNCTION_CONTEXT_V1"
ENTRY_ID_PREFIX = "M6A:"
FEATURE_TIMEFRAMES = ("M5", "M15", "H1", "H4", "D1")
HTF_TIMEFRAMES = ("H1", "H4", "D1")
EXPANSION_THRESHOLD_ATR_M5 = 1.0
CLEAN_MAE_THRESHOLD_ATR_M5 = 1.0


class ContextMapContractError(RuntimeError):
    pass


def ensure_context_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS alert_function_contexts (
            entry_id TEXT PRIMARY KEY REFERENCES virtual_entries(entry_id),
            context_contract_version TEXT NOT NULL,
            source_entry_alert_id INTEGER NOT NULL REFERENCES raw_alerts(cloudflare_id),
            episode_id TEXT NOT NULL REFERENCES episodes(episode_id),
            ticker TEXT NOT NULL,
            direction TEXT NOT NULL CHECK (direction IN ('LONG', 'SHORT')),
            entry_role TEXT NOT NULL CHECK (entry_role IN ('PRIMARY_ALERT', 'REENTRY_ALERT')),
            entry_time_utc TEXT NOT NULL,
            entry_time_jst TEXT NOT NULL,
            jst_session TEXT NOT NULL,
            context_class TEXT NOT NULL,
            htf_ema_context TEXT NOT NULL,
            htf_ema_aligned_count INTEGER NOT NULL,
            htf_ema_opposed_count INTEGER NOT NULL,
            htf_ema_mixed_count INTEGER NOT NULL,
            m15_macd_context TEXT NOT NULL,
            m5_rci_context TEXT NOT NULL,
            m15_range_context TEXT NOT NULL,
            favorable_first_status TEXT NOT NULL,
            functional_class TEXT NOT NULL,
            exit_class TEXT NOT NULL,
            source_return_atr_m5 REAL,
            mfe_atr_m5 REAL,
            mae_atr_m5 REAL,
            context_json TEXT NOT NULL,
            outcome_json TEXT,
            future_entry_fields_used INTEGER NOT NULL CHECK (future_entry_fields_used = 0),
            outcome_used_for_context_class INTEGER NOT NULL CHECK (outcome_used_for_context_class = 0),
            approved_for_trading INTEGER NOT NULL CHECK (approved_for_trading = 0)
        );

        CREATE INDEX IF NOT EXISTS idx_mochipoyo_context_source_entry
        ON alert_function_contexts (source_entry_alert_id, entry_role);

        CREATE INDEX IF NOT EXISTS idx_mochipoyo_context_class
        ON alert_function_contexts (ticker, direction, context_class);

        CREATE TABLE IF NOT EXISTS alert_function_cohorts (
            dimension TEXT NOT NULL,
            dimension_value TEXT NOT NULL,
            resolved_count INTEGER NOT NULL,
            open_count INTEGER NOT NULL,
            clean_expansion_count INTEGER NOT NULL,
            volatile_expansion_count INTEGER NOT NULL,
            no_expansion_count INTEGER NOT NULL,
            positive_exit_count INTEGER NOT NULL,
            positive_exit_ratio REAL,
            expansion_ratio REAL,
            mean_source_return_atr_m5 REAL,
            mean_mfe_atr_m5 REAL,
            mean_mae_atr_m5 REAL,
            sample_status TEXT NOT NULL,
            generated_at_utc TEXT NOT NULL,
            PRIMARY KEY (dimension, dimension_value)
        );

        CREATE TABLE IF NOT EXISTS alert_function_context_build_runs (
            build_id INTEGER PRIMARY KEY AUTOINCREMENT,
            built_at_utc TEXT NOT NULL,
            context_contract_version TEXT NOT NULL,
            virtual_entry_count INTEGER NOT NULL,
            resolved_entry_count INTEGER NOT NULL,
            open_entry_count INTEGER NOT NULL,
            context_row_count INTEGER NOT NULL,
            cohort_row_count INTEGER NOT NULL,
            future_entry_violation_count INTEGER NOT NULL,
            outcome_used_for_context_class INTEGER NOT NULL
                CHECK (outcome_used_for_context_class = 0),
            approved_for_trading INTEGER NOT NULL CHECK (approved_for_trading = 0),
            audit_only INTEGER NOT NULL CHECK (audit_only = 1)
        );
        """
    )
    connection.commit()


def _finite_float(value: Any, *, label: str) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise ContextMapContractError(f"non-finite value for {label}")
    return result


def _entry_role(entry_type: str) -> str:
    if entry_type == "SOURCE_PRIMARY_ALERT_IMMEDIATE":
        return "PRIMARY_ALERT"
    if entry_type == "SOURCE_REENTRY_ALERT_IMMEDIATE":
        return "REENTRY_ALERT"
    raise ContextMapContractError(f"unsupported M6A entry type: {entry_type}")


def _jst_values(entry_time_utc: str) -> tuple[str, str]:
    value = parse_utc(entry_time_utc) + timedelta(hours=9)
    hour = value.hour
    if 0 <= hour <= 5:
        session = "JST_00_05"
    elif 6 <= hour <= 11:
        session = "JST_06_11"
    elif 12 <= hour <= 17:
        session = "JST_12_17"
    else:
        session = "JST_18_23"
    return value.strftime("%Y-%m-%dT%H:%M:%S+09:00"), session


def _directional_ema_state(direction: str, alignment: str) -> str:
    aligned = (
        (direction == "LONG" and alignment == "BULLISH_STACK")
        or (direction == "SHORT" and alignment == "BEARISH_STACK")
    )
    opposed = (
        (direction == "LONG" and alignment == "BEARISH_STACK")
        or (direction == "SHORT" and alignment == "BULLISH_STACK")
    )
    if aligned:
        return "ALIGNED"
    if opposed:
        return "OPPOSED"
    return "MIXED"


def classify_htf_ema_context(
    direction: str,
    features_by_timeframe: dict[str, dict[str, Any]],
) -> tuple[str, dict[str, int], dict[str, str]]:
    states: dict[str, str] = {}
    counts = {"ALIGNED": 0, "OPPOSED": 0, "MIXED": 0}
    for timeframe in HTF_TIMEFRAMES:
        alignment = str(features_by_timeframe[timeframe]["ema"]["alignment"])
        state = _directional_ema_state(direction, alignment)
        states[timeframe] = state
        counts[state] += 1
    if counts["ALIGNED"] >= 2:
        context = "ALIGNED"
    elif counts["OPPOSED"] >= 2:
        context = "OPPOSED"
    else:
        context = "MIXED"
    return context, counts, states


def classify_macd_context(direction: str, histogram: float) -> str:
    signed = histogram if direction == "LONG" else -histogram
    if signed > 0:
        return "ALIGNED"
    if signed < 0:
        return "OPPOSED"
    return "NEUTRAL"


def classify_m5_rci_context(direction: str, rci9: float, rci14: float) -> str:
    if direction == "LONG":
        pullback = min(rci9, rci14) <= -80.0
        chasing = max(rci9, rci14) >= 80.0
    else:
        pullback = max(rci9, rci14) >= 80.0
        chasing = min(rci9, rci14) <= -80.0
    if pullback and chasing:
        return "SPLIT_EXTREMES"
    if pullback:
        return "PULLBACK_EXTREME"
    if chasing:
        return "CHASING_EXTREME"
    return "NEUTRAL"


def classify_m15_range_context(direction: str, position: float) -> str:
    if position < 0.0 or position > 1.0:
        raise ContextMapContractError(
            f"M15 range position is outside 0..1: {position}"
        )
    if direction == "LONG":
        if position <= 0.25:
            return "FAVORABLE_EDGE"
        if position >= 0.75:
            return "CHASING_EDGE"
    else:
        if position >= 0.75:
            return "FAVORABLE_EDGE"
        if position <= 0.25:
            return "CHASING_EDGE"
    return "MIDDLE"


def classify_entry_context(
    *,
    entry_role: str,
    htf_ema_context: str,
    m15_macd_context: str,
    m15_range_context: str,
) -> str:
    """Classify from entry-time context only. Outcome data is intentionally absent."""
    if entry_role == "REENTRY_ALERT":
        return "C_REENTRY_CONTEXT"
    if (
        htf_ema_context == "ALIGNED"
        and m15_macd_context != "OPPOSED"
        and m15_range_context != "CHASING_EDGE"
    ):
        return "A_CONTINUATION_CONTEXT"
    if (
        htf_ema_context == "OPPOSED"
        or m15_macd_context == "OPPOSED"
        or m15_range_context == "CHASING_EDGE"
    ):
        return "B_WAIT_OR_REVERSAL_CONTEXT"
    return "UNCLASSIFIED_CONTEXT"


def classify_resolved_outcome(
    *,
    source_return_atr_m5: float,
    mfe_atr_m5: float,
    mae_atr_m5: float,
    time_to_mfe_seconds: float,
    time_to_mae_seconds: float,
) -> tuple[str, str, str, dict[str, Any]]:
    if min(mfe_atr_m5, mae_atr_m5) < -1e-12:
        raise ContextMapContractError("negative normalized MFE/MAE")
    if mfe_atr_m5 < EXPANSION_THRESHOLD_ATR_M5:
        functional_class = "NO_EXPANSION"
    elif mae_atr_m5 <= CLEAN_MAE_THRESHOLD_ATR_M5:
        functional_class = "CLEAN_EXPANSION"
    else:
        functional_class = "VOLATILE_EXPANSION"

    exit_class = (
        "POSITIVE_EXIT" if source_return_atr_m5 > 0 else "NONPOSITIVE_EXIT"
    )
    if time_to_mfe_seconds < time_to_mae_seconds:
        favorable_first = "FAVORABLE_FIRST"
    elif time_to_mae_seconds < time_to_mfe_seconds:
        favorable_first = "ADVERSE_FIRST"
    else:
        favorable_first = "SAME_TIME"

    outcome = {
        "functional_class": functional_class,
        "exit_class": exit_class,
        "favorable_first_status": favorable_first,
        "source_return_atr_m5": source_return_atr_m5,
        "mfe_atr_m5": mfe_atr_m5,
        "mae_atr_m5": mae_atr_m5,
        "mfe_to_mae_ratio": (
            None if mae_atr_m5 <= 1e-12 else mfe_atr_m5 / mae_atr_m5
        ),
        "source_exit_efficiency_vs_mfe": (
            None if mfe_atr_m5 <= 1e-12 else source_return_atr_m5 / mfe_atr_m5
        ),
        "time_to_mfe_seconds": time_to_mfe_seconds,
        "time_to_mae_seconds": time_to_mae_seconds,
        "classification_thresholds": {
            "expansion_atr_m5": EXPANSION_THRESHOLD_ATR_M5,
            "clean_mae_atr_m5": CLEAN_MAE_THRESHOLD_ATR_M5,
            "thresholds_optimized_on_current_sample": False,
        },
    }
    return functional_class, exit_class, favorable_first, outcome


def _read_entries(connection: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT
            v.entry_id,
            v.episode_id,
            v.entry_type,
            v.entry_index,
            v.entry_time_utc,
            v.entry_price,
            v.status,
            e.ticker,
            e.direction,
            e.primary_alert_id,
            CASE
                WHEN v.entry_type = 'SOURCE_PRIMARY_ALERT_IMMEDIATE'
                    THEN e.primary_alert_id
                WHEN v.entry_type = 'SOURCE_REENTRY_ALERT_IMMEDIATE'
                    THEN (
                        SELECT ee.raw_alert_id
                        FROM episode_events ee
                        WHERE ee.episode_id = v.episode_id
                          AND ee.event_role = 'REENTRY_ALERT'
                          AND ee.reentry_index = v.entry_index
                    )
                ELSE NULL
            END AS source_entry_alert_id,
            p.outcome_contract_version,
            p.source_return_atr_m5,
            p.mfe_atr_m5,
            p.mae_atr_m5,
            p.source_return_bps,
            p.mfe_bps,
            p.mae_bps,
            p.time_to_mfe_seconds,
            p.time_to_mae_seconds,
            p.path_quality_status
        FROM virtual_entries v
        JOIN episodes e ON e.episode_id = v.episode_id
        LEFT JOIN outcome_path_metrics p ON p.entry_id = v.entry_id
        WHERE v.entry_id LIKE ?
        ORDER BY e.primary_alert_id, v.entry_index, v.entry_id
        """,
        (ENTRY_ID_PREFIX + "%",),
    ).fetchall()
    return [dict(row) for row in rows]


def _expected_entry_source_ids(connection: sqlite3.Connection) -> list[int]:
    rows = connection.execute(
        """
        SELECT raw_alert_id
        FROM episode_events
        WHERE event_role IN ('PRIMARY_ALERT', 'REENTRY_ALERT')
        ORDER BY raw_alert_id
        """
    ).fetchall()
    return [int(row[0]) for row in rows]


def _load_features(
    connection: sqlite3.Connection,
    source_ids: Iterable[int],
) -> dict[int, dict[str, dict[str, Any]]]:
    ids = sorted(set(int(value) for value in source_ids))
    if not ids:
        raise ContextMapContractError("no source entry IDs are available")
    placeholders = ",".join("?" for _ in ids)
    rows = connection.execute(
        f"""
        SELECT source_event_id, timeframe, features_json, future_fields_present
        FROM feature_snapshots
        WHERE source_event_id IN ({placeholders})
        ORDER BY source_event_id, timeframe
        """,
        ids,
    ).fetchall()
    result: dict[int, dict[str, dict[str, Any]]] = {}
    future_count = 0
    for row in rows:
        source_id = int(row["source_event_id"])
        timeframe = str(row["timeframe"])
        future_count += int(row["future_fields_present"] or 0)
        payload = json.loads(str(row["features_json"]))
        if bool(payload.get("contract", {}).get("future_relative_to_decision_used")):
            future_count += 1
        result.setdefault(source_id, {})[timeframe] = payload
    if future_count:
        raise ContextMapContractError(
            f"Stage M5 contains {future_count} future-entry violations"
        )
    expected = set(FEATURE_TIMEFRAMES)
    incomplete = {
        source_id: sorted(expected - set(values))
        for source_id, values in result.items()
        if set(values) != expected
    }
    missing_ids = sorted(set(ids) - set(result))
    if incomplete or missing_ids or len(rows) != len(ids) * len(expected):
        raise ContextMapContractError(
            "Stage M5 entry feature coverage is stale or incomplete: "
            f"missing_ids={missing_ids[:10]} incomplete={list(incomplete.items())[:5]}"
        )
    return result


def validate_m6a_freshness(
    connection: sqlite3.Connection,
    entries: list[dict[str, Any]],
) -> dict[str, int]:
    expected_source_ids = _expected_entry_source_ids(connection)
    actual_source_ids: list[int] = []
    resolved_count = 0
    open_count = 0
    for row in entries:
        source_id = row.get("source_entry_alert_id")
        if source_id is None:
            raise ContextMapContractError(
                f"cannot resolve source alert for {row['entry_id']}"
            )
        actual_source_ids.append(int(source_id))
        status = str(row["status"])
        has_metric = row.get("outcome_contract_version") is not None
        if status == "RESOLVED_SOURCE_EXIT":
            resolved_count += 1
            if not has_metric:
                raise ContextMapContractError(
                    f"resolved M6A entry lacks path metrics: {row['entry_id']}"
                )
        elif status == "OPEN_SOURCE_EPISODE":
            open_count += 1
            if has_metric:
                raise ContextMapContractError(
                    f"open M6A entry unexpectedly has path metrics: {row['entry_id']}"
                )
        else:
            raise ContextMapContractError(
                f"unsupported M6A entry status: {status}"
            )
    if sorted(actual_source_ids) != sorted(expected_source_ids):
        raise ContextMapContractError(
            "Stage M6A virtual entries are stale relative to Stage M3 entry events: "
            f"expected={expected_source_ids[:10]} actual={actual_source_ids[:10]}"
        )
    if resolved_count + open_count != len(entries):
        raise ContextMapContractError("resolved/open M6A accounting does not balance")
    return {
        "virtual_entry_count": len(entries),
        "resolved_entry_count": resolved_count,
        "open_entry_count": open_count,
    }


def _build_context_row(
    entry: dict[str, Any],
    features: dict[str, dict[str, Any]],
    *,
    built_at_utc: str,
) -> tuple[dict[str, Any], tuple[Any, ...]]:
    entry_role = _entry_role(str(entry["entry_type"]))
    direction = str(entry["direction"])
    source_id = int(entry["source_entry_alert_id"])
    entry_time_jst, jst_session = _jst_values(str(entry["entry_time_utc"]))

    htf_context, htf_counts, htf_states = classify_htf_ema_context(
        direction,
        features,
    )
    m15_hist = _finite_float(
        features["M15"]["macd"]["histogram"],
        label="M15 MACD histogram",
    )
    m15_macd_context = classify_macd_context(direction, m15_hist)
    m5_rci9 = _finite_float(features["M5"]["rci"]["rci9"], label="M5 RCI9")
    m5_rci14 = _finite_float(features["M5"]["rci"]["rci14"], label="M5 RCI14")
    m5_rci_context = classify_m5_rci_context(direction, m5_rci9, m5_rci14)
    m15_position = _finite_float(
        features["M15"]["recent_ranges"]["bars_20"]["close_position_0_1"],
        label="M15 20-bar close position",
    )
    m15_range_context = classify_m15_range_context(direction, m15_position)
    context_class = classify_entry_context(
        entry_role=entry_role,
        htf_ema_context=htf_context,
        m15_macd_context=m15_macd_context,
        m15_range_context=m15_range_context,
    )

    context_payload = {
        "contract": {
            "version": CONTEXT_CONTRACT_VERSION,
            "audit_only": True,
            "entry_time_information_only": True,
            "outcome_used_for_context_class": False,
            "approved_for_trading": False,
            "entry_gate_enabled": False,
            "thresholds_optimized_on_current_sample": False,
            "chart_label_redraw_required_for_event_identity": False,
            "reentry_event_identity_source": "WEBHOOK_SQLITE_SOURCE_EVENT_ID",
        },
        "identity": {
            "entry_id": str(entry["entry_id"]),
            "source_entry_alert_id": source_id,
            "episode_id": str(entry["episode_id"]),
            "ticker": str(entry["ticker"]),
            "direction": direction,
            "entry_role": entry_role,
            "entry_time_utc": str(entry["entry_time_utc"]),
            "entry_time_jst": entry_time_jst,
            "jst_session": jst_session,
            "built_at_utc": built_at_utc,
        },
        "classification": {
            "context_class": context_class,
            "htf_ema_context": htf_context,
            "htf_ema_counts": htf_counts,
            "htf_ema_states": htf_states,
            "m15_macd_context": m15_macd_context,
            "m5_rci_context": m5_rci_context,
            "m15_range_context": m15_range_context,
        },
        "entry_time_values": {
            "m15_macd_histogram": m15_hist,
            "m5_rci9": m5_rci9,
            "m5_rci14": m5_rci14,
            "m15_close_position_20": m15_position,
            "atr14_bps": {
                timeframe: _finite_float(
                    features[timeframe]["volatility"]["atr14_bps"],
                    label=f"{timeframe} ATR14 bps",
                )
                for timeframe in FEATURE_TIMEFRAMES
            },
        },
    }

    if str(entry["status"]) == "OPEN_SOURCE_EPISODE":
        functional_class = "OPEN_UNRESOLVED"
        exit_class = "OPEN_UNRESOLVED"
        favorable_first = "OPEN_UNRESOLVED"
        source_return = None
        mfe = None
        mae = None
        outcome_payload = None
    else:
        source_return = _finite_float(
            entry["source_return_atr_m5"],
            label="source return ATR M5",
        )
        mfe = _finite_float(entry["mfe_atr_m5"], label="MFE ATR M5")
        mae = _finite_float(entry["mae_atr_m5"], label="MAE ATR M5")
        functional_class, exit_class, favorable_first, outcome_payload = (
            classify_resolved_outcome(
                source_return_atr_m5=source_return,
                mfe_atr_m5=mfe,
                mae_atr_m5=mae,
                time_to_mfe_seconds=_finite_float(
                    entry["time_to_mfe_seconds"],
                    label="time to MFE",
                ),
                time_to_mae_seconds=_finite_float(
                    entry["time_to_mae_seconds"],
                    label="time to MAE",
                ),
            )
        )
        outcome_payload.update(
            {
                "source_return_bps": _finite_float(
                    entry["source_return_bps"], label="source return bps"
                ),
                "mfe_bps": _finite_float(entry["mfe_bps"], label="MFE bps"),
                "mae_bps": _finite_float(entry["mae_bps"], label="MAE bps"),
                "path_quality_status": str(entry["path_quality_status"]),
                "post_entry_data_used_for_outcome_measurement": True,
                "post_entry_data_used_for_context_class": False,
            }
        )

    summary = {
        "entry_id": str(entry["entry_id"]),
        "source_entry_alert_id": source_id,
        "episode_id": str(entry["episode_id"]),
        "ticker": str(entry["ticker"]),
        "direction": direction,
        "entry_role": entry_role,
        "entry_time_utc": str(entry["entry_time_utc"]),
        "entry_time_jst": entry_time_jst,
        "jst_session": jst_session,
        "context_class": context_class,
        "htf_ema_context": htf_context,
        "m15_macd_context": m15_macd_context,
        "m5_rci_context": m5_rci_context,
        "m15_range_context": m15_range_context,
        "functional_class": functional_class,
        "exit_class": exit_class,
        "favorable_first_status": favorable_first,
        "source_return_atr_m5": source_return,
        "mfe_atr_m5": mfe,
        "mae_atr_m5": mae,
    }
    row = (
        summary["entry_id"],
        CONTEXT_CONTRACT_VERSION,
        source_id,
        summary["episode_id"],
        summary["ticker"],
        direction,
        entry_role,
        summary["entry_time_utc"],
        entry_time_jst,
        jst_session,
        context_class,
        htf_context,
        htf_counts["ALIGNED"],
        htf_counts["OPPOSED"],
        htf_counts["MIXED"],
        m15_macd_context,
        m5_rci_context,
        m15_range_context,
        favorable_first,
        functional_class,
        exit_class,
        source_return,
        mfe,
        mae,
        json.dumps(
            context_payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ),
        (
            None
            if outcome_payload is None
            else json.dumps(
                outcome_payload,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
        ),
        0,
        0,
        0,
    )
    return summary, row


def _sample_status(resolved_count: int) -> str:
    if resolved_count < 5:
        return "VERY_SMALL_SAMPLE"
    if resolved_count < 20:
        return "SMALL_SAMPLE"
    return "OBSERVATIONAL_SAMPLE"


def _mean(values: list[float]) -> float | None:
    return None if not values else sum(values) / len(values)


def _cohort_rows(
    summaries: list[dict[str, Any]],
    *,
    built_at_utc: str,
) -> tuple[list[dict[str, Any]], list[tuple[Any, ...]]]:
    dimensions = (
        "ticker",
        "direction",
        "entry_role",
        "context_class",
        "htf_ema_context",
        "m15_macd_context",
        "m5_rci_context",
        "m15_range_context",
        "jst_session",
    )
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for item in summaries:
        for dimension in dimensions:
            grouped[(dimension, str(item[dimension]))].append(item)
        composite = (
            f"{item['ticker']}|{item['direction']}|{item['entry_role']}|"
            f"{item['context_class']}"
        )
        grouped[("ticker_direction_role_context", composite)].append(item)

    output: list[dict[str, Any]] = []
    rows: list[tuple[Any, ...]] = []
    for key in sorted(grouped):
        values = grouped[key]
        resolved = [
            item for item in values if item["functional_class"] != "OPEN_UNRESOLVED"
        ]
        open_count = len(values) - len(resolved)
        clean = sum(
            1 for item in resolved if item["functional_class"] == "CLEAN_EXPANSION"
        )
        volatile = sum(
            1
            for item in resolved
            if item["functional_class"] == "VOLATILE_EXPANSION"
        )
        no_expansion = sum(
            1 for item in resolved if item["functional_class"] == "NO_EXPANSION"
        )
        positive = sum(
            1 for item in resolved if item["exit_class"] == "POSITIVE_EXIT"
        )
        resolved_count = len(resolved)
        expansion_count = clean + volatile
        returns = [float(item["source_return_atr_m5"]) for item in resolved]
        mfes = [float(item["mfe_atr_m5"]) for item in resolved]
        maes = [float(item["mae_atr_m5"]) for item in resolved]
        item = {
            "dimension": key[0],
            "dimension_value": key[1],
            "resolved_count": resolved_count,
            "open_count": open_count,
            "clean_expansion_count": clean,
            "volatile_expansion_count": volatile,
            "no_expansion_count": no_expansion,
            "positive_exit_count": positive,
            "positive_exit_ratio": (
                None if resolved_count == 0 else positive / resolved_count
            ),
            "expansion_ratio": (
                None if resolved_count == 0 else expansion_count / resolved_count
            ),
            "mean_source_return_atr_m5": _mean(returns),
            "mean_mfe_atr_m5": _mean(mfes),
            "mean_mae_atr_m5": _mean(maes),
            "sample_status": _sample_status(resolved_count),
        }
        output.append(item)
        rows.append(
            (
                item["dimension"],
                item["dimension_value"],
                resolved_count,
                open_count,
                clean,
                volatile,
                no_expansion,
                positive,
                item["positive_exit_ratio"],
                item["expansion_ratio"],
                item["mean_source_return_atr_m5"],
                item["mean_mfe_atr_m5"],
                item["mean_mae_atr_m5"],
                item["sample_status"],
                built_at_utc,
            )
        )
    return output, rows


def _count_by(summaries: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    counts: dict[str, int] = defaultdict(int)
    for item in summaries:
        counts[str(item[key])] += 1
    return [{key: value, "count": counts[value]} for value in sorted(counts)]


def rebuild_alert_function_context_map(
    connection: sqlite3.Connection,
    *,
    built_at_utc: str,
) -> dict[str, Any]:
    ensure_context_schema(connection)
    entries = _read_entries(connection)
    if not entries:
        raise ContextMapContractError(
            "Stage M6A virtual entries do not exist; run M6A first"
        )
    stage_counts = validate_m6a_freshness(connection, entries)
    source_ids = [int(row["source_entry_alert_id"]) for row in entries]
    features = _load_features(connection, source_ids)

    summaries: list[dict[str, Any]] = []
    context_rows: list[tuple[Any, ...]] = []
    for entry in entries:
        source_id = int(entry["source_entry_alert_id"])
        summary, row = _build_context_row(
            entry,
            features[source_id],
            built_at_utc=built_at_utc,
        )
        summaries.append(summary)
        context_rows.append(row)

    if len(context_rows) != stage_counts["virtual_entry_count"]:
        raise ContextMapContractError("context row count does not match M6A entries")
    cohorts, cohort_rows = _cohort_rows(summaries, built_at_utc=built_at_utc)

    # Recheck immediately before the atomic replacement so new/rebuilt upstream
    # rows cannot be silently omitted.
    current_entries = _read_entries(connection)
    validate_m6a_freshness(connection, current_entries)
    if [row["entry_id"] for row in current_entries] != [row["entry_id"] for row in entries]:
        raise ContextMapContractError(
            "M6A entry set changed while building M6B; rerun M6B"
        )

    connection.execute("BEGIN IMMEDIATE")
    try:
        connection.execute("DELETE FROM alert_function_cohorts")
        connection.execute("DELETE FROM alert_function_contexts")
        connection.executemany(
            """
            INSERT INTO alert_function_contexts (
                entry_id, context_contract_version, source_entry_alert_id,
                episode_id, ticker, direction, entry_role,
                entry_time_utc, entry_time_jst, jst_session,
                context_class, htf_ema_context,
                htf_ema_aligned_count, htf_ema_opposed_count,
                htf_ema_mixed_count, m15_macd_context,
                m5_rci_context, m15_range_context,
                favorable_first_status, functional_class, exit_class,
                source_return_atr_m5, mfe_atr_m5, mae_atr_m5,
                context_json, outcome_json,
                future_entry_fields_used, outcome_used_for_context_class,
                approved_for_trading
            ) VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?, ?
            )
            """,
            context_rows,
        )
        connection.executemany(
            """
            INSERT INTO alert_function_cohorts (
                dimension, dimension_value, resolved_count, open_count,
                clean_expansion_count, volatile_expansion_count,
                no_expansion_count, positive_exit_count,
                positive_exit_ratio, expansion_ratio,
                mean_source_return_atr_m5, mean_mfe_atr_m5,
                mean_mae_atr_m5, sample_status, generated_at_utc
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            cohort_rows,
        )
        connection.execute(
            """
            INSERT INTO alert_function_context_build_runs (
                built_at_utc, context_contract_version,
                virtual_entry_count, resolved_entry_count, open_entry_count,
                context_row_count, cohort_row_count,
                future_entry_violation_count,
                outcome_used_for_context_class, approved_for_trading, audit_only
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 0, 0, 0, 1)
            """,
            (
                built_at_utc,
                CONTEXT_CONTRACT_VERSION,
                stage_counts["virtual_entry_count"],
                stage_counts["resolved_entry_count"],
                stage_counts["open_entry_count"],
                len(context_rows),
                len(cohort_rows),
            ),
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise

    open_entries = [
        item for item in summaries if item["functional_class"] == "OPEN_UNRESOLVED"
    ]
    return {
        "context_contract_version": CONTEXT_CONTRACT_VERSION,
        **stage_counts,
        "context_row_count": len(context_rows),
        "cohort_row_count": len(cohort_rows),
        "future_entry_violation_count": 0,
        "outcome_used_for_context_class": False,
        "approved_for_trading": False,
        "entry_gate_enabled": False,
        "chart_label_redraw_required_for_reentry_detection": False,
        "reentry_identity_source": "WEBHOOK_SQLITE_SOURCE_EVENT_ID",
        "classification_thresholds": {
            "htf_ema_majority": "2_of_3_H1_H4_D1",
            "m15_range_favorable_edge": "directional_outer_quarter",
            "m15_range_chasing_edge": "opposite_directional_outer_quarter",
            "functional_expansion_atr_m5": EXPANSION_THRESHOLD_ATR_M5,
            "clean_mae_atr_m5": CLEAN_MAE_THRESHOLD_ATR_M5,
            "optimized_on_current_sample": False,
        },
        "by_context_class": _count_by(summaries, "context_class"),
        "by_functional_class": _count_by(summaries, "functional_class"),
        "by_exit_class": _count_by(summaries, "exit_class"),
        "by_entry_role": _count_by(summaries, "entry_role"),
        "open_entries": open_entries,
        "entry_context_rows": summaries,
        "cohorts": cohorts,
        "sample_size_warning": (
            "Current resolved sample is descriptive only. Context classes are not "
            "approved gates, and cohort results must be frozen and checked on later alerts."
        ),
    }
