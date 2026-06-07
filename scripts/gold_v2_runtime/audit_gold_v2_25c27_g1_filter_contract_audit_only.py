#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse, json, os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Sequence
import pandas as pd

STEP="25C27_COREB_G1_LEFT_ONLY_REPLAY_FILTER_CONTRACT_AUDIT_ONLY"
STATUS="COREB_G1_LEFT_ONLY_REPLAY_FILTER_CONTRACT_COMPLETED_AUDIT_ONLY_FILTER_NARROWING_PLAN_REQUIRED"
STOP="25C27_STOP_MISSING_INPUT_AUDIT_ONLY"
OUT_DIR="gold_v2_25c27_coreb_g1_left_only_replay_filter_contract_audit_only"
IN26="gold_v2_25c26_coreb_g1_left_only_root_cause_audit_only"

def repo_root(): return Path(__file__).resolve().parents[2]
def files_root():
    r=repo_root(); return r.parents[1] if len(r.parents)>=2 else r.parent
def fx_outputs(): return files_root()/"FX_OUTPUTS"
def lp(p:Path)->Path:
    if os.name!="nt": return p
    s=str(p)
    if s.startswith("\\\\?\\"): return Path(s)
    if s.startswith("\\\\"): return Path("\\\\?\\UNC\\"+s[2:])
    return Path("\\\\?\\"+s)
def read_json(p:Path): return json.loads(lp(p).read_text(encoding="utf-8-sig"))
def read_csv(p:Path):
    last=None
    for enc in ("utf-8-sig","utf-8","cp932"):
        try: return pd.read_csv(lp(p), encoding=enc, keep_default_na=False)
        except Exception as e: last=e
    raise RuntimeError(f"read failed {p}: {last}")
def write_csv(p:Path, df:pd.DataFrame):
    lp(p.parent).mkdir(parents=True, exist_ok=True); df.to_csv(lp(p), index=False, encoding="utf-8-sig")
def write_json(p:Path, obj:dict):
    lp(p.parent).mkdir(parents=True, exist_ok=True); lp(p).write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
def md_table(df:pd.DataFrame, n:int=80):
    if df.empty: return "_No rows._"
    v=df.head(n); cols=list(v.columns)
    rows=["| "+" | ".join(cols)+" |", "| "+" | ".join(["---"]*len(cols))+" |"]
    for _,r in v.iterrows(): rows.append("| "+" | ".join(str(r[c]).replace("|","\\|") for c in cols)+" |")
    return "\n".join(rows)

def main(argv:Optional[Sequence[str]]=None)->int:
    ap=argparse.ArgumentParser(); ap.add_argument("--output-dir", default=None); args=ap.parse_args(argv)
    out=Path(args.output_dir).resolve() if args.output_dir else fx_outputs()/OUT_DIR; lp(out).mkdir(parents=True, exist_ok=True)
    base=fx_outputs()/IN26
    req={
        "s26":base/"02_25c26_coreb_g1_left_only_root_cause_summary.json",
        "family_profile":base/"04_25c26_left_only_filter_family_profile.csv",
        "multiplicity":base/"05_25c26_left_only_signal_multiplicity_profile.csv",
        "sample_enrichment":base/"06_25c26_left_only_sample_enrichment.csv",
    }
    ia=pd.DataFrame([{"role":k,"path":str(v),"exists":lp(v).exists(),"status":"PASS" if lp(v).exists() else "STOP"} for k,v in req.items()])
    write_csv(out/"03_25c27_input_audit.csv", ia)
    if not bool(ia["exists"].all()):
        write_json(out/"02_25c27_coreb_g1_left_only_replay_filter_contract_summary.json", {"created_utc":datetime.now(timezone.utc).isoformat(),"step":STEP,"status":STOP,"total_stop_rows":int((ia["status"]=="STOP").sum())}); return 2
    s26=read_json(req["s26"]); fam=read_csv(req["family_profile"]); mult=read_csv(req["multiplicity"]); sample=read_csv(req["sample_enrichment"])
    if "filter" not in sample.columns: sample["filter"]=""
    if "filter_family" not in sample.columns: sample["filter_family"]=""
    sample["filter"]=sample["filter"].astype(str); sample["filter_family"]=sample["filter_family"].astype(str)
    driver=sample.groupby(["filter_family","filter"], dropna=False).agg(g1_keys=("entry_time","nunique"), rows=("filter","count")).reset_index().sort_values(["rows","g1_keys"], ascending=[False,False])
    write_csv(out/"04_25c27_replay_filter_driver_matrix.csv", driver)
    fam2=fam.copy()
    for col in ["left_only_g1_keys","replay_filter_rows","replay_filter_unique"]:
        fam2[col]=pd.to_numeric(fam2[col], errors="coerce").fillna(0)
    total=float(fam2["replay_filter_rows"].sum()) if len(fam2) else 0.0
    fam2["row_share"]=fam2["replay_filter_rows"].apply(lambda x: round(float(x)/total,6) if total else 0)
    fam2["candidate_action"]=fam2["filter_family"].apply(lambda x: "review_first" if str(x)=="same_count_and_unique_origins" else "diagnostic")
    write_csv(out/"05_25c27_replay_filter_family_contract_matrix.csv", fam2)
    mult2=mult.copy()
    for col in ["replay_filter_rows","replay_filter_unique","replay_family_unique","g1_key_count"]:
        mult2[col]=pd.to_numeric(mult2[col], errors="coerce").fillna(0)
    mult2["risk"]=mult2["replay_filter_rows"].apply(lambda x: "HIGH" if x>=7 else ("MEDIUM" if x>=3 else "LOW"))
    risk=mult2.groupby("risk", dropna=False).agg(g1_key_count=("g1_key_count","sum"), max_filter_rows=("replay_filter_rows","max")).reset_index().sort_values("g1_key_count", ascending=False)
    write_csv(out/"06_25c27_replay_overlap_risk_matrix.csv", risk)
    fam_sorted=fam2.sort_values("replay_filter_rows", ascending=False)
    top_family=str(fam_sorted.iloc[0]["filter_family"]) if len(fam_sorted) else ""
    top_rows=int(fam_sorted.iloc[0]["replay_filter_rows"]) if len(fam_sorted) else 0
    high_keys=int(risk.loc[risk["risk"].eq("HIGH"),"g1_key_count"].sum()) if not risk.empty else 0
    dec=pd.DataFrame([
        {"decision_id":"D001","question":"top family is same_count_and_unique_origins","decision":"YES" if top_family=="same_count_and_unique_origins" else "NO","observed":f"{top_family}:{top_rows}"},
        {"decision_id":"D002","question":"high overlap entries present","decision":"YES" if high_keys>0 else "NO","observed":high_keys},
        {"decision_id":"D003","question":"narrowing plan required","decision":"YES","observed":"left-only overgeneration"},
        {"decision_id":"D004","question":"CoreB enable allowed","decision":"NO","observed":False},
    ])
    write_csv(out/"07_25c27_replay_filter_contract_decision_matrix.csv", dec)
    nxt=pd.DataFrame([
        {"rank":1,"next_step":"25C28_COREB_G1_FILTER_NARROWING_PLAN_AUDIT_ONLY","allowed_now":True,"purpose":"plan audit-only filter narrowing review"},
        {"rank":2,"next_step":"CoreB live evaluator","allowed_now":False,"purpose":"blocked"},
    ])
    write_csv(out/"08_25c27_next_step_plan.csv", nxt)
    unnecessary=["25C26 older reports if summary is available","full target rows","full replay rows"]
    necessary=["01_25c27_GOLD_V2_COREB_G1_LEFT_ONLY_REPLAY_FILTER_CONTRACT_AUDIT_ONLY_REPORT.md","02_25c27_coreb_g1_left_only_replay_filter_contract_summary.json","04_25c27_replay_filter_driver_matrix.csv","05_25c27_replay_filter_family_contract_matrix.csv","06_25c27_replay_overlap_risk_matrix.csv","07_25c27_replay_filter_contract_decision_matrix.csv","08_25c27_next_step_plan.csv"]
    write_csv(out/"00_不要_25c27_file_request_list.csv", pd.DataFrame([{"section":"00_不要_貼らなくてOK","rank":i+1,"item":x} for i,x in enumerate(unnecessary)] + [{"section":"必要・貼ってほしい","rank":i+1,"item":x} for i,x in enumerate(necessary)]))
    summary={"created_utc":datetime.now(timezone.utc).isoformat(),"step":STEP,"status":STATUS,"audit_only":True,"condition_changed":False,"full_coreb_parity":False,"top_replay_filter_family":top_family,"top_replay_filter_family_rows":top_rows,"high_overlap_g1_key_count":high_keys,"source_recovery_executed":False,"source_mutation_executed":False,"coreb_live_evaluator_unblocked":False,"next_recommended_step":"25C28_COREB_G1_FILTER_NARROWING_PLAN_AUDIT_ONLY","total_stop_rows":0}
    write_json(out/"02_25c27_coreb_g1_left_only_replay_filter_contract_summary.json", summary)
    report="\n".join(["# GOLD V2 25C27 CoreB G1 left-only replay filter contract audit-only report","",f"Created UTC: {summary['created_utc']}",f"Step: `{STEP}`",f"Status: `{STATUS}`","","## Replay filter driver matrix","",md_table(driver),"","## Replay filter family contract matrix","",md_table(fam2),"","## Replay overlap risk matrix","",md_table(risk),"","## Decisions","",md_table(dec),"","## File request list","","```text","00_不要_貼らなくてOK",*[f"00-{i+1}. {x}" for i,x in enumerate(unnecessary)],"","必要・貼ってほしい",*[f"{i+1:02d}. {x}" for i,x in enumerate(necessary)],"```","","## Next step plan","",md_table(nxt),"","## Safety","","CoreB remains blocked. External/live actions remain off."])
    lp(out/"01_25c27_GOLD_V2_COREB_G1_LEFT_ONLY_REPLAY_FILTER_CONTRACT_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")
    print(json.dumps({"status":STATUS,"top_replay_filter_family":top_family,"next_recommended_step":summary["next_recommended_step"]}, ensure_ascii=False, indent=2))
    return 0

if __name__=="__main__": raise SystemExit(main())
