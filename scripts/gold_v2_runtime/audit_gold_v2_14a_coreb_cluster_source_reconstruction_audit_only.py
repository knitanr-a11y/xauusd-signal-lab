#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations
import json, math, os
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd

STEP="14A_COREB_CLUSTER_SOURCE_RECONSTRUCTION_AUDIT_ONLY"
OUT="gold_v2_14a_coreb_cluster_source_reconstruction_audit_only"
REPORT="GOLD_V2_14A_COREB_CLUSTER_SOURCE_RECONSTRUCTION_AUDIT_ONLY_REPORT.md"
KEYS=["cluster_id","same_direction_count","same_count","top_candidate_id","top_variant","coreb","rr125","refined","component"]
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
def safe_read_cols(p):
    try:
        return list(pd.read_csv(lp(p),nrows=5).columns), None
    except Exception as e:
        return [], str(e)
def rel(p):
    try: return str(Path(p).resolve().relative_to(rr().resolve()))
    except Exception: return str(p)
def iter_files(root, exts, max_files=5000):
    out=[]
    if not ex(root): return out
    skip={".git","__pycache__",".venv","venv","site-packages","node_modules"}
    for dp, dns, fns in os.walk(lp(root)):
        dns[:] = [d for d in dns if d not in skip]
        for fn in fns:
            if len(out)>=max_files: return out
            p=Path(dp)/fn
            if p.suffix.lower() in exts: out.append(p)
    return out

def main():
    out=od(); now=datetime.now(timezone.utc).isoformat()
    targets=[fx()/"gold_v2_coreb_refined_probe_outputs",fx()/"gold_v2_rr125_second_core_probe_outputs",rr()/"scripts"/"gold_v2_runtime",rr()/"docs"/"gold_v2"]
    ia=pd.DataFrame([{"target":str(t),"exists":ex(t)} for t in targets]); wc(ia,out/"gold_v2_14a_input_audit.csv")
    csv_files=[]
    for t in targets[:2]: csv_files += iter_files(t,{".csv"},max_files=3000)
    inv=[]; colinv=[]
    for p in csv_files:
        cols,err=safe_read_cols(p); low=[c.lower() for c in cols]
        hits=[k for k in KEYS if any(k in c for c in low)]
        score=0
        for k in hits: score += {"cluster_id":5,"same_direction_count":5,"same_count":4,"top_candidate_id":3,"top_variant":3,"coreb":2,"rr125":2,"refined":2,"component":1}.get(k,1)
        inv.append({"path":str(p),"name":p.name,"cols_count":len(cols),"keyword_hits":";".join(hits),"score":score,"read_error":err})
        for c in cols:
            cl=c.lower()
            if any(k in cl for k in KEYS): colinv.append({"path":str(p),"column":c,"keyword_matches":";".join([k for k in KEYS if k in cl])})
    invdf=pd.DataFrame(inv).sort_values(["score","name"],ascending=[False,True]) if inv else pd.DataFrame(columns=["path","name","cols_count","keyword_hits","score","read_error"])
    coldf=pd.DataFrame(colinv)
    wc(invdf,out/"gold_v2_14a_csv_file_inventory.csv"); wc(coldf,out/"gold_v2_14a_cluster_column_inventory.csv")
    code_files=[]
    for t in targets[2:]: code_files += iter_files(t,{".py",".md",".json",".yml",".yaml",".bat",".txt"},max_files=3000)
    hits=[]
    for p in code_files:
        try:
            txt=Path(lp(p)).read_text(encoding="utf-8",errors="ignore")
        except Exception as e:
            continue
        low=txt.lower(); kws=[k for k in KEYS if k in low]
        if not kws: continue
        lines=txt.splitlines(); snippets=[]
        for i,line in enumerate(lines,1):
            ll=line.lower()
            if any(k in ll for k in KEYS):
                snippets.append(f"L{i}: {line.strip()[:240]}")
                if len(snippets)>=6: break
        score=sum({"cluster_id":5,"same_direction_count":5,"same_count":4,"top_candidate_id":3,"top_variant":3,"coreb":2,"rr125":2,"refined":2,"component":1}.get(k,1) for k in kws)
        hits.append({"path":rel(p),"keyword_hits":";".join(kws),"score":score,"snippet":" || ".join(snippets)})
    hitdf=pd.DataFrame(hits).sort_values(["score","path"],ascending=[False,True]) if hits else pd.DataFrame(columns=["path","keyword_hits","score","snippet"])
    wc(hitdf,out/"gold_v2_14a_code_keyword_hits.csv")
    cand=[]
    for _,r in invdf.head(80).iterrows():
        cand.append({"type":"csv","path":r["path"],"score":int(r["score"]),"evidence":r["keyword_hits"],"reason":"CSV columns contain CoreB cluster reconstruction keywords."})
    for _,r in hitdf.head(80).iterrows():
        cand.append({"type":"code","path":r["path"],"score":int(r["score"]),"evidence":r["keyword_hits"],"reason":"Code/doc contains CoreB cluster reconstruction keywords."})
    canddf=pd.DataFrame(cand).sort_values(["score","type","path"],ascending=[False,True,True]) if cand else pd.DataFrame(columns=["type","path","score","evidence","reason"])
    wc(canddf,out/"gold_v2_14a_coreb_candidate_scores.csv")
    has_cluster=bool((coldf.get("column",pd.Series(dtype=str)).astype(str).str.lower()=="cluster_id").any()) if not coldf.empty else False
    has_same=bool(coldf.get("column",pd.Series(dtype=str)).astype(str).str.lower().isin(["same_direction_count","same_count"]).any()) if not coldf.empty else False
    has_candidates=not canddf.empty
    status="COREB_CLUSTER_SOURCE_CANDIDATES_FOUND_AUDIT_ONLY" if has_cluster and has_same else ("COREB_CLUSTER_SOURCE_CANDIDATES_PARTIAL_AUDIT_ONLY" if has_candidates else "COREB_CLUSTER_SOURCE_CANDIDATES_NOT_FOUND_AUDIT_ONLY")
    dec=pd.DataFrame([
        ["14A-C001","csv/code candidates found",has_candidates,True,"PASS" if has_candidates else "STOP"],
        ["14A-C002","cluster_id column found",has_cluster,True,"PASS" if has_cluster else "PARTIAL"],
        ["14A-C003","same_direction_count or same_count found",has_same,True,"PASS" if has_same else "PARTIAL"],
        ["14A-C004","next","14B_COREB_CLUSTER_SOURCE_READ_AND_REPLAY_AUDIT_ONLY" if has_candidates else "STOP","review","INFO"],
    ],columns=["check_id","check","observed","expected","status"]); wc(dec,out/"gold_v2_14a_decision_matrix.csv")
    block=pd.DataFrame([
        ["14A-B004","COREB_REPLAY","HARD","OPEN","CoreB live evaluator","Need 14B to read top candidates and replay cluster/same_count source chain."],
        ["14A-B099","SAFETY","SAFETY","OPEN","external actions","All external actions remain false; final signal is still off."],
    ],columns=["blocker_id","component","severity","status","blocked_item","required_resolution"]); wc(block,out/"gold_v2_14a_blockers.csv")
    summary={"created_utc":now,"step":STEP,"status":status,"audit_only":True,"csv_files_scanned":len(csv_files),"code_files_scanned":len(code_files),"candidate_count":len(canddf),"has_cluster_id_column":has_cluster,"has_same_count_column":has_same,"external_actions":EXT,"next":"14B_COREB_CLUSTER_SOURCE_READ_AND_REPLAY_AUDIT_ONLY" if has_candidates else "STOP"}
    wj(out/"gold_v2_14a_coreb_cluster_source_reconstruction_summary.json",summary)
    wt(out/REPORT,"\n".join(["# GOLD V2 14A CoreB cluster source reconstruction audit-only report","",f"Created UTC: {now}",f"Status: `{status}`","", "## Decision",md(dec),"","## Top candidates",md(canddf.head(30)),"","## Blockers",md(block),"","External actions remain false. Final signal remains off."]))
    print(json.dumps(clean(summary|{"output_dir":str(out)}),ensure_ascii=False,indent=2,allow_nan=False))
    return 0 if has_candidates else 2
if __name__=="__main__": raise SystemExit(main())
