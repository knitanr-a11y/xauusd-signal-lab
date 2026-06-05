#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations
import json, math, os
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd

STEP="15A_COREA_A_GATE_SOURCE_RECONSTRUCTION_AUDIT_ONLY"
OUT="gold_v2_15a_corea_a_gate_source_reconstruction_audit_only"
REPORT="GOLD_V2_15A_COREA_A_GATE_SOURCE_RECONSTRUCTION_AUDIT_ONLY_REPORT.md"
KEYS=["is_A","signal_ABC","signal_fixed_ABC","candidateA_top5_by_month","chosen_names","tail_hard","top5","all-consensus","all_consensus","stack","KEEP","fold4_rules","abc_stack_cap","CAP5","CAP3"]
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
    for _,r in d.head(limit).iterrows(): z.append("| "+" | ".join(str(r[c]).replace("|","\\|").replace("\n"," ") for c in d.columns)+" |")
    return "\n".join(z)
def iter_files(root,exts,max_files=6000):
    out=[]
    if not ex(root): return out
    skip={".git","__pycache__",".venv","venv","site-packages","node_modules"}
    for dp,dns,fns in os.walk(lp(root)):
        dns[:]=[d for d in dns if d not in skip]
        for fn in fns:
            if len(out)>=max_files: return out
            p=Path(dp)/fn
            if p.suffix.lower() in exts: out.append(p)
    return out
def rel(p):
    try: return str(Path(p).resolve().relative_to(rr().resolve())).replace("\\","/")
    except Exception: return str(p)
def read_cols(p):
    try: return list(pd.read_csv(lp(p),nrows=5).columns), None
    except Exception as e: return [], str(e)
def key_hits_in_cols(cols):
    low=[c.lower() for c in cols]
    return [k for k in KEYS if any(k.lower() in c for c in low)]
def score_hits(hits):
    weights={"is_A":8,"signal_ABC":7,"signal_fixed_ABC":7,"candidateA_top5_by_month":8,"chosen_names":6,"tail_hard":7,"top5":5,"all-consensus":7,"all_consensus":7,"stack":4,"KEEP":5,"fold4_rules":8,"abc_stack_cap":5,"CAP5":3,"CAP3":2}
    return sum(weights.get(k,1) for k in hits)

def main():
    out=od(); now=datetime.now(timezone.utc).isoformat()
    targets=[fx()/"gold_v2_ABC_stack_cap_2025_2026_validation_outputs",fx()/"gold_v2_13b_corea_executable_mapping_freeze_audit_only",rr()/"configs"/"gold_v2",rr()/"scripts"/"gold_v2_runtime",rr()/"docs"/"gold_v2"]
    ia=pd.DataFrame([{"target":str(t),"exists":ex(t)} for t in targets]); wc(ia,out/"gold_v2_15a_input_audit.csv")
    csv_files=[]
    for t in targets[:2]: csv_files += iter_files(t,{".csv"},max_files=4000)
    inv=[]; colrows=[]
    for p in csv_files:
        cols,err=read_cols(p); hits=key_hits_in_cols(cols); score=score_hits(hits)
        inv.append({"path":str(p),"name":p.name,"cols_count":len(cols),"keyword_hits":";".join(hits),"score":score,"read_error":err})
        for c in cols:
            ch=[k for k in KEYS if k.lower() in c.lower()]
            if ch: colrows.append({"path":str(p),"column":c,"keyword_matches":";".join(ch)})
    invdf=pd.DataFrame(inv).sort_values(["score","name"],ascending=[False,True]) if inv else pd.DataFrame(columns=["path","name","cols_count","keyword_hits","score","read_error"])
    coldf=pd.DataFrame(colrows)
    wc(invdf,out/"gold_v2_15a_csv_file_inventory.csv"); wc(coldf,out/"gold_v2_15a_corea_column_inventory.csv")
    code_files=[]
    for t in targets[2:]: code_files += iter_files(t,{".py",".md",".json",".bat",".txt",".yml",".yaml",".ps1"},max_files=5000)
    hits=[]
    for p in code_files:
        try: txt=Path(lp(p)).read_text(encoding="utf-8",errors="ignore")
        except Exception: continue
        low=txt.lower(); kws=[k for k in KEYS if k.lower() in low or k.lower() in rel(p).lower()]
        if not kws: continue
        snippets=[]
        for i,line in enumerate(txt.splitlines(),1):
            ll=line.lower()
            if any(k.lower() in ll for k in KEYS):
                snippets.append(f"L{i}: {line.strip()[:240]}")
                if len(snippets)>=8: break
        generated=any(x in rel(p).lower() for x in ["audit_gold_v2_13","audit_gold_v2_14","audit_gold_v2_15","gold_v2_13","gold_v2_14","gold_v2_15"])
        hits.append({"path":rel(p),"keyword_hits":";".join(kws),"score":score_hits(kws) - (10 if generated else 0),"generated_or_audit_file":generated,"snippet":" || ".join(snippets)})
    hitdf=pd.DataFrame(hits).sort_values(["score","path"],ascending=[False,True]) if hits else pd.DataFrame(columns=["path","keyword_hits","score","generated_or_audit_file","snippet"])
    wc(hitdf,out/"gold_v2_15a_code_keyword_hits.csv")
    cand=[]
    for _,r in invdf.head(100).iterrows(): cand.append({"type":"csv","path":r.path,"score":int(r.score),"evidence":r.keyword_hits,"reason":"CSV columns contain CoreA A-gate source keywords."})
    for _,r in hitdf.head(100).iterrows(): cand.append({"type":"code","path":r.path,"score":int(r.score),"evidence":r.keyword_hits,"reason":"Code/doc/config contains CoreA A-gate source keywords."})
    canddf=pd.DataFrame(cand).sort_values(["score","type","path"],ascending=[False,True,True]) if cand else pd.DataFrame(columns=["type","path","score","evidence","reason"])
    wc(canddf,out/"gold_v2_15a_candidate_scores.csv")
    has_is_a=bool(coldf.get("column",pd.Series(dtype=str)).astype(str).str.lower().eq("is_a").any()) if not coldf.empty else False
    has_sig=bool(coldf.get("column",pd.Series(dtype=str)).astype(str).str.lower().isin(["signal_abc","signal_fixed_abc"]).any()) if not coldf.empty else False
    has_top5=bool((invdf["name"].astype(str).str.contains("top5|candidateA",case=False,na=False)).any()) if not invdf.empty else False
    has_candidates=not canddf.empty
    status="COREA_A_GATE_SOURCE_CANDIDATES_FOUND_AUDIT_ONLY" if has_is_a and has_sig and has_top5 else ("COREA_A_GATE_SOURCE_CANDIDATES_PARTIAL_AUDIT_ONLY" if has_candidates else "COREA_A_GATE_SOURCE_CANDIDATES_NOT_FOUND_AUDIT_ONLY")
    dec=pd.DataFrame([
        ["15A-C001","csv/code candidates found",has_candidates,True,"PASS" if has_candidates else "STOP"],
        ["15A-C002","is_A column found",has_is_a,True,"PASS" if has_is_a else "PARTIAL"],
        ["15A-C003","signal_ABC column found",has_sig,True,"PASS" if has_sig else "PARTIAL"],
        ["15A-C004","candidateA/top5 evidence found",has_top5,True,"PASS" if has_top5 else "PARTIAL"],
        ["15A-C005","next","15B_COREA_A_GATE_SOURCE_READ_AND_REPLAY_AUDIT_ONLY" if has_candidates else "STOP","review","INFO"],
    ],columns=["check_id","check","observed","expected","status"]); wc(dec,out/"gold_v2_15a_decision_matrix.csv")
    block=pd.DataFrame([
        ["15A-B001","COREA_A_GATE","HARD","OPEN","CoreA live evaluator","Need 15B to read top candidates and determine whether A-gate is executable or historical-only."],
        ["15A-B099","SAFETY","SAFETY","OPEN","external actions","All external actions remain false; final signal is still off."],
    ],columns=["blocker_id","component","severity","status","blocked_item","required_resolution"]); wc(block,out/"gold_v2_15a_blockers.csv")
    summary={"created_utc":now,"step":STEP,"status":status,"audit_only":True,"csv_files_scanned":len(csv_files),"code_files_scanned":len(code_files),"candidate_count":len(canddf),"has_is_A_column":has_is_a,"has_signal_ABC_column":has_sig,"has_candidateA_top5_evidence":has_top5,"corea_live_evaluator_allowed":False,"final_signal_allowed":False,"external_actions":EXT,"next":"15B_COREA_A_GATE_SOURCE_READ_AND_REPLAY_AUDIT_ONLY" if has_candidates else "STOP"}
    wj(out/"gold_v2_15a_corea_a_gate_source_reconstruction_summary.json",summary)
    wt(out/REPORT,"\n".join(["# GOLD V2 15A CoreA A-gate source reconstruction audit-only report","",f"Created UTC: {now}",f"Status: `{status}`","","## Decision",md(dec),"","## Top candidates",md(canddf.head(30)),"","## Blockers",md(block),"","CoreA live evaluator remains disabled."]))
    print(json.dumps(clean(summary|{"output_dir":str(out)}),ensure_ascii=False,indent=2,allow_nan=False))
    return 0 if has_candidates else 2
if __name__=="__main__": raise SystemExit(main())
