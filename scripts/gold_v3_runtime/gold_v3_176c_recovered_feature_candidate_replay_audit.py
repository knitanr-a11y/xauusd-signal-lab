#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse
import json
import math
import time
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
import gold_v3_107gy_light_non_calendar_subfilter_search_audit as gy

STEP='GOLD_V3_176C_RECOVERED_FEATURE_CANDIDATE_REPLAY_AUDIT_ONLY'
CUR='density_safe||100||Q0.6'
P2POL='density_safe||100||Q0.35'
CUTOFF='2026-06-05 15:15:00'


def read_csv_any(path: Path) -> pd.DataFrame:
    if not path.exists(): return pd.DataFrame()
    for enc in ['utf-8-sig','utf-8','cp932']:
        for sep in [',',';','\t']:
            try:
                df=pd.read_csv(path,encoding=enc,sep=sep,low_memory=False)
                if len(df.columns)>1: return df
            except Exception:
                pass
    return pd.DataFrame()

def save(df: pd.DataFrame,path:Path)->None:
    path.parent.mkdir(parents=True,exist_ok=True); df.to_csv(path,index=False,encoding='utf-8-sig')

def col(df:pd.DataFrame,names:list[str])->str:
    for n in names:
        if n in df.columns: return n
    return ''

def prep(df:pd.DataFrame)->pd.DataFrame:
    x=df.copy(); x.columns=[str(c).strip() for c in x.columns]
    if 'time' not in x.columns: return pd.DataFrame()
    x['time_dt']=pd.to_datetime(x['time'],errors='coerce')
    for c in ['open','high','low','close']:
        if c in x.columns: x[c]=pd.to_numeric(x[c],errors='coerce')
    return x[x.time_dt.notna()].sort_values('time_dt').reset_index(drop=True)

def tr(df:pd.DataFrame)->pd.Series:
    pc=df.close.shift(1)
    return pd.concat([(df.high-df.low).abs(),(df.high-pc).abs(),(df.low-pc).abs()],axis=1).max(axis=1)

def atr_sma(df:pd.DataFrame,p:int)->pd.Series:
    return tr(df).rolling(p,min_periods=p).mean()

def atr_ewm(df:pd.DataFrame,p:int)->pd.Series:
    return tr(df).ewm(alpha=1/p,adjust=False,min_periods=p).mean()

def rsi_sma(close:pd.Series,p:int=14)->pd.Series:
    d=close.diff(); g=d.clip(lower=0); l=-d.clip(upper=0)
    ag=g.rolling(p,min_periods=p).mean(); al=l.rolling(p,min_periods=p).mean(); rs=ag/al.replace(0,math.nan)
    out=100-100/(1+rs)
    return out.where(al.ne(0),100.0)

def asof(entry:pd.Series,src:pd.DataFrame,value:pd.Series,name:str)->pd.Series:
    left=pd.DataFrame({'entry_dt':entry}).reset_index(names='_row_id')
    right=pd.DataFrame({'src_time':src.time_dt,name:value})
    m=pd.merge_asof(left.sort_values('entry_dt'),right.sort_values('src_time'),left_on='entry_dt',right_on='src_time',direction='backward')
    return m.sort_values('_row_id')[name].reset_index(drop=True)

def pf(s)->float:
    x=pd.to_numeric(pd.Series(s),errors='coerce').dropna().astype(float)
    if x.empty: return 0.0
    gp=float(x[x>0].sum()); gl=float(-x[x<0].sum())
    return gp/gl if gl>0 else (math.inf if gp>0 else 0.0)

def metric(df:pd.DataFrame,rc:str)->dict:
    if df.empty:
        return dict(events=0,entry_dt=0,sum=0.0,pf=0.0,wr=0.0,neg_events=0,months=0,neg_months=0,june_events=0,june_sum=0.0,after_events=0,after_sum=0.0,after_pf=0.0,after_wr=0.0)
    r=pd.to_numeric(df[rc],errors='coerce').fillna(0); m=df.groupby('month')[rc].sum(); aft=df[df.entry_dt>=pd.Timestamp(CUTOFF)]; ar=pd.to_numeric(aft[rc],errors='coerce').fillna(0) if not aft.empty else pd.Series(dtype=float)
    return dict(events=int(len(df)),entry_dt=int(df.entry_dt.nunique()),sum=float(r.sum()),pf=pf(r),wr=float((r>0).mean()),neg_events=int((r<0).sum()),months=int(len(m)),neg_months=int((m<0).sum()),june_events=int((df.month=='2026-06').sum()),june_sum=float(m.get('2026-06',0.0)),after_events=int(len(aft)),after_sum=float(ar.sum()) if not ar.empty else 0.0,after_pf=pf(ar),after_wr=float((ar>0).mean()) if not ar.empty else 0.0)

def score_cols(df:pd.DataFrame)->list[str]:
    return [c for c in ['feature_score','score','ledger_score','score_threshold'] if c in df.columns]

def one_entry(df:pd.DataFrame)->pd.DataFrame:
    if df.empty: return df.copy()
    x=df.copy(); sc=score_cols(x)
    for c in sc: x[c]=pd.to_numeric(x[c],errors='coerce')
    if sc:
        return x.sort_values(['entry_dt']+sc,ascending=[True]+[False]*len(sc),kind='mergesort').groupby('entry_dt',as_index=False).head(1)
    return x.sort_values('entry_dt',kind='mergesort').groupby('entry_dt',as_index=False).head(1)

def sides(g:pd.DataFrame)->set[str]:
    if 'side' not in g.columns: return set()
    return {str(x) for x in g.side.dropna().unique() if str(x)!='nan'}

def skip_mixed(df:pd.DataFrame)->tuple[pd.DataFrame,int]:
    if df.empty: return df.copy(),0
    keep=[]; mixed=0
    for _,g in df.groupby('entry_dt',sort=True):
        if len(sides(g))>1:
            mixed+=1; continue
        keep.append(g)
    return (pd.concat(keep,ignore_index=True) if keep else pd.DataFrame(columns=df.columns)),mixed

def make_candidates(x:pd.DataFrame,mode:str)->pd.DataFrame:
    base=~x.policy_norm.eq(CUR)
    def n(c): return pd.to_numeric(x[c],errors='coerce') if c in x.columns else pd.Series(float('nan'),index=x.index)
    if mode=='original':
        d1=n('d1_dist_atr'); h1r=n('h1_range_atr'); rsi=n('m15_rsi14'); h1up=x.h1_up.astype(str).str.lower().isin(['true','1','yes','y']) if 'h1_up' in x.columns else pd.Series(False,index=x.index)
    else:
        d1=n('d1_dist_atr_rec'); h1r=n('h1_range_atr_rec'); rsi=n('m15_rsi14_rec'); h1up=x.h1_up_rec.astype(str).str.lower().isin(['true','1','yes','y'])
    specs=[('P1_D1',base&(d1<=-1.641755654337)),('P2_DEN',x.policy_norm.eq(P2POL)&(d1<=-0.781481)),('P3_RSI',base&(rsi>=73.861004)),('P4_H1_D1_STRICT',base&(h1r<=0.737217834712)&(d1<=-0.781481)),('P5_H1UP_CUR',base&h1up&(d1<=1.247038)&(h1r<=0.744978))]
    frames=[]
    for lab,mask in specs:
        z=one_entry(x[mask].copy())
        if z.empty: continue
        z.insert(0,'candidate',lab); z.insert(0,'mode',mode); frames.append(z)
    return pd.concat(frames,ignore_index=True) if frames else pd.DataFrame(columns=list(x.columns)+['mode','candidate'])

def diff_summary(x:pd.DataFrame)->pd.DataFrame:
    rows=[]
    for a,b in [('m15_rsi14','m15_rsi14_rec'),('h1_range_atr','h1_range_atr_rec'),('d1_dist_atr','d1_dist_atr_rec')]:
        if a in x.columns and b in x.columns:
            aa=pd.to_numeric(x[a],errors='coerce'); bb=pd.to_numeric(x[b],errors='coerce'); d=(aa-bb).abs().dropna()
            rows.append({'feature':a,'rows':int(len(d)),'mae':float(d.mean()) if len(d) else math.nan,'median_abs':float(d.median()) if len(d) else math.nan,'p95_abs':float(d.quantile(0.95)) if len(d) else math.nan,'max_abs':float(d.max()) if len(d) else math.nan,'corr':float(aa.corr(bb)) if d.notna().sum()>3 else math.nan})
    if 'h1_up' in x.columns:
        oh=x.h1_up.astype(str).str.lower().isin(['true','1','yes','y']); rh=x.h1_up_rec.astype(str).str.lower().isin(['true','1','yes','y']); dd=(oh!=rh).astype(int)
        rows.append({'feature':'h1_up','rows':int(len(dd)),'mae':float(dd.mean()),'median_abs':float(dd.median()),'p95_abs':float(dd.quantile(0.95)),'max_abs':float(dd.max()),'corr':float(oh.astype(int).corr(rh.astype(int)))})
    return pd.DataFrame(rows)

def main()->int:
    t0=time.time(); ap=argparse.ArgumentParser(); ap.add_argument('--mt5-files-dir',default=''); args=ap.parse_args()
    mt5=gy.mt5_files_dir(args.mt5_files_dir); root=mt5/'FX_OUTPUTS'/'gold_v3'; out=root/'176c'; out.mkdir(parents=True,exist_ok=True)
    raw=read_csv_any(root/'107k2c'/'gold_v3_107k2_all_regime_ledgers.csv'); m15=prep(read_csv_any(mt5/'goldsharp_m15.csv')); h1=prep(read_csv_any(mt5/'goldsharp_h1.csv')); d1=prep(read_csv_any(mt5/'goldsharp_d1.csv'))
    blockers=[]; warnings=[]
    pc=col(raw,['policy_key','k2_policy_key','rule_key','policy']) if not raw.empty else ''; rc=col(raw,['result_usd','worst_result_usd','pnl_usd','profit_usd','rep_result_usd']) if not raw.empty else ''
    if raw.empty: blockers.append({'id':'missing_107k2_ledger'})
    if m15.empty: blockers.append({'id':'missing_m15_csv'})
    if h1.empty: blockers.append({'id':'missing_h1_csv'})
    if d1.empty: blockers.append({'id':'missing_d1_csv'})
    if not pc: blockers.append({'id':'missing_policy_column'})
    if not rc: blockers.append({'id':'missing_result_column'})
    missing=[c for c in ['entry_dt','m15_rsi14','h1_range_atr','d1_dist_atr','h1_up'] if not raw.empty and c not in raw.columns]
    if missing: blockers.append({'id':'missing_original_feature_columns','missing':missing})
    diff=pd.DataFrame(); metrics=pd.DataFrame(); overlap=pd.DataFrame()
    if not blockers:
        x=raw.copy(); x['entry_dt']=pd.to_datetime(x.entry_dt,errors='coerce'); x=x[x.entry_dt.notna()].sort_values('entry_dt').reset_index(drop=True)
        x['policy_norm']=x[pc].astype(str); x[rc]=pd.to_numeric(x[rc],errors='coerce').fillna(0); x['month']=x.entry_dt.dt.to_period('M').astype(str)
        entry=x.entry_dt
        # Recovered formulas from 176B best live-safe hits.
        x['m15_rsi14_rec']=asof(entry,m15,rsi_sma(m15.close,14),'m15_rsi14_rec')
        h1_ema20=h1.close.ewm(span=20,adjust=False,min_periods=20).mean(); h1_ema50=h1.close.ewm(span=50,adjust=False,min_periods=50).mean()
        x['h1_up_rec']=asof(entry,h1,(h1_ema20>h1_ema50),'h1_up_rec')
        x['h1_range_atr_rec']=asof(entry,h1,(h1.high-h1.low)/atr_ewm(h1,14),'h1_range_atr_rec')
        m15_close=asof(entry,m15,m15.close,'m15_close_for_d1')
        d1_low=asof(entry,d1,d1.low.shift(2),'d1_low_shift2')
        d1_atr=asof(entry,d1,atr_sma(d1,50).shift(2),'d1_atr_sma50_shift2')
        x['d1_dist_atr_rec']=(pd.to_numeric(m15_close,errors='coerce')-pd.to_numeric(d1_low,errors='coerce'))/pd.to_numeric(d1_atr,errors='coerce')
        save(x[['entry_dt','m15_rsi14','m15_rsi14_rec','h1_range_atr','h1_range_atr_rec','d1_dist_atr','d1_dist_atr_rec','h1_up','h1_up_rec']],out/'gold_v3_176c_feature_recovery_rows.csv')
        diff=diff_summary(x); save(diff,out/'gold_v3_176c_feature_diff_summary.csv')
        orig=make_candidates(x,'original'); rec=make_candidates(x,'recovered')
        orig_skip,om=skip_mixed(orig); rec_skip,rm=skip_mixed(rec)
        save(orig_skip,out/'gold_v3_176c_original_orders.csv'); save(rec_skip,out/'gold_v3_176c_recovered_orders.csv')
        rows=[]
        for mode,df,mixed in [('original',orig_skip,om),('recovered',rec_skip,rm)]:
            rows.append({'mode':mode,'candidate':'LATER_UNION_INTERNAL_MIXED_SKIPPED','mixed_skipped_entry_dt':mixed,**metric(df,rc)})
            for cand,g in df.groupby('candidate',sort=True): rows.append({'mode':mode,'candidate':cand,'mixed_skipped_entry_dt':0,**metric(g,rc)})
        metrics=pd.DataFrame(rows); save(metrics,out/'gold_v3_176c_candidate_metric_compare.csv')
        ows=[]
        for cand in ['P1_D1','P2_DEN','P3_RSI','P4_H1_D1_STRICT','P5_H1UP_CUR']:
            od=set(orig_skip[orig_skip.candidate.eq(cand)].entry_dt.astype(str)) if not orig_skip.empty else set(); rd=set(rec_skip[rec_skip.candidate.eq(cand)].entry_dt.astype(str)) if not rec_skip.empty else set()
            ows.append({'candidate':cand,'original_entry_dt':len(od),'recovered_entry_dt':len(rd),'overlap_entry_dt':len(od&rd),'only_original':len(od-rd),'only_recovered':len(rd-od),'jaccard':(len(od&rd)/len(od|rd)) if od|rd else 1.0})
        overlap=pd.DataFrame(ows); save(overlap,out/'gold_v3_176c_entrydt_overlap.csv')
    ready=len(blockers)==0
    review=True
    if ready and not overlap.empty:
        review=bool(overlap[['only_original','only_recovered']].sum().sum()>0)
    status='READY' if ready else 'BLOCKED'; decision='RECOVERED_FEATURE_REPLAY_READY' if ready else 'RECOVERED_FEATURE_REPLAY_BLOCKED'
    summary={'step':STEP,'status':status,'ready':ready,'decision':decision,'created_at_utc':datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z'),'output_dir':str(out),'audit_only':True,'review_only':True,'recovered_formula_set':'m15_rsi_sma14_shift0__h1_up_ema20_gt_ema50_shift0__h1_range_atr_ewm14_shift0__d1_low_atr_sma50_shift2','review_required_before_payload':review,'feature_diff_rows':int(len(diff)),'candidate_metric_rows':int(len(metrics)),'overlap_rows':int(len(overlap)),'source_csv_mutated':False,'contract_mutated':False,'open_asof_allowed':False,'candidate_pool_removed':False,'f002_exclusion_bypassed':False,'final_live_enabled':False,'blocker_count':len(blockers),'warning_count':len(warnings),'elapsed_seconds':round(time.time()-t0,2)}
    (out/'gold_v3_176c_summary.json').write_text(json.dumps({**summary,'blockers':blockers,'warnings':warnings},ensure_ascii=False,indent=2),encoding='utf-8'); save(pd.DataFrame([summary]),out/'gold_v3_176c_decision.csv')
    lines=['GOLD V3 176C PASTE_ME_RECOVERED_FEATURE_CANDIDATE_REPLAY_AUDIT']+[f'{k}: {v}' for k,v in summary.items()]
    lines+=['','FEATURE_DIFF_SUMMARY',diff.to_string(index=False) if not diff.empty else 'NO_FEATURE_DIFF']
    lines+=['','CANDIDATE_METRIC_COMPARE',metrics.to_string(index=False) if not metrics.empty else 'NO_CANDIDATE_METRICS']
    lines+=['','ENTRYDT_OVERLAP',overlap.to_string(index=False) if not overlap.empty else 'NO_OVERLAP']
    lines+=['','INTERPRETATION','Replays P1-P5 using the best live-safe recovered formula set from 176B. If recovered metrics/overlap do not return close to original, old ledger PF remains non-live-reproducible and OHLC-only redesign is required.']
    lines+=['','BLOCKERS','NO_BLOCKERS' if not blockers else json.dumps(blockers,ensure_ascii=False,indent=2),'','WARNINGS','NO_WARNINGS' if not warnings else json.dumps(warnings,ensure_ascii=False,indent=2)]
    (out/'paste_me.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({'ready':ready,'decision':decision,'paste_me':str(out/'paste_me.txt')},ensure_ascii=False)); return 0 if ready else 2
if __name__=='__main__': raise SystemExit(main())
