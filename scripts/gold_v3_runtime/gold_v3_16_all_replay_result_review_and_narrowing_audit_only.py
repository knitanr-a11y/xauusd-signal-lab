#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse, csv, hashlib, json, math, sys, traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import pandas as pd

STEP='GOLD_V3_16_ALL_REPLAY_RESULT_REVIEW_AND_NARROWING_AUDIT_ONLY'
OUT_NAME='16_all_replay_result_review_and_narrowing_audit_only'
UP15='15_audit_only_replay_execution'
UP15_READY='GOLD_V3_15_AUDIT_ONLY_REPLAY_EXECUTION_READY_AUDIT_ONLY'
READY='GOLD_V3_16_ALL_REPLAY_RESULT_REVIEW_AND_NARROWING_READY_AUDIT_ONLY'
BLOCKED='GOLD_V3_16_ALL_REPLAY_RESULT_REVIEW_AND_NARROWING_BLOCKED_AUDIT_ONLY'
EXCEPTION='GOLD_V3_16_ALL_REPLAY_RESULT_REVIEW_AND_NARROWING_EXCEPTION_AUDIT_ONLY'
MIN_TPD=2.0
STRONG_PF=1.50
GOOD_PF=1.30
STRONG_WR=0.58
GOOD_WR=0.50
MAX_NEG_MONTH_RATE=0.25
FALSE_FLAGS=dict(auto_approval=False,final_candidate_approval=False,threshold_finalization=False,model_training=False,signals_generated=False,zip_output_created=False,ai_api_called=False,discord_enabled=False,mt5_enabled=False,live_hook_enabled=False,live_evaluator_enabled=False,final_signal_enabled=False,gold_v2_live_sot_used=False,quarantined_legacy_artifacts_read=False)

INPUT_FIELDS=['input_label','path','required','exists','size_bytes','sha256']
DECISION_FIELDS=['decision_key','value','detail']
BLOCKER_FIELDS=['blocker_id','blocker_name','status','detail']
REVIEW_FIELDS=['source_rank','candidate_group_id','profile_id','direction','feature_column','rule_expression_preview','rows_replayed','trades_per_calendar_day_true','win_rate_result_positive','profit_factor','max_drawdown_usd','max_consecutive_losses','sum_result_usd','avg_result_usd','tp_rate','timeout_count','negative_months','positive_months','month_count','negative_month_rate','min_month_sum','median_month_pf','min_month_pf','median_month_win_rate','score_objective_fit','frequency_bucket','quality_bucket','monthly_bucket','h1_family_profile_role','audit_recommendation','audit_reason','not_final_approval']
MONTHLY_FIELDS=['source_rank','candidate_group_id','profile_id','entry_month','rows_replayed','win_rate_result_positive','profit_factor','sum_result_usd','month_result_bucket']
H1_FIELDS=['source_rank','profile_id','rows_replayed','trades_per_calendar_day_true','win_rate_result_positive','profit_factor','max_drawdown_usd','max_consecutive_losses','sum_result_usd','negative_months','min_month_sum','profile_comparison_role','profile_comparison_note']
REC_FIELDS=['tier','source_rank','candidate_group_id','profile_id','reason','next_audit_action']

def now(): return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')
def repo_default(): return Path(__file__).resolve().parents[2]
def files_root(repo:Path)->Path: return repo.parents[1] if len(repo.parents)>=2 else repo.parent
def v3_candidates(repo:Path):
    a=files_root(repo)/'FX_OUTPUTS'/'gold_v3'; b=repo/'Files'/'FX_OUTPUTS'/'gold_v3'; return [a] if a==b else [a,b]
def select_root(repo:Path):
    for p in v3_candidates(repo):
        if (p/UP15/'gold_v3_15_summary.json').exists(): return p,'selected_existing_stage15_root'
    return v3_candidates(repo)[0],'selected_primary_gold_v3_root_no_stage15_inputs_found'
def sha256_file(p:Path):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024), b''): h.update(b)
    return h.hexdigest()
def clean(x:Any):
    if isinstance(x,dict): return {str(k):clean(v) for k,v in x.items()}
    if isinstance(x,list): return [clean(v) for v in x]
    try:
        if pd.isna(x): return None
    except Exception: pass
    if isinstance(x,float) and (math.isnan(x) or math.isinf(x)): return None
    if hasattr(x,'isoformat'): return x.isoformat()
    return x
def write_json(p:Path,obj): p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(clean(obj),ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf-8')
def write_csv(p:Path,rows,fields):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore'); w.writeheader()
        for r in rows: w.writerow({k:r.get(k,'') for k in fields})
def inv_rows(items):
    out=[]
    for label,p,req in items:
        out.append(dict(input_label=label,path=str(p),required=req,exists=p.exists(),size_bytes=p.stat().st_size if p.exists() else '',sha256=sha256_file(p) if p.exists() else ''))
    return out
def flt(x,default=0.0):
    s=str(x).strip() if x is not None else ''
    if not s or s.lower() in {'nan','none'}: return default
    if s.upper().startswith('INF'): return 999999.0
    try: return float(s)
    except Exception: return default
def it(x,default=0):
    try: return int(float(str(x).strip()))
    except Exception: return default
def mbucket(sumv,pf):
    if sumv>0 and pf>=1: return 'POSITIVE_MONTH'
    if sumv>0: return 'POSITIVE_SUM_WEAK_PF'
    if sumv<0: return 'NEGATIVE_MONTH'
    return 'FLAT_MONTH'
def md(x): return str(x).replace('\n',' ').replace('\r',' ').replace('|','/')
def md_table(rows,fields,limit=80):
    if not rows: return '_No rows._'
    lines=['| '+' | '.join(fields)+' |','| '+' | '.join(['---']*len(fields))+' |']
    for r in list(rows)[:limit]: lines.append('| '+' | '.join(md(r.get(f,''))[:500] for f in fields)+' |')
    return '\n'.join(lines)
def score(row):
    pf=flt(row.get('profit_factor')); wr=flt(row.get('win_rate_result_positive')); tpd=flt(row.get('trades_per_calendar_day_true')); neg=flt(row.get('negative_month_rate')); dd=max(flt(row.get('max_drawdown_usd')),1.0); total=flt(row.get('sum_result_usd'))
    return round(35*min(pf/STRONG_PF,1.5)+25*min(wr/STRONG_WR,1.3)+15*(min(tpd/MIN_TPD,3)/3)+15*max(0,1-neg)+10*max(-1,min((total/dd)/4,1)),6)
def classify(row):
    group=str(row.get('candidate_group_id','')); profile=str(row.get('profile_id','')); pf=flt(row.get('profit_factor')); wr=flt(row.get('win_rate_result_positive')); tpd=flt(row.get('trades_per_calendar_day_true')); neg=flt(row.get('negative_month_rate')); streak=it(row.get('max_consecutive_losses'))
    freq='FREQ_OK_2PLUS_PER_DAY' if tpd>=MIN_TPD else 'FREQ_LOW_BELOW_2_PER_DAY'
    if pf>=STRONG_PF and wr>=STRONG_WR: quality='QUALITY_STRONG_PF_AND_WINRATE'
    elif pf>=GOOD_PF and wr>=GOOD_WR: quality='QUALITY_GOOD_PF_AND_WINRATE'
    elif pf>=GOOD_PF: quality='QUALITY_PF_OK_WINRATE_WEAK'
    else: quality='QUALITY_WEAK'
    monthly='MONTHLY_STABLE' if neg<=MAX_NEG_MONTH_RATE else 'MONTHLY_NEEDS_FILTER'
    if group=='GROUP_H1_ATR56_HIGH_VOL':
        role='H1_FAMILY_BEST_PF_PROFILE' if profile=='USDPRICE_TP100_SL40_H96' else ('H1_FAMILY_COMPARISON_SECONDARY_PROFILE' if profile in {'USDPRICE_TP80_SL30_H64','USDPRICE_TP50_SL20_H48'} else 'H1_FAMILY_COMPARISON_WEAK_PROFILE')
    else: role='UNIQUE_ENTRY_FAMILY'
    if freq!='FREQ_OK_2PLUS_PER_DAY': rec='DO_NOT_KEEP_FOR_2_TRADES_PER_DAY_OBJECTIVE'; reason='true trades/day below objective'
    elif group!='GROUP_H1_ATR56_HIGH_VOL' and pf>=STRONG_PF and wr>=STRONG_WR and neg<=MAX_NEG_MONTH_RATE: rec='KEEP_MAIN'; reason='unique family with strong PF/win rate, enough frequency, and acceptable monthly stability'
    elif group!='GROUP_H1_ATR56_HIGH_VOL' and pf>=STRONG_PF and wr>=GOOD_WR: rec='KEEP_MAIN_WITH_MONTHLY_FILTER_REVIEW'; reason='strong PF and enough frequency, but monthly stability requires review'
    elif group=='GROUP_H1_ATR56_HIGH_VOL' and profile=='USDPRICE_TP100_SL40_H96': rec='KEEP_AUXILIARY_FAMILY_BEST'; reason='best h1_atr56 PF profile; high frequency but weaker win rate than unique families'
    elif group=='GROUP_H1_ATR56_HIGH_VOL' and profile in {'USDPRICE_TP80_SL30_H64','USDPRICE_TP50_SL20_H48'} and pf>=GOOD_PF: rec='KEEP_FOR_H1_FAMILY_PROFILE_COMPARISON'; reason='not independent entry idea; keep to compare TP/SL tradeoff, drawdown, and stability'
    elif group=='GROUP_H1_ATR56_HIGH_VOL': rec='AUDITED_BUT_NARROW_OR_DROP'; reason='audited together; lower PF/win-rate profile within same h1_atr56 family'
    else: rec='REQUEST_MORE_NARROWING_AUDIT'; reason='metrics are not strong enough for main keep without additional filters'
    if streak>=100: reason+='; max consecutive losses is large and requires cooldown/entry-spacing audit'
    return freq,quality,monthly,role,rec,reason

def build_reviews(cand,monthly):
    mon_review=[]
    for _,r in monthly.iterrows():
        sv=flt(r.get('sum_result_usd')); pf=flt(r.get('profit_factor'))
        mon_review.append(dict(source_rank=it(r.get('source_rank')),candidate_group_id=r.get('candidate_group_id',''),profile_id=r.get('profile_id',''),entry_month=r.get('entry_month',''),rows_replayed=it(r.get('rows_replayed')),win_rate_result_positive=round(flt(r.get('win_rate_result_positive')),10),profit_factor=r.get('profit_factor',''),sum_result_usd=round(sv,10),month_result_bucket=mbucket(sv,pf)))
    ms={}
    for key,x in monthly.groupby(['source_rank','candidate_group_id','profile_id'],dropna=False):
        sums=x['sum_result_usd'].map(flt); pfs=x['profit_factor'].map(flt); wrs=x['win_rate_result_positive'].map(flt); n=len(x); neg=int((sums<0).sum())
        ms[key]=dict(month_count=n,negative_months=neg,positive_months=int((sums>0).sum()),negative_month_rate=round(neg/n,10) if n else 0,min_month_sum=round(float(sums.min()),10) if n else 0,median_month_pf=round(float(pfs.median()),10) if n else 0,min_month_pf=round(float(pfs.min()),10) if n else 0,median_month_win_rate=round(float(wrs.median()),10) if n else 0)
    reviews=[]
    for _,r in cand.iterrows():
        key=(r.get('source_rank'),r.get('candidate_group_id'),r.get('profile_id'))
        row=dict(source_rank=it(r.get('source_rank')),candidate_group_id=r.get('candidate_group_id',''),profile_id=r.get('profile_id',''),direction=r.get('direction',''),feature_column=r.get('feature_column',''),rule_expression_preview=r.get('rule_expression_preview',''),rows_replayed=it(r.get('rows_replayed')),trades_per_calendar_day_true=round(flt(r.get('trades_per_calendar_day_true')),10),win_rate_result_positive=round(flt(r.get('win_rate_result_positive')),10),profit_factor=r.get('profit_factor',''),max_drawdown_usd=round(flt(r.get('max_drawdown_usd')),10),max_consecutive_losses=it(r.get('max_consecutive_losses')),sum_result_usd=round(flt(r.get('sum_result_usd')),10),avg_result_usd=round(flt(r.get('avg_result_usd')),10),tp_rate=round(flt(r.get('tp_rate')),10),timeout_count=it(r.get('timeout_count')),not_final_approval=True)
        row.update(ms.get(key,dict(month_count=0,negative_months=0,positive_months=0,negative_month_rate=0,min_month_sum=0,median_month_pf=0,min_month_pf=0,median_month_win_rate=0)))
        row['frequency_bucket'],row['quality_bucket'],row['monthly_bucket'],row['h1_family_profile_role'],row['audit_recommendation'],row['audit_reason']=classify(row)
        row['score_objective_fit']=score(row); reviews.append(row)
    reviews.sort(key=lambda r:(flt(r.get('score_objective_fit')),flt(r.get('profit_factor')),flt(r.get('win_rate_result_positive'))),reverse=True)
    h1=[]
    for r in reviews:
        if r.get('candidate_group_id')=='GROUP_H1_ATR56_HIGH_VOL':
            h1.append(dict(source_rank=r['source_rank'],profile_id=r['profile_id'],rows_replayed=r['rows_replayed'],trades_per_calendar_day_true=r['trades_per_calendar_day_true'],win_rate_result_positive=r['win_rate_result_positive'],profit_factor=r['profit_factor'],max_drawdown_usd=r['max_drawdown_usd'],max_consecutive_losses=r['max_consecutive_losses'],sum_result_usd=r['sum_result_usd'],negative_months=r['negative_months'],min_month_sum=r['min_month_sum'],profile_comparison_role=r['h1_family_profile_role'],profile_comparison_note=r['audit_reason']))
    tier={'KEEP_MAIN':'TIER_1_MAIN','KEEP_MAIN_WITH_MONTHLY_FILTER_REVIEW':'TIER_1_MAIN_REQUIRES_FILTER_REVIEW','KEEP_AUXILIARY_FAMILY_BEST':'TIER_2_AUXILIARY','KEEP_FOR_H1_FAMILY_PROFILE_COMPARISON':'TIER_3_FAMILY_COMPARISON','AUDITED_BUT_NARROW_OR_DROP':'TIER_4_AUDITED_NARROW_OR_DROP','REQUEST_MORE_NARROWING_AUDIT':'TIER_4_REQUEST_MORE_NARROWING','DO_NOT_KEEP_FOR_2_TRADES_PER_DAY_OBJECTIVE':'TIER_5_FREQ_FAIL'}
    rec=[dict(tier=tier.get(r['audit_recommendation'],'TIER_UNKNOWN'),source_rank=r['source_rank'],candidate_group_id=r['candidate_group_id'],profile_id=r['profile_id'],reason=r['audit_reason'],next_audit_action=('include as negative comparison; likely drop unless filters rescue it' if r['audit_recommendation']=='AUDITED_BUT_NARROW_OR_DROP' else 'include in overlap/cooldown/spacing audit')) for r in reviews]
    return reviews,mon_review,h1,rec

def decisions(root,reason,status,reviews,h1):
    kept=[r for r in reviews if str(r.get('audit_recommendation','')).startswith('KEEP')]
    dropped=[r for r in reviews if r.get('audit_recommendation')=='AUDITED_BUT_NARROW_OR_DROP']
    return [dict(decision_key='selected_gold_v3_output_root',value=str(root),detail=reason),dict(decision_key='status',value=status,detail='all Stage 15 replay candidates reviewed'),dict(decision_key='candidate_rows_reviewed',value=len(reviews),detail='includes main and previously deferred/narrow profiles'),dict(decision_key='h1_atr56_profiles_reviewed',value=len(h1),detail='same entry family TP/SL profile comparison'),dict(decision_key='keep_or_compare_rows',value=len(kept),detail='main/auxiliary/family comparison rows'),dict(decision_key='audited_but_narrow_or_drop_rows',value=len(dropped),detail='still audited; not silently excluded'),dict(decision_key='final_candidate_approval',value=False,detail='blocked by policy'),dict(decision_key='threshold_finalization',value=False,detail='blocked by policy'),dict(decision_key='model_training',value=False,detail='blocked by policy'),dict(decision_key='signals_generated',value=False,detail='blocked by policy'),dict(decision_key='zip_output_created',value=False,detail='disabled'),dict(decision_key='external_actions',value=False,detail='Discord/MT5/AI/live integrations remain OFF'),dict(decision_key='quarantined_legacy_artifacts_read',value=False,detail='GOLD V2 / old GOLD / DISC8 not read')]
def blockers(up_ok,in_ok,review_ok):
    return [dict(blocker_id='G3-16-001',blocker_name='stage-15 inputs',status='CLOSED' if in_ok and up_ok else 'OPEN_BLOCKER',detail='Stage 15 READY summary and replay metrics are required'),dict(blocker_id='G3-16-002',blocker_name='all candidate review',status='CLOSED' if review_ok else 'OPEN_BLOCKER',detail='all 7 Stage 15 candidate rows must be reviewed, including h1_atr56 comparison profiles'),dict(blocker_id='G3-16-003',blocker_name='deferred profile inclusion',status='CLOSED' if review_ok else 'OPEN_BLOCKER',detail='rank 4/6/7/8 are audited as h1_atr56 family comparisons'),dict(blocker_id='G3-16-004',blocker_name='final approval',status='CLOSED_BLOCKED_BY_POLICY',detail='Stage 16 does not approve final candidates'),dict(blocker_id='G3-16-005',blocker_name='threshold finalization',status='CLOSED_BLOCKED_BY_POLICY',detail='Stage 16 does not finalize thresholds'),dict(blocker_id='G3-16-006',blocker_name='model training',status='CLOSED_BLOCKED_BY_POLICY',detail='Stage 16 does not train models'),dict(blocker_id='G3-16-007',blocker_name='signal/live',status='CLOSED_BLOCKED_BY_POLICY',detail='signal/live/final signal remain OFF'),dict(blocker_id='G3-16-008',blocker_name='zip output',status='CLOSED_DISABLED',detail='ZIP output disabled'),dict(blocker_id='G3-16-009',blocker_name='external actions',status='CLOSED',detail='Discord/MT5/AI API/live integrations remain OFF'),dict(blocker_id='G3-16-010',blocker_name='quarantined legacy artifacts',status='CLOSED',detail='GOLD V2 / old GOLD / DISC8 remain quarantined and are not read')]
def report(summary,reviews,h1,rec,blocks):
    lines=['# GOLD V3 16 all replay result review and narrowing audit-only report','',f"Created UTC: `{summary.get('created_at_utc','')}`",f"Status: `{summary.get('status','')}`",'','## Scope','','This stage reviews all seven Stage 15 replay candidates, including the previously deferred/narrowing h1_atr56 TP/SL profiles.','','No final candidate approval, threshold finalization, model training, signal generation, ZIP output, AI API call, Discord notification, MT5 order, live hook, live evaluator, or final signal action was performed.','','## Counts']
    for k in ['stage15_candidate_metric_rows','candidate_rows_reviewed','h1_atr56_profiles_reviewed','keep_main_rows','keep_auxiliary_rows','keep_family_comparison_rows','audited_but_narrow_or_drop_rows']: lines.append(f"- {k}: `{summary.get(k,'')}`")
    lines += ['','## All candidate review','',md_table(reviews,['source_rank','candidate_group_id','profile_id','trades_per_calendar_day_true','win_rate_result_positive','profit_factor','negative_months','max_drawdown_usd','max_consecutive_losses','score_objective_fit','audit_recommendation'],20),'','## h1_atr56 profile comparison','',md_table(h1,H1_FIELDS,20),'','## Narrowing recommendation','',md_table(rec,REC_FIELDS,20),'','## Blockers','',md_table(blocks,BLOCKER_FIELDS,80),'','## Safety','','Stage 16 includes rank 4/6/7/8 in the audit, but still makes no final/live approval. h1_atr56 rows are shared-entry TP/SL/horizon comparisons, not independent entry ideas.']
    return '\n'.join(lines)
def write_all(out,inv,reviews,mon,h1,rec,dec,blocks,summary):
    out.mkdir(parents=True,exist_ok=True)
    write_csv(out/'gold_v3_16_input_inventory.csv',inv,INPUT_FIELDS); write_csv(out/'gold_v3_16_all_candidate_review.csv',reviews,REVIEW_FIELDS); write_csv(out/'gold_v3_16_monthly_robustness_review.csv',mon,MONTHLY_FIELDS); write_csv(out/'gold_v3_16_h1_atr56_profile_comparison.csv',h1,H1_FIELDS); write_csv(out/'gold_v3_16_narrowing_recommendation.csv',rec,REC_FIELDS); write_csv(out/'gold_v3_16_decision_matrix.csv',dec,DECISION_FIELDS); write_csv(out/'gold_v3_16_blocker_matrix.csv',blocks,BLOCKER_FIELDS); write_json(out/'gold_v3_16_summary.json',summary); (out/'GOLD_V3_16_ALL_REPLAY_RESULT_REVIEW_AND_NARROWING_AUDIT_ONLY_REPORT.md').write_text(report(summary,reviews,h1,rec,blocks),encoding='utf-8')
def run(repo:Path):
    repo=repo.resolve(); root,reason=select_root(repo); st15=root/UP15; out=root/OUT_NAME
    paths=dict(summary=st15/'gold_v3_15_summary.json',cand=st15/'gold_v3_15_replay_candidate_metrics.csv',fam=st15/'gold_v3_15_replay_family_metrics.csv',mon=st15/'gold_v3_15_replay_monthly_metrics.csv',ov=st15/'gold_v3_15_replay_overlap_audit.csv')
    inv=inv_rows([('stage15_summary',paths['summary'],True),('candidate_metrics',paths['cand'],True),('family_metrics',paths['fam'],True),('monthly_metrics',paths['mon'],True),('overlap_audit',paths['ov'],True)])
    in_ok=all(bool(r['exists']) for r in inv if r['required'])
    if not in_ok:
        status=BLOCKED; reviews=[]; mon=[]; h1=[]; rec=[]; blocks=blockers(False,False,False); dec=decisions(root,reason,status,reviews,h1); summary=dict(created_at_utc=now(),step=STEP,status=status,blocked_reason='missing Stage 15 required inputs',selected_gold_v3_output_root=str(root),path_resolution_note=reason,stage15_status='',stage15_candidate_metric_rows=0,candidate_rows_reviewed=0,h1_atr56_profiles_reviewed=0,keep_main_rows=0,keep_auxiliary_rows=0,keep_family_comparison_rows=0,audited_but_narrow_or_drop_rows=0,**FALSE_FLAGS); write_all(out,inv,reviews,mon,h1,rec,dec,blocks,summary); print(json.dumps({'status':status,'blocked_reason':summary['blocked_reason'],'output_dir':str(out)},ensure_ascii=False,indent=2)); return 2
    s15=json.loads(paths['summary'].read_text(encoding='utf-8')); up_ok=str(s15.get('status',''))==UP15_READY
    cand=pd.read_csv(paths['cand']); monthly=pd.read_csv(paths['mon']); reviews,mon,h1,rec=build_reviews(cand,monthly)
    review_ok=up_ok and len(reviews)==len(cand) and len(reviews)>=7 and len(h1)>=5
    status=READY if review_ok else BLOCKED; blocks=blockers(up_ok,in_ok,review_ok); dec=decisions(root,reason,status,reviews,h1)
    keep_main=sum(1 for r in reviews if r.get('audit_recommendation') in {'KEEP_MAIN','KEEP_MAIN_WITH_MONTHLY_FILTER_REVIEW'}); keep_aux=sum(1 for r in reviews if r.get('audit_recommendation')=='KEEP_AUXILIARY_FAMILY_BEST'); keep_comp=sum(1 for r in reviews if r.get('audit_recommendation')=='KEEP_FOR_H1_FAMILY_PROFILE_COMPARISON'); audited_drop=sum(1 for r in reviews if r.get('audit_recommendation')=='AUDITED_BUT_NARROW_OR_DROP')
    summary=dict(created_at_utc=now(),step=STEP,status=status,blocked_reason='' if status==READY else 'Stage 16 review checks failed',selected_gold_v3_output_root=str(root),path_resolution_note=reason,stage15_status=str(s15.get('status','')),stage15_candidate_metric_rows=int(len(cand)),candidate_rows_reviewed=len(reviews),h1_atr56_profiles_reviewed=len(h1),keep_main_rows=keep_main,keep_auxiliary_rows=keep_aux,keep_family_comparison_rows=keep_comp,audited_but_narrow_or_drop_rows=audited_drop,all_deferred_profiles_included=True,deferred_profile_scope='rank 4/6/7/8 are included as h1_atr56 family TP/SL comparisons',objective_min_trades_per_day=MIN_TPD,objective_quality_note='prefer high PF/win-rate while preserving >=2 true trades/day',final_candidate_approval=False,threshold_finalization=False,model_training=False,signals_generated=False,zip_output_created=False,old_gold_disc8_quarantined=True,**FALSE_FLAGS)
    write_all(out,inv,reviews,mon,h1,rec,dec,blocks,summary)
    print(json.dumps({'status':status,'candidate_rows_reviewed':len(reviews),'h1_atr56_profiles_reviewed':len(h1),'keep_main_rows':keep_main,'keep_auxiliary_rows':keep_aux,'keep_family_comparison_rows':keep_comp,'audited_but_narrow_or_drop_rows':audited_drop,'output_dir':str(out),'final_candidate_approval':False,'signals_generated':False,'zip_output_created':False},ensure_ascii=False,indent=2)); return 0 if status==READY else 2
def write_exception(repo,exc):
    try: root,reason=select_root(repo.resolve())
    except Exception: root,reason=repo/'Files'/'FX_OUTPUTS'/'gold_v3','exception_fallback'
    out=root/OUT_NAME; out.mkdir(parents=True,exist_ok=True); reason2=f'{exc.__class__.__name__}: {exc}'; blocks=blockers(False,False,False); dec=decisions(root,reason,EXCEPTION,[],[]); summary=dict(created_at_utc=now(),step=STEP,status=EXCEPTION,blocked_reason=reason2,selected_gold_v3_output_root=str(root),path_resolution_note=reason,**FALSE_FLAGS); write_all(out,[],[],[],[],[],dec,blocks,summary); (out/'gold_v3_16_exception.txt').write_text(traceback.format_exc(),encoding='utf-8')
def main(argv=None):
    ap=argparse.ArgumentParser(); ap.add_argument('--repo-root',default=''); a=ap.parse_args(argv); repo=Path(a.repo_root).resolve() if a.repo_root else repo_default()
    try: return run(repo)
    except Exception as e: write_exception(repo,e); print('[GOLD_V3_16] EXCEPTION. See output gold_v3_16_exception.txt',file=sys.stderr); print(traceback.format_exc(),file=sys.stderr); return 1
if __name__=='__main__': raise SystemExit(main())
