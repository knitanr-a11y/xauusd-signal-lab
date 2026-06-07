#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse, json, os, re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Sequence
import pandas as pd

STEP = "25C13_COREB_POLICY_SOURCE_LINKAGE_AUDIT_ONLY"
STATUS = "COREB_POLICY_SOURCE_LINKAGE_AUDIT_COMPLETED_AUDIT_ONLY_SELECTED_POLICY_ASSIGNMENT_REVIEW_REQUIRED"
STOP = "25C13_STOP_MISSING_INPUT_AUDIT_ONLY"
OUT_DIR = "gold_v2_25c13_coreb_policy_source_linkage_audit_only"
IN25C12 = "gold_v2_25c12_coreb_policy_mapping_audit_only"

CONFIGS = [
    "configs/gold_v2/frozen_coreB_same_count_source_universe_20260604.json",
    "configs/gold_v2/frozen_coreB_rr125_buy_confluence_rules_20260603.json",
    "configs/gold_v2/frozen_coreB_rr125_source_rule_conditions_20260603.json",
    "configs/gold_v2/frozen_coreB_combined_evaluator_definition_20260604.json",
]
POLICIES = ["RR125_from_ALL_BUY_rules", "RR125_from_RR1_rules"]

def repo_root() -> Path: return Path(__file__).resolve().parents[2]
def files_root() -> Path:
    r = repo_root(); return r.parents[1] if len(r.parents) >= 2 else r.parent
def fx_outputs() -> Path: return files_root() / "FX_OUTPUTS"
def lp(p: Path) -> Path:
    if os.name != "nt": return p
    s = str(p)
    if s.startswith("\\\\?\\"): return Path(s)
    if s.startswith("\\\\"): return Path("\\\\?\\UNC\\" + s[2:])
    return Path("\\\\?\\" + s)
def read_json(p: Path) -> Any: return json.loads(lp(p).read_text(encoding="utf-8-sig"))
def read_text(p: Path) -> str: return lp(p).read_text(encoding="utf-8-sig")
def read_csv(p: Path) -> pd.DataFrame:
    last=None
    for enc in ("utf-8-sig","utf-8","cp932"):
        try: return pd.read_csv(lp(p), encoding=enc, keep_default_na=False)
        except Exception as e: last=e
    raise RuntimeError(f"read failed {p}: {last}")
def write_csv(p: Path, df: pd.DataFrame) -> None:
    lp(p.parent).mkdir(parents=True, exist_ok=True); df.to_csv(lp(p), index=False, encoding="utf-8-sig")
def write_json(p: Path, obj: dict) -> None:
    lp(p.parent).mkdir(parents=True, exist_ok=True); lp(p).write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
def md_table(df: pd.DataFrame, n: int = 80) -> str:
    if df.empty: return "_No rows._"
    v=df.head(n); cols=list(v.columns)
    out=["| "+" | ".join(cols)+" |", "| "+" | ".join(["---"]*len(cols))+" |"]
    for _,r in v.iterrows(): out.append("| "+" | ".join(str(r[c]).replace("|","\\|") for c in cols)+" |")
    return "\n".join(out)
def flatten(obj: Any, path: str = ""):
    if isinstance(obj, dict):
        for k,v in obj.items(): yield from flatten(v, f"{path}.{k}" if path else str(k))
    elif isinstance(obj, list):
        for i,v in enumerate(obj): yield from flatten(v, f"{path}[{i}]")
    else:
        yield path, obj

def main(argv: Optional[Sequence[str]]=None) -> int:
    ap=argparse.ArgumentParser(); ap.add_argument("--output-dir", default=None); args=ap.parse_args(argv)
    out=Path(args.output_dir).resolve() if args.output_dir else fx_outputs()/OUT_DIR; lp(out).mkdir(parents=True, exist_ok=True)
    req={"25c12_summary": fx_outputs()/IN25C12/"02_25c12_coreb_policy_mapping_summary.json"}
    for c in CONFIGS: req[c]=repo_root()/c
    ia=pd.DataFrame([{"role":k,"path":str(v),"exists":lp(v).exists(),"status":"PASS" if lp(v).exists() else "STOP"} for k,v in req.items()])
    write_csv(out/"03_25c13_input_audit.csv", ia)
    if not bool(ia["exists"].all()):
        write_json(out/"02_25c13_coreb_policy_source_linkage_summary.json", {"created_utc":datetime.now(timezone.utc).isoformat(),"step":STEP,"status":STOP,"total_stop_rows":int((ia["status"]=="STOP").sum())}); return 2
    s12=read_json(req["25c12_summary"])
    inv=[]; samples=[]
    for c in CONFIGS:
        p=repo_root()/c; txt=read_text(p); data=read_json(p)
        for pol in POLICIES:
            inv.append({"config_path":c,"policy":pol,"text_hits":txt.count(pol)})
        for path,val in flatten(data):
            sv=str(val)
            for pol in POLICIES:
                if pol in sv or pol in path:
                    samples.append({"config_path":c,"policy":pol,"json_path":path,"value_sample":sv[:240]})
    inv_df=pd.DataFrame(inv); samples_df=pd.DataFrame(samples)
    write_csv(out/"04_25c13_config_policy_token_inventory.csv", inv_df)
    write_csv(out/"05_25c13_config_policy_path_samples.csv", samples_df)
    link_rows=[]
    for pol in POLICIES:
        sub=inv_df[inv_df["policy"].eq(pol)]
        link_rows.append({
            "policy":pol,
            "configs_with_policy_token":int(sub[sub["text_hits"].gt(0)]["config_path"].nunique()),
            "total_token_hits":int(sub["text_hits"].sum()),
            "raw_seen_from_25c12": bool((pol=="RR125_from_ALL_BUY_rules" and s12.get("all_buy_policy_missing_in_replay")) or (pol=="RR125_from_RR1_rules" and s12.get("rr1_policy_overexpanded_in_replay"))),
            "review_class":"POLICY_TOKEN_ABSENT_OR_UNLINKED" if int(sub["text_hits"].sum())==0 else "POLICY_TOKEN_PRESENT_REVIEW_ASSIGNMENT",
        })
    link=pd.DataFrame(link_rows)
    write_csv(out/"06_25c13_pipeline_config_linkage_matrix.csv", link)
    all_buy_hits=int(inv_df[inv_df["policy"].eq("RR125_from_ALL_BUY_rules")]["text_hits"].sum())
    rr1_hits=int(inv_df[inv_df["policy"].eq("RR125_from_RR1_rules")]["text_hits"].sum())
    dec=pd.DataFrame([
        {"decision_id":"D001","question":"ALL_BUY token appears in frozen configs","decision":"YES" if all_buy_hits>0 else "NO","reason":f"hits={all_buy_hits}"},
        {"decision_id":"D002","question":"RR1 token appears in frozen configs","decision":"YES" if rr1_hits>0 else "NO","reason":f"hits={rr1_hits}"},
        {"decision_id":"D003","question":"selected policy assignment needs review","decision":"YES","reason":"25C12 showed raw/target vs selected/replay policy mismatch"},
        {"decision_id":"D004","question":"CoreB enable allowed","decision":"NO","reason":"mapping review incomplete"},
    ])
    write_csv(out/"07_25c13_policy_source_linkage_decision_matrix.csv", dec)
    nxt=pd.DataFrame([
        {"rank":1,"next_step":"25C14_COREB_SELECTED_POLICY_ASSIGNMENT_AUDIT_ONLY","allowed_now":True,"purpose":"inspect selected rule assignment and policy handling"},
        {"rank":2,"next_step":"CoreB live evaluator","allowed_now":False,"purpose":"blocked"},
    ])
    write_csv(out/"08_25c13_next_step_plan.csv", nxt)
    unnecessary=["25C12 older reports", "large row samples", "target ledger alone"]
    necessary=["01_25c13_GOLD_V2_COREB_POLICY_SOURCE_LINKAGE_AUDIT_ONLY_REPORT.md","02_25c13_coreb_policy_source_linkage_summary.json","04_25c13_config_policy_token_inventory.csv","05_25c13_config_policy_path_samples.csv","06_25c13_pipeline_config_linkage_matrix.csv","07_25c13_policy_source_linkage_decision_matrix.csv","08_25c13_next_step_plan.csv"]
    write_csv(out/"00_不要_25c13_file_request_list.csv", pd.DataFrame([{"section":"00_不要_貼らなくてOK","rank":i+1,"item":x} for i,x in enumerate(unnecessary)] + [{"section":"必要・貼ってほしい","rank":i+1,"item":x} for i,x in enumerate(necessary)]))
    summary={"created_utc":datetime.now(timezone.utc).isoformat(),"step":STEP,"status":STATUS,"audit_only":True,"condition_changed":False,"full_coreb_parity":False,"all_buy_config_token_hits":all_buy_hits,"rr1_config_token_hits":rr1_hits,"selected_policy_assignment_review_required":True,"coreb_live_evaluator_unblocked":False,"next_recommended_step":"25C14_COREB_SELECTED_POLICY_ASSIGNMENT_AUDIT_ONLY","total_stop_rows":0}
    write_json(out/"02_25c13_coreb_policy_source_linkage_summary.json", summary)
    report="\n".join(["# GOLD V2 25C13 CoreB policy source linkage audit-only report","",f"Created UTC: {summary['created_utc']}",f"Step: `{STEP}`",f"Status: `{STATUS}`","","## Policy token inventory","",md_table(inv_df),"","## Pipeline/config linkage","",md_table(link),"","## Decisions","",md_table(dec),"","## File request list","","```text","00_不要_貼らなくてOK",*[f"00-{i+1}. {x}" for i,x in enumerate(unnecessary)],"","必要・貼ってほしい",*[f"{i+1:02d}. {x}" for i,x in enumerate(necessary)],"```","","## Next step plan","",md_table(nxt),"","## Safety","","CoreB remains blocked. External/live actions remain off."])
    lp(out/"01_25c13_GOLD_V2_COREB_POLICY_SOURCE_LINKAGE_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")
    print(json.dumps({"status":STATUS,"all_buy_config_token_hits":all_buy_hits,"rr1_config_token_hits":rr1_hits,"next_recommended_step":summary["next_recommended_step"]}, ensure_ascii=False, indent=2))
    return 0

if __name__ == "__main__": raise SystemExit(main())
