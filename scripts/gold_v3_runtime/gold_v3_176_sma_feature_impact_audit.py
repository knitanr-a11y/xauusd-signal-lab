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

STEP = 'GOLD_V3_176_SMA_FEATURE_IMPACT_AUDIT_ONLY'
CUR = 'density_safe||100||Q0.6'
P2POL = 'density_safe||100||Q0.35'
CUTOFF = '2026-06-05 15:15:00'
PERIOD = 14


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

def col(df: pd.DataFrame, names: list[str]) -> str:
    for n in names:
        if n in df.columns: return n
    return ''

def pf(s) -> float:
    x = pd.to_numeric(pd.Series(s), errors='coerce').dropna().astype(float)
    if x.empty: return 0.0
    gp = float(x[x>0].sum()); gl = float(-x[x<0].sum())
    return gp/gl if gl>0 else (math.inf if gp>0 else 0.0)

def metric(df: pd.DataFrame, rc: str) -> dict:
    if df.empty:
        return dict(events=0, entry_dt=0, sum=0.0, pf=0.0, wr=0.0, neg_events=0, months=0, neg_months=0, june_events=0, june_sum=0.0, after_events=0, after_sum=0.0, after_pf=0.0, after_wr=0.0)
    r = pd.to_numeric(df[rc], errors='coerce').fillna(0)
    m = df.groupby('month')[rc].sum()
    cut = pd.Timestamp(CUTOFF)
    aft = df[df.entry_dt >= cut]
    ar = pd.to_numeric(aft[rc], errors='coerce').fillna(0) if not aft.empty else pd.Series(dtype=float)
    return dict(events=int(len(df)), entry_dt=int(df.entry_dt.nunique()), sum=float(r.sum()), pf=pf(r), wr=float((r>0).mean()), neg_events=int((r<0).sum()), months=int(len(m)), neg_months=int((m<0).sum()), june_events=int((df.month=='2026-06').sum()), june_sum=float(m.get('2026-06',0.0)), after_events=int(len(aft)), after_sum=float(ar.sum()) if not ar.empty else 0.0, after_pf=pf(ar), after_wr=float((ar>0).mean()) if not ar.empty else 0.0)

def pref(d: dict, p: str) -> dict:
    return {p+k:v for k,v in d.items()}

def prep_ohlc(df: pd.DataFrame) -> pd.DataFrame:
    x = df.copy(); x.columns = [str(c).strip() for c in x.columns]
    if 'time' not in x.columns: return pd.DataFrame()
    x['time_dt'] = pd.to_datetime(x['time'], errors='coerce')
    for c in ['open','high','low','close']:
        if c in x.columns: x[c] = pd.to_numeric(x[c], errors='coerce')
    return x[x.time_dt.notna()].sort_values('time_dt').reset_index(drop=True)

def tr(df: pd.DataFrame) -> pd.Series:
    pc = df['close'].shift(1)
    return pd.concat([(df.high-df.low).abs(), (df.high-pc).abs(), (df.low-pc).abs()], axis=1).max(axis=1)

def atr_sma(df: pd.DataFrame) -> pd.Series:
    return tr(df).rolling(PERIOD, min_periods=PERIOD).mean()

def rma(s: pd.Series, p: int) -> pd.Series:
    return s.ewm(alpha=1/p, adjust=False, min_periods=p).mean()

def rsi(close: pd.Series) -> pd.Series:
    d = close.diff(); g = d.clip(lower=0); l = -d.clip(upper=0)
    ag = rma(g, PERIOD); al = rma(l, PERIOD); rs = ag / al.replace(0, math.nan)
    out = 100 - 100/(1+rs)
    return out.where(al.ne(0), 100.0)

def build_feature_table(mt5: Path) -> pd.DataFrame:
    m15 = prep_ohlc(read_csv_any(mt5 / 'goldsharp_m15.csv'))
    h1 = prep_ohlc(read_csv_any(mt5 / 'goldsharp_h1.csv'))
    d1 = prep_ohlc(read_csv_any(mt5 / 'goldsharp_d1.csv'))
    if m15.empty or h1.empty or d1.empty: return pd.DataFrame()
    m15['m15_rsi14_sma_live'] = rsi(m15.close)
    h1['h1_atr14_sma_live'] = atr_sma(h1)
    h1['h1_range_atr_sma_live'] = (h1.high - h1.low) / h1.h1_atr14_sma_live
    h1['h1_up_sma_live'] = h1.close > h1.close.shift(1)
    d1['d1_atr14_sma_live'] = atr_sma(d1)
    m15s = m15[['time_dt','close','m15_rsi14_sma_live']].rename(columns={'time_dt':'entry_dt','close':'m15_close_sma_live'})
    h1s = h1[['time_dt','close','h1_atr14_sma_live','h1_range_atr_sma_live','h1_up_sma_live']].rename(columns={'time_dt':'h1_time','close':'h1_close_sma_live'})
    d1s = d1[['time_dt','close','d1_atr14_sma_live']].rename(columns={'time_dt':'d1_time','close':'d1_close_sma_live'})
    z = pd.merge_asof(m15s.sort_values('entry_dt'), h1s.sort_values('h1_time'), left_on='entry_dt', right_on='h1_time', direction='backward')
    z = pd.merge_asof(z.sort_values('entry_dt'), d1s.sort_values('d1_time'), left_on='entry_dt', right_on='d1_time', direction='backward')
    z['d1_dist_atr_sma_live'] = (z.m15_close_sma_live - z.d1_close_sma_live) / z.d1_atr14_sma_live
    return z

def score_cols(df: pd.DataFrame) -> list[str]:
    return [c for c in ['feature_score','score','ledger_score','score_threshold'] if c in df.columns]

def one_entry(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty: return df.copy()
    x = df.copy(); sc = score_cols(x)
    for c in sc: x[c] = pd.to_numeric(x[c], errors='coerce')
    if sc:
        return x.sort_values(['entry_dt']+sc, ascending=[True]+[False]*len(sc), kind='mergesort').groupby('entry_dt', as_index=False).head(1)
    return x.sort_values('entry_dt', kind='mergesort').groupby('entry_dt', as_index=False).head(1)

def side_set(g: pd.DataFrame) -> set[str]:
    if 'side' not in g.columns: return set()
    return {str(x) for x in g.side.dropna().unique() if str(x) != 'nan'}

def later_candidates(x: pd.DataFrame, mode: str) -> pd.DataFrame:
    base = ~x.policy_norm.eq(CUR)
    def n(c): return pd.to_numeric(x[c], errors='coerce') if c in x.columns else pd.Series(float('nan'), index=x.index)
    if mode == 'original':
        d1 = n('d1_dist_atr'); h1r = n('h1_range_atr'); rsi14 = n('m15_rsi14')
        h1up = x['h1_up'].astype(str).eq('True') if 'h1_up' in x.columns else pd.Series(False, index=x.index)
    else:
        d1 = n('d1_dist_atr_sma_live'); h1r = n('h1_range_atr_sma_live'); rsi14 = n('m15_rsi14_sma_live')
        h1up = x['h1_up_sma_live'].astype(str).eq('True') if 'h1_up_sma_live' in x.columns else pd.Series(False, index=x.index)
    specs = [
        ('P1_D1', base & (d1 <= -1.641755654337)),
        ('P2_DEN', x.policy_norm.eq(P2POL) & (d1 <= -0.781481)),
        ('P3_RSI', base & (rsi14 >= 73.861004)),
        ('P4_H1_D1_STRICT', base & (h1r <= 0.737217834712) & (d1 <= -0.781481)),
        ('P5_H1UP_CUR', base & h1up & (d1 <= 1.247038) & (h1r <= 0.744978)),
    ]
    frames=[]
    for lab, mask in specs:
        z = one_entry(x[mask].copy())
        if z.empty: continue
        z.insert(0, 'candidate', lab); z.insert(0, 'mode', mode)
        frames.append(z)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=x.columns.tolist()+['mode','candidate'])

def skip_internal_mixed(df: pd.DataFrame) -> tuple[pd.DataFrame,int]:
    if df.empty: return df.copy(),0
    keep=[]; mixed=0
    for dt,g in df.groupby('entry_dt', sort=True):
        ss=side_set(g)
        if len(ss)>1:
            mixed += 1
            continue
        keep.append(g)
    return (pd.concat(keep, ignore_index=True) if keep else pd.DataFrame(columns=df.columns)), mixed

def main() -> int:
    t0=time.time(); ap=argparse.ArgumentParser(); ap.add_argument('--mt5-files-dir',default=''); args=ap.parse_args()
    mt5=gy.mt5_files_dir(args.mt5_files_dir); root=mt5/'FX_OUTPUTS'/'gold_v3'; out=root/'176'; out.mkdir(parents=True,exist_ok=True)
    raw = read_csv_any(root/'107k2c'/'gold_v3_107k2_all_regime_ledgers.csv')
    features = build_feature_table(mt5)
    blockers=[]; warnings=[]
    pc = col(raw, ['policy_key','k2_policy_key','rule_key','policy']) if not raw.empty else ''
    rc = col(raw, ['result_usd','worst_result_usd','pnl_usd','profit_usd','rep_result_usd']) if not raw.empty else ''
    if raw.empty: blockers.append({'id':'missing_107k2_ledger'})
    if features.empty: blockers.append({'id':'missing_or_unusable_ohlc_feature_table'})
    if not pc: blockers.append({'id':'missing_policy_column'})
    if not rc: blockers.append({'id':'missing_result_column'})
    feature_diff=pd.DataFrame(); cand_metrics=pd.DataFrame(); overlap=pd.DataFrame(); union_metrics=pd.DataFrame()
    if not blockers:
        x=raw.copy(); x['entry_dt']=pd.to_datetime(x.entry_dt, errors='coerce'); x=x[x.entry_dt.notna()].sort_values('entry_dt').reset_index(drop=True)
        x['policy_norm']=x[pc].astype(str); x[rc]=pd.to_numeric(x[rc], errors='coerce').fillna(0); x['month']=x.entry_dt.dt.to_period('M').astype(str)
        x=pd.merge_asof(x.sort_values('entry_dt'), features.sort_values('entry_dt'), on='entry_dt', direction='backward')
        # Difference summary for rows where original columns exist.
        diff_rows=[]
        for orig,new in [('m15_rsi14','m15_rsi14_sma_live'),('h1_range_atr','h1_range_atr_sma_live'),('d1_dist_atr','d1_dist_atr_sma_live')]:
            if orig in x.columns and new in x.columns:
                a=pd.to_numeric(x[orig], errors='coerce'); b=pd.to_numeric(x[new], errors='coerce'); d=(a-b).abs().dropna()
                diff_rows.append({'feature':orig,'rows':int(len(d)),'mean_abs_diff':float(d.mean()) if len(d) else math.nan,'median_abs_diff':float(d.median()) if len(d) else math.nan,'max_abs_diff':float(d.max()) if len(d) else math.nan,'p95_abs_diff':float(d.quantile(0.95)) if len(d) else math.nan})
        if 'h1_up' in x.columns and 'h1_up_sma_live' in x.columns:
            oh=x.h1_up.astype(str).str.lower().isin(['true','1','yes','y']); nh=x.h1_up_sma_live.astype(str).str.lower().isin(['true','1','yes','y'])
            diff_rows.append({'feature':'h1_up','rows':int(len(x)),'mean_abs_diff':float((oh!=nh).mean()),'median_abs_diff':0.0,'max_abs_diff':int((oh!=nh).max()),'p95_abs_diff':float((oh!=nh).quantile(0.95))})
        feature_diff=pd.DataFrame(diff_rows); save(feature_diff,out/'gold_v3_176_feature_diff_summary.csv')
        orig = later_candidates(x, 'original')
        sma = later_candidates(x, 'sma_live')
        orig_skip, orig_mixed = skip_internal_mixed(orig)
        sma_skip, sma_mixed = skip_internal_mixed(sma)
        save(orig_skip,out/'gold_v3_176_original_later_orders.csv'); save(sma_skip,out/'gold_v3_176_sma_later_orders.csv')
        rows=[]
        for mode,df,mixed in [('original',orig_skip,orig_mixed),('sma_live',sma_skip,sma_mixed)]:
            rows.append({'mode':mode,'candidate':'LATER_UNION_INTERNAL_MIXED_SKIPPED','mixed_skipped_entry_dt':mixed,**metric(df,rc)})
            for cand,g in df.groupby('candidate', sort=True):
                rows.append({'mode':mode,'candidate':cand,'mixed_skipped_entry_dt':0,**metric(g,rc)})
        cand_metrics=pd.DataFrame(rows); save(cand_metrics,out/'gold_v3_176_candidate_metric_compare.csv')
        # Candidate-level overlap on entry_dt.
        ows=[]
        for cand in ['P1_D1','P2_DEN','P3_RSI','P4_H1_D1_STRICT','P5_H1UP_CUR']:
            od=set(orig_skip[orig_skip.candidate.eq(cand)].entry_dt.astype(str)) if not orig_skip.empty else set()
            sd=set(sma_skip[sma_skip.candidate.eq(cand)].entry_dt.astype(str)) if not sma_skip.empty else set()
            ows.append({'candidate':cand,'original_entry_dt':len(od),'sma_entry_dt':len(sd),'overlap_entry_dt':len(od&sd),'only_original':len(od-sd),'only_sma':len(sd-od),'jaccard':(len(od&sd)/len(od|sd)) if od|sd else 1.0})
        overlap=pd.DataFrame(ows); save(overlap,out/'gold_v3_176_entrydt_overlap.csv')
    ready=len(blockers)==0
    status='READY' if ready else 'BLOCKED'; decision='SMA_FEATURE_IMPACT_READY' if ready else 'SMA_FEATURE_IMPACT_BLOCKED'
    # A short verdict flag: if SMA metrics differ from original, review required before payload.
    review_required=True
    if ready and not overlap.empty:
        review_required=bool((overlap[['only_original','only_sma']].sum().sum())>0)
    summary={'step':STEP,'status':status,'ready':ready,'decision':decision,'created_at_utc':datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z'),'output_dir':str(out),'audit_only':True,'review_only':True,'comparison':'original historical feature columns vs OHLC-derived SMA14 live-style feature columns','review_required_before_payload':review_required,'feature_diff_rows':int(len(feature_diff)),'candidate_metric_rows':int(len(cand_metrics)),'overlap_rows':int(len(overlap)),'source_csv_mutated':False,'contract_mutated':False,'open_asof_allowed':False,'candidate_pool_removed':False,'f002_exclusion_bypassed':False,'final_live_enabled':False,'blocker_count':len(blockers),'warning_count':len(warnings),'elapsed_seconds':round(time.time()-t0,2)}
    (out/'gold_v3_176_summary.json').write_text(json.dumps({**summary,'blockers':blockers,'warnings':warnings},ensure_ascii=False,indent=2),encoding='utf-8'); save(pd.DataFrame([summary]),out/'gold_v3_176_decision.csv')
    lines=['GOLD V3 176 PASTE_ME_SMA_FEATURE_IMPACT_AUDIT']+[f'{k}: {v}' for k,v in summary.items()]
    lines+=['','FEATURE_DIFF_SUMMARY',feature_diff.to_string(index=False) if not feature_diff.empty else 'NO_FEATURE_DIFF']
    lines+=['','CANDIDATE_METRIC_COMPARE',cand_metrics.to_string(index=False) if not cand_metrics.empty else 'NO_CANDIDATE_METRICS']
    lines+=['','ENTRYDT_OVERLAP',overlap.to_string(index=False) if not overlap.empty else 'NO_OVERLAP']
    lines+=['','INTERPRETATION','Compares historical Stage169-style feature columns against OHLC-derived SMA14 live-style features. If candidate entry_dt changes, old PF cannot be blindly reused for live payload generation. Current bucket still depends on policy_key/score reconstruction and is not replaced here.']
    lines+=['','BLOCKERS','NO_BLOCKERS' if not blockers else json.dumps(blockers,ensure_ascii=False,indent=2),'','WARNINGS','NO_WARNINGS' if not warnings else json.dumps(warnings,ensure_ascii=False,indent=2)]
    (out/'paste_me.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({'ready':ready,'decision':decision,'paste_me':str(out/'paste_me.txt')},ensure_ascii=False)); return 0 if ready else 2
if __name__=='__main__': raise SystemExit(main())
