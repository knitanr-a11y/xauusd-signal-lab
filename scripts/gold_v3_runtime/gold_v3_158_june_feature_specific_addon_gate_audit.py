#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse,json,math,time,re
from datetime import datetime,timezone
from pathlib import Path
import pandas as pd
import gold_v3_107gy_light_non_calendar_subfilter_search_audit as gy
STEP='GOLD_V3_158_JUNE_FEATURE_SPECIFIC_ADDON_GATE_AUDIT_ONLY'
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
def prep(df,policy_col,result_col):
    x=df.copy(); x['entry_dt']=pd.to_datetime(x['entry_dt'],errors='coerce') if 'entry_dt' in x.columns else pd.to_datetime(x.get('time',''),errors='coerce')
    x=x[x.entry_dt.notna()].copy(); x['month']=x.entry_dt.dt.to_period('M').astype(str); x['hour']=x.entry_dt.dt.hour; x['hour_bucket']=x.hour.map(lambda h:'00_05' if h<6 else ('06_11' if h<12 else ('12_17' if h<18 else '18_23')))
    x['policy_key_norm']=x[policy_col].astype(str); x[result_col]=pd.to_numeric(x[result_col],errors='coerce').fillna(0)
    return x
def score_cols(df): return [c for c in ['feature_score','score','ledger_score','max_score','score_threshold'] if c in df.columns]
def dedup(df,result_col):
    if df.empty: return df.copy()
    x=df.copy(); sc=score_cols(x)
    for c in sc: x[c]=pd.to_numeric(x[c],errors='coerce')
    return x.sort_values(['entry_dt']+sc,ascending=[True]+[False]*len(sc),kind='mergesort').groupby('entry_dt',as_index=False,group_keys=False).head(1)
def met(df,result_col):
    if df.empty: return {'events':0,'sum':0.0,'pf':0.0,'wr':0.0,'neg_events':0,'month_count':0,'neg_months':0,'june_events':0,'june_sum':0.0,'active_months':''}
    r=pd.to_numeric(df[result_col],errors='coerce').fillna(0); mo=df.groupby('month')[result_col].sum()
    return {'events':int(len(df)),'sum':float(r.sum()),'pf':pf(r),'wr':float((r>0).mean()),'neg_events':int((r<0).sum()),'month_count':int(mo.shape[0]),'neg_months':int((mo<0).sum()),'june_events':int((df.month=='2026-06').sum()),'june_sum':float(mo.get('2026-06',0.0)),'active_months':';'.join(mo.index.astype(str).tolist())}
def gate_eval(base,after,before,result_col,gate_label,mask_after,mask_before,live_safe=True,gate_kind=''):
    aa=dedup(after[mask_after].copy(),result_col); bb=dedup(before[mask_before].copy(),result_col)
    ma=met(aa,result_col); mb=met(bb,result_col)
    before_avg=mb['events']/max(1,mb['month_count'])
    specificity=ma['events']/(before_avg+1.0)
    return {'gate_label':gate_label,'gate_kind':gate_kind,'live_safe_feature_gate':bool(live_safe),**{f'after_{k}':v for k,v in ma.items()},**{f'before_{k}':v for k,v in mb.items()},'temporal_specificity':float(specificity),'before_monthly_avg_events':float(before_avg)}
def main():
    t0=time.time(); ap=argparse.ArgumentParser(); ap.add_argument('--mt5-files-dir',default=''); ap.add_argument('--min-after-events',type=int,default=3); args=ap.parse_args()
    mt5=gy.mt5_files_dir(args.mt5_files_dir); root=mt5/'FX_OUTPUTS'/'gold_v3'; out=root/'158'; out.mkdir(parents=True,exist_ok=True)
    ledger=load(root/'107k2c'/'gold_v3_107k2_all_regime_ledgers.csv'); s156=readj(root/'156'/'gold_v3_156_summary.json'); s157=readj(root/'157'/'gold_v3_157_summary.json')
    cur=str(s156.get('current_best_policy_key') or s157.get('current_best_policy_key') or DEFAULT_CURRENT)
    blockers=[]
    if ledger.empty: blockers.append({'id':'missing_107k2c_ledger'})
    pcol=pick_policy_col(ledger) if not ledger.empty else ''; rcol=pick_result_col(ledger) if not ledger.empty else ''
    if not blockers and not pcol: blockers.append({'id':'missing_policy_key_column'})
    if not blockers and not rcol: blockers.append({'id':'missing_result_column'})
    rows=[]; total=1; done=0; prog(out,0,total,'START',t0)
    if not blockers:
        x=prep(ledger,pcol,rcol); cutoff=pd.Timestamp(CUTOFF); base=x[x.policy_key_norm!=cur].copy(); after=base[base.entry_dt>=cutoff].copy(); before=base[base.entry_dt<cutoff].copy()
        cat_cols=[c for c in ['side','condition','hour_bucket','m15_up','h1_up','h4_up','d1_up','m15_close_gt_ema20','h1_close_gt_ema20','h4_close_gt_ema20','d1_close_gt_ema20'] if c in x.columns]
        audit_only_cols=[c for c in ['regime_split','source_name'] if c in x.columns]
        num_candidates=['cooldown_bars','score','feature_score','ledger_score','m15_atr28','m15_rsi14','m15_dist_atr','m15_range_atr','h1_atr28','h1_rsi14','h1_dist_atr','h1_range_atr','h4_atr28','h4_rsi14','h4_dist_atr','h4_range_atr','d1_atr28','d1_rsi14','d1_dist_atr','d1_range_atr']
        num_cols=[c for c in num_candidates if c in x.columns and pd.to_numeric(x[c],errors='coerce').notna().sum()>0]
        total=len(cat_cols)+len(audit_only_cols)+len(num_cols)*2
        # categorical live-safe feature gates
        for c in cat_cols:
            done+=1; prog(out,done,total,f'CAT {c}',t0)
            vals=after[c].fillna('MISSING').astype(str).value_counts().head(30).index.tolist()
            for v in vals:
                ma=after[c].fillna('MISSING').astype(str).eq(str(v)); mb=before[c].fillna('MISSING').astype(str).eq(str(v))
                rows.append(gate_eval(base,after,before,rcol,f'{c} == {v}',ma,mb,True,'CATEGORICAL_FEATURE'))
        # audit-only context labels, explicitly not live-safe
        for c in audit_only_cols:
            done+=1; prog(out,done,total,f'CTX {c}',t0)
            vals=after[c].fillna('MISSING').astype(str).value_counts().head(20).index.tolist()
            for v in vals:
                ma=after[c].fillna('MISSING').astype(str).eq(str(v)); mb=before[c].fillna('MISSING').astype(str).eq(str(v))
                rows.append(gate_eval(base,after,before,rcol,f'{c} == {v}',ma,mb,False,'AUDIT_ONLY_CONTEXT'))
        # numeric thresholds from after distribution; no result-based thresholding
        for c in num_cols:
            xa=pd.to_numeric(after[c],errors='coerce'); xb=pd.to_numeric(before[c],errors='coerce')
            qs=sorted(set([round(float(x),12) for x in xa.dropna().quantile([.1,.2,.3,.5,.7,.8,.9]).tolist() if pd.notna(x)]))
            done+=1; prog(out,min(done,total),total,f'NUM_GE {c}',t0)
            for th in qs:
                ma=xa>=th; mb=xb>=th
                rows.append(gate_eval(base,after,before,rcol,f'{c} >= {th}',ma,mb,True,'NUMERIC_GE'))
            done+=1; prog(out,min(done,total),total,f'NUM_LE {c}',t0)
            for th in qs:
                ma=xa<=th; mb=xb<=th
                rows.append(gate_eval(base,after,before,rcol,f'{c} <= {th}',ma,mb,True,'NUMERIC_LE'))
        rank=pd.DataFrame(rows)
        if not rank.empty:
            rank['strict_june_specific_pass']=(rank.live_safe_feature_gate)&(rank.after_events>=args.min_after_events)&(rank.after_sum>0)&(rank.after_pf>=1.2)&(rank.temporal_specificity>=2.0)&(rank.before_month_count<=6)
            rank['loose_june_specific_pass']=(rank.live_safe_feature_gate)&(rank.after_events>=args.min_after_events)&(rank.after_sum>0)&(rank.after_pf>=1.2)&(rank.temporal_specificity>=1.25)
            rank['rank_score']=rank.after_sum+rank.after_pf*50+rank.after_wr*50-rank.after_neg_events*8+rank.temporal_specificity*50-rank.before_month_count*10-rank.before_neg_months*10
            rank=rank.sort_values(['strict_june_specific_pass','loose_june_specific_pass','rank_score','after_sum'],ascending=[False,False,False,False]).reset_index(drop=True)
            selected=rank[(rank.strict_june_specific_pass)|(rank.loose_june_specific_pass)].head(30).copy()
        else:
            selected=pd.DataFrame()
        save(rank,out/'gold_v3_158_june_feature_specific_gate_ranking.csv'); save(selected,out/'gold_v3_158_selected_feature_specific_gates.csv')
    else:
        rank=pd.DataFrame(); selected=pd.DataFrame(); prog(out,1,1,'BLOCKED',t0)
    status='READY' if not blockers else 'INPUT_MISSING'
    decision='JUNE_FEATURE_SPECIFIC_GATE_READY' if status=='READY' and not selected.empty else ('JUNE_FEATURE_SPECIFIC_GATE_NO_PASS_FOUND_REVIEW_TOP_RANKS' if status=='READY' else 'JUNE_FEATURE_SPECIFIC_GATE_INPUT_MISSING')
    best=selected.head(1) if not selected.empty else pd.DataFrame()
    summary={'step':STEP,'status':status,'ready':not blockers,'decision':decision,'created_at_utc':datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z'),'output_dir':str(out),'audit_only':True,'review_only':True,'current_best_policy_key':cur,'current_best_preserved':True,'important_correction':'This stage does NOT use current-best absence as a gate. It searches June/after-cutoff feature specificity for non-current addon rows.','cutoff':CUTOFF,'selected_gate_label':str(best.iloc[0].gate_label) if not best.empty else '','selected_live_safe_feature_gate':bool(best.iloc[0].live_safe_feature_gate) if not best.empty else False,'selected_after_events':int(best.iloc[0].after_events) if not best.empty else 0,'selected_after_sum':float(best.iloc[0].after_sum) if not best.empty else 0.0,'selected_after_pf':float(best.iloc[0].after_pf) if not best.empty else 0.0,'selected_before_events':int(best.iloc[0].before_events) if not best.empty else 0,'selected_before_month_count':int(best.iloc[0].before_month_count) if not best.empty else 0,'selected_temporal_specificity':float(best.iloc[0].temporal_specificity) if not best.empty else 0.0,'candidate_count':int(len(rank)) if not rank.empty else 0,'selected_count':int(len(selected)) if not selected.empty else 0,'progress_total_configs':total,'progress_completed_configs':done if not blockers else 0,'progress_output':str(out/'progress.txt'),'source_csv_mutated':False,'contract_mutated':False,'open_asof_allowed':False,'candidate_pool_removed':False,'f002_exclusion_bypassed':False,'blocker_count':len(blockers),'elapsed_seconds':round(time.time()-t0,2)}
    (out/'gold_v3_158_summary.json').write_text(json.dumps(summary|{'blockers':blockers},ensure_ascii=False,indent=2,default=str),encoding='utf-8'); save(pd.DataFrame([summary]),out/'gold_v3_158_decision.csv')
    lines=['GOLD V3 158 PASTE_ME_JUNE_FEATURE_SPECIFIC_ADDON_GATE_AUDIT']+[f'{k}: {v}' for k,v in summary.items()]
    lines += ['','SELECTED_FEATURE_SPECIFIC_GATES_TOP30',selected.head(30).to_string(index=False) if not selected.empty else 'NO_SELECTED_FEATURE_SPECIFIC_GATES']
    lines += ['','FEATURE_SPECIFIC_GATE_RANKING_TOP100',rank.head(100).to_string(index=False) if not rank.empty else 'NO_RANKING']
    lines += ['','INTERPRETATION','This corrects Stage157 direction. It does not say addon only when current best has no same-timestamp row. Instead it searches feature/regime-like gates that are concentrated in the after-cutoff June environment. Audit-only; no final/live.']
    lines += ['','BLOCKERS','NO_BLOCKERS' if not blockers else json.dumps(blockers,ensure_ascii=False,indent=2)]
    (out/'paste_me.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({'ready':not blockers,'decision':decision,'paste_me':str(out/'paste_me.txt')},ensure_ascii=False,indent=2)); return 0 if not blockers else 2
if __name__=='__main__': raise SystemExit(main())
