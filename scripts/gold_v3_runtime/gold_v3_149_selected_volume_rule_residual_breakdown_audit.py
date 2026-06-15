#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse,json,math,time
from datetime import datetime,timezone
from pathlib import Path
import pandas as pd
import gold_v3_107gy_light_non_calendar_subfilter_search_audit as gy
STEP='GOLD_V3_149_SELECTED_VOLUME_RULE_RESIDUAL_BREAKDOWN_AUDIT_ONLY'

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
def hb(h):
    h=int(h); return '00_05' if h<6 else ('06_11' if h<12 else ('12_17' if h<18 else '18_23'))
def yes(s): return s.astype(str).str.lower().isin(['true','1','yes'])
def bucket(s):
    x=pd.to_numeric(s,errors='coerce')
    if x.notna().sum()<8: return pd.Series(['unknown']*len(s),index=s.index)
    try: return pd.qcut(x.rank(method='first'),4,labels=['Q1_low','Q2_midlow','Q3_midhigh','Q4_high'])
    except Exception: return pd.Series(['unknown']*len(s),index=s.index)
def prep(df):
    x=df.copy(); x['entry_dt']=pd.to_datetime(x.entry_dt,errors='coerce'); x=x[x.entry_dt.notna()].copy(); x['month']=pd.to_datetime(x.date,errors='coerce').dt.to_period('M').astype(str); x['hour_bucket']=x.entry_dt.dt.hour.map(hb)
    k=yes(x.kept_after_score_trim)&(x.chosen_route_score_trimmed.astype(str)!='NO_ROUTE')
    x=x[k].copy(); x['route']=x.chosen_route_score_trimmed.astype(str); x['rep']=pd.to_numeric(x.rep_result_usd_trimmed,errors='coerce').fillna(0); x['worst']=pd.to_numeric(x.worst_result_usd_trimmed,errors='coerce').fillna(0)
    for c in ['feature_score','score','max_score']:
        if c in x.columns: x[c]=pd.to_numeric(x[c],errors='coerce'); x[c+'_bucket']=bucket(x[c])
    return x
def skip_mask(x,rule):
    r=x.route; h=x.hour_bucket; m=pd.Series(False,index=x.index)
    if 'CHAMP_NOT_00_05' in rule: m=m|((r=='CHAMPION')&(h=='00_05'))
    if 'CHAL_NOT_06_11_12_17' in rule: m=m|((r=='CHALLENGER')&h.isin(['06_11','12_17']))
    elif 'CHAL_NOT_06_11' in rule: m=m|((r=='CHALLENGER')&(h=='06_11'))
    elif 'CHAL_NOT_12_17' in rule: m=m|((r=='CHALLENGER')&(h=='12_17'))
    return m
def apply_rule(x,rule):
    y=x.copy(); m=skip_mask(y,rule); y['selected_volume_rule']=rule; y['skipped_by_volume_rule']=m; y['route_after_rule']=y.route.where(~m,'NO_ROUTE'); y['rep_after_rule']=y.rep.where(~m,0); y['worst_after_rule']=y.worst.where(~m,0); return y
def gm(df,cols,label):
    if df.empty: return pd.DataFrame()
    rows=[]
    for key,g in df.groupby(cols,dropna=False):
        if not isinstance(key,tuple): key=(key,)
        w=pd.to_numeric(g.worst_after_rule,errors='coerce').fillna(0); r=pd.to_numeric(g.rep_after_rule,errors='coerce').fillna(0)
        row={'group_label':label,'events':int(len(g)),'rep_sum':float(r.sum()),'worst_sum':float(w.sum()),'worst_pf':pf(w[w!=0]),'negative_events':int((w<0).sum())}
        for c,v in zip(cols,key): row[c]=v
        rows.append(row)
    z=pd.DataFrame(rows)
    return z.sort_values(['worst_sum','events'],ascending=[True,False]).reset_index(drop=True) if not z.empty else z
def main():
    t0=time.time(); ap=argparse.ArgumentParser(); ap.add_argument('--mt5-files-dir',default=''); args=ap.parse_args(); mt5=gy.mt5_files_dir(args.mt5_files_dir); root=mt5/'FX_OUTPUTS'/'gold_v3'; out=root/'149'; out.mkdir(parents=True,exist_ok=True); prog(out,0,1,'START',t0)
    s148=readj(root/'148'/'gold_v3_148_summary.json'); rule=str(s148.get('selected_rule_name','CHAMP_NOT_00_05_AND_CHAL_NOT_06_11'))
    src=root/'145'/'gold_v3_145_selected_trim_reconstructed_events.csv'; raw=load(src); notes=[]
    if raw.empty: notes.append({'id':'missing_input','path':str(src)})
    events=monthly=neg_months=neg_events=factors=pd.DataFrame()
    if not notes:
        base=prep(raw); events=apply_rule(base,rule); active=events[events.route_after_rule.astype(str)!='NO_ROUTE'].copy()
        monthly=gm(active,['month','route_after_rule'],'month_route')
        month_total=gm(active,['month'],'month_total')
        neg_months=month_total[month_total.worst_sum<0].copy()
        neg_events=active[pd.to_numeric(active.worst_after_rule,errors='coerce').fillna(0)<0].copy().sort_values('worst_after_rule')
        frames=[gm(active,['route_after_rule','hour_bucket'],'route_hour'),gm(active,['month','route_after_rule','hour_bucket'],'month_route_hour')]
        for c in ['feature_score_bucket','score_bucket','max_score_bucket']:
            if c in active.columns: frames.append(gm(active,['route_after_rule',c],c))
        factors=pd.concat([f for f in frames if not f.empty],ignore_index=True) if frames else pd.DataFrame()
        save(events,out/'gold_v3_149_selected_rule_events.csv'); save(monthly,out/'gold_v3_149_monthly_route.csv'); save(neg_months,out/'gold_v3_149_negative_months.csv'); save(neg_events,out/'gold_v3_149_negative_events.csv'); save(factors,out/'gold_v3_149_factor_breakdown.csv')
    prog(out,1,1,'DONE',t0)
    status='READY' if not notes else 'INPUT_MISSING'; active_events=int((events.route_after_rule.astype(str)!='NO_ROUTE').sum()) if not events.empty else 0
    wsum=float(pd.to_numeric(events.worst_after_rule,errors='coerce').fillna(0).sum()) if not events.empty else 0.0; wpf=pf(pd.to_numeric(events.worst_after_rule,errors='coerce').fillna(0)[events.route_after_rule.astype(str)!='NO_ROUTE']) if not events.empty else 0.0
    summary={'step':STEP,'status':status,'ready':not notes,'decision':'RESIDUAL_BREAKDOWN_READY_NEGATIVE_MONTHS_REMAIN' if not neg_months.empty else ('RESIDUAL_BREAKDOWN_READY_NO_NEGATIVE_MONTHS' if not notes else 'RESIDUAL_BREAKDOWN_INPUT_MISSING'),'created_at_utc':datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z'),'output_dir':str(out),'audit_only':True,'review_only':True,'source_148_selected_rule_name':rule,'progress_total_configs':1,'progress_completed_configs':1 if not notes else 0,'progress_output':str(out/'progress.txt'),'active_events':active_events,'worst_sum':wsum,'worst_pf':wpf,'negative_month_count':int(len(neg_months)) if not neg_months.empty else 0,'negative_event_count':int(len(neg_events)) if not neg_events.empty else 0,'source_csv_mutated':False,'contract_mutated':False,'open_asof_allowed':False,'candidate_pool_removed':False,'f002_exclusion_bypassed':False,'blocker_count':len(notes),'elapsed_seconds':round(time.time()-t0,2)}
    (out/'gold_v3_149_summary.json').write_text(json.dumps(summary|{'blockers':notes},ensure_ascii=False,indent=2,default=str),encoding='utf-8'); save(pd.DataFrame([summary]),out/'gold_v3_149_decision.csv')
    lines=['GOLD V3 149 PASTE_ME_SELECTED_VOLUME_RULE_RESIDUAL_BREAKDOWN_AUDIT']+[f'{k}: {v}' for k,v in summary.items()]+['','NEGATIVE_MONTHS',neg_months.to_string(index=False) if not neg_months.empty else 'NO_NEGATIVE_MONTHS','','FACTOR_BREAKDOWN_TOP60',factors.head(60).to_string(index=False) if not factors.empty else 'NO_FACTOR_ROWS','','NEGATIVE_EVENTS_TOP60',neg_events.head(60).to_string(index=False) if not neg_events.empty else 'NO_NEGATIVE_EVENTS','','MONTHLY_ROUTE',monthly.to_string(index=False) if not monthly.empty else 'NO_MONTHLY_ROUTE','','BLOCKERS','NO_BLOCKERS' if not notes else json.dumps(notes,ensure_ascii=False,indent=2)]
    (out/'paste_me.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8'); print(json.dumps({'ready':not notes,'paste_me':str(out/'paste_me.txt')},ensure_ascii=False,indent=2)); return 0 if not notes else 2
if __name__=='__main__': raise SystemExit(main())
