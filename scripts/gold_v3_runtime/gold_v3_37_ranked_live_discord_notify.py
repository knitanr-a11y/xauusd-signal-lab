#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse,csv,hashlib,json,os,sys,traceback,urllib.request
from datetime import datetime,timezone
from pathlib import Path
from typing import Any
import pandas as pd

STEP='GOLD_V3_37_RANKED_LIVE_DISCORD_NOTIFY'
OUT='37_ranked_live_discord_notify'
UP36='36_final_ranked_candidate_contract_audit_only'
READY='GOLD_V3_37_RANKED_LIVE_DISCORD_NOTIFY_READY'
NO_SIGNAL='GOLD_V3_37_RANKED_LIVE_DISCORD_NOTIFY_NO_SIGNAL'
BLOCKED='GOLD_V3_37_RANKED_LIVE_DISCORD_NOTIFY_BLOCKED'
ERR='GOLD_V3_37_RANKED_LIVE_DISCORD_NOTIFY_EXCEPTION'
INV=['input_label','path','required','exists','size_bytes','sha256']
SIG=['selected','dispatch_status','rank','ranked_candidate_name','packet_row','source_scenario_key','variant_key','direction','entry_time_utc','entry_time_jst','entry_price','tp_price','sl_price','symbol','matched_filters','blocked_filters','discord_status','dedupe_key']
EVT=['event_time_utc','level','event_key','detail']; BLK=['blocker_id','blocker_name','status','detail']; REV=['review_key','value','detail']

def now(): return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')
def repo_default(): return Path(__file__).resolve().parents[2]
def files_root(repo): return repo.parents[1] if len(repo.parents)>=2 else repo.parent
def roots(repo):
    a=files_root(repo)/'FX_OUTPUTS'/'gold_v3'; b=repo/'Files'/'FX_OUTPUTS'/'gold_v3'; return [a] if a==b else [a,b]
def pick(repo):
    for r in roots(repo):
        if (r/UP36/'gold_v3_36_summary.json').exists(): return r,'stage36_root'
    return roots(repo)[0],'fallback_root_no_stage36'
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()
def inv(paths): return [dict(input_label=k,path=str(p),required=req,exists=p.exists(),size_bytes=p.stat().st_size if p.exists() else '',sha256=sha(p) if p.exists() else '') for k,p,req in paths]
def rcsv(p):
    with p.open('r',encoding='utf-8-sig',newline='') as f: return list(csv.DictReader(f))
def rjson(p): return json.loads(p.read_text(encoding='utf-8'))
def wcsv(p,rows,fields):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore'); w.writeheader()
        for r in rows: w.writerow({k:r.get(k,'') for k in fields})
def wjson(p,o): p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(o,ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf-8')
def f(x,d=0.0):
    try:
        if pd.isna(x): return d
        return float(str(x).strip())
    except Exception: return d
def sval(row,*names,default=''):
    for n in names:
        v=row.get(n)
        if v is not None and str(v).strip() and str(v).strip().lower()!='nan': return str(v).strip()
    return default
def to_utc(x):
    dt=pd.to_datetime(x,utc=True,errors='coerce')
    return '' if pd.isna(dt) else dt.isoformat().replace('+00:00','Z')
def to_jst(x):
    dt=pd.to_datetime(x,utc=True,errors='coerce')
    return '' if pd.isna(dt) else (dt+pd.Timedelta(hours=9)).strftime('%Y-%m-%d %H:%M:%S JST')
def jst_wday(x):
    dt=pd.to_datetime(x,utc=True,errors='coerce')
    return '' if pd.isna(dt) else (dt+pd.Timedelta(hours=9)).day_name()
def direction(x):
    s=str(x or '').strip().upper()
    if s in ['BUY','LONG','UP']: return 'BUY'
    if s in ['SELL','SHORT','DOWN']: return 'SELL'
    return ''
def live_path(root,explicit):
    if explicit: return Path(explicit).expanduser().resolve()
    c=[root/'live'/'gold_v3_live_candidate_snapshot.csv',root/'live'/'gold_v3_live_feature_snapshot.csv',root/'gold_v3_live_candidate_snapshot.csv',root/'gold_v3_live_feature_snapshot.csv']
    return next((p for p in c if p.exists()),c[0])
def state_load(p):
    if not p.exists(): return {'sent_keys':[]}
    try: return rjson(p)
    except Exception: return {'sent_keys':[]}
def state_save(p,s): s['updated_at_utc']=now(); wjson(p,s)
def row_matches(row,cand):
    if sval(row,'packet_row'): return sval(row,'packet_row')==str(cand.get('packet_row',''))
    if sval(row,'source_scenario_key'): return sval(row,'source_scenario_key')==str(cand.get('source_scenario_key',''))
    if sval(row,'variant_key'): return sval(row,'variant_key')==str(cand.get('variant_key',''))
    return False
def filter_blocks(row,flt,entry_time):
    cid=str(flt.get('cut_id','')); col=str(flt.get('feature_column',''))
    if cid=='GLOBAL_SATURDAY':
        wd=sval(row,'jst_weekday') or jst_wday(row.get(entry_time,''))
        return wd=='Saturday',f'{cid}: jst_weekday={wd}'
    rs=str(flt.get('rank_scope','ALL'))
    if rs not in ['','ALL']:
        sr=sval(row,'source_rank')
        if sr and int(f(sr,-999))!=int(f(rs,-1)): return False,f'{cid}: rank_scope={rs} source_rank={sr} no-scope'
    if col not in row: return False,f'{cid}: missing {col}'
    if str(flt.get('filter_type',''))=='categorical':
        vals=[v for v in str(flt.get('values','')).split(';') if v]
        hit=str(row.get(col,'')) in vals
        return hit,f'{cid}: {col}={row.get(col,"")} values={vals}'
    low=f(flt.get('low'),float('-inf')); high=f(flt.get('high'),float('inf')); val=f(row.get(col),float('nan'))
    hit=pd.notna(val) and val>=low and val<high
    return hit,f'{cid}: {low} <= {col}={val} < {high}'
def calc_tp_sl(row,side,price,tp_default,sl_default):
    tp=sval(row,'tp_price','take_profit_price'); sl=sval(row,'sl_price','stop_loss_price')
    if tp and sl: return f(tp),f(sl)
    tpd=f(sval(row,'tp_distance_usd','tp_usd','tp_distance',default=str(tp_default)),tp_default); sld=f(sval(row,'sl_distance_usd','sl_usd','sl_distance',default=str(sl_default)),sl_default)
    return (round(price+tpd,3),round(price-sld,3)) if side=='BUY' else (round(price-tpd,3),round(price+sld,3))
def discord_payload(sig):
    title=f"GOLD {sig['direction']}"
    desc='\n'.join([f"rank: {sig['rank']} {sig['ranked_candidate_name']}",f"entry time (JST): {sig['entry_time_jst']}",f"entry price: {sig['entry_price']}",f"TP/SL: {sig['tp_price']} / {sig['sl_price']}"])
    return {'username':'GOLD V3','embeds':[{'title':title,'description':desc}]}
def post(url,obj):
    data=json.dumps(obj,ensure_ascii=False).encode('utf-8')
    req=urllib.request.Request(url,data=data,headers={'Content-Type':'application/json'},method='POST')
    with urllib.request.urlopen(req,timeout=10) as r: return f'HTTP_{r.status}'
def ev(level,key,detail): return {'event_time_utc':now(),'level':level,'event_key':key,'detail':detail}
def by_packet(rows):
    d={}
    for r in rows: d.setdefault(str(r.get('packet_row','')),[]).append(r)
    return d
def run(args):
    repo=Path(args.repo_root).resolve() if args.repo_root else repo_default(); root,note=pick(repo); out=root/OUT
    ranked=root/UP36/'gold_v3_36_ranked_candidate_contract.csv'; filters=root/UP36/'gold_v3_36_final_filter_contract.csv'; summ=root/UP36/'gold_v3_36_summary.json'; live=live_path(root,args.live_snapshot)
    inv_rows=inv([('stage36_summary',summ,True),('ranked_candidate_contract',ranked,True),('final_filter_contract',filters,True),('live_snapshot',live,True)])
    events=[]; sigs=[]; blockers=[]
    if not all(x['exists'] for x in inv_rows):
        summary={'created_at_utc':now(),'step':STEP,'status':BLOCKED,'selected_gold_v3_output_root':str(root),'path_resolution_note':note,'blocked_reason':'missing Stage36 output or live snapshot','discord_enabled_requested':bool(args.enable_discord)}
        blockers=[{'blocker_id':'G3-37-001','blocker_name':'required inputs','status':'OPEN_BLOCKER','detail':'Stage36 outputs and live snapshot required'}]
        out.mkdir(parents=True,exist_ok=True); wcsv(out/'gold_v3_37_input_inventory.csv',inv_rows,INV); wcsv(out/'gold_v3_37_signal_dispatch_log.csv',sigs,SIG); wcsv(out/'gold_v3_37_event_log.csv',events,EVT); wcsv(out/'gold_v3_37_blocker_matrix.csv',blockers,BLK); wjson(out/'gold_v3_37_summary.json',summary); print(json.dumps(summary,ensure_ascii=False,indent=2)); return 2
    rank_rows=rcsv(ranked); filt_by=by_packet(rcsv(filters)); live_rows=rcsv(live); stage36=rjson(summ)
    state_path=out/'gold_v3_37_live_state.json'; state=state_load(state_path); sent=set(state.get('sent_keys',[])); candidates=[]
    for row in live_rows:
        for cand in rank_rows:
            if not row_matches(row,cand): continue
            packet=str(cand.get('packet_row','')); side=direction(sval(row,'direction','side','signal_direction'))
            et=to_utc(row.get(args.entry_time_column) or row.get('entry_time_utc') or row.get('feature_bar_open_utc'))
            price=f(sval(row,'entry_price','price','close','bid','ask'),0.0)
            if not side or not et or price<=0:
                events.append(ev('WARN','MISSING_REQUIRED_SIGNAL_FIELD',f'packet={packet} direction={side} entry_time={et} price={price}'))
                continue
            matched=[]; blocked=[]; blocked_flag=False
            for flt in filt_by.get(packet,[]):
                hit,detail=filter_blocks(row,flt,args.entry_time_column)
                if hit: blocked.append(detail); blocked_flag=True
                else: matched.append(detail)
            tp,sl=calc_tp_sl(row,side,price,args.default_tp_usd,args.default_sl_usd)
            sig={'selected':False,'dispatch_status':'BLOCKED_BY_FILTER' if blocked_flag else 'CANDIDATE_HIT','rank':cand.get('rank'),'ranked_candidate_name':cand.get('ranked_candidate_name'),'packet_row':packet,'source_scenario_key':cand.get('source_scenario_key'),'variant_key':cand.get('variant_key'),'direction':side,'entry_time_utc':et,'entry_time_jst':to_jst(et),'entry_price':round(price,3),'tp_price':tp,'sl_price':sl,'symbol':args.symbol,'matched_filters':' / '.join(matched),'blocked_filters':' / '.join(blocked),'discord_status':'NOT_SENT','dedupe_key':f'{et}|{side}|{packet}'}
            if blocked_flag: sigs.append(sig)
            else: candidates.append(sig)
    candidates=sorted(candidates,key=lambda x:int(f(x.get('rank'),999999)))
    used=set(); selected=[]
    for sig in candidates:
        bd=f"{sig['entry_time_utc']}|{sig['direction']}"
        if not args.notify_all_hits and bd in used: sig['dispatch_status']='SKIPPED_LOWER_RANK_SAME_BAR_DIRECTION'; sigs.append(sig); continue
        if sig['dedupe_key'] in sent and not args.resend_duplicate: sig['dispatch_status']='SKIPPED_DUPLICATE'; sigs.append(sig); continue
        sig['selected']=True; sig['dispatch_status']='SELECTED_FOR_DISCORD'; selected.append(sig); used.add(bd); sigs.append(sig)
    wh=args.discord_webhook_url or os.environ.get(args.discord_webhook_env,'')
    for sig in selected:
        if args.enable_discord:
            if not wh: sig['discord_status']='BLOCKED_NO_WEBHOOK'; events.append(ev('WARN','DISCORD_NO_WEBHOOK',sig['dedupe_key']))
            else:
                try: sig['discord_status']=post(wh,discord_payload(sig))
                except Exception as e: sig['discord_status']=f'DISCORD_FAILED:{e.__class__.__name__}:{e}'
        else: sig['discord_status']='DISABLED'
        sent.add(sig['dedupe_key'])
    state['sent_keys']=sorted(sent)[-500:]; state_save(state_path,state)
    status=READY if selected else NO_SIGNAL
    blockers=[{'blocker_id':'G3-37-001','blocker_name':'required inputs','status':'CLOSED','detail':'Stage36 outputs and live snapshot found'},{'blocker_id':'G3-37-002','blocker_name':'duplicate control','status':'CLOSED','detail':'highest-rank-per-bar/direction by default'},{'blocker_id':'G3-37-003','blocker_name':'mt5 direct send','status':'CLOSED_BLOCKED','detail':'direct MT5 execution was not added; Discord notify only'}]
    review=[{'review_key':'status','value':status,'detail':'live candidate snapshot evaluated'},{'review_key':'stage36_status','value':stage36.get('status',''),'detail':'ranked source'},{'review_key':'discord_enabled','value':bool(args.enable_discord),'detail':'Discord flag'},{'review_key':'mt5_direct_send_enabled','value':False,'detail':'not implemented by this script'},{'review_key':'candidate_hits','value':len(candidates),'detail':'unblocked candidate hits'},{'review_key':'selected_dispatches','value':len(selected),'detail':'selected highest-rank signals'}]
    summary={'created_at_utc':now(),'step':STEP,'status':status,'selected_gold_v3_output_root':str(root),'path_resolution_note':note,'live_snapshot_path':str(live),'candidate_hits':len(candidates),'selected_dispatches':len(selected),'discord_enabled':bool(args.enable_discord),'discord_webhook_env':args.discord_webhook_env,'mt5_direct_send_enabled':False,'symbol':args.symbol,'notify_all_hits':bool(args.notify_all_hits),'message_title':'GOLD BUY / GOLD SELL','message_order':'rank -> entry time JST -> entry price -> TP/SL','ai_api_called':False}
    out.mkdir(parents=True,exist_ok=True); wcsv(out/'gold_v3_37_input_inventory.csv',inv_rows,INV); wcsv(out/'gold_v3_37_signal_dispatch_log.csv',sigs,SIG); wcsv(out/'gold_v3_37_event_log.csv',events,EVT); wcsv(out/'gold_v3_37_review_matrix.csv',review,REV); wcsv(out/'gold_v3_37_blocker_matrix.csv',blockers,BLK); wjson(out/'gold_v3_37_summary.json',summary)
    report=['# GOLD V3 37 ranked live Discord notify report','',f"Created UTC: `{summary['created_at_utc']}`",f"Status: `{status}`",'', '## Message format','- Title: `GOLD BUY` or `GOLD SELL`','- Order: rank -> entry time JST -> entry price -> TP/SL','', '## MT5','- Direct MT5 execution is not included in this script.']
    (out/'GOLD_V3_37_RANKED_LIVE_DISCORD_NOTIFY_REPORT.md').write_text('\n'.join(report)+'\n',encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False,indent=2)); return 0
def fail(repo,e):
    root,note=pick(repo.resolve()); out=root/OUT; out.mkdir(parents=True,exist_ok=True); wjson(out/'gold_v3_37_summary.json',{'created_at_utc':now(),'step':STEP,'status':ERR,'blocked_reason':f'{e.__class__.__name__}: {e}','path_resolution_note':note}); (out/'gold_v3_37_exception.txt').write_text(traceback.format_exc(),encoding='utf-8'); print(traceback.format_exc(),file=sys.stderr); return 1
def main(argv=None):
    ap=argparse.ArgumentParser(); ap.add_argument('--repo-root',default=''); ap.add_argument('--live-snapshot',default=''); ap.add_argument('--entry-time-column',default='entry_time_utc'); ap.add_argument('--symbol',default='XAUUSD'); ap.add_argument('--default-tp-usd',type=float,default=10.0); ap.add_argument('--default-sl-usd',type=float,default=5.0); ap.add_argument('--enable-discord',action='store_true'); ap.add_argument('--discord-webhook-env',default='GOLD_V3_DISCORD_WEBHOOK_URL'); ap.add_argument('--discord-webhook-url',default=''); ap.add_argument('--notify-all-hits',action='store_true'); ap.add_argument('--resend-duplicate',action='store_true')
    args=ap.parse_args(argv); repo=Path(args.repo_root).resolve() if args.repo_root else repo_default()
    try: return run(args)
    except Exception as e: return fail(repo,e)
if __name__=='__main__': raise SystemExit(main())
