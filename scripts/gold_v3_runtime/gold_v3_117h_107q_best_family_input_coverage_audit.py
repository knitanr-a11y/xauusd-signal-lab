#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse, json, math, re, time
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
import numpy as np
import gold_v3_107gy_light_non_calendar_subfilter_search_audit as gy

STEP='GOLD_V3_117H_107Q_BEST_FAMILY_INPUT_COVERAGE_AUDIT'
READY='GOLD_V3_117H_107Q_BEST_FAMILY_INPUT_COVERAGE_AUDIT_READY'
BLOCKED='GOLD_V3_117H_107Q_BEST_FAMILY_INPUT_COVERAGE_AUDIT_BLOCKED'
NAMES={'m15':['gold#_m15.csv','goldsharp_m15.csv'],'m5':['gold#_m5.csv','goldsharp_m5.csv']}

def save(df,p): p.parent.mkdir(parents=True,exist_ok=True); df.to_csv(p,index=False,encoding='utf-8-sig')
def write_json(p,o): p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(o,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
def pf(vals):
    a=np.asarray(pd.to_numeric(pd.Series(vals),errors='coerce').dropna(),dtype=float)
    gp=a[a>0].sum(); gl=-a[a<0].sum()
    if gl>0: return float(gp/gl)
    if gp>0: return math.inf
    return 0.0
def metrics(df):
    if df is None or df.empty: return dict(trades=0,wins=0,losses=0,win_rate=0.0,profit_factor=0.0,sum_result_usd=0.0)
    x=df.copy(); x['entry_dt']=pd.to_datetime(x['entry_dt'],errors='coerce')
    if 'result_usd' in x.columns: x['result_usd']=pd.to_numeric(x['result_usd'],errors='coerce')
    else: x['result_usd']=np.nan
    x=x[x.entry_dt.notna()&x.result_usd.notna()].copy()
    if x.empty: return dict(trades=0,wins=0,losses=0,win_rate=0.0,profit_factor=0.0,sum_result_usd=0.0)
    return dict(trades=int(len(x)),wins=int((x.result_usd>0).sum()),losses=int((x.result_usd<0).sum()),win_rate=float((x.result_usd>0).mean()),profit_factor=pf(x.result_usd),sum_result_usd=float(x.result_usd.sum()))
def detect_sep(path):
    try:
        s=path.read_text(encoding='utf-8-sig',errors='ignore')[:4096]
        return ';' if s.count(';')>s.count(',') else ','
    except Exception: return ','
def read_ohlc(p):
    df=pd.read_csv(p,sep=detect_sep(p),encoding='utf-8-sig',low_memory=False)
    low={c.lower():c for c in df.columns}; t=low.get('time') or low.get('datetime') or low.get('date') or low.get('timestamp')
    if not t: raise ValueError('time column missing')
    x=df[[t]].copy(); x.columns=['time']; x.time=pd.to_datetime(x.time,errors='coerce'); x=x[x.time.notna()]
    return {'file':p.name,'path':str(p),'exists':True,'rows':int(len(x)),'min_time':str(x.time.min()) if len(x) else '', 'max_time':str(x.time.max()) if len(x) else '', 'june_rows':int(((x.time>=pd.Timestamp('2026-06-01'))&(x.time<pd.Timestamp('2026-07-01'))).sum()),'error':''}
def ohlc_coverage(mt5):
    rows=[]
    for tf,names in NAMES.items():
        for name in names:
            p=mt5/name
            if p.exists():
                try: r=read_ohlc(p); r['tf']=tf; rows.append(r)
                except Exception as e: rows.append({'tf':tf,'file':name,'path':str(p),'exists':True,'rows':0,'min_time':'','max_time':'','june_rows':0,'error':str(e)})
            else: rows.append({'tf':tf,'file':name,'path':str(p),'exists':False,'rows':0,'min_time':'','max_time':'','june_rows':0,'error':''})
    return pd.DataFrame(rows)
def group_month(df):
    if df is None or df.empty: return pd.DataFrame()
    x=df.copy(); x['entry_dt']=pd.to_datetime(x.entry_dt,errors='coerce'); x=x[x.entry_dt.notna()].copy(); x['month']=x.entry_dt.dt.to_period('M').astype(str)
    rows=[]
    for m,g in x.groupby('month'):
        r={'month':m}; r.update(metrics(g)); rows.append(r)
    return pd.DataFrame(rows)
def main():
    t0=time.time(); ap=argparse.ArgumentParser(); ap.add_argument('--mt5-files-dir',default=''); args=ap.parse_args()
    mt5=gy.mt5_files_dir(args.mt5_files_dir); root=mt5/'FX_OUTPUTS'/'gold_v3'; out=root/'117h'; out.mkdir(parents=True,exist_ok=True)
    q=root/'107qc'/'gold_v3_107q_best_family_trade_ledger.csv'
    blockers=[]
    if not q.exists(): blockers.append({'blocker_id':'missing_107q_best_family_trade_ledger','path':str(q)})
    df=pd.DataFrame(); monthly=pd.DataFrame(); cov=pd.DataFrame(); min_dt=''; max_dt=''; june_rows=0
    if not blockers:
        df=pd.read_csv(q,encoding='utf-8-sig',low_memory=False)
        if 'entry_dt' not in df.columns: blockers.append({'blocker_id':'107q_missing_entry_dt'})
    if not blockers:
        df=df.copy(); df['entry_dt']=pd.to_datetime(df.entry_dt,errors='coerce'); df=df[df.entry_dt.notna()].copy().sort_values('entry_dt')
        min_dt=str(df.entry_dt.min()) if not df.empty else ''; max_dt=str(df.entry_dt.max()) if not df.empty else ''
        june_rows=int(((df.entry_dt>=pd.Timestamp('2026-06-01'))&(df.entry_dt<pd.Timestamp('2026-07-01'))).sum())
        cov=pd.DataFrame([{'path':str(q),'rows':len(df),'columns':len(df.columns),'min_entry_dt':min_dt,'max_entry_dt':max_dt,'june_rows':june_rows,'has_result_usd':'result_usd' in df.columns,'has_side':'side' in df.columns or 'portfolio_side' in df.columns,'has_profile_id':'profile_id' in df.columns}])
        save(cov,out/'gold_v3_117h_107q_best_family_coverage.csv')
        monthly=group_month(df); save(monthly,out/'gold_v3_117h_monthly_metrics.csv')
    oc=ohlc_coverage(mt5); save(oc,out/'gold_v3_117h_ohlc_coverage.csv')
    m=metrics(df) if not df.empty else metrics(pd.DataFrame())
    m15_june=int(oc[(oc.tf=='m15') & (oc.exists==True)]['june_rows'].max()) if not oc.empty and len(oc[(oc.tf=='m15') & (oc.exists==True)]) else 0
    m5_june=int(oc[(oc.tf=='m5') & (oc.exists==True)]['june_rows'].max()) if not oc.empty and len(oc[(oc.tf=='m5') & (oc.exists==True)]) else 0
    if blockers: decision='BLOCKED_INPUT_INCOMPLETE'
    elif june_rows>0 and m15_june>0 and m5_june>0: decision='107Q_HAS_JUNE_ROWS_RERUN_107R6_SHADOW_READY'
    elif june_rows>0: decision='107Q_HAS_JUNE_ROWS_BUT_OHLC_COVERAGE_INCOMPLETE'
    else: decision='107Q_BEST_FAMILY_STOPS_BEFORE_JUNE_REGENERATE_107Q_REQUIRED'
    dec=pd.DataFrame([{'decision':decision,'path':str(q),'rows':len(df),'min_entry_dt':min_dt,'max_entry_dt':max_dt,'june_rows':june_rows,'m15_june_rows':m15_june,'m5_june_rows':m5_june}]); save(dec,out/'gold_v3_117h_decision.csv')
    status=READY if not blockers else BLOCKED
    summary=dict(step=STEP,status=status,ready=status==READY,decision=decision,created_at_utc=datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z'),output_dir=str(out),path=str(q),rows=int(len(df)),min_entry_dt=min_dt,max_entry_dt=max_dt,june_rows=june_rows,m15_june_rows=m15_june,m5_june_rows=m5_june,source_csv_mutated=False,contract_mutated=False,open_asof_allowed=False,approximate_reconstruction=False,blocker_count=len(blockers),elapsed_seconds=round(time.time()-t0,2))
    summary.update({f'base_{k}':v for k,v in m.items()})
    write_json(out/'gold_v3_117h_summary.json',summary|{'blockers':blockers})
    lines=['GOLD V3 117H PASTE_ME_107Q_BEST_FAMILY_INPUT_COVERAGE_AUDIT',f'status: {status}',f'ready: {str(status==READY).lower()}',f'decision: {decision}',f'path: {q}',f'rows: {len(df)}',f'min_entry_dt: {min_dt}',f'max_entry_dt: {max_dt}',f'june_rows: {june_rows}',f'm15_june_rows: {m15_june}',f'm5_june_rows: {m5_june}','source_csv_mutated: false','contract_mutated: false','open_asof_allowed: false','approximate_reconstruction: false','blocker_count: '+str(len(blockers)),'','KEY_METRICS']+[f'{k}: {v}' for k,v in summary.items()]+['','MONTHLY_METRICS',monthly.to_string(index=False) if not monthly.empty else 'NO_MONTHLY_ROWS','','OHLC_COVERAGE',oc.to_string(index=False),'','BLOCKERS','NO_BLOCKERS' if not blockers else json.dumps(blockers,ensure_ascii=False)]
    (out/'paste_me.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({'status':status,'ready':status==READY,'decision':decision,'paste_me':str(out/'paste_me.txt')},ensure_ascii=False,indent=2))
    return 0 if status==READY else 2
if __name__=='__main__': raise SystemExit(main())
