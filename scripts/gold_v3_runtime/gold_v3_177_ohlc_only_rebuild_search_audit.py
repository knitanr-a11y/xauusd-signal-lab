#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse, json, math, time
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd
import gold_v3_107gy_light_non_calendar_subfilter_search_audit as gy

STEP='GOLD_V3_177_OHLC_ONLY_REBUILD_SEARCH_AUDIT_ONLY'
BENCHMARK_PF=2.237
SAMPLE_MIN_TRAIN=50
SAMPLE_MIN_TEST=15
FULL_MIN_TRADES=100


def progress(msg:str)->None:
    print(f'[177 progress] {msg}', flush=True)

def read_csv_any(path:Path)->pd.DataFrame:
    if not path.exists(): return pd.DataFrame()
    for enc in ['utf-8-sig','utf-8','cp932']:
        for sep in [',',';','\t']:
            try:
                df=pd.read_csv(path,encoding=enc,sep=sep,low_memory=False)
                if len(df.columns)>1:
                    df.columns=[str(c).strip() for c in df.columns]
                    if 'time' in df.columns:
                        df['dt']=pd.to_datetime(df['time'],errors='coerce')
                    elif 'entry_dt' in df.columns:
                        df['dt']=pd.to_datetime(df['entry_dt'],errors='coerce')
                    text_cols={'time','entry_dt','dt','symbol','exported_at','is_closed'}
                    for c in df.columns:
                        if c in text_cols:
                            continue
                        try:
                            df[c]=pd.to_numeric(df[c])
                        except Exception:
                            pass
                    if 'dt' in df.columns:
                        return df[df['dt'].notna()].drop_duplicates('dt').sort_values('dt').reset_index(drop=True)
                    return df
            except Exception:
                pass
    return pd.DataFrame()

def combine(tf:str, data_dir:Path)->pd.DataFrame:
    live=read_csv_any(data_dir/f'goldsharp_{tf}.csv')
    old=read_csv_any(data_dir/f'gold#_{tf}.csv')
    if live.empty and old.empty: return pd.DataFrame()
    parts=[]
    if not live.empty: parts.append(live[live['dt']<pd.Timestamp('2025-01-01')])
    if not old.empty: parts.append(old[(old['dt']>=pd.Timestamp('2025-01-01'))&(old['dt']<pd.Timestamp('2026-01-01'))])
    if not live.empty: parts.append(live[live['dt']>=pd.Timestamp('2026-01-01')])
    if not parts: return pd.DataFrame()
    return pd.concat(parts,ignore_index=True).drop_duplicates('dt',keep='last').sort_values('dt').reset_index(drop=True)

def save(df:pd.DataFrame,path:Path)->None:
    path.parent.mkdir(parents=True,exist_ok=True); df.to_csv(path,index=False,encoding='utf-8-sig')

def rsi_sma(close:pd.Series,p:int=14)->pd.Series:
    d=close.diff(); g=d.clip(lower=0); l=-d.clip(upper=0)
    ag=g.rolling(p,min_periods=p).mean(); al=l.rolling(p,min_periods=p).mean(); rs=ag/al.replace(0,np.nan)
    out=100-100/(1+rs); return out.where(al.ne(0),100.0)

def make_features(df:pd.DataFrame,prefix:str)->pd.DataFrame:
    x=pd.DataFrame({'dt':df['dt']})
    o,h,l,c,v=df['open'],df['high'],df['low'],df['close'],df['tick_volume']
    for name,ser in [('open',o),('high',h),('low',l),('close',c),('tick_volume',v)]: x[f'{prefix}_{name}']=ser
    pc=c.shift(1); tr=pd.concat([(h-l).abs(),(h-pc).abs(),(l-pc).abs()],axis=1).max(axis=1)
    x[f'{prefix}_ret1']=c.diff(); x[f'{prefix}_ret3']=c.diff(3); x[f'{prefix}_ret8']=c.diff(8)
    x[f'{prefix}_range']=h-l; x[f'{prefix}_body']=c-o; x[f'{prefix}_body_abs']=(c-o).abs()
    x[f'{prefix}_upper_wick']=h-np.maximum(o,c); x[f'{prefix}_lower_wick']=np.minimum(o,c)-l
    for p in [5,10,14,20,28,50,56,100,200]:
        x[f'{prefix}_atr{p}']=tr.rolling(p,min_periods=p).mean()
        x[f'{prefix}_sma{p}']=c.rolling(p,min_periods=p).mean()
        x[f'{prefix}_ema{p}']=c.ewm(span=p,adjust=False,min_periods=p).mean()
    x[f'{prefix}_rsi14']=rsi_sma(c,14)
    for p in [14,20,28,50,56]:
        x[f'{prefix}_range_atr{p}']=x[f'{prefix}_range']/x[f'{prefix}_atr{p}']
        x[f'{prefix}_body_atr{p}']=x[f'{prefix}_body']/x[f'{prefix}_atr{p}']
    x[f'{prefix}_ema20_gt_ema50']=(x[f'{prefix}_ema20']>x[f'{prefix}_ema50']).astype(int)
    x[f'{prefix}_ema50_gt_ema100']=(x[f'{prefix}_ema50']>x[f'{prefix}_ema100']).astype(int)
    x[f'{prefix}_close_ema20_dist_atr28']=(c-x[f'{prefix}_ema20'])/x[f'{prefix}_atr28']
    x[f'{prefix}_close_sma50_dist_atr28']=(c-x[f'{prefix}_sma50'])/x[f'{prefix}_atr28']
    return x

def merge_features(m15,h1,h4,d1)->pd.DataFrame:
    base=make_features(m15,'m15')
    for f in [make_features(h1,'h1'),make_features(h4,'h4'),make_features(d1,'d1')]:
        base=pd.merge_asof(base.sort_values('dt'),f.sort_values('dt'),on='dt',direction='backward')
    base['hour']=base['dt'].dt.hour
    base['month']=base['dt'].dt.to_period('M').astype(str)
    base['session_7_22']=((base.hour>=7)&(base.hour<=22)).astype(int)
    base['session_12_22']=((base.hour>=12)&(base.hour<=22)).astype(int)
    base['session_15_23']=((base.hour>=15)&(base.hour<=23)).astype(int)
    base['d1_dist_close_atr14']=(base.m15_close-base.d1_close)/base.d1_atr14
    base['d1_dist_close_atr28']=(base.m15_close-base.d1_close)/base.d1_atr28
    base['d1_dist_ema20_atr28']=(base.m15_close-base.d1_ema20)/base.d1_atr28
    base['d1_dist_sma50_atr28']=(base.m15_close-base.d1_sma50)/base.d1_atr28
    base['h1_dist_ema20_atr28']=(base.m15_close-base.h1_ema20)/base.h1_atr28
    base['h4_dist_ema20_atr28']=(base.m15_close-base.h4_ema20)/base.h4_atr28
    return base

def snapshot_parity(data:pd.DataFrame,snap:pd.DataFrame)->pd.DataFrame:
    try:
        if snap.empty or 'entry_dt' not in snap.columns:
            return pd.DataFrame()
        s=snap.copy(); s['dt']=pd.to_datetime(s['entry_dt'],errors='coerce'); s=s[s['dt'].notna()].sort_values('dt')
        if s.empty:
            return pd.DataFrame([{'status':'SNAPSHOT_DT_PARSE_FAILED'}])
        row=s.iloc[-1]
        row_dt=row['dt']
        hit=data[data['dt'].eq(row_dt)]
        if hit.empty:
            return pd.DataFrame([{'snapshot_entry_dt':str(row_dt),'status':'NO_MATCHING_M15_BAR_IN_COMBINED_OHLC'}])
        d=hit.iloc[-1]
        pairs=[('m15_open','m15_open'),('m15_high','m15_high'),('m15_low','m15_low'),('m15_close','m15_close'),('m15_tick_volume','m15_tick_volume'),('m15_rsi14','m15_rsi14'),('h1_atr14','h1_atr14'),('h1_range_atr','h1_range_atr14'),('d1_atr14','d1_atr14'),('d1_dist_atr','d1_dist_close_atr14')]
        rows=[]
        for snap_col,py_col in pairs:
            if snap_col not in row.index or py_col not in data.columns:
                continue
            sv=pd.to_numeric(pd.Series([row[snap_col]]),errors='coerce').iloc[0]
            pv=pd.to_numeric(pd.Series([d[py_col]]),errors='coerce').iloc[0]
            diff=abs(float(sv)-float(pv)) if pd.notna(sv) and pd.notna(pv) else np.nan
            rows.append({'snapshot_entry_dt':str(row_dt),'snapshot_col':snap_col,'python_col':py_col,'snapshot_value':sv,'python_value':pv,'abs_diff':diff,'match_1e_6':bool(pd.notna(diff) and diff<=1e-6)})
        if 'h1_up' in row.index:
            sv=str(row['h1_up']).lower() in ['true','1','yes','y']
            pv=int(d.get('h1_ema20_gt_ema50',-1))
            rows.append({'snapshot_entry_dt':str(row_dt),'snapshot_col':'h1_up','python_col':'h1_ema20_gt_ema50','snapshot_value':int(sv),'python_value':pv,'abs_diff':abs(int(sv)-pv),'match_1e_6':bool(int(sv)==pv)})
        return pd.DataFrame(rows)
    except Exception as e:
        return pd.DataFrame([{'status':'SNAPSHOT_PARITY_EXCEPTION_NON_BLOCKING','error':repr(e)}])

def compute_outcome(entries:pd.DataFrame,m5:pd.DataFrame,direction:str,tp:float,sl:float,horizon_m5:int)->np.ndarray:
    m5=m5.sort_values('dt').reset_index(drop=True)
    times=m5['dt'].values.astype('datetime64[ns]'); et=entries['dt'].values.astype('datetime64[ns]')
    ep=entries.m15_close.values.astype(float); idx=np.searchsorted(times,et,side='right')
    highs=m5.high.values.astype(float); lows=m5.low.values.astype(float); closes=m5.close.values.astype(float)
    out=np.full(len(entries),np.nan,dtype=float)
    for i,j in enumerate(idx):
        end=min(j+horizon_m5,len(m5))
        if j>=len(m5) or end<=j: continue
        price=ep[i]
        if direction=='LONG':
            tpv=price+tp; slv=price-sl; ht=highs[j:end]>=tpv; hs=lows[j:end]<=slv
            hit=ht|hs
            if hit.any():
                k=int(np.argmax(hit)); out[i]=-sl if hs[k] else tp
            else: out[i]=float(max(-sl,min(tp,closes[end-1]-price)))
        else:
            tpv=price-tp; slv=price+sl; ht=lows[j:end]<=tpv; hs=highs[j:end]>=slv
            hit=ht|hs
            if hit.any():
                k=int(np.argmax(hit)); out[i]=-sl if hs[k] else tp
            else: out[i]=float(max(-sl,min(tp,price-closes[end-1])))
    return out

def fast_metric(mask:np.ndarray,pnl:np.ndarray,idx:np.ndarray):
    m=mask & idx & np.isfinite(pnl); n=int(m.sum())
    if n==0: return None
    x=pnl[m]; gp=float(x[x>0].sum()); gl=float(-x[x<0].sum()); pf=gp/gl if gl>0 else (math.inf if gp>0 else 0.0)
    return n,float(x.sum()),pf,float((x>0).mean())

def fast_all(mask,pnl,train_idx,test_idx,full_idx):
    a=fast_metric(mask,pnl,train_idx); b=fast_metric(mask,pnl,test_idx); c=fast_metric(mask,pnl,full_idx)
    if not a or not b or not c: return None
    return {'train_n':a[0],'train_sum':a[1],'train_pf':a[2],'train_wr':a[3],'test_n':b[0],'test_sum':b[1],'test_pf':b[2],'test_wr':b[3],'full_n':c[0],'full_sum':c[1],'full_pf':c[2],'full_wr':c[3]}

def month_stats(mask,pnl,months):
    m=mask & np.isfinite(pnl)
    if not m.any(): return 0,0
    s=pd.DataFrame({'month':months[m],'pnl':pnl[m]}).groupby('month').pnl.sum()
    return int(len(s)),int((s<0).sum())

def make_conditions(data:pd.DataFrame):
    bool_cols=[c for c in data.columns if c.endswith('_gt_ema50') or c.endswith('_gt_ema100') or c.startswith('session_')]
    num_cols=[]
    for c in data.columns:
        if c in ['dt','month','hour']: continue
        if c in bool_cols: continue
        if pd.api.types.is_numeric_dtype(data[c]) and data[c].notna().sum()>1000 and data[c].nunique(dropna=True)>20:
            if any(k in c for k in ['rsi','range_atr','body_atr','ret','dist','atr','body','wick','range']): num_cols.append(c)
    conds=[]
    for c in bool_cols:
        arr=data[c].fillna(0).astype(int).values
        for v in [0,1]: conds.append((f'{c}=={v}',arr==v))
    qs=[.05,.1,.15,.2,.25,.3,.35,.4,.45,.5,.55,.6,.65,.7,.75,.8,.85,.9,.95]
    for c in num_cols:
        s=pd.to_numeric(data[c],errors='coerce').replace([np.inf,-np.inf],np.nan)
        qv=s.dropna().quantile(qs).drop_duplicates(); arr=s.values.astype(float)
        for _,v in qv.items():
            if np.isfinite(v): conds.append((f'{c}>={v:.6g}',arr>=v)); conds.append((f'{c}<={v:.6g}',arr<=v))
    return conds

def main()->int:
    t0=time.time(); ap=argparse.ArgumentParser(); ap.add_argument('--mt5-files-dir',default=''); args=ap.parse_args()
    data_dir=gy.mt5_files_dir(args.mt5_files_dir); root=data_dir/'FX_OUTPUTS'/'gold_v3'; out=root/'177'; out.mkdir(parents=True,exist_ok=True)
    progress('load and combine OHLC: 2025=gold#; 2026+=goldsharp; pre-2025 warmup=goldsharp if available')
    frames={tf:combine(tf,data_dir) for tf in ['m15','m5','h1','h4','d1']}
    snap=read_csv_any(data_dir/'gold_v3_live_feature_snapshot.csv')
    blockers=[]
    for tf,df in frames.items():
        if df.empty: blockers.append({'id':'missing_combined_ohlc','tf':tf})
    top=pd.DataFrame(); allout=pd.DataFrame(); parity=pd.DataFrame()
    if not blockers:
        progress('build live-reproducible OHLC features')
        data=merge_features(frames['m15'],frames['h1'],frames['h4'],frames['d1'])
        save(data.head(500),out/'gold_v3_177_feature_sample_head500.csv')
        if not snap.empty:
            progress('compare optional gold_v3_live_feature_snapshot.csv against Python OHLC features')
            parity=snapshot_parity(data,snap); save(parity,out/'gold_v3_177_live_snapshot_parity.csv')
            if not parity.empty and 'status' in parity.columns and str(parity.iloc[0].get('status','')).startswith('SNAPSHOT_PARITY_EXCEPTION'):
                progress('snapshot parity failed non-blocking; continue OHLC-only search')
        train_idx=((data.dt>=pd.Timestamp('2025-01-02'))&(data.dt<pd.Timestamp('2026-01-01'))).values
        test_idx=(data.dt>=pd.Timestamp('2026-01-01')).values
        full_idx=(data.dt>=pd.Timestamp('2025-01-02')).values
        months=data.month.values
        progress('build rule conditions')
        conds=make_conditions(data); names=[x[0] for x in conds]; masks=[x[1] for x in conds]
        profiles=[]
        for direction in ['LONG','SHORT']:
            for tp,sl,h in [(10,5,48),(15,7.5,64),(20,10,96),(25,10,96),(30,15,128),(40,20,192)]: profiles.append((direction,tp,sl,h))
        results=[]
        for pi,(direction,tp,sl,h) in enumerate(profiles,1):
            progress(f'profile {pi}/{len(profiles)} {direction} TP={tp} SL={sl} horizon_m5={h}: compute outcomes')
            pnl=compute_outcome(data,frames['m5'],direction,tp,sl,h)
            singles=[]
            for name,mask in zip(names,masks):
                met=fast_all(mask,pnl,train_idx,test_idx,full_idx)
                if met and met['train_n']>=60 and met['test_n']>=20 and met['full_n']>=120 and met['train_pf']>=1.15 and met['test_pf']>=1.15:
                    singles.append({'direction':direction,'tp':tp,'sl':sl,'horizon_m5':h,'rule':name,'conds':1,**met})
            singles=sorted(singles,key=lambda r:(min(r['train_pf'],r['test_pf']),r['full_pf'],r['full_n']),reverse=True)
            results.extend(singles[:100])
            progress(f'profile {pi}: singles_pass={len(singles)} pair_scan_top80')
            rule_to_mask={n:m for n,m in zip(names,masks)}; pairs=[]; top_rules=[r['rule'] for r in singles[:80]]
            for i in range(len(top_rules)):
                m1=rule_to_mask[top_rules[i]]
                for j in range(i+1,len(top_rules)):
                    mask=m1 & rule_to_mask[top_rules[j]]
                    met=fast_all(mask,pnl,train_idx,test_idx,full_idx)
                    if met and met['train_n']>=SAMPLE_MIN_TRAIN and met['test_n']>=SAMPLE_MIN_TEST and met['full_n']>=FULL_MIN_TRADES and met['train_pf']>=1.35 and met['test_pf']>=1.35:
                        pairs.append({'direction':direction,'tp':tp,'sl':sl,'horizon_m5':h,'rule':top_rules[i]+' & '+top_rules[j],'conds':2,**met})
            pairs=sorted(pairs,key=lambda r:(min(r['train_pf'],r['test_pf']),r['full_pf'],r['full_n']),reverse=True)
            results.extend(pairs[:150])
        allout=pd.DataFrame(results)
        if not allout.empty:
            top=allout.sort_values(['full_pf','test_pf','train_pf','full_n'],ascending=[False,False,False,False]).head(100).copy()
            rule_to_mask={n:m for n,m in zip(names,masks)}; rows=[]
            for _,r in top.iterrows():
                pnl=compute_outcome(data,frames['m5'],r.direction,float(r.tp),float(r.sl),int(r.horizon_m5)); mask=np.ones(len(data),dtype=bool)
                for part in str(r.rule).split(' & '): mask &= rule_to_mask.get(part,np.zeros(len(data),dtype=bool))
                months_n,neg_m=month_stats(mask & full_idx,pnl,months); rr=r.to_dict(); rr['full_months']=months_n; rr['full_neg_months']=neg_m; rr['beats_old_pf_2_237']=bool(r.full_pf>BENCHMARK_PF and r.test_pf>BENCHMARK_PF and r.train_pf>BENCHMARK_PF); rows.append(rr)
            top=pd.DataFrame(rows); save(allout,out/'gold_v3_177_all_passed_rules.csv'); save(top,out/'gold_v3_177_top100_rules.csv')
    ready=not blockers
    best_pf=float(top.iloc[0].full_pf) if ready and not top.empty else math.nan; best_rule=str(top.iloc[0].rule) if ready and not top.empty else ''
    snapshot_rows=int(len(snap)) if not snap.empty else 0; parity_rows=int(len(parity)) if not parity.empty else 0; parity_fail=int((~parity.get('match_1e_6',pd.Series(dtype=bool))).sum()) if not parity.empty and 'match_1e_6' in parity.columns else 0
    summary={'step':STEP,'status':'READY' if ready else 'BLOCKED','ready':ready,'decision':'OHLC_ONLY_REBUILD_SEARCH_READY' if ready else 'OHLC_ONLY_REBUILD_SEARCH_BLOCKED','created_at_utc':datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z'),'output_dir':str(out),'audit_only':True,'review_only':True,'old_pf_benchmark':BENCHMARK_PF,'best_full_pf':best_pf,'best_rule':best_rule,'top_rows':int(len(top)) if ready else 0,'live_snapshot_detected_rows':snapshot_rows,'live_snapshot_parity_rows':parity_rows,'live_snapshot_parity_fail_rows':parity_fail,'source_csv_mutated':False,'contract_mutated':False,'open_asof_allowed':False,'candidate_pool_removed':False,'f002_exclusion_bypassed':False,'final_live_enabled':False,'blocker_count':len(blockers),'elapsed_seconds':round(time.time()-t0,2)}
    (out/'gold_v3_177_summary.json').write_text(json.dumps({**summary,'blockers':blockers},ensure_ascii=False,indent=2),encoding='utf-8'); save(pd.DataFrame([summary]),out/'gold_v3_177_decision.csv')
    lines=['GOLD V3 177 PASTE_ME_OHLC_ONLY_REBUILD_SEARCH_AUDIT']+[f'{k}: {v}' for k,v in summary.items()]
    lines+=['','LIVE_SNAPSHOT_PARITY',parity.to_string(index=False) if not parity.empty else 'NO_LIVE_SNAPSHOT_PARITY']
    lines+=['','TOP30_RULES',top.head(30).to_string(index=False) if not top.empty else 'NO_TOP_RULES']
    lines+=['','INTERPRETATION','This is an OHLC-only rebuild search. It uses 2025 gold# candles, 2026+ goldsharp candles, and goldsharp pre-2025 only as HTF warmup. Optional live snapshot is used only for parity audit and never as a backtest/search source. Rules are generated only from candle-derived features known at entry time. Results are audit-only and must still pass spread/slippage/robustness gates before any live payload.']
    lines+=['','BLOCKERS','NO_BLOCKERS' if not blockers else json.dumps(blockers,ensure_ascii=False,indent=2)]
    (out/'paste_me.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    progress('done')
    print(json.dumps({'ready':ready,'decision':summary['decision'],'paste_me':str(out/'paste_me.txt')},ensure_ascii=False)); return 0 if ready else 2
if __name__=='__main__': raise SystemExit(main())
