#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse, json, math, time
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
import gold_v3_107gy_light_non_calendar_subfilter_search_audit as gy
import gold_v3_176b_historical_feature_definition_recovery_audit as rec

STEP='GOLD_V3_176D_CURRENT_AND_FORMULA_REPRODUCTION_AUDIT_ONLY'
CUR='density_safe||100||Q0.6'
P2POL='density_safe||100||Q0.35'
PERIODS=[5,7,10,14,20,28,50,56,100]
SHIFTS=[-3,-2,-1,0,1,2,3]
SAMPLE_N=80000
TOP_FULL=120


def progress(msg:str)->None:
    print(f'[176D progress] {msg}', flush=True)

def read_csv_any(path:Path)->pd.DataFrame:
    return rec.read_csv_any(path)

def save(df:pd.DataFrame,path:Path)->None:
    path.parent.mkdir(parents=True,exist_ok=True); df.to_csv(path,index=False,encoding='utf-8-sig')

def prep(df:pd.DataFrame)->pd.DataFrame:
    return rec.prep(df)

def col(df:pd.DataFrame,names:list[str])->str:
    for n in names:
        if n in df.columns: return n
    return ''

def metric_abs(orig,cand)->dict:
    a=pd.to_numeric(orig,errors='coerce'); b=pd.to_numeric(cand,errors='coerce')
    d=(a-b).abs(); ok=d.notna()
    if ok.sum()==0: return dict(rows=0,mae=math.nan,median_abs=math.nan,p95_abs=math.nan,max_abs=math.nan,corr=math.nan,exact=False)
    aa=a[ok]; bb=b[ok]; dd=d[ok]
    return dict(rows=int(ok.sum()),mae=float(dd.mean()),median_abs=float(dd.median()),p95_abs=float(dd.quantile(.95)),max_abs=float(dd.max()),corr=float(aa.corr(bb)) if ok.sum()>3 else math.nan,exact=bool(float(dd.max())<1e-9))

def bool_metric(orig,cand)->dict:
    a=orig.astype(str).str.lower().isin(['true','1','yes','y']); b=cand.astype(str).str.lower().isin(['true','1','yes','y'])
    ok=orig.notna() & cand.notna(); mm=(a[ok]!=b[ok]).astype(int)
    return dict(rows=int(ok.sum()),mismatch_rate=float(mm.mean()) if len(mm) else math.nan,agreement=float(1-mm.mean()) if len(mm) else math.nan,exact=bool(len(mm) and int(mm.sum())==0))

def asof(entry:pd.Series,src:pd.DataFrame,value:pd.Series,name:str)->pd.Series:
    left=pd.DataFrame({'entry_dt':entry}).reset_index(names='_row_id')
    right=pd.DataFrame({'src_time':src.time_dt,name:value})
    m=pd.merge_asof(left.sort_values('entry_dt'),right.sort_values('src_time'),left_on='entry_dt',right_on='src_time',direction='backward')
    return m.sort_values('_row_id')[name].reset_index(drop=True)

def atrs(df:pd.DataFrame,prefix:str)->dict[str,pd.Series]:
    out={}
    for p in PERIODS:
        out[f'{prefix}_atr_sma{p}']=rec.atr_sma(df,p)
        out[f'{prefix}_atr_ewmA0_{p}']=rec.atr_ewm(df,p,False)
        out[f'{prefix}_atr_ewmA1_{p}']=rec.atr_ewm(df,p,True)
    return out

def price_refs(df:pd.DataFrame,prefix:str)->dict[str,pd.Series]:
    return {f'{prefix}_open':df.open,f'{prefix}_high':df.high,f'{prefix}_low':df.low,f'{prefix}_close':df.close,f'{prefix}_hl2':(df.high+df.low)/2,f'{prefix}_ohlc4':(df.open+df.high+df.low+df.close)/4}

def main()->int:
    t0=time.time(); ap=argparse.ArgumentParser(); ap.add_argument('--mt5-files-dir',default=''); args=ap.parse_args()
    mt5=gy.mt5_files_dir(args.mt5_files_dir); root=mt5/'FX_OUTPUTS'/'gold_v3'; out=root/'176d'; out.mkdir(parents=True,exist_ok=True)
    progress('load ledger and OHLC CSVs')
    raw=read_csv_any(root/'107k2c'/'gold_v3_107k2_all_regime_ledgers.csv'); m15=prep(read_csv_any(mt5/'goldsharp_m15.csv')); h1=prep(read_csv_any(mt5/'goldsharp_h1.csv')); d1=prep(read_csv_any(mt5/'goldsharp_d1.csv'))
    blockers=[]; warnings=[]
    if raw.empty: blockers.append({'id':'missing_107k2_ledger'})
    if m15.empty: blockers.append({'id':'missing_m15_csv'})
    if h1.empty: blockers.append({'id':'missing_h1_csv'})
    if d1.empty: blockers.append({'id':'missing_d1_csv'})
    pc=col(raw,['policy_key','k2_policy_key','rule_key','policy']) if not raw.empty else ''
    rc=col(raw,['result_usd','worst_result_usd','pnl_usd','profit_usd','rep_result_usd']) if not raw.empty else ''
    if not pc: blockers.append({'id':'missing_policy_column'})
    missing=[c for c in ['entry_dt','m15_rsi14','h1_range_atr','d1_dist_atr','h1_up'] if not raw.empty and c not in raw.columns]
    if missing: blockers.append({'id':'missing_original_feature_columns','missing':missing})
    d1_rank=pd.DataFrame(); h1_rank=pd.DataFrame(); exact_rows=[]; current_inv=[]; reused_sample=False
    if not blockers:
        progress('prepare ledger and sample index')
        x=raw.copy(); x['entry_dt']=pd.to_datetime(x.entry_dt,errors='coerce'); x=x[x.entry_dt.notna()].sort_values('entry_dt').reset_index(drop=True); x['policy_norm']=x[pc].astype(str)
        entry=x.entry_dt
        idx=x.index
        if len(x)>SAMPLE_N:
            step=max(1,len(x)//SAMPLE_N); idx=x.index[::step]
        xs=x.loc[idx].reset_index(drop=True); es=xs.entry_dt
        progress(f'sample rows={len(xs)} full rows={len(x)}')
        # exact already-known checks
        progress('check exact recovered formulas: m15_rsi14 and h1_up')
        m15_rsi=asof(es,m15,rec.rsi_sma(m15.close,14),'m15_rsi')
        h1_ema20=h1.close.ewm(span=20,adjust=False,min_periods=20).mean(); h1_ema50=h1.close.ewm(span=50,adjust=False,min_periods=50).mean()
        h1up=asof(es,h1,(h1_ema20>h1_ema50),'h1_up')
        exact_rows.append({'feature':'m15_rsi14','candidate':'m15_rsi_sma14_shift0',**metric_abs(xs.m15_rsi14,m15_rsi)})
        exact_rows.append({'feature':'h1_up','candidate':'h1_ema20_gt_ema50_shift0',**bool_metric(xs.h1_up,h1up)})
        # H1 exhaustive range
        progress('scan h1_range_atr formulas')
        h1_nums={'h1_high_low':h1.high-h1.low,'h1_true_range':rec.tr(h1),'h1_body_abs':(h1.close-h1.open).abs(),'h1_close_open':h1.close-h1.open}
        h1_dens={**atrs(h1,'h1'), **{f'd1_{k}':v for k,v in atrs(d1,'d1').items()}}
        rows=[]
        for nn,nser in h1_nums.items():
            for dn,dser in h1_dens.items():
                src = h1 if dn.startswith('h1_') else d1
                for sh in SHIFTS:
                    num=asof(es,h1,nser.shift(sh),nn); den=asof(es,src,dser.shift(sh),dn)
                    cand=pd.to_numeric(num,errors='coerce')/pd.to_numeric(den,errors='coerce')
                    cname=f'{nn}_over_{dn}_shift{sh}'
                    rows.append({'feature':'h1_range_atr','candidate_col':cname,'shift':sh,'live_safe':sh>=0,**metric_abs(xs.h1_range_atr,cand)})
        h1_rank=pd.DataFrame(rows).sort_values(['mae','p95_abs','max_abs']).head(80); save(h1_rank,out/'gold_v3_176d_h1_range_exhaustive_top80.csv')
        # D1 dist exhaustive sample can be reused if previous failed after sample top120 was written.
        progress('prepare d1_dist_atr formula dictionaries')
        src_prices={**price_refs(m15,'m15'), **price_refs(h1,'h1')}
        ref_prices={**price_refs(d1,'d1')}
        for p in [5,10,20,50,100,200]:
            ref_prices[f'd1_sma{p}']=d1.close.rolling(p,min_periods=p).mean()
            ref_prices[f'd1_ema{p}']=d1.close.ewm(span=p,adjust=False,min_periods=p).mean()
        denoms={**atrs(d1,'d1'), **{f'h1_{k}':v for k,v in atrs(h1,'h1').items()}, 'd1_range':(d1.high-d1.low).replace(0,math.nan)}
        sample_path=out/'gold_v3_176d_d1_dist_sample_top120.csv'
        if sample_path.exists():
            progress('reuse existing d1_dist sample top120 from previous run')
            samp=read_csv_any(sample_path)
            needed={'src','ref','denom','shift','candidate_col'}
            if not needed.issubset(set(samp.columns)):
                warnings.append({'id':'sample_top120_invalid_rebuilding'})
                samp=pd.DataFrame()
            else:
                reused_sample=True
        else:
            samp=pd.DataFrame()
        if samp.empty:
            progress('scan d1_dist_atr formulas on sample')
            sample_rows=[]
            for sn,sser in src_prices.items():
                ssrc=m15 if sn.startswith('m15_') else h1
                srcv=asof(es,ssrc,sser,sn)
                for rn,rser in ref_prices.items():
                    for dn,dser in denoms.items():
                        dsrc=h1 if dn.startswith('h1_') else d1
                        for sh in SHIFTS:
                            refv=asof(es,d1,rser.shift(sh),rn); denv=asof(es,dsrc,dser.shift(sh),dn)
                            denv=pd.to_numeric(denv,errors='coerce')
                            cand=(pd.to_numeric(srcv,errors='coerce')-pd.to_numeric(refv,errors='coerce'))/denv
                            cname=f'{sn}_minus_{rn}_over_{dn}_shift{sh}'
                            met=metric_abs(xs.d1_dist_atr,cand)
                            sample_rows.append({'feature':'d1_dist_atr','candidate_col':cname,'src':sn,'ref':rn,'denom':dn,'shift':sh,'live_safe':sh>=0,**met})
            samp=pd.DataFrame(sample_rows).sort_values(['mae','p95_abs','max_abs']).head(TOP_FULL); save(samp,sample_path)
        # full metrics for sample winners only
        progress('full re-evaluate top d1_dist_atr candidates')
        full=[]
        for i,(_,r) in enumerate(samp.iterrows(), start=1):
            sn=str(r['src']); rn=str(r['ref']); dn=str(r['denom']); sh=int(r['shift'])
            if i == 1 or i % 20 == 0:
                progress(f'full d1 candidate {i}/{len(samp)}')
            if sn not in src_prices or rn not in ref_prices or dn not in denoms:
                warnings.append({'id':'skip_candidate_missing_key','candidate_col':str(r.get('candidate_col','')),'src':sn,'ref':rn,'denom':dn})
                continue
            sser=src_prices[sn]; ssrc=m15 if sn.startswith('m15_') else h1
            rser=ref_prices[rn]; dser=denoms[dn]; dsrc=h1 if dn.startswith('h1_') else d1
            srcv=asof(entry,ssrc,sser,sn); refv=asof(entry,d1,rser.shift(sh),rn); denv=asof(entry,dsrc,dser.shift(sh),dn)
            cand=(pd.to_numeric(srcv,errors='coerce')-pd.to_numeric(refv,errors='coerce'))/pd.to_numeric(denv,errors='coerce')
            full.append({'feature':'d1_dist_atr','candidate_col':r['candidate_col'],'src':sn,'ref':rn,'denom':dn,'shift':sh,'live_safe':bool(sh>=0),**metric_abs(x.d1_dist_atr,cand)})
        d1_rank=pd.DataFrame(full).sort_values(['mae','p95_abs','max_abs']); save(d1_rank,out/'gold_v3_176d_d1_dist_full_top120.csv')
        # current policy inventory
        progress('inventory current policy and score columns')
        cur=x[x.policy_norm.eq(CUR)].copy()
        score_cols=[c for c in ['feature_score','score','ledger_score','score_threshold','rank_score','prob','confidence'] if c in x.columns]
        current_inv.append({'policy':CUR,'rows':int(len(cur)),'entry_dt':int(cur.entry_dt.nunique()) if not cur.empty else 0,'score_columns_found':','.join(score_cols),'has_result_column':bool(rc),'note':'This confirms ledger availability only. OHLC reproduction of current score still requires formula/source code for density_safe score.'})
    # decisions
    progress('write outputs')
    exact_df=pd.DataFrame(exact_rows); save(exact_df,out/'gold_v3_176d_exact_recovered_checks.csv')
    cur_df=pd.DataFrame(current_inv); save(cur_df,out/'gold_v3_176d_current_policy_inventory.csv')
    d1_exact=bool((not d1_rank.empty) and float(d1_rank.iloc[0].max_abs)<1e-9)
    h1_exact=bool((not h1_rank.empty) and float(h1_rank.iloc[0].max_abs)<1e-9)
    status='READY' if not blockers else 'BLOCKED'
    decision='EXHAUSTIVE_REPRODUCTION_AUDIT_READY' if not blockers else 'EXHAUSTIVE_REPRODUCTION_AUDIT_BLOCKED'
    summary={'step':STEP,'status':status,'ready':not blockers,'decision':decision,'created_at_utc':datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z'),'output_dir':str(out),'audit_only':True,'review_only':True,'progress_resume_enabled':True,'reused_d1_sample_top120':reused_sample,'sample_rows_used':int(min(len(raw),SAMPLE_N)) if not raw.empty else 0,'h1_range_exact_recovered':h1_exact,'d1_dist_exact_recovered':d1_exact,'d1_best_mae':float(d1_rank.iloc[0].mae) if not d1_rank.empty else math.nan,'d1_best_max_abs':float(d1_rank.iloc[0].max_abs) if not d1_rank.empty else math.nan,'current_policy_inventory_rows':int(len(cur_df)),'current_score_formula_recovered':False,'source_csv_mutated':False,'contract_mutated':False,'open_asof_allowed':False,'candidate_pool_removed':False,'f002_exclusion_bypassed':False,'final_live_enabled':False,'blocker_count':len(blockers),'warning_count':len(warnings),'elapsed_seconds':round(time.time()-t0,2)}
    (out/'gold_v3_176d_summary.json').write_text(json.dumps({**summary,'blockers':blockers,'warnings':warnings},ensure_ascii=False,indent=2),encoding='utf-8'); save(pd.DataFrame([summary]),out/'gold_v3_176d_decision.csv')
    lines=['GOLD V3 176D PASTE_ME_CURRENT_AND_FORMULA_REPRODUCTION_AUDIT']+[f'{k}: {v}' for k,v in summary.items()]
    lines+=['','EXACT_RECOVERED_CHECKS',exact_df.to_string(index=False) if not exact_df.empty else 'NO_EXACT_CHECKS']
    lines+=['','H1_RANGE_TOP20',h1_rank.head(20).to_string(index=False) if not h1_rank.empty else 'NO_H1_RANK']
    lines+=['','D1_DIST_TOP30_FULL',d1_rank.head(30).to_string(index=False) if not d1_rank.empty else 'NO_D1_RANK']
    lines+=['','CURRENT_POLICY_INVENTORY',cur_df.to_string(index=False) if not cur_df.empty else 'NO_CURRENT_INVENTORY']
    lines+=['','INTERPRETATION','This stage separates two claims: (1) entry-available OHLC information exists, and (2) the exact historical feature/score formula is reproduced. If d1_dist_exact_recovered or current_score_formula_recovered is false, old PF cannot be treated as live-reproducible yet.']
    lines+=['','BLOCKERS','NO_BLOCKERS' if not blockers else json.dumps(blockers,ensure_ascii=False,indent=2),'','WARNINGS','NO_WARNINGS' if not warnings else json.dumps(warnings,ensure_ascii=False,indent=2)]
    (out/'paste_me.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    progress('done')
    print(json.dumps({'ready':not blockers,'decision':decision,'paste_me':str(out/'paste_me.txt')},ensure_ascii=False))
    return 0 if not blockers else 2
if __name__=='__main__': raise SystemExit(main())
