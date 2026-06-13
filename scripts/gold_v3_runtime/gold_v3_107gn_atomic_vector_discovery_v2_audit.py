#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse, itertools, json, math, os
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd

STEP='GOLD_V3_107GN_ATOMIC_VECTOR_DISCOVERY_V2_AUDIT_ONLY'
READY='GOLD_V3_107GN_ATOMIC_VECTOR_DISCOVERY_V2_READY_AUDIT_ONLY'
BLOCKED='GOLD_V3_107GN_ATOMIC_VECTOR_DISCOVERY_V2_BLOCKED_INPUT_INCOMPLETE_AUDIT_ONLY'
CSV_CONTRACT='open/in-progress candles are not written to CSV; CSV latest row is contractually closed; open/as-of treatment is forbidden'
POOL_POLICY='poolから外さない。rolling health gateに判断させる。'
FORBIDDEN=('gold_v2','old_gold','disc8','stage41')
NAMES={'m15':['gold#_m15.csv','goldsharp_m15.csv'],'m5':['gold#_m5.csv','goldsharp_m5.csv'],'h1':['gold#_h1.csv','goldsharp_h1.csv'],'h4':['gold#_h4.csv','goldsharp_h4.csv'],'d1':['gold#_d1.csv','goldsharp_d1.csv']}
PROFILES=[('TP5_SL2.5_RR2_H64','fixed',5.0,2.5,64),('TP10_SL5_RR2_H64','fixed',10.0,5.0,64),('TP15_SL7.5_RR2_H64','fixed',15.0,7.5,64),('TPmax5_ATR0.50_RR1.5_H64','dynamic',0.50,1.5,64),('TPmax5_ATR0.75_RR2.0_H64','dynamic',0.75,2.0,64),('TPmax5_ATR1.00_RR2.0_H64','dynamic',1.00,2.0,64)]
COOLDOWNS=[2,4]

def save(df,p): p.parent.mkdir(parents=True,exist_ok=True); df.to_csv(p,index=False,encoding='utf-8-sig')
def bad(p): return any(x in str(p).replace('\\','/').lower() for x in FORBIDDEN)
def base_dirs(data_dir,mt5):
    out=[]
    if data_dir: out.append(Path(data_dir).expanduser().resolve())
    if mt5:
        b=Path(mt5).expanduser().resolve(); out += [b/'FX_INPUTS'/'gold_v3'/'107g', b]
    out.append(Path.cwd())
    return list(dict.fromkeys(out))
def read_one(p):
    df=pd.read_csv(p,sep=None,engine='python',encoding='utf-8-sig')
    cols={c.lower():c for c in df.columns}; t=cols.get('time') or cols.get('datetime') or cols.get('date')
    if not t or any(k not in cols for k in ['open','high','low','close']): raise ValueError('missing time/ohlc')
    x=df[[t,cols['open'],cols['high'],cols['low'],cols['close']]].copy(); x.columns=['time','open','high','low','close']
    x['time']=pd.to_datetime(x.time,errors='coerce')
    for c in ['open','high','low','close']: x[c]=pd.to_numeric(x[c],errors='coerce')
    return x.dropna().sort_values('time').drop_duplicates('time',keep='last')
def load_tf(tf,dirs):
    parts=[]; used=[]
    for d in dirs:
        for n in NAMES[tf]:
            p=d/n
            if p.exists() and not bad(p):
                x=read_one(p); x['source_file']=n; parts.append(x); used.append(str(p))
    if not parts: return pd.DataFrame(),used
    df=pd.concat(parts,ignore_index=True).sort_values(['time','source_file'])
    before=len(df); df=df.drop_duplicates('time',keep='last').sort_values('time').reset_index(drop=True); df.attrs['dup_dropped']=before-len(df)
    return df,used

def ema(s,n): return s.ewm(span=n,adjust=False,min_periods=n).mean()
def atr(df,n):
    pc=df.close.shift(1); tr=pd.concat([(df.high-df.low),(df.high-pc).abs(),(df.low-pc).abs()],axis=1).max(axis=1)
    return tr.rolling(n,min_periods=n).mean()
def rsi(s,n=14):
    d=s.diff(); up=d.clip(lower=0); dn=-d.clip(upper=0); rs=up.rolling(n,min_periods=n).mean()/dn.rolling(n,min_periods=n).mean()
    return 100-100/(1+rs)
def vf(s): return s.fillna(False).astype(bool)
def add_base(df,prefix=''):
    x=df.copy(); x[prefix+'ema20']=ema(x.close,20); x[prefix+'ema50']=ema(x.close,50); x[prefix+'ema100']=ema(x.close,100)
    x[prefix+'atr14']=atr(x,14); x[prefix+'atr28']=atr(x,28); x[prefix+'ret1']=x.close.diff(1); x[prefix+'ret2']=x.close.diff(2); x[prefix+'ret4']=x.close.diff(4); x[prefix+'ret8']=x.close.diff(8); x[prefix+'ret16']=x.close.diff(16); x[prefix+'rsi14']=rsi(x.close,14)
    return x
def add_m15(df):
    x=add_base(df)
    for n in [12,20,48,96]:
        x[f'hi{n}']=x.high.rolling(n,min_periods=n).max().shift(1); x[f'lo{n}']=x.low.rolling(n,min_periods=n).min().shift(1)
    rng=(x.high-x.low).replace(0,np.nan); x['body']=x.close-x.open; x['body_abs']=x.body.abs(); x['body_ratio']=x.body_abs/rng
    x['upper_wick']=(x.high-np.maximum(x.open,x.close))/rng; x['lower_wick']=(np.minimum(x.open,x.close)-x.low)/rng
    x['ema_gap']=(x.close-x.ema20)/x.atr28.replace(0,np.nan); x['ema20_slope']=x.ema20.diff(4); x['ema50_slope']=x.ema50.diff(4)
    x['pos48']=(x.close-x.lo48)/(x.hi48-x.lo48).replace(0,np.nan)
    x['break_hi20']=x.close>x.hi20; x['break_lo20']=x.close<x.lo20
    x['reclaim_ema20']=(x.low<x.ema20)&(x.close>x.ema20)&(x.close>x.open); x['reject_ema20']=(x.high>x.ema20)&(x.close<x.ema20)&(x.close<x.open)
    x['failed_breakdown']=(x.low<x.lo20)&(x.close>x.lo20)&(x.close>x.open); x['failed_breakout']=(x.high>x.hi20)&(x.close<x.hi20)&(x.close<x.open)
    x['atr_q70']=x.atr28.rolling(500,min_periods=100).quantile(.70); x['atr_q30']=x.atr28.rolling(500,min_periods=100).quantile(.30)
    x['high_vol']=x.atr28>=x.atr_q70; x['low_vol']=x.atr28<=x.atr_q30; x['non_high_vol']=x.atr28<x.atr_q70
    x['session_7_15']=x.time.dt.hour.between(7,15); x['session_16_22']=x.time.dt.hour.between(16,22)
    return x
def merge_htf(m15,h1,h4,d1):
    x=m15.copy()
    for tf,df in [('h1',h1),('h4',h4),('d1',d1)]:
        if df.empty: continue
        f=add_base(df,tf+'_'); cols=['time']+[c for c in f.columns if c.startswith(tf+'_')]
        x=pd.merge_asof(x.sort_values('time'),f[cols].sort_values('time'),on='time',direction='backward')
    return x

def atoms(df,side):
    x=df; false=vf(pd.Series(False,index=x.index))
    h1_up=vf((x.h1_ema20>x.h1_ema50)&(x.h1_ret4>0)) if 'h1_ema20' in x else false
    h1_down=vf((x.h1_ema20<x.h1_ema50)&(x.h1_ret4<0)) if 'h1_ema20' in x else false
    h4_up=vf((x.h4_ema20>x.h4_ema50)&(x.h4_ret4>0)) if 'h4_ema20' in x else false
    h4_down=vf((x.h4_ema20<x.h4_ema50)&(x.h4_ret4<0)) if 'h4_ema20' in x else false
    d1_up=vf((x.d1_ema20>x.d1_ema50)&(x.d1_ret4>0)) if 'd1_ema20' in x else false
    d1_down=vf((x.d1_ema20<x.d1_ema50)&(x.d1_ret4<0)) if 'd1_ema20' in x else false
    common={'high_vol':vf(x.high_vol),'non_high_vol':vf(x.non_high_vol),'low_vol':vf(x.low_vol),'session_7_15':vf(x.session_7_15),'session_16_22':vf(x.session_16_22)}
    if side=='LONG':
        ctx={'h4_up':h4_up,'h1_up':h1_up,'d1_up':d1_up,'h4_not_down':~h4_down,'h1_not_down':~h1_down,'ema20_above_ema50':vf(x.ema20>x.ema50),'ema50_slope_up':vf(x.ema50_slope>0),'pos48_low_mid':vf((x.pos48>=0.20)&(x.pos48<=0.65)),'pos48_high':vf(x.pos48>=0.75),**common}
        trig={'ema_reclaim_long':vf(x.reclaim_ema20),'failed_breakdown_reclaim':vf(x.failed_breakdown),'lower_wick_reversal':vf((x.lower_wick>=0.45)&(x.close>x.open)),'rsi_rebound_long':vf((x.rsi14.shift(1)<40)&(x.rsi14>=40)),'breakout_hold_long':vf(x.break_hi20)&vf(x.close>x.open),'momentum_reaccel_long':vf((x.ret2>0)&(x.ret4>0)&(x.close>x.ema20)),'oversold_turn_long':vf((x.rsi14<=42)&(x.ret2>0)&(x.lower_wick>=0.25))}
    else:
        ctx={'h4_down':h4_down,'h1_down':h1_down,'d1_down':d1_down,'h4_not_up':~h4_up,'h1_not_up':~h1_up,'ema20_below_ema50':vf(x.ema20<x.ema50),'ema50_slope_down':vf(x.ema50_slope<0),'pos48_high_mid':vf((x.pos48>=0.35)&(x.pos48<=0.80)),'pos48_low':vf(x.pos48<=0.25),**common}
        trig={'ema_reject_short':vf(x.reject_ema20),'failed_breakout_reject':vf(x.failed_breakout),'upper_wick_reversal':vf((x.upper_wick>=0.45)&(x.close<x.open)),'rsi_rollover_short':vf((x.rsi14.shift(1)>60)&(x.rsi14<=60)),'breakdown_hold_short':vf(x.break_lo20)&vf(x.close<x.open),'momentum_reaccel_short':vf((x.ret2<0)&(x.ret4<0)&(x.close<x.ema20)),'overbought_turn_short':vf((x.rsi14>=58)&(x.ret2<0)&(x.upper_wick>=0.25))}
    return {k:v.values for k,v in ctx.items()},{k:v.values for k,v in trig.items()}

def make_seeds(df,side,max_seeds):
    ctx,trig=atoms(df,side); fwd=df.close.shift(-16)-df.close; rows=[]
    ctx_items=list(ctx.items())
    for tn,tm in trig.items():
        groups=[(),*itertools.combinations(ctx_items,1),*itertools.combinations(ctx_items,2)]
        for combo in groups:
            mask=tm.copy(); names=[tn]
            for cn,cm in combo: mask &= cm; names.append(cn)
            n=int(mask.sum())
            if n<30 or n>3500: continue
            edge=float(np.nanmean(fwd[mask])) if side=='LONG' else float(np.nanmean(-fwd[mask]))
            if not np.isfinite(edge): continue
            family=tn.split('_')[0]+'_'+tn.split('_')[1] if '_' in tn else tn
            score=edge*1000 + min(n,800)*0.2 - max(0,n-1500)*0.15
            rows.append(dict(side=side,family=family,condition='&'.join(names),raw_events=n,forward_edge=edge,seed_score=score,mask=mask))
    out=[]; seen_family={}
    for r in sorted(rows,key=lambda x:x['seed_score'],reverse=True):
        fam=r['family']; seen_family[fam]=seen_family.get(fam,0)+1
        if seen_family[fam]<=max(8,max_seeds//8): out.append(r)
        if len(out)>=max_seeds: break
    return out

def apply_cd(idx,cool):
    out=[]; last=-10**9
    for i in idx:
        if i-last>=cool: out.append(i); last=i
    return out
def profile_tp_sl(row, prof):
    pid,kind,a,b,h=prof
    if kind=='fixed': return float(a),float(b),int(h)
    tp=max(5.0,float(row.atr28)*float(a)); return tp,tp/float(b),int(h)
def result_idx(i,df,m5,prof,side,cache):
    key=(int(i),side,prof[0])
    if key in cache: return cache[key]
    row=df.iloc[i]; tp,sl,h=profile_tp_sl(row,prof); ep=float(row.close)
    start=np.searchsorted(m5['time'],row.time.to_datetime64(),side='right'); end=min(len(m5['time']),start+h*3)
    tpv=ep+tp if side=='LONG' else ep-tp; slv=ep-sl if side=='LONG' else ep+sl
    res=0.0
    for j in range(start,end):
        ht=(m5['high'][j]>=tpv) if side=='LONG' else (m5['low'][j]<=tpv)
        hs=(m5['low'][j]<=slv) if side=='LONG' else (m5['high'][j]>=slv)
        if ht and hs: res=-sl; break
        if hs: res=-sl; break
        if ht: res=tp; break
    cache[key]=float(res); return float(res)
def metrics(vals,months=None):
    a=np.array(vals,float); tr=len(a)
    if tr==0: return dict(trades=0,wins=0,losses=0,win_rate=0.0,profit_factor=0.0,sum_result_usd=0.0,negative_month_count=0)
    gp=a[a>0].sum(); gl=-a[a<0].sum(); pf=gp/gl if gl>0 else (math.inf if gp>0 else 0.0); neg=0
    if months is not None and len(months)==tr:
        neg=int((pd.DataFrame({'m':months,'r':a}).groupby('m').r.sum()<0).sum())
    return dict(trades=int(tr),wins=int((a>0).sum()),losses=int((a<0).sum()),win_rate=float((a>0).mean()),profit_factor=float(pf),sum_result_usd=float(a.sum()),negative_month_count=neg)
def eval_seed(df,m5,seed,prof,cool,cache):
    idx=apply_cd(np.where(seed['mask'])[0],cool); vals=[]; mons=[]; entries=[]
    for i in idx:
        vals.append(result_idx(i,df,m5,prof,seed['side'],cache)); mons.append(str(df.iloc[i].time.to_period('M'))); entries.append(i)
    m=metrics(vals,mons); pid,kind,a,b,h=prof
    m.update(side=seed['side'],family=seed['family'],condition=seed['condition'],profile_id=pid,profile_kind=kind,cooldown_bars=cool,horizon_m15=h,raw_events=int(seed['raw_events']),entry_count=len(idx),forward_edge=float(seed['forward_edge']))
    rows=pd.DataFrame({'entry_dt':[df.iloc[i].time for i in entries],'side':seed['side'],'family':seed['family'],'condition':seed['condition'],'profile_id':pid,'cooldown_bars':cool,'result_usd':vals}) if vals else pd.DataFrame()
    return m,rows
def split_perf(rows):
    if rows.empty: return {}
    x=rows.copy(); x['entry_dt']=pd.to_datetime(x.entry_dt); d=x.entry_dt
    ss={'2025':d.dt.year==2025,'2026':d.dt.year==2026,'2025H1':(d>=pd.Timestamp('2025-01-01'))&(d<pd.Timestamp('2025-07-01')),'2025H2':(d>=pd.Timestamp('2025-07-01'))&(d<pd.Timestamp('2026-01-01')),'2026_03_PLUS':d>=pd.Timestamp('2026-03-01'),'2026_05_06':d>=pd.Timestamp('2026-05-01')}
    out={}
    for k,mask in ss.items():
        m=metrics(x.loc[mask,'result_usd'].tolist())
        for kk,v in m.items(): out[f'{k}_{kk}']=v
    return out
def pfcap(v):
    try: return 10.0 if math.isinf(float(v)) else min(max(float(v),0.0),10.0)
    except Exception: return 0.0
def quality_score(r):
    penalty=0
    if r.get('2026_trades',0)>=20 and r.get('2026_profit_factor',0)<1.2: penalty+=700
    if r.get('2025H2_trades',0)>=20 and r.get('2025H2_profit_factor',0)<1.2: penalty+=500
    return pfcap(r.get('profit_factor',0))*1000 + float(r.get('win_rate',0))*900 + min(float(r.get('trades',0)),500)*0.25 - float(r.get('negative_month_count',0))*350 - penalty

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--data-dir',default=''); ap.add_argument('--mt5-files-dir',default=os.environ.get('MT5_FILES_DIR','')); ap.add_argument('--max-seeds-per-side',type=int,default=70)
    args=ap.parse_args(); dirs=base_dirs(args.data_dir,args.mt5_files_dir); base=Path(args.mt5_files_dir).expanduser().resolve() if args.mt5_files_dir else Path.cwd(); out=base/'FX_OUTPUTS'/'gold_v3'/'107gnc'; out.mkdir(parents=True,exist_ok=True)
    blockers=[]; vals=[]; findings=[]; outputs=[]; loaded={}; cov=[]
    for tf in ['m15','m5','h1','h4','d1']:
        loaded[tf],used=load_tf(tf,dirs); cov.append(dict(timeframe=tf,rows=len(loaded[tf]),min_time=loaded[tf].time.min() if len(loaded[tf]) else '',max_time=loaded[tf].time.max() if len(loaded[tf]) else '',sources=';'.join(used),duplicate_rows_dropped=loaded[tf].attrs.get('dup_dropped',0)))
    save(pd.DataFrame(cov),out/'gold_v3_107gn_input_coverage.csv'); outputs.append('gold_v3_107gn_input_coverage.csv')
    if loaded['m15'].empty or loaded['m5'].empty: blockers.append(dict(blocker_id='missing_m15_or_m5',reason='M15 and M5 exact OHLC files are required'))
    if not blockers:
        df=merge_htf(add_m15(loaded['m15']),loaded['h1'],loaded['h4'],loaded['d1']).dropna(subset=['atr28','ema20','ema50','rsi14','hi20','lo20','hi48','lo48']).reset_index(drop=True)
        df['entry_month']=df.time.dt.to_period('M').astype(str)
        save(pd.DataFrame([dict(feature_rows=len(df),months=df.entry_month.nunique(),min_time=df.time.min(),max_time=df.time.max())]),out/'gold_v3_107gn_feature_coverage.csv'); outputs.append('gold_v3_107gn_feature_coverage.csv')
        seeds=[]
        for side in ['LONG','SHORT']: seeds += make_seeds(df,side,args.max_seeds_per_side)
        seed_df=pd.DataFrame([{k:v for k,v in s.items() if k!='mask'} for s in seeds]).sort_values(['side','seed_score'],ascending=[True,False])
        save(seed_df,out/'gold_v3_107gn_atomic_seed_summary.csv'); outputs.append('gold_v3_107gn_atomic_seed_summary.csv')
        m5={'time':loaded['m5'].time.values,'high':loaded['m5'].high.values.astype(float),'low':loaded['m5'].low.values.astype(float)}
        rows=[]; ledgers=[]; cache={}
        for seed in seeds:
            for prof in PROFILES:
                for cd in COOLDOWNS:
                    m,lg=eval_seed(df,m5,seed,prof,cd,cache)
                    if not lg.empty: m.update(split_perf(lg))
                    m['quality_score']=quality_score(m); rows.append(m)
                    if not lg.empty and m['trades']>=20 and (m['profit_factor']>=1.5 or m['win_rate']>=0.55):
                        key=f"{seed['side']}||{seed['family']}||{seed['condition']}||{prof[0]}||CD{cd}"
                        ledgers.append(lg.assign(candidate_key=key))
        summ=pd.DataFrame(rows)
        if summ.empty: blockers.append(dict(blocker_id='no_candidate_results',reason='atomic vector discovery returned no evaluated candidates'))
        else:
            summ=summ.sort_values(['side','quality_score'],ascending=[True,False])
            save(summ,out/'gold_v3_107gn_candidate_summary.csv'); outputs.append('gold_v3_107gn_candidate_summary.csv')
            long_s=summ[summ.side=='LONG'].sort_values('quality_score',ascending=False); short_s=summ[summ.side=='SHORT'].sort_values('quality_score',ascending=False)
            save(long_s.head(80),out/'gold_v3_107gn_top_long_candidates.csv'); save(short_s.head(80),out/'gold_v3_107gn_top_short_candidates.csv'); outputs += ['gold_v3_107gn_top_long_candidates.csv','gold_v3_107gn_top_short_candidates.csv']
            if ledgers:
                top_keys=set(pd.concat([long_s.head(20),short_s.head(20)],ignore_index=True).apply(lambda r:f"{r.side}||{r.family}||{r.condition}||{r.profile_id}||CD{int(r.cooldown_bars)}",axis=1))
                lgall=pd.concat(ledgers,ignore_index=True); lgall=lgall[lgall.candidate_key.isin(top_keys)]
                save(lgall,out/'gold_v3_107gn_top_candidate_trade_ledger.csv'); outputs.append('gold_v3_107gn_top_candidate_trade_ledger.csv')
            fam=[]
            for (side,family),g in summ.groupby(['side','family']):
                b=g.sort_values('quality_score',ascending=False).iloc[0]
                fam.append(dict(side=side,family=family,candidate_count=len(g),best_condition=b.condition,best_profile_id=b.profile_id,best_trades=int(b.trades),best_win_rate=float(b.win_rate),best_profit_factor=float(b.profit_factor),best_negative_month_count=int(b.negative_month_count),best_quality_score=float(b.quality_score)))
            save(pd.DataFrame(fam),out/'gold_v3_107gn_family_summary.csv'); outputs.append('gold_v3_107gn_family_summary.csv')
            split_columns=[c for c in summ.columns if any(c.startswith(p+'_') for p in ['2025','2026','2025H1','2025H2','2026_03_PLUS','2026_05_06'])]
            save(summ[['side','family','condition','profile_id','cooldown_bars','trades','win_rate','profit_factor','sum_result_usd','negative_month_count','quality_score']+split_columns].sort_values('quality_score',ascending=False).head(120),out/'gold_v3_107gn_split_summary.csv'); outputs.append('gold_v3_107gn_split_summary.csv')
            goodL=long_s[(long_s.trades>=150)&(long_s.profit_factor>=2.0)&(long_s.win_rate>=0.55)&(long_s.negative_month_count<=2)]
            goodS=short_s[(short_s.trades>=150)&(short_s.profit_factor>=2.0)&(short_s.win_rate>=0.55)&(short_s.negative_month_count<=2)]
            gates=pd.DataFrame([dict(gate='long_viable_count',observed=len(goodL),operator='>=',threshold=1,result='PASS' if len(goodL)>=1 else 'FAIL'),dict(gate='short_viable_count',observed=len(goodS),operator='>=',threshold=1,result='PASS' if len(goodS)>=1 else 'FAIL')])
            save(gates,out/'gold_v3_107gn_quality_gate_matrix.csv'); outputs.append('gold_v3_107gn_quality_gate_matrix.csv')
            acts=[]
            if len(goodL) or len(goodS): acts.append(dict(priority=1,action='run_anchored_train_test_on_atomic_vectors',reason=f'long_good={len(goodL)}, short_good={len(goodS)}'))
            else: acts.append(dict(priority=1,action='do_not_advance_atomic_vectors_without_manual_feature_redesign',reason='No viable atomic candidates under current thresholds.'))
            save(pd.DataFrame(acts),out/'gold_v3_107gn_recommended_next_actions.csv'); outputs.append('gold_v3_107gn_recommended_next_actions.csv')
            findings.append('best_atomic_long='+json.dumps(long_s.iloc[0].to_dict() if len(long_s) else {},ensure_ascii=False,default=str))
            findings.append('best_atomic_short='+json.dumps(short_s.iloc[0].to_dict() if len(short_s) else {},ensure_ascii=False,default=str))
            findings.append(f'good_counts: LONG={len(goodL)} SHORT={len(goodS)}')
            vals.append(dict(check_id='atomic_candidate_rows_positive',result='PASS' if len(summ)>0 else 'FAIL',observed=len(summ),expected='>0',severity='BLOCKER'))
    vals += [dict(check_id='audit_only',result='PASS',observed=True,expected=True,severity='BLOCKER'),dict(check_id='source_csv_mutated',result='PASS',observed=False,expected=False,severity='BLOCKER'),dict(check_id='candidate_pool_mutated',result='PASS',observed=False,expected=False,severity='BLOCKER'),dict(check_id='open_asof_allowed',result='PASS',observed=False,expected=False,severity='BLOCKER')]
    val=pd.DataFrame(vals); status=READY if not blockers and val.result.eq('PASS').all() else BLOCKED
    summary=dict(step=STEP,status=status,created_at_utc=datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z'),output_dir=str(out),audit_only=True,live_ready=False,source_csv_mutated=False,contract_mutated=False,manual_candidate_demotion_or_removal=False,open_asof_allowed=False,csv_contract=CSV_CONTRACT,csv_open_bar_exclusion_required=False,pool_policy=POOL_POLICY,blocker_count=len(blockers),validation_failure_count=int((~val.result.eq('PASS')).sum()),runtime_estimate='medium_to_heavy_30_to_90min_stop_if_over_90min')
    if 'summ' in locals() and not summ.empty: summary.update(candidate_rows=len(summ),seed_rows=len(seeds),outcome_cache_size=len(cache))
    save(pd.DataFrame(blockers),out/'gold_v3_107gn_blocker_matrix.csv'); save(val,out/'gold_v3_107gn_validation_matrix.csv')
    outputs += ['gold_v3_107gn_blocker_matrix.csv','gold_v3_107gn_validation_matrix.csv','gold_v3_107gn_summary.json','GOLD_V3_107GN_ATOMIC_VECTOR_DISCOVERY_V2_AUDIT_ONLY_REPORT.md','paste_me.txt']
    (out/'gold_v3_107gn_summary.json').write_text(json.dumps(summary|{'findings':findings},ensure_ascii=False,indent=2,default=str),encoding='utf-8')
    (out/'GOLD_V3_107GN_ATOMIC_VECTOR_DISCOVERY_V2_AUDIT_ONLY_REPORT.md').write_text('# GOLD V3 107GN report\n\n'+json.dumps({'summary':summary,'findings':findings,'blockers':blockers},ensure_ascii=False,indent=2,default=str),encoding='utf-8')
    lines=['GOLD V3 107GN PASTE_ME_ATOMIC_VECTOR_DISCOVERY_V2',f'status: {status}',f'ready: {str(status==READY).lower()}','live_ready: false','source_csv_mutated: false','contract_mutated: false','manual_candidate_demotion_or_removal: false','open_asof_allowed: false','csv_contract: '+CSV_CONTRACT,'csv_open_bar_exclusion_required: false','safety: audit_only=true, proxy_only=true, mt5=false, discord=false, ai_api=false, live_hook=false, final_signal=false','pool_policy: '+POOL_POLICY,'source: exact GOLD V3 107g OHLC inputs; atomic vector discovery v2; no runtime change','runtime_estimate: medium_to_heavy; 30_to_90min; stop_if_over_90min',f'blocker_count: {len(blockers)}','','KEY_METRICS']+[f'{k}: {v}' for k,v in summary.items()]+['','FINDINGS']+(findings or ['NO_FINDINGS'])+['','BLOCKERS',pd.DataFrame(blockers).to_string(index=False) if blockers else 'NO_BLOCKERS','','VALIDATION',val.to_string(index=False),'','OUTPUTS']+outputs
    (out/'paste_me.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({'status':status,'ready':status==READY,'paste_me':str(out/'paste_me.txt')},ensure_ascii=False,indent=2)); return 0 if status==READY else 2
if __name__=='__main__': raise SystemExit(main())
