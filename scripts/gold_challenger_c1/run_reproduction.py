from __future__ import annotations
from pathlib import Path
import os
import json,hashlib
import numpy as np
import pandas as pd
from .data_io import read_union
from .e40_router import build_semiannual_ledger
from .wave_state import build_wave_ledger
from .candidate_engine import build_candidates
from .exact_m1_execution import execute_candidates,execute_candidates_simple
from .portfolio_accounting import simulate_v19_priority,summarize_pnl,monthly_correlation
from .parity_audit import first_router_mismatch
from .contracts import ALLOWED_ENTRY_COLUMNS

ROOT=Path(os.environ.get('GOLD_C1_SOURCE_ROOT','/mnt/data')).resolve()
BASE=Path(os.environ.get('GOLD_C1_RESEARCH_ROOT',str(ROOT/'GOLD_CHALLENGER_C1_V2_DATA_V3_RESEARCH_20260801'))).resolve()
OUT=BASE/'outputs';CFG=BASE/'config';DER=BASE/'derived_sources';OUT.mkdir(parents=True,exist_ok=True)
V10_REFERENCE=Path(os.environ.get('GOLD_C1_V10_REFERENCE',str(ROOT/'gold_challenger_c1_work'/'inputs'/'GOLD_NEXT_CHAT_REQUESTED_RESEARCH_INPUTS_20260801'/'V10_E40_signal_ledger.csv.gz'))).resolve()
V19_REFERENCE_ROOT=Path(os.environ.get('GOLD_C1_V19_REFERENCE_ROOT',str(ROOT/'gold_challenger_c1_work'/'v19'/'GOLD_FIRST_P90_IMPULSE_EARLY_EPISODE_ROBUSTNESS_V19_20260801'))).resolve()

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def writej(name,obj):(OUT/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2,default=str),encoding='utf-8')

def load_data():
 return {
 'M1':read_union([ROOT/'gold_v3_2023_2026_m1(3).csv',ROOT/'goldsharp_m1(3).csv']),
 'M5':read_union([ROOT/'gold_v3_2023_2026_m5(3).csv',ROOT/'goldsharp_m5(3).csv']),
 'M15':read_union([DER/'gold_m15_v3_derived_from_full_m1_union.csv']),
 'H1':read_union([ROOT/'gold_v3_2023_2026_h1(3).csv',ROOT/'goldsharp_h1(3).csv']),
 'H4':read_union([ROOT/'gold_v3_2023_2026_h4(3).csv',ROOT/'goldsharp_h4(3).csv']),
 }

def period(t):
 t=pd.Timestamp(t)
 return '2024H2' if t<pd.Timestamp('2025-01-01') else '2025H1' if t<pd.Timestamp('2025-07-01') else '2025H2' if t<pd.Timestamp('2026-01-01') else '2026H1' if t<pd.Timestamp('2026-07-01') else '2026JUL'

def main():
 data=load_data(); rr=build_semiannual_ledger(data); rr.ledger.to_csv(OUT/'data_v3_e40_router_ledger.csv.gz',index=False,compression='gzip');writej('model_update_metadata.json',rr.model_metadata)
 refp=V10_REFERENCE;ref=pd.read_csv(refp,parse_dates=['entry_time']);mismatch=first_router_mismatch(ref,rr.ledger,rr.model_metadata,data);writej('first_mismatch.json',mismatch)
 wave=build_wave_ledger(rr.ledger,data);wave.to_csv(OUT/'data_v3_router_wave_ledger.csv.gz',index=False,compression='gzip')
 x=pd.DataFrame({'decision_dt':wave.entry_time,'origin_id':wave.origin_id.astype(int),'entry_idx':wave.entry_idx.astype(int),'chosen_side':wave.chosen_side.astype(str),'chosen_rank':wave.chosen_rank.astype(float),'wave_state':wave.wave_state.astype(str),'episode_id':0,'previous_decision_dt':wave.entry_time.shift()})
 x=x.loc[:,ALLOWED_ENTRY_COLUMNS].copy();cand,events=build_candidates(x);cand['period']=cand.decision_dt.map(period);cand['entry_time']=cand.decision_dt
 cand_exec=execute_candidates(cand,data['M1']);simple=execute_candidates_simple(cand,data['M1'])
 checks={'rows':len(cand_exec),'entry_idx_exact':bool(np.array_equal(cand_exec.entry_idx.to_numpy(),simple.entry_idx.to_numpy())),'exit_idx_exact':bool(np.array_equal(cand_exec.natural_exit_idx.to_numpy(),simple.natural_exit_idx.to_numpy())),'reason_exact':bool(np.array_equal(cand_exec.natural_exit_reason.to_numpy(),simple.natural_exit_reason.to_numpy())),'pnl_exact':bool(np.allclose(cand_exec.natural_pnl,simple.natural_pnl,equal_nan=True,atol=0,rtol=0))};writej('raw_m1_dual_execution_parity.json',checks)
 if not all(v for k,v in checks.items() if k.endswith('exact')):raise RuntimeError('RAW_M1_DUAL_EXECUTION_MISMATCH')
 cand_exec.to_csv(OUT/'data_v3_candidate_natural_execution.csv',index=False);events.to_csv(OUT/'data_v3_candidate_event_timeline.csv',index=False)
 # Frozen V19 timestamps are read-only; outcomes are recalculated from DATA_V3 M1.
 v19root=V19_REFERENCE_ROOT;v=pd.read_csv(v19root/'trades_SEMIANNUAL_EXPANDING_P90.csv',parse_dates=['entry_time']);idx=pd.Index(data['M1'].time);v['entry_idx']=idx.get_indexer(v.entry_time);v=v[v.entry_idx>=0].copy();vbase=v[['origin_id','entry_time','entry_idx','chosen_side']].copy();vexec=execute_candidates(vbase.rename(columns={'entry_time':'decision_dt'}),data['M1']);vexec['entry_time']=vexec.decision_dt
 # Validate frozen V19 natural outcome on DATA_V3.
 vr=v.merge(vexec[['origin_id','natural_pnl','natural_exit_idx']],on='origin_id',suffixes=('_ref','_v3'));vpar={'trades':len(vr),'pnl_exact':bool(np.allclose(vr.immediate_pnl,vr.natural_pnl,atol=1e-9)),'exit_time_exact':bool(np.array_equal(pd.to_datetime(data['M1'].time.to_numpy()[vr.natural_exit_idx.to_numpy(int)]).to_numpy(),pd.to_datetime(data['M1'].time.to_numpy()[vr.immediate_exit_idx.to_numpy(int)]).to_numpy()))};writej('v19_data_v3_execution_parity.json',vpar)
 cc,vv,comb,supp=simulate_v19_priority(cand_exec,vexec,data['M1'],preempt=True);cc.to_csv(OUT/'data_v3_challenger_v19_priority_trades.csv',index=False);vv.to_csv(OUT/'data_v3_v19_recalculated_trades.csv',index=False);comb.to_csv(OUT/'data_v3_combined_portfolio.csv',index=False);supp.to_csv(OUT/'data_v3_suppressed_events.csv',index=False)
 cc_np,vv_np,comb_np,supp_np=simulate_v19_priority(cand_exec,vexec,data['M1'],preempt=False);cc_np.to_csv(OUT/'counterfactual_no_preempt_challenger.csv',index=False);vv_np.to_csv(OUT/'counterfactual_no_preempt_v19.csv',index=False)
 resolved_cc=cc[np.isfinite(cc.resolved_pnl)].copy() if len(cc) else cc;resolved_vv=vv[np.isfinite(vv.resolved_pnl)].copy() if len(vv) else vv;corr,monthly=monthly_correlation(resolved_vv,resolved_cc);monthly.to_csv(OUT/'monthly_pnl_correlation_inputs.csv',index=False)
 metrics={'candidate_raw_onsets':len(cand),'challenger_accepted':len(cc),'v19_accepted':len(vv),'candidate':summarize_pnl(cc.resolved_pnl if len(cc) else []),'v19':summarize_pnl(vv.resolved_pnl if len(vv) else []),'combined':summarize_pnl(comb.resolved_pnl if len(comb) else []),'counterfactual_no_preempt_combined':summarize_pnl(comb_np.resolved_pnl if len(comb_np) else []),'monthly_pnl_correlation':corr,'first_mismatch':mismatch,'raw_m1_dual_execution':checks,'v19_data_v3_parity':vpar}
 writej('base_result.json',metrics)
 print(json.dumps(metrics,indent=2,default=str))
if __name__=='__main__':main()
