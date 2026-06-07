#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse, json, os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Sequence
import pandas as pd

STEP = "25C3_COREB_INTERSECTION_ONLY_DRY_RUN_IMPLEMENTATION_AUDIT_ONLY"
PASS_STATUS = "COREB_INTERSECTION_ONLY_DRY_RUN_IMPLEMENTED_AUDIT_ONLY_REVIEW_REQUIRED"
STOP_STATUS = "25C3_STOP_MISSING_INPUT_OR_UNSAFE_STATE_AUDIT_ONLY"
IN25C2 = "gold_v2_25c2_coreb_intersection_only_dry_run_plan_audit_only"
IN25B3 = "gold_v2_25b3_coreb_source_shortlist_content_audit_only"
OUT_DIR = "gold_v2_25c3_coreb_intersection_only_dry_run_implementation_audit_only"
RAW_LEDGER_NAME = "rr125_raw_signal_ledger.csv"
TARGET_LEDGER_NAME = "rr125_top_ledgers.csv"
COMBINED_NAME = "frozen_coreB_combined_evaluator_definition_20260604.json"
UNIVERSE_NAME = "frozen_coreB_same_count_source_universe_20260604.json"

SAFETY_FLAGS = {
    "source_recovery_execution_allowed_now": False,
    "source_mutation_allowed": False,
    "source_identity_finalization_allowed_now": False,
    "live_evaluator_final_signal_allowed": False,
    "final_signal_allowed": False,
    "discord_send_allowed": False,
    "mt5_order_allowed": False,
    "ai_api_allowed": False,
    "live_hook_allowed": False,
    "no_signal_discord_notification_allowed": False,
    "old_gold_disc8_quarantined": True,
    "source_recovery_chain_status": "PAUSED_AT_24AF",
}

def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--output-dir", default=None)
    return p.parse_args(argv)

def repo_root() -> Path: return Path(__file__).resolve().parents[2]
def files_dir_from_repo() -> Path:
    r = repo_root(); return r.parents[1] if len(r.parents) >= 2 else r.parent
def fx_outputs() -> Path: return files_dir_from_repo() / "FX_OUTPUTS"
def lp(path: Path) -> Path:
    if os.name != "nt": return path
    s = str(path)
    if s.startswith("\\\\?\\"): return Path(s)
    if s.startswith("\\\\"): return Path("\\\\?\\UNC\\" + s[2:])
    return Path("\\\\?\\" + s)

def read_csv(path: Path, usecols: list[str] | None = None) -> pd.DataFrame:
    last = None
    for enc in ("utf-8-sig", "utf-8", "cp932"):
        try: return pd.read_csv(lp(path), encoding=enc, keep_default_na=False, usecols=usecols)
        except Exception as e: last = e
    raise RuntimeError(f"Could not read CSV {path}: {last}")
def read_json(path: Path) -> dict[str, Any]: return json.loads(lp(path).read_text(encoding="utf-8-sig"))
def write_csv(path: Path, df: pd.DataFrame) -> None:
    lp(path.parent).mkdir(parents=True, exist_ok=True); df.to_csv(lp(path), index=False, encoding="utf-8-sig")
def write_json(path: Path, obj: dict[str, Any]) -> None:
    lp(path.parent).mkdir(parents=True, exist_ok=True); lp(path).write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
def md_table(df: pd.DataFrame, max_rows: int = 60) -> str:
    if df.empty: return "_No rows._"
    v = df.head(max_rows); cols = list(v.columns)
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"]*len(cols)) + " |"]
    for _, r in v.iterrows(): lines.append("| " + " | ".join(str(r[c]).replace("|","\\|").replace("\n"," ") for c in cols) + " |")
    if len(df) > max_rows: lines.append(f"| ... | truncated {len(df)-max_rows} more rows |" + " |"*max(0,len(cols)-2))
    return "\n".join(lines)

def path_from_audit(df: pd.DataFrame, name: str) -> Path:
    colp = "normalized_path" if "normalized_path" in df.columns else "path"
    absp = "absolute_path" if "absolute_path" in df.columns else colp
    m = df[df[colp].astype(str).str.contains(name, case=False, regex=False, na=False)]
    return Path(str(m.iloc[0][absp])) if not m.empty else Path("")

def safety_problems(s: dict[str, Any]) -> list[str]:
    p = []
    if s.get("status") != "COREB_INTERSECTION_ONLY_DRY_RUN_PLAN_READY_AUDIT_ONLY_EXECUTION_BLOCKED": p.append("25C2 status mismatch")
    if not bool(s.get("intersection_only")): p.append("25C2 intersection_only not true")
    if bool(s.get("full_coreb_parity")): p.append("25C2 full_coreb_parity unexpectedly true")
    for k, expected in SAFETY_FLAGS.items():
        if s.get(k) != expected: p.append(f"safety flag mismatch: {k}")
    for k in ["coreb_live_evaluator_unblocked","source_recovery_executed","source_mutation_executed","same_count_exact_parity_proven","cluster_membership_parity_proven","target_key_parity_proven"]:
        if bool(s.get(k)): p.append(f"unsafe prior state: {k}")
    return p

def collect_rules(obj: Any, key: str) -> list[dict[str, Any]]:
    if isinstance(obj, dict):
        if key in obj and isinstance(obj[key], list): return [x for x in obj[key] if isinstance(x, dict)]
        out=[]
        for v in obj.values(): out += collect_rules(v, key)
        return out
    if isinstance(obj, list):
        out=[]
        for v in obj: out += collect_rules(v, key)
        return out
    return []

def condition_objects(rule: dict[str, Any]) -> list[dict[str, Any]]:
    out=[]
    for k in ("base_condition_objects", "added_filter_condition_objects", "conditions", "condition_objects"):
        v = rule.get(k)
        if isinstance(v, list): out += [x for x in v if isinstance(x, dict)]
    return out

def rule_key(rule: dict[str, Any]) -> tuple[str,str,str,str,str]:
    return tuple(str(rule.get(k,"")) for k in ["candidate_id","origin_id","policy","variant","rr_bucket"])

def match_rule_rows(df: pd.DataFrame, rule: dict[str, Any]) -> pd.Series:
    m = pd.Series(True, index=df.index)
    for k in ["candidate_id","origin_id","policy","variant","rr_bucket","direction"]:
        v = str(rule.get(k,""))
        if v and k in df.columns: m &= df[k].astype(str).eq(v)
    return m

def eval_rule(df: pd.DataFrame, rule: dict[str, Any]) -> pd.Series:
    m = match_rule_rows(df, rule)
    for c in condition_objects(rule):
        field = str(c.get("field", c.get("feature", "")))
        op = str(c.get("operator", c.get("op", "")))
        val = c.get("value", c.get("threshold", None))
        if not field or field not in df.columns or val is None:
            return pd.Series(False, index=df.index)
        x = pd.to_numeric(df[field], errors="coerce"); tv = pd.to_numeric(pd.Series([val]), errors="coerce").iloc[0]
        if pd.isna(tv): return pd.Series(False, index=df.index)
        if op == ">": m &= x.gt(tv)
        elif op == "<=": m &= x.le(tv)
        elif op == ">=": m &= x.ge(tv)
        elif op == "<": m &= x.lt(tv)
        elif op in ("==", "="): m &= x.eq(tv)
        else: return pd.Series(False, index=df.index)
        m &= x.notna()
    return m.fillna(False)

def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv); out_dir = Path(args.output_dir).expanduser().resolve() if args.output_dir else fx_outputs()/OUT_DIR; lp(out_dir).mkdir(parents=True, exist_ok=True)
    in25c2 = fx_outputs()/IN25C2; in25b3 = fx_outputs()/IN25B3
    req = {"25c2_summary": in25c2/"02_25c2_coreb_intersection_only_dry_run_plan_summary.json", "25b3_file_audit": in25b3/"gold_v2_25b3_shortlist_file_content_audit.csv"}
    ia = pd.DataFrame([{"role":k,"path":str(v),"required":True,"exists":lp(v).exists(),"status":"PASS" if lp(v).exists() else "STOP"} for k,v in req.items()])
    write_csv(out_dir/"03_25c3_input_audit.csv", ia)
    if not bool(ia["exists"].all()):
        write_json(out_dir/"02_25c3_coreb_intersection_only_dry_run_implementation_summary.json", {"created_utc":datetime.now(timezone.utc).isoformat(),"step":STEP,"status":STOP_STATUS,"total_stop_rows":int((ia["status"]=="STOP").sum()),**SAFETY_FLAGS}); return 2
    s25c2 = read_json(req["25c2_summary"]); problems = safety_problems(s25c2); audit = read_csv(req["25b3_file_audit"])
    raw_path = path_from_audit(audit, RAW_LEDGER_NAME); target_path = path_from_audit(audit, TARGET_LEDGER_NAME); combined_path = path_from_audit(audit, COMBINED_NAME); universe_path = path_from_audit(audit, UNIVERSE_NAME)
    feature_path = Path(str(s25c2.get("feature_source_path", "")))
    if not feature_path or not lp(feature_path).exists():
        # known accepted source path from 25C0/25C1 chain if absent in 25C2
        fp = fx_outputs()/"gold_v2_coreb_combined_required_feature_snapshot_audit_only"/"gold_v2_coreb_combined_required_feature_snapshot.csv"
        feature_path = fp
    for label,p in [("raw",raw_path),("target",target_path),("combined",combined_path),("universe",universe_path),("feature",feature_path)]:
        if not str(p) or not lp(p).exists(): problems.append(f"missing {label} path")
    paths_df = pd.DataFrame([{"role":"raw_signal_ledger","path":str(raw_path)},{"role":"target_top_ledger_compare_only","path":str(target_path)},{"role":"combined_evaluator","path":str(combined_path)},{"role":"same_count_universe","path":str(universe_path)},{"role":"feature_source","path":str(feature_path)}])
    write_csv(out_dir/"04_25c3_resolved_source_paths.csv", paths_df)
    if problems:
        write_json(out_dir/"02_25c3_coreb_intersection_only_dry_run_implementation_summary.json", {"created_utc":datetime.now(timezone.utc).isoformat(),"step":STEP,"status":STOP_STATUS,"status_problems":problems,"total_stop_rows":len(problems),**SAFETY_FLAGS}); return 2

    raw = read_csv(raw_path); feat = read_csv(feature_path); target = read_csv(target_path)
    raw["time_norm"] = pd.to_datetime(raw["entry_time"], errors="coerce"); feat["time_norm"] = pd.to_datetime(feat["time"], errors="coerce")
    join = raw.merge(feat.drop(columns=["time"], errors="ignore"), on="time_norm", how="inner", suffixes=("","_feature"))
    join_summary = pd.DataFrame([{"raw_rows":len(raw),"feature_rows":len(feat),"intersection_rows":len(join),"excluded_raw_rows":len(raw)-len(join),"intersection_only":True,"full_coreb_parity":False}])
    write_csv(out_dir/"06_25c3_intersection_join_summary.csv", join_summary)

    combined = read_json(combined_path); universe = read_json(universe_path)
    selected_rules = collect_rules(combined, "selected_rules") or collect_rules(combined, "source_rule_conditions")
    universe_rules = collect_rules(universe, "source_universe_rules")
    schema = pd.DataFrame([{"rule_role":"selected_rules","rule_count":len(selected_rules)},{"rule_role":"source_universe_rules","rule_count":len(universe_rules)}])
    write_csv(out_dir/"05_25c3_rule_schema_audit.csv", schema)

    source_hits=[]; source_count = pd.Series(0, index=join.index, dtype="int64")
    for i, rule in enumerate(universe_rules):
        hit = eval_rule(join, rule); source_count += hit.astype(int)
        if hit.any():
            tmp = join.loc[hit, ["dataset","entry_time","candidate_id","origin_id","policy","direction","variant","rr_bucket"]].copy(); tmp["source_rule_index"] = i; source_hits.append(tmp)
    source_by_entry = join[["dataset","entry_time","candidate_id","origin_id","policy","direction","variant","rr_bucket"]].copy(); source_by_entry["source_universe_hit_count"] = source_count.values
    write_csv(out_dir/"07_25c3_source_universe_hit_counts_by_entry.csv", source_by_entry)

    selected_any = pd.Series(False, index=join.index)
    selected_hits=[]
    for i, rule in enumerate(selected_rules):
        hit = eval_rule(join, rule); selected_any |= hit
        if hit.any():
            tmp = join.loc[hit, ["dataset","entry_time","candidate_id","origin_id","policy","direction","variant","rr_bucket"]].copy(); tmp["selected_rule_index"] = i; selected_hits.append(tmp)
    selected_df = pd.concat(selected_hits, ignore_index=True) if selected_hits else pd.DataFrame(columns=["dataset","entry_time","candidate_id","origin_id","policy","direction","variant","rr_bucket","selected_rule_index"])
    write_csv(out_dir/"08_25c3_selected_rule_hit_rows.csv", selected_df)

    signal = join.loc[selected_any & source_count.ge(15), ["dataset","entry_time","candidate_id","origin_id","policy","direction","variant","rr_bucket"]].copy()
    signal["source_universe_hit_count"] = source_count.loc[signal.index].values; signal["intersection_only"] = True; signal["full_coreb_parity"] = False
    write_csv(out_dir/"09_25c3_diagnostic_signal_rows.csv", signal)

    # diagnostic target compare by entry_time only + direction if available; not parity claim
    target_key_cols = [c for c in ["dataset","entry_time","top_direction","top_candidate_id","policy","filter"] if c in target.columns]
    sig_keys = signal[["dataset","entry_time","candidate_id","policy"]].drop_duplicates() if not signal.empty else pd.DataFrame(columns=["dataset","entry_time","candidate_id","policy"])
    tgt = target.copy(); tgt["target_row"] = True
    cmp = sig_keys.merge(tgt, on=[c for c in ["dataset","entry_time","policy"] if c in sig_keys.columns and c in tgt.columns], how="outer", indicator=True)
    counts = cmp["_merge"].value_counts(dropna=False).reset_index(); counts.columns=["compare_status","rows"]
    counts["compare_scope"] = "diagnostic_intersection_only_not_full_parity"
    write_csv(out_dir/"10_25c3_target_compare_summary.csv", counts)

    gates = pd.DataFrame([
        {"gate_id":"G001","gate":"intersection join executed","observed":True,"required":True,"status":"PASS"},
        {"gate_id":"G002","gate":"condition objects evaluated","observed":True,"required":True,"status":"PASS"},
        {"gate_id":"G003","gate":"full_coreb_parity","observed":False,"required":False,"status":"BLOCKED"},
        {"gate_id":"G004","gate":"source_recovery_execution","observed":False,"required":False,"status":"BLOCKED"},
        {"gate_id":"G005","gate":"CoreB live evaluator unblock","observed":False,"required":False,"status":"BLOCKED"},
    ])
    write_csv(out_dir/"11_25c3_acceptance_gate_matrix.csv", gates)
    next_plan = pd.DataFrame([
        {"rank":1,"next_step":"25C4_COREB_INTERSECTION_DRY_RUN_REVIEW_AUDIT_ONLY","allowed_now":True,"purpose":"Review diagnostic counts and compare failures"},
        {"rank":2,"next_step":"CoreB full parity recovery","allowed_now":False,"purpose":"Requires full coverage or accepted limitation"},
        {"rank":3,"next_step":"CoreB live evaluator","allowed_now":False,"purpose":"Still blocked"},
    ])
    write_csv(out_dir/"12_25c3_next_step_plan.csv", next_plan)
    unnecessary=["25C2 CSV details already processed","25C1B and older report/summary files","rr125_top_ledgers.csv alone"]
    necessary=["01_25c3_GOLD_V2_COREB_INTERSECTION_ONLY_DRY_RUN_IMPLEMENTATION_AUDIT_ONLY_REPORT.md","02_25c3_coreb_intersection_only_dry_run_implementation_summary.json","06_25c3_intersection_join_summary.csv","09_25c3_diagnostic_signal_rows.csv","10_25c3_target_compare_summary.csv","11_25c3_acceptance_gate_matrix.csv","12_25c3_next_step_plan.csv"]
    reqdf=pd.DataFrame([{"section":"00_不要_貼らなくてOK","rank":i+1,"item":x} for i,x in enumerate(unnecessary)] + [{"section":"必要・貼ってほしい","rank":i+1,"item":x} for i,x in enumerate(necessary)])
    write_csv(out_dir/"00_不要_25c3_file_request_list.csv", reqdf)
    summary={"created_utc":datetime.now(timezone.utc).isoformat(),"step":STEP,"status":PASS_STATUS,"audit_only":True,"intersection_only":True,"full_coreb_parity":False,"raw_rows_total":len(raw),"intersection_rows":len(join),"excluded_raw_rows":len(raw)-len(join),"selected_rule_count":len(selected_rules),"source_universe_rule_count":len(universe_rules),"selected_rule_hit_rows":int(len(selected_df)),"diagnostic_signal_rows":int(len(signal)),"source_recovery_executed":False,"source_mutation_executed":False,"coreb_live_evaluator_unblocked":False,"same_count_exact_parity_proven":False,"cluster_membership_parity_proven":False,"target_key_parity_proven":False,"next_recommended_step":"25C4_COREB_INTERSECTION_DRY_RUN_REVIEW_AUDIT_ONLY","total_stop_rows":0,**SAFETY_FLAGS}
    write_json(out_dir/"02_25c3_coreb_intersection_only_dry_run_implementation_summary.json", summary)
    report="\n".join(["# GOLD V2 25C3 CoreB intersection-only dry-run implementation audit-only report","",f"Created UTC: {summary['created_utc']}",f"Step: `{STEP}`",f"Status: `{PASS_STATUS}`","","## Boundary","","25C3 executed diagnostic intersection-only dry-run. It does not prove full CoreB parity or unblock CoreB.","","## Intersection join summary","",md_table(join_summary),"","## Rule schema audit","",md_table(schema),"","## Target compare summary","",md_table(counts),"","## Acceptance gates","",md_table(gates),"","## File request list","","```text","00_不要_貼らなくてOK",*[f"00-{i+1}. {x}" for i,x in enumerate(unnecessary)],"","必要・貼ってほしい",*[f"{i+1:02d}. {x}" for i,x in enumerate(necessary)],"```","","## Next step plan","",md_table(next_plan),"","## Safety","","CoreB remains blocked. Source recovery/live/final/external actions remain off."])
    lp(out_dir/"01_25c3_GOLD_V2_COREB_INTERSECTION_ONLY_DRY_RUN_IMPLEMENTATION_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")
    print(json.dumps({"status":PASS_STATUS,"intersection_rows":len(join),"diagnostic_signal_rows":len(signal),"full_coreb_parity":False,"next_recommended_step":summary["next_recommended_step"]},ensure_ascii=False,indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
