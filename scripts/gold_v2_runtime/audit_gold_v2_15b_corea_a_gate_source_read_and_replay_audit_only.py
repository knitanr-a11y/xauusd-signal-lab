#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations
import json, math, os
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd

STEP="15B_COREA_A_GATE_SOURCE_READ_AND_REPLAY_AUDIT_ONLY"
OUT="gold_v2_15b_corea_a_gate_source_read_and_replay_audit_only"
REPORT="GOLD_V2_15B_COREA_A_GATE_SOURCE_READ_AND_REPLAY_AUDIT_ONLY_REPORT.md"
EXT={"discord_send_allowed":False,"mt5_order_allowed":False,"ai_api_allowed":False,"live_hook_allowed":False}
A_KEYS=["tail_hard","top5","all-consensus","all_consensus","stack","keep","chosen_names","is_A","signal_ABC","signal_fixed_ABC"]

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
def flatten_json(obj,prefix=""):
    rows=[]
    if isinstance(obj,dict):
        for k,v in obj.items(): rows += flatten_json(v, f"{prefix}.{k}" if prefix else str(k))
    elif isinstance(obj,list):
        for i,v in enumerate(obj): rows += flatten_json(v, f"{prefix}[{i}]")
    else:
        rows.append({"path":prefix,"value":obj})
    return rows
def text_from_json(o): return json.dumps(o,ensure_ascii=False).lower()
def boolcol(s): return s.astype(str).str.lower().isin(["true","1","yes"])

def main():
    out=od(); now=datetime.now(timezone.utc).isoformat()
    bdir=fx()/"gold_v2_13b_corea_executable_mapping_freeze_audit_only"
    paths={
        "frozen_corea_config": rr()/"configs"/"gold_v2"/"frozen_coreA_fold4_ABC_CAP5_rules_20260603.json",
        "live_mapping_corea_config": rr()/"configs"/"gold_v2"/"live_evaluator_mapping_coreA_20260603.json",
        "summary_13b": bdir/"gold_v2_13b_corea_mapping_summary.json",
        "selected_source_rows": bdir/"gold_v2_13b_corea_selected_source_rows.csv",
        "abc_gate_inventory": bdir/"gold_v2_13b_corea_abc_gate_inventory.csv",
        "candidateA_top5_inventory": bdir/"gold_v2_13b_corea_candidateA_top5_inventory.csv",
        "unmapped_conditions": bdir/"gold_v2_13b_corea_unmapped_conditions.csv",
        "required_fields": bdir/"gold_v2_13b_corea_required_fields.csv",
    }
    ia=pd.DataFrame([{"role":k,"path":str(p),"exists":ex(p)} for k,p in paths.items()]); wc(ia,out/"gold_v2_15b_input_audit.csv")
    if not ex(paths["summary_13b"]) or not ex(paths["selected_source_rows"]) or not ex(paths["abc_gate_inventory"]):
        status="COREA_A_GATE_READ_REPLAY_MISSING_13B_INPUTS_AUDIT_ONLY"; wj(out/"gold_v2_15b_corea_a_gate_read_replay_summary.json",{"created_utc":now,"step":STEP,"status":status,"audit_only":True,"external_actions":EXT}); wt(out/REPORT,md(ia)); return 2
    s13b=rj(paths["summary_13b"]); selected=rd(paths["selected_source_rows"]); abc=rd(paths["abc_gate_inventory"])
    top5=rd(paths["candidateA_top5_inventory"]) if ex(paths["candidateA_top5_inventory"]) else pd.DataFrame()
    unmapped=rd(paths["unmapped_conditions"]) if ex(paths["unmapped_conditions"]) else pd.DataFrame()
    required=rd(paths["required_fields"]) if ex(paths["required_fields"]) else pd.DataFrame()
    frozen=rj(paths["frozen_corea_config"]) if ex(paths["frozen_corea_config"]) else {}
    livecfg=rj(paths["live_mapping_corea_config"]) if ex(paths["live_mapping_corea_config"]) else {}
    for name,obj in [("frozen_corea_config",frozen),("live_mapping_corea_config",livecfg)]:
        flat=pd.DataFrame(flatten_json(obj)) if obj else pd.DataFrame(columns=["path","value"])
        wc(flat,out/f"gold_v2_15b_{name}_flattened.csv")
    frozen_text=text_from_json(frozen); live_text=text_from_json(livecfg)
    frozen_hits=[k for k in A_KEYS if k.lower() in frozen_text]
    live_hits=[k for k in A_KEYS if k.lower() in live_text]
    a_rows=selected[selected.get("signal_ABC",pd.Series(dtype=str)).astype(str).eq("A")].copy() if "signal_ABC" in selected.columns else selected.iloc[0:0].copy()
    selected_counts=selected.groupby(["dataset","signal_ABC"]).size().reset_index(name="rows") if set(["dataset","signal_ABC"]).issubset(selected.columns) else pd.DataFrame()
    wc(selected_counts,out/"gold_v2_15b_selected_signal_counts.csv")
    a_gate_rows=abc[abc.get("signal_ABC",pd.Series(dtype=str)).astype(str).eq("A")].copy() if "signal_ABC" in abc.columns else pd.DataFrame()
    wc(a_gate_rows,out/"gold_v2_15b_a_gate_inventory_rows.csv")
    a_known_formula = "; ".join(a_gate_rows.get("known_formula",pd.Series(dtype=str)).dropna().astype(str).unique().tolist()) if not a_gate_rows.empty and "known_formula" in a_gate_rows.columns else ""
    a_formula_is_flag_only = "ledger flag" in a_known_formula.lower() or "underlying" in a_known_formula.lower()
    unmapped_a = unmapped[unmapped.astype(str).apply(lambda r: r.str.contains("A gate|fold4|is_A|tail_hard|top5|all-consensus|stack",case=False,regex=True).any(),axis=1)].copy() if not unmapped.empty else pd.DataFrame()
    wc(unmapped_a,out/"gold_v2_15b_a_gate_unmapped_rows.csv")
    required_a = required[required.astype(str).apply(lambda r: r.str.contains("ABC A gate|fold4|CoreA",case=False,regex=True).any(),axis=1)].copy() if not required.empty else pd.DataFrame()
    wc(required_a,out/"gold_v2_15b_a_gate_required_field_rows.csv")
    config_has_a_words=bool(frozen_hits or live_hits)
    config_has_executable_predicates=bool(config_has_a_words and any(k in (frozen_text+live_text) for k in ["tail_hard","all-consensus","all_consensus","top5"]) and any(k in (frozen_text+live_text) for k in ["condition","predicate","rules"]))
    a_gate_executable=bool(config_has_executable_predicates and not a_formula_is_flag_only and unmapped_a.empty)
    checks=pd.DataFrame([
        ["15B-C001","13B summary status",s13b.get("status"),"COREA_SOT_READY_EXECUTABLE_MAPPING_BLOCKED_AUDIT_ONLY"],
        ["15B-C002","selected rows readable",len(selected)>0,True],
        ["15B-C003","A selected rows",len(a_rows),len(a_rows)],
        ["15B-C004","ABC A known formula is executable",not a_formula_is_flag_only,True],
        ["15B-C005","frozen config exists",ex(paths["frozen_corea_config"]),True],
        ["15B-C006","live mapping config exists",ex(paths["live_mapping_corea_config"]),True],
        ["15B-C007","config contains A-gate keywords",config_has_a_words,True],
        ["15B-C008","config contains executable predicate hints",config_has_executable_predicates,True],
        ["15B-C009","A-gate unmapped rows absent",unmapped_a.empty,True],
        ["15B-C010","CoreA live evaluator allowed",a_gate_executable,True],
    ],columns=["check_id","check","observed","expected"])
    checks["status"]=checks.apply(lambda r:"PASS" if r.observed==r.expected else ("BLOCK_EXPECTED" if r.check in ["ABC A known formula is executable","A-gate unmapped rows absent","CoreA live evaluator allowed","config contains executable predicate hints"] else "REVIEW"),axis=1)
    wc(checks,out/"gold_v2_15b_read_replay_checks.csv")
    status="COREA_A_GATE_EXECUTABLE_CANDIDATE_FOUND_REPLAY_REQUIRED_AUDIT_ONLY" if a_gate_executable else "COREA_A_GATE_SOURCE_READABLE_BUT_LIVE_MAPPING_BLOCKED_AUDIT_ONLY"
    dec=pd.DataFrame([
        ["15B-D001","CoreA historical selected source rows readable",len(selected)>0,True,"PASS" if len(selected)>0 else "STOP"],
        ["15B-D002","A gate executable now",a_gate_executable,True,"BLOCK_EXPECTED" if not a_gate_executable else "REPLAY_REQUIRED"],
        ["15B-D003","CoreA live enabled",False,False,"PASS_BLOCKED_AS_EXPECTED"],
        ["15B-D004","next","15C_COREA_HISTORICAL_SOT_MAPPING_AUDIT_ONLY" if not a_gate_executable else "15C_COREA_A_GATE_REPLAY_PARITY_AUDIT_ONLY","review","INFO"],
    ],columns=["check_id","check","observed","expected","status"]); wc(dec,out/"gold_v2_15b_decision_matrix.csv")
    block=pd.DataFrame([
        ["15B-B001","COREA_A_GATE","HARD","OPEN","CoreA live evaluator","Underlying A-gate executable predicates or replay parity are required before live CoreA."],
        ["15B-B099","SAFETY","SAFETY","OPEN","external actions","All external actions remain false; final signal is still off."],
    ],columns=["blocker_id","component","severity","status","blocked_item","required_resolution"]); wc(block,out/"gold_v2_15b_blockers.csv")
    summary={"created_utc":now,"step":STEP,"status":status,"audit_only":True,"selected_source_rows":int(len(selected)),"a_selected_rows":int(len(a_rows)),"frozen_config_exists":ex(paths["frozen_corea_config"]),"live_mapping_config_exists":ex(paths["live_mapping_corea_config"]),"frozen_keyword_hits":frozen_hits,"live_mapping_keyword_hits":live_hits,"a_known_formula":a_known_formula,"a_formula_is_flag_only":a_formula_is_flag_only,"a_gate_executable":a_gate_executable,"corea_live_evaluator_allowed":False,"final_signal_allowed":False,"external_actions":EXT,"next":"15C_COREA_HISTORICAL_SOT_MAPPING_AUDIT_ONLY" if not a_gate_executable else "15C_COREA_A_GATE_REPLAY_PARITY_AUDIT_ONLY"}
    wj(out/"gold_v2_15b_corea_a_gate_read_replay_summary.json",summary)
    wt(out/REPORT,"\n".join(["# GOLD V2 15B CoreA A-gate source read and replay audit-only report","",f"Created UTC: {now}",f"Status: `{status}`","","## Checks",md(checks),"","## Selected signal counts",md(selected_counts),"","## A gate inventory",md(a_gate_rows),"","## Decision",md(dec),"","## Blockers",md(block),"","CoreA live evaluator remains disabled."]))
    print(json.dumps(clean(summary|{"output_dir":str(out)}),ensure_ascii=False,indent=2,allow_nan=False))
    return 0 if len(selected)>0 else 2
if __name__=="__main__": raise SystemExit(main())
