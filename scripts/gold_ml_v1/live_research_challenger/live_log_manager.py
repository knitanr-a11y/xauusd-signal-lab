from __future__ import annotations

import gzip
import json
import os
import re
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd

from live_store import atomic_write_csv, atomic_write_text

SHORT_LOG_RETENTION_DAYS = 31
SHORT_LOG_COMPRESS_AFTER_DAYS = 7

CANDIDATE_INDEX_COLUMNS = [
    "candidate_key",
    "candidate_id",
    "comp",
    "decision_time",
    "execution_status",
    "trade_state",
    "first_recorded_at",
    "last_recorded_at",
]

TRADE_INDEX_COLUMNS = [
    "candidate_key",
    "candidate_id",
    "comp",
    "direction",
    "decision_time",
    "requested_at",
    "closed_at",
    "execution_status",
    "live_result",
    "symbol",
    "volume",
    "order_ticket",
    "deal_ticket",
    "position_ticket",
    "fill_price",
    "stop_price",
    "target_price",
    "net_profit",
    "archive_file",
    "archived_at",
]

MONTHLY_SUMMARY_COLUMNS = [
    "month",
    "comp",
    "trades",
    "wins",
    "losses_or_flat",
    "win_rate",
    "net_profit",
]

_DATE_PATTERN = re.compile(r"(?P<date>\d{4}-\d{2}-\d{2})")


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and np.isnan(value):
        return ""
    return str(value).strip()


def _timestamp(value: Any) -> pd.Timestamp | None:
    text = _text(value)
    if not text:
        return None
    parsed = pd.to_datetime(text, errors="coerce")
    return None if pd.isna(parsed) else pd.Timestamp(parsed)


def _daily_path(output_dir: Path, category: str, stem: str, now: pd.Timestamp) -> Path:
    return (
        output_dir
        / "logs"
        / category
        / now.strftime("%Y")
        / now.strftime("%m")
        / f"{stem}_{now.strftime('%Y-%m-%d')}.jsonl"
    )


def append_short_log(
    output_dir: Path,
    *,
    category: str,
    stem: str,
    payload: dict[str, Any],
    now: pd.Timestamp,
) -> Path:
    path = _daily_path(output_dir, category, stem, now)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
        handle.write("\n")
    return path


def append_notification_log(
    output_dir: Path,
    *,
    now_text: str,
    status: str,
    content: str,
    username: str,
    error: str | None = None,
) -> Path:
    now = pd.Timestamp(now_text)
    first_line = content.splitlines()[0] if content else ""
    event_type = "EXIT" if "決済" in first_line else "ENTRY"
    return append_short_log(
        output_dir,
        category="notifications",
        stem="discord",
        now=now,
        payload={
            "time": now.strftime("%Y-%m-%d %H:%M:%S"),
            "event_type": event_type,
            "status": status,
            "username": username,
            "content": content,
            "error": error,
        },
    )


def ingest_root_runtime_logs(output_dir: Path, now_text: str) -> list[str]:
    """Move append-only root JSONL logs into daily short-retention partitions."""

    moved: list[str] = []
    now = pd.Timestamp(now_text)
    sources = {
        "live_audit.jsonl": "candidate_runtime",
        "live_execution_audit.jsonl": "execution_runtime",
    }
    for filename, stem in sources.items():
        source = output_dir / filename
        if not source.is_file() or source.stat().st_size == 0:
            continue
        target = _daily_path(output_dir, "runtime", stem, now)
        target.parent.mkdir(parents=True, exist_ok=True)
        with source.open("r", encoding="utf-8") as src, target.open(
            "a", encoding="utf-8", newline="\n"
        ) as dst:
            for line in src:
                if line.strip():
                    dst.write(line.rstrip("\r\n") + "\n")
        source.unlink(missing_ok=True)
        moved.append(str(target.relative_to(output_dir)))
    return moved


def _log_date(path: Path) -> pd.Timestamp | None:
    match = _DATE_PATTERN.search(path.name)
    if match:
        parsed = pd.to_datetime(match.group("date"), errors="coerce")
        if not pd.isna(parsed):
            return pd.Timestamp(parsed).normalize()
    try:
        return pd.Timestamp(path.stat().st_mtime, unit="s").normalize()
    except OSError:
        return None


def _gzip_file(path: Path) -> Path:
    target = path.with_suffix(path.suffix + ".gz")
    temporary = target.with_name(target.name + f".tmp.{os.getpid()}")
    with path.open("rb") as src, gzip.open(temporary, "wb", compresslevel=6) as dst:
        while True:
            chunk = src.read(1024 * 1024)
            if not chunk:
                break
            dst.write(chunk)
    os.replace(temporary, target)
    path.unlink(missing_ok=True)
    return target


def prune_and_compress_short_logs(output_dir: Path, now_text: str) -> dict[str, int]:
    now = pd.Timestamp(now_text).normalize()
    deleted = 0
    compressed = 0
    for category in ("notifications", "runtime"):
        root = output_dir / "logs" / category
        if not root.is_dir():
            continue
        files = sorted(
            path
            for path in root.rglob("*")
            if path.is_file() and (path.name.endswith(".jsonl") or path.name.endswith(".jsonl.gz") or path.name.endswith(".log") or path.name.endswith(".log.gz"))
        )
        for path in files:
            dated = _log_date(path)
            if dated is None:
                continue
            age_days = int((now - dated).days)
            if age_days > SHORT_LOG_RETENTION_DAYS:
                path.unlink(missing_ok=True)
                deleted += 1
            elif age_days > SHORT_LOG_COMPRESS_AFTER_DAYS and not path.name.endswith(".gz"):
                _gzip_file(path)
                compressed += 1
        for directory in sorted(root.rglob("*"), reverse=True):
            if directory.is_dir():
                try:
                    directory.rmdir()
                except OSError:
                    pass
    return {"deleted": deleted, "compressed": compressed}


def _read_csv(path: Path, columns: Iterable[str]) -> pd.DataFrame:
    requested = list(columns)
    if not path.is_file():
        return pd.DataFrame(columns=requested)
    frame = pd.read_csv(path, dtype=object)
    for column in requested:
        if column not in frame.columns:
            frame[column] = ""
    return frame[requested].copy()


def load_candidate_key_index(output_dir: Path) -> pd.DataFrame:
    return _read_csv(
        output_dir / "state" / "candidate_key_index.csv",
        CANDIDATE_INDEX_COLUMNS,
    )


def known_candidate_keys(output_dir: Path) -> set[str]:
    frame = load_candidate_key_index(output_dir)
    if frame.empty:
        return set()
    return set(frame["candidate_key"].astype(str))


def _upsert_by_key(
    existing: pd.DataFrame,
    addition: pd.DataFrame,
    *,
    columns: list[str],
) -> pd.DataFrame:
    if existing.empty and addition.empty:
        return pd.DataFrame(columns=columns)
    combined = pd.concat([existing, addition], ignore_index=True)
    combined = combined[columns]
    combined = combined.drop_duplicates("candidate_key", keep="last")
    return combined.sort_values(
        [column for column in ("decision_time", "comp", "candidate_key") if column in columns],
        kind="mergesort",
    ).reset_index(drop=True)


def update_candidate_key_index(
    output_dir: Path,
    ledger: pd.DataFrame,
    now_text: str,
) -> pd.DataFrame:
    path = output_dir / "state" / "candidate_key_index.csv"
    existing = _read_csv(path, CANDIDATE_INDEX_COLUMNS)
    if ledger.empty:
        return existing
    old_first = (
        existing.set_index("candidate_key")["first_recorded_at"].to_dict()
        if not existing.empty
        else {}
    )
    rows: list[dict[str, Any]] = []
    for row in ledger.to_dict(orient="records"):
        key = _text(row.get("candidate_key"))
        if not key:
            continue
        rows.append(
            {
                "candidate_key": key,
                "candidate_id": _text(row.get("candidate_id")),
                "comp": _text(row.get("comp")),
                "decision_time": _text(row.get("decision_time")),
                "execution_status": _text(row.get("execution_status")),
                "trade_state": _text(row.get("trade_state")),
                "first_recorded_at": _text(old_first.get(key)) or now_text,
                "last_recorded_at": now_text,
            }
        )
    addition = pd.DataFrame(rows, columns=CANDIDATE_INDEX_COLUMNS)
    updated = _upsert_by_key(existing, addition, columns=CANDIDATE_INDEX_COLUMNS)
    atomic_write_csv(path, updated)
    return updated


def _has_ticket(row: pd.Series) -> bool:
    return any(
        _text(row.get(column))
        for column in ("order_ticket", "deal_ticket", "position_ticket")
    )


def _archivable_trade_rows(ledger: pd.DataFrame) -> pd.DataFrame:
    if ledger.empty:
        return ledger.copy()
    closed = ledger[ledger["trade_state"].astype(str).eq("CLOSED")].copy()
    if closed.empty:
        return closed
    actual = closed.apply(_has_ticket, axis=1)
    notified = ~closed["exit_discord_sent_at"].fillna("").astype(str).str.strip().eq("")
    return closed[actual & notified].copy()


def _archive_month(row: pd.Series) -> str:
    closed = _timestamp(row.get("closed_at"))
    decision = _timestamp(row.get("decision_time"))
    basis = closed or decision
    if basis is None:
        raise ValueError(f"trade {row.get('candidate_key')} has no archive date")
    return basis.strftime("%Y-%m")


def _monthly_archive_path(output_dir: Path, month: str) -> Path:
    year = month[:4]
    return output_dir / "trades" / year / f"live_trades_{month}.csv"


def _trade_index_rows(
    archived: pd.DataFrame,
    archive_paths: dict[str, str],
    now_text: str,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for row in archived.to_dict(orient="records"):
        key = _text(row.get("candidate_key"))
        rows.append(
            {
                "candidate_key": key,
                "candidate_id": _text(row.get("candidate_id")),
                "comp": _text(row.get("comp")),
                "direction": _text(row.get("direction")),
                "decision_time": _text(row.get("decision_time")),
                "requested_at": _text(row.get("requested_at")),
                "closed_at": _text(row.get("closed_at")),
                "execution_status": _text(row.get("execution_status")),
                "live_result": _text(row.get("live_result")),
                "symbol": _text(row.get("symbol")),
                "volume": _text(row.get("volume")),
                "order_ticket": _text(row.get("order_ticket")),
                "deal_ticket": _text(row.get("deal_ticket")),
                "position_ticket": _text(row.get("position_ticket")),
                "fill_price": _text(row.get("fill_price")),
                "stop_price": _text(row.get("stop_price")),
                "target_price": _text(row.get("target_price")),
                "net_profit": _text(row.get("net_profit")),
                "archive_file": archive_paths[key],
                "archived_at": now_text,
            }
        )
    return pd.DataFrame(rows, columns=TRADE_INDEX_COLUMNS)


def load_trade_index(output_dir: Path) -> pd.DataFrame:
    return _read_csv(output_dir / "trades" / "trade_index.csv", TRADE_INDEX_COLUMNS)


def _write_monthly_summary(output_dir: Path, trade_index: pd.DataFrame) -> None:
    path = output_dir / "trades" / "monthly_summary.csv"
    if trade_index.empty:
        atomic_write_csv(path, pd.DataFrame(columns=MONTHLY_SUMMARY_COLUMNS))
        return
    frame = trade_index.copy()
    frame["closed_dt"] = pd.to_datetime(frame["closed_at"], errors="coerce")
    frame = frame[frame["closed_dt"].notna()].copy()
    frame["month"] = frame["closed_dt"].dt.strftime("%Y-%m")
    frame["is_win"] = frame["live_result"].astype(str).eq("WIN").astype(int)
    frame["net_numeric"] = pd.to_numeric(frame["net_profit"], errors="coerce").fillna(0.0)
    grouped = (
        frame.groupby(["month", "comp"], dropna=False)
        .agg(trades=("candidate_key", "count"), wins=("is_win", "sum"), net_profit=("net_numeric", "sum"))
        .reset_index()
    )
    grouped["losses_or_flat"] = grouped["trades"] - grouped["wins"]
    grouped["win_rate"] = grouped["wins"] / grouped["trades"]
    grouped = grouped[MONTHLY_SUMMARY_COLUMNS].sort_values(
        ["month", "comp"], kind="mergesort"
    )
    atomic_write_csv(path, grouped.reset_index(drop=True))


def archive_closed_trades(
    output_dir: Path,
    ledger: pd.DataFrame,
    now_text: str,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    update_candidate_key_index(output_dir, ledger, now_text)
    archived = _archivable_trade_rows(ledger)
    if archived.empty:
        return ledger, {"archived_trades": 0, "operational_rows": int(len(ledger))}

    archive_paths: dict[str, str] = {}
    archived_keys: set[str] = set()
    for month, group in archived.assign(
        _archive_month=archived.apply(_archive_month, axis=1)
    ).groupby("_archive_month", sort=True):
        path = _monthly_archive_path(output_dir, str(month))
        existing = pd.read_csv(path, dtype=object) if path.is_file() else pd.DataFrame(columns=ledger.columns)
        for column in ledger.columns:
            if column not in existing.columns:
                existing[column] = ""
        addition = group.drop(columns=["_archive_month"])[list(ledger.columns)].copy()
        monthly = _upsert_by_key(existing[list(ledger.columns)], addition, columns=list(ledger.columns))
        atomic_write_csv(path, monthly)
        relative = str(path.relative_to(output_dir)).replace("\\", "/")
        for key in addition["candidate_key"].astype(str):
            archive_paths[key] = relative
            archived_keys.add(key)

    trade_index_path = output_dir / "trades" / "trade_index.csv"
    existing_index = _read_csv(trade_index_path, TRADE_INDEX_COLUMNS)
    addition_index = _trade_index_rows(archived, archive_paths, now_text)
    updated_index = _upsert_by_key(
        existing_index, addition_index, columns=TRADE_INDEX_COLUMNS
    )
    atomic_write_csv(trade_index_path, updated_index)
    _write_monthly_summary(output_dir, updated_index)

    compacted = ledger[
        ~ledger["candidate_key"].astype(str).isin(archived_keys)
    ].copy()
    return compacted, {
        "archived_trades": int(len(archived_keys)),
        "operational_rows": int(len(compacted)),
        "trade_index_rows": int(len(updated_index)),
    }


def purge_old_non_trade_rows(
    ledger: pd.DataFrame,
    now_text: str,
) -> tuple[pd.DataFrame, int]:
    if ledger.empty:
        return ledger, 0
    cutoff = pd.Timestamp(now_text) - pd.Timedelta(days=SHORT_LOG_RETENTION_DAYS)
    decision = pd.to_datetime(ledger["decision_time"], errors="coerce")
    has_ticket = ledger.apply(_has_ticket, axis=1)
    active = ledger["trade_state"].astype(str).eq("OPEN")
    old = decision.notna() & decision.lt(cutoff)
    purge = old & ~has_ticket & ~active
    purged = int(purge.sum())
    return ledger[~purge].copy(), purged


def combined_live_trade_frame(output_dir: Path, operational: pd.DataFrame) -> pd.DataFrame:
    archived = load_trade_index(output_dir)
    frames: list[pd.DataFrame] = []
    if not archived.empty:
        frames.append(
            pd.DataFrame(
                {
                    "candidate_key": archived["candidate_key"],
                    "comp": archived["comp"],
                    "trade_state": "CLOSED",
                    "live_result": archived["live_result"],
                }
            )
        )
    if not operational.empty:
        required = ["candidate_key", "comp", "trade_state", "live_result"]
        if set(required).issubset(operational.columns):
            frames.append(operational[required].copy())
    if not frames:
        return pd.DataFrame(columns=["candidate_key", "comp", "trade_state", "live_result"])
    combined = pd.concat(frames, ignore_index=True)
    return combined.drop_duplicates("candidate_key", keep="last").reset_index(drop=True)


def maintain_logs_and_trades(
    output_dir: Path,
    *,
    ledger: pd.DataFrame,
    now_text: str,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    compacted, trade_stats = archive_closed_trades(output_dir, ledger, now_text)
    compacted, purged = purge_old_non_trade_rows(compacted, now_text)
    moved = ingest_root_runtime_logs(output_dir, now_text)
    short_stats = prune_and_compress_short_logs(output_dir, now_text)
    manifest = {
        "schema_version": 1,
        "updated_at": now_text,
        "notification_retention_days": SHORT_LOG_RETENTION_DAYS,
        "runtime_log_retention_days": SHORT_LOG_RETENTION_DAYS,
        "trade_retention": "permanent_monthly_csv",
        "trade_index": "trades/trade_index.csv",
        "monthly_summary": "trades/monthly_summary.csv",
        "candidate_key_index": "state/candidate_key_index.csv",
        "operational_ledger": "live_execution_ledger.csv",
        "archived_trades": trade_stats.get("archived_trades", 0),
        "operational_rows": int(len(compacted)),
        "purged_old_non_trade_rows": purged,
        "ingested_runtime_logs": moved,
        "short_log_files_deleted": short_stats["deleted"],
        "short_log_files_compressed": short_stats["compressed"],
    }
    atomic_write_text(
        output_dir / "log_manifest.json",
        json.dumps(manifest, ensure_ascii=False, indent=2),
    )
    return compacted, manifest
