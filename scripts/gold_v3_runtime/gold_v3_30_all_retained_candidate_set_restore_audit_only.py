#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse,csv,hashlib,json,sys,traceback
from datetime import datetime,timezone
from pathlib import Path

STEP='GOLD_V3_30_ALL_RETAINED_CANDIDATE_SET_RESTORE_AUDIT_ONLY'
OUT='30_all_retained_candidate_set_restore_audit_only'
UP24='24_further_pruned_decision_proposal_audit_only'
UP25='25_retained_packet_robustness_review_audit_only'
READY='GOLD_V3_30_ALL_RETAINED_CANDIDATE_SET_RESTORE_READY_AUDIT_ONLY'
ERR='GOLD_V3_30_ALL_RETAINED_CANDIDATE_SET_RESTORE_EXCEPTION_AUDIT_ONLY'
INV=['input_label','path','required','exists','size_bytes','sha256']
SET=['packet_row','source_scenario_key','variant_key','proposal_tier','review_action','candidate_set_role','robustness_flags','trades_per_calendar_day','win_rate_result_positive','profit_factor','negative_months','worst_month_sum','july_profit_factor','july_sum_result_usd','added_filter_ids','added_filter_descriptions','restore_note']
CONTRACT=['packet_row','candidate_set_role','source_scenario_key','variant_key','filter_order','filter_origin','filter_id','filter_description','filter_family','filter_type','rank_scope','column','values','low','high','entry_pre_known_only']
ROLE=['packet_row','source_scenario_key','variant_key','candidate_set_role','robustness_flags','kept_in_candidate_set','reason']
MAT=['review_key','value','detail']; BLK=['blocker_id','blocker_name','status','detail']

def now(): return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')
def repo_default(): return Path(__file__).resolve().parents[2]
def files_root(repo): return repo.parents[1] if len(repo.parents)>=2 else repo.parent
def roots(repo):
    a=files_root(repo)/'FX_OUTPUTS'/'gold_v3'; b=repo/'Files'/'FX_OUTPUTS'/'gold_v3'; return [a] if a==b else [a,b]
def pick(repo):
    for r in roots(repo):
        if (r/UP24/'gold_v3_24_retained_packet.csv').exists(): return r,'stage24_root'
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
def role(flag): return 'RETAINED_CLEAR' if flag=='CLEAR' else 'RETAINED_WATCH'
def md(x): return str(x).replace('\n',' ').replace('\r',' ').replace('|','/')
def table(rows,cols,limit=80):
    if not rows: return '_No rows._'
    out=['| '+' | '.join(cols)+' |','| '+' | '.join(['---']*len(cols))+' |']
    for r in rows[:limit]: out.append('| '+' | '.join(md(r.get(c,''))[:240] for c in cols)+' |')
    return '\n'.join(out)
def report(summary,set_rows,roles,blk):
    lines=['# GOLD V3 30 all retained candidate set restore audit-only report','',f"Created UTC: `{summary['created_at_utc']}`",f"Status: `{summary['status']}`",'','## Counts']
    for k in ['retained_candidate_rows','retained_clear_rows','retained_watch_rows','contract_rows','daily_cap_used','switching_used']: lines.append(f"- {k}: `{summary.get(k,'')}`")
    lines+=['','## Restored candidate set','',table(set_rows,SET),'','## Role matrix','',table(roles,ROLE),'','## Blockers','',table(blk,BLK),'','## Safety','','Audit-only restore. No order sending, no alert sending, no model training, no daily cap, no month filter, no switching rule.']
    return '\n'.join(lines)
def run(repo):
    root,note=pick(repo.resolve()); out=root/OUT
    paths={'s24':root/UP24/'gold_v3_24_summary.json','retained':root/UP24/'gold_v3_24_retained_packet.csv','trace':root/UP24/'gold_v3_24_filter_traceability_retained.csv','review25':root/UP25/'gold_v3_25_retained_robustness_review.csv'}
    inv_rows=inv(paths)
    if not all(x['exists'] for x in inv_rows): raise RuntimeError('missing inputs')
    s24=rjson(paths['s24']); retained=rcsv(paths['retained']); trace=rcsv(paths['trace']); review25=rcsv(paths['review25'])
    flags_by_packet={str(r.get('packet_row','')):r.get('robustness_flags','') for r in review25}
    set_rows=[]; roles=[]; contract=[]
    for r in retained:
        pr=str(r.get('packet_row','')); flag=flags_by_packet.get(pr,'UNKNOWN'); rr=role(flag)
        row={k:r.get(k,'') for k in SET if k not in ['candidate_set_role','robustness_flags','restore_note']}
        row['candidate_set_role']=rr; row['robustness_flags']=flag; row['restore_note']='Stage24 retained row restored; flag is advisory only'
        set_rows.append(row)
        roles.append(dict(packet_row=pr,source_scenario_key=r.get('source_scenario_key',''),variant_key=r.get('variant_key',''),candidate_set_role=rr,robustness_flags=flag,kept_in_candidate_set=True,reason='Stage24 retained candidate restored'))
        frows=[x for x in trace if str(x.get('packet_row',''))==pr]
        for i,t in enumerate(frows,1):
            contract.append(dict(packet_row=pr,candidate_set_role=rr,source_scenario_key=t.get('source_scenario_key',''),variant_key=t.get('variant_key',''),filter_order=i,filter_origin=t.get('filter_origin',''),filter_id=t.get('filter_id',''),filter_description=t.get('filter_description',''),filter_family=t.get('filter_family',''),filter_type=t.get('filter_type',''),rank_scope=t.get('rank_scope',''),column=t.get('column',''),values=t.get('values',''),low=t.get('low',''),high=t.get('high',''),entry_pre_known_only=t.get('entry_pre_known_only','True')))
    clear=sum(1 for r in roles if r['candidate_set_role']=='RETAINED_CLEAR'); watch=sum(1 for r in roles if r['candidate_set_role']=='RETAINED_WATCH')
    blk=[dict(blocker_id='G3-30-001',blocker_name='inputs',status='CLOSED',detail='Stage24 retained packet and Stage25 flags found'),dict(blocker_id='G3-30-002',blocker_name='restore',status='CLOSED' if len(set_rows)==7 else 'OPEN_BLOCKER',detail=f'restored rows={len(set_rows)}'),dict(blocker_id='G3-30-003',blocker_name='mode',status='CLOSED',detail='audit-only')]
    mat=[dict(review_key='status',value=READY,detail='all retained candidate set restored'),dict(review_key='retained_candidate_rows',value=len(set_rows),detail='Stage24 retained rows'),dict(review_key='retained_clear_rows',value=clear,detail='advisory clear rows'),dict(review_key='retained_watch_rows',value=watch,detail='advisory watch rows'),dict(review_key='over_narrowing_corrected',value=True,detail='Stage26/29 narrowing no longer removes candidates'),dict(review_key='daily_cap_used',value=False,detail='not used'),dict(review_key='switching_used',value=False,detail='not used')]
    summary=dict(created_at_utc=now(),step=STEP,status=READY,selected_gold_v3_output_root=str(root),path_resolution_note=note,stage24_status=s24.get('status',''),retained_candidate_rows=len(set_rows),retained_clear_rows=clear,retained_watch_rows=watch,contract_rows=len(contract),daily_cap_used=False,switching_used=False,month_filter_used=False,review_scope='all Stage24 retained candidates restored')
    wcsv(out/'gold_v3_30_input_inventory.csv',inv_rows,INV); wcsv(out/'gold_v3_30_all_retained_candidate_set.csv',set_rows,SET); wcsv(out/'gold_v3_30_all_retained_filter_contract.csv',contract,CONTRACT); wcsv(out/'gold_v3_30_candidate_role_matrix.csv',roles,ROLE); wcsv(out/'gold_v3_30_review_matrix.csv',mat,MAT); wcsv(out/'gold_v3_30_blocker_matrix.csv',blk,BLK); wjson(out/'gold_v3_30_summary.json',summary); (out/'GOLD_V3_30_ALL_RETAINED_CANDIDATE_SET_RESTORE_AUDIT_ONLY_REPORT.md').write_text(report(summary,set_rows,roles,blk),encoding='utf-8')
    print(json.dumps({'status':READY,'retained_candidate_rows':len(set_rows),'clear':clear,'watch':watch,'output_dir':str(out)},ensure_ascii=False,indent=2)); return 0
def fail(repo,e):
    root,note=pick(repo.resolve()); out=root/OUT; out.mkdir(parents=True,exist_ok=True); wjson(out/'gold_v3_30_summary.json',dict(created_at_utc=now(),step=STEP,status=ERR,blocked_reason=f'{e.__class__.__name__}: {e}',path_resolution_note=note)); (out/'gold_v3_30_exception.txt').write_text(traceback.format_exc(),encoding='utf-8')
def main(argv=None):
    ap=argparse.ArgumentParser(); ap.add_argument('--repo-root',default=''); a=ap.parse_args(argv); repo=Path(a.repo_root).resolve() if a.repo_root else repo_default()
    try: return run(repo)
    except Exception as e: fail(repo,e); print(traceback.format_exc(),file=sys.stderr); return 1
if __name__=='__main__': raise SystemExit(main())
