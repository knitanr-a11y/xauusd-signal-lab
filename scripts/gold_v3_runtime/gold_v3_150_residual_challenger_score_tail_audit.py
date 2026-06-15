#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse,json,math,time
from datetime import datetime,timezone
from pathlib import Path
import pandas as pd
import gold_v3_107gy_light_non_calendar_subfilter_search_audit as gy
STEP='GOLD_V3_150_RESIDUAL_CHALLENGER_SCORE_TAIL_AUDIT_ONLY'

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
def prep(df):
    x=df.copy(); x['entry_dt']=pd.to_datetime(x.entry_dt,errors='coerce'); x=x[x.entry_dt.notna()].copy(); x['month']=pd.to_datetime(x.date,errors='coerce').dt.to_period('M').astype(str)
    x=x[x.route_after_rule.astype(str)!='NO_ROUTE'].copy(); x['route']=x.route_after_rule.astype(str); x['rep']=pd.to_numeric(x.rep_after_rule,errors='coerce').fillna(0); x['worst']=pd.to_numeric(x.worst_after_rule,errors='coerce').fillna(0)
    for c in ['feature_score','score','max_score']:
        if c in x.columns: x[c]=pd.to_numeric(x[c],errors='coerce')
    return x.sort_values('entry_dt').reset_index(drop=True)
def apply_cfg(base,cfg,min_hist):
    name,col,tail,q=cfg; x=base.copy(); rem=[]; ths=[]; hist=[]
    for _,r in x.iterrows():
        if str(r['route'])!='CHALLENGER' or col not in x.columns:
            rem.append(False); ths.append(math.nan); continue
        sc=r[col]
        h=pd.Series(hist).dropna()
        th=float(h.quantile(q)) if len(h)>=min_hist else math.nan
        cut=False
        if not math.isnan(th):
            if tail=='LOW': cut=pd.notna(sc) and float(sc)<th
            if tail=='HIGH': cut=pd.notna(sc) and float(sc)>=th
        rem.append(bool(cut)); ths.append(th); hist.append(sc)
    x['score_tail_rule']=name; x['score_tail_threshold']=ths; x['removed_by_score_tail']=rem
    x['route2']=x.route.where(~x.removed_by_score_tail,'NO_ROUTE'); x['rep2']=x.rep.where(~x.removed_by_score_tail,0); x['worst2']=x.worst.where(~x.removed_by_score_tail,0)
    return x
def summ(x,name):
    rows=[]
    for mo,g in x.groupby('month'):
        r=g.route2.astype(str); w=pd.to_numeric(g.worst2,errors='coerce').fillna(0); rp=pd.to_numeric(g.rep2,errors='coerce').fillna(0)
        rows.append({'rule':name,'month':mo,'events':int((r!='NO_ROUTE').sum()),'champion':int((r=='CHAMPION').sum()),'challenger':int((r=='CHALLENGER').sum()),'removed':int(g.removed_by_score_tail.sum()),'rep_sum':float(rp.sum()),'worst_sum':float(w.sum())})
    mon=pd.DataFrame(rows); r=x.route2.astype(str); w=pd.to_numeric(x.worst2,errors='coerce').fillna(0); rp=pd.to_numeric(x.rep2,errors='coerce').fillna(0); june=mon[mon.month=='2026-06'] if not mon.empty else pd.DataFrame()
    return {'rule':name,'events':int((r!='NO_ROUTE').sum()),'champion':int((r=='CHAMPION').sum()),'challenger':int((r=='CHALLENGER').sum()),'removed':int(x.removed_by_score_tail.sum()),'rep_sum':float(rp.sum()),'worst_sum':float(w.sum()),'rep_pf':pf(rp[r!='NO_ROUTE']),'worst_pf':pf(w[r!='NO_ROUTE']),'neg_months':int((mon.worst_sum<0).sum()) if not mon.empty else 0,'june_events':int(june.iloc[0].events) if not june.empty else 0,'june_challenger':int(june.iloc[0].challenger) if not june.empty else 0,'june_worst':float(june.iloc[0].worst_sum) if not june.empty else 0.0},mon
def main():
    t0=time.time(); ap=argparse.ArgumentParser(); ap.add_argument('--mt5-files-dir',default=''); ap.add_argument('--min-history-events',type=int,default=30); args=ap.parse_args(); mt5=gy.mt5_files_dir(args.mt5_files_dir); root=mt5/'FX_OUTPUTS'/'gold_v3'; out=root/'150'; out.mkdir(parents=True,exist_ok=True)
    s149=readj(root/'149'/'gold_v3_149_summary.json'); src=root/'149'/'gold_v3_149_selected_rule_events.csv'; raw=load(src); notes=[]
    if raw.empty: notes.append({'id':'missing_149_selected_rule_events','path':str(src)})
    cfgs=[('BASE_NO_SCORE_TAIL','score','NONE',0.0)]
    for col in ['score','feature_score','max_score']:
        for q in [0.5,0.6,0.7,0.8]:
            cfgs.append((f'OMIT_CHAL_{col}_LOW_Q{q}',col,'LOW',q)); cfgs.append((f'OMIT_CHAL_{col}_HIGH_Q{q}',col,'HIGH',q))
    prog(out,0,len(cfgs),'START',t0); rows=[]; months=[]; cache={}; done=0
    if not notes:
        base=prep(raw)
        for i,cfg in enumerate(cfgs,1):
            if cfg[0]=='BASE_NO_SCORE_TAIL':
                x=base.copy(); x['removed_by_score_tail']=False; x['route2']=x.route; x['rep2']=x.rep; x['worst2']=x.worst; x['score_tail_rule']=cfg[0]; x['score_tail_threshold']=math.nan
            else: x=apply_cfg(base,cfg,args.min_history_events)
            r,m=summ(x,cfg[0]); rows.append(r); months.append(m); cache[cfg[0]]=(x,m); done=i; prog(out,i,len(cfgs),cfg[0],t0)
    rank=pd.DataFrame(rows); allm=pd.concat(months,ignore_index=True) if months else pd.DataFrame(); selx=pd.DataFrame(); selm=pd.DataFrame()
    if not rank.empty:
        b=rank[rank.rule=='BASE_NO_SCORE_TAIL'].iloc[0]
        rank['tier']='REJECTED'; ok=(rank.rule!='BASE_NO_SCORE_TAIL')&(rank.events>=80)&(rank.challenger>=40)&(rank.june_events>=4)&(rank.june_worst>=0)&(rank.worst_sum>=float(b.worst_sum))&(rank.neg_months<=int(b.neg_months)); rank.loc[ok,'tier']='PASS'
        rank['tier_order']=rank.tier.map({'PASS':0,'REJECTED':1}).fillna(9); rank['rank_score']=rank.worst_sum+rank.worst_pf*100-rank.neg_months*500+rank.june_worst-rank.removed*0.2
        rank=rank.sort_values(['tier_order','neg_months','worst_sum','worst_pf'],ascending=[True,True,False,False]).reset_index(drop=True); key=str(rank.iloc[0].rule); selx,selm=cache.get(key,(pd.DataFrame(),pd.DataFrame()))
    save(rank,out/'gold_v3_150_score_tail_ranking.csv'); save(allm,out/'gold_v3_150_score_tail_monthly_all.csv'); save(selx,out/'gold_v3_150_selected_score_tail_events.csv'); save(selm,out/'gold_v3_150_selected_score_tail_monthly.csv')
    selected=rank.head(1) if not rank.empty else pd.DataFrame(); status='READY' if not notes else 'INPUT_MISSING'
    if notes: dec='SCORE_TAIL_INPUT_MISSING'
    elif selected.empty: dec='SCORE_TAIL_READY_NO_RULE'
    elif str(selected.iloc[0].tier)=='PASS' and int(selected.iloc[0].neg_months)==0: dec='SCORE_TAIL_READY_NO_NEGATIVE_MONTHS'
    elif str(selected.iloc[0].tier)=='PASS': dec='SCORE_TAIL_REVIEW_PASS_NEGATIVE_MONTHS_REMAIN'
    else: dec='SCORE_TAIL_NO_IMPROVING_RULE_FOUND'
    summary={'step':STEP,'status':status,'ready':not notes,'decision':dec,'created_at_utc':datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z'),'output_dir':str(out),'audit_only':True,'review_only':True,'source_149_decision':s149.get('decision',''),'rule_basis':'challenger score tail running quantile only; no result based deletion','progress_total_configs':len(cfgs),'progress_completed_configs':done,'progress_output':str(out/'progress.txt'),'selected_rule':str(selected.iloc[0].rule) if not selected.empty else '','selected_tier':str(selected.iloc[0].tier) if not selected.empty and 'tier' in selected else '','selected_events':int(selected.iloc[0].events) if not selected.empty else 0,'selected_challenger_events':int(selected.iloc[0].challenger) if not selected.empty else 0,'selected_removed':int(selected.iloc[0].removed) if not selected.empty else 0,'selected_worst_sum':float(selected.iloc[0].worst_sum) if not selected.empty else 0.0,'selected_worst_pf':float(selected.iloc[0].worst_pf) if not selected.empty else 0.0,'selected_negative_months':int(selected.iloc[0].neg_months) if not selected.empty else 0,'selected_june_worst':float(selected.iloc[0].june_worst) if not selected.empty else 0.0,'source_csv_mutated':False,'contract_mutated':False,'open_asof_allowed':False,'candidate_pool_removed':False,'f002_exclusion_bypassed':False,'blocker_count':len(notes),'elapsed_seconds':round(time.time()-t0,2)}
    (out/'gold_v3_150_summary.json').write_text(json.dumps(summary|{'blockers':notes},ensure_ascii=False,indent=2,default=str),encoding='utf-8'); save(pd.DataFrame([summary]),out/'gold_v3_150_decision.csv')
    lines=['GOLD V3 150 PASTE_ME_RESIDUAL_CHALLENGER_SCORE_TAIL_AUDIT']+[f'{k}: {v}' for k,v in summary.items()]+['','SCORE_TAIL_RANKING_TOP40',rank.head(40).to_string(index=False) if not rank.empty else 'NO_RANKING','','SELECTED_MONTHLY',selm.to_string(index=False) if not selm.empty else 'NO_SELECTED_MONTHLY','','BLOCKERS','NO_BLOCKERS' if not notes else json.dumps(notes,ensure_ascii=False,indent=2)]
    (out/'paste_me.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8'); print(json.dumps({'ready':not notes,'decision':dec,'paste_me':str(out/'paste_me.txt')},ensure_ascii=False,indent=2)); return 0 if not notes else 2
if __name__=='__main__': raise SystemExit(main())
