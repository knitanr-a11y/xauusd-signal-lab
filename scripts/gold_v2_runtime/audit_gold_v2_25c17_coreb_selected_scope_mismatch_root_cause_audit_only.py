#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse, json, os, re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Sequence
import pandas as pd

STEP="25C17_COREB_SELECTED_SCOPE_MISMATCH_ROOT_CAUSE_AUDIT_ONLY"
STATUS="COREB_SELECTED_SCOPE_MISMATCH_ROOT_CAUSE_COMPLETED_AUDIT_ONLY_REPLAY_CONTRACT_REVIEW_REQUIRED"
STOP="25C17_STOP_MISSING_INPUT_AUDIT_ONLY"
OUT_DIR="gold_v2_25c17_coreb_selected_scope_mismatch_root_cause_audit_only"
IN16="gold_v2_25c16_coreb_selected_scope_target_review_audit_only"
IN10="gold_v2_25c10_coreb_target_filter_contract_replay_dry_run_audit_only"

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
    out=["| "+" | ".join(cols)+" |", "| "+" | ".join(["---"]*len(cols))+" |"]
    for _,r in v.iterrows(): out.append("| "+" | ".join(str(r[c]).replace("|","\\|") for c in cols)+" |")
    return "\n".join(out)
def threshold(filter_text:str):
    s=str(filter_text)
    sm=re.search(r"same_count>=(\d+)",s); um=re.search(r"unique_origins>=(\d+)",s)
    return (int(sm.group(1)) if sm else None, int(um.group(1)) if um else None)

def main(argv:Optional[Sequence[str]]=None)->int:
    ap=argparse.ArgumentParser(); ap.add_argument("--output-dir", default=None); args=ap.parse_args(argv)
    out=Path(args.output_dir).resolve() if args.output_dir else fx_outputs()/OUT_DIR; lp(out).mkdir(parents=True, exist_ok=True)
    req={
        "s16":fx_outputs()/IN16/"02_25c16_coreb_selected_scope_target_review_summary.json",
        "selected_compare":fx_outputs()/IN16/"05_25c16_selected_scope_filter_compare_matrix.csv",
        "by_contract":fx_outputs()/IN10/"06_25c10_filter_compare_by_contract.csv",
    }
    ia=pd.DataFrame([{"role":k,"path":str(v),"exists":lp(v).exists(),"status":"PASS" if lp(v).exists() else "STOP"} for k,v in req.items()])
    write_csv(out/"03_25c17_input_audit.csv", ia)
    if not bool(ia["exists"].all()):
        write_json(out/"02_25c17_coreb_selected_scope_mismatch_root_cause_summary.json", {"created_utc":datetime.now(timezone.utc).isoformat(),"step":STEP,"status":STOP,"total_stop_rows":int((ia["status"]=="STOP").sum())}); return 2
    s16=read_json(req["s16"]); by=read_csv(req["by_contract"])
    selected=set(s16.get("selected_output_policies", []))
    by=by[by["policy"].astype(str).isin(selected)].copy()
    by["rows"]=pd.to_numeric(by["rows"], errors="coerce").fillna(0).astype(int)
    piv=by.pivot_table(index=["policy","filter"], columns="_merge", values="rows", aggfunc="sum", fill_value=0).reset_index()
    for c in ["both","left_only","right_only"]:
        if c not in piv.columns: piv[c]=0
    piv["total_rows"]=piv[["both","left_only","right_only"]].sum(axis=1)
    piv["match_rate"]=(piv["both"] / piv["total_rows"].where(piv["total_rows"].ne(0),1)).round(6)
    th=piv["filter"].apply(lambda x: pd.Series(threshold(x), index=["same_count_threshold","unique_origins_threshold"]))
    root=pd.concat([piv,th],axis=1)
    root["root_cause_hint"]=root.apply(lambda r: "LOW_THRESHOLD_OVERGENERATION" if r["left_only"]>r["right_only"]*2 else ("HIGH_THRESHOLD_TARGET_MISSING" if r["right_only"]>r["left_only"]*2 else "MIXED_MISMATCH"), axis=1)
    write_csv(out/"04_25c17_selected_scope_filter_root_cause_matrix.csv", root.sort_values(["root_cause_hint","left_only","right_only"], ascending=[True,False,False]))
    over=root[root["left_only"].gt(0)].groupby(["same_count_threshold","unique_origins_threshold"],dropna=False).agg(filters=("filter","nunique"),left_only=("left_only","sum"),both=("both","sum"),right_only=("right_only","sum")).reset_index().sort_values("left_only",ascending=False)
    miss=root[root["right_only"].gt(0)].groupby(["same_count_threshold","unique_origins_threshold"],dropna=False).agg(filters=("filter","nunique"),right_only=("right_only","sum"),both=("both","sum"),left_only=("left_only","sum")).reset_index().sort_values("right_only",ascending=False)
    write_csv(out/"05_25c17_overgeneration_threshold_profile.csv", over)
    write_csv(out/"06_25c17_missing_threshold_profile.csv", miss)
    total_left=int(root["left_only"].sum()); total_right=int(root["right_only"].sum()); total_both=int(root["both"].sum())
    low_over=int(root[root["root_cause_hint"].eq("LOW_THRESHOLD_OVERGENERATION")]["left_only"].sum())
    high_missing=int(root[root["root_cause_hint"].eq("HIGH_THRESHOLD_TARGET_MISSING")]["right_only"].sum())
    dec=pd.DataFrame([
        {"decision_id":"D001","question":"selected scope exact parity reached","decision":"NO" if total_left+total_right>0 else "YES","observed":f"both={total_both}; left={total_left}; right={total_right}"},
        {"decision_id":"D002","question":"low threshold over-generation present","decision":"YES" if low_over>0 else "NO","observed":low_over},
        {"decision_id":"D003","question":"high threshold target missing present","decision":"YES" if high_missing>0 else "NO","observed":high_missing},
        {"decision_id":"D004","question":"replay contract review required","decision":"YES","observed":True},
        {"decision_id":"D005","question":"CoreB enable allowed","decision":"NO","observed":False},
    ])
    write_csv(out/"07_25c17_root_cause_decision_matrix.csv", dec)
    nxt=pd.DataFrame([
        {"rank":1,"next_step":"25C18_COREB_REPLAY_CONTRACT_REVIEW_AUDIT_ONLY","allowed_now":True,"purpose":"review selected-scope replay contract before any further dry-run"},
        {"rank":2,"next_step":"CoreB live evaluator","allowed_now":False,"purpose":"blocked"},
    ])
    write_csv(out/"08_25c17_next_step_plan.csv", nxt)
    unnecessary=["25C16 older reports","large per-row signal files unless debugging","target ledger alone"]
    necessary=["01_25c17_GOLD_V2_COREB_SELECTED_SCOPE_MISMATCH_ROOT_CAUSE_AUDIT_ONLY_REPORT.md","02_25c17_coreb_selected_scope_mismatch_root_cause_summary.json","04_25c17_selected_scope_filter_root_cause_matrix.csv","05_25c17_overgeneration_threshold_profile.csv","06_25c17_missing_threshold_profile.csv","07_25c17_root_cause_decision_matrix.csv","08_25c17_next_step_plan.csv"]
    write_csv(out/"00_不要_25c17_file_request_list.csv", pd.DataFrame([{"section":"00_不要_貼らなくてOK","rank":i+1,"item":x} for i,x in enumerate(unnecessary)] + [{"section":"必要・貼ってほしい","rank":i+1,"item":x} for i,x in enumerate(necessary)]))
    summary={"created_utc":datetime.now(timezone.utc).isoformat(),"step":STEP,"status":STATUS,"audit_only":True,"condition_changed":False,"full_coreb_parity":False,"selected_scope_both":total_both,"selected_scope_left_only":total_left,"selected_scope_right_only":total_right,"low_threshold_overgeneration_rows":low_over,"high_threshold_missing_rows":high_missing,"coreb_live_evaluator_unblocked":False,"next_recommended_step":"25C18_COREB_REPLAY_CONTRACT_REVIEW_AUDIT_ONLY","total_stop_rows":0}
    write_json(out/"02_25c17_coreb_selected_scope_mismatch_root_cause_summary.json", summary)
    report="\n".join(["# GOLD V2 25C17 CoreB selected-scope mismatch root cause audit-only report","",f"Created UTC: {summary['created_utc']}",f"Step: `{STEP}`",f"Status: `{STATUS}`","","## Filter root cause matrix","",md_table(root.sort_values(["left_only","right_only"],ascending=[False,False])),"","## Over-generation threshold profile","",md_table(over),"","## Missing threshold profile","",md_table(miss),"","## Decisions","",md_table(dec),"","## File request list","","```text","00_不要_貼らなくてOK",*[f"00-{i+1}. {x}" for i,x in enumerate(unnecessary)],"","必要・貼ってほしい",*[f"{i+1:02d}. {x}" for i,x in enumerate(necessary)],"```","","## Next step plan","",md_table(nxt),"","## Safety","","CoreB remains blocked. External/live actions remain off."])
    lp(out/"01_25c17_GOLD_V2_COREB_SELECTED_SCOPE_MISMATCH_ROOT_CAUSE_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")
    print(json.dumps({"status":STATUS,"selected_scope_left_only":total_left,"selected_scope_right_only":total_right,"next_recommended_step":summary["next_recommended_step"]}, ensure_ascii=False, indent=2))
    return 0

if __name__=="__main__": raise SystemExit(main())
