from __future__ import annotations

import pandas as pd

from stage263_architecture_reset import apply_one_active, feature_columns, strategy_signals


def test_one_active_uses_exit_time_boundary():
    df = pd.DataFrame([
        {'entry_time': pd.Timestamp('2026-06-01 08:00'), 'exit_time': pd.Timestamp('2026-06-01 09:00'), 'gross_return_usd': 5.0, 'd': 1},
        {'entry_time': pd.Timestamp('2026-06-01 08:45'), 'exit_time': pd.Timestamp('2026-06-01 09:45'), 'gross_return_usd': 10.0, 'd': 1},
        {'entry_time': pd.Timestamp('2026-06-01 09:00'), 'exit_time': pd.Timestamp('2026-06-01 10:00'), 'gross_return_usd': -3.0, 'd': -1},
    ])
    out = apply_one_active(df, 'd')
    assert len(out) == 2
    assert list(out['entry_time']) == [pd.Timestamp('2026-06-01 08:00'), pd.Timestamp('2026-06-01 09:00')]
    assert list(out['cost2_pnl']) == [3.0, 1.0]


def test_signal_requires_model_sign_agreement_and_threshold():
    df = pd.DataFrame({
        'ridge_usd': [4.0, 5.0, -5.0],
        'hgb_usd': [4.0, -5.0, -2.0],
        'ensemble_usd': [4.0, 0.0, -3.5],
        'sign_agree': [True, False, True],
    })
    out = strategy_signals(df, 3.6)
    assert list(out['model_direction']) == [1, 0, 0]


def test_feature_columns_exclude_timestamps_and_absolute_ohlc():
    frame = pd.DataFrame({
        'm15_ret_1': [0.1], 'h1_ret_1': [0.2], 'h4_ret_1': [0.3],
        'h1_source_close_time': [pd.Timestamp('2026-01-01')],
        'h4_source_close_time': [pd.Timestamp('2026-01-01')],
        'hour_sin': [0.0], 'hour_cos': [1.0], 'weekday_sin': [0.0], 'weekday_cos': [1.0],
        'open': [4000.0], 'close': [4001.0],
    })
    cols = feature_columns(frame)
    assert 'h1_source_close_time' not in cols
    assert 'h4_source_close_time' not in cols
    assert 'open' not in cols and 'close' not in cols
    assert 'm15_ret_1' in cols and 'h1_ret_1' in cols and 'h4_ret_1' in cols
