#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse,json,math,time,re
from datetime import datetime,timezone
import pandas as pd
import gold_v3_107gy_light_non_calendar_subfilter_search_audit as gy
STEP='GOLD_V3_162_CURRENT_BEST_MULTIPLICITY_STACK_AUDIT_ONLY'
CUR='density_safe||100||Q0.6'

def load(p): return pd.read_csv(p,encoding='utf-8-sig',low_memory=False) if p.exists() else pd.DataFrame()
def save(df,p): p.parent.mkdir(parents=True,exist_ok=True); df.to_csv(p,index=False,encoding='utf-8-sig')
def readj(p):
    try: return json.loads(p.read_text(encoding='utf-8')) if p.exists() else {}
    except Exception: return {}
def prog(out,d,t,label,t0):
    msg=f'[PROGRESS] config {d}/{t} {label} elapsed={time.time()-t0:.1f}s'; print(msg,flush=True); (out/'progress.txt').write_text(msg+'\n',encoding='utf-8')
def pf(s):
    x=pd.to_numeric(pd.Series(s),errors='coerce').dropna().astype(float)
    if x.empty: return 0.0
    gp=float(x[x>0].sum()); gl=float(-x[x<0].sum())
    return gp/gl if gl>0 else (math.inf if gp>0 else 0.0)
def col(df,names):
    for n in names:
        if n in df.columns: return n
    return ''
def met(v):
    x=pd.to_numeric(pd.Series(v),errors='coerce').fillna(0)
    return {'count':int(len(x)),'sum':float(x.sum()),'pf':pf(x),'wr':float((x>0).mean()) if len(x) else 0.0,'neg':int((x<0).sum())}
def uniq(g,c): return int(g[c].nunique(dropna=True)) if c in g.columns else 0
def vals(g,c): return ';'.join(map(str,g[c].dropna().astype(str).unique()[:8])) if c in g.columns else ''
def main():
    t0=time.time(); ap=argparse.ArgumentParser(); ap.add_argument('--mt5-files-dir',default=''); args=ap.parse_args(); mt5=gy.mt5_files_dir(args.mt5_files_dir); root=mt5/'FX_OUTPUTS'/'gold_v3'; out=root/'162'; out.mkdir(parents=True,exist_ok=True)
    s161=readj(root/'161'/'gold_v3_161_summary.json'); cur=str(s161.get('current_best_policy_key') or CUR)
    raw=load(root/'107k2c'/'gold_v3_107k2_all_regime_ledgers.csv'); blockers=[]
    pc=col(raw,['policy_key','k2_policy_key','rule_key','policy']); rc=col(raw,['result_usd','worst_result_usd','pnl_usd','profit_usd','rep_result_usd'])
    if raw.empty: blockers.append({'id':'missing_ledger'})
    if not pc: blockers.append({'id':'missing_policy_column'})
    if not rc: blockers.append({'id':'missing_result_column'})
    prog(out,0,1,'START',t0); detail=pd.DataFrame(); summary_rows=[]; modes=[]
    if not blockers:
        x=raw.copy(); x['entry_dt']=pd.to_datetime(x['entry_dt'],errors='coerce'); x=x[x.entry_dt.notna()].copy(); x['month']=x.entry_dt.dt.to_period('M').astype(str); x['policy_norm']=x[pc].astype(str); x[rc]=pd.to_numeric(x[rc],errors='coerce').fillna(0)
        c=x[x.policy_norm.eq(cur)].copy()
        for dt,g in c.groupby('entry_dt'):
            result_sum=float(g[rc].sum()); result_mean=float(g[rc].mean())
            summary_rows.append({'entry_dt':dt,'rows':int(len(g)),'stack_sum':result_sum,'row_mean':result_mean,'unique_side':uniq(g,'side'),'side_values':vals(g,'side'),'unique_condition':uniq(g,'condition'),'condition_values':vals(g,'condition'),'unique_profile_id':uniq(g,'profile_id'),'profile_values':vals(g,'profile_id'),'unique_candidate_key':uniq(g,'candidate_key'),'unique_result':uniq(g,rc),'min_result':float(g[rc].min()),'max_result':float(g[rc].max())})
        detail=pd.DataFrame(summary_rows).sort_values(['rows','entry_dt'],ascending=[False,True])
        save(detail,out/'gold_v3_162_current_best_entry_multiplicity.csv')
        # metric modes: raw rows vs stacked timestamp PnL vs single best/worst/first rows
        raw_m=met(c[rc]); stack_m=met(detail['stack_sum'])
        first=c.sort_values('entry_dt').groupby('entry_dt',as_index=False).head(1); best=c.sort_values(['entry_dt',rc],ascending=[True,False]).groupby('entry_dt',as_index=False).head(1); worst=c.sort_values(['entry_dt',rc],ascending=[True,True]).groupby('entry_dt',as_index=False).head(1)
        modes=[{'mode':'RAW_ALL_ROWS_AS_SEPARATE_ORDERS',**raw_m},{'mode':'STACK_SUM_PER_ENTRY_DT',**stack_m},{'mode':'FIRST_ROW_PER_ENTRY_DT',**met(first[rc])},{'mode':'BEST_RESULT_PER_ENTRY_DT_DEBUG_ONLY',**met(best[rc])},{'mode':'WORST_RESULT_PER_ENTRY_DT_DEBUG_ONLY',**met(worst[rc])}]
        mode_df=pd.DataFrame(modes); save(mode_df,out/'gold_v3_162_current_best_stack_metric_modes.csv')
        dist=detail.rows.value_counts().sort_index().reset_index(); dist.columns=['rows_per_entry_dt','entry_dt_count']; save(dist,out/'gold_v3_162_rows_per_entry_distribution.csv')
    else:
        mode_df=pd.DataFrame(); dist=pd.DataFrame(); prog(out,1,1,'BLOCKED',t0)
    multi=int((detail.rows>1).sum()) if not detail.empty else 0; mixed_side=int((detail.unique_side>1).sum()) if not detail.empty else 0; multi_profile=int((detail.unique_profile_id>1).sum()) if not detail.empty else 0; total_dt=int(len(detail)) if not detail.empty else 0
    if mixed_side>0:
        interpretation='MIXED_SIDE_EXISTS_REVIEW_REQUIRED_STACKING_NOT_SAFE_AS_IS'
    elif multi_profile>0 or multi>0:
        interpretation='SAME_DIRECTION_MULTI_ROW_LIKELY_PROFILE_OR_VECTOR_STACKING_REVIEW'
    else:
        interpretation='SINGLE_ROW_PER_TIME_NO_STACKING_STRUCTURE'
    status='READY' if not blockers else 'INPUT_MISSING'; decision='CURRENT_BEST_MULTIPLICITY_STACK_READY' if status=='READY' else 'CURRENT_BEST_MULTIPLICITY_STACK_INPUT_MISSING'
    summary={'step':STEP,'status':status,'ready':not blockers,'decision':decision,'created_at_utc':datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z'),'output_dir':str(out),'audit_only':True,'review_only':True,'current_best_policy_key':cur,'total_policy_rows':int(mode_df.loc[mode_df.mode.eq('RAW_ALL_ROWS_AS_SEPARATE_ORDERS'),'count'].iloc[0]) if not mode_df.empty else 0,'unique_entry_dt':total_dt,'multi_row_entry_dt':multi,'mixed_side_entry_dt':mixed_side,'multi_profile_entry_dt':multi_profile,'interpretation':interpretation,'raw_pf':float(mode_df.loc[mode_df.mode.eq('RAW_ALL_ROWS_AS_SEPARATE_ORDERS'),'pf'].iloc[0]) if not mode_df.empty else 0.0,'stack_sum_pf':float(mode_df.loc[mode_df.mode.eq('STACK_SUM_PER_ENTRY_DT'),'pf'].iloc[0]) if not mode_df.empty else 0.0,'source_csv_mutated':False,'contract_mutated':False,'open_asof_allowed':False,'candidate_pool_removed':False,'f002_exclusion_bypassed':False,'blocker_count':len(blockers),'elapsed_seconds':round(time.time()-t0,2)}
    (out/'gold_v3_162_summary.json').write_text(json.dumps(summary|{'blockers':blockers},ensure_ascii=False,indent=2),encoding='utf-8'); save(pd.DataFrame([summary]),out/'gold_v3_162_decision.csv')
    lines=['GOLD V3 162 PASTE_ME_CURRENT_BEST_MULTIPLICITY_STACK_AUDIT']+[f'{k}: {v}' for k,v in summary.items()]+['','STACK_METRIC_MODES',mode_df.to_string(index=False) if not mode_df.empty else 'NO_MODES','','ROWS_PER_ENTRY_DISTRIBUTION',dist.to_string(index=False) if not dist.empty else 'NO_DISTRIBUTION','','TOP_MULTIPLICITY_ENTRY_DT',detail.head(80).to_string(index=False) if not detail.empty else 'NO_DETAIL','','INTERPRETATION','If mixed_side_entry_dt is 0 and many entry times have multiple rows/profiles, old current best may have been evaluated as stacked/vector rows. If mixed sides exist, MT5 stacking needs explicit conflict handling. Audit-only; no final/live.','','BLOCKERS','NO_BLOCKERS' if not blockers else json.dumps(blockers,ensure_ascii=False,indent=2)]
    (out/'paste_me.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({'ready':not blockers,'decision':decision,'paste_me':str(out/'paste_me.txt')},ensure_ascii=False)); return 0 if not blockers else 2
if __name__=='__main__': raise SystemExit(main())
