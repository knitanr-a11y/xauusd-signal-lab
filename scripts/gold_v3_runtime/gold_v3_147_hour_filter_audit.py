#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse,json,math,time
from datetime import datetime,timezone
from pathlib import Path
import pandas as pd
import gold_v3_107gy_light_non_calendar_subfilter_search_audit as gy
STEP='GOLD_V3_147_HOUR_FILTER_AUDIT_ONLY'

def pf(v):
    a=pd.to_numeric(pd.Series(v),errors='coerce').dropna().astype(float)
    if len(a)==0: return 0.0
    gp=float(a[a>0].sum()); gl=float(-a[a<0].sum())
    return gp/gl if gl>0 else (math.inf if gp>0 else 0.0)
def hb(h):
    h=int(h); return '00_05' if h<6 else ('06_11' if h<12 else ('12_17' if h<18 else '18_23'))
def save(df,p): p.parent.mkdir(parents=True,exist_ok=True); df.to_csv(p,index=False,encoding='utf-8-sig')
def readj(p):
    try: return json.loads(p.read_text(encoding='utf-8')) if p.exists() else {}
    except Exception: return {}
def prog(out,d,t,label,t0):
    pct=d/t*100 if t else 100; msg=f'[PROGRESS] config {d}/{t} ({pct:.1f}%) {label} elapsed={time.time()-t0:.1f}s'
    print(msg,flush=True); (out/'progress.txt').write_text(msg+'\n',encoding='utf-8')
    (out/'progress.json').write_text(json.dumps({'done':d,'total':t,'percent':pct,'label':label,'elapsed_seconds':round(time.time()-t0,1)},ensure_ascii=False,indent=2),encoding='utf-8')
def prep(df):
    x=df.copy(); x['entry_dt']=pd.to_datetime(x.entry_dt,errors='coerce'); x=x[x.entry_dt.notna()].copy(); x['hour_bucket']=x.entry_dt.dt.hour.map(hb); x['month']=pd.to_datetime(x.date,errors='coerce').dt.to_period('M').astype(str)
    keep=x.kept_after_score_trim.astype(str).str.lower().isin(['true','1','yes']) & (x.chosen_route_score_trimmed.astype(str)!='NO_ROUTE')
    y=x[keep].copy(); y['route']=y.chosen_route_score_trimmed.astype(str); y['rep']=pd.to_numeric(y.rep_result_usd_trimmed,errors='coerce').fillna(0); y['worst']=pd.to_numeric(y.worst_result_usd_trimmed,errors='coerce').fillna(0)
    return y[['date','entry_dt','month','route','hour_bucket','rep','worst']]
def filt(df,name):
    x=df.copy(); r=x.route; h=x.hour_bucket; m=pd.Series(False,index=x.index)
    if name=='CHAL_NOT_06_11': m=(r=='CHALLENGER')&(h=='06_11')
    if name=='CHAL_NOT_12_17': m=(r=='CHALLENGER')&(h=='12_17')
    if name=='CHAL_NOT_06_11_12_17': m=(r=='CHALLENGER')&h.isin(['06_11','12_17'])
    if name=='CHAMP_NOT_00_05': m=(r=='CHAMPION')&(h=='00_05')
    if name=='CHAMP_NOT_00_05_AND_CHAL_NOT_06_11': m=((r=='CHAMPION')&(h=='00_05'))|((r=='CHALLENGER')&(h=='06_11'))
    if name=='CHAMP_NOT_00_05_AND_CHAL_NOT_06_11_12_17': m=((r=='CHAMPION')&(h=='00_05'))|((r=='CHALLENGER')&h.isin(['06_11','12_17']))
    x['rule_name']=name; x['removed']=m; x['route2']=x.route.where(~m,'NO_ROUTE'); x['rep2']=x.rep.where(~m,0); x['worst2']=x.worst.where(~m,0)
    return x
def summ(x,name):
    ms=[]
    for mo,g in x.groupby('month'):
        rt=g.route2.astype(str); w=g.worst2; rp=g.rep2
        ms.append({'rule_name':name,'month':mo,'events':int((rt!='NO_ROUTE').sum()),'champion':int((rt=='CHAMPION').sum()),'challenger':int((rt=='CHALLENGER').sum()),'removed':int(g.removed.sum()),'rep_sum':float(rp.sum()),'worst_sum':float(w.sum())})
    mon=pd.DataFrame(ms); rt=x.route2.astype(str); w=x.worst2; rp=x.rep2; june=mon[mon.month=='2026-06'] if not mon.empty else pd.DataFrame()
    return {'rule_name':name,'events':int((rt!='NO_ROUTE').sum()),'champion':int((rt=='CHAMPION').sum()),'challenger':int((rt=='CHALLENGER').sum()),'removed':int(x.removed.sum()),'rep_sum':float(rp.sum()),'worst_sum':float(w.sum()),'rep_pf':pf(rp[rt!='NO_ROUTE']),'worst_pf':pf(w[rt!='NO_ROUTE']),'neg_months':int((mon.worst_sum<0).sum()) if not mon.empty else 0,'june_events':int(june.iloc[0].events) if not june.empty else 0,'june_challenger':int(june.iloc[0].challenger) if not june.empty else 0,'june_worst':float(june.iloc[0].worst_sum) if not june.empty else 0.0},mon
def main():
    t0=time.time(); ap=argparse.ArgumentParser(); ap.add_argument('--mt5-files-dir',default=''); args=ap.parse_args(); mt5=gy.mt5_files_dir(args.mt5_files_dir); root=mt5/'FX_OUTPUTS'/'gold_v3'; out=root/'147'; out.mkdir(parents=True,exist_ok=True)
    s146=readj(root/'146'/'gold_v3_146_summary.json'); p=root/'145'/'gold_v3_145_selected_trim_reconstructed_events.csv'; problems=[]
    df=pd.read_csv(p,encoding='utf-8-sig',low_memory=False) if p.exists() else pd.DataFrame()
    if df.empty: problems.append({'id':'missing_input','path':str(p)})
    rules=['BASE','CHAL_NOT_06_11','CHAL_NOT_12_17','CHAL_NOT_06_11_12_17','CHAMP_NOT_00_05','CHAMP_NOT_00_05_AND_CHAL_NOT_06_11','CHAMP_NOT_00_05_AND_CHAL_NOT_06_11_12_17']
    prog(out,0,len(rules),'START',t0); rows=[]; mons=[]; cache={}; done=0
    if not problems:
        base=prep(df)
        for i,name in enumerate(rules,1):
            x=filt(base,name); r,m=summ(x,name); rows.append(r); mons.append(m); cache[name]=(x,m); done=i; prog(out,i,len(rules),name,t0)
    rank=pd.DataFrame(rows); allm=pd.concat(mons,ignore_index=True) if mons else pd.DataFrame()
    selx=pd.DataFrame(); selm=pd.DataFrame()
    if not rank.empty:
        b=rank[rank.rule_name=='BASE'].iloc[0]
        rank['tier']='REJECTED'; strict=(rank.rule_name!='BASE')&(rank.events>=120)&(rank.challenger>=40)&(rank.june_events>=4)&(rank.june_worst>=1)&(rank.worst_sum>=float(b.worst_sum))&(rank.neg_months<=int(b.neg_months)); rank.loc[strict,'tier']='STRICT_PASS'
        rank['tier_order']=rank.tier.map({'STRICT_PASS':0,'REJECTED':1}).fillna(9); rank['rank_score']=rank.worst_sum+rank.worst_pf*100-rank.neg_months*400+rank.june_worst-rank.removed*0.2
        rank=rank.sort_values(['tier_order','neg_months','worst_sum','worst_pf'],ascending=[True,True,False,False]).reset_index(drop=True); key=str(rank.iloc[0].rule_name); selx,selm=cache.get(key,(pd.DataFrame(),pd.DataFrame()))
    save(rank,out/'gold_v3_147_hour_filter_ranking.csv'); save(allm,out/'gold_v3_147_hour_filter_monthly_all.csv'); save(selx,out/'gold_v3_147_selected_events.csv'); save(selm,out/'gold_v3_147_selected_monthly.csv')
    selected=rank.head(1) if not rank.empty else pd.DataFrame(); status='READY' if not problems else 'BLOCKED'
    if problems: decision='HOUR_FILTER_BLOCKED_INPUT_MISSING'
    elif selected.empty: decision='HOUR_FILTER_READY_NO_RULE'
    elif str(selected.iloc[0].tier)=='STRICT_PASS' and int(selected.iloc[0].neg_months)==0: decision='HOUR_FILTER_READY_NO_NEGATIVE_MONTHS'
    elif str(selected.iloc[0].tier)=='STRICT_PASS': decision='HOUR_FILTER_REVIEW_STRICT_PASS_NEGATIVE_MONTHS_REMAIN'
    else: decision='HOUR_FILTER_NO_ACCEPTABLE_RULE_FOUND'
    summary={'step':STEP,'status':status,'ready':status=='READY','decision':decision,'created_at_utc':datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z'),'output_dir':str(out),'audit_only':True,'review_only':True,'source_146_decision':s146.get('decision',''),'rule_basis':'fixed route/hour only','progress_total_configs':len(rules),'progress_completed_configs':done,'progress_output':str(out/'progress.txt'),'selected_rule_name':str(selected.iloc[0].rule_name) if not selected.empty else '','selected_tier':str(selected.iloc[0].tier) if not selected.empty and 'tier' in selected else '','selected_events':int(selected.iloc[0].events) if not selected.empty else 0,'selected_champion_events':int(selected.iloc[0].champion) if not selected.empty else 0,'selected_challenger_events':int(selected.iloc[0].challenger) if not selected.empty else 0,'selected_removed_events':int(selected.iloc[0].removed) if not selected.empty else 0,'selected_worst_sum':float(selected.iloc[0].worst_sum) if not selected.empty else 0.0,'selected_worst_pf':float(selected.iloc[0].worst_pf) if not selected.empty else 0.0,'selected_negative_months':int(selected.iloc[0].neg_months) if not selected.empty else 0,'selected_june_events':int(selected.iloc[0].june_events) if not selected.empty else 0,'selected_june_challenger_events':int(selected.iloc[0].june_challenger) if not selected.empty else 0,'selected_june_worst':float(selected.iloc[0].june_worst) if not selected.empty else 0.0,'source_csv_mutated':False,'contract_mutated':False,'open_asof_allowed':False,'candidate_pool_removed':False,'f002_exclusion_bypassed':False,'blocker_count':len(problems),'elapsed_seconds':round(time.time()-t0,2)}
    (out/'gold_v3_147_summary.json').write_text(json.dumps(summary|{'blockers':problems},ensure_ascii=False,indent=2,default=str),encoding='utf-8'); save(pd.DataFrame([summary]),out/'gold_v3_147_decision.csv')
    lines=['GOLD V3 147 PASTE_ME_HOUR_FILTER_AUDIT']+[f'{k}: {v}' for k,v in summary.items()]+['','HOUR_FILTER_RANKING',rank.to_string(index=False) if not rank.empty else 'NO_RANKING','','SELECTED_MONTHLY',selm.to_string(index=False) if not selm.empty else 'NO_SELECTED_MONTHLY','','BLOCKERS','NO_BLOCKERS' if not problems else json.dumps(problems,ensure_ascii=False,indent=2)]
    (out/'paste_me.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8'); print(json.dumps({'status':status,'ready':status=='READY','decision':decision,'selected_rule_name':summary['selected_rule_name'],'paste_me':str(out/'paste_me.txt')},ensure_ascii=False,indent=2)); return 0 if status=='READY' else 2
if __name__=='__main__': raise SystemExit(main())
