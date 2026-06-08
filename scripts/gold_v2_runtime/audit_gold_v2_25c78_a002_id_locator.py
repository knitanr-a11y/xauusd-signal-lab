#!/usr/bin/env python
from __future__ import annotations
import csv, json
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd

STEP='25C78_A002_ID_LOCATOR'
LEDGER_DIR='gold_v2_25c66_a002_fixed_scope_dry_run_execution_audit_only'
OUT_DIR='gold_v2_25c78_a002_id_locator'
REQ=['candidate_id','origin_id','variant','base_condition','added_filter_text']
TIME=['entry_time','signal_time','time','datetime','open_time']


def base():
    r=Path(__file__).resolve().parents[2]
    return r.parents[1]/'FX_OUTPUTS'

def head(p):
    for e in ('utf-8-sig','utf-8','cp932'):
        try:
            with open(p,encoding=e,newline='') as f: return next(csv.reader(f))
        except Exception: pass
    return []

def rcsv(p,usecols=None):
    for e in ('utf-8-sig','utf-8','cp932'):
        try: return pd.read_csv(p,encoding=e,keep_default_na=False,usecols=usecols)
        except Exception: pass
    return pd.read_csv(p,usecols=usecols)

def first(cols,names):
    m={c.lower().strip():c for c in cols}
    for n in names:
        if n in m: return m[n]
    return ''

def wcsv(p,df):
    p.parent.mkdir(parents=True,exist_ok=True); df.to_csv(p,index=False,encoding='utf-8-sig')

def main():
    b=base(); out=b/OUT_DIR; out.mkdir(parents=True,exist_ok=True)
    ev=rcsv(b/LEDGER_DIR/'05_25c66_dry_run_event_ledger.csv')
    times=set(ev['entry_time'].astype(str))
    rows=[]
    for p in b.rglob('*.csv'):
        if OUT_DIR in p.parts: continue
        cols=head(p)
        if not cols: continue
        low={c.lower().strip():c for c in cols}
        ids=[x for x in REQ if x in low]
        tc=first(cols,TIME)
        if not ids and not tc: continue
        cnt=0; exact=False; n=0; stat='READ_OK'
        try:
            use=[]
            if tc: use.append(tc)
            use += [low[x] for x in ids]
            df=rcsv(p,usecols=list(dict.fromkeys(use)) if use else None)
            n=len(df)
            if tc:
                vals=set(df[tc].astype(str)); cnt=len(vals.intersection(times)); exact=times.issubset(vals)
        except Exception as e:
            stat='READ_ERROR:'+str(e)[:80]
        cat='FULL' if exact and len(ids)==len(REQ) else ('PARTIAL' if cnt>0 and ids else 'OTHER')
        rows.append({'relative_path':str(p.relative_to(b)),'rows':n,'time_column':tc,'id_columns':';'.join(ids),'id_count':len(ids),'match_count':cnt,'match_ratio':round(cnt/772,6),'exact_772':exact,'category':cat,'read_status':stat})
    inv=pd.DataFrame(rows)
    if inv.empty: inv=pd.DataFrame(columns=['relative_path','rows','time_column','id_columns','id_count','match_count','match_ratio','exact_772','category','read_status'])
    inv=inv.sort_values(['category','exact_772','match_count','id_count'],ascending=[True,False,False,False]).reset_index(drop=True)
    full=inv[inv['category'].eq('FULL')].copy(); part=inv[inv['category'].eq('PARTIAL')].copy()
    counts=inv.groupby('category',dropna=False).agg(files=('relative_path','size'),max_match=('match_count','max'),max_id_cols=('id_count','max')).reset_index() if len(inv) else pd.DataFrame()
    req=pd.DataFrame([{'column':x,'status':'REQUIRED'} for x in REQ])
    summary={'created_utc':datetime.now(timezone.utc).isoformat(),'step':STEP,'events':772,'full_candidates':int(len(full)),'partial_candidates':int(len(part)),'best_full':str(full.iloc[0]['relative_path']) if len(full) else '','best_partial':str(part.iloc[0]['relative_path']) if len(part) else '','ready':bool(len(full)),'next':'25C79_A002_ID_JOIN' if len(full) else 'REQUEST_A002_LEDGER_WITH_ID_COLUMNS'}
    wcsv(out/'03_25c78_inventory.csv',inv); wcsv(out/'04_25c78_full_candidates.csv',full); wcsv(out/'05_25c78_partial_candidates.csv',part.head(200)); wcsv(out/'06_25c78_category_counts.csv',counts); wcsv(out/'07_25c78_required_columns.csv',req)
    with open(out/'02_25c78_summary.json','w',encoding='utf-8') as f: json.dump(summary,f,ensure_ascii=False,indent=2)
    (out/'01_25c78_A002_ID_LOCATOR.md').write_text('# GOLD V2 25C78 A002 id locator\n\n'+json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False,indent=2)); return 0
if __name__=='__main__': raise SystemExit(main())
