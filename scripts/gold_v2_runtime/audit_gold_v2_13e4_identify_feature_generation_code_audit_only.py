#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations
import json, math, os, zipfile
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd

STEP="13E4_IDENTIFY_FEATURE_GENERATION_CODE_AUDIT_ONLY"
SRC="gold_v2_13e3_medium_feature_source_locator_audit_only"
OUT="gold_v2_13e4_identify_feature_generation_code_audit_only"
REPORT="GOLD_V2_13E4_IDENTIFY_FEATURE_GENERATION_CODE_AUDIT_ONLY_REPORT.md"
EXT={"discord_send_allowed":False,"mt5_order_allowed":False,"ai_api_allowed":False,"live_hook_allowed":False}
TERMS=["abc_stack_cap_2025_2026_portfolio_ledger.csv","gold_v2_ABC_stack_cap_2025_2026_validation_outputs","coreb_refined_combined_ledgers.csv","gold_v2_coreb_refined_probe_outputs","gold_v2_13b_corea_source_cluster_ledger_normalized.csv","range96","trend_eff96","ret96","tr_mean_32"]
EXTS={".py",".bat",".ps1",".md",".json",".yaml",".yml",".txt"}
MAX_FILES=2500
MAX_BYTES=2_000_000
SKIP={".git","__pycache__","venv",".venv","site-packages","node_modules","logs","cache"}
PIN_DIRS=["gold_v2_ABC_stack_cap_2025_2026_validation_outputs","gold_v2_coreb_refined_probe_outputs","gold_v2_13b_corea_executable_mapping_freeze_audit_only"]

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
def md(d,n=60):
    if d.empty: return "_No rows._"
    d=d.head(n); z=["| "+" | ".join(map(str,d.columns))+" |","| "+" | ".join(["---"]*len(d.columns))+" |"]
    for _,r in d.iterrows(): z.append("| "+" | ".join(str(r[c]).replace("|","\\|").replace("\n"," ") for c in d.columns)+" |")
    return "\n".join(z)
def read_text(p):
    try:
        if os.path.getsize(lp(p))>MAX_BYTES: return ""
    except Exception: pass
    for enc in ["utf-8","utf-8-sig","cp932","latin-1"]:
        try:
            with open(lp(p),"r",encoding=enc,errors="ignore") as f: return f.read(MAX_BYTES)
        except Exception: pass
    return ""
def wanted_path(p):
    parts={x.lower() for x in p.parts}
    if parts & SKIP: return False
    if p.suffix.lower() not in EXTS: return False
    s=str(p).lower()
    if "fx_outputs" in s and not any(d.lower() in s for d in PIN_DIRS): return False
    return True
def roots():
    rs=[rr()/"scripts", rr()/"docs", rr()/"configs", rr()]
    rs += [fx()/d for d in PIN_DIRS]
    return [p for p in rs if ex(p)]
def inventory():
    rows=[]; seen=set()
    for root in roots():
        try:
            it=root.rglob("*") if root.is_dir() else [root]
            for p in it:
                if len(rows)>=MAX_FILES: break
                if not p.is_file() or not wanted_path(p): continue
                s=str(p)
                if s in seen: continue
                seen.add(s)
                try: size=os.path.getsize(lp(p))
                except Exception: size=None
                rows.append({"path":s,"name":p.name,"suffix":p.suffix.lower(),"bytes":size,"root":str(root)})
        except Exception: pass
    return pd.DataFrame(rows)
def score(p):
    txt=read_text(p); low=txt.lower(); name=p.name.lower()
    hits=[]; score=0
    for t in TERMS:
        tl=t.lower()
        if tl in low or tl in name:
            hits.append(t); score += 10 if ".csv" in t or "outputs" in t else 1
    strong=any(t.lower() in low for t in TERMS[:5]); feat=sum(1 for t in TERMS[5:] if t.lower() in low)
    return {"path":str(p),"name":p.name,"suffix":p.suffix.lower(),"hit_terms":"|".join(hits),"hit_count":len(hits),"feature_hit_count":feat,"strong_output_hit":strong,"score":score,"bytes":os.path.getsize(lp(p)) if ex(p) else None}, txt
def snippets(p,txt):
    rows=[]; lines=txt.splitlines()
    for i,l in enumerate(lines):
        if any(t.lower() in l.lower() for t in TERMS):
            rows.append({"path":str(p),"line":i+1,"snippet":"\n".join(lines[max(0,i-2):min(len(lines),i+3)])[:2000]})
            if len(rows)>=8: break
    return rows

def main():
    out=od(); now=datetime.now(timezone.utc).isoformat(); srcsum=fx()/SRC/"gold_v2_13e3_medium_feature_source_locator_summary.json"
    ia=pd.DataFrame([{"name":srcsum.name,"path":str(srcsum),"exists":ex(srcsum)}]); wcsv(ia,out/"gold_v2_13e4_input_audit.csv")
    inv=inventory(); wcsv(inv,out/"gold_v2_13e4_code_candidate_inventory.csv")
    rows=[]; sn=[]
    for _,r in inv.iterrows():
        row,txt=score(Path(r.path))
        if row["hit_count"]>0:
            rows.append(row); sn.extend(snippets(Path(r.path),txt))
    hits=pd.DataFrame(rows)
    if hits.empty: hits=pd.DataFrame(columns=["path","name","suffix","hit_terms","hit_count","feature_hit_count","strong_output_hit","score","bytes"])
    hits=hits.sort_values(["strong_output_hit","score","feature_hit_count","hit_count"],ascending=[False,False,False,False]); wcsv(hits,out/"gold_v2_13e4_code_candidate_hits.csv")
    snip=pd.DataFrame(sn); wcsv(snip,out/"gold_v2_13e4_best_code_candidate_snippets.csv")
    found=bool(len(hits) and bool(hits.iloc[0].strong_output_hit) and int(hits.iloc[0].feature_hit_count)>=1)
    status="FEATURE_GENERATION_CODE_CANDIDATE_FOUND_AUDIT_ONLY" if found else "FEATURE_GENERATION_CODE_CANDIDATE_NOT_FOUND_AUDIT_ONLY"
    b=pd.DataFrame(([] if found else [["13E4-B003","CODE_SOURCE","HARD","OPEN","generation code locator","No code file tied output ledger name/folder to feature columns in targeted scan."]])+[["13E4-B004","REPLAY","HARD","OPEN","code replay","Candidate code must be read and replayed before live evaluator."],["13E4-B099","SAFETY","SAFETY","OPEN","external actions","All external actions remain false."]],columns=["blocker_id","component","severity","status","blocked_item","required_resolution"]); wcsv(b,out/"gold_v2_13e4_blockers.csv")
    dec=pd.DataFrame([["13E4-C001","candidate code files scanned",len(inv),f"<= {MAX_FILES}","PASS" if len(inv)>0 else "STOP"],["13E4-C002","strong output-linked hit",bool(found),True,"PASS" if found else "STOP"],["13E4-C003","next","13E5_READ_REPLAY_FEATURE_GENERATION_CODE_AUDIT_ONLY" if found else "STOP_FIND_OR_PROVIDE_GENERATION_CODE","review","INFO"]],columns=["check_id","check","observed","expected","status"]); wcsv(dec,out/"gold_v2_13e4_decision_matrix.csv")
    best=hits.head(1).to_dict("records")[0] if len(hits) else None
    wjson(out/"gold_v2_13e4_identify_feature_generation_code_summary.json",{"created_utc":now,"step":STEP,"status":status,"audit_only":True,"targeted_scan":True,"max_files":MAX_FILES,"code_files_scanned":len(inv),"hit_files":len(hits),"best_candidate":best,"medium_live_evaluator_allowed":False,"final_signal_allowed":False,"step13_allowed":False,"external_actions":EXT})
    wtxt(out/REPORT,"\n".join(["# GOLD V2 13E4 identify feature generation code audit-only report","",f"Created UTC: {now}",f"Status: `{status}`","","## Scan scope","- targeted_scan: true",f"- max_files: {MAX_FILES}","- FX_OUTPUTS scan is limited to 13E3 full-match source folders.","","## Best code candidates",md(hits.head(20)),"","## Decision",md(dec),"","## Blockers",md(b),"","External actions remain false."]))
    z=fx()/"gold_v2_13e4_identify_feature_generation_code_audit.zip"
    if ex(z): os.remove(lp(z))
    with zipfile.ZipFile(lp(z),"w",zipfile.ZIP_DEFLATED) as zz:
        for p in out.iterdir(): zz.write(lp(p),arcname=p.name)
    print(json.dumps(clean({"status":status,"output_dir":str(out),"zip":str(z),"best_candidate":best,"audit_only":True,"external_actions":EXT}),ensure_ascii=False,indent=2,allow_nan=False))
    return 0 if found else 2
if __name__=="__main__": raise SystemExit(main())
