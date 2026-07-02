from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import shutil
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np

SYMBOL = "BTCUSD#"
DEFAULT_OUTPUT_DIR = Path("Files")
DEFAULT_START = "2017-01-01"
TIMEFRAME_SECONDS = {
    "M1": 60,
    "M5": 5 * 60,
    "M15": 15 * 60,
    "H1": 60 * 60,
    "H4": 4 * 60 * 60,
    "D1": 24 * 60 * 60,
}
CHUNK_DAYS = {
    "M1": 31,
    "M5": 124,
    "M15": 366,
    "H1": 1098,
    "H4": 3660,
    "D1": 20000,
}
RESEARCH_MINIMUM_ROWS = {
    "M1": 100_000,
    "M5": 30_000,
    "M15": 10_000,
    "H1": 5_000,
    "H4": 1_000,
    "D1": 365,
}
FILE_BY_TIMEFRAME = {
    timeframe: f"btcusdsharp_{timeframe.lower()}.csv"
    for timeframe in TIMEFRAME_SECONDS
}
CSV_COLUMNS = [
    "time",
    "open",
    "high",
    "low",
    "close",
    "tick_volume",
    "spread",
    "real_volume",
]


@dataclass(frozen=True)
class TimeframeExport:
    timeframe: str
    path: str
    rows: int
    first_time_utc: str
    last_time_utc: str
    requested_start_utc: str
    requested_end_utc: str
    chunk_calls: int
    chunks_with_data: int
    duplicate_rows_replaced: int
    gaps_over_one_bar: int
    maximum_gap_seconds: int
    research_minimum_rows: int
    research_minimum_met: bool
    sha256: str


def _asdict(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return dict(value)
    method = getattr(value, "_asdict", None)
    if callable(method):
        return dict(method())
    return {
        name: getattr(value, name)
        for name in (
            "name",
            "description",
            "digits",
            "point",
            "trade_contract_size",
            "volume_min",
            "volume_step",
            "volume_max",
            "trade_tick_size",
            "trade_tick_value",
            "spread",
            "spread_float",
            "trade_stops_level",
            "filling_mode",
            "trade_mode",
            "maxbars",
            "company",
            "server",
            "currency",
        )
        if hasattr(value, name)
    }


def _json_value(value: Any) -> Any:
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        return None if not np.isfinite(value) else float(value)
    if isinstance(value, (np.bool_, bool)):
        return bool(value)
    return value


def _parse_utc(text: str, *, end_of_day: bool = False) -> datetime:
    normalized = text.strip().replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    parsed = parsed.astimezone(timezone.utc)
    if end_of_day and len(text.strip()) == 10:
        parsed += timedelta(days=1)
    return parsed


def _utc_text(epoch_seconds: int) -> str:
    return datetime.fromtimestamp(epoch_seconds, tz=timezone.utc).strftime(
        "%Y-%m-%d %H:%M:%S"
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _timeframe_constant(mt5: Any, timeframe: str) -> Any:
    return getattr(mt5, f"TIMEFRAME_{timeframe}")


def _connect(mt5: Any, args: argparse.Namespace) -> None:
    kwargs: dict[str, Any] = {}
    login = args.login or os.getenv("BTC0_MT5_LOGIN")
    password = args.password or os.getenv("BTC0_MT5_PASSWORD")
    server = args.server or os.getenv("BTC0_MT5_SERVER")
    if login:
        kwargs["login"] = int(login)
    if password:
        kwargs["password"] = password
    if server:
        kwargs["server"] = server
    terminal_path = args.terminal_path or os.getenv("BTC0_MT5_TERMINAL_PATH")
    initialized = (
        mt5.initialize(terminal_path, **kwargs)
        if terminal_path
        else mt5.initialize(**kwargs)
    )
    if not initialized:
        raise RuntimeError(f"MT5 initialize failed: {mt5.last_error()}")


def _select_symbol(mt5: Any) -> Any:
    info = mt5.symbol_info(SYMBOL)
    if info is None:
        raise RuntimeError(f"MT5 symbol not found: {SYMBOL}")
    if not bool(getattr(info, "visible", False)):
        if not mt5.symbol_select(SYMBOL, True):
            raise RuntimeError(f"MT5 symbol_select failed for {SYMBOL}: {mt5.last_error()}")
        info = mt5.symbol_info(SYMBOL)
    return info


def _acquire_lock(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as exc:
        raise RuntimeError(f"BTC history export is already running: {path}") from exc
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        handle.write(str(os.getpid()))


def _create_database(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(path)
    connection.execute("PRAGMA journal_mode=OFF")
    connection.execute("PRAGMA synchronous=OFF")
    connection.execute("PRAGMA temp_store=MEMORY")
    connection.execute(
        """
        CREATE TABLE bars (
            time_epoch INTEGER PRIMARY KEY,
            open REAL NOT NULL,
            high REAL NOT NULL,
            low REAL NOT NULL,
            close REAL NOT NULL,
            tick_volume INTEGER NOT NULL,
            spread INTEGER NOT NULL,
            real_volume INTEGER NOT NULL
        )
        """
    )
    return connection


def _closed_rows(
    raw_rates: Any,
    *,
    timeframe_seconds: int,
    snapshot_utc: datetime,
) -> list[tuple[int, float, float, float, float, int, int, int]]:
    if raw_rates is None:
        return []
    frame = np.asarray(raw_rates)
    if frame.size == 0:
        return []
    cutoff = int(snapshot_utc.timestamp())
    rows: list[tuple[int, float, float, float, float, int, int, int]] = []
    for raw in frame:
        epoch = int(raw["time"])
        if epoch + timeframe_seconds > cutoff:
            continue
        values = (
            epoch,
            float(raw["open"]),
            float(raw["high"]),
            float(raw["low"]),
            float(raw["close"]),
            int(raw["tick_volume"]),
            int(raw["spread"]),
            int(raw["real_volume"]),
        )
        if not all(np.isfinite(value) for value in values[1:5]):
            continue
        rows.append(values)
    rows.sort(key=lambda item: item[0])
    return rows


def _insert_rows(
    connection: sqlite3.Connection,
    rows: Iterable[tuple[int, float, float, float, float, int, int, int]],
) -> tuple[int, int]:
    before = int(connection.execute("SELECT COUNT(*) FROM bars").fetchone()[0])
    batch = list(rows)
    connection.executemany(
        """
        INSERT OR REPLACE INTO bars (
            time_epoch, open, high, low, close, tick_volume, spread, real_volume
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        batch,
    )
    connection.commit()
    after = int(connection.execute("SELECT COUNT(*) FROM bars").fetchone()[0])
    inserted = max(after - before, 0)
    replaced = max(len(batch) - inserted, 0)
    return inserted, replaced


def _write_csv_from_database(connection: sqlite3.Connection, path: Path) -> None:
    temporary = path.with_name(path.name + f".tmp.{os.getpid()}")
    with temporary.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(CSV_COLUMNS)
        cursor = connection.execute(
            """
            SELECT time_epoch, open, high, low, close,
                   tick_volume, spread, real_volume
            FROM bars ORDER BY time_epoch
            """
        )
        while True:
            rows = cursor.fetchmany(50_000)
            if not rows:
                break
            writer.writerows(
                [
                    (
                        _utc_text(int(row[0])),
                        row[1],
                        row[2],
                        row[3],
                        row[4],
                        int(row[5]),
                        int(row[6]),
                        int(row[7]),
                    )
                    for row in rows
                ]
            )
    os.replace(temporary, path)


def _gap_statistics(
    connection: sqlite3.Connection,
    timeframe_seconds: int,
) -> tuple[int, int]:
    cursor = connection.execute("SELECT time_epoch FROM bars ORDER BY time_epoch")
    previous: int | None = None
    gap_count = 0
    maximum_gap = 0
    while True:
        rows = cursor.fetchmany(100_000)
        if not rows:
            break
        for row in rows:
            current = int(row[0])
            if previous is not None:
                gap = current - previous
                if gap > timeframe_seconds:
                    gap_count += 1
                    maximum_gap = max(maximum_gap, gap)
            previous = current
    return gap_count, maximum_gap


def _export_timeframe(
    mt5: Any,
    *,
    timeframe: str,
    start_utc: datetime,
    end_utc: datetime,
    stage_dir: Path,
) -> TimeframeExport:
    seconds = TIMEFRAME_SECONDS[timeframe]
    database_path = stage_dir / f"{timeframe.lower()}.sqlite"
    connection = _create_database(database_path)
    calls = 0
    chunks_with_data = 0
    replacements = 0
    try:
        cursor = start_utc
        while cursor < end_utc:
            chunk_end = min(cursor + timedelta(days=CHUNK_DAYS[timeframe]), end_utc)
            raw = mt5.copy_rates_range(
                SYMBOL,
                _timeframe_constant(mt5, timeframe),
                cursor,
                chunk_end,
            )
            calls += 1
            rows = _closed_rows(
                raw,
                timeframe_seconds=seconds,
                snapshot_utc=end_utc,
            )
            if rows:
                chunks_with_data += 1
                _inserted, replaced = _insert_rows(connection, rows)
                replacements += replaced
            cursor = chunk_end

        row_count, first_epoch, last_epoch = connection.execute(
            "SELECT COUNT(*), MIN(time_epoch), MAX(time_epoch) FROM bars"
        ).fetchone()
        row_count = int(row_count or 0)
        if row_count <= 0 or first_epoch is None or last_epoch is None:
            raise RuntimeError(
                f"{SYMBOL} {timeframe}: no closed bars returned for "
                f"{start_utc.isoformat()} .. {end_utc.isoformat()}"
            )

        target = stage_dir / FILE_BY_TIMEFRAME[timeframe]
        _write_csv_from_database(connection, target)
        gap_count, maximum_gap = _gap_statistics(connection, seconds)
        minimum = RESEARCH_MINIMUM_ROWS[timeframe]
        return TimeframeExport(
            timeframe=timeframe,
            path=target.name,
            rows=row_count,
            first_time_utc=_utc_text(int(first_epoch)),
            last_time_utc=_utc_text(int(last_epoch)),
            requested_start_utc=start_utc.strftime("%Y-%m-%d %H:%M:%S"),
            requested_end_utc=end_utc.strftime("%Y-%m-%d %H:%M:%S"),
            chunk_calls=calls,
            chunks_with_data=chunks_with_data,
            duplicate_rows_replaced=replacements,
            gaps_over_one_bar=gap_count,
            maximum_gap_seconds=maximum_gap,
            research_minimum_rows=minimum,
            research_minimum_met=row_count >= minimum,
            sha256=_sha256(target),
        )
    finally:
        connection.close()
        database_path.unlink(missing_ok=True)


def _backup_existing(
    output_dir: Path,
    *,
    timeframes: Sequence[str],
    stamp: str,
) -> Path | None:
    existing = [
        output_dir / FILE_BY_TIMEFRAME[timeframe]
        for timeframe in timeframes
        if (output_dir / FILE_BY_TIMEFRAME[timeframe]).is_file()
    ]
    manifest = output_dir / "btcusdsharp_history_manifest.json"
    if manifest.is_file():
        existing.append(manifest)
    if not existing:
        return None
    backup = output_dir / "btcusdsharp_backups" / stamp
    backup.mkdir(parents=True, exist_ok=False)
    for path in existing:
        shutil.copy2(path, backup / path.name)
    return backup


def _commit_staged_files(
    output_dir: Path,
    stage_dir: Path,
    timeframes: Sequence[str],
) -> None:
    for timeframe in timeframes:
        source = stage_dir / FILE_BY_TIMEFRAME[timeframe]
        if not source.is_file():
            raise RuntimeError(f"staged CSV missing: {source}")
    for timeframe in timeframes:
        source = stage_dir / FILE_BY_TIMEFRAME[timeframe]
        os.replace(source, output_dir / source.name)


def _masked_account(mt5: Any) -> dict[str, Any]:
    account = _asdict(mt5.account_info())
    login = str(account.get("login") or "")
    return {
        "login_masked": f"***{login[-4:]}" if login else "",
        "server": account.get("server", ""),
        "company": account.get("company", ""),
        "currency": account.get("currency", ""),
    }


def run_export(mt5: Any, args: argparse.Namespace) -> dict[str, Any]:
    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    lock_path = output_dir / "btcusdsharp_history_export.lock"
    _acquire_lock(lock_path)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    stage_dir = output_dir / f".btcusdsharp_stage_{stamp}_{os.getpid()}"
    stage_dir.mkdir(parents=True, exist_ok=False)

    start_utc = _parse_utc(args.start)
    end_utc = _parse_utc(args.end, end_of_day=True) if args.end else datetime.now(timezone.utc)
    if start_utc >= end_utc:
        raise ValueError("start must be earlier than end")
    timeframes = tuple(args.timeframes)
    invalid = [value for value in timeframes if value not in TIMEFRAME_SECONDS]
    if invalid:
        raise ValueError(f"unsupported timeframes: {invalid}")

    _connect(mt5, args)
    backup: Path | None = None
    try:
        symbol_info = _select_symbol(mt5)
        exports = [
            _export_timeframe(
                mt5,
                timeframe=timeframe,
                start_utc=start_utc,
                end_utc=end_utc,
                stage_dir=stage_dir,
            )
            for timeframe in timeframes
        ]

        backup = _backup_existing(output_dir, timeframes=timeframes, stamp=stamp)
        _commit_staged_files(output_dir, stage_dir, timeframes)

        terminal = _asdict(mt5.terminal_info())
        manifest = {
            "schema_version": 1,
            "stage": "BTC_HISTORY_ACQUISITION_BEFORE_CANDIDATE_DISCOVERY",
            "generated_at_utc": datetime.now(timezone.utc).strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
            "symbol": SYMBOL,
            "time_basis": "UTC_NAIVE_FROM_MT5_EPOCH",
            "latest_row_contract": "CLOSED_ONLY",
            "open_bar_policy": "BAR_OPEN_EPOCH_PLUS_TIMEFRAME_MUST_BE_LE_SNAPSHOT",
            "orders_enabled": False,
            "discord_enabled": False,
            "live_ready": False,
            "final_signal": False,
            "candidate_discovery_started": False,
            "requested_start_utc": start_utc.strftime("%Y-%m-%d %H:%M:%S"),
            "snapshot_end_utc": end_utc.strftime("%Y-%m-%d %H:%M:%S"),
            "output_dir": str(output_dir),
            "backup_dir": str(backup) if backup is not None else "",
            "symbol_contract": {
                key: _json_value(value)
                for key, value in _asdict(symbol_info).items()
            },
            "terminal": {
                "company": terminal.get("company", ""),
                "name": terminal.get("name", ""),
                "maxbars": _json_value(terminal.get("maxbars")),
            },
            "account": _masked_account(mt5),
            "timeframes": [export.__dict__ for export in exports],
            "warnings": [
                f"{export.timeframe}: only {export.rows} rows; research target is {export.research_minimum_rows}"
                for export in exports
                if not export.research_minimum_met
            ],
        }
        manifest_path = output_dir / "btcusdsharp_history_manifest.json"
        temporary = manifest_path.with_name(manifest_path.name + f".tmp.{os.getpid()}")
        temporary.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        os.replace(temporary, manifest_path)
        return manifest
    finally:
        try:
            mt5.shutdown()
        finally:
            shutil.rmtree(stage_dir, ignore_errors=True)
            lock_path.unlink(missing_ok=True)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Download closed BTCUSD# history from MT5 into Files/btcusdsharp_*.csv. "
            "Existing files are backed up only after all staged timeframes succeed."
        )
    )
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--start", default=DEFAULT_START)
    parser.add_argument("--end", help="UTC ISO date/time. Date-only values include that full date.")
    parser.add_argument(
        "--timeframes",
        nargs="+",
        default=list(TIMEFRAME_SECONDS),
        choices=list(TIMEFRAME_SECONDS),
    )
    parser.add_argument("--terminal-path")
    parser.add_argument("--login")
    parser.add_argument("--password")
    parser.add_argument("--server")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        import MetaTrader5 as mt5
    except ImportError as exc:
        raise SystemExit(
            "MetaTrader5 Python package is required on the user PC"
        ) from exc
    manifest = run_export(mt5, args)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
