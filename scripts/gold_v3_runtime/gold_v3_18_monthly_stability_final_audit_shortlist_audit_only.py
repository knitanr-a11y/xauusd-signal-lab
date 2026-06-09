#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse, json, math, sys, traceback
from pathlib import Path
import pandas as pd
import gold_v3_17_overlap_cooldown_spacing_audit_only as st17

STEP='GOLD_V3_18_MONTHLY_STABILITY_FINAL_AUDIT_SHORTLIST_AUDIT_ONLY'
OUT_NAME='18_monthly_stability_final_audit_shortlist_audit_only'
UP15='15_audit_only_replay_execution'; UP16='16_all_replay_result_review_and_narrowing_audit_only'; UP17='17_overlap_cooldown_spacing_audit_only'
UP15_READY='GOLD_V3_15_AUDIT_ONLY_REPLAY_EXECUTION_READY_AUDIT_ONLY'
UP16_READY='GOLD_V3_16_ALL_REPLAY_RESULT_REVIEW_AND_NARROWING_READY_AUDIT_ONLY'
UP17_READY='GOLD_V3_17_OVERLAP_COOLDOWN_SPACING_READY_AUDIT_ONLY'
READY='GOLD_V3_18_MONTHLY_STABILITY_FINAL_AUDIT_SHORTLIST_READY_AUDIT_ONLY'
BLOCKED='GOLD_V3_18_MONTHLY_STABILITY_FINAL_AUDIT_SHORTLIST_BLOCKED_AUDIT_ONLY'
EXCEPTION='GOLD_V3_18_MONTHLY_STABILITY_FINAL_AUDIT_SHORTLIST_EXCEPTION_AUDIT_ONLY'
OBJ_TPD=2.0
FALSE_FLAGS=st17.FALSE_FLAGS.copy()
SHORTLIST=[('PRIMARY_MAIN_BALANCED','MAIN_R1_R2',60,[1,2],'FINAL_AUDIT_PRIMARY_BALANCED'),('PRIMARY_MAIN_CONSERVATIVE','MAIN_R1_R2',120,[1,2],'FINAL_AUDIT_PRIMARY_CONSERVATIVE'),('PRIMARY_MAIN_AGGRESSIVE','MAIN_R1_R2',30,[1,2],'FINAL_AUDIT_PRIMARY_AGGRESSIVE'),('AUX_H1_BEST_R3','MAIN_R1_R2_PLUS_H1_BEST_R3',120,[1,2,3],'AUXILIARY_REVIEW'),('AUX_H1_R4','MAIN_R1_R2_PLUS_H1_R4',120,[1,2,4],'AUXILIARY_REVIEW'),('AUX_H1_R6','MAIN_R1_R2_PLUS_H1_R6',120,[1,2,6],'AUXILIARY_REVIEW'),('DIAG_H1_ONLY_R3','H1_ONLY_R3',120,[3],'H1_DIAGNOSTIC'),('DIAG_H1_ONLY_R4','H1_ONLY_R4',120,[4],'H1_DIAGNOSTIC'),('DIAG_H1_ONLY_R6','H1_ONLY_R6',120,[6],'H1_DIAGNOSTIC'),('WEAK_DIAG_H1_ONLY_R7','H1_ONLY_R7',120,[7],'WEAK_PROFILE_DIAGNOSTIC'),('WEAK_DIAG_H1_ONLY_R8','H1_ONLY_R8',120,[8],'WEAK_PROFILE_DIAGNOSTIC')]

def repo_default(): return Path(__file__).resolve().parents[2]
def flt(x,d=0.0):
    s=str(x).strip() if x is not None else ''
    if not s or s.lower() in {'nan','none'}: return d
    if s.upper().startswith('INF'): return 999999.0
    try: return float(s)
    except Exception: return d
def pf(res):
    gp=float(res[res>0].sum()); gl=float(-res[res<0].sum())
    return ('INF_NO_LOSS' if gl==0 and gp>0 else (round(gp/gl,10) if gl>0 else ''), gp, gl)
def pfnum(v): return 999999.0 if str(v).upper().startswith('INF') else flt(v)
def streak(vals):
    best=cur=0
    for v in vals:
        if v<0: cur+=1; best=max(best,cur)
        else: cur=0
    return best
def inv(items):
    return pd.DataFrame([dict(input_label=label,path=str(p),required=req,exists=p.exists(),size_bytes=p.stat().st_size if p.exists() else '',sha256=st17.sha256_file(p) if p.exists() else '') for label,p,req in items])
def dedup_cooldown(df, minutes):
    if df.empty: return df.copy()
    w=df.copy(); w['_dt']=pd.to_datetime(w.entry_time_utc,utc=True,errors='coerce')
    w=w[w._dt.notna()].sort_values(['_dt','priority','source_rank'],kind='mergesort').drop_duplicates('entry_time_utc',keep='first')
    if minutes<=0: return w.drop(columns=['_dt'],errors='ignore')
    ns=w._dt.astype('int64').to_numpy(); step=int(minutes)*60*1_000_000_000; keep=[]; last=None
    for i,t in enumerate(ns):
        if last is None or t>=last+step: keep.append(i); last=t
    return w.iloc[keep].drop(columns=['_dt'],errors='ignore')
def metrics(df):
    if df.empty:
        return dict(rows=0,calendar_days=0,active_days=0,trades_per_calendar_day=0,win_rate_result_positive=0,profit_factor='',sum_result_usd=0,avg_result_usd=0,max_drawdown_usd=0,max_consecutive_losses=0,tp_count=0,sl_count=0,timeout_count=0,first_entry_time_utc='',last_entry_time_utc='')
    w=df.copy(); dt=pd.to_datetime(w.entry_time_utc,utc=True,errors='coerce'); res=pd.to_numeric(w.label_price_distance_result_usd,errors='coerce').fillna(0.0); n=len(w); d=dt.dropna()
    cal=(d.max().date()-d.min().date()).days+1 if not d.empty else 0; p,gp,gl=pf(res); cum=res.cumsum(); dd=float((cum.cummax()-cum).max()) if len(cum) else 0
    return dict(rows=n,calendar_days=int(cal),active_days=int(d.dt.date.nunique()) if not d.empty else 0,trades_per_calendar_day=round(n/cal,10) if cal else 0,win_rate_result_positive=round(float((res>0).sum()/n),10) if n else 0,profit_factor=p,sum_result_usd=round(float(res.sum()),10),avg_result_usd=round(float(res.mean()),10),max_drawdown_usd=round(dd,10),max_consecutive_losses=streak(res.tolist()),tp_count=int((w.label_outcome.astype(str)=='TP').sum()),sl_count=int((w.label_outcome.astype(str)=='SL').sum()),timeout_count=int((w.label_outcome.astype(str)=='TIMEOUT').sum()),first_entry_time_utc=str(d.min()) if not d.empty else '',last_entry_time_utc=str(d.max()) if not d.empty else '')
def evaluate(sk,sid,cd,ranks,tier,df,months):
    rows=[]
    for m in months:
        part=df[df.entry_month.astype(str).eq(str(m))]; mt=metrics(part)
        if mt['rows']==0: bucket='NO_TRADE_MONTH'
        elif flt(mt['sum_result_usd'])<0: bucket='NEGATIVE_MONTH'
        elif flt(mt['sum_result_usd'])>0: bucket='POSITIVE_MONTH'
        else: bucket='FLAT_MONTH'
        mt.update(dict(scenario_key=sk,scenario_id=sid,cooldown_minutes=cd,shortlist_tier=tier,scenario_ranks=','.join(map(str,ranks)),entry_month=m,month_result_bucket=bucket)); rows.append(mt)
    allm=metrics(df); sums=[flt(r['sum_result_usd']) for r in rows]; pfs=[pfnum(r['profit_factor']) for r in rows if r['rows']>0]; wrs=[flt(r['win_rate_result_positive']) for r in rows if r['rows']>0]
    neg=sum(v<0 for v in sums); total=len(rows) or 1
    allm.update(dict(scenario_key=sk,scenario_id=sid,cooldown_minutes=cd,shortlist_tier=tier,scenario_ranks=','.join(map(str,ranks)),month_count=len(rows),positive_months=sum(v>0 for v in sums),negative_months=int(neg),no_trade_months=sum(r['rows']==0 for r in rows),negative_month_rate=round(neg/total,10),worst_month_sum=round(min(sums) if sums else 0,10),best_month_sum=round(max(sums) if sums else 0,10),median_month_sum=round(float(pd.Series(sums).median()) if sums else 0,10),median_month_pf=round(float(pd.Series(pfs).median()) if pfs else 0,10),min_month_pf=round(float(min(pfs)) if pfs else 0,10),median_month_win_rate=round(float(pd.Series(wrs).median()) if wrs else 0,10),objective_2_trades_per_day_pass=allm['trades_per_calendar_day']>=OBJ_TPD))
    score=35*min(pfnum(allm['profit_factor'])/1.6,1.4)+25*min(flt(allm['win_rate_result_positive'])/0.6,1.25)+15*min(flt(allm['trades_per_calendar_day'])/OBJ_TPD,3)/3+15*max(0,1-allm['negative_month_rate'])+5*max(0,1-min(flt(allm['max_drawdown_usd'])/8000,1))+5*max(0,1-min(flt(allm['max_consecutive_losses'])/80,1))
    allm['score_monthly_shortlist']=round(score,6)
    if tier.startswith('FINAL_AUDIT_PRIMARY') and allm['objective_2_trades_per_day_pass'] and pfnum(allm['profit_factor'])>=1.55 and flt(allm['win_rate_result_positive'])>=0.58 and neg<=3: rec='KEEP_FINAL_AUDIT_SHORTLIST'
    elif tier=='AUXILIARY_REVIEW' and allm['objective_2_trades_per_day_pass'] and pfnum(allm['profit_factor'])>=1.38 and flt(allm['win_rate_result_positive'])>=0.52: rec='KEEP_AUXILIARY_SHORTLIST'
    elif tier=='H1_DIAGNOSTIC': rec='H1_DIAGNOSTIC_ONLY'
    else: rec='DROP_OR_FILTER_RESCUE_ONLY'
    allm['audit_recommendation']=rec; allm['audit_reason']='monthly stability audit only; not final/live approval'
    return allm, rows
def blockers(ok15,ok16,ok17,in_ok,metrics_ok):
    return pd.DataFrame([('G3-18-001','stage-15 ledger','CLOSED' if ok15 and in_ok else 'OPEN_BLOCKER','Stage 15 READY ledger is required'),('G3-18-002','stage-16 review','CLOSED' if ok16 and in_ok else 'OPEN_BLOCKER','Stage 16 READY all-candidate review is required'),('G3-18-003','stage-17 spacing','CLOSED' if ok17 and in_ok else 'OPEN_BLOCKER','Stage 17 READY spacing metrics are required'),('G3-18-004','monthly scenario metrics','CLOSED' if metrics_ok else 'OPEN_BLOCKER','shortlist scenarios must produce monthly stability rows'),('G3-18-005','rank 7/8 handling','CLOSED' if metrics_ok else 'OPEN_BLOCKER','rank 7/8 are diagnostic/drop-bias rows, not silently ignored'),('G3-18-006','final approval','CLOSED_BLOCKED_BY_POLICY','Stage 18 does not approve final candidates'),('G3-18-007','threshold finalization','CLOSED_BLOCKED_BY_POLICY','Stage 18 does not finalize thresholds'),('G3-18-008','model training','CLOSED_BLOCKED_BY_POLICY','Stage 18 does not train models'),('G3-18-009','signal/live','CLOSED_BLOCKED_BY_POLICY','signal/live/final signal remain OFF'),('G3-18-010','zip output','CLOSED_DISABLED','ZIP output disabled'),('G3-18-011','external actions','CLOSED','Discord/MT5/AI/live integrations remain OFF'),('G3-18-012','legacy quarantine','CLOSED','GOLD V2 / old GOLD / DISC8 not read')],columns=['blocker_id','blocker_name','status','detail'])
def md(x): return str(x).replace('\n',' ').replace('\r',' ').replace('|','/')
def md_table(df,cols,limit=30):
    if df.empty: return '_No rows._'
    out=['| '+' | '.join(cols)+' |','| '+' | '.join(['---']*len(cols))+' |']
    for _,r in df.head(limit).iterrows(): out.append('| '+' | '.join(md(r.get(c,''))[:500] for c in cols)+' |')
    return '\n'.join(out)
def make_report(summary,stab,rankret,rec,blocks):
    lines=['# GOLD V3 18 monthly stability final audit shortlist audit-only report','',f"Created UTC: `{summary.get('created_at_utc','')}`",f"Status: `{summary.get('status','')}`",'','## Scope','','This stage audits monthly stability for Stage 17 shortlist scenarios. It creates an audit shortlist only; it is not final approval and not live approval.','','## Counts']
    for k in ['shortlist_scenario_rows','monthly_metric_rows','rank_retention_rows','keep_final_audit_shortlist_rows','keep_auxiliary_shortlist_rows','drop_or_filter_rescue_only_rows']: lines.append(f"- {k}: `{summary.get(k,'')}`")
    lines+=['','## Scenario stability summary','',md_table(stab.sort_values('score_monthly_shortlist',ascending=False),['scenario_key','scenario_id','cooldown_minutes','shortlist_tier','trades_per_calendar_day','win_rate_result_positive','profit_factor','sum_result_usd','negative_months','worst_month_sum','max_drawdown_usd','max_consecutive_losses','score_monthly_shortlist','audit_recommendation']),'','## Shortlist recommendation','',md_table(rec,['recommendation_tier','scenario_key','scenario_id','cooldown_minutes','shortlist_tier','reason','next_audit_action']),'','## Rank retention / rank 7-8 handling','',md_table(rankret,['source_rank','candidate_group_id','profile_id','stage16_recommendation','stage18_retention_role','rank_7_8_not_silently_dropped']),'','## Blockers','',md_table(blocks,['blocker_id','blocker_name','status','detail'],80),'','## Safety','','Stage 18 does not approve final candidates, finalize thresholds, train models, generate signals, create ZIP output, call AI API, notify Discord, place MT5 orders, or enable live hooks/evaluators/final signals.']
    return '\n'.join(lines)
def run(repo:Path):
    repo=repo.resolve(); root,reason=st17.select_root(repo); out=root/OUT_NAME; d15=root/UP15; d16=root/UP16; d17=root/UP17
    paths=dict(s15=d15/'gold_v3_15_summary.json',ledger=d15/'gold_v3_15_replay_trade_ledger.csv',s16=d16/'gold_v3_16_summary.json',review=d16/'gold_v3_16_all_candidate_review.csv',s17=d17/'gold_v3_17_summary.json',port=d17/'gold_v3_17_portfolio_spacing_metrics.csv',cand=d17/'gold_v3_17_candidate_cooldown_metrics.csv',rec17=d17/'gold_v3_17_spacing_recommendation.csv')
    invdf=inv([('stage15_summary',paths['s15'],True),('stage15_trade_ledger',paths['ledger'],True),('stage16_summary',paths['s16'],True),('stage16_all_candidate_review',paths['review'],True),('stage17_summary',paths['s17'],True),('stage17_portfolio_spacing_metrics',paths['port'],True),('stage17_candidate_cooldown_metrics',paths['cand'],True),('stage17_spacing_recommendation',paths['rec17'],True)])
    out.mkdir(parents=True,exist_ok=True); in_ok=bool(invdf[invdf.required.astype(bool)].exists.all())
    if not in_ok: raise RuntimeError('missing required Stage 15/16/17 inputs')
    s15=json.loads(paths['s15'].read_text(encoding='utf-8')); s16=json.loads(paths['s16'].read_text(encoding='utf-8')); s17=json.loads(paths['s17'].read_text(encoding='utf-8'))
    ok15=s15.get('status')==UP15_READY; ok16=s16.get('status')==UP16_READY; ok17=s17.get('status')==UP17_READY
    ledger=pd.read_csv(paths['ledger']); review=pd.read_csv(paths['review']); review['source_rank']=pd.to_numeric(review.source_rank,errors='coerce').astype(int)
    prio={int(r.source_rank):i+1 for i,r in enumerate(review.sort_values(['score_objective_fit','profit_factor','win_rate_result_positive'],ascending=[False,False,False]).itertuples())}
    ledger['source_rank']=pd.to_numeric(ledger.source_rank,errors='coerce').astype(int); ledger['priority']=ledger.source_rank.map(prio).fillna(999).astype(int); ledger['entry_month']=ledger.entry_month.astype(str)
    months=sorted(ledger.entry_month.dropna().unique().tolist()); stab=[]; mon=[]
    for sk,sid,cd,ranks,tier in SHORTLIST:
        spaced=dedup_cooldown(ledger[ledger.source_rank.isin(ranks)].copy(),cd); st,mr=evaluate(sk,sid,cd,ranks,tier,spaced,months); stab.append(st); mon.extend(mr)
    stabdf=pd.DataFrame(stab); mondf=pd.DataFrame(mon)
    rankret=[]
    for _,r in review.iterrows():
        rank=int(r.source_rank); role='PRIMARY_COMPONENT_RETAINED' if rank in {1,2} else ('AUX_OR_DIAGNOSTIC_COMPONENT_RETAINED' if rank in {3,4,6} else 'WEAK_PROFILE_DIAGNOSTIC_ONLY_DROP_BIAS')
        rankret.append(dict(source_rank=rank,candidate_group_id=r.candidate_group_id,profile_id=r.profile_id,stage16_recommendation=r.audit_recommendation,stage18_retention_role=role,rank_7_8_not_silently_dropped=rank in {7,8},not_final_approval=True))
    rankdf=pd.DataFrame(rankret); metrics_ok=ok15 and ok16 and ok17 and len(stabdf)==len(SHORTLIST) and len(mondf)>=len(SHORTLIST)*6 and {7,8}.issubset(set(rankdf.source_rank))
    status=READY if metrics_ok else BLOCKED; blocks=blockers(ok15,ok16,ok17,in_ok,metrics_ok)
    rec=[]
    for _,r in stabdf.sort_values('score_monthly_shortlist',ascending=False).iterrows():
        ar=str(r.audit_recommendation); tier={'KEEP_FINAL_AUDIT_SHORTLIST':'TIER_1_FINAL_AUDIT_SHORTLIST','KEEP_AUXILIARY_SHORTLIST':'TIER_2_AUXILIARY_SHORTLIST','H1_DIAGNOSTIC_ONLY':'TIER_3_DIAGNOSTIC_ONLY','DROP_OR_FILTER_RESCUE_ONLY':'TIER_4_DROP_OR_FILTER_RESCUE_ONLY'}.get(ar,'TIER_REVIEW')
        rec.append(dict(recommendation_tier=tier,scenario_key=r.scenario_key,scenario_id=r.scenario_id,cooldown_minutes=int(r.cooldown_minutes),shortlist_tier=r.shortlist_tier,reason=f"{ar}; PF={r.profit_factor}; WR={r.win_rate_result_positive}; TPD={r.trades_per_calendar_day}; neg_months={r.negative_months}; not final approval",next_audit_action='Stage 19 should build human decision template for final audit shortlist only'))
    recdf=pd.DataFrame(rec); decisions=pd.DataFrame([('selected_gold_v3_output_root',str(root),reason),('status',status,'monthly stability shortlist audit-only status'),('final_candidate_approval',False,'blocked by policy'),('threshold_finalization',False,'blocked by policy'),('model_training',False,'blocked by policy'),('signals_generated',False,'blocked by policy'),('zip_output_created',False,'disabled'),('external_actions',False,'Discord/MT5/AI/live integrations remain OFF')],columns=['decision_key','value','detail'])
    summary=dict(created_at_utc=st17.now(),step=STEP,status=status,blocked_reason='' if status==READY else 'Stage 18 monthly stability checks failed',selected_gold_v3_output_root=str(root),path_resolution_note=reason,stage15_status=str(s15.get('status','')),stage16_status=str(s16.get('status','')),stage17_status=str(s17.get('status','')),shortlist_scenario_rows=int(len(stabdf)),monthly_metric_rows=int(len(mondf)),rank_retention_rows=int(len(rankdf)),keep_final_audit_shortlist_rows=int((stabdf.audit_recommendation=='KEEP_FINAL_AUDIT_SHORTLIST').sum()),keep_auxiliary_shortlist_rows=int((stabdf.audit_recommendation=='KEEP_AUXILIARY_SHORTLIST').sum()),drop_or_filter_rescue_only_rows=int((stabdf.audit_recommendation=='DROP_OR_FILTER_RESCUE_ONLY').sum()),rank_7_8_included=True,objective_min_trades_per_day=OBJ_TPD,replay_scope='audit-only monthly stability over Stage17 shortlist scenarios; not live',old_gold_disc8_quarantined=True,**FALSE_FLAGS)
    st17.write_df(out/'gold_v3_18_input_inventory.csv',invdf); st17.write_df(out/'gold_v3_18_scenario_monthly_metrics.csv',mondf); st17.write_df(out/'gold_v3_18_scenario_stability_summary.csv',stabdf); st17.write_df(out/'gold_v3_18_rank_retention_review.csv',rankdf); st17.write_df(out/'gold_v3_18_shortlist_recommendation.csv',recdf); st17.write_df(out/'gold_v3_18_decision_matrix.csv',decisions); st17.write_df(out/'gold_v3_18_blocker_matrix.csv',blocks); st17.write_json(out/'gold_v3_18_summary.json',summary); (out/'GOLD_V3_18_MONTHLY_STABILITY_FINAL_AUDIT_SHORTLIST_AUDIT_ONLY_REPORT.md').write_text(make_report(summary,stabdf,rankdf,recdf,blocks),encoding='utf-8')
    print(json.dumps({'status':status,'shortlist_scenario_rows':len(stabdf),'monthly_metric_rows':len(mondf),'rank_7_8_included':True,'output_dir':str(out),'final_candidate_approval':False,'signals_generated':False,'zip_output_created':False},ensure_ascii=False,indent=2)); return 0 if status==READY else 2
def write_exception(repo,exc):
    try: root,reason=st17.select_root(repo.resolve())
    except Exception: root,reason=repo/'Files'/'FX_OUTPUTS'/'gold_v3','exception_fallback'
    out=root/OUT_NAME; out.mkdir(parents=True,exist_ok=True); summary=dict(created_at_utc=st17.now(),step=STEP,status=EXCEPTION,blocked_reason=f'{exc.__class__.__name__}: {exc}',selected_gold_v3_output_root=str(root),path_resolution_note=reason,**FALSE_FLAGS); st17.write_json(out/'gold_v3_18_summary.json',summary); (out/'gold_v3_18_exception.txt').write_text(traceback.format_exc(),encoding='utf-8')
def main(argv=None):
    ap=argparse.ArgumentParser(); ap.add_argument('--repo-root',default=''); a=ap.parse_args(argv); repo=Path(a.repo_root).resolve() if a.repo_root else repo_default()
    try: return run(repo)
    except Exception as e: write_exception(repo,e); print('[GOLD_V3_18] EXCEPTION. See output gold_v3_18_exception.txt',file=sys.stderr); print(traceback.format_exc(),file=sys.stderr); return 1
if __name__=='__main__': raise SystemExit(main())
