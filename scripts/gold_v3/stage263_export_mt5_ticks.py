from __future__ import annotations

import argparse
import json
from datetime import timedelta
from pathlib import Path
from typing import Any

import pandas as pd


def parse_utc(value: str):
    ts = pd.Timestamp(value)
    if ts.tzinfo is None:
        ts = ts.tz_localize('UTC')
    else:
        ts = ts.tz_convert('UTC')
    return ts.to_pydatetime()


def main() -> None:
    parser = argparse.ArgumentParser(description='Read-only MT5 tick exporter for GOLD V3 audit.')
    parser.add_argument('--symbol', required=True, help='Actual MT5 symbol name')
    parser.add_argument('--from-utc', required=True, help='ISO UTC start')
    parser.add_argument('--to-utc', required=True, help='ISO UTC end')
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--terminal-path', default=None, help='Optional terminal64.exe path')
    parser.add_argument('--chunk-days', type=int, default=7)
    args = parser.parse_args()

    try:
        import MetaTrader5 as mt5
    except ImportError as exc:
        raise SystemExit('MetaTrader5 package is not installed in this Python environment.') from exc

    start = parse_utc(args.from_utc)
    end = parse_utc(args.to_utc)
    if end <= start:
        raise SystemExit('--to-utc must be after --from-utc')

    initialized = mt5.initialize(path=args.terminal_path) if args.terminal_path else mt5.initialize()
    if not initialized:
        raise SystemExit(f'MT5 initialize failed: {mt5.last_error()}')

    try:
        if not mt5.symbol_select(args.symbol, True):
            raise SystemExit(f'symbol_select failed for {args.symbol}: {mt5.last_error()}')
        account = mt5.account_info()
        terminal = mt5.terminal_info()
        symbol_info = mt5.symbol_info(args.symbol)
        if account is None or terminal is None or symbol_info is None:
            raise SystemExit(f'MT5 metadata unavailable: {mt5.last_error()}')

        frames: list[pd.DataFrame] = []
        cursor = start
        while cursor < end:
            chunk_end = min(cursor + timedelta(days=max(1, args.chunk_days)), end)
            ticks = mt5.copy_ticks_range(args.symbol, cursor, chunk_end, mt5.COPY_TICKS_ALL)
            if ticks is None:
                raise SystemExit(f'copy_ticks_range failed at {cursor} - {chunk_end}: {mt5.last_error()}')
            if len(ticks):
                frames.append(pd.DataFrame(ticks))
            cursor = chunk_end

        if not frames:
            raise SystemExit('No ticks returned for the requested range.')

        data = pd.concat(frames, ignore_index=True)
        dedup_cols = [c for c in ['time_msc', 'bid', 'ask', 'last', 'flags'] if c in data.columns]
        data = data.drop_duplicates(dedup_cols).sort_values('time_msc').reset_index(drop=True)
        data['time_utc'] = pd.to_datetime(data['time_msc'], unit='ms', utc=True)
        data['source_available_at'] = data['time_utc']
        data['broker_or_server_id'] = f'{account.company}|{account.server}'
        data['symbol'] = args.symbol
        data['tick_volume_delta'] = 1
        package_version = getattr(mt5, '__version__', 'unknown')
        data['source_version'] = f'MetaTrader5={package_version};terminal_build={terminal.build}'

        ordered = [
            'broker_or_server_id','symbol','time_utc','bid','ask','last','tick_volume_delta',
            'source_available_at','source_version','time','time_msc','volume','flags','volume_real',
        ]
        ordered = [c for c in ordered if c in data.columns]
        args.out.parent.mkdir(parents=True, exist_ok=True)
        data[ordered].to_csv(args.out, index=False)

        metadata: dict[str, Any] = {
            'audit_only': True,
            'read_only_export': True,
            'symbol': args.symbol,
            'requested_from_utc': pd.Timestamp(start).isoformat(),
            'requested_to_utc': pd.Timestamp(end).isoformat(),
            'rows': int(len(data)),
            'first_tick_utc': data['time_utc'].min().isoformat(),
            'last_tick_utc': data['time_utc'].max().isoformat(),
            'broker_company': account.company,
            'server': account.server,
            'account_login_redacted': True,
            'terminal_build': int(terminal.build),
            'package_version': package_version,
            'symbol_path': symbol_info.path,
            'digits': int(symbol_info.digits),
            'trade_mode': int(symbol_info.trade_mode),
            'note': 'No order or position API is called by this exporter.',
        }
        args.out.with_suffix(args.out.suffix + '.metadata.json').write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2), encoding='utf-8'
        )
        print(json.dumps(metadata, ensure_ascii=False, indent=2))
    finally:
        mt5.shutdown()


if __name__ == '__main__':
    main()
