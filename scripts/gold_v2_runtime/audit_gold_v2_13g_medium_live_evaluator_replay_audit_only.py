#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations
import json, math, os
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd

STEP="13G_MEDIUM_LIVE_EVALUATOR_REPLAY_AUDIT_ONLY"
OUT="gold_v2_13g_medium_live_evaluator_replay_audit_only"
REPORT="GOLD_V2_13G_MEDIUM_LIVE_EVALUATOR_REPLAY_AUDIT_ONLY_REPORT.md"
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

def key(df):
    d=df.copy(); t=col(d,"entry_time","top_entry_time"); dc=col(d,"direction","top_direction"); cc=col(d,"component","refined_rule")
    d["__time__"]=pd.to_datetime(d[t],errors="coerce").astype("int64").astype(str)
    d["__direction__"]=d[dc].astype(str) if dc else ""
    d["__component__"]=d[cc].astype(str).str.replace("MEDIUM_","",regex=False) if cc else "TIER2_HVT"
    d["__key__"]=d["__time__"]+"|"+d["__direction__"]+"|"+d["__component__"]
    return d

def main():
    out=od(); now=datetime.now(timezone.utc).isoformat()
    base=fx()/"gold_v2_13d3_freeze_medium_tier2_hvt_reconciled_rule_audit_only"
    srcp=base/"gold_v2_13d3_tier2_source_rows_with_reconciled_match.csv"
    candp=base/"gold_v2_13d3_tier2_reconciled_rule_candidate.json"
    e5p=fx()/"gold_v2_13e5_read_replay_feature_source_chain_audit_only"/"gold_v2_13e5_feature_source_chain_summary.json"
    rulep=fx()/"gold_v2_coreb_refined_probe_outputs"/"coreb_refined_rule_ledgers.csv"
    mapp=rr()/"configs"/"gold_v2"/"live_evaluator_mapping_medium_20260603.json"
    inputs=[srcp,candp,e5p,rulep,mapp]
    audit=pd.DataFrame([{"name":p.name,"path":str(p),"exists":ex(p)} for p in inputs]); wc(audit,out/"gold_v2_13g_input_audit.csv")
    if not all(ex(p) for p in [srcp,candp,e5p,rulep]):
        status="MISSING_13G_REQUIRED_INPUTS_AUDIT_ONLY"; wj(out/"gold_v2_13g_medium_live_evaluator_replay_summary.json",{"created_utc":now,"step":STEP,"status":status,"audit_only":True,"external_actions":EXT}); wt(out/REPORT,md(audit)); return 2
    src=key(rd(srcp)); cand=rj(candp); e5=rj(e5p); rule=rd(rulep)
    cond=cand.get("reconciled_conditions",{})
    d=rule.copy(); comp=col(d,"component","refined_rule"); ds=col(d,"dataset")
    if comp: d=d[d[comp].astype(str).eq("TIER2_HVT")].copy()
    mask=pd.Series(True,index=d.index)
    if "trend_eff96_max" in cond: mask &= num(d["trend_eff96"]) <= float(cond["trend_eff96_max"])+1e-12
    if "ret96_max" in cond: mask &= num(d["ret96"]) <= float(cond["ret96_max"])+1e-12
    if "tr_mean_32_min" in cond: mask &= num(d["tr_mean_32"]) >= float(cond["tr_mean_32_min"])-1e-12
    selected=key(d[mask].copy()); wc(selected,out/"gold_v2_13g_replay_selected_rows.csv")
    src_keys=set(src["__key__"]); sel_keys=set(selected["__key__"])
    missing=src_keys-sel_keys; extra=sel_keys-src_keys
    diff=pd.DataFrame([{"metric":"source_rows","value":len(src)},{"metric":"selected_rows","value":len(selected)},{"metric":"reproduced_source_rows","value":len(src_keys & sel_keys)},{"metric":"missing_source_rows","value":len(missing)},{"metric":"extra_selected_rows","value":len(extra)},{"metric":"mapping_config_exists","value":ex(mapp)},{"metric":"e5_ok","value":e5.get("status")=="FEATURE_SOURCE_CHAIN_FIXED_AUDIT_ONLY"}]); wc(diff,out/"gold_v2_13g_replay_diff_summary.csv")
    ok=len(src)==31 and len(selected)==31 and len(missing)==0 and len(extra)==0 and e5.get("status")=="FEATURE_SOURCE_CHAIN_FIXED_AUDIT_ONLY"
    status="MEDIUM_TIER2_HVT_LIVE_EVALUATOR_REPLAY_PROVEN_AUDIT_ONLY" if ok else "MEDIUM_TIER2_HVT_LIVE_EVALUATOR_REPLAY_NOT_PROVEN_AUDIT_ONLY"
    blockers=[]
    if not ok: blockers.append(["13G-B004","LIVE_REPLAY","HARD","OPEN","live evaluator replay","Selected rows must match source 31/31 with no extras."])
    blockers.append(["13G-B099","SAFETY","SAFETY","OPEN","external actions","All external actions remain false."])
    block=pd.DataFrame(blockers,columns=["blocker_id","component","severity","status","blocked_item","required_resolution"]); wc(block,out/"gold_v2_13g_blockers.csv")
    dec=pd.DataFrame([["13G-C001","replay exact 31 rows",ok,True,"PASS" if ok else "STOP"],["13G-C002","live config updated",False,False,"PASS_NOT_UPDATED"],["13G-C003","next","13H_CONFIG_PATCH_PREVIEW_AUDIT_ONLY" if ok else "STOP","review","INFO"]],columns=["check_id","check","observed","expected","status"]); wc(dec,out/"gold_v2_13g_decision_matrix.csv")
    wj(out/"gold_v2_13g_medium_live_evaluator_replay_summary.json",{"created_utc":now,"step":STEP,"status":status,"audit_only":True,"source_rows":len(src),"selected_rows":len(selected),"reproduced_source_rows":len(src_keys & sel_keys),"missing_source_rows":len(missing),"extra_selected_rows":len(extra),"medium_live_evaluator_allowed":False,"final_signal_allowed":False,"step13_allowed":False,"external_actions":EXT})
    wt(out/REPORT,"\n".join(["# GOLD V2 13G MEDIUM live evaluator replay audit-only report","",f"Created UTC: {now}",f"Status: `{status}`","","## Diff summary",md(diff),"","## Decision",md(dec),"","## Blockers",md(block),"","External actions remain false."]))
    print(json.dumps(clean({"status":status,"output_dir":str(out),"selected_rows":len(selected),"audit_only":True,"external_actions":EXT}),ensure_ascii=False,indent=2,allow_nan=False))
    return 0 if ok else 2
if __name__=="__main__": raise SystemExit(main())
