#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Shared closed-candle IO and indicator primitives for Stage289."""
from __future__ import annotations
import base64,gzip
from collections import deque
from io import StringIO
from pathlib import Path
from typing import Iterable
import lightgbm as lgb
import numpy as np
import pandas as pd

TF_MINUTES={"M1":1,"M5":5,"M15":15,"H1":60,"H4":240,"D1":1440}
GOLD_FILES={"M1":"goldsharp_m1.csv","M5":"goldsharp_m5.csv","M15":"goldsharp_m15.csv","H1":"goldsharp_h1.csv","H4":"goldsharp_h4.csv","D1":"goldsharp_d1.csv"}
EXTERNAL_FILES={"SP_M15":"us500cashsharp_m15.csv","NQ_M15":"us100cashsharp_m15.csv"}
LIVE_TAIL_ROWS={"M1":30000,"M5":12000,"M15":6000,"H1":3000,"H4":1500,"D1":600}

def read_candles(path:Path,tail_rows:int|None=None)->pd.DataFrame:
 if tail_rows and tail_rows>0:
  with path.open("r",encoding="utf-8-sig",errors="replace") as fh:
   header=fh.readline(); lines=deque(fh,maxlen=int(tail_rows))
  df=pd.read_csv(StringIO(header+"".join(lines)))
 else: df=pd.read_csv(path,encoding="utf-8-sig")
 df.columns=[str(c).strip().lower() for c in df.columns]
 df=df.rename(columns={"datetime":"time","date":"time","timestamp":"time","volume":"tick_volume","tickvolume":"tick_volume"})
 req=["time","open","high","low","close"]
 missing=[c for c in req if c not in df.columns]
 if missing: raise ValueError(f"{path}: missing columns {missing}; columns={list(df.columns)}")
 df["time"]=pd.to_datetime(df["time"],errors="coerce")
 for c in ["open","high","low","close","tick_volume","spread","real_volume"]:
  if c in df.columns: df[c]=pd.to_numeric(df[c],errors="coerce")
 if "tick_volume" not in df.columns: df["tick_volume"]=0.0
 if "spread" not in df.columns: df["spread"]=0.0
 return df.dropna(subset=req).sort_values("time").drop_duplicates("time",keep="last").reset_index(drop=True)

def add_indicators(df:pd.DataFrame,wins:Iterable[int])->pd.DataFrame:
 x=df.copy(); prev=x.close.shift(1)
 tr=pd.concat([(x.high-x.low).abs(),(x.high-prev).abs(),(x.low-prev).abs()],axis=1).max(axis=1)
 x["atr14"]=tr.ewm(alpha=1/14,adjust=False,min_periods=14).mean(); x["atr50"]=tr.ewm(alpha=1/50,adjust=False,min_periods=50).mean(); x["atr_ratio"]=x.atr14/x.atr50
 for n in [8,20,50,200]:
  x[f"ema{n}"]=x.close.ewm(span=n,adjust=False,min_periods=n).mean(); x[f"dist_ema{n}_atr"]=(x.close-x[f"ema{n}"])/x.atr14
 x["ema20_slope6_atr"]=(x.ema20-x.ema20.shift(6))/x.atr14; x["ema50_slope12_atr"]=(x.ema50-x.ema50.shift(12))/x.atr14
 rng=(x.high-x.low).replace(0,np.nan)
 x["body_signed"]=(x.close-x.open)/rng; x["body_ratio"]=(x.close-x.open).abs()/rng
 x["upper_wick_ratio"]=(x.high-x[["open","close"]].max(axis=1))/rng; x["lower_wick_ratio"]=(x[["open","close"]].min(axis=1)-x.low)/rng
 x["range_atr"]=rng/x.atr14; x["vol_ratio20"]=x.tick_volume/x.tick_volume.rolling(20).mean(); x["spread_usd"]=x.spread*.01; x["spread_ratio20"]=x.spread/x.spread.rolling(20).median().replace(0,np.nan)
 delta=x.close.diff().abs()
 for n in wins:
  hi=x.high.rolling(n).max(); lo=x.low.rolling(n).min()
  x[f"ret{n}_atr"]=(x.close-x.close.shift(n))/x.atr14; x[f"range{n}_atr"]=(hi-lo)/x.atr14; x[f"pos{n}"]=(x.close-lo)/(hi-lo).replace(0,np.nan); x[f"eff{n}"]=(x.close-x.close.shift(n)).abs()/delta.rolling(n).sum().replace(0,np.nan); x[f"volratio{n}"]=x.tick_volume.rolling(n).mean()/x.tick_volume.rolling(n).mean().shift(n); x[f"spreadmax{n}_usd"]=x.spread.rolling(n).max()*.01
 return x

def merge_closed(base:pd.DataFrame,src:pd.DataFrame,prefix:str,minutes:int,cols:list[str])->pd.DataFrame:
 s=src[["time"]+cols].copy(); s["available_time"]=s.time+pd.Timedelta(minutes=minutes); s=s.drop(columns="time").rename(columns={c:f"{prefix}_{c}" for c in cols})
 return pd.merge_asof(base.sort_values("time"),s.sort_values("available_time"),left_on="time",right_on="available_time",direction="backward").drop(columns="available_time")

def decision_times(raw:pd.DataFrame,minutes:int,include_next:bool)->pd.DataFrame:
 times=raw[["time"]].copy()
 if include_next and len(raw):
  nxt=pd.Timestamp(raw.time.max())+pd.Timedelta(minutes=minutes)
  if nxt not in set(times.time): times=pd.concat([times,pd.DataFrame({"time":[nxt]})],ignore_index=True)
 return times.sort_values("time").drop_duplicates("time").reset_index(drop=True)

def m1_arrays(m1:pd.DataFrame):
 return m1.time.to_numpy("datetime64[ns]"),m1.open.to_numpy(float),m1.high.to_numpy(float),m1.low.to_numpy(float),m1.close.to_numpy(float),m1.tick_volume.to_numpy(float),m1.spread.to_numpy(float)*.01

def load_gold(candle_dir:Path,tail_only:bool=True)->dict[str,pd.DataFrame]:
 return {tf:read_candles(candle_dir/name,LIVE_TAIL_ROWS[tf] if tail_only else None) for tf,name in GOLD_FILES.items()}

def load_booster(path:Path)->lgb.Booster:
 if path.name.endswith(".txt.gz.b64"):
  if path.exists(): text=path.read_text(encoding="ascii")
  else: text="".join(p.read_text(encoding="ascii") for p in sorted(path.parent.glob(path.name+".part*")))
  return lgb.Booster(model_str=gzip.decompress(base64.b64decode(text)).decode("utf-8"))
 return lgb.Booster(model_file=str(path))
