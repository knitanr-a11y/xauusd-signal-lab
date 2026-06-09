#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse,csv,hashlib,itertools,json,math,sys,traceback
from datetime import datetime,timezone
from pathlib import Path
import pandas as pd

STEP='GOLD_V3_20_LOSS_FEATURE_PRUNING_PF_UPLIFT_AUDIT_ONLY'
OUT_NAME='20_loss_feature_pruning_pf_uplift_audit_only'
UP15='15_audit_only_replay_execution'; UP16='16_all_replay_result_review_and_narrowing_audit_only'; UP18='18_monthly_stability_final_audit_shortlist_audit_only'; UP19='19_final_audit_shortlist_human_decision_template_audit_only'
READY='GOLD_V3_20_LOSS_FEATURE_PRUNING_PF_UPLIFT_READY_AUDIT_ONLY'; BLOCKED='GOLD_V3_20_LOSS_FEATURE_PRUNING_PF_UPLIFT_BLOCKED_AUDIT_ONLY'; EXCEPTION='GOLD_V3_20_LOSS_FEATURE_PRUNING_PF_UPLIFT_EXCEPTION_AUDIT_ONLY'
UP15_READY='GOLD_V3_15_AUDIT_ONLY_REPLAY_EXECUTION_READY_AUDIT_ONLY'; UP18_READY='GOLD_V3_18_MONTHLY_STABILITY_FINAL_AUDIT_SHORTLIST_READY_AUDIT_ONLY'; UP19_READY='GOLD_V3_19_FINAL_AUDIT_SHORTLIST_HUMAN_DECISION_TEMPLATE_READY_AUDIT_ONLY'
FALSE_FLAGS=dict(auto_approval=False,final_candidate_approval=False,threshold_finalization=False,model_training=False,signals_generated=False,zip_output_created=False,ai_api_called=False,discord_enabled=False,mt5_enabled=False,live_hook_enabled=False,live_evaluator_enabled=False,final_signal_enabled=False,gold_v2_live_sot_used=False,quarantined_legacy_artifacts_read=False)
BASE_RANKS=[1,2]; BASE_CD=60; MIN_TPD=2.0; MIN_SEG=30; TOP_FILTERS=18; MAX_STACKS=220
COOLDOWNS=[60,90,120,150,180,240,360]
INV=['input_label','path','required','exists','size_bytes','sha256']
SEG=['filter_id','filter_family','filter_type','rank_scope','column','values','low','high','segment_rows','segment_share','segment_win_rate','segment_profit_factor','segment_sum_result_usd','segment_avg_result_usd','baseline_win_rate','baseline_profit_factor','loss_enrichment_score','filter_description','leakage_check']
MET=['scenario_key','scenario_family','ranks','cooldown_minutes','filter_count','filter_ids','filter_descriptions','rows_before_filter','rows_after_filter_before_spacing','rows_after_spacing','calendar_days','active_days','trades_per_calendar_day','trades_per_active_day','win_rate_result_positive','profit_factor','pf_uplift_vs_baseline','winrate_uplift_vs_baseline','sum_result_usd','avg_result_usd','median_result_usd','gross_profit_usd','gross_loss_abs_usd','max_drawdown_usd','max_consecutive_losses','tp_count','sl_count','timeout_count','negative_months','positive_months','month_count','worst_month_sum','worst_month_pf','median_month_pf','score_pf_uplift','audit_recommendation','audit_reason','not_final_approval']
MON=['scenario_key','scenario_family','cooldown_minutes','filter_ids','entry_month','rows','trades_per_calendar_day','win_rate_result_positive','profit_factor','sum_result_usd','avg_result_usd','max_drawdown_usd','max_consecutive_losses','month_bucket']
REC=['recommendation_tier','scenario_key','scenario_family','cooldown_minutes','filter_ids','trades_per_calendar_day','win_rate_result_positive','profit_factor','pf_uplift_vs_baseline','negative_months','worst_month_sum','max_drawdown_usd','max_consecutive_losses','reason','next_audit_action']
DEC=['decision_key','value','detail']; BLOCK=['blocker_id','blocker_name','status','detail']

def now(): return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')
def repo_default(): return Path(__file__).resolve().parents[2]
def files_root(repo:Path)->Path: return repo.parents[1] if len(repo.parents)>=2 else repo.parent
def roots(repo):
    a=files_root(repo)/'FX_OUTPUTS'/'gold_v3'; b=repo/'Files'/'FX_OUTPUTS'/'gold_v3'; return [a] if a==b else [a,b]
def select_root(repo):
    for p in roots(repo):
        if (p/UP19/'gold_v3_19_summary.json').exists(): return p,'selected_existing_stage19_root'
    for p in roots(repo):
        if (p/UP18/'gold_v3_18_summary.json').exists(): return p,'selected_existing_stage18_root'
    for p in roots(repo):
        if (p/UP15/'gold_v3_15_summary.json').exists(): return p,'selected_existing_stage15_root'
    return roots(repo)[0],'selected_primary_gold_v3_root_no_stage15_or_later_inputs_found'
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()
def clean(x):
    if isinstance(x,dict): return {str(k):clean(v) for k,v in x.items()}
    if isinstance(x,list): return [clean(v) for v in x]
    try:
        if pd.isna(x): return None
    except Exception: pass
    if isinstance(x,float) and (math.isnan(x) or math.isinf(x)): return None
    return x
def wjson(p,o): p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(clean(o),ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf-8')
def wcsv(p,rows,fields):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore'); w.writeheader(); [w.writerow({k:r.get(k,'') for k in fields}) for r in rows]
def fnum(x,d=0.0):
    s=str(x).strip() if x is not None else ''
    if not s or s.lower() in {'nan','none'}: return d
    if s.upper().startswith('INF'): return 999999.0
    try: return float(s)
    except Exception: return d
def pfnum(x): return 999999.0 if str(x).upper().startswith('INF') else fnum(x,-1)
def maxloss(vals):
    best=cur=0
    for v in vals:
        if v<0: cur+=1; best=max(best,cur)
        else: cur=0
    return best
def pf(res):
    gp=float(res[res>0].sum()); gl=float(-res[res<0].sum())
    if gl>0: return round(gp/gl,10),gp,gl
    if gp>0: return 'INF_NO_LOSS',gp,gl
    return '',gp,gl
def metrics(df):
    if df.empty: return dict(rows=0,calendar_days=0,active_days=0,trades_per_calendar_day=0.0,trades_per_active_day=0.0,win_rate_result_positive=0.0,profit_factor='',sum_result_usd=0.0,avg_result_usd=0.0,median_result_usd=0.0,gross_profit_usd=0.0,gross_loss_abs_usd=0.0,max_drawdown_usd=0.0,max_consecutive_losses=0,tp_count=0,sl_count=0,timeout_count=0)
    w=df.sort_values('_dt'); res=pd.to_numeric(w.label_price_distance_result_usd,errors='coerce').fillna(0.0); n=len(w); dt=w._dt; days=(dt.max().date()-dt.min().date()).days+1; active=dt.dt.date.nunique(); p,gp,gl=pf(res); cum=res.cumsum(); dd=float((cum.cummax()-cum).max()) if n else 0
    return dict(rows=n,calendar_days=int(days),active_days=int(active),trades_per_calendar_day=round(n/days,10) if days else 0.0,trades_per_active_day=round(n/active,10) if active else 0.0,win_rate_result_positive=round(float((res>0).sum()/n),10),profit_factor=p,sum_result_usd=round(float(res.sum()),10),avg_result_usd=round(float(res.mean()),10),median_result_usd=round(float(res.median()),10),gross_profit_usd=round(gp,10),gross_loss_abs_usd=round(gl,10),max_drawdown_usd=round(dd,10),max_consecutive_losses=maxloss(res.tolist()),tp_count=int((w.label_outcome.astype(str)=='TP').sum()),sl_count=int((w.label_outcome.astype(str)=='SL').sum()),timeout_count=int((w.label_outcome.astype(str)=='TIMEOUT').sum()))
def monthly(df,key,months):
    rows=[]
    for m in months:
        part=df[df.entry_month.astype(str).eq(str(m))]; mt=metrics(part); bucket='NO_TRADE_MONTH' if mt['rows']==0 else ('NEGATIVE_MONTH' if mt['sum_result_usd']<0 else ('POSITIVE_MONTH' if mt['sum_result_usd']>0 else 'FLAT_MONTH'))
        rows.append(dict(scenario_key=key,entry_month=m,rows=mt['rows'],trades_per_calendar_day=mt['trades_per_calendar_day'],win_rate_result_positive=mt['win_rate_result_positive'],profit_factor=mt['profit_factor'],sum_result_usd=mt['sum_result_usd'],avg_result_usd=mt['avg_result_usd'],max_drawdown_usd=mt['max_drawdown_usd'],max_consecutive_losses=mt['max_consecutive_losses'],month_bucket=bucket))
    sums=[r['sum_result_usd'] for r in rows]; pfs=[pfnum(r['profit_factor']) for r in rows if r['rows']>0]
    return rows,dict(negative_months=sum(v<0 for v in sums),positive_months=sum(v>0 for v in sums),month_count=len(rows),worst_month_sum=round(min(sums) if sums else 0,10),worst_month_pf=round(min(pfs) if pfs else 0,10),median_month_pf=round(float(pd.Series(pfs).median()) if pfs else 0,10))
def prep_ledger(df,review):
    w=df.copy(); w['source_rank']=pd.to_numeric(w.source_rank,errors='coerce').astype('Int64').astype(int); w['_dt']=pd.to_datetime(w.entry_time_utc,utc=True,errors='coerce'); w=w[w._dt.notna()].copy(); j=w._dt+pd.Timedelta(hours=9); w['jst_hour']=j.dt.hour.astype(int); w['jst_weekday']=j.dt.day_name(); w['jst_weekday_num']=j.dt.weekday.astype(int); w['entry_month']=w.entry_month.astype(str) if 'entry_month' in w.columns else w._dt.dt.strftime('%Y-%m')
    pr={}
    if not review.empty and {'source_rank','score_objective_fit'}.issubset(review.columns):
        r=review.copy(); r.source_rank=pd.to_numeric(r.source_rank,errors='coerce'); r=r.dropna(subset=['source_rank']).sort_values(['score_objective_fit','profit_factor','win_rate_result_positive'],ascending=[False,False,False]); pr={int(x.source_rank):i+1 for i,x in enumerate(r.itertuples())}
    w['priority']=w.source_rank.map(pr).fillna(999).astype(int)
    for c in ['label_price_distance_result_usd','h1_atr56','h4_ret4','m15_atr28']:
        if c in w.columns: w[c]=pd.to_numeric(w[c],errors='coerce')
    return w
def cool(df,minutes):
    if df.empty: return df.copy()
    w=df.sort_values(['_dt','priority','source_rank'],kind='mergesort').drop_duplicates('entry_time_utc',keep='first')
    if minutes<=0: return w
    step=int(minutes)*60*1_000_000_000; ns=w._dt.astype('int64').to_numpy(); keep=[]; last=None
    for i,t in enumerate(ns):
        if last is None or t>=last+step: keep.append(i); last=t
    return w.iloc[keep].copy()
def apply_filters(df,filters):
    if df.empty or not filters: return df.copy()
    keep=pd.Series(True,index=df.index)
    for flt in filters:
        mask=pd.Series(True,index=df.index); rs=flt.get('rank_scope','ALL')
        if rs!='ALL': mask &= df.source_rank.eq(int(rs))
        if flt['filter_type']=='categorical': mask &= df[flt['column']].astype(str).isin(set(str(flt.get('values','')).split(';')))
        else: mask &= pd.to_numeric(df[flt['column']],errors='coerce').ge(fnum(flt['low'])) & pd.to_numeric(df[flt['column']],errors='coerce').lt(fnum(flt['high']))
        keep &= ~mask
    return df[keep].copy()
def select(ledger,ranks,cd,filters):
    raw=ledger[ledger.source_rank.isin(ranks)].copy(); after=apply_filters(raw,filters); return cool(after,cd),len(raw),len(after)
def seg_row(family,typ,rs,col,vals,lo,hi,seg,base):
    sm=metrics(seg); bm=metrics(base); share=sm['rows']/max(len(base),1); score=(pfnum(bm['profit_factor'])-max(pfnum(sm['profit_factor']),0))*0.55+(fnum(bm['win_rate_result_positive'])-fnum(sm['win_rate_result_positive']))*3+max(0,-fnum(sm['avg_result_usd']))*0.03+share*0.5; desc=f'exclude {col}={vals}' if typ=='categorical' else f'exclude rank {rs} {col} in [{lo}, {hi})'
    return dict(filter_id='',filter_family=family,filter_type=typ,rank_scope=rs,column=col,values=vals,low=lo,high=hi,segment_rows=sm['rows'],segment_share=round(share,10),segment_win_rate=sm['win_rate_result_positive'],segment_profit_factor=sm['profit_factor'],segment_sum_result_usd=sm['sum_result_usd'],segment_avg_result_usd=sm['avg_result_usd'],baseline_win_rate=bm['win_rate_result_positive'],baseline_profit_factor=bm['profit_factor'],loss_enrichment_score=round(score,10),filter_description=desc,leakage_check='entry_pre_known_feature_only')
def build_segments(base):
    out=[]; bm=metrics(base); bpf=pfnum(bm['profit_factor']); bwr=fnum(bm['win_rate_result_positive'])
    def add(r):
        if r['segment_rows']>=MIN_SEG and (pfnum(r['segment_profit_factor'])<bpf*0.98 or fnum(r['segment_win_rate'])<bwr*0.97 or fnum(r['segment_avg_result_usd'])<0): out.append(r)
    for col,fam in [('jst_hour','time_jst_hour'),('jst_weekday','time_jst_weekday')]:
        for v,g in base.groupby(col,dropna=False): add(seg_row(fam,'categorical','ALL',col,str(v),'','',g,base))
    for rank,col in {1:'h4_ret4',2:'m15_atr28',3:'h1_atr56',4:'h1_atr56',6:'h1_atr56',7:'h1_atr56',8:'h1_atr56'}.items():
        if col not in base.columns: continue
        part=base[base.source_rank.eq(rank)&base[col].notna()]
        if len(part)<MIN_SEG*2: continue
        qs=part[col].quantile([i/10 for i in range(11)]).drop_duplicates().tolist()
        for lo,hi in zip(qs[:-1],qs[1:]):
            if hi>lo: add(seg_row(f'rank{rank}_{col}_quantile_bin','numeric_bin',rank,col,'',round(float(lo),10),round(float(hi),10),part[part[col].ge(lo)&part[col].lt(hi)],base))
    out.sort(key=lambda r:(fnum(r['loss_enrichment_score']),r['segment_rows']),reverse=True)
    for i,r in enumerate(out,1): r['filter_id']=f'F{i:03d}'
    return out
def score(m):
    return round(38*min(max(pfnum(m['profit_factor']),0)/2.2,1.35)+24*min(fnum(m['win_rate_result_positive'])/0.66,1.25)+18*min(fnum(m['trades_per_calendar_day'])/MIN_TPD,2.5)/2.5+12*max(0,1-int(m['negative_months'])/3)+4*max(0,1-min(fnum(m['max_drawdown_usd'])/5000,1))+4*max(0,1-min(int(m['max_consecutive_losses'])/50,1))+max(0,fnum(m['pf_uplift_vs_baseline']))*12+max(0,fnum(m['winrate_uplift_vs_baseline']))*30,6)
def rec_for(m,fam):
    pfv=pfnum(m['profit_factor']); wr=fnum(m['win_rate_result_positive']); tpd=fnum(m['trades_per_calendar_day']); neg=int(m['negative_months']); up=fnum(m['pf_uplift_vs_baseline'])
    if fam.startswith('WEAK_'): return 'WEAK_DIAGNOSTIC_ONLY','weak profile retained only for filter-rescue transparency'
    if tpd<MIN_TPD: return 'REQUEST_MORE_AUDIT_LOW_FREQUENCY','PF may improve but frequency fell below objective'
    if pfv>=2.0 and wr>=0.63 and neg<=1 and up>=0.25: return 'KEEP_PF_UPLIFT_SHORTLIST','feature pruning materially improves PF/win-rate while preserving frequency'
    if pfv>=1.8 and wr>=0.61 and neg<=2 and up>=0.15: return 'KEEP_PF_UPLIFT_CANDIDATE','PF uplift candidate; verify monthly robustness next'
    if fam in {'R1_ONLY','R2_ONLY'} and pfv>=1.65 and wr>=0.58 and tpd>=MIN_TPD: return 'KEEP_ADDITIONAL_CANDIDATE_REVIEW','single-rank additional candidate; compare correlation and month bias'
    if pfv>=1.65 and up>0: return 'REQUEST_MORE_AUDIT','some PF uplift but not strong enough yet'
    return 'DROP_OR_FILTER_RESCUE_ONLY','insufficient PF/win-rate uplift for shortlist'
def eval_scenario(ledger,key,fam,ranks,cd,filters,months,base_m):
    df,before,after=select(ledger,ranks,cd,filters); mt=metrics(df); mon,mons=monthly(df,key,months); mt.update(mons); mt.update(dict(scenario_key=key,scenario_family=fam,ranks=','.join(map(str,ranks)),cooldown_minutes=cd,filter_count=len(filters),filter_ids=';'.join(f['filter_id'] for f in filters),filter_descriptions=' | '.join(f['filter_description'] for f in filters),rows_before_filter=before,rows_after_filter_before_spacing=after,rows_after_spacing=mt['rows'],pf_uplift_vs_baseline=round(pfnum(mt['profit_factor'])-pfnum(base_m['profit_factor']),10),winrate_uplift_vs_baseline=round(fnum(mt['win_rate_result_positive'])-fnum(base_m['win_rate_result_positive']),10),not_final_approval=True)); mt['score_pf_uplift']=score(mt); mt['audit_recommendation'],mt['audit_reason']=rec_for(mt,fam)
    for r in mon: r.update(dict(scenario_family=fam,cooldown_minutes=cd,filter_ids=mt['filter_ids']))
    return mt,mon
def build_scenarios(ledger,filters,months,base_m):
    rows=[]; mon=[]; defs=[('MAIN_R1_R2',[1,2]),('R1_ONLY',[1]),('R2_ONLY',[2]),('MAIN_R1_R2_PLUS_H1_R3',[1,2,3]),('MAIN_R1_R2_PLUS_H1_R4',[1,2,4]),('MAIN_R1_R2_PLUS_H1_R6',[1,2,6]),('WEAK_H1_R7_DIAGNOSTIC',[7]),('WEAK_H1_R8_DIAGNOSTIC',[8])]
    for fam,ranks in defs:
        for cd in ([60] if fam.startswith('WEAK_') else COOLDOWNS):
            m,mm=eval_scenario(ledger,f'{fam}_CD{cd}_NO_PRUNING',fam,ranks,cd,[],months,base_m); rows.append(m); mon+=mm
    top=filters[:TOP_FILTERS]; stacks=[[f] for f in top]
    for k in [2,3]:
        for combo in itertools.combinations(top[:12],k):
            fams=[c['filter_family'] for c in combo]
            if k==3 and len(fams)!=len(set(fams)): continue
            stacks.append(list(combo))
            if len(stacks)>=MAX_STACKS: break
        if len(stacks)>=MAX_STACKS: break
    for i,stack in enumerate(stacks[:MAX_STACKS],1):
        for fam,ranks,cds in [('MAIN_R1_R2',[1,2],[60,90,120]),('R1_ONLY',[1],[60,90,120]),('R2_ONLY',[2],[60,90,120])]:
            if any(f.get('rank_scope','ALL')!='ALL' and int(f['rank_scope']) not in ranks for f in stack): continue
            for cd in cds:
                m,mm=eval_scenario(ledger,f'{fam}_CD{cd}_PRUNE_{i:03d}',fam,ranks,cd,stack,months,base_m); rows.append(m); mon+=mm
    rows.sort(key=lambda r:(fnum(r['score_pf_uplift']),pfnum(r['profit_factor']),fnum(r['win_rate_result_positive'])),reverse=True); return rows,mon
def recommendations(metrics):
    good=[r for r in metrics if r['audit_recommendation'] in {'KEEP_PF_UPLIFT_SHORTLIST','KEEP_PF_UPLIFT_CANDIDATE','KEEP_ADDITIONAL_CANDIDATE_REVIEW'}]
    good.sort(key=lambda r:(0 if r['scenario_family']=='MAIN_R1_R2' else 1,-fnum(r['score_pf_uplift']))); rec=[]
    for r in good[:30]:
        tier='TIER_1_PF_UPLIFT_MAIN' if r['audit_recommendation']=='KEEP_PF_UPLIFT_SHORTLIST' and r['scenario_family']=='MAIN_R1_R2' else ('TIER_2_ADDITIONAL_CANDIDATE' if r['scenario_family'] in {'R1_ONLY','R2_ONLY'} else 'TIER_3_REVIEW')
        rec.append(dict(recommendation_tier=tier,scenario_key=r['scenario_key'],scenario_family=r['scenario_family'],cooldown_minutes=r['cooldown_minutes'],filter_ids=r['filter_ids'],trades_per_calendar_day=r['trades_per_calendar_day'],win_rate_result_positive=r['win_rate_result_positive'],profit_factor=r['profit_factor'],pf_uplift_vs_baseline=r['pf_uplift_vs_baseline'],negative_months=r['negative_months'],worst_month_sum=r['worst_month_sum'],max_drawdown_usd=r['max_drawdown_usd'],max_consecutive_losses=r['max_consecutive_losses'],reason=r['audit_reason'],next_audit_action='Stage21 should validate selected pruning rules on monthly rows and produce human intake template'))
    for r in [x for x in metrics if x['scenario_family'].startswith('WEAK_')][:4]: rec.append(dict(recommendation_tier='TIER_4_WEAK_DIAGNOSTIC_ONLY',scenario_key=r['scenario_key'],scenario_family=r['scenario_family'],cooldown_minutes=r['cooldown_minutes'],filter_ids=r['filter_ids'],trades_per_calendar_day=r['trades_per_calendar_day'],win_rate_result_positive=r['win_rate_result_positive'],profit_factor=r['profit_factor'],pf_uplift_vs_baseline=r['pf_uplift_vs_baseline'],negative_months=r['negative_months'],worst_month_sum=r['worst_month_sum'],max_drawdown_usd=r['max_drawdown_usd'],max_consecutive_losses=r['max_consecutive_losses'],reason='weak diagnostic retained; not a main candidate',next_audit_action='do not promote unless explicit filter-rescue request'))
    return rec
def month_bias(mon,base_mon):
    b={r['entry_month']:r for r in base_mon}; out=[]
    for r in mon:
        bb=b.get(r['entry_month'],{}); out.append(dict(scenario_key=r['scenario_key'],scenario_family=r.get('scenario_family',''),cooldown_minutes=r.get('cooldown_minutes',''),filter_ids=r.get('filter_ids',''),entry_month=r['entry_month'],rows=r['rows'],win_rate_result_positive=r['win_rate_result_positive'],profit_factor=r['profit_factor'],sum_result_usd=r['sum_result_usd'],baseline_profit_factor=bb.get('profit_factor',''),baseline_sum_result_usd=bb.get('sum_result_usd',''),pf_vs_baseline_delta=round(pfnum(r['profit_factor'])-pfnum(bb.get('profit_factor','')),10) if r['rows'] and bb else '',sum_vs_baseline_delta=round(fnum(r['sum_result_usd'])-fnum(bb.get('sum_result_usd')),10) if bb else '',month_bucket=r['month_bucket']))
    return out
def blockers(ok15,ok18,ok19,in_ok,seg_ok,met_ok):
    return [dict(blocker_id='G3-20-001',blocker_name='stage-15 ledger',status='CLOSED' if ok15 and in_ok else 'OPEN_BLOCKER',detail='Stage 15 READY ledger is required'),dict(blocker_id='G3-20-002',blocker_name='stage-18/19 context',status='CLOSED' if ok18 and ok19 and in_ok else 'OPEN_BLOCKER',detail='Stage 18 and 19 READY context is required'),dict(blocker_id='G3-20-003',blocker_name='loss feature segments',status='CLOSED' if seg_ok else 'OPEN_BLOCKER',detail='entry-pre-known loss-feature segments must be generated'),dict(blocker_id='G3-20-004',blocker_name='no daily cap',status='CLOSED',detail='Stage 20 uses feature pruning only; no daily cap or outcome-after-entry filters'),dict(blocker_id='G3-20-005',blocker_name='PF uplift metrics',status='CLOSED' if met_ok else 'OPEN_BLOCKER',detail='PF uplift scenarios and monthly metrics must be generated'),dict(blocker_id='G3-20-006',blocker_name='rank 7/8 visibility',status='CLOSED' if met_ok else 'OPEN_BLOCKER',detail='rank 7/8 remain weak diagnostic rows'),dict(blocker_id='G3-20-007',blocker_name='final approval',status='CLOSED_BLOCKED_BY_POLICY',detail='Stage 20 does not approve final candidates'),dict(blocker_id='G3-20-008',blocker_name='threshold finalization',status='CLOSED_BLOCKED_BY_POLICY',detail='Stage 20 does not finalize thresholds'),dict(blocker_id='G3-20-009',blocker_name='model training',status='CLOSED_BLOCKED_BY_POLICY',detail='Stage 20 does not train models'),dict(blocker_id='G3-20-010',blocker_name='signal/live',status='CLOSED_BLOCKED_BY_POLICY',detail='signal/live/final signal remain OFF'),dict(blocker_id='G3-20-011',blocker_name='zip output',status='CLOSED_DISABLED',detail='ZIP output disabled'),dict(blocker_id='G3-20-012',blocker_name='external actions',status='CLOSED',detail='Discord/MT5/AI/live integrations remain OFF'),dict(blocker_id='G3-20-013',blocker_name='legacy quarantine',status='CLOSED',detail='GOLD V2 / old GOLD / DISC8 not read')]
def md(x): return str(x).replace('\n',' ').replace('\r',' ').replace('|','/')
def mdt(rows,fields,n=30):
    if not rows: return '_No rows._'
    out=['| '+' | '.join(fields)+' |','| '+' | '.join(['---']*len(fields))+' |']
    for r in rows[:n]: out.append('| '+' | '.join(md(r.get(c,''))[:500] for c in fields)+' |')
    return '\n'.join(out)
def report(summary,segs,metrics,recs,blocks):
    lines=['# GOLD V3 20 loss feature pruning PF uplift audit-only report','',f"Created UTC: `{summary.get('created_at_utc','')}`",f"Status: `{summary.get('status','')}`",'','## Scope','','This stage audits entry-pre-known loss-feature pruning. It does not use daily trade caps. It is not final approval and not live approval.','','## Counts']
    for k in ['baseline_scenario','baseline_profit_factor','baseline_win_rate','baseline_trades_per_calendar_day','loss_segment_rows','scenario_metric_rows','monthly_metric_rows','recommendation_rows','keep_pf_uplift_rows','additional_candidate_rows','daily_cap_used']: lines.append(f"- {k}: `{summary.get(k,'')}`")
    lines+=['','## Top loss-feature segments','',mdt(segs,['filter_id','filter_description','segment_rows','segment_share','segment_win_rate','segment_profit_factor','segment_avg_result_usd','loss_enrichment_score'],25),'','## Top PF uplift scenarios','',mdt(metrics,['scenario_key','scenario_family','cooldown_minutes','filter_count','filter_ids','trades_per_calendar_day','win_rate_result_positive','profit_factor','pf_uplift_vs_baseline','negative_months','worst_month_sum','max_drawdown_usd','max_consecutive_losses','audit_recommendation'],30),'','## Recommendations','',mdt(recs,REC,40),'','## Blockers','',mdt(blocks,BLOCK,80),'','## Safety','','Stage 20 uses only entry-pre-known features such as source_rank, JST hour, weekday, h4_ret4, m15_atr28, and h1_atr56. It does not approve final candidates, finalize thresholds, train models, generate signals, create ZIP output, call AI API, notify Discord, place MT5 orders, or enable live hooks/evaluators/final signals.']
    return '\n'.join(lines)
def run(repo):
    repo=repo.resolve(); root,reason=select_root(repo); out=root/OUT_NAME; p=dict(s15=root/UP15/'gold_v3_15_summary.json',ledger=root/UP15/'gold_v3_15_replay_trade_ledger.csv',review=root/UP16/'gold_v3_16_all_candidate_review.csv',s18=root/UP18/'gold_v3_18_summary.json',m18=root/UP18/'gold_v3_18_scenario_monthly_metrics.csv',s19=root/UP19/'gold_v3_19_summary.json')
    inv=[dict(input_label=k,path=str(v),required=True,exists=v.exists(),size_bytes=v.stat().st_size if v.exists() else '',sha256=sha(v) if v.exists() else '') for k,v in p.items()]
    in_ok=all(r['exists'] for r in inv)
    if not in_ok: raise RuntimeError('missing Stage 15/16/18/19 required inputs')
    s15=json.loads(p['s15'].read_text(encoding='utf-8')); s18=json.loads(p['s18'].read_text(encoding='utf-8')); s19=json.loads(p['s19'].read_text(encoding='utf-8')); ok15=s15.get('status')=='GOLD_V3_15_AUDIT_ONLY_REPLAY_EXECUTION_READY_AUDIT_ONLY'; ok18=s18.get('status')=='GOLD_V3_18_MONTHLY_STABILITY_FINAL_AUDIT_SHORTLIST_READY_AUDIT_ONLY'; ok19=s19.get('status')=='GOLD_V3_19_FINAL_AUDIT_SHORTLIST_HUMAN_DECISION_TEMPLATE_READY_AUDIT_ONLY'
    ledger=prep_ledger(pd.read_csv(p['ledger']),pd.read_csv(p['review'])); months=sorted(ledger.entry_month.dropna().astype(str).unique().tolist()); base,_,_=select(ledger,BASE_RANKS,BASE_CD,[]); base_m=metrics(base); base_mon,base_mons=monthly(base,'MAIN_R1_R2_CD60_BASELINE_NO_PRUNING',months); segs=build_segments(base); mets,mons=build_scenarios(ledger,segs,months,base_m); recs=recommendations(mets); mbias=month_bias(mons,base_mon)
    seg_ok=len(segs)>0; met_ok=len(mets)>0 and any(r['scenario_family']=='R1_ONLY' for r in mets) and any(r['scenario_family'].startswith('WEAK_') for r in mets); keep=sum(1 for r in mets if r['audit_recommendation'] in {'KEEP_PF_UPLIFT_SHORTLIST','KEEP_PF_UPLIFT_CANDIDATE'}); add=sum(1 for r in mets if r['audit_recommendation']=='KEEP_ADDITIONAL_CANDIDATE_REVIEW'); status=READY if ok15 and ok18 and ok19 and in_ok and seg_ok and met_ok else BLOCKED; blocks=blockers(ok15,ok18,ok19,in_ok,seg_ok,met_ok)
    decisions=[dict(decision_key='selected_gold_v3_output_root',value=str(root),detail=reason),dict(decision_key='status',value=status,detail='loss-feature pruning PF uplift audit-only status'),dict(decision_key='daily_cap_used',value=False,detail='no daily cap; only feature pruning'),dict(decision_key='final_candidate_approval',value=False,detail='blocked by policy'),dict(decision_key='threshold_finalization',value=False,detail='blocked by policy'),dict(decision_key='model_training',value=False,detail='blocked by policy'),dict(decision_key='signals_generated',value=False,detail='blocked by policy'),dict(decision_key='zip_output_created',value=False,detail='disabled'),dict(decision_key='external_actions',value=False,detail='Discord/MT5/AI/live integrations remain OFF')]
    summary=dict(created_at_utc=now(),step=STEP,status=status,blocked_reason='' if status==READY else 'Stage 20 loss-feature pruning checks failed',selected_gold_v3_output_root=str(root),path_resolution_note=reason,stage15_status=s15.get('status',''),stage18_status=s18.get('status',''),stage19_status=s19.get('status',''),baseline_scenario='MAIN_R1_R2_CD60_BASELINE_NO_PRUNING',baseline_profit_factor=base_m['profit_factor'],baseline_win_rate=base_m['win_rate_result_positive'],baseline_trades_per_calendar_day=base_m['trades_per_calendar_day'],baseline_negative_months=base_mons['negative_months'],loss_segment_rows=len(segs),scenario_metric_rows=len(mets),monthly_metric_rows=len(mons),month_bias_rows=len(mbias),recommendation_rows=len(recs),keep_pf_uplift_rows=keep,additional_candidate_rows=add,daily_cap_used=False,entry_pre_known_features_only=True,rank_7_8_visible=True,replay_scope='audit-only entry-feature pruning; not final/live approval',old_gold_disc8_quarantined=True,**FALSE_FLAGS)
    wcsv(out/'gold_v3_20_input_inventory.csv',inv,INV); wcsv(out/'gold_v3_20_loss_segment_audit.csv',segs,SEG); wcsv(out/'gold_v3_20_scenario_metrics.csv',mets,MET); wcsv(out/'gold_v3_20_scenario_monthly_metrics.csv',mons,MON); wcsv(out/'gold_v3_20_month_bias_matrix.csv',mbias,['scenario_key','scenario_family','cooldown_minutes','filter_ids','entry_month','rows','win_rate_result_positive','profit_factor','sum_result_usd','baseline_profit_factor','baseline_sum_result_usd','pf_vs_baseline_delta','sum_vs_baseline_delta','month_bucket']); wcsv(out/'gold_v3_20_pf_uplift_recommendation.csv',recs,REC); wcsv(out/'gold_v3_20_decision_matrix.csv',decisions,DEC); wcsv(out/'gold_v3_20_blocker_matrix.csv',blocks,BLOCK); wjson(out/'gold_v3_20_summary.json',summary); (out/'GOLD_V3_20_LOSS_FEATURE_PRUNING_PF_UPLIFT_AUDIT_ONLY_REPORT.md').write_text(report(summary,segs,mets,recs,blocks),encoding='utf-8')
    print(json.dumps({'status':status,'baseline_pf':base_m['profit_factor'],'loss_segment_rows':len(segs),'scenario_metric_rows':len(mets),'recommendation_rows':len(recs),'daily_cap_used':False,'output_dir':str(out),'final_candidate_approval':False,'signals_generated':False,'zip_output_created':False},ensure_ascii=False,indent=2)); return 0 if status==READY else 2
def write_exception(repo,e):
    try: root,reason=select_root(repo.resolve())
    except Exception: root,reason=repo/'Files'/'FX_OUTPUTS'/'gold_v3','exception_fallback'
    out=root/OUT_NAME; out.mkdir(parents=True,exist_ok=True); wjson(out/'gold_v3_20_summary.json',dict(created_at_utc=now(),step=STEP,status=EXCEPTION,blocked_reason=f'{e.__class__.__name__}: {e}',selected_gold_v3_output_root=str(root),path_resolution_note=reason,**FALSE_FLAGS)); (out/'gold_v3_20_exception.txt').write_text(traceback.format_exc(),encoding='utf-8')
def main(argv=None):
    ap=argparse.ArgumentParser(); ap.add_argument('--repo-root',default=''); a=ap.parse_args(argv); repo=Path(a.repo_root).resolve() if a.repo_root else repo_default()
    try: return run(repo)
    except Exception as e: write_exception(repo,e); print('[GOLD_V3_20] EXCEPTION. See output gold_v3_20_exception.txt',file=sys.stderr); print(traceback.format_exc(),file=sys.stderr); return 1
if __name__=='__main__': raise SystemExit(main())
