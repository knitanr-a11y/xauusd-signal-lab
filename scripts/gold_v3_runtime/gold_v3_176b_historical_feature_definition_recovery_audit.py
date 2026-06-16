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

STEP = 'GOLD_V3_176B_HISTORICAL_FEATURE_DEFINITION_RECOVERY_AUDIT_ONLY'
PERIODS = [14, 50, 56]
SHIFTS = [-2, -1, 0, 1, 2]


def read_csv_any(path: Path) -> pd.DataFrame:
    if not path.exists(): return pd.DataFrame()
    for enc in ['utf-8-sig','utf-8','cp932']:
        for sep in [',',';','\t']:
            try:
                df = pd.read_csv(path, encoding=enc, sep=sep, low_memory=False)
                if len(df.columns) > 1: return df
            except Exception:
                pass
    return pd.DataFrame()

def save(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding='utf-8-sig')

def prep(df: pd.DataFrame) -> pd.DataFrame:
    x = df.copy(); x.columns = [str(c).strip() for c in x.columns]
    if 'time' not in x.columns: return pd.DataFrame()
    x['time_dt'] = pd.to_datetime(x['time'], errors='coerce')
    for c in ['open','high','low','close']:
        if c in x.columns: x[c] = pd.to_numeric(x[c], errors='coerce')
    return x[x.time_dt.notna()].sort_values('time_dt').reset_index(drop=True)

def tr(df: pd.DataFrame) -> pd.Series:
    pc = df['close'].shift(1)
    return pd.concat([(df.high-df.low).abs(), (df.high-pc).abs(), (df.low-pc).abs()], axis=1).max(axis=1)

def atr_sma(df: pd.DataFrame, p: int) -> pd.Series:
    return tr(df).rolling(p, min_periods=p).mean()

def atr_ewm(df: pd.DataFrame, p: int, adjust: bool=False) -> pd.Series:
    return tr(df).ewm(alpha=1/p, adjust=adjust, min_periods=p).mean()

def rma(s: pd.Series, p: int, adjust: bool=False) -> pd.Series:
    return s.ewm(alpha=1/p, adjust=adjust, min_periods=p).mean()

def rsi_ewm(close: pd.Series, p: int=14, adjust: bool=False) -> pd.Series:
    d=close.diff(); g=d.clip(lower=0); l=-d.clip(upper=0)
    ag=rma(g,p,adjust); al=rma(l,p,adjust); rs=ag/al.replace(0, math.nan)
    out=100-100/(1+rs)
    return out.where(al.ne(0),100.0)

def rsi_sma(close: pd.Series, p: int=14) -> pd.Series:
    d=close.diff(); g=d.clip(lower=0); l=-d.clip(upper=0)
    ag=g.rolling(p,min_periods=p).mean(); al=l.rolling(p,min_periods=p).mean(); rs=ag/al.replace(0, math.nan)
    out=100-100/(1+rs)
    return out.where(al.ne(0),100.0)

def add_shifted(base: pd.DataFrame, cols: dict[str,pd.Series], time_col: str='time_dt') -> pd.DataFrame:
    out = base[[time_col]].copy()
    for name, ser in cols.items():
        for sh in SHIFTS:
            out[f'{name}__shift{sh}'] = ser.shift(sh)
    return out

def corr(a: pd.Series, b: pd.Series) -> float:
    aa=pd.to_numeric(a,errors='coerce'); bb=pd.to_numeric(b,errors='coerce')
    ok=aa.notna() & bb.notna()
    if ok.sum() < 3: return math.nan
    return float(aa[ok].corr(bb[ok]))

def numeric_metrics(x: pd.DataFrame, orig: str, cand: str) -> dict:
    a=pd.to_numeric(x[orig],errors='coerce'); b=pd.to_numeric(x[cand],errors='coerce')
    d=(a-b).abs(); ok=d.notna()
    if ok.sum()==0:
        return {'rows':0,'mae':math.nan,'median_abs':math.nan,'p95_abs':math.nan,'max_abs':math.nan,'rmse':math.nan,'corr':math.nan}
    dd=d[ok]; diff=(a[ok]-b[ok])
    return {'rows':int(ok.sum()),'mae':float(dd.mean()),'median_abs':float(dd.median()),'p95_abs':float(dd.quantile(0.95)),'max_abs':float(dd.max()),'rmse':float(math.sqrt(float((diff*diff).mean()))),'corr':corr(a,b)}

def bool_series(s: pd.Series) -> pd.Series:
    return s.astype(str).str.lower().isin(['true','1','yes','y'])

def bool_metrics(x: pd.DataFrame, orig: str, cand: str) -> dict:
    a=bool_series(x[orig]); b=bool_series(x[cand])
    ok=x[orig].notna() & x[cand].notna()
    if ok.sum()==0: return {'rows':0,'agreement':math.nan,'mismatch_rate':math.nan,'true_overlap':0,'orig_true':0,'cand_true':0}
    aa=a[ok]; bb=b[ok]
    return {'rows':int(ok.sum()),'agreement':float((aa==bb).mean()),'mismatch_rate':float((aa!=bb).mean()),'true_overlap':int((aa & bb).sum()),'orig_true':int(aa.sum()),'cand_true':int(bb.sum())}

def parse_variant(name: str) -> dict:
    parts=name.split('__shift')
    base=parts[0]; sh=int(parts[1]) if len(parts)>1 else 0
    return {'variant':base,'shift':sh,'live_safe': bool(sh >= 0)}

def main() -> int:
    t0=time.time(); ap=argparse.ArgumentParser(); ap.add_argument('--mt5-files-dir',default=''); args=ap.parse_args()
    mt5=gy.mt5_files_dir(args.mt5_files_dir); root=mt5/'FX_OUTPUTS'/'gold_v3'; out=root/'176b'; out.mkdir(parents=True,exist_ok=True)
    ledger=read_csv_any(root/'107k2c'/'gold_v3_107k2_all_regime_ledgers.csv')
    m15=prep(read_csv_any(mt5/'goldsharp_m15.csv')); h1=prep(read_csv_any(mt5/'goldsharp_h1.csv')); d1=prep(read_csv_any(mt5/'goldsharp_d1.csv'))
    blockers=[]; warnings=[]
    if ledger.empty: blockers.append({'id':'missing_107k2_ledger'})
    if m15.empty: blockers.append({'id':'missing_m15_csv'})
    if h1.empty: blockers.append({'id':'missing_h1_csv'})
    if d1.empty: blockers.append({'id':'missing_d1_csv'})
    required=[c for c in ['entry_dt','m15_rsi14','h1_range_atr','d1_dist_atr','h1_up'] if c not in ledger.columns]
    if required: blockers.append({'id':'missing_original_feature_columns','missing':required})
    num_rows=[]; bool_rows=[]
    best_num=pd.DataFrame(); best_bool=pd.DataFrame()
    if not blockers:
        x=ledger.copy(); x['entry_dt']=pd.to_datetime(x.entry_dt, errors='coerce'); x=x[x.entry_dt.notna()].sort_values('entry_dt').reset_index(drop=True)
        # M15 RSI variants
        m15_cols={'m15_rsi_ewm14_adjustFalse':rsi_ewm(m15.close,14,False),'m15_rsi_ewm14_adjustTrue':rsi_ewm(m15.close,14,True),'m15_rsi_sma14':rsi_sma(m15.close,14)}
        m15v=add_shifted(m15,m15_cols).rename(columns={'time_dt':'m15_time'})
        x=pd.merge_asof(x.sort_values('entry_dt'),m15v.sort_values('m15_time'),left_on='entry_dt',right_on='m15_time',direction='backward')
        # H1 range/ATR and trend variants
        h1_cols={}
        h1_range=(h1.high-h1.low)
        for p in PERIODS:
            for method,ser in [('sma',atr_sma(h1,p)),('ewmA0',atr_ewm(h1,p,False)),('ewmA1',atr_ewm(h1,p,True))]:
                h1_cols[f'h1_range_atr_{method}{p}']=h1_range/ser
        ema20=h1.close.ewm(span=20,adjust=False,min_periods=20).mean(); ema50=h1.close.ewm(span=50,adjust=False,min_periods=50).mean(); sma20=h1.close.rolling(20,min_periods=20).mean()
        h1_cols.update({'h1_up_close_gt_prev':h1.close>h1.close.shift(1),'h1_up_close_gt_open':h1.close>h1.open,'h1_up_ema20_gt_ema50':ema20>ema50,'h1_up_close_gt_sma20':h1.close>sma20,'h1_up_close_delta3_gt0':(h1.close-h1.close.shift(3))>0})
        h1v=add_shifted(h1,h1_cols).rename(columns={'time_dt':'h1_time'})
        x=pd.merge_asof(x.sort_values('entry_dt'),h1v.sort_values('h1_time'),left_on='entry_dt',right_on='h1_time',direction='backward')
        # D1 distance variants: m15 close against D1 ref divided by ATR variants
        mclose=m15[['time_dt','close']].rename(columns={'time_dt':'entry_dt','close':'m15_close_for_d1'})
        xd=pd.merge_asof(x[['entry_dt']].sort_values('entry_dt'),mclose.sort_values('entry_dt'),on='entry_dt',direction='backward')
        x=x.merge(xd,on='entry_dt',how='left')
        d1_cols={}
        refs={'close':d1.close,'open':d1.open,'high':d1.high,'low':d1.low,'hl2':(d1.high+d1.low)/2,'ohlc4':(d1.open+d1.high+d1.low+d1.close)/4}
        atrs={}
        for p in PERIODS:
            atrs[f'sma{p}']=atr_sma(d1,p); atrs[f'ewmA0_{p}']=atr_ewm(d1,p,False); atrs[f'ewmA1_{p}']=atr_ewm(d1,p,True)
        for refn,ref in refs.items():
            for atrn,aser in atrs.items():
                d1_cols[f'd1_ref_{refn}_atr_{atrn}__ref'] = ref
                d1_cols[f'd1_ref_{refn}_atr_{atrn}__atr'] = aser
        d1tmp=d1[['time_dt']].copy()
        for k,v in d1_cols.items(): d1tmp[k]=v
        d1_shifted=add_shifted(d1tmp, {k:d1tmp[k] for k in d1tmp.columns if k!='time_dt'}).rename(columns={'time_dt':'d1_time'})
        x=pd.merge_asof(x.sort_values('entry_dt'),d1_shifted.sort_values('d1_time'),left_on='entry_dt',right_on='d1_time',direction='backward')
        # materialize d1 distance candidates from paired shifted ref/atr columns
        d1_dist_cols=[]
        for c in list(x.columns):
            if not c.startswith('d1_ref_') or '__ref__shift' not in c: continue
            ac=c.replace('__ref__shift','__atr__shift')
            if ac in x.columns:
                outc=c.replace('__ref__shift','__dist__shift')
                x[outc]=(pd.to_numeric(x['m15_close_for_d1'],errors='coerce')-pd.to_numeric(x[c],errors='coerce'))/pd.to_numeric(x[ac],errors='coerce')
                d1_dist_cols.append(outc)
        # numeric ranking
        feature_map={'m15_rsi14':[c for c in x.columns if c.startswith('m15_rsi_')], 'h1_range_atr':[c for c in x.columns if c.startswith('h1_range_atr_')], 'd1_dist_atr':d1_dist_cols}
        for orig,cands in feature_map.items():
            for cand in cands:
                pv=parse_variant(cand); met=numeric_metrics(x,orig,cand)
                num_rows.append({'feature':orig,'candidate_col':cand,**pv,**met})
        # bool ranking for h1_up
        for cand in [c for c in x.columns if c.startswith('h1_up_')]:
            pv=parse_variant(cand); met=bool_metrics(x,'h1_up',cand)
            bool_rows.append({'feature':'h1_up','candidate_col':cand,**pv,**met})
        num=pd.DataFrame(num_rows); boo=pd.DataFrame(bool_rows)
        if not num.empty:
            num=num.sort_values(['feature','mae','p95_abs','rmse'], ascending=[True,True,True,True])
            save(num,out/'gold_v3_176b_numeric_formula_ranking.csv')
            best_num=num.groupby('feature',as_index=False).head(10); save(best_num,out/'gold_v3_176b_best_numeric_formulas.csv')
        if not boo.empty:
            boo=boo.sort_values(['mismatch_rate','feature','candidate_col'], ascending=[True,True,True])
            save(boo,out/'gold_v3_176b_bool_formula_ranking.csv')
            best_bool=boo.groupby('feature',as_index=False).head(10); save(best_bool,out/'gold_v3_176b_best_bool_formulas.csv')
    ready=len(blockers)==0
    status='READY' if ready else 'BLOCKED'; decision='HISTORICAL_FEATURE_DEFINITION_RECOVERY_READY' if ready else 'HISTORICAL_FEATURE_DEFINITION_RECOVERY_BLOCKED'
    summary={'step':STEP,'status':status,'ready':ready,'decision':decision,'created_at_utc':datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z'),'output_dir':str(out),'audit_only':True,'review_only':True,'numeric_candidates':int(len(num_rows)),'bool_candidates':int(len(bool_rows)),'best_numeric_rows':int(len(best_num)) if not best_num.empty else 0,'best_bool_rows':int(len(best_bool)) if not best_bool.empty else 0,'source_csv_mutated':False,'contract_mutated':False,'open_asof_allowed':False,'candidate_pool_removed':False,'f002_exclusion_bypassed':False,'final_live_enabled':False,'blocker_count':len(blockers),'warning_count':len(warnings),'elapsed_seconds':round(time.time()-t0,2)}
    (out/'gold_v3_176b_summary.json').write_text(json.dumps({**summary,'blockers':blockers,'warnings':warnings},ensure_ascii=False,indent=2),encoding='utf-8'); save(pd.DataFrame([summary]),out/'gold_v3_176b_decision.csv')
    lines=['GOLD V3 176B PASTE_ME_HISTORICAL_FEATURE_DEFINITION_RECOVERY_AUDIT']+[f'{k}: {v}' for k,v in summary.items()]
    lines+=['','BEST_NUMERIC_FORMULAS',best_num.to_string(index=False) if not best_num.empty else 'NO_BEST_NUMERIC']
    lines+=['','BEST_BOOL_FORMULAS',best_bool.to_string(index=False) if not best_bool.empty else 'NO_BEST_BOOL']
    lines+=['','INTERPRETATION','Ranks OHLC-derived formula/shift candidates against original 107k2 feature columns. Negative shifts are diagnostic only and are not live-safe. Prefer low MAE/P95 for numeric features and low mismatch_rate for h1_up, with live_safe=True.']
    lines+=['','BLOCKERS','NO_BLOCKERS' if not blockers else json.dumps(blockers,ensure_ascii=False,indent=2),'','WARNINGS','NO_WARNINGS' if not warnings else json.dumps(warnings,ensure_ascii=False,indent=2)]
    (out/'paste_me.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({'ready':ready,'decision':decision,'paste_me':str(out/'paste_me.txt')},ensure_ascii=False)); return 0 if ready else 2
if __name__=='__main__': raise SystemExit(main())
