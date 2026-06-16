#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse,json,time
from datetime import datetime,timezone
from pathlib import Path
import pandas as pd
import gold_v3_107gy_light_non_calendar_subfilter_search_audit as gy
STEP='GOLD_V3_172_REVIEW_DASHBOARD_AUDIT_ONLY'
SELECTED='PARALLEL_SKIP_ALL_ON_BUCKET_CONFLICT'

def csv(p:Path)->pd.DataFrame:
    return pd.read_csv(p,encoding='utf-8-sig',low_memory=False) if p.exists() else pd.DataFrame()
def js(p:Path)->dict:
    try: return json.loads(p.read_text(encoding='utf-8')) if p.exists() else {}
    except Exception: return {}
def save(df,p): p.parent.mkdir(parents=True,exist_ok=True); df.to_csv(p,index=False,encoding='utf-8-sig')
def f(v):
    try: return float(v) if not pd.isna(v) else 0.0
    except Exception: return 0.0
def i(v):
    try: return int(v) if not pd.isna(v) else 0
    except Exception: return 0

def main():
    t0=time.time(); ap=argparse.ArgumentParser(); ap.add_argument('--mt5-files-dir',default=''); args=ap.parse_args()
    root=gy.mt5_files_dir(args.mt5_files_dir)/'FX_OUTPUTS'/'gold_v3'; out=root/'172'; out.mkdir(parents=True,exist_ok=True)
    s171=js(root/'171'/'gold_v3_171_summary.json'); metrics=csv(root/'169'/'gold_v3_169_parallel_bucket_variant_metrics.csv'); packet=csv(root/'169'/'gold_v3_169_later_candidate_packet.csv'); monthly=csv(root/'169'/'gold_v3_169_parallel_bucket_monthly.csv')
    blockers=[]
    if not s171: blockers.append({'id':'missing_171'})
    if metrics.empty: blockers.append({'id':'missing_169_metrics'})
    if packet.empty: blockers.append({'id':'missing_169_later_packet'})
    rows=[]
    labels={'CURRENT_ONLY':'旧current bestのみ','LATER_ONLY_SKIP_INTERNAL_MIXED':'後続候補のみ','PARALLEL_SKIP_ALL_ON_BUCKET_CONFLICT':'採用候補: 旧current best + 後続候補'}
    if not metrics.empty:
        for v in ['CURRENT_ONLY','LATER_ONLY_SKIP_INTERNAL_MIXED','PARALLEL_SKIP_ALL_ON_BUCKET_CONFLICT']:
            h=metrics[metrics.variant.astype(str).eq(v)]
            if h.empty: continue
            r=h.iloc[0]
            rows.append({'variant':v,'name':labels[v],'selected':v==SELECTED,'max_lot_observed':f(r.get('max_lot_if_001_per_order')),'full_units':i(r.get('full_orders')),'full_times':i(r.get('full_entry_dt')),'full_sum':round(f(r.get('full_sum')),2),'full_pf':round(f(r.get('full_stack_pf')),3),'full_neg_months':i(r.get('full_neg_months')),'after_units':i(r.get('after_orders')),'after_times':i(r.get('after_entry_dt')),'after_sum':round(f(r.get('after_sum')),2),'after_pf':round(f(r.get('after_stack_pf')),3),'after_neg_months':i(r.get('after_neg_months'))})
    dash=pd.DataFrame(rows); save(dash,out/'gold_v3_172_review_dashboard.csv')
    crows=[]
    if not packet.empty:
        for _,r in packet.iterrows():
            c=str(r.get('candidate',''))
            crows.append({'candidate':c,'desc':str(r.get('desc','')),'lot_each':0.01,'full_units':i(r.get('one_full_orders')),'full_sum':round(f(r.get('one_full_sum')),2),'full_pf':round(f(r.get('one_full_row_pf')),3),'full_neg_months':i(r.get('one_full_neg_months')),'after_units':i(r.get('one_after_orders')),'after_sum':round(f(r.get('one_after_sum')),2),'after_pf':str(r.get('one_after_row_pf')) if str(r.get('one_after_row_pf')).lower()=='inf' else round(f(r.get('one_after_row_pf')),3)})
    cand=pd.DataFrame(crows); save(cand,out/'gold_v3_172_later_candidate_dashboard.csv')
    mp=pd.DataFrame()
    if not monthly.empty:
        u=monthly[monthly.variant.astype(str).isin(['CURRENT_ONLY','LATER_ONLY_SKIP_INTERNAL_MIXED',SELECTED])]
        if not u.empty: mp=u.pivot_table(index='month',columns='variant',values='sum',aggfunc='sum').reset_index(); save(mp,out/'gold_v3_172_monthly_dashboard.csv')
    status='READY' if not blockers else 'BLOCKED'; decision='REVIEW_DASHBOARD_READY' if status=='READY' else 'REVIEW_DASHBOARD_BLOCKED'
    summary={'step':STEP,'status':status,'ready':not blockers,'decision':decision,'created_at_utc':datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z'),'output_dir':str(out),'audit_only':True,'review_only':True,'selected_variant':SELECTED,'dashboard_rows':len(dash),'candidate_rows':len(cand),'monthly_rows':len(mp),'source_171_decision':s171.get('decision','') if s171 else '','source_csv_mutated':False,'contract_mutated':False,'open_asof_allowed':False,'candidate_pool_removed':False,'f002_exclusion_bypassed':False,'final_live_enabled':False,'mt5_order_enabled':False,'discord_enabled':False,'blocker_count':len(blockers),'elapsed_seconds':round(time.time()-t0,2)}
    (out/'gold_v3_172_summary.json').write_text(json.dumps(summary|{'blockers':blockers},ensure_ascii=False,indent=2),encoding='utf-8'); save(pd.DataFrame([summary]),out/'gold_v3_172_decision.csv')
    lines=['GOLD V3 172 PASTE_ME_REVIEW_DASHBOARD_AUDIT']+[f'{k}: {v}' for k,v in summary.items()]+['','OPERATION_DASHBOARD',dash.to_string(index=False) if not dash.empty else 'NO_DASHBOARD','','LATER_CANDIDATE_DASHBOARD',cand.to_string(index=False) if not cand.empty else 'NO_CANDIDATES','','MONTHLY_DASHBOARD',mp.to_string(index=False) if not mp.empty else 'NO_MONTHLY','','INTERPRETATION','Compact audit-only dashboard for reviewing practical performance by operation pattern and by later candidate. No final/live path is enabled.','','BLOCKERS','NO_BLOCKERS' if not blockers else json.dumps(blockers,ensure_ascii=False,indent=2)]
    (out/'paste_me.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({'ready':not blockers,'decision':decision,'paste_me':str(out/'paste_me.txt')},ensure_ascii=False)); return 0 if not blockers else 2
if __name__=='__main__': raise SystemExit(main())
