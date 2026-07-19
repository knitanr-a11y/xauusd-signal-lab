from __future__ import annotations

import csv
import hashlib
import json
import math
import sqlite3
import statistics
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from mt5_csv_contract import (
    EXPECTED_HEADER,
    FILE_MAP,
    TIMEFRAME_SECONDS,
    parse_mt5_time,
    parse_utc,
)

FEATURE_CONTRACT_VERSION = "MOCHIPOYO_M5_CAUSAL_FEATURES_V1"
FEATURE_TIMEFRAMES = ("M5", "M15", "H1", "H4", "D1")
EMA_PERIODS = (20, 30, 40)
RCI_PERIODS = (9, 14, 18)
RECENT_WINDOWS = (5, 10, 20)
MINIMUM_WARMUP_BARS = 50
ZIGZAG_PROXY_SETTINGS = {
    "short": {
        "depth": 5,
        "deviation_reference": 3,
        "right_confirmation_bars": 2,
    },
    "medium": {
        "depth": 12,
        "deviation_reference": 5,
        "right_confirmation_bars": 3,
    },
}


class FeatureContractError(RuntimeError):
    pass


@dataclass(frozen=True)
class Bar:
    server_open: datetime
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    tick_volume: int
    spread: int
    real_volume: int
    prefix_sha256: str


@dataclass
class IndicatorSeries:
    bars: list[Bar]
    index_by_server_open: dict[datetime, int]
    ema: dict[int, list[float]]
    rci: dict[int, list[float | None]]
    true_range: list[float]
    atr14: list[float | None]
    macd_line: list[float]
    macd_signal: list[float]
    macd_histogram: list[float]


def _canonical_bar_text(row: dict[str, str]) -> str:
    return "|".join(str(row[name]).strip() for name in EXPECTED_HEADER)


def _ema(values: list[float], period: int) -> list[float]:
    if not values:
        return []
    alpha = 2.0 / (period + 1.0)
    result = [values[0]]
    for value in values[1:]:
        result.append(alpha * value + (1.0 - alpha) * result[-1])
    return result


def _average_ranks(values: list[float]) -> list[float]:
    indexed = sorted(enumerate(values), key=lambda item: item[1])
    ranks = [0.0] * len(values)
    cursor = 0
    while cursor < len(indexed):
        end = cursor + 1
        while end < len(indexed) and indexed[end][1] == indexed[cursor][1]:
            end += 1
        average_rank = ((cursor + 1) + end) / 2.0
        for position in range(cursor, end):
            ranks[indexed[position][0]] = average_rank
        cursor = end
    return ranks


def rci_value(values: list[float]) -> float:
    length = len(values)
    if length < 2:
        raise ValueError("RCI requires at least two values")
    price_ranks = _average_ranks(values)
    denominator = length * (length * length - 1)
    squared_difference = sum(
        ((index + 1) - price_ranks[index]) ** 2 for index in range(length)
    )
    return (1.0 - 6.0 * squared_difference / denominator) * 100.0


def _rci_series(values: list[float], period: int) -> list[float | None]:
    result: list[float | None] = [None] * len(values)
    for index in range(period - 1, len(values)):
        result[index] = rci_value(values[index - period + 1 : index + 1])
    return result


def _true_range_and_atr14(
    bars: list[Bar],
) -> tuple[list[float], list[float | None]]:
    true_range: list[float] = []
    for index, bar in enumerate(bars):
        if index == 0:
            value = bar.high_price - bar.low_price
        else:
            previous_close = bars[index - 1].close_price
            value = max(
                bar.high_price - bar.low_price,
                abs(bar.high_price - previous_close),
                abs(bar.low_price - previous_close),
            )
        true_range.append(value)

    period = 14
    atr: list[float | None] = [None] * len(bars)
    if len(true_range) >= period:
        atr[period - 1] = sum(true_range[:period]) / period
        for index in range(period, len(true_range)):
            previous = atr[index - 1]
            assert previous is not None
            atr[index] = ((period - 1) * previous + true_range[index]) / period
    return true_range, atr


def load_indicator_series(path: Path) -> IndicatorSeries:
    bars: list[Bar] = []
    index_by_server_open: dict[datetime, int] = {}
    rolling_digest = b""
    previous_time: datetime | None = None

    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != EXPECTED_HEADER:
            raise FeatureContractError(f"unexpected header for {path.name}")
        for line_number, row in enumerate(reader, start=2):
            try:
                server_open = parse_mt5_time(row["time"])
                if previous_time is not None and server_open <= previous_time:
                    raise ValueError("timestamp is not strictly ascending")
                previous_time = server_open
                canonical = _canonical_bar_text(row).encode("utf-8")
                rolling_digest = hashlib.sha256(
                    rolling_digest + b"\n" + canonical
                ).digest()
                bar = Bar(
                    server_open=server_open,
                    open_price=float(row["open"]),
                    high_price=float(row["high"]),
                    low_price=float(row["low"]),
                    close_price=float(row["close"]),
                    tick_volume=int(row["tick_volume"]),
                    spread=int(row["spread"]),
                    real_volume=int(row["real_volume"]),
                    prefix_sha256=rolling_digest.hex(),
                )
            except Exception as exc:
                raise FeatureContractError(
                    f"invalid row in {path.name} at CSV line {line_number}"
                ) from exc
            index_by_server_open[server_open] = len(bars)
            bars.append(bar)

    if not bars:
        raise FeatureContractError(f"CSV has no data rows: {path.name}")

    closes = [bar.close_price for bar in bars]
    ema = {period: _ema(closes, period) for period in EMA_PERIODS}
    rci = {period: _rci_series(closes, period) for period in RCI_PERIODS}
    true_range, atr14 = _true_range_and_atr14(bars)
    ema6 = _ema(closes, 6)
    ema13 = _ema(closes, 13)
    macd_line = [fast - slow for fast, slow in zip(ema6, ema13)]
    macd_signal = _ema(macd_line, 4)
    macd_histogram = [
        line - signal for line, signal in zip(macd_line, macd_signal)
    ]
    return IndicatorSeries(
        bars=bars,
        index_by_server_open=index_by_server_open,
        ema=ema,
        rci=rci,
        true_range=true_range,
        atr14=atr14,
        macd_line=macd_line,
        macd_signal=macd_signal,
        macd_histogram=macd_histogram,
    )


def _safe_ratio(numerator: float, denominator: float) -> float | None:
    if abs(denominator) <= 1e-12:
        return None
    return numerator / denominator


def _bps(value: float, reference: float) -> float | None:
    ratio = _safe_ratio(value, abs(reference))
    return None if ratio is None else ratio * 10000.0


def _pivot_candidate(
    bars: list[Bar],
    confirmation_index: int,
    *,
    depth: int,
    right_bars: int,
) -> dict[str, Any] | None:
    pivot_index = confirmation_index - right_bars
    start = pivot_index - depth + 1
    if start < 0:
        return None
    window = bars[start : confirmation_index + 1]
    pivot = bars[pivot_index]
    highs = [bar.high_price for bar in window]
    lows = [bar.low_price for bar in window]
    is_high = pivot.high_price == max(highs) and highs.count(pivot.high_price) == 1
    is_low = pivot.low_price == min(lows) and lows.count(pivot.low_price) == 1
    if is_high == is_low:
        return None
    return {
        "type": "HIGH" if is_high else "LOW",
        "price": pivot.high_price if is_high else pivot.low_price,
        "pivot_index": pivot_index,
        "confirmation_index": confirmation_index,
        "pivot_server_open": pivot.server_open.strftime("%Y.%m.%d %H:%M:%S"),
        "confirmed_server_open": bars[confirmation_index].server_open.strftime(
            "%Y.%m.%d %H:%M:%S"
        ),
    }


def _latest_pivots(
    bars: list[Bar],
    selected_index: int,
    *,
    depth: int,
    right_bars: int,
) -> dict[str, Any]:
    latest_any: dict[str, Any] | None = None
    latest_high: dict[str, Any] | None = None
    latest_low: dict[str, Any] | None = None
    minimum_confirmation = depth - 1 + right_bars
    for confirmation_index in range(
        selected_index,
        minimum_confirmation - 1,
        -1,
    ):
        candidate = _pivot_candidate(
            bars,
            confirmation_index,
            depth=depth,
            right_bars=right_bars,
        )
        if candidate is None:
            continue
        candidate = dict(candidate)
        candidate["pivot_bars_ago"] = selected_index - int(
            candidate["pivot_index"]
        )
        candidate["confirmation_bars_ago"] = selected_index - int(
            candidate["confirmation_index"]
        )
        candidate.pop("pivot_index")
        candidate.pop("confirmation_index")
        if latest_any is None:
            latest_any = candidate
        if candidate["type"] == "HIGH" and latest_high is None:
            latest_high = candidate
        if candidate["type"] == "LOW" and latest_low is None:
            latest_low = candidate
        if (
            latest_any is not None
            and latest_high is not None
            and latest_low is not None
        ):
            break
    return {
        "latest_pivot": latest_any,
        "latest_confirmed_high": latest_high,
        "latest_confirmed_low": latest_low,
    }


def _recent_range(
    series: IndicatorSeries,
    selected_index: int,
    window: int,
) -> dict[str, Any]:
    start = max(0, selected_index - window + 1)
    selected = series.bars[start : selected_index + 1]
    highest = max(bar.high_price for bar in selected)
    lowest = min(bar.low_price for bar in selected)
    close = series.bars[selected_index].close_price
    width = highest - lowest
    return {
        "window_bars": window,
        "highest_high": highest,
        "lowest_low": lowest,
        "range": width,
        "range_bps": _bps(width, close),
        "close_position_0_1": _safe_ratio(close - lowest, width),
        "distance_to_high_bps": _bps(highest - close, close),
        "distance_to_low_bps": _bps(close - lowest, close),
    }


def build_feature_payload(
    series: IndicatorSeries,
    *,
    selected_index: int,
    ticker: str,
    timeframe: str,
    source_filename: str,
    decision_time_utc: datetime,
    selected_utc_close: datetime,
    selected_offset_hours: float,
    built_at_utc: str,
) -> dict[str, Any]:
    bar = series.bars[selected_index]
    selected_utc_open = selected_utc_close - timedelta(
        seconds=TIMEFRAME_SECONDS[timeframe]
    )
    if selected_utc_close > decision_time_utc:
        raise FeatureContractError("selected feature bar closes after decision time")

    atr14 = series.atr14[selected_index]
    if atr14 is None:
        raise FeatureContractError(
            f"ATR warmup is insufficient for {ticker} {timeframe} "
            f"at {bar.server_open}"
        )
    rci_values = {
        period: series.rci[period][selected_index] for period in RCI_PERIODS
    }
    if any(value is None for value in rci_values.values()):
        raise FeatureContractError(
            f"RCI warmup is insufficient for {ticker} {timeframe} "
            f"at {bar.server_open}"
        )

    ema20 = series.ema[20][selected_index]
    ema30 = series.ema[30][selected_index]
    ema40 = series.ema[40][selected_index]
    if ema20 > ema30 > ema40:
        ema_alignment = "BULLISH_STACK"
    elif ema20 < ema30 < ema40:
        ema_alignment = "BEARISH_STACK"
    else:
        ema_alignment = "MIXED"
    ema_spread = max(ema20, ema30, ema40) - min(ema20, ema30, ema40)

    candle_range = bar.high_price - bar.low_price
    body = bar.close_price - bar.open_price
    upper_wick = bar.high_price - max(bar.open_price, bar.close_price)
    lower_wick = min(bar.open_price, bar.close_price) - bar.low_price

    slope_lookback = 3
    slope_index = max(0, selected_index - slope_lookback)
    macd_line = series.macd_line[selected_index]
    macd_signal = series.macd_signal[selected_index]
    macd_histogram = series.macd_histogram[selected_index]

    tick_start = max(0, selected_index - 19)
    tick_values = [
        item.tick_volume
        for item in series.bars[tick_start : selected_index + 1]
    ]
    tick_mean20 = sum(tick_values) / len(tick_values)

    zigzag_proxies: dict[str, Any] = {}
    for name, settings in ZIGZAG_PROXY_SETTINGS.items():
        pivot_data = _latest_pivots(
            series.bars,
            selected_index,
            depth=int(settings["depth"]),
            right_bars=int(settings["right_confirmation_bars"]),
        )
        zigzag_proxies[name] = {
            "settings_reference": {
                "depth": int(settings["depth"]),
                "deviation": int(settings["deviation_reference"]),
                "backstep": int(settings["right_confirmation_bars"]),
            },
            "method": "INDEPENDENT_CAUSAL_CONFIRMED_PIVOT_PROXY",
            "deviation_rule_applied": False,
            "deviation_note": (
                "The proprietary/MT5 point-based deviation rule is not assumed. "
                "Depth and delayed confirmation are retained as an independent proxy."
            ),
            "future_relative_to_decision_used": False,
            **pivot_data,
        }

    return {
        "contract": {
            "version": FEATURE_CONTRACT_VERSION,
            "audit_only": True,
            "independent_analysis": True,
            "proprietary_indicator_reconstruction": False,
            "closed_bars_only": True,
            "future_relative_to_decision_used": False,
            "entry_gate_enabled": False,
            "ema_alignment_is_gate": False,
            "all_indicators_required": False,
            "ema_method": (
                "recursive alpha=2/(period+1), seeded with first close"
            ),
            "atr_method": "Wilder ATR14 seeded by first 14 true ranges",
            "rci_method": (
                "Spearman rank correlation with average ranks for ties"
            ),
            "macd_method": "EMA6 - EMA13, signal EMA4, close",
        },
        "identity": {
            "ticker": ticker,
            "timeframe": timeframe,
            "source_csv": source_filename,
            "selected_server_open": bar.server_open.strftime(
                "%Y.%m.%d %H:%M:%S"
            ),
            "selected_estimated_utc_open": selected_utc_open.strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            ),
            "selected_estimated_utc_close": selected_utc_close.strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            ),
            "decision_time_utc": decision_time_utc.strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            ),
            "selected_offset_hours": selected_offset_hours,
            "bar_age_seconds": (
                decision_time_utc - selected_utc_close
            ).total_seconds(),
            "history_prefix_sha256": bar.prefix_sha256,
            "built_at_utc": built_at_utc,
        },
        "bar": {
            "open": bar.open_price,
            "high": bar.high_price,
            "low": bar.low_price,
            "close": bar.close_price,
            "tick_volume": bar.tick_volume,
            "spread": bar.spread,
            "real_volume": bar.real_volume,
        },
        "ema": {
            "ema20": ema20,
            "ema30": ema30,
            "ema40": ema40,
            "alignment": ema_alignment,
            "spread": ema_spread,
            "spread_bps": _bps(ema_spread, bar.close_price),
            "spread_atr_ratio": _safe_ratio(ema_spread, atr14),
            "close_minus_ema20_bps": _bps(
                bar.close_price - ema20,
                bar.close_price,
            ),
            "close_minus_ema30_bps": _bps(
                bar.close_price - ema30,
                bar.close_price,
            ),
            "close_minus_ema40_bps": _bps(
                bar.close_price - ema40,
                bar.close_price,
            ),
            "ema20_slope_3_bars_bps": _bps(
                ema20 - series.ema[20][slope_index],
                bar.close_price,
            ),
            "ema30_slope_3_bars_bps": _bps(
                ema30 - series.ema[30][slope_index],
                bar.close_price,
            ),
            "ema40_slope_3_bars_bps": _bps(
                ema40 - series.ema[40][slope_index],
                bar.close_price,
            ),
        },
        "rci": {
            "rci9": float(rci_values[9]),
            "rci14": float(rci_values[14]),
            "rci18": float(rci_values[18]),
            "rci9_overbought_80": float(rci_values[9]) >= 80.0,
            "rci9_oversold_minus80": float(rci_values[9]) <= -80.0,
            "rci14_overbought_80": float(rci_values[14]) >= 80.0,
            "rci14_oversold_minus80": float(rci_values[14]) <= -80.0,
            "rci18_overbought_80": float(rci_values[18]) >= 80.0,
            "rci18_oversold_minus80": float(rci_values[18]) <= -80.0,
        },
        "macd": {
            "fast": 6,
            "slow": 13,
            "signal_period": 4,
            "line": macd_line,
            "signal": macd_signal,
            "histogram": macd_histogram,
            "line_bps": _bps(macd_line, bar.close_price),
            "signal_bps": _bps(macd_signal, bar.close_price),
            "histogram_bps": _bps(macd_histogram, bar.close_price),
            "zero_proximity_atr_ratio": _safe_ratio(abs(macd_line), atr14),
        },
        "volatility": {
            "true_range": series.true_range[selected_index],
            "atr14": atr14,
            "atr14_bps": _bps(atr14, bar.close_price),
            "bar_range": candle_range,
            "bar_range_atr_ratio": _safe_ratio(candle_range, atr14),
        },
        "candle": {
            "direction": (
                "UP" if body > 0 else "DOWN" if body < 0 else "DOJI"
            ),
            "body": body,
            "body_abs": abs(body),
            "body_to_range_ratio": _safe_ratio(abs(body), candle_range),
            "upper_wick": upper_wick,
            "upper_wick_to_range_ratio": _safe_ratio(
                upper_wick,
                candle_range,
            ),
            "lower_wick": lower_wick,
            "lower_wick_to_range_ratio": _safe_ratio(
                lower_wick,
                candle_range,
            ),
        },
        "volume": {
            "tick_volume": bar.tick_volume,
            "tick_volume_mean20": tick_mean20,
            "tick_volume_ratio20": _safe_ratio(
                bar.tick_volume,
                tick_mean20,
            ),
        },
        "recent_ranges": {
            f"bars_{window}": _recent_range(
                series,
                selected_index,
                window,
            )
            for window in RECENT_WINDOWS
        },
        "zigzag_proxies": zigzag_proxies,
        "quality": {
            "selected_bar_index": selected_index,
            "bars_available_including_selected": selected_index + 1,
            "minimum_warmup_bars": MINIMUM_WARMUP_BARS,
            "warmup_sufficient": selected_index + 1 >= MINIMUM_WARMUP_BARS,
            "selected_bar_matches_alignment": True,
            "future_fields_present": False,
        },
    }


def ensure_feature_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_mochipoyo_feature_source_timeframe
        ON feature_snapshots (source_event_id, timeframe);

        CREATE INDEX IF NOT EXISTS idx_mochipoyo_feature_episode_timeframe
        ON feature_snapshots (episode_id, timeframe);

        CREATE TABLE IF NOT EXISTS feature_build_runs (
            build_id INTEGER PRIMARY KEY AUTOINCREMENT,
            built_at_utc TEXT NOT NULL,
            feature_contract_version TEXT NOT NULL,
            eligible_alert_count INTEGER NOT NULL,
            timeframe_count INTEGER NOT NULL,
            expected_snapshot_count INTEGER NOT NULL,
            snapshot_count INTEGER NOT NULL,
            warmup_insufficient_count INTEGER NOT NULL,
            future_violation_count INTEGER NOT NULL,
            audit_only INTEGER NOT NULL CHECK (audit_only = 1),
            future_entry_fields_used INTEGER NOT NULL
                CHECK (future_entry_fields_used = 0)
        );

        CREATE TRIGGER IF NOT EXISTS trg_mochipoyo_episode_delete_features
        BEFORE DELETE ON episodes
        BEGIN
            DELETE FROM feature_snapshots WHERE episode_id = OLD.episode_id;
        END;

        CREATE TRIGGER IF NOT EXISTS trg_mochipoyo_alignment_delete_features
        BEFORE DELETE ON mt5_alignment
        BEGIN
            DELETE FROM feature_snapshots
            WHERE source_event_id = OLD.raw_alert_id
              AND timeframe = OLD.timeframe;
        END;
        """
    )
    connection.commit()


def _alignment_rows(connection: sqlite3.Connection) -> list[sqlite3.Row]:
    return connection.execute(
        """
        SELECT
            a.raw_alert_id,
            a.timeframe,
            a.tv_event_time_utc,
            a.mt5_server_time,
            a.estimated_mt5_time_utc,
            a.selected_offset_hours,
            a.mt5_close_price,
            a.alignment_status,
            a.diagnostics_json,
            r.ticker,
            r.event,
            ee.episode_id,
            ee.event_role
        FROM mt5_alignment a
        JOIN raw_alerts r ON r.cloudflare_id = a.raw_alert_id
        LEFT JOIN episode_events ee ON ee.raw_alert_id = a.raw_alert_id
        ORDER BY a.raw_alert_id, a.timeframe
        """
    ).fetchall()


def rebuild_feature_snapshots(
    connection: sqlite3.Connection,
    *,
    mt5_files_root: Path,
    built_at_utc: str,
) -> dict[str, Any]:
    ensure_feature_schema(connection)
    alignments = _alignment_rows(connection)
    if not alignments:
        raise FeatureContractError(
            "mt5_alignment is empty; run Stage M4 closed-bar alignment first"
        )
    duplicate_keys = {
        (int(row["raw_alert_id"]), str(row["timeframe"]))
        for row in alignments
    }
    if len(duplicate_keys) != len(alignments):
        raise FeatureContractError("duplicate MT5 alignment rows are present")

    eligible_alert_count = len(
        {int(row["raw_alert_id"]) for row in alignments}
    )
    expected_count = eligible_alert_count * len(FEATURE_TIMEFRAMES)
    if len(alignments) != expected_count:
        raise FeatureContractError(
            f"alignment coverage is incomplete: "
            f"{len(alignments)} != {expected_count}"
        )

    series_cache: dict[tuple[str, str], IndicatorSeries] = {}
    insert_rows: list[tuple[Any, ...]] = []
    warmup_insufficient_count = 0
    future_violation_count = 0
    role_counts: dict[str, int] = {}
    timeframe_counts: dict[str, int] = {}

    for row in alignments:
        raw_alert_id = int(row["raw_alert_id"])
        ticker = str(row["ticker"])
        timeframe = str(row["timeframe"])
        if timeframe not in FEATURE_TIMEFRAMES:
            raise FeatureContractError(
                f"unexpected alignment timeframe: {timeframe}"
            )
        if str(row["alignment_status"]) != "ALIGNED_CLOSED_BAR":
            raise FeatureContractError(
                f"alignment {raw_alert_id}/{timeframe} is not "
                "ALIGNED_CLOSED_BAR"
            )
        if row["episode_id"] is None or row["event_role"] is None:
            raise FeatureContractError(
                f"eligible alert {raw_alert_id} is not mapped to an episode"
            )
        episode_id = str(row["episode_id"])
        event_role = str(row["event_role"])

        cache_key = (ticker, timeframe)
        if cache_key not in series_cache:
            filename = FILE_MAP[ticker][timeframe]
            series_cache[cache_key] = load_indicator_series(
                mt5_files_root / filename
            )
        series = series_cache[cache_key]

        server_open = parse_mt5_time(str(row["mt5_server_time"]))
        selected_index = series.index_by_server_open.get(server_open)
        if selected_index is None:
            raise FeatureContractError(
                "selected alignment bar disappeared from "
                f"{FILE_MAP[ticker][timeframe]}: {row['mt5_server_time']}"
            )
        selected_bar = series.bars[selected_index]
        stored_close = float(row["mt5_close_price"])
        if not math.isclose(
            selected_bar.close_price,
            stored_close,
            rel_tol=0.0,
            abs_tol=1e-9,
        ):
            raise FeatureContractError(
                "selected bar close changed after Stage M4 for "
                f"{raw_alert_id}/{timeframe}"
            )
        diagnostics = json.loads(str(row["diagnostics_json"]))
        stored_ohlc = diagnostics.get("ohlc", {})
        for key, current in (
            ("open", selected_bar.open_price),
            ("high", selected_bar.high_price),
            ("low", selected_bar.low_price),
            ("close", selected_bar.close_price),
        ):
            if key not in stored_ohlc or not math.isclose(
                float(stored_ohlc[key]),
                current,
                rel_tol=0.0,
                abs_tol=1e-9,
            ):
                raise FeatureContractError(
                    "selected bar OHLC changed after Stage M4 for "
                    f"{raw_alert_id}/{timeframe}/{key}"
                )

        decision_time_utc = parse_utc(str(row["tv_event_time_utc"]))
        selected_utc_close = parse_utc(
            str(row["estimated_mt5_time_utc"])
        )
        if selected_utc_close > decision_time_utc:
            future_violation_count += 1
            raise FeatureContractError(
                f"future bar selected for {raw_alert_id}/{timeframe}"
            )
        if selected_index + 1 < MINIMUM_WARMUP_BARS:
            warmup_insufficient_count += 1
            raise FeatureContractError(
                f"warmup is insufficient for {raw_alert_id}/{timeframe}"
            )

        payload = build_feature_payload(
            series,
            selected_index=selected_index,
            ticker=ticker,
            timeframe=timeframe,
            source_filename=FILE_MAP[ticker][timeframe],
            decision_time_utc=decision_time_utc,
            selected_utc_close=selected_utc_close,
            selected_offset_hours=float(row["selected_offset_hours"]),
            built_at_utc=built_at_utc,
        )
        payload["source_event"] = {
            "raw_alert_id": raw_alert_id,
            "event": str(row["event"]),
            "episode_id": episode_id,
            "event_role": event_role,
        }
        if payload["quality"]["future_fields_present"]:
            future_violation_count += 1
            raise FeatureContractError("feature payload contains future fields")

        snapshot_id = (
            f"{FEATURE_CONTRACT_VERSION}:{raw_alert_id}:{timeframe}"
        )
        insert_rows.append(
            (
                snapshot_id,
                raw_alert_id,
                episode_id,
                decision_time_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
                decision_time_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
                timeframe,
                selected_utc_close.strftime("%Y-%m-%dT%H:%M:%SZ"),
                json.dumps(
                    payload,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                    allow_nan=False,
                ),
                0,
            )
        )
        role_counts[event_role] = role_counts.get(event_role, 0) + 1
        timeframe_counts[timeframe] = timeframe_counts.get(timeframe, 0) + 1

    if len(insert_rows) != expected_count:
        raise FeatureContractError(
            "feature snapshot coverage is incomplete: "
            f"{len(insert_rows)} != {expected_count}"
        )

    connection.execute("BEGIN IMMEDIATE")
    try:
        connection.execute("DELETE FROM feature_snapshots")
        connection.executemany(
            """
            INSERT INTO feature_snapshots (
                snapshot_id,
                source_event_id,
                episode_id,
                snapshot_time_utc,
                knowledge_cutoff_utc,
                timeframe,
                latest_closed_bar_time,
                features_json,
                future_fields_present
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            insert_rows,
        )
        connection.execute(
            """
            INSERT INTO feature_build_runs (
                built_at_utc,
                feature_contract_version,
                eligible_alert_count,
                timeframe_count,
                expected_snapshot_count,
                snapshot_count,
                warmup_insufficient_count,
                future_violation_count,
                audit_only,
                future_entry_fields_used
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, 0)
            """,
            (
                built_at_utc,
                FEATURE_CONTRACT_VERSION,
                eligible_alert_count,
                len(FEATURE_TIMEFRAMES),
                expected_count,
                len(insert_rows),
                warmup_insufficient_count,
                future_violation_count,
            ),
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise

    return {
        "feature_contract_version": FEATURE_CONTRACT_VERSION,
        "eligible_alert_count": eligible_alert_count,
        "timeframe_count": len(FEATURE_TIMEFRAMES),
        "timeframes": list(FEATURE_TIMEFRAMES),
        "expected_snapshot_count": expected_count,
        "snapshot_count": len(insert_rows),
        "warmup_insufficient_count": warmup_insufficient_count,
        "future_violation_count": future_violation_count,
        "by_timeframe": [
            {
                "timeframe": timeframe,
                "snapshot_count": timeframe_counts.get(timeframe, 0),
            }
            for timeframe in FEATURE_TIMEFRAMES
        ],
        "by_event_role": [
            {
                "event_role": role,
                "snapshot_count": role_counts[role],
            }
            for role in sorted(role_counts)
        ],
        "indicator_contract": {
            "ema": [20, 30, 40],
            "rci": [9, 14, 18],
            "macd": {
                "fast": 6,
                "slow": 13,
                "signal": 4,
                "source": "close",
            },
            "atr": 14,
            "recent_ranges": list(RECENT_WINDOWS),
            "zigzag_proxies": ZIGZAG_PROXY_SETTINGS,
            "zigzag_is_proprietary_clone": False,
            "zigzag_future_relative_to_decision_used": False,
        },
    }
