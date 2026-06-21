import importlib.util
import numpy as np
import pandas as pd

spec=importlib.util.spec_from_file_location('s','/mnt/data/stage269_entry_resolution.py')
s=importlib.util.module_from_spec(spec);spec.loader.exec_module(s)


def test_ltf_availability_uses_close_time():
    x=pd.DataFrame({'time':[pd.Timestamp('2026-01-01 10:00')], 'open':[1.], 'high':[2.], 'low':[.5], 'close':[1.5], 'tick_volume':[1], 'spread':[1], 'source_id':['X']})
    assert s.add_ltf_features(x,5).available_time.iloc[0]==pd.Timestamp('2026-01-01 10:05')
    assert s.add_ltf_features(x,15).available_time.iloc[0]==pd.Timestamp('2026-01-01 10:15')


def test_false_break_reclaim_is_direction_symmetric():
    base=pd.DataFrame({
      'time':pd.date_range('2026-01-01',periods=6,freq='5min'),
      'open':[10,10,10,10,9.2,10.8], 'high':[11,11,11,11,10.8,11.5],
      'low':[9,9,9,9,8.5,9.8], 'close':[10,10,10,10,10.5,9.4],
      'tick_volume':1,'spread':1,'source_id':'X'})
    x=s.add_ltf_features(base,5)
    x.loc[4,'prev3_low']=9.0;x.loc[4,'close_loc']=.85
    x.loc[5,'prev3_high']=11.0;x.loc[5,'close_loc']=.15
    assert bool(s.trigger_mask(x,1,'T3_FALSE_BREAK_RECLAIM').iloc[4])
    assert bool(s.trigger_mask(x,-1,'T3_FALSE_BREAK_RECLAIM').iloc[5])


def test_m1_metrics_long_short_symmetry():
    m1=pd.DataFrame({'time':pd.date_range('2026-01-01',periods=4,freq='min'), 'open':[100,101,102,103], 'high':[101,103,104,105], 'low':[99,100,101,102], 'close':[100,102,103,104]})
    lr,lmfe,lmae=s.m1_metrics(m1,0,3,1,2.0)
    sr,smfe,smae=s.m1_metrics(m1,0,3,-1,2.0)
    assert np.isclose(lr,-sr)
    assert np.isclose(lmfe,-smae)
    assert np.isclose(lmae,-smfe)


def test_selected_regimes_exclude_no_source_coverage():
    h1=pd.DataFrame({
      'h1_trend_state':['WEAK_TREND','WEAK_TREND'], 'h1_volatility_bucket':['LOW','LOW'],
      'hour_bin':['UTC00_03','UTC00_03'],'h1_candle_state':['NORMAL_CANDLE','NORMAL_CANDLE'],
      'TIMEFRAME_TREND_direction':[1.,1.], 'BAR_CONTINUATION_direction':[1.,1.],
      'source_id':['GOLD_HASH_2025',np.nan], 'activation_time':[pd.Timestamp('2025-01-01'),pd.NaT],
      'decision_time':[pd.Timestamp('2025-01-01'),pd.Timestamp('2025-01-02')], 'h1_atr14':[2.,2.]})
    out=s.select_regimes(h1)
    assert out.source_id.notna().all()
    assert out.activation_time.notna().all()
