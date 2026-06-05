#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations
import json, math, os
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd

STEP="13E5_READ_REPLAY_FEATURE_SOURCE_CHAIN_AUDIT_ONLY"
OUT="gold_v2_13e5_read_replay_feature_source_chain_audit_only"
REPORT="GOLD_V2_13E5_READ_REPLAY_FEATURE_SOURCE_CHAIN_AUDIT_ONLY_REPORT.md"
FEATS=["range96","trend_eff96","ret96","tr_mean_32"]
EXT={"discord_send_allowed":False,"mt5_order_allowed":False,"ai_api_allowed":False,"live_hook_allowed":False}

def rr(): return Path(__file__).resolve().parents[2]
def fr():
    r=rr(); return r.parents[1] if len(r.parents)>=2 else r.parent
def fx(): return fr()/"FX_OUTPUTS"
def lp(p):
    s=str(Path(p).resolve(strict=False))
    if os.name!="nt" or s.startswith("\\\\?\\"): return s
    return "\\\\?\\UNC\\"+s.lstrip("\\") if s.startswith("\\\\") else "\\\\?\\"+s
def ex(p): return os.path.exists(lp(p))
def od():
    p=fx()/OUT; os.makedirs(lp(p),exist_ok=True); return p
def rd(p): return pd.read_csv(lp(p))
def wc(d,p): d.to_csv(lp(p),index=False,encoding="utf-8-sig")
def wt(p,s):
    os.makedirs(lp(Path(p).parent),exist_ok=True)
    with open(lp(p),"w",encoding="utf-8",newline="") as f: f.write(s)
def cl(x):
    if isinstance(x,dict): return {str(k):cl(v) for k,v in x.items()}
    if isinstance(x,list): return [cl(v) for v in x]
    if isinstance(x,(np.integer,)): return int(x)
    if isinstance(x,(np.floating,float)):
        if math.isnan(float(x)): return None
        if math.isinf(float(x)): return "inf" if float(x)>0 else "-inf"
        return float(x)
    try:
        if pd.isna(x): return None
    except Exception: pass
    return x
def wj(p,o): wt(p,json.dumps(cl(o),ensure_ascii=False,indent=2,allow_nan=False))
def num(s): return pd.to_numeric(s,errors="coerce")
def md(d):
    if d.empty: return "_No rows._"
    z=["| "+" | ".join(map(str,d.columns))+" |","| "+" | ".join(["---"]*len(d.columns))+" |"]
    for _,r in d.head(80).iterrows(): z.append("| "+" | ".join(str(r[c]).replace("|","\\|") for c in d.columns)+" |")
    return "\n".join(z)
def tc(p):
    try: return Path(p).read_text(encoding="utf-8",errors="ignore")
    except Exception: return ""
def cn(df,*ns):
    low={c.lower():c for c in df.columns}
    for n in ns:
        if n.lower() in low: return low[n.lower()]
    return None

def score(src,cand,name):
    s=src.copy(); c=cand.copy()
    st=cn(s,"entry_time","top_entry_time"); ct=cn(c,"entry_time","top_entry_time")
    sd=cn(s,"direction","top_direction"); cd=cn(c,"direction","top_direction")
    sc=cn(s,"component","refined_rule"); cc=cn(c,"component","refined_rule")
    s["t"]=pd.to_datetime(s[st],errors="coerce"); c["t"]=pd.to_datetime(c[ct],errors="coerce")
    s["d"]=s[sd].astype(str) if sd else ""; c["d"]=c[cd].astype(str) if cd else ""
    s["comp"]=s[sc].astype(str).str.replace("MEDIUM_","",regex=False) if sc else ""; c["comp"]=c[cc].astype(str).str.replace("MEDIUM_","",regex=False) if cc else ""
    c=c.drop_duplicates(["t","d","comp"],keep="first")
    m=s.merge(c[["t","d","comp"]+[f for f in FEATS if f in c.columns]],on=["t","d","comp"],how="left",suffixes=("_src","_cand"))
    row={"candidate":name,"source_rows":len(s)}; total=0
    for f in FEATS:
        sf=f+"_src" if f+"_src" in m.columns else f; cf=f+"_cand"
        if sf not in m.columns or cf not in m.columns:
            row[f+"_matched_rows"]=0; row[f+"_max_abs_diff"]=None; continue
        diff=(num(m[cf])-num(m[sf])).abs(); ok=diff.le(1e-6)
        row[f+"_matched_rows"]=int(ok.sum()); row[f+"_max_abs_diff"]=float(diff.max()) if diff.notna().any() else None; total+=int(ok.sum())
    row["total_feature_matches"]=total; row["all_feature_full_match"]=bool(total==len(s)*4)
    return row

def main():
    out=od(); now=datetime.now(timezone.utc).isoformat()
    srcp=fx()/"gold_v2_13d3_freeze_medium_tier2_hvt_reconciled_rule_audit_only"/"gold_v2_13d3_tier2_source_rows_with_reconciled_match.csv"
    rulep=fx()/"gold_v2_coreb_refined_probe_outputs"/"coreb_refined_rule_ledgers.csv"; combp=fx()/"gold_v2_coreb_refined_probe_outputs"/"coreb_refined_combined_ledgers.csv"
    codep=rr()/"scripts"/"gold_v2_runtime"/"freeze_gold_v2_final_portfolio_sot_audit_only.py"
    inputs=[srcp,rulep,combp,codep]
    audit=pd.DataFrame([{"name":p.name,"path":str(p),"exists":ex(p)} for p in inputs]); wc(audit,out/"gold_v2_13e5_input_audit.csv")
    if not audit.exists.all():
        status="MISSING_FEATURE_CHAIN_INPUTS_AUDIT_ONLY"; wj(out/"gold_v2_13e5_feature_source_chain_summary.json",{"created_utc":now,"step":STEP,"status":status,"audit_only":True,"external_actions":EXT}); wt(out/REPORT,md(audit)); return 2
    src=rd(srcp); checks=pd.DataFrame([score(src,rd(rulep),"coreb_refined_rule_ledgers.csv"),score(src,rd(combp),"coreb_refined_combined_ledgers.csv")]); wc(checks,out/"gold_v2_13e5_medium_source_join_checks.csv")
    code=tc(codep)
    trace=pd.DataFrame([{"code":"freeze_gold_v2_final_portfolio_sot_audit_only.py","has_medium_dir":"gold_v2_coreb_refined_probe_outputs" in code,"reads_rule_ledgers":"coreb_refined_rule_ledgers.csv" in code,"has_normalize_medium":"def normalize_medium" in code,"has_medium_components":all(x in code for x in ["RANGE96_REFINED","VOL_TRMEAN32_REFINED","TIER2_HVT"]),"has_feature_columns":all(f in code for f in FEATS)}]); wc(trace,out/"gold_v2_13e5_code_trace_checks.csv")
    join_ok=bool(checks.all_feature_full_match.any()); code_ok=bool(trace.drop(columns=["code"]).all(axis=1).iloc[0])
    status="FEATURE_SOURCE_CHAIN_FIXED_AUDIT_ONLY" if join_ok and code_ok else "FEATURE_SOURCE_CHAIN_NOT_FIXED_AUDIT_ONLY"
    dec=pd.DataFrame([["13E5-C001","source ledger feature join",join_ok,True,"PASS" if join_ok else "STOP"],["13E5-C002","code pass-through trace",code_ok,True,"PASS" if code_ok else "STOP"],["13E5-C003","next","13F_MEDIUM_LIVE_ELIGIBILITY_MATRIX_AUDIT_ONLY" if join_ok and code_ok else "STOP","review","INFO"]],columns=["check_id","check","observed","expected","status"]); wc(dec,out/"gold_v2_13e5_decision_matrix.csv")
    block=pd.DataFrame([["13E5-B004","LIVE_REPLAY","HARD","OPEN","live evaluator replay","Need 13F/13G before live evaluator."],["13E5-B099","SAFETY","SAFETY","OPEN","external actions","All external actions remain false."]],columns=["blocker_id","component","severity","status","blocked_item","required_resolution"]); wc(block,out/"gold_v2_13e5_blockers.csv")
    wj(out/"gold_v2_13e5_feature_source_chain_summary.json",{"created_utc":now,"step":STEP,"status":status,"audit_only":True,"join_ok":join_ok,"code_ok":code_ok,"medium_live_evaluator_allowed":False,"final_signal_allowed":False,"step13_allowed":False,"external_actions":EXT})
    wt(out/REPORT,"\n".join(["# GOLD V2 13E5 feature source chain audit-only report","",f"Created UTC: {now}",f"Status: `{status}`","","## Join checks",md(checks),"","## Code trace checks",md(trace),"","## Decision",md(dec),"","## Blockers",md(block),"","External actions remain false."]))
    print(json.dumps(cl({"status":status,"output_dir":str(out),"join_ok":join_ok,"code_ok":code_ok,"audit_only":True,"external_actions":EXT}),ensure_ascii=False,indent=2,allow_nan=False))
    return 0 if join_ok and code_ok else 2
if __name__=="__main__": raise SystemExit(main())
