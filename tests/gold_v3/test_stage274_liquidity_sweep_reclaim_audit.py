import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd

SPEC = importlib.util.spec_from_file_location('stage274', '/mnt/data/stage274_liquidity_sweep_reclaim_audit.py')
S = importlib.util.module_from_spec(SPEC)
sys.modules['stage274'] = S
SPEC.loader.exec_module(S)


def test_context_asof_never_uses_unclosed_h4_or_d1():
    ctx, _ = S.build_context()
    first = ctx.loc[ctx['h4_ema50'].notna(), 'close_time'].min()
    assert first >= pd.Timestamp('2023-01-11 08:00:00')
    early = ctx[ctx['close_time'] < pd.Timestamp('2023-01-04 00:00:00')]
    assert early['prev_day_high'].isna().all()


def test_same_m1_tp_sl_uses_sl_priority():
    m1 = pd.DataFrame({
        'time': pd.date_range('2023-06-01', periods=1440, freq='min'),
        'open': np.full(1440, 100.0),
        'high': np.full(1440, 100.2),
        'low': np.full(1440, 99.8),
        'close': np.full(1440, 100.0),
    })
    m1.loc[0, 'high'] = 103.0
    m1.loc[0, 'low'] = 98.0
    row = pd.Series({'entry_idx': 0, 'entry_year': 2023, 'direction': 1,
                     'entry_price': 100.0, 'sl_price': 99.0, 'risk_usd': 1.0})
    out = S.simulate(row, 2.0, m1)
    assert out['exit_reason'] == 'SL'
    assert out['gross_r'] == -1.0


def test_independent_stream_is_variant_direction_local():
    c = pd.DataFrame({
        'variant': ['A_PD', 'A_PD', 'A_H1S20'],
        'direction': [1, 1, 1],
        'entry_idx': [100, 500, 500],
    })
    out = S.apply_independent_stream(c)
    accepted = out.set_index('variant')['accepted_independent'].to_dict()
    assert accepted['A_H1S20']
    assert out[(out['variant'] == 'A_PD')]['accepted_independent'].tolist() == [True, False]


def test_discovery_grid_has_12_fixed_cells_and_zero_leads():
    path = Path('/mnt/data/stage274_liquidity_sweep_reclaim/stage274_discovery_grid.csv')
    grid = pd.read_csv(path)
    assert len(grid) == 12
    assert int(grid['discovery_lead'].sum()) == 0
    assert set(grid['variant']) == {'A_PD', 'A_H1S20', 'B_PD', 'B_H1S20'}
    assert set(grid['tp_r']) == {1.5, 2.0, 2.5}
