#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse, json, math, time
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
import numpy as np
import gold_v3_107gy_light_non_calendar_subfilter_search_audit as gy

STEP='GOLD_V3_117G_107R6_BASE_LEDGER_COVERAGE_AND_SHADOW_109'
READY='GOLD_V3_117G_107R6_BASE_LEDGER_COVERAGE_AND_SHADOW_109_READY'
BLOCKED='GOLD_V3_117G_107R6_BASE_LEDGER_COVERAGE_AND_SHADOW_109_BLOCKED'

def save(df,p): p.parent.mkdir(parents=True,exist_ok=True); df.to_csv(p,index=False,encoding='utf-8-sig')
def write_json(p,o): p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(o,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
def load_json(p):
    if not p.exists(): return {}
    try: return json.loads(p.read_text(encoding='utf-8'))
    except Exception: return {}
def pf(vals):
    a=np.asarray(pd.to_numeric(pd.Series(vals),errors='coerce').dropna(),dtype=float)
    gp=a[a>0].sum(); gl=-a[a<0].sum()
    if gl>0: return float(gp/gl)
    if gp>0: return math.inf
    return 0.0
def metrics(df):
    if df is None or df.empty: return dict(trades=0,wins=0,losses=0,win_rate=0.0,profit_factor=0.0,sum_result_usd=0.0,negative_month_count=0)
    x=df.copy(); x['entry_dt']=pd.to_datetime(x['entry_dt'],errors='coerce'); x['result_usd']=pd.to_numeric(x['result_usd'],errors='coerce')
    x=x[x.entry_dt.notna()&x.result_usd.notna()].copy()
    if x.empty: return metrics(pd.DataFrame())
    mon=x.groupby(x.entry_dt.dt.to_period('M').astype(str)).result_usd.sum()
    return dict(trades=int(len(x)),wins=int((x.result_usd>0).sum()),losses=int((x.result_usd<0).sum()),win_rate=float((x.result_usd>0).mean()),profit_factor=pf(x.result_usd),sum_result_usd=float(x.result_usd.sum()),negative_month_count=int((mon<0).sum()))
def group_month(df):
    if df is None or df.empty: return pd.DataFrame()
    x=df.copy(); x['entry_dt']=pd.to_datetime(x['entry_dt'],errors='coerce'); x=x[x.entry_dt.notna()].copy(); x['month']=x.entry_dt.dt.to_period('M').astype(str)
    rows=[]
    for m,g in x.groupby('month'):
        r={'month':m}; r.update(metrics(g)); rows.append(r)
    return pd.DataFrame(rows)
def main():
    t0=time.time(); ap=argparse.ArgumentParser(); ap.add_argument('--mt5-files-dir',default=''); args=ap.parse_args()
    mt5=gy.mt5_files_dir(args.mt5_files_dir); root=mt5/'FX_OUTPUTS'/'gold_v3'; out=root/'117g'; out.mkdir(parents=True,exist_ok=True)
    base=root/'107r6c'/'gold_v3_107r6_resolved_107q_best_family_ledger.csv'
    req={'base_ledger':base,'s107':root/'107sc'/'gold_v3_107s_summary.json','s108':root/'108c'/'gold_v3_108_summary.json','s108b':root/'108bc'/'gold_v3_108b_summary.json'}
    blockers=[]
    for k,p in req.items():
        if not p.exists(): blockers.append({'blocker_id':'missing_'+k,'path':str(p)})
    ledger=pd.DataFrame(); cov=pd.DataFrame(); monthly=pd.DataFrame(); june_rows=0; max_dt=''; min_dt=''
    if not blockers:
        ledger=pd.read_csv(base,encoding='utf-8-sig',low_memory=False)
        for c in ['entry_dt','exit_dt','result_usd']:
            if c not in ledger.columns: blockers.append({'blocker_id':'base_ledger_missing_required_column','column':c})
    if not blockers:
        ledger=ledger.copy(); ledger['entry_dt']=pd.to_datetime(ledger.entry_dt,errors='coerce'); ledger['result_usd']=pd.to_numeric(ledger.result_usd,errors='coerce')
        ledger=ledger[ledger.entry_dt.notna()&ledger.result_usd.notna()].copy().sort_values('entry_dt')
        min_dt=str(ledger.entry_dt.min()) if not ledger.empty else ''; max_dt=str(ledger.entry_dt.max()) if not ledger.empty else ''
        june_rows=int(((ledger.entry_dt>=pd.Timestamp('2026-06-01'))&(ledger.entry_dt<pd.Timestamp('2026-07-01'))).sum())
        cov=pd.DataFrame([{'path':str(base),'rows':len(ledger),'min_entry_dt':min_dt,'max_entry_dt':max_dt,'june_rows':june_rows,'columns':len(ledger.columns)}])
        save(cov,out/'gold_v3_117g_107r6_base_ledger_coverage.csv')
        shadow=ledger.copy()
        shadow['selected_option']='KEEP_107Q_BASE'
        shadow['selected_policy_key']='107Q_BASE_RESOLVED_PASS_THROUGH'
        shadow['health_gate_adopted']=False
        shadow['stage117g_shadow_reason']='shadow copy of Stage109 direct base ledger input; 109c not overwritten'
        save(shadow,out/'gold_v3_117g_shadow_109_selected_base_policy_ledger.csv')
        monthly=group_month(shadow)
        save(monthly,out/'gold_v3_117g_monthly_metrics.csv')
    m=metrics(ledger) if not ledger.empty else metrics(pd.DataFrame())
    if blockers: decision='BLOCKED_INPUT_INCOMPLETE'
    elif june_rows>0: decision='SHADOW_109_REGEN_HAS_JUNE_ROWS_REVIEW_READY'
    else: decision='107R6_BASE_LEDGER_STOPS_BEFORE_JUNE_REGENERATE_107R6_REQUIRED'
    dec=pd.DataFrame([{'decision':decision,'base_ledger_path':str(base),'base_rows':len(ledger),'min_entry_dt':min_dt,'max_entry_dt':max_dt,'june_rows':june_rows}])
    save(dec,out/'gold_v3_117g_decision.csv')
    status=READY if not blockers else BLOCKED
    summary=dict(step=STEP,status=status,ready=status==READY,decision=decision,created_at_utc=datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z'),output_dir=str(out),base_ledger_path=str(base),base_rows=int(len(ledger)),min_entry_dt=min_dt,max_entry_dt=max_dt,june_rows=june_rows,source_csv_mutated=False,contract_mutated=False,open_asof_allowed=False,approximate_reconstruction=False,shadow_only=True,blocker_count=len(blockers),elapsed_seconds=round(time.time()-t0,2))
    summary.update({f'base_{k}':v for k,v in m.items()})
    write_json(out/'gold_v3_117g_summary.json',summary|{'blockers':blockers})
    lines=['GOLD V3 117G PASTE_ME_107R6_BASE_LEDGER_COVERAGE_AND_SHADOW_109',f'status: {status}',f'ready: {str(status==READY).lower()}',f'decision: {decision}',f'base_ledger_path: {base}',f'base_rows: {len(ledger)}',f'min_entry_dt: {min_dt}',f'max_entry_dt: {max_dt}',f'june_rows: {june_rows}','shadow_only: true','source_csv_mutated: false','contract_mutated: false','open_asof_allowed: false','approximate_reconstruction: false','blocker_count: '+str(len(blockers)),'','KEY_METRICS']+[f'{k}: {v}' for k,v in summary.items()]+['','MONTHLY_METRICS',monthly.to_string(index=False) if not monthly.empty else 'NO_MONTHLY_ROWS','','BLOCKERS','NO_BLOCKERS' if not blockers else json.dumps(blockers,ensure_ascii=False)]
    (out/'paste_me.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({'status':status,'ready':status==READY,'decision':decision,'paste_me':str(out/'paste_me.txt')},ensure_ascii=False,indent=2))
    return 0 if status==READY else 2
if __name__=='__main__': raise SystemExit(main())
