from __future__ import annotations

import csv
import json
import math
import sqlite3
import statistics
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Iterable

from feature_snapshot_builder import (
    MINIMUM_WARMUP_BARS,
    build_feature_payload,
    load_indicator_series,
)
from mt5_csv_contract import FILE_MAP, parse_utc

CONTRACT_VERSION = "MOCHIPOYO_M7A_TRIGGER_SIGNATURE_V1"
TIMEFRAME = "M15"
TRANSITIONS = (
    "PRIMARY_LONG",
    "PRIMARY_SHORT",
    "REENTRY_LONG",
    "REENTRY_SHORT",
    "LONG_EXIT",
    "SHORT_EXIT",
)
ELIGIBLE_STATE = {
    "PRIMARY_LONG": "IDLE",
    "PRIMARY_SHORT": "IDLE",
    "REENTRY_LONG": "ACTIVE_LONG",
    "REENTRY_SHORT": "ACTIVE_SHORT",
    "LONG_EXIT": "ACTIVE_LONG",
    "SHORT_EXIT": "ACTIVE_SHORT",
}
NUMERIC_QUANTILES = (0.0, 0.1, 0.25, 0.5, 0.75, 0.9, 1.0)
TOP_SINGLE_LIMIT = 16
TOP_PAIR_SOURCE_LIMIT = 12
TOP_PAIR_LIMIT = 20


class TriggerSignatureContractError(RuntimeError):
    pass


@dataclass(frozen=True)
class AlertEvent:
    raw_id: int
    ticker: str
    event: str
    event_role: str
    bar_time_utc: datetime
    fired_at_utc: datetime
    selected_offset_hours: float
    selected_server_open: datetime


@dataclass
class DecisionSample:
    ticker: str
    decision_time_utc: datetime
    selected_server_open: datetime
    state_before: str
    transition: str
    raw_alert_id: int | None
    features: dict[str, Any]


def iso_z(value: datetime) -> str:
    return value.strftime("%Y-%m-%dT%H:%M:%SZ")


def floor_15(value: datetime) -> datetime:
    return value.replace(minute=(value.minute // 15) * 15, second=0, microsecond=0)


def _finite(value: Any, *, label: str) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise TriggerSignatureContractError(f"non-finite {label}")
    return result


def _median(values: Iterable[float]) -> float | None:
    data = list(values)
    return None if not data else float(statistics.median(data))


def _mean(values: Iterable[float]) -> float | None:
    data = list(values)
    return None if not data else float(sum(data) / len(data))


def _quantile(values: list[float], q: float) -> float:
    if not values:
        raise ValueError("quantile requires values")
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = q * (len(ordered) - 1)
    lower = int(math.floor(position))
    upper = int(math.ceil(position))
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def _parse_alignment_diagnostics(text: str) -> dict[str, Any]:
    try:
        payload = json.loads(text)
    except Exception as exc:
        raise TriggerSignatureContractError("invalid M15 alignment diagnostics JSON") from exc
    if not isinstance(payload, dict):
        raise TriggerSignatureContractError("M15 alignment diagnostics is not an object")
    return payload


def validate_upstream_coverage(connection: sqlite3.Connection) -> dict[str, int]:
    eligible_rows = connection.execute(
        """
        SELECT r.cloudflare_id
        FROM raw_alerts r
        WHERE NOT EXISTS (
            SELECT 1 FROM raw_alert_annotations a
            WHERE a.raw_alert_id = r.cloudflare_id
              AND a.annotation_type = 'CONNECTION_TEST'
        )
        ORDER BY r.cloudflare_id
        """
    ).fetchall()
    eligible_ids = [int(row[0]) for row in eligible_rows]
    if not eligible_ids:
        raise TriggerSignatureContractError("no eligible raw alerts")

    assigned_rows = connection.execute(
        "SELECT raw_alert_id, event_role FROM episode_events ORDER BY raw_alert_id"
    ).fetchall()
    assigned_ids = [int(row[0]) for row in assigned_rows]
    if assigned_ids != eligible_ids:
        raise TriggerSignatureContractError(
            "Stage M3 episode events are stale relative to raw alerts"
        )
    unsupported_roles = sorted(
        {
            str(row[1])
            for row in assigned_rows
            if str(row[1]) not in ("PRIMARY_ALERT", "REENTRY_ALERT", "EXIT_ALERT")
        }
    )
    if unsupported_roles:
        raise TriggerSignatureContractError(
            "M7A six-transition contract does not silently omit assigned roles: "
            f"{unsupported_roles}"
        )

    alignment_rows = connection.execute(
        """
        SELECT raw_alert_id, alignment_status
        FROM mt5_alignment
        WHERE timeframe = 'M15'
        ORDER BY raw_alert_id
        """
    ).fetchall()
    alignment_ids = [int(row[0]) for row in alignment_rows]
    if alignment_ids != eligible_ids:
        raise TriggerSignatureContractError(
            "Stage M4 M15 alignment is stale relative to raw alerts"
        )
    invalid_alignment = sum(
        1 for row in alignment_rows if str(row[1]) != "ALIGNED_CLOSED_BAR"
    )
    if invalid_alignment:
        raise TriggerSignatureContractError(
            f"Stage M4 has {invalid_alignment} invalid M15 alignment rows"
        )
    return {"eligible_raw_alert_count": len(eligible_ids)}


def read_alert_events(connection: sqlite3.Connection) -> list[AlertEvent]:
    rows = connection.execute(
        """
        SELECT
            r.cloudflare_id,
            r.ticker,
            r.event,
            r.bar_time_utc,
            r.fired_at_utc,
            ee.event_role,
            a.selected_offset_hours,
            a.mt5_server_time,
            a.alignment_status,
            a.diagnostics_json
        FROM raw_alerts r
        JOIN episode_events ee ON ee.raw_alert_id = r.cloudflare_id
        JOIN mt5_alignment a
          ON a.raw_alert_id = r.cloudflare_id AND a.timeframe = 'M15'
        WHERE ee.event_role IN ('PRIMARY_ALERT', 'REENTRY_ALERT', 'EXIT_ALERT')
          AND NOT EXISTS (
              SELECT 1 FROM raw_alert_annotations x
              WHERE x.raw_alert_id = r.cloudflare_id
                AND x.annotation_type = 'CONNECTION_TEST'
          )
        ORDER BY r.fired_at_utc, r.cloudflare_id
        """
    ).fetchall()
    if not rows:
        raise TriggerSignatureContractError("no eligible genuine alert events")
    output: list[AlertEvent] = []
    for row in rows:
        if str(row["alignment_status"]) != "ALIGNED_CLOSED_BAR":
            raise TriggerSignatureContractError(
                f"M15 alignment is not valid for raw alert {row['cloudflare_id']}"
            )
        if row["selected_offset_hours"] is None or row["mt5_server_time"] is None:
            raise TriggerSignatureContractError(
                f"M15 alignment is incomplete for raw alert {row['cloudflare_id']}"
            )
        _parse_alignment_diagnostics(str(row["diagnostics_json"]))
        output.append(
            AlertEvent(
                raw_id=int(row["cloudflare_id"]),
                ticker=str(row["ticker"]),
                event=str(row["event"]),
                event_role=str(row["event_role"]),
                bar_time_utc=parse_utc(str(row["bar_time_utc"])),
                fired_at_utc=parse_utc(str(row["fired_at_utc"])),
                selected_offset_hours=_finite(
                    row["selected_offset_hours"], label="M15 selected offset"
                ),
                selected_server_open=datetime.strptime(
                    str(row["mt5_server_time"]), "%Y.%m.%d %H:%M:%S"
                ),
            )
        )
    return output


def validate_event_roles(events: list[AlertEvent]) -> None:
    anomaly_count = 0
    for event in events:
        if event.event_role == "PRIMARY_ALERT" and event.event not in ("LONG", "SHORT"):
            anomaly_count += 1
        elif event.event_role == "REENTRY_ALERT" and event.event not in ("LONG", "SHORT"):
            anomaly_count += 1
        elif event.event_role == "EXIT_ALERT" and event.event not in (
            "LONG_EXIT",
            "SHORT_EXIT",
        ):
            anomaly_count += 1
    if anomaly_count:
        raise TriggerSignatureContractError("event role/raw event mismatch")


def transition_for(event: AlertEvent, state_before: str) -> tuple[str, str]:
    if event.event == "LONG":
        if state_before == "IDLE" and event.event_role == "PRIMARY_ALERT":
            return "PRIMARY_LONG", "ACTIVE_LONG"
        if state_before == "ACTIVE_LONG" and event.event_role == "REENTRY_ALERT":
            return "REENTRY_LONG", "ACTIVE_LONG"
    elif event.event == "SHORT":
        if state_before == "IDLE" and event.event_role == "PRIMARY_ALERT":
            return "PRIMARY_SHORT", "ACTIVE_SHORT"
        if state_before == "ACTIVE_SHORT" and event.event_role == "REENTRY_ALERT":
            return "REENTRY_SHORT", "ACTIVE_SHORT"
    elif event.event == "LONG_EXIT":
        if state_before == "ACTIVE_LONG" and event.event_role == "EXIT_ALERT":
            return "LONG_EXIT", "IDLE"
    elif event.event == "SHORT_EXIT":
        if state_before == "ACTIVE_SHORT" and event.event_role == "EXIT_ALERT":
            return "SHORT_EXIT", "IDLE"
    raise TriggerSignatureContractError(
        f"state/role transition mismatch at raw alert {event.raw_id}: "
        f"state={state_before} event={event.event} role={event.event_role}"
    )


def _feature_value(payload: dict[str, Any], path: tuple[str, ...]) -> Any:
    value: Any = payload
    for key in path:
        value = value[key]
    return value


def flatten_features(
    series: Any,
    index: int,
    payload: dict[str, Any],
) -> dict[str, Any]:
    features: dict[str, Any] = {
        "ema_alignment": _feature_value(payload, ("ema", "alignment")),
        "ema_spread_atr": _feature_value(payload, ("ema", "spread_atr_ratio")),
        "close_minus_ema20_bps": _feature_value(
            payload, ("ema", "close_minus_ema20_bps")
        ),
        "close_minus_ema30_bps": _feature_value(
            payload, ("ema", "close_minus_ema30_bps")
        ),
        "close_minus_ema40_bps": _feature_value(
            payload, ("ema", "close_minus_ema40_bps")
        ),
        "ema20_slope_3_bars_bps": _feature_value(
            payload, ("ema", "ema20_slope_3_bars_bps")
        ),
        "ema30_slope_3_bars_bps": _feature_value(
            payload, ("ema", "ema30_slope_3_bars_bps")
        ),
        "ema40_slope_3_bars_bps": _feature_value(
            payload, ("ema", "ema40_slope_3_bars_bps")
        ),
        "rci9": _feature_value(payload, ("rci", "rci9")),
        "rci14": _feature_value(payload, ("rci", "rci14")),
        "rci18": _feature_value(payload, ("rci", "rci18")),
        "macd_line_bps": _feature_value(payload, ("macd", "line_bps")),
        "macd_signal_bps": _feature_value(payload, ("macd", "signal_bps")),
        "macd_histogram_bps": _feature_value(payload, ("macd", "histogram_bps")),
        "macd_zero_proximity_atr": _feature_value(
            payload, ("macd", "zero_proximity_atr_ratio")
        ),
        "atr14_bps": _feature_value(payload, ("volatility", "atr14_bps")),
        "bar_range_atr": _feature_value(
            payload, ("volatility", "bar_range_atr_ratio")
        ),
        "candle_direction": _feature_value(payload, ("candle", "direction")),
        "body_to_range": _feature_value(
            payload, ("candle", "body_to_range_ratio")
        ),
        "upper_wick_to_range": _feature_value(
            payload, ("candle", "upper_wick_to_range_ratio")
        ),
        "lower_wick_to_range": _feature_value(
            payload, ("candle", "lower_wick_to_range_ratio")
        ),
        "tick_volume_ratio20": _feature_value(
            payload, ("volume", "tick_volume_ratio20")
        ),
        "range5_position": _feature_value(
            payload, ("recent_ranges", "bars_5", "close_position_0_1")
        ),
        "range10_position": _feature_value(
            payload, ("recent_ranges", "bars_10", "close_position_0_1")
        ),
        "range20_position": _feature_value(
            payload, ("recent_ranges", "bars_20", "close_position_0_1")
        ),
        "range20_distance_high_bps": _feature_value(
            payload, ("recent_ranges", "bars_20", "distance_to_high_bps")
        ),
        "range20_distance_low_bps": _feature_value(
            payload, ("recent_ranges", "bars_20", "distance_to_low_bps")
        ),
    }

    close_price = float(_feature_value(payload, ("bar", "close")))
    atr14 = float(_feature_value(payload, ("volatility", "atr14")))
    for proxy_name in ("short", "medium"):
        proxy = _feature_value(payload, ("zigzag_proxies", proxy_name))
        latest = proxy.get("latest_pivot")
        high = proxy.get("latest_confirmed_high")
        low = proxy.get("latest_confirmed_low")
        features[f"{proxy_name}_latest_pivot_type"] = (
            "NONE" if latest is None else str(latest["type"])
        )
        features[f"{proxy_name}_latest_pivot_bars_ago"] = (
            None if latest is None else int(latest["pivot_bars_ago"])
        )
        features[f"{proxy_name}_high_distance_atr"] = (
            None if high is None else (float(high["price"]) - close_price) / atr14
        )
        features[f"{proxy_name}_low_distance_atr"] = (
            None if low is None else (close_price - float(low["price"])) / atr14
        )

    for period in (9, 14, 18):
        current = series.rci[period][index]
        previous = series.rci[period][index - 1] if index >= 1 else None
        previous2 = series.rci[period][index - 2] if index >= 2 else None
        if current is not None and previous is not None:
            features[f"rci{period}_delta1"] = float(current - previous)
            features[f"rci{period}_cross_up_minus80"] = bool(
                previous <= -80.0 < current
            )
            features[f"rci{period}_cross_down_plus80"] = bool(
                previous >= 80.0 > current
            )
        if current is not None and previous is not None and previous2 is not None:
            features[f"rci{period}_turn_up"] = bool(
                current > previous and previous <= previous2
            )
            features[f"rci{period}_turn_down"] = bool(
                current < previous and previous >= previous2
            )

    if index >= 1:
        current_hist = series.macd_histogram[index]
        previous_hist = series.macd_histogram[index - 1]
        features["macd_hist_delta1_bps"] = (
            (current_hist - previous_hist) / abs(series.bars[index].close_price) * 10000.0
        )
        features["macd_cross_up"] = bool(previous_hist <= 0.0 < current_hist)
        features["macd_cross_down"] = bool(previous_hist >= 0.0 > current_hist)
    if index >= 2:
        h0 = series.macd_histogram[index]
        h1 = series.macd_histogram[index - 1]
        h2 = series.macd_histogram[index - 2]
        features["macd_hist_turn_up"] = bool(h0 > h1 and h1 <= h2)
        features["macd_hist_turn_down"] = bool(h0 < h1 and h1 >= h2)

    for key, value in list(features.items()):
        if isinstance(value, float) and not math.isfinite(value):
            features[key] = None
    return features


def _event_map(events: list[AlertEvent]) -> dict[tuple[str, datetime], list[AlertEvent]]:
    output: dict[tuple[str, datetime], list[AlertEvent]] = defaultdict(list)
    for event in events:
        boundary = floor_15(event.bar_time_utc)
        if abs((event.bar_time_utc - boundary).total_seconds()) > 1e-9:
            raise TriggerSignatureContractError(
                f"alert bar time is not on a 15-minute boundary: {event.raw_id}"
            )
        output[(event.ticker, boundary)].append(event)
    for key, values in output.items():
        values.sort(key=lambda item: (item.fired_at_utc, item.raw_id))
        if len(values) > 1:
            raise TriggerSignatureContractError(
                f"multiple source events share one ticker/M15 boundary: {key}"
            )
    return output


def build_decision_samples(
    connection: sqlite3.Connection,
    *,
    mt5_files_root: Path,
    built_at_utc: str,
) -> tuple[list[DecisionSample], dict[str, Any]]:
    upstream = validate_upstream_coverage(connection)
    events = read_alert_events(connection)
    validate_event_roles(events)
    db_anomalies = int(
        connection.execute("SELECT COUNT(*) FROM episode_build_anomalies").fetchone()[0]
        or 0
    )
    if db_anomalies:
        raise TriggerSignatureContractError(
            f"Stage M3 contains {db_anomalies} sequence anomalies"
        )

    event_map = _event_map(events)
    by_ticker: dict[str, list[AlertEvent]] = defaultdict(list)
    for event in events:
        by_ticker[event.ticker].append(event)

    samples: list[DecisionSample] = []
    coverage: list[dict[str, Any]] = []
    for ticker in sorted(by_ticker):
        ticker_events = sorted(by_ticker[ticker], key=lambda item: (item.bar_time_utc, item.raw_id))
        offsets = sorted({round(item.selected_offset_hours, 9) for item in ticker_events})
        if len(offsets) != 1:
            raise TriggerSignatureContractError(
                f"multiple M15 offsets in current observation window for {ticker}: {offsets}; "
                "segment by DST before inference"
            )
        offset = offsets[0]
        start = min(floor_15(item.bar_time_utc) for item in ticker_events)
        end = max(floor_15(item.bar_time_utc) for item in ticker_events)
        series = load_indicator_series(mt5_files_root / FILE_MAP[ticker][TIMEFRAME])

        selected_indices: list[tuple[datetime, int, int]] = []
        for current_index in range(1, len(series.bars)):
            current_bar = series.bars[current_index]
            decision_time = current_bar.server_open - timedelta(hours=offset)
            if decision_time < start or decision_time > end:
                continue
            selected_index = current_index - 1
            previous_bar = series.bars[selected_index]
            previous_utc_close = (
                previous_bar.server_open - timedelta(hours=offset) + timedelta(minutes=15)
            )
            if previous_utc_close > decision_time:
                raise TriggerSignatureContractError(
                    f"previous M15 bar closes after current bar open for {ticker}"
                )
            if selected_index + 1 < MINIMUM_WARMUP_BARS:
                continue
            selected_indices.append((decision_time, selected_index, current_index))
        if not selected_indices:
            raise TriggerSignatureContractError(
                f"no causal M15 decisions available for {ticker}"
            )

        state = "IDLE"
        state_started_at: datetime | None = None
        last_event_time: datetime | None = None
        previous_transition = "NONE"
        matched_event_ids: list[int] = []
        for decision_time, index, current_index in selected_indices:
            bar = series.bars[index]
            current_bar = series.bars[current_index]
            payload = build_feature_payload(
                series,
                selected_index=index,
                ticker=ticker,
                timeframe=TIMEFRAME,
                source_filename=FILE_MAP[ticker][TIMEFRAME],
                decision_time_utc=decision_time,
                selected_utc_close=decision_time,
                selected_offset_hours=offset,
                built_at_utc=built_at_utc,
            )
            features = flatten_features(series, index, payload)
            atr14 = float(payload["volatility"]["atr14"])
            features["current_open_gap_atr"] = (
                current_bar.open_price - bar.close_price
            ) / atr14
            features["current_open_minus_ema20_atr"] = (
                current_bar.open_price - float(payload["ema"]["ema20"])
            ) / atr14
            features["current_open_minus_ema40_atr"] = (
                current_bar.open_price - float(payload["ema"]["ema40"])
            ) / atr14
            features["state_before"] = state
            features["previous_transition"] = previous_transition
            features["bars_since_last_event"] = (
                None
                if last_event_time is None
                else (decision_time - last_event_time).total_seconds() / 900.0
            )
            features["state_age_m15_bars"] = (
                0.0
                if state == "IDLE" or state_started_at is None
                else (decision_time - state_started_at).total_seconds() / 900.0
            )
            values = event_map.get((ticker, decision_time), [])
            state_before = state
            if not values:
                samples.append(
                    DecisionSample(
                        ticker=ticker,
                        decision_time_utc=decision_time,
                        selected_server_open=bar.server_open,
                        state_before=state_before,
                        transition="NO_EVENT",
                        raw_alert_id=None,
                        features=features,
                    )
                )
                continue
            event = values[0]
            if event.selected_server_open != bar.server_open:
                raise TriggerSignatureContractError(
                    f"M15 all-bar selection differs from audited event alignment for raw "
                    f"alert {event.raw_id}: {bar.server_open} != {event.selected_server_open}"
                )
            transition, state_after = transition_for(event, state_before)
            samples.append(
                DecisionSample(
                    ticker=ticker,
                    decision_time_utc=decision_time,
                    selected_server_open=bar.server_open,
                    state_before=state_before,
                    transition=transition,
                    raw_alert_id=event.raw_id,
                    features=features,
                )
            )
            matched_event_ids.append(event.raw_id)
            if state_before == "IDLE" and state_after in ("ACTIVE_LONG", "ACTIVE_SHORT"):
                state_started_at = decision_time
            elif state_after == "IDLE":
                state_started_at = None
            last_event_time = decision_time
            previous_transition = transition
            state = state_after

        expected_ids = [item.raw_id for item in ticker_events]
        if matched_event_ids != expected_ids:
            raise TriggerSignatureContractError(
                f"not all genuine events matched causal M15 decisions for {ticker}: "
                f"matched={matched_event_ids} expected={expected_ids}"
            )
        coverage.append(
            {
                "ticker": ticker,
                "offset_hours": offset,
                "observation_start_utc": iso_z(start),
                "observation_end_utc": iso_z(end),
                "decision_count": len(selected_indices),
                "event_count": len(ticker_events),
                "no_event_count": len(selected_indices) - len(ticker_events),
                "negative_labels_outside_observation_window_used": False,
            }
        )

    return samples, {
        **upstream,
        "eligible_event_count": len(events),
        "ticker_coverage": coverage,
    }


def _condition_key(condition: dict[str, Any]) -> tuple[Any, ...]:
    return (
        condition["feature"],
        condition["operator"],
        json.dumps(condition["value"], sort_keys=True),
    )


def _matches(features: dict[str, Any], condition: dict[str, Any]) -> bool:
    value = features.get(str(condition["feature"]))
    if value is None:
        return False
    operator = str(condition["operator"])
    target = condition["value"]
    if operator == "==":
        return value == target
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    if operator == "<=":
        return float(value) <= float(target)
    if operator == ">=":
        return float(value) >= float(target)
    raise ValueError(f"unsupported operator {operator}")


def _evaluate(
    rows: list[DecisionSample],
    target: str,
    conditions: list[dict[str, Any]],
) -> dict[str, Any]:
    positive_total = sum(1 for row in rows if row.transition == target)
    matched = [row for row in rows if all(_matches(row.features, c) for c in conditions)]
    matched_positive = sum(1 for row in matched if row.transition == target)
    matched_total = len(matched)
    eligible_total = len(rows)
    base_rate = positive_total / eligible_total if eligible_total else 0.0
    precision = matched_positive / matched_total if matched_total else 0.0
    recall = matched_positive / positive_total if positive_total else 0.0
    lift = precision / base_rate if base_rate > 0 else None
    f1 = (
        2.0 * precision * recall / (precision + recall)
        if precision + recall > 0
        else 0.0
    )
    score = f1 * math.log1p(lift or 0.0) * math.log1p(matched_positive)
    return {
        "conditions": conditions,
        "positive_total": positive_total,
        "eligible_total": eligible_total,
        "matched_total": matched_total,
        "matched_positive": matched_positive,
        "matched_control": matched_total - matched_positive,
        "precision": precision,
        "recall": recall,
        "base_rate": base_rate,
        "lift": lift,
        "f1": f1,
        "score": score,
    }


def _candidate_conditions(rows: list[DecisionSample], target: str) -> list[dict[str, Any]]:
    positives = [row for row in rows if row.transition == target]
    if not positives:
        return []
    keys = sorted({key for row in rows for key in row.features})
    output: dict[tuple[Any, ...], dict[str, Any]] = {}
    for key in keys:
        values = [row.features.get(key) for row in rows]
        present = [value for value in values if value is not None]
        if not present:
            continue
        if all(isinstance(value, bool) for value in present):
            for value in (True, False):
                condition = {"feature": key, "operator": "==", "value": value}
                output[_condition_key(condition)] = condition
            continue
        if all(isinstance(value, str) for value in present):
            for value in sorted(set(str(item) for item in present)):
                condition = {"feature": key, "operator": "==", "value": value}
                output[_condition_key(condition)] = condition
            continue
        numeric = [
            float(value)
            for value in present
            if isinstance(value, (int, float)) and not isinstance(value, bool)
        ]
        positive_numeric = [
            float(row.features[key])
            for row in positives
            if key in row.features
            and row.features[key] is not None
            and isinstance(row.features[key], (int, float))
            and not isinstance(row.features[key], bool)
        ]
        if not numeric or not positive_numeric:
            continue
        thresholds: set[float] = set()
        for q in NUMERIC_QUANTILES:
            thresholds.add(round(_quantile(numeric, q), 12))
            thresholds.add(round(_quantile(positive_numeric, q), 12))
        for threshold in sorted(thresholds):
            for operator in ("<=", ">="):
                condition = {
                    "feature": key,
                    "operator": operator,
                    "value": threshold,
                }
                output[_condition_key(condition)] = condition
    return list(output.values())


def _human_condition(condition: dict[str, Any]) -> str:
    value = condition["value"]
    if isinstance(value, float):
        text = f"{value:.6g}"
    else:
        text = str(value)
    return f"{condition['feature']} {condition['operator']} {text}"


def discover_rules(rows: list[DecisionSample], target: str) -> dict[str, Any]:
    positives = [row for row in rows if row.transition == target]
    positive_count = len(positives)
    eligible_count = len(rows)
    if positive_count == 0:
        return {
            "transition": target,
            "positive_count": 0,
            "eligible_decision_count": eligible_count,
            "status": "NO_POSITIVES",
            "top_single_rules": [],
            "top_pair_rules": [],
        }

    minimum_support = 1 if positive_count < 3 else max(2, math.ceil(positive_count * 0.35))
    singles: list[dict[str, Any]] = []
    for condition in _candidate_conditions(rows, target):
        result = _evaluate(rows, target, [condition])
        if result["matched_positive"] < minimum_support:
            continue
        result["rule_text"] = _human_condition(condition)
        singles.append(result)
    singles.sort(
        key=lambda item: (
            float(item["score"]),
            float(item["recall"]),
            float(item["precision"]),
            int(item["matched_positive"]),
        ),
        reverse=True,
    )
    singles = singles[:TOP_SINGLE_LIMIT]

    pair_source = singles[:TOP_PAIR_SOURCE_LIMIT]
    pairs: list[dict[str, Any]] = []
    seen_pairs: set[tuple[tuple[Any, ...], tuple[Any, ...]]] = set()
    for left_index, left in enumerate(pair_source):
        left_condition = left["conditions"][0]
        for right in pair_source[left_index + 1 :]:
            right_condition = right["conditions"][0]
            if left_condition["feature"] == right_condition["feature"]:
                continue
            key = tuple(sorted((_condition_key(left_condition), _condition_key(right_condition))))
            if key in seen_pairs:
                continue
            seen_pairs.add(key)
            result = _evaluate(rows, target, [left_condition, right_condition])
            if result["matched_positive"] < minimum_support:
                continue
            result["rule_text"] = " AND ".join(
                _human_condition(condition) for condition in result["conditions"]
            )
            pairs.append(result)
    pairs.sort(
        key=lambda item: (
            float(item["score"]),
            float(item["recall"]),
            float(item["precision"]),
            int(item["matched_positive"]),
        ),
        reverse=True,
    )
    pairs = pairs[:TOP_PAIR_LIMIT]

    best = pairs[0] if pairs else singles[0] if singles else None
    return {
        "transition": target,
        "positive_count": positive_count,
        "eligible_decision_count": eligible_count,
        "base_rate": positive_count / eligible_count if eligible_count else None,
        "minimum_positive_support": minimum_support,
        "status": "EXPLORATORY_ONLY" if positive_count >= 5 else "VERY_SMALL_SAMPLE",
        "top_single_rules": singles,
        "top_pair_rules": pairs,
        "best_exploratory_rule": best,
        "exact_internal_condition_identified": False,
        "historical_candidate_extraction_approved": False,
    }


def _eligible_rows(samples: list[DecisionSample], transition: str) -> list[DecisionSample]:
    required_state = ELIGIBLE_STATE[transition]
    return [row for row in samples if row.state_before == required_state]


def _feature_contrasts(rows: list[DecisionSample], target: str) -> list[dict[str, Any]]:
    positives = [row for row in rows if row.transition == target]
    controls = [row for row in rows if row.transition != target]
    keys = sorted({key for row in rows for key in row.features})
    output: list[dict[str, Any]] = []
    for key in keys:
        positive_values = [row.features.get(key) for row in positives]
        control_values = [row.features.get(key) for row in controls]
        p_present = [value for value in positive_values if value is not None]
        c_present = [value for value in control_values if value is not None]
        if not p_present or not c_present:
            continue
        if all(
            isinstance(value, (int, float)) and not isinstance(value, bool)
            for value in p_present + c_present
        ):
            p_numeric = [float(value) for value in p_present]
            c_numeric = [float(value) for value in c_present]
            output.append(
                {
                    "feature": key,
                    "type": "NUMERIC",
                    "positive_min": min(p_numeric),
                    "positive_median": _median(p_numeric),
                    "positive_max": max(p_numeric),
                    "control_median": _median(c_numeric),
                    "median_difference": (
                        (_median(p_numeric) or 0.0) - (_median(c_numeric) or 0.0)
                    ),
                }
            )
        else:
            p_counts: dict[str, int] = defaultdict(int)
            c_counts: dict[str, int] = defaultdict(int)
            for value in p_present:
                p_counts[str(value)] += 1
            for value in c_present:
                c_counts[str(value)] += 1
            output.append(
                {
                    "feature": key,
                    "type": "CATEGORICAL",
                    "positive_counts": dict(sorted(p_counts.items())),
                    "control_counts": dict(sorted(c_counts.items())),
                }
            )
    return output


def audit_trigger_signatures(
    connection: sqlite3.Connection,
    *,
    mt5_files_root: Path,
    built_at_utc: str,
) -> dict[str, Any]:
    samples, coverage = build_decision_samples(
        connection,
        mt5_files_root=mt5_files_root,
        built_at_utc=built_at_utc,
    )
    transition_reports: list[dict[str, Any]] = []
    event_rows: list[dict[str, Any]] = []
    rule_rows: list[dict[str, Any]] = []

    for sample in samples:
        if sample.transition == "NO_EVENT":
            continue
        event_rows.append(
            {
                "raw_alert_id": sample.raw_alert_id,
                "ticker": sample.ticker,
                "decision_time_utc": iso_z(sample.decision_time_utc),
                "selected_server_open": sample.selected_server_open.strftime(
                    "%Y.%m.%d %H:%M:%S"
                ),
                "state_before": sample.state_before,
                "transition": sample.transition,
                **sample.features,
            }
        )

    scopes: list[tuple[str, list[DecisionSample]]] = [("ALL", samples)]
    for ticker in sorted({sample.ticker for sample in samples}):
        scopes.append((ticker, [sample for sample in samples if sample.ticker == ticker]))

    for scope, scoped_samples in scopes:
        for transition in TRANSITIONS:
            eligible = _eligible_rows(scoped_samples, transition)
            report = discover_rules(eligible, transition)
            report["scope"] = scope
            report["feature_contrasts"] = _feature_contrasts(eligible, transition)
            transition_reports.append(report)
            for family in ("top_single_rules", "top_pair_rules"):
                for rank, item in enumerate(report.get(family, []), start=1):
                    rule_rows.append(
                        {
                            "scope": scope,
                            "transition": transition,
                            "rule_family": family,
                            "rank": rank,
                            "rule_text": item["rule_text"],
                            "matched_positive": item["matched_positive"],
                            "positive_total": item["positive_total"],
                            "matched_control": item["matched_control"],
                            "eligible_total": item["eligible_total"],
                            "precision": item["precision"],
                            "recall": item["recall"],
                            "lift": item["lift"],
                            "f1": item["f1"],
                            "score": item["score"],
                        }
                    )

    transition_counts: dict[str, int] = defaultdict(int)
    state_counts: dict[str, int] = defaultdict(int)
    for sample in samples:
        transition_counts[sample.transition] += 1
        state_counts[sample.state_before] += 1

    return {
        "contract_version": CONTRACT_VERSION,
        **coverage,
        "decision_sample_count": len(samples),
        "event_decision_count": sum(
            1 for sample in samples if sample.transition != "NO_EVENT"
        ),
        "no_event_decision_count": sum(
            1 for sample in samples if sample.transition == "NO_EVENT"
        ),
        "transition_counts": [
            {"transition": key, "count": transition_counts.get(key, 0)}
            for key in (*TRANSITIONS, "NO_EVENT")
        ],
        "state_before_counts": [
            {"state": key, "count": state_counts[key]} for key in sorted(state_counts)
        ],
        "transition_reports": transition_reports,
        "event_feature_rows": event_rows,
        "candidate_rule_rows": rule_rows,
        "inference_contract": {
            "positive_labels": "genuine Webhook/SQLite events only",
            "negative_labels": (
                "M15 decision boundaries only inside each ticker's first-to-last "
                "genuine event observation window"
            ),
            "decision_feature_cutoff": "last fully closed MT5 M15 bar",
            "alert_bar_ohlc_used": False,
            "future_bars_used": False,
            "event_state_is_part_of_eligibility": True,
            "exact_proprietary_logic_claimed": False,
            "independent_proxy_only": True,
        },
        "sample_size_warning": (
            "Current transition samples are small. Rules are discovery signatures, "
            "not approved replay detectors. Freeze and validate on later genuine "
            "events before historical or cross-timeframe candidate extraction."
        ),
        "historical_scan_approved": False,
        "cross_timeframe_scan_approved": False,
        "automatic_trading_rule_approved": False,
        "event_csv_rows": event_rows,
        "rule_csv_rows": rule_rows,
    }


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames: list[str] = []
    seen: set[str] = set()
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
