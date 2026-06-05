#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations
import json, os, re, math
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd

STEP="14D_COREB_ORIGINAL_CLUSTERING_CANDIDATE_REVIEW_AUDIT_ONLY"
OUT="gold_v2_14d_coreb_original_clustering_candidate_review_audit_only"
REPORT="GOLD_V2_14D_COREB_ORIGINAL_CLUSTERING_CANDIDATE_REVIEW_AUDIT_ONLY_REPORT.md"
EXT={"discord_send_allowed":False,"mt5_order_allowed":False,"ai_api_allowed":False,"live_hook_allowed":False}
TEXT_SUFFIXES={".py",".md",".json",".bat",".txt",".yml",".yaml",".ps1"}
GENERATED=["audit_gold_v2_13","audit_gold_v2_14","gold_v2_13","gold_v2_14","freeze_gold_v2_final_portfolio","evaluate_gold_v2_corea_coreb_medium","freeze_coreb_same_count_source_universe","combined_evaluator_replay"]
KEYS=["rr125_top_ledgers","rr125_raw_signal_ledger","same_count","cluster_id","source_rule_count","rr125_from_rr1_rules","top_ledgers"]

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
    if not ex(fx()): return fx()/name
    m=list(Path(lp(fx())).rglob(name)); return m[0] if m else fx()/name
def od():
    p=fx()/OUT; os.makedirs(lp(p),exist_ok=True); return p
def wt(p,s):
    os.makedirs(lp(Path(p).parent),exist_ok=True)
    with open(lp(p),"w",encoding="utf-8",newline="") as f: f.write(s)
def wc(d,p): d.to_csv(lp(p),index=False,encoding="utf-8-sig")
def rj(p):
    try:
        with open(lp(p),"r",encoding="utf-8") as f: return json.load(f)
    except Exception: return {}
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
    for _,r in d.head(limit).iterrows(): z.append("| "+" | ".join(str(r[c]).replace("|","\\|").replace("\n"," ") for c in d.columns)+" |")
    return "\n".join(z)
def read_text(p):
    try: return Path(lp(p)).read_bytes()[:2_000_000].decode("utf-8",errors="ignore")
    except Exception: return ""
def rel(p):
    try: return str(Path(p).resolve().relative_to(rr().resolve())).replace("\\","/")
    except Exception: return str(p)

def classify(p):
    text=read_text(p); low=text.lower(); path_low=rel(p).lower()
    hits=[k for k in KEYS if k in low or k in path_low]
    if not hits: return None
    is_py=Path(p).suffix.lower()==".py"
    generated=any(g in path_low for g in GENERATED)
    reads_raw="rr125_raw_signal_ledger" in low
    reads_top="rr125_top_ledgers" in low or "top_ledgers" in low
    writes_top=bool(re.search(r"to_csv\s*\([^\n]*(rr125_top_ledgers|top_ledgers)",low)) or ("to_csv" in low and "top_ledgers" in low)
    assigns_cluster=bool(re.search(r"\[\s*[\"']cluster_id[\"']\s*\]\s*=",text)) or bool(re.search(r"\.assign\s*\([^\)]*cluster_id",low))
    assigns_same=bool(re.search(r"\[\s*[\"']same_count[\"']\s*\]\s*=",text)) or bool(re.search(r"\.assign\s*\([^\)]*same_count",low))
    group="groupby" in low or "group by" in low
    membership=any(w in low for w in ["membership","member","cluster_members","connected","component","overlap"])
    strict=is_py and reads_raw and writes_top and assigns_cluster and assigns_same and group and not generated
    if strict:
        cls="STRICT_ORIGINAL_CLUSTERING_CANDIDATE"
        live_candidate=True
        reason="Meets strict raw->top-ledger generation hints; replay parity still required."
    elif is_py and reads_top and not writes_top:
        cls="SOT_READER_ONLY"; live_candidate=False; reason="Reads existing top-ledger; not original clustering generator."
    elif generated:
        cls="AUDIT_OR_POST_HOC"; live_candidate=False; reason="Generated audit/freeze helper or later reconstruction script."
    elif Path(p).suffix.lower() in {".md",".json",".txt",".yml",".yaml"}:
        cls="DOC_OR_CONFIG"; live_candidate=False; reason="Source definition or documentation only."
    else:
        cls="MENTIONS_ONLY"; live_candidate=False; reason="Mentions keywords but lacks strict generation evidence."
    return {"path":rel(p),"classification":cls,"strict_live_algorithm_candidate":live_candidate,"keyword_hits":"|".join(hits),"generated_or_post_hoc":generated,"reads_raw":reads_raw,"reads_top":reads_top,"writes_top":writes_top,"assigns_cluster_id":assigns_cluster,"assigns_same_count":assigns_same,"has_groupby":group,"has_membership_words":membership,"reason":reason}

def main():
    out=od(); now=datetime.now(timezone.utc).isoformat()
    s14c=find_file("gold_v2_14c_coreb_historical_sot_candidate_mapping_summary.json")
    s13c5=find_file("gold_v2_13c5_review_restored_clustering_script_parity_summary.json")
    ia=pd.DataFrame([{"name":p.name,"path":str(p),"exists":ex(p)} for p in [s14c,s13c5]]); wc(ia,out/"gold_v2_14d_input_audit.csv")
    rows=[]; skip={".git","__pycache__",".venv","venv","node_modules"}
    for dp,dns,fns in os.walk(lp(rr())):
        dns[:]=[d for d in dns if d not in skip]
        for fn in fns:
            p=Path(dp)/fn
            if p.suffix.lower() not in TEXT_SUFFIXES: continue
            rec=classify(p)
            if rec: rows.append(rec)
    review=pd.DataFrame(rows)
    if review.empty: review=pd.DataFrame(columns=["path","classification","strict_live_algorithm_candidate","reason"])
    else: review=review.sort_values(["strict_live_algorithm_candidate","classification","path"],ascending=[False,True,True])
    wc(review,out/"gold_v2_14d_candidate_file_review.csv")
    counts=review.groupby("classification").size().reset_index(name="file_count") if not review.empty else pd.DataFrame(columns=["classification","file_count"])
    wc(counts,out/"gold_v2_14d_classification_counts.csv")
    strict=review[review.get("strict_live_algorithm_candidate",pd.Series(dtype=bool)).astype(bool)].copy() if not review.empty else pd.DataFrame()
    wc(strict,out/"gold_v2_14d_strict_original_clustering_candidates.csv")
    j14c=rj(s14c); j13c5=rj(s13c5)
    strict_count=int(len(strict))
    status="COREB_ORIGINAL_CLUSTERING_CANDIDATE_CONFIRMED_REPLAY_REQUIRED_AUDIT_ONLY" if strict_count else "COREB_ORIGINAL_CLUSTERING_CANDIDATE_NOT_CONFIRMED_LIVE_BLOCKED_AUDIT_ONLY"
    dec=pd.DataFrame([
        ["14D-D001","14C historical-only mapping",j14c.get("status"),"COREB_HISTORICAL_SOT_CANDIDATE_MAPPING_BUILT_AUDIT_ONLY_LIVE_BLOCKED","PASS" if j14c.get("status")=="COREB_HISTORICAL_SOT_CANDIDATE_MAPPING_BUILT_AUDIT_ONLY_LIVE_BLOCKED" else "REVIEW"],
        ["14D-D002","13C5 strict candidates",j13c5.get("true_original_clustering_candidate_files"),0,"INFO"],
        ["14D-D003","14D strict candidates",strict_count,0,"BLOCK_EXPECTED" if strict_count==0 else "REPLAY_REQUIRED"],
        ["14D-D004","CoreB live evaluator allowed",False,False,"PASS_BLOCKED_AS_EXPECTED"],
        ["14D-D005","next","15A_COREA_A_GATE_SOURCE_RECONSTRUCTION_AUDIT_ONLY" if strict_count==0 else "14E_REPLAY_STRICT_COREB_CLUSTERING_CANDIDATE_AUDIT_ONLY","review","INFO"],
    ],columns=["check_id","check","observed","expected","status"]); wc(dec,out/"gold_v2_14d_decision_matrix.csv")
    block=pd.DataFrame([
        ["14D-B004","COREB_LIVE_REPLAY","HARD","OPEN","CoreB live evaluator","Need strict original clustering algorithm and replay parity before live CoreB."],
        ["14D-B099","SAFETY","SAFETY","OPEN","external actions","All external actions remain false; final signal is still off."],
    ],columns=["blocker_id","component","severity","status","blocked_item","required_resolution"]); wc(block,out/"gold_v2_14d_blockers.csv")
    summary={"created_utc":now,"step":STEP,"status":status,"audit_only":True,"reviewed_files":int(len(review)),"strict_original_clustering_candidate_files":strict_count,"coreb_historical_sot_allowed":True,"coreb_live_evaluator_allowed":False,"final_signal_allowed":False,"external_actions":EXT,"next":"15A_COREA_A_GATE_SOURCE_RECONSTRUCTION_AUDIT_ONLY" if strict_count==0 else "14E_REPLAY_STRICT_COREB_CLUSTERING_CANDIDATE_AUDIT_ONLY"}
    wj(out/"gold_v2_14d_coreb_original_clustering_candidate_review_summary.json",summary)
    wt(out/REPORT,"\n".join(["# GOLD V2 14D CoreB original clustering candidate review audit-only report","",f"Created UTC: {now}",f"Status: `{status}`","","## Classification counts",md(counts),"","## Strict original clustering candidates",md(strict),"","## Decision",md(dec),"","## Blockers",md(block),"","CoreB remains historical-only unless strict clustering replay parity is proven."]))
    print(json.dumps(clean(summary|{"output_dir":str(out)}),ensure_ascii=False,indent=2,allow_nan=False))
    return 0
if __name__=="__main__": raise SystemExit(main())
