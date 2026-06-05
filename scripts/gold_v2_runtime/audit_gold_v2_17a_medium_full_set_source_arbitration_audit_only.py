#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations
import json, math, os
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd

STEP="17A_MEDIUM_FULL_SET_SOURCE_ARBITRATION_AUDIT_ONLY"
OUT="gold_v2_17a_medium_full_set_source_arbitration_audit_only"
REPORT="GOLD_V2_17A_MEDIUM_FULL_SET_SOURCE_ARBITRATION_AUDIT_ONLY_REPORT.md"
EXT={"discord_send_allowed":False,"mt5_order_allowed":False,"ai_api_allowed":False,"live_hook_allowed":False}
EXPECTED=["RANGE96_REFINED","VOL_TRMEAN32_REFINED","TIER2_HVT"]

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
def rd(p): return pd.read_csv(lp(p))
def rj(p):
    if not ex(p): return {}
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
def md(d,limit=100):
    if d.empty: return "_No rows._"
    z=["| "+" | ".join(map(str,d.columns))+" |","| "+" | ".join(["---"]*len(d.columns))+" |"]
    for _,r in d.head(limit).iterrows(): z.append("| "+" | ".join(str(r[c]).replace("|","\\|").replace("\n"," ") for c in d.columns)+" |")
    return "\n".join(z)
def comp_col(df):
    for c in ["component","rule_component","medium_component","source_component"]:
        if c in df.columns: return c
    return None

def main():
    out=od(); now=datetime.now(timezone.utc).isoformat()
    paths={
        "handoff_16b": fx()/"gold_v2_16b_next_chat_handoff_and_safe_roadmap_audit_only"/"gold_v2_16b_handoff_summary.json",
        "medium_13l": fx()/"gold_v2_13l_medium_tier2_hvt_candidate_mapping_load_smoke_audit"/"gold_v2_13l_load_smoke_summary.json",
        "rule_ledgers": fx()/"gold_v2_coreb_refined_probe_outputs"/"coreb_refined_rule_ledgers.csv",
        "combined_ledgers": fx()/"gold_v2_coreb_refined_probe_outputs"/"coreb_refined_combined_ledgers.csv",
        "tier2_mapping": rr()/"configs"/"gold_v2"/"medium_tier2_hvt_candidate_mapping_20260605.json",
    }
    ia=pd.DataFrame([{"role":k,"path":str(p),"exists":ex(p)} for k,p in paths.items()]); wc(ia,out/"gold_v2_17a_input_audit.csv")
    rule=rd(paths["rule_ledgers"]) if ex(paths["rule_ledgers"]) else pd.DataFrame()
    comb=rd(paths["combined_ledgers"]) if ex(paths["combined_ledgers"]) else pd.DataFrame()
    med13l=rj(paths["medium_13l"]); cfg=rj(paths["tier2_mapping"])
    inv=[]
    for name,df in [("coreb_refined_rule_ledgers",rule),("coreb_refined_combined_ledgers",comb)]:
        c=comp_col(df)
        if df.empty:
            inv.append({"source":name,"component":"__MISSING__","rows":0,"component_col":c,"columns":""})
        elif c:
            for comp,n in df[c].astype(str).value_counts(dropna=False).items():
                inv.append({"source":name,"component":comp,"rows":int(n),"component_col":c,"columns":"|".join(df.columns.astype(str).tolist()[:40])})
        else:
            inv.append({"source":name,"component":"__NO_COMPONENT_COLUMN__","rows":int(len(df)),"component_col":"","columns":"|".join(df.columns.astype(str).tolist()[:40])})
    invdf=pd.DataFrame(inv); wc(invdf,out/"gold_v2_17a_medium_component_inventory.csv")
    arb=[]
    for comp in EXPECTED:
        rows_rule=int(invdf[(invdf.source.eq("coreb_refined_rule_ledgers")) & (invdf.component.eq(comp))]["rows"].sum()) if not invdf.empty else 0
        rows_comb=int(invdf[(invdf.source.eq("coreb_refined_combined_ledgers")) & (invdf.component.eq(comp))]["rows"].sum()) if not invdf.empty else 0
        if comp=="TIER2_HVT" and med13l.get("status")=="MEDIUM_TIER2_HVT_CANDIDATE_MAPPING_LOAD_SMOKE_PASSED":
            status="READY_CANDIDATE_MAPPING"
            resolution="Already passed 13D3-13L candidate mapping/load-smoke. Still no final signal."
        elif rows_rule>0 or rows_comb>0:
            status="NEEDS_REPLAY_PARITY"
            resolution="Source rows exist but no reconciled candidate mapping/load-smoke chain like TIER2_HVT yet."
        else:
            status="MISSING_SOURCE"
            resolution="No component rows found in available refined ledgers; source recovery required."
        arb.append({"component":comp,"rule_ledger_rows":rows_rule,"combined_ledger_rows":rows_comb,"arbitration_status":status,"required_resolution":resolution,"live_evaluator_allowed":False,"final_signal_allowed":False})
    arbdf=pd.DataFrame(arb); wc(arbdf,out/"gold_v2_17a_medium_arbitration_matrix.csv")
    blockers=pd.DataFrame([
        ["17A-B001","MEDIUM_FULL_SET","HARD","OPEN","full MEDIUM live evaluator","Complete source arbitration and replay parity for all non-TIER2_HVT MEDIUM components."],
        ["17A-B002","MEDIUM_TIER2_HVT","SAFETY","OPEN","final signal","TIER2_HVT is candidate mapping only; no final signal or external action."],
        ["17A-B099","SAFETY","SAFETY","OPEN","external actions","All external actions remain false; final signal is still off."],
    ],columns=["blocker_id","component","severity","status","blocked_item","required_resolution"]); wc(blockers,out/"gold_v2_17a_blockers.csv")
    ready=int((arbdf.arbitration_status=="READY_CANDIDATE_MAPPING").sum())
    needs=int((arbdf.arbitration_status=="NEEDS_REPLAY_PARITY").sum())
    missing=int((arbdf.arbitration_status=="MISSING_SOURCE").sum())
    status="MEDIUM_FULL_SET_SOURCE_ARBITRATION_BUILT_AUDIT_ONLY_PARTIAL_READY"
    summary={"created_utc":now,"step":STEP,"status":status,"audit_only":True,"ready_candidate_mapping_components":ready,"needs_replay_parity_components":needs,"missing_source_components":missing,"medium_full_set_live_allowed":False,"final_signal_allowed":False,"external_actions":EXT,"next":"17B_MEDIUM_NON_TIER2_COMPONENT_REPLAY_PLANNING_AUDIT_ONLY"}
    wj(out/"gold_v2_17a_medium_full_set_source_arbitration_summary.json",summary)
    wt(out/REPORT,"\n".join(["# GOLD V2 17A MEDIUM full-set source arbitration audit-only report","",f"Created UTC: {now}",f"Status: `{status}`","","## Component inventory",md(invdf),"","## Arbitration matrix",md(arbdf),"","## Blockers",md(blockers),"","MEDIUM full set remains live-blocked. No final signal, Discord, MT5, AI API, or live hook is enabled."]))
    print(json.dumps(clean(summary|{"output_dir":str(out)}),ensure_ascii=False,indent=2,allow_nan=False))
    return 0
if __name__=="__main__": raise SystemExit(main())
