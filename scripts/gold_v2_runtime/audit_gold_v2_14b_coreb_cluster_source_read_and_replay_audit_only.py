#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations
import json, math, os
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd

STEP="14B_COREB_CLUSTER_SOURCE_READ_AND_REPLAY_AUDIT_ONLY"
OUT="gold_v2_14b_coreb_cluster_source_read_and_replay_audit_only"
REPORT="GOLD_V2_14B_COREB_CLUSTER_SOURCE_READ_AND_REPLAY_AUDIT_ONLY_REPORT.md"
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
def find_file(name):
    direct=fx()/name
    if ex(direct): return direct
    matches=list(Path(lp(fx())).rglob(name)) if ex(fx()) else []
    return matches[0] if matches else direct
def od():
    p=fx()/OUT; os.makedirs(lp(p),exist_ok=True); return p
def rd(p): return pd.read_csv(lp(p))
def rj(p):
    with open(lp(p),"r",encoding="utf-8") as f: return json.load(f)
def wt(p,s):
    os.makedirs(lp(Path(p).parent),exist_ok=True)
    with open(lp(p),"w",encoding="utf-8",newline="") as f: f.write(s)
def wc(d,p): d.to_csv(lp(p),index=False,encoding="utf-8-sig")
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
def wj(p,o): wt(p,json.dumps(clean(o),ensure_ascii=False,indent=2,allow_nan=False))
def md(d,limit=80):
    if d.empty: return "_No rows._"
    z=["| "+" | ".join(map(str,d.columns))+" |","| "+" | ".join(["---"]*len(d.columns))+" |"]
    for _,r in d.head(limit).iterrows(): z.append("| "+" | ".join(str(r[c]).replace("|","\\|") for c in d.columns)+" |")
    return "\n".join(z)
def metrics(vals):
    s=pd.to_numeric(pd.Series(vals),errors="coerce").dropna()
    if len(s)==0: return {"count":0,"win_rate_pct":None,"pf":None,"total_r":0.0}
    gw=float(s[s>0].sum()); gl=float(-s[s<0].sum())
    return {"count":int(len(s)),"win_rate_pct":float((s>0).mean()*100),"pf":float(gw/gl) if gl>0 else (float("inf") if gw>0 else None),"total_r":float(s.sum())}

def main():
    out=od(); now=datetime.now(timezone.utc).isoformat()
    rawp=find_file("rr125_raw_signal_ledger.csv")
    topp=find_file("rr125_top_ledgers.csv")
    filterp=find_file("rr125_filter_results.csv")
    recp=find_file("rr125_recommended_filters.csv")
    s13c3=find_file("gold_v2_13c3_coreb_reconstruct_source_cluster_membership_summary.json")
    s13c4=find_file("gold_v2_13c4_coreb_clustering_script_search_summary.json")
    inputs=[rawp,topp,filterp,recp,s13c3,s13c4]
    ia=pd.DataFrame([{"name":p.name,"path":str(p),"exists":ex(p)} for p in inputs]); wc(ia,out/"gold_v2_14b_input_audit.csv")
    if not ex(rawp) or not ex(topp):
        status="COREB_SOURCE_LEDGER_MISSING_AUDIT_ONLY"; wj(out/"gold_v2_14b_coreb_cluster_source_read_and_replay_summary.json",{"created_utc":now,"step":STEP,"status":status,"audit_only":True,"external_actions":EXT}); wt(out/REPORT,md(ia)); return 2
    raw=rd(rawp); top=rd(topp)
    raw_rr=raw[raw.get("policy",pd.Series(dtype=str)).astype(str).eq("RR125_from_RR1_rules")].copy() if "policy" in raw.columns else raw.iloc[0:0].copy()
    top_rr=top[top.get("policy",pd.Series(dtype=str)).astype(str).eq("RR125_from_RR1_rules")].copy() if "policy" in top.columns else top.iloc[0:0].copy()
    target=top_rr[top_rr.get("filter",pd.Series(dtype=str)).astype(str).eq("same_count>=15")].copy() if "filter" in top_rr.columns else top_rr.iloc[0:0].copy()
    wc(target,out/"gold_v2_14b_coreb_source_top_ledger_target_rows.csv")
    source_rules=raw_rr[[c for c in ["policy","candidate_id","origin_id","direction","variant","tp_pips","sl_pips","rr","rr_bucket","base_condition","added_filter_text","train_score"] if c in raw_rr.columns]].drop_duplicates().sort_values([c for c in ["candidate_id","variant","base_condition","added_filter_text"] if c in raw_rr.columns]).reset_index(drop=True)
    wc(source_rules,out/"gold_v2_14b_coreb_source_rule_rows.csv")
    if "profit" in target.columns: profit_col="profit"
    elif "profit_r" in target.columns: profit_col="profit_r"
    else: profit_col=None
    summary_rows=[]
    if profit_col:
        for ds,g in target.groupby("dataset") if "dataset" in target.columns else [("ALL",target)]:
            row=metrics(g[profit_col]); row.update(dataset=ds, view="rr125_top_ledgers_same_count_ge15"); summary_rows.append(row)
    perf=pd.DataFrame(summary_rows); wc(perf,out/"gold_v2_14b_coreb_target_performance_summary.csv")
    j13c3=rj(s13c3) if ex(s13c3) else {}; j13c4=rj(s13c4) if ex(s13c4) else {}
    c3_blocked = (j13c3.get("status") or "").find("FAILED")>=0 or j13c3.get("live_coreb_allowed") is False
    c4_found_algo = bool(j13c4.get("found_original_cluster_membership_algorithm", False))
    c4_live_allowed = bool(j13c4.get("coreb_live_evaluator_allowed", False))
    top_has_cluster="cluster_id" in top.columns
    top_has_same="same_count" in top.columns
    raw_has_cluster="cluster_id" in raw.columns
    target_rows=int(len(target)); source_rule_count=int(len(source_rules))
    checks=pd.DataFrame([
        ["14B-C001","raw ledger readable",len(raw)>0,True,"PASS" if len(raw)>0 else "STOP"],
        ["14B-C002","top ledger readable",len(top)>0,True,"PASS" if len(top)>0 else "STOP"],
        ["14B-C003","top has cluster_id",top_has_cluster,True,"PASS" if top_has_cluster else "STOP"],
        ["14B-C004","top has same_count",top_has_same,True,"PASS" if top_has_same else "STOP"],
        ["14B-C005","target rows same_count>=15",target_rows,125,"PASS" if target_rows==125 else "REVIEW"],
        ["14B-C006","source rule rows",source_rule_count,12,"PASS" if source_rule_count==12 else "REVIEW"],
        ["14B-C007","raw has cluster_id",raw_has_cluster,True,"BLOCK_EXPECTED" if not raw_has_cluster else "PASS"],
        ["14B-C008","13C3 raw replay status",not c3_blocked,True,"BLOCK_EXPECTED" if c3_blocked else "PASS"],
        ["14B-C009","13C4 original algorithm found",c4_found_algo,True,"BLOCK_EXPECTED" if not c4_found_algo else "PASS"],
        ["14B-C010","CoreB live allowed",c4_live_allowed,True,"BLOCK_EXPECTED" if not c4_live_allowed else "PASS"],
    ],columns=["check_id","check","observed","expected","status"]); wc(checks,out/"gold_v2_14b_read_replay_checks.csv")
    safe_readable = len(raw)>0 and len(top)>0 and top_has_cluster and top_has_same and target_rows>0 and source_rule_count>0
    live_allowed = bool(raw_has_cluster and c4_found_algo and c4_live_allowed)
    status="COREB_SOURCE_TOP_LEDGER_READABLE_BUT_LIVE_REPLAY_BLOCKED_AUDIT_ONLY" if safe_readable and not live_allowed else ("COREB_LIVE_REPLAY_READY_REVIEW_REQUIRED_AUDIT_ONLY" if live_allowed else "COREB_SOURCE_READ_REPLAY_BLOCKED_AUDIT_ONLY")
    dec=pd.DataFrame([
        ["14B-D001","historical source top ledger readable",safe_readable,True,"PASS" if safe_readable else "STOP"],
        ["14B-D002","live same_count replay proven",live_allowed,True,"BLOCK_EXPECTED" if not live_allowed else "PASS"],
        ["14B-D003","CoreB live evaluator allowed",False,False,"PASS_BLOCKED_AS_EXPECTED"],
        ["14B-D004","next","14C_COREB_HISTORICAL_SOT_CANDIDATE_MAPPING_AUDIT_ONLY" if safe_readable else "STOP","review","INFO"],
    ],columns=["check_id","check","observed","expected","status"]); wc(dec,out/"gold_v2_14b_decision_matrix.csv")
    block=pd.DataFrame([
        ["14B-B004","COREB_LIVE_REPLAY","HARD","OPEN","CoreB live evaluator","Original clustering algorithm or row-level membership ledger is still required before live CoreB."],
        ["14B-B099","SAFETY","SAFETY","OPEN","external actions","All external actions remain false; final signal is still off."],
    ],columns=["blocker_id","component","severity","status","blocked_item","required_resolution"]); wc(block,out/"gold_v2_14b_blockers.csv")
    summary={"created_utc":now,"step":STEP,"status":status,"audit_only":True,"raw_rows":int(len(raw)),"raw_rr125_rows":int(len(raw_rr)),"top_rows":int(len(top)),"target_same_count_ge15_rows":target_rows,"source_rule_rows":source_rule_count,"top_has_cluster_id":top_has_cluster,"top_has_same_count":top_has_same,"raw_has_cluster_id":raw_has_cluster,"upstream_13c3_status":j13c3.get("status"),"upstream_13c4_status":j13c4.get("status"),"coreb_historical_sot_allowed":safe_readable,"coreb_live_evaluator_allowed":False,"final_signal_allowed":False,"external_actions":EXT,"next":"14C_COREB_HISTORICAL_SOT_CANDIDATE_MAPPING_AUDIT_ONLY" if safe_readable else "STOP"}
    wj(out/"gold_v2_14b_coreb_cluster_source_read_and_replay_summary.json",summary)
    wt(out/REPORT,"\n".join(["# GOLD V2 14B CoreB cluster source read and replay audit-only report","",f"Created UTC: {now}",f"Status: `{status}`","","## Checks",md(checks),"","## Decision",md(dec),"","## CoreB target performance",md(perf),"","## Blockers",md(block),"","CoreB historical SOT is readable, but live evaluator remains blocked unless original same_count clustering is restored."]))
    print(json.dumps(clean(summary|{"output_dir":str(out)}),ensure_ascii=False,indent=2,allow_nan=False))
    return 0 if safe_readable else 2
if __name__=="__main__": raise SystemExit(main())
