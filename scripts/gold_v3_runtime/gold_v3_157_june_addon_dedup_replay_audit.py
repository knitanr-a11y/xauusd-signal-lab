#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse,json,math,time,re
from datetime import datetime,timezone
from pathlib import Path
import pandas as pd
import gold_v3_107gy_light_non_calendar_subfilter_search_audit as gy
STEP='GOLD_V3_157_JUNE_ADDON_DEDUP_REPLAY_AUDIT_ONLY'
DEFAULT_CURRENT='density_safe||100||Q0.6'
CUTOFF='2026-06-05 15:15:00'

def load(p): return pd.read_csv(p,encoding='utf-8-sig',low_memory=False) if p.exists() else pd.DataFrame()
def save(df,p): p.parent.mkdir(parents=True,exist_ok=True); df.to_csv(p,index=False,encoding='utf-8-sig')
def readj(p):
    try: return json.loads(p.read_text(encoding='utf-8')) if p.exists() else {}
    except Exception: return {}
def prog(out,d,t,label,t0):
    msg=f'[PROGRESS] config {d}/{t} ({(d/t*100 if t else 100):.1f}%) {label} elapsed={time.time()-t0:.1f}s'
    print(msg,flush=True); (out/'progress.txt').write_text(msg+'\n',encoding='utf-8'); (out/'progress.json').write_text(json.dumps({'done':d,'total':t,'label':label,'elapsed_seconds':round(time.time()-t0,1)},ensure_ascii=False,indent=2),encoding='utf-8')
def pf(v):
    a=pd.to_numeric(pd.Series(v),errors='coerce').dropna().astype(float)
    if a.empty: return 0.0
    gp=float(a[a>0].sum()); gl=float(-a[a<0].sum())
    return gp/gl if gl>0 else (math.inf if gp>0 else 0.0)
def metric(df,result_col):
    if df.empty or result_col not in df.columns:
        return dict(events=0,sum=0.0,pf=0.0,win_rate=0.0,neg_events=0,months=0,neg_months=0,june_events=0,june_sum=0.0)
    r=pd.to_numeric(df[result_col],errors='coerce').fillna(0); m=df.groupby('month')[result_col].sum() if 'month' in df.columns else pd.Series(dtype=float)
    return dict(events=int(len(df)),sum=float(r.sum()),pf=pf(r),win_rate=float((r>0).mean()) if len(r) else 0.0,neg_events=int((r<0).sum()),months=int(m.shape[0]) if len(m) else 0,neg_months=int((m<0).sum()) if len(m) else 0,june_events=int((df.month=='2026-06').sum()) if 'month' in df.columns else 0,june_sum=float(m.get('2026-06',0.0)) if len(m) else 0.0)
def addpref(d,p): return {p+k:v for k,v in d.items()}
def pick_policy_col(df):
    for c in ['policy_key','k2_policy_key','rule_key','policy','config_key']:
        if c in df.columns: return c
    return ''
def pick_result_col(df):
    for c in ['worst_result_usd','worst2','event_worst','result_usd','pnl_usd','profit_usd','rep_result_usd','rep2']:
        if c in df.columns: return c
    for c in df.columns:
        if re.search(r'(result|profit|pnl)',c,re.I) and pd.to_numeric(df[c],errors='coerce').notna().sum()>0: return c
    return ''
def ensure_cols(x):
    x=x.copy(); x['entry_dt']=pd.to_datetime(x['entry_dt'],errors='coerce') if 'entry_dt' in x.columns else pd.to_datetime(x.get('time',''),errors='coerce')
    x=x[x.entry_dt.notna()].copy(); x['month']=x.entry_dt.dt.to_period('M').astype(str); x['hour']=x.entry_dt.dt.hour; x['hour_bucket']=x.hour.map(lambda h:'00_05' if h<6 else ('06_11' if h<12 else ('12_17' if h<18 else '18_23')))
    return x
def score_cols(df): return [c for c in ['feature_score','score','ledger_score','max_score','score_threshold'] if c in df.columns]
def dedup(df,result_col,current_policy=''):
    if df.empty: return df.copy()
    x=df.copy(); sc=score_cols(x)
    for c in sc: x[c]=pd.to_numeric(x[c],errors='coerce')
    x['_is_current']=x.policy_key_norm.astype(str).eq(current_policy).astype(int) if current_policy else 0
    sort_cols=['entry_dt','_is_current']+sc
    asc=[True,False]+[False]*len(sc)
    x=x.sort_values(sort_cols,ascending=asc,kind='mergesort')
    return x.groupby('entry_dt',as_index=False,group_keys=False).head(1).drop(columns=['_is_current'],errors='ignore')
def gate_mask(df,row,current):
    gate_type=str(row.get('gate_type','')); pol=str(row.get('policy_key','')); col=str(row.get('gate_col','')); val=str(row.get('gate_value',''))
    m=~df.policy_key_norm.astype(str).eq(current)
    if gate_type=='POLICY_ONLY':
        m=m & df.policy_key_norm.astype(str).eq(pol)
    elif gate_type=='POLICY_AND_CATEGORICAL':
        m=m & df.policy_key_norm.astype(str).eq(pol)
        if col and col in df.columns: m=m & df[col].fillna('MISSING').astype(str).eq(val)
        else: m=pd.Series(False,index=df.index)
    elif gate_type=='CATEGORICAL':
        if col and col in df.columns: m=m & df[col].fillna('MISSING').astype(str).eq(val)
        else: m=pd.Series(False,index=df.index)
    else:
        m=pd.Series(False,index=df.index)
    return m.fillna(False)
def main():
    t0=time.time(); ap=argparse.ArgumentParser(); ap.add_argument('--mt5-files-dir',default=''); ap.add_argument('--top-n',type=int,default=40); args=ap.parse_args()
    mt5=gy.mt5_files_dir(args.mt5_files_dir); root=mt5/'FX_OUTPUTS'/'gold_v3'; out=root/'157'; out.mkdir(parents=True,exist_ok=True)
    s132=readj(root/'132'/'gold_v3_132_summary.json'); s131=readj(root/'131'/'gold_v3_131_summary.json'); s156=readj(root/'156'/'gold_v3_156_summary.json')
    cur=str(s156.get('current_best_policy_key') or s132.get('current_best_policy_key') or s131.get('current_best_policy_key') or DEFAULT_CURRENT)
    ledger=load(root/'107k2c'/'gold_v3_107k2_all_regime_ledgers.csv'); gates=load(root/'156'/'gold_v3_156_june_addon_gate_ranking.csv')
    blockers=[]
    if ledger.empty: blockers.append({'id':'missing_107k2c_ledger'})
    if gates.empty: blockers.append({'id':'missing_156_gate_ranking'})
    policy_col=pick_policy_col(ledger) if not ledger.empty else ''; result_col=pick_result_col(ledger) if not ledger.empty else ''
    if not blockers and not policy_col: blockers.append({'id':'missing_policy_key_column'})
    if not blockers and not result_col: blockers.append({'id':'missing_result_column'})
    total=max(1,min(args.top_n,len(gates))) if not blockers else 1; prog(out,0,total,'START',t0)
    ranking=pd.DataFrame(); selected_events=pd.DataFrame(); month_all=[]; rows=[]; done=0
    if not blockers:
        x=ensure_cols(ledger); x['policy_key_norm']=x[policy_col].astype(str); x[result_col]=pd.to_numeric(x[result_col],errors='coerce').fillna(0)
        cutoff=pd.Timestamp(CUTOFF); before=x[x.entry_dt<cutoff].copy(); after=x[x.entry_dt>=cutoff].copy(); current_after=after[after.policy_key_norm==cur].copy(); current_before=before[before.policy_key_norm==cur].copy()
        current_after_dedup=dedup(current_after,result_col,cur); current_before_dedup=dedup(current_before,result_col,cur)
        gtop=gates.head(args.top_n).copy()
        seen=set()
        for i,row in gtop.iterrows():
            key='|'.join([str(row.get('gate_type','')),str(row.get('policy_key','')),str(row.get('gate_col','')),str(row.get('gate_value',''))])
            if key in seen: continue
            seen.add(key); done+=1
            label=f"{row.get('gate_type','')}::{row.get('policy_key','')}::{row.get('gate_col','')}={row.get('gate_value','')}"
            ma=gate_mask(after,row,cur); mb=gate_mask(before,row,cur)
            addon_after=dedup(after[ma].copy(),result_col,cur); addon_before=dedup(before[mb].copy(),result_col,cur)
            comb_after=dedup(pd.concat([current_after,after[ma]],ignore_index=True),result_col,cur)
            comb_before=dedup(pd.concat([current_before,before[mb]],ignore_index=True),result_col,cur)
            rec={'addon_label':label,'gate_type':str(row.get('gate_type','')),'policy_key':str(row.get('policy_key','')),'gate_col':str(row.get('gate_col','')),'gate_value':str(row.get('gate_value','')),'raw_after_rows':int(ma.sum()),'raw_before_rows':int(mb.sum())}
            rec.update(addpref(metric(addon_after,result_col),'addon_after_dedup_'))
            rec.update(addpref(metric(addon_before,result_col),'addon_before_dedup_'))
            rec.update(addpref(metric(comb_after,result_col),'combined_after_dedup_'))
            rec.update(addpref(metric(comb_before,result_col),'combined_before_dedup_'))
            rec['current_after_dedup_events']=int(len(current_after_dedup)); rec['current_before_dedup_events']=int(len(current_before_dedup))
            rec['risk_note']='dedup replay: current best priority, addon only when current best absent at same timestamp'
            rows.append(rec)
            tmp=comb_after.copy(); tmp['addon_label']=label; month_all.append(tmp.groupby(['addon_label','month'],as_index=False)[result_col].agg(['count','sum']).reset_index().rename(columns={'count':'events','sum':'sum'}))
            if done%5==0 or done==total: prog(out,min(done,total),total,label[:80],t0)
            if done>=args.top_n: break
        ranking=pd.DataFrame(rows)
        if not ranking.empty:
            ranking['pass_flag']=(ranking.combined_after_dedup_events>=3)&(ranking.combined_after_dedup_sum>0)&(ranking.combined_after_dedup_pf>=1.2)&(ranking.addon_after_dedup_events>=3)&(ranking.addon_before_dedup_sum>0)&(ranking.addon_before_dedup_pf>=1.0)
            ranking['rank_score']=ranking.combined_after_dedup_sum+ranking.combined_after_dedup_pf*50+ranking.addon_after_dedup_win_rate*50-ranking.combined_after_dedup_neg_events*10+ranking.addon_before_dedup_pf*10+ranking.addon_after_dedup_events*0.2
            ranking=ranking.sort_values(['pass_flag','combined_after_dedup_sum','combined_after_dedup_pf','addon_after_dedup_events'],ascending=[False,False,False,False]).reset_index(drop=True)
            sel_label=str(ranking.iloc[0].addon_label)
            # reconstruct selected combined after events
            top=ranking.iloc[0]; gr=gates[(gates.gate_type.astype(str)==str(top.gate_type))&(gates.policy_key.astype(str)==str(top.policy_key))&(gates.gate_col.fillna('').astype(str)==str(top.gate_col))&(gates.gate_value.fillna('').astype(str)==str(top.gate_value))].head(1)
            if not gr.empty:
                m=gate_mask(after,gr.iloc[0],cur); selected_events=dedup(pd.concat([current_after,after[m]],ignore_index=True),result_col,cur)
        save(ranking,out/'gold_v3_157_june_addon_dedup_ranking.csv'); save(selected_events,out/'gold_v3_157_selected_combined_after_events.csv')
        mall=pd.concat(month_all,ignore_index=True) if month_all else pd.DataFrame(); save(mall,out/'gold_v3_157_combined_after_monthly_all.csv')
    else:
        prog(out,1,1,'BLOCKED',t0)
    selected=ranking.head(1) if not ranking.empty else pd.DataFrame()
    status='READY' if not blockers else 'INPUT_MISSING'
    decision='JUNE_ADDON_DEDUP_REPLAY_READY' if status=='READY' and not selected.empty else ('JUNE_ADDON_DEDUP_REPLAY_NO_CONFIG' if status=='READY' else 'JUNE_ADDON_DEDUP_REPLAY_INPUT_MISSING')
    summary={'step':STEP,'status':status,'ready':not blockers,'decision':decision,'created_at_utc':datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z'),'output_dir':str(out),'audit_only':True,'review_only':True,'current_best_policy_key':cur,'current_best_preserved':True,'dedup_rule':'one row per entry_dt; current best priority; addon selected by score columns only, never by result','cutoff':CUTOFF,'selected_addon_label':str(selected.iloc[0].addon_label) if not selected.empty else '','selected_pass_flag':bool(selected.iloc[0].pass_flag) if not selected.empty and 'pass_flag' in selected else False,'selected_combined_after_events':int(selected.iloc[0].combined_after_dedup_events) if not selected.empty else 0,'selected_combined_after_sum':float(selected.iloc[0].combined_after_dedup_sum) if not selected.empty else 0.0,'selected_combined_after_pf':float(selected.iloc[0].combined_after_dedup_pf) if not selected.empty else 0.0,'selected_addon_after_events':int(selected.iloc[0].addon_after_dedup_events) if not selected.empty else 0,'selected_addon_after_sum':float(selected.iloc[0].addon_after_dedup_sum) if not selected.empty else 0.0,'selected_addon_after_pf':float(selected.iloc[0].addon_after_dedup_pf) if not selected.empty else 0.0,'selected_addon_before_events':int(selected.iloc[0].addon_before_dedup_events) if not selected.empty else 0,'selected_addon_before_sum':float(selected.iloc[0].addon_before_dedup_sum) if not selected.empty else 0.0,'selected_addon_before_pf':float(selected.iloc[0].addon_before_dedup_pf) if not selected.empty else 0.0,'progress_total_configs':total,'progress_completed_configs':done if not blockers else 0,'progress_output':str(out/'progress.txt'),'source_156_decision':s156.get('decision',''),'source_csv_mutated':False,'contract_mutated':False,'open_asof_allowed':False,'candidate_pool_removed':False,'f002_exclusion_bypassed':False,'blocker_count':len(blockers),'elapsed_seconds':round(time.time()-t0,2)}
    (out/'gold_v3_157_summary.json').write_text(json.dumps(summary|{'blockers':blockers},ensure_ascii=False,indent=2,default=str),encoding='utf-8'); save(pd.DataFrame([summary]),out/'gold_v3_157_decision.csv')
    lines=['GOLD V3 157 PASTE_ME_JUNE_ADDON_DEDUP_REPLAY_AUDIT']+[f'{k}: {v}' for k,v in summary.items()]
    lines += ['','JUNE_ADDON_DEDUP_RANKING_TOP60',ranking.head(60).to_string(index=False) if not ranking.empty else 'NO_RANKING']
    lines += ['','SELECTED_COMBINED_AFTER_EVENTS_TOP80',selected_events.head(80).to_string(index=False) if not selected_events.empty else 'NO_SELECTED_EVENTS']
    lines += ['','INTERPRETATION','This is still audit-only. It converts Stage156 raw K2 rows into one-row-per-entry_dt combined replay with current-best priority. If a candidate survives here, it can be considered a June addon audit candidate, not final/live.']
    lines += ['','BLOCKERS','NO_BLOCKERS' if not blockers else json.dumps(blockers,ensure_ascii=False,indent=2)]
    (out/'paste_me.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({'ready':not blockers,'decision':decision,'paste_me':str(out/'paste_me.txt')},ensure_ascii=False,indent=2)); return 0 if not blockers else 2
if __name__=='__main__': raise SystemExit(main())
