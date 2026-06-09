#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse,csv,hashlib,json,math,sys,traceback
from datetime import datetime,timezone
from pathlib import Path
import pandas as pd

STEP='GOLD_V3_32_REQUESTED_ACTIVE_CANDIDATE_LOSS_FEATURE_PRUNING_AUDIT_ONLY'
OUT='32_requested_active_candidate_loss_feature_pruning_audit_only'
UP31='31_all_active_candidate_uplift_queue_audit_only'
UP15='15_audit_only_replay_execution'
READY='GOLD_V3_32_REQUESTED_ACTIVE_CANDIDATE_LOSS_FEATURE_PRUNING_READY_AUDIT_ONLY'
ERR='GOLD_V3_32_REQUESTED_ACTIVE_CANDIDATE_LOSS_FEATURE_PRUNING_EXCEPTION_AUDIT_ONLY'
INV=['input_label','path','required','exists','size_bytes','sha256']
PLAN=['cut_id','packet_rows','cut_description','filter_type','rank_scope','column','values','low','high','production_eligible','diagnostic_note']
APP=['packet_row','source_scenario_key','variant_key','applied_cut_ids','applied_cut_descriptions','candidate_still_active','production_eligible_filter_count','diagnostic_only_filter_count']
MET=['packet_row','source_scenario_key','variant_key','rows_before','rows_after','removed_rows','trades_per_calendar_day_before','trades_per_calendar_day_after','win_rate_before','win_rate_after','win_rate_delta','profit_factor_before','profit_factor_after','pf_delta','sum_result_usd_before','sum_result_usd_after','sum_delta','negative_months_before','negative_months_after','july_pf_before','july_pf_after','audit_note']
REM=['cut_id','packet_row','source_scenario_key','removed_rows','removed_win_rate','removed_profit_factor','removed_sum_result_usd','removed_avg_result_usd','diagnostic_note']
MON=['packet_row','variant_key','entry_month','rows','win_rate_result_positive','profit_factor','sum_result_usd','month_bucket','is_july']
MAT=['review_key','value','detail']; BLK=['blocker_id','blocker_name','status','detail']

def now(): return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')
def repo_default(): return Path(__file__).resolve().parents[2]
def files_root(repo): return repo.parents[1] if len(repo.parents)>=2 else repo.parent
def roots(repo):
    a=files_root(repo)/'FX_OUTPUTS'/'gold_v3'; b=repo/'Files'/'FX_OUTPUTS'/'gold_v3'; return [a] if a==b else [a,b]
def pick(repo):
    for r in roots(repo):
        if (r/UP31/'gold_v3_31_summary.json').exists() and (r/UP15/'gold_v3_15_replay_trade_ledger.csv').exists(): return r,'stage31_and_stage15_root'
    for r in roots(repo):
        if (r/UP31/'gold_v3_31_summary.json').exists(): return r,'stage31_root'
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
    try:
        if pd.isna(x): return d
        return float(str(x).strip())
    except Exception: return d
def pfnum(x): return 999999.0 if str(x).upper().startswith('INF') else f(x,-1.0)
def pf(res):
    gp=float(res[res>0].sum()); gl=float(-res[res<0].sum())
    if gl>0: return round(gp/gl,10),gp,gl
    if gp>0: return 'INF_NO_LOSS',gp,gl
    return '',gp,gl
def prep_ledger(df):
    w=df.copy(); w['source_rank']=pd.to_numeric(w['source_rank'],errors='coerce').fillna(0).astype(int); w['_dt']=pd.to_datetime(w['entry_time_utc'],utc=True,errors='coerce'); w=w[w['_dt'].notna()].copy(); j=w['_dt']+pd.Timedelta(hours=9); w['jst_hour']=j.dt.hour.astype(int); w['jst_weekday']=j.dt.day_name(); w['entry_month']=w['entry_month'].astype(str); w['priority']=w['source_rank']
    for c in ['label_price_distance_result_usd','h1_atr56','h4_ret4','m15_atr28']:
        if c in w.columns: w[c]=pd.to_numeric(w[c],errors='coerce')
    return w
def apply_filters(df,filters):
    keep=pd.Series(True,index=df.index)
    for flt in filters:
        col=str(flt.get('column',''))
        if col not in df.columns: continue
        mask=pd.Series(True,index=df.index)
        rs=str(flt.get('rank_scope','ALL')).strip()
        if rs and rs!='ALL': mask &= df['source_rank'].eq(int(float(rs)))
        typ=str(flt.get('filter_type','categorical'))
        if typ=='categorical':
            vals=[v for v in str(flt.get('values','')).split(';') if v!='']
            mask &= df[col].astype(str).isin(vals)
        else:
            mask &= pd.to_numeric(df[col],errors='coerce').ge(f(flt.get('low'))) & pd.to_numeric(df[col],errors='coerce').lt(f(flt.get('high')))
        keep &= ~mask
    return df[keep].copy()
def cool(df,minutes=60):
    if df.empty: return df.copy()
    w=df.sort_values(['_dt','priority','source_rank'],kind='mergesort').drop_duplicates('entry_time_utc',keep='first')
    step=int(minutes)*60*1_000_000_000; ns=w['_dt'].astype('int64').to_numpy(); keep=[]; last=None
    for i,t in enumerate(ns):
        if last is None or t>=last+step: keep.append(i); last=t
    return w.iloc[keep].copy()
def ranks(src): return [1] if src.startswith('R1_ONLY') else ([2] if src.startswith('R2_ONLY') else [1,2])
def metrics(df):
    if df.empty: return dict(rows=0,trades_per_calendar_day=0,win_rate_result_positive=0,profit_factor='',sum_result_usd=0,avg_result_usd=0)
    w=df.sort_values('_dt'); res=pd.to_numeric(w['label_price_distance_result_usd'],errors='coerce').fillna(0.0); days=(w['_dt'].max().date()-w['_dt'].min().date()).days+1; p,gp,gl=pf(res)
    return dict(rows=len(w),trades_per_calendar_day=round(len(w)/days,10) if days else 0,win_rate_result_positive=round(float((res>0).sum()/len(w)),10),profit_factor=p,sum_result_usd=round(float(res.sum()),10),avg_result_usd=round(float(res.mean()),10))
def month_stats(df,variant,packet):
    rows=[]
    for m in sorted(df['entry_month'].astype(str).unique()):
        part=df[df['entry_month'].astype(str).eq(m)]; mt=metrics(part); s=mt['sum_result_usd']; bucket='NEGATIVE_MONTH' if s<0 else ('POSITIVE_MONTH' if s>0 else 'FLAT_MONTH')
        rows.append(dict(packet_row=packet,variant_key=variant,entry_month=m,rows=mt['rows'],win_rate_result_positive=mt['win_rate_result_positive'],profit_factor=mt['profit_factor'],sum_result_usd=s,month_bucket=bucket,is_july=(m=='2025-07')))
    return rows
def neg_months(months): return sum(1 for r in months if f(r.get('sum_result_usd'))<0)
def july_pf(months): return next((r.get('profit_factor','') for r in months if r.get('entry_month')=='2025-07'),'')
def table(rows,cols,limit=60):
    def md(x): return str(x).replace('\n',' ').replace('\r',' ').replace('|','/')[:240]
    if not rows: return '_No rows._'
    out=['| '+' | '.join(cols)+' |','| '+' | '.join(['---']*len(cols))+' |']
    for r in rows[:limit]: out.append('| '+' | '.join(md(r.get(c,'')) for c in cols)+' |')
    return '\n'.join(out)
def report(summary,plan,met,rem,blk):
    lines=['# GOLD V3 32 requested active candidate loss-feature pruning audit-only report','',f"Created UTC: `{summary['created_at_utc']}`",f"Status: `{summary['status']}`",'','## Counts']
    for k in ['active_candidate_rows','cut_plan_rows','before_after_rows','removed_segment_rows','daily_cap_used','candidate_removal_used']: lines.append(f"- {k}: `{summary.get(k,'')}`")
    lines+=['','## Requested cut plan','',table(plan,PLAN),'','## Before / after metrics','',table(met,MET),'','## Removed segment metrics','',table(rem,REM),'','## Blockers','',table(blk,BLK),'','## Safety','','Audit-only. All candidates remain active. Diagnostic month cuts are not production-ready filters.']
    return '\n'.join(lines)
def existing_filters(contract,packet):
    return [r for r in contract if str(r.get('packet_row'))==str(packet)]
def requested_plan():
    return [
        dict(cut_id='C01',packet_rows='1',cut_description='packet 1 exclude jst_weekday=Saturday',filter_type='categorical',rank_scope='ALL',column='jst_weekday',values='Saturday',low='',high='',production_eligible=True,diagnostic_note='pre-entry weekday cut'),
        dict(cut_id='C02',packet_rows='13',cut_description='packet 13 exclude rank 2 m15_atr28 in [3.828, 3.953)',filter_type='numeric_bin',rank_scope='2',column='m15_atr28',values='',low='3.828',high='3.953',production_eligible=True,diagnostic_note='pre-entry rank2 m15_atr28 band'),
        dict(cut_id='C03',packet_rows='8',cut_description='packet 8 exclude entry_month=2025-02',filter_type='categorical',rank_scope='ALL',column='entry_month',values='2025-02',low='',high='',production_eligible=False,diagnostic_note='historical month diagnostic only'),
        dict(cut_id='C04',packet_rows='7',cut_description='packet 7 exclude entry_month=2025-02',filter_type='categorical',rank_scope='ALL',column='entry_month',values='2025-02',low='',high='',production_eligible=False,diagnostic_note='historical month diagnostic only'),
        dict(cut_id='C05',packet_rows='4;7',cut_description='packet 4 and 7 exclude jst_weekday=Saturday',filter_type='categorical',rank_scope='ALL',column='jst_weekday',values='Saturday',low='',high='',production_eligible=True,diagnostic_note='pre-entry weekday cut'),
        dict(cut_id='C06',packet_rows='9;11',cut_description='packet 9 and 11 exclude source_rank=2',filter_type='categorical',rank_scope='2',column='source_rank',values='2',low='',high='',production_eligible=True,diagnostic_note='pre-entry rank cut for MAIN rank2 weakness'),
    ]
def cuts_for_packet(plan,packet): return [p for p in plan if str(packet) in str(p['packet_rows']).split(';')]
def run(repo):
    root,note=pick(repo.resolve()); out=root/OUT
    paths={'s31':root/UP31/'gold_v3_31_summary.json','active':root/UP31/'gold_v3_31_all_active_candidate_set.csv','contract':root/UP31/'gold_v3_31_all_active_filter_contract.csv','ledger':root/UP15/'gold_v3_15_replay_trade_ledger.csv'}
    inv_rows=inv(paths)
    if not all(x['exists'] for x in inv_rows): raise RuntimeError('missing inputs')
    s31=rjson(paths['s31']); active=rcsv(paths['active']); contract=rcsv(paths['contract']); ledger=prep_ledger(pd.read_csv(paths['ledger']))
    plan=requested_plan(); app=[]; mets=[]; removed=[]; mon=[]
    for a in active:
        packet=str(a.get('packet_row')); src=a.get('source_scenario_key',''); var=a.get('variant_key','')
        base_filters=existing_filters(contract,packet); add=cuts_for_packet(plan,packet)
        raw=ledger[ledger['source_rank'].isin(ranks(src))].copy(); before=cool(apply_filters(raw,base_filters),60); after=cool(apply_filters(raw,base_filters+add),60)
        bm=metrics(before); am=metrics(after); bmon=month_stats(before,var,packet); amon=month_stats(after,var,packet); mon.extend(amon)
        cut_ids=';'.join(x['cut_id'] for x in add); cut_desc=' / '.join(x['cut_description'] for x in add)
        app.append(dict(packet_row=packet,source_scenario_key=src,variant_key=var,applied_cut_ids=cut_ids,applied_cut_descriptions=cut_desc,candidate_still_active=True,production_eligible_filter_count=sum(str(x['production_eligible'])=='True' or x['production_eligible'] is True for x in add),diagnostic_only_filter_count=sum(not (str(x['production_eligible'])=='True' or x['production_eligible'] is True) for x in add)))
        note='UPLIFT_OR_DIAGNOSTIC' if add else 'NO_REQUESTED_EXTRA_CUT'
        if add and pfnum(am['profit_factor']) < pfnum(bm['profit_factor']): note='CUT_REMOVES_WEAK_SEGMENT_BUT_AFTER_COOLDOWN_PF_NOT_IMPROVED'
        mets.append(dict(packet_row=packet,source_scenario_key=src,variant_key=var,rows_before=bm['rows'],rows_after=am['rows'],removed_rows=bm['rows']-am['rows'],trades_per_calendar_day_before=bm['trades_per_calendar_day'],trades_per_calendar_day_after=am['trades_per_calendar_day'],win_rate_before=bm['win_rate_result_positive'],win_rate_after=am['win_rate_result_positive'],win_rate_delta=round(f(am['win_rate_result_positive'])-f(bm['win_rate_result_positive']),10),profit_factor_before=bm['profit_factor'],profit_factor_after=am['profit_factor'],pf_delta=round(pfnum(am['profit_factor'])-pfnum(bm['profit_factor']),10),sum_result_usd_before=bm['sum_result_usd'],sum_result_usd_after=am['sum_result_usd'],sum_delta=round(f(am['sum_result_usd'])-f(bm['sum_result_usd']),10),negative_months_before=neg_months(bmon),negative_months_after=neg_months(amon),july_pf_before=july_pf(bmon),july_pf_after=july_pf(amon),audit_note=note))
        for c in add:
            cf=[c]; seg=cool(apply_filters(raw,base_filters),60); cutseg=seg.loc[~seg.index.isin(cool(apply_filters(raw,base_filters+cf),60).index)].copy()
            rm=metrics(cutseg)
            removed.append(dict(cut_id=c['cut_id'],packet_row=packet,source_scenario_key=src,removed_rows=rm['rows'],removed_win_rate=rm['win_rate_result_positive'],removed_profit_factor=rm['profit_factor'],removed_sum_result_usd=rm['sum_result_usd'],removed_avg_result_usd=rm['avg_result_usd'],diagnostic_note=c['diagnostic_note']))
    blk=[dict(blocker_id='G3-32-001',blocker_name='inputs',status='CLOSED',detail='Stage31 active set and Stage15 ledger found'),dict(blocker_id='G3-32-002',blocker_name='candidate preservation',status='CLOSED',detail='all 7 candidates remain active'),dict(blocker_id='G3-32-003',blocker_name='mode',status='CLOSED',detail='audit-only')]
    mat=[dict(review_key='status',value=READY,detail='requested cuts evaluated'),dict(review_key='active_candidate_rows',value=len(active),detail='still 7'),dict(review_key='candidate_removal_used',value=False,detail='none removed'),dict(review_key='diagnostic_month_filters_present',value=True,detail='month cuts are diagnostic-only'),dict(review_key='daily_cap_used',value=False,detail='not used'),dict(review_key='switching_used',value=False,detail='not used')]
    summary=dict(created_at_utc=now(),step=STEP,status=READY,selected_gold_v3_output_root=str(root),path_resolution_note=note,stage31_status=s31.get('status',''),active_candidate_rows=len(active),cut_plan_rows=len(plan),before_after_rows=len(mets),removed_segment_rows=len(removed),monthly_rows=len(mon),candidate_removal_used=False,daily_cap_used=False,switching_used=False,month_filter_used_for_production=False,diagnostic_month_filter_evaluated=True,review_scope='user requested six pruning groups against seven active candidates')
    wcsv(out/'gold_v3_32_input_inventory.csv',inv_rows,INV); wcsv(out/'gold_v3_32_requested_cut_plan.csv',plan,PLAN); wcsv(out/'gold_v3_32_per_packet_cut_application.csv',app,APP); wcsv(out/'gold_v3_32_before_after_metrics.csv',mets,MET); wcsv(out/'gold_v3_32_removed_segment_metrics.csv',removed,REM); wcsv(out/'gold_v3_32_after_monthly_metrics.csv',mon,MON); wcsv(out/'gold_v3_32_review_matrix.csv',mat,MAT); wcsv(out/'gold_v3_32_blocker_matrix.csv',blk,BLK); wjson(out/'gold_v3_32_summary.json',summary); (out/'GOLD_V3_32_REQUESTED_ACTIVE_CANDIDATE_LOSS_FEATURE_PRUNING_AUDIT_ONLY_REPORT.md').write_text(report(summary,plan,mets,removed,blk),encoding='utf-8')
    print(json.dumps({'status':READY,'active_candidate_rows':len(active),'before_after_rows':len(mets),'output_dir':str(out)},ensure_ascii=False,indent=2)); return 0
def fail(repo,e):
    root,note=pick(repo.resolve()); out=root/OUT; out.mkdir(parents=True,exist_ok=True); wjson(out/'gold_v3_32_summary.json',dict(created_at_utc=now(),step=STEP,status=ERR,blocked_reason=f'{e.__class__.__name__}: {e}',path_resolution_note=note)); (out/'gold_v3_32_exception.txt').write_text(traceback.format_exc(),encoding='utf-8')
def main(argv=None):
    ap=argparse.ArgumentParser(); ap.add_argument('--repo-root',default=''); a=ap.parse_args(argv); repo=Path(a.repo_root).resolve() if a.repo_root else repo_default()
    try: return run(repo)
    except Exception as e: fail(repo,e); print(traceback.format_exc(),file=sys.stderr); return 1
if __name__=='__main__': raise SystemExit(main())
