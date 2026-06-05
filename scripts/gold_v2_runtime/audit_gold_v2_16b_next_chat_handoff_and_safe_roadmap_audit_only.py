#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations
import json, math, os
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd

STEP="16B_NEXT_CHAT_HANDOFF_AND_SAFE_ROADMAP_AUDIT_ONLY"
OUT="gold_v2_16b_next_chat_handoff_and_safe_roadmap_audit_only"
REPORT="GOLD_V2_16B_NEXT_CHAT_HANDOFF_AND_SAFE_ROADMAP_AUDIT_ONLY_REPORT.md"
HANDOFF="NEXT_CHAT_HANDOFF_GOLD_V2_16B_PORTFOLIO_STATUS_AND_SAFE_ROADMAP_20260605.md"
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
def rd(p): return pd.read_csv(lp(p))
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
def md(d,limit=120):
    if d.empty: return "_No rows._"
    z=["| "+" | ".join(map(str,d.columns))+" |","| "+" | ".join(["---"]*len(d.columns))+" |"]
    for _,r in d.head(limit).iterrows(): z.append("| "+" | ".join(str(r[c]).replace("|","\\|").replace("\n"," ") for c in d.columns)+" |")
    return "\n".join(z)

def main():
    out=od(); now=datetime.now(timezone.utc).isoformat()
    bdir=fx()/"gold_v2_16a_portfolio_status_consolidation_audit_only"
    sp=bdir/"gold_v2_16a_portfolio_status_consolidation_summary.json"
    matrixp=bdir/"gold_v2_16a_component_status_matrix.csv"
    safetyp=bdir/"gold_v2_16a_safety_matrix.csv"
    blockersp=bdir/"gold_v2_16a_blockers.csv"
    inputs=[sp,matrixp,safetyp,blockersp]
    ia=pd.DataFrame([{"name":p.name,"path":str(p),"exists":ex(p)} for p in inputs]); wc(ia,out/"gold_v2_16b_input_audit.csv")
    if not all(ex(p) for p in inputs):
        status="GOLD_V2_16B_HANDOFF_MISSING_INPUTS_AUDIT_ONLY"; wj(out/"gold_v2_16b_handoff_summary.json",{"created_utc":now,"step":STEP,"status":status}); wt(out/REPORT,md(ia)); return 2
    sj=rj(sp); matrix=rd(matrixp); safety=rd(safetyp); blockers=rd(blockersp)
    next_steps=pd.DataFrame([
        ["17A","MEDIUM_FULL_SET_SOURCE_ARBITRATION_AUDIT_ONLY","Recover/verify remaining MEDIUM components beyond TIER2_HVT before any MEDIUM full live path.","audit-only"],
        ["18A","COREA_A_GATE_EXECUTABLE_SOURCE_RECOVERY_AUDIT_ONLY","Find explicit A-gate predicates behind is_A / tail_hard/top5/all-consensus/stack KEEP.","audit-only"],
        ["19A","COREB_CLUSTER_MEMBERSHIP_RECOVERY_AUDIT_ONLY","Find original clustering algorithm or membership ledger for same_count replay parity.","audit-only"],
        ["20A","SAFE_DRY_RUN_ONLY_PORTFOLIO_EVALUATOR_DESIGN","Only after component parity; still no Discord/MT5/final signal.","audit-only"],
    ],columns=["step","title","purpose","mode"]); wc(next_steps,out/"gold_v2_16b_next_steps.csv")
    wc(safety,out/"gold_v2_16b_safety_matrix.csv"); wc(blockers,out/"gold_v2_16b_blockers.csv")
    handoff="\n".join([
        "# NEXT CHAT HANDOFF - GOLD V2 portfolio status and safe roadmap 20260605",
        "",
        "## Read this first",
        "GOLD V2 remains audit-only. Do not enable final signal, Discord, MT5, AI API, or live hooks without explicit user approval and new dry-run parity gates.",
        "",
        "旧GOLD/DISC8 は HTF open-time 不整合疑いで隔離済み。近似再実装は禁止。source-of-truth の監査済みartifactを優先すること。",
        "",
        "## Current consolidated status",
        md(matrix),
        "",
        "## Safety state",
        md(safety),
        "",
        "Required safety invariants:",
        "- final_signal_allowed=false",
        "- Discord=false",
        "- MT5=false",
        "- AI API=false",
        "- live_hook=false",
        "- NO_SIGNAL does not notify Discord",
        "",
        "## Component conclusions",
        "- MEDIUM_TIER2_HVT: candidate mapping and load-smoke passed through 13L. It is still not a final signal path.",
        "- CoreB: historical SOT allowed, but live blocked because original clustering / same_count replay is not proven.",
        "- CoreA: historical SOT allowed, but live blocked because A-gate is is_A ledger flag only and underlying predicates are not replay-proven.",
        "- MEDIUM full set: incomplete. Only TIER2_HVT is ready as candidate mapping.",
        "",
        "## Open blockers",
        md(blockers),
        "",
        "## Recommended next steps",
        md(next_steps),
        "",
        "## Next action recommendation",
        "Start with 17A MEDIUM_FULL_SET_SOURCE_ARBITRATION_AUDIT_ONLY, unless the user explicitly wants CoreA or CoreB source recovery first.",
        "",
    ])
    wt(out/HANDOFF,handoff)
    status="GOLD_V2_16B_NEXT_CHAT_HANDOFF_AND_SAFE_ROADMAP_BUILT_AUDIT_ONLY"
    summary={"created_utc":now,"step":STEP,"status":status,"audit_only":True,"handoff_file":HANDOFF,"final_signal_allowed":False,"external_actions":EXT,"next_recommended_step":"17A_MEDIUM_FULL_SET_SOURCE_ARBITRATION_AUDIT_ONLY"}
    wj(out/"gold_v2_16b_handoff_summary.json",summary)
    wt(out/REPORT,"\n".join(["# GOLD V2 16B next-chat handoff and safe roadmap audit-only report","",f"Created UTC: {now}",f"Status: `{status}`","","## Handoff file",f"`{HANDOFF}`","","## Component status",md(matrix),"","## Safety",md(safety),"","## Next steps",md(next_steps),"","No final signal, Discord, MT5, AI API, or live hook is enabled."]))
    print(json.dumps(clean(summary|{"output_dir":str(out)}),ensure_ascii=False,indent=2,allow_nan=False))
    return 0
if __name__=="__main__": raise SystemExit(main())
