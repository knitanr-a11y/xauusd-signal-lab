#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Fetch candle history from a locally installed MetaTrader 5 terminal.

This script is intentionally standalone and writes outputs outside the git repo by
default.  It is meant for GOLD V2 external validation data pulls such as 2025
XAUUSD/GOLD candles.

Example:
    python scripts/gold_v2_data/fetch_mt5_candles.py \
        --symbol XAUUSD \
        --start 2025-01-01 \
        --end 2026-01-01 \
        --timeframes M1,M5,M15,H1,H4,D1 \
        --output-dir ..\..\FX_OUTPUTS\mt5_candles\gold_2025

Notes:
    * MT5 terminal must be installed and logged in, or login/server/password must
      be supplied through args or environment variables.
    * Historical depth depends on broker/server availability and MT5 terminal
      settings.  In MT5, increase Tools > Options > Charts > Max bars in chart
      if returned rows are unexpectedly short.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import pandas as pd

try:
    import MetaTrader5 as mt5  # type: ignore
except Exception as exc:  # pragma: no cover - executed on user machine
    mt5 = None  # type: ignore
    MT5_IMPORT_ERROR = exc
else:
    MT5_IMPORT_ERROR = None


TIMEFRAME_NAMES: Dict[str, str] = {
    "M1": "TIMEFRAME_M1",
    "M2": "TIMEFRAME_M2",
    "M3": "TIMEFRAME_M3",
    "M4": "TIMEFRAME_M4",
    "M5": "TIMEFRAME_M5",
    "M6": "TIMEFRAME_M6",
    "M10": "TIMEFRAME_M10",
    "M12": "TIMEFRAME_M12",
    "M15": "TIMEFRAME_M15",
    "M20": "TIMEFRAME_M20",
    "M30": "TIMEFRAME_M30",
    "H1": "TIMEFRAME_H1",
    "H2": "TIMEFRAME_H2",
    "H3": "TIMEFRAME_H3",
    "H4": "TIMEFRAME_H4",
    "H6": "TIMEFRAME_H6",
    "H8": "TIMEFRAME_H8",
    "H12": "TIMEFRAME_H12",
    "D1": "TIMEFRAME_D1",
    "W1": "TIMEFRAME_W1",
    "MN1": "TIMEFRAME_MN1",
}

# Reasonable chunk sizes so M1 does not ask the terminal for a full year in one
# call.  copy_rates_range can handle longer ranges on some terminals, but chunking
# makes failures easier to diagnose.
DEFAULT_CHUNK_DAYS: Dict[str, int] = {
    "M1": 14,
    "M2": 20,
    "M3": 20,
    "M4": 20,
    "M5": 31,
    "M6": 31,
    "M10": 45,
    "M12": 45,
    "M15": 62,
    "M20": 62,
    "M30": 90,
    "H1": 120,
    "H2": 180,
    "H3": 180,
    "H4": 240,
    "H6": 240,
    "H8": 240,
    "H12": 365,
    "D1": 365,
    "W1": 365 * 3,
    "MN1": 365 * 10,
}


@dataclass
class FetchResult:
    symbol_requested: str
    symbol_used: str
    timeframe: str
    start_utc: str
    end_utc: str
    rows: int
    first_time_utc: Optional[str]
    last_time_utc: Optional[str]
    output_csv: str
    status: str
    message: str


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch MT5 candle history to CSV")
    parser.add_argument("--symbol", default="XAUUSD", help="Preferred MT5 symbol, e.g. XAUUSD or GOLD")
    parser.add_argument(
        "--symbol-aliases",
        default="XAUUSD,GOLD,XAUUSDm,XAUUSD.,XAUUSD#,GOLDm,GOLD.",
        help="Comma-separated fallback symbols to try before fuzzy XAU/GOLD search",
    )
    parser.add_argument("--start", default="2025-01-01", help="UTC start date/datetime, inclusive")
    parser.add_argument("--end", default="2026-01-01", help="UTC end date/datetime, exclusive-ish")
    parser.add_argument(
        "--timeframes",
        default="M1,M5,M15,H1,H4,D1",
        help="Comma-separated MT5 timeframes",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Output directory. Default: <repo>/../../FX_OUTPUTS/mt5_candles/<symbol>_<start>_<end>",
    )
    parser.add_argument("--sep", default=";", help="CSV separator. Default ';' for existing GOLD tools")
    parser.add_argument("--encoding", default="utf-8-sig", help="CSV encoding. Default utf-8-sig")
    parser.add_argument("--terminal-path", default=os.environ.get("MT5_PATH", ""), help="Optional terminal64.exe path")
    parser.add_argument("--login", default=os.environ.get("MT5_LOGIN", ""), help="Optional MT5 login")
    parser.add_argument("--password", default=os.environ.get("MT5_PASSWORD", ""), help="Optional MT5 password")
    parser.add_argument("--server", default=os.environ.get("MT5_SERVER", ""), help="Optional MT5 server")
    parser.add_argument("--chunk-days", type=int, default=0, help="Override chunk length in days for all timeframes")
    parser.add_argument("--sleep-sec", type=float, default=0.2, help="Sleep between chunk requests")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero if any timeframe returns zero rows")
    parser.add_argument("--no-fuzzy-symbol", action="store_true", help="Disable fuzzy XAU/GOLD symbol search")
    return parser.parse_args(argv)


def parse_utc_datetime(value: str) -> datetime:
    value = value.strip()
    if not value:
        raise ValueError("empty datetime")
    if len(value) == 10:
        dt = datetime.strptime(value, "%Y-%m-%d")
    else:
        # Accept 'YYYY-mm-dd HH:MM[:SS]' or ISO with T/Z.
        v = value.replace("T", " ").replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(v)
        except ValueError:
            dt = datetime.strptime(v, "%Y-%m-%d %H:%M:%S")
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def clean_list(value: str) -> List[str]:
    return [x.strip() for x in value.split(",") if x.strip()]


def get_timeframe_constant(name: str) -> int:
    if mt5 is None:
        raise RuntimeError("MetaTrader5 module is not imported")
    key = name.upper().strip()
    if key not in TIMEFRAME_NAMES:
        raise ValueError(f"Unsupported timeframe: {name}. Supported: {', '.join(TIMEFRAME_NAMES)}")
    attr = TIMEFRAME_NAMES[key]
    if not hasattr(mt5, attr):
        raise ValueError(f"Installed MetaTrader5 package does not expose {attr}")
    return int(getattr(mt5, attr))


def initialize_mt5(args: argparse.Namespace) -> None:
    if mt5 is None:
        raise RuntimeError(
            "MetaTrader5 Python package is not available. Install with: python -m pip install MetaTrader5\n"
            f"Original import error: {MT5_IMPORT_ERROR}"
        )

    kwargs = {}
    if args.terminal_path:
        kwargs["path"] = args.terminal_path
    if args.login:
        kwargs["login"] = int(str(args.login).strip())
    if args.password:
        kwargs["password"] = args.password
    if args.server:
        kwargs["server"] = args.server

    ok = mt5.initialize(**kwargs) if kwargs else mt5.initialize()
    if not ok:
        code, message = mt5.last_error()
        raise RuntimeError(f"mt5.initialize failed: {code} {message}")

    account = mt5.account_info()
    terminal = mt5.terminal_info()
    print("[MT5] initialized")
    print(f"[MT5] account={getattr(account, 'login', None)} server={getattr(account, 'server', None)}")
    print(f"[MT5] terminal_path={getattr(terminal, 'path', None)}")


def shutdown_mt5() -> None:
    if mt5 is not None:
        try:
            mt5.shutdown()
        except Exception:
            pass


def find_symbol(preferred: str, aliases: Iterable[str], fuzzy: bool = True) -> str:
    if mt5 is None:
        raise RuntimeError("MetaTrader5 module is not imported")

    candidates = []
    for s in [preferred, *aliases]:
        if s and s not in candidates:
            candidates.append(s)

    for symbol in candidates:
        info = mt5.symbol_info(symbol)
        if info is not None:
            if not info.visible:
                mt5.symbol_select(symbol, True)
            print(f"[MT5] symbol selected: requested={preferred} used={symbol}")
            return symbol

    if fuzzy:
        fuzzy_candidates = []
        for pattern in ("*XAU*", "*GOLD*", "*Gold*", "*gold*"):
            got = mt5.symbols_get(pattern)
            if got:
                fuzzy_candidates.extend(got)
        # Prefer names that are short and not obvious CFD suffix variants if possible.
        fuzzy_candidates = sorted(
            {s.name: s for s in fuzzy_candidates}.values(),
            key=lambda x: (0 if "XAU" in x.name.upper() or "GOLD" in x.name.upper() else 1, len(x.name), x.name),
        )
        for sym in fuzzy_candidates:
            if mt5.symbol_select(sym.name, True):
                print(f"[MT5] fuzzy symbol selected: requested={preferred} used={sym.name}")
                return sym.name

    raise RuntimeError(
        f"Could not find/select symbol '{preferred}'. Tried aliases={candidates}. "
        "Open Market Watch in MT5 and confirm the broker-specific GOLD/XAUUSD symbol name."
    )


def iter_chunks(start: datetime, end: datetime, days: int) -> Iterable[Tuple[datetime, datetime]]:
    cur = start
    step = timedelta(days=days)
    while cur < end:
        nxt = min(cur + step, end)
        yield cur, nxt
        cur = nxt


def fetch_timeframe(symbol: str, timeframe_name: str, start: datetime, end: datetime, chunk_days: int, sleep_sec: float) -> pd.DataFrame:
    if mt5 is None:
        raise RuntimeError("MetaTrader5 module is not imported")

    tf_const = get_timeframe_constant(timeframe_name)
    frames: List[pd.DataFrame] = []
    for chunk_start, chunk_end in iter_chunks(start, end, chunk_days):
        print(f"[FETCH] {symbol} {timeframe_name} {chunk_start.isoformat()} -> {chunk_end.isoformat()}")
        rates = mt5.copy_rates_range(symbol, tf_const, chunk_start, chunk_end)
        if rates is None:
            code, message = mt5.last_error()
            print(f"[WARN] copy_rates_range returned None for {timeframe_name}: {code} {message}")
        elif len(rates) == 0:
            print(f"[WARN] zero rows for {timeframe_name} chunk {chunk_start} -> {chunk_end}")
        else:
            frames.append(pd.DataFrame(rates))
        if sleep_sec > 0:
            time.sleep(sleep_sec)

    if not frames:
        return pd.DataFrame(columns=["time", "open", "high", "low", "close", "tick_volume", "spread", "real_volume"])

    df = pd.concat(frames, ignore_index=True)
    df = df.drop_duplicates(subset=["time"]).sort_values("time").reset_index(drop=True)

    # MT5 stores bar open time as UNIX seconds. Convert to explicit UTC/JST audit columns.
    time_utc = pd.to_datetime(df["time"], unit="s", utc=True)
    df.insert(0, "time_utc", time_utc.dt.strftime("%Y-%m-%d %H:%M:%S%z"))
    df.insert(1, "time_jst", time_utc.dt.tz_convert("Asia/Tokyo").dt.strftime("%Y-%m-%d %H:%M:%S%z"))
    df["time"] = time_utc.dt.strftime("%Y-%m-%d %H:%M:%S")

    wanted = ["time", "time_utc", "time_jst", "open", "high", "low", "close", "tick_volume", "spread", "real_volume"]
    existing = [c for c in wanted if c in df.columns]
    rest = [c for c in df.columns if c not in existing]
    return df[existing + rest]


def default_output_dir(symbol: str, start: datetime, end: datetime) -> Path:
    repo_root = Path(__file__).resolve().parents[2]
    files_dir = repo_root.parents[1] if len(repo_root.parents) >= 2 else repo_root.parent
    safe_start = start.strftime("%Y%m%d")
    safe_end = end.strftime("%Y%m%d")
    return files_dir / "FX_OUTPUTS" / "mt5_candles" / f"{symbol}_{safe_start}_{safe_end}"


def write_outputs(
    df: pd.DataFrame,
    output_dir: Path,
    symbol: str,
    timeframe: str,
    sep: str,
    encoding: str,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{symbol.lower()}_{timeframe.lower()}.csv"
    df.to_csv(path, index=False, sep=sep, encoding=encoding)
    return path


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    start = parse_utc_datetime(args.start)
    end = parse_utc_datetime(args.end)
    if end <= start:
        raise ValueError(f"end must be after start: start={start}, end={end}")

    requested_timeframes = [x.upper() for x in clean_list(args.timeframes)]
    aliases = clean_list(args.symbol_aliases)

    results: List[FetchResult] = []
    try:
        initialize_mt5(args)
        symbol = find_symbol(args.symbol, aliases, fuzzy=not args.no_fuzzy_symbol)
        outdir = Path(args.output_dir).expanduser().resolve() if args.output_dir else default_output_dir(symbol, start, end)
        outdir.mkdir(parents=True, exist_ok=True)
        print(f"[OUT] {outdir}")

        for tf in requested_timeframes:
            chunk_days = args.chunk_days if args.chunk_days > 0 else DEFAULT_CHUNK_DAYS.get(tf, 60)
            status = "OK"
            message = ""
            output_csv = ""
            first_time = None
            last_time = None
            rows = 0
            try:
                df = fetch_timeframe(symbol, tf, start, end, chunk_days, args.sleep_sec)
                rows = int(len(df))
                if rows > 0:
                    first_time = str(df["time_utc"].iloc[0]) if "time_utc" in df.columns else str(df["time"].iloc[0])
                    last_time = str(df["time_utc"].iloc[-1]) if "time_utc" in df.columns else str(df["time"].iloc[-1])
                    output_csv = str(write_outputs(df, outdir, symbol, tf, args.sep, args.encoding))
                    print(f"[DONE] {tf}: rows={rows} first={first_time} last={last_time} -> {output_csv}")
                else:
                    status = "ZERO_ROWS"
                    message = "No rows returned. Check symbol, broker history availability, and MT5 Max bars in chart."
                    output_csv = str(write_outputs(df, outdir, symbol, tf, args.sep, args.encoding))
                    print(f"[ZERO] {tf}: wrote empty CSV -> {output_csv}")
            except Exception as exc:
                status = "ERROR"
                message = repr(exc)
                print(f"[ERROR] {tf}: {message}")
            results.append(
                FetchResult(
                    symbol_requested=args.symbol,
                    symbol_used=symbol,
                    timeframe=tf,
                    start_utc=start.isoformat(),
                    end_utc=end.isoformat(),
                    rows=rows,
                    first_time_utc=first_time,
                    last_time_utc=last_time,
                    output_csv=output_csv,
                    status=status,
                    message=message,
                )
            )

        summary_path = outdir / "fetch_summary.json"
        summary = {
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "symbol_requested": args.symbol,
            "symbol_used": results[0].symbol_used if results else None,
            "start_utc": start.isoformat(),
            "end_utc": end.isoformat(),
            "timeframes": requested_timeframes,
            "sep": args.sep,
            "encoding": args.encoding,
            "results": [asdict(r) for r in results],
        }
        summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[SUMMARY] {summary_path}")

        failures = [r for r in results if r.status == "ERROR" or (args.strict and r.rows == 0)]
        if failures:
            print("[FAILURES]")
            for r in failures:
                print(f"  {r.timeframe}: status={r.status} rows={r.rows} message={r.message}")
            return 2
        return 0
    finally:
        shutdown_mt5()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("Interrupted", file=sys.stderr)
        raise SystemExit(130)
