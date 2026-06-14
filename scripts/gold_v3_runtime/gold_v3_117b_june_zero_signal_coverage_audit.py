#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse, json, re, time
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
import gold_v3_107gy_light_non_calendar_subfilter_search_audit as gy

STEP='GOLD_V3_117B_JUNE_ZERO_SIGNAL_COVERAGE_AUDIT'
READY='GOLD_V3_117B_JUNE_ZERO_SIGNAL_COVERAGE_AUDIT_READY'
BLOCKED='GOLD_V3_117B_JUNE_ZERO_SIGNAL_COVERAGE_AUDIT_BLOCKED'
M15_FILES=['goldsharp_m15.csv','gold#_m15.csv']

def save(df,p): p.parent.mkdir(parents=True,exist_ok=True); df.to_csv(p,index=False,encoding='utf-8-sig')
def write_json(p,o): p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(o,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
def load_json(p):
    if not p.exists(): return {}
    try: return json.loads(p.read_text(encoding='utf-8'))
    except Exception: return {}
def norm(x): return re.sub(r'[^a-z0-9]+','',str(x).lower())
def find_col(cols,names):
    m={norm(c):c for c in cols}
    for n in names:
        if n in m: return m[n]
    for k,v in m.items():
        if any(n in k for n in names): return v
    return None
def read_m15_coverage(mt5: Path, june_start, july_start):
    rows=[]; parts=[]
    for fn in M15_FILES:
        p=mt5/fn
        rec={'file':fn,'path':str(p),'exists':p.exists(),'rows':0,'min_time':'','max_time':'','june_rows':0,'error':''}
        if p.exists():
            try:
                sample=p.read_text(encoding='utf-8-sig',errors='ignore')[:4096]
                sep=';' if sample.count(';')>sample.count(',') else ','
                df=pd.read_csv(p,sep=sep,encoding='utf-8-sig')
                t=find_col(df.columns,['time','datetime','date','timestamp'])
                if not t:
                    rec['error']='missing_time_column'
                else:
                    x=pd.DataFrame({'time':pd.to_datetime(df[t],errors='coerce')}).dropna().drop_duplicates('time').sort_values('time')
                    rec['rows']=int(len(x))
                    if not x.empty:
                        rec['min_time']=str(x.time.min())
                        rec['max_time']=str(x.time.max())
                        rec['june_rows']=int(((x.time>=june_start)&(x.time<july_start)).sum())
                        parts.append(x.assign(file=fn))
            except Exception as e:
                rec['error']=str(e)
        rows.append(rec)
    combined=pd.concat(parts,ignore_index=True).drop_duplicates('time').sort_values('time') if parts else pd.DataFrame(columns=['time','file'])
    return pd.DataFrame(rows), combined
def main():
    t0=time.time(); ap=argparse.ArgumentParser(); ap.add_argument('--mt5-files-dir',default=''); args=ap.parse_args()
    mt5=gy.mt5_files_dir(args.mt5_files_dir); root=mt5/'FX_OUTPUTS'/'gold_v3'; out=root/'117b'; out.mkdir(parents=True,exist_ok=True)
    ledger_path=root/'109c'/'gold_v3_109_selected_base_policy_ledger.csv'
    freeze_path=root/'112c'/'gold_v3_112_selected_policy_freeze_manifest.json'
    blockers=[]
    if not ledger_path.exists(): blockers.append({'blocker_id':'missing_selected_ledger','path':str(ledger_path)})
    freeze=load_json(freeze_path)
    if not freeze: blockers.append({'blocker_id':'missing_or_unreadable_freeze_manifest','path':str(freeze_path)})
    june_start=pd.Timestamp('2026-06-01'); july_start=pd.Timestamp('2026-07-01')
    ledger=pd.DataFrame(); month_counts=pd.DataFrame(); ledger_min=''; ledger_max=''; june_selected_rows=0
    if not blockers:
        ledger=pd.read_csv(ledger_path,encoding='utf-8-sig',low_memory=False)
        if 'entry_dt' not in ledger.columns:
            blockers.append({'blocker_id':'ledger_missing_entry_dt'})
        else:
            ledger['entry_dt']=pd.to_datetime(ledger['entry_dt'],errors='coerce')
            ledger=ledger[ledger.entry_dt.notna()].copy()
            if not ledger.empty:
                ledger_min=str(ledger.entry_dt.min())
                ledger_max=str(ledger.entry_dt.max())
                ledger['month']=ledger.entry_dt.dt.to_period('M').astype(str)
                month_counts=ledger.groupby('month').size().reset_index(name='selected_rows')
                june_selected_rows=int(((ledger.entry_dt>=june_start)&(ledger.entry_dt<july_start)).sum())
            save(month_counts,out/'gold_v3_117b_selected_ledger_month_counts.csv')
    cov, m15 = read_m15_coverage(mt5,june_start,july_start)
    save(cov,out/'gold_v3_117b_m15_ohlc_coverage.csv')
    combined_m15_rows=int(len(m15))
    m15_min=str(m15.time.min()) if not m15.empty else ''
    m15_max=str(m15.time.max()) if not m15.empty else ''
    m15_june_rows=int(((m15.time>=june_start)&(m15.time<july_start)).sum()) if not m15.empty else 0
    decision=''
    if blockers:
        decision='BLOCKED_INPUT_INCOMPLETE'
    elif m15_june_rows==0:
        decision='DATA_COVERAGE_INCOMPLETE_M15_NO_JUNE_ROWS'
    elif june_selected_rows>0:
        decision='JUNE_SELECTED_ROWS_PRESENT'
    elif pd.Timestamp(ledger.entry_dt.max()) < june_start:
        decision='SELECTED_LEDGER_ENDS_BEFORE_JUNE'
    elif m15_june_rows>0 and june_selected_rows==0:
        decision='M15_HAS_JUNE_BUT_SELECTED_LEDGER_HAS_ZERO_JUNE_ROWS'
    else:
        decision='JUNE_ZERO_UNCLASSIFIED_REVIEW'
    dec=pd.DataFrame([{
        'decision':decision,
        'selected_policy_key':freeze.get('selected_policy_key',''),
        'ledger_min_entry_dt':ledger_min,
        'ledger_max_entry_dt':ledger_max,
        'june_selected_rows':june_selected_rows,
        'm15_min_time':m15_min,
        'm15_max_time':m15_max,
        'm15_june_rows':m15_june_rows,
        'combined_m15_rows':combined_m15_rows,
    }])
    save(dec,out/'gold_v3_117b_coverage_decision.csv')
    status=READY if not blockers else BLOCKED
    summary=dict(step=STEP,status=status,ready=status==READY,decision=decision,created_at_utc=datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z'),output_dir=str(out),selected_policy_key=freeze.get('selected_policy_key',''),ledger_min_entry_dt=ledger_min,ledger_max_entry_dt=ledger_max,june_selected_rows=june_selected_rows,m15_min_time=m15_min,m15_max_time=m15_max,m15_june_rows=m15_june_rows,combined_m15_rows=combined_m15_rows,source_csv_mutated=False,contract_mutated=False,open_asof_allowed=False,approximate_reconstruction=False,blocker_count=len(blockers),elapsed_seconds=round(time.time()-t0,2))
    write_json(out/'gold_v3_117b_summary.json',summary|{'blockers':blockers})
    lines=['GOLD V3 117B PASTE_ME_JUNE_ZERO_SIGNAL_COVERAGE_AUDIT',f'status: {status}',f'ready: {str(status==READY).lower()}',f'decision: {decision}',f'selected_policy_key: {summary.get("selected_policy_key")}',f'ledger_min_entry_dt: {ledger_min}',f'ledger_max_entry_dt: {ledger_max}',f'june_selected_rows: {june_selected_rows}',f'm15_min_time: {m15_min}',f'm15_max_time: {m15_max}',f'm15_june_rows: {m15_june_rows}',f'combined_m15_rows: {combined_m15_rows}','source_csv_mutated: false','contract_mutated: false','open_asof_allowed: false','approximate_reconstruction: false','blocker_count: '+str(len(blockers)),'','KEY_METRICS']+[f'{k}: {v}' for k,v in summary.items()]+['','SELECTED_LEDGER_MONTH_COUNTS',month_counts.to_string(index=False) if not month_counts.empty else 'NO_LEDGER_MONTH_ROWS','','M15_COVERAGE',cov.to_string(index=False),'','BLOCKERS','NO_BLOCKERS' if not blockers else json.dumps(blockers,ensure_ascii=False)]
    (out/'paste_me.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({'status':status,'ready':status==READY,'decision':decision,'paste_me':str(out/'paste_me.txt')},ensure_ascii=False,indent=2))
    return 0 if status==READY else 2
if __name__=='__main__': raise SystemExit(main())
