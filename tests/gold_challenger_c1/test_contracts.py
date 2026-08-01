from pathlib import Path
import pandas as pd, numpy as np, pytest
from gold_challenger_c1.e40_router import _rank_day,update_masks,build_feature_frame
from gold_challenger_c1.candidate_engine import build_candidates
from gold_challenger_c1.contracts import ALLOWED_ENTRY_COLUMNS
from gold_challenger_c1.data_io import read_candle
from gold_challenger_c1.wave_state import build_scale_features

def test_rank_uses_strictly_prior_dates_only():
 cur=pd.DataFrame({'entry_time':[pd.Timestamp('2026-01-02 01:00')],'score_long':[.5],'score_short':[.5]})
 hist=pd.DataFrame({'entry_time':[pd.Timestamp('2026-01-01'),pd.Timestamp('2026-01-02 00:00'),pd.Timestamp('2026-01-03')],'score_long':[.1,.99,.99],'score_short':[.1,.99,.99]})
 cal=pd.DataFrame({'entry_time':pd.date_range('2025-12-01',periods=100,freq='h'),'score_long':np.linspace(0,.4,100),'score_short':np.linspace(0,.4,100)})
 r=_rank_day(cur,hist,cal); prior=pd.concat([cal, hist.iloc[[0]]],ignore_index=True); expected=float((prior.score_long<=.5).mean()); assert r.rank_long.iloc[0]==expected

def test_current_row_not_in_rank_reference():
 cur=pd.DataFrame({'entry_time':[pd.Timestamp('2026-01-02 01:00')],'score_long':[1.0],'score_short':[1.0]});hist=pd.DataFrame(columns=cur.columns);cal=pd.DataFrame({'entry_time':pd.date_range('2025-12-01',periods=100,freq='h'),'score_long':np.zeros(100),'score_short':np.zeros(100)})
 assert _rank_day(cur,hist,cal).rank_long.iloc[0]==1.0

def test_future_test_scores_not_in_rank_reference():
 cur=pd.DataFrame({'entry_time':[pd.Timestamp('2026-01-02')],'score_long':[.5],'score_short':[.5]});hist=pd.DataFrame({'entry_time':[pd.Timestamp('2026-01-03')],'score_long':[0.0],'score_short':[0.0]});cal=pd.DataFrame({'entry_time':pd.date_range('2025-12-01',periods=100,freq='h'),'score_long':np.ones(100),'score_short':np.ones(100)})
 assert _rank_day(cur,hist,cal).rank_long.iloc[0]==0.0

def test_720_minute_embargo():
 d=pd.DatetimeIndex([pd.Timestamp('2025-06-30 11:59'),pd.Timestamp('2025-06-30 12:00'),pd.Timestamp('2025-07-01')]);train,cal=update_masks(d,pd.Timestamp('2026-01-01'));assert train.tolist()==[True,False,False]

def test_candidate_ignores_outcome_columns():
 x=pd.DataFrame(columns=list(ALLOWED_ENTRY_COLUMNS)+['pnl'])
 with pytest.raises(ValueError,match='NOT_WHITELISTED'):build_candidates(x)

def test_wave_state_uses_no_future_pivot():
 t=pd.date_range('2026-01-01',periods=100,freq='15min');d=pd.DataFrame({'time':t,'open':np.arange(100.),'high':np.arange(100.)+1,'low':np.arange(100.)-1,'close':np.sin(np.arange(100)/5)*10+100,'tick_volume':1,'spread':1});target=pd.DatetimeIndex([t[70]+pd.Timedelta(minutes=15)]);a=build_scale_features(d.iloc[:80].copy(),'M15',.8,'X',target);d2=pd.concat([d,pd.DataFrame({'time':pd.date_range(t[-1]+pd.Timedelta(minutes=15),periods=10,freq='15min'),'open':999,'high':1000,'low':1,'close':500,'tick_volume':1,'spread':1})],ignore_index=True);b=build_scale_features(d2,'M15',.8,'X',target);pd.testing.assert_frame_equal(a,b)

def test_source_hash_mismatch_fails_closed(tmp_path):
 p=tmp_path/'x.csv';p.write_text('time,open,high,low,close,tick_volume,spread\n2026.01.01 00:00:00,1,1,1,1,1,1\n')
 with pytest.raises(RuntimeError,match='SOURCE_HASH_MISMATCH'):read_candle(p,'0'*64)

def test_duplicate_timestamp_fails_closed(tmp_path):
 p=tmp_path/'x.csv';p.write_text('time,open,high,low,close,tick_volume,spread\n2026.01.01 00:00:00,1,1,1,1,1,1\n2026.01.01 00:00:00,1,1,1,1,1,1\n')
 with pytest.raises(ValueError,match='DUPLICATE'):read_candle(p)
