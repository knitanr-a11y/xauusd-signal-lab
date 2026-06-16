#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path

import pandas as pd

import gold_v3_177_ohlc_only_rebuild_search_audit as base


HIST_2025_REL = Path('FX_OUTPUTS') / 'mt5_candles' / 'gold_2025'


def combine(tf: str, data_dir: Path):
    """Stage177 data-location contract.

    - Historical 2025 candles are stored under:
      Files/FX_OUTPUTS/mt5_candles/gold_2025/gold#_<tf>.csv
    - Live / continuation goldsharp candles stay directly under Files:
      Files/goldsharp_<tf>.csv
    - Pre-2025 goldsharp rows are warm-up only.
    - 2025 rows must come from the gold_2025 folder, not Files root.
    """
    live_path = data_dir / f'goldsharp_{tf}.csv'
    old_path = data_dir / HIST_2025_REL / f'gold#_{tf}.csv'

    live = base.read_csv_any(live_path)
    old = base.read_csv_any(old_path)
    diag = [
        base.summarize_raw(tf, 'goldsharp_files_root', live_path, live),
        base.summarize_raw(tf, 'gold#_gold_2025_folder', old_path, old),
    ]

    if live.empty and old.empty:
        return pd.DataFrame(), diag

    parts = []
    if not live.empty and 'dt' in live.columns:
        parts.append(live[live['dt'] < pd.Timestamp('2025-01-01')])
    if not old.empty and 'dt' in old.columns:
        parts.append(old[(old['dt'] >= pd.Timestamp('2025-01-01')) & (old['dt'] < pd.Timestamp('2026-01-01'))])
    if not live.empty and 'dt' in live.columns:
        parts.append(live[live['dt'] >= pd.Timestamp('2026-01-01')])

    if not parts:
        return pd.DataFrame(), diag
    out = pd.concat(parts, ignore_index=True)
    if out.empty:
        return pd.DataFrame(), diag
    return out.drop_duplicates('dt', keep='last').sort_values('dt').reset_index(drop=True), diag


def main() -> int:
    base.combine = combine
    return base.main()


if __name__ == '__main__':
    raise SystemExit(main())
