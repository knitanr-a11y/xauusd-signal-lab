#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse,csv,hashlib,json,sys,traceback
from datetime import datetime,timezone
from pathlib import Path

STEP='GOLD_V3_31_ALL_ACTIVE_CANDIDATE_UPLIFT_QUEUE_AUDIT_ONLY'
OUT='31_all_active_candidate_uplift_queue_audit_only'
UP='30_all_retained_candidate_set_restore_audit_only'
READY='GOLD_V3_31_ALL_ACTIVE_CANDIDATE_UPLIFT_QUEUE_READY_AUDIT_ONLY'
ERR='GOLD_V3_31_ALL_ACTIVE_CANDIDATE_UPLIFT_QUEUE_EXCEPTION_AUDIT_ONLY'
INV=['input_label','path','required','exists','size_bytes','sha256']
ACTIVE=['packet_row','source_scenario_key','variant_key','active_candidate_role','uplift_diagnostic','trades_per_calendar_day','win_rate_result_positive','profit_factor','negative_months','worst_month_sum','july_profit_factor','july_sum_result_usd','added_filter_ids','added_filter_descriptions']
CONTRACT=['packet_row','active_candidate_role','source_scenario_key','variant_key','filter_order','filter_origin','filter_id','filter_description','filter_family','filter_type','rank_scope','column','values','low','high','entry_pre_known_only']
QUEUE=['queue_order','packet_row','source_scenario_key','variant_key','uplift_priority','uplift_diagnostic','current_profit_factor','current_win_rate','current_trades_per_day','negative_months','july_profit_factor','next_audit_focus']
MAT=['review_key','value','detail']; BLK=['blocker_id','blocker_name','status','detail']

def now(): return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')
def repo_default(): return Path(__file__).resolve().parents[2]
def files_root(repo): return repo.parents[1] if len(repo.parents)>=2 else repo.parent
def roots(repo):
    a=files_root(repo)/'FX_OUTPUTS'/'gold_v3'; b=repo/'Files'/'FX_OUTPUTS'/'gold_v3'; return [a] if a==b else [a,b]
def pick(repo):
    for r in roots(repo):
        if (r/UP/'gold_v3_30_summary.json').exists(): return r,'stage30_root'
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
def f(x,d=0.0):
    try: return float(str(x).strip())
    except Exception: return d
def diag(r):
    bits=[]
    if f(r.get('negative_months'))>0: bits.append('NEGATIVE_MONTHS_TO_PRUNE')
    if f(r.get('worst_month_sum'))<0: bits.append('WORST_MONTH_LOSS_TO_PRUNE')
    if f(r.get('july_profit_factor'))<1.1: bits.append('JULY_PF_UPLIFT_TARGET')
    return ';'.join(bits) if bits else 'CONTINUE_UPLIFT_BASELINE'
def prio(d):
    if 'NEGATIVE_MONTHS' in d or 'WORST_MONTH_LOSS' in d: return 'HIGH'
    if 'JULY_PF' in d: return 'MEDIUM'
    return 'BASELINE_COMPARE'
def focus(d):
    if 'NEGATIVE_MONTHS' in d: return 'find pre-entry loss features inside negative/worst month segments'
    if 'JULY_PF' in d: return 'find pre-entry filters that improve July PF without removing candidate'
    return 'keep as benchmark while continuing uplift comparison'
def md(x): return str(x).replace('\n',' ').replace('\r',' ').replace('|','/')
def table(rows,cols,limit=80):
    if not rows: return '_No rows._'
    out=['| '+' | '.join(cols)+' |','| '+' | '.join(['---']*len(cols))+' |']
    for r in rows[:limit]: out.append('| '+' | '.join(md(r.get(c,''))[:240] for c in cols)+' |')
    return '\n'.join(out)
def report(summary,active,queue,blk):
    lines=['# GOLD V3 31 all active candidate uplift queue audit-only report','',f"Created UTC: `{summary['created_at_utc']}`",f"Status: `{summary['status']}`",'','## Counts']
    for k in ['active_candidate_rows','uplift_queue_rows','contract_rows','daily_cap_used','switching_used']: lines.append(f"- {k}: `{summary.get(k,'')}`")
    lines+=['','## Active candidate set','',table(active,ACTIVE),'','## Uplift queue','',table(queue,QUEUE),'','## Blockers','',table(blk,BLK),'','## Safety','','Audit-only. All 7 candidates remain active. Diagnostics are uplift targets, not demotion labels.']
    return '\n'.join(lines)
def run(repo):
    root,note=pick(repo.resolve()); d=root/UP; out=root/OUT
    paths={'s30':d/'gold_v3_30_summary.json','set':d/'gold_v3_30_all_retained_candidate_set.csv','contract':d/'gold_v3_30_all_retained_filter_contract.csv'}
    inv_rows=inv(paths)
    if not all(x['exists'] for x in inv_rows): raise RuntimeError('missing inputs')
    s30=rjson(paths['s30']); rows=rcsv(paths['set']); con=rcsv(paths['contract'])
    active=[]; queue=[]
    for r in rows:
        dgn=diag(r)
        a={k:r.get(k,'') for k in ACTIVE if k not in ['active_candidate_role','uplift_diagnostic']}
        a['active_candidate_role']='ACTIVE_CANDIDATE'; a['uplift_diagnostic']=dgn; active.append(a)
        queue.append(dict(queue_order=0,packet_row=r.get('packet_row',''),source_scenario_key=r.get('source_scenario_key',''),variant_key=r.get('variant_key',''),uplift_priority=prio(dgn),uplift_diagnostic=dgn,current_profit_factor=r.get('profit_factor',''),current_win_rate=r.get('win_rate_result_positive',''),current_trades_per_day=r.get('trades_per_calendar_day',''),negative_months=r.get('negative_months',''),july_profit_factor=r.get('july_profit_factor',''),next_audit_focus=focus(dgn)))
    order={'HIGH':0,'MEDIUM':1,'BASELINE_COMPARE':2}
    queue=sorted(queue,key=lambda x:(order.get(x['uplift_priority'],9),-f(x.get('current_profit_factor'))))
    for i,q in enumerate(queue,1): q['queue_order']=i
    contract=[]
    for c in con:
        x={k:c.get(k,'') for k in CONTRACT if k!='active_candidate_role'}; x['active_candidate_role']='ACTIVE_CANDIDATE'; contract.append(x)
    blk=[dict(blocker_id='G3-31-001',blocker_name='inputs',status='CLOSED',detail='Stage30 active source found'),dict(blocker_id='G3-31-002',blocker_name='active set',status='CLOSED' if len(active)==7 else 'OPEN_BLOCKER',detail=f'active rows={len(active)}'),dict(blocker_id='G3-31-003',blocker_name='mode',status='CLOSED',detail='audit-only')]
    mat=[dict(review_key='status',value=READY,detail='all retained rows converted to active candidates'),dict(review_key='active_candidate_rows',value=len(active),detail='should remain 7'),dict(review_key='watchlist_rows',value=0,detail='no watchlist role used'),dict(review_key='diagnostics_are_demotions',value=False,detail='diagnostics only guide uplift pruning'),dict(review_key='daily_cap_used',value=False,detail='not used'),dict(review_key='switching_used',value=False,detail='not used')]
    summary=dict(created_at_utc=now(),step=STEP,status=READY,selected_gold_v3_output_root=str(root),path_resolution_note=note,stage30_status=s30.get('status',''),active_candidate_rows=len(active),uplift_queue_rows=len(queue),contract_rows=len(contract),watchlist_rows=0,daily_cap_used=False,switching_used=False,month_filter_used=False,review_scope='all candidates active; diagnostics for uplift only')
    wcsv(out/'gold_v3_31_input_inventory.csv',inv_rows,INV); wcsv(out/'gold_v3_31_all_active_candidate_set.csv',active,ACTIVE); wcsv(out/'gold_v3_31_all_active_filter_contract.csv',contract,CONTRACT); wcsv(out/'gold_v3_31_uplift_queue.csv',queue,QUEUE); wcsv(out/'gold_v3_31_review_matrix.csv',mat,MAT); wcsv(out/'gold_v3_31_blocker_matrix.csv',blk,BLK); wjson(out/'gold_v3_31_summary.json',summary); (out/'GOLD_V3_31_ALL_ACTIVE_CANDIDATE_UPLIFT_QUEUE_AUDIT_ONLY_REPORT.md').write_text(report(summary,active,queue,blk),encoding='utf-8')
    print(json.dumps({'status':READY,'active_candidate_rows':len(active),'watchlist_rows':0,'output_dir':str(out)},ensure_ascii=False,indent=2)); return 0
def fail(repo,e):
    root,note=pick(repo.resolve()); out=root/OUT; out.mkdir(parents=True,exist_ok=True); wjson(out/'gold_v3_31_summary.json',dict(created_at_utc=now(),step=STEP,status=ERR,blocked_reason=f'{e.__class__.__name__}: {e}',path_resolution_note=note)); (out/'gold_v3_31_exception.txt').write_text(traceback.format_exc(),encoding='utf-8')
def main(argv=None):
    ap=argparse.ArgumentParser(); ap.add_argument('--repo-root',default=''); a=ap.parse_args(argv); repo=Path(a.repo_root).resolve() if a.repo_root else repo_default()
    try: return run(repo)
    except Exception as e: fail(repo,e); print(traceback.format_exc(),file=sys.stderr); return 1
if __name__=='__main__': raise SystemExit(main())
