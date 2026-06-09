#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse,csv,hashlib,itertools,json,math,sys,traceback
from datetime import datetime,timezone
from pathlib import Path
import pandas as pd

STEP='GOLD_V3_22_WITHIN_CANDIDATE_LOSS_FEATURE_PRUNING_AUDIT_ONLY'
OUT_NAME='22_within_candidate_loss_feature_pruning_audit_only'
UP15='15_audit_only_replay_execution'; UP16='16_all_replay_result_review_and_narrowing_audit_only'; UP20='20_loss_feature_pruning_pf_uplift_audit_only'; UP21='21_selected_pruning_rule_validation_audit_only'
UP15_READY='GOLD_V3_15_AUDIT_ONLY_REPLAY_EXECUTION_READY_AUDIT_ONLY'; UP20_READY='GOLD_V3_20_LOSS_FEATURE_PRUNING_PF_UPLIFT_READY_AUDIT_ONLY'; UP21_READY='GOLD_V3_21_SELECTED_PRUNING_RULE_VALIDATION_READY_AUDIT_ONLY'
READY='GOLD_V3_22_WITHIN_CANDIDATE_LOSS_FEATURE_PRUNING_READY_AUDIT_ONLY'; BLOCKED='GOLD_V3_22_WITHIN_CANDIDATE_LOSS_FEATURE_PRUNING_BLOCKED_AUDIT_ONLY'; EXCEPTION='GOLD_V3_22_WITHIN_CANDIDATE_LOSS_FEATURE_PRUNING_EXCEPTION_AUDIT_ONLY'
FALSE_FLAGS=dict(auto_approval=False,final_candidate_approval=False,threshold_finalization=False,model_training=False,signals_generated=False,zip_output_created=False,ai_api_called=False,discord_enabled=False,mt5_enabled=False,live_hook_enabled=False,live_evaluator_enabled=False,final_signal_enabled=False,gold_v2_live_sot_used=False,quarantined_legacy_artifacts_read=False)
JULY='2025-07'; MIN_TPD=2.0; MIN_SEG=10; TOP_SEG=8; MAX_VARIANTS=30
INV=['input_label','path','required','exists','size_bytes','sha256']
BASE=['source_scenario_key','scenario_family','cooldown_minutes','existing_filter_ids','rows','trades_per_calendar_day','win_rate_result_positive','profit_factor','sum_result_usd','negative_months','worst_month','worst_month_sum','worst_month_pf','july_rows','july_win_rate_result_positive','july_profit_factor','july_sum_result_usd','max_drawdown_usd','max_consecutive_losses']
SEG=['source_scenario_key','candidate_segment_id','filter_description','filter_family','filter_type','rank_scope','column','values','low','high','segment_rows','segment_share','segment_win_rate','segment_profit_factor','segment_avg_result_usd','segment_sum_result_usd','base_win_rate','base_profit_factor','loss_score','entry_pre_known_only']
MET=['variant_key','source_scenario_key','scenario_family','cooldown_minutes','existing_filter_ids','added_filter_ids','added_filter_descriptions','total_filter_count','rows_before_filter','rows_after_filter_before_spacing','rows_after_spacing','trades_per_calendar_day','win_rate_result_positive','profit_factor','pf_uplift_vs_source','winrate_uplift_vs_source','sum_result_usd','avg_result_usd','median_result_usd','gross_profit_usd','gross_loss_abs_usd','negative_months','positive_months','worst_month','worst_month_sum','worst_month_pf','july_rows','july_win_rate_result_positive','july_profit_factor','july_sum_result_usd','max_drawdown_usd','max_consecutive_losses','score','audit_recommendation','audit_reason','not_final_approval']
MON=['variant_key','source_scenario_key','entry_month','rows','trades_per_calendar_day','win_rate_result_positive','profit_factor','sum_result_usd','max_drawdown_usd','max_consecutive_losses','month_bucket','is_july','is_worst_month']
TRACE=['variant_key','source_scenario_key','filter_origin','filter_id','filter_description','filter_family','filter_type','rank_scope','column','values','low','high','entry_pre_known_only']
REC=['recommendation_tier','variant_key','source_scenario_key','trades_per_calendar_day','win_rate_result_positive','profit_factor','pf_uplift_vs_source','negative_months','worst_month','worst_month_sum','july_profit_factor','july_sum_result_usd','added_filter_ids','added_filter_descriptions','reason','next_audit_action']
DEC=['decision_key','value','detail']; BLOCK=['blocker_id','blocker_name','status','detail']

def now(): return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')
def repo_default(): return Path(__file__).resolve().parents[2]
def files_root(repo:Path)->Path: return repo.parents[1] if len(repo.parents)>=2 else repo.parent
def roots(repo):
    a=files_root(repo)/'FX_OUTPUTS'/'gold_v3'; b=repo/'Files'/'FX_OUTPUTS'/'gold_v3'; return [a] if a==b else [a,b]
def select_root(repo):
    for p in roots(repo):
        if (p/UP21/'gold_v3_21_summary.json').exists(): return p,'selected_existing_stage21_root'
    for p in roots(repo):
        if (p/UP20/'gold_v3_20_summary.json').exists(): return p,'selected_existing_stage20_root'
    return roots(repo)[0],'selected_primary_gold_v3_root_no_stage20_or_21_inputs_found'
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()
def clean(x):
    try:
        if pd.isna(x): return None
    except Exception: pass
    if isinstance(x,float) and (math.isnan(x) or math.isinf(x)): return None
    if isinstance(x,dict): return {str(k):clean(v) for k,v in x.items()}
    if isinstance(x,list): return [clean(v) for v in x]
    return x
def wjson(p,o): p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(clean(o),ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf-8')
def wcsv(p,rows,fields):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore'); w.writeheader(); [w.writerow({k:r.get(k,'') for k in fields}) for r in rows]
def rcsv(p):
    with p.open('r',encoding='utf-8-sig',newline='') as f: return list(csv.DictReader(f))
def rjson(p): return json.loads(p.read_text(encoding='utf-8'))
def fnum(x,d=0.0):
    try: return float(str(x).strip())
    except Exception: return d
def pfnum(x): return 999999.0 if str(x).upper().startswith('INF') else fnum(x,-1.0)
def pf(res):
    gp=float(res[res>0].sum()); gl=float(-res[res<0].sum())
    if gl>0: return round(gp/gl,10),gp,gl
    if gp>0: return 'INF_NO_LOSS',gp,gl
    return '',gp,gl
def streak(vals):
    best=cur=0
    for v in vals:
        if v<0: cur+=1; best=max(best,cur)
        else: cur=0
    return best
def inv(items): return [dict(input_label=k,path=str(p),required=req,exists=p.exists(),size_bytes=p.stat().st_size if p.exists() else '',sha256=sha(p) if p.exists() else '') for k,p,req in items]
def prep_ledger(df,review):
    w=df.copy(); w['source_rank']=pd.to_numeric(w.source_rank,errors='coerce').astype('Int64').astype(int); w['_dt']=pd.to_datetime(w.entry_time_utc,utc=True,errors='coerce'); w=w[w._dt.notna()].copy(); j=w._dt+pd.Timedelta(hours=9); w['jst_hour']=j.dt.hour.astype(int); w['jst_weekday']=j.dt.day_name(); w['entry_month']=w.entry_month.astype(str) if 'entry_month' in w.columns else w._dt.dt.strftime('%Y-%m')
    pr={}
    if not review.empty and {'source_rank','score_objective_fit'}.issubset(review.columns):
        r=review.copy(); r.source_rank=pd.to_numeric(r.source_rank,errors='coerce'); r=r.dropna(subset=['source_rank']).sort_values(['score_objective_fit','profit_factor','win_rate_result_positive'],ascending=[False,False,False]); pr={int(x.source_rank):i+1 for i,x in enumerate(r.itertuples())}
    w['priority']=w.source_rank.map(pr).fillna(999).astype(int)
    for c in ['label_price_distance_result_usd','h1_atr56','h4_ret4','m15_atr28']:
        if c in w.columns: w[c]=pd.to_numeric(w[c],errors='coerce')
    return w
def ranks_for(fam,key):
    s=f'{fam} {key}'
    if 'R1_ONLY' in s: return [1]
    if 'R2_ONLY' in s: return [2]
    if 'MAIN_R1_R2' in s: return [1,2]
    return [1,2]
def apply_filters(df,filters):
    if df.empty or not filters: return df.copy()
    keep=pd.Series(True,index=df.index)
    for flt in filters:
        rs=str(flt.get('rank_scope','ALL')).strip(); mask=pd.Series(True,index=df.index)
        if rs and rs!='ALL': mask &= df.source_rank.eq(int(float(rs)))
        typ=str(flt.get('filter_type','categorical'))
        col=flt.get('column','')
        if col not in df.columns: continue
        if typ=='categorical':
            vals=set(str(flt.get('values','')).split(';')); mask &= df[col].astype(str).isin(vals)
        else:
            mask &= pd.to_numeric(df[col],errors='coerce').ge(fnum(flt.get('low'))) & pd.to_numeric(df[col],errors='coerce').lt(fnum(flt.get('high')))
        keep &= ~mask
    return df[keep].copy()
def cool(df,minutes):
    if df.empty: return df.copy()
    w=df.sort_values(['_dt','priority','source_rank'],kind='mergesort').drop_duplicates('entry_time_utc',keep='first')
    if int(float(minutes))<=0: return w
    step=int(float(minutes))*60*1_000_000_000; ns=w._dt.astype('int64').to_numpy(); keep=[]; last=None
    for i,t in enumerate(ns):
        if last is None or t>=last+step: keep.append(i); last=t
    return w.iloc[keep].copy()
def stream(ledger,ranks,cd,filters):
    raw=ledger[ledger.source_rank.isin(ranks)].copy(); aft=apply_filters(raw,filters); sp=cool(aft,cd); return sp,len(raw),len(aft)
def metrics(df):
    if df.empty: return dict(rows=0,calendar_days=0,active_days=0,trades_per_calendar_day=0,win_rate_result_positive=0,profit_factor='',sum_result_usd=0,avg_result_usd=0,median_result_usd=0,gross_profit_usd=0,gross_loss_abs_usd=0,max_drawdown_usd=0,max_consecutive_losses=0)
    w=df.sort_values('_dt'); res=pd.to_numeric(w.label_price_distance_result_usd,errors='coerce').fillna(0.0); dt=w._dt; days=(dt.max().date()-dt.min().date()).days+1; p,gp,gl=pf(res); cum=res.cumsum(); dd=float((cum.cummax()-cum).max())
    return dict(rows=len(w),calendar_days=int(days),active_days=int(dt.dt.date.nunique()),trades_per_calendar_day=round(len(w)/days,10) if days else 0,win_rate_result_positive=round(float((res>0).sum()/len(w)),10),profit_factor=p,sum_result_usd=round(float(res.sum()),10),avg_result_usd=round(float(res.mean()),10),median_result_usd=round(float(res.median()),10),gross_profit_usd=round(gp,10),gross_loss_abs_usd=round(gl,10),max_drawdown_usd=round(dd,10),max_consecutive_losses=streak(res.tolist()))
def monthly(df,key,months):
    rows=[]
    for m in months:
        part=df[df.entry_month.astype(str).eq(str(m))]; mt=metrics(part); bucket='NO_TRADE_MONTH' if mt['rows']==0 else ('NEGATIVE_MONTH' if mt['sum_result_usd']<0 else ('POSITIVE_MONTH' if mt['sum_result_usd']>0 else 'FLAT_MONTH'))
        rows.append(dict(variant_key=key,entry_month=m,rows=mt['rows'],trades_per_calendar_day=mt['trades_per_calendar_day'],win_rate_result_positive=mt['win_rate_result_positive'],profit_factor=mt['profit_factor'],sum_result_usd=mt['sum_result_usd'],max_drawdown_usd=mt['max_drawdown_usd'],max_consecutive_losses=mt['max_consecutive_losses'],month_bucket=bucket))
    sums=[r['sum_result_usd'] for r in rows]; pfs=[pfnum(r['profit_factor']) for r in rows if r['rows']>0]
    worst=rows[sums.index(min(sums))] if rows else {}
    return rows,dict(negative_months=sum(v<0 for v in sums),positive_months=sum(v>0 for v in sums),worst_month=worst.get('entry_month',''),worst_month_sum=round(min(sums) if sums else 0,10),worst_month_pf=worst.get('profit_factor',''),july_rows=next((r['rows'] for r in rows if r['entry_month']==JULY),0),july_win_rate_result_positive=next((r['win_rate_result_positive'] for r in rows if r['entry_month']==JULY),''),july_profit_factor=next((r['profit_factor'] for r in rows if r['entry_month']==JULY),''),july_sum_result_usd=next((r['sum_result_usd'] for r in rows if r['entry_month']==JULY),0))
def filter_sig(f): return (str(f.get('rank_scope','ALL')),str(f.get('filter_type','')),str(f.get('column','')),str(f.get('values','')),str(f.get('low','')),str(f.get('high','')))
def seg_row(src,i,fam,typ,rs,col,vals,lo,hi,seg,base):
    sm=metrics(seg); bm=metrics(base); share=sm['rows']/max(len(base),1); score=(pfnum(bm['profit_factor'])-max(0,pfnum(sm['profit_factor'])))*0.8+(fnum(bm['win_rate_result_positive'])-fnum(sm['win_rate_result_positive']))*4+max(0,-fnum(sm['avg_result_usd']))*0.05+share*0.4
    desc=f'exclude {col}={vals}' if typ=='categorical' else f'exclude rank {rs} {col} in [{lo}, {hi})'
    return dict(source_scenario_key=src,candidate_segment_id=f'{src}_S{i:03d}',filter_description=desc,filter_family=fam,filter_type=typ,rank_scope=rs,column=col,values=vals,low=lo,high=hi,segment_rows=sm['rows'],segment_share=round(share,10),segment_win_rate=sm['win_rate_result_positive'],segment_profit_factor=sm['profit_factor'],segment_avg_result_usd=sm['avg_result_usd'],segment_sum_result_usd=sm['sum_result_usd'],base_win_rate=bm['win_rate_result_positive'],base_profit_factor=bm['profit_factor'],loss_score=round(score,10),entry_pre_known_only=True)
def build_segments(src,base,existing):
    out=[]; existing_sigs=set(filter_sig(x) for x in existing); bm=metrics(base); bpf=pfnum(bm['profit_factor']); bwr=fnum(bm['win_rate_result_positive'])
    def add(r):
        sig=filter_sig(r)
        if sig in existing_sigs: return
        if r['segment_rows']>=MIN_SEG and (pfnum(r['segment_profit_factor'])<bpf*0.97 or fnum(r['segment_win_rate'])<bwr*0.97 or fnum(r['segment_avg_result_usd'])<0): out.append(r)
    i=0
    for col,fam in [('jst_hour','time_jst_hour'),('jst_weekday','time_jst_weekday')]:
        for v,g in base.groupby(col,dropna=False): i+=1; add(seg_row(src,i,fam,'categorical','ALL',col,str(v),'','',g,base))
    for rank,col in {1:'h4_ret4',2:'m15_atr28'}.items():
        if col not in base.columns: continue
        part=base[base.source_rank.eq(rank)&base[col].notna()]
        if len(part)<MIN_SEG*2: continue
        qs=part[col].quantile([x/8 for x in range(9)]).drop_duplicates().tolist()
        for lo,hi in zip(qs[:-1],qs[1:]):
            if hi>lo:
                i+=1; add(seg_row(src,i,f'rank{rank}_{col}_candidate_bin','numeric_bin',rank,col,'',round(float(lo),10),round(float(hi),10),part[part[col].ge(lo)&part[col].lt(hi)],base))
    out.sort(key=lambda r:(fnum(r['loss_score']),r['segment_rows']),reverse=True)
    return out[:TOP_SEG]
def seg_as_filter(s): return dict(filter_id=s['candidate_segment_id'],filter_description=s['filter_description'],filter_family=s['filter_family'],filter_type=s['filter_type'],rank_scope=s['rank_scope'],column=s['column'],values=s['values'],low=s['low'],high=s['high'],entry_pre_known_only=True)
def score(m):
    return round(38*min(max(pfnum(m['profit_factor']),0)/2.5,1.3)+24*min(fnum(m['win_rate_result_positive'])/0.66,1.25)+16*min(fnum(m['trades_per_calendar_day'])/MIN_TPD,2.0)/2+10*max(0,1-int(m['negative_months'])/3)+6*max(0,1-min(fnum(m['max_drawdown_usd'])/2500,1))+6*max(0,1-min(fnum(m['max_consecutive_losses'])/35,1))+max(0,fnum(m['pf_uplift_vs_source']))*16+max(0,fnum(m['winrate_uplift_vs_source']))*40,6)
def recommendation(m):
    pfv=pfnum(m['profit_factor']); wr=fnum(m['win_rate_result_positive']); tpd=fnum(m['trades_per_calendar_day']); neg=int(m['negative_months']); up=fnum(m['pf_uplift_vs_source']); july_pf=pfnum(m['july_profit_factor'])
    if tpd<MIN_TPD: return 'REQUEST_MORE_AUDIT_LOW_FREQUENCY','pruning improved quality but dropped below frequency objective'
    if pfv>=2.2 and wr>=0.63 and neg==0 and up>=0.12: return 'KEEP_FURTHER_PRUNED_SHORTLIST','within-candidate pruning materially improves PF/win-rate without switching'
    if pfv>=2.0 and neg<=1 and up>0.05 and july_pf>=1.0: return 'KEEP_FURTHER_PRUNED_REVIEW','further pruning improves candidate; validate robustness next'
    if up>0 and pfv>=1.8: return 'REQUEST_MORE_AUDIT','modest uplift; needs more robustness proof'
    return 'DROP_OR_NO_IMPROVEMENT','no useful within-candidate pruning improvement'
def eval_variant(ledger,source_key,fam,cd,ranks,existing,added,months,source_m):
    df,before,after=stream(ledger,ranks,cd,existing+added); mt=metrics(df); mon,ms=monthly(df,source_key+'__'+'__'.join(x['filter_id'] for x in added),months); mt.update(ms); mt.update(dict(variant_key=source_key+'__'+'__'.join(x['filter_id'] for x in added),source_scenario_key=source_key,scenario_family=fam,cooldown_minutes=cd,existing_filter_ids=';'.join(x.get('filter_id','') for x in existing),added_filter_ids=';'.join(x.get('filter_id','') for x in added),added_filter_descriptions=' | '.join(x.get('filter_description','') for x in added),total_filter_count=len(existing)+len(added),rows_before_filter=before,rows_after_filter_before_spacing=after,rows_after_spacing=mt['rows'],pf_uplift_vs_source=round(pfnum(mt['profit_factor'])-pfnum(source_m['profit_factor']),10),winrate_uplift_vs_source=round(fnum(mt['win_rate_result_positive'])-fnum(source_m['win_rate_result_positive']),10),not_final_approval=True)); mt['score']=score(mt); mt['audit_recommendation'],mt['audit_reason']=recommendation(mt)
    for r in mon: r.update(dict(source_scenario_key=source_key,is_july=r['entry_month']==JULY,is_worst_month=r['entry_month']==mt['worst_month']))
    return mt,mon
def base_row(key,fam,cd,filters,df,months):
    mt=metrics(df); mon,ms=monthly(df,key,months); mt.update(ms); return dict(source_scenario_key=key,scenario_family=fam,cooldown_minutes=cd,existing_filter_ids=';'.join(x.get('filter_id','') for x in filters),rows=mt['rows'],trades_per_calendar_day=mt['trades_per_calendar_day'],win_rate_result_positive=mt['win_rate_result_positive'],profit_factor=mt['profit_factor'],sum_result_usd=mt['sum_result_usd'],negative_months=mt['negative_months'],worst_month=mt['worst_month'],worst_month_sum=mt['worst_month_sum'],worst_month_pf=mt['worst_month_pf'],july_rows=mt['july_rows'],july_win_rate_result_positive=mt['july_win_rate_result_positive'],july_profit_factor=mt['july_profit_factor'],july_sum_result_usd=mt['july_sum_result_usd'],max_drawdown_usd=mt['max_drawdown_usd'],max_consecutive_losses=mt['max_consecutive_losses']),mt
def blockers(ok15,ok20,ok21,in_ok,seg_ok,met_ok):
    return [dict(blocker_id='G3-22-001',blocker_name='stage inputs',status='CLOSED' if ok15 and ok20 and ok21 and in_ok else 'OPEN_BLOCKER',detail='Stage15/20/21 READY inputs are required'),dict(blocker_id='G3-22-002',blocker_name='remaining loss segments',status='CLOSED' if seg_ok else 'OPEN_BLOCKER',detail='remaining loss-prone entry-feature segments must be generated'),dict(blocker_id='G3-22-003',blocker_name='further pruning metrics',status='CLOSED' if met_ok else 'OPEN_BLOCKER',detail='further-pruned candidate variants must be evaluated'),dict(blocker_id='G3-22-004',blocker_name='no switching',status='CLOSED',detail='Stage22 prunes within candidates; it does not switch by month/season'),dict(blocker_id='G3-22-005',blocker_name='no daily cap',status='CLOSED',detail='no daily cap is used'),dict(blocker_id='G3-22-006',blocker_name='final approval',status='CLOSED_BLOCKED_BY_POLICY',detail='Stage22 does not approve final candidates'),dict(blocker_id='G3-22-007',blocker_name='signal/live',status='CLOSED_BLOCKED_BY_POLICY',detail='signal/live/final signal remain OFF'),dict(blocker_id='G3-22-008',blocker_name='legacy quarantine',status='CLOSED',detail='GOLD V2 / old GOLD / DISC8 not read')]
def md(x): return str(x).replace('\n',' ').replace('\r',' ').replace('|','/')
def mdt(rows,cols,n=50):
    if not rows: return '_No rows._'
    out=['| '+' | '.join(cols)+' |','| '+' | '.join(['---']*len(cols))+' |']
    for r in rows[:n]: out.append('| '+' | '.join(md(r.get(c,''))[:500] for c in cols)+' |')
    return '\n'.join(out)
def report(summary,base,segs,mets,recs,blocks):
    lines=['# GOLD V3 22 within-candidate loss feature pruning audit-only report','',f"Created UTC: `{summary.get('created_at_utc','')}`",f"Status: `{summary.get('status','')}`",'','## Scope','','This stage does not switch candidates by season/month. It prunes remaining loss-prone entry-pre-known feature segments inside each selected candidate.','','## Counts']
    for k in ['base_candidate_rows','remaining_loss_segment_rows','further_pruned_metric_rows','monthly_metric_rows','recommendation_rows','switching_used','daily_cap_used']: lines.append(f"- {k}: `{summary.get(k,'')}`")
    lines+=['','## Base candidates','',mdt(base,['source_scenario_key','trades_per_calendar_day','win_rate_result_positive','profit_factor','negative_months','worst_month','worst_month_sum','july_profit_factor','july_sum_result_usd'],40),'','## Remaining loss segments','',mdt(segs,['source_scenario_key','candidate_segment_id','filter_description','segment_rows','segment_win_rate','segment_profit_factor','segment_avg_result_usd','loss_score'],80),'','## Further-pruned variants','',mdt(mets,['variant_key','source_scenario_key','added_filter_ids','trades_per_calendar_day','win_rate_result_positive','profit_factor','pf_uplift_vs_source','negative_months','worst_month','worst_month_sum','july_profit_factor','max_drawdown_usd','max_consecutive_losses','audit_recommendation'],60),'','## Recommendations','',mdt(recs,REC,40),'','## Blockers','',mdt(blocks,BLOCK,80),'','## Safety','','Audit-only. No switching, no month filter, no daily cap, no final approval, no live enablement.']
    return '\n'.join(lines)
def run(repo):
    repo=repo.resolve(); root,reason=select_root(repo); out=root/OUT_NAME
    p=dict(s15=root/UP15/'gold_v3_15_summary.json',ledger=root/UP15/'gold_v3_15_replay_trade_ledger.csv',review=root/UP16/'gold_v3_16_all_candidate_review.csv',s20=root/UP20/'gold_v3_20_summary.json',s21=root/UP21/'gold_v3_21_summary.json',sel=root/UP21/'gold_v3_21_selected_candidate_validation.csv',trace=root/UP21/'gold_v3_21_filter_traceability.csv')
    invr=inv([(k,v,True) for k,v in p.items()]); in_ok=all(x['exists'] for x in invr)
    if not in_ok: raise RuntimeError('missing Stage15/20/21 required inputs')
    s15=rjson(p['s15']); s20=rjson(p['s20']); s21=rjson(p['s21']); ok15=s15.get('status')==UP15_READY; ok20=s20.get('status')==UP20_READY and not bool(s20.get('daily_cap_used',True)); ok21=s21.get('status')==UP21_READY and not bool(s21.get('daily_cap_used',True))
    ledger=prep_ledger(pd.read_csv(p['ledger']),pd.read_csv(p['review'])); months=sorted(ledger.entry_month.dropna().astype(str).unique().tolist()); selected=rcsv(p['sel']); traces=rcsv(p['trace']); by_s={}
    for t in traces: by_s.setdefault(t.get('scenario_key',''),[]).append(dict(filter_id=t.get('filter_id',''),filter_description=t.get('filter_description',''),filter_family=t.get('filter_family',''),filter_type=t.get('filter_type',''),rank_scope=t.get('rank_scope','ALL'),column=t.get('column',''),values=t.get('values',''),low=t.get('low',''),high=t.get('high',''),entry_pre_known_only=True))
    base_rows=[]; base_metrics={}; all_segs=[]; all_mets=[]; all_mon=[]; all_trace=[]
    for row in selected:
        key=row['scenario_key']; fam=row.get('scenario_family') or ('R1_ONLY' if 'R1_ONLY' in key else 'MAIN_R1_R2'); cd=int(float(row.get('cooldown_minutes') or ''.join([c for c in key.split('_CD')[-1].split('_')[0] if c.isdigit()]) or 60)); ranks=ranks_for(fam,key); existing=by_s.get(key,[]); df,_,_=stream(ledger,ranks,cd,existing); br,bm=base_row(key,fam,cd,existing,df,months); base_rows.append(br); base_metrics[key]=bm
        segs=build_segments(key,df,existing); all_segs += segs; filt=[seg_as_filter(s) for s in segs]
        combos=[[x] for x in filt]
        for pair in itertools.combinations(filt[:5],2): combos.append(list(pair))
        for add in combos[:MAX_VARIANTS]:
            mt,mo=eval_variant(ledger,key,fam,cd,ranks,existing,add,months,bm); all_mets.append(mt); all_mon+=mo
            for fl in existing: all_trace.append(dict(variant_key=mt['variant_key'],source_scenario_key=key,filter_origin='existing_stage21',**fl))
            for fl in add: all_trace.append(dict(variant_key=mt['variant_key'],source_scenario_key=key,filter_origin='added_stage22',**fl))
    all_mets.sort(key=lambda r:(fnum(r['score']),pfnum(r['profit_factor']),fnum(r['win_rate_result_positive'])),reverse=True)
    recs=[]
    for r in [x for x in all_mets if x['audit_recommendation'] in {'KEEP_FURTHER_PRUNED_SHORTLIST','KEEP_FURTHER_PRUNED_REVIEW','REQUEST_MORE_AUDIT'}][:40]:
        tier='TIER_1_FURTHER_PRUNED_SHORTLIST' if r['audit_recommendation']=='KEEP_FURTHER_PRUNED_SHORTLIST' else ('TIER_2_FURTHER_PRUNED_REVIEW' if r['audit_recommendation']=='KEEP_FURTHER_PRUNED_REVIEW' else 'TIER_3_MORE_AUDIT')
        recs.append(dict(recommendation_tier=tier,variant_key=r['variant_key'],source_scenario_key=r['source_scenario_key'],trades_per_calendar_day=r['trades_per_calendar_day'],win_rate_result_positive=r['win_rate_result_positive'],profit_factor=r['profit_factor'],pf_uplift_vs_source=r['pf_uplift_vs_source'],negative_months=r['negative_months'],worst_month=r['worst_month'],worst_month_sum=r['worst_month_sum'],july_profit_factor=r['july_profit_factor'],july_sum_result_usd=r['july_sum_result_usd'],added_filter_ids=r['added_filter_ids'],added_filter_descriptions=r['added_filter_descriptions'],reason=r['audit_reason'],next_audit_action='Stage23 should create human intake for further-pruned shortlist only'))
    seg_ok=len(all_segs)>0; met_ok=len(all_mets)>0; status=READY if ok15 and ok20 and ok21 and in_ok and seg_ok and met_ok else BLOCKED; blocks=blockers(ok15,ok20,ok21,in_ok,seg_ok,met_ok)
    decisions=[dict(decision_key='selected_gold_v3_output_root',value=str(root),detail=reason),dict(decision_key='status',value=status,detail='within-candidate feature pruning audit-only status'),dict(decision_key='switching_used',value=False,detail='no seasonal/month switching'),dict(decision_key='month_filter_used',value=False,detail='month used for validation only'),dict(decision_key='daily_cap_used',value=False,detail='no daily cap'),dict(decision_key='final_candidate_approval',value=False,detail='blocked by policy'),dict(decision_key='signals_generated',value=False,detail='blocked by policy')]
    summary=dict(created_at_utc=now(),step=STEP,status=status,blocked_reason='' if status==READY else 'Stage22 within-candidate pruning checks failed',selected_gold_v3_output_root=str(root),path_resolution_note=reason,stage15_status=s15.get('status',''),stage20_status=s20.get('status',''),stage21_status=s21.get('status',''),base_candidate_rows=len(base_rows),remaining_loss_segment_rows=len(all_segs),further_pruned_metric_rows=len(all_mets),monthly_metric_rows=len(all_mon),filter_trace_rows=len(all_trace),recommendation_rows=len(recs),switching_used=False,month_filter_used=False,daily_cap_used=False,entry_pre_known_features_only=True,replay_scope='audit-only within-candidate feature pruning; not switching and not live',old_gold_disc8_quarantined=True,**FALSE_FLAGS)
    wcsv(out/'gold_v3_22_input_inventory.csv',invr,INV); wcsv(out/'gold_v3_22_base_candidate_metrics.csv',base_rows,BASE); wcsv(out/'gold_v3_22_remaining_loss_segment_audit.csv',all_segs,SEG); wcsv(out/'gold_v3_22_further_pruned_candidate_metrics.csv',all_mets,MET); wcsv(out/'gold_v3_22_further_pruned_monthly_metrics.csv',all_mon,MON); wcsv(out/'gold_v3_22_filter_traceability.csv',all_trace,TRACE); wcsv(out/'gold_v3_22_recommendation.csv',recs,REC); wcsv(out/'gold_v3_22_decision_matrix.csv',decisions,DEC); wcsv(out/'gold_v3_22_blocker_matrix.csv',blocks,BLOCK); wjson(out/'gold_v3_22_summary.json',summary); (out/'GOLD_V3_22_WITHIN_CANDIDATE_LOSS_FEATURE_PRUNING_AUDIT_ONLY_REPORT.md').write_text(report(summary,base_rows,all_segs,all_mets,recs,blocks),encoding='utf-8')
    print(json.dumps({'status':status,'base_candidate_rows':len(base_rows),'remaining_loss_segment_rows':len(all_segs),'further_pruned_metric_rows':len(all_mets),'switching_used':False,'daily_cap_used':False,'output_dir':str(out)},ensure_ascii=False,indent=2)); return 0 if status==READY else 2
def write_exception(repo,e):
    try: root,reason=select_root(repo.resolve())
    except Exception: root,reason=repo/'Files'/'FX_OUTPUTS'/'gold_v3','exception_fallback'
    out=root/OUT_NAME; out.mkdir(parents=True,exist_ok=True); wjson(out/'gold_v3_22_summary.json',dict(created_at_utc=now(),step=STEP,status=EXCEPTION,blocked_reason=f'{e.__class__.__name__}: {e}',selected_gold_v3_output_root=str(root),path_resolution_note=reason,**FALSE_FLAGS)); (out/'gold_v3_22_exception.txt').write_text(traceback.format_exc(),encoding='utf-8')
def main(argv=None):
    ap=argparse.ArgumentParser(); ap.add_argument('--repo-root',default=''); a=ap.parse_args(argv); repo=Path(a.repo_root).resolve() if a.repo_root else repo_default()
    try: return run(repo)
    except Exception as e: write_exception(repo,e); print('[GOLD_V3_22] EXCEPTION. See output gold_v3_22_exception.txt',file=sys.stderr); print(traceback.format_exc(),file=sys.stderr); return 1
if __name__=='__main__': raise SystemExit(main())
