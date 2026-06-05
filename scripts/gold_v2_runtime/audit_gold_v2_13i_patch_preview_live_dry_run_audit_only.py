#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations
import json, math, os
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd

STEP="13I_PATCH_PREVIEW_LIVE_DRY_RUN_AUDIT_ONLY"
OUT="gold_v2_13i_patch_preview_live_dry_run_audit_only"
REPORT="GOLD_V2_13I_PATCH_PREVIEW_LIVE_DRY_RUN_AUDIT_ONLY_REPORT.md"
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
def rj(p):
    with open(lp(p),"r",encoding="utf-8") as f: return json.load(f)
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
def num(s): return pd.to_numeric(s,errors="coerce")
def md(d):
    if d.empty: return "_No rows._"
    z=["| "+" | ".join(map(str,d.columns))+" |","| "+" | ".join(["---"]*len(d.columns))+" |"]
    for _,r in d.head(80).iterrows(): z.append("| "+" | ".join(str(r[c]).replace("|","\\|") for c in d.columns)+" |")
    return "\n".join(z)
def col(df,*names):
    low={c.lower():c for c in df.columns}
    for n in names:
        if n.lower() in low: return low[n.lower()]
    return None

def main():
    out=od(); now=datetime.now(timezone.utc).isoformat()
    hdir=fx()/"gold_v2_13h_medium_config_patch_preview_audit_only"
    patchp=hdir/"gold_v2_13h_patch_preview.json"; hp=hdir/"gold_v2_13h_medium_config_patch_preview_summary.json"
    rulep=fx()/"gold_v2_coreb_refined_probe_outputs"/"coreb_refined_rule_ledgers.csv"
    inputs=[patchp,hp,rulep]
    ia=pd.DataFrame([{"name":p.name,"path":str(p),"exists":ex(p)} for p in inputs]); wc(ia,out/"gold_v2_13i_input_audit.csv")
    if not all(ex(p) for p in inputs):
        status="MISSING_13I_REQUIRED_INPUTS_AUDIT_ONLY"; wj(out/"gold_v2_13i_patch_preview_live_dry_run_summary.json",{"created_utc":now,"step":STEP,"status":status,"audit_only":True,"external_actions":EXT}); wt(out/REPORT,md(ia)); return 2
    patch=rj(patchp); h=rj(hp); d=rd(rulep)
    cond=patch.get("rule",{}).get("conditions",{}); exp=patch.get("rule",{}).get("expected_replay",{})
    comp=col(d,"component","refined_rule")
    if comp: d=d[d[comp].astype(str).eq("TIER2_HVT")].copy()
    mask=pd.Series(True,index=d.index)
    mask &= num(d["trend_eff96"]) <= float(cond["trend_eff96_max"])+1e-12
    mask &= num(d["ret96"]) <= float(cond["ret96_max"])+1e-12
    mask &= num(d["tr_mean_32"]) >= float(cond["tr_mean_32_min"])-1e-12
    sel=d[mask].copy(); wc(sel,out/"gold_v2_13i_dry_run_selected_rows.csv")
    checks=[
        ["13I-D001","patch_preview_only",patch.get("patch_preview_only") is True,True],
        ["13I-D002","do_not_apply_automatically",patch.get("do_not_apply_automatically") is True,True],
        ["13I-D003","13H summary ok",h.get("status")=="MEDIUM_CONFIG_PATCH_PREVIEW_BUILT_AUDIT_ONLY",True],
        ["13I-D004","selected_rows",len(sel),int(exp.get("selected_rows",31))],
        ["13I-D005","production_config_modified",False,False],
        ["13I-D006","external_actions_false",all(v is False for v in patch.get("safety",{}).get("external_actions",EXT).values()),True],
    ]
    chk=pd.DataFrame(checks,columns=["check_id","check","observed","expected"]); chk["status"]=chk.apply(lambda r:"PASS" if r.observed==r.expected else "STOP",axis=1); wc(chk,out/"gold_v2_13i_dry_run_checks.csv")
    ok=bool((chk["status"]=="PASS").all())
    status="PATCH_PREVIEW_LIVE_DRY_RUN_PASSED_AUDIT_ONLY" if ok else "PATCH_PREVIEW_LIVE_DRY_RUN_FAILED_AUDIT_ONLY"
    block=pd.DataFrame([["13I-B004","FINAL_APPROVAL","HARD","OPEN","final approval gate","13J must explicitly decide whether patch can be applied."],["13I-B099","SAFETY","SAFETY","OPEN","external actions","All external actions remain false and config is not modified."]],columns=["blocker_id","component","severity","status","blocked_item","required_resolution"]); wc(block,out/"gold_v2_13i_blockers.csv")
    dec=pd.DataFrame([["13I-C001","patch preview dry-run",ok,True,"PASS" if ok else "STOP"],["13I-C002","production config modified",False,False,"PASS_NOT_MODIFIED"],["13I-C003","next","13J_FINAL_APPROVAL_GATE_AUDIT_ONLY" if ok else "STOP","review","INFO"]],columns=["check_id","check","observed","expected","status"]); wc(dec,out/"gold_v2_13i_decision_matrix.csv")
    wj(out/"gold_v2_13i_patch_preview_live_dry_run_summary.json",{"created_utc":now,"step":STEP,"status":status,"audit_only":True,"selected_rows":len(sel),"dry_run_ok":ok,"production_config_modified":False,"medium_live_evaluator_allowed":False,"final_signal_allowed":False,"step13_allowed":False,"external_actions":EXT})
    wt(out/REPORT,"\n".join(["# GOLD V2 13I patch preview live dry-run audit-only report","",f"Created UTC: {now}",f"Status: `{status}`","","## Dry-run checks",md(chk),"","## Decision",md(dec),"","## Blockers",md(block),"","External actions remain false. Production config is not modified."]))
    print(json.dumps(clean({"status":status,"output_dir":str(out),"selected_rows":len(sel),"audit_only":True,"external_actions":EXT}),ensure_ascii=False,indent=2,allow_nan=False))
    return 0 if ok else 2
if __name__=="__main__": raise SystemExit(main())
