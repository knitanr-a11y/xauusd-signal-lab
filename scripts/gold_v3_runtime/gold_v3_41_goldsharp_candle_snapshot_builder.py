#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse,csv,json,sys,time,traceback
from datetime import datetime,timezone
from pathlib import Path

STEP='GOLD_V3_41_GOLDSHARP_CANDLE_SNAPSHOT_BUILDER'
OUT='41_goldsharp_candle_snapshot_builder'
READY='GOLD_V3_41_GOLDSHARP_CANDLE_SNAPSHOT_BUILDER_READY'
NO_SIGNAL='GOLD_V3_41_GOLDSHARP_CANDLE_SNAPSHOT_BUILDER_NO_SIGNAL'
BLOCKED='GOLD_V3_41_GOLDSHARP_CANDLE_SNAPSHOT_BUILDER_BLOCKED'
ERR='GOLD_V3_41_GOLDSHARP_CANDLE_SNAPSHOT_BUILDER_EXCEPTION'
SNAP=['packet_row','source_scenario_key','variant_key','source_rank','direction','entry_time_utc','feature_bar_open_utc','entry_price','close','m15_atr28','h4_ret4','jst_weekday','snapshot_status','snapshot_reason']
REV=['review_key','value','detail']

def now_dt(): return datetime.now(timezone.utc)
def now(): return now_dt().replace(microsecond=0).isoformat().replace('+00:00','Z')
def repo_default(): return Path(__file__).resolve().parents[2]
def files_root(repo): return repo.parents[1] if len(repo.parents)>=2 else repo.parent
def root(repo): return files_root(repo)/'FX_OUTPUTS'/'gold_v3'
def wjson(p,o): p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(o,ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf-8')
def wcsv(p,rows,fields):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore'); w.writeheader()
        for r in rows: w.writerow({k:r.get(k,'') for k in fields})
def rcsv(p):
    with p.open('r',encoding='utf-8-sig',newline='') as f: return list(csv.DictReader(f))
def parse_time(s):
    for fmt in ['%Y.%m.%d %H:%M:%S','%Y-%m-%d %H:%M:%S']:
        try: return datetime.strptime(str(s),fmt).replace(tzinfo=timezone.utc)
        except Exception: pass
    try: return datetime.fromisoformat(str(s).replace('Z','+00:00')).astimezone(timezone.utc)
    except Exception: return None
def f(x,d=0.0):
    try: return float(str(x).strip())
    except Exception: return d
def read_candles(path):
    rows=rcsv(path); out=[]
    for r in rows:
        dt=parse_time(r.get('time') or r.get('datetime') or r.get('Time'))
        if not dt: continue
        out.append({'time':dt,'open':f(r.get('open')),'high':f(r.get('high')),'low':f(r.get('low')),'close':f(r.get('close'))})
    out.sort(key=lambda x:x['time'])
    return out
def true_range(row,prev_close): return max(row['high']-row['low'],abs(row['high']-prev_close),abs(row['low']-prev_close))
def atr(rows,n):
    if len(rows)<n+1: return None
    trs=[]
    for i in range(len(rows)-n,len(rows)):
        trs.append(true_range(rows[i],rows[i-1]['close']))
    return sum(trs)/len(trs)
def resample_m5_to_m15(m5):
    buckets={}
    for r in m5:
        minute=(r['time'].minute//15)*15
        key=r['time'].replace(minute=minute,second=0,microsecond=0)
        buckets.setdefault(key,[]).append(r)
    out=[]
    for k in sorted(buckets):
        b=buckets[k]
        out.append({'time':k,'open':b[0]['open'],'high':max(x['high'] for x in b),'low':min(x['low'] for x in b),'close':b[-1]['close']})
    return out
def find_path(repo,name,explicit):
    if explicit: return Path(explicit).expanduser().resolve()
    fr=files_root(repo)
    candidates=[fr/name, repo/name, fr/'MQL5'/'Files'/name, fr/'Files'/name]
    return next((p for p in candidates if p.exists()),candidates[0])
def stage36_root(repo):
    g=root(repo); return g/'36_final_ranked_candidate_contract_audit_only'
def infer_direction(cand,fallback):
    for k in ['direction','side','signal_direction']:
        v=str(cand.get(k,'')).upper().strip()
        if v in ['BUY','SELL','LONG','SHORT','UP','DOWN']:
            return 'BUY' if v in ['BUY','LONG','UP'] else 'SELL'
    fb=str(fallback or '').upper().strip()
    if fb in ['BUY','SELL']: return fb
    return ''
def build_once(args,repo):
    g=root(repo); out=g/OUT; live=g/'live'; live.mkdir(parents=True,exist_ok=True); out.mkdir(parents=True,exist_ok=True)
    m5p=find_path(repo,'goldsharp_m5.csv',args.m5); h1p=find_path(repo,'goldsharp_h1.csv',args.h1); h4p=find_path(repo,'goldsharp_h4.csv',args.h4)
    ranked=stage36_root(repo)/'gold_v3_36_ranked_candidate_contract.csv'
    rows=[]; status=READY; reason='snapshot built'
    if not m5p.exists() or not h1p.exists() or not h4p.exists() or not ranked.exists():
        status=BLOCKED; reason=f'missing input m5={m5p.exists()} h1={h1p.exists()} h4={h4p.exists()} ranked={ranked.exists()}'
    else:
        m5=read_candles(m5p); h4=read_candles(h4p); m15=resample_m5_to_m15(m5)
        a28=atr(m15,28)
        h4ret4=None
        if len(h4)>=5 and h4[-5]['close']!=0: h4ret4=(h4[-1]['close']-h4[-5]['close'])/h4[-5]['close']
        latest=m5[-1] if m5 else None
        if latest is None or a28 is None or h4ret4 is None:
            status=BLOCKED; reason='not enough candle rows for m15_atr28/h4_ret4'
        else:
            jst=(latest['time']+__import__('datetime').timedelta(hours=9)).strftime('%A')
            for cand in rcsv(ranked):
                side=infer_direction(cand,args.fallback_direction)
                if not side:
                    continue
                rows.append({'packet_row':cand.get('packet_row',''),'source_scenario_key':cand.get('source_scenario_key',''),'variant_key':cand.get('variant_key',''),'source_rank':cand.get('rank',''),'direction':side,'entry_time_utc':latest['time'].replace(microsecond=0).isoformat().replace('+00:00','Z'),'feature_bar_open_utc':latest['time'].replace(microsecond=0).isoformat().replace('+00:00','Z'),'entry_price':round(latest['close'],3),'close':round(latest['close'],3),'m15_atr28':round(a28,6),'h4_ret4':round(h4ret4,10),'jst_weekday':jst,'snapshot_status':'CANDIDATE_FEATURE_ROW','snapshot_reason':'built from goldsharp candles; direction requires contract/fallback'})
            if not rows:
                status=NO_SIGNAL; reason='no direction available in ranked contract; set --fallback-direction BUY or SELL only for controlled testing'
    snap=live/'gold_v3_live_candidate_snapshot.csv'
    tmp=snap.with_suffix('.tmp')
    wcsv(tmp,rows,SNAP); tmp.replace(snap)
    review=[{'review_key':'status','value':status,'detail':reason},{'review_key':'m5_path','value':str(m5p),'detail':'input'},{'review_key':'h1_path','value':str(h1p),'detail':'input currently inventoried'},{'review_key':'h4_path','value':str(h4p),'detail':'input'},{'review_key':'snapshot_rows','value':len(rows),'detail':str(snap)}]
    wcsv(out/'gold_v3_41_review_matrix.csv',review,REV)
    summary={'created_at_utc':now(),'step':STEP,'status':status,'reason':reason,'m5_path':str(m5p),'h1_path':str(h1p),'h4_path':str(h4p),'snapshot_path':str(snap),'snapshot_rows':len(rows),'fallback_direction':args.fallback_direction,'warning':'This builder does not reconstruct historical entry rules; it only creates live feature rows for Stage37. Do not use fallback direction without manual approval.'}
    wjson(out/'gold_v3_41_summary.json',summary)
    print(json.dumps(summary,ensure_ascii=False,indent=2)); return 0 if status in [READY,NO_SIGNAL] else 2
def next_tick(delay):
    t=time.time(); m=int(t//60)*60; target=m+delay
    if t>=target: target=m+60+delay
    return float(target)
def sleep_until(ts):
    while True:
        left=ts-time.time()
        if left<=0: return
        time.sleep(min(left,0.25))
def main(argv=None):
    ap=argparse.ArgumentParser(); ap.add_argument('--repo-root',default=''); ap.add_argument('--m5',default=''); ap.add_argument('--h1',default=''); ap.add_argument('--h4',default=''); ap.add_argument('--fallback-direction',default=''); ap.add_argument('--delay-seconds',type=int,default=3); ap.add_argument('--loop',action='store_true'); ap.add_argument('--run-once',action='store_true')
    args=ap.parse_args(argv); repo=Path(args.repo_root).resolve() if args.repo_root else repo_default()
    if not args.loop and not args.run_once: args.run_once=True
    try:
        while True:
            t=next_tick(args.delay_seconds); sleep_until(t); rc=build_once(args,repo)
            if args.run_once and not args.loop: return rc
    except KeyboardInterrupt: return 0
    except Exception as e:
        out=root(repo)/OUT; out.mkdir(parents=True,exist_ok=True); wjson(out/'gold_v3_41_summary.json',{'created_at_utc':now(),'step':STEP,'status':ERR,'blocked_reason':f'{e.__class__.__name__}: {e}'}); (out/'gold_v3_41_exception.txt').write_text(traceback.format_exc(),encoding='utf-8'); print(traceback.format_exc(),file=sys.stderr); return 1
if __name__=='__main__': raise SystemExit(main())
