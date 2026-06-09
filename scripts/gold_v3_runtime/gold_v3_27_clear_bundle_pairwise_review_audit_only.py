#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse,csv,hashlib,json,sys,traceback
from datetime import datetime,timezone
from pathlib import Path

STEP='GOLD_V3_27_CLEAR_BUNDLE_PAIRWISE_REVIEW_AUDIT_ONLY'
OUT='27_clear_bundle_pairwise_review_audit_only'
UP='26_clear_packet_validation_bundle_audit_only'
READY='GOLD_V3_27_CLEAR_BUNDLE_PAIRWISE_REVIEW_READY_AUDIT_ONLY'
ERR='GOLD_V3_27_CLEAR_BUNDLE_PAIRWISE_REVIEW_EXCEPTION_AUDIT_ONLY'
INV=['input_label','path','required','exists','size_bytes','sha256']
PAIR=['pair_key','left_source','right_source','left_pf','right_pf','pf_delta_left_minus_right','left_wr','right_wr','wr_delta_left_minus_right','left_tpd','right_tpd','tpd_delta_left_minus_right','left_july_pf','right_july_pf','july_pf_delta_left_minus_right','pair_note']
MON=['pair_key','entry_month','left_source','right_source','left_profit_factor','right_profit_factor','pf_delta_left_minus_right','left_sum_result_usd','right_sum_result_usd','sum_delta_left_minus_right','left_win_rate','right_win_rate','wr_delta_left_minus_right']
FD=['pair_key','source_scenario_key','filter_origin','filter_id','filter_description','column','values','low','high','side']
RANK=['rank_order','bundle_role','source_scenario_key','variant_key','profit_factor','win_rate_result_positive','trades_per_calendar_day','negative_months','july_profit_factor','rank_reason']
MAT=['review_key','value','detail']; BLK=['blocker_id','blocker_name','status','detail']

def now(): return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')
def repo_default(): return Path(__file__).resolve().parents[2]
def files_root(repo): return repo.parents[1] if len(repo.parents)>=2 else repo.parent
def roots(repo):
    a=files_root(repo)/'FX_OUTPUTS'/'gold_v3'; b=repo/'Files'/'FX_OUTPUTS'/'gold_v3'; return [a] if a==b else [a,b]
def pick(repo):
    for r in roots(repo):
        if (r/UP/'gold_v3_26_summary.json').exists(): return r,'stage26_root'
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
def source(r): return r.get('source_scenario_key','')
def pair_name(a,b): return source(a)+'__VS__'+source(b)
def make_pair(a,b):
    return dict(pair_key=pair_name(a,b),left_source=source(a),right_source=source(b),left_pf=a.get('profit_factor',''),right_pf=b.get('profit_factor',''),pf_delta_left_minus_right=round(f(a.get('profit_factor'))-f(b.get('profit_factor')),10),left_wr=a.get('win_rate_result_positive',''),right_wr=b.get('win_rate_result_positive',''),wr_delta_left_minus_right=round(f(a.get('win_rate_result_positive'))-f(b.get('win_rate_result_positive')),10),left_tpd=a.get('trades_per_calendar_day',''),right_tpd=b.get('trades_per_calendar_day',''),tpd_delta_left_minus_right=round(f(a.get('trades_per_calendar_day'))-f(b.get('trades_per_calendar_day')),10),left_july_pf=a.get('july_profit_factor',''),right_july_pf=b.get('july_profit_factor',''),july_pf_delta_left_minus_right=round(f(a.get('july_profit_factor'))-f(b.get('july_profit_factor')),10),pair_note='compare clear bundle rows only')
def md(x): return str(x).replace('\n',' ').replace('\r',' ').replace('|','/')
def table(rows,cols,limit=80):
    if not rows: return '_No rows._'
    out=['| '+' | '.join(cols)+' |','| '+' | '.join(['---']*len(cols))+' |']
    for r in rows[:limit]: out.append('| '+' | '.join(md(r.get(c,''))[:220] for c in cols)+' |')
    return '\n'.join(out)
def report(summary,pairs,rank,blk):
    lines=['# GOLD V3 27 clear bundle pairwise review audit-only report','',f"Created UTC: `{summary['created_at_utc']}`",f"Status: `{summary['status']}`",'','## Counts']
    for k in ['clear_rows','pairwise_rows','monthly_delta_rows','filter_delta_rows','rank_rows','daily_cap_used','switching_used']: lines.append(f"- {k}: `{summary.get(k,'')}`")
    lines+=['','## Pairwise review','',table(pairs,PAIR),'','## Rank proposal','',table(rank,RANK),'','## Blockers','',table(blk,BLK),'','## Safety','','Audit-only pairwise review. No switching, no month filter, no daily cap.']
    return '\n'.join(lines)
def run(repo):
    root,note=pick(repo.resolve()); d=root/UP; out=root/OUT
    paths={'summary':d/'gold_v3_26_summary.json','bundle':d/'gold_v3_26_clear_validation_bundle.csv','monthly':d/'gold_v3_26_clear_monthly_bundle.csv','trace':d/'gold_v3_26_clear_filter_traceability.csv'}
    inv_rows=inv(paths)
    if not all(x['exists'] for x in inv_rows): raise RuntimeError('missing inputs')
    s26=rjson(paths['summary']); bundle=rcsv(paths['bundle']); monthly=rcsv(paths['monthly']); trace=rcsv(paths['trace'])
    bysrc={source(r):r for r in bundle}; rows=list(bysrc.values())
    pairs=[]
    for i in range(len(rows)):
        for j in range(i+1,len(rows)): pairs.append(make_pair(rows[i],rows[j]))
    bymon={}
    for m in monthly: bymon.setdefault((m.get('source_scenario_key',''),m.get('entry_month','')),m)
    months=sorted(set(m.get('entry_month','') for m in monthly))
    mon_delta=[]
    for p in pairs:
        for mo in months:
            a=bymon.get((p['left_source'],mo),{}); b=bymon.get((p['right_source'],mo),{})
            mon_delta.append(dict(pair_key=p['pair_key'],entry_month=mo,left_source=p['left_source'],right_source=p['right_source'],left_profit_factor=a.get('profit_factor',''),right_profit_factor=b.get('profit_factor',''),pf_delta_left_minus_right=round(f(a.get('profit_factor'))-f(b.get('profit_factor')),10),left_sum_result_usd=a.get('sum_result_usd',''),right_sum_result_usd=b.get('sum_result_usd',''),sum_delta_left_minus_right=round(f(a.get('sum_result_usd'))-f(b.get('sum_result_usd')),10),left_win_rate=a.get('win_rate_result_positive',''),right_win_rate=b.get('win_rate_result_positive',''),wr_delta_left_minus_right=round(f(a.get('win_rate_result_positive'))-f(b.get('win_rate_result_positive')),10)))
    fdelta=[]
    for p in pairs:
        for src,side in [(p['left_source'],'LEFT'),(p['right_source'],'RIGHT')]:
            for t in [x for x in trace if x.get('source_scenario_key')==src]:
                fdelta.append(dict(pair_key=p['pair_key'],source_scenario_key=src,filter_origin=t.get('filter_origin',''),filter_id=t.get('filter_id',''),filter_description=t.get('filter_description',''),column=t.get('column',''),values=t.get('values',''),low=t.get('low',''),high=t.get('high',''),side=side))
    ordered=sorted(rows,key=lambda r:(-f(r.get('profit_factor')),-f(r.get('win_rate_result_positive')),-f(r.get('trades_per_calendar_day'))))
    rank=[]
    for n,r in enumerate(ordered,1):
        role='PRIMARY_REVIEW' if n==1 else ('SIBLING_COMPARE' if r.get('source_scenario_key','').startswith('R1_ONLY') else 'LOW_FREQ_COMPARE')
        reason='highest PF in clear bundle' if n==1 else ('R1 sibling comparison' if role=='SIBLING_COMPARE' else 'lower frequency clear comparison')
        rank.append(dict(rank_order=n,bundle_role=role,source_scenario_key=r.get('source_scenario_key',''),variant_key=r.get('variant_key',''),profit_factor=r.get('profit_factor',''),win_rate_result_positive=r.get('win_rate_result_positive',''),trades_per_calendar_day=r.get('trades_per_calendar_day',''),negative_months=r.get('negative_months',''),july_profit_factor=r.get('july_profit_factor',''),rank_reason=reason))
    blk=[dict(blocker_id='G3-27-001',blocker_name='inputs',status='CLOSED',detail='Stage26 clear bundle found'),dict(blocker_id='G3-27-002',blocker_name='pairwise',status='CLOSED',detail='pairwise rows written'),dict(blocker_id='G3-27-003',blocker_name='mode',status='CLOSED',detail='audit-only')]
    mat=[dict(review_key='status',value=READY,detail='pairwise review ready'),dict(review_key='primary_source',value=rank[0]['source_scenario_key'] if rank else '',detail='top clear row'),dict(review_key='daily_cap_used',value=False,detail='not used'),dict(review_key='switching_used',value=False,detail='not used')]
    summary=dict(created_at_utc=now(),step=STEP,status=READY,selected_gold_v3_output_root=str(root),path_resolution_note=note,stage26_status=s26.get('status',''),clear_rows=len(bundle),pairwise_rows=len(pairs),monthly_delta_rows=len(mon_delta),filter_delta_rows=len(fdelta),rank_rows=len(rank),daily_cap_used=False,switching_used=False,month_filter_used=False,review_scope='clear bundle pairwise review only')
    wcsv(out/'gold_v3_27_input_inventory.csv',inv_rows,INV); wcsv(out/'gold_v3_27_pairwise_review.csv',pairs,PAIR); wcsv(out/'gold_v3_27_monthly_delta_review.csv',mon_delta,MON); wcsv(out/'gold_v3_27_filter_delta_review.csv',fdelta,FD); wcsv(out/'gold_v3_27_rank_proposal.csv',rank,RANK); wcsv(out/'gold_v3_27_review_matrix.csv',mat,MAT); wcsv(out/'gold_v3_27_blocker_matrix.csv',blk,BLK); wjson(out/'gold_v3_27_summary.json',summary); (out/'GOLD_V3_27_CLEAR_BUNDLE_PAIRWISE_REVIEW_AUDIT_ONLY_REPORT.md').write_text(report(summary,pairs,rank,blk),encoding='utf-8')
    print(json.dumps({'status':READY,'clear_rows':len(bundle),'pairwise_rows':len(pairs),'primary_source':rank[0]['source_scenario_key'] if rank else '', 'output_dir':str(out)},ensure_ascii=False,indent=2)); return 0
def fail(repo,e):
    root,note=pick(repo.resolve()); out=root/OUT; out.mkdir(parents=True,exist_ok=True); wjson(out/'gold_v3_27_summary.json',dict(created_at_utc=now(),step=STEP,status=ERR,blocked_reason=f'{e.__class__.__name__}: {e}',path_resolution_note=note)); (out/'gold_v3_27_exception.txt').write_text(traceback.format_exc(),encoding='utf-8')
def main(argv=None):
    ap=argparse.ArgumentParser(); ap.add_argument('--repo-root',default=''); a=ap.parse_args(argv); repo=Path(a.repo_root).resolve() if a.repo_root else repo_default()
    try: return run(repo)
    except Exception as e: fail(repo,e); print(traceback.format_exc(),file=sys.stderr); return 1
if __name__=='__main__': raise SystemExit(main())
