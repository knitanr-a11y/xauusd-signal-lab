import sys

import numpy as np
import pandas as pd

sys.path.insert(0, '/mnt/data')
import stage267_architecture_reset as s


def m1(times, prices=None, source='TEST'):
    times = pd.to_datetime(times)
    if prices is None:
        prices = np.arange(len(times), dtype=float) + 100.0
    prices = np.asarray(prices, dtype=float)
    return pd.DataFrame({
        'time': times,
        'open': prices,
        'high': prices + 1,
        'low': prices - 1,
        'close': prices + 0.5,
        'tick_volume': 1,
        'spread': 1,
        'source_id': source,
    })


def test_gap_classification_distinguishes_maintenance_and_rare_gap():
    assert s.classify_gap(62) == 'OBSERVED_DAILY_MAINTENANCE'
    assert s.classify_gap(2943) == 'OBSERVED_WEEKEND_CLOSURE'
    assert s.classify_gap(216) == 'OBSERVED_HOLIDAY_OR_EARLY_CLOSE'
    assert s.classify_gap(4) == 'RARE_DATA_GAP'


def test_decision_during_maintenance_activates_at_first_real_m1():
    src = m1(['2025-01-02 23:58', '2025-01-03 01:00', '2025-01-03 01:01'], [100, 105, 106], 'X')
    tf = pd.DataFrame([{
        'time': pd.Timestamp('2025-01-02 23:00'),
        'open': 99, 'high': 101, 'low': 98, 'close': 100,
        'tick_volume': 1, 'spread': 1,
    }])
    out = s.map_decisions(tf, 'H1', 60, {'X': src}).iloc[0]
    assert out.activation_status == 'ACTIVATED_AFTER_OBSERVED_CLOSURE'
    assert out.activation_time == pd.Timestamp('2025-01-03 01:00')
    assert out.activation_delay_minutes == 60
    assert out.activation_price == 105
    assert out.observed_closure_class == 'OBSERVED_DAILY_MAINTENANCE'


def test_forward_path_long_short_algebra_is_symmetric():
    times = pd.date_range('2025-01-01', periods=8000, freq='min')
    src = m1(times, np.linspace(100, 200, len(times)), 'X')
    decision = pd.DataFrame([{
        'timeframe': 'H1', 'bar_open_time': pd.Timestamp('2025-01-01'),
        'decision_time': pd.Timestamp('2025-01-01'),
        'bar_open': 99., 'bar_high': 101., 'bar_low': 98., 'bar_close': 100.,
        'bar_tick_volume': 1., 'bar_spread': 1., 'decision_hour': 0,
        'decision_weekday': 2, 'completed_bar_sign': 1, 'source_id': 'X',
        'activation_status': 'ACTIVATED_EXACT', 'activation_time': pd.Timestamp('2025-01-01'),
        'activation_delay_minutes': 0., 'activation_price': 100.,
        'decision_has_exact_m1': True, 'observed_closure_class': None,
        'prior_m1_time': pd.NaT, 'activation_index': 0,
    }])
    out = s.add_forward_paths(decision, {'X': src}).iloc[0]
    assert np.isclose(out.h4_long_return, -out.h4_short_return)
    assert np.isclose(out.h4_long_mfe, -out.h4_short_mae)
    assert np.isclose(out.h4_long_mae, -out.h4_short_mfe)


def test_no_source_coverage_does_not_fallback_to_other_source():
    a = m1(pd.date_range('2025-01-01', periods=10, freq='min'), source='A')
    b = m1(pd.date_range('2025-02-01', periods=10, freq='min'), source='B')
    tf = pd.DataFrame([{
        'time': pd.Timestamp('2025-01-15 00:00'),
        'open': 99, 'high': 101, 'low': 98, 'close': 100,
        'tick_volume': 1, 'spread': 1,
    }])
    out = s.map_decisions(tf, 'H1', 60, {'A': a, 'B': b}).iloc[0]
    assert out.activation_status == 'NO_M1_SOURCE_COVERAGE'
    assert pd.isna(out.source_id)
