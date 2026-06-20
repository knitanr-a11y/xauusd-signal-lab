import sys
import numpy as np
import pandas as pd

sys.path.insert(0,'/mnt/data')
import stage268_regime_diagnostic as s


def test_context_regime_aliases_are_present():
    df=pd.DataFrame({
        'h1_volatility_bucket':['LOW'], 'h1_expansion_state':['NORMAL'],
        'h1_trend_state':['WEAK_TREND'], 'h1_extension_bucket':['HEALTHY_EXTENSION'],
        'h1_candle_state':['NORMAL_CANDLE'], 'h1_direction':[1.0],
        'd1_direction':[1.0], 'd1_ema_spread_abs_atr':[1.0], 'h4_direction':[1.0],
        'decision_hour':[8], 'activation_delay_minutes':[0.0],
    })
    out=s.add_context_regimes(df,'h1',True)
    assert out.loc[0,'volatility_bucket']=='LOW'
    assert out.loc[0,'trend_state']=='WEAK_TREND'
    assert out.loc[0,'h1_h4_d1_alignment']=='ALL_ALIGNED'
    assert out.loc[0,'hour_bin']=='UTC08_11'


def test_hypothesis_alignment_uses_short_path_for_negative_direction():
    d={
        'completed_bar_sign':[-1.0], 'h1_direction':[-1.0], 'h1_trend_state':['WEAK_TREND'],
        'd1_direction':[-1.0], 'd1_ema_spread_abs_atr':[1.0],
        'h1_extension_bucket':['HEALTHY_EXTENSION'], 'h1_atr14':[10.0],
    }
    for h in s.HORIZONS:
        d[f'h{h}_long_return']=[5.0]; d[f'h{h}_short_return']=[-5.0]
        d[f'h{h}_long_mfe']=[8.0]; d[f'h{h}_long_mae']=[-3.0]
        d[f'h{h}_short_mfe']=[3.0]; d[f'h{h}_short_mae']=[-8.0]
    out=s.add_hypothesis_columns(pd.DataFrame(d),'h1')
    assert out.loc[0,'TIMEFRAME_TREND_h48_return_atr']==-0.5
    assert out.loc[0,'TIMEFRAME_TREND_h48_mfe_atr']==0.3
    assert out.loc[0,'TIMEFRAME_TREND_h48_mae_atr']==-0.8


def test_asof_merge_never_uses_future_d1_or_h4():
    paths=pd.DataFrame({
        'bar_open_time':[pd.Timestamp('2025-01-02 08:00')],
        'decision_time':[pd.Timestamp('2025-01-02 09:00')],
        'activation_time':[pd.Timestamp('2025-01-02 09:00')],
    })
    tf=pd.DataFrame({'time':[pd.Timestamp('2025-01-02 08:00')], 'source_close_time':[pd.Timestamp('2025-01-02 09:00')], 'h1_atr14':[2.0]})
    d1=pd.DataFrame({
        'time':[pd.Timestamp('2024-12-31'),pd.Timestamp('2025-01-02')],
        'source_close_time':[pd.Timestamp('2025-01-01'),pd.Timestamp('2025-01-03')],
        'd1_atr14':[10.0,99.0], 'd1_direction':[1.0,-1.0],
    })
    h4=pd.DataFrame({
        'time':[pd.Timestamp('2025-01-02 04:00'),pd.Timestamp('2025-01-02 08:00')],
        'source_close_time':[pd.Timestamp('2025-01-02 08:00'),pd.Timestamp('2025-01-02 12:00')],
        'h4_atr14':[4.0,44.0], 'h4_direction':[1.0,-1.0],
    })
    out=s.merge_features(paths,tf,d1,h4)
    assert out.loc[0,'d1_atr14']==10.0
    assert out.loc[0,'h4_atr14']==4.0
    assert out.loc[0,'d1_source_close_time']<=out.loc[0,'decision_time']
    assert out.loc[0,'h4_source_close_time']<=out.loc[0,'decision_time']


def test_researchable_cell_requires_both_direction_stability_and_adjacent_horizon():
    base={
        'summary_type':'INTERACTION','timeframe':'H1','hypothesis':'TIMEFRAME_TREND',
        'axis_1':'trend_state','category_1':'WEAK_TREND','axis_2':'volatility_bucket','category_2':'LOW',
        'n':200,'n_2025':100,'n_2026':100,'positive_rate':0.61,'median_return_atr':0.5,
        'source_sign_stable_positive':True,'median_mfe_mae_ratio':1.5,'top_hour_share':0.3,
        'n_long':100,'n_short':100,'positive_rate_long':0.60,'positive_rate_short':0.58,
        'mean_return_atr_long':0.5,'median_return_atr_long':0.4,
        'mean_return_atr_short':0.3,'median_return_atr_short':0.2,
    }
    df=pd.DataFrame([dict(base,horizon_hours=24),dict(base,horizon_hours=48,median_return_atr=0.7)])
    out=s.add_researchable_flags(df)
    assert out['researchable_distribution_cell'].all()
    bad=df.copy(); bad['median_return_atr_short']=-0.1
    out2=s.add_researchable_flags(bad)
    assert not out2['researchable_distribution_cell'].any()
    assert out2['direction_biased_research_lead'].all()
