#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations
import json, math, os
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd
STEP="13K_MEDIUM_TIER2_HVT_CANDIDATE_MAPPING_AUDIT"
OUT="gold_v2_13k_medium_tier2_hvt_candidate_mapping_audit"
REPORT="GOLD_V2_13K_MEDIUM_TIER2_HVT_CANDIDATE_MAPPING_AUDIT_REPORT.md"
EXT={"discord_enabled":False,"mt5_enabled":False,"ai_api_enabled":False,"external_hook_enabled":False}
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
def md(d):
    if d.empty: return "_No rows._"
    z=["| "+" | ".join(map(str,d.columns))+" |","| "+" | ".join(["---"]*len(d.columns))+" |"]
    for _,r in d.iterrows(): z.append("| "+" | ".join(str(r[c]).replace("|","\\|") for c in d.columns)+" |")
    return "\n".join(z)
def cond_map(cfg):
    return {c["feature"]:{"op":c.get("operator"),"value":c.get("value")} for c in cfg.get("rule",{}).get("conditions",[])}
def main():
    out=od(); now=datetime.now(timezone.utc).isoformat()
    cfg=rr()/"configs"/"gold_v2"/"medium_tier2_hvt_candidate_mapping_20260605.json"
    patch=fx()/"gold_v2_13h_medium_config_patch_preview_audit_only"/"gold_v2_13h_patch_preview.json"
    inputs=[cfg,patch]
    ia=pd.DataFrame([{"name":p.name,"path":str(p),"exists":ex(p)} for p in inputs]); wc(ia,out/"gold_v2_13k_input_audit.csv")
    if not ia.exists.all():
        status="MEDIUM_TIER2_HVT_CANDIDATE_MAPPING_AUDIT_MISSING_INPUTS"; wj(out/"gold_v2_13k_candidate_mapping_audit_summary.json",{"created_utc":now,"step":STEP,"status":status}); wt(out/REPORT,md(ia)); return 2
    c=rj(cfg); p=rj(patch); cm=cond_map(c); pc=p.get("rule",{}).get("conditions",{})
    checks=[
        ["13K-C001","scope",c.get("scope"),"MEDIUM_TIER2_HVT_ONLY"],
        ["13K-C002","trend_eff96",cm.get("trend_eff96",{}).get("value"),pc.get("trend_eff96_max")],
        ["13K-C003","ret96",cm.get("ret96",{}).get("value"),pc.get("ret96_max")],
        ["13K-C004","tr_mean_32",cm.get("tr_mean_32",{}).get("value"),pc.get("tr_mean_32_min")],
        ["13K-C005","selected_rows",c.get("rule",{}).get("expected_replay",{}).get("selected_rows"),p.get("rule",{}).get("expected_replay",{}).get("selected_rows")],
        ["13K-C006","final_signal_enabled",c.get("safety",{}).get("final_signal_enabled"),False],
        ["13K-C007","discord_enabled",c.get("safety",{}).get("discord_enabled"),False],
        ["13K-C008","mt5_enabled",c.get("safety",{}).get("mt5_enabled"),False],
        ["13K-C009","CoreA blocked","CoreA" in c.get("blocked_components",{}),True],
        ["13K-C010","CoreB blocked","CoreB" in c.get("blocked_components",{}),True],
    ]
    df=pd.DataFrame(checks,columns=["check_id","check","observed","expected"]); df["status"]=df.apply(lambda r:"PASS" if r.observed==r.expected else "STOP",axis=1); wc(df,out/"gold_v2_13k_candidate_mapping_checks.csv")
    ok=bool((df.status=="PASS").all())
    status="MEDIUM_TIER2_HVT_CANDIDATE_MAPPING_APPLY_AUDIT_PASSED" if ok else "MEDIUM_TIER2_HVT_CANDIDATE_MAPPING_APPLY_AUDIT_FAILED"
    block=pd.DataFrame([["13K-B099","SAFETY","SAFETY","OPEN","external actions","External actions remain disabled; final signal is still off."]],columns=["blocker_id","component","severity","status","blocked_item","required_resolution"]); wc(block,out/"gold_v2_13k_blockers.csv")
    wj(out/"gold_v2_13k_candidate_mapping_audit_summary.json",{"created_utc":now,"step":STEP,"status":status,"audit_ok":ok,"candidate_mapping_config":str(cfg),"final_signal_enabled":False,"discord_enabled":False,"mt5_enabled":False,"ai_api_enabled":False,"external_hook_enabled":False})
    wt(out/REPORT,"\n".join(["# GOLD V2 13K MEDIUM TIER2_HVT candidate mapping audit report","",f"Created UTC: {now}",f"Status: `{status}`","","## Checks",md(df),"","## Blockers",md(block),"","Final signal and external actions remain disabled."]))
    print(json.dumps(clean({"status":status,"output_dir":str(out),"audit_ok":ok,"final_signal_enabled":False}),ensure_ascii=False,indent=2,allow_nan=False))
    return 0 if ok else 2
if __name__=="__main__": raise SystemExit(main())
