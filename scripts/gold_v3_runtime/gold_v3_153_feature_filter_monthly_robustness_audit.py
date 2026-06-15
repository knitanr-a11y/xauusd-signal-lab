#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse,json,math,time
from datetime import datetime,timezone
from pathlib import Path
import pandas as pd
import gold_v3_107gy_light_non_calendar_subfilter_search_audit as gy
STEP='GOLD_V3_153_FEATURE_FILTER_MONTHLY_ROBUSTNESS_AUDIT_ONLY'

def load(p): return pd.read_csv(p,encoding='utf-8-sig',low_memory=False) if p.exists() else pd.DataFrame()
def save(df,p): p.parent.mkdir(parents=True,exist_ok=True); df.to_csv(p,index=False,encoding='utf-8-sig')
def readj(p):
    try: return json.loads(p.read_text(encoding='utf-8')) if p.exists() else {}
    except Exception: return {}
def pf(v):
    a=pd.to_numeric(pd.Series(v),errors='coerce').dropna().astype(float)
    if a.empty: return 0.0
    gp=float(a[a>0].sum()); gl=float(-a[a<0].sum())
    return gp/gl if gl>0 else (math.inf if gp>0 else 0.0)
def prog(out,d,t,label,t0):
    msg=f'[PROGRESS] config {d}/{t} ({(d/t*100 if t else 100):.1f}%) {label} elapsed={time.time()-t0:.1f}s'
    print(msg,flush=True); (out/'progress.txt').write_text(msg+'\n',encoding='utf-8'); (out/'progress.json').write_text(json.dumps({'done':d,'total':t,'label':label,'elapsed_seconds':round(time.time()-t0,1)},ensure_ascii=False,indent=2),encoding='utf-8')
def metric(df):
    if df.empty: return dict(events=0,challenger=0,champion=0,sum=0.0,pf=0.0,neg_months=0,june_sum=0.0,june_events=0)
    w=pd.to_numeric(df.event_worst,errors='coerce').fillna(0); r=df.route_for_policy.astype(str); m=df.groupby('month').event_worst.sum()
    j=float(m.get('2026-06',0.0)); je=int((df.month=='2026-06').sum())
    return dict(events=int(len(df)),challenger=int((r=='CHALLENGER').sum()),champion=int((r=='CHAMPION').sum()),sum=float(w.sum()),pf=pf(w),neg_months=int((m<0).sum()),june_sum=j,june_events=je)
def add(d,p): return {p+k:v for k,v in d.items()}
def parse_rule(label):
    if str(label).startswith('BASE'): return []
    parts=str(label).split(' && '); out=[]
    for p in parts:
        a=p.split('|')
        if len(a)<5: continue
        typ,col,op,scope=a[0],a[1],a[2],a[-1]; val='|'.join(a[3:-1])
        out.append((typ,col,op,val,scope))
    return out
def mask_one(df,r):
    typ,col,op,val,scope=r
    if col not in df.columns: return pd.Series(False,index=df.index)
    smask=pd.Series(True,index=df.index) if scope=='ALL' else (df.route_for_policy.astype(str)==scope)
    if typ=='num':
        x=pd.to_numeric(df[col],errors='coerce'); v=float(val)
        m=(x>=v) if op=='GE' else (x<=v)
    else:
        m=df[col].fillna('MISSING').astype(str)==str(val)
    return smask & m.fillna(False)
def apply_rules(df,rs):
    m=pd.Series(False,index=df.index)
    for r in rs: m=m|mask_one(df,r)
    return df[~m].copy(), int(m.sum())
def monthly_rows(df,label):
    rows=[]
    for mo,g in df.groupby('month'):
        w=pd.to_numeric(g.event_worst,errors='coerce').fillna(0); rt=g.route_for_policy.astype(str)
        rows.append(dict(rule_label=label,month=mo,events=int(len(g)),champion=int((rt=='CHAMPION').sum()),challenger=int((rt=='CHALLENGER').sum()),sum=float(w.sum()),pf=pf(w),neg_events=int((w<0).sum())))
    return pd.DataFrame(rows)
def lomo_rows(df,label):
    rows=[]; months=sorted(df.month.dropna().unique().tolist())
    for mo in months:
        g=df[df.month!=mo].copy(); mt=metric(g)
        rows.append(dict(rule_label=label,omitted_month=mo,**mt))
    return pd.DataFrame(rows)
def main():
    t0=time.time(); ap=argparse.ArgumentParser(); ap.add_argument('--mt5-files-dir',default=''); ap.add_argument('--top-n',type=int,default=40); args=ap.parse_args()
    mt5=gy.mt5_files_dir(args.mt5_files_dir); root=mt5/'FX_OUTPUTS'/'gold_v3'; out=root/'153'; out.mkdir(parents=True,exist_ok=True)
    s152=readj(root/'152'/'gold_v3_152_summary.json'); rank=load(root/'152'/'gold_v3_152_feature_filter_validation_ranking.csv'); ev=load(root/'151'/'gold_v3_151_selected_events_enriched.csv'); probs=[]
    if rank.empty: probs.append({'id':'missing_152_ranking'})
    if ev.empty: probs.append({'id':'missing_151_enriched_events'})
    prog(out,0,1 if probs else min(args.top_n,len(rank)),'START',t0)
    summary_rows=[]; mon_all=[]; lomo_all=[]; best_events=pd.DataFrame(); done=0
    if not probs:
        ev['entry_dt']=pd.to_datetime(ev.entry_dt,errors='coerce'); ev=ev[ev.entry_dt.notna()].copy(); ev['month']=ev.entry_dt.dt.to_period('M').astype(str); ev['event_worst']=pd.to_numeric(ev.event_worst,errors='coerce').fillna(0); ev['route_for_policy']=ev.route_for_policy.astype(str)
        labels=[]
        if 'rule_label' in rank.columns:
            for x in rank.head(args.top_n).rule_label.astype(str).tolist():
                if x not in labels: labels.append(x)
        total=len(labels)
        base_metric=None
        for i,label in enumerate(labels,1):
            kept,removed=apply_rules(ev,parse_rule(label)); mt=metric(kept); mon=monthly_rows(kept,label); lo=lomo_rows(kept,label)
            worst_month_sum=float(mon['sum'].min()) if not mon.empty else 0.0; worst_month=str(mon.sort_values('sum').iloc[0].month) if not mon.empty else ''
            lomo_min_sum=float(lo['sum'].min()) if not lo.empty else 0.0; lomo_max_neg=int(lo['neg_months'].max()) if not lo.empty else 0
            rec=dict(rule_label=label,removed=removed,month_count=int(mon.month.nunique()) if not mon.empty else 0,worst_month=worst_month,worst_month_sum=worst_month_sum,lomo_min_sum=lomo_min_sum,lomo_max_neg_months=lomo_max_neg,lomo_positive_all=bool(lomo_min_sum>0),june_kept=bool(mt['june_events']>0 and mt['june_sum']>=0))
            rec.update(add(mt,'full_'))
            if label.startswith('BASE'): base_metric=mt
            summary_rows.append(rec); mon_all.append(mon); lomo_all.append(lo); done=i
            if i%5==0 or i==total: prog(out,i,total,label[:80],t0)
        summ=pd.DataFrame(summary_rows); mon_all=pd.concat(mon_all,ignore_index=True) if mon_all else pd.DataFrame(); lomo_all=pd.concat(lomo_all,ignore_index=True) if lomo_all else pd.DataFrame()
        if not summ.empty:
            base_sum=float(base_metric['sum']) if base_metric else 0.0
            summ['robust_tier']='REJECTED'
            ok=(summ.full_events>=70)&(summ.full_sum>=base_sum)&(summ.lomo_min_sum>0)&(summ.june_kept)&(summ.full_neg_months<=2)
            summ.loc[ok,'robust_tier']='PASS'
            summ['tier_order']=summ.robust_tier.map({'PASS':0,'REJECTED':1}).fillna(9)
            summ['robust_score']=summ.full_sum+summ.full_pf*100-summ.full_neg_months*500+summ.lomo_min_sum*0.2+summ.full_june_sum-summ.removed*0.1
            summ=summ.sort_values(['tier_order','full_neg_months','lomo_min_sum','full_sum','full_pf'],ascending=[True,True,False,False,False]).reset_index(drop=True)
            sel=str(summ.iloc[0].rule_label); best_events,_=apply_rules(ev,parse_rule(sel)); selected_monthly=mon_all[mon_all.rule_label.astype(str)==sel].copy(); selected_lomo=lomo_all[lomo_all.rule_label.astype(str)==sel].copy()
        else:
            selected_monthly=pd.DataFrame(); selected_lomo=pd.DataFrame()
        save(summ,out/'gold_v3_153_monthly_robustness_summary.csv'); save(mon_all,out/'gold_v3_153_candidate_monthly_all.csv'); save(lomo_all,out/'gold_v3_153_leave_one_month_out_all.csv'); save(best_events,out/'gold_v3_153_selected_robust_events.csv'); save(selected_monthly,out/'gold_v3_153_selected_monthly.csv'); save(selected_lomo,out/'gold_v3_153_selected_leave_one_month_out.csv')
    else:
        summ=pd.DataFrame(); selected_monthly=pd.DataFrame(); selected_lomo=pd.DataFrame()
    selected=summ.head(1) if not summ.empty else pd.DataFrame(); status='READY' if not probs else 'INPUT_MISSING'
    if probs: dec='MONTHLY_ROBUSTNESS_INPUT_MISSING'
    elif selected.empty: dec='MONTHLY_ROBUSTNESS_NO_CONFIG'
    elif str(selected.iloc[0].robust_tier)=='PASS': dec='MONTHLY_ROBUSTNESS_PASS_REVIEW'
    else: dec='MONTHLY_ROBUSTNESS_NO_PASS_FOUND'
    summary={'step':STEP,'status':status,'ready':not probs,'decision':dec,'created_at_utc':datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z'),'output_dir':str(out),'audit_only':True,'review_only':True,'source_152_decision':s152.get('decision',''),'robustness_scope':'top Stage152 candidates; monthly and leave-one-month-out only','progress_total_configs':done if done else (0 if probs else 1),'progress_completed_configs':done,'progress_output':str(out/'progress.txt'),'selected_rule_label':str(selected.iloc[0].rule_label) if not selected.empty else '','selected_robust_tier':str(selected.iloc[0].robust_tier) if not selected.empty and 'robust_tier' in selected else '','selected_removed':int(selected.iloc[0].removed) if not selected.empty else 0,'selected_full_events':int(selected.iloc[0].full_events) if not selected.empty else 0,'selected_full_sum':float(selected.iloc[0].full_sum) if not selected.empty else 0.0,'selected_full_pf':float(selected.iloc[0].full_pf) if not selected.empty else 0.0,'selected_full_neg_months':int(selected.iloc[0].full_neg_months) if not selected.empty else 0,'selected_worst_month':str(selected.iloc[0].worst_month) if not selected.empty else '','selected_worst_month_sum':float(selected.iloc[0].worst_month_sum) if not selected.empty else 0.0,'selected_lomo_min_sum':float(selected.iloc[0].lomo_min_sum) if not selected.empty else 0.0,'selected_lomo_max_neg_months':int(selected.iloc[0].lomo_max_neg_months) if not selected.empty else 0,'selected_june_sum':float(selected.iloc[0].full_june_sum) if not selected.empty else 0.0,'source_csv_mutated':False,'contract_mutated':False,'open_asof_allowed':False,'candidate_pool_removed':False,'f002_exclusion_bypassed':False,'blocker_count':len(probs),'elapsed_seconds':round(time.time()-t0,2)}
    (out/'gold_v3_153_summary.json').write_text(json.dumps(summary|{'blockers':probs},ensure_ascii=False,indent=2,default=str),encoding='utf-8'); save(pd.DataFrame([summary]),out/'gold_v3_153_decision.csv')
    lines=['GOLD V3 153 PASTE_ME_FEATURE_FILTER_MONTHLY_ROBUSTNESS_AUDIT']+[f'{k}: {v}' for k,v in summary.items()]+['','TOP40_MONTHLY_ROBUSTNESS',summ.head(40).to_string(index=False) if not summ.empty else 'NO_SUMMARY','','SELECTED_MONTHLY',selected_monthly.to_string(index=False) if not selected_monthly.empty else 'NO_SELECTED_MONTHLY','','SELECTED_LEAVE_ONE_MONTH_OUT',selected_lomo.to_string(index=False) if not selected_lomo.empty else 'NO_SELECTED_LOMO','','BLOCKERS','NO_BLOCKERS' if not probs else json.dumps(probs,ensure_ascii=False,indent=2)]
    (out/'paste_me.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({'ready':not probs,'decision':dec,'paste_me':str(out/'paste_me.txt')},ensure_ascii=False,indent=2)); return 0 if not probs else 2
if __name__=='__main__': raise SystemExit(main())
