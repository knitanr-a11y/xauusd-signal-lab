#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse,json,time
from datetime import datetime,timezone
from pathlib import Path
import pandas as pd
import gold_v3_107gy_light_non_calendar_subfilter_search_audit as gy
STEP='GOLD_V3_170_PARALLEL_EXECUTION_CONTRACT_PACKET_AUDIT_ONLY'
SELECTED_VARIANT='PARALLEL_SKIP_ALL_ON_BUCKET_CONFLICT'

def load_csv(path:Path)->pd.DataFrame:
    return pd.read_csv(path,encoding='utf-8-sig',low_memory=False) if path.exists() else pd.DataFrame()

def read_json(path:Path)->dict:
    try:
        return json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
    except Exception:
        return {}

def save_csv(df:pd.DataFrame,path:Path)->None:
    path.parent.mkdir(parents=True,exist_ok=True)
    df.to_csv(path,index=False,encoding='utf-8-sig')

def pick_variant(metrics:pd.DataFrame,name:str)->dict:
    if metrics.empty or 'variant' not in metrics.columns:
        return {}
    hit=metrics[metrics['variant'].astype(str).eq(name)]
    if hit.empty:
        return {}
    row=hit.iloc[0]
    return {k:(None if pd.isna(v) else (float(v) if isinstance(v,float) else (int(v) if hasattr(v,'item') and str(type(v)).find('int')>=0 else v))) for k,v in row.to_dict().items()}

def main()->int:
    t0=time.time()
    ap=argparse.ArgumentParser()
    ap.add_argument('--mt5-files-dir',default='')
    args=ap.parse_args()
    mt5=gy.mt5_files_dir(args.mt5_files_dir)
    root=mt5/'FX_OUTPUTS'/'gold_v3'
    out=root/'170'
    out.mkdir(parents=True,exist_ok=True)
    s169=read_json(root/'169'/'gold_v3_169_summary.json')
    metrics=load_csv(root/'169'/'gold_v3_169_parallel_bucket_variant_metrics.csv')
    conflict=load_csv(root/'169'/'gold_v3_169_conflict_summary.csv')
    packet=load_csv(root/'169'/'gold_v3_169_later_candidate_packet.csv')
    blockers=[]
    if not s169:
        blockers.append({'id':'missing_stage169_summary','path':str(root/'169'/'gold_v3_169_summary.json')})
    if metrics.empty:
        blockers.append({'id':'missing_stage169_variant_metrics','path':str(root/'169'/'gold_v3_169_parallel_bucket_variant_metrics.csv')})
    selected=pick_variant(metrics,SELECTED_VARIANT)
    if not selected:
        blockers.append({'id':'missing_selected_variant','variant':SELECTED_VARIANT})
    status='READY' if not blockers else 'INPUT_MISSING'
    decision='PARALLEL_EXECUTION_CONTRACT_PACKET_READY' if status=='READY' else 'PARALLEL_EXECUTION_CONTRACT_PACKET_INPUT_MISSING'
    later_candidates=[]
    if not packet.empty and 'candidate' in packet.columns:
        for _,r in packet.iterrows():
            later_candidates.append({
                'candidate':str(r.get('candidate','')),
                'description':str(r.get('desc','')),
                'one_full_orders':int(r.get('one_full_orders',0) or 0),
                'one_full_row_pf':float(r.get('one_full_row_pf',0) or 0),
                'one_after_orders':int(r.get('one_after_orders',0) or 0),
                'one_after_sum':float(r.get('one_after_sum',0) or 0),
            })
    conflict_dict={}
    if not conflict.empty:
        conflict_dict=conflict.iloc[0].to_dict()
        for k,v in list(conflict_dict.items()):
            try:
                if pd.isna(v): conflict_dict[k]=None
                elif hasattr(v,'item'): conflict_dict[k]=v.item()
            except Exception:
                pass
    contract={
        'step':STEP,
        'status':status,
        'ready':not blockers,
        'decision':decision,
        'created_at_utc':datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z'),
        'audit_only':True,
        'review_only':True,
        'source_csv_mutated':False,
        'contract_mutated':False,
        'open_asof_allowed':False,
        'candidate_pool_removed':False,
        'f002_exclusion_bypassed':False,
        'final_live_enabled':False,
        'discord_enabled':False,
        'mt5_order_enabled':False,
        'ai_api_enabled':False,
        'selected_variant':SELECTED_VARIANT,
        'execution_model':{
            'current_bucket':{
                'source_policy_key':'density_safe||100||Q0.6',
                'selector':'score desc',
                'side_conflict_policy':'if current bucket rows contain mixed LONG/SHORT at same entry_dt, skip current bucket for that timestamp',
                'max_orders_per_entry_dt':10,
                'lot_per_order':0.01,
                'max_bucket_lot':0.10,
            },
            'later_bucket':{
                'candidates':['P1_D1','P2_DEN','P3_RSI','P4_H1_D1_STRICT','P5_H1UP_CUR'],
                'selector':'one order per candidate per entry_dt, score desc inside each candidate',
                'side_conflict_policy':'if later bucket candidates contain mixed LONG/SHORT at same entry_dt, skip later bucket for that timestamp',
                'max_orders_per_entry_dt':5,
                'lot_per_order':0.01,
                'max_bucket_lot':0.05,
            },
            'bucket_conflict_policy':'if current bucket and later bucket fire opposite sides at same entry_dt, skip all orders for that timestamp',
            'max_total_orders_per_entry_dt_contract':15,
            'max_total_lot_contract':0.15,
            'observed_max_orders_per_entry_dt_from_stage169':selected.get('full_max_orders_per_entry_dt') if selected else None,
            'observed_max_lot_from_stage169':selected.get('max_lot_if_001_per_order') if selected else None,
        },
        'selected_variant_metrics':selected,
        'stage169_conflict_summary':conflict_dict,
        'later_candidate_packet':later_candidates,
        'source_169_decision':s169.get('decision',''),
        'blocker_count':len(blockers),
        'elapsed_seconds':round(time.time()-t0,2),
    }
    (out/'gold_v3_170_parallel_execution_contract_packet.json').write_text(json.dumps(contract|{'blockers':blockers},ensure_ascii=False,indent=2),encoding='utf-8')
    save_csv(pd.DataFrame([{
        'step':STEP,'status':status,'ready':not blockers,'decision':decision,'selected_variant':SELECTED_VARIANT,
        'full_orders':selected.get('full_orders') if selected else None,
        'full_sum':selected.get('full_sum') if selected else None,
        'full_stack_pf':selected.get('full_stack_pf') if selected else None,
        'full_neg_months':selected.get('full_neg_months') if selected else None,
        'after_orders':selected.get('after_orders') if selected else None,
        'after_sum':selected.get('after_sum') if selected else None,
        'after_stack_pf':selected.get('after_stack_pf') if selected else None,
        'max_total_lot_contract':0.15,
        'observed_max_lot':selected.get('max_lot_if_001_per_order') if selected else None,
        'source_csv_mutated':False,'contract_mutated':False,'open_asof_allowed':False,'candidate_pool_removed':False,
        'f002_exclusion_bypassed':False,'final_live_enabled':False,'blocker_count':len(blockers)
    }]),out/'gold_v3_170_decision.csv')
    md=[]
    md.append('# GOLD V3 170 Parallel Execution Contract Packet Audit-Only')
    md.append('')
    md.append(f'- step: `{STEP}`')
    md.append(f'- status: `{status}`')
    md.append(f'- decision: `{decision}`')
    md.append('- audit_only: true')
    md.append('- final/live: disabled')
    md.append('')
    md.append('## Selected execution model')
    md.append('')
    md.append('### Current bucket')
    md.append('- source policy: `density_safe||100||Q0.6`')
    md.append('- selector: score-desc top rows')
    md.append('- max orders per timestamp: 10')
    md.append('- lot per order: 0.01')
    md.append('- max current bucket lot: 0.10')
    md.append('- mixed LONG/SHORT inside current bucket: skip current bucket for that timestamp')
    md.append('')
    md.append('### Later bucket')
    md.append('- candidates: `P1_D1`, `P2_DEN`, `P3_RSI`, `P4_H1_D1_STRICT`, `P5_H1UP_CUR`')
    md.append('- max orders per timestamp: 5')
    md.append('- lot per order: 0.01')
    md.append('- max later bucket lot: 0.05')
    md.append('- mixed LONG/SHORT inside later bucket: skip later bucket for that timestamp')
    md.append('')
    md.append('### Bucket conflict')
    md.append('- If current bucket and later bucket fire opposite sides at the same timestamp, skip all orders for that timestamp.')
    md.append('')
    md.append('## Risk cap')
    md.append('- contract max orders per timestamp: 15')
    md.append('- contract max lot per timestamp: 0.15')
    if selected:
        md.append(f'- observed max orders in Stage169 selected variant: {selected.get("full_max_orders_per_entry_dt")}')
        md.append(f'- observed max lot in Stage169 selected variant: {selected.get("max_lot_if_001_per_order")}')
    md.append('')
    md.append('## Stage169 selected metrics')
    if selected:
        for k in ['full_orders','full_entry_dt','full_sum','full_stack_pf','full_neg_months','full_max_orders_per_entry_dt','full_gt15_entry_dt','after_orders','after_entry_dt','after_sum','after_stack_pf','after_max_orders_per_entry_dt']:
            md.append(f'- {k}: {selected.get(k)}')
    md.append('')
    md.append('## Guardrails')
    md.append('- CSV latest row remains closed only.')
    md.append('- No open/as-of shortcut.')
    md.append('- Candidate pool is not removed.')
    md.append('- F002 exclusion is not bypassed.')
    md.append('- No Discord, MT5 order, AI API, live hook, live evaluator, or final signal is enabled by this packet.')
    (out/'GOLD_V3_170_PARALLEL_EXECUTION_CONTRACT_PACKET_AUDIT_ONLY.md').write_text('\n'.join(md)+'\n',encoding='utf-8')
    lines=[]
    lines.append('GOLD V3 170 PASTE_ME_PARALLEL_EXECUTION_CONTRACT_PACKET_AUDIT')
    for k in ['step','status','ready','decision','selected_variant','source_csv_mutated','contract_mutated','open_asof_allowed','candidate_pool_removed','f002_exclusion_bypassed','final_live_enabled','mt5_order_enabled','blocker_count','elapsed_seconds']:
        lines.append(f'{k}: {contract.get(k)}')
    lines.append('')
    lines.append('EXECUTION_CONTRACT')
    lines.append('current_bucket: density_safe||100||Q0.6, score-desc, max 10 orders, 0.01 lot/order, max 0.10 lot')
    lines.append('later_bucket: P1_D1/P2_DEN/P3_RSI/P4_H1_D1_STRICT/P5_H1UP_CUR, max 5 orders, 0.01 lot/order, max 0.05 lot')
    lines.append('bucket_conflict_policy: current and later opposite sides at same entry_dt -> skip all orders at that timestamp')
    lines.append('internal_mixed_side_policy: mixed LONG/SHORT inside a bucket -> skip that bucket at that timestamp')
    lines.append('max_total_orders_contract: 15')
    lines.append('max_total_lot_contract: 0.15')
    if selected:
        lines.append(f'observed_max_orders_stage169: {selected.get("full_max_orders_per_entry_dt")}')
        lines.append(f'observed_max_lot_stage169: {selected.get("max_lot_if_001_per_order")}')
    lines.append('')
    lines.append('SELECTED_VARIANT_METRICS')
    if selected:
        for k,v in selected.items():
            lines.append(f'{k}: {v}')
    lines.append('')
    lines.append('LATER_CANDIDATE_PACKET')
    lines.append(packet.to_string(index=False) if not packet.empty else 'NO_PACKET')
    lines.append('')
    lines.append('INTERPRETATION')
    lines.append('This packet freezes the audit-only candidate execution contract for the parallel-bucket design. It does not enable live trading, Discord, MT5 order execution, AI API, live hook, live evaluator, or final signal.')
    lines.append('')
    lines.append('BLOCKERS')
    lines.append('NO_BLOCKERS' if not blockers else json.dumps(blockers,ensure_ascii=False,indent=2))
    (out/'paste_me.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({'ready':not blockers,'decision':decision,'paste_me':str(out/'paste_me.txt')},ensure_ascii=False))
    return 0 if not blockers else 2
if __name__=='__main__': raise SystemExit(main())
