from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable

VALID_EVENTS = {"LONG", "SHORT", "LONG_EXIT", "SHORT_EXIT"}
VALID_TICKERS = {"XAUUSD", "BTCUSD"}
REQUIRED_TEXT_FIELDS = (
    "event_key",
    "received_at_utc",
    "source",
    "strategy",
    "event",
    "ticker",
    "bar_time_utc",
    "fired_at_utc",
)


class ContractError(ValueError):
    pass


class ImmutableCollisionError(RuntimeError):
    pass


@dataclass(frozen=True)
class StoreResult:
    response_count: int
    inserted_count: int
    duplicate_count: int
    max_response_id: int | None
    cursor_after: int


def utc_now_text() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def open_database(database_path: Path, schema_path: Path) -> sqlite3.Connection:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA journal_mode = WAL")
    connection.execute("PRAGMA synchronous = FULL")
    connection.executescript(schema_path.read_text(encoding="utf-8"))
    return connection


def state_int(connection: sqlite3.Connection, key: str, default: int = 0) -> int:
    row = connection.execute(
        "SELECT state_value FROM collector_state WHERE state_key = ?", (key,)
    ).fetchone()
    if row is None:
        return default
    try:
        return int(row["state_value"])
    except (TypeError, ValueError) as exc:
        raise ContractError(f"collector_state {key!r} is not an integer") from exc


def set_state(
    connection: sqlite3.Connection, key: str, value: str, updated_at_utc: str
) -> None:
    connection.execute(
        """
        INSERT INTO collector_state (state_key, state_value, updated_at_utc)
        VALUES (?, ?, ?)
        ON CONFLICT(state_key) DO UPDATE SET
            state_value = excluded.state_value,
            updated_at_utc = excluded.updated_at_utc
        """,
        (key, value, updated_at_utc),
    )


def _required_text(row: dict[str, Any], key: str) -> str:
    value = row.get(key)
    text = "" if value is None else str(value).strip()
    if not text:
        raise ContractError(f"event row is missing required field {key!r}")
    return text


def _number_or_none(value: Any, key: str) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ContractError(f"{key} must be numeric or null") from exc


def normalize_event_row(row: Any) -> dict[str, Any]:
    if not isinstance(row, dict):
        raise ContractError("each event must be a JSON object")
    try:
        cloudflare_id = int(row.get("id"))
    except (TypeError, ValueError) as exc:
        raise ContractError("event id must be an integer") from exc
    if cloudflare_id <= 0:
        raise ContractError("event id must be positive")

    required = {key: _required_text(row, key) for key in REQUIRED_TEXT_FIELDS}
    if required["event"] not in VALID_EVENTS:
        raise ContractError(f"unsupported event: {required['event']}")
    if required["ticker"] not in VALID_TICKERS:
        raise ContractError(f"unsupported ticker: {required['ticker']}")
    if required["source"] != "tradingview":
        raise ContractError("source must be tradingview")
    if required["strategy"] != "mochipoyo":
        raise ContractError("strategy must be mochipoyo")

    worker_raw = row.get("raw_json")
    if isinstance(worker_raw, str):
        worker_raw_json = worker_raw
    elif worker_raw is None:
        raise ContractError("raw_json is required")
    else:
        worker_raw_json = canonical_json(worker_raw)

    source_json = canonical_json(row)
    digest = hashlib.sha256(source_json.encode("utf-8")).hexdigest()
    exchange_name = row.get("exchange_name", row.get("exchange"))
    timeframe = row.get("timeframe", row.get("interval"))
    return {
        "cloudflare_id": cloudflare_id,
        "event_key": required["event_key"],
        "received_at_utc": required["received_at_utc"],
        "source": required["source"],
        "strategy": required["strategy"],
        "event": required["event"],
        "exchange_name": None if exchange_name is None else str(exchange_name),
        "ticker": required["ticker"],
        "timeframe": None if timeframe is None else str(timeframe),
        "bar_time_utc": required["bar_time_utc"],
        "fired_at_utc": required["fired_at_utc"],
        "open_price": _number_or_none(row.get("open_price", row.get("open")), "open_price"),
        "high_price": _number_or_none(row.get("high_price", row.get("high")), "high_price"),
        "low_price": _number_or_none(row.get("low_price", row.get("low")), "low_price"),
        "close_price": _number_or_none(row.get("close_price", row.get("close")), "close_price"),
        "message": None if row.get("message") is None else str(row.get("message")),
        "worker_raw_json": worker_raw_json,
        "collector_source_row_json": source_json,
        "payload_sha256": digest,
    }


def validate_page(rows: Iterable[Any], after_id: int) -> list[dict[str, Any]]:
    normalized = [normalize_event_row(row) for row in rows]
    ids = [row["cloudflare_id"] for row in normalized]
    if len(ids) != len(set(ids)):
        raise ContractError("response contains duplicate event IDs")
    if ids != sorted(ids):
        raise ContractError("response event IDs must be in ascending order")
    if any(event_id <= after_id for event_id in ids):
        raise ContractError(
            f"response contains id <= requested after_id ({after_id})"
        )
    event_keys = [row["event_key"] for row in normalized]
    if len(event_keys) != len(set(event_keys)):
        raise ContractError("response contains duplicate event_key values")
    return normalized


def _existing_collision(
    connection: sqlite3.Connection, row: dict[str, Any]
) -> sqlite3.Row | None:
    return connection.execute(
        """
        SELECT cloudflare_id, event_key, payload_sha256
        FROM raw_alerts
        WHERE cloudflare_id = ? OR event_key = ?
        """,
        (row["cloudflare_id"], row["event_key"]),
    ).fetchone()


def store_page(
    connection: sqlite3.Connection,
    rows: Iterable[Any],
    *,
    after_id_before: int,
    downloaded_at_utc: str | None = None,
) -> StoreResult:
    normalized = validate_page(rows, after_id_before)
    downloaded = downloaded_at_utc or utc_now_text()
    inserted = 0
    duplicates = 0
    connection.execute("BEGIN IMMEDIATE")
    try:
        for row in normalized:
            existing = _existing_collision(connection, row)
            if existing is not None:
                same_identity = (
                    int(existing["cloudflare_id"]) == row["cloudflare_id"]
                    and str(existing["event_key"]) == row["event_key"]
                )
                same_payload = str(existing["payload_sha256"]) == row["payload_sha256"]
                if not (same_identity and same_payload):
                    raise ImmutableCollisionError(
                        "immutable raw alert collision for "
                        f"id={row['cloudflare_id']} event_key={row['event_key']}"
                    )
                duplicates += 1
                continue
            connection.execute(
                """
                INSERT INTO raw_alerts (
                    cloudflare_id, event_key, received_at_utc, source, strategy,
                    event, exchange_name, ticker, timeframe, bar_time_utc,
                    fired_at_utc, open_price, high_price, low_price, close_price,
                    message, worker_raw_json, collector_source_row_json,
                    payload_sha256, downloaded_at_utc
                ) VALUES (
                    :cloudflare_id, :event_key, :received_at_utc, :source, :strategy,
                    :event, :exchange_name, :ticker, :timeframe, :bar_time_utc,
                    :fired_at_utc, :open_price, :high_price, :low_price, :close_price,
                    :message, :worker_raw_json, :collector_source_row_json,
                    :payload_sha256, :downloaded_at_utc
                )
                """,
                {**row, "downloaded_at_utc": downloaded},
            )
            inserted += 1

        max_response_id = (
            max(row["cloudflare_id"] for row in normalized) if normalized else None
        )
        cursor_after = max_response_id if max_response_id is not None else after_id_before
        set_state(connection, "last_successful_id", str(cursor_after), downloaded)
        connection.commit()
        return StoreResult(
            response_count=len(normalized),
            inserted_count=inserted,
            duplicate_count=duplicates,
            max_response_id=max_response_id,
            cursor_after=cursor_after,
        )
    except Exception:
        connection.rollback()
        raise


def record_collection_run(
    connection: sqlite3.Connection,
    *,
    run_id: str,
    started_at_utc: str,
    finished_at_utc: str,
    after_id_before: int,
    requested_limit: int,
    response_count: int,
    inserted_count: int,
    duplicate_count: int,
    max_response_id: int | None,
    cursor_after: int,
    status: str,
    source_mode: str,
    events_url_redacted: str,
    error_type: str = "",
    error_message_redacted: str = "",
) -> None:
    connection.execute(
        """
        INSERT INTO collection_runs (
            run_id, started_at_utc, finished_at_utc, after_id_before,
            requested_limit, response_count, inserted_count, duplicate_count,
            max_response_id, cursor_after, status, source_mode,
            events_url_redacted, error_type, error_message_redacted
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            run_id,
            started_at_utc,
            finished_at_utc,
            after_id_before,
            requested_limit,
            response_count,
            inserted_count,
            duplicate_count,
            max_response_id,
            cursor_after,
            status,
            source_mode,
            events_url_redacted,
            error_type or None,
            error_message_redacted or None,
        ),
    )
    connection.commit()
