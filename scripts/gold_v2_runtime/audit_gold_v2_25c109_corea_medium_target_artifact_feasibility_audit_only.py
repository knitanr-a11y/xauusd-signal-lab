#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import hashlib, json, re, zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import pandas as pd

STEP = "25C109_COREA_MEDIUM_TARGET_ARTIFACT_FEASIBILITY_AUDIT_ONLY"
OUT_NAME = "gold_v2_25c109_corea_medium_target_artifact_feasibility_audit_only"
INPUTS = ["25c108_summary.json", "25c108_replay_target_shortlist.csv", "25c108_target_column_risk_rows.csv", "25c108_component_replay_scope.csv"]
EXPECTED_STATUS = "COREA_MEDIUM_REPLAY_TARGET_SHORTLIST_READY_AUDIT_ONLY_LIVE_BLOCKED"
ACTIONS = {"discord_send_allowed": False, "mt5_order_allowed": False, "ai_api_allowed": False, "live_hook_allowed": False, "live_evaluator_allowed": False, "final_signal_allowed": False}
FUTURE = ["exit_time", "top_exit_time", "close_time", "outcome", "result", "win", "loss", "hit", "mae", "mfe", "realized"]
PROFIT_PAT = ["profit", "profit_r", "selected_profit", "selected_profit_r", "top_profit", "top_profit_r", "pnl"]
SELECT_PAT = ["selected", "top_candidate_id", "top_variant", "top_direction", "final_sot", "arbitration", "priority", "chosen", "prefer"]
ENTRY_PAT = ["entry_time", "top_entry_time", "direction", "dataset", "strategy_id", "range96", "ret96", "trend_eff96", "tr_mean_32", "regime", "count", "score", "condition", "filter"]


def repo_root() -> Path: return Path(__file__).resolve().parents[2]
def files_root() -> Path:
    r = repo_root(); return r.parents[1] if len(r.parents) >= 2 else r.parent
def fx_outputs() -> Path: return files_root() / "FX_OUTPUTS"
def out_dir() -> Path:
    p = fx_outputs() / OUT_NAME; p.mkdir(parents=True, exist_ok=True); return p

def find_file(name: str) -> Path | None:
    for c in [repo_root() / name, fx_outputs() / name]:
        if c.exists(): return c
    for base in [fx_outputs(), repo_root(), files_root()]:
        if base.exists():
            found = sorted(base.rglob(name))
            if found: return found[0]
    return None

def resolve_path(raw: str) -> Path | None:
    p = Path(str(raw))
    if p.exists(): return p
    return find_file(p.name)

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

def inv(paths: dict[str, Path | None]) -> pd.DataFrame:
    rows=[]
    for n,p in paths.items():
        r={"filename":n,"exists":bool(p and p.exists()),"path":str(p) if p else ""}
        if p and p.exists():
            r["bytes"]=p.stat().st_size; r["sha256"]=sha256_file(p)
            if p.suffix.lower()==".csv": r["row_count"]=len(pd.read_csv(p))
        rows.append(r)
    return pd.DataFrame(rows)

def md(df: pd.DataFrame, n: int = 80) -> str:
    if df.empty: return "_No rows._"
    d=df.head(n).fillna("")
    lines=["| "+" | ".join(map(str,d.columns))+" |","| "+" | ".join(["---"]*len(d.columns))+" |"]
    for _,r in d.iterrows(): lines.append("| "+" | ".join(str(r[c]).replace("|","\\|").replace("\n"," ")[:500] for c in d.columns)+" |")
    return "\n".join(lines)

def flatten_json_keys(obj: Any, prefix: str="") -> list[str]:
    keys=[]
    if isinstance(obj, dict):
        for k,v in obj.items():
            nk=f"{prefix}.{k}" if prefix else str(k); keys.append(nk); keys.extend(flatten_json_keys(v,nk))
    elif isinstance(obj, list):
        for v in obj[:50]: keys.extend(flatten_json_keys(v, f"{prefix}[]" if prefix else "[]"))
    return keys

def keys_and_rows(p: Path) -> tuple[list[str], int]:
    try:
        if p.suffix.lower()==".csv":
            head=pd.read_csv(p,nrows=0); rows=sum(1 for _ in p.open("rb"))-1
            return list(head.columns), max(rows,0)
        if p.suffix.lower()==".json":
            obj=json.loads(p.read_text(encoding="utf-8", errors="ignore")); return flatten_json_keys(obj), -1
    except Exception: return [], -1
    return [], -1

def fam(k: str) -> str:
    low=k.lower()
    if any(t in low for t in FUTURE): return "future_or_outcome"
    if any(t in low for t in PROFIT_PAT): return "profit_or_representative"
    if any(t in low for t in SELECT_PAT) or re.search(r"is_.*selected", low): return "selection_or_arbitration"
    if any(t in low for t in ENTRY_PAT): return "entry_time_candidate"
    return "other"

def main() -> int:
    created=datetime.now(timezone.utc).isoformat(); out=out_dir(); paths={n:find_file(n) for n in INPUTS}
    input_inv=inv(paths); s108=read_json(paths["25c108_summary.json"]); targets=read_csv(paths["25c108_replay_target_shortlist.csv"])
    inputs_ok=bool(input_inv["exists"].all()) if not input_inv.empty else False; upstream_ok=s108.get("status")==EXPECTED_STATUS
    load_rows=[]; col_rows=[]
    for _,r in targets.iterrows():
        rp=str(r.get("relative_path","")); comp=str(r.get("component","")); role=str(r.get("artifact_role","")); risk=float(r.get("risk_score",0) or 0)
        p=resolve_path(rp); readable=bool(p and p.exists())
        keys=[]; nrows=-1
        if readable:
            keys,nrows=keys_and_rows(p)
        counts={"future_or_outcome":0,"profit_or_representative":0,"selection_or_arbitration":0,"entry_time_candidate":0,"other":0}
        for k in keys:
            f=fam(k); counts[f]=counts.get(f,0)+1
            if f!="other": col_rows.append({"component":comp,"artifact_role":role,"relative_path":rp,"resolved_path":str(p) if p else "","column_or_key":k,"family":f})
        load_rows.append({"component":comp,"artifact_role":role,"relative_path":rp,"resolved_path":str(p) if p else "","readable":readable,"suffix":p.suffix.lower() if p else "","rows":nrows,"risk_score":risk,"column_or_key_count":len(keys),**counts})
    load=pd.DataFrame(load_rows); cols=pd.DataFrame(col_rows)
    prim=[]
    for comp, preferred in [("CoreA","gold_v2_13b_corea_selected_source_rows.csv"),("MEDIUM","gold_v2_13d_medium_selected_after_internal_priority.csv")]:
        sub=load[load["component"].eq(comp) & load["readable"].astype(bool)].copy() if not load.empty else pd.DataFrame()
        if sub.empty: continue
        pref=sub[sub["relative_path"].astype(str).str.endswith(preferred)]
        pick=(pref.iloc[0] if not pref.empty else sub.sort_values(["risk_score"],ascending=False).iloc[0]).to_dict()
        pick["primary_reason"]="preferred_artifact" if not pref.empty else "highest_readable_risk_score"
        prim.append(pick)
    primary=pd.DataFrame(prim)
    has_corea=not primary.empty and primary["component"].eq("CoreA").any(); has_medium=not primary.empty and primary["component"].eq("MEDIUM").any()
    if not (inputs_ok and upstream_ok): status="COREA_MEDIUM_TARGET_ARTIFACT_FEASIBILITY_INPUT_REVIEW_REQUIRED_AUDIT_ONLY"
    elif has_corea and has_medium: status="COREA_MEDIUM_PRIMARY_REPLAY_TARGETS_READY_AUDIT_ONLY_LIVE_BLOCKED"
    elif has_corea or has_medium: status="COREA_MEDIUM_PRIMARY_REPLAY_TARGETS_PARTIAL_AUDIT_ONLY_LIVE_BLOCKED"
    else: status="COREA_MEDIUM_PRIMARY_REPLAY_TARGETS_UNREADABLE_AUDIT_ONLY_LIVE_BLOCKED"
    decision=pd.DataFrame([
        ["inputs_present",inputs_ok,True,"PASS" if inputs_ok else "FAIL"],
        ["upstream_25c108_ok",upstream_ok,True,"PASS" if upstream_ok else "FAIL"],
        ["target_artifacts",len(load),">0","PASS" if len(load) else "FAIL"],
        ["readable_targets",int(load["readable"].sum()) if not load.empty else 0,">0","PASS" if (not load.empty and int(load["readable"].sum())>0) else "FAIL"],
        ["corea_primary_ready",has_corea,True,"PASS" if has_corea else "FAIL"],
        ["medium_primary_ready",has_medium,True,"PASS" if has_medium else "FAIL"],
        ["corea_medium_live_evaluator_allowed",False,False,"PASS"],
        ["final_signal_allowed",False,False,"PASS"],
        ["source_recovery_approved",False,False,"PASS"],
        ["a002_used",False,False,"PASS"],
    ],columns=["decision_item","observed","required","status"])
    blockers=pd.DataFrame([
        ["B109-001","25C108 inputs","CLOSED" if inputs_ok and upstream_ok else "OPEN","HARD","25C108 outputs must be present."],
        ["B109-002","CoreA primary replay target","REVIEW" if has_corea else "OPEN","HARD","CoreA target readable." if has_corea else "CoreA target not readable."],
        ["B109-003","MEDIUM primary replay target","REVIEW" if has_medium else "OPEN","HARD","MEDIUM target readable." if has_medium else "MEDIUM target not readable."],
        ["B109-004","entry-time replay proof","OPEN","HARD","Target readiness is not replay proof; next step must test entry-time reproducibility."],
        ["B109-005","CoreA/MEDIUM live evaluator","OPEN","HARD","Live remains blocked."],
        ["B109-006","source recovery","OPEN","HARD","No source recovery approval."],
        ["B109-007","A002","CLOSED_FOR_MAIN_PATH","INFO","A002 is auxiliary-only and not used."],
    ],columns=["blocker_id","component","status","severity","detail"])
    summary={"created_utc":created,"step":STEP,"status":status,"audit_only":True,"source_recovery_approved":False,"upstream_25c108_ok":upstream_ok,"inputs_present":inputs_ok,"target_artifacts":int(len(load)),"readable_targets":int(load["readable"].sum()) if not load.empty else 0,"corea_primary_ready":bool(has_corea),"medium_primary_ready":bool(has_medium),"corea_medium_live_evaluator_allowed":False,"final_signal_allowed":False,"a002_used":False,"external_actions":ACTIONS}
    load.to_csv(out/"25c109_target_load_matrix.csv",index=False,encoding="utf-8-sig")
    cols.to_csv(out/"25c109_target_column_family_matrix.csv",index=False,encoding="utf-8-sig")
    primary.to_csv(out/"25c109_primary_replay_targets.csv",index=False,encoding="utf-8-sig")
    decision.to_csv(out/"25c109_decision_matrix.csv",index=False,encoding="utf-8-sig")
    blockers.to_csv(out/"25c109_blocker_matrix.csv",index=False,encoding="utf-8-sig")
    write_json(out/"25c109_summary.json",summary)
    report="\n".join(["# GOLD V2 25C109 CoreA/MEDIUM target artifact feasibility audit-only report","",f"Created UTC: {created}",f"Status: `{status}`","","## Decision matrix",md(decision),"","## Primary replay targets",md(primary),"","## Target load matrix",md(load),"","## Target column family matrix",md(cols),"","## Blockers",md(blockers),"","## Safety","- audit_only: true","- target feasibility only; no replay proof","- A002 not used","- source recovery not approved","- live evaluator/final signal/external actions remain OFF","- NO_SIGNAL must not notify Discord"])
    (out/"GOLD_V2_25C109_COREA_MEDIUM_TARGET_ARTIFACT_FEASIBILITY_AUDIT_ONLY_REPORT.md").write_text(report,encoding="utf-8")
    zip_path=fx_outputs()/f"{OUT_NAME}.zip"
    if zip_path.exists(): zip_path.unlink()
    with zipfile.ZipFile(zip_path,"w",compression=zipfile.ZIP_DEFLATED) as z:
        for p in out.iterdir(): z.write(p,arcname=p.name)
    print(json.dumps({"status":status,"output_dir":str(out),"zip":str(zip_path)},ensure_ascii=False,indent=2))
    print("No Discord, MT5, AI API, live hook, live evaluator, or final signal action was performed.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
