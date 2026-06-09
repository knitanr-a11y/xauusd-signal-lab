#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse,csv,json,os,sys,time,traceback,urllib.request
from datetime import datetime,timezone
from pathlib import Path

STEP='GOLD_V3_40_MT5_DEMO_EXECUTOR_LOOP'
OUT='40_mt5_demo_executor_loop'
READY='GOLD_V3_40_MT5_DEMO_EXECUTOR_LOOP_READY'
NO_SIGNAL='GOLD_V3_40_MT5_DEMO_EXECUTOR_LOOP_NO_SIGNAL'
BLOCKED='GOLD_V3_40_MT5_DEMO_EXECUTOR_LOOP_BLOCKED'
ERR='GOLD_V3_40_MT5_DEMO_EXECUTOR_LOOP_EXCEPTION'
RESULT_FIELDS=['result_time_utc','result_time_jst','status','reason','rank','candidate_name','symbol','direction','entry_time_utc','entry_time_jst','entry_price','tp_price','sl_price','volume','ticket','retcode','dedupe_key']
LOOP_FIELDS=['run_id','scheduled_at_utc','started_at_utc','finished_at_utc','elapsed_seconds','status','reason','error_discord_status']

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
def webhook(args): return args.discord_webhook_url or os.environ.get(args.discord_webhook_env,'')
def post_error(args,title,detail):
    if not args.notify_errors_to_discord: return 'ERROR_NOTIFY_DISABLED'
    url=webhook(args)
    if not url: return 'ERROR_NOTIFY_BLOCKED_NO_WEBHOOK'
    payload={'username':'GOLD V3','embeds':[{'title':title,'description':detail[-3500:]}]}
    data=json.dumps(payload,ensure_ascii=False).encode('utf-8')
    req=urllib.request.Request(url,data=data,headers={'Content-Type':'application/json'},method='POST')
    with urllib.request.urlopen(req,timeout=10) as r: return f'HTTP_{r.status}'
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
def fnum(x,d=0.0):
    try: return float(str(x).strip())
    except Exception: return d

def send_demo_order(args,sig):
    try:
        import MetaTrader5 as mt5
    except Exception as e:
        return 'MT5_IMPORT_FAILED',str(e),'',''
    if not mt5.initialize(): return 'MT5_INITIALIZE_FAILED',str(mt5.last_error()),'',''
    try:
        acc=mt5.account_info()
        if acc is None: return 'MT5_ACCOUNT_INFO_FAILED',str(mt5.last_error()),'',''
        if getattr(acc,'trade_mode',None)!=getattr(mt5,'ACCOUNT_TRADE_MODE_DEMO',0):
            return 'MT5_BLOCKED_NON_DEMO_ACCOUNT',f"trade_mode={getattr(acc,'trade_mode',None)} login={getattr(acc,'login','')}",'',''
        symbol=str(sig.get('symbol') or args.symbol)
        if not mt5.symbol_select(symbol, True): return 'MT5_SYMBOL_SELECT_FAILED',str(mt5.last_error()),'',''
        tick=mt5.symbol_info_tick(symbol)
        if tick is None: return 'MT5_TICK_FAILED',str(mt5.last_error()),'',''
        side=str(sig.get('direction','')).upper()
        typ=mt5.ORDER_TYPE_BUY if side=='BUY' else mt5.ORDER_TYPE_SELL
        price=tick.ask if side=='BUY' else tick.bid
        req={'action':mt5.TRADE_ACTION_DEAL,'symbol':symbol,'volume':fnum(sig.get('volume'),args.volume),'type':typ,'price':float(price),'sl':fnum(sig.get('sl_price')),'tp':fnum(sig.get('tp_price')),'deviation':args.deviation,'magic':args.magic,'comment':f"GOLDV3_{sig.get('rank','')}_{sig.get('packet_row','')}"[:31],'type_time':mt5.ORDER_TIME_GTC,'type_filling':mt5.ORDER_FILLING_IOC}
        res=mt5.order_send(req)
        if res is None: return 'MT5_ORDER_SEND_NONE',str(mt5.last_error()),'',''
        ret=str(getattr(res,'retcode',''))
        ticket=str(getattr(res,'order','') or getattr(res,'deal',''))
        if getattr(res,'retcode',None)==mt5.TRADE_RETCODE_DONE: return 'MT5_ORDER_DONE','order done',ticket,ret
        return 'MT5_ORDER_REJECTED',str(res),ticket,ret
    finally:
        mt5.shutdown()

def run_once(args,repo,run_id,scheduled):
    g=root(repo); live=g/'live_runtime'; out=g/OUT; out.mkdir(parents=True,exist_ok=True)
    start=now_dt(); sig,sig_path=read_latest_signal(live); state,state_path=load_state(live)
    status=NO_SIGNAL; reason='latest_signal status is not SIGNAL'; ticket=''; retcode=''; err_notify=''
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
        elif args.enable_mt5_demo_order:
            status,reason,ticket,retcode=send_demo_order(args,sig)
            if status=='MT5_ORDER_DONE':
                state['executed_keys']=(state.get('executed_keys',[])+[key])[-500:]; save_state(state_path,state)
        else:
            status='PENDING_DEMO_BRIDGE'; reason='direct MT5 disabled; external demo bridge can consume latest_signal; no Discord result notification'
            state['executed_keys']=(state.get('executed_keys',[])+[key])[-500:]; save_state(state_path,state)
        for k in ['rank','candidate_name','ranked_candidate_name','symbol','direction','entry_time_utc','entry_time_jst','entry_price','tp_price','sl_price','volume','dedupe_key']:
            if k in sig: result_row[k if k!='ranked_candidate_name' else 'candidate_name']=sig.get(k,'')
    finish=now_dt(); elapsed=(finish-start).total_seconds()
    result_row.update({'status':status,'reason':reason,'ticket':ticket,'retcode':retcode})
    wcsv_append(daily_path(live,'mt5_results'),result_row,RESULT_FIELDS)
    if status not in [NO_SIGNAL,'PENDING_DEMO_BRIDGE','MT5_ORDER_DONE']:
        try: err_notify=post_error(args,'GOLD V3 MT5 ERROR',f'status: {status}\nreason: {reason}\nsignal: {json.dumps(sig,ensure_ascii=False)[:2500]}')
        except Exception as e: err_notify=f'ERROR_NOTIFY_FAILED:{e.__class__.__name__}:{e}'
    wcsv_append(out/'gold_v3_40_loop_runs.csv',{'run_id':run_id,'scheduled_at_utc':datetime.fromtimestamp(scheduled,tz=timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z'),'started_at_utc':start.replace(microsecond=0).isoformat().replace('+00:00','Z'),'finished_at_utc':finish.replace(microsecond=0).isoformat().replace('+00:00','Z'),'elapsed_seconds':round(elapsed,6),'status':status,'reason':reason,'error_discord_status':err_notify},LOOP_FIELDS)
    wjson(live/'current'/'latest_mt5_result.json',result_row)
    summary={'created_at_utc':now(),'step':STEP,'status':READY if status in ['PENDING_DEMO_BRIDGE',NO_SIGNAL,'MT5_ORDER_DONE'] else status,'delay_seconds_after_minute':args.delay_seconds,'mt5_result_discord_notify':False,'error_discord_notify':bool(args.notify_errors_to_discord),'result_log_only':True,'direct_mt5_enabled':bool(args.enable_mt5_demo_order),'last_result':result_row}
    wjson(out/'gold_v3_40_summary.json',summary)
    return status

def main(argv=None):
    ap=argparse.ArgumentParser(); ap.add_argument('--repo-root',default=''); ap.add_argument('--delay-seconds',type=int,default=7); ap.add_argument('--loop',action='store_true'); ap.add_argument('--run-once',action='store_true'); ap.add_argument('--symbol',default='XAUUSD'); ap.add_argument('--volume',type=float,default=0.01); ap.add_argument('--deviation',type=int,default=30); ap.add_argument('--magic',type=int,default=370040); ap.add_argument('--enable-mt5-demo-order',action='store_true'); ap.add_argument('--discord-webhook-env',default='GOLD_V3_DISCORD_WEBHOOK_URL'); ap.add_argument('--discord-webhook-url',default=''); ap.add_argument('--notify-errors-to-discord',action='store_true',default=True); ap.add_argument('--no-error-discord',dest='notify_errors_to_discord',action='store_false')
    args=ap.parse_args(argv); repo=Path(args.repo_root).resolve() if args.repo_root else repo_default()
    if not args.loop and not args.run_once: args.run_once=True
    run_id=0
    try:
        while True:
            t=next_tick(args.delay_seconds); sleep_until(t); run_id+=1; run_once(args,repo,run_id,t)
            if args.run_once and not args.loop: return 0
    except KeyboardInterrupt:
        try: post_error(args,'GOLD V3 MT5 LOOP STOPPED','MT5 demo executor loop was stopped by KeyboardInterrupt.')
        except Exception: pass
        wjson(root(repo)/OUT/'gold_v3_40_summary.json',{'created_at_utc':now(),'step':STEP,'status':'STOPPED_BY_USER'}); return 0
    except Exception as e:
        out=root(repo)/OUT; out.mkdir(parents=True,exist_ok=True)
        try: post_error(args,'GOLD V3 MT5 LOOP EXCEPTION',f'{e.__class__.__name__}: {e}\n{traceback.format_exc()}')
        except Exception: pass
        wjson(out/'gold_v3_40_summary.json',{'created_at_utc':now(),'step':STEP,'status':ERR,'blocked_reason':f'{e.__class__.__name__}: {e}'}); (out/'gold_v3_40_exception.txt').write_text(traceback.format_exc(),encoding='utf-8'); print(traceback.format_exc(),file=sys.stderr); return 1
if __name__=='__main__': raise SystemExit(main())
