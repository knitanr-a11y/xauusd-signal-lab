#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
import gold_v3_107gy_light_non_calendar_subfilter_search_audit as gy

def jst(): return datetime.now(timezone(timedelta(hours=9)))
def append_jsonl(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a', encoding='utf-8') as f:
        f.write(json.dumps(obj, ensure_ascii=False, default=str) + '\n')

def main():
    mt5 = gy.mt5_files_dir('')
    root = mt5 / 'FX_OUTPUTS' / 'gold_v3'
    now = jst()
    key = 'BAT_RUNTIME_STOP|' + now.strftime('%Y-%m-%dT%H:%M:%S%z')
    item = {
        'created_at_jst': now.isoformat(),
        'queue_id': key,
        'signal_id': key,
        'side': 'STOP_REVIEW',
        'symbol': 'XAUUSD',
        'entry_dt': now.isoformat(),
        'monitor_state': 'BAT_RUNTIME_STOP',
        'reason': '115 loop BAT reached error branch; check local terminal logs',
    }
    q = root / '115a' / 'queue' / now.strftime('%Y-%m') / f'gold_v3_115x_bat_error_{now.strftime("%Y-%m-%d")}.jsonl'
    append_jsonl(q, item)
    print(json.dumps({'queued': True, 'queue_id': key, 'path': str(q)}, ensure_ascii=False, indent=2))
    return 0
if __name__ == '__main__': raise SystemExit(main())
