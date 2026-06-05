#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations
import json, math, os, zipfile
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd

STEP="13E2_MEDIUM_FEATURE_FORMULA_ASOF_GRID_AUDIT_ONLY"
SRC3="gold_v2_13d3_freeze_medium_tier2_hvt_reconciled_rule_audit_only"
SRC13E="gold_v2_13e_medium_feature_asof_parity_preflight_audit_only"
OUT="gold_v2_13e2_medium_feature_formula_asof_grid_audit_only"
REPORT="GOLD_V2_13E2_MEDIUM_FEATURE_FORMULA_ASOF_GRID_AUDIT_ONLY_REPORT.md"
EXT={"discord_send_allowed":False,"mt5_order_allowed":False,"ai_api_allowed":False,"live_hook_allowed":False}
OHLC=["goldsharp_m15.csv","xauusd_m15.csv","XAUUSD_M15.csv","candles_history_M15.csv","M15.csv"]
FEATS=["range96","ret96","trend_eff96","tr_mean_32"]

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
    try:
        if pd.isna(x): return None
    except Exception: pass
    return x
def wjson(p,o): wtxt(p,json.dumps(clean(o),ensure_ascii=False,indent=2,allow_nan=False))
def num(s): return pd.to_numeric(s,errors="coerce")
def md(d,n=60):
    if d.empty: return "_No rows._"
    d=d.head(n); z=["| "+" | ".join(map(str,d.columns))+" |","| "+" | ".join(["---"]*len(d.columns))+" |"]
    for _,r in d.iterrows(): z.append("| "+" | ".join(str(r[c]).replace("|","\\|") for c in d.columns)+" |")
    return "\n".join(z)

def find_ohlc():
    rows=[]
    for root in [rr(),files_root(),fx()]:
        for n in OHLC:
            p=root/n
            if ex(p): rows.append({"name":n,"path":str(p),"exists":True})
    return pd.DataFrame(rows)

def norm(d):
    low={c.lower().strip():c for c in d.columns}
    t=next((low[x] for x in ["time","datetime","date","timestamp","open_time"] if x in low),None)
    if t is None: raise ValueError("time column missing")
    ren={t:"time"}
    for x in ["open","high","low","close"]:
        if x in low: ren[low[x]]=x
    d=d.rename(columns=ren)
    for c in ["open","high","low","close"]: d[c]=num(d[c])
    d["time"]=pd.to_datetime(d["time"],errors="coerce")
    return d.dropna(subset=["time"]).sort_values("time").drop_duplicates("time",keep="last")[["time","open","high","low","close"]]

def eval_variant(ohlc, src, asof, rw, rs, tw, tm):
    d=ohlc.copy(); pc=d.close.shift(1)
    tr=(d.high-d.low).abs() if tm=="hl" else pd.concat([(d.high-d.low).abs(),(d.high-pc).abs(),(d.low-pc).abs()],axis=1).max(axis=1)
    d["range96"]=d.high.rolling(rw,min_periods=rw).max()-d.low.rolling(rw,min_periods=rw).min()
    d["ret96"]=d.close-d.close.shift(rs)
    d["trend_eff96"]=(d.ret96.abs()/d.range96).replace([np.inf,-np.inf],np.nan)
    d["tr_mean_32"]=tr.rolling(tw,min_periods=tw).mean()
    d["join_time"]=d.time-pd.to_timedelta(asof*15,unit="m")
    m=src.merge(d[["join_time"]+FEATS],left_on="entry_time_dt",right_on="join_time",how="left",suffixes=("_source","_calc"))
    row={"asof_shift_bars":asof,"range_window":rw,"ret_shift_bars":rs,"tr_mean_window":tw,"tr_mode":tm,"found_rows":int(m.join_time.notna().sum())}
    total=0; maxdiff=0.0
    for f in FEATS:
        s=num(m[f"{f}_source"] if f"{f}_source" in m.columns else m[f]); c=num(m[f"{f}_calc"])
        diff=(c-s).abs(); ok=diff.le(1e-6)
        row[f"{f}_matched_rows"]=int(ok.sum()); row[f"{f}_max_abs_diff"]=float(diff.max()) if diff.notna().any() else None
        total+=int(ok.sum()); maxdiff=max(maxdiff, float(diff.max()) if diff.notna().any() else 1e99)
    row["total_feature_matches"]=total; row["all_features_all_rows_match"]=bool(total==len(src)*len(FEATS)); row["worst_max_abs_diff"]=maxdiff
    return row,m

def main():
    out=od(); now=datetime.now(timezone.utc).isoformat()
    srcp=fx()/SRC3/"gold_v2_13d3_tier2_source_rows_with_reconciled_match.csv"; sump=fx()/SRC3/"gold_v2_13d3_freeze_medium_tier2_hvt_reconciled_rule_summary.json"; e13=fx()/SRC13E/"gold_v2_13e_medium_feature_asof_parity_preflight_summary.json"
    ia=pd.DataFrame([{"name":p.name,"path":str(p),"exists":ex(p)} for p in [srcp,sump,e13]]); wcsv(ia,out/"gold_v2_13e2_input_audit.csv")
    inv=find_ohlc(); wcsv(inv,out/"gold_v2_13e2_ohlc_inventory.csv")
    if not ia.exists.all() or inv.empty:
        status="MISSING_INPUT_OR_OHLC_AUDIT_ONLY"; wjson(out/"gold_v2_13e2_medium_feature_formula_asof_grid_summary.json",{"created_utc":now,"step":STEP,"status":status,"audit_only":True,"external_actions":EXT}); wtxt(out/REPORT,md(ia)+"\n\n"+md(inv)); return 2
    src=rcsv(srcp); summ=rjson(sump); _e13=rjson(e13); ohlc=norm(rcsv(Path(inv.iloc[0].path)))
    src["entry_time_dt"]=pd.to_datetime(src.get("entry_time",src.get("top_entry_time")),errors="coerce")
    rows=[]; best_m=None; best_row=None
    for asof in range(-8,9):
      for rw in range(94,99):
       for rs in range(90,103):
        for tw in range(30,35):
         for tm in ["tr","hl"]:
          row,m=eval_variant(ohlc,src,asof,rw,rs,tw,tm); rows.append(row)
          if best_row is None or (row["total_feature_matches"],-row["worst_max_abs_diff"])>(best_row["total_feature_matches"],-best_row["worst_max_abs_diff"]): best_row=row; best_m=m
    grid=pd.DataFrame(rows).sort_values(["all_features_all_rows_match","total_feature_matches","worst_max_abs_diff"],ascending=[False,False,True])
    wcsv(grid.head(500),out/"gold_v2_13e2_joint_best_variants.csv")
    feat_best=[]
    for f in FEATS:
        feat_best.append(grid.sort_values([f"{f}_matched_rows",f"{f}_max_abs_diff"],ascending=[False,True]).head(20).assign(feature=f))
    wcsv(pd.concat(feat_best,ignore_index=True),out/"gold_v2_13e2_feature_best_variants.csv")
    wcsv(best_m,out/"gold_v2_13e2_best_variant_row_diffs.csv")
    ok=bool(best_row and best_row["all_features_all_rows_match"])
    status="MEDIUM_FEATURE_FORMULA_ASOF_GRID_FULL_MATCH_FOUND_AUDIT_ONLY" if ok else "MEDIUM_FEATURE_FORMULA_ASOF_GRID_NO_FULL_MATCH_AUDIT_ONLY"
    block=pd.DataFrame(([ ["13E2-B003","FEATURE","HARD","OPEN","formula/asof parity","No single grid variant reproduced all features 31/31."] ] if not ok else [])+[["13E2-B004","REGIME","HARD","OPEN","regime formula","Regime formula still not frozen."],["13E2-B099","SAFETY","SAFETY","OPEN","external actions","All external actions remain false."]],columns=["blocker_id","component","severity","status","blocked_item","required_resolution"]); wcsv(block,out/"gold_v2_13e2_blockers.csv")
    dec=pd.DataFrame([["13E2-C001","13D3 status",summ.get("status"),"TIER2_HVT_RECONCILED_RULE_CANDIDATE_FROZEN_AUDIT_ONLY","PASS" if summ.get("status")=="TIER2_HVT_RECONCILED_RULE_CANDIDATE_FROZEN_AUDIT_ONLY" else "STOP"],["13E2-C002","best total matches",best_row["total_feature_matches"],124,"PASS" if ok else "STOP"],["13E2-C003","next","13E3_FREEZE_FEATURE_FORMULA_OR_STOP_AUDIT_ONLY" if ok else "STOP_REVIEW_FEATURE_GENERATION_SOURCE","review","INFO"]],columns=["check_id","check","observed","expected","status"]); wcsv(dec,out/"gold_v2_13e2_decision_matrix.csv")
    wjson(out/"gold_v2_13e2_medium_feature_formula_asof_grid_summary.json",{"created_utc":now,"step":STEP,"status":status,"audit_only":True,"best_variant":best_row,"full_match_found":ok,"grid_rows":len(grid),"medium_live_evaluator_allowed":False,"final_signal_allowed":False,"step13_allowed":False,"external_actions":EXT})
    wtxt(out/REPORT,"\n".join(["# GOLD V2 13E2 MEDIUM feature formula/asof grid audit-only report","",f"Created UTC: {now}",f"Status: `{status}`","","## Best joint variants",md(grid.head(20)),"","## Decision",md(dec),"","## Blockers",md(block),"","External actions remain false."]))
    z=fx()/"gold_v2_13e2_medium_feature_formula_asof_grid_audit.zip"
    if ex(z): os.remove(lp(z))
    with zipfile.ZipFile(lp(z),"w",zipfile.ZIP_DEFLATED) as zz:
        for p in out.iterdir(): zz.write(lp(p),arcname=p.name)
    print(json.dumps(clean({"status":status,"output_dir":str(out),"zip":str(z),"best_variant":best_row,"audit_only":True,"external_actions":EXT}),ensure_ascii=False,indent=2,allow_nan=False))
    return 0 if ok else 2
if __name__=="__main__": raise SystemExit(main())
