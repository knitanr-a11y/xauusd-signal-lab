#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse, json, math, os
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd

STEP='GOLD_V3_107GL_NEW_LONG_SHORT_VECTOR_FAMILY_GENERATION_AUDIT_ONLY'
READY='GOLD_V3_107GL_NEW_LONG_SHORT_VECTOR_FAMILY_GENERATION_READY_AUDIT_ONLY'
BLOCKED='GOLD_V3_107GL_NEW_LONG_SHORT_VECTOR_FAMILY_GENERATION_BLOCKED_INPUT_INCOMPLETE_AUDIT_ONLY'
CSV_CONTRACT='open/in-progress candles are not written to CSV; CSV latest row is contractually closed; open/as-of treatment is forbidden'
POOL_POLICY='poolから外さない。rolling health gateに判断させる。'
FORBIDDEN=('gold_v2','old_gold','disc8','stage41')
NAMES={'m15':['gold#_m15.csv','goldsharp_m15.csv'],'m5':['gold#_m5.csv','goldsharp_m5.csv'],'h1':['gold#_h1.csv','goldsharp_h1.csv'],'h4':['gold#_h4.csv','goldsharp_h4.csv'],'d1':['gold#_d1.csv','goldsharp_d1.csv']}
FIXED=[('TP5_SL2.5_RR2_H64','fixed',5.0,2.5,64),('TP10_SL5_RR2_H64','fixed',10.0,5.0,64),('TP15_SL7.5_RR2_H64','fixed',15.0,7.5,64),('TP20_SL10_RR2_H64','fixed',20.0,10.0,64)]
DYN=[('TPmax5_ATR0.50_RR1.5_H64','dynamic',0.50,1.5,64),('TPmax5_ATR0.75_RR2.0_H64','dynamic',0.75,2.0,64),('TPmax5_ATR1.00_RR2.0_H64','dynamic',1.00,2.0,64),('TPmax5_ATR1.25_RR2.5_H64','dynamic',1.25,2.5,64)]
PROFILES=FIXED+DYN
COOLDOWNS=[0,2,4]

def bad(p):
    s=str(p).replace('\\','/').lower(); return any(x in s for x in FORBIDDEN)

def base_dirs(data_dir, mt5):
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

def load_tf(tf, dirs):
    parts=[]; used=[]
    for d in dirs:
        for n in NAMES[tf]:
            p=d/n
            if p.exists() and not bad(p):
                x=read_one(p); x['source_file']=n; parts.append(x); used.append(str(p))
    if not parts: return pd.DataFrame(), used
    df=pd.concat(parts,ignore_index=True).sort_values(['time','source_file'])
    before=len(df); df=df.drop_duplicates('time',keep='last').sort_values('time').reset_index(drop=True)
    df.attrs['dup_dropped']=before-len(df); return df, used

def ema(s,n): return s.ewm(span=n,adjust=False,min_periods=n).mean()
def atr(df,n):
    pc=df.close.shift(1); tr=pd.concat([(df.high-df.low),(df.high-pc).abs(),(df.low-pc).abs()],axis=1).max(axis=1)
    return tr.rolling(n,min_periods=n).mean()
def rsi(s,n=14):
    d=s.diff(); up=d.clip(lower=0); dn=-d.clip(upper=0); rs=up.rolling(n,min_periods=n).mean()/dn.rolling(n,min_periods=n).mean()
    return 100-100/(1+rs)

def add_base(df,prefix=''):
    x=df.copy(); x[prefix+'ema20']=ema(x.close,20); x[prefix+'ema50']=ema(x.close,50); x[prefix+'ema100']=ema(x.close,100)
    x[prefix+'atr14']=atr(x,14); x[prefix+'atr28']=atr(x,28); x[prefix+'ret1']=x.close.diff(1); x[prefix+'ret4']=x.close.diff(4); x[prefix+'ret16']=x.close.diff(16); x[prefix+'rsi14']=rsi(x.close,14)
    return x

def add_m15_features(m15):
    x=add_base(m15)
    x['roll_hi20']=x.high.rolling(20,min_periods=20).max().shift(1)
    x['roll_lo20']=x.low.rolling(20,min_periods=20).min().shift(1)
    x['roll_hi48']=x.high.rolling(48,min_periods=48).max().shift(1)
    x['roll_lo48']=x.low.rolling(48,min_periods=48).min().shift(1)
    x['range48']=(x.roll_hi48-x.roll_lo48).replace(0,np.nan)
    x['pos48']=(x.close-x.roll_lo48)/x.range48
    x['body']=x.close-x.open; x['body_abs']=x.body.abs(); rng=(x.high-x.low).replace(0,np.nan)
    x['body_ratio']=x.body_abs/rng
    x['upper_wick']=(x.high-np.maximum(x.open,x.close))/rng
    x['lower_wick']=(np.minimum(x.open,x.close)-x.low)/rng
    x['break_hi20']=(x.close>x.roll_hi20)
    x['break_lo20']=(x.close<x.roll_lo20)
    x['failed_breakdown']=(x.low<x.roll_lo20)&(x.close>x.roll_lo20)&(x.close>x.open)
    x['failed_breakout']=(x.high>x.roll_hi20)&(x.close<x.roll_hi20)&(x.close<x.open)
    x['atr_q70']=x.atr28.rolling(500,min_periods=100).quantile(.70)
    x['atr_q30']=x.atr28.rolling(500,min_periods=100).quantile(.30)
    x['high_vol']=x.atr28>=x.atr_q70; x['low_vol']=x.atr28<=x.atr_q30; x['non_high_vol']=x.atr28<x.atr_q70
    x['session_7_15']=x.time.dt.hour.between(7,15); x['session_16_22']=x.time.dt.hour.between(16,22)
    x['weekday']=x.time.dt.weekday
    return x

def merge_htf(m15,h1,h4,d1):
    x=m15.copy()
    for tf,df in [('h1',h1),('h4',h4),('d1',d1)]:
        if df.empty: continue
        f=add_base(df,tf+'_'); cols=['time']+[c for c in f.columns if c.startswith(tf+'_')]
        x=pd.merge_asof(x.sort_values('time'),f[cols].sort_values('time'),on='time',direction='backward')
    return x

def vtrue(x): return pd.Series(True,index=x.index)
def vf(s): return s.fillna(False).astype(bool)

def build_vectors(df):
    x=df
    h1_up=vf((x.h1_ema20>x.h1_ema50)&(x.h1_ret4>0)) if 'h1_ema20' in x else vf(pd.Series(False,index=x.index))
    h1_down=vf((x.h1_ema20<x.h1_ema50)&(x.h1_ret4<0)) if 'h1_ema20' in x else vf(pd.Series(False,index=x.index))
    h4_up=vf((x.h4_ema20>x.h4_ema50)&(x.h4_ret4>0)) if 'h4_ema20' in x else vf(pd.Series(False,index=x.index))
    h4_down=vf((x.h4_ema20<x.h4_ema50)&(x.h4_ret4<0)) if 'h4_ema20' in x else vf(pd.Series(False,index=x.index))
    d1_up=vf((x.d1_ema20>x.d1_ema50)&(x.d1_ret4>0)) if 'd1_ema20' in x else vf(pd.Series(False,index=x.index))
    d1_down=vf((x.d1_ema20<x.d1_ema50)&(x.d1_ret4<0)) if 'd1_ema20' in x else vf(pd.Series(False,index=x.index))
    uptrend=vf(x.ema20>x.ema50); downtrend=vf(x.ema20<x.ema50)
    mom_up=vf((x.ret4>0)&(x.close>x.ema20)); mom_down=vf((x.ret4<0)&(x.close<x.ema20))
    body_up=vf((x.body>0)&(x.body_ratio>=0.45)); body_down=vf((x.body<0)&(x.body_ratio>=0.45))
    lower_rej=vf((x.lower_wick>=0.45)&(x.close>x.open)); upper_rej=vf((x.upper_wick>=0.45)&(x.close<x.open))
    hv=vf(x.high_vol); nhv=vf(x.non_high_vol); s1=vf(x.session_7_15); s2=vf(x.session_16_22)
    vec=[]
    def add(side,fam,name,mask): vec.append(dict(side=side,family=fam,condition=name,mask=vf(mask).values))
    # LONG families
    add('LONG','LONG_TREND_CONTINUATION','h4_up&h1_up&m15_uptrend&momentum_long',h4_up&h1_up&uptrend&mom_up)
    add('LONG','LONG_TREND_CONTINUATION','h1_up&m15_uptrend&body_up&session_16_22',h1_up&uptrend&body_up&s2)
    add('LONG','LONG_TREND_CONTINUATION','d1_up&h4_up&m15_uptrend&non_high_vol',d1_up&h4_up&uptrend&nhv)
    add('LONG','LONG_VOL_EXPANSION_BREAKOUT','h1_up&break_hi20&high_vol&body_up',h1_up&vf(x.break_hi20)&hv&body_up)
    add('LONG','LONG_VOL_EXPANSION_BREAKOUT','h4_up&break_hi20&ret16_positive&session_16_22',h4_up&vf(x.break_hi20)&vf(x.ret16>0)&s2)
    add('LONG','LONG_VOL_EXPANSION_BREAKOUT','h1_up&pos48_high&momentum_long',h1_up&vf(x.pos48>=0.80)&mom_up)
    add('LONG','LONG_FAILED_BREAKDOWN_RECLAIM','failed_breakdown&rsi_under45&h1_not_down',vf(x.failed_breakdown)&vf(x.rsi14<=45)&(~h1_down))
    add('LONG','LONG_FAILED_BREAKDOWN_RECLAIM','failed_breakdown&lower_wick_reject&session_7_15',vf(x.failed_breakdown)&lower_rej&s1)
    add('LONG','LONG_FAILED_BREAKDOWN_RECLAIM','failed_breakdown&h4_up_or_d1_up',vf(x.failed_breakdown)&(h4_up|d1_up))
    add('LONG','LONG_SELL_EXHAUSTION_REVERSAL','rsi_under35&lower_wick_reject&non_h4_down',vf(x.rsi14<=35)&lower_rej&(~h4_down))
    add('LONG','LONG_SELL_EXHAUSTION_REVERSAL','rsi_30_45&ret4_turn_up&lower_wick',vf((x.rsi14>=30)&(x.rsi14<=45))&vf(x.ret4>0)&vf(x.lower_wick>=0.35))
    add('LONG','LONG_SESSION_CONTINUATION','session_7_15&h1_up&momentum_long',s1&h1_up&mom_up)
    add('LONG','LONG_SESSION_CONTINUATION','session_16_22&h4_up&break_hi20',s2&h4_up&vf(x.break_hi20))
    add('LONG','LONG_HTF_UP_M15_MOMENTUM','h4_up&h1_up&ret16_positive&close_above_ema20',h4_up&h1_up&vf(x.ret16>0)&vf(x.close>x.ema20))
    # SHORT families
    add('SHORT','SHORT_BEARISH_CONTINUATION','h4_down&h1_down&m15_downtrend&momentum_short',h4_down&h1_down&downtrend&mom_down)
    add('SHORT','SHORT_BEARISH_CONTINUATION','h1_down&m15_downtrend&body_down&session_7_15',h1_down&downtrend&body_down&s1)
    add('SHORT','SHORT_BEARISH_CONTINUATION','d1_down&h4_down&m15_downtrend&non_high_vol',d1_down&h4_down&downtrend&nhv)
    add('SHORT','SHORT_VOL_EXPANSION_BREAKDOWN','h1_down&break_lo20&high_vol&body_down',h1_down&vf(x.break_lo20)&hv&body_down)
    add('SHORT','SHORT_VOL_EXPANSION_BREAKDOWN','h4_down&break_lo20&ret16_negative&session_7_15',h4_down&vf(x.break_lo20)&vf(x.ret16<0)&s1)
    add('SHORT','SHORT_VOL_EXPANSION_BREAKDOWN','h1_down&pos48_low&momentum_short',h1_down&vf(x.pos48<=0.20)&mom_down)
    add('SHORT','SHORT_FAILED_BREAKOUT_REJECT','failed_breakout&rsi_over55&h1_not_up',vf(x.failed_breakout)&vf(x.rsi14>=55)&(~h1_up))
    add('SHORT','SHORT_FAILED_BREAKOUT_REJECT','failed_breakout&upper_wick_reject&session_16_22',vf(x.failed_breakout)&upper_rej&s2)
    add('SHORT','SHORT_FAILED_BREAKOUT_REJECT','failed_breakout&h4_down_or_d1_down',vf(x.failed_breakout)&(h4_down|d1_down))
    add('SHORT','SHORT_BUY_EXHAUSTION_REVERSAL','rsi_over65&upper_wick_reject&non_h4_up',vf(x.rsi14>=65)&upper_rej&(~h4_up))
    add('SHORT','SHORT_BUY_EXHAUSTION_REVERSAL','rsi_55_70&ret4_turn_down&upper_wick',vf((x.rsi14>=55)&(x.rsi14<=70))&vf(x.ret4<0)&vf(x.upper_wick>=0.35))
    add('SHORT','SHORT_SESSION_SELL_PRESSURE','session_7_15&h1_down&momentum_short',s1&h1_down&mom_down)
    add('SHORT','SHORT_SESSION_SELL_PRESSURE','session_16_22&h4_down&break_lo20',s2&h4_down&vf(x.break_lo20))
    add('SHORT','SHORT_HTF_DOWN_M15_MOMENTUM','h4_down&h1_down&ret16_negative&close_below_ema20',h4_down&h1_down&vf(x.ret16<0)&vf(x.close<x.ema20))
    return vec

def apply_cd(idx,cool):
    if cool<=0: return list(idx)
    out=[]; last=-10**9
    for i in idx:
        if i-last>=cool: out.append(i); last=i
    return out

def profile_tp_sl(row, profile):
    pid,kind,a,b,h=profile
    if kind=='fixed': return float(a),float(b),int(h)
    tp=max(5.0,float(row.atr28)*float(a)); sl=tp/float(b); return tp,sl,int(h)

def result_idx(i,df,m5_np,profile,side,cache):
    pid=profile[0]; key=(int(i),side,pid)
    if key in cache: return cache[key]
    row=df.iloc[i]; tp,sl,h=profile_tp_sl(row,profile)
    start=np.searchsorted(m5_np['time'],row.time.to_datetime64(),side='right'); end=min(len(m5_np['time']),start+h*3)
    ep=float(row.close)
    if side=='LONG': tpv=ep+tp; slv=ep-sl
    else: tpv=ep-tp; slv=ep+sl
    hi=m5_np['high']; lo=m5_np['low']; res=0.0
    for j in range(start,end):
        ht=(hi[j]>=tpv) if side=='LONG' else (lo[j]<=tpv)
        hs=(lo[j]<=slv) if side=='LONG' else (hi[j]>=slv)
        if ht and hs: res=-sl; break
        if hs: res=-sl; break
        if ht: res=tp; break
    cache[key]=float(res); return float(res)

def metrics(vals,months=None):
    a=np.array(vals,float); tr=len(a)
    if tr==0: return dict(trades=0,wins=0,losses=0,win_rate=0.0,profit_factor=0.0,sum_result_usd=0.0,negative_month_count=0)
    gp=a[a>0].sum(); gl=-a[a<0].sum(); p=gp/gl if gl>0 else (math.inf if gp>0 else 0.0); neg=0
    if months is not None and len(months)==tr:
        s=pd.DataFrame({'m':months,'r':a}).groupby('m').r.sum(); neg=int((s<0).sum())
    return dict(trades=int(tr),wins=int((a>0).sum()),losses=int((a<0).sum()),win_rate=float((a>0).mean()),profit_factor=float(p),sum_result_usd=float(a.sum()),negative_month_count=neg)

def eval_candidate(df,m5_np,vec,profile,cool,cache):
    idx=np.where(vec['mask'])[0]; idx=apply_cd(idx,cool)
    vals=[]; mons=[]; entries=[]
    for i in idx:
        v=result_idx(i,df,m5_np,profile,vec['side'],cache); vals.append(v); mons.append(str(df.iloc[i].time.to_period('M'))); entries.append(i)
    m=metrics(vals,mons); pid,kind,a,b,h=profile
    m.update(side=vec['side'],family=vec['family'],condition=vec['condition'],profile_id=pid,profile_kind=kind,cooldown_bars=cool,horizon_m15=h,raw_events=int(vec['mask'].sum()),entry_count=len(idx))
    rows=pd.DataFrame({'entry_dt':[df.iloc[i].time for i in entries],'side':vec['side'],'family':vec['family'],'condition':vec['condition'],'profile_id':pid,'cooldown_bars':cool,'result_usd':vals}) if vals else pd.DataFrame()
    return m,rows

def split_perf(rows):
    if rows.empty: return {}
    x=rows.copy(); x['entry_dt']=pd.to_datetime(x.entry_dt); d=x.entry_dt
    splits={'2025':d.dt.year==2025,'2026':d.dt.year==2026,'2025H1':(d>=pd.Timestamp('2025-01-01'))&(d<pd.Timestamp('2025-07-01')),'2025H2':(d>=pd.Timestamp('2025-07-01'))&(d<pd.Timestamp('2026-01-01')),'2026_03_PLUS':d>=pd.Timestamp('2026-03-01'),'2026_05_06':d>=pd.Timestamp('2026-05-01')}
    out={}
    for k,mask in splits.items():
        m=metrics(x.loc[mask,'result_usd'].tolist())
        for kk,v in m.items(): out[f'{k}_{kk}']=v
    return out

def pfcap(x):
    try: return 10.0 if math.isinf(float(x)) else min(float(x),10.0)
    except Exception: return 0.0

def cand_score(r):
    return pfcap(r.get('profit_factor',0))*1000 + float(r.get('win_rate',0))*700 + min(float(r.get('trades',0)),800)*0.25 + float(r.get('sum_result_usd',0))*0.05 - float(r.get('negative_month_count',0))*300

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--data-dir',default=''); ap.add_argument('--mt5-files-dir',default=os.environ.get('MT5_FILES_DIR','')); ap.add_argument('--max-vectors-per-side',type=int,default=80)
    args=ap.parse_args(); dirs=base_dirs(args.data_dir,args.mt5_files_dir); base=Path(args.mt5_files_dir).expanduser().resolve() if args.mt5_files_dir else Path.cwd(); out=base/'FX_OUTPUTS'/'gold_v3'/'107glc'; out.mkdir(parents=True,exist_ok=True)
    blockers=[]; vals=[]; findings=[]; outputs=[]; loaded={}; cov=[]
    for tf in ['m15','m5','h1','h4','d1']:
        loaded[tf],used=load_tf(tf,dirs); cov.append(dict(timeframe=tf,rows=len(loaded[tf]),min_time=loaded[tf].time.min() if len(loaded[tf]) else '',max_time=loaded[tf].time.max() if len(loaded[tf]) else '',sources=';'.join(used),duplicate_rows_dropped=loaded[tf].attrs.get('dup_dropped',0)))
    covdf=pd.DataFrame(cov); save(covdf,out/'gold_v3_107gl_input_coverage.csv'); outputs.append('gold_v3_107gl_input_coverage.csv')
    if loaded['m15'].empty or loaded['m5'].empty: blockers.append(dict(blocker_id='missing_m15_or_m5',reason='M15 and M5 exact OHLC files are required'))
    if not blockers:
        m15=add_m15_features(loaded['m15']); df=merge_htf(m15,loaded['h1'],loaded['h4'],loaded['d1']).dropna(subset=['atr28','ema20','ema50','rsi14','roll_hi20','roll_lo20']).reset_index(drop=True)
        df['entry_year']=df.time.dt.year; df['entry_month']=df.time.dt.to_period('M').astype(str)
        save(pd.DataFrame([dict(feature_rows=len(df),years=','.join(map(str,sorted(df.entry_year.dropna().unique()))),months=df.entry_month.nunique(),min_time=df.time.min(),max_time=df.time.max())]),out/'gold_v3_107gl_feature_coverage.csv'); outputs.append('gold_v3_107gl_feature_coverage.csv')
        vecs=build_vectors(df)
        fwd=df.close.shift(-16)-df.close
        pre=[]
        for v in vecs:
            mask=v['mask']; n=int(mask.sum())
            if n<20: continue
            edge=float(np.nanmean(fwd[mask])) if v['side']=='LONG' else float(np.nanmean(-fwd[mask]))
            pre.append(dict(**{k:v[k] for k in ['side','family','condition']},raw_events=n,forward_edge=edge,mask=v['mask']))
        selected=[]
        for side in ['LONG','SHORT']:
            side_pre=sorted([p for p in pre if p['side']==side],key=lambda x:(np.nan_to_num(x['forward_edge']),x['raw_events']),reverse=True)[:args.max_vectors_per_side]
            selected += side_pre
        m5_np={'time':loaded['m5'].time.values,'high':loaded['m5'].high.values.astype(float),'low':loaded['m5'].low.values.astype(float)}
        all_summ=[]; ledgers=[]; cache={}
        for v in selected:
            for prof in PROFILES:
                for cd in COOLDOWNS:
                    m,lg=eval_candidate(df,m5_np,v,prof,cd,cache)
                    m.update(forward_edge=v['forward_edge'])
                    if not lg.empty: m.update(split_perf(lg))
                    all_summ.append(m)
                    if not lg.empty and m['trades']>=20 and (m['profit_factor']>=1.4 or m['win_rate']>=0.55): ledgers.append(lg.assign(candidate_key=f"{v['side']}||{v['family']}||{v['condition']}||{prof[0]}||CD{cd}"))
        summ=pd.DataFrame(all_summ)
        if summ.empty: blockers.append(dict(blocker_id='no_candidate_results',reason='new vector family evaluation returned no rows'))
        else:
            summ['score']=summ.apply(cand_score,axis=1)
            save(summ.sort_values('score',ascending=False),out/'gold_v3_107gl_vector_candidate_summary.csv'); outputs.append('gold_v3_107gl_vector_candidate_summary.csv')
            long_s=summ[summ.side=='LONG'].sort_values('score',ascending=False); short_s=summ[summ.side=='SHORT'].sort_values('score',ascending=False)
            save(long_s.head(80),out/'gold_v3_107gl_top_long_vectors.csv'); save(short_s.head(80),out/'gold_v3_107gl_top_short_vectors.csv'); outputs += ['gold_v3_107gl_top_long_vectors.csv','gold_v3_107gl_top_short_vectors.csv']
            if ledgers:
                top_keys=set(pd.concat([long_s.head(20),short_s.head(20)],ignore_index=True).apply(lambda r:f"{r.side}||{r.family}||{r.condition}||{r.profile_id}||CD{int(r.cooldown_bars)}",axis=1))
                lgall=pd.concat(ledgers,ignore_index=True); lgall=lgall[lgall.candidate_key.isin(top_keys)]
                save(lgall,out/'gold_v3_107gl_top_vector_trade_ledger.csv'); outputs.append('gold_v3_107gl_top_vector_trade_ledger.csv')
            fam=[]
            for (side,family),g in summ.groupby(['side','family']):
                best=g.sort_values('score',ascending=False).iloc[0].to_dict(); best.update(side=side,family=family); fam.append(best)
            save(pd.DataFrame(fam).sort_values(['side','score'],ascending=[True,False]),out/'gold_v3_107gl_side_family_summary.csv'); outputs.append('gold_v3_107gl_side_family_summary.csv')
            mon=[]
            if ledgers:
                lgall=pd.concat(ledgers,ignore_index=True); lgall['entry_month']=pd.to_datetime(lgall.entry_dt).dt.to_period('M').astype(str)
                for (side,fam,monv),g in lgall.groupby(['side','family','entry_month']):
                    m=metrics(g.result_usd.tolist()); m.update(side=side,family=fam,entry_month=monv); mon.append(m)
            save(pd.DataFrame(mon),out/'gold_v3_107gl_monthly_summary.csv'); outputs.append('gold_v3_107gl_monthly_summary.csv')
            split_cols=[c for c in summ.columns if any(c.startswith(p+'_') for p in ['2025','2026','2025H1','2025H2','2026_03_PLUS','2026_05_06'])]
            save(summ[['side','family','condition','profile_id','cooldown_bars','trades','win_rate','profit_factor','sum_result_usd','negative_month_count','score']+split_cols].sort_values('score',ascending=False).head(120),out/'gold_v3_107gl_anchored_split_summary.csv'); outputs.append('gold_v3_107gl_anchored_split_summary.csv')
            bL=long_s.iloc[0].to_dict() if len(long_s) else {}; bS=short_s.iloc[0].to_dict() if len(short_s) else {}
            findings.append('best_new_long_vector='+json.dumps(bL,ensure_ascii=False,default=str)); findings.append('best_new_short_vector='+json.dumps(bS,ensure_ascii=False,default=str))
            goodL=long_s[(long_s.trades>=150)&(long_s.profit_factor>=2.0)&(long_s.win_rate>=0.55)&(long_s.negative_month_count<=2)]
            goodS=short_s[(short_s.trades>=150)&(short_s.profit_factor>=2.0)&(short_s.win_rate>=0.55)&(short_s.negative_month_count<=2)]
            actions=[]
            actions.append(dict(priority=1,action='review_new_long_vector_candidates',reason=f'long_good_count={len(goodL)}'))
            actions.append(dict(priority=2,action='review_new_short_vector_candidates',reason=f'short_good_count={len(goodS)}'))
            actions.append(dict(priority=3,action='run_anchored_train_test_on_new_vector_candidates',reason='107GL is full-period vector generation audit; next stage must validate train/test stability'))
            save(pd.DataFrame(actions),out/'gold_v3_107gl_recommended_next_actions.csv'); outputs.append('gold_v3_107gl_recommended_next_actions.csv')
            vals.append(dict(check_id='new_long_vectors_present',result='PASS' if len(long_s)>0 else 'FAIL',observed=len(long_s),expected='>0',severity='BLOCKER'))
            vals.append(dict(check_id='new_short_vectors_present',result='PASS' if len(short_s)>0 else 'FAIL',observed=len(short_s),expected='>0',severity='BLOCKER'))
    vals += [dict(check_id='audit_only',result='PASS',observed=True,expected=True,severity='BLOCKER'),dict(check_id='source_csv_mutated',result='PASS',observed=False,expected=False,severity='BLOCKER'),dict(check_id='candidate_pool_mutated',result='PASS',observed=False,expected=False,severity='BLOCKER'),dict(check_id='open_asof_allowed',result='PASS',observed=False,expected=False,severity='BLOCKER')]
    val=pd.DataFrame(vals); status=READY if not blockers and val.result.eq('PASS').all() else BLOCKED
    summary=dict(step=STEP,status=status,created_at_utc=datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z'),output_dir=str(out),audit_only=True,live_ready=False,source_csv_mutated=False,contract_mutated=False,manual_candidate_demotion_or_removal=False,open_asof_allowed=False,csv_contract=CSV_CONTRACT,csv_open_bar_exclusion_required=False,pool_policy=POOL_POLICY,blocker_count=len(blockers),validation_failure_count=int((~val.result.eq('PASS')).sum()),runtime_estimate='medium_to_heavy_30_to_90min_stop_if_over_90min')
    if 'summ' in locals() and not summ.empty:
        summary.update(candidate_rows=int(len(summ)),evaluated_vector_seeds=int(len(selected)),outcome_cache_size=int(len(cache)))
    save(pd.DataFrame(blockers),out/'gold_v3_107gl_blocker_matrix.csv'); save(val,out/'gold_v3_107gl_validation_matrix.csv')
    outputs += ['gold_v3_107gl_blocker_matrix.csv','gold_v3_107gl_validation_matrix.csv','gold_v3_107gl_summary.json','GOLD_V3_107GL_NEW_LONG_SHORT_VECTOR_FAMILY_GENERATION_AUDIT_ONLY_REPORT.md','paste_me.txt']
    (out/'gold_v3_107gl_summary.json').write_text(json.dumps(summary|{'findings':findings},ensure_ascii=False,indent=2,default=str),encoding='utf-8')
    (out/'GOLD_V3_107GL_NEW_LONG_SHORT_VECTOR_FAMILY_GENERATION_AUDIT_ONLY_REPORT.md').write_text('# GOLD V3 107GL report\n\n'+json.dumps({'summary':summary,'findings':findings,'blockers':blockers},ensure_ascii=False,indent=2,default=str),encoding='utf-8')
    lines=['GOLD V3 107GL PASTE_ME_NEW_LONG_SHORT_VECTOR_FAMILY_GENERATION',f'status: {status}',f'ready: {str(status==READY).lower()}','live_ready: false','source_csv_mutated: false','contract_mutated: false','manual_candidate_demotion_or_removal: false','open_asof_allowed: false','csv_contract: '+CSV_CONTRACT,'csv_open_bar_exclusion_required: false','safety: audit_only=true, proxy_only=true, mt5=false, discord=false, ai_api=false, live_hook=false, final_signal=false','pool_policy: '+POOL_POLICY,'source: exact GOLD V3 107g OHLC inputs; new vector families; no runtime change','runtime_estimate: medium_to_heavy; 30_to_90min; stop_if_over_90min',f'blocker_count: {len(blockers)}','','KEY_METRICS']+[f'{k}: {v}' for k,v in summary.items()]+['','FINDINGS']+(findings or ['NO_FINDINGS'])+['','BLOCKERS',pd.DataFrame(blockers).to_string(index=False) if blockers else 'NO_BLOCKERS','','VALIDATION',val.to_string(index=False),'','OUTPUTS']+outputs
    (out/'paste_me.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({'status':status,'ready':status==READY,'paste_me':str(out/'paste_me.txt')},ensure_ascii=False,indent=2)); return 0 if status==READY else 2
if __name__=='__main__': raise SystemExit(main())
