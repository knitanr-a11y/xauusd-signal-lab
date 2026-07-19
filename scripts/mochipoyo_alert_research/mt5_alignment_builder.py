from __future__ import annotations

import csv
import json
import math
import sqlite3
import statistics
from bisect import bisect_right
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from mt5_csv_contract import (
    EXPECTED_HEADER,
    FILE_MAP,
    TIMEFRAME_SECONDS,
    load_m1_bars,
    parse_mt5_time,
    parse_utc,
    provisional_offset,
    score_offsets,
)

CONTEXT_TIMEFRAMES = ("M5", "M15", "H1", "H4", "D1")


class AlignmentContractError(RuntimeError):
    pass


@dataclass(frozen=True)
class ClosedBar:
    server_open: datetime
    utc_open: datetime
    utc_close: datetime
    open_price: float
    high_price: float
    low_price: float
    close_price: float


def iso_z(value: datetime) -> str:
    return value.strftime("%Y-%m-%dT%H:%M:%SZ")


def load_closed_bars(
    path: Path,
    *,
    timeframe: str,
    offset_hours: int,
) -> tuple[list[datetime], list[ClosedBar]]:
    utc_closes: list[datetime] = []
    bars: list[ClosedBar] = []
    previous_server_open: datetime | None = None

    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != EXPECTED_HEADER:
            raise AlignmentContractError(f"unexpected header for {path.name}")

        for line_number, row in enumerate(reader, start=2):
            try:
                server_open = parse_mt5_time(row["time"])
                open_price = float(row["open"])
                high_price = float(row["high"])
                low_price = float(row["low"])
                close_price = float(row["close"])
            except Exception as exc:
                raise AlignmentContractError(
                    f"invalid row in {path.name} at CSV line {line_number}"
                ) from exc

            if (
                previous_server_open is not None
                and server_open <= previous_server_open
            ):
                raise AlignmentContractError(
                    f"non-ascending timestamp in {path.name} at CSV line {line_number}"
                )
            previous_server_open = server_open

            utc_open = server_open - timedelta(hours=offset_hours)
            utc_close = utc_open + timedelta(
                seconds=TIMEFRAME_SECONDS[timeframe]
            )
            bar = ClosedBar(
                server_open=server_open,
                utc_open=utc_open,
                utc_close=utc_close,
                open_price=open_price,
                high_price=high_price,
                low_price=low_price,
                close_price=close_price,
            )
            utc_closes.append(utc_close)
            bars.append(bar)

    if not bars:
        raise AlignmentContractError(f"CSV has no data rows: {path.name}")
    return utc_closes, bars


def select_latest_closed_bar(
    utc_closes: list[datetime],
    bars: list[ClosedBar],
    decision_time_utc: datetime,
) -> ClosedBar | None:
    index = bisect_right(utc_closes, decision_time_utc) - 1
    return None if index < 0 else bars[index]


def validate_offset_for_alignment(
    scores: list[dict[str, Any]],
    selected: dict[str, Any],
    *,
    eligible_alert_count: int,
) -> tuple[int, dict[str, Any]]:
    if (
        selected.get("status") != "PROVISIONAL"
        or selected.get("offset_hours") is None
    ):
        raise AlignmentContractError(f"broker offset is unresolved: {selected}")

    best = scores[0]
    second = scores[1] if len(scores) > 1 else None
    matched_count = int(best["matched_m1_count"])
    best_hit_count = int(best["price_range_hit_count"])
    hit_ratio = float(best["price_range_hit_ratio"])
    second_hit_count = (
        int(second["price_range_hit_count"]) if second is not None else 0
    )
    required_matched_count = max(5, math.ceil(eligible_alert_count * 0.80))
    required_hit_lead = max(3, math.ceil(matched_count * 0.20))

    if matched_count < required_matched_count:
        raise AlignmentContractError(
            "M1 coverage is insufficient for closed-bar alignment"
        )
    if hit_ratio < 0.90:
        raise AlignmentContractError(
            f"best broker offset hit ratio is below 0.90: {hit_ratio:.3f}"
        )
    if best_hit_count - second_hit_count < required_hit_lead:
        raise AlignmentContractError(
            "best broker offset does not lead the second candidate sufficiently"
        )

    for ticker_result in best.get("by_ticker", []):
        ticker_matched = int(ticker_result["matched_m1_count"])
        ticker_ratio = float(ticker_result["price_range_hit_ratio"])
        if ticker_matched > 0 and ticker_ratio < 0.80:
            raise AlignmentContractError(
                "broker offset agreement is below 0.80 for "
                f"{ticker_result['ticker']}: {ticker_ratio:.3f}"
            )

    evidence = {
        "best_hit_count": best_hit_count,
        "second_hit_count": second_hit_count,
        "hit_lead": best_hit_count - second_hit_count,
        "required_hit_lead": required_hit_lead,
        "matched_count": matched_count,
        "required_matched_count": required_matched_count,
        "best_hit_ratio": hit_ratio,
    }
    return int(selected["offset_hours"]), evidence


def read_eligible_alerts(
    connection: sqlite3.Connection,
) -> list[dict[str, Any]]:
    annotations_exist = (
        connection.execute(
            """
            SELECT 1
            FROM sqlite_master
            WHERE type = 'table' AND name = 'raw_alert_annotations'
            """
        ).fetchone()
        is not None
    )
    exclusion = ""
    if annotations_exist:
        exclusion = """
            WHERE NOT EXISTS (
                SELECT 1
                FROM raw_alert_annotations a
                WHERE a.raw_alert_id = r.cloudflare_id
                  AND a.annotation_type = 'CONNECTION_TEST'
            )
        """

    rows = connection.execute(
        f"""
        SELECT
            r.cloudflare_id,
            r.ticker,
            r.event,
            r.fired_at_utc,
            r.bar_time_utc,
            r.close_price
        FROM raw_alerts r
        {exclusion}
        ORDER BY r.cloudflare_id ASC
        """
    ).fetchall()
    return [dict(row) for row in rows]


def build_mt5_closed_bar_alignment(
    connection: sqlite3.Connection,
    *,
    mt5_files_root: Path,
    built_at_utc: str,
) -> dict[str, Any]:
    alerts = read_eligible_alerts(connection)
    if not alerts:
        raise AlignmentContractError("no eligible alerts are available")

    m1_by_ticker = {
        ticker: load_m1_bars(mt5_files_root / files["M1"])
        for ticker, files in FILE_MAP.items()
    }
    offset_scores = score_offsets(alerts, m1_by_ticker)
    selected_offset = provisional_offset(offset_scores)
    offset_hours, offset_evidence = validate_offset_for_alignment(
        offset_scores,
        selected_offset,
        eligible_alert_count=len(alerts),
    )

    bar_cache: dict[
        tuple[str, str], tuple[list[datetime], list[ClosedBar]]
    ] = {}
    for ticker, files in FILE_MAP.items():
        for timeframe in CONTEXT_TIMEFRAMES:
            bar_cache[(ticker, timeframe)] = load_closed_bars(
                mt5_files_root / files[timeframe],
                timeframe=timeframe,
                offset_hours=offset_hours,
            )

    insert_rows: list[tuple[Any, ...]] = []
    missing_alignments: list[dict[str, Any]] = []
    future_bar_selection_count = 0
    bar_ages: list[float] = []

    for alert in alerts:
        raw_alert_id = int(alert["cloudflare_id"])
        ticker = str(alert["ticker"])
        decision_time_utc = parse_utc(str(alert["fired_at_utc"]))

        for timeframe in CONTEXT_TIMEFRAMES:
            utc_closes, bars = bar_cache[(ticker, timeframe)]
            selected_bar = select_latest_closed_bar(
                utc_closes,
                bars,
                decision_time_utc,
            )
            if selected_bar is None:
                missing_alignments.append(
                    {
                        "raw_alert_id": raw_alert_id,
                        "ticker": ticker,
                        "timeframe": timeframe,
                    }
                )
                continue

            bar_age_seconds = (
                decision_time_utc - selected_bar.utc_close
            ).total_seconds()
            if bar_age_seconds < 0:
                future_bar_selection_count += 1
            bar_ages.append(bar_age_seconds)

            tv_close_price = (
                None
                if alert["close_price"] is None
                else float(alert["close_price"])
            )
            price_diff = (
                None
                if tv_close_price is None
                else selected_bar.close_price - tv_close_price
            )
            diagnostics = {
                "selection_rule": "latest utc_close <= decision_time_utc",
                "decision_time_utc": iso_z(decision_time_utc),
                "server_open": selected_bar.server_open.strftime(
                    "%Y.%m.%d %H:%M:%S"
                ),
                "estimated_utc_open": iso_z(selected_bar.utc_open),
                "estimated_utc_close": iso_z(selected_bar.utc_close),
                "bar_age_seconds": bar_age_seconds,
                "ohlc": {
                    "open": selected_bar.open_price,
                    "high": selected_bar.high_price,
                    "low": selected_bar.low_price,
                    "close": selected_bar.close_price,
                },
                "offset_status": selected_offset["status"],
                "offset_evidence": offset_evidence,
                "same_printed_hour_join_used": False,
                "dst_recheck_required": True,
                "usage": "AUDIT_CONTEXT_ONLY",
                "built_at_utc": built_at_utc,
            }
            insert_rows.append(
                (
                    raw_alert_id,
                    timeframe,
                    iso_z(decision_time_utc),
                    selected_bar.server_open.strftime("%Y.%m.%d %H:%M:%S"),
                    iso_z(selected_bar.utc_close),
                    float(offset_hours),
                    bar_age_seconds,
                    tv_close_price,
                    selected_bar.close_price,
                    price_diff,
                    "ALIGNED_CLOSED_BAR",
                    json.dumps(
                        diagnostics,
                        ensure_ascii=False,
                        sort_keys=True,
                        separators=(",", ":"),
                    ),
                )
            )

    expected_alignment_count = len(alerts) * len(CONTEXT_TIMEFRAMES)
    if (
        missing_alignments
        or future_bar_selection_count > 0
        or len(insert_rows) != expected_alignment_count
    ):
        raise AlignmentContractError(
            "closed-bar alignment is incomplete; previous derived alignment "
            "was preserved. "
            f"rows={len(insert_rows)} expected={expected_alignment_count} "
            f"missing={missing_alignments[:5]} "
            f"future={future_bar_selection_count}"
        )

    connection.execute("BEGIN IMMEDIATE")
    try:
        connection.execute("DELETE FROM mt5_alignment")
        connection.executemany(
            """
            INSERT INTO mt5_alignment (
                raw_alert_id,
                timeframe,
                tv_event_time_utc,
                mt5_server_time,
                estimated_mt5_time_utc,
                selected_offset_hours,
                time_diff_seconds,
                tv_close_price,
                mt5_close_price,
                price_diff,
                alignment_status,
                diagnostics_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            insert_rows,
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise

    return {
        "eligible_alert_count": len(alerts),
        "timeframes": list(CONTEXT_TIMEFRAMES),
        "expected_alignment_count": expected_alignment_count,
        "aligned_count": len(insert_rows),
        "missing_alignment_count": 0,
        "future_bar_selection_count": 0,
        "selected_offset": selected_offset,
        "offset_evidence": offset_evidence,
        "median_bar_age_seconds": statistics.median(bar_ages),
        "maximum_bar_age_seconds": max(bar_ages),
    }
