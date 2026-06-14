#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse,json,os,time,urllib.request
from datetime import datetime,timedelta,timezone
from pathlib import Path
import gold_v3_107gy_light_non_calendar_subfilter_search_audit as gy

STEP='GOLD_V3_115B_QUEUE_SENDER_LOCAL_ENV'
READY='GOLD_V3_115B_QUEUE_SENDER_LOCAL_ENV_READY'
BLOCKED='GOLD_V3_115B_QUEUE_SENDER_LOCAL_ENV_BLOCKED'
ENV_KEYS=['GOLD_V3_DISCORD_WEBHOOK_URL','DISCORD_WEBHOOK_URL','DISCORD_WEBHOOK','GOLD_DISCORD_WEBHOOK_URL']

def jst(): return datetime.now(timezone(timedelta(hours=9)))
def log(s): print(f"[{datetime.now().strftime('%H:%M:%S')}] {s}",flush=True)
def jd(p,d=None):
    if d is None: d={}
    if not p.exists(): return d
    try: return json.loads(p.read_text(encoding='utf-8'))
    except Exception: return d
def jw(p,o): p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(o,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
def app(p,o):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('a',encoding='utf-8') as f: f.write(json.dumps(o,ensure_ascii=False,default=str)+'\n')
def read_env_file(p):
    d={}
    if not p.exists(): return d
    for line in p.read_text(encoding='utf-8',errors='ignore').splitlines():
        s=line.strip()
        if not s or s.startswith('#') or '=' not in s: continue
        k,v=s.split('=',1); d[k.strip()]=v.strip().strip('"').strip("'")
    return d
def find_endpoint(repo_root,mt5,override=''):
    candidates=[]
    if override: candidates.append(Path(override))
    candidates += [repo_root/'.env', repo_root/'config'/'.env', mt5/'.env', mt5/'config'/'.env']
    env=dict(os.environ); used=[]
    for p in candidates:
        if p.exists(): env.update(read_env_file(p)); used.append(str(p))
    for k in ENV_KEYS:
        if env.get(k): return k,env[k],used
    return '', '', used
def sleep_to(sec):
    n=datetime.now(); t=n.replace(second=sec,microsecond=0)
    if t<=n: t+=timedelta(minutes=1)
    return max(0,(t-n).total_seconds())
def month(base,dt): return base/dt.strftime('%Y-%m')
def post(url,content,timeout=10):
    body=json.dumps({'content':content},ensure_ascii=False).encode('utf-8')
    req=urllib.request.Request(url,data=body,headers={'Content-Type':'application/json','User-Agent':'gold-v3-queue-sender'},method='POST')
    with urllib.request.urlopen(req,timeout=timeout) as r:
        return int(r.status)
def iter_queue(root):
    q=root/'115a'/'queue'
    if not q.exists(): return []
    files=sorted(q.rglob('*.jsonl'))
    rows=[]
    for p in files:
        for i,line in enumerate(p.read_text(encoding='utf-8',errors='ignore').splitlines(),1):
            if not line.strip(): continue
            try:
                o=json.loads(line); o['_file']=str(p); o['_line']=i; rows.append(o)
            except Exception: pass
    return rows
def run_once(root,repo_root,mt5,args,state):
    out=root/'115b'; cur=out/'current'; st=out/'state'; journal=out/'journal'
    for d in [cur,st,journal]: d.mkdir(parents=True,exist_ok=True)
    key,url,used=find_endpoint(repo_root,mt5,args.env_file)
    rows=iter_queue(root); dt=jst(); ymd=dt.strftime('%Y-%m-%d')
    sent=0; skipped=0; errors=0; last={}
    for o in rows:
        qid=str(o.get('queue_id') or o.get('key') or f"{o.get('_file')}:{o.get('_line')}")
        if qid in state.get('sent_ids',[]): skipped+=1; continue
        content=str(o.get('content') or '\n'.join([f"GOLD V3 DEMO ALERT",f"symbol: {o.get('symbol','XAUUSD')}",f"side: {o.get('side','')}",f"entry_dt: {o.get('entry_dt','')}",f"entry_price: {o.get('entry_price','')}",f"tp: {o.get('tp','')}",f"sl: {o.get('sl','')}",f"monitor_state: {o.get('monitor_state','')}",f"reason: {o.get('reason','')}"]))
        result={'processed_at_jst':dt.isoformat(),'queue_id':qid,'env_key_name':key,'action':'PENDING'}
        if not url:
            result['action']='SKIPPED_NO_ENDPOINT'; skipped+=1
        elif args.no_send:
            result['action']='DRY_RUN_NO_SEND'; skipped+=1
        else:
            try:
                status=post(url,content,args.timeout); result['action']='SENT'; result['http_status']=status; sent+=1
                state.setdefault('sent_ids',[]).append(qid); state['last_sent_at_jst']=dt.isoformat()
            except Exception as e:
                result['action']='SEND_ERROR'; result['error']=str(e); errors+=1
        app(month(journal,dt)/f'gold_v3_115b_sender_{ymd}.jsonl',result); last=result
    if len(state.get('sent_ids',[]))>5000: state['sent_ids']=state['sent_ids'][-5000:]
    summary={'checked_at_jst':dt.isoformat(),'queue_rows':len(rows),'sent':sent,'skipped':skipped,'errors':errors,'env_key_found':bool(key),'env_key_name':key,'last_result':last}
    jw(cur/'latest_sender_result.json',summary); jw(st/'sender_state.json',state); return summary,state
def write_paste(root,summary,blockers,args):
    out=root/'115b'; lines=['GOLD V3 115B PASTE_ME_QUEUE_SENDER_LOCAL_ENV',f"status: {summary['status']}",f"ready: {str(summary['ready']).lower()}",f"loop_mode: {args.loop}",f"target_second: {args.target_second}",f"env_key_found: {summary.get('env_key_found')}",f"env_key_name: {summary.get('env_key_name','')}",f"sent: {summary.get('sent',0)}",f"skipped: {summary.get('skipped',0)}",f"errors: {summary.get('errors',0)}",'secret_printed: false','source_csv_mutated: false','contract_mutated: false','open_asof_allowed: false','blocker_count: '+str(len(blockers)),'','KEY_METRICS']+[f'{k}: {v}' for k,v in summary.items()]+['','BLOCKERS','NO_BLOCKERS' if not blockers else json.dumps(blockers,ensure_ascii=False)]
    (out/'paste_me.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
def main():
    t0=time.time(); ap=argparse.ArgumentParser(); ap.add_argument('--mt5-files-dir',default=''); ap.add_argument('--env-file',default=''); ap.add_argument('--loop',action='store_true'); ap.add_argument('--target-second',type=int,default=5); ap.add_argument('--no-send',action='store_true'); ap.add_argument('--timeout',type=int,default=10)
    args=ap.parse_args(); repo_root=Path(__file__).resolve().parents[2]; mt5=gy.mt5_files_dir(args.mt5_files_dir); root=mt5/'FX_OUTPUTS'/'gold_v3'; out=root/'115b'; out.mkdir(parents=True,exist_ok=True)
    log(STEP+' START'); blockers=[]
    if not (root/'115a').exists(): blockers.append({'blocker_id':'missing_115a_folder'})
    state=jd(out/'state'/'sender_state.json',{'sent_ids':[]})
    last={}
    if not blockers:
        while True:
            last,state=run_once(root,repo_root,mt5,args,state); log(f"queue_rows={last.get('queue_rows')} sent={last.get('sent')} skipped={last.get('skipped')} errors={last.get('errors')}")
            if not args.loop: break
            time.sleep(sleep_to(args.target_second))
    status=READY if not blockers else BLOCKED
    summary={'step':STEP,'status':status,'ready':not blockers,'decision':'QUEUE_SENDER_READY' if not blockers else 'QUEUE_SENDER_BLOCKED','created_at_utc':datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z'),'output_dir':str(out),'elapsed_seconds':round(time.time()-t0,2),'source_csv_mutated':False,'contract_mutated':False,'open_asof_allowed':False}|last
    jw(out/'gold_v3_115b_summary.json',summary|{'blockers':blockers}); write_paste(root,summary,blockers,args); print(json.dumps({'status':status,'ready':not blockers,'paste_me':str(out/'paste_me.txt')},ensure_ascii=False,indent=2)); return 0 if not blockers else 2
if __name__=='__main__': raise SystemExit(main())
