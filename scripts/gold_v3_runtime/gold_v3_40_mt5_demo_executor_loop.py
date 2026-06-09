#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse,csv,json,sys,time,traceback
from datetime import datetime,timezone
from pathlib import Path
from typing import Any

STEP='GOLD_V3_40_MT5_DEMO_EXECUTOR_LOOP'
OUT='40_mt5_demo_executor_loop'
READY='GOLD_V3_40_MT5_DEMO_EXECUTOR_LOOP_READY'
NO_SIGNAL='GOLD_V3_40_MT5_DEMO_EXECUTOR_LOOP_NO_SIGNAL'
BLOCKED='GOLD_V3_40_MT5_DEMO_EXECUTOR_LOOP_BLOCKED'
ERR='GOLD_V3_40_MT5_DEMO_EXECUTOR_LOOP_EXCEPTION'
RESULT_FIELDS=['result_time_utc','result_time_jst','status','reason','rank','candidate_name','symbol','direction','entry_time_utc','entry_time_jst','entry_price','tp_price','sl_price','volume','dedupe_key']
LOOP_FIELDS=['run_id','scheduled_at_utc','started_at_utc','finished_at_utc','elapsed_seconds','status','reason']

def now_dt(): return datetime.now(timezone.utc)
def now(): return now_dt().replace(microsecond=0).isoformat().replace('+00:00','Z')
def jst(dt): return (dt+__import__('datetime').timedelta(hours=9)).strftime('%Y-%m-%d %H:%M:%S JST')
def repo_default(): return Path(__file__).resolve().parents[2]
def files_root(repo): return repo.parents[1] if len(repo.parents)>=2 else repo.parent
def root(repo): return files_root(repo)/'FX_OUTPUTS'/'gold_v3'
def wjson(p,o): p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(o,ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf-8')
def rjson(p): return json.loads(p.read_text(encoding='utf-8')) if p.exists() else {}
def wcsv_append(p,row,fields):
    p.parent.mkdir(parents=True,exist_ok=True); exists=p.exists()
    with p.open('a',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore')
        if not exists: w.writeheader()
        w.writerow({k:row.get(k,'') for k in fields})
def next_tick(delay):
    t=time.time(); m=int(t//60)*60; target=m+delay
    if t>=target: target=m+60+delay
    return float(target)
def sleep_until(ts):
    while True:
        left=ts-time.time()
        if left<=0: return
        time.sleep(min(left,0.25))
def read_latest_signal(live):
    p=live/'current'/'latest_signal.json'
    return rjson(p),p
def load_state(live):
    p=live/'state'/'dedupe_state.json'
    s=rjson(p) if p.exists() else {}
    s.setdefault('executed_keys',[]); return s,p
def save_state(p,s): s['updated_at_utc']=now(); wjson(p,s)
def daily_path(live,prefix): return live/'logs'/f'{prefix}_{now_dt().strftime("%Y%m%d")}.csv'
def run_once(args,repo,run_id,scheduled):
    g=root(repo); live=g/'live_runtime'; out=g/OUT; out.mkdir(parents=True,exist_ok=True)
    start=now_dt(); sig,sig_path=read_latest_signal(live); state,state_path=load_state(live)
    status=NO_SIGNAL; reason='latest_signal status is not SIGNAL'
    result_row={'result_time_utc':now(),'result_time_jst':jst(now_dt()),'status':status,'reason':reason}
    if not sig_path.exists():
        status=BLOCKED; reason='latest_signal.json not found; run GOLD_V3_39 first and notification loop before MT5 executor'
    elif str(sig.get('status','')).upper() not in ['SIGNAL','SELECTED_FOR_DISCORD','DISCORD_SENT','READY']:
        status=NO_SIGNAL; reason=f"no executable signal status={sig.get('status','')}"
    else:
        key=str(sig.get('dedupe_key',''))
        if not key:
            status=BLOCKED; reason='signal missing dedupe_key'
        elif key in set(state.get('executed_keys',[])):
            status=NO_SIGNAL; reason='duplicate signal already recorded for execution'
        else:
            # This stage intentionally records a demo-execution request/result log only.
            # The actual broker bridge/EA should consume these fields and enforce demo account checks.
            status='PENDING_DEMO_BRIDGE'; reason='queued for external demo MT5 bridge; no Discord result notification'
            state['executed_keys']=(state.get('executed_keys',[])+[key])[-500:]
            save_state(state_path,state)
            for k in ['rank','candidate_name','ranked_candidate_name','symbol','direction','entry_time_utc','entry_time_jst','entry_price','tp_price','sl_price','volume','dedupe_key']:
                if k in sig: result_row[k if k!='ranked_candidate_name' else 'candidate_name']=sig.get(k,'')
    finish=now_dt(); elapsed=(finish-start).total_seconds()
    result_row.update({'status':status,'reason':reason})
    wcsv_append(daily_path(live,'mt5_results'),result_row,RESULT_FIELDS)
    wcsv_append(out/'gold_v3_40_loop_runs.csv',{'run_id':run_id,'scheduled_at_utc':datetime.fromtimestamp(scheduled,tz=timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z'),'started_at_utc':start.replace(microsecond=0).isoformat().replace('+00:00','Z'),'finished_at_utc':finish.replace(microsecond=0).isoformat().replace('+00:00','Z'),'elapsed_seconds':round(elapsed,6),'status':status,'reason':reason},LOOP_FIELDS)
    wjson(live/'current'/'latest_mt5_result.json',result_row)
    summary={'created_at_utc':now(),'step':STEP,'status':READY if status in ['PENDING_DEMO_BRIDGE',NO_SIGNAL] else status,'delay_seconds_after_minute':args.delay_seconds,'mt5_result_discord_notify':False,'result_log_only':True,'last_result':result_row}
    wjson(out/'gold_v3_40_summary.json',summary)
    return status
def main(argv=None):
    ap=argparse.ArgumentParser(); ap.add_argument('--repo-root',default=''); ap.add_argument('--delay-seconds',type=int,default=7); ap.add_argument('--loop',action='store_true'); ap.add_argument('--run-once',action='store_true')
    args=ap.parse_args(argv); repo=Path(args.repo_root).resolve() if args.repo_root else repo_default()
    if not args.loop and not args.run_once: args.run_once=True
    run_id=0
    try:
        while True:
            t=next_tick(args.delay_seconds); sleep_until(t); run_id+=1; run_once(args,repo,run_id,t)
            if args.run_once and not args.loop: return 0
    except KeyboardInterrupt:
        wjson(root(repo)/OUT/'gold_v3_40_summary.json',{'created_at_utc':now(),'step':STEP,'status':'STOPPED_BY_USER'}); return 0
    except Exception as e:
        out=root(repo)/OUT; out.mkdir(parents=True,exist_ok=True); wjson(out/'gold_v3_40_summary.json',{'created_at_utc':now(),'step':STEP,'status':ERR,'blocked_reason':f'{e.__class__.__name__}: {e}'}); (out/'gold_v3_40_exception.txt').write_text(traceback.format_exc(),encoding='utf-8'); print(traceback.format_exc(),file=sys.stderr); return 1
if __name__=='__main__': raise SystemExit(main())
