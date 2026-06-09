#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse,csv,hashlib,json,sys,traceback
from datetime import datetime,timezone
from pathlib import Path

STEP='GOLD_V3_24_FURTHER_PRUNED_DECISION_PROPOSAL_AUDIT_ONLY'
UP='23_further_pruned_shortlist_human_intake_audit_only'
OUT='24_further_pruned_decision_proposal_audit_only'
READY='GOLD_V3_24_FURTHER_PRUNED_DECISION_PROPOSAL_READY_AUDIT_ONLY'
ERR='GOLD_V3_24_FURTHER_PRUNED_DECISION_PROPOSAL_EXCEPTION_AUDIT_ONLY'
FIELDS=['packet_row','proposal_tier','source_scenario_key','variant_key','review_action','trades_per_calendar_day','win_rate_result_positive','profit_factor','negative_months','worst_month_sum','july_profit_factor','july_sum_result_usd','added_filter_ids','added_filter_descriptions','proposal_reason']
INV=['input_label','path','required','exists','size_bytes','sha256']
TRACE=['packet_row','source_scenario_key','variant_key','filter_origin','filter_id','filter_description','filter_family','filter_type','rank_scope','column','values','low','high','entry_pre_known_only']
DEC=['decision_key','value','detail']; BLK=['blocker_id','blocker_name','status','detail']

def now(): return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')
def repo_default(): return Path(__file__).resolve().parents[2]
def files_root(repo): return repo.parents[1] if len(repo.parents)>=2 else repo.parent
def roots(repo):
    a=files_root(repo)/'FX_OUTPUTS'/'gold_v3'; b=repo/'Files'/'FX_OUTPUTS'/'gold_v3'; return [a] if a==b else [a,b]
def pick_root(repo):
    for r in roots(repo):
        if (r/UP/'gold_v3_23_summary.json').exists(): return r,'stage23_root'
    return roots(repo)[0],'fallback_root'
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()
def rcsv(p):
    with p.open('r',encoding='utf-8-sig',newline='') as f: return list(csv.DictReader(f))
def wcsv(p,rows,fields):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore'); w.writeheader()
        for r in rows: w.writerow({k:r.get(k,'') for k in fields})
def wjson(p,o): p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(o,ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf-8')
def inv(paths): return [dict(input_label=k,path=str(p),required=True,exists=p.exists(),size_bytes=p.stat().st_size if p.exists() else '',sha256=sha(p) if p.exists() else '') for k,p in paths.items()]
def classify(row,seen):
    src=row.get('source_scenario_key',''); seen[src]=seen.get(src,0)+1; n=seen[src]
    if src=='R1_ONLY_CD60_PRUNE_111' and n==1: return 'PRIMARY','NEXT','top R1_ONLY_CD60_PRUNE_111'
    if src=='R1_ONLY_CD60_PRUNE_115' and n==1: return 'COMPARE_R1','COMPARE','top sibling R1_ONLY_CD60_PRUNE_115'
    if src=='R1_ONLY_CD60_PRUNE_015': return 'JULY_REVIEW','KEEP','explicit user-retained review row'
    if src.startswith('MAIN_R1_R2') and n==1: return 'COMPARE_MAIN','COMPARE','top MAIN comparison row'
    return 'DROP_DUPLICATE','DROP','redundant sibling row'
def make_report(summary,rows,keep,drop,blk):
    cols=['packet_row','proposal_tier','source_scenario_key','variant_key','review_action','trades_per_calendar_day','win_rate_result_positive','profit_factor','negative_months','july_profit_factor','proposal_reason']
    def tab(rs):
        if not rs: return '_No rows._'
        out=['| '+' | '.join(cols)+' |','| '+' | '.join(['---']*len(cols))+' |']
        for r in rs: out.append('| '+' | '.join(str(r.get(c,''))[:240].replace('|','/') for c in cols)+' |')
        return '\n'.join(out)
    b='\n'.join(f"- {k}: `{summary.get(k,'')}`" for k in ['status','packet_rows','keep_rows','drop_rows','daily_cap_used','switching_used'])
    return '# GOLD V3 24 further-pruned decision proposal audit-only report\n\n## Counts\n'+b+'\n\n## Proposal\n\n'+tab(rows)+'\n\n## Kept\n\n'+tab(keep)+'\n\n## Dropped as duplicate\n\n'+tab(drop)+'\n'
def run(repo):
    root,note=pick_root(repo.resolve()); d=root/UP; out=root/OUT
    paths={'summary':d/'gold_v3_23_summary.json','packet':d/'gold_v3_23_compact_decision_packet.csv','trace':d/'gold_v3_23_filter_traceability_packet.csv','group':d/'gold_v3_23_source_group_review.csv'}
    inv_rows=inv(paths)
    if not all(x['exists'] for x in inv_rows): raise RuntimeError('missing input')
    p=rcsv(paths['packet']); t=rcsv(paths['trace']); seen={}; rows=[]; keep=[]; drop=[]
    for r in p:
        tier,act,why=classify(r,seen)
        item={k:r.get(k,'') for k in ['packet_row','source_scenario_key','variant_key','trades_per_calendar_day','win_rate_result_positive','profit_factor','negative_months','worst_month_sum','july_profit_factor','july_sum_result_usd','added_filter_ids','added_filter_descriptions']}
        item.update(proposal_tier=tier,review_action=act,proposal_reason=why)
        rows.append(item); (drop if tier=='DROP_DUPLICATE' else keep).append(item)
    keep_ids={str(x['packet_row']) for x in keep}; trace_keep=[x for x in t if str(x.get('packet_row','')) in keep_ids]
    summary=dict(created_at_utc=now(),step=STEP,status=READY,selected_gold_v3_output_root=str(root),path_resolution_note=note,packet_rows=len(rows),keep_rows=len(keep),drop_rows=len(drop),primary_rows=sum(1 for x in keep if x['proposal_tier']=='PRIMARY'),compare_rows=sum(1 for x in keep if 'COMPARE' in x['proposal_tier']),july_rows=sum(1 for x in keep if x['proposal_tier']=='JULY_REVIEW'),daily_cap_used=False,switching_used=False,month_filter_used=False,review_scope='packet review only')
    blk=[dict(blocker_id='G3-24-001',blocker_name='inputs',status='CLOSED',detail='stage23 files found'),dict(blocker_id='G3-24-002',blocker_name='packet',status='CLOSED',detail='proposal written'),dict(blocker_id='G3-24-003',blocker_name='mode',status='CLOSED',detail='review only')]
    dec=[dict(decision_key='status',value=READY,detail='review packet ready'),dict(decision_key='primary_row',value='packet 1',detail='top R1_ONLY_CD60_PRUNE_111'),dict(decision_key='daily_cap_used',value=False,detail='not used'),dict(decision_key='switching_used',value=False,detail='not used')]
    wcsv(out/'gold_v3_24_input_inventory.csv',inv_rows,INV); wcsv(out/'gold_v3_24_decision_proposal.csv',rows,FIELDS); wcsv(out/'gold_v3_24_retained_packet.csv',keep,FIELDS); wcsv(out/'gold_v3_24_rejected_redundant_packet.csv',drop,FIELDS); wcsv(out/'gold_v3_24_filter_traceability_retained.csv',trace_keep,TRACE); wcsv(out/'gold_v3_24_decision_matrix.csv',dec,DEC); wcsv(out/'gold_v3_24_blocker_matrix.csv',blk,BLK); wjson(out/'gold_v3_24_summary.json',summary); (out/'GOLD_V3_24_FURTHER_PRUNED_DECISION_PROPOSAL_AUDIT_ONLY_REPORT.md').write_text(make_report(summary,rows,keep,drop,blk),encoding='utf-8')
    print(json.dumps({'status':READY,'keep_rows':len(keep),'drop_rows':len(drop),'output_dir':str(out)},ensure_ascii=False,indent=2)); return 0
def fail(repo,e):
    root,note=pick_root(repo.resolve()); out=root/OUT; out.mkdir(parents=True,exist_ok=True); wjson(out/'gold_v3_24_summary.json',dict(created_at_utc=now(),step=STEP,status=ERR,blocked_reason=f'{e.__class__.__name__}: {e}',path_resolution_note=note)); (out/'gold_v3_24_exception.txt').write_text(traceback.format_exc(),encoding='utf-8')
def main(argv=None):
    ap=argparse.ArgumentParser(); ap.add_argument('--repo-root',default=''); a=ap.parse_args(argv); repo=Path(a.repo_root).resolve() if a.repo_root else repo_default()
    try: return run(repo)
    except Exception as e: fail(repo,e); print(traceback.format_exc(),file=sys.stderr); return 1
if __name__=='__main__': raise SystemExit(main())
