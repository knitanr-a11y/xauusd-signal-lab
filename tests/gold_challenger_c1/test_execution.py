import pandas as pd,numpy as np
from gold_challenger_c1.exact_m1_execution import execute_candidates
from gold_challenger_c1.portfolio_accounting import simulate_v19_priority

def m1(n=600):return pd.DataFrame({'time':pd.date_range('2026-01-01',periods=n,freq='min'),'open':100.,'high':100.,'low':100.,'close':100.,'tick_volume':1,'spread':1})
def cand(side='LONG',idx=0):return pd.DataFrame([{'candidate_id':1,'origin_id':1,'decision_dt':pd.Timestamp('2026-01-01')+pd.Timedelta(minutes=idx),'entry_time':pd.Timestamp('2026-01-01')+pd.Timedelta(minutes=idx),'entry_idx':idx,'chosen_side':side,'chosen_rank':.5,'wave_state':'IMPULSE_LATE'}])
def test_entry_mapping_matches_frozen_contract():
 d=m1();x=execute_candidates(cand(idx=15),d);assert x.entry_idx.iloc[0]==15 and d.time.iloc[15]==x.decision_dt.iloc[0]
def test_same_m1_tp_sl_is_sl_first():
 d=m1();d.loc[0,['high','low']]=[130,80];x=execute_candidates(cand(),d);assert x.natural_exit_reason.iloc[0]=='SL' and x.natural_pnl.iloc[0]==-10
def test_time_exit_uses_boundary_open_before_high_low():
 d=m1();d.loc[480,['open','high','low']]=[101,150,50];x=execute_candidates(cand(),d);assert x.natural_exit_reason.iloc[0]=='TIME' and abs(x.natural_pnl.iloc[0]-.7)<1e-12
def test_v19_is_not_preempted_before_v19_arrival():
 d=m1();c=execute_candidates(cand(idx=0),d);v=execute_candidates(cand(idx=30).rename(columns={'candidate_id':'vtmp'}),d);v['origin_id']=9;cc,vv,_,_=simulate_v19_priority(c,v,d,True);assert cc.resolved_exit_idx.iloc[0]==30
def test_v19_preempt_occurs_only_at_actual_timestamp():
 d=m1();c=execute_candidates(cand(idx=0),d);v=execute_candidates(cand(idx=30).rename(columns={'candidate_id':'vtmp'}),d);v['origin_id']=9;cc,_,_,_=simulate_v19_priority(c,v,d,True);assert cc.exit_reason.iloc[0]=='V19_PREEMPT' and cc.resolved_exit_dt.iloc[0]==d.time.iloc[30]
def test_one_position_non_overlap():
 d=m1();a=cand(idx=0);b=cand(idx=15);b['candidate_id']=2;b['origin_id']=2;c=execute_candidates(pd.concat([a,b],ignore_index=True),d);v=pd.DataFrame(columns=['origin_id','entry_idx','natural_exit_idx','natural_exit_dt','natural_pnl','chosen_side']);cc,_,_,supp=simulate_v19_priority(c,v,d,True);assert len(cc)==1 and len(supp)==1
