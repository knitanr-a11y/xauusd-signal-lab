#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse, json, os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Sequence
import pandas as pd

STEP="25C16_COREB_SELECTED_SCOPE_TARGET_REVIEW_AUDIT_ONLY"
STATUS="COREB_SELECTED_SCOPE_TARGET_REVIEW_COMPLETED_AUDIT_ONLY_SELECTED_SCOPE_MISMATCH_REVIEW_REQUIRED"
STOP="25C16_STOP_MISSING_INPUT_AUDIT_ONLY"
OUT_DIR="gold_v2_25c16_coreb_selected_scope_target_review_audit_only"
IN15="gold_v2_25c15_coreb_selected_policy_replay_contract_audit_only"
IN10="gold_v2_25c10_coreb_target_filter_contract_replay_dry_run_audit_only"
IN7="gold_v2_25c7_coreb_target_compare_mismatch_triage_audit_only"
INB3="gold_v2_25b3_coreb_source_shortlist_content_audit_only"
TARGET_NAME="rr125_top_ledgers.csv"

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
def path_from_audit(df:pd.DataFrame, name:str)->Path:
    m=df[df["normalized_path"].astype(str).str.contains(name, case=False, regex=False, na=False)]
    return Path(str(m.iloc[0]["absolute_path"])) if not m.empty else Path("")

def main(argv:Optional[Sequence[str]]=None)->int:
    ap=argparse.ArgumentParser(); ap.add_argument("--output-dir", default=None); args=ap.parse_args(argv)
    out=Path(args.output_dir).resolve() if args.output_dir else fx_outputs()/OUT_DIR; lp(out).mkdir(parents=True, exist_ok=True)
    req={
        "s15":fx_outputs()/IN15/"02_25c15_coreb_selected_policy_replay_contract_summary.json",
        "handling":fx_outputs()/IN15/"06_25c15_target_policy_handling_contract.csv",
        "signals":fx_outputs()/IN10/"04_25c10_filter_replay_signal_rows.csv",
        "s7":fx_outputs()/IN7/"02_25c7_coreb_target_compare_mismatch_triage_summary.json",
        "audit":fx_outputs()/INB3/"gold_v2_25b3_shortlist_file_content_audit.csv",
    }
    ia=pd.DataFrame([{"role":k,"path":str(v),"exists":lp(v).exists(),"status":"PASS" if lp(v).exists() else "STOP"} for k,v in req.items()])
    write_csv(out/"03_25c16_input_audit.csv", ia)
    if not bool(ia["exists"].all()):
        write_json(out/"02_25c16_coreb_selected_scope_target_review_summary.json", {"created_utc":datetime.now(timezone.utc).isoformat(),"step":STEP,"status":STOP,"total_stop_rows":int((ia["status"]=="STOP").sum())}); return 2
    s15=read_json(req["s15"]); s7=read_json(req["s7"]); audit=read_csv(req["audit"])
    target_path=path_from_audit(audit,TARGET_NAME)
    target=read_csv(target_path); signals=read_csv(req["signals"]); handling=read_csv(req["handling"])
    selected=set(s15.get("selected_output_policies", []))
    for df in (target,signals):
        for c in ("dataset","entry_time","policy","filter"):
            if c in df.columns: df[c]=df[c].astype(str)
    fmin=pd.to_datetime(s7.get("feature_min_time"), errors="coerce"); fmax=pd.to_datetime(s7.get("feature_max_time"), errors="coerce")
    target["time_norm"]=pd.to_datetime(target["entry_time"], errors="coerce")
    t_all=target[(target["time_norm"]>=fmin)&(target["time_norm"]<=fmax)].copy()
    t_sel=t_all[t_all["policy"].isin(selected)].copy(); t_other=t_all[~t_all["policy"].isin(selected)].copy(); s_sel=signals[signals["policy"].isin(selected)].copy()
    pol=pd.DataFrame([
        {"scope":"direct_target_policy_scope","rows":len(t_sel),"policies":";".join(sorted(t_sel["policy"].unique())) if not t_sel.empty else ""},
        {"scope":"non_direct_target_policy_scope","rows":len(t_other),"policies":";".join(sorted(t_other["policy"].unique())) if not t_other.empty else ""},
        {"scope":"replay_direct_policy_scope","rows":len(s_sel),"policies":";".join(sorted(s_sel["policy"].unique())) if not s_sel.empty else ""},
    ])
    write_csv(out/"04_25c16_selected_scope_policy_matrix.csv", pol)
    tkey=t_sel[["dataset","entry_time","policy","filter"]].drop_duplicates(); skey=s_sel[["dataset","entry_time","policy","filter"]].drop_duplicates()
    cmp=skey.merge(tkey,on=["dataset","entry_time","policy","filter"],how="outer",indicator=True)
    mx=cmp["_merge"].value_counts(dropna=False).reset_index(); mx.columns=["compare_status","filter_rows"]
    write_csv(out/"05_25c16_selected_scope_filter_compare_matrix.csv", mx)
    other=t_other.groupby(["policy","filter"],dropna=False).size().reset_index(name="non_direct_target_rows").sort_values("non_direct_target_rows",ascending=False) if not t_other.empty else pd.DataFrame(columns=["policy","filter","non_direct_target_rows"])
    write_csv(out/"06_25c16_excluded_source_only_target_policy_matrix.csv", other)
    both=int((cmp["_merge"]=="both").sum()); left=int((cmp["_merge"]=="left_only").sum()); right=int((cmp["_merge"]=="right_only").sum())
    dec=pd.DataFrame([
        {"decision_id":"D001","question":"non-direct policy rows separated","decision":"YES","observed":len(t_other)},
        {"decision_id":"D002","question":"direct policy exact match","decision":"YES" if left==0 and right==0 else "NO","observed":f"both={both}; left={left}; right={right}"},
        {"decision_id":"D003","question":"direct policy review required","decision":"YES" if left+right>0 else "NO","observed":left+right},
        {"decision_id":"D004","question":"CoreB enable allowed","decision":"NO","observed":False},
    ])
    write_csv(out/"07_25c16_selected_scope_mismatch_decision_matrix.csv", dec)
    nxt=pd.DataFrame([
        {"rank":1,"next_step":"25C17_COREB_SELECTED_SCOPE_MISMATCH_ROOT_CAUSE_AUDIT_ONLY","allowed_now":True,"purpose":"review remaining direct policy mismatch"},
        {"rank":2,"next_step":"CoreB live evaluator","allowed_now":False,"purpose":"blocked"},
    ])
    write_csv(out/"08_25c16_next_step_plan.csv", nxt)
    unnecessary=["25C15 older reports","non-direct row details unless debugging","target ledger alone"]
    necessary=["01_25c16_GOLD_V2_COREB_SELECTED_SCOPE_TARGET_REVIEW_AUDIT_ONLY_REPORT.md","02_25c16_coreb_selected_scope_target_review_summary.json","04_25c16_selected_scope_policy_matrix.csv","05_25c16_selected_scope_filter_compare_matrix.csv","06_25c16_excluded_source_only_target_policy_matrix.csv","07_25c16_selected_scope_mismatch_decision_matrix.csv","08_25c16_next_step_plan.csv"]
    write_csv(out/"00_不要_25c16_file_request_list.csv", pd.DataFrame([{"section":"00_不要_貼らなくてOK","rank":i+1,"item":x} for i,x in enumerate(unnecessary)] + [{"section":"必要・貼ってほしい","rank":i+1,"item":x} for i,x in enumerate(necessary)]))
    status=STATUS if left+right>0 else "COREB_SELECTED_SCOPE_TARGET_REVIEW_COMPLETED_AUDIT_ONLY_SELECTED_SCOPE_EXACT_MATCH_REVIEW_REQUIRED"
    summary={"created_utc":datetime.now(timezone.utc).isoformat(),"step":STEP,"status":status,"audit_only":True,"condition_changed":False,"full_coreb_parity":False,"selected_output_policies":sorted(selected),"selected_scope_target_rows":int(len(tkey)),"selected_scope_replay_rows":int(len(skey)),"non_direct_target_rows":int(len(t_other[["dataset","entry_time","policy","filter"]].drop_duplicates())) if not t_other.empty else 0,"selected_scope_both":both,"selected_scope_left_only":left,"selected_scope_right_only":right,"coreb_live_evaluator_unblocked":False,"next_recommended_step":"25C17_COREB_SELECTED_SCOPE_MISMATCH_ROOT_CAUSE_AUDIT_ONLY","total_stop_rows":0}
    write_json(out/"02_25c16_coreb_selected_scope_target_review_summary.json", summary)
    report="\n".join(["# GOLD V2 25C16 CoreB selected-scope target review audit-only report","",f"Created UTC: {summary['created_utc']}",f"Step: `{STEP}`",f"Status: `{status}`","","## Policy scope matrix","",md_table(pol),"","## Direct policy compare matrix","",md_table(mx),"","## Non-direct target policy matrix","",md_table(other),"","## Decisions","",md_table(dec),"","## File request list","","```text","00_不要_貼らなくてOK",*[f"00-{i+1}. {x}" for i,x in enumerate(unnecessary)],"","必要・貼ってほしい",*[f"{i+1:02d}. {x}" for i,x in enumerate(necessary)],"```","","## Next step plan","",md_table(nxt),"","## Safety","","CoreB remains blocked. External/live actions remain off."])
    lp(out/"01_25c16_GOLD_V2_COREB_SELECTED_SCOPE_TARGET_REVIEW_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")
    print(json.dumps({"status":status,"selected_scope_both":both,"selected_scope_left_only":left,"selected_scope_right_only":right,"next_recommended_step":summary["next_recommended_step"]}, ensure_ascii=False, indent=2))
    return 0

if __name__=="__main__": raise SystemExit(main())
