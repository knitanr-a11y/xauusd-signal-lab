#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse,csv,hashlib,json,re,sys,traceback
from datetime import datetime,timezone
from pathlib import Path
import pandas as pd

STEP='GOLD_V3_35_CUMULATIVE_SELECTED_BAND_PRUNING_WITH_PACKET9_AUDIT_ONLY'
OUT='35_cumulative_selected_band_pruning_with_packet9_audit_only'
UP31='31_all_active_candidate_uplift_queue_audit_only'
UP15='15_audit_only_replay_execution'
READY='GOLD_V3_35_CUMULATIVE_SELECTED_BAND_PRUNING_WITH_PACKET9_READY_AUDIT_ONLY'
ERR='GOLD_V3_35_CUMULATIVE_SELECTED_BAND_PRUNING_WITH_PACKET9_EXCEPTION_AUDIT_ONLY'
INV=['input_label','path','required','exists','size_bytes','sha256']
PLAN=['cut_id','packet_row','feature_column','rank_scope','low','high','cut_description','selection_note','month_filter_used','candidate_removal_used']
MET=['packet_row','source_scenario_key','variant_key','cooldown_minutes','active_candidate_role','selected_cut_ids','rows_original','rows_final','removed_rows','trades_per_day_original','trades_per_day_final','win_rate_original','win_rate_final','win_rate_delta','profit_factor_original','profit_factor_final','pf_delta','sum_result_usd_original','sum_result_usd_final','sum_delta','negative_months_original','negative_months_final','july_pf_original','july_pf_final','candidate_still_active','audit_note']
REM=['cut_id','packet_row','source_scenario_key','variant_key','removed_rows','removed_win_rate','removed_profit_factor','removed_sum_result_usd','removed_avg_result_usd']
MON=['packet_row','variant_key','entry_month','rows','win_rate','profit_factor','sum_result_usd','month_bucket','is_july']
TOT=['comparison','rows','win_rate','profit_factor','sum_result_usd']
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
    if df.empty: return dict(rows=0,trades_per_day=0,win_rate=0,profit_factor='',sum_result_usd=0,avg_result_usd=0)
    w=df.sort_values('_dt'); res=pd.to_numeric(w['label_price_distance_result_usd'],errors='coerce').fillna(0.0); days=(w['_dt'].max().date()-w['_dt'].min().date()).days+1
    return dict(rows=len(w),trades_per_day=round(len(w)/days,10) if days else 0,win_rate=round(float((res>0).sum()/len(w)),10),profit_factor=pf(res),sum_result_usd=round(float(res.sum()),10),avg_result_usd=round(float(res.mean()),10))
def combined_metrics(metrics_rows,pre):
    rows=sum(int(r[f'rows_{pre}']) for r in metrics_rows)
    gp=gl=0.0; wins=0; losses=0; total_sum=0.0
    # cannot recover gp/gl from aggregate rows; use weighted approximation unavailable -> use sum of actual streams below not here
    return rows
def prep(df):
    w=df.copy(); w['source_rank']=pd.to_numeric(w['source_rank'],errors='coerce').fillna(0).astype(int); w['_dt']=pd.to_datetime(w['entry_time_utc'],utc=True,errors='coerce'); w=w[w['_dt'].notna()].copy(); j=w['_dt']+pd.Timedelta(hours=9); w['jst_hour']=j.dt.hour.astype(int); w['jst_weekday']=j.dt.day_name(); w['entry_month']=w['entry_month'].astype(str); w['priority']=w['source_rank']
    for c in ['label_price_distance_result_usd','h1_atr56','h4_ret4','m15_atr28']:
        if c in w.columns: w[c]=pd.to_numeric(w[c],errors='coerce')
    return w
def ranks(src):
    if str(src).startswith('R1_ONLY'): return [1]
    if str(src).startswith('R2_ONLY'): return [2]
    return [1,2]
def cooldown(src,variant):
    m=re.search(r'CD(\d+)',str(src)+' '+str(variant))
    return int(m.group(1)) if m else 60
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
def cool(df,minutes):
    if df.empty: return df.copy()
    w=df.sort_values(['_dt','priority','source_rank'],kind='mergesort').drop_duplicates('entry_time_utc',keep='first')
    ns=w['_dt'].astype('int64').to_numpy(); step=int(minutes)*60*1_000_000_000; keep=[]; last=None
    for i,t in enumerate(ns):
        if last is None or t>=last+step: keep.append(i); last=t
    return w.iloc[keep].copy()
def plan():
    return [
        dict(cut_id='GLOBAL_SATURDAY',packet_row='ALL',feature_column='jst_weekday',rank_scope='ALL',low='',high='',cut_description='all packets exclude Saturday',selection_note='market closed / weekend exclusion',month_filter_used=False,candidate_removal_used=False),
        dict(cut_id='B07_H4RET4_013598_015292',packet_row='7',feature_column='h4_ret4',rank_scope='ALL',low='0.0135985561',high='0.015292471',cut_description='packet 7 h4_ret4 band',selection_note='accepted from Stage34',month_filter_used=False,candidate_removal_used=False),
        dict(cut_id='B08_H4RET4_013657_015425',packet_row='8',feature_column='h4_ret4',rank_scope='ALL',low='0.013657835',high='0.0154251557',cut_description='packet 8 h4_ret4 band',selection_note='accepted from Stage34',month_filter_used=False,candidate_removal_used=False),
        dict(cut_id='B09_R2_M15ATR28_3878714_3998071',packet_row='9',feature_column='m15_atr28',rank_scope='2',low='3.878714',high='3.998071',cut_description='packet 9 rank2 narrow m15_atr28 band',selection_note='new accepted packet9 proposal',month_filter_used=False,candidate_removal_used=False),
        dict(cut_id='B11_M15ATR28_422839_429071',packet_row='11',feature_column='m15_atr28',rank_scope='ALL',low='4.2283928571',high='4.2907142857',cut_description='packet 11 m15_atr28 band',selection_note='accepted from Stage34',month_filter_used=False,candidate_removal_used=False),
        dict(cut_id='B13_H4RET4_007518_007783',packet_row='13',feature_column='h4_ret4',rank_scope='ALL',low='0.007518',high='0.007783',cut_description='packet 13 narrow h4_ret4 band',selection_note='accepted from Stage34',month_filter_used=False,candidate_removal_used=False),
    ]
def pfilters(plan_rows,packet):
    out=[dict(filter_type='categorical',rank_scope='ALL',column='jst_weekday',values='Saturday',low='',high='')]
    for p in plan_rows:
        if p['packet_row']==str(packet):
            out.append(dict(filter_type='numeric_bin',rank_scope=p['rank_scope'],column=p['feature_column'],values='',low=p['low'],high=p['high']))
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
def report(summary,plan_rows,met,rem,tot,blk):
    lines=['# GOLD V3 35 cumulative selected band pruning with packet9 audit-only report','',f"Created UTC: `{summary['created_at_utc']}`",f"Status: `{summary['status']}`",'','## Counts']
    for k in ['active_candidate_rows','selected_cut_rows','before_after_rows','removed_segment_rows','candidate_removal_used','month_filter_used','saturday_cut_used']: lines.append(f"- {k}: `{summary.get(k,'')}`")
    lines+=['','## Selected cumulative plan','',table(plan_rows,PLAN),'','## Before / final metrics','',table(met,MET),'','## Extended totals','',table(tot,TOT),'','## Removed segment metrics','',table(rem,REM),'','## Blockers','',table(blk,BLK),'','## Safety','','Audit-only. Seven candidates remain active. No month filter. No candidate removal.']
    return '\n'.join(lines)
def run(repo):
    root,note=pick(repo.resolve()); out=root/OUT
    paths={'s31':root/UP31/'gold_v3_31_summary.json','active':root/UP31/'gold_v3_31_all_active_candidate_set.csv','contract':root/UP31/'gold_v3_31_all_active_filter_contract.csv','ledger':root/UP15/'gold_v3_15_replay_trade_ledger.csv'}
    inv_rows=inv(paths)
    if not all(x['exists'] for x in inv_rows): raise RuntimeError('missing inputs')
    s31=rjson(paths['s31']); active=rcsv(paths['active']); contract=rcsv(paths['contract']); ledger=prep(pd.read_csv(paths['ledger']))
    plan_rows=plan(); met_rows=[]; rem_rows=[]; mon_rows=[]; orig_streams=[]; final_streams=[]
    for a in active:
        packet=str(a.get('packet_row')); src=a.get('source_scenario_key',''); var=a.get('variant_key',''); cd=cooldown(src,var)
        base_filters=[r for r in contract if str(r.get('packet_row'))==packet]
        raw=ledger[ledger['source_rank'].isin(ranks(src))].copy()
        original=cool(apply_filters(raw,base_filters),cd)
        final=cool(apply_filters(raw,base_filters+pfilters(plan_rows,packet)),cd)
        orig_streams.append(original.assign(_packet_row=packet)); final_streams.append(final.assign(_packet_row=packet))
        om=metrics(original); fm=metrics(final); omon=month_rows(original,var,packet); fmon=month_rows(final,var,packet); mon_rows.extend(fmon)
        ids=';'.join([p['cut_id'] for p in plan_rows if p['packet_row'] in [packet,'ALL']])
        note2='CUMULATIVE_SELECTED_BANDS_APPLIED'
        if pfnum(fm['profit_factor'])<pfnum(om['profit_factor']): note2='REVIEW_REQUIRED_PF_DOWN'
        met_rows.append(dict(packet_row=packet,source_scenario_key=src,variant_key=var,cooldown_minutes=cd,active_candidate_role='ACTIVE_CANDIDATE',selected_cut_ids=ids,rows_original=om['rows'],rows_final=fm['rows'],removed_rows=om['rows']-fm['rows'],trades_per_day_original=om['trades_per_day'],trades_per_day_final=fm['trades_per_day'],win_rate_original=om['win_rate'],win_rate_final=fm['win_rate'],win_rate_delta=round(f(fm['win_rate'])-f(om['win_rate']),10),profit_factor_original=om['profit_factor'],profit_factor_final=fm['profit_factor'],pf_delta=round(pfnum(fm['profit_factor'])-pfnum(om['profit_factor']),10),sum_result_usd_original=om['sum_result_usd'],sum_result_usd_final=fm['sum_result_usd'],sum_delta=round(f(fm['sum_result_usd'])-f(om['sum_result_usd']),10),negative_months_original=neg_months(omon),negative_months_final=neg_months(fmon),july_pf_original=july_pf(omon),july_pf_final=july_pf(fmon),candidate_still_active=True,audit_note=note2))
        for p in [x for x in plan_rows if x['packet_row'] in [packet,'ALL']]:
            before=cool(apply_filters(raw,base_filters),cd) if p['packet_row']=='ALL' else cool(apply_filters(raw,base_filters+[dict(filter_type='categorical',rank_scope='ALL',column='jst_weekday',values='Saturday',low='',high='')]),cd)
            one = [dict(filter_type='categorical',rank_scope='ALL',column='jst_weekday',values='Saturday',low='',high='')] if p['packet_row']=='ALL' else [dict(filter_type='categorical',rank_scope='ALL',column='jst_weekday',values='Saturday',low='',high=''), dict(filter_type='numeric_bin',rank_scope=p['rank_scope'],column=p['feature_column'],values='',low=p['low'],high=p['high'])]
            after=cool(apply_filters(raw,base_filters+one),cd)
            removed=before.loc[~before.index.isin(after.index)].copy(); rm=metrics(removed)
            rem_rows.append(dict(cut_id=p['cut_id'],packet_row=packet,source_scenario_key=src,variant_key=var,removed_rows=rm['rows'],removed_win_rate=rm['win_rate'],removed_profit_factor=rm['profit_factor'],removed_sum_result_usd=rm['sum_result_usd'],removed_avg_result_usd=rm['avg_result_usd']))
    orig_all=pd.concat(orig_streams,ignore_index=True) if orig_streams else pd.DataFrame()
    final_all=pd.concat(final_streams,ignore_index=True) if final_streams else pd.DataFrame()
    om=metrics(orig_all); fm=metrics(final_all)
    tot=[dict(comparison='original_extended_candidate_sum',rows=om['rows'],win_rate=om['win_rate'],profit_factor=om['profit_factor'],sum_result_usd=om['sum_result_usd']),dict(comparison='final_extended_candidate_sum',rows=fm['rows'],win_rate=fm['win_rate'],profit_factor=fm['profit_factor'],sum_result_usd=fm['sum_result_usd']),dict(comparison='delta_final_minus_original',rows=fm['rows']-om['rows'],win_rate=round(f(fm['win_rate'])-f(om['win_rate']),10),profit_factor=round(pfnum(fm['profit_factor'])-pfnum(om['profit_factor']),10),sum_result_usd=round(f(fm['sum_result_usd'])-f(om['sum_result_usd']),10))]
    blk=[dict(blocker_id='G3-35-001',blocker_name='inputs',status='CLOSED',detail='Stage31 and Stage15 found'),dict(blocker_id='G3-35-002',blocker_name='candidate preservation',status='CLOSED',detail='all 7 candidates remain active'),dict(blocker_id='G3-35-003',blocker_name='month filter',status='CLOSED',detail='not used')]
    mat=[dict(review_key='status',value=READY,detail='cumulative selected bands plus packet9 evaluated'),dict(review_key='active_candidate_rows',value=len(active),detail='all candidates active'),dict(review_key='selected_cut_rows',value=len(plan_rows),detail='global Saturday plus five packet filters'),dict(review_key='packet9_new_band_used',value=True,detail='rank2 m15_atr28 [3.878714, 3.998071)'),dict(review_key='old_packet9_band_used',value=False,detail='not used'),dict(review_key='month_filter_used',value=False,detail='not used'),dict(review_key='candidate_removal_used',value=False,detail='not used')]
    summary=dict(created_at_utc=now(),step=STEP,status=READY,selected_gold_v3_output_root=str(root),path_resolution_note=note,stage31_status=s31.get('status',''),active_candidate_rows=len(active),selected_cut_rows=len(plan_rows),before_after_rows=len(met_rows),removed_segment_rows=len(rem_rows),monthly_rows=len(mon_rows),candidate_removal_used=False,month_filter_used=False,saturday_cut_used=True,daily_cap_used=False,switching_used=False,old_packet9_band_used=False,new_packet9_band_used=True,review_scope='global Saturday plus accepted bands plus refined packet9 band')
    wcsv(out/'gold_v3_35_input_inventory.csv',inv_rows,INV); wcsv(out/'gold_v3_35_selected_cut_plan.csv',plan_rows,PLAN); wcsv(out/'gold_v3_35_before_after_metrics.csv',met_rows,MET); wcsv(out/'gold_v3_35_removed_segment_metrics.csv',rem_rows,REM); wcsv(out/'gold_v3_35_after_monthly_metrics.csv',mon_rows,MON); wcsv(out/'gold_v3_35_extended_totals.csv',tot,TOT); wcsv(out/'gold_v3_35_review_matrix.csv',mat,MAT); wcsv(out/'gold_v3_35_blocker_matrix.csv',blk,BLK); wjson(out/'gold_v3_35_summary.json',summary); (out/'GOLD_V3_35_CUMULATIVE_SELECTED_BAND_PRUNING_WITH_PACKET9_AUDIT_ONLY_REPORT.md').write_text(report(summary,plan_rows,met_rows,rem_rows,tot,blk),encoding='utf-8')
    print(json.dumps({'status':READY,'selected_cut_rows':len(plan_rows),'output_dir':str(out)},ensure_ascii=False,indent=2)); return 0
def fail(repo,e):
    root,note=pick(repo.resolve()); out=root/OUT; out.mkdir(parents=True,exist_ok=True); wjson(out/'gold_v3_35_summary.json',dict(created_at_utc=now(),step=STEP,status=ERR,blocked_reason=f'{e.__class__.__name__}: {e}',path_resolution_note=note)); (out/'gold_v3_35_exception.txt').write_text(traceback.format_exc(),encoding='utf-8')
def main(argv=None):
    ap=argparse.ArgumentParser(); ap.add_argument('--repo-root',default=''); a=ap.parse_args(argv); repo=Path(a.repo_root).resolve() if a.repo_root else repo_default()
    try: return run(repo)
    except Exception as e: fail(repo,e); print(traceback.format_exc(),file=sys.stderr); return 1
if __name__=='__main__': raise SystemExit(main())
