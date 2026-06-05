#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations
import json, math, os
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd

STEP="13L_MEDIUM_TIER2_HVT_CANDIDATE_MAPPING_LOAD_SMOKE_AUDIT"
OUT="gold_v2_13l_medium_tier2_hvt_candidate_mapping_load_smoke_audit"
REPORT="GOLD_V2_13L_MEDIUM_TIER2_HVT_CANDIDATE_MAPPING_LOAD_SMOKE_AUDIT_REPORT.md"

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
    for _,r in d.head(80).iterrows(): z.append("| "+" | ".join(str(r[c]).replace("|","\\|") for c in d.columns)+" |")
    return "\n".join(z)
def num(s): return pd.to_numeric(s,errors="coerce")
def col(df,*names):
    low={c.lower():c for c in df.columns}
    for n in names:
        if n.lower() in low: return low[n.lower()]
    return None

def apply_condition(series, op, value):
    x=num(series); v=float(value); op=str(op).lower()
    if op in ("lte","<=","le"): return x <= v + 1e-12
    if op in ("gte",">=","ge"): return x >= v - 1e-12
    if op in ("lt","<"): return x < v
    if op in ("gt",">"): return x > v
    if op in ("eq","=="): return (x - v).abs() <= 1e-12
    raise ValueError(f"unsupported operator: {op}")

def main():
    out=od(); now=datetime.now(timezone.utc).isoformat()
    cfgp=rr()/"configs"/"gold_v2"/"medium_tier2_hvt_candidate_mapping_20260605.json"
    ledgerp=fx()/"gold_v2_coreb_refined_probe_outputs"/"coreb_refined_rule_ledgers.csv"
    inputs=[cfgp,ledgerp]
    ia=pd.DataFrame([{"name":p.name,"path":str(p),"exists":ex(p)} for p in inputs]); wc(ia,out/"gold_v2_13l_input_audit.csv")
    if not ia.exists.all():
        status="MEDIUM_TIER2_HVT_CANDIDATE_MAPPING_LOAD_SMOKE_MISSING_INPUTS"; wj(out/"gold_v2_13l_load_smoke_summary.json",{"created_utc":now,"step":STEP,"status":status}); wt(out/REPORT,md(ia)); return 2
    cfg=rj(cfgp); df=rd(ledgerp)
    rule=cfg.get("rule",{}); safety=cfg.get("safety",{})
    comp=col(df,"component","refined_rule")
    work=df.copy()
    if comp: work=work[work[comp].astype(str).eq(rule.get("component","TIER2_HVT"))].copy()
    mask=pd.Series(True,index=work.index)
    parsed=[]
    for c in rule.get("conditions",[]):
        feat=c["feature"]; op=c["operator"]; val=c["value"]
        mask &= apply_condition(work[feat],op,val)
        parsed.append({"feature":feat,"operator":op,"value":val,"available":feat in work.columns})
    sel=work[mask].copy(); wc(sel,out/"gold_v2_13l_selected_rows.csv")
    parsed_df=pd.DataFrame(parsed); wc(parsed_df,out/"gold_v2_13l_parsed_conditions.csv")
    exp=rule.get("expected_replay",{})
    checks=[
        ["13L-C001","schema_version",cfg.get("schema_version"),"gold_v2_medium_candidate_mapping.v1"],
        ["13L-C002","scope",cfg.get("scope"),"MEDIUM_TIER2_HVT_ONLY"],
        ["13L-C003","rule_id",rule.get("rule_id"),"MEDIUM_TIER2_HVT_RECONCILED_13D3"],
        ["13L-C004","active_for_audit_evaluator",rule.get("active_for_audit_evaluator"),True],
        ["13L-C005","conditions_count",len(rule.get("conditions",[])),3],
        ["13L-C006","selected_rows",len(sel),int(exp.get("selected_rows",31))],
        ["13L-C007","final_signal_enabled",safety.get("final_signal_enabled"),False],
        ["13L-C008","discord_enabled",safety.get("discord_enabled"),False],
        ["13L-C009","mt5_enabled",safety.get("mt5_enabled"),False],
        ["13L-C010","ai_api_enabled",safety.get("ai_api_enabled"),False],
        ["13L-C011","external_hook_enabled",safety.get("external_hook_enabled"),False],
        ["13L-C012","CoreA blocked","CoreA" in cfg.get("blocked_components",{}),True],
        ["13L-C013","CoreB blocked","CoreB" in cfg.get("blocked_components",{}),True],
    ]
    chk=pd.DataFrame(checks,columns=["check_id","check","observed","expected"]); chk["status"]=chk.apply(lambda r:"PASS" if r.observed==r.expected else "STOP",axis=1); wc(chk,out/"gold_v2_13l_load_smoke_checks.csv")
    ok=bool((chk.status=="PASS").all())
    status="MEDIUM_TIER2_HVT_CANDIDATE_MAPPING_LOAD_SMOKE_PASSED" if ok else "MEDIUM_TIER2_HVT_CANDIDATE_MAPPING_LOAD_SMOKE_FAILED"
    block=pd.DataFrame([["13L-B099","SAFETY","SAFETY","OPEN","external actions","External actions remain disabled; final signal is still off."],["13L-B014","NEXT","INFO","OPEN","CoreB reconstruction","Proceed to 14A CoreB cluster source reconstruction audit-only."]],columns=["blocker_id","component","severity","status","blocked_item","required_resolution"]); wc(block,out/"gold_v2_13l_blockers.csv")
    wj(out/"gold_v2_13l_load_smoke_summary.json",{"created_utc":now,"step":STEP,"status":status,"audit_ok":ok,"selected_rows":len(sel),"final_signal_enabled":False,"discord_enabled":False,"mt5_enabled":False,"ai_api_enabled":False,"external_hook_enabled":False,"next":"14A_COREB_CLUSTER_SOURCE_RECONSTRUCTION_AUDIT_ONLY"})
    wt(out/REPORT,"\n".join(["# GOLD V2 13L MEDIUM TIER2_HVT candidate mapping load smoke audit report","",f"Created UTC: {now}",f"Status: `{status}`","","## Parsed conditions",md(parsed_df),"","## Checks",md(chk),"","## Blockers / next",md(block),"","Final signal and external actions remain disabled."]))
    print(json.dumps(clean({"status":status,"output_dir":str(out),"selected_rows":len(sel),"audit_ok":ok,"final_signal_enabled":False,"next":"14A_COREB_CLUSTER_SOURCE_RECONSTRUCTION_AUDIT_ONLY"}),ensure_ascii=False,indent=2,allow_nan=False))
    return 0 if ok else 2
if __name__=="__main__": raise SystemExit(main())
