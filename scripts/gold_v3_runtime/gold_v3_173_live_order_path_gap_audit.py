#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse,json,time
from datetime import datetime,timezone
from pathlib import Path
import pandas as pd
import gold_v3_107gy_light_non_calendar_subfilter_search_audit as gy
STEP='GOLD_V3_173_LIVE_ORDER_PATH_GAP_AUDIT_ONLY'

def js(p:Path)->dict:
    try: return json.loads(p.read_text(encoding='utf-8')) if p.exists() else {}
    except Exception: return {}
def csv_exists(p:Path)->bool: return p.exists() and p.stat().st_size>0
def save(df,p): p.parent.mkdir(parents=True,exist_ok=True); df.to_csv(p,index=False,encoding='utf-8-sig')

def main()->int:
    t0=time.time(); ap=argparse.ArgumentParser(); ap.add_argument('--mt5-files-dir',default=''); args=ap.parse_args()
    root=gy.mt5_files_dir(args.mt5_files_dir)/'FX_OUTPUTS'/'gold_v3'; out=root/'173'; out.mkdir(parents=True,exist_ok=True)
    s170=js(root/'170'/'gold_v3_170_parallel_execution_contract_packet.json')
    s171=js(root/'171'/'gold_v3_171_summary.json')
    s172=js(root/'172'/'gold_v3_172_summary.json')
    checks=[]; blockers=[]
    def add(name,ready,detail,blocker=True):
        checks.append({'component':name,'ready':bool(ready),'blocker':bool(blocker and not ready),'detail':detail})
        if blocker and not ready: blockers.append({'id':name,'detail':detail})
    add('parallel_execution_contract',bool(s170 and s170.get('decision')=='PARALLEL_EXECUTION_CONTRACT_PACKET_READY'),s170.get('decision','missing'))
    add('preflight_passed',bool(s171 and s171.get('blocker_count',1)==0),s171.get('decision','missing'))
    add('review_dashboard_ready',bool(s172 and s172.get('decision')=='REVIEW_DASHBOARD_READY'),s172.get('decision','missing'),False)
    # These are intentionally checked as missing unless implemented later.
    add('live_signal_generator_from_closed_csv',False,'MISSING: must compute current_bucket and later_bucket from latest closed CSV/features, not from historical ledger')
    add('live_signal_to_order_queue_csv',False,'MISSING: must write stable signal queue with bucket/candidate/side/lot/tp/sl/magic/comment')
    add('mt5_order_bridge_disabled_by_default',False,'MISSING: must implement MT5 bridge with explicit live-enable switch, kill switch, max lot checks, duplicate prevention')
    add('real_trade_ledger_dashboard',False,'MISSING: must read actual closed deals/trade log and update live performance without rerunning historical 172')
    items=[
      {'next_stage':'174','name':'LIVE_SIGNAL_GENERATOR_DRY_RUN','purpose':'closed CSV -> current/later bucket signals, no MT5 order'},
      {'next_stage':'175','name':'MT5_ORDER_BRIDGE_DRY_RUN','purpose':'signal queue -> simulated order ledger, duplicate/lot/conflict checks'},
      {'next_stage':'176','name':'LIVE_TRADE_LEDGER_DASHBOARD','purpose':'actual or simulated trades -> live performance dashboard'},
      {'next_stage':'177','name':'MT5_REAL_ORDER_GATED_BRIDGE','purpose':'only after explicit final approval, real MT5 order path with kill switch'},
    ]
    save(pd.DataFrame(checks),out/'gold_v3_173_live_order_path_checks.csv')
    save(pd.DataFrame(items),out/'gold_v3_173_next_implementation_sequence.csv')
    status='BLOCKED' if blockers else 'READY'
    decision='LIVE_ORDER_PATH_REQUIRES_RUNTIME_IMPLEMENTATION' if blockers else 'LIVE_ORDER_PATH_READY'
    summary={'step':STEP,'status':status,'ready':not blockers,'decision':decision,'created_at_utc':datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z'),'output_dir':str(out),'audit_only':True,'review_only':True,'user_intent':'move toward MT5 order execution and live performance tracking','current_state':'historical execution contract is ready, but live signal generator and MT5 bridge are not implemented yet','source_csv_mutated':False,'contract_mutated':False,'open_asof_allowed':False,'candidate_pool_removed':False,'f002_exclusion_bypassed':False,'final_live_enabled':False,'mt5_order_enabled':False,'discord_enabled':False,'blocker_count':len(blockers),'elapsed_seconds':round(time.time()-t0,2)}
    (out/'gold_v3_173_summary.json').write_text(json.dumps(summary|{'blockers':blockers,'checks':checks,'next_items':items},ensure_ascii=False,indent=2),encoding='utf-8')
    save(pd.DataFrame([summary]),out/'gold_v3_173_decision.csv')
    lines=['GOLD V3 173 PASTE_ME_LIVE_ORDER_PATH_GAP_AUDIT']+[f'{k}: {v}' for k,v in summary.items()]+['','LIVE_ORDER_PATH_CHECKS',pd.DataFrame(checks).to_string(index=False),'','NEXT_IMPLEMENTATION_SEQUENCE',pd.DataFrame(items).to_string(index=False),'','INTERPRETATION','Historical contract and dashboard are ready, but MT5 real execution must not be wired to the historical ledger. Next implement a closed-CSV live signal generator, then a dry-run order queue, then a live performance ledger, then a gated real MT5 bridge.','','BLOCKERS',json.dumps(blockers,ensure_ascii=False,indent=2) if blockers else 'NO_BLOCKERS']
    (out/'paste_me.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({'ready':not blockers,'decision':decision,'paste_me':str(out/'paste_me.txt')},ensure_ascii=False))
    return 0
if __name__=='__main__': raise SystemExit(main())
