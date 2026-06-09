#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse,csv,hashlib,json,sys,traceback
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
import pandas as pd

STEP='GOLD_V3_33_FEATURE_BAND_REVIEW_AUDIT_ONLY'
OUT='33_feature_band_review_audit_only'
UP31='31_all_active_candidate_uplift_queue_audit_only'
UP15='15_audit_only_replay_execution'
READY='GOLD_V3_33_FEATURE_BAND_REVIEW_READY_AUDIT_ONLY'
ERR='GOLD_V3_33_FEATURE_BAND_REVIEW_EXCEPTION_AUDIT_ONLY'
FEATURES=['h1_atr56','h4_ret4','m15_atr28']
INV=['input_label','path','required','exists','size_bytes','sha256']
BASE=['packet_row','source_scenario_key','variant_key','rows','trades_per_calendar_day','win_rate','profit_factor','sum_result_usd','saturday_rows_removed','saturday_sum_removed']
BINS=['packet_row','source_scenario_key','variant_key','feature_column','rank_scope','low','high','segment_rows','segment_win_rate','segment_profit_factor','segment_sum_result_usd','segment_avg_result_usd','win_count','loss_count','base_win_rate','base_profit_factor','loss_share','win_share','loss_win_share_ratio','review_score','band_note']
CUT=['packet_row','source_scenario_key','variant_key','feature_column','rank_scope','low','high','rows_before','rows_after','removed_rows','win_rate_before','win_rate_after','profit_factor_before','profit_factor_after','pf_delta','sum_before','sum_after','sum_delta','candidate_still_active']
SAT=['packet_row','source_scenario_key','variant_key','removed_rows','removed_win_rate','removed_profit_factor','removed_sum_result_usd']
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
    for c in ['label_price_distance_result_usd']+FEATURES:
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
def top_bins(df,packet,src,var):
    out=[]; base=metrics(df); res=df['label_price_distance_result_usd'].fillna(0); wins=res>0; losses=res<0; win_n=int(wins.sum()); loss_n=int(losses.sum())
    if win_n==0 or loss_n==0: return out
    for col in FEATURES:
        if col not in df.columns or df[col].dropna().nunique()<5: continue
        for rs in ['ALL'] + ([str(r) for r in sorted(df['source_rank'].unique())] if len(df['source_rank'].unique())>1 else []):
            part=df.copy() if rs=='ALL' else df[df['source_rank'].eq(int(rs))].copy()
            vals=part[col].dropna()
            if len(vals)<80 or vals.nunique()<5: continue
            qs=np.unique(np.quantile(vals,np.linspace(0,1,9)))
            for lo,hi in zip(qs[:-1],qs[1:]):
                if hi<=lo: continue
                mask=part[col].ge(lo)&(part[col].lt(hi) if hi<qs[-1] else part[col].le(hi)); seg=part[mask].copy()
                if len(seg)<25: continue
                sres=seg['label_price_distance_result_usd'].fillna(0); sw=int((sres>0).sum()); sl=int((sres<0).sum())
                if sl<5: continue
                loss_share=sl/max(loss_n,1); win_share=sw/max(win_n,1); ratio=loss_share/max(win_share,1e-9); sm=metrics(seg)
                score=(ratio-1)*2 + (f(base['win_rate'])-f(sm['win_rate']))*3 + max(0,pfnum(base['profit_factor'])-pfnum(sm['profit_factor']))*0.2 + max(0,-f(sm['sum_result_usd']))/100
                if ratio>=1.25 and f(sm['win_rate'])<f(base['win_rate']) and (pfnum(sm['profit_factor'])<pfnum(base['profit_factor']) or f(sm['sum_result_usd'])<0):
                    out.append(dict(packet_row=packet,source_scenario_key=src,variant_key=var,feature_column=col,rank_scope=rs,low=round(float(lo),10),high=round(float(hi),10),segment_rows=sm['rows'],segment_win_rate=sm['win_rate'],segment_profit_factor=sm['profit_factor'],segment_sum_result_usd=sm['sum_result_usd'],segment_avg_result_usd=sm['avg_result_usd'],win_count=sw,loss_count=sl,base_win_rate=base['win_rate'],base_profit_factor=base['profit_factor'],loss_share=round(loss_share,10),win_share=round(win_share,10),loss_win_share_ratio=round(ratio,10),review_score=round(score,10),band_note='loss share exceeds win share'))
    return sorted(out,key=lambda x:(f(x['review_score']),x['segment_rows']),reverse=True)
def single_cut(df,band,packet,src,var):
    before=metrics(df); col=band['feature_column']; rs=str(band['rank_scope']); mask=df[col].ge(f(band['low'])) & df[col].lt(f(band['high']))
    if rs!='ALL': mask &= df['source_rank'].eq(int(float(rs)))
    after=cool(df[~mask].copy(),60); aft=metrics(after)
    return dict(packet_row=packet,source_scenario_key=src,variant_key=var,feature_column=col,rank_scope=rs,low=band['low'],high=band['high'],rows_before=before['rows'],rows_after=aft['rows'],removed_rows=before['rows']-aft['rows'],win_rate_before=before['win_rate'],win_rate_after=aft['win_rate'],profit_factor_before=before['profit_factor'],profit_factor_after=aft['profit_factor'],pf_delta=round(pfnum(aft['profit_factor'])-pfnum(before['profit_factor']),10),sum_before=before['sum_result_usd'],sum_after=aft['sum_result_usd'],sum_delta=round(f(aft['sum_result_usd'])-f(before['sum_result_usd']),10),candidate_still_active=True)
def table(rows,cols,limit=40):
    if not rows: return '_No rows._'
    def md(x): return str(x).replace('\n',' ').replace('\r',' ').replace('|','/')[:220]
    out=['| '+' | '.join(cols)+' |','| '+' | '.join(['---']*len(cols))+' |']
    for r in rows[:limit]: out.append('| '+' | '.join(md(r.get(c,'')) for c in cols)+' |')
    return '\n'.join(out)
def report(summary,base,bins,cuts,blk):
    lines=['# GOLD V3 33 feature band review audit-only report','',f"Created UTC: `{summary['created_at_utc']}`",f"Status: `{summary['status']}`",'','## Counts']
    for k in ['active_candidate_rows','baseline_rows','indicator_band_rows','single_cut_rows','saturday_cut_applied_to_all_candidates','month_filter_used','candidate_removal_used']: lines.append(f"- {k}: `{summary.get(k,'')}`")
    lines+=['','## Baseline after Saturday exclusion','',table(base,BASE),'','## Loss-skew indicator bands','',table(bins,BINS),'','## Single-band cut backtest','',table(cuts,CUT),'','## Blockers','',table(blk,BLK),'','## Safety','','Audit-only. All candidates remain active. No month filter.']
    return '\n'.join(lines)
def run(repo):
    root,note=pick(repo.resolve()); out=root/OUT
    paths={'s31':root/UP31/'gold_v3_31_summary.json','active':root/UP31/'gold_v3_31_all_active_candidate_set.csv','contract':root/UP31/'gold_v3_31_all_active_filter_contract.csv','ledger':root/UP15/'gold_v3_15_replay_trade_ledger.csv'}
    inv_rows=inv(paths)
    if not all(x['exists'] for x in inv_rows): raise RuntimeError('missing inputs')
    s31=rjson(paths['s31']); active=rcsv(paths['active']); contract=rcsv(paths['contract']); ledger=prep(pd.read_csv(paths['ledger']))
    base_rows=[]; sat_rows=[]; bin_rows=[]; cut_rows=[]
    for a in active:
        packet=str(a.get('packet_row')); src=a.get('source_scenario_key',''); var=a.get('variant_key','')
        filters=[r for r in contract if str(r.get('packet_row'))==packet]
        raw=ledger[ledger['source_rank'].isin(ranks(src))].copy(); pre=cool(apply_filters(raw,filters),60)
        sat=pre[pre['jst_weekday'].eq('Saturday')].copy(); after=pre[~pre['jst_weekday'].eq('Saturday')].copy(); bm=metrics(after); sm=metrics(sat)
        base_rows.append(dict(packet_row=packet,source_scenario_key=src,variant_key=var,rows=bm['rows'],trades_per_calendar_day=bm['trades_per_calendar_day'],win_rate=bm['win_rate'],profit_factor=bm['profit_factor'],sum_result_usd=bm['sum_result_usd'],saturday_rows_removed=sm['rows'],saturday_sum_removed=sm['sum_result_usd']))
        sat_rows.append(dict(packet_row=packet,source_scenario_key=src,variant_key=var,removed_rows=sm['rows'],removed_win_rate=sm['win_rate'],removed_profit_factor=sm['profit_factor'],removed_sum_result_usd=sm['sum_result_usd']))
        bins=top_bins(after,packet,src,var); bin_rows.extend(bins)
        used=set()
        for b in bins[:3]:
            key=(b['feature_column'],b['rank_scope'])
            if key in used: continue
            used.add(key); cut_rows.append(single_cut(after,b,packet,src,var))
    bin_rows=sorted(bin_rows,key=lambda x:(f(x['review_score']),x['segment_rows']),reverse=True)
    blk=[dict(blocker_id='G3-33-001',blocker_name='inputs',status='CLOSED',detail='Stage31 and Stage15 files found'),dict(blocker_id='G3-33-002',blocker_name='candidate preservation',status='CLOSED',detail='all candidates kept active'),dict(blocker_id='G3-33-003',blocker_name='month filter',status='CLOSED',detail='not used')]
    mat=[dict(review_key='status',value=READY,detail='feature band review ready'),dict(review_key='active_candidate_rows',value=len(active),detail='all candidates active'),dict(review_key='saturday_cut_applied_to_all_candidates',value=True,detail='global Saturday cut'),dict(review_key='month_filter_used',value=False,detail='not used'),dict(review_key='candidate_removal_used',value=False,detail='not used')]
    summary=dict(created_at_utc=now(),step=STEP,status=READY,selected_gold_v3_output_root=str(root),path_resolution_note=note,stage31_status=s31.get('status',''),active_candidate_rows=len(active),baseline_rows=len(base_rows),indicator_band_rows=len(bin_rows),single_cut_rows=len(cut_rows),saturday_segment_rows=len(sat_rows),saturday_cut_applied_to_all_candidates=True,month_filter_used=False,candidate_removal_used=False,daily_cap_used=False,switching_used=False,review_scope='all active candidates with Saturday removed, indicator band loss-skew scan')
    wcsv(out/'gold_v3_33_input_inventory.csv',inv_rows,INV); wcsv(out/'gold_v3_33_active_baseline_after_saturday.csv',base_rows,BASE); wcsv(out/'gold_v3_33_indicator_loss_skew_bins.csv',bin_rows,BINS); wcsv(out/'gold_v3_33_indicator_single_cut_backtest.csv',cut_rows,CUT); wcsv(out/'gold_v3_33_saturday_removed_segments.csv',sat_rows,SAT); wcsv(out/'gold_v3_33_review_matrix.csv',mat,MAT); wcsv(out/'gold_v3_33_blocker_matrix.csv',blk,BLK); wjson(out/'gold_v3_33_summary.json',summary); (out/'GOLD_V3_33_FEATURE_BAND_REVIEW_AUDIT_ONLY_REPORT.md').write_text(report(summary,base_rows,bin_rows,cut_rows,blk),encoding='utf-8')
    print(json.dumps({'status':READY,'indicator_band_rows':len(bin_rows),'output_dir':str(out)},ensure_ascii=False,indent=2)); return 0
def fail(repo,e):
    root,note=pick(repo.resolve()); out=root/OUT; out.mkdir(parents=True,exist_ok=True); wjson(out/'gold_v3_33_summary.json',dict(created_at_utc=now(),step=STEP,status=ERR,blocked_reason=f'{e.__class__.__name__}: {e}',path_resolution_note=note)); (out/'gold_v3_33_exception.txt').write_text(traceback.format_exc(),encoding='utf-8')
def main(argv=None):
    ap=argparse.ArgumentParser(); ap.add_argument('--repo-root',default=''); a=ap.parse_args(argv); repo=Path(a.repo_root).resolve() if a.repo_root else repo_default()
    try: return run(repo)
    except Exception as e: fail(repo,e); print(traceback.format_exc(),file=sys.stderr); return 1
if __name__=='__main__': raise SystemExit(main())
