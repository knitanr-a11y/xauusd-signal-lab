#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse, csv, hashlib, json, sys, traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STEP='GOLD_V3_19_FINAL_AUDIT_SHORTLIST_HUMAN_DECISION_TEMPLATE_AUDIT_ONLY'
OUT_NAME='19_final_audit_shortlist_human_decision_template_audit_only'
UP18='18_monthly_stability_final_audit_shortlist_audit_only'
UP18_READY='GOLD_V3_18_MONTHLY_STABILITY_FINAL_AUDIT_SHORTLIST_READY_AUDIT_ONLY'
READY='GOLD_V3_19_FINAL_AUDIT_SHORTLIST_HUMAN_DECISION_TEMPLATE_READY_AUDIT_ONLY'
BLOCKED='GOLD_V3_19_FINAL_AUDIT_SHORTLIST_HUMAN_DECISION_TEMPLATE_BLOCKED_AUDIT_ONLY'
EXCEPTION='GOLD_V3_19_FINAL_AUDIT_SHORTLIST_HUMAN_DECISION_TEMPLATE_EXCEPTION_AUDIT_ONLY'
FALSE_FLAGS=dict(auto_approval=False,final_candidate_approval=False,threshold_finalization=False,model_training=False,signals_generated=False,zip_output_created=False,ai_api_called=False,discord_enabled=False,mt5_enabled=False,live_hook_enabled=False,live_evaluator_enabled=False,final_signal_enabled=False,gold_v2_live_sot_used=False,quarantined_legacy_artifacts_read=False)
ALLOWED='APPROVE_FOR_NEXT_AUDIT_ONLY_FINAL_VALIDATION;APPROVE_AS_AUXILIARY_COMPARISON_ONLY;KEEP_DIAGNOSTIC_ONLY;REQUEST_MORE_AUDIT;REQUEST_FILTER_RESCUE_AUDIT;REJECT_FROM_FINAL_AUDIT_SHORTLIST'
INV=['input_label','path','required','exists','size_bytes','sha256']
BLOCK=['blocker_id','blocker_name','status','detail']
DEC=['decision_key','value','detail']
PACKET=['packet_row','recommendation_tier','scenario_key','scenario_id','cooldown_minutes','shortlist_tier','trades_per_calendar_day','win_rate_result_positive','profit_factor','sum_result_usd','negative_months','worst_month_sum','max_drawdown_usd','max_consecutive_losses','audit_recommendation','stage18_reason','suggested_human_decision','decision_note']
TEMPLATE=['packet_row','recommendation_tier','scenario_key','scenario_id','cooldown_minutes','shortlist_tier','stage18_audit_recommendation','suggested_human_decision','allowed_human_decisions','human_decision','human_note','reviewer','reviewed_at_utc']

def now(): return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')
def repo_default(): return Path(__file__).resolve().parents[2]
def files_root(repo:Path)->Path: return repo.parents[1] if len(repo.parents)>=2 else repo.parent
def root_candidates(repo:Path):
    a=files_root(repo)/'FX_OUTPUTS'/'gold_v3'; b=repo/'Files'/'FX_OUTPUTS'/'gold_v3'; return [a] if a==b else [a,b]
def select_root(repo:Path):
    for p in root_candidates(repo):
        if (p/UP18/'gold_v3_18_summary.json').exists(): return p,'selected_existing_stage18_root'
    return root_candidates(repo)[0],'selected_primary_gold_v3_root_no_stage18_inputs_found'
def sha256_file(p:Path):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024), b''): h.update(b)
    return h.hexdigest()
def read_json(p:Path): return json.loads(p.read_text(encoding='utf-8'))
def read_csv(p:Path):
    with p.open('r',encoding='utf-8-sig',newline='') as f: return list(csv.DictReader(f))
def write_json(p:Path,obj:dict[str,Any]): p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(obj,ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf-8')
def write_csv(p:Path,rows:list[dict[str,Any]],fields:list[str]):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore'); w.writeheader()
        for r in rows: w.writerow({k:r.get(k,'') for k in fields})
def inv_rows(items):
    rows=[]
    for label,p,req in items:
        rows.append(dict(input_label=label,path=str(p),required=req,exists=p.exists(),size_bytes=p.stat().st_size if p.exists() else '',sha256=sha256_file(p) if p.exists() else ''))
    return rows
def f(x):
    try: return float(str(x).strip())
    except Exception: return 0.0
def suggested(tier, rec):
    tier=str(tier); rec=str(rec)
    if tier=='TIER_1_FINAL_AUDIT_SHORTLIST' or rec=='KEEP_FINAL_AUDIT_SHORTLIST': return 'APPROVE_FOR_NEXT_AUDIT_ONLY_FINAL_VALIDATION'
    if tier=='TIER_2_AUXILIARY_SHORTLIST' or rec=='KEEP_AUXILIARY_SHORTLIST': return 'APPROVE_AS_AUXILIARY_COMPARISON_ONLY'
    if tier=='TIER_3_DIAGNOSTIC_ONLY' or rec=='H1_DIAGNOSTIC_ONLY': return 'KEEP_DIAGNOSTIC_ONLY'
    if tier=='TIER_4_DROP_OR_FILTER_RESCUE_ONLY' or rec=='DROP_OR_FILTER_RESCUE_ONLY': return 'REQUEST_FILTER_RESCUE_AUDIT'
    return 'REQUEST_MORE_AUDIT'
def note_for(row):
    tier=str(row.get('recommendation_tier','')); scen=str(row.get('scenario_key',''))
    if tier=='TIER_1_FINAL_AUDIT_SHORTLIST': return 'primary final-audit candidate; still not final/live approval'
    if tier=='TIER_2_AUXILIARY_SHORTLIST': return 'auxiliary comparison candidate; review whether H1 profile improves robustness enough'
    if 'R7' in scen or 'R8' in scen: return 'weak diagnostic/drop-bias profile retained for transparent review'
    return 'diagnostic-only row retained for comparison'
def md(x): return str(x).replace('\n',' ').replace('\r',' ').replace('|','/')
def md_table(rows,fields,limit=40):
    if not rows: return '_No rows._'
    out=['| '+' | '.join(fields)+' |','| '+' | '.join(['---']*len(fields))+' |']
    for r in rows[:limit]: out.append('| '+' | '.join(md(r.get(c,''))[:500] for c in fields)+' |')
    return '\n'.join(out)
def blockers(ok,in_ok,packet_ok):
    return [dict(blocker_id='G3-19-001',blocker_name='stage-18 inputs',status='CLOSED' if ok and in_ok else 'OPEN_BLOCKER',detail='Stage 18 READY summary and shortlist rows are required'),dict(blocker_id='G3-19-002',blocker_name='human decision template',status='CLOSED' if packet_ok else 'OPEN_BLOCKER',detail='human decision template must include all Stage 18 recommendation rows'),dict(blocker_id='G3-19-003',blocker_name='rank 7/8 visibility',status='CLOSED' if packet_ok else 'OPEN_BLOCKER',detail='rank 7/8 weak diagnostic/drop-bias rows remain visible'),dict(blocker_id='G3-19-004',blocker_name='final approval',status='CLOSED_BLOCKED_BY_POLICY',detail='Stage 19 does not approve final candidates'),dict(blocker_id='G3-19-005',blocker_name='threshold finalization',status='CLOSED_BLOCKED_BY_POLICY',detail='Stage 19 does not finalize thresholds'),dict(blocker_id='G3-19-006',blocker_name='model training',status='CLOSED_BLOCKED_BY_POLICY',detail='Stage 19 does not train models'),dict(blocker_id='G3-19-007',blocker_name='signal/live',status='CLOSED_BLOCKED_BY_POLICY',detail='signal/live/final signal remain OFF'),dict(blocker_id='G3-19-008',blocker_name='zip output',status='CLOSED_DISABLED',detail='ZIP output disabled'),dict(blocker_id='G3-19-009',blocker_name='external actions',status='CLOSED',detail='Discord/MT5/AI/live integrations remain OFF'),dict(blocker_id='G3-19-010',blocker_name='legacy quarantine',status='CLOSED',detail='GOLD V2 / old GOLD / DISC8 not read')]
def report(summary,packet,template,blocks):
    lines=['# GOLD V3 19 final audit shortlist human decision template audit-only report','',f"Created UTC: `{summary.get('created_at_utc','')}`",f"Status: `{summary.get('status','')}`",'','## Scope','','This stage creates a human decision template from Stage 18 monthly stability results. It is not final approval and not live approval.','','## Counts']
    for k in ['stage18_recommendation_rows','packet_rows','human_template_rows','tier1_rows','tier2_rows','diagnostic_rows','drop_or_filter_rescue_rows']: lines.append(f"- {k}: `{summary.get(k,'')}`")
    lines += ['','## Final audit shortlist packet','',md_table(packet,['packet_row','recommendation_tier','scenario_key','scenario_id','cooldown_minutes','trades_per_calendar_day','win_rate_result_positive','profit_factor','negative_months','suggested_human_decision'],80),'','## Human decision template preview','',md_table(template,['packet_row','scenario_key','suggested_human_decision','human_decision','human_note'],80),'','## Blockers','',md_table(blocks,BLOCK,80),'','## Safety','','`APPROVE_FOR_NEXT_AUDIT_ONLY_FINAL_VALIDATION` is not final/live approval. Stage 19 does not approve candidates, finalize thresholds, train models, generate signals, create ZIP output, call AI API, notify Discord, place MT5 orders, or enable live hooks/evaluators/final signals.']
    return '\n'.join(lines)
def run(repo:Path):
    repo=repo.resolve(); root,reason=select_root(repo); d18=root/UP18; out=root/OUT_NAME
    paths=dict(summary=d18/'gold_v3_18_summary.json',stab=d18/'gold_v3_18_scenario_stability_summary.csv',rec=d18/'gold_v3_18_shortlist_recommendation.csv',rank=d18/'gold_v3_18_rank_retention_review.csv')
    inv=inv_rows([('stage18_summary',paths['summary'],True),('stage18_stability_summary',paths['stab'],True),('stage18_shortlist_recommendation',paths['rec'],True),('stage18_rank_retention_review',paths['rank'],True)])
    in_ok=all(r['exists'] for r in inv if r['required'])
    if not in_ok: raise RuntimeError('missing Stage 18 required inputs')
    s18=read_json(paths['summary']); ok=s18.get('status')=='GOLD_V3_18_MONTHLY_STABILITY_FINAL_AUDIT_SHORTLIST_READY_AUDIT_ONLY'
    stab=read_csv(paths['stab']); rec=read_csv(paths['rec']); by_key={r.get('scenario_key',''):r for r in stab}
    packet=[]; template=[]
    for i,r in enumerate(rec,1):
        key=r.get('scenario_key',''); st=by_key.get(key,{})
        sg=suggested(r.get('recommendation_tier',''), st.get('audit_recommendation',''))
        row=dict(packet_row=i,recommendation_tier=r.get('recommendation_tier',''),scenario_key=key,scenario_id=r.get('scenario_id',''),cooldown_minutes=r.get('cooldown_minutes',''),shortlist_tier=r.get('shortlist_tier',''),trades_per_calendar_day=st.get('trades_per_calendar_day',''),win_rate_result_positive=st.get('win_rate_result_positive',''),profit_factor=st.get('profit_factor',''),sum_result_usd=st.get('sum_result_usd',''),negative_months=st.get('negative_months',''),worst_month_sum=st.get('worst_month_sum',''),max_drawdown_usd=st.get('max_drawdown_usd',''),max_consecutive_losses=st.get('max_consecutive_losses',''),audit_recommendation=st.get('audit_recommendation',''),stage18_reason=r.get('reason',''),suggested_human_decision=sg,decision_note=note_for(r))
        packet.append(row); template.append(dict(packet_row=i,recommendation_tier=row['recommendation_tier'],scenario_key=key,scenario_id=row['scenario_id'],cooldown_minutes=row['cooldown_minutes'],shortlist_tier=row['shortlist_tier'],stage18_audit_recommendation=row['audit_recommendation'],suggested_human_decision=sg,allowed_human_decisions=ALLOWED,human_decision='',human_note='',reviewer='',reviewed_at_utc=''))
    packet_ok=ok and len(packet)==len(rec) and any('R7' in str(x.get('scenario_key','')) for x in packet) and any('R8' in str(x.get('scenario_key','')) for x in packet)
    status=READY if packet_ok else BLOCKED; blocks=blockers(ok,in_ok,packet_ok)
    decisions=[dict(decision_key='selected_gold_v3_output_root',value=str(root),detail=reason),dict(decision_key='status',value=status,detail='human decision template audit-only status'),dict(decision_key='final_candidate_approval',value=False,detail='blocked by policy'),dict(decision_key='threshold_finalization',value=False,detail='blocked by policy'),dict(decision_key='model_training',value=False,detail='blocked by policy'),dict(decision_key='signals_generated',value=False,detail='blocked by policy'),dict(decision_key='zip_output_created',value=False,detail='disabled'),dict(decision_key='external_actions',value=False,detail='Discord/MT5/AI/live integrations remain OFF')]
    tier1=sum(1 for r in packet if r['recommendation_tier']=='TIER_1_FINAL_AUDIT_SHORTLIST'); tier2=sum(1 for r in packet if r['recommendation_tier']=='TIER_2_AUXILIARY_SHORTLIST'); diag=sum(1 for r in packet if r['recommendation_tier']=='TIER_3_DIAGNOSTIC_ONLY'); drop=sum(1 for r in packet if r['recommendation_tier']=='TIER_4_DROP_OR_FILTER_RESCUE_ONLY')
    summary=dict(created_at_utc=now(),step=STEP,status=status,blocked_reason='' if status==READY else 'Stage 19 template checks failed',selected_gold_v3_output_root=str(root),path_resolution_note=reason,stage18_status=s18.get('status',''),stage18_recommendation_rows=len(rec),packet_rows=len(packet),human_template_rows=len(template),tier1_rows=tier1,tier2_rows=tier2,diagnostic_rows=diag,drop_or_filter_rescue_rows=drop,rank_7_8_visible=True,replay_scope='audit-only human decision template; not final/live approval',old_gold_disc8_quarantined=True,**FALSE_FLAGS)
    write_csv(out/'gold_v3_19_input_inventory.csv',inv,INV); write_csv(out/'gold_v3_19_final_audit_shortlist_packet.csv',packet,PACKET); write_csv(out/'gold_v3_19_human_decision_template.csv',template,TEMPLATE); write_csv(out/'gold_v3_19_decision_matrix.csv',decisions,DEC); write_csv(out/'gold_v3_19_blocker_matrix.csv',blocks,BLOCK); write_json(out/'gold_v3_19_summary.json',summary); (out/'GOLD_V3_19_FINAL_AUDIT_SHORTLIST_HUMAN_DECISION_TEMPLATE_AUDIT_ONLY_REPORT.md').write_text(report(summary,packet,template,blocks),encoding='utf-8')
    print(json.dumps({'status':status,'packet_rows':len(packet),'human_template_rows':len(template),'tier1_rows':tier1,'tier2_rows':tier2,'rank_7_8_visible':True,'output_dir':str(out),'final_candidate_approval':False,'signals_generated':False,'zip_output_created':False},ensure_ascii=False,indent=2)); return 0 if status==READY else 2
def write_exception(repo,exc):
    try: root,reason=select_root(repo.resolve())
    except Exception: root,reason=repo/'Files'/'FX_OUTPUTS'/'gold_v3','exception_fallback'
    out=root/OUT_NAME; out.mkdir(parents=True,exist_ok=True); summary=dict(created_at_utc=now(),step=STEP,status=EXCEPTION,blocked_reason=f'{exc.__class__.__name__}: {exc}',selected_gold_v3_output_root=str(root),path_resolution_note=reason,**FALSE_FLAGS); write_json(out/'gold_v3_19_summary.json',summary); (out/'gold_v3_19_exception.txt').write_text(traceback.format_exc(),encoding='utf-8')
def main(argv=None):
    ap=argparse.ArgumentParser(); ap.add_argument('--repo-root',default=''); a=ap.parse_args(argv); repo=Path(a.repo_root).resolve() if a.repo_root else repo_default()
    try: return run(repo)
    except Exception as e: write_exception(repo,e); print('[GOLD_V3_19] EXCEPTION. See output gold_v3_19_exception.txt',file=sys.stderr); print(traceback.format_exc(),file=sys.stderr); return 1
if __name__=='__main__': raise SystemExit(main())
