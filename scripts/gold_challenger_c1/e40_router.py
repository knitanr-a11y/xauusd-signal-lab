from __future__ import annotations
from dataclasses import dataclass
import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier
from .contracts import SEED,FIXED_SPREAD,SPREAD_GATE_POINTS,E40_TARGET,E40_STOP,E40_HORIZON
from .exact_m1_execution import contiguous_forward, resolve_many

CTX_SUFFIX=["atr14","ret3_atr","ret10_atr","eff5","close_loc","atr_ratio14_50","dist_ema20_atr","ema20_slope4_atr","compression10_atr","vol_ratio20"]

def atr14_ewm(frame):
 h=frame.high.to_numpy(float);l=frame.low.to_numpy(float);c=frame.close.to_numpy(float);tr=np.empty(len(frame));tr[0]=h[0]-l[0];tr[1:]=np.maximum.reduce([h[1:]-l[1:],np.abs(h[1:]-c[:-1]),np.abs(l[1:]-c[:-1])]);return pd.Series(tr).ewm(alpha=1/14,adjust=False,min_periods=14).mean()

def lean_features(frame,prefix,delta):
 atr=atr14_ewm(frame); rng=(frame.high-frame.low).replace(0,np.nan); body=frame.close-frame.open; out=pd.DataFrame({'time_key':frame.time+delta})
 def put(n,v): out[f'{prefix}_{n}']=np.asarray(v,dtype=np.float32)
 put('atr14',atr);put('body_atr',body/atr);put('range_atr',rng/atr);put('body_ratio',body.abs()/rng);put('close_loc',(frame.close-frame.low)/rng);put('upper_wick_atr',(frame.high-frame[['open','close']].max(axis=1))/atr);put('lower_wick_atr',(frame[['open','close']].min(axis=1)-frame.low)/atr);put('vol_ratio20',frame.tick_volume/frame.tick_volume.rolling(20,min_periods=20).median());put('vol_ratio5_20',frame.tick_volume.rolling(5,min_periods=5).mean()/frame.tick_volume.rolling(20,min_periods=20).mean());put('atr_ratio14_50',atr/atr.rolling(50,min_periods=50).median());put('range_ratio20',rng/rng.rolling(20,min_periods=20).median())
 for n in [1,3,5,10,20]: put(f'ret{n}_atr',(frame.close-frame.close.shift(n))/atr)
 ad=frame.close.diff().abs()
 for n in [3,5,10]: put(f'eff{n}',(frame.close-frame.close.shift(n)).abs()/ad.rolling(n,min_periods=n).sum().replace(0,np.nan))
 for n in [5,10]:
  ph=frame.high.shift(1).rolling(n,min_periods=n).max();pl=frame.low.shift(1).rolling(n,min_periods=n).min();put(f'dist_prior{n}_high_atr',(frame.close-ph)/atr);put(f'dist_prior{n}_low_atr',(frame.close-pl)/atr);put(f'compression{n}_atr',(ph-pl)/atr)
 for n in [20,50,200]:
  ema=frame.close.ewm(span=n,adjust=False,min_periods=n).mean();put(f'dist_ema{n}_atr',(frame.close-ema)/atr)
  if n<200: put(f'ema{n}_slope4_atr',(ema-ema.shift(4))/atr)
 sign=np.sign(body);put('signed_run3',sign.rolling(3,min_periods=3).sum()/3);put('signed_run5',sign.rolling(5,min_periods=5).sum()/5)
 dm=frame.time.diff().dt.total_seconds()/60; restart=dm.gt(30);restart.iloc[0]=True;last=frame.time.where(restart).ffill();put('minutes_since_restart',(frame.time-last).dt.total_seconds()/60)
 return out

def ctx_cols(prefix): return [f'{prefix}_{s}' for s in CTX_SUFFIX]

def build_feature_frame(data):
 m1=data['M1'].copy(); feats={'M1':lean_features(m1,'m1',pd.Timedelta(minutes=1))}
 for tf,delta in [('M5',pd.Timedelta(minutes=5)),('M15',pd.Timedelta(minutes=15)),('H1',pd.Timedelta(hours=1)),('H4',pd.Timedelta(hours=4))]: feats[tf]=lean_features(data[tf],tf.lower(),delta)
 own=feats['M15'].rename(columns={'time_key':'decision_time'}).copy()
 for tf in ['M1','M5','H1','H4']:
  prefix=tf.lower(); own=pd.merge_asof(own.sort_values('decision_time'),feats[tf][['time_key']+ctx_cols(prefix)].sort_values('time_key'),left_on='decision_time',right_on='time_key',direction='backward').drop(columns='time_key')
 idx=pd.Index(m1.time);own['entry_idx']=idx.get_indexer(pd.DatetimeIndex(own.decision_time));own=own[own.entry_idx>=0].copy();ii=own.entry_idx.to_numpy(int);own['entry_time']=m1.time.to_numpy()[ii];own['entry_spread_points']=m1.spread.to_numpy(float)[ii];own=own[own.entry_spread_points<=SPREAD_GATE_POINTS].reset_index(drop=True);own['origin_id']=np.arange(len(own),dtype=int);et=pd.DatetimeIndex(own.entry_time);own['month']=et.to_period('M').astype(str);own['year']=et.year;own['hour_sin']=np.sin(2*np.pi*et.hour/24).astype(np.float32);own['hour_cos']=np.cos(2*np.pi*et.hour/24).astype(np.float32);own['dow_sin']=np.sin(2*np.pi*et.dayofweek/7).astype(np.float32);own['dow_cos']=np.cos(2*np.pi*et.dayofweek/7).astype(np.float32)
 return own,m1

def feature_columns(frame):
 ex={'decision_time','entry_time','entry_idx','entry_spread_points','year','month','origin_id','e40_out_long','e40_out_short','e40_y_long','e40_y_short'}
 return [c for c in frame if c not in ex and pd.api.types.is_numeric_dtype(frame[c])]

def cap_idx(y,max_n=80000):
 if len(y)<=max_n:return np.arange(len(y))
 rng=np.random.default_rng(60731);pos=np.flatnonzero(y==1);neg=np.flatnonzero(y==0);np_=min(len(pos),max_n//2);nn=min(len(neg),max_n-np_);np_=min(len(pos),max_n-nn);sel=np.r_[rng.choice(pos,np_,False),rng.choice(neg,nn,False)];rng.shuffle(sel);return sel

def fit_tree(x,y):
 sel=cap_idx(y);m=LGBMClassifier(n_estimators=50,learning_rate=.08,num_leaves=15,min_child_samples=300,subsample=.8,colsample_bytree=.72,reg_lambda=7,reg_alpha=1,class_weight='balanced',random_state=60731,n_jobs=8,verbosity=-1);m.fit(x[sel],y[sel]);return m

def causal_session_guard(rows,m1,weekday_offset=1378,friday_offset=1377):
 if rows.empty:return rows.copy()
 gaps=m1.time.diff().dt.total_seconds().div(60).fillna(999999);sid=gaps.gt(1).cumsum();starts=m1.groupby(sid).time.transform('min');ii=rows.entry_idx.to_numpy(np.int64);st=pd.DatetimeIndex(starts.iloc[ii]);off=np.where(st.dayofweek==4,friday_offset,weekday_offset);end=st+pd.to_timedelta(off,unit='m');mask=end-pd.DatetimeIndex(rows.entry_time)>=pd.Timedelta(minutes=E40_HORIZON);return rows.loc[np.asarray(mask)].copy()

@dataclass
class RouterResult:
 ledger: pd.DataFrame
 origins: pd.DataFrame
 model_metadata: list[dict]

def _rank_day(current,history,cal):
 day=pd.DatetimeIndex(current.entry_time).normalize()[0];start=day-pd.Timedelta(days=60);h=pd.concat([cal[['entry_time','score_long','score_short']],history[['entry_time','score_long','score_short']]],ignore_index=True);hd=pd.DatetimeIndex(h.entry_time).normalize();h=h[(hd<day)&(hd>=start)]
 r=current.copy()
 for side in ['long','short']:
  vals=np.sort(h[f'score_{side}'].dropna().to_numpy(float))
  if len(vals)<100:vals=np.sort(cal[f'score_{side}'].dropna().to_numpy(float))
  r[f'rank_{side}']=np.searchsorted(vals,r[f'score_{side}'].to_numpy(float),side='right')/max(1,len(vals))
 r['chosen_side']=np.where(r.rank_long>=r.rank_short,'LONG','SHORT');r['chosen_rank']=np.maximum(r.rank_long,r.rank_short);return r

def build_semiannual_ledger(data,boundaries=None):
 own,m1=build_feature_frame(data);contig=contiguous_forward(m1.time.to_numpy('datetime64[ns]').astype(np.int64));idx=own.entry_idx.to_numpy(np.int64);ones=np.ones(len(idx),np.int8);minus=-ones
 lp,le,lr=resolve_many(m1.open.to_numpy(float),m1.high.to_numpy(float),m1.low.to_numpy(float),contig,idx,ones,E40_TARGET,E40_STOP,E40_HORIZON,FIXED_SPREAD);sp,se,sr=resolve_many(m1.open.to_numpy(float),m1.high.to_numpy(float),m1.low.to_numpy(float),contig,idx,minus,E40_TARGET,E40_STOP,E40_HORIZON,FIXED_SPREAD)
 labeled=own.copy();labeled['e40_out_long']=lr;labeled['e40_out_short']=sr;labeled['e40_y_long']=(lr==1).astype(np.int8);labeled['e40_y_short']=(sr==1).astype(np.int8);labeled=labeled[(lr!=9)&(sr!=9)].reset_index(drop=True)
 cols=feature_columns(labeled);X=labeled[cols].to_numpy(np.float32);times=pd.DatetimeIndex(labeled.entry_time)
 if boundaries is None: boundaries=[pd.Timestamp('2024-07-01'),pd.Timestamp('2025-01-01'),pd.Timestamp('2025-07-01'),pd.Timestamp('2026-01-01'),pd.Timestamp('2026-07-01')]
 max_time=pd.Timestamp(own.entry_time.max())+pd.Timedelta(minutes=1);parts=[];meta=[]
 for bi,b in enumerate(boundaries):
  nxt=boundaries[bi+1] if bi+1<len(boundaries) else max_time;cal_start=b-pd.DateOffset(months=6);train_end=cal_start;train=(times>=pd.Timestamp('2023-01-01'))&(times<train_end-pd.Timedelta(minutes=E40_HORIZON));calmask=(times>=cal_start)&(times<b)
  lm=fit_tree(X[train],labeled.e40_y_long.to_numpy(np.int8)[train]);sm=fit_tree(X[train],labeled.e40_y_short.to_numpy(np.int8)[train]);cal=labeled.loc[calmask,['entry_time','origin_id']].copy();cal['score_long']=lm.predict_proba(X[calmask])[:,1];cal['score_short']=sm.predict_proba(X[calmask])[:,1]
  test=own[(own.entry_time>=b)&(own.entry_time<nxt)].copy();test=causal_session_guard(test,m1);Xt=test[cols].to_numpy(np.float32);sc=test[['origin_id','entry_time','entry_idx','entry_spread_points','m15_atr14']].copy();sc['score_long']=lm.predict_proba(Xt)[:,1];sc['score_short']=sm.predict_proba(Xt)[:,1];history=pd.DataFrame(columns=['entry_time','score_long','score_short']);daily=[]
  for day,g in sc.groupby(pd.DatetimeIndex(sc.entry_time).normalize(),sort=True):
   rr=_rank_day(g,history,cal);daily.append(rr);history=pd.concat([history,g[['entry_time','score_long','score_short']]],ignore_index=True)
  fold=pd.concat(daily,ignore_index=True) if daily else sc.assign(rank_long=np.nan,rank_short=np.nan,chosen_side='',chosen_rank=np.nan)
  fold['schedule']='SEMIANNUAL_EXPANDING';fold['fold_id']=['F1_2024H2','F2_2025H1','F3_2025H2','F4_2026H1','F5_2026JUL'][bi];fold['period']=['2024H2','2025H1','2025H2','2026H1','2026JUL'][bi];parts.append(fold)
  meta.append({'boundary':str(b),'test_end':str(nxt),'train_n':int(train.sum()),'calibration_n':int(calmask.sum()),'test_n':len(fold),'feature_count':len(cols),'train_cutoff':str(train_end-pd.Timedelta(minutes=E40_HORIZON)),'calibration_start':str(cal_start),'calibration_end':str(b)})
 return RouterResult(pd.concat(parts,ignore_index=True).sort_values(['entry_time','origin_id']).reset_index(drop=True),own,meta)

def update_masks(decision_times,boundary):
    boundary=pd.Timestamp(boundary);cal_start=boundary-pd.DateOffset(months=6);dt=pd.DatetimeIndex(decision_times)
    train=(dt>=pd.Timestamp('2023-01-01'))&(dt<cal_start-pd.Timedelta(minutes=E40_HORIZON));cal=(dt>=cal_start)&(dt<boundary)
    return train,cal
