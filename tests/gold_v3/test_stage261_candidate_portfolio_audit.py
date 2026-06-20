from __future__ import annotations

import pandas as pd

from stage261_candidate_portfolio_audit import first_come, overlap


def test_first_come_preserves_unknown_outcome_and_blocks_following_event() -> None:
    events = pd.DataFrame([
        {'candidate_id':'E5','candidate_family':'A','live_parity_tier':'LIVE_PARITY_PASS','entry_time':pd.Timestamp('2025-01-01 10:00'),'direction':'LONG','half':'2025H1'},
        {'candidate_id':'E7','candidate_family':'B','live_parity_tier':'LIVE_PARITY_PASS','entry_time':pd.Timestamp('2025-01-01 10:30'),'direction':'SHORT','half':'2025H1'},
        {'candidate_id':'E8','candidate_family':'C','live_parity_tier':'LIVE_PARITY_PASS','entry_time':pd.Timestamp('2025-01-01 14:30'),'direction':'LONG','half':'2025H1'},
    ])
    trades = pd.DataFrame([
        {'candidate_id':'E8','candidate_family':'C','live_parity_tier':'LIVE_PARITY_PASS','entry_time':pd.Timestamp('2025-01-01 14:30'),'direction':'LONG','half':'2025H1','quarter':'2025Q1','month':'2025-01','fixed_horizon':60,'fixed_tp':20.0,'fixed_sl':15.0,'result':'TP','exit_min':20,'exit_time':pd.Timestamp('2025-01-01 14:50'),'gross_pnl':20.0,'cost2_pnl':18.0},
    ])
    accepted, suppressed = first_come(events, trades, fixed_120=False)
    assert len(accepted) == 2
    assert accepted.iloc[0]['result'] == 'OUTCOME_UNAVAILABLE'
    assert accepted.iloc[1]['candidate_id'] == 'E8'
    assert len(suppressed) == 1
    assert suppressed.iloc[0]['candidate_id'] == 'E7'


def test_overlap_nonreplacement_and_direction_rate() -> None:
    a = pd.DataFrame([
        {'entry_time':pd.Timestamp('2025-01-01 10:00'),'direction':'LONG'},
        {'entry_time':pd.Timestamp('2025-01-01 10:10'),'direction':'SHORT'},
    ])
    b = pd.DataFrame([
        {'entry_time':pd.Timestamp('2025-01-01 10:05'),'direction':'LONG'},
    ])
    result = overlap(a, b, 15)
    assert result['matched_pairs'] == 1
    assert result['same_direction_rate'] == 1.0
