from pathlib import Path
import sys
import pandas as pd
import numpy as np

sys.path.insert(0, '/mnt/data')
import stage265_htf_intrabar_breakout_audit as s


def candidate(decision='2025-01-06 08:00', direction='LONG', stop=100.0, hold=60, sl=1.0, tp=2.0):
    dt=pd.Timestamp(decision)
    return pd.DataFrame([{
        'strategy':'TEST','setup_id':'T1','time':dt-pd.Timedelta(hours=1),
        'decision_time':dt,'order_expiry':dt+pd.Timedelta(hours=1),
        'direction':direction,'context_state':direction,'candidate':True,
        'order_stop':stop,'atr14':10.0,'hold_minutes':hold,'sl_mult':sl,'tp_mult':tp,
    }])


def m1_frame(rows, source='GOLD_HASH_2025'):
    df=pd.DataFrame(rows, columns=['time','open','high','low','close'])
    df['time']=pd.to_datetime(df['time'])
    df['source_id']=source
    df['tick_volume']=1; df['spread']=0; df['real_volume']=0
    return df


def full_minutes(start, end, price=99.0):
    times=pd.date_range(start,end,freq='min')
    return pd.DataFrame({'time':times,'open':price,'high':price,'low':price,'close':price,
                         'source_id':'GOLD_HASH_2025','tick_volume':1,'spread':0,'real_volume':0})


def test_stop_touch_does_not_retroactively_fill_at_m1_open():
    m=full_minutes('2025-01-06 08:00','2025-01-06 09:00')
    m.loc[m.time==pd.Timestamp('2025-01-06 08:05'), ['open','high','low','close']] = [99,101,98.5,100.5]
    m.loc[m.time==pd.Timestamp('2025-01-06 08:10'), ['open','high','low','close']] = [110,121,109,120]
    out=s.simulate(candidate(),m).iloc[0]
    assert out.status=='RESOLVED'
    assert out.fill_bar_time==pd.Timestamp('2025-01-06 08:05')
    assert out.fill_price==100.0
    assert out.exit_reason=='TP_EXIT'


def test_gap_fill_uses_m1_open_not_stop():
    m=full_minutes('2025-01-06 08:00','2025-01-06 09:00')
    m.loc[m.time==pd.Timestamp('2025-01-06 08:00'), ['open','high','low','close']] = [103,104,102,103]
    m.loc[m.time==pd.Timestamp('2025-01-06 08:01'), ['open','high','low','close']] = [103,124,102,123]
    out=s.simulate(candidate(),m).iloc[0]
    assert out.gap_fill
    assert out.fill_price==103.0


def test_entry_and_sl_same_m1_is_sl_first():
    m=full_minutes('2025-01-06 08:00','2025-01-06 09:00')
    m.loc[m.time==pd.Timestamp('2025-01-06 08:00'), ['open','high','low','close']] = [99,121,89,110]
    out=s.simulate(candidate(),m).iloc[0]
    assert out.fill_price==100.0
    assert out.exit_reason=='SL_EXIT'
    assert out.exit_price==90.0


def test_future_missing_minute_does_not_cancel_trade_that_exited_before_gap():
    m=full_minutes('2025-01-06 08:00','2025-01-06 09:00')
    m.loc[m.time==pd.Timestamp('2025-01-06 08:00'), ['open','high','low','close']] = [99,101,98,100]
    m.loc[m.time==pd.Timestamp('2025-01-06 08:01'), ['open','high','low','close']] = [100,121,99,120]
    m=m[m.time!=pd.Timestamp('2025-01-06 08:30')]
    out=s.simulate(candidate(),m).iloc[0]
    assert out.status=='RESOLVED'
    assert out.exit_reason=='TP_EXIT'
    assert out.exit_time==pd.Timestamp('2025-01-06 08:01')
