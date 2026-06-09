#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse,csv,hashlib,json,sys,traceback
from datetime import datetime,timezone
from pathlib import Path

STEP='GOLD_V3_29_MULTI_PRIMARY_CLEAR_SET_CONTRACT_AUDIT_ONLY'
OUT='29_multi_primary_clear_set_contract_audit_only'
UP26='26_clear_packet_validation_bundle_audit_only'
UP27='27_clear_bundle_pairwise_review_audit_only'
UP28='28_primary_review_filter_contract_audit_only'
READY='GOLD_V3_29_MULTI_PRIMARY_CLEAR_SET_CONTRACT_READY_AUDIT_ONLY'
ERR='GOLD_V3_29_MULTI_PRIMARY_CLEAR_SET_CONTRACT_EXCEPTION_AUDIT_ONLY'
INV=['input_label','path','required','exists','size_bytes','sha256']
CONTRACT=['set_role','source_scenario_key','variant_key','filter_order','filter_origin','filter_id','filter_description','filter_family','filter_type','rank_scope','column','values','low','high','entry_pre_known_only']
MET=['set_role','source_scenario_key','variant_key','profit_factor','win_rate_result_positive','trades_per_calendar_day','negative_months','july_profit_factor','bundle_role','rank_order','rank_reason']
ROLE=['source_scenario_key','variant_key','set_role','reason','kept_as_multi_primary','notes']
MAT=['review_key','value','detail']; BLK=['blocker_id','blocker_name','status','detail']

def now(): return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')
def repo_default(): return Path(__file__).resolve().parents[2]
def files_root(repo): return repo.parents[1] if len(repo.parents)>=2 else repo.parent
def roots(repo):
    a=files_root(repo)/'FX_OUTPUTS'/'gold_v3'; b=repo/'Files'/'FX_OUTPUTS'/'gold_v3'; return [a] if a==b else [a,b]
def pick(repo):
    for r in roots(repo):
        if (r/UP26/'gold_v3_26_summary.json').exists(): return r,'stage26_root'
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
def role(src): return 'MULTI_PRIMARY_SET_COMPARE' if src.startswith('MAIN_R1_R2') else 'MULTI_PRIMARY_SET'
def md(x): return str(x).replace('\n',' ').replace('\r',' ').replace('|','/')
def table(rows,cols):
    if not rows: return '_No rows._'
    out=['| '+' | '.join(cols)+' |','| '+' | '.join(['---']*len(cols))+' |']
    for r in rows: out.append('| '+' | '.join(md(r.get(c,''))[:240] for c in cols)+' |')
    return '\n'.join(out)
def report(summary,metrics,contract,roles,blk):
    lines=['# GOLD V3 29 multi-primary clear set contract audit-only report','',f"Created UTC: `{summary['created_at_utc']}`",f"Status: `{summary['status']}`",'','## Counts']
    for k in ['multi_primary_rows','contract_rows','daily_cap_used','switching_used']: lines.append(f"- {k}: `{summary.get(k,'')}`")
    lines+=['','## Multi-primary metrics','',table(metrics,MET),'','## Candidate role matrix','',table(roles,ROLE),'','## Multi-primary filter contract','',table(contract,CONTRACT),'','## Blockers','',table(blk,BLK),'','## Safety','','Audit-only multi-primary set contract. No switching, no month filter, no daily cap.']
    return '\n'.join(lines)
def run(repo):
    root,note=pick(repo.resolve()); out=root/OUT
    paths={'s26':root/UP26/'gold_v3_26_summary.json','bundle':root/UP26/'gold_v3_26_clear_validation_bundle.csv','trace':root/UP26/'gold_v3_26_clear_filter_traceability.csv','rank':root/UP27/'gold_v3_27_rank_proposal.csv','s28':root/UP28/'gold_v3_28_summary.json'}
    inv_rows=inv(paths)
    if not all(x['exists'] for x in inv_rows): raise RuntimeError('missing inputs')
    s26=rjson(paths['s26']); s28=rjson(paths['s28']); bundle=rcsv(paths['bundle']); trace=rcsv(paths['trace']); rank=rcsv(paths['rank'])
    rank_by={r.get('source_scenario_key',''):r for r in rank}
    metrics=[]; roles=[]; contract=[]
    for b in bundle:
        src=b.get('source_scenario_key',''); v=b.get('variant_key',''); sr=role(src); rr=rank_by.get(src,{})
        metrics.append(dict(set_role=sr,source_scenario_key=src,variant_key=v,profit_factor=b.get('profit_factor',''),win_rate_result_positive=b.get('win_rate_result_positive',''),trades_per_calendar_day=b.get('trades_per_calendar_day',''),negative_months=b.get('negative_months',''),july_profit_factor=b.get('july_profit_factor',''),bundle_role=b.get('bundle_role',''),rank_order=rr.get('rank_order',''),rank_reason=rr.get('rank_reason','')))
        roles.append(dict(source_scenario_key=src,variant_key=v,set_role=sr,reason='CLEAR row retained as multi-candidate set',kept_as_multi_primary=True,notes='not production behavior'))
        filt=[x for x in trace if x.get('source_scenario_key')==src and x.get('variant_key')==v]
        for i,t in enumerate(filt,1):
            contract.append(dict(set_role=sr,source_scenario_key=src,variant_key=v,filter_order=i,filter_origin=t.get('filter_origin',''),filter_id=t.get('filter_id',''),filter_description=t.get('filter_description',''),filter_family=t.get('filter_family',''),filter_type=t.get('filter_type',''),rank_scope=t.get('rank_scope',''),column=t.get('column',''),values=t.get('values',''),low=t.get('low',''),high=t.get('high',''),entry_pre_known_only=t.get('entry_pre_known_only','True')))
    blk=[dict(blocker_id='G3-29-001',blocker_name='inputs',status='CLOSED',detail='Stage26/27/28 files found'),dict(blocker_id='G3-29-002',blocker_name='multi-primary set',status='CLOSED' if metrics else 'OPEN_BLOCKER',detail='clear set retained'),dict(blocker_id='G3-29-003',blocker_name='mode',status='CLOSED',detail='audit-only')]
    mat=[dict(review_key='status',value=READY,detail='multi-primary clear set ready'),dict(review_key='multi_primary_rows',value=len(metrics),detail='CLEAR candidates retained together'),dict(review_key='contract_rows',value=len(contract),detail='all retained filters'),dict(review_key='stage28_single_primary_correction',value=True,detail='Stage28 over-narrowing corrected'),dict(review_key='daily_cap_used',value=False,detail='not used'),dict(review_key='switching_used',value=False,detail='not used')]
    summary=dict(created_at_utc=now(),step=STEP,status=READY,selected_gold_v3_output_root=str(root),path_resolution_note=note,stage26_status=s26.get('status',''),stage28_status=s28.get('status',''),multi_primary_rows=len(metrics),contract_rows=len(contract),daily_cap_used=False,switching_used=False,month_filter_used=False,review_scope='multi-primary clear set contract only')
    wcsv(out/'gold_v3_29_input_inventory.csv',inv_rows,INV); wcsv(out/'gold_v3_29_multi_primary_contract.csv',contract,CONTRACT); wcsv(out/'gold_v3_29_multi_primary_metrics.csv',metrics,MET); wcsv(out/'gold_v3_29_candidate_role_matrix.csv',roles,ROLE); wcsv(out/'gold_v3_29_review_matrix.csv',mat,MAT); wcsv(out/'gold_v3_29_blocker_matrix.csv',blk,BLK); wjson(out/'gold_v3_29_summary.json',summary); (out/'GOLD_V3_29_MULTI_PRIMARY_CLEAR_SET_CONTRACT_AUDIT_ONLY_REPORT.md').write_text(report(summary,metrics,contract,roles,blk),encoding='utf-8')
    print(json.dumps({'status':READY,'multi_primary_rows':len(metrics),'contract_rows':len(contract),'output_dir':str(out)},ensure_ascii=False,indent=2)); return 0
def fail(repo,e):
    root,note=pick(repo.resolve()); out=root/OUT; out.mkdir(parents=True,exist_ok=True); wjson(out/'gold_v3_29_summary.json',dict(created_at_utc=now(),step=STEP,status=ERR,blocked_reason=f'{e.__class__.__name__}: {e}',path_resolution_note=note)); (out/'gold_v3_29_exception.txt').write_text(traceback.format_exc(),encoding='utf-8')
def main(argv=None):
    ap=argparse.ArgumentParser(); ap.add_argument('--repo-root',default=''); a=ap.parse_args(argv); repo=Path(a.repo_root).resolve() if a.repo_root else repo_default()
    try: return run(repo)
    except Exception as e: fail(repo,e); print(traceback.format_exc(),file=sys.stderr); return 1
if __name__=='__main__': raise SystemExit(main())
