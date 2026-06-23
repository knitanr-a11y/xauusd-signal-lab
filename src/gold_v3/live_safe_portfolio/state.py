from __future__ import annotations

from contextlib import contextmanager
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
import json
import sqlite3
from typing import Iterator

from .models import Candidate, Decision, Resolution
from .timeutil import dt_to_text, parse_dt


SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS portfolio_state(
 id INTEGER PRIMARY KEY CHECK(id=1), equity REAL NOT NULL DEFAULT 0,
 peak_equity REAL NOT NULL DEFAULT 0, last_candidate_entry_dt TEXT,
 last_candidate_loss_exit_dt TEXT, last_applied_exit_dt TEXT,
 last_processed_entry_dt TEXT, last_processed_priority INTEGER,
 time_basis TEXT NOT NULL, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS candidates(
 candidate_id TEXT PRIMARY KEY, source TEXT NOT NULL, direction TEXT NOT NULL,
 signal_dt TEXT NOT NULL, entry_dt TEXT NOT NULL,
 max_holding_minutes INTEGER NOT NULL, status TEXT NOT NULL,
 accepted INTEGER NOT NULL, decision_reason TEXT NOT NULL,
 priority INTEGER NOT NULL, dd_before_entry REAL NOT NULL,
 payload_json TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_candidates_entry ON candidates(entry_dt,priority);
CREATE TABLE IF NOT EXISTS resolutions(
 candidate_id TEXT PRIMARY KEY REFERENCES candidates(candidate_id),
 exit_dt TEXT NOT NULL, pnl REAL NOT NULL, exit_reason TEXT NOT NULL,
 observed_asof TEXT, applied INTEGER NOT NULL DEFAULT 0,
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_resolutions_apply ON resolutions(applied,exit_dt);
CREATE TABLE IF NOT EXISTS decisions(
 seq INTEGER PRIMARY KEY AUTOINCREMENT, candidate_id TEXT NOT NULL,
 status TEXT NOT NULL, reason TEXT NOT NULL, entry_dt TEXT NOT NULL,
 dd_before_entry REAL NOT NULL, equity_before_entry REAL NOT NULL,
 peak_before_entry REAL NOT NULL, diagnostics_json TEXT NOT NULL,
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


class SQLiteStateStore:
    def __init__(self, path: str | Path, time_basis: str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.time_basis = time_basis
        with sqlite3.connect(self.path) as conn:
            conn.executescript(SCHEMA)
            row = conn.execute("SELECT time_basis FROM portfolio_state WHERE id=1").fetchone()
            if row is None:
                conn.execute("INSERT INTO portfolio_state(id,time_basis) VALUES(1,?)", (time_basis,))
            elif row[0] != time_basis:
                raise ValueError("database time_basis differs from config")

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("BEGIN IMMEDIATE")
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def get_state(self, conn: sqlite3.Connection) -> dict:
        return dict(conn.execute("SELECT * FROM portfolio_state WHERE id=1").fetchone())

    def candidate_exists(self, conn: sqlite3.Connection, candidate_id: str) -> bool:
        return conn.execute("SELECT 1 FROM candidates WHERE candidate_id=?", (candidate_id,)).fetchone() is not None

    def active_position_at(self, conn: sqlite3.Connection, current_dt: datetime):
        return conn.execute(
            """SELECT c.* FROM candidates c LEFT JOIN resolutions r USING(candidate_id)
               WHERE c.accepted=1 AND (r.candidate_id IS NULL OR r.exit_dt>?)
               ORDER BY c.entry_dt LIMIT 1""",
            (dt_to_text(current_dt),),
        ).fetchone()

    def active_position(self, conn: sqlite3.Connection):
        return conn.execute(
            """SELECT c.* FROM candidates c LEFT JOIN resolutions r USING(candidate_id)
               WHERE c.accepted=1 AND r.candidate_id IS NULL
               ORDER BY c.entry_dt LIMIT 1"""
        ).fetchone()

    def insert_candidate(self, conn, candidate: Candidate, decision: Decision, priority: int) -> None:
        payload = asdict(candidate)
        payload.update({
            "source": candidate.source.value,
            "direction": candidate.direction.value,
            "signal_dt": dt_to_text(candidate.signal_dt),
            "entry_dt": dt_to_text(candidate.entry_dt),
            "features_asof": dt_to_text(candidate.features_asof),
            "closed_bar_time": dt_to_text(candidate.closed_bar_time),
        })
        accepted = int(decision.status.value == "ACCEPTED_SHADOW")
        conn.execute(
            """INSERT INTO candidates(candidate_id,source,direction,signal_dt,entry_dt,
               max_holding_minutes,status,accepted,decision_reason,priority,
               dd_before_entry,payload_json) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
            (candidate.candidate_id, candidate.source.value, candidate.direction.value,
             dt_to_text(candidate.signal_dt), dt_to_text(candidate.entry_dt),
             candidate.max_holding_minutes, decision.status.value, accepted,
             decision.reason, priority, decision.dd_before_entry,
             json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)),
        )
        conn.execute(
            """INSERT INTO decisions(candidate_id,status,reason,entry_dt,dd_before_entry,
               equity_before_entry,peak_before_entry,diagnostics_json)
               VALUES(?,?,?,?,?,?,?,?)""",
            (candidate.candidate_id, decision.status.value, decision.reason,
             dt_to_text(candidate.entry_dt), decision.dd_before_entry,
             decision.equity_before_entry, decision.peak_before_entry,
             json.dumps(decision.diagnostics, ensure_ascii=False, sort_keys=True, default=str)),
        )
        conn.execute(
            "UPDATE portfolio_state SET last_processed_entry_dt=?,last_processed_priority=?,updated_at=CURRENT_TIMESTAMP WHERE id=1",
            (dt_to_text(candidate.entry_dt), priority),
        )
        if accepted and candidate.source.value != "BASE":
            conn.execute(
                "UPDATE portfolio_state SET last_candidate_entry_dt=?,updated_at=CURRENT_TIMESTAMP WHERE id=1",
                (dt_to_text(candidate.entry_dt),),
            )

    def add_resolution(self, resolution: Resolution) -> None:
        resolution.validate()
        with self.transaction() as conn:
            row = conn.execute("SELECT accepted,entry_dt FROM candidates WHERE candidate_id=?", (resolution.candidate_id,)).fetchone()
            if row is None:
                raise ValueError("unknown candidate_id")
            if not bool(row["accepted"]):
                raise ValueError("cannot resolve a rejected candidate")
            if resolution.exit_dt < parse_dt(row["entry_dt"]):
                raise ValueError("exit_dt is earlier than entry_dt")
            conn.execute(
                """INSERT INTO resolutions(candidate_id,exit_dt,pnl,exit_reason,observed_asof,applied)
                   VALUES(?,?,?,?,?,0)
                   ON CONFLICT(candidate_id) DO UPDATE SET exit_dt=excluded.exit_dt,
                   pnl=excluded.pnl,exit_reason=excluded.exit_reason,
                   observed_asof=excluded.observed_asof WHERE resolutions.applied=0""",
                (resolution.candidate_id, dt_to_text(resolution.exit_dt), resolution.pnl,
                 resolution.exit_reason, dt_to_text(resolution.observed_asof)),
            )

    def apply_resolved_through(self, conn, current_entry_dt: datetime) -> list[dict]:
        rows = conn.execute(
            """SELECT r.*,c.source FROM resolutions r JOIN candidates c USING(candidate_id)
               WHERE r.applied=0 AND c.accepted=1 AND r.exit_dt<=?
               ORDER BY r.exit_dt,r.candidate_id""",
            (dt_to_text(current_entry_dt),),
        ).fetchall()
        applied = []
        for row in rows:
            state = self.get_state(conn)
            equity = float(state["equity"]) + float(row["pnl"])
            peak = max(float(state["peak_equity"]), equity)
            last_loss = state["last_candidate_loss_exit_dt"]
            if row["source"] != "BASE" and float(row["pnl"]) < 0:
                last_loss = row["exit_dt"]
            conn.execute(
                """UPDATE portfolio_state SET equity=?,peak_equity=?,
                   last_candidate_loss_exit_dt=?,last_applied_exit_dt=?,
                   updated_at=CURRENT_TIMESTAMP WHERE id=1""",
                (equity, peak, last_loss, row["exit_dt"]),
            )
            conn.execute("UPDATE resolutions SET applied=1 WHERE candidate_id=?", (row["candidate_id"],))
            applied.append({"candidate_id": row["candidate_id"], "source": row["source"],
                            "exit_dt": row["exit_dt"], "pnl": float(row["pnl"]),
                            "equity_after": equity, "peak_after": peak})
        return applied

    def snapshot(self) -> dict:
        with self.transaction() as conn:
            state = self.get_state(conn)
            active = self.active_position(conn)
            counts = conn.execute("SELECT status,COUNT(*) n FROM candidates GROUP BY status").fetchall()
            return {
                "equity": float(state["equity"]),
                "peak_equity": float(state["peak_equity"]),
                "realized_dd": float(state["peak_equity"]) - float(state["equity"]),
                "last_candidate_entry_dt": state["last_candidate_entry_dt"],
                "last_candidate_loss_exit_dt": state["last_candidate_loss_exit_dt"],
                "last_applied_exit_dt": state["last_applied_exit_dt"],
                "last_processed_entry_dt": state["last_processed_entry_dt"],
                "last_processed_priority": state["last_processed_priority"],
                "active_candidate_id": active["candidate_id"] if active else None,
                "counts": {row["status"]: row["n"] for row in counts},
                "time_basis": state["time_basis"],
            }

    def replace_state_for_bootstrap(self, *, equity: float, peak_equity: float,
                                    last_candidate_entry_dt: datetime | None,
                                    last_candidate_loss_exit_dt: datetime | None,
                                    last_applied_exit_dt: datetime | None,
                                    last_processed_entry_dt: datetime | None = None,
                                    last_processed_priority: int | None = None) -> None:
        if peak_equity < equity:
            raise ValueError("peak_equity cannot be below equity")
        with self.transaction() as conn:
            if conn.execute("SELECT COUNT(*) FROM candidates").fetchone()[0] != 0:
                raise ValueError("bootstrap requires an empty candidate database")
            conn.execute(
                """UPDATE portfolio_state SET equity=?,peak_equity=?,
                   last_candidate_entry_dt=?,last_candidate_loss_exit_dt=?,
                   last_applied_exit_dt=?,last_processed_entry_dt=?,
                   last_processed_priority=?,updated_at=CURRENT_TIMESTAMP WHERE id=1""",
                (equity, peak_equity, dt_to_text(last_candidate_entry_dt),
                 dt_to_text(last_candidate_loss_exit_dt), dt_to_text(last_applied_exit_dt),
                 dt_to_text(last_processed_entry_dt), last_processed_priority),
            )
