#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse,csv,hashlib,json,sys,traceback
from datetime import datetime,timezone
from pathlib import Path
from typing import Any

STEP='GOLD_V3_21_SELECTED_PRUNING_RULE_VALIDATION_AUDIT_ONLY'
OUT_NAME='21_selected_pruning_rule_validation_audit_only'
UP20='20_loss_feature_pruning_pf_uplift_audit_only'
UP20_READY='GOLD_V3_20_LOSS_FEATURE_PRUNING_PF_UPLIFT_READY_AUDIT_ONLY'
READY='GOLD_V3_21_SELECTED_PRUNING_RULE_VALIDATION_READY_AUDIT_ONLY'
BLOCKED='GOLD_V3_21_SELECTED_PRUNING_RULE_VALIDATION_BLOCKED_AUDIT_ONLY'
EXCEPTION='GOLD_V3_21_SELECTED_PRUNING_RULE_VALIDATION_EXCEPTION_AUDIT_ONLY'
FALSE_FLAGS=dict(auto_approval=False,final_candidate_approval=False,threshold_finalization=False,model_training=False,signals_generated=False,zip_output_created=False,ai_api_called=False,discord_enabled=False,mt5_enabled=False,live_hook_enabled=False,live_evaluator_enabled=False,final_signal_enabled=False,gold_v2_live_sot_used=False,quarantined_legacy_artifacts_read=False)
SELECTED=[('MAIN_PF_UPLIFT','MAIN_R1_R2_CD90_PRUNE_133'),('MAIN_PF_UPLIFT','MAIN_R1_R2_CD90_PRUNE_132'),('MAIN_PF_UPLIFT','MAIN_R1_R2_CD120_PRUNE_122'),('ADDITIONAL_R1','R1_ONLY_CD60_PRUNE_111'),('ADDITIONAL_R1','R1_ONLY_CD60_PRUNE_115'),('ADDITIONAL_R1','R1_ONLY_CD90_PRUNE_050'),('JULY_RESCUE_R1','R1_ONLY_CD60_PRUNE_015')]
JULY='2025-07'
INV=['input_label','path','required','exists','size_bytes','sha256']
SEL=['selection_tier','scenario_key','scenario_family','cooldown_minutes','filter_ids','filter_descriptions','trades_per_calendar_day','win_rate_result_positive','profit_factor','pf_uplift_vs_baseline','negative_months','worst_month','worst_month_sum','worst_month_pf','july_rows','july_trades_per_calendar_day','july_win_rate_result_positive','july_profit_factor','july_sum_result_usd','max_drawdown_usd','max_consecutive_losses','audit_recommendation','stage21_recommendation','stage21_reason','not_final_approval']
MON=['selection_tier','scenario_key','entry_month','rows','trades_per_calendar_day','win_rate_result_positive','profit_factor','sum_result_usd','month_bucket','is_july','is_worst_month']
TRACE=['scenario_key','filter_id','filter_description','filter_family','filter_type','rank_scope','column','values','low','high','segment_rows','segment_win_rate','segment_profit_factor','segment_avg_result_usd','loss_enrichment_score','entry_pre_known_only']
TEMP=['template_row','selection_tier','scenario_key','suggested_human_decision','allowed_human_decisions','human_decision','human_note','reviewer','reviewed_at_utc']
DEC=['decision_key','value','detail']; BLOCK=['blocker_id','blocker_name','status','detail']
ALLOWED='APPROVE_FOR_NEXT_AUDIT_ONLY_FINAL_VALIDATION;APPROVE_AS_JULY_RESCUE_CANDIDATE;APPROVE_AS_AUXILIARY_COMPARISON_ONLY;REQUEST_MORE_AUDIT;REJECT_FROM_SHORTLIST'

def now(): return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')
def repo_default(): return Path(__file__).resolve().parents[2]
def files_root(repo:Path)->Path: return repo.parents[1] if len(repo.parents)>=2 else repo.parent
def roots(repo):
    a=files_root(repo)/'FX_OUTPUTS'/'gold_v3'; b=repo/'Files'/'FX_OUTPUTS'/'gold_v3'; return [a] if a==b else [a,b]
def select_root(repo):
    for p in roots(repo):
        if (p/UP20/'gold_v3_20_summary.json').exists(): return p,'selected_existing_stage20_root'
    return roots(repo)[0],'selected_primary_gold_v3_root_no_stage20_inputs_found'
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()
def rjson(p): return json.loads(p.read_text(encoding='utf-8'))
def rcsv(p):
    with p.open('r',encoding='utf-8-sig',newline='') as f: return list(csv.DictReader(f))
def wjson(p,o): p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(o,ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf-8')
def wcsv(p,rows,fields):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore'); w.writeheader(); [w.writerow({k:r.get(k,'') for k in fields}) for r in rows]
def f(x,d=0.0):
    try: return float(str(x).strip())
    except Exception: return d
def pfnum(x):
    s=str(x)
    if s.upper().startswith('INF'): return 999999.0
    return f(x,-1.0)
def inv(items):
    return [dict(input_label=k,path=str(p),required=req,exists=p.exists(),size_bytes=p.stat().st_size if p.exists() else '',sha256=sha(p) if p.exists() else '') for k,p,req in items]
def by(rows,key): return {r.get(key,''):r for r in rows}
def md(x): return str(x).replace('\n',' ').replace('\r',' ').replace('|','/')
def mdt(rows,fields,n=80):
    if not rows: return '_No rows._'
    out=['| '+' | '.join(fields)+' |','| '+' | '.join(['---']*len(fields))+' |']
    for r in rows[:n]: out.append('| '+' | '.join(md(r.get(c,''))[:500] for c in fields)+' |')
    return '\n'.join(out)
def stage_rec(tier,sc,ju,met):
    jpf=pfnum(ju.get('profit_factor','')); allpf=pfnum(sc.get('profit_factor','')); tpd=f(sc.get('trades_per_calendar_day')); neg=int(f(sc.get('negative_months'))); wr=f(sc.get('win_rate_result_positive')); jsum=f(ju.get('sum_result_usd'))
    if tier=='JULY_RESCUE_R1':
        if jpf>=3 and jsum>0 and allpf>=1.75: return 'KEEP_JULY_RESCUE_REVIEW','July rescue candidate retained; compare against full-period robustness before any final audit decision'
        return 'REQUEST_MORE_AUDIT','July candidate needs more robustness proof'
    if allpf>=2.0 and wr>=0.61 and tpd>=2 and neg<=1: return 'KEEP_MAIN_PF_UPLIFT_REVIEW','main PF uplift candidate; July weakness must be explicitly reviewed'
    if allpf>=2.0 and tpd>=2: return 'KEEP_ADDITIONAL_REVIEW','additional candidate with strong all-period PF'
    return 'REQUEST_MORE_AUDIT','selected candidate retained for audit but not yet strong enough'
def blockers(ok,in_ok,all_found,july_found):
    return [dict(blocker_id='G3-21-001',blocker_name='stage-20 inputs',status='CLOSED' if ok and in_ok else 'OPEN_BLOCKER',detail='Stage20 READY outputs are required'),dict(blocker_id='G3-21-002',blocker_name='selected candidates found',status='CLOSED' if all_found else 'OPEN_BLOCKER',detail='all selected scenario keys must be found in Stage20 metrics'),dict(blocker_id='G3-21-003',blocker_name='July rescue candidate',status='CLOSED' if july_found else 'OPEN_BLOCKER',detail='R1_ONLY_CD60_PRUNE_015 must be present'),dict(blocker_id='G3-21-004',blocker_name='no daily cap',status='CLOSED',detail='Stage21 validates Stage20 feature-pruning scenarios; no daily cap'),dict(blocker_id='G3-21-005',blocker_name='final approval',status='CLOSED_BLOCKED_BY_POLICY',detail='Stage21 does not approve final candidates'),dict(blocker_id='G3-21-006',blocker_name='threshold finalization',status='CLOSED_BLOCKED_BY_POLICY',detail='Stage21 does not finalize thresholds'),dict(blocker_id='G3-21-007',blocker_name='model training',status='CLOSED_BLOCKED_BY_POLICY',detail='Stage21 does not train models'),dict(blocker_id='G3-21-008',blocker_name='signal/live',status='CLOSED_BLOCKED_BY_POLICY',detail='signal/live/final signal remain OFF'),dict(blocker_id='G3-21-009',blocker_name='zip output',status='CLOSED_DISABLED',detail='ZIP output disabled'),dict(blocker_id='G3-21-010',blocker_name='external actions',status='CLOSED',detail='external integrations remain OFF'),dict(blocker_id='G3-21-011',blocker_name='legacy quarantine',status='CLOSED',detail='GOLD V2 / old GOLD / DISC8 not read')]
def report(summary,sel,mon,tr,temp,blocks):
    lines=['# GOLD V3 21 selected pruning rule validation audit-only report','',f"Created UTC: `{summary.get('created_at_utc','')}`",f"Status: `{summary.get('status','')}`",'','## Scope','','This stage validates selected Stage20 pruning scenarios, including `R1_ONLY_CD60_PRUNE_015` as a July-rescue candidate. It is not final approval and not live approval.','','## Counts']
    for k in ['selected_candidate_rows','monthly_validation_rows','filter_trace_rows','human_template_rows','july_rescue_candidate_included','daily_cap_used']: lines.append(f"- {k}: `{summary.get(k,'')}`")
    lines += ['','## Selected candidate validation','',mdt(sel,['selection_tier','scenario_key','trades_per_calendar_day','win_rate_result_positive','profit_factor','negative_months','worst_month','worst_month_sum','july_profit_factor','july_sum_result_usd','stage21_recommendation'],80),'','## July rows','',mdt([r for r in mon if str(r.get('is_july'))=='True'],['selection_tier','scenario_key','entry_month','rows','trades_per_calendar_day','win_rate_result_positive','profit_factor','sum_result_usd','month_bucket'],80),'','## Filter traceability','',mdt(tr,TRACE,120),'','## Human decision template','',mdt(temp,['template_row','selection_tier','scenario_key','suggested_human_decision','human_decision','human_note'],80),'','## Blockers','',mdt(blocks,BLOCK,80),'','## Safety','','Stage21 is audit-only. No daily cap, final approval, threshold finalization, model training, signal generation, ZIP output, external action, or live enablement is performed.']
    return '\n'.join(lines)
def run(repo):
    repo=repo.resolve(); root,reason=select_root(repo); d=root/UP20; out=root/OUT_NAME
    p=dict(summary=d/'gold_v3_20_summary.json',metrics=d/'gold_v3_20_scenario_metrics.csv',monthly=d/'gold_v3_20_scenario_monthly_metrics.csv',segments=d/'gold_v3_20_loss_segment_audit.csv',bias=d/'gold_v3_20_month_bias_matrix.csv')
    invr=inv([('stage20_summary',p['summary'],True),('stage20_scenario_metrics',p['metrics'],True),('stage20_monthly_metrics',p['monthly'],True),('stage20_loss_segment_audit',p['segments'],True),('stage20_month_bias_matrix',p['bias'],True)])
    in_ok=all(x['exists'] for x in invr if x['required'])
    if not in_ok: raise RuntimeError('missing Stage20 required inputs')
    s20=rjson(p['summary']); ok=s20.get('status')==UP20_READY and not bool(s20.get('daily_cap_used',True)); metrics=rcsv(p['metrics']); monthly=rcsv(p['monthly']); segs=rcsv(p['segments']); mb=rcsv(p['bias'])
    mm_by={(r.get('scenario_key',''),r.get('entry_month','')):r for r in monthly}; met_by=by(metrics,'scenario_key'); seg_by=by(segs,'filter_id')
    selected=[]; monrows=[]; trace=[]; temp=[]; found=[]
    for idx,(tier,key) in enumerate(SELECTED,1):
        sc=met_by.get(key); found.append(bool(sc)); ju=mm_by.get((key,JULY),{}); months=[r for r in monthly if r.get('scenario_key')==key]
        worst=min(months,key=lambda r:f(r.get('sum_result_usd')),default={}); rec,reason=stage_rec(tier,sc or {},ju,metrics)
        row=dict(selection_tier=tier,scenario_key=key,scenario_family=(sc or {}).get('scenario_family',''),cooldown_minutes=(sc or {}).get('cooldown_minutes',''),filter_ids=(sc or {}).get('filter_ids',''),filter_descriptions=(sc or {}).get('filter_descriptions',''),trades_per_calendar_day=(sc or {}).get('trades_per_calendar_day',''),win_rate_result_positive=(sc or {}).get('win_rate_result_positive',''),profit_factor=(sc or {}).get('profit_factor',''),pf_uplift_vs_baseline=(sc or {}).get('pf_uplift_vs_baseline',''),negative_months=(sc or {}).get('negative_months',''),worst_month=worst.get('entry_month',''),worst_month_sum=worst.get('sum_result_usd',''),worst_month_pf=worst.get('profit_factor',''),july_rows=ju.get('rows',''),july_trades_per_calendar_day=ju.get('trades_per_calendar_day',''),july_win_rate_result_positive=ju.get('win_rate_result_positive',''),july_profit_factor=ju.get('profit_factor',''),july_sum_result_usd=ju.get('sum_result_usd',''),max_drawdown_usd=(sc or {}).get('max_drawdown_usd',''),max_consecutive_losses=(sc or {}).get('max_consecutive_losses',''),audit_recommendation=(sc or {}).get('audit_recommendation',''),stage21_recommendation=rec,stage21_reason=reason,not_final_approval=True)
        selected.append(row)
        for r in months:
            monrows.append(dict(selection_tier=tier,scenario_key=key,entry_month=r.get('entry_month',''),rows=r.get('rows',''),trades_per_calendar_day=r.get('trades_per_calendar_day',''),win_rate_result_positive=r.get('win_rate_result_positive',''),profit_factor=r.get('profit_factor',''),sum_result_usd=r.get('sum_result_usd',''),month_bucket=r.get('month_bucket',''),is_july=r.get('entry_month')==JULY,is_worst_month=r.get('entry_month')==worst.get('entry_month')))
        for fid in str(row['filter_ids']).split(';') if row['filter_ids'] else []:
            sg=seg_by.get(fid,{})
            trace.append(dict(scenario_key=key,filter_id=fid,filter_description=sg.get('filter_description',''),filter_family=sg.get('filter_family',''),filter_type=sg.get('filter_type',''),rank_scope=sg.get('rank_scope',''),column=sg.get('column',''),values=sg.get('values',''),low=sg.get('low',''),high=sg.get('high',''),segment_rows=sg.get('segment_rows',''),segment_win_rate=sg.get('segment_win_rate',''),segment_profit_factor=sg.get('segment_profit_factor',''),segment_avg_result_usd=sg.get('segment_avg_result_usd',''),loss_enrichment_score=sg.get('loss_enrichment_score',''),entry_pre_known_only=True))
        sug='APPROVE_AS_JULY_RESCUE_CANDIDATE' if tier=='JULY_RESCUE_R1' else ('APPROVE_FOR_NEXT_AUDIT_ONLY_FINAL_VALIDATION' if rec.startswith('KEEP_') else 'REQUEST_MORE_AUDIT')
        temp.append(dict(template_row=idx,selection_tier=tier,scenario_key=key,suggested_human_decision=sug,allowed_human_decisions=ALLOWED,human_decision='',human_note='',reviewer='',reviewed_at_utc=''))
    all_found=all(found); july_found=any(r['scenario_key']=='R1_ONLY_CD60_PRUNE_015' for r in selected); status=READY if ok and all_found and july_found else BLOCKED; blocks=blockers(ok,in_ok,all_found,july_found)
    decisions=[dict(decision_key='selected_gold_v3_output_root',value=str(root),detail=reason),dict(decision_key='status',value=status,detail='selected pruning validation audit-only status'),dict(decision_key='july_rescue_candidate',value='R1_ONLY_CD60_PRUNE_015',detail='included by user request'),dict(decision_key='daily_cap_used',value=False,detail='no daily cap'),dict(decision_key='final_candidate_approval',value=False,detail='blocked by policy'),dict(decision_key='threshold_finalization',value=False,detail='blocked by policy'),dict(decision_key='signals_generated',value=False,detail='blocked by policy'),dict(decision_key='zip_output_created',value=False,detail='disabled')]
    summary=dict(created_at_utc=now(),step=STEP,status=status,blocked_reason='' if status==READY else 'Stage21 validation checks failed',selected_gold_v3_output_root=str(root),path_resolution_note=reason,stage20_status=s20.get('status',''),selected_candidate_rows=len(selected),monthly_validation_rows=len(monrows),filter_trace_rows=len(trace),human_template_rows=len(temp),july_rescue_candidate_included=july_found,july_rescue_candidate='R1_ONLY_CD60_PRUNE_015',daily_cap_used=False,entry_pre_known_features_only=True,replay_scope='audit-only selected pruning validation; not final/live approval',old_gold_disc8_quarantined=True,**FALSE_FLAGS)
    wcsv(out/'gold_v3_21_input_inventory.csv',invr,INV); wcsv(out/'gold_v3_21_selected_candidate_validation.csv',selected,SEL); wcsv(out/'gold_v3_21_selected_candidate_monthly_validation.csv',monrows,MON); wcsv(out/'gold_v3_21_filter_traceability.csv',trace,TRACE); wcsv(out/'gold_v3_21_human_decision_template.csv',temp,TEMP); wcsv(out/'gold_v3_21_decision_matrix.csv',decisions,DEC); wcsv(out/'gold_v3_21_blocker_matrix.csv',blocks,BLOCK); wjson(out/'gold_v3_21_summary.json',summary); (out/'GOLD_V3_21_SELECTED_PRUNING_RULE_VALIDATION_AUDIT_ONLY_REPORT.md').write_text(report(summary,selected,monrows,trace,temp,blocks),encoding='utf-8')
    print(json.dumps({'status':status,'selected_candidate_rows':len(selected),'july_rescue_candidate_included':july_found,'output_dir':str(out),'final_candidate_approval':False,'daily_cap_used':False},ensure_ascii=False,indent=2)); return 0 if status==READY else 2
def write_exception(repo,e):
    try: root,reason=select_root(repo.resolve())
    except Exception: root,reason=repo/'Files'/'FX_OUTPUTS'/'gold_v3','exception_fallback'
    out=root/OUT_NAME; out.mkdir(parents=True,exist_ok=True); wjson(out/'gold_v3_21_summary.json',dict(created_at_utc=now(),step=STEP,status=EXCEPTION,blocked_reason=f'{e.__class__.__name__}: {e}',selected_gold_v3_output_root=str(root),path_resolution_note=reason,**FALSE_FLAGS)); (out/'gold_v3_21_exception.txt').write_text(traceback.format_exc(),encoding='utf-8')
def main(argv=None):
    ap=argparse.ArgumentParser(); ap.add_argument('--repo-root',default=''); a=ap.parse_args(argv); repo=Path(a.repo_root).resolve() if a.repo_root else repo_default()
    try: return run(repo)
    except Exception as e: write_exception(repo,e); print('[GOLD_V3_21] EXCEPTION. See output gold_v3_21_exception.txt',file=sys.stderr); print(traceback.format_exc(),file=sys.stderr); return 1
if __name__=='__main__': raise SystemExit(main())
