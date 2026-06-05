#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations
import json, math, os, zipfile
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd

STEP="13E3_MEDIUM_FEATURE_SOURCE_LOCATOR_AUDIT_ONLY"
SRC="gold_v2_13d3_freeze_medium_tier2_hvt_reconciled_rule_audit_only"
OUT="gold_v2_13e3_medium_feature_source_locator_audit_only"
REPORT="GOLD_V2_13E3_MEDIUM_FEATURE_SOURCE_LOCATOR_AUDIT_ONLY_REPORT.md"
FEATS=["range96","ret96","trend_eff96","tr_mean_32"]
EXT={"discord_send_allowed":False,"mt5_order_allowed":False,"ai_api_allowed":False,"live_hook_allowed":False}

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

def read_any(p):
    if p.suffix.lower()==".csv": return pd.read_csv(lp(p),nrows=200000)
    if p.suffix.lower()==".parquet": return pd.read_parquet(lp(p))
    raise ValueError(str(p))
def find_time(cols):
    lows={c.lower():c for c in cols}
    for k in ["entry_time","top_entry_time","time","datetime","date","timestamp","open_time"]:
        if k in lows: return lows[k]
    return None
def canon_feature_cols(cols):
    lows={c.lower():c for c in cols}; out={}
    for f in FEATS:
        if f in lows: out[f]=lows[f]
        elif f+"_source" in lows: out[f]=lows[f+"_source"]
        elif f+"_m15" in lows: out[f]=lows[f+"_m15"]
    return out

def inventory():
    roots=[rr(),files_root(),fx()]; seen=set(); rows=[]
    keys=["feature","medium","coreb","ledger","candidate","rule","source","final","sot"]
    for root in roots:
        for pat in ["*.csv","*.parquet"]:
            try:
                for p in root.rglob(pat):
                    s=str(p)
                    if s in seen: continue
                    seen.add(s); name=p.name.lower(); pri=any(k in name for k in keys)
                    if not pri and len(rows)>3000: continue
                    rows.append({"path":s,"name":p.name,"suffix":p.suffix.lower(),"bytes":os.path.getsize(lp(p)) if ex(p) else None,"priority_name":pri})
            except Exception: pass
    return pd.DataFrame(rows)

def score_file(p,src):
    try: d=read_any(p)
    except Exception as e: return {"path":str(p),"read_error":str(e)} , None
    t=find_time(d.columns); fcols=canon_feature_cols(d.columns)
    row={"path":str(p),"rows":len(d),"columns":len(d.columns),"time_col":t,"feature_cols":"|".join(fcols.keys()),"feature_col_count":len(fcols)}
    if not t or len(fcols)==0: return row,None
    d=d.copy(); d["__time__"]=pd.to_datetime(d[t],errors="coerce"); d=d.dropna(subset=["__time__"]).drop_duplicates("__time__",keep="last")
    m=src.merge(d[["__time__"]+list(fcols.values())],left_on="entry_time_dt",right_on="__time__",how="left",suffixes=("_src","_cand"))
    row["found_rows"]=int(m.__time__.notna().sum()); total=0
    for f,c in fcols.items():
        s=num(m[f]); v=num(m[c]); diff=(v-s).abs(); ok=diff.le(1e-6)
        row[f+"_matched_rows"]=int(ok.sum()); row[f+"_max_abs_diff"]=float(diff.max()) if diff.notna().any() else None; total+=int(ok.sum())
    row["total_feature_matches"]=total; row["all_four_full_match"]=bool(total==len(src)*4 and len(fcols)==4)
    return row,m

def main():
    out=od(); now=datetime.now(timezone.utc).isoformat()
    srcp=fx()/SRC/"gold_v2_13d3_tier2_source_rows_with_reconciled_match.csv"; sump=fx()/SRC/"gold_v2_13d3_freeze_medium_tier2_hvt_reconciled_rule_summary.json"
    ia=pd.DataFrame([{"name":p.name,"path":str(p),"exists":ex(p)} for p in [srcp,sump]]); wcsv(ia,out/"gold_v2_13e3_input_audit.csv")
    if not ia.exists.all():
        status="MISSING_13D3_INPUTS_AUDIT_ONLY"; wjson(out/"gold_v2_13e3_medium_feature_source_locator_summary.json",{"created_utc":now,"step":STEP,"status":status,"audit_only":True,"external_actions":EXT}); wtxt(out/REPORT,md(ia)); return 2
    src=rcsv(srcp); src["entry_time_dt"]=pd.to_datetime(src.get("entry_time",src.get("top_entry_time")),errors="coerce")
    inv=inventory(); wcsv(inv,out/"gold_v2_13e3_candidate_file_inventory.csv")
    scores=[]; best=None; bestm=None
    for _,r in inv.sort_values(["priority_name","bytes"],ascending=[False,False]).head(1000).iterrows():
        row,m=score_file(Path(r.path),src); scores.append(row)
        if "total_feature_matches" in row and (best is None or row.get("total_feature_matches",0)>best.get("total_feature_matches",0)):
            best=row; bestm=m
    sc=pd.DataFrame(scores).sort_values(["all_four_full_match","total_feature_matches","found_rows","feature_col_count"],ascending=[False,False,False,False]); wcsv(sc,out/"gold_v2_13e3_candidate_file_scores.csv")
    if bestm is not None: wcsv(bestm,out/"gold_v2_13e3_best_candidate_join_rows.csv")
    found=bool(best and best.get("all_four_full_match") is True)
    status="FEATURE_SOURCE_FILE_FULL_MATCH_FOUND_AUDIT_ONLY" if found else "FEATURE_SOURCE_FILE_FULL_MATCH_NOT_FOUND_AUDIT_ONLY"
    b=pd.DataFrame(([] if found else [["13E3-B003","FEATURE_SOURCE","HARD","OPEN","feature source locator","No existing CSV/parquet fully matched source 31 rows and four features."]])+[["13E3-B004","CODE_SOURCE","HARD","OPEN","feature generation code","After file source is found, generating code must be identified."],["13E3-B099","SAFETY","SAFETY","OPEN","external actions","All external actions remain false."]],columns=["blocker_id","component","severity","status","blocked_item","required_resolution"]); wcsv(b,out/"gold_v2_13e3_blockers.csv")
    dec=pd.DataFrame([["13E3-C001","candidate files",len(inv),">0","PASS" if len(inv)>0 else "STOP"],["13E3-C002","best total feature matches",best.get("total_feature_matches") if best else 0,124,"PASS" if found else "STOP"],["13E3-C003","next","13E4_IDENTIFY_FEATURE_GENERATION_CODE_AUDIT_ONLY" if found else "STOP_FIND_OR_PROVIDE_FEATURE_SOURCE","review","INFO"]],columns=["check_id","check","observed","expected","status"]); wcsv(dec,out/"gold_v2_13e3_decision_matrix.csv")
    wjson(out/"gold_v2_13e3_medium_feature_source_locator_summary.json",{"created_utc":now,"step":STEP,"status":status,"audit_only":True,"source_rows":len(src),"candidate_files":len(inv),"best_candidate":best,"full_match_found":found,"medium_live_evaluator_allowed":False,"final_signal_allowed":False,"step13_allowed":False,"external_actions":EXT})
    wtxt(out/REPORT,"\n".join(["# GOLD V2 13E3 MEDIUM feature source locator audit-only report","",f"Created UTC: {now}",f"Status: `{status}`","","## Best candidates",md(sc.head(20)),"","## Decision",md(dec),"","## Blockers",md(b),"","External actions remain false."]))
    z=fx()/"gold_v2_13e3_medium_feature_source_locator_audit.zip"
    if ex(z): os.remove(lp(z))
    with zipfile.ZipFile(lp(z),"w",zipfile.ZIP_DEFLATED) as zz:
        for p in out.iterdir(): zz.write(lp(p),arcname=p.name)
    print(json.dumps(clean({"status":status,"output_dir":str(out),"zip":str(z),"best_candidate":best,"audit_only":True,"external_actions":EXT}),ensure_ascii=False,indent=2,allow_nan=False))
    return 0 if found else 2
if __name__=="__main__": raise SystemExit(main())
