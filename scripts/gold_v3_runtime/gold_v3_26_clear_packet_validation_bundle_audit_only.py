#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse,csv,hashlib,json,sys,traceback
from datetime import datetime,timezone
from pathlib import Path

STEP='GOLD_V3_26_CLEAR_PACKET_VALIDATION_BUNDLE_AUDIT_ONLY'
OUT='26_clear_packet_validation_bundle_audit_only'
UP='25_retained_packet_robustness_review_audit_only'
READY='GOLD_V3_26_CLEAR_PACKET_VALIDATION_BUNDLE_READY_AUDIT_ONLY'
ERR='GOLD_V3_26_CLEAR_PACKET_VALIDATION_BUNDLE_EXCEPTION_AUDIT_ONLY'
INV=['input_label','path','required','exists','size_bytes','sha256']
BUNDLE=['packet_row','proposal_tier','source_scenario_key','variant_key','review_action','trades_per_calendar_day','win_rate_result_positive','profit_factor','negative_months','worst_month','worst_month_sum','july_profit_factor','july_sum_result_usd','max_drawdown_usd','max_consecutive_losses','added_filter_ids','robustness_flags','bundle_role','bundle_note']
MON=['packet_row','proposal_tier','source_scenario_key','variant_key','entry_month','rows','trades_per_calendar_day','win_rate_result_positive','profit_factor','sum_result_usd','month_bucket','is_july','is_worst_month']
TRACE=['packet_row','source_scenario_key','variant_key','filter_origin','filter_id','filter_description','filter_family','filter_type','rank_scope','column','values','low','high','entry_pre_known_only']
MAT=['review_key','value','detail']; BLK=['blocker_id','blocker_name','status','detail']

def now(): return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')
def repo_default(): return Path(__file__).resolve().parents[2]
def files_root(repo): return repo.parents[1] if len(repo.parents)>=2 else repo.parent
def roots(repo):
    a=files_root(repo)/'FX_OUTPUTS'/'gold_v3'; b=repo/'Files'/'FX_OUTPUTS'/'gold_v3'; return [a] if a==b else [a,b]
def pick(repo):
    for r in roots(repo):
        if (r/UP/'gold_v3_25_summary.json').exists(): return r,'stage25_root'
    return roots(repo)[0],'fallback_root'
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()
def rcsv(p):
    with p.open('r',encoding='utf-8-sig',newline='') as f: return list(csv.DictReader(f))
def rjson(p): return json.loads(p.read_text(encoding='utf-8'))
def wcsv(p,rows,fields):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore'); w.writeheader()
        for r in rows: w.writerow({k:r.get(k,'') for k in fields})
def wjson(p,o): p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(o,ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf-8')
def inv(paths): return [dict(input_label=k,path=str(p),required=True,exists=p.exists(),size_bytes=p.stat().st_size if p.exists() else '',sha256=sha(p) if p.exists() else '') for k,p in paths.items()]
def md(x): return str(x).replace('\n',' ').replace('\r',' ').replace('|','/')
def table(rows,cols,limit=80):
    if not rows: return '_No rows._'
    out=['| '+' | '.join(cols)+' |','| '+' | '.join(['---']*len(cols))+' |']
    for r in rows[:limit]: out.append('| '+' | '.join(md(r.get(c,''))[:240] for c in cols)+' |')
    return '\n'.join(out)
def report(summary,clear,watch,blk):
    lines=['# GOLD V3 26 clear packet validation bundle audit-only report','',f"Created UTC: `{summary['created_at_utc']}`",f"Status: `{summary['status']}`",'','## Counts']
    for k in ['source_rows','clear_bundle_rows','watchlist_rows','clear_monthly_rows','clear_trace_rows','daily_cap_used','switching_used']: lines.append(f"- {k}: `{summary.get(k,'')}`")
    lines+=['','## Clear validation bundle','',table(clear,['packet_row','proposal_tier','source_scenario_key','review_action','trades_per_calendar_day','win_rate_result_positive','profit_factor','negative_months','july_profit_factor','bundle_role']),'','## Watchlist','',table(watch,['packet_row','proposal_tier','source_scenario_key','review_action','trades_per_calendar_day','win_rate_result_positive','profit_factor','negative_months','july_profit_factor','robustness_flags']),'','## Blockers','',table(blk,BLK),'','## Safety','','Audit-only bundle creation. No switching, no month filter, no daily cap.']
    return '\n'.join(lines)
def run(repo):
    root,note=pick(repo.resolve()); d=root/UP; out=root/OUT
    paths={'summary':d/'gold_v3_25_summary.json','review':d/'gold_v3_25_retained_robustness_review.csv','monthly':d/'gold_v3_25_retained_monthly_review.csv','trace':d/'gold_v3_25_filter_traceability_review.csv'}
    inv_rows=inv(paths)
    if not all(x['exists'] for x in inv_rows): raise RuntimeError('missing inputs')
    s25=rjson(paths['summary']); rows=rcsv(paths['review']); monthly=rcsv(paths['monthly']); trace=rcsv(paths['trace'])
    clear=[]; watch=[]
    for r in rows:
        role='VALIDATION_BUNDLE' if r.get('robustness_flags')=='CLEAR' else 'WATCHLIST'
        item={k:r.get(k,'') for k in BUNDLE if k not in ['bundle_role','bundle_note']}
        item['bundle_role']=role; item['bundle_note']='clear robustness row' if role=='VALIDATION_BUNDLE' else 'kept for review but not clear'
        (clear if role=='VALIDATION_BUNDLE' else watch).append(item)
    clear_ids={str(x['packet_row']) for x in clear}
    mon=[x for x in monthly if str(x.get('packet_row','')) in clear_ids]
    tr=[x for x in trace if str(x.get('packet_row','')) in clear_ids]
    blk=[dict(blocker_id='G3-26-001',blocker_name='inputs',status='CLOSED',detail='Stage25 review files found'),dict(blocker_id='G3-26-002',blocker_name='clear bundle',status='CLOSED' if clear else 'OPEN_BLOCKER',detail='clear rows selected'),dict(blocker_id='G3-26-003',blocker_name='mode',status='CLOSED',detail='audit-only')]
    mat=[dict(review_key='status',value=READY,detail='clear bundle ready'),dict(review_key='clear_bundle_rows',value=len(clear),detail='clear rows'),dict(review_key='watchlist_rows',value=len(watch),detail='flagged rows'),dict(review_key='daily_cap_used',value=False,detail='not used'),dict(review_key='switching_used',value=False,detail='not used')]
    summary=dict(created_at_utc=now(),step=STEP,status=READY,selected_gold_v3_output_root=str(root),path_resolution_note=note,stage25_status=s25.get('status',''),source_rows=len(rows),clear_bundle_rows=len(clear),watchlist_rows=len(watch),clear_monthly_rows=len(mon),clear_trace_rows=len(tr),daily_cap_used=False,switching_used=False,month_filter_used=False,review_scope='clear packet bundle only')
    wcsv(out/'gold_v3_26_input_inventory.csv',inv_rows,INV); wcsv(out/'gold_v3_26_clear_validation_bundle.csv',clear,BUNDLE); wcsv(out/'gold_v3_26_watchlist_packet.csv',watch,BUNDLE); wcsv(out/'gold_v3_26_clear_monthly_bundle.csv',mon,MON); wcsv(out/'gold_v3_26_clear_filter_traceability.csv',tr,TRACE); wcsv(out/'gold_v3_26_review_matrix.csv',mat,MAT); wcsv(out/'gold_v3_26_blocker_matrix.csv',blk,BLK); wjson(out/'gold_v3_26_summary.json',summary); (out/'GOLD_V3_26_CLEAR_PACKET_VALIDATION_BUNDLE_AUDIT_ONLY_REPORT.md').write_text(report(summary,clear,watch,blk),encoding='utf-8')
    print(json.dumps({'status':READY,'clear_bundle_rows':len(clear),'watchlist_rows':len(watch),'output_dir':str(out)},ensure_ascii=False,indent=2)); return 0
def fail(repo,e):
    root,note=pick(repo.resolve()); out=root/OUT; out.mkdir(parents=True,exist_ok=True); wjson(out/'gold_v3_26_summary.json',dict(created_at_utc=now(),step=STEP,status=ERR,blocked_reason=f'{e.__class__.__name__}: {e}',path_resolution_note=note)); (out/'gold_v3_26_exception.txt').write_text(traceback.format_exc(),encoding='utf-8')
def main(argv=None):
    ap=argparse.ArgumentParser(); ap.add_argument('--repo-root',default=''); a=ap.parse_args(argv); repo=Path(a.repo_root).resolve() if a.repo_root else repo_default()
    try: return run(repo)
    except Exception as e: fail(repo,e); print(traceback.format_exc(),file=sys.stderr); return 1
if __name__=='__main__': raise SystemExit(main())
