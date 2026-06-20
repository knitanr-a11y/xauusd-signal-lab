from __future__ import annotations

import pandas as pd

from stage262_live_resolvable_exit import (
    CandidateTrade, StreamingExitEngine, evaluate_trade_batch, plan_trade,
)


def cal(published='2024-12-01 00:00:00'):
    return pd.DataFrame([{
        'calendar_id':'C1','broker_or_server_id':'S1','symbol_group':'GOLD','server_timezone':'UTC',
        'session_date':'2025-01-02','session_open_time':'2025-01-02 01:00:00',
        'session_close_time':'2025-01-02 23:59:00','is_holiday_closed':False,
        'is_short_session':False,'published_at':published,'source_name':'BROKER','source_version':'V1',
    }])


def candidate(entry='2025-01-02 20:00:00', direction='LONG'):
    return CandidateTrade('E5','K1',pd.Timestamp(entry),direction,240,10.0,5.0)


def test_same_m1_sl_priority():
    p=plan_trade(candidate(),cal())
    m1=pd.DataFrame([
        {'time':'2025-01-02 20:00:00','open':100,'high':111,'low':94,'close':105},
        {'time':'2025-01-02 23:54:00','open':105,'high':105,'low':105,'close':105},
    ])
    r=evaluate_trade_batch(p,m1)
    assert r['exit_reason']=='SL_EXIT'
    assert r['gross_pnl']==-5.0


def test_forced_exit_exact_open():
    p=plan_trade(candidate(),cal())
    m1=pd.DataFrame([
        {'time':'2025-01-02 20:00:00','open':100,'high':101,'low':99,'close':100},
        {'time':'2025-01-02 23:54:00','open':103,'high':104,'low':102,'close':103},
    ])
    r=evaluate_trade_batch(p,m1)
    assert r['exit_reason']=='FORCED_EXIT'
    assert r['exit_time']==pd.Timestamp('2025-01-02 23:54:00')
    assert r['gross_pnl']==3.0


def test_calendar_not_preknown_no_entry():
    p=plan_trade(candidate(),cal('2025-01-02 21:00:00'))
    assert p.eligibility_status=='CALENDAR_NOT_PREKNOWN_NO_ENTRY'


def test_missing_calendar_no_entry():
    p=plan_trade(candidate(),cal().iloc[0:0])
    assert p.eligibility_status=='CALENDAR_MISSING_NO_ENTRY'


def test_restart_parity():
    p=plan_trade(candidate(),cal())
    bars=[
        {'time':pd.Timestamp('2025-01-02 20:00:00'),'open':100,'high':101,'low':99,'close':100},
        {'time':pd.Timestamp('2025-01-02 20:01:00'),'open':100,'high':102,'low':99,'close':101},
        {'time':pd.Timestamp('2025-01-02 23:54:00'),'open':103,'high':104,'low':102,'close':103},
    ]
    full=StreamingExitEngine(); full.add_plan(p,bars[0])
    for b in bars: full.on_bar(b)
    first=StreamingExitEngine(); first.add_plan(p,bars[0]); first.on_bar(bars[0]); first.on_bar(bars[1])
    restored=StreamingExitEngine.from_snapshot(first.snapshot()); restored.on_bar(bars[2])
    a=full.states['K1']; b=restored.states['K1']
    assert a.exit_reason==b.exit_reason=='FORCED_EXIT'
    assert a.exit_price==b.exit_price==103.0
