#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse, json, math, time
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd
import gold_v3_107gy_light_non_calendar_subfilter_search_audit as gy

STEP='GOLD_V3_117I_107Q_GENERATOR_INPUT_FEASIBILITY_AUDIT'
READY='GOLD_V3_117I_107Q_GENERATOR_INPUT_FEASIBILITY_AUDIT_READY'
BLOCKED='GOLD_V3_117I_107Q_GENERATOR_INPUT_FEASIBILITY_AUDIT_BLOCKED'

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
    x=df.copy(); x['entry_dt']=pd.to_datetime(x.get('entry_dt'),errors='coerce'); x['result_usd']=pd.to_numeric(x.get('result_usd'),errors='coerce')
    x=x[x.entry_dt.notna()&x.result_usd.notna()].copy()
    if x.empty: return dict(trades=0,wins=0,losses=0,win_rate=0.0,profit_factor=0.0,sum_result_usd=0.0)
    return dict(trades=int(len(x)),wins=int((x.result_usd>0).sum()),losses=int((x.result_usd<0).sum()),win_rate=float((x.result_usd>0).mean()),profit_factor=pf(x.result_usd),sum_result_usd=float(x.result_usd.sum()))
def coverage_csv(path, kind):
    rec={'kind':kind,'path':str(path),'exists':path.exists(),'rows':0,'cols':0,'min_entry_dt':'','max_entry_dt':'','june_rows':0,'has_entry_dt':False,'has_result_usd':False,'error':''}
    if not path.exists(): return rec, pd.DataFrame()
    try:
        df=pd.read_csv(path,encoding='utf-8-sig',low_memory=False)
        rec['rows']=int(len(df)); rec['cols']=int(len(df.columns)); rec['has_entry_dt']='entry_dt' in df.columns; rec['has_result_usd']='result_usd' in df.columns
        if 'entry_dt' in df.columns:
            dt=pd.to_datetime(df.entry_dt,errors='coerce').dropna()
            if len(dt):
                rec['min_entry_dt']=str(dt.min()); rec['max_entry_dt']=str(dt.max()); rec['june_rows']=int(((dt>=pd.Timestamp('2026-06-01'))&(dt<pd.Timestamp('2026-07-01'))).sum())
        return rec, df
    except Exception as e:
        rec['error']=str(e); return rec, pd.DataFrame()
def group_month(df):
    if df is None or df.empty or 'entry_dt' not in df.columns: return pd.DataFrame()
    x=df.copy(); x['entry_dt']=pd.to_datetime(x.entry_dt,errors='coerce'); x=x[x.entry_dt.notna()].copy(); x['month']=x.entry_dt.dt.to_period('M').astype(str)
    rows=[]
    for m,g in x.groupby('month'):
        r={'month':m}; r.update(metrics(g)); rows.append(r)
    return pd.DataFrame(rows)
def main():
    t0=time.time(); ap=argparse.ArgumentParser(); ap.add_argument('--mt5-files-dir',default=''); args=ap.parse_args()
    mt5=gy.mt5_files_dir(args.mt5_files_dir); root=mt5/'FX_OUTPUTS'/'gold_v3'; out=root/'117i'; out.mkdir(parents=True,exist_ok=True)
    p107l=root/'107lc'/'gold_v3_107l_rehydrated_best_policy_ledger.csv'
    p107m=root/'107mc'/'gold_v3_107m_loss_trim_frontier.csv'
    rec_l, df_l=coverage_csv(p107l,'107L_REHYDRATED_BEST_POLICY_LEDGER')
    rec_m, df_m=coverage_csv(p107m,'107M_LOSS_TRIM_FRONTIER')
    cov=pd.DataFrame([rec_l,rec_m]); save(cov,out/'gold_v3_117i_107q_input_coverage.csv')
    mon=group_month(df_l); save(mon,out/'gold_v3_117i_107l_monthly_metrics.csv')
    frontier=df_m.head(2000).copy() if not df_m.empty else pd.DataFrame(); save(frontier,out/'gold_v3_117i_107m_frontier_inventory.csv')
    blockers=[]
    if not rec_l['exists']: blockers.append({'blocker_id':'missing_107l_input','path':str(p107l)})
    if not rec_m['exists']: blockers.append({'blocker_id':'missing_107m_input','path':str(p107m)})
    if rec_l['exists'] and not rec_l['has_entry_dt']: blockers.append({'blocker_id':'107l_missing_entry_dt'})
    if rec_l['exists'] and not rec_l['has_result_usd']: blockers.append({'blocker_id':'107l_missing_result_usd'})
    if rec_m['exists'] and len(df_m)==0: blockers.append({'blocker_id':'107m_frontier_empty'})
    june_l=int(rec_l.get('june_rows',0) or 0)
    if blockers: decision='BLOCKED_INPUT_INCOMPLETE'
    elif june_l>0: decision='107Q_INPUTS_HAVE_JUNE_RERUN_107Q_READY'
    else: decision='107L_INPUT_STOPS_BEFORE_JUNE_REGENERATE_107L_REQUIRED'
    dec=pd.DataFrame([{'decision':decision,'107l_rows':rec_l['rows'],'107l_max_entry_dt':rec_l['max_entry_dt'],'107l_june_rows':june_l,'107m_rows':rec_m['rows']}]); save(dec,out/'gold_v3_117i_decision.csv')
    status=READY if not blockers else BLOCKED
    summary=dict(step=STEP,status=status,ready=status==READY,decision=decision,created_at_utc=datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z'),output_dir=str(out),input_107l_path=str(p107l),input_107m_path=str(p107m),input_107l_rows=rec_l['rows'],input_107l_min_entry_dt=rec_l['min_entry_dt'],input_107l_max_entry_dt=rec_l['max_entry_dt'],input_107l_june_rows=june_l,input_107m_rows=rec_m['rows'],source_csv_mutated=False,contract_mutated=False,open_asof_allowed=False,approximate_reconstruction=False,blocker_count=len(blockers),elapsed_seconds=round(time.time()-t0,2))
    if not df_l.empty: summary.update({f'input_107l_{k}':v for k,v in metrics(df_l).items()})
    write_json(out/'gold_v3_117i_summary.json',summary|{'blockers':blockers})
    lines=['GOLD V3 117I PASTE_ME_107Q_GENERATOR_INPUT_FEASIBILITY_AUDIT',f'status: {status}',f'ready: {str(status==READY).lower()}',f'decision: {decision}',f'input_107l_rows: {rec_l["rows"]}',f'input_107l_min_entry_dt: {rec_l["min_entry_dt"]}',f'input_107l_max_entry_dt: {rec_l["max_entry_dt"]}',f'input_107l_june_rows: {june_l}',f'input_107m_rows: {rec_m["rows"]}','source_csv_mutated: false','contract_mutated: false','open_asof_allowed: false','approximate_reconstruction: false','blocker_count: '+str(len(blockers)),'','KEY_METRICS']+[f'{k}: {v}' for k,v in summary.items()]+['','INPUT_COVERAGE',cov.to_string(index=False),'','107L_MONTHLY_METRICS',mon.to_string(index=False) if not mon.empty else 'NO_MONTHLY_ROWS','','BLOCKERS','NO_BLOCKERS' if not blockers else json.dumps(blockers,ensure_ascii=False)]
    (out/'paste_me.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({'status':status,'ready':status==READY,'decision':decision,'paste_me':str(out/'paste_me.txt')},ensure_ascii=False,indent=2))
    return 0 if status==READY else 2
if __name__=='__main__': raise SystemExit(main())
