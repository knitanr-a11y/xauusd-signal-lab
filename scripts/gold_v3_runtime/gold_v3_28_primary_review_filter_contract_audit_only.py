#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse,csv,hashlib,json,sys,traceback
from datetime import datetime,timezone
from pathlib import Path

STEP='GOLD_V3_28_PRIMARY_REVIEW_FILTER_CONTRACT_AUDIT_ONLY'
OUT='28_primary_review_filter_contract_audit_only'
UP27='27_clear_bundle_pairwise_review_audit_only'
UP26='26_clear_packet_validation_bundle_audit_only'
READY='GOLD_V3_28_PRIMARY_REVIEW_FILTER_CONTRACT_READY_AUDIT_ONLY'
ERR='GOLD_V3_28_PRIMARY_REVIEW_FILTER_CONTRACT_EXCEPTION_AUDIT_ONLY'
PRIMARY='R1_ONLY_CD60_PRUNE_111'
INV=['input_label','path','required','exists','size_bytes','sha256']
CONTRACT=['contract_role','source_scenario_key','variant_key','filter_order','filter_origin','filter_id','filter_description','filter_family','filter_type','rank_scope','column','values','low','high','entry_pre_known_only']
MET=['source_scenario_key','variant_key','profit_factor','win_rate_result_positive','trades_per_calendar_day','negative_months','july_profit_factor','bundle_role','rank_order','rank_reason']
CMP=['rank_order','bundle_role','source_scenario_key','variant_key','profit_factor','win_rate_result_positive','trades_per_calendar_day','negative_months','july_profit_factor','rank_reason']
MAT=['review_key','value','detail']; BLK=['blocker_id','blocker_name','status','detail']

def now(): return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')
def repo_default(): return Path(__file__).resolve().parents[2]
def files_root(repo): return repo.parents[1] if len(repo.parents)>=2 else repo.parent
def roots(repo):
    a=files_root(repo)/'FX_OUTPUTS'/'gold_v3'; b=repo/'Files'/'FX_OUTPUTS'/'gold_v3'; return [a] if a==b else [a,b]
def pick(repo):
    for r in roots(repo):
        if (r/UP27/'gold_v3_27_summary.json').exists(): return r,'stage27_root'
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
def table(rows,cols):
    if not rows: return '_No rows._'
    out=['| '+' | '.join(cols)+' |','| '+' | '.join(['---']*len(cols))+' |']
    for r in rows: out.append('| '+' | '.join(md(r.get(c,''))[:240] for c in cols)+' |')
    return '\n'.join(out)
def report(summary,contract,met,cmp,blk):
    lines=['# GOLD V3 28 primary review filter contract audit-only report','',f"Created UTC: `{summary['created_at_utc']}`",f"Status: `{summary['status']}`",'','## Counts']
    for k in ['primary_contract_rows','comparison_rows','daily_cap_used','switching_used']: lines.append(f"- {k}: `{summary.get(k,'')}`")
    lines+=['','## Primary candidate metrics','',table(met,MET),'','## Primary filter contract','',table(contract,CONTRACT),'','## Comparison rows','',table(cmp,CMP),'','## Blockers','',table(blk,BLK),'','## Safety','','Audit-only filter contract. No switching, no month filter, no daily cap.']
    return '\n'.join(lines)
def run(repo):
    root,note=pick(repo.resolve()); out=root/OUT
    paths={'s27':root/UP27/'gold_v3_27_summary.json','rank':root/UP27/'gold_v3_27_rank_proposal.csv','bundle':root/UP26/'gold_v3_26_clear_validation_bundle.csv','trace':root/UP26/'gold_v3_26_clear_filter_traceability.csv'}
    inv_rows=inv(paths)
    if not all(x['exists'] for x in inv_rows): raise RuntimeError('missing inputs')
    s27=rjson(paths['s27']); rank=rcsv(paths['rank']); bundle=rcsv(paths['bundle']); trace=rcsv(paths['trace'])
    primary_rank=[r for r in rank if r.get('source_scenario_key')==PRIMARY]
    primary_bundle=[r for r in bundle if r.get('source_scenario_key')==PRIMARY]
    variant=(primary_rank[0].get('variant_key') if primary_rank else (primary_bundle[0].get('variant_key') if primary_bundle else ''))
    contract=[]
    for i,t in enumerate([x for x in trace if x.get('source_scenario_key')==PRIMARY and (not variant or x.get('variant_key')==variant)],1):
        contract.append(dict(contract_role='PRIMARY_FILTER_CONTRACT',source_scenario_key=PRIMARY,variant_key=t.get('variant_key',variant),filter_order=i,filter_origin=t.get('filter_origin',''),filter_id=t.get('filter_id',''),filter_description=t.get('filter_description',''),filter_family=t.get('filter_family',''),filter_type=t.get('filter_type',''),rank_scope=t.get('rank_scope',''),column=t.get('column',''),values=t.get('values',''),low=t.get('low',''),high=t.get('high',''),entry_pre_known_only=t.get('entry_pre_known_only','True')))
    metrics=[]
    for r in primary_bundle:
        rr=primary_rank[0] if primary_rank else {}
        metrics.append(dict(source_scenario_key=PRIMARY,variant_key=r.get('variant_key',''),profit_factor=r.get('profit_factor',''),win_rate_result_positive=r.get('win_rate_result_positive',''),trades_per_calendar_day=r.get('trades_per_calendar_day',''),negative_months=r.get('negative_months',''),july_profit_factor=r.get('july_profit_factor',''),bundle_role=r.get('bundle_role',''),rank_order=rr.get('rank_order',''),rank_reason=rr.get('rank_reason','')))
    cmp=[r for r in rank]
    blk=[dict(blocker_id='G3-28-001',blocker_name='inputs',status='CLOSED',detail='Stage27 and Stage26 files found'),dict(blocker_id='G3-28-002',blocker_name='primary contract',status='CLOSED' if contract else 'OPEN_BLOCKER',detail='primary filters written'),dict(blocker_id='G3-28-003',blocker_name='mode',status='CLOSED',detail='audit-only')]
    mat=[dict(review_key='status',value=READY,detail='primary filter contract ready'),dict(review_key='primary_source',value=PRIMARY,detail='primary review source'),dict(review_key='primary_variant',value=variant,detail='primary review variant'),dict(review_key='filter_count',value=len(contract),detail='contract filters'),dict(review_key='daily_cap_used',value=False,detail='not used'),dict(review_key='switching_used',value=False,detail='not used')]
    status=READY if contract else ERR
    summary=dict(created_at_utc=now(),step=STEP,status=status,selected_gold_v3_output_root=str(root),path_resolution_note=note,stage27_status=s27.get('status',''),primary_source=PRIMARY,primary_variant=variant,primary_contract_rows=len(contract),comparison_rows=len(cmp),daily_cap_used=False,switching_used=False,month_filter_used=False,review_scope='primary filter contract only')
    wcsv(out/'gold_v3_28_input_inventory.csv',inv_rows,INV); wcsv(out/'gold_v3_28_primary_filter_contract.csv',contract,CONTRACT); wcsv(out/'gold_v3_28_primary_candidate_metrics.csv',metrics,MET); wcsv(out/'gold_v3_28_comparison_rows.csv',cmp,CMP); wcsv(out/'gold_v3_28_review_matrix.csv',mat,MAT); wcsv(out/'gold_v3_28_blocker_matrix.csv',blk,BLK); wjson(out/'gold_v3_28_summary.json',summary); (out/'GOLD_V3_28_PRIMARY_REVIEW_FILTER_CONTRACT_AUDIT_ONLY_REPORT.md').write_text(report(summary,contract,metrics,cmp,blk),encoding='utf-8')
    print(json.dumps({'status':status,'primary_source':PRIMARY,'filter_count':len(contract),'output_dir':str(out)},ensure_ascii=False,indent=2)); return 0 if status==READY else 2
def fail(repo,e):
    root,note=pick(repo.resolve()); out=root/OUT; out.mkdir(parents=True,exist_ok=True); wjson(out/'gold_v3_28_summary.json',dict(created_at_utc=now(),step=STEP,status=ERR,blocked_reason=f'{e.__class__.__name__}: {e}',path_resolution_note=note)); (out/'gold_v3_28_exception.txt').write_text(traceback.format_exc(),encoding='utf-8')
def main(argv=None):
    ap=argparse.ArgumentParser(); ap.add_argument('--repo-root',default=''); a=ap.parse_args(argv); repo=Path(a.repo_root).resolve() if a.repo_root else repo_default()
    try: return run(repo)
    except Exception as e: fail(repo,e); print(traceback.format_exc(),file=sys.stderr); return 1
if __name__=='__main__': raise SystemExit(main())
