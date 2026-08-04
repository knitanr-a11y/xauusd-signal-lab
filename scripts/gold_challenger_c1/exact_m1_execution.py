from __future__ import annotations
import numpy as np
import pandas as pd
from numba import njit
from .contracts import FIXED_SPREAD, T20_TARGET, T20_STOP, T20_HORIZON

@njit(cache=True)
def contiguous_forward(times_ns: np.ndarray) -> np.ndarray:
    n=len(times_ns); out=np.ones(n,np.int32); minute=60_000_000_000
    for i in range(n-2,-1,-1): out[i]=out[i+1]+1 if times_ns[i+1]-times_ns[i]==minute else 1
    return out

@njit(cache=True)
def resolve_many(open_,high,low,contig,indices,sides,target,stop,horizon,spread):
    n=len(indices); pnl=np.full(n,np.nan); exits=np.full(n,-1,np.int64); reasons=np.full(n,9,np.int8)
    for row in range(n):
        i=indices[row]
        if i<0 or i+horizon>=len(open_) or contig[i]<horizon+1: continue
        if sides[row]==1:
            entry=open_[i]+spread; tp=entry+target; sl=entry-stop
            for k in range(i,i+horizon):
                if low[k]<=sl: pnl[row]=-stop; exits[row]=k; reasons[row]=-1; break
                if high[k]>=tp: pnl[row]=target; exits[row]=k; reasons[row]=1; break
            if exits[row]<0: exits[row]=i+horizon; pnl[row]=open_[i+horizon]-entry; reasons[row]=0
        else:
            entry=open_[i]; tp_bid=entry-target-spread; sl_bid=entry+stop-spread
            for k in range(i,i+horizon):
                if high[k]>=sl_bid: pnl[row]=-stop; exits[row]=k; reasons[row]=-1; break
                if low[k]<=tp_bid: pnl[row]=target; exits[row]=k; reasons[row]=1; break
            if exits[row]<0: exits[row]=i+horizon; pnl[row]=entry-(open_[i+horizon]+spread); reasons[row]=0
    return pnl,exits,reasons

def execute_candidates(candidates: pd.DataFrame,m1: pd.DataFrame,target=T20_TARGET,stop=T20_STOP,horizon=T20_HORIZON,spread=FIXED_SPREAD)->pd.DataFrame:
    x=candidates.copy()
    idx=x.entry_idx.to_numpy(np.int64); sides=np.where(x.chosen_side.eq("LONG"),1,-1).astype(np.int8)
    contig=contiguous_forward(m1.time.to_numpy("datetime64[ns]").astype(np.int64))
    pnl,exits,reasons=resolve_many(m1.open.to_numpy(float),m1.high.to_numpy(float),m1.low.to_numpy(float),contig,idx,sides,target,stop,horizon,spread)
    x["natural_pnl"]=pnl; x["natural_exit_idx"]=exits
    x["natural_exit_reason"]=pd.Series(reasons).map({-1:"SL",0:"TIME",1:"TP",9:"UNRESOLVED"}).to_numpy()
    valid=exits>=0
    et=np.full(len(x),np.datetime64("NaT"),dtype="datetime64[ns]"); et[valid]=m1.time.to_numpy()[exits[valid]]
    x["natural_exit_dt"]=pd.to_datetime(et)
    return x

def execute_candidates_simple(candidates: pd.DataFrame,m1: pd.DataFrame,target=T20_TARGET,stop=T20_STOP,horizon=T20_HORIZON,spread=FIXED_SPREAD)->pd.DataFrame:
    rows=[]; O=m1.open.to_numpy(float); H=m1.high.to_numpy(float); L=m1.low.to_numpy(float); T=m1.time.to_numpy();
    contig=contiguous_forward(m1.time.to_numpy("datetime64[ns]").astype(np.int64))
    for r in candidates.itertuples(index=False):
        i=int(r.entry_idx); side=str(r.chosen_side); pnl=np.nan; ex=-1; reason="UNRESOLVED"
        if i>=0 and i+horizon<len(O) and contig[i]>=horizon+1:
            if side=="LONG":
                entry=O[i]+spread; tp=entry+target; sl=entry-stop
                for k in range(i,i+horizon):
                    if L[k]<=sl: pnl=-stop;ex=k;reason="SL";break
                    if H[k]>=tp: pnl=target;ex=k;reason="TP";break
                if ex<0: ex=i+horizon;pnl=O[ex]-entry;reason="TIME"
            else:
                entry=O[i];tp=entry-target-spread;sl=entry+stop-spread
                for k in range(i,i+horizon):
                    if H[k]>=sl: pnl=-stop;ex=k;reason="SL";break
                    if L[k]<=tp: pnl=target;ex=k;reason="TP";break
                if ex<0: ex=i+horizon;pnl=entry-(O[ex]+spread);reason="TIME"
        rows.append((pnl,ex,reason,pd.Timestamp(T[ex]) if ex>=0 else pd.NaT))
    out=candidates.copy(); out[["natural_pnl","natural_exit_idx","natural_exit_reason","natural_exit_dt"]]=pd.DataFrame(rows,index=out.index)
    return out
