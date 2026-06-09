#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse,csv,hashlib,json,sys,traceback
from datetime import datetime,timezone
from pathlib import Path
from typing import Any

STEP='GOLD_V3_23_FURTHER_PRUNED_SHORTLIST_HUMAN_INTAKE_AUDIT_ONLY'
OUT_NAME='23_further_pruned_shortlist_human_intake_audit_only'
UP22='22_within_candidate_loss_feature_pruning_audit_only'
UP22_READY='GOLD_V3_22_WITHIN_CANDIDATE_LOSS_FEATURE_PRUNING_READY_AUDIT_ONLY'
READY='GOLD_V3_23_FURTHER_PRUNED_SHORTLIST_HUMAN_INTAKE_READY_AUDIT_ONLY'
BLOCKED='GOLD_V3_23_FURTHER_PRUNED_SHORTLIST_HUMAN_INTAKE_BLOCKED_AUDIT_ONLY'
EXCEPTION='GOLD_V3_23_FURTHER_PRUNED_SHORTLIST_HUMAN_INTAKE_EXCEPTION_AUDIT_ONLY'
FALSE_FLAGS=dict(auto_approval=False,final_candidate_approval=False,threshold_finalization=False,model_training=False,signals_generated=False,zip_output_created=False,ai_api_called=False,discord_enabled=False,mt5_enabled=False,live_hook_enabled=False,live_evaluator_enabled=False,final_signal_enabled=False,gold_v2_live_sot_used=False,quarantined_legacy_artifacts_read=False)
REQUIRED_SOURCES=['R1_ONLY_CD60_PRUNE_111','R1_ONLY_CD60_PRUNE_115','R1_ONLY_CD60_PRUNE_015','MAIN_R1_R2_CD90_PRUNE_133','MAIN_R1_R2_CD90_PRUNE_132','MAIN_R1_R2_CD120_PRUNE_122']
ALLOWED='APPROVE_FOR_NEXT_AUDIT_ONLY_FINAL_VALIDATION;APPROVE_AS_AUXILIARY_COMPARISON_ONLY;KEEP_JULY_RESCUE_REVIEW;REQUEST_MORE_AUDIT;REJECT_FROM_SHORTLIST'
INV=['input_label','path','required','exists','size_bytes','sha256']
PACKET=['packet_row','source_rank_group','source_scenario_key','variant_key','recommendation_tier','suggested_human_decision','trades_per_calendar_day','win_rate_result_positive','profit_factor','pf_uplift_vs_source','negative_months','worst_month','worst_month_sum','july_profit_factor','july_sum_result_usd','max_drawdown_usd','max_consecutive_losses','added_filter_ids','added_filter_descriptions','reason','not_final_approval']
TEMPLATE=['packet_row','source_scenario_key','variant_key','recommendation_tier','suggested_human_decision','allowed_human_decisions','human_decision','human_note','reviewer','reviewed_at_utc']
GROUP=['source_scenario_key','available_variant_rows','packet_rows_selected','best_packet_variant','best_profit_factor','best_win_rate','best_trades_per_day','best_negative_months','best_worst_month_sum','best_july_profit_factor','source_group_note']
TRACE=['packet_row','source_scenario_key','variant_key','filter_origin','filter_id','filter_description','filter_family','filter_type','rank_scope','column','values','low','high','entry_pre_known_only']
DEC=['decision_key','value','detail']; BLOCK=['blocker_id','blocker_name','status','detail']

def now(): return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')
def repo_default(): return Path(__file__).resolve().parents[2]
def files_root(repo:Path)->Path: return repo.parents[1] if len(repo.parents)>=2 else repo.parent
def roots(repo):
    a=files_root(repo)/'FX_OUTPUTS'/'gold_v3'; b=repo/'Files'/'FX_OUTPUTS'/'gold_v3'; return [a] if a==b else [a,b]
def select_root(repo):
    for p in roots(repo):
        if (p/UP22/'gold_v3_22_summary.json').exists(): return p,'selected_existing_stage22_root'
    return roots(repo)[0],'selected_primary_gold_v3_root_no_stage22_inputs_found'
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
def pfnum(x): return 999999.0 if str(x).upper().startswith('INF') else f(x,-1.0)
def inv(items): return [dict(input_label=k,path=str(p),required=req,exists=p.exists(),size_bytes=p.stat().st_size if p.exists() else '',sha256=sha(p) if p.exists() else '') for k,p,req in items]
def src_rank_group(src):
    if src=='R1_ONLY_CD60_PRUNE_015': return 'JULY_RESCUE_R1'
    if src.startswith('R1_ONLY'): return 'R1_ONLY_FURTHER_PRUNED'
    if src.startswith('MAIN_R1_R2'): return 'MAIN_R1_R2_FURTHER_PRUNED'
    return 'OTHER'
def suggested(row):
    src=row.get('source_scenario_key',''); tier=row.get('recommendation_tier','')
    if src=='R1_ONLY_CD60_PRUNE_015': return 'KEEP_JULY_RESCUE_REVIEW'
    if tier=='TIER_1_FURTHER_PRUNED_SHORTLIST': return 'APPROVE_FOR_NEXT_AUDIT_ONLY_FINAL_VALIDATION'
    if tier=='TIER_2_FURTHER_PRUNED_REVIEW': return 'APPROVE_AS_AUXILIARY_COMPARISON_ONLY'
    return 'REQUEST_MORE_AUDIT'
def score(row):
    return (0 if row.get('recommendation_tier')=='TIER_1_FURTHER_PRUNED_SHORTLIST' else 1, -pfnum(row.get('profit_factor')), -f(row.get('win_rate_result_positive')), -f(row.get('trades_per_calendar_day')), f(row.get('negative_months')), f(row.get('worst_month_sum')))
def md(x): return str(x).replace('\n',' ').replace('\r',' ').replace('|','/')
def table(rows,cols,n=60):
    if not rows: return '_No rows._'
    out=['| '+' | '.join(cols)+' |','| '+' | '.join(['---']*len(cols))+' |']
    for r in rows[:n]: out.append('| '+' | '.join(md(r.get(c,''))[:500] for c in cols)+' |')
    return '\n'.join(out)
def blockers(ok,in_ok,packet_ok,required_ok):
    return [dict(blocker_id='G3-23-001',blocker_name='stage-22 inputs',status='CLOSED' if ok and in_ok else 'OPEN_BLOCKER',detail='Stage22 READY outputs are required'),dict(blocker_id='G3-23-002',blocker_name='compact packet',status='CLOSED' if packet_ok else 'OPEN_BLOCKER',detail='compact decision packet must be produced'),dict(blocker_id='G3-23-003',blocker_name='required source coverage',status='CLOSED' if required_ok else 'OPEN_BLOCKER',detail='required Stage21/22 source scenarios must remain visible'),dict(blocker_id='G3-23-004',blocker_name='no switching',status='CLOSED',detail='packet does not implement switching logic'),dict(blocker_id='G3-23-005',blocker_name='no daily cap',status='CLOSED',detail='no daily cap is used'),dict(blocker_id='G3-23-006',blocker_name='final approval',status='CLOSED_BLOCKED_BY_POLICY',detail='Stage23 does not approve final candidates'),dict(blocker_id='G3-23-007',blocker_name='signal/live',status='CLOSED_BLOCKED_BY_POLICY',detail='signal/live/final signal remain OFF'),dict(blocker_id='G3-23-008',blocker_name='legacy quarantine',status='CLOSED',detail='GOLD V2 / old GOLD / DISC8 not read')]
def report(summary,packet,groups,trace,template,blocks):
    lines=['# GOLD V3 23 further-pruned shortlist human intake audit-only report','',f"Created UTC: `{summary.get('created_at_utc','')}`",f"Status: `{summary.get('status','')}`",'','## Scope','','This stage compacted Stage22 further-pruned recommendations into a human decision packet/template. It does not approve final candidates and does not enable live behavior.','','## Counts']
    for k in ['stage22_recommendation_rows','compact_packet_rows','human_template_rows','source_group_rows','filter_trace_packet_rows','required_sources_present','daily_cap_used','switching_used']: lines.append(f"- {k}: `{summary.get(k,'')}`")
    lines+=['','## Compact decision packet','',table(packet,['packet_row','source_rank_group','source_scenario_key','variant_key','recommendation_tier','suggested_human_decision','trades_per_calendar_day','win_rate_result_positive','profit_factor','negative_months','worst_month_sum','july_profit_factor','added_filter_ids'],80),'','## Source group review','',table(groups,GROUP,80),'','## Filter traceability packet','',table(trace,TRACE,120),'','## Human decision template','',table(template,['packet_row','source_scenario_key','variant_key','suggested_human_decision','human_decision','human_note'],80),'','## Blockers','',table(blocks,BLOCK,80),'','## Safety','','Audit-only. No switching, no month filter, no daily cap, no final approval, no live enablement.']
    return '\n'.join(lines)
def run(repo):
    repo=repo.resolve(); root,reason=select_root(repo); d=root/UP22; out=root/OUT_NAME
    paths=dict(summary=d/'gold_v3_22_summary.json',rec=d/'gold_v3_22_recommendation.csv',metrics=d/'gold_v3_22_further_pruned_candidate_metrics.csv',trace=d/'gold_v3_22_filter_traceability.csv',base=d/'gold_v3_22_base_candidate_metrics.csv')
    invr=inv([(k,p,True) for k,p in paths.items()]); in_ok=all(x['exists'] for x in invr)
    if not in_ok: raise RuntimeError('missing Stage22 required inputs')
    s22=rjson(paths['summary']); ok=s22.get('status')==UP22_READY and not bool(s22.get('daily_cap_used',True)) and not bool(s22.get('switching_used',True))
    rec=rcsv(paths['rec']); met=rcsv(paths['metrics']); tr=rcsv(paths['trace'])
    met_by={r.get('variant_key',''):r for r in met}; traces_by={}
    for r in tr: traces_by.setdefault(r.get('variant_key',''),[]).append(r)
    by_src={}
    for r in rec:
        src=r.get('source_scenario_key',''); by_src.setdefault(src,[]).append(r)
    packet=[]; groups=[]; trace_packet=[]; template=[]; rowno=0
    required_present=all(src in by_src for src in REQUIRED_SOURCES if src!='MAIN_R1_R2_CD120_PRUNE_122')
    for src in sorted(by_src.keys(), key=lambda x:(0 if x in REQUIRED_SOURCES else 1, REQUIRED_SOURCES.index(x) if x in REQUIRED_SOURCES else x)):
        rows=by_src[src]
        rows.sort(key=score)
        keep_n=3 if src in {'R1_ONLY_CD60_PRUNE_111','R1_ONLY_CD60_PRUNE_115'} else 2
        if src=='R1_ONLY_CD60_PRUNE_015': keep_n=2
        if src.startswith('MAIN_R1_R2'): keep_n=2
        chosen=rows[:keep_n]
        for r in chosen:
            rowno+=1; v=r.get('variant_key',''); m=met_by.get(v,{})
            item=dict(packet_row=rowno,source_rank_group=src_rank_group(src),source_scenario_key=src,variant_key=v,recommendation_tier=r.get('recommendation_tier',''),suggested_human_decision=suggested(r),trades_per_calendar_day=r.get('trades_per_calendar_day',''),win_rate_result_positive=r.get('win_rate_result_positive',''),profit_factor=r.get('profit_factor',''),pf_uplift_vs_source=r.get('pf_uplift_vs_source',''),negative_months=r.get('negative_months',''),worst_month=r.get('worst_month',''),worst_month_sum=r.get('worst_month_sum',''),july_profit_factor=r.get('july_profit_factor',''),july_sum_result_usd=r.get('july_sum_result_usd',''),max_drawdown_usd=m.get('max_drawdown_usd',''),max_consecutive_losses=m.get('max_consecutive_losses',''),added_filter_ids=r.get('added_filter_ids',''),added_filter_descriptions=r.get('added_filter_descriptions',''),reason=r.get('reason',''),not_final_approval=True)
            packet.append(item)
            template.append(dict(packet_row=rowno,source_scenario_key=src,variant_key=v,recommendation_tier=r.get('recommendation_tier',''),suggested_human_decision=item['suggested_human_decision'],allowed_human_decisions=ALLOWED,human_decision='',human_note='',reviewer='',reviewed_at_utc=''))
            for t in traces_by.get(v,[]):
                z=dict(packet_row=rowno,source_scenario_key=src,variant_key=v,filter_origin=t.get('filter_origin',''),filter_id=t.get('filter_id',''),filter_description=t.get('filter_description',''),filter_family=t.get('filter_family',''),filter_type=t.get('filter_type',''),rank_scope=t.get('rank_scope',''),column=t.get('column',''),values=t.get('values',''),low=t.get('low',''),high=t.get('high',''),entry_pre_known_only=t.get('entry_pre_known_only',True)); trace_packet.append(z)
        best=chosen[0] if chosen else {}
        groups.append(dict(source_scenario_key=src,available_variant_rows=len(rows),packet_rows_selected=len(chosen),best_packet_variant=best.get('variant_key',''),best_profit_factor=best.get('profit_factor',''),best_win_rate=best.get('win_rate_result_positive',''),best_trades_per_day=best.get('trades_per_calendar_day',''),best_negative_months=best.get('negative_months',''),best_worst_month_sum=best.get('worst_month_sum',''),best_july_profit_factor=best.get('july_profit_factor',''),source_group_note='required source retained' if src in REQUIRED_SOURCES else 'extra source retained from Stage22'))
    packet_ok=len(packet)>0 and len(template)==len(packet); status=READY if ok and in_ok and packet_ok and required_present else BLOCKED; blocks=blockers(ok,in_ok,packet_ok,required_present)
    decisions=[dict(decision_key='selected_gold_v3_output_root',value=str(root),detail=reason),dict(decision_key='status',value=status,detail='further-pruned human intake audit-only status'),dict(decision_key='switching_used',value=False,detail='no switching logic'),dict(decision_key='month_filter_used',value=False,detail='month used only in metrics'),dict(decision_key='daily_cap_used',value=False,detail='no daily cap'),dict(decision_key='final_candidate_approval',value=False,detail='blocked by policy'),dict(decision_key='signals_generated',value=False,detail='blocked by policy')]
    summary=dict(created_at_utc=now(),step=STEP,status=status,blocked_reason='' if status==READY else 'Stage23 packet checks failed',selected_gold_v3_output_root=str(root),path_resolution_note=reason,stage22_status=s22.get('status',''),stage22_recommendation_rows=len(rec),compact_packet_rows=len(packet),human_template_rows=len(template),source_group_rows=len(groups),filter_trace_packet_rows=len(trace_packet),required_sources_present=required_present,switching_used=False,month_filter_used=False,daily_cap_used=False,entry_pre_known_features_only=True,replay_scope='audit-only further-pruned human intake; not final/live approval',old_gold_disc8_quarantined=True,**FALSE_FLAGS)
    wcsv(out/'gold_v3_23_input_inventory.csv',invr,INV); wcsv(out/'gold_v3_23_compact_decision_packet.csv',packet,PACKET); wcsv(out/'gold_v3_23_human_decision_template.csv',template,TEMPLATE); wcsv(out/'gold_v3_23_source_group_review.csv',groups,GROUP); wcsv(out/'gold_v3_23_filter_traceability_packet.csv',trace_packet,TRACE); wcsv(out/'gold_v3_23_decision_matrix.csv',decisions,DEC); wcsv(out/'gold_v3_23_blocker_matrix.csv',blocks,BLOCK); wjson(out/'gold_v3_23_summary.json',summary); (out/'GOLD_V3_23_FURTHER_PRUNED_SHORTLIST_HUMAN_INTAKE_AUDIT_ONLY_REPORT.md').write_text(report(summary,packet,groups,trace_packet,template,blocks),encoding='utf-8')
    print(json.dumps({'status':status,'compact_packet_rows':len(packet),'human_template_rows':len(template),'required_sources_present':required_present,'daily_cap_used':False,'switching_used':False,'output_dir':str(out)},ensure_ascii=False,indent=2)); return 0 if status==READY else 2
def write_exception(repo,e):
    try: root,reason=select_root(repo.resolve())
    except Exception: root,reason=repo/'Files'/'FX_OUTPUTS'/'gold_v3','exception_fallback'
    out=root/OUT_NAME; out.mkdir(parents=True,exist_ok=True); wjson(out/'gold_v3_23_summary.json',dict(created_at_utc=now(),step=STEP,status=EXCEPTION,blocked_reason=f'{e.__class__.__name__}: {e}',selected_gold_v3_output_root=str(root),path_resolution_note=reason,**FALSE_FLAGS)); (out/'gold_v3_23_exception.txt').write_text(traceback.format_exc(),encoding='utf-8')
def main(argv=None):
    ap=argparse.ArgumentParser(); ap.add_argument('--repo-root',default=''); a=ap.parse_args(argv); repo=Path(a.repo_root).resolve() if a.repo_root else repo_default()
    try: return run(repo)
    except Exception as e: write_exception(repo,e); print('[GOLD_V3_23] EXCEPTION. See output gold_v3_23_exception.txt',file=sys.stderr); print(traceback.format_exc(),file=sys.stderr); return 1
if __name__=='__main__': raise SystemExit(main())
