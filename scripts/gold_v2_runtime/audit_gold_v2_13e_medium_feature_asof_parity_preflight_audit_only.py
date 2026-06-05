#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations
import json, math, os, zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import numpy as np
import pandas as pd

STEP="13E_MEDIUM_FEATURE_ASOF_PARITY_PREFLIGHT_AUDIT_ONLY"
SRC="gold_v2_13d3_freeze_medium_tier2_hvt_reconciled_rule_audit_only"
OUT="gold_v2_13e_medium_feature_asof_parity_preflight_audit_only"
REPORT="GOLD_V2_13E_MEDIUM_FEATURE_ASOF_PARITY_PREFLIGHT_AUDIT_ONLY_REPORT.md"
EXT={"discord_send_allowed":False,"mt5_order_allowed":False,"ai_api_allowed":False,"live_hook_allowed":False}
FEATS=["range96","ret96","trend_eff96","tr_mean_32"]
OHLC_NAMES=["goldsharp_m15.csv","xauusd_m15.csv","XAUUSD_M15.csv","candles_history_M15.csv","M15.csv"]

def rr(): return Path(__file__).resolve().parents[2]
def files_root():
    r=rr(); return r.parents[1] if len(r.parents)>=2 else r.parent
def fx(): return files_root()/"FX_OUTPUTS"
def lp(p):
    s=str(Path(p).resolve(strict=False))
    if os.name!="nt" or s.startswith("\\\\?\\"): return s
    return "\\\\?\\UNC\\"+s.lstrip("\\") if s.startswith("\\\\") else "\\\\?\\"+s
def ex(p): return os.path.exists(lp(p))
def od():
    p=fx()/OUT; os.makedirs(lp(p),exist_ok=True); return p
def fp(n): return fx()/SRC/n
def rcsv(p): return pd.read_csv(lp(p))
def rjson(p):
    with open(lp(p),"r",encoding="utf-8") as f: return json.load(f)
def wcsv(d,p): d.to_csv(lp(p),index=False,encoding="utf-8-sig")
def wtxt(p,s):
    os.makedirs(lp(Path(p).parent),exist_ok=True)
    with open(lp(p),"w",encoding="utf-8",newline="") as f: f.write(s)
def clean(x):
    if isinstance(x,dict): return {str(k):clean(v) for k,v in x.items()}
    if isinstance(x,list): return [clean(v) for v in x]
    if isinstance(x,(np.integer,)): return int(x)
    if isinstance(x,(np.floating,float)):
        if math.isnan(float(x)): return None
        if math.isinf(float(x)): return "inf" if float(x)>0 else "-inf"
        return float(x)
    if isinstance(x,pd.Timestamp): return x.isoformat()
    try:
        if pd.isna(x): return None
    except Exception: pass
    return x
def wjson(p,o): wtxt(p,json.dumps(clean(o),ensure_ascii=False,indent=2,allow_nan=False))
def num(s): return pd.to_numeric(s,errors="coerce")
def md(d):
    if d.empty: return "_No rows._"
    z=["| "+" | ".join(map(str,d.columns))+" |","| "+" | ".join(["---"]*len(d.columns))+" |"]
    for _,r in d.head(80).iterrows(): z.append("| "+" | ".join(str(r[c]).replace("|","\\|") for c in d.columns)+" |")
    return "\n".join(z)

def find_ohlc():
    roots=[rr(),files_root(),fx()]
    rows=[]
    for root in roots:
        for name in OHLC_NAMES:
            p=root/name
            if ex(p): rows.append({"name":name,"path":str(p),"exists":True})
    if not rows:
        for root in roots:
            try:
                for name in OHLC_NAMES:
                    for p in root.rglob(name): rows.append({"name":name,"path":str(p),"exists":True})
            except Exception: pass
    return pd.DataFrame(rows)

def norm_ohlc(df):
    d=df.copy(); low={c.lower().strip():c for c in d.columns}
    t=next((low[x] for x in ["time","datetime","date","timestamp","open_time"] if x in low),None)
    if t is None: raise ValueError("OHLC time column not found")
    ren={t:"time"}
    for x in ["open","high","low","close"]:
        if x in low: ren[low[x]]=x
    d=d.rename(columns=ren)
    for c in ["open","high","low","close"]:
        if c not in d.columns: raise ValueError(f"OHLC column missing: {c}")
        d[c]=num(d[c])
    d["time"]=pd.to_datetime(d["time"],errors="coerce")
    d=d.dropna(subset=["time"]).sort_values("time").drop_duplicates("time",keep="last")
    return d[["time","open","high","low","close"]].copy()

def features(ohlc):
    d=ohlc.copy()
    pc=d.close.shift(1)
    tr=pd.concat([(d.high-d.low).abs(),(d.high-pc).abs(),(d.low-pc).abs()],axis=1).max(axis=1)
    d["range96"]=d.high.rolling(96,min_periods=96).max()-d.low.rolling(96,min_periods=96).min()
    d["ret96"]=d.close-d.close.shift(96)
    d["trend_eff96"]=(d.ret96.abs()/d.range96).replace([np.inf,-np.inf],np.nan)
    d["tr_mean_32"]=tr.rolling(32,min_periods=32).mean()
    return d

def main():
    out=od(); now=datetime.now(timezone.utc).isoformat()
    inputs=["gold_v2_13d3_freeze_medium_tier2_hvt_reconciled_rule_summary.json","gold_v2_13d3_tier2_source_rows_with_reconciled_match.csv","gold_v2_13d3_tier2_final_rows_with_reconciled_match.csv","gold_v2_13d3_tier2_reconciled_rule_candidate.json"]
    ia=pd.DataFrame([{"name":n,"path":str(fp(n)),"exists":ex(fp(n))} for n in inputs]); wcsv(ia,out/"gold_v2_13e_input_audit.csv")
    inv=find_ohlc(); wcsv(inv,out/"gold_v2_13e_ohlc_inventory.csv")
    formula={"range96":"rolling96(high_max)-rolling96(low_min)","ret96":"close-close.shift(96)","trend_eff96":"abs(ret96)/range96","tr_mean_32":"rolling32(mean(true_range))","regime":"not frozen in 13E"}
    wjson(out/"gold_v2_13e_feature_formula_candidate_manifest.json",{"audit_only":True,"formula":formula,"external_actions":EXT})
    status=""; blockers=[]
    if not ia.exists.all():
        status="MISSING_13D3_INPUTS_AUDIT_ONLY"; blockers.append(["13E-B001","INPUT","HARD","OPEN","13D3 outputs","Run 13D3 first."])
    elif inv.empty:
        status="M15_OHLC_NOT_FOUND_AUDIT_ONLY"; blockers.append(["13E-B002","OHLC","HARD","OPEN","M15 OHLC","Place goldsharp_m15.csv or equivalent where script can find it."])
    if status:
        b=pd.DataFrame(blockers+[["13E-B099","SAFETY","SAFETY","OPEN","external actions","All external actions remain false."]],columns=["blocker_id","component","severity","status","blocked_item","required_resolution"]); wcsv(b,out/"gold_v2_13e_blockers.csv")
        wjson(out/"gold_v2_13e_medium_feature_asof_parity_preflight_summary.json",{"created_utc":now,"step":STEP,"status":status,"audit_only":True,"external_actions":EXT})
        wtxt(out/REPORT,"\n".join(["# GOLD V2 13E MEDIUM feature/asof parity preflight audit-only report","",f"Status: `{status}`","",md(ia),"",md(inv),"",md(b)])); return 2
    summ=rjson(fp(inputs[0])); src=rcsv(fp(inputs[1])); cand=rjson(fp(inputs[3]))
    ohlc=norm_ohlc(rcsv(Path(inv.iloc[0].path))); feat=features(ohlc)
    src=src.copy(); src["entry_time_dt"]=pd.to_datetime(src.get("entry_time",src.get("top_entry_time")),errors="coerce")
    merged=src.merge(feat[["time"]+FEATS],left_on="entry_time_dt",right_on="time",how="left",suffixes=("_source","_recalc"))
    rows=[]
    tol=1e-6
    for f in FEATS:
        s=num(merged[f"{f}_source"] if f"{f}_source" in merged.columns else merged[f])
        r=num(merged[f"{f}_recalc"] if f"{f}_recalc" in merged.columns else merged[f])
        diff=(r-s).abs(); ok=diff.le(tol)
        rows.append({"feature":f,"rows":len(merged),"source_non_null":int(s.notna().sum()),"recalc_non_null":int(r.notna().sum()),"matched_rows":int(ok.sum()),"max_abs_diff":float(diff.max()) if diff.notna().any() else None,"all_match":bool(ok.all())})
        merged[f"{f}_abs_diff"]=diff; merged[f"{f}_match"] = ok
    ps=pd.DataFrame(rows); wcsv(merged,out/"gold_v2_13e_source_rows_with_recomputed_features.csv"); wcsv(merged[[c for c in merged.columns if c.endswith("_match") or c.endswith("_abs_diff") or c in ["entry_time","entry_time_dt","time","strategy_id"]]],out/"gold_v2_13e_feature_parity_by_row.csv"); wcsv(ps,out/"gold_v2_13e_feature_parity_summary.csv")
    found=int(merged.time.notna().sum()); all_match=bool(found==31 and ps.all_match.all())
    status="MEDIUM_TIER2_HVT_FEATURE_ASOF_PARITY_PROVEN_PREFLIGHT_AUDIT_ONLY" if all_match else "MEDIUM_TIER2_HVT_FEATURE_ASOF_PARITY_NOT_PROVEN_AUDIT_ONLY"
    btxt=[] if all_match else [["13E-B003","FEATURE","HARD","OPEN","feature/asof parity","Candidate OHLC formula did not match source feature values 31/31."]]
    btxt += [["13E-B004","REGIME","HARD","OPEN","regime formula","Regime generation is not frozen in 13E."],["13E-B099","SAFETY","SAFETY","OPEN","external actions","All external actions remain false."]]
    b=pd.DataFrame(btxt,columns=["blocker_id","component","severity","status","blocked_item","required_resolution"]); wcsv(b,out/"gold_v2_13e_blockers.csv")
    dec=pd.DataFrame([["13E-C001","13D3 status",summ.get("status"),"TIER2_HVT_RECONCILED_RULE_CANDIDATE_FROZEN_AUDIT_ONLY","PASS" if summ.get("status")=="TIER2_HVT_RECONCILED_RULE_CANDIDATE_FROZEN_AUDIT_ONLY" else "STOP"],["13E-C002","entry_time feature rows",found,31,"PASS" if found==31 else "STOP"],["13E-C003","feature parity",all_match,True,"PASS" if all_match else "STOP"],["13E-C004","next","13F_BUILD_COMPONENT_LIVE_ELIGIBILITY_MATRIX_AUDIT_ONLY","13F/Review","INFO"]],columns=["check_id","check","observed","expected","status"]); wcsv(dec,out/"gold_v2_13e_decision_matrix.csv")
    wjson(out/"gold_v2_13e_medium_feature_asof_parity_preflight_summary.json",{"created_utc":now,"step":STEP,"status":status,"audit_only":True,"source_rows":len(src),"entry_time_feature_rows_found":found,"feature_parity_all_match":all_match,"feature_parity_summary":ps.to_dict("records"),"candidate_rule":cand,"medium_live_evaluator_allowed":False,"final_signal_allowed":False,"step13_allowed":False,"external_actions":EXT})
    wtxt(out/REPORT,"\n".join(["# GOLD V2 13E MEDIUM feature/asof parity preflight audit-only report","",f"Created UTC: {now}",f"Status: `{status}`","","## Feature parity summary",md(ps),"","## Decision",md(dec),"","## Blockers",md(b),"","External actions remain false."]))
    z=fx()/"gold_v2_13e_medium_feature_asof_parity_preflight_audit.zip"
    if ex(z): os.remove(lp(z))
    with zipfile.ZipFile(lp(z),"w",zipfile.ZIP_DEFLATED) as zz:
        for p in out.iterdir(): zz.write(lp(p),arcname=p.name)
    print(json.dumps(clean({"status":status,"output_dir":str(out),"zip":str(z),"entry_time_feature_rows_found":found,"feature_parity_all_match":all_match,"audit_only":True,"external_actions":EXT}),ensure_ascii=False,indent=2,allow_nan=False))
    return 0 if all_match else 2
if __name__=="__main__": raise SystemExit(main())
