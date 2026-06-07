#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse, json, os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Sequence
import pandas as pd

STEP="25C34_COREB_G1_RETENTION_AWARE_DRY_RUN_AUDIT_ONLY"
STATUS="COREB_G1_RETENTION_AWARE_DRY_RUN_COMPLETED_AUDIT_ONLY_RESULT_REVIEW_REQUIRED"
STATUS_EXACT="COREB_G1_RETENTION_AWARE_DRY_RUN_COMPLETED_AUDIT_ONLY_EXACT_MATCH_REVIEW_REQUIRED"
STOP="25C34_STOP_MISSING_INPUT_AUDIT_ONLY"
OUT_DIR="gold_v2_25c34_coreb_g1_retention_aware_dry_run_audit_only"
IN33="gold_v2_25c33_coreb_g1_retention_aware_narrowing_plan_audit_only"
IN10="gold_v2_25c10_coreb_target_filter_contract_replay_dry_run_audit_only"
IN15="gold_v2_25c15_coreb_selected_policy_replay_contract_audit_only"
IN7="gold_v2_25c7_coreb_target_compare_mismatch_triage_audit_only"
INB3="gold_v2_25b3_coreb_source_shortlist_content_audit_only"
TARGET_NAME="rr125_top_ledgers.csv"
KEY=["dataset","entry_time","policy"]

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
def norm(df):
    out=df.copy()
    for c in KEY: out[c]=out[c].astype(str)
    return out
def path_from_audit(df,name):
    m=df[df["normalized_path"].astype(str).str.contains(name, case=False, regex=False, na=False)]
    return Path(str(m.iloc[0]["absolute_path"])) if not m.empty else Path("")
def compare_variant(name, replay_df, target_key):
    rk=norm(replay_df)[KEY].drop_duplicates()
    cmp=rk.merge(target_key,on=KEY,how="outer",indicator=True)
    cmp["_merge"]=cmp["_merge"].astype(str)
    row={"variant":name,"replay_g1_rows":int(len(rk)),"both":int((cmp["_merge"]=="both").sum()),"left_only":int((cmp["_merge"]=="left_only").sum()),"right_only":int((cmp["_merge"]=="right_only").sum()),"exact_match":bool((cmp["_merge"]!="both").sum()==0)}
    return row, cmp

def main(argv:Optional[Sequence[str]]=None)->int:
    ap=argparse.ArgumentParser(); ap.add_argument("--output-dir", default=None); args=ap.parse_args(argv)
    out=Path(args.output_dir).resolve() if args.output_dir else fx_outputs()/OUT_DIR; lp(out).mkdir(parents=True, exist_ok=True)
    req={
        "s33":fx_outputs()/IN33/"02_25c33_coreb_g1_retention_aware_narrowing_plan_summary.json",
        "bundles":fx_outputs()/IN33/"04_25c33_retention_aware_bundle_matrix.csv",
        "members":fx_outputs()/IN33/"05_25c33_bundle_filter_membership.csv",
        "signals":fx_outputs()/IN10/"04_25c10_filter_replay_signal_rows.csv",
        "s15":fx_outputs()/IN15/"02_25c15_coreb_selected_policy_replay_contract_summary.json",
        "s7":fx_outputs()/IN7/"02_25c7_coreb_target_compare_mismatch_triage_summary.json",
        "audit":fx_outputs()/INB3/"gold_v2_25b3_shortlist_file_content_audit.csv",
    }
    ia=pd.DataFrame([{"role":k,"path":str(v),"exists":lp(v).exists(),"status":"PASS" if lp(v).exists() else "STOP"} for k,v in req.items()])
    write_csv(out/"03_25c34_input_audit.csv", ia)
    if not bool(ia["exists"].all()):
        write_json(out/"02_25c34_coreb_g1_retention_aware_dry_run_summary.json", {"created_utc":datetime.now(timezone.utc).isoformat(),"step":STEP,"status":STOP,"total_stop_rows":int((ia["status"]=="STOP").sum())}); return 2
    s33=read_json(req["s33"])
    if not s33.get("requires_human_acceptance_before_25c34", False):
        write_json(out/"02_25c34_coreb_g1_retention_aware_dry_run_summary.json", {"created_utc":datetime.now(timezone.utc).isoformat(),"step":STEP,"status":"25C34_STOP_25C33_ACCEPTANCE_CONTRACT_MISSING_AUDIT_ONLY","total_stop_rows":1}); return 2
    bundles=read_csv(req["bundles"]); members=read_csv(req["members"]); signals=norm(read_csv(req["signals"])); s15=read_json(req["s15"]); s7=read_json(req["s7"]); audit=read_csv(req["audit"])
    signals["filter"]=signals.get("filter",pd.Series(dtype=str)).astype(str)
    selected=set(s15.get("selected_output_policies", []))
    fmin=pd.to_datetime(s7.get("feature_min_time"), errors="coerce"); fmax=pd.to_datetime(s7.get("feature_max_time"), errors="coerce")
    target=norm(read_csv(path_from_audit(audit,TARGET_NAME)))
    target["time_norm"]=pd.to_datetime(target["entry_time"], errors="coerce")
    target=target[(target["time_norm"]>=fmin)&(target["time_norm"]<=fmax)&target["policy"].isin(selected)].copy()
    target_key=target[KEY].drop_duplicates()
    signals=signals[signals["policy"].isin(selected)].copy()
    variant_rows=[]; compare_frames=[]; contract_rows=[]
    base_row, base_cmp=compare_variant("BASELINE_CURRENT", signals, target_key)
    variant_rows.append(base_row); compare_frames.append(base_cmp.assign(variant="BASELINE_CURRENT"))
    for _,b in bundles.iterrows():
        bid=str(b["bundle_id"]); bname=str(b["bundle_name"])
        filters=set(members[members["bundle_id"].astype(str).eq(bid)]["filter"].astype(str).tolist())
        for f in sorted(filters): contract_rows.append({"variant":bid+"_"+bname,"bundle_id":bid,"bundle_name":bname,"filter":f,"simulated_exclusion":True,"conditions_changed":False})
        narrowed=signals[~signals["filter"].isin(filters)].copy()
        row, cmp=compare_variant(bid+"_"+bname, narrowed, target_key)
        variant_rows.append(row); compare_frames.append(cmp.assign(variant=bid+"_"+bname))
    contract=pd.DataFrame(contract_rows); matrix=pd.DataFrame(variant_rows)
    write_csv(out/"04_25c34_variant_filter_contract.csv", contract)
    write_csv(out/"05_25c34_variant_compare_matrix.csv", matrix)
    base=matrix[matrix["variant"].eq("BASELINE_CURRENT")].iloc[0]
    deltas=[]
    for _,r in matrix[~matrix["variant"].eq("BASELINE_CURRENT")].iterrows():
        for metric in ["left_only","right_only","both","replay_g1_rows"]:
            deltas.append({"variant":r["variant"],"metric":metric,"baseline":int(base[metric]),"variant_value":int(r[metric]),"delta":int(r[metric])-int(base[metric])})
    delta=pd.DataFrame(deltas)
    write_csv(out/"06_25c34_variant_delta_matrix.csv", delta)
    allcmp=pd.concat(compare_frames, ignore_index=True)
    by=allcmp.groupby(["variant","dataset","policy","_merge"],dropna=False).size().reset_index(name="entry_rows")
    write_csv(out/"07_25c34_variant_by_dataset_policy.csv", by)
    best=matrix.sort_values(["left_only","right_only"], ascending=[True,True]).iloc[0]["variant"]
    write_csv(out/"08_25c34_best_variant_left_only_samples.csv", allcmp[allcmp["variant"].eq(best)&allcmp["_merge"].eq("left_only")].sort_values(KEY).head(200))
    exact=bool(matrix[~matrix["variant"].eq("BASELINE_CURRENT")]["exact_match"].any())
    gates=pd.DataFrame([
        {"gate_id":"G001","gate":"25C33 accepted","observed":True,"status":"PASS"},
        {"gate_id":"G002","gate":"retention-aware dry-run executed audit-only","observed":True,"status":"PASS"},
        {"gate_id":"G003","gate":"any exact match reached","observed":exact,"status":"PASS" if exact else "REVIEW_REQUIRED"},
        {"gate_id":"G004","gate":"conditions changed","observed":False,"status":"PASS"},
        {"gate_id":"G005","gate":"CoreB live evaluator unblock","observed":False,"status":"BLOCKED"},
    ])
    write_csv(out/"09_25c34_acceptance_gate_matrix.csv", gates)
    nxt=pd.DataFrame([
        {"rank":1,"next_step":"25C35_COREB_G1_RETENTION_AWARE_DRY_RUN_RESULT_REVIEW_AUDIT_ONLY","allowed_now":True,"purpose":"review best bundle and remaining mismatch"},
        {"rank":2,"next_step":"CoreB live evaluator","allowed_now":False,"purpose":"blocked"},
    ])
    write_csv(out/"10_25c34_next_step_plan.csv", nxt)
    unnecessary=["25C33 older reports if summary is available","full replay rows","full target rows"]
    necessary=["01_25c34_GOLD_V2_COREB_G1_RETENTION_AWARE_DRY_RUN_AUDIT_ONLY_REPORT.md","02_25c34_coreb_g1_retention_aware_dry_run_summary.json","04_25c34_variant_filter_contract.csv","05_25c34_variant_compare_matrix.csv","06_25c34_variant_delta_matrix.csv","07_25c34_variant_by_dataset_policy.csv","08_25c34_best_variant_left_only_samples.csv","09_25c34_acceptance_gate_matrix.csv","10_25c34_next_step_plan.csv"]
    write_csv(out/"00_不要_25c34_file_request_list.csv", pd.DataFrame([{"section":"00_不要_貼らなくてOK","rank":i+1,"item":x} for i,x in enumerate(unnecessary)] + [{"section":"必要・貼ってほしい","rank":i+1,"item":x} for i,x in enumerate(necessary)]))
    best_row=matrix[matrix["variant"].eq(best)].iloc[0]
    status=STATUS_EXACT if exact else STATUS
    summary={"created_utc":datetime.now(timezone.utc).isoformat(),"step":STEP,"status":status,"audit_only":True,"dry_run_executed":True,"condition_changed":False,"full_coreb_parity":False,"variant_count":int(len(matrix)-1),"best_variant":str(best),"best_left_only":int(best_row["left_only"]),"best_right_only":int(best_row["right_only"]),"best_both":int(best_row["both"]),"any_exact_match":exact,"source_recovery_executed":False,"source_mutation_executed":False,"coreb_live_evaluator_unblocked":False,"next_recommended_step":"25C35_COREB_G1_RETENTION_AWARE_DRY_RUN_RESULT_REVIEW_AUDIT_ONLY","total_stop_rows":0}
    write_json(out/"02_25c34_coreb_g1_retention_aware_dry_run_summary.json", summary)
    report="\n".join(["# GOLD V2 25C34 CoreB G1 retention-aware dry-run audit-only report","",f"Created UTC: {summary['created_utc']}",f"Step: `{STEP}`",f"Status: `{status}`","","## Variant filter contract","",md_table(contract),"","## Variant compare matrix","",md_table(matrix),"","## Variant delta matrix","",md_table(delta),"","## Acceptance gates","",md_table(gates),"","## File request list","","```text","00_不要_貼らなくてOK",*[f"00-{i+1}. {x}" for i,x in enumerate(unnecessary)],"","必要・貼ってほしい",*[f"{i+1:02d}. {x}" for i,x in enumerate(necessary)],"```","","## Next step plan","",md_table(nxt),"","## Safety","","CoreB remains blocked. External/live actions remain off."])
    lp(out/"01_25c34_GOLD_V2_COREB_G1_RETENTION_AWARE_DRY_RUN_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")
    print(json.dumps({"status":status,"best_variant":str(best),"best_left_only":int(best_row["left_only"]),"next_recommended_step":summary["next_recommended_step"]}, ensure_ascii=False, indent=2))
    return 0

if __name__=="__main__": raise SystemExit(main())
