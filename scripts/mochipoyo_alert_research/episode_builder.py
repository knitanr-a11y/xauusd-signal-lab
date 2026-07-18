from __future__ import annotations

import sqlite3
from dataclasses import dataclass

ENTRY_EVENTS = {"LONG", "SHORT"}
EXIT_EVENTS = {"LONG_EXIT", "SHORT_EXIT"}


@dataclass(frozen=True)
class EpisodeBuildResult:
    raw_alert_count: int
    episode_count: int
    closed_episode_count: int
    open_episode_count: int
    reentry_count: int
    anomaly_count: int
    ignored_opposite_count: int
    latest_raw_id: int


@dataclass
class ActiveEpisode:
    episode_id: str
    ticker: str
    direction: str
    primary_alert_id: int
    started_at_utc: str
    reentry_count: int = 0
    sequence_anomaly: int = 0


def deterministic_episode_id(ticker: str, direction: str, primary_alert_id: int) -> str:
    return f"{ticker}:{direction}:{primary_alert_id}"


def _direction_for_exit(event: str) -> str:
    if event == "LONG_EXIT":
        return "LONG"
    if event == "SHORT_EXIT":
        return "SHORT"
    raise ValueError(f"not an exit event: {event}")


def _insert_episode(connection: sqlite3.Connection, active: ActiveEpisode) -> None:
    connection.execute(
        """
        INSERT INTO episodes (
            episode_id, ticker, direction, primary_alert_id, started_at_utc,
            exit_alert_id, exited_at_utc, episode_status, exit_missing,
            sequence_anomaly
        ) VALUES (?, ?, ?, ?, ?, NULL, NULL, 'OPEN', 1, 0)
        """,
        (
            active.episode_id,
            active.ticker,
            active.direction,
            active.primary_alert_id,
            active.started_at_utc,
        ),
    )
    connection.execute(
        """
        INSERT INTO episode_events (episode_id, raw_alert_id, event_role, reentry_index)
        VALUES (?, ?, 'PRIMARY_ALERT', NULL)
        """,
        (active.episode_id, active.primary_alert_id),
    )


def _record_anomaly(
    connection: sqlite3.Connection,
    *,
    raw_alert_id: int,
    ticker: str,
    event: str,
    state_before: str,
    reason: str,
    related_episode_id: str | None,
    created_at_utc: str,
) -> None:
    connection.execute(
        """
        INSERT INTO episode_build_anomalies (
            raw_alert_id, ticker, event, state_before, reason,
            related_episode_id, created_at_utc
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            raw_alert_id,
            ticker,
            event,
            state_before,
            reason,
            related_episode_id,
            created_at_utc,
        ),
    )


def rebuild_episodes(
    connection: sqlite3.Connection, *, built_at_utc: str
) -> EpisodeBuildResult:
    """Rebuild source-alert episodes from immutable raw alerts.

    This is chronology labelling only. Exit information is stored as a later event
    and must never be used by entry-time feature filters.
    """
    rows = connection.execute(
        """
        SELECT cloudflare_id, ticker, event, fired_at_utc
        FROM raw_alerts
        ORDER BY cloudflare_id ASC
        """
    ).fetchall()

    active_by_ticker: dict[str, ActiveEpisode] = {}
    reentry_count = 0
    anomaly_count = 0
    ignored_opposite_count = 0

    connection.execute("BEGIN IMMEDIATE")
    try:
        connection.execute("DELETE FROM episode_events")
        connection.execute("DELETE FROM episode_build_anomalies")
        connection.execute("DELETE FROM episodes")

        for raw in rows:
            raw_alert_id = int(raw["cloudflare_id"])
            ticker = str(raw["ticker"])
            event = str(raw["event"])
            fired_at_utc = str(raw["fired_at_utc"])
            active = active_by_ticker.get(ticker)
            state_before = "IDLE" if active is None else f"ACTIVE_{active.direction}"

            if event in ENTRY_EVENTS:
                if active is None:
                    new_active = ActiveEpisode(
                        episode_id=deterministic_episode_id(ticker, event, raw_alert_id),
                        ticker=ticker,
                        direction=event,
                        primary_alert_id=raw_alert_id,
                        started_at_utc=fired_at_utc,
                    )
                    _insert_episode(connection, new_active)
                    active_by_ticker[ticker] = new_active
                    continue

                if event == active.direction:
                    active.reentry_count += 1
                    reentry_count += 1
                    connection.execute(
                        """
                        INSERT INTO episode_events (
                            episode_id, raw_alert_id, event_role, reentry_index
                        ) VALUES (?, ?, 'REENTRY_ALERT', ?)
                        """,
                        (active.episode_id, raw_alert_id, active.reentry_count),
                    )
                    continue

                active.sequence_anomaly = 1
                ignored_opposite_count += 1
                anomaly_count += 1
                connection.execute(
                    """
                    INSERT INTO episode_events (
                        episode_id, raw_alert_id, event_role, reentry_index
                    ) VALUES (?, ?, 'OPPOSITE_ALERT_IGNORED', NULL)
                    """,
                    (active.episode_id, raw_alert_id),
                )
                connection.execute(
                    "UPDATE episodes SET sequence_anomaly = 1 WHERE episode_id = ?",
                    (active.episode_id,),
                )
                _record_anomaly(
                    connection,
                    raw_alert_id=raw_alert_id,
                    ticker=ticker,
                    event=event,
                    state_before=state_before,
                    reason="OPPOSITE_ENTRY_BEFORE_EXIT",
                    related_episode_id=active.episode_id,
                    created_at_utc=built_at_utc,
                )
                continue

            if event in EXIT_EVENTS:
                exit_direction = _direction_for_exit(event)
                if active is None:
                    anomaly_count += 1
                    _record_anomaly(
                        connection,
                        raw_alert_id=raw_alert_id,
                        ticker=ticker,
                        event=event,
                        state_before=state_before,
                        reason="ORPHAN_EXIT_WHILE_IDLE",
                        related_episode_id=None,
                        created_at_utc=built_at_utc,
                    )
                    continue

                if exit_direction != active.direction:
                    active.sequence_anomaly = 1
                    ignored_opposite_count += 1
                    anomaly_count += 1
                    connection.execute(
                        """
                        INSERT INTO episode_events (
                            episode_id, raw_alert_id, event_role, reentry_index
                        ) VALUES (?, ?, 'OPPOSITE_EXIT_IGNORED', NULL)
                        """,
                        (active.episode_id, raw_alert_id),
                    )
                    connection.execute(
                        "UPDATE episodes SET sequence_anomaly = 1 WHERE episode_id = ?",
                        (active.episode_id,),
                    )
                    _record_anomaly(
                        connection,
                        raw_alert_id=raw_alert_id,
                        ticker=ticker,
                        event=event,
                        state_before=state_before,
                        reason="OPPOSITE_EXIT_BEFORE_ACTIVE_EXIT",
                        related_episode_id=active.episode_id,
                        created_at_utc=built_at_utc,
                    )
                    continue

                connection.execute(
                    """
                    INSERT INTO episode_events (
                        episode_id, raw_alert_id, event_role, reentry_index
                    ) VALUES (?, ?, 'EXIT_ALERT', NULL)
                    """,
                    (active.episode_id, raw_alert_id),
                )
                connection.execute(
                    """
                    UPDATE episodes
                    SET exit_alert_id = ?, exited_at_utc = ?, episode_status = 'CLOSED',
                        exit_missing = 0, sequence_anomaly = ?
                    WHERE episode_id = ?
                    """,
                    (
                        raw_alert_id,
                        fired_at_utc,
                        active.sequence_anomaly,
                        active.episode_id,
                    ),
                )
                del active_by_ticker[ticker]
                continue

            anomaly_count += 1
            _record_anomaly(
                connection,
                raw_alert_id=raw_alert_id,
                ticker=ticker,
                event=event,
                state_before=state_before,
                reason="UNSUPPORTED_EVENT_IN_RAW_ALERTS",
                related_episode_id=None if active is None else active.episode_id,
                created_at_utc=built_at_utc,
            )

        for active in active_by_ticker.values():
            connection.execute(
                """
                UPDATE episodes
                SET episode_status = 'OPEN', exit_missing = 1,
                    sequence_anomaly = ?
                WHERE episode_id = ?
                """,
                (active.sequence_anomaly, active.episode_id),
            )

        counts = connection.execute(
            """
            SELECT
                COUNT(*) AS episode_count,
                SUM(CASE WHEN episode_status = 'CLOSED' THEN 1 ELSE 0 END) AS closed_count,
                SUM(CASE WHEN episode_status = 'OPEN' THEN 1 ELSE 0 END) AS open_count
            FROM episodes
            """
        ).fetchone()
        latest_raw_id = max((int(row["cloudflare_id"]) for row in rows), default=0)
        result = EpisodeBuildResult(
            raw_alert_count=len(rows),
            episode_count=int(counts["episode_count"] or 0),
            closed_episode_count=int(counts["closed_count"] or 0),
            open_episode_count=int(counts["open_count"] or 0),
            reentry_count=reentry_count,
            anomaly_count=anomaly_count,
            ignored_opposite_count=ignored_opposite_count,
            latest_raw_id=latest_raw_id,
        )
        connection.execute(
            """
            INSERT INTO episode_build_runs (
                built_at_utc, raw_alert_count, episode_count,
                closed_episode_count, open_episode_count, reentry_count,
                anomaly_count, ignored_opposite_count, latest_raw_id,
                audit_only, future_entry_fields_used
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, 0)
            """,
            (
                built_at_utc,
                result.raw_alert_count,
                result.episode_count,
                result.closed_episode_count,
                result.open_episode_count,
                result.reentry_count,
                result.anomaly_count,
                result.ignored_opposite_count,
                result.latest_raw_id,
            ),
        )
        connection.commit()
        return result
    except Exception:
        connection.rollback()
        raise
