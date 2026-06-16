#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse,json,time
from datetime import datetime,timezone
from pathlib import Path
import pandas as pd
import gold_v3_107gy_light_non_calendar_subfilter_search_audit as gy
STEP='GOLD_V3_171_PARALLEL_CONTRACT_PREFLIGHT_AUDIT_ONLY'

def read_json(p:Path)->dict:
    try:
        return json.loads(p.read_text(encoding='utf-8')) if p.exists() else {}
    except Exception:
        return {}

def read_csv(p:Path)->pd.DataFrame:
    return pd.read_csv(p,encoding='utf-8-sig',low_memory=False) if p.exists() else pd.DataFrame()

def save_csv(df:pd.DataFrame,p:Path)->None:
    p.parent.mkdir(parents=True,exist_ok=True)
    df.to_csv(p,index=False,encoding='utf-8-sig')

def ok_bool(v):
    if isinstance(v,bool): return v
    if isinstance(v,str): return v.lower()=='true'
    return bool(v)

def main()->int:
    t0=time.time()
    ap=argparse.ArgumentParser()
    ap.add_argument('--mt5-files-dir',default='')
    args=ap.parse_args()
    mt5=gy.mt5_files_dir(args.mt5_files_dir)
    root=mt5/'FX_OUTPUTS'/'gold_v3'
    out=root/'171'
    out.mkdir(parents=True,exist_ok=True)
    contract=read_json(root/'170'/'gold_v3_170_parallel_execution_contract_packet.json')
    metrics=read_csv(root/'169'/'gold_v3_169_parallel_bucket_variant_metrics.csv')
    conflict=read_csv(root/'169'/'gold_v3_169_conflict_summary.csv')
    current_orders=read_csv(root/'169'/'gold_v3_169_current_cap10_orders.csv')
    later_orders=read_csv(root/'169'/'gold_v3_169_later_cap5_internal_mixed_skipped_orders.csv')
    blockers=[]; checks=[]
    def add(name,passed,detail,blocker=False):
        checks.append({'check':name,'passed':bool(passed),'blocker':bool(blocker and not passed),'detail':detail})
        if blocker and not passed:
            blockers.append({'id':name,'detail':detail})
    add('stage170_contract_exists',bool(contract),str(root/'170'/'gold_v3_170_parallel_execution_contract_packet.json'),True)
    add('stage169_metrics_exists',not metrics.empty,str(root/'169'/'gold_v3_169_parallel_bucket_variant_metrics.csv'),True)
    add('current_orders_exists',not current_orders.empty,str(root/'169'/'gold_v3_169_current_cap10_orders.csv'),True)
    add('later_orders_exists',not later_orders.empty,str(root/'169'/'gold_v3_169_later_cap5_internal_mixed_skipped_orders.csv'),True)
    if contract:
        add('audit_only_true',ok_bool(contract.get('audit_only')),contract.get('audit_only'),True)
        add('final_live_disabled',not ok_bool(contract.get('final_live_enabled')),contract.get('final_live_enabled'),True)
        add('mt5_order_disabled',not ok_bool(contract.get('mt5_order_enabled')),contract.get('mt5_order_enabled'),True)
        add('discord_disabled',not ok_bool(contract.get('discord_enabled')),contract.get('discord_enabled'),True)
        add('open_asof_not_allowed',not ok_bool(contract.get('open_asof_allowed')),contract.get('open_asof_allowed'),True)
        add('candidate_pool_not_removed',not ok_bool(contract.get('candidate_pool_removed')),contract.get('candidate_pool_removed'),True)
        add('f002_not_bypassed',not ok_bool(contract.get('f002_exclusion_bypassed')),contract.get('f002_exclusion_bypassed'),True)
        ex=contract.get('execution_model',{})
        cur=ex.get('current_bucket',{})
        lat=ex.get('later_bucket',{})
        add('current_max_orders_10',cur.get('max_orders_per_entry_dt')==10,cur.get('max_orders_per_entry_dt'),True)
        add('later_max_orders_5',lat.get('max_orders_per_entry_dt')==5,lat.get('max_orders_per_entry_dt'),True)
        add('total_max_orders_15',ex.get('max_total_orders_per_entry_dt_contract')==15,ex.get('max_total_orders_per_entry_dt_contract'),True)
        add('total_max_lot_015',abs(float(ex.get('max_total_lot_contract',-1))-0.15)<1e-9,ex.get('max_total_lot_contract'),True)
        add('bucket_conflict_skip_all_defined','skip all' in str(ex.get('bucket_conflict_policy','')).lower(),ex.get('bucket_conflict_policy'),True)
    selected=None
    if not metrics.empty and 'variant' in metrics.columns:
        hit=metrics[metrics['variant'].astype(str).eq('PARALLEL_SKIP_ALL_ON_BUCKET_CONFLICT')]
        if not hit.empty: selected=hit.iloc[0]
    add('selected_variant_metrics_present',selected is not None,'PARALLEL_SKIP_ALL_ON_BUCKET_CONFLICT',True)
    if selected is not None:
        add('selected_full_neg_months_zero',int(selected.get('full_neg_months',999))==0,selected.get('full_neg_months'),True)
        add('selected_after_neg_months_zero',int(selected.get('after_neg_months',999))==0,selected.get('after_neg_months'),True)
        add('observed_orders_within_contract',int(selected.get('full_max_orders_per_entry_dt',999))<=15,selected.get('full_max_orders_per_entry_dt'),True)
        add('after_pf_positive',float(selected.get('after_stack_pf',0))>0,selected.get('after_stack_pf'),True)
    if not conflict.empty:
        row=conflict.iloc[0]
        add('later_internal_mixed_handled',int(row.get('later_internal_mixed_skipped',0))>=0,row.get('later_internal_mixed_skipped'),False)
        add('bucket_conflict_count_known','bucket_conflict_entry_dt' in conflict.columns,row.to_dict(),True)
    runtime_items=[
        {'item':'CSV latest row contract','required':'closed row only; no open/as-of shortcut','status':'MUST_KEEP'},
        {'item':'Current bucket construction','required':'density_safe||100||Q0.6; score-desc top 10; mixed-side skip','status':'READY_FOR_DRY_RUN_SPEC'},
        {'item':'Later bucket construction','required':'P1_D1/P2_DEN/P3_RSI/P4_H1_D1_STRICT/P5_H1UP_CUR; one per candidate; mixed-side bucket skip','status':'READY_FOR_DRY_RUN_SPEC'},
        {'item':'Bucket conflict','required':'current and later opposite sides at same entry_dt -> skip all orders for that timestamp','status':'READY_FOR_DRY_RUN_SPEC'},
        {'item':'Lot sizing','required':'0.01 lot per order; current max 0.10; later max 0.05; total contract max 0.15','status':'READY_FOR_DRY_RUN_SPEC'},
        {'item':'NO_SIGNAL','required':'NO_SIGNAL does not notify Discord','status':'MUST_KEEP'},
        {'item':'Live enablement','required':'No Discord/MT5 order/AI API/live hook/live evaluator/final signal enabled by this packet','status':'BLOCKED_UNTIL_EXPLICIT_APPROVAL'},
    ]
    save_csv(pd.DataFrame(checks),out/'gold_v3_171_preflight_checks.csv')
    save_csv(pd.DataFrame(runtime_items),out/'gold_v3_171_runtime_implementation_items.csv')
    status='READY' if not blockers else 'BLOCKED'
    decision='PARALLEL_CONTRACT_PREFLIGHT_READY_FOR_DRY_RUN_SPEC' if status=='READY' else 'PARALLEL_CONTRACT_PREFLIGHT_BLOCKED'
    summary={
        'step':STEP,'status':status,'ready':not blockers,'decision':decision,
        'created_at_utc':datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z'),
        'output_dir':str(out),'audit_only':True,'review_only':True,
        'selected_variant':'PARALLEL_SKIP_ALL_ON_BUCKET_CONFLICT',
        'source_170_decision':contract.get('decision','') if contract else '',
        'source_csv_mutated':False,'contract_mutated':False,'open_asof_allowed':False,'candidate_pool_removed':False,'f002_exclusion_bypassed':False,
        'final_live_enabled':False,'mt5_order_enabled':False,'discord_enabled':False,'ai_api_enabled':False,'live_hook_enabled':False,'live_evaluator_enabled':False,
        'check_count':len(checks),'passed_count':sum(1 for c in checks if c['passed']),'blocker_count':len(blockers),'elapsed_seconds':round(time.time()-t0,2)
    }
    (out/'gold_v3_171_summary.json').write_text(json.dumps(summary|{'blockers':blockers,'checks':checks,'runtime_items':runtime_items},ensure_ascii=False,indent=2),encoding='utf-8')
    save_csv(pd.DataFrame([summary]),out/'gold_v3_171_decision.csv')
    lines=[]
    lines.append('GOLD V3 171 PASTE_ME_PARALLEL_CONTRACT_PREFLIGHT_AUDIT')
    for k,v in summary.items(): lines.append(f'{k}: {v}')
    lines.append('')
    lines.append('PREFLIGHT_CHECKS')
    lines.append(pd.DataFrame(checks).to_string(index=False))
    lines.append('')
    lines.append('RUNTIME_IMPLEMENTATION_ITEMS')
    lines.append(pd.DataFrame(runtime_items).to_string(index=False))
    lines.append('')
    lines.append('INTERPRETATION')
    lines.append('The Stage170 parallel execution contract is preflight-checked for a future audit-only dry-run specification. This does not enable live trading, MT5 orders, Discord, AI API, live hook, live evaluator, or final signal.')
    lines.append('')
    lines.append('BLOCKERS')
    lines.append('NO_BLOCKERS' if not blockers else json.dumps(blockers,ensure_ascii=False,indent=2))
    (out/'paste_me.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({'ready':not blockers,'decision':decision,'paste_me':str(out/'paste_me.txt')},ensure_ascii=False))
    return 0 if not blockers else 2
if __name__=='__main__': raise SystemExit(main())
