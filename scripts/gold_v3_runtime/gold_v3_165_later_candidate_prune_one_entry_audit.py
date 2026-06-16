#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse,json,math,time
from datetime import datetime,timezone
import pandas as pd
import gold_v3_107gy_light_non_calendar_subfilter_search_audit as gy
STEP='GOLD_V3_165_LATER_CANDIDATE_PRUNE_ONE_ENTRY_AUDIT_ONLY'
CUR='density_safe||100||Q0.6'
CUTOFF='2026-06-05 15:15:00'

def load(p): return pd.read_csv(p,encoding='utf-8-sig',low_memory=False) if p.exists() else pd.DataFrame()
def save(df,p): p.parent.mkdir(parents=True,exist_ok=True); df.to_csv(p,index=False,encoding='utf-8-sig')
def readj(p):
    try: return json.loads(p.read_text(encoding='utf-8')) if p.exists() else {}
    except Exception: return {}
def pf(s):
    x=pd.to_numeric(pd.Series(s),errors='coerce').dropna().astype(float)
    if x.empty: return 0.0
    gp=float(x[x>0].sum()); gl=float(-x[x<0].sum())
    return gp/gl if gl>0 else (math.inf if gp>0 else 0.0)
def col(df,names):
    for n in names:
        if n in df.columns: return n
    return ''
def metric(df,rc):
    if df.empty: return dict(events=0,sum=0.0,pf=0.0,wr=0.0,neg=0,months=0,neg_months=0,june_events=0,june_sum=0.0,min_entry_dt='',max_entry_dt='')
    r=pd.to_numeric(df[rc],errors='coerce').fillna(0); m=df.groupby('month')[rc].sum()
    return dict(events=int(len(df)),sum=float(r.sum()),pf=pf(r),wr=float((r>0).mean()),neg=int((r<0).sum()),months=int(len(m)),neg_months=int((m<0).sum()),june_events=int((df.month=='2026-06').sum()),june_sum=float(m.get('2026-06',0.0)),min_entry_dt=str(df.entry_dt.min()),max_entry_dt=str(df.entry_dt.max()))
def pref(d,p): return {p+k:v for k,v in d.items()}
def score_cols(df): return [c for c in ['feature_score','score','ledger_score','score_threshold'] if c in df.columns]
def one_entry(df,rc):
    if df.empty: return df.copy()
    x=df.copy(); sc=score_cols(x)
    for c in sc: x[c]=pd.to_numeric(x[c],errors='coerce')
    if sc: return x.sort_values(['entry_dt']+sc,ascending=[True]+[False]*len(sc),kind='mergesort').groupby('entry_dt',as_index=False).head(1)
    return x.sort_values(['entry_dt'],kind='mergesort').groupby('entry_dt',as_index=False).head(1)
def base_masks(x,cur):
    base=~x.policy_norm.eq(cur); out=[]
    if 'h1_up' in x: out.append(('ANY_H1_UP_TRUE','ANY_NON_CURRENT + h1_up=True',base & x.h1_up.astype(str).eq('True'),'BROAD'))
    if 'side' in x: out.append(('ANY_LONG','ANY_NON_CURRENT + side=LONG',base & x.side.astype(str).eq('LONG'),'BROAD'))
    out.append(('ANY_18_23','ANY_NON_CURRENT + hour_bucket=18_23',base & x.hour_bucket.eq('18_23'),'BROAD'))
    out.append(('DENSITY_Q035','density_safe||100||Q0.35',x.policy_norm.eq('density_safe||100||Q0.35'),'POLICY'))
    if 'd1_dist_atr' in x: out.append(('D1_DIST_LE_164','d1_dist_atr <= -1.641755654337',base & (pd.to_numeric(x.d1_dist_atr,errors='coerce')<=-1.641755654337),'FEATURE'))
    if 'h1_range_atr' in x: out.append(('H1_RANGE_LE_0737','h1_range_atr <= 0.737217834712',base & (pd.to_numeric(x.h1_range_atr,errors='coerce')<=0.737217834712),'FEATURE'))
    if 'm15_rsi14' in x: out.append(('M15_RSI_GE_6693','m15_rsi14 >= 66.932872868553',base & (pd.to_numeric(x.m15_rsi14,errors='coerce')>=66.932872868553),'FEATURE'))
    return out
def add_num_filters(filters,df,colname,direction,qs):
    if colname not in df.columns: return
    s=pd.to_numeric(df[colname],errors='coerce')
    if s.notna().sum()<20: return
    for q in qs:
        v=float(s.quantile(q))
        if direction=='le': filters.append((f'{colname}_LE_Q{q:g}',f'{colname} <= {v:.6f}',s<=v))
        else: filters.append((f'{colname}_GE_Q{q:g}',f'{colname} >= {v:.6f}',s>=v))
def build_filters(df):
    filters=[('NO_PRUNE','no extra pruning',pd.Series(True,index=df.index))]
    sc=score_cols(df)
    if sc:
        s=pd.to_numeric(df[sc[0]],errors='coerce')
        for q in [0.5,0.7,0.8,0.9]:
            v=float(s.quantile(q)); filters.append((f'{sc[0]}_GE_Q{q:g}',f'{sc[0]} >= {v:.6f}',s>=v))
    add_num_filters(filters,df,'d1_dist_atr','le',[0.1,0.2,0.3,0.4,0.5])
    add_num_filters(filters,df,'h1_range_atr','le',[0.1,0.2,0.3,0.4,0.5])
    add_num_filters(filters,df,'m15_rsi14','ge',[0.6,0.7,0.8,0.9])
    if 'hour_bucket' in df.columns:
        for h in ['00_05','06_11','12_17','18_23']:
            filters.append((f'hour_{h}',f'hour_bucket == {h}',df.hour_bucket.eq(h)))
    # conservative pair filters, built only when both primitives exist
    by=dict((name,(desc,mask)) for name,desc,mask in filters)
    pairs=[('feature_score_GE_Q0.7','d1_dist_atr_LE_Q0.3'),('score_GE_Q0.7','d1_dist_atr_LE_Q0.3'),('feature_score_GE_Q0.7','h1_range_atr_LE_Q0.3'),('d1_dist_atr_LE_Q0.3','h1_range_atr_LE_Q0.3'),('m15_rsi14_GE_Q0.7','h1_range_atr_LE_Q0.4')]
    for a,b in pairs:
        if a in by and b in by:
            filters.append((f'{a}__AND__{b}',by[a][0]+' AND '+by[b][0],by[a][1] & by[b][1]))
    return filters
def main():
    t0=time.time(); ap=argparse.ArgumentParser(); ap.add_argument('--mt5-files-dir',default=''); args=ap.parse_args(); mt5=gy.mt5_files_dir(args.mt5_files_dir); root=mt5/'FX_OUTPUTS'/'gold_v3'; out=root/'165'; out.mkdir(parents=True,exist_ok=True)
    s164=readj(root/'164'/'gold_v3_164_summary.json'); cur=str(s164.get('current_best_policy_key') or CUR)
    raw=load(root/'107k2c'/'gold_v3_107k2_all_regime_ledgers.csv'); blockers=[]; pc=col(raw,['policy_key','k2_policy_key','rule_key','policy']); rc=col(raw,['result_usd','worst_result_usd','pnl_usd','profit_usd','rep_result_usd'])
    if raw.empty: blockers.append({'id':'missing_ledger'})
    if not pc: blockers.append({'id':'missing_policy_column'})
    if not rc: blockers.append({'id':'missing_result_column'})
    rows=[]; monthly=[]
    if not blockers:
        x=raw.copy(); x['entry_dt']=pd.to_datetime(x['entry_dt'],errors='coerce'); x=x[x.entry_dt.notna()].copy(); x['month']=x.entry_dt.dt.to_period('M').astype(str); x['policy_norm']=x[pc].astype(str); x[rc]=pd.to_numeric(x[rc],errors='coerce').fillna(0); x['hour']=x.entry_dt.dt.hour; x['hour_bucket']=x.hour.map(lambda h:'00_05' if h<6 else ('06_11' if h<12 else ('12_17' if h<18 else '18_23')))
        cut=pd.Timestamp(CUTOFF); configs=base_masks(x,cur); total=0
        for lab,desc,bmask,kind in configs:
            rawc=x[bmask].copy(); filters=build_filters(rawc); total+=len(filters)
        done=0
        for lab,desc,bmask,kind in configs:
            rawc=x[bmask].copy(); base_oe=one_entry(rawc,rc); base_full_events=len(base_oe)
            for fname,fdesc,fmask in build_filters(rawc):
                done+=1; print(f'[PROGRESS] config {done}/{total} {lab} {fname}',flush=True)
                sub=rawc[fmask].copy(); oe=one_entry(sub,rc)
                rec={'candidate':lab,'candidate_desc':desc,'kind':kind,'prune_filter':fname,'prune_desc':fdesc,'raw_rows':int(len(sub)),'raw_unique_entry_dt':int(sub.entry_dt.nunique()),'base_one_full_events':int(base_full_events),'event_reduction_vs_base':int(base_full_events-len(oe))}
                rec.update(pref(metric(oe,rc),'one_full_')); rec.update(pref(metric(oe[oe.entry_dt>=cut],rc),'one_after_')); rec.update(pref(metric(oe[oe.entry_dt<cut],rc),'one_before_'))
                rec['practical_pass']=bool(rec['one_after_events']>=4 and rec['one_after_sum']>0 and rec['one_full_events']<=500 and rec['one_full_pf']>=1.5 and rec['one_full_neg_months']<=2)
                rec['rank_score']=rec['one_after_sum'] + rec['one_after_pf']*20 + rec['one_after_events']*5 - max(0,rec['one_full_events']-300)*0.35 - rec['one_full_neg_months']*40
                rows.append(rec)
                mo=oe.groupby('month')[rc].agg(['count','sum']).reset_index(); mo.insert(0,'candidate',lab); mo.insert(1,'prune_filter',fname); monthly.append(mo)
        rank=pd.DataFrame(rows).sort_values(['practical_pass','rank_score','one_after_sum'],ascending=[False,False,False]).reset_index(drop=True)
        save(rank,out/'gold_v3_165_later_candidate_prune_ranking.csv')
        if monthly: save(pd.concat(monthly,ignore_index=True),out/'gold_v3_165_later_candidate_prune_monthly.csv')
    else: rank=pd.DataFrame()
    top=rank.head(1) if not rank.empty else pd.DataFrame(); status='READY' if not blockers else 'INPUT_MISSING'; decision='LATER_CANDIDATE_PRUNE_READY' if status=='READY' else 'LATER_CANDIDATE_PRUNE_INPUT_MISSING'
    summary={'step':STEP,'status':status,'ready':not blockers,'decision':decision,'created_at_utc':datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z'),'output_dir':str(out),'audit_only':True,'review_only':True,'current_best_policy_key':cur,'evaluation_contract':'later candidates only; one entry per entry_dt; no stacking; non-result pruning filters','top_candidate':str(top.iloc[0].candidate) if not top.empty else '','top_prune_filter':str(top.iloc[0].prune_filter) if not top.empty else '','top_one_full_events':int(top.iloc[0].one_full_events) if not top.empty else 0,'top_one_after_events':int(top.iloc[0].one_after_events) if not top.empty else 0,'top_one_after_sum':float(top.iloc[0].one_after_sum) if not top.empty else 0.0,'top_one_after_pf':float(top.iloc[0].one_after_pf) if not top.empty else 0.0,'candidate_count':int(len(rank)) if not rank.empty else 0,'practical_pass_count':int(rank.practical_pass.sum()) if not rank.empty and 'practical_pass' in rank else 0,'source_164_decision':s164.get('decision',''),'source_csv_mutated':False,'contract_mutated':False,'open_asof_allowed':False,'candidate_pool_removed':False,'f002_exclusion_bypassed':False,'blocker_count':len(blockers),'elapsed_seconds':round(time.time()-t0,2)}
    (out/'gold_v3_165_summary.json').write_text(json.dumps(summary|{'blockers':blockers},ensure_ascii=False,indent=2),encoding='utf-8'); save(pd.DataFrame([summary]),out/'gold_v3_165_decision.csv')
    show=rank.head(80) if not rank.empty else rank
    lines=['GOLD V3 165 PASTE_ME_LATER_CANDIDATE_PRUNE_ONE_ENTRY_AUDIT']+[f'{k}: {v}' for k,v in summary.items()]+['','TOP_PRUNED_LATER_CANDIDATES_ONE_ENTRY',show.to_string(index=False) if not show.empty else 'NO_RANKING','','INTERPRETATION','This stage prunes broad later candidates while keeping the one-entry-per-timestamp rule. Filters are non-result filters only. Audit-only; no final/live.','','BLOCKERS','NO_BLOCKERS' if not blockers else json.dumps(blockers,ensure_ascii=False,indent=2)]
    (out/'paste_me.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({'ready':not blockers,'decision':decision,'paste_me':str(out/'paste_me.txt')},ensure_ascii=False)); return 0 if not blockers else 2
if __name__=='__main__': raise SystemExit(main())
