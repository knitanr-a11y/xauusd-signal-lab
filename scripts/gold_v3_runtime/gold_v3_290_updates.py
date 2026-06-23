from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd
from gold_v3_290_io import read_csv_optional, require_columns

UPDATE_COLUMNS=["candidate_id","event_type","event_dt","price","pnl","reason"]

def load_updates(path: Path) -> pd.DataFrame:
    data=read_csv_optional(path,UPDATE_COLUMNS)
    if data.empty: return data
    require_columns(data,set(UPDATE_COLUMNS),"updates")
    data["event_dt"]=pd.to_datetime(data.event_dt,errors="coerce")
    data["event_type"]=data.event_type.astype(str).str.upper().str.strip()
    data["price"]=pd.to_numeric(data.price,errors="coerce")
    data["pnl"]=pd.to_numeric(data.pnl,errors="coerce")
    bad=sorted(set(data.event_type)-{"FILLED","CANCELLED","CLOSED"})
    if bad: raise ValueError(f"unsupported event_type: {bad}")
    return data.dropna(subset=["candidate_id","event_type","event_dt"]).sort_values(["event_dt","candidate_id"])

def apply_updates(ledger: pd.DataFrame, updates: pd.DataFrame, asof: pd.Timestamp):
    current=ledger.copy(); applied=[]
    for row in updates[pd.to_datetime(updates.event_dt).le(pd.Timestamp(asof))].itertuples(index=False):
        hit=current.index[current.candidate_id.astype(str).eq(str(row.candidate_id))]
        if len(hit)!=1: raise ValueError(f"candidate not found: {row.candidate_id}")
        idx=hit[0]; status=str(current.at[idx,"status"])
        if row.event_type=="FILLED" and status=="PENDING_FILL":
            if not np.isfinite(float(row.price)): raise ValueError("FILLED requires price")
            current.loc[idx,["status","fill_dt","fill_price"]]=["OPEN",row.event_dt,float(row.price)]
        elif row.event_type=="CANCELLED" and status=="PENDING_FILL":
            current.loc[idx,["status","exit_dt","exit_reason"]]=["CANCELLED",row.event_dt,str(row.reason or "CANCELLED")]
        elif row.event_type=="CLOSED" and status=="OPEN":
            if not np.isfinite(float(row.price)) or not np.isfinite(float(row.pnl)): raise ValueError("CLOSED requires price and pnl")
            current.loc[idx,["status","exit_dt","exit_price","pnl","exit_reason"]]=["CLOSED",row.event_dt,float(row.price),float(row.pnl),str(row.reason or "CLOSED")]
        else: continue
        applied.append({"candidate_id":str(row.candidate_id),"event_type":row.event_type,"event_dt":row.event_dt})
    return current,pd.DataFrame(applied)
