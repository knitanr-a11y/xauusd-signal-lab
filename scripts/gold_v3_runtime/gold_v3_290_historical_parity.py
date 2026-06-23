#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from pathlib import Path
import numpy as np
import pandas as pd

TARGETS={2024:(242,1.6452078476376886,279.44973547467157,28.94112080381211),2025:(229,1.9405961307567556,600.1607503293883,42.9229853282708),2026:(102,2.8428076234281456,965.6008808154027,66.06159660301591)}
PRIORITY={"STAGE280":10,"STAGE281":20,"SHORT_STRICT":60}

def pf(values):
    a=np.asarray(values,float); gp=a[a>0].sum(); gl=-a[a<0].sum(); return gp/gl if gl>0 else np.inf

def stats(frame):
    data=frame.sort_values("entry_dt"); values=data.pnl.to_numpy(float); curve=np.cumsum(values); peak=np.maximum.accumulate(np.r_[0.0,curve]); dd=float((peak[1:]-curve).max()) if len(values) else 0.0
    return len(values),float(pf(values)),float(values.sum()),dd

def read_base(path):
    data=pd.read_csv(path,encoding="utf-8-sig"); data["entry_dt"]=pd.to_datetime(data.entry_dt); exit_col="exit_dt_new" if "exit_dt_new" in data else "exit_dt"; pnl_col="pnl_new" if "pnl_new" in data else "pnl"; data["exit_dt"]=pd.to_datetime(data[exit_col]); data["pnl"]=pd.to_numeric(data[pnl_col]); data["source"]="BASE"; data["priority"]=0; return data

def read_candidate(path,source,long_only=False):
    data=pd.read_csv(path,encoding="utf-8-sig"); data["entry_dt"]=pd.to_datetime(data.entry_dt); data["exit_dt"]=pd.to_datetime(data.exit_dt); data["pnl"]=pd.to_numeric(data.pnl)
    if long_only and "direction" in data: data=data[data.direction.astype(str).eq("LONG")].copy()
    data["source"]=source; data["priority"]=PRIORITY[source]; return data

def run_year(year,base,s280,s281,strict):
    b=base[base.entry_dt.dt.year.eq(year)][["entry_dt","exit_dt","pnl","source","priority"]].copy()
    frames=[]
    for data in [s280,s281,strict]: frames.append(data[data.entry_dt.dt.year.eq(year)][["entry_dt","exit_dt","pnl","source","priority"]].copy())
    candidates=pd.concat(frames,ignore_index=True).sort_values(["entry_dt","priority"],kind="mergesort")
    base_events=list(b.sort_values("exit_dt").itertuples(index=False)); bi=0; accepted=[]; pending=[]; equity=0.0; peak=0.0; active_end=pd.Timestamp.min; last_entry=pd.Timestamp.min; last_candidate_loss=pd.Timestamp.min
    for row in candidates.itertuples(index=False):
        t=row.entry_dt; events=[]
        while bi<len(base_events) and base_events[bi].exit_dt<=t:
            events.append((base_events[bi].exit_dt,float(base_events[bi].pnl),"BASE")); bi+=1
        remaining=[]
        for event in pending:
            if event[0]<=t: events.append(event)
            else: remaining.append(event)
        pending=remaining
        for exit_dt,pnl,source in sorted(events,key=lambda x:x[0]):
            equity+=pnl; peak=max(peak,equity)
            if source!="BASE" and pnl<0: last_candidate_loss=max(last_candidate_loss,exit_dt)
        dd=peak-equity
        if t<active_end or dd>30 or t<last_entry+pd.Timedelta(hours=12): continue
        if row.source=="SHORT_STRICT":
            if dd>10: continue
            if t<last_candidate_loss+pd.Timedelta(hours=24): continue
        accepted.append({"entry_dt":row.entry_dt,"exit_dt":row.exit_dt,"pnl":row.pnl,"source":row.source,"priority":row.priority,"dd_before_entry":dd}); active_end=row.exit_dt; last_entry=t; pending.append((row.exit_dt,float(row.pnl),row.source))
    additions=pd.DataFrame(accepted)
    union=pd.concat([b,additions],ignore_index=True).sort_values(["entry_dt","priority"],kind="mergesort"); keep=[]; end=pd.Timestamp.min
    for row in union.itertuples():
        if row.entry_dt>=end: keep.append(row.Index); end=row.exit_dt
    return union.loc[keep].sort_values("entry_dt").reset_index(drop=True)

def main():
    p=argparse.ArgumentParser(); p.add_argument("--base",required=True); p.add_argument("--stage280",required=True); p.add_argument("--stage281",required=True); p.add_argument("--strict",required=True); p.add_argument("--output",required=True); a=p.parse_args()
    base=read_base(a.base); s280=read_candidate(a.stage280,"STAGE280",True); s281=read_candidate(a.stage281,"STAGE281"); strict=read_candidate(a.strict,"SHORT_STRICT")
    rows=[]; ledgers=[]; passed=True
    for year,target in TARGETS.items():
        result=run_year(year,base,s280,s281,strict); observed=stats(result); ok=observed[0]==target[0] and abs(observed[1]-target[1])<=1e-9 and abs(observed[2]-target[2])<=1e-8 and abs(observed[3]-target[3])<=1e-8; passed &= ok
        rows.append({"year":year,"passed":ok,"n":observed[0],"pf":observed[1],"sum":observed[2],"dd":observed[3],"expected_n":target[0],"expected_pf":target[1],"expected_sum":target[2],"expected_dd":target[3]}); result["year"]=year; ledgers.append(result)
    output=Path(a.output); output.mkdir(parents=True,exist_ok=True); pd.DataFrame(rows).to_csv(output/"gold_v3_290_historical_parity.csv",index=False,encoding="utf-8-sig"); pd.concat(ledgers,ignore_index=True).to_csv(output/"gold_v3_290_historical_replay_trades.csv",index=False,encoding="utf-8-sig"); (output/"gold_v3_290_historical_parity.json").write_text(json.dumps({"status":"PASS" if passed else "FAIL","rows":rows},indent=2),encoding="utf-8"); return 0 if passed else 2

if __name__=="__main__": raise SystemExit(main())
