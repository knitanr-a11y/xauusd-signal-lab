#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations
import json, math, os, zipfile
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd

STEP="13D3_FREEZE_MEDIUM_TIER2_HVT_RECONCILED_RULE_AUDIT_ONLY"
SRC="gold_v2_13d2_medium_tier2_hvt_source_definition_reconciliation_audit_only"
OUT="gold_v2_13d3_freeze_medium_tier2_hvt_reconciled_rule_audit_only"
EXT={"discord_send_allowed":False,"mt5_order_allowed":False,"ai_api_allowed":False,"live_hook_allowed":False}
EXP={"source_rows":31,"final_rows":13,"original_source_match_rows":19,"reconciled_source_match_rows":31,"reconciled_final_match_rows":13}
REPORT="GOLD_V2_13D3_FREEZE_MEDIUM_TIER2_HVT_RECONCILED_RULE_AUDIT_ONLY_REPORT.md"

def rr(): return Path(__file__).resolve().parents[2]
def fx():
    r=rr(); return (r.parents[1] if len(r.parents)>=2 else r.parent)/"FX_OUTPUTS"
def lp(p):
    s=str(Path(p).resolve(strict=False))
    if os.name!="nt" or s.startswith("\\\\?\\"): return s
    return "\\\\?\\UNC\\"+s.lstrip("\\") if s.startswith("\\\\") else "\\\\?\\"+s
def ex(p): return os.path.exists(lp(p))
def od():
    p=fx()/OUT; os.makedirs(lp(p),exist_ok=True); return p
def fp(n): return fx()/SRC/n
def rcsv(n): return pd.read_csv(lp(fp(n)))
def rjson(n):
    with open(lp(fp(n)),"r",encoding="utf-8") as f: return json.load(f)
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
def num(s): return pd.to_numeric(s if isinstance(s,pd.Series) else pd.Series(s),errors="coerce")
def ev(df,rule):
    ok=pd.Series(True,index=df.index)
    for k,v in rule.items():
        k=str(k)
        if k.endswith("_min"):
            f=k[:-4]; ok &= num(df[f])>=float(v)-1e-12 if f in df.columns else False
        elif k.endswith("_max"):
            f=k[:-4]; ok &= num(df[f])<=float(v)+1e-12 if f in df.columns else False
        else:
            f=k; ok &= num(df[f]).eq(float(v)) if f in df.columns else False
    return ok
def mt(s):
    a=num(s).dropna().astype(float).to_numpy()
    if len(a)==0: return {"count":0,"win_rate_pct":None,"pf":None,"total_r":0.0}
    gw=float(a[a>0].sum()); gl=float(-a[a<0].sum())
    pf=math.inf if gl==0 and gw>0 else (gw/gl if gl>0 else math.nan)
    return {"count":int(len(a)),"win_rate_pct":float((a>0).mean()*100),"pf":pf,"total_r":float(a.sum()),"worst":float(a.min())}
def md(d):
    if d.empty: return "_No rows._"
    z=["| "+" | ".join(map(str,d.columns))+" |","| "+" | ".join(["---"]*len(d.columns))+" |"]
    for _,r in d.iterrows(): z.append("| "+" | ".join(str(r[c]).replace("|","\\|") for c in d.columns)+" |")
    return "\n".join(z)

def main():
    out=od(); now=datetime.now(timezone.utc).isoformat()
    needed=["gold_v2_13d2_medium_tier2_hvt_reconciliation_summary.json","gold_v2_13d2_tier2_source_rows.csv","gold_v2_13d2_tier2_final_sot_rows.csv","gold_v2_13d2_tier2_candidate_rule_manifest_patch_preview.json"]
    audit=pd.DataFrame([{"name":n,"path":str(fp(n)),"exists":ex(fp(n))} for n in needed]); wcsv(audit,out/"gold_v2_13d3_input_audit.csv")
    if not audit.exists.all():
        status="MISSING_13D2_INPUTS_AUDIT_ONLY"; wjson(out/"gold_v2_13d3_freeze_medium_tier2_hvt_reconciled_rule_summary.json",{"created_utc":now,"step":STEP,"status":status,"audit_only":True,"external_actions":EXT}); wtxt(out/REPORT,md(audit)); return 2
    summ=rjson(needed[0]); src=rcsv(needed[1]); fin=rcsv(needed[2]); prev=rjson(needed[3])
    orig=dict(summ.get("original_tier2_conditions",{})); rec=dict(orig); rec["tr_mean_32_min"]=float(prev.get("source_31_envelope_preview",{}).get("tr_mean_32_min",num(src.tr_mean_32).min()))
    src["original_match"]=ev(src,orig); src["reconciled_match"]=ev(src,rec); fin["original_match"]=ev(fin,orig); fin["reconciled_match"]=ev(fin,rec)
    obs={"source_rows":len(src),"final_rows":len(fin),"original_source_match_rows":int(src.original_match.sum()),"original_final_match_rows":int(fin.original_match.sum()),"reconciled_source_match_rows":int(src.reconciled_match.sum()),"reconciled_final_match_rows":int(fin.reconciled_match.sum())}
    checks=pd.DataFrame([{"metric":k,"observed":int(obs[k]),"expected":int(v),"ok":int(obs[k])==int(v)} for k,v in EXP.items()]); ok=bool(checks.ok.all() and summ.get("counts_ok") is True and int(summ.get("unique_failed_condition_sets",-1))==1)
    status="TIER2_HVT_RECONCILED_RULE_CANDIDATE_FROZEN_AUDIT_ONLY" if ok else "TIER2_HVT_RECONCILED_RULE_FREEZE_STOPPED_AUDIT_ONLY"
    delta=pd.DataFrame([{"condition_key":k,"original_value":orig.get(k),"reconciled_value":rec.get(k),"changed":orig.get(k)!=rec.get(k)} for k in sorted(set(orig)|set(rec))])
    block=pd.DataFrame([["13D3-B004","MEDIUM","HARD","OPEN","feature/asof parity","13E must prove feature/asof parity."],["13D3-B005","SAFETY","SAFETY","OPEN","external actions","All external actions remain false."]],columns=["blocker_id","component","severity","status","blocked_item","required_resolution"])
    dec=pd.DataFrame([["13D3-C001","13D2 precondition",summ.get("counts_ok"),True,"PASS" if summ.get("counts_ok") else "STOP"],["13D3-C002","source replay",obs["reconciled_source_match_rows"],31,"PASS" if obs["reconciled_source_match_rows"]==31 else "STOP"],["13D3-C003","final replay",obs["reconciled_final_match_rows"],13,"PASS" if obs["reconciled_final_match_rows"]==13 else "STOP"],["13D3-C004","next","13E_MEDIUM_FEATURE_ASOF_PARITY_PREFLIGHT_AUDIT_ONLY","13E","INFO"]],columns=["check_id","check","observed","expected","status"])
    for name,df in [("gold_v2_13d3_tier2_source_rows_with_reconciled_match.csv",src),("gold_v2_13d3_tier2_final_rows_with_reconciled_match.csv",fin),("gold_v2_13d3_tier2_replay_checks.csv",checks),("gold_v2_13d3_tier2_rule_delta.csv",delta),("gold_v2_13d3_tier2_blockers.csv",block),("gold_v2_13d3_tier2_decision_matrix.csv",dec)]: wcsv(df,out/name)
    cand={"audit_only":True,"candidate_name":"TIER2_HVT_RECONCILED_SOURCE_31","original_conditions":orig,"reconciled_conditions":rec,"source_rows_matched":obs["reconciled_source_match_rows"],"final_rows_matched":obs["reconciled_final_match_rows"],"external_actions":EXT}
    wjson(out/"gold_v2_13d3_tier2_reconciled_rule_candidate.json",cand); wcsv(pd.DataFrame([{"rule_name":"TIER2_HVT_RECONCILED_SOURCE_31",**rec}]),out/"gold_v2_13d3_tier2_reconciled_rule_candidate.csv")
    wjson(out/"gold_v2_13d3_freeze_medium_tier2_hvt_reconciled_rule_summary.json",{"created_utc":now,"step":STEP,"status":status,"audit_only":True,"source_of_truth":"13D2 outputs only","original_conditions":orig,"reconciled_conditions":rec,"observed_counts":obs,"next_recommended_step":"13E_MEDIUM_FEATURE_ASOF_PARITY_PREFLIGHT_AUDIT_ONLY","medium_live_evaluator_allowed":False,"final_signal_allowed":False,"step13_allowed":False,"external_actions":EXT})
    wtxt(out/REPORT,"\n".join(["# GOLD V2 13D3 freeze MEDIUM TIER2_HVT reconciled rule audit-only report","",f"Created UTC: {now}",f"Status: `{status}`","","## Rule delta",md(delta),"","## Replay checks",md(checks),"","## Metrics",md(pd.DataFrame([{"scope":"source_31",**mt(src.profit_r)},{"scope":"final_13",**mt(fin.profit_r)}])),"","## Decision",md(dec),"","## Blockers",md(block),"","External actions remain false."]))
    z=fx()/"gold_v2_13d3_freeze_medium_tier2_hvt_reconciled_rule_audit.zip"
    if ex(z): os.remove(lp(z))
    with zipfile.ZipFile(lp(z),"w",zipfile.ZIP_DEFLATED) as zz:
        for p in out.iterdir(): zz.write(lp(p),arcname=p.name)
    print(json.dumps(clean({"status":status,"output_dir":str(out),"zip":str(z),**obs,"next_recommended_step":"13E_MEDIUM_FEATURE_ASOF_PARITY_PREFLIGHT_AUDIT_ONLY","audit_only":True,"external_actions":EXT}),ensure_ascii=False,indent=2,allow_nan=False))
    return 0 if ok else 2
if __name__=="__main__": raise SystemExit(main())
