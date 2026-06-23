from __future__ import annotations
from pathlib import Path
import pandas as pd
from gold_v3_290_io import read_csv_optional, require_columns

COLUMNS=["candidate_id","source","priority","decision_dt","trigger_dt","planned_entry_dt","direction","direction_num","reference_price","atr_entry","tp_atr","sl_atr","max_holding_minutes","status","fill_dt","fill_price","exit_dt","exit_price","pnl","exit_reason","reject_reasons"]

def empty_ledger():
    return pd.DataFrame(columns=COLUMNS)

def load_ledger(path: Path) -> pd.DataFrame:
    data=read_csv_optional(path,COLUMNS)
    for c in ["decision_dt","trigger_dt","planned_entry_dt","fill_dt","exit_dt"]:
        if c in data: data[c]=pd.to_datetime(data[c],errors="coerce")
    for c in ["priority","direction_num","reference_price","atr_entry","tp_atr","sl_atr","max_holding_minutes","fill_price","exit_price","pnl"]:
        if c in data: data[c]=pd.to_numeric(data[c],errors="coerce")
    return data

def import_bootstrap(path: Path,start=None,end=None) -> pd.DataFrame:
    data=pd.read_csv(path,encoding="utf-8-sig")
    require_columns(data,{"entry_dt","exit_dt","pnl","source"},"bootstrap")
    if "portfolio" in data.columns:
        data=data[data.portfolio.astype(str)=="PLUS_STRICT_SAFE"].copy()
    data["entry_dt"]=pd.to_datetime(data.entry_dt,errors="coerce")
    data["exit_dt"]=pd.to_datetime(data.exit_dt,errors="coerce")
    data["pnl"]=pd.to_numeric(data.pnl,errors="coerce")
    data=data.dropna(subset=["entry_dt","exit_dt","pnl","source"])
    if start is not None: data=data[data.entry_dt>=pd.Timestamp(start)]
    if end is not None: data=data[data.exit_dt<=pd.Timestamp(end)]
    if (data.exit_dt<data.entry_dt).any(): raise ValueError("bootstrap has exit before entry")
    if "candidate_id" not in data:
        data=data.reset_index(drop=True)
        data["candidate_id"]=[f"BOOTSTRAP|{i}|{t.isoformat()}" for i,t in enumerate(data.entry_dt)]
    return data[["candidate_id","source","entry_dt","exit_dt","pnl"]].drop_duplicates("candidate_id",keep="last")
