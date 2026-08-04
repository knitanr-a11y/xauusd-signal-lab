from __future__ import annotations
from pathlib import Path
import json,hashlib
import numpy as np
import pandas as pd
from .contracts import SEED,ALLOWED_ENTRY_COLUMNS,TARGET_STATES
from .candidate_engine import build_candidates
from .exact_m1_execution import execute_candidates
from .portfolio_accounting import simulate_v19_priority,summarize_pnl,monthly_correlation
from .run_reproduction import load_data,period
from .wave_state import build_wave_ledger,SCALES

ROOT=Path('/mnt/data');BASE=ROOT/'GOLD_CHALLENGER_C1_V2_DATA_V3_RESEARCH_20260801';OUT=BASE/'outputs'
def writej(n,o):(OUT/n).write_text(json.dumps(o,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
def pct(a,v):return float(np.mean(np.asarray(a,float)<=float(v)))
def metrics(df,cost=0):return summarize_pnl(df.resolved_pnl.to_numpy(float)-cost if len(df) else [])
def make_events(wave,mode='interaction',states=None):
    x=wave.sort_values(['entry_time','origin_id']).reset_index(drop=True);gap=x.entry_time.diff().dt.total_seconds()/60;sidechg=x.chosen_side.ne(x.chosen_side.shift())
    if mode=='interaction':eligible=x.chosen_rank.lt(.9)&x.wave_state.isin(states or TARGET_STATES);zone=np.where(eligible,'I_'+x.wave_state.astype(str),'OTHER')
    elif mode=='wave_only':eligible=x.wave_state.isin(states or TARGET_STATES);zone=np.where(eligible,'W_'+x.wave_state.astype(str),'OTHER')
    elif mode=='e40_only':eligible=x.chosen_rank.lt(.9);zone=np.where(eligible,'SUBP90','OTHER')
    elif mode=='all_subp90_wave_transitions':eligible=x.chosen_rank.lt(.9);zone=np.where(eligible,'R_'+x.wave_state.astype(str),'OTHER')
    else:raise ValueError(mode)
    zchg=pd.Series(zone).ne(pd.Series(zone).shift());on=gap.eq(15)&(sidechg|zchg)&eligible
    c=x.loc[on,['origin_id','entry_time','entry_idx','chosen_side','chosen_rank','wave_state','period']].copy();c=c.rename(columns={'entry_time':'decision_dt'});c['entry_time']=c.decision_dt;c['candidate_id']=np.arange(len(c));return c

def exec_and_port(c,m1,vexec):
    e=execute_candidates(c,m1);cc,vv,comb,supp=simulate_v19_priority(e,vexec,m1,True);return e,cc,vv,comb,supp

def main():
    rng=np.random.default_rng(SEED);data=load_data();wave=pd.read_csv(OUT/'data_v3_router_wave_ledger.csv.gz',parse_dates=['entry_time']);base_c=pd.read_csv(OUT/'data_v3_candidate_natural_execution.csv',parse_dates=['decision_dt','entry_time','natural_exit_dt']);base_cc=pd.read_csv(OUT/'data_v3_challenger_v19_priority_trades.csv',parse_dates=['decision_dt','entry_time','natural_exit_dt','resolved_exit_dt']);base_cc=base_cc[np.isfinite(base_cc.resolved_pnl)].copy();vexec=pd.read_csv(OUT/'data_v3_v19_recalculated_trades.csv',parse_dates=['decision_dt','entry_time','natural_exit_dt']);vbase=pd.read_csv(OUT/'data_v3_v19_recalculated_trades.csv',parse_dates=['resolved_exit_dt']) if 'resolved_exit_dt' in pd.read_csv(OUT/'data_v3_v19_recalculated_trades.csv',nrows=1).columns else None
    # vexec needs only natural columns for simulator.
    # Period, direction, cost.
    period_rows=[]
    for p,g in base_cc.groupby('period',sort=True):period_rows.append({'period':p,**metrics(g)})
    pd.DataFrame(period_rows).to_csv(OUT/'robustness_forward_period.csv',index=False)
    pd.DataFrame([{'chosen_side':s,**metrics(base_cc[base_cc.chosen_side.eq(s)])} for s in ['LONG','SHORT']]).to_csv(OUT/'robustness_direction.csv',index=False)
    pd.DataFrame([{'additional_cost':c,**metrics(base_cc,c)} for c in [0,.30,.60]]).to_csv(OUT/'robustness_cost.csv',index=False)
    # Month block bootstrap.
    b=base_cc.assign(exit_month=pd.to_datetime(base_cc.resolved_exit_dt).dt.to_period('M').astype(str));blocks=[g.resolved_pnl.to_numpy(float) for _,g in b.groupby('exit_month',sort=True)];boot=[]
    for _ in range(2000):
        p=np.concatenate([blocks[i] for i in rng.integers(0,len(blocks),len(blocks))]);s=summarize_pnl(p);boot.append((s['net'],s['pf']))
    boot=np.asarray(boot);boot_res={'iterations':2000,'months':len(blocks),'net_positive_probability':float(np.mean(boot[:,0]>0)),'pf_above_1_probability':float(np.mean(boot[:,1]>1)),'net_p05':float(np.quantile(boot[:,0],.05)),'net_median':float(np.median(boot[:,0])),'pf_p05':float(np.quantile(boot[:,1],.05)),'pf_median':float(np.median(boot[:,1]))};writej('month_block_bootstrap_summary.json',boot_res);pd.DataFrame(boot,columns=['net','pf']).to_csv(OUT/'month_block_bootstrap_iterations.csv',index=False)
    # Precompute exact outcomes for every router row, enabling fixed controls without outcome access in candidate generation.
    allc=wave[['origin_id','entry_time','entry_idx','chosen_side','chosen_rank','wave_state','period']].copy().rename(columns={'entry_time':'decision_dt'});allc['entry_time']=allc.decision_dt;allc['candidate_id']=np.arange(len(allc));allex=execute_candidates(allc,data['M1']);outmap=allex.set_index('origin_id')
    def attach(c):
        z=c.drop(columns=[q for q in ['natural_pnl','natural_exit_idx','natural_exit_reason','natural_exit_dt'] if q in c],errors='ignore').merge(outmap[['natural_pnl','natural_exit_idx','natural_exit_reason','natural_exit_dt']],left_on='origin_id',right_index=True,how='left',validate='one_to_one');return z
    # Matched random from the accepted all-subP90-wave-transition portfolio, exact base resolved counts by month and side.
    pool=make_events(wave,'all_subp90_wave_transitions');pool=attach(pool);pool_cc,_,_,_=simulate_v19_priority(pool,vexec,data['M1'],True);pool_cc=pool_cc[np.isfinite(pool_cc.resolved_pnl)].copy();pool_cc['month']=pd.to_datetime(pool_cc.entry_time).dt.to_period('M').astype(str);base_cc['month']=pd.to_datetime(base_cc.entry_time).dt.to_period('M').astype(str);targets=base_cc.groupby(['month','chosen_side']).size();groups={(m,s):g for (m,s),g in pool_cc.groupby(['month','chosen_side'])};feasible=all(k in groups and len(groups[k])>=n for k,n in targets.items());mr=[]
    if feasible:
        for _ in range(2000):
            sel=[]
            for k,n in targets.items():sel.append(groups[k].iloc[rng.choice(len(groups[k]),size=n,replace=False)])
            z=pd.concat(sel);s=summarize_pnl(z.resolved_pnl);mr.append((s['net'],s['pf']))
    mr=np.asarray(mr,float) if mr else np.empty((0,2));actual=metrics(base_cc);mr_res={'feasible':feasible,'iterations':len(mr),'actual_net':actual['net'],'actual_pf':actual['pf'],'net_percentile':pct(mr[:,0],actual['net']) if len(mr) else None,'pf_percentile':pct(mr[:,1],actual['pf']) if len(mr) else None,'pool_trades':len(pool_cc)};writej('matched_random_summary.json',mr_res);pd.DataFrame(mr,columns=['net','pf']).to_csv(OUT/'matched_random_iterations.csv',index=False)
    # Pseudo wave-state circular shifts within fixed periods.
    pseudo=[];period_indices={p:g.index.to_numpy() for p,g in wave.groupby('period',sort=False)}
    for _ in range(2000):
        w=wave.copy();states=w.wave_state.to_numpy(object).copy()
        for p,ii in period_indices.items():
            n=len(ii);off=int(rng.integers(32,max(33,n-31))) if n>64 else 1;states[ii]=np.roll(states[ii],off)
        w['wave_state']=states;c=make_events(w,'interaction');c=attach(c);cc,_,_,_=simulate_v19_priority(c,vexec,data['M1'],True);cc=cc[np.isfinite(cc.resolved_pnl)];s=metrics(cc);pseudo.append((s['net'],s['pf'],len(cc)))
    pseudo=np.asarray(pseudo);ps_res={'iterations':2000,'actual_net':actual['net'],'actual_pf':actual['pf'],'net_percentile':pct(pseudo[:,0],actual['net']),'pf_percentile':pct(pseudo[:,1],actual['pf']),'median_trades':float(np.median(pseudo[:,2]))};writej('pseudo_wave_summary.json',ps_res);pd.DataFrame(pseudo,columns=['net','pf','trades']).to_csv(OUT/'pseudo_wave_iterations.csv',index=False)
    # Leave one scale out.
    loo=[]
    for name,tf,k,wgt in SCALES:
        lw=build_wave_ledger(wave.drop(columns=[c for c in wave if c.startswith(('M15_K','H1_K','H4_K')) or c.startswith('wave_') or c=='wave_state'],errors='ignore'),data,omit_scale=name)
        c=make_events(lw,'interaction');c=attach(c);cc,_,_,_=simulate_v19_priority(c,vexec,data['M1'],True);cc=cc[np.isfinite(cc.resolved_pnl)];loo.append({'omitted_scale':name,**metrics(cc),'raw_onsets':len(c)})
    loo_df=pd.DataFrame(loo);loo_df.to_csv(OUT/'leave_one_scale_out.csv',index=False)
    # Component comparison.
    comps=[]
    for mode in ['wave_only','e40_only','interaction']:
        c=make_events(wave,mode);c=attach(c);cc,_,_,_=simulate_v19_priority(c,vexec,data['M1'],True);cc=cc[np.isfinite(cc.resolved_pnl)];comps.append({'component':mode,**metrics(cc),'raw_onsets':len(c)})
    pd.DataFrame(comps).to_csv(OUT/'wave_e40_interaction.csv',index=False)
    # Rank bands.
    labels=['LT_050','050_070','070_080','080_090'];base_cc['rank_band']=pd.cut(base_cc.chosen_rank,[-np.inf,.5,.7,.8,.9],labels=labels,right=False);pd.DataFrame([{'rank_band':x,**metrics(base_cc[base_cc.rank_band.eq(x)])} for x in labels]).to_csv(OUT/'rank_band_diagnostic.csv',index=False)
    # V19 overlap and additive counts.
    vints=vexec[['entry_idx','natural_exit_idx']].to_numpy(int);raw=make_events(wave,'interaction');eq=0;active=0
    for r in raw.itertuples():
        if np.any(vints[:,0]==r.entry_idx):eq+=1
        if np.any((vints[:,0]<=r.entry_idx)&(r.entry_idx<=vints[:,1])):active+=1
    overlap={'raw_onsets':len(raw),'same_timestamp_v19':eq,'inside_v19_open':active,'inside_v19_open_rate':active/max(1,len(raw)),'resolved_net_additive_trades':len(base_cc)};writej('v19_overlap_and_additive.json',overlap)
    # Combined and preempt fixed comparison already produced.
    comb=pd.read_csv(OUT/'data_v3_combined_portfolio.csv',parse_dates=['resolved_exit_dt']);vv=comb[comb.system.eq('V19')];cc=comb[comb.system.eq('CHALLENGER') & np.isfinite(comb.resolved_pnl)];corr,monthly=monthly_correlation(vv,cc);monthly.to_csv(OUT/'robustness_monthly_correlation.csv',index=False)
    no_c=pd.read_csv(OUT/'counterfactual_no_preempt_challenger.csv',parse_dates=['resolved_exit_dt']);no_v=pd.read_csv(OUT/'counterfactual_no_preempt_v19.csv',parse_dates=['resolved_exit_dt']);no_comb=pd.concat([no_c,no_v],ignore_index=True,sort=False);no_comb=no_comb[np.isfinite(no_comb.resolved_pnl)].sort_values(['resolved_exit_dt','resolved_exit_idx','entry_idx']).reset_index(drop=True);preempt={'main_v19_priority_combined':summarize_pnl(comb.resolved_pnl),'counterfactual_no_preempt_combined':summarize_pnl(no_comb.resolved_pnl),'policy_selection_authorized':False};writej('preempt_fixed_comparison.json',preempt)
    # Formal gate.
    per=pd.read_csv(OUT/'robustness_forward_period.csv');direc=pd.read_csv(OUT/'robustness_direction.csv');cost=pd.read_csv(OUT/'robustness_cost.csv');v19m=metrics(vv);combined=metrics(comb[np.isfinite(comb.resolved_pnl)]);gates={
      'minimum_resolved_trades':actual['trades']>=80,'pooled_pf':actual['pf']>=1.20,'pooled_net_positive':actual['net']>0,'positive_forward_periods':int((per.net>0).sum())>=4,'long_pf':float(direc.loc[direc.chosen_side.eq('LONG'),'pf'].iloc[0])>=1.0,'short_pf':float(direc.loc[direc.chosen_side.eq('SHORT'),'pf'].iloc[0])>=1.0,'direction_counts':bool((direc.trades>=15).all()),'cost_060_pf':float(cost.loc[cost.additional_cost.eq(.6),'pf'].iloc[0])>=1.10,'bootstrap':boot_res['net_positive_probability']>=.90,'matched_random':bool(feasible and mr_res['net_percentile']>=.95 and mr_res['pf_percentile']>=.95),'pseudo_wave':bool(ps_res['pf_percentile']>=.95),'leave_one_scale_out':bool((loo_df.pf>=1.0).all()),'combined_pf_degradation':combined['pf']>=v19m['pf']-.05,'combined_dd_increase':combined['max_dd']<=v19m['max_dd']+20,'dual_execution':True}
    formal={'classification':'RETROSPECTIVE_STRUCTURAL_ROBUSTNESS_ONLY' if all(gates.values()) else 'RETROSPECTIVE_STRUCTURAL_ROBUSTNESS_FAILED','all_gates_pass':all(gates.values()),'gates':gates,'base':actual,'combined':combined,'v19':v19m,'monthly_pnl_correlation':corr,'matched_random':mr_res,'pseudo_wave':ps_res,'bootstrap':boot_res,'overlap':overlap};writej('formal_robustness_result.json',formal);print(json.dumps(formal,indent=2,default=str))
if __name__=='__main__':main()
