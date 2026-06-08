#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import hashlib, json, zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import pandas as pd

STEP = "25C108_COREA_MEDIUM_REPLAY_TARGET_SHORTLIST_AUDIT_ONLY"
OUT_NAME = "gold_v2_25c108_corea_medium_replay_target_shortlist_audit_only"
INPUTS = ["25c107_summary.json", "25c107_artifact_inventory.csv", "25c107_column_key_risk_rows.csv", "25c107_component_artifact_risk_summary.csv", "25c107_decision_matrix.csv", "25c107_blocker_matrix.csv"]
EXPECTED_STATUS = "COREA_MEDIUM_SOT_PRECHECK_RISK_FOUND_AUDIT_ONLY_LIVE_BLOCKED"
ACTIONS = {"discord_send_allowed": False, "mt5_order_allowed": False, "ai_api_allowed": False, "live_hook_allowed": False, "live_evaluator_allowed": False, "final_signal_allowed": False}
COREA_ROLES = ["corea_mapping_or_frozen;corea_source_or_selected", "corea_source_or_selected", "corea_mapping_or_frozen"]
MEDIUM_ROLES = ["medium_final_sot;medium_source_or_selected", "medium_arbitration;medium_source_or_selected", "medium_arbitration", "medium_source_or_selected", "medium_arbitration;medium_final_sot", "medium_mapping_or_frozen;medium_source_or_selected"]


def repo_root() -> Path: return Path(__file__).resolve().parents[2]
def files_root() -> Path:
    r = repo_root(); return r.parents[1] if len(r.parents) >= 2 else r.parent
def fx_outputs() -> Path: return files_root() / "FX_OUTPUTS"
def out_dir() -> Path:
    p = fx_outputs() / OUT_NAME; p.mkdir(parents=True, exist_ok=True); return p

def find_file(name: str) -> Path | None:
    for c in [repo_root() / name, fx_outputs() / name]:
        if c.exists(): return c
    for base in [fx_outputs(), repo_root()]:
        if base.exists():
            found = sorted(base.rglob(name))
            if found: return found[0]
    return None

def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""): h.update(b)
    return h.hexdigest()

def clean(x: Any) -> Any:
    if isinstance(x, dict): return {str(k): clean(v) for k, v in x.items()}
    if isinstance(x, list): return [clean(v) for v in x]
    try:
        if pd.isna(x): return None
    except Exception: pass
    return x.isoformat() if hasattr(x, "isoformat") else x

def write_json(p: Path, obj: dict[str, Any]) -> None:
    p.write_text(json.dumps(clean(obj), ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")

def read_json(p: Path | None) -> dict[str, Any]:
    if not p or not p.exists(): return {}
    try: return json.loads(p.read_text(encoding="utf-8"))
    except Exception: return {}

def read_csv(p: Path | None) -> pd.DataFrame:
    return pd.read_csv(p) if p and p.exists() else pd.DataFrame()

def inventory(paths: dict[str, Path | None]) -> pd.DataFrame:
    rows=[]
    for n,p in paths.items():
        r={"filename":n,"exists":bool(p and p.exists()),"path":str(p) if p else ""}
        if p and p.exists():
            r["bytes"]=p.stat().st_size; r["sha256"]=sha256_file(p)
            if p.suffix.lower()==".csv":
                r["row_count"]=len(pd.read_csv(p)); r["columns"]=";".join(pd.read_csv(p,nrows=0).columns)
        rows.append(r)
    return pd.DataFrame(rows)

def md(df: pd.DataFrame, n: int = 50) -> str:
    if df.empty: return "_No rows._"
    d=df.head(n).fillna("")
    lines=["| "+" | ".join(map(str,d.columns))+" |","| "+" | ".join(["---"]*len(d.columns))+" |"]
    for _,r in d.iterrows(): lines.append("| "+" | ".join(str(r[c]).replace("|","\\|").replace("\n"," ")[:500] for c in d.columns)+" |")
    return "\n".join(lines)

def role_bonus(component: str, role: str) -> int:
    roles = COREA_ROLES if component == "CoreA" else MEDIUM_ROLES if component == "MEDIUM" else []
    return max(0, 100 - 10 * roles.index(role)) if role in roles else 0

def main() -> int:
    created=datetime.now(timezone.utc).isoformat(); out=out_dir(); paths={n:find_file(n) for n in INPUTS}
    inv_inputs=inventory(paths); s107=read_json(paths["25c107_summary.json"])
    inv=read_csv(paths["25c107_artifact_inventory.csv"]); risks=read_csv(paths["25c107_column_key_risk_rows.csv"]); comp=read_csv(paths["25c107_component_artifact_risk_summary.csv"])
    inputs_ok=bool(inv_inputs["exists"].all()) if not inv_inputs.empty else False
    upstream_ok=s107.get("status")==EXPECTED_STATUS
    targets=pd.DataFrame()
    if not inv.empty:
        inv=inv.copy()
        for c in ["hard_future_or_outcome_keys","profit_or_representative_keys","selection_or_arbitration_keys","entry_time_candidate_keys"]:
            if c not in inv.columns: inv[c]=0
        inv["role_bonus"]=inv.apply(lambda r: role_bonus(str(r.get("component","")), str(r.get("artifact_role",""))), axis=1)
        inv["risk_score"]=inv["role_bonus"] + inv["hard_future_or_outcome_keys"]*10 + inv["profit_or_representative_keys"]*8 + inv["selection_or_arbitration_keys"]*5 + inv["entry_time_candidate_keys"]
        inv["target_reason"] = inv.apply(lambda r: f"role={r.get('artifact_role')} hard={r.get('hard_future_or_outcome_keys')} profit={r.get('profit_or_representative_keys')} selection={r.get('selection_or_arbitration_keys')} entry={r.get('entry_time_candidate_keys')}", axis=1)
        pool=inv[(inv["component"].isin(["CoreA","MEDIUM"])) & (inv["risk_score"]>0)].copy()
        target_parts=[]
        for component, maxn in [("CoreA",5),("MEDIUM",8)]:
            sub=pool[pool["component"].eq(component)].sort_values(["risk_score","hard_future_or_outcome_keys","profit_or_representative_keys"], ascending=False).head(maxn)
            target_parts.append(sub)
        targets=pd.concat(target_parts, ignore_index=True) if target_parts else pd.DataFrame()
    target_risks = risks[risks["relative_path"].isin(targets["relative_path"])] if (not risks.empty and not targets.empty) else pd.DataFrame()
    scope = targets.groupby("component").agg(targets=("relative_path","count"), hard_keys=("hard_future_or_outcome_keys","sum"), profit_keys=("profit_or_representative_keys","sum"), selection_keys=("selection_or_arbitration_keys","sum"), entry_keys=("entry_time_candidate_keys","sum"), max_risk_score=("risk_score","max")).reset_index() if not targets.empty else pd.DataFrame()
    has_corea = not targets.empty and targets["component"].eq("CoreA").any()
    has_medium = not targets.empty and targets["component"].eq("MEDIUM").any()
    if not (inputs_ok and upstream_ok): status="COREA_MEDIUM_REPLAY_TARGET_SHORTLIST_INPUT_REVIEW_REQUIRED_AUDIT_ONLY"
    elif has_corea and has_medium: status="COREA_MEDIUM_REPLAY_TARGET_SHORTLIST_READY_AUDIT_ONLY_LIVE_BLOCKED"
    elif has_corea or has_medium: status="COREA_MEDIUM_REPLAY_TARGET_SHORTLIST_PARTIAL_AUDIT_ONLY_LIVE_BLOCKED"
    else: status="COREA_MEDIUM_REPLAY_TARGET_SHORTLIST_INPUT_REVIEW_REQUIRED_AUDIT_ONLY"
    decision=pd.DataFrame([
        ["inputs_present",inputs_ok,True,"PASS" if inputs_ok else "FAIL"],
        ["upstream_25c107_ok",upstream_ok,True,"PASS" if upstream_ok else "FAIL"],
        ["corea_targets_found",int(has_corea),1,"PASS" if has_corea else "FAIL"],
        ["medium_targets_found",int(has_medium),1,"PASS" if has_medium else "FAIL"],
        ["target_count",len(targets),">0","PASS" if len(targets) else "FAIL"],
        ["corea_medium_live_evaluator_allowed",False,False,"PASS"],
        ["final_signal_allowed",False,False,"PASS"],
        ["source_recovery_approved",False,False,"PASS"],
        ["a002_used",False,False,"PASS"],
    ],columns=["decision_item","observed","required","status"])
    blockers=pd.DataFrame([
        ["B108-001","25C107 inputs","CLOSED" if inputs_ok and upstream_ok else "OPEN","HARD","25C107 outputs must be present."],
        ["B108-002","CoreA replay targets","REVIEW" if has_corea else "OPEN","HARD","CoreA replay targets selected." if has_corea else "CoreA replay targets missing."],
        ["B108-003","MEDIUM replay targets","REVIEW" if has_medium else "OPEN","HARD","MEDIUM replay targets selected." if has_medium else "MEDIUM replay targets missing."],
        ["B108-004","entry-time replay proof","OPEN","HARD","Shortlist is not replay proof; deeper entry-time replay still required."],
        ["B108-005","CoreA/MEDIUM live evaluator","OPEN","HARD","Live remains blocked until entry-time reproducibility is proven."],
        ["B108-006","source recovery","OPEN","HARD","No source recovery approval."],
        ["B108-007","A002","CLOSED_FOR_MAIN_PATH","INFO","A002 is auxiliary-only and not used."],
    ],columns=["blocker_id","component","status","severity","detail"])
    summary={"created_utc":created,"step":STEP,"status":status,"audit_only":True,"source_recovery_approved":False,"upstream_25c107_ok":upstream_ok,"inputs_present":inputs_ok,"target_count":int(len(targets)),"corea_targets_found":bool(has_corea),"medium_targets_found":bool(has_medium),"corea_medium_live_evaluator_allowed":False,"final_signal_allowed":False,"a002_used":False,"external_actions":ACTIONS}
    inv_inputs.to_csv(out/"25c108_input_inventory.csv",index=False,encoding="utf-8-sig")
    targets.to_csv(out/"25c108_replay_target_shortlist.csv",index=False,encoding="utf-8-sig")
    scope.to_csv(out/"25c108_component_replay_scope.csv",index=False,encoding="utf-8-sig")
    target_risks.to_csv(out/"25c108_target_column_risk_rows.csv",index=False,encoding="utf-8-sig")
    decision.to_csv(out/"25c108_decision_matrix.csv",index=False,encoding="utf-8-sig")
    blockers.to_csv(out/"25c108_blocker_matrix.csv",index=False,encoding="utf-8-sig")
    write_json(out/"25c108_summary.json",summary)
    report="\n".join(["# GOLD V2 25C108 CoreA/MEDIUM replay target shortlist audit-only report","",f"Created UTC: {created}",f"Status: `{status}`","","## Decision matrix",md(decision),"","## Component replay scope",md(scope),"","## Replay target shortlist",md(targets[[c for c in ["component","artifact_role","relative_path","risk_score","target_reason"] if c in targets.columns]] if not targets.empty else targets),"","## Target column/key risk rows",md(target_risks),"","## Blockers",md(blockers),"","## Safety","- audit_only: true","- target shortlist only; no replay proof","- A002 not used","- source recovery not approved","- live evaluator/final signal/external actions remain OFF","- NO_SIGNAL must not notify Discord"])
    (out/"GOLD_V2_25C108_COREA_MEDIUM_REPLAY_TARGET_SHORTLIST_AUDIT_ONLY_REPORT.md").write_text(report,encoding="utf-8")
    zip_path=fx_outputs()/f"{OUT_NAME}.zip"
    if zip_path.exists(): zip_path.unlink()
    with zipfile.ZipFile(zip_path,"w",compression=zipfile.ZIP_DEFLATED) as z:
        for p in out.iterdir(): z.write(p,arcname=p.name)
    print(json.dumps({"status":status,"output_dir":str(out),"zip":str(zip_path)},ensure_ascii=False,indent=2))
    print("No Discord, MT5, AI API, live hook, live evaluator, or final signal action was performed.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
