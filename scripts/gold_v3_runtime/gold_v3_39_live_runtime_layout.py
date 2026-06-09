#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse,csv,json,sys,traceback
from datetime import datetime,timezone
from pathlib import Path
from typing import Any

STEP='GOLD_V3_39_LIVE_RUNTIME_LAYOUT'
OUT='39_live_runtime_layout'
READY='GOLD_V3_39_LIVE_RUNTIME_LAYOUT_READY'
ERR='GOLD_V3_39_LIVE_RUNTIME_LAYOUT_EXCEPTION'
INV=['path_key','path','status','purpose']
REV=['review_key','value','detail']
BLK=['blocker_id','blocker_name','status','detail']

def now(): return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')
def repo_default(): return Path(__file__).resolve().parents[2]
def files_root(repo): return repo.parents[1] if len(repo.parents)>=2 else repo.parent
def root(repo): return files_root(repo)/'FX_OUTPUTS'/'gold_v3'
def wjson(p,o): p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(o,ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf-8')
def wcsv(p,rows,fields):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore'); w.writeheader()
        for r in rows: w.writerow({k:r.get(k,'') for k in fields})
def ensure_empty_csv(p,fields):
    if p.exists(): return
    wcsv(p,[],fields)
def run(args):
    repo=Path(args.repo_root).resolve() if args.repo_root else repo_default(); g=root(repo); live=g/'live_runtime'; current=live/'current'; logs=live/'logs'; state=live/'state'; archive=live/'archive'; out=g/OUT
    inv=[]
    for key,path,purpose in [('base',live,'live runtime root'),('current',current,'latest small files'),('logs',logs,'daily append logs'),('state',state,'dedupe and lock state'),('archive',archive,'old retained files')]:
        existed=path.exists(); path.mkdir(parents=True,exist_ok=True); inv.append({'path_key':key,'path':str(path),'status':'exists' if existed else 'created','purpose':purpose})
    config={'created_at_utc':now(),'layout_version':'GOLD_V3_LIVE_RUNTIME_V1','current_dir':str(current),'logs_dir':str(logs),'state_dir':str(state),'archive_dir':str(archive),'discord_signal_notify':True,'discord_mt5_result_notify':False,'mt5_result_log_only':True,'no_signal_detail_log':False,'no_signal_summary_counter_only':True,'daily_log_keep_days':int(args.keep_days),'compact_loop_max_rows':int(args.max_loop_rows),'notify_and_mt5_same_bat':False,'recommended_notify_bat':'GOLD_V3_38_LIVE_MINUTE_LOOP_DISCORD.bat','recommended_mt5_bat':'GOLD_V3_40_MT5_DEMO_EXECUTOR_LOOP.bat'}
    wjson(live/'gold_v3_live_runtime_config.json',config)
    wjson(current/'latest_status.json',{'updated_at_utc':now(),'status':'INITIALIZED','no_signal_count_today':0,'signal_count_today':0,'error_count_today':0})
    wjson(current/'latest_signal.json',{'updated_at_utc':now(),'status':'NO_SIGNAL_YET'})
    ensure_empty_csv(current/'latest_discord_dispatch.csv',['updated_at_utc','status','title','rank','entry_time_jst','entry_price','tp_price','sl_price','dedupe_key'])
    ensure_empty_csv(current/'latest_mt5_result.csv',['updated_at_utc','status','symbol','direction','volume','entry_price','tp_price','sl_price','ticket','retcode','dedupe_key'])
    wjson(state/'dedupe_state.json',{'updated_at_utc':now(),'sent_signal_keys':[],'executed_keys':[]})
    readme='''# GOLD V3 live runtime layout\n\n- current/: overwrite latest status/signal files.\n- logs/: daily append logs for later verification.\n- state/: dedupe and lock state.\n- NO_SIGNAL detail is not appended every minute.\n- MT5 results are log-only and are not posted to Discord.\n- Discord notification BAT and MT5 demo BAT are separated.\n'''
    (live/'GOLD_V3_LIVE_RUNTIME_LAYOUT.md').write_text(readme,encoding='utf-8')
    review=[{'review_key':'status','value':READY,'detail':'layout initialized'},{'review_key':'mt5_result_discord_notify','value':False,'detail':'results remain log-only'},{'review_key':'no_signal_detail_log','value':False,'detail':'counter only'},{'review_key':'notify_and_mt5_same_bat','value':False,'detail':'separate BATs'}]
    blockers=[{'blocker_id':'G3-39-001','blocker_name':'layout','status':'CLOSED','detail':'live_runtime folders ready'},{'blocker_id':'G3-39-002','blocker_name':'log policy','status':'CLOSED','detail':'current overwrite + daily append logs'}]
    summary={'created_at_utc':now(),'step':STEP,'status':READY,'live_runtime_root':str(live),'current_dir':str(current),'logs_dir':str(logs),'state_dir':str(state),'archive_dir':str(archive),'mt5_result_discord_notify':False,'mt5_result_log_only':True,'no_signal_detail_log':False,'daily_log_keep_days':int(args.keep_days),'compact_loop_max_rows':int(args.max_loop_rows)}
    wcsv(out/'gold_v3_39_path_inventory.csv',inv,INV); wcsv(out/'gold_v3_39_review_matrix.csv',review,REV); wcsv(out/'gold_v3_39_blocker_matrix.csv',blockers,BLK); wjson(out/'gold_v3_39_summary.json',summary)
    (out/'GOLD_V3_39_LIVE_RUNTIME_LAYOUT_REPORT.md').write_text('# GOLD V3 39 live runtime layout\n\nStatus: `'+READY+'`\n\nMT5 results are log-only. Discord result notification is disabled.\n',encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False,indent=2)); return 0
def fail(repo,e):
    g=root(repo); out=g/OUT; out.mkdir(parents=True,exist_ok=True); wjson(out/'gold_v3_39_summary.json',{'created_at_utc':now(),'step':STEP,'status':ERR,'blocked_reason':f'{e.__class__.__name__}: {e}'}); (out/'gold_v3_39_exception.txt').write_text(traceback.format_exc(),encoding='utf-8'); print(traceback.format_exc(),file=sys.stderr); return 1
def main(argv=None):
    ap=argparse.ArgumentParser(); ap.add_argument('--repo-root',default=''); ap.add_argument('--keep-days',type=int,default=14); ap.add_argument('--max-loop-rows',type=int,default=10080); args=ap.parse_args(argv); repo=Path(args.repo_root).resolve() if args.repo_root else repo_default()
    try: return run(args)
    except Exception as e: return fail(repo,e)
if __name__=='__main__': raise SystemExit(main())
