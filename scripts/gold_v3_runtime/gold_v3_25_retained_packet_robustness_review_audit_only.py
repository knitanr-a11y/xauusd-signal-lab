#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse,csv,hashlib,json,sys,traceback
from datetime import datetime,timezone
from pathlib import Path

STEP='GOLD_V3_25_RETAINED_PACKET_ROBUSTNESS_REVIEW_AUDIT_ONLY'
OUT='25_retained_packet_robustness_review_audit_only'
UP24='24_further_pruned_decision_proposal_audit_only'
UP22='22_within_candidate_loss_feature_pruning_audit_only'
READY='GOLD_V3_25_RETAINED_PACKET_ROBUSTNESS_REVIEW_READY_AUDIT_ONLY'
ERR='GOLD_V3_25_RETAINED_PACKET_ROBUSTNESS_REVIEW_EXCEPTION_AUDIT_ONLY'
INV=['input_label','path','required','exists','size_bytes','sha256']
ROB=['packet_row','proposal_tier','source_scenario_key','variant_key','review_action','trades_per_calendar_day','win_rate_result_positive','profit_factor','negative_months','worst_month','worst_month_sum','july_profit_factor','july_sum_result_usd','max_drawdown_usd','max_consecutive_losses','added_filter_ids','robustness_flags','robustness_note']
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
        if (r/UP24/'gold_v3_24_summary.json').exists(): return r,'stage24_root'
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
def flags(row):
    fs=[]
    if int(f(row.get('negative_months')))>0: fs.append('NEGATIVE_MONTHS')
    if f(row.get('worst_month_sum'))<0: fs.append('WORST_MONTH_BELOW_ZERO')
    if f(row.get('july_profit_factor'))<1.1: fs.append('JULY_PF_LOW')
    if f(row.get('trades_per_calendar_day'))<2.0: fs.append('LOW_FREQUENCY')
    return ';'.join(fs) if fs else 'CLEAR'
def note(fs):
    if fs=='CLEAR': return 'no major robustness flags'
    return 'review required: '+fs
def md(x): return str(x).replace('\n',' ').replace('\r',' ').replace('|','/')
def table(rows,cols,limit=80):
    if not rows: return '_No rows._'
    out=['| '+' | '.join(cols)+' |','| '+' | '.join(['---']*len(cols))+' |']
    for r in rows[:limit]: out.append('| '+' | '.join(md(r.get(c,''))[:260] for c in cols)+' |')
    return '\n'.join(out)
def report(summary,rob,mon,blk):
    lines=['# GOLD V3 25 retained packet robustness review audit-only report','',f"Created UTC: `{summary['created_at_utc']}`",f"Status: `{summary['status']}`",'','## Counts']
    for k in ['retained_rows','monthly_rows','clear_rows','flagged_rows','daily_cap_used','switching_used']: lines.append(f"- {k}: `{summary.get(k,'')}`")
    lines+=['','## Retained robustness review','',table(rob,['packet_row','proposal_tier','source_scenario_key','review_action','trades_per_calendar_day','win_rate_result_positive','profit_factor','negative_months','worst_month_sum','july_profit_factor','robustness_flags']),'','## Monthly rows','',table(mon,['packet_row','source_scenario_key','entry_month','rows','win_rate_result_positive','profit_factor','sum_result_usd','month_bucket'],120),'','## Blockers','',table(blk,BLK),'','## Safety','','Audit-only robustness review. No switching, no month filter, no daily cap.']
    return '\n'.join(lines)
def run(repo):
    root,note_root=pick(repo.resolve()); out=root/OUT
    paths={'s24':root/UP24/'gold_v3_24_summary.json','retained':root/UP24/'gold_v3_24_retained_packet.csv','trace':root/UP24/'gold_v3_24_filter_traceability_retained.csv','m22':root/UP22/'gold_v3_22_further_pruned_candidate_metrics.csv','mon22':root/UP22/'gold_v3_22_further_pruned_monthly_metrics.csv'}
    inv_rows=inv(paths)
    if not all(x['exists'] for x in inv_rows): raise RuntimeError('missing inputs')
    s24=rjson(paths['s24']); retained=rcsv(paths['retained']); tr=rcsv(paths['trace']); m22={r.get('variant_key',''):r for r in rcsv(paths['m22'])}; mon22=rcsv(paths['mon22'])
    rob=[]; mon=[]
    by_var={}
    for r in mon22: by_var.setdefault(r.get('variant_key',''),[]).append(r)
    for r in retained:
        v=r.get('variant_key',''); m=m22.get(v,{})
        row={k:r.get(k,'') for k in ['packet_row','proposal_tier','source_scenario_key','variant_key','review_action','added_filter_ids']}
        for k in ['trades_per_calendar_day','win_rate_result_positive','profit_factor','negative_months','worst_month','worst_month_sum','july_profit_factor','july_sum_result_usd','max_drawdown_usd','max_consecutive_losses']:
            row[k]=m.get(k,r.get(k,''))
        fs=flags(row); row['robustness_flags']=fs; row['robustness_note']=note(fs); rob.append(row)
        for x in by_var.get(v,[]):
            mon.append(dict(packet_row=r.get('packet_row',''),proposal_tier=r.get('proposal_tier',''),source_scenario_key=r.get('source_scenario_key',''),variant_key=v,entry_month=x.get('entry_month',''),rows=x.get('rows',''),trades_per_calendar_day=x.get('trades_per_calendar_day',''),win_rate_result_positive=x.get('win_rate_result_positive',''),profit_factor=x.get('profit_factor',''),sum_result_usd=x.get('sum_result_usd',''),month_bucket=x.get('month_bucket',''),is_july=x.get('is_july',''),is_worst_month=x.get('is_worst_month','')))
    blk=[dict(blocker_id='G3-25-001',blocker_name='inputs',status='CLOSED',detail='Stage24 retained and Stage22 metrics found'),dict(blocker_id='G3-25-002',blocker_name='review',status='CLOSED',detail='retained robustness review written'),dict(blocker_id='G3-25-003',blocker_name='mode',status='CLOSED',detail='audit-only')]
    mat=[dict(review_key='status',value=READY,detail='retained robustness review ready'),dict(review_key='retained_rows',value=len(rob),detail='reviewed rows'),dict(review_key='flagged_rows',value=sum(1 for r in rob if r['robustness_flags']!='CLEAR'),detail='rows with flags'),dict(review_key='daily_cap_used',value=False,detail='not used'),dict(review_key='switching_used',value=False,detail='not used')]
    summary=dict(created_at_utc=now(),step=STEP,status=READY,selected_gold_v3_output_root=str(root),path_resolution_note=note_root,stage24_status=s24.get('status',''),retained_rows=len(rob),monthly_rows=len(mon),clear_rows=sum(1 for r in rob if r['robustness_flags']=='CLEAR'),flagged_rows=sum(1 for r in rob if r['robustness_flags']!='CLEAR'),daily_cap_used=False,switching_used=False,month_filter_used=False,review_scope='retained packet robustness only')
    wcsv(out/'gold_v3_25_input_inventory.csv',inv_rows,INV); wcsv(out/'gold_v3_25_retained_robustness_review.csv',rob,ROB); wcsv(out/'gold_v3_25_retained_monthly_review.csv',mon,MON); wcsv(out/'gold_v3_25_filter_traceability_review.csv',tr,TRACE); wcsv(out/'gold_v3_25_review_matrix.csv',mat,MAT); wcsv(out/'gold_v3_25_blocker_matrix.csv',blk,BLK); wjson(out/'gold_v3_25_summary.json',summary); (out/'GOLD_V3_25_RETAINED_PACKET_ROBUSTNESS_REVIEW_AUDIT_ONLY_REPORT.md').write_text(report(summary,rob,mon,blk),encoding='utf-8')
    print(json.dumps({'status':READY,'retained_rows':len(rob),'flagged_rows':summary['flagged_rows'],'output_dir':str(out)},ensure_ascii=False,indent=2)); return 0
def fail(repo,e):
    root,note=pick(repo.resolve()); out=root/OUT; out.mkdir(parents=True,exist_ok=True); wjson(out/'gold_v3_25_summary.json',dict(created_at_utc=now(),step=STEP,status=ERR,blocked_reason=f'{e.__class__.__name__}: {e}',path_resolution_note=note)); (out/'gold_v3_25_exception.txt').write_text(traceback.format_exc(),encoding='utf-8')
def main(argv=None):
    ap=argparse.ArgumentParser(); ap.add_argument('--repo-root',default=''); a=ap.parse_args(argv); repo=Path(a.repo_root).resolve() if a.repo_root else repo_default()
    try: return run(repo)
    except Exception as e: fail(repo,e); print(traceback.format_exc(),file=sys.stderr); return 1
if __name__=='__main__': raise SystemExit(main())
