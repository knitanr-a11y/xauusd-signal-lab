#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse,csv,hashlib,json,sys,traceback
from datetime import datetime,timezone
from pathlib import Path
import pandas as pd

STEP='GOLD_V3_34_SELECTED_BAND_PRUNING_AUDIT_ONLY'
OUT='34_selected_band_pruning_audit_only'
UP31='31_all_active_candidate_uplift_queue_audit_only'
UP15='15_audit_only_replay_execution'
READY='GOLD_V3_34_SELECTED_BAND_PRUNING_READY_AUDIT_ONLY'
ERR='GOLD_V3_34_SELECTED_BAND_PRUNING_EXCEPTION_AUDIT_ONLY'
INV=['input_label','path','required','exists','size_bytes','sha256']
PLAN=['cut_id','packet_row','feature_column','rank_scope','low','high','cut_description','source_reason','month_filter_used','candidate_removal_used']
MET=['packet_row','source_scenario_key','variant_key','active_candidate_role','selected_cut_ids','rows_before','rows_after','removed_rows','trades_per_calendar_day_before','trades_per_calendar_day_after','win_rate_before','win_rate_after','win_rate_delta','profit_factor_before','profit_factor_after','pf_delta','sum_result_usd_before','sum_result_usd_after','sum_delta','negative_months_before','negative_months_after','july_pf_before','july_pf_after','candidate_still_active','audit_note']
REM=['cut_id','packet_row','source_scenario_key','variant_key','removed_rows','removed_win_rate','removed_profit_factor','removed_sum_result_usd','removed_avg_result_usd']
MON=['packet_row','variant_key','entry_month','rows','win_rate','profit_factor','sum_result_usd','month_bucket','is_july']
MAT=['review_key','value','detail']; BLK=['blocker_id','blocker_name','status','detail']

def now(): return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')
def repo_default(): return Path(__file__).resolve().parents[2]
def files_root(repo): return repo.parents[1] if len(repo.parents)>=2 else repo.parent
def roots(repo):
    a=files_root(repo)/'FX_OUTPUTS'/'gold_v3'; b=repo/'Files'/'FX_OUTPUTS'/'gold_v3'; return [a] if a==b else [a,b]
def pick(repo):
    for r in roots(repo):
        if (r/UP31/'gold_v3_31_summary.json').exists() and (r/UP15/'gold_v3_15_replay_trade_ledger.csv').exists(): return r,'stage31_stage15_root'
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
    if gl>0: return round(gp/gl,10)
    if gp>0: return 'INF_NO_LOSS'
    return ''
def metrics(df):
    if df.empty: return dict(rows=0,trades_per_calendar_day=0,win_rate=0,profit_factor='',sum_result_usd=0,avg_result_usd=0)
    w=df.sort_values('_dt'); res=pd.to_numeric(w['label_price_distance_result_usd'],errors='coerce').fillna(0.0); days=(w['_dt'].max().date()-w['_dt'].min().date()).days+1
    return dict(rows=len(w),trades_per_calendar_day=round(len(w)/days,10) if days else 0,win_rate=round(float((res>0).sum()/len(w)),10),profit_factor=pf(res),sum_result_usd=round(float(res.sum()),10),avg_result_usd=round(float(res.mean()),10))
def prep(df):
    w=df.copy(); w['source_rank']=pd.to_numeric(w['source_rank'],errors='coerce').fillna(0).astype(int); w['_dt']=pd.to_datetime(w['entry_time_utc'],utc=True,errors='coerce'); w=w[w['_dt'].notna()].copy(); j=w['_dt']+pd.Timedelta(hours=9); w['jst_hour']=j.dt.hour.astype(int); w['jst_weekday']=j.dt.day_name(); w['entry_month']=w['entry_month'].astype(str); w['priority']=w['source_rank']
    for c in ['label_price_distance_result_usd','h1_atr56','h4_ret4','m15_atr28']:
        if c in w.columns: w[c]=pd.to_numeric(w[c],errors='coerce')
    return w
def ranks(src):
    if str(src).startswith('R1_ONLY'): return [1]
    if str(src).startswith('R2_ONLY'): return [2]
    return [1,2]
def apply_filters(df,filters):
    keep=pd.Series(True,index=df.index)
    for flt in filters:
        col=str(flt.get('column',''))
        if col not in df.columns: continue
        mask=pd.Series(True,index=df.index)
        rs=str(flt.get('rank_scope','ALL')).strip()
        if rs and rs!='ALL' and rs!='nan': mask &= df['source_rank'].eq(int(float(rs)))
        typ=str(flt.get('filter_type','categorical'))
        if typ=='categorical':
            vals=[v for v in str(flt.get('values','')).split(';') if v and v!='nan']
            mask &= df[col].astype(str).isin(vals)
        else:
            mask &= pd.to_numeric(df[col],errors='coerce').ge(f(flt.get('low'))) & pd.to_numeric(df[col],errors='coerce').lt(f(flt.get('high')))
        keep &= ~mask
    return df[keep].copy()
def cool(df,minutes=60):
    if df.empty: return df.copy()
    w=df.sort_values(['_dt','priority','source_rank'],kind='mergesort').drop_duplicates('entry_time_utc',keep='first')
    ns=w['_dt'].astype('int64').to_numpy(); step=int(minutes)*60*1_000_000_000; keep=[]; last=None
    for i,t in enumerate(ns):
        if last is None or t>=last+step: keep.append(i); last=t
    return w.iloc[keep].copy()
def selected_plan():
    return [
        dict(cut_id='B07_H4RET4_013598_015292',packet_row='7',feature_column='h4_ret4',rank_scope='ALL',low='0.0135985561',high='0.015292471',cut_description='packet 7 h4_ret4 band',source_reason='Stage33 PF/WR/sum uplift',month_filter_used=False,candidate_removal_used=False),
        dict(cut_id='B08_H4RET4_013657_015425',packet_row='8',feature_column='h4_ret4',rank_scope='ALL',low='0.013657835',high='0.0154251557',cut_description='packet 8 h4_ret4 band',source_reason='Stage33 PF/WR/sum uplift',month_filter_used=False,candidate_removal_used=False),
        dict(cut_id='B09_M15ATR28_417535_429285',packet_row='9',feature_column='m15_atr28',rank_scope='ALL',low='4.1753571429',high='4.2928571429',cut_description='packet 9 m15_atr28 band',source_reason='Stage33 PF/WR/sum uplift',month_filter_used=False,candidate_removal_used=False),
        dict(cut_id='B11_M15ATR28_422839_429071',packet_row='11',feature_column='m15_atr28',rank_scope='ALL',low='4.2283928571',high='4.2907142857',cut_description='packet 11 m15_atr28 band',source_reason='Stage33 PF/WR/sum uplift',month_filter_used=False,candidate_removal_used=False),
        dict(cut_id='B13_H4RET4_007518_007783',packet_row='13',feature_column='h4_ret4',rank_scope='ALL',low='0.007518',high='0.007783',cut_description='packet 13 narrow h4_ret4 band',source_reason='refined band review',month_filter_used=False,candidate_removal_used=False),
    ]
def plan_filters(plan,packet):
    out=[]
    for p in plan:
        if str(p['packet_row'])==str(packet):
            out.append(dict(filter_type='numeric_bin',rank_scope=p['rank_scope'],column=p['feature_column'],low=p['low'],high=p['high'],values=''))
    return out
def month_rows(df,variant,packet):
    rows=[]
    for m in sorted(df['entry_month'].astype(str).unique()):
        part=df[df['entry_month'].astype(str).eq(m)]; mt=metrics(part); s=mt['sum_result_usd']; bucket='NEGATIVE_MONTH' if s<0 else ('POSITIVE_MONTH' if s>0 else 'FLAT_MONTH')
        rows.append(dict(packet_row=packet,variant_key=variant,entry_month=m,rows=mt['rows'],win_rate=mt['win_rate'],profit_factor=mt['profit_factor'],sum_result_usd=s,month_bucket=bucket,is_july=(m=='2025-07')))
    return rows
def neg_months(rows): return sum(1 for r in rows if f(r.get('sum_result_usd'))<0)
def july_pf(rows): return next((r.get('profit_factor','') for r in rows if r.get('entry_month')=='2025-07'),'')
def table(rows,cols,limit=60):
    if not rows: return '_No rows._'
    def md(x): return str(x).replace('\n',' ').replace('\r',' ').replace('|','/')[:220]
    out=['| '+' | '.join(cols)+' |','| '+' | '.join(['---']*len(cols))+' |']
    for r in rows[:limit]: out.append('| '+' | '.join(md(r.get(c,'')) for c in cols)+' |')
    return '\n'.join(out)
def report(summary,plan,met,rem,blk):
    lines=['# GOLD V3 34 selected band pruning audit-only report','',f"Created UTC: `{summary['created_at_utc']}`",f"Status: `{summary['status']}`",'','## Counts']
    for k in ['active_candidate_rows','selected_cut_rows','before_after_rows','removed_segment_rows','candidate_removal_used','month_filter_used','saturday_cut_used']: lines.append(f"- {k}: `{summary.get(k,'')}`")
    lines+=['','## Selected cut plan','',table(plan,PLAN),'','## Before / after metrics','',table(met,MET),'','## Removed segment metrics','',table(rem,REM),'','## Blockers','',table(blk,BLK),'','## Safety','','Audit-only. Seven candidates remain active. No month filter. No candidate removal.']
    return '\n'.join(lines)
def run(repo):
    root,note=pick(repo.resolve()); out=root/OUT
    paths={'s31':root/UP31/'gold_v3_31_summary.json','active':root/UP31/'gold_v3_31_all_active_candidate_set.csv','contract':root/UP31/'gold_v3_31_all_active_filter_contract.csv','ledger':root/UP15/'gold_v3_15_replay_trade_ledger.csv'}
    inv_rows=inv(paths)
    if not all(x['exists'] for x in inv_rows): raise RuntimeError('missing inputs')
    s31=rjson(paths['s31']); active=rcsv(paths['active']); contract=rcsv(paths['contract']); ledger=prep(pd.read_csv(paths['ledger']))
    plan=selected_plan(); met_rows=[]; rem_rows=[]; mon_rows=[]
    for a in active:
        packet=str(a.get('packet_row')); src=a.get('source_scenario_key',''); var=a.get('variant_key','')
        base_filters=[r for r in contract if str(r.get('packet_row'))==packet]
        sat_filter=[dict(filter_type='categorical',rank_scope='ALL',column='jst_weekday',values='Saturday',low='',high='')]
        add_filters=plan_filters(plan,packet)
        raw=ledger[ledger['source_rank'].isin(ranks(src))].copy()
        before=cool(apply_filters(raw,base_filters+sat_filter),60)
        after=cool(apply_filters(raw,base_filters+sat_filter+add_filters),60)
        bm=metrics(before); am=metrics(after); bmon=month_rows(before,var,packet); amon=month_rows(after,var,packet); mon_rows.extend(amon)
        ids=';'.join([p['cut_id'] for p in plan if p['packet_row']==packet])
        note='SELECTED_BAND_APPLIED' if ids else 'NO_EXTRA_BAND_APPLIED'
        if ids and (pfnum(am['profit_factor'])<pfnum(bm['profit_factor']) or f(am['sum_result_usd'])<f(bm['sum_result_usd'])): note='REVIEW_REQUIRED_PF_OR_SUM_NOT_FULLY_UP'
        met_rows.append(dict(packet_row=packet,source_scenario_key=src,variant_key=var,active_candidate_role='ACTIVE_CANDIDATE',selected_cut_ids=ids,rows_before=bm['rows'],rows_after=am['rows'],removed_rows=bm['rows']-am['rows'],trades_per_calendar_day_before=bm['trades_per_calendar_day'],trades_per_calendar_day_after=am['trades_per_calendar_day'],win_rate_before=bm['win_rate'],win_rate_after=am['win_rate'],win_rate_delta=round(f(am['win_rate'])-f(bm['win_rate']),10),profit_factor_before=bm['profit_factor'],profit_factor_after=am['profit_factor'],pf_delta=round(pfnum(am['profit_factor'])-pfnum(bm['profit_factor']),10),sum_result_usd_before=bm['sum_result_usd'],sum_result_usd_after=am['sum_result_usd'],sum_delta=round(f(am['sum_result_usd'])-f(bm['sum_result_usd']),10),negative_months_before=neg_months(bmon),negative_months_after=neg_months(amon),july_pf_before=july_pf(bmon),july_pf_after=july_pf(amon),candidate_still_active=True,audit_note=note))
        for p in [x for x in plan if x['packet_row']==packet]:
            seg_before=cool(apply_filters(raw,base_filters+sat_filter),60)
            seg_after=cool(apply_filters(raw,base_filters+sat_filter+plan_filters([p],packet)),60)
            removed=seg_before.loc[~seg_before.index.isin(seg_after.index)].copy(); rm=metrics(removed)
            rem_rows.append(dict(cut_id=p['cut_id'],packet_row=packet,source_scenario_key=src,variant_key=var,removed_rows=rm['rows'],removed_win_rate=rm['win_rate'],removed_profit_factor=rm['profit_factor'],removed_sum_result_usd=rm['sum_result_usd'],removed_avg_result_usd=rm['avg_result_usd']))
    blk=[dict(blocker_id='G3-34-001',blocker_name='inputs',status='CLOSED',detail='Stage31 and Stage15 found'),dict(blocker_id='G3-34-002',blocker_name='candidate preservation',status='CLOSED',detail='all 7 candidates remain active'),dict(blocker_id='G3-34-003',blocker_name='month filter',status='CLOSED',detail='not used')]
    mat=[dict(review_key='status',value=READY,detail='selected band pruning evaluated'),dict(review_key='active_candidate_rows',value=len(active),detail='all candidates active'),dict(review_key='selected_cut_rows',value=len(plan),detail='five selected indicator bands'),dict(review_key='packet_1_extra_band_used',value=False,detail='not used'),dict(review_key='packet_4_extra_band_used',value=False,detail='not used'),dict(review_key='month_filter_used',value=False,detail='not used'),dict(review_key='candidate_removal_used',value=False,detail='not used')]
    summary=dict(created_at_utc=now(),step=STEP,status=READY,selected_gold_v3_output_root=str(root),path_resolution_note=note,stage31_status=s31.get('status',''),active_candidate_rows=len(active),selected_cut_rows=len(plan),before_after_rows=len(met_rows),removed_segment_rows=len(rem_rows),monthly_rows=len(mon_rows),candidate_removal_used=False,month_filter_used=False,saturday_cut_used=True,daily_cap_used=False,switching_used=False,review_scope='global Saturday plus five selected indicator bands')
    wcsv(out/'gold_v3_34_input_inventory.csv',inv_rows,INV); wcsv(out/'gold_v3_34_selected_cut_plan.csv',plan,PLAN); wcsv(out/'gold_v3_34_before_after_metrics.csv',met_rows,MET); wcsv(out/'gold_v3_34_removed_segment_metrics.csv',rem_rows,REM); wcsv(out/'gold_v3_34_after_monthly_metrics.csv',mon_rows,MON); wcsv(out/'gold_v3_34_review_matrix.csv',mat,MAT); wcsv(out/'gold_v3_34_blocker_matrix.csv',blk,BLK); wjson(out/'gold_v3_34_summary.json',summary); (out/'GOLD_V3_34_SELECTED_BAND_PRUNING_AUDIT_ONLY_REPORT.md').write_text(report(summary,plan,met_rows,rem_rows,blk),encoding='utf-8')
    print(json.dumps({'status':READY,'selected_cut_rows':len(plan),'output_dir':str(out)},ensure_ascii=False,indent=2)); return 0
def fail(repo,e):
    root,note=pick(repo.resolve()); out=root/OUT; out.mkdir(parents=True,exist_ok=True); wjson(out/'gold_v3_34_summary.json',dict(created_at_utc=now(),step=STEP,status=ERR,blocked_reason=f'{e.__class__.__name__}: {e}',path_resolution_note=note)); (out/'gold_v3_34_exception.txt').write_text(traceback.format_exc(),encoding='utf-8')
def main(argv=None):
    ap=argparse.ArgumentParser(); ap.add_argument('--repo-root',default=''); a=ap.parse_args(argv); repo=Path(a.repo_root).resolve() if a.repo_root else repo_default()
    try: return run(repo)
    except Exception as e: fail(repo,e); print(traceback.format_exc(),file=sys.stderr); return 1
if __name__=='__main__': raise SystemExit(main())
