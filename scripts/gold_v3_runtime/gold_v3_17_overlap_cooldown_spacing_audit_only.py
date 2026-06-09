#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse, hashlib, json, math, sys, traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import pandas as pd

STEP='GOLD_V3_17_OVERLAP_COOLDOWN_SPACING_AUDIT_ONLY'
OUT_NAME='17_overlap_cooldown_spacing_audit_only'
UP15='15_audit_only_replay_execution'
UP16='16_all_replay_result_review_and_narrowing_audit_only'
UP15_READY='GOLD_V3_15_AUDIT_ONLY_REPLAY_EXECUTION_READY_AUDIT_ONLY'
UP16_READY='GOLD_V3_16_ALL_REPLAY_RESULT_REVIEW_AND_NARROWING_READY_AUDIT_ONLY'
READY='GOLD_V3_17_OVERLAP_COOLDOWN_SPACING_READY_AUDIT_ONLY'
BLOCKED='GOLD_V3_17_OVERLAP_COOLDOWN_SPACING_BLOCKED_AUDIT_ONLY'
EXCEPTION='GOLD_V3_17_OVERLAP_COOLDOWN_SPACING_EXCEPTION_AUDIT_ONLY'
CDS=[0,15,30,60,120,240,480,720,1440]
OBJ_TPD=2.0
FALSE_FLAGS=dict(auto_approval=False,final_candidate_approval=False,threshold_finalization=False,model_training=False,signals_generated=False,zip_output_created=False,ai_api_called=False,discord_enabled=False,mt5_enabled=False,live_hook_enabled=False,live_evaluator_enabled=False,final_signal_enabled=False,gold_v2_live_sot_used=False,quarantined_legacy_artifacts_read=False)


def now(): return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')
def repo_default(): return Path(__file__).resolve().parents[2]
def files_root(repo:Path)->Path: return repo.parents[1] if len(repo.parents)>=2 else repo.parent
def v3_candidates(repo:Path):
    a=files_root(repo)/'FX_OUTPUTS'/'gold_v3'; b=repo/'Files'/'FX_OUTPUTS'/'gold_v3'; return [a] if a==b else [a,b]
def select_root(repo:Path):
    for p in v3_candidates(repo):
        if (p/UP16/'gold_v3_16_summary.json').exists(): return p,'selected_existing_stage16_root'
    for p in v3_candidates(repo):
        if (p/UP15/'gold_v3_15_summary.json').exists(): return p,'selected_existing_stage15_root'
    return v3_candidates(repo)[0],'selected_primary_gold_v3_root_no_stage15_or_stage16_inputs_found'
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
def write_df(p:Path,df:pd.DataFrame): p.parent.mkdir(parents=True,exist_ok=True); df.to_csv(p,index=False,encoding='utf-8-sig')
def inv(items):
    rows=[]
    for label,p,req in items:
        rows.append(dict(input_label=label,path=str(p),required=req,exists=p.exists(),size_bytes=p.stat().st_size if p.exists() else '',sha256=sha256_file(p) if p.exists() else ''))
    return pd.DataFrame(rows)
def flt(x,default=0.0):
    s=str(x).strip() if x is not None else ''
    if not s or s.lower() in {'nan','none'}: return default
    if s.upper().startswith('INF'): return 999999.0
    try: return float(s)
    except Exception: return default
def pf_disp(gp,gl):
    if gl>0: return round(gp/gl,10)
    if gp>0: return 'INF_NO_LOSS'
    return ''
def pf_sort(v):
    if str(v).upper().startswith('INF'): return 999999.0
    return flt(v,-1.0)
def max_loss_streak(vals):
    best=cur=0
    for v in vals:
        if v<0: cur+=1; best=max(best,cur)
        else: cur=0
    return best

def cooldown(df:pd.DataFrame, minutes:int)->pd.DataFrame:
    if df.empty: return df.copy()
    w=df.copy(); w['_dt']=pd.to_datetime(w['entry_time_utc'],utc=True,errors='coerce')
    w=w[w['_dt'].notna()].sort_values(['_dt','priority','source_rank'],kind='mergesort')
    if minutes<=0: return w.drop_duplicates(subset=['entry_time_utc'],keep='first').drop(columns=['_dt'],errors='ignore')
    ns=w['_dt'].astype('int64').to_numpy(); step=int(minutes)*60*1_000_000_000; keep=[]; last=None
    for i,t in enumerate(ns):
        if last is None or t>=last+step: keep.append(i); last=t
    return w.iloc[keep].drop(columns=['_dt'],errors='ignore')

def metric(df, scope, sid, cd, before, policy, rank='', group='', profile='', ranks=''):
    base=dict(scope=scope,scenario_id=sid,cooldown_minutes=cd,source_rank=rank,candidate_group_id=group,profile_id=profile,scenario_ranks=ranks,selection_policy=policy,rows_before_spacing=before)
    if df.empty:
        return base|dict(rows_after_spacing=0,unique_entry_times_after_spacing=0,calendar_days=0,active_days=0,trades_per_calendar_day=0.0,trades_per_active_day=0.0,win_rate_result_positive=0.0,profit_factor='',sum_result_usd=0.0,avg_result_usd=0.0,median_result_usd=0.0,gross_profit_usd=0.0,gross_loss_abs_usd=0.0,max_drawdown_usd=0.0,max_consecutive_losses=0,tp_count=0,sl_count=0,timeout_count=0,best_trade_usd=0.0,worst_trade_usd=0.0,first_entry_time_utc='',last_entry_time_utc='',objective_2_trades_per_day_pass=False,score_spacing_objective=0.0)
    w=df.copy(); w['_dt']=pd.to_datetime(w['entry_time_utc'],utc=True,errors='coerce'); w=w.sort_values(['_dt','priority','source_rank'],kind='mergesort')
    res=pd.to_numeric(w['label_price_distance_result_usd'],errors='coerce').fillna(0.0); dt=w['_dt'].dropna(); n=len(w)
    cal=(dt.max().date()-dt.min().date()).days+1 if not dt.empty else 0; active=dt.dt.date.nunique() if not dt.empty else 0
    gp=float(res[res>0].sum()); gl=float(-res[res<0].sum()); pf=pf_disp(gp,gl); cum=res.cumsum(); dd=float((cum.cummax()-cum).max()) if len(cum) else 0.0
    tpd=float(n/cal) if cal else 0.0; wr=float((res>0).sum()/n) if n else 0.0; streak=max_loss_streak(res.tolist())
    score=round(35*min(pf_sort(pf)/1.5,1.5)+25*min(wr/0.58,1.3)+20*min(tpd/OBJ_TPD,3)/3+10*max(0,1-min(dd/20000,1))+10*max(0,1-min(streak/180,1)),6)
    return base|dict(rows_after_spacing=n,unique_entry_times_after_spacing=int(w['entry_time_utc'].astype(str).nunique()),calendar_days=int(cal),active_days=int(active),trades_per_calendar_day=round(tpd,10),trades_per_active_day=round(float(n/active),10) if active else 0.0,win_rate_result_positive=round(wr,10),profit_factor=pf,sum_result_usd=round(float(res.sum()),10),avg_result_usd=round(float(res.mean()),10),median_result_usd=round(float(res.median()),10),gross_profit_usd=round(gp,10),gross_loss_abs_usd=round(gl,10),max_drawdown_usd=round(dd,10),max_consecutive_losses=streak,tp_count=int((w['label_outcome'].astype(str)=='TP').sum()),sl_count=int((w['label_outcome'].astype(str)=='SL').sum()),timeout_count=int((w['label_outcome'].astype(str)=='TIMEOUT').sum()),best_trade_usd=round(float(res.max()),10),worst_trade_usd=round(float(res.min()),10),first_entry_time_utc=str(dt.min()) if not dt.empty else '',last_entry_time_utc=str(dt.max()) if not dt.empty else '',objective_2_trades_per_day_pass=tpd>=OBJ_TPD,score_spacing_objective=score)

def scen_defs():
    return [('MAIN_R1_R2',[1,2],'portfolio_priority_by_stage16_score'),('MAIN_R1_R2_PLUS_H1_BEST_R3',[1,2,3],'portfolio_priority_by_stage16_score'),('MAIN_R1_R2_PLUS_H1_R4',[1,2,4],'portfolio_priority_by_stage16_score'),('MAIN_R1_R2_PLUS_H1_R6',[1,2,6],'portfolio_priority_by_stage16_score'),('H1_ONLY_R3',[3],'single_h1_profile'),('H1_ONLY_R4',[4],'single_h1_profile'),('H1_ONLY_R6',[6],'single_h1_profile'),('H1_ONLY_R7',[7],'weak_h1_profile_diagnostic'),('H1_ONLY_R8',[8],'weak_h1_profile_diagnostic'),('ALL_7_DIAGNOSTIC_PRIORITY_DEDUP',[1,2,3,4,6,7,8],'diagnostic_only_priority_dedup_not_live_approval')]

def overlap(df, sid, rank='', group='', profile=''):
    if df.empty: return dict(scenario_id=sid,source_rank=rank,candidate_group_id=group,profile_id=profile,rows=0,unique_entry_times=0,entry_times_with_multiple_rows=0,max_rows_same_entry_time=0,entry_times_with_multiple_source_ranks=0,entry_times_with_multiple_entry_families=0,h1_atr56_duplicate_entry_times=0,overlap_note='no rows')
    g=df.groupby('entry_time_utc'); rc=g.size(); rankc=g['source_rank'].nunique(); famc=g['entry_family_key'].nunique() if 'entry_family_key' in df.columns else rc*0
    h1=df[df['candidate_group_id'].astype(str).eq('GROUP_H1_ATR56_HIGH_VOL')]; h1dup=0 if h1.empty else int((h1.groupby('entry_time_utc')['source_rank'].nunique()>1).sum())
    return dict(scenario_id=sid,source_rank=rank,candidate_group_id=group,profile_id=profile,rows=len(df),unique_entry_times=int(df['entry_time_utc'].astype(str).nunique()),entry_times_with_multiple_rows=int((rc>1).sum()),max_rows_same_entry_time=int(rc.max()),entry_times_with_multiple_source_ranks=int((rankc>1).sum()),entry_times_with_multiple_entry_families=int((famc>1).sum()),h1_atr56_duplicate_entry_times=h1dup,overlap_note='same timestamp duplicates are expected for h1_atr56 TP/SL profiles; portfolio scenarios keep priority winner before cooldown')

def recs(cand, port):
    rows=[]
    c=cand[cand['objective_2_trades_per_day_pass'].astype(bool)].copy(); c['pf_sort']=c['profit_factor'].map(pf_sort); c=c.sort_values(['score_spacing_objective','pf_sort','win_rate_result_positive'],ascending=[False,False,False]).head(12)
    for _,r in c.iterrows(): rows.append(dict(recommendation_tier='CANDIDATE_COOLDOWN_KEEP_REVIEW' if int(r.source_rank) in {1,2,3,4,6} else 'WEAK_PROFILE_COOLDOWN_DIAGNOSTIC',scenario_id=r.scenario_id,cooldown_minutes=int(r.cooldown_minutes),source_rank=r.source_rank,candidate_group_id=r.candidate_group_id,profile_id=r.profile_id,trades_per_calendar_day=r.trades_per_calendar_day,win_rate_result_positive=r.win_rate_result_positive,profit_factor=r.profit_factor,max_drawdown_usd=r.max_drawdown_usd,max_consecutive_losses=r.max_consecutive_losses,sum_result_usd=r.sum_result_usd,reason='candidate-level spacing keeps >=2 trades/day; review PF/win-rate/DD/streak tradeoff',next_audit_action='compare against portfolio spacing and monthly stability'))
    p=port[port['objective_2_trades_per_day_pass'].astype(bool)].copy(); p['pf_sort']=p['profit_factor'].map(pf_sort); p=p.sort_values(['score_spacing_objective','pf_sort','win_rate_result_positive'],ascending=[False,False,False]).head(10)
    for _,r in p.iterrows(): rows.append(dict(recommendation_tier='PORTFOLIO_SPACING_KEEP_REVIEW',scenario_id=r.scenario_id,cooldown_minutes=int(r.cooldown_minutes),source_rank='',candidate_group_id='',profile_id='',trades_per_calendar_day=r.trades_per_calendar_day,win_rate_result_positive=r.win_rate_result_positive,profit_factor=r.profit_factor,max_drawdown_usd=r.max_drawdown_usd,max_consecutive_losses=r.max_consecutive_losses,sum_result_usd=r.sum_result_usd,reason='portfolio priority+cooldown scenario; not final approval',next_audit_action='next stage should inspect top scenarios by month and decide final audit shortlist'))
    return pd.DataFrame(rows)

def md(x): return str(x).replace('\n',' ').replace('\r',' ').replace('|','/')
def md_table(df, cols, limit=30):
    if df.empty: return '_No rows._'
    out=['| '+' | '.join(cols)+' |','| '+' | '.join(['---']*len(cols))+' |']
    for _,r in df.head(limit).iterrows(): out.append('| '+' | '.join(md(r.get(c,''))[:500] for c in cols)+' |')
    return '\n'.join(out)

def blockers(up15,up16,in_ok,metrics_ok):
    return pd.DataFrame([('G3-17-001','stage-15 inputs','CLOSED' if up15 and in_ok else 'OPEN_BLOCKER','Stage 15 READY trade ledger and metrics are required'),('G3-17-002','stage-16 inputs','CLOSED' if up16 and in_ok else 'OPEN_BLOCKER','Stage 16 READY all candidate review is required'),('G3-17-003','all candidate inclusion','CLOSED' if metrics_ok else 'OPEN_BLOCKER','rank 1/2/3/4/6/7/8 must be included in cooldown/spacing audit'),('G3-17-004','h1_atr56 weak profiles','CLOSED' if metrics_ok else 'OPEN_BLOCKER','rank 7/8 are included as weak comparison profiles, not silently dropped'),('G3-17-005','final approval','CLOSED_BLOCKED_BY_POLICY','Stage 17 does not approve final candidates'),('G3-17-006','threshold finalization','CLOSED_BLOCKED_BY_POLICY','Stage 17 does not finalize thresholds'),('G3-17-007','model training','CLOSED_BLOCKED_BY_POLICY','Stage 17 does not train models'),('G3-17-008','signal/live','CLOSED_BLOCKED_BY_POLICY','signal/live/final signal remain OFF'),('G3-17-009','zip output','CLOSED_DISABLED','ZIP output disabled'),('G3-17-010','external actions','CLOSED','Discord/MT5/AI/live integrations remain OFF'),('G3-17-011','quarantined legacy artifacts','CLOSED','GOLD V2 / old GOLD / DISC8 remain quarantined and are not read')],columns=['blocker_id','blocker_name','status','detail'])

def report(summary,cand,port,ov,rec,blocks):
    lines=['# GOLD V3 17 overlap cooldown spacing audit-only report','',f"Created UTC: `{summary.get('created_at_utc','')}`",f"Status: `{summary.get('status','')}`",'','## Scope','','This stage audits overlap, duplicate timestamps, cooldown, and spacing across all Stage 16 reviewed candidates, including rank 7/8 as weak comparison profiles.','','No final candidate approval, threshold finalization, model training, signal generation, ZIP output, AI API call, Discord notification, MT5 order, live hook, live evaluator, or final signal action was performed.','','## Counts']
    for k in ['trade_ledger_rows','candidate_cooldown_metric_rows','portfolio_spacing_metric_rows','overlap_audit_rows','recommendation_rows','candidate_rows_reviewed','h1_atr56_profiles_reviewed']: lines.append(f"- {k}: `{summary.get(k,'')}`")
    lines+=['','## Top candidate cooldown metrics','',md_table(cand.sort_values(['score_spacing_objective'],ascending=False),['source_rank','profile_id','cooldown_minutes','trades_per_calendar_day','win_rate_result_positive','profit_factor','max_drawdown_usd','max_consecutive_losses','score_spacing_objective']),'','## Top portfolio spacing metrics','',md_table(port.sort_values(['score_spacing_objective'],ascending=False),['scenario_id','cooldown_minutes','trades_per_calendar_day','win_rate_result_positive','profit_factor','max_drawdown_usd','max_consecutive_losses','score_spacing_objective']),'','## Overlap diagnostics','',md_table(ov,['scenario_id','source_rank','candidate_group_id','profile_id','rows','unique_entry_times','entry_times_with_multiple_rows','max_rows_same_entry_time','entry_times_with_multiple_source_ranks','entry_times_with_multiple_entry_families','h1_atr56_duplicate_entry_times','overlap_note'],20),'','## Recommendations','',md_table(rec,['recommendation_tier','scenario_id','cooldown_minutes','source_rank','candidate_group_id','profile_id','trades_per_calendar_day','win_rate_result_positive','profit_factor','max_drawdown_usd','max_consecutive_losses','sum_result_usd','reason','next_audit_action']),'','## Blockers','',md_table(blocks,['blocker_id','blocker_name','status','detail'],80),'','## Safety','','Stage 17 is audit-only. It may recommend cooldown/spacing scenarios, but it does not approve final candidates or enable live behavior.']
    return '\n'.join(lines)

def run(repo:Path):
    repo=repo.resolve(); root,reason=select_root(repo); d15=root/UP15; d16=root/UP16; out=root/OUT_NAME
    paths=dict(s15=d15/'gold_v3_15_summary.json',ledger=d15/'gold_v3_15_replay_trade_ledger.csv',c15=d15/'gold_v3_15_replay_candidate_metrics.csv',s16=d16/'gold_v3_16_summary.json',review=d16/'gold_v3_16_all_candidate_review.csv',h1=d16/'gold_v3_16_h1_atr56_profile_comparison.csv')
    invdf=inv([('stage15_summary',paths['s15'],True),('stage15_trade_ledger',paths['ledger'],True),('stage15_candidate_metrics',paths['c15'],True),('stage16_summary',paths['s16'],True),('stage16_all_candidate_review',paths['review'],True),('stage16_h1_atr56_profile_comparison',paths['h1'],True)])
    out.mkdir(parents=True,exist_ok=True); in_ok=bool(invdf[invdf.required.astype(bool)].exists.all())
    if not in_ok: raise RuntimeError('missing required Stage 15/16 inputs')
    s15=json.loads(paths['s15'].read_text(encoding='utf-8')); s16=json.loads(paths['s16'].read_text(encoding='utf-8')); up15=s15.get('status')==UP15_READY; up16=s16.get('status')==UP16_READY
    ledger=pd.read_csv(paths['ledger']); review=pd.read_csv(paths['review']); h1=pd.read_csv(paths['h1'])
    ranks=sorted(set(pd.to_numeric(review['source_rank'],errors='coerce').dropna().astype(int).tolist()))
    prio={int(r.source_rank):i+1 for i,r in enumerate(review.sort_values(['score_objective_fit','profit_factor','win_rate_result_positive'],ascending=[False,False,False]).itertuples())}
    ledger['source_rank']=pd.to_numeric(ledger['source_rank'],errors='coerce').astype(int); ledger['priority']=ledger['source_rank'].map(prio).fillna(999).astype(int)
    cand_rows=[]; ov_rows=[]
    for rank in ranks:
        part=ledger[ledger.source_rank.eq(rank)].copy(); meta=review[review.source_rank.eq(rank)].iloc[0].to_dict(); ov_rows.append(overlap(part,f'CANDIDATE_R{rank}',rank,meta.get('candidate_group_id',''),meta.get('profile_id','')))
        for cd in CDS: cand_rows.append(metric(cooldown(part,cd),'candidate',f'CANDIDATE_R{rank}',cd,len(part),'candidate_local_cooldown',rank,meta.get('candidate_group_id',''),meta.get('profile_id',''),str(rank)))
    port_rows=[]
    for sid,rs,pol in scen_defs():
        part=ledger[ledger.source_rank.isin(rs)].copy(); ov_rows.append(overlap(part,sid,'','',''))
        for cd in CDS: port_rows.append(metric(cooldown(part,cd),'portfolio',sid,cd,len(part),pol,'','','',','.join(map(str,rs))))
    cand=pd.DataFrame(cand_rows); port=pd.DataFrame(port_rows); ov=pd.DataFrame(ov_rows); rec=recs(cand,port)
    metrics_ok=up15 and up16 and len(cand)==len(ranks)*len(CDS) and len(port)==len(scen_defs())*len(CDS) and {7,8}.issubset(set(ranks)) and len(h1)>=5
    status=READY if metrics_ok else BLOCKED; blocks=blockers(up15,up16,in_ok,metrics_ok)
    decisions=pd.DataFrame([('selected_gold_v3_output_root',str(root),reason),('status',status,'overlap/cooldown/spacing audit-only status'),('candidate_cooldown_metric_rows',len(cand),'candidate-by-candidate cooldown metrics'),('portfolio_spacing_metric_rows',len(port),'portfolio scenario cooldown metrics'),('final_candidate_approval',False,'blocked by policy'),('threshold_finalization',False,'blocked by policy'),('model_training',False,'blocked by policy'),('signals_generated',False,'blocked by policy'),('zip_output_created',False,'disabled'),('external_actions',False,'Discord/MT5/AI/live integrations remain OFF')],columns=['decision_key','value','detail'])
    summary=dict(created_at_utc=now(),step=STEP,status=status,blocked_reason='' if status==READY else 'Stage 17 metrics checks failed',selected_gold_v3_output_root=str(root),path_resolution_note=reason,stage15_status=str(s15.get('status','')),stage16_status=str(s16.get('status','')),trade_ledger_rows=int(len(ledger)),candidate_rows_reviewed=int(len(ranks)),h1_atr56_profiles_reviewed=int(len(h1)),cooldown_minutes_tested=CDS,candidate_cooldown_metric_rows=int(len(cand)),portfolio_spacing_metric_rows=int(len(port)),overlap_audit_rows=int(len(ov)),recommendation_rows=int(len(rec)),rank_7_8_included=True,objective_min_trades_per_day=OBJ_TPD,replay_scope='audit-only spacing/cooldown over Stage15 ledger and Stage16 review; not live',old_gold_disc8_quarantined=True,**FALSE_FLAGS)
    write_df(out/'gold_v3_17_input_inventory.csv',invdf); write_df(out/'gold_v3_17_candidate_cooldown_metrics.csv',cand); write_df(out/'gold_v3_17_portfolio_spacing_metrics.csv',port); write_df(out/'gold_v3_17_overlap_diagnostics.csv',ov); write_df(out/'gold_v3_17_spacing_recommendation.csv',rec); write_df(out/'gold_v3_17_decision_matrix.csv',decisions); write_df(out/'gold_v3_17_blocker_matrix.csv',blocks); write_json(out/'gold_v3_17_summary.json',summary); (out/'GOLD_V3_17_OVERLAP_COOLDOWN_SPACING_AUDIT_ONLY_REPORT.md').write_text(report(summary,cand,port,ov,rec,blocks),encoding='utf-8')
    print(json.dumps({'status':status,'candidate_cooldown_metric_rows':len(cand),'portfolio_spacing_metric_rows':len(port),'overlap_audit_rows':len(ov),'recommendation_rows':len(rec),'rank_7_8_included':True,'output_dir':str(out),'final_candidate_approval':False,'signals_generated':False,'zip_output_created':False},ensure_ascii=False,indent=2)); return 0 if status==READY else 2

def write_exception(repo,exc):
    try: root,reason=select_root(repo.resolve())
    except Exception: root,reason=repo/'Files'/'FX_OUTPUTS'/'gold_v3','exception_fallback'
    out=root/OUT_NAME; out.mkdir(parents=True,exist_ok=True); summary=dict(created_at_utc=now(),step=STEP,status=EXCEPTION,blocked_reason=f'{exc.__class__.__name__}: {exc}',selected_gold_v3_output_root=str(root),path_resolution_note=reason,**FALSE_FLAGS); write_json(out/'gold_v3_17_summary.json',summary); (out/'gold_v3_17_exception.txt').write_text(traceback.format_exc(),encoding='utf-8')

def main(argv=None):
    ap=argparse.ArgumentParser(); ap.add_argument('--repo-root',default=''); a=ap.parse_args(argv); repo=Path(a.repo_root).resolve() if a.repo_root else repo_default()
    try: return run(repo)
    except Exception as e: write_exception(repo,e); print('[GOLD_V3_17] EXCEPTION. See output gold_v3_17_exception.txt',file=sys.stderr); print(traceback.format_exc(),file=sys.stderr); return 1
if __name__=='__main__': raise SystemExit(main())
