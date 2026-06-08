#!/usr/bin/env python
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd

STEP='25C79_A002_ID_JOIN'
OUT_DIR='gold_v2_25c79_a002_id_join'
LEDGER='gold_v2_25c66_a002_fixed_scope_dry_run_execution_audit_only/05_25c66_dry_run_event_ledger.csv'
ID1='gold_v2_25c3_coreb_intersection_only_dry_run_implementation_audit_only/07_25c3_source_universe_hit_counts_by_entry.csv'
ID2='gold_v2_25c3_coreb_intersection_only_dry_run_implementation_audit_only/08_25c3_selected_rule_hit_rows.csv'
RAW='gold_v2_rr125_second_core_probe_outputs/rr125_raw_signal_ledger.csv'


def base():
    r=Path(__file__).resolve().parents[2]
    return r.parents[1]/'FX_OUTPUTS'

def rcsv(p):
    for e in ('utf-8-sig','utf-8','cp932'):
        try: return pd.read_csv(p,encoding=e,keep_default_na=False)
        except Exception: pass
    return pd.read_csv(p)

def wcsv(p,df):
    p.parent.mkdir(parents=True,exist_ok=True); df.to_csv(p,index=False,encoding='utf-8-sig')

def prep(df):
    for c in df.columns:
        if c in ['entry_time','dataset','policy','candidate_id','origin_id','variant']:
            df[c]=df[c].astype(str)
    return df

def review(src_name, id_path, ledger, raw):
    ids=prep(rcsv(id_path))
    keys=[c for c in ['entry_time','dataset','policy'] if c in ledger.columns and c in ids.columns]
    id_cols=[c for c in ['candidate_id','origin_id','variant'] if c in ids.columns]
    id_keep=list(dict.fromkeys(keys+id_cols))
    id_rows=ledger[['a002_fixed_scope_event_id']+keys].merge(ids[id_keep].drop_duplicates(),on=keys,how='left')
    raw_keys=[c for c in ['entry_time','dataset','policy','candidate_id','origin_id','variant'] if c in id_rows.columns and c in raw.columns]
    joined=id_rows.merge(raw,on=raw_keys,how='left',indicator=True)
    g=joined.groupby('a002_fixed_scope_event_id',dropna=False).agg(
        id_rows=('a002_fixed_scope_event_id','size'),
        raw_match_rows=('_merge',lambda s:int((s=='both').sum())),
        unique_profit_r=('profit_r',lambda s:s.astype(str).nunique(dropna=False)),
        unique_exit_time=('exit_time',lambda s:s.astype(str).nunique(dropna=False)),
        unique_candidate_id=('candidate_id',lambda s:s.astype(str).nunique(dropna=False)),
        unique_origin_id=('origin_id',lambda s:s.astype(str).nunique(dropna=False)),
        unique_variant=('variant',lambda s:s.astype(str).nunique(dropna=False)),
    ).reset_index()
    g['profit_exit_unique']=g['unique_profit_r'].eq(1)&g['unique_exit_time'].eq(1)&g['raw_match_rows'].gt(0)
    summary={
        'source':src_name,
        'id_rows_total':int(len(id_rows)),
        'joined_rows_total':int(len(joined)),
        'events':int(len(g)),
        'events_with_raw_match':int((g['raw_match_rows']>0).sum()),
        'events_profit_exit_unique':int(g['profit_exit_unique'].sum()),
        'events_ambiguous':int((~g['profit_exit_unique']).sum()),
        'raw_keys':';'.join(raw_keys),
    }
    return pd.DataFrame([summary]), g


def main():
    b=base(); out=b/OUT_DIR; out.mkdir(parents=True,exist_ok=True)
    paths={'ledger':b/LEDGER,'id1':b/ID1,'id2':b/ID2,'raw':b/RAW}
    checks=pd.DataFrame([{'name':k,'path':str(v.relative_to(b)),'exists':v.exists(),'status':'PASS' if v.exists() else 'STOP'} for k,v in paths.items()])
    wcsv(out/'03_25c79_input_checks.csv',checks)
    if checks['status'].eq('STOP').any():
        summary={'created_utc':datetime.now(timezone.utc).isoformat(),'step':STEP,'status':'STOP_MISSING_INPUT','total_stop_rows':int(checks['status'].eq('STOP').sum())}
        with open(out/'02_25c79_summary.json','w',encoding='utf-8') as f: json.dump(summary,f,ensure_ascii=False,indent=2)
        (out/'01_25c79_A002_ID_JOIN.md').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps(summary,ensure_ascii=False,indent=2)); return 2
    ledger=prep(rcsv(paths['ledger'])); raw=prep(rcsv(paths['raw']))
    s1,g1=review('source_universe_hit_counts_by_entry',paths['id1'],ledger,raw)
    s2,g2=review('selected_rule_hit_rows',paths['id2'],ledger,raw)
    allsum=pd.concat([s1,s2],ignore_index=True)
    best=allsum.sort_values(['events_profit_exit_unique','events_with_raw_match'],ascending=False).iloc[0].to_dict()
    status='A002_ID_JOIN_READY' if int(best['events_profit_exit_unique'])==772 else 'A002_ID_JOIN_BLOCKED'
    decision=pd.DataFrame([
        {'decision':'use_all_772_profit_exit','status':'PASS' if status.endswith('READY') else 'BLOCKED','reason':'requires 772 unique profit and exit rows'},
        {'decision':'best_identity_source','status':'RECORDED','reason':str(best['source'])},
    ])
    next_plan=pd.DataFrame([
        {'rank':1,'next_step':'25C80_A002_RESULT_SUMMARY' if status.endswith('READY') else 'REQUEST_EXACT_A002_ID_LEDGER','allowed_now':True},
        {'rank':2,'next_step':'use_ambiguous_profit','allowed_now':False},
    ])
    summary={'created_utc':datetime.now(timezone.utc).isoformat(),'step':STEP,'status':status,'best_source':str(best['source']),'best_events_with_raw_match':int(best['events_with_raw_match']),'best_events_profit_exit_unique':int(best['events_profit_exit_unique']),'best_events_ambiguous':int(best['events_ambiguous']),'raw_keys':str(best['raw_keys']),'next_recommended_step':str(next_plan.iloc[0]['next_step']),'total_stop_rows':0}
    wcsv(out/'04_25c79_source_summary.csv',allsum)
    wcsv(out/'05_25c79_source_universe_event_review.csv',g1)
    wcsv(out/'06_25c79_selected_rule_event_review.csv',g2)
    wcsv(out/'07_25c79_decision_matrix.csv',decision)
    wcsv(out/'08_25c79_next_step_plan.csv',next_plan)
    with open(out/'02_25c79_summary.json','w',encoding='utf-8') as f: json.dump(summary,f,ensure_ascii=False,indent=2)
    (out/'01_25c79_A002_ID_JOIN.md').write_text('# GOLD V2 25C79 A002 id join\n\n'+json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False,indent=2)); return 0
if __name__=='__main__': raise SystemExit(main())
