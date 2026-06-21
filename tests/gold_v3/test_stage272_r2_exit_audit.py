from types import SimpleNamespace
import importlib.util
import sys
import numpy as np
import pandas as pd

spec=importlib.util.spec_from_file_location('stage272','/mnt/data/stage272_r2_exit_audit.py')
stage272=importlib.util.module_from_spec(spec)
sys.modules['stage272']=stage272
spec.loader.exec_module(stage272)


def m1_df(opens, highs, lows, closes):
    return pd.DataFrame({
        'time':pd.date_range('2026-01-01',periods=len(opens),freq='min'),
        'open':opens,'high':highs,'low':lows,'close':closes,'spread':1,'source_id':'X'
    })


def h1_df():
    t=pd.date_range('2025-12-31 20:00',periods=10,freq='h')
    df=pd.DataFrame({'time':t,'open':100.,'high':101.,'low':99.,'close':100.5})
    df['close_time']=df.time+pd.Timedelta(hours=1)
    df['ema20']=100.
    df['prev3_low']=99.
    df['prev3_high']=101.
    df['bar_sign']=1.
    return df


def trade(direction=1, entry=100., atr=10.):
    return SimpleNamespace(activation_time=pd.Timestamp('2026-01-01 00:00'),activation_price=entry,h1_atr14=atr,direction=direction)


def test_fixed_exit_long_short_symmetry():
    n=24*60+1
    prices=np.linspace(100,110,n)
    m=m1_df(prices,prices+0.1,prices-0.1,prices)
    long=stage272.simulate_one(stage272.ExitSpec('F','fixed',24),trade(1),m,h1_df())
    short=stage272.simulate_one(stage272.ExitSpec('F','fixed',24),trade(-1),m,h1_df())
    assert np.isclose(long['gross_usd'],-short['gross_usd'])


def test_gap_through_stop_uses_worse_open():
    n=48*60+1
    opens=np.full(n,100.); highs=np.full(n,101.); lows=np.full(n,99.); closes=np.full(n,100.)
    opens[10]=84.; highs[10]=86.; lows[10]=83.; closes[10]=85.
    m=m1_df(opens,highs,lows,closes)
    out=stage272.simulate_one(stage272.ExitSpec('S','stop_fixed',48,stop_atr=1.5),trade(1,100,10),m,h1_df())
    assert out['exit_reason']=='STOP'
    assert out['exit_price']==84.
    assert out['gross_usd']==-16.


def test_partial_same_bar_stop_has_priority():
    n=48*60+1
    opens=np.full(n,100.); highs=np.full(n,101.); lows=np.full(n,99.); closes=np.full(n,100.)
    highs[5]=111.; lows[5]=84.
    m=m1_df(opens,highs,lows,closes)
    out=stage272.simulate_one(stage272.ExitSpec('P','partial_fixed',48,stop_atr=1.5,trigger_atr=1.0),trade(1,100,10),m,h1_df())
    assert out['exit_reason']=='STOP'
    assert not out['tp1_hit']
    assert np.isclose(out['gross_usd'],-15.)


def test_common_r2_sample_is_300_with_both_directions():
    r=stage272.select_r2()
    assert len(r)==300
    assert set(r.direction.unique())=={-1,1}
    assert (r.decision_time>=pd.Timestamp('2026-04-20 19:00')).sum()==34
