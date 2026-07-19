from __future__ import annotations

import csv
import json
import math
import sqlite3
from bisect import bisect_left, bisect_right
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from mt5_csv_contract import EXPECTED_HEADER, FILE_MAP, parse_mt5_time, parse_utc

OUTCOME_CONTRACT_VERSION = "MOCHIPOYO_M6A_SOURCE_OUTCOMES_V1"
ENTRY_ID_PREFIX = "M6A:"
FEATURE_TIMEFRAMES = ("M5", "M15", "H1", "H4", "D1")
ENTRY_ROLES = ("PRIMARY_ALERT", "REENTRY_ALERT")


class OutcomeContractError(RuntimeError):
    pass


@dataclass(frozen=True)
class M1Bar:
    server_open: datetime
    open_price: float
    high_price: float
    low_price: float
    close_price: float


@dataclass(frozen=True)
class EntryCandidate:
    episode_id: str
    ticker: str
    direction: str
    episode_status: str
    source_exit_alert_id: int | None
    episode_exit_time_utc: str | None
    entry_alert_id: int
    entry_role: str
    reentry_index: int | None
    entry_time_utc: str
    entry_received_at_utc: str
    entry_price: float
    exit_time_utc: str | None
    exit_received_at_utc: str | None
    exit_price: float | None


def iso_z(value: datetime) -> str:
    return value.strftime("%Y-%m-%dT%H:%M:%SZ")


def floor_minute(value: datetime) -> datetime:
    return value.replace(second=0, microsecond=0)


def _safe_ratio(numerator: float, denominator: float) -> float | None:
    if (
        not math.isfinite(numerator)
        or not math.isfinite(denominator)
        or abs(denominator) <= 1e-12
    ):
        return None
    return numerator / denominator


def _bps(value: float, reference: float) -> float | None:
    ratio = _safe_ratio(value, abs(reference))
    return None if ratio is None else ratio * 10000.0


def ensure_outcome_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE INDEX IF NOT EXISTS idx_mochipoyo_virtual_entry_episode
        ON virtual_entries (episode_id, entry_index);

        CREATE INDEX IF NOT EXISTS idx_mochipoyo_virtual_entry_status
        ON virtual_entries (status, entry_type);

        CREATE TABLE IF NOT EXISTS outcome_path_metrics (
            entry_id TEXT PRIMARY KEY REFERENCES outcomes(entry_id),
            outcome_contract_version TEXT NOT NULL,
            source_entry_alert_id INTEGER NOT NULL REFERENCES raw_alerts(cloudflare_id),
            source_exit_alert_id INTEGER NOT NULL REFERENCES raw_alerts(cloudflare_id),
            ticker TEXT NOT NULL,
            direction TEXT NOT NULL CHECK (direction IN ('LONG', 'SHORT')),
            entry_role TEXT NOT NULL CHECK (entry_role IN ('PRIMARY_ALERT', 'REENTRY_ALERT')),
            entry_source_price REAL NOT NULL,
            exit_source_price REAL NOT NULL,
            source_return_price_units REAL NOT NULL,
            source_return_bps REAL NOT NULL,
            mfe_price_units REAL NOT NULL,
            mae_price_units REAL NOT NULL,
            mfe_bps REAL NOT NULL,
            mae_bps REAL NOT NULL,
            atr14_m5 REAL NOT NULL,
            atr14_m15 REAL NOT NULL,
            source_return_atr_m5 REAL NOT NULL,
            source_return_atr_m15 REAL NOT NULL,
            mfe_atr_m5 REAL NOT NULL,
            mae_atr_m5 REAL NOT NULL,
            mfe_atr_m15 REAL NOT NULL,
            mae_atr_m15 REAL NOT NULL,
            selected_offset_hours REAL NOT NULL,
            path_bar_count INTEGER NOT NULL,
            path_gap_count INTEGER NOT NULL,
            path_first_bar_utc TEXT,
            path_last_bar_utc TEXT,
            max_favorable_time_utc TEXT NOT NULL,
            max_adverse_time_utc TEXT NOT NULL,
            time_to_mfe_seconds REAL NOT NULL,
            time_to_mae_seconds REAL NOT NULL,
            same_entry_minute_excluded INTEGER NOT NULL CHECK (same_entry_minute_excluded = 1),
            same_exit_minute_excluded INTEGER NOT NULL CHECK (same_exit_minute_excluded = 1),
            future_path_bar_count INTEGER NOT NULL CHECK (future_path_bar_count = 0),
            path_quality_status TEXT NOT NULL,
            diagnostics_json TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_mochipoyo_outcome_path_source_entry
        ON outcome_path_metrics (source_entry_alert_id, entry_role);

        CREATE INDEX IF NOT EXISTS idx_mochipoyo_outcome_path_ticker_direction
        ON outcome_path_metrics (ticker, direction, entry_role);

        CREATE TABLE IF NOT EXISTS source_outcome_build_runs (
            build_id INTEGER PRIMARY KEY AUTOINCREMENT,
            built_at_utc TEXT NOT NULL,
            outcome_contract_version TEXT NOT NULL,
            eligible_alert_count INTEGER NOT NULL,
            episode_count INTEGER NOT NULL,
            closed_episode_count INTEGER NOT NULL,
            open_episode_count INTEGER NOT NULL,
            virtual_entry_count INTEGER NOT NULL,
            resolved_entry_count INTEGER NOT NULL,
            open_entry_count INTEGER NOT NULL,
            path_metric_count INTEGER NOT NULL,
            endpoint_only_count INTEGER NOT NULL,
            future_path_violation_count INTEGER NOT NULL,
            audit_only INTEGER NOT NULL CHECK (audit_only = 1),
            future_outcomes_used_for_entry_selection INTEGER NOT NULL
                CHECK (future_outcomes_used_for_entry_selection = 0)
        );
        """
    )
    connection.commit()


def eligible_raw_alert_ids(connection: sqlite3.Connection) -> list[int]:
    annotations_exist = (
        connection.execute(
            "SELECT 1 FROM sqlite_master "
            "WHERE type='table' AND name='raw_alert_annotations'"
        ).fetchone()
        is not None
    )
    exclusion = ""
    if annotations_exist:
        exclusion = """
            WHERE NOT EXISTS (
                SELECT 1 FROM raw_alert_annotations a
                WHERE a.raw_alert_id = r.cloudflare_id
                  AND a.annotation_type = 'CONNECTION_TEST'
            )
        """
    rows = connection.execute(
        f"SELECT r.cloudflare_id FROM raw_alerts r "
        f"{exclusion} ORDER BY r.cloudflare_id"
    ).fetchall()
    return [int(row[0]) for row in rows]


def validate_current_stage_coverage(
    connection: sqlite3.Connection,
) -> dict[str, int]:
    eligible_ids = eligible_raw_alert_ids(connection)
    eligible_set = set(eligible_ids)
    if not eligible_ids:
        raise OutcomeContractError("no eligible raw alerts are available")

    assigned_rows = connection.execute(
        "SELECT raw_alert_id FROM episode_events ORDER BY raw_alert_id"
    ).fetchall()
    assigned_ids = {int(row[0]) for row in assigned_rows}
    if assigned_ids != eligible_set:
        raise OutcomeContractError(
            "Stage M3 episodes are stale or incomplete relative to current raw alerts: "
            f"missing={sorted(eligible_set - assigned_ids)[:10]} "
            f"extra={sorted(assigned_ids - eligible_set)[:10]}"
        )

    anomaly_count = int(
        connection.execute(
            "SELECT COUNT(*) FROM episode_build_anomalies"
        ).fetchone()[0]
        or 0
    )
    if anomaly_count != 0:
        raise OutcomeContractError(
            f"Stage M3 still contains {anomaly_count} sequence anomalies"
        )

    alignment_rows = connection.execute(
        "SELECT raw_alert_id, timeframe FROM mt5_alignment "
        "ORDER BY raw_alert_id, timeframe"
    ).fetchall()
    alignment_ids = {int(row[0]) for row in alignment_rows}
    if alignment_ids != eligible_set:
        raise OutcomeContractError(
            "Stage M4 alignment is stale or incomplete relative to current raw alerts"
        )
    alignment_tf: dict[int, set[str]] = {}
    for row in alignment_rows:
        alignment_tf.setdefault(int(row[0]), set()).add(str(row[1]))
    expected_tf = set(FEATURE_TIMEFRAMES)
    bad_alignment = {
        raw_id: sorted(expected_tf - values)
        for raw_id, values in alignment_tf.items()
        if values != expected_tf
    }
    if (
        bad_alignment
        or len(alignment_rows)
        != len(eligible_ids) * len(FEATURE_TIMEFRAMES)
    ):
        raise OutcomeContractError(
            "Stage M4 timeframe coverage is incomplete: "
            f"{list(bad_alignment.items())[:5]}"
        )

    feature_rows = connection.execute(
        "SELECT source_event_id, timeframe, future_fields_present "
        "FROM feature_snapshots ORDER BY source_event_id, timeframe"
    ).fetchall()
    feature_ids = {int(row[0]) for row in feature_rows}
    if feature_ids != eligible_set:
        raise OutcomeContractError(
            "Stage M5 feature snapshots are stale or incomplete relative to current raw alerts"
        )
    feature_tf: dict[int, set[str]] = {}
    future_count = 0
    for row in feature_rows:
        feature_tf.setdefault(int(row[0]), set()).add(str(row[1]))
        future_count += int(row[2] or 0)
    bad_features = {
        raw_id: sorted(expected_tf - values)
        for raw_id, values in feature_tf.items()
        if values != expected_tf
    }
    if (
        bad_features
        or len(feature_rows) != len(eligible_ids) * len(FEATURE_TIMEFRAMES)
    ):
        raise OutcomeContractError(
            "Stage M5 timeframe coverage is incomplete: "
            f"{list(bad_features.items())[:5]}"
        )
    if future_count != 0:
        raise OutcomeContractError(
            f"Stage M5 contains {future_count} future-field violations"
        )

    episode_counts = connection.execute(
        """
        SELECT COUNT(*) AS total,
               SUM(CASE WHEN episode_status='CLOSED' THEN 1 ELSE 0 END)
                   AS closed_count,
               SUM(CASE WHEN episode_status='OPEN' THEN 1 ELSE 0 END)
                   AS open_count
        FROM episodes
        """
    ).fetchone()
    return {
        "eligible_alert_count": len(eligible_ids),
        "episode_count": int(episode_counts["total"] or 0),
        "closed_episode_count": int(episode_counts["closed_count"] or 0),
        "open_episode_count": int(episode_counts["open_count"] or 0),
    }


def read_entry_candidates(
    connection: sqlite3.Connection,
) -> list[EntryCandidate]:
    rows = connection.execute(
        """
        SELECT
            e.episode_id,
            e.ticker,
            e.direction,
            e.episode_status,
            e.exit_alert_id,
            e.exited_at_utc,
            ee.raw_alert_id AS entry_alert_id,
            ee.event_role,
            ee.reentry_index,
            entry_raw.event AS entry_event,
            entry_raw.fired_at_utc AS entry_time_utc,
            entry_raw.received_at_utc AS entry_received_at_utc,
            entry_raw.close_price AS entry_price,
            exit_raw.event AS exit_event,
            exit_raw.fired_at_utc AS exit_time_utc,
            exit_raw.received_at_utc AS exit_received_at_utc,
            exit_raw.close_price AS exit_price
        FROM episodes e
        JOIN episode_events ee ON ee.episode_id = e.episode_id
        JOIN raw_alerts entry_raw
          ON entry_raw.cloudflare_id = ee.raw_alert_id
        LEFT JOIN raw_alerts exit_raw
          ON exit_raw.cloudflare_id = e.exit_alert_id
        WHERE ee.event_role IN ('PRIMARY_ALERT', 'REENTRY_ALERT')
        ORDER BY e.primary_alert_id ASC, ee.raw_alert_id ASC
        """
    ).fetchall()
    candidates: list[EntryCandidate] = []
    for row in rows:
        direction = str(row["direction"])
        if str(row["entry_event"]) != direction:
            raise OutcomeContractError(
                f"entry alert {row['entry_alert_id']} does not match episode direction"
            )
        status = str(row["episode_status"])
        exit_alert_id = (
            None if row["exit_alert_id"] is None else int(row["exit_alert_id"])
        )
        if status == "CLOSED":
            expected_exit = f"{direction}_EXIT"
            if exit_alert_id is None or str(row["exit_event"]) != expected_exit:
                raise OutcomeContractError(
                    f"closed episode {row['episode_id']} has an invalid exit alert"
                )
            if row["exit_time_utc"] is None or row["exit_price"] is None:
                raise OutcomeContractError(
                    f"closed episode {row['episode_id']} has incomplete exit data"
                )
        elif status == "OPEN":
            if exit_alert_id is not None:
                raise OutcomeContractError(
                    f"open episode {row['episode_id']} unexpectedly has an exit"
                )
        else:
            raise OutcomeContractError(f"unsupported episode status: {status}")
        if row["entry_price"] is None:
            raise OutcomeContractError(
                f"entry alert {row['entry_alert_id']} has no source close price"
            )
        candidates.append(
            EntryCandidate(
                episode_id=str(row["episode_id"]),
                ticker=str(row["ticker"]),
                direction=direction,
                episode_status=status,
                source_exit_alert_id=exit_alert_id,
                episode_exit_time_utc=(
                    None
                    if row["exited_at_utc"] is None
                    else str(row["exited_at_utc"])
                ),
                entry_alert_id=int(row["entry_alert_id"]),
                entry_role=str(row["event_role"]),
                reentry_index=(
                    None
                    if row["reentry_index"] is None
                    else int(row["reentry_index"])
                ),
                entry_time_utc=str(row["entry_time_utc"]),
                entry_received_at_utc=str(row["entry_received_at_utc"]),
                entry_price=float(row["entry_price"]),
                exit_time_utc=(
                    None
                    if row["exit_time_utc"] is None
                    else str(row["exit_time_utc"])
                ),
                exit_received_at_utc=(
                    None
                    if row["exit_received_at_utc"] is None
                    else str(row["exit_received_at_utc"])
                ),
                exit_price=(
                    None
                    if row["exit_price"] is None
                    else float(row["exit_price"])
                ),
            )
        )
    return candidates


def load_m1_bars(path: Path) -> tuple[list[datetime], list[M1Bar]]:
    if not path.is_file():
        raise OutcomeContractError(f"missing M1 CSV: {path.name}")
    server_opens: list[datetime] = []
    bars: list[M1Bar] = []
    previous: datetime | None = None
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != EXPECTED_HEADER:
            raise OutcomeContractError(f"unexpected header for {path.name}")
        for line_number, row in enumerate(reader, start=2):
            try:
                server_open = parse_mt5_time(row["time"])
                bar = M1Bar(
                    server_open=server_open,
                    open_price=float(row["open"]),
                    high_price=float(row["high"]),
                    low_price=float(row["low"]),
                    close_price=float(row["close"]),
                )
            except Exception as exc:
                raise OutcomeContractError(
                    f"invalid row in {path.name} at CSV line {line_number}"
                ) from exc
            if previous is not None and server_open <= previous:
                raise OutcomeContractError(
                    f"non-ascending M1 timestamp in {path.name} "
                    f"at CSV line {line_number}"
                )
            previous = server_open
            server_opens.append(server_open)
            bars.append(bar)
    if not bars:
        raise OutcomeContractError(f"M1 CSV has no rows: {path.name}")
    return server_opens, bars


def _alignment_offset(
    connection: sqlite3.Connection,
    raw_alert_id: int,
) -> float:
    row = connection.execute(
        """
        SELECT selected_offset_hours, alignment_status
        FROM mt5_alignment
        WHERE raw_alert_id = ? AND timeframe = 'M5'
        """,
        (raw_alert_id,),
    ).fetchone()
    if row is None or str(row["alignment_status"]) != "ALIGNED_CLOSED_BAR":
        raise OutcomeContractError(
            f"missing valid M5 alignment for raw alert {raw_alert_id}"
        )
    offset = float(row["selected_offset_hours"])
    if not math.isfinite(offset):
        raise OutcomeContractError(
            f"non-finite MT5 offset for raw alert {raw_alert_id}"
        )
    return offset


def _entry_atr_values(
    connection: sqlite3.Connection,
    raw_alert_id: int,
) -> tuple[float, float]:
    rows = connection.execute(
        """
        SELECT timeframe, features_json, future_fields_present
        FROM feature_snapshots
        WHERE source_event_id = ? AND timeframe IN ('M5', 'M15')
        ORDER BY timeframe
        """,
        (raw_alert_id,),
    ).fetchall()
    values: dict[str, float] = {}
    for row in rows:
        if int(row["future_fields_present"] or 0) != 0:
            raise OutcomeContractError(
                f"future fields are present for raw alert {raw_alert_id}"
            )
        payload = json.loads(str(row["features_json"]))
        atr = float(payload["volatility"]["atr14"])
        if not math.isfinite(atr) or atr <= 0:
            raise OutcomeContractError(
                f"invalid ATR14 for raw alert {raw_alert_id} "
                f"{row['timeframe']}"
            )
        values[str(row["timeframe"])] = atr
    if set(values) != {"M5", "M15"}:
        raise OutcomeContractError(
            f"missing M5/M15 ATR features for raw alert {raw_alert_id}"
        )
    return values["M5"], values["M15"]


def deterministic_entry_id(candidate: EntryCandidate) -> str:
    role = "PRIMARY" if candidate.entry_role == "PRIMARY_ALERT" else "REENTRY"
    return (
        f"{ENTRY_ID_PREFIX}{candidate.episode_id}:"
        f"{role}:{candidate.entry_alert_id}"
    )


def _path_slice(
    server_opens: list[datetime],
    bars: list[M1Bar],
    *,
    entry_time_utc: datetime,
    exit_time_utc: datetime,
    offset_hours: float,
) -> tuple[list[M1Bar], datetime, datetime]:
    entry_server_minute = floor_minute(entry_time_utc) + timedelta(
        hours=offset_hours
    )
    exit_server_minute = floor_minute(exit_time_utc) + timedelta(
        hours=offset_hours
    )
    left = bisect_right(server_opens, entry_server_minute)
    right = bisect_left(server_opens, exit_server_minute)
    return bars[left:right], entry_server_minute, exit_server_minute


def _path_gap_count(path_bars: list[M1Bar]) -> int:
    return sum(
        1
        for previous, current in zip(path_bars, path_bars[1:])
        if int((current.server_open - previous.server_open).total_seconds()) != 60
    )


def _build_resolved_metrics(
    candidate: EntryCandidate,
    *,
    connection: sqlite3.Connection,
    server_opens: list[datetime],
    bars: list[M1Bar],
    m1_filename: str,
    built_at_utc: str,
) -> tuple[dict[str, Any], tuple[Any, ...], tuple[Any, ...]]:
    if candidate.exit_time_utc is None or candidate.exit_price is None:
        raise OutcomeContractError("resolved metric requested for an open entry")
    if (
        candidate.source_exit_alert_id is None
        or candidate.exit_received_at_utc is None
    ):
        raise OutcomeContractError("closed entry lacks exit identity/receipt time")

    entry_dt = parse_utc(candidate.entry_time_utc)
    exit_dt = parse_utc(candidate.exit_time_utc)
    if exit_dt <= entry_dt:
        raise OutcomeContractError(
            f"non-positive episode duration for {candidate.episode_id}"
        )

    entry_offset = _alignment_offset(connection, candidate.entry_alert_id)
    exit_offset = _alignment_offset(
        connection,
        candidate.source_exit_alert_id,
    )
    if abs(entry_offset - exit_offset) > 1e-9:
        raise OutcomeContractError(
            f"MT5 offset changed within episode {candidate.episode_id}: "
            f"entry={entry_offset} exit={exit_offset}"
        )
    atr_m5, atr_m15 = _entry_atr_values(
        connection,
        candidate.entry_alert_id,
    )
    path_bars, entry_server_minute, exit_server_minute = _path_slice(
        server_opens,
        bars,
        entry_time_utc=entry_dt,
        exit_time_utc=exit_dt,
        offset_hours=entry_offset,
    )

    future_count = 0
    for bar in path_bars:
        utc_open = bar.server_open - timedelta(hours=entry_offset)
        if (
            utc_open <= floor_minute(entry_dt)
            or utc_open >= floor_minute(exit_dt)
        ):
            future_count += 1
    if future_count:
        raise OutcomeContractError(
            f"path selection contract violated for entry "
            f"{candidate.entry_alert_id}"
        )

    entry_price = candidate.entry_price
    exit_price = candidate.exit_price
    direction_sign = 1.0 if candidate.direction == "LONG" else -1.0
    source_return = direction_sign * (exit_price - entry_price)

    favorable_value = entry_price
    favorable_time = entry_dt
    adverse_value = entry_price
    adverse_time = entry_dt

    def consider_favorable(value: float, event_time: datetime) -> None:
        nonlocal favorable_value, favorable_time
        if candidate.direction == "LONG":
            if value > favorable_value:
                favorable_value = value
                favorable_time = event_time
        elif value < favorable_value:
            favorable_value = value
            favorable_time = event_time

    def consider_adverse(value: float, event_time: datetime) -> None:
        nonlocal adverse_value, adverse_time
        if candidate.direction == "LONG":
            if value < adverse_value:
                adverse_value = value
                adverse_time = event_time
        elif value > adverse_value:
            adverse_value = value
            adverse_time = event_time

    for bar in path_bars:
        bar_utc_open = bar.server_open - timedelta(hours=entry_offset)
        if candidate.direction == "LONG":
            consider_favorable(bar.high_price, bar_utc_open)
            consider_adverse(bar.low_price, bar_utc_open)
        else:
            consider_favorable(bar.low_price, bar_utc_open)
            consider_adverse(bar.high_price, bar_utc_open)

    consider_favorable(exit_price, exit_dt)
    consider_adverse(exit_price, exit_dt)

    if candidate.direction == "LONG":
        mfe = favorable_value - entry_price
        mae = entry_price - adverse_value
    else:
        mfe = entry_price - favorable_value
        mae = adverse_value - entry_price
    if mfe < -1e-9 or mae < -1e-9:
        raise OutcomeContractError(
            "negative MFE/MAE internal invariant violated"
        )
    mfe = max(0.0, mfe)
    mae = max(0.0, mae)

    path_first_utc = (
        None
        if not path_bars
        else iso_z(
            path_bars[0].server_open - timedelta(hours=entry_offset)
        )
    )
    path_last_utc = (
        None
        if not path_bars
        else iso_z(
            path_bars[-1].server_open - timedelta(hours=entry_offset)
        )
    )
    gap_count = _path_gap_count(path_bars)
    quality = (
        "FULL_M1_INTERIOR"
        if path_bars
        else "ENDPOINT_ONLY_NO_M1_INTERIOR"
    )

    source_return_bps = _bps(source_return, entry_price)
    mfe_bps = _bps(mfe, entry_price)
    mae_bps = _bps(mae, entry_price)
    if source_return_bps is None or mfe_bps is None or mae_bps is None:
        raise OutcomeContractError(
            "cannot normalize source outcome by entry price"
        )

    diagnostics = {
        "contract_version": OUTCOME_CONTRACT_VERSION,
        "entry_price_basis": "TRADINGVIEW_SOURCE_CLOSE",
        "exit_price_basis": "TRADINGVIEW_SOURCE_EXIT_CLOSE",
        "path_price_basis": "MT5_M1_OHLC_USING_AUDITED_OFFSET",
        "m1_filename": m1_filename,
        "entry_time_utc": iso_z(entry_dt),
        "exit_time_utc": iso_z(exit_dt),
        "entry_server_minute": entry_server_minute.strftime(
            "%Y.%m.%d %H:%M:%S"
        ),
        "exit_server_minute": exit_server_minute.strftime(
            "%Y.%m.%d %H:%M:%S"
        ),
        "path_selection": (
            "server_open > floor(entry_utc)+offset AND "
            "server_open < floor(exit_utc)+offset"
        ),
        "same_entry_minute_excluded": True,
        "same_exit_minute_excluded": True,
        "reason_for_minute_exclusion": (
            "M1 OHLC does not reveal whether intraminute extremes occurred before "
            "or after the source event. Full entry and exit minutes are "
            "conservatively excluded."
        ),
        "source_exit_price_included_as_terminal_point": True,
        "sl_policy_defined": False,
        "tp_policy_defined": False,
        "result_r_defined": False,
        "actual_position_size_defined": False,
        "result_usd_defined": False,
        "future_outcomes_used_for_entry_selection": False,
        "post_entry_data_used_for_outcome_measurement": True,
        "entry_gate_enabled": False,
        "audit_only": True,
        "built_at_utc": built_at_utc,
    }

    entry_id = deterministic_entry_id(candidate)
    metric_row = (
        entry_id,
        OUTCOME_CONTRACT_VERSION,
        candidate.entry_alert_id,
        candidate.source_exit_alert_id,
        candidate.ticker,
        candidate.direction,
        candidate.entry_role,
        entry_price,
        exit_price,
        source_return,
        source_return_bps,
        mfe,
        mae,
        mfe_bps,
        mae_bps,
        atr_m5,
        atr_m15,
        source_return / atr_m5,
        source_return / atr_m15,
        mfe / atr_m5,
        mae / atr_m5,
        mfe / atr_m15,
        mae / atr_m15,
        entry_offset,
        len(path_bars),
        gap_count,
        path_first_utc,
        path_last_utc,
        iso_z(favorable_time),
        iso_z(adverse_time),
        (favorable_time - entry_dt).total_seconds(),
        (adverse_time - entry_dt).total_seconds(),
        1,
        1,
        0,
        quality,
        json.dumps(
            diagnostics,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ),
    )
    outcome_row = (
        entry_id,
        iso_z(exit_dt),
        exit_price,
        "SOURCE_EXIT_ALERT",
        mfe,
        mae,
        None,
        None,
        candidate.exit_received_at_utc,
    )
    summary = {
        "entry_id": entry_id,
        "ticker": candidate.ticker,
        "direction": candidate.direction,
        "entry_role": candidate.entry_role,
        "source_return_bps": source_return_bps,
        "mfe_bps": mfe_bps,
        "mae_bps": mae_bps,
        "source_return_atr_m5": source_return / atr_m5,
        "mfe_atr_m5": mfe / atr_m5,
        "mae_atr_m5": mae / atr_m5,
        "path_bar_count": len(path_bars),
        "path_quality_status": quality,
    }
    return summary, outcome_row, metric_row


def _virtual_entry_row(candidate: EntryCandidate) -> tuple[Any, ...]:
    entry_index = (
        0
        if candidate.entry_role == "PRIMARY_ALERT"
        else int(candidate.reentry_index or 0)
    )
    if candidate.entry_role == "REENTRY_ALERT" and entry_index <= 0:
        raise OutcomeContractError(
            f"reentry alert {candidate.entry_alert_id} "
            "has no positive reentry index"
        )
    entry_type = (
        "SOURCE_PRIMARY_ALERT_IMMEDIATE"
        if candidate.entry_role == "PRIMARY_ALERT"
        else "SOURCE_REENTRY_ALERT_IMMEDIATE"
    )
    status = (
        "RESOLVED_SOURCE_EXIT"
        if candidate.episode_status == "CLOSED"
        else "OPEN_SOURCE_EPISODE"
    )
    return (
        deterministic_entry_id(candidate),
        candidate.episode_id,
        entry_type,
        entry_index,
        candidate.entry_time_utc,
        candidate.entry_time_utc,
        candidate.entry_price,
        None,
        None,
        status,
    )


def _group_summary(
    resolved: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for row in resolved:
        key = (
            str(row["ticker"]),
            str(row["direction"]),
            str(row["entry_role"]),
        )
        groups.setdefault(key, []).append(row)
    output: list[dict[str, Any]] = []
    for key in sorted(groups):
        values = groups[key]
        count = len(values)
        positive = sum(
            1
            for item in values
            if float(item["source_return_bps"]) > 0
        )
        output.append(
            {
                "ticker": key[0],
                "direction": key[1],
                "entry_role": key[2],
                "resolved_count": count,
                "positive_exit_count": positive,
                "positive_exit_ratio": (
                    positive / count if count else None
                ),
                "mean_source_return_bps": sum(
                    float(item["source_return_bps"])
                    for item in values
                )
                / count,
                "mean_mfe_bps": sum(
                    float(item["mfe_bps"]) for item in values
                )
                / count,
                "mean_mae_bps": sum(
                    float(item["mae_bps"]) for item in values
                )
                / count,
                "mean_source_return_atr_m5": sum(
                    float(item["source_return_atr_m5"])
                    for item in values
                )
                / count,
                "mean_mfe_atr_m5": sum(
                    float(item["mfe_atr_m5"])
                    for item in values
                )
                / count,
                "mean_mae_atr_m5": sum(
                    float(item["mae_atr_m5"])
                    for item in values
                )
                / count,
            }
        )
    return output


def rebuild_source_outcomes(
    connection: sqlite3.Connection,
    *,
    mt5_files_root: Path,
    built_at_utc: str,
) -> dict[str, Any]:
    ensure_outcome_schema(connection)
    initial_state = validate_current_stage_coverage(connection)
    initial_eligible_ids = eligible_raw_alert_ids(connection)
    candidates = read_entry_candidates(connection)
    if not candidates:
        raise OutcomeContractError(
            "no primary/reentry source entries are available"
        )

    m1_cache: dict[
        str,
        tuple[list[datetime], list[M1Bar], str],
    ] = {}
    for ticker in sorted({candidate.ticker for candidate in candidates}):
        filename = FILE_MAP[ticker]["M1"]
        opens, bars = load_m1_bars(mt5_files_root / filename)
        m1_cache[ticker] = (opens, bars, filename)

    virtual_rows: list[tuple[Any, ...]] = []
    outcome_rows: list[tuple[Any, ...]] = []
    metric_rows: list[tuple[Any, ...]] = []
    resolved_summaries: list[dict[str, Any]] = []
    open_entries: list[dict[str, Any]] = []

    for candidate in candidates:
        virtual_rows.append(_virtual_entry_row(candidate))
        if candidate.episode_status == "OPEN":
            open_entries.append(
                {
                    "entry_id": deterministic_entry_id(candidate),
                    "episode_id": candidate.episode_id,
                    "ticker": candidate.ticker,
                    "direction": candidate.direction,
                    "entry_role": candidate.entry_role,
                    "source_entry_alert_id": candidate.entry_alert_id,
                    "entry_time_utc": candidate.entry_time_utc,
                    "status": "OPEN_SOURCE_EPISODE",
                }
            )
            continue
        opens, bars, filename = m1_cache[candidate.ticker]
        summary, outcome_row, metric_row = _build_resolved_metrics(
            candidate,
            connection=connection,
            server_opens=opens,
            bars=bars,
            m1_filename=filename,
            built_at_utc=built_at_utc,
        )
        resolved_summaries.append(summary)
        outcome_rows.append(outcome_row)
        metric_rows.append(metric_row)

    if len(virtual_rows) != len(candidates):
        raise OutcomeContractError(
            "virtual entry row count changed unexpectedly"
        )
    if len(outcome_rows) != len(metric_rows):
        raise OutcomeContractError(
            "outcome and path metric row counts differ"
        )
    if len(outcome_rows) + len(open_entries) != len(virtual_rows):
        raise OutcomeContractError(
            "resolved/open entry accounting does not balance"
        )

    current_eligible_ids = eligible_raw_alert_ids(connection)
    if current_eligible_ids != initial_eligible_ids:
        raise OutcomeContractError(
            "raw alert set changed while building outcomes; "
            "rerun M3-M6A in order"
        )
    validate_current_stage_coverage(connection)

    endpoint_only_count = sum(
        1
        for row in resolved_summaries
        if row["path_quality_status"] != "FULL_M1_INTERIOR"
    )

    connection.execute("BEGIN IMMEDIATE")
    try:
        connection.execute(
            "DELETE FROM outcome_path_metrics WHERE entry_id LIKE ?",
            (ENTRY_ID_PREFIX + "%",),
        )
        connection.execute(
            "DELETE FROM outcomes WHERE entry_id LIKE ?",
            (ENTRY_ID_PREFIX + "%",),
        )
        connection.execute(
            "DELETE FROM virtual_entries WHERE entry_id LIKE ?",
            (ENTRY_ID_PREFIX + "%",),
        )
        connection.executemany(
            """
            INSERT INTO virtual_entries (
                entry_id, episode_id, entry_type, entry_index,
                setup_detected_at_utc, entry_time_utc, entry_price,
                sl_price, tp_price, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            virtual_rows,
        )
        connection.executemany(
            """
            INSERT INTO outcomes (
                entry_id, exit_dt, exit_price, exit_reason,
                mfe, mae, result_r, result_usd, resolved_at_utc
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            outcome_rows,
        )
        connection.executemany(
            """
            INSERT INTO outcome_path_metrics (
                entry_id, outcome_contract_version,
                source_entry_alert_id, source_exit_alert_id,
                ticker, direction, entry_role,
                entry_source_price, exit_source_price,
                source_return_price_units, source_return_bps,
                mfe_price_units, mae_price_units, mfe_bps, mae_bps,
                atr14_m5, atr14_m15,
                source_return_atr_m5, source_return_atr_m15,
                mfe_atr_m5, mae_atr_m5, mfe_atr_m15, mae_atr_m15,
                selected_offset_hours, path_bar_count, path_gap_count,
                path_first_bar_utc, path_last_bar_utc,
                max_favorable_time_utc, max_adverse_time_utc,
                time_to_mfe_seconds, time_to_mae_seconds,
                same_entry_minute_excluded, same_exit_minute_excluded,
                future_path_bar_count, path_quality_status,
                diagnostics_json
            ) VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
            """,
            metric_rows,
        )
        connection.execute(
            """
            INSERT INTO source_outcome_build_runs (
                built_at_utc, outcome_contract_version,
                eligible_alert_count, episode_count,
                closed_episode_count, open_episode_count,
                virtual_entry_count, resolved_entry_count,
                open_entry_count, path_metric_count,
                endpoint_only_count, future_path_violation_count,
                audit_only, future_outcomes_used_for_entry_selection
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 1, 0)
            """,
            (
                built_at_utc,
                OUTCOME_CONTRACT_VERSION,
                initial_state["eligible_alert_count"],
                initial_state["episode_count"],
                initial_state["closed_episode_count"],
                initial_state["open_episode_count"],
                len(virtual_rows),
                len(outcome_rows),
                len(open_entries),
                len(metric_rows),
                endpoint_only_count,
            ),
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise

    return {
        "outcome_contract_version": OUTCOME_CONTRACT_VERSION,
        **initial_state,
        "virtual_entry_count": len(virtual_rows),
        "resolved_entry_count": len(outcome_rows),
        "open_entry_count": len(open_entries),
        "path_metric_count": len(metric_rows),
        "endpoint_only_count": endpoint_only_count,
        "future_path_violation_count": 0,
        "same_entry_minute_excluded_count": len(metric_rows),
        "same_exit_minute_excluded_count": len(metric_rows),
        "result_r_defined_count": 0,
        "result_usd_defined_count": 0,
        "open_entries": open_entries,
        "by_ticker_direction_entry_role": _group_summary(
            resolved_summaries
        ),
        "outcome_usage": "AUDIT_CONTEXT_ONLY",
        "entry_variants_implemented": [
            "SOURCE_PRIMARY_ALERT_IMMEDIATE",
            "SOURCE_REENTRY_ALERT_IMMEDIATE",
        ],
        "exit_variant_implemented": "SOURCE_EXIT_ALERT",
        "not_implemented_yet": [
            "M5_STRUCTURE_TURN_ENTRY",
            "SECOND_BOTTOM_OR_TOP_ENTRY",
            "FIXED_R_EXIT",
            "M5_OPPOSITE_RCI_EXIT",
            "RECENT_HIGH_LOW_EXIT",
        ],
    }
