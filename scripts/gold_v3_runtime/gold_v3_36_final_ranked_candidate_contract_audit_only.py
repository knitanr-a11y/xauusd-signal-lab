#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse,csv,hashlib,json,sys,traceback
from datetime import datetime,timezone
from pathlib import Path

STEP='GOLD_V3_36_FINAL_RANKED_CANDIDATE_CONTRACT_AUDIT_ONLY'
OUT='36_final_ranked_candidate_contract_audit_only'
UP35='35_cumulative_selected_band_pruning_with_packet9_audit_only'
READY='GOLD_V3_36_FINAL_RANKED_CANDIDATE_CONTRACT_READY_AUDIT_ONLY'
ERR='GOLD_V3_36_FINAL_RANKED_CANDIDATE_CONTRACT_EXCEPTION_AUDIT_ONLY'
INV=['input_label','path','required','exists','size_bytes','sha256']
RANK=['rank','rank_prefix','ranked_candidate_name','packet_row','source_scenario_key','variant_key','cooldown_minutes','rows_final','trades_per_day_final','win_rate_final','profit_factor_final','sum_result_usd_final','negative_months_final','july_pf_final','rank_basis','active_candidate_role','candidate_still_active']
FILTER=['rank','ranked_candidate_name','packet_row','cut_id','feature_column','rank_scope','low','high','filter_type','values','filter_description','month_filter_used','candidate_removal_used']
MAT=['review_key','value','detail']; BLK=['blocker_id','blocker_name','status','detail']

def now(): return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')
def repo_default(): return Path(__file__).resolve().parents[2]
def files_root(repo): return repo.parents[1] if len(repo.parents)>=2 else repo.parent
def roots(repo):
    a=files_root(repo)/'FX_OUTPUTS'/'gold_v3'; b=repo/'Files'/'FX_OUTPUTS'/'gold_v3'; return [a] if a==b else [a,b]
def pick(repo):
    for r in roots(repo):
        if (r/UP35/'gold_v3_35_summary.json').exists() and (r/UP35/'gold_v3_35_before_after_metrics.csv').exists(): return r,'stage35_root'
    return roots(repo)[0],'fallback_root'
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()
def inv(paths): return [dict(input_label=k,path=str(p),required=True,exists=p.exists(),size_bytes=p.stat().st_size if p.exists() else '',sha256=sha(p) if p.exists() else '') for k,p in paths.items()]
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
    try: return float(str(x).strip())
    except Exception: return d
def pfnum(x): return 999999.0 if str(x).upper().startswith('INF') else f(x,-1.0)
def safe_name(s):
    out=''.join(c if (c.isalnum() or c in '._-') else '_' for c in str(s))
    while '__' in out: out=out.replace('__','_')
    return out.strip('_')
def table(rows,cols,limit=60):
    if not rows: return '_No rows._'
    def md(x): return str(x).replace('\n',' ').replace('\r',' ').replace('|','/')[:220]
    out=['| '+' | '.join(cols)+' |','| '+' | '.join(['---']*len(cols))+' |']
    for r in rows[:limit]: out.append('| '+' | '.join(md(r.get(c,'')) for c in cols)+' |')
    return '\n'.join(out)
def report(summary,rank_rows,filter_rows,blk):
    lines=['# GOLD V3 36 final ranked candidate contract audit-only report','',f"Created UTC: `{summary['created_at_utc']}`",f"Status: `{summary['status']}`",'','## Counts']
    for k in ['ranked_candidate_rows','filter_contract_rows','candidate_removal_used','month_filter_used','saturday_cut_used','old_packet9_band_used','new_packet9_band_used']: lines.append(f"- {k}: `{summary.get(k,'')}`")
    lines+=['','## Rank basis','','Primary: `profit_factor_final desc`  ','Secondary: `win_rate_final desc`  ','Tertiary: `sum_result_usd_final desc`','','## Ranked candidates','',table(rank_rows,RANK),'','## Final filter contract','',table(filter_rows,FILTER),'','## Blockers','',table(blk,BLK),'','## Safety','','Audit-only. This only creates a ranked candidate naming/contract packet. It does not enable live trading, MT5, Discord, AI API, model training, or final signal.']
    return '\n'.join(lines)
def run(repo):
    root,note=pick(repo.resolve()); out=root/OUT
    paths={'s35':root/UP35/'gold_v3_35_summary.json','metrics':root/UP35/'gold_v3_35_before_after_metrics.csv','plan':root/UP35/'gold_v3_35_selected_cut_plan.csv'}
    inv_rows=inv(paths)
    if not all(x['exists'] for x in inv_rows): raise RuntimeError('missing Stage35 inputs')
    s35=rjson(paths['s35']); metrics=rcsv(paths['metrics']); plan=rcsv(paths['plan'])
    rows=sorted(metrics,key=lambda r:(pfnum(r.get('profit_factor_final')),f(r.get('win_rate_final')),f(r.get('sum_result_usd_final'))),reverse=True)
    rank_rows=[]; name_by_packet={}; rank_by_packet={}
    for i,r in enumerate(rows,1):
        prefix=f'R{i:02d}'
        base=f"P{r.get('packet_row')}_{r.get('source_scenario_key')}"
        ranked=f"{prefix}_{safe_name(base)}"
        name_by_packet[str(r.get('packet_row'))]=ranked; rank_by_packet[str(r.get('packet_row'))]=i
        rank_rows.append(dict(rank=i,rank_prefix=prefix,ranked_candidate_name=ranked,packet_row=r.get('packet_row'),source_scenario_key=r.get('source_scenario_key'),variant_key=r.get('variant_key'),cooldown_minutes=r.get('cooldown_minutes'),rows_final=r.get('rows_final'),trades_per_day_final=r.get('trades_per_day_final'),win_rate_final=r.get('win_rate_final'),profit_factor_final=r.get('profit_factor_final'),sum_result_usd_final=r.get('sum_result_usd_final'),negative_months_final=r.get('negative_months_final'),july_pf_final=r.get('july_pf_final'),rank_basis='profit_factor_final desc -> win_rate_final desc -> sum_result_usd_final desc',active_candidate_role='ACTIVE_CANDIDATE',candidate_still_active=True))
    filter_rows=[]
    for p in plan:
        targets=list(name_by_packet.keys()) if p.get('packet_row')=='ALL' else [str(p.get('packet_row'))]
        for packet in targets:
            if packet not in name_by_packet: continue
            typ='categorical' if p.get('feature_column')=='jst_weekday' else 'numeric_bin'
            vals='Saturday' if p.get('cut_id')=='GLOBAL_SATURDAY' else ''
            filter_rows.append(dict(rank=rank_by_packet[packet],ranked_candidate_name=name_by_packet[packet],packet_row=packet,cut_id=p.get('cut_id'),feature_column=p.get('feature_column'),rank_scope=p.get('rank_scope'),low=p.get('low'),high=p.get('high'),filter_type=typ,values=vals,filter_description=p.get('cut_description'),month_filter_used=False,candidate_removal_used=False))
    filter_rows=sorted(filter_rows,key=lambda r:(int(r['rank']),str(r['cut_id'])))
    blk=[dict(blocker_id='G3-36-001',blocker_name='Stage35 input',status='CLOSED',detail=s35.get('status','')),dict(blocker_id='G3-36-002',blocker_name='candidate preservation',status='CLOSED',detail='all 7 candidates remain active'),dict(blocker_id='G3-36-003',blocker_name='live safety',status='CLOSED',detail='audit-only naming contract only')]
    mat=[dict(review_key='status',value=READY,detail='ranked naming contract ready'),dict(review_key='rank_basis',value='PF_DESC_WINRATE_DESC_SUM_DESC',detail='profit_factor_final desc, then win_rate_final desc, then sum_result_usd_final desc'),dict(review_key='ranked_candidate_rows',value=len(rank_rows),detail='all active candidates ranked'),dict(review_key='filter_contract_rows',value=len(filter_rows),detail='expanded global Saturday plus packet-specific filters'),dict(review_key='candidate_removal_used',value=False,detail='not used'),dict(review_key='month_filter_used',value=False,detail='not used')]
    summary=dict(created_at_utc=now(),step=STEP,status=READY,selected_gold_v3_output_root=str(root),path_resolution_note=note,stage35_status=s35.get('status',''),rank_basis='profit_factor_final desc -> win_rate_final desc -> sum_result_usd_final desc',ranked_candidate_rows=len(rank_rows),filter_contract_rows=len(filter_rows),candidate_removal_used=False,month_filter_used=False,saturday_cut_used=True,old_packet9_band_used=False,new_packet9_band_used=True,daily_cap_used=False,switching_used=False,review_scope='audit-only final ranked candidate naming contract from Stage35')
    wcsv(out/'gold_v3_36_input_inventory.csv',inv_rows,INV); wcsv(out/'gold_v3_36_ranked_candidate_contract.csv',rank_rows,RANK); wcsv(out/'gold_v3_36_final_filter_contract.csv',filter_rows,FILTER); wcsv(out/'gold_v3_36_review_matrix.csv',mat,MAT); wcsv(out/'gold_v3_36_blocker_matrix.csv',blk,BLK); wjson(out/'gold_v3_36_summary.json',summary); (out/'GOLD_V3_36_FINAL_RANKED_CANDIDATE_CONTRACT_AUDIT_ONLY_REPORT.md').write_text(report(summary,rank_rows,filter_rows,blk),encoding='utf-8')
    print(json.dumps({'status':READY,'ranked_candidate_rows':len(rank_rows),'output_dir':str(out)},ensure_ascii=False,indent=2)); return 0
def fail(repo,e):
    root,note=pick(repo.resolve()); out=root/OUT; out.mkdir(parents=True,exist_ok=True); wjson(out/'gold_v3_36_summary.json',dict(created_at_utc=now(),step=STEP,status=ERR,blocked_reason=f'{e.__class__.__name__}: {e}',path_resolution_note=note)); (out/'gold_v3_36_exception.txt').write_text(traceback.format_exc(),encoding='utf-8')
def main(argv=None):
    ap=argparse.ArgumentParser(); ap.add_argument('--repo-root',default=''); a=ap.parse_args(argv); repo=Path(a.repo_root).resolve() if a.repo_root else repo_default()
    try: return run(repo)
    except Exception as e: fail(repo,e); print(traceback.format_exc(),file=sys.stderr); return 1
if __name__=='__main__': raise SystemExit(main())
