#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import hashlib, json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import pandas as pd

STEP = "GOLD_V3_12_DEPLOYABILITY_REVIEW_PACKET_AUDIT_ONLY"
OUT_NAME = "12_deployability_review_packet_audit_only"
EXPECTED_11_STATUS = "GOLD_V3_11_RULE_EXPRESSION_PREVIEW_READY_AUDIT_ONLY"
REVIEW_READY_LABELS = {"REVIEW_READY", "REVIEW_READY_WITH_NEGATIVE_FOLD_RISK"}
ACTIONS = {"discord_send_allowed": False, "mt5_order_allowed": False, "ai_api_allowed": False, "live_hook_allowed": False, "live_evaluator_allowed": False, "final_signal_allowed": False}


def repo_root() -> Path: return Path(__file__).resolve().parents[2]

def files_root() -> Path:
    r=repo_root()
    return r.parents[1] if len(r.parents) >= 2 else r.parent

def v3_output_root() -> Path: return files_root() / "FX_OUTPUTS" / "gold_v3"

def out_dir() -> Path:
    p=v3_output_root()/OUT_NAME
    p.mkdir(parents=True, exist_ok=True)
    return p

def dir11() -> Path: return v3_output_root() / "11_rule_expression_preview_audit_only"

def sha256_file(p: Path) -> str:
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(1024*1024), b""):
            h.update(b)
    return h.hexdigest()

def read_json(p: Path) -> dict[str, Any]:
    if not p.exists(): return {}
    try: return json.loads(p.read_text(encoding="utf-8"))
    except Exception: return {}

def clean(x: Any) -> Any:
    if isinstance(x, dict): return {str(k): clean(v) for k,v in x.items()}
    if isinstance(x, list): return [clean(v) for v in x]
    try:
        if pd.isna(x): return None
    except Exception: pass
    return x.isoformat() if hasattr(x,"isoformat") else x

def write_json(p: Path, obj: dict[str, Any]) -> None:
    p.write_text(json.dumps(clean(obj), ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")

def md(df: pd.DataFrame, n:int=80) -> str:
    if df.empty: return "_No rows._"
    d=df.head(n).fillna("")
    lines=["| "+" | ".join(map(str,d.columns))+" |", "| "+" | ".join(["---"]*len(d.columns))+" |"]
    for _,r in d.iterrows():
        lines.append("| "+" | ".join(str(r[c]).replace("|","\\|").replace("\n"," ")[:500] for c in d.columns)+" |")
    return "\n".join(lines)

def input_inventory(paths:list[Path]) -> pd.DataFrame:
    rows=[]
    for p in paths:
        rows.append({"path":str(p),"filename":p.name,"exists":p.exists(),"bytes":p.stat().st_size if p.exists() else 0,"sha256":sha256_file(p) if p.exists() else ""})
    return pd.DataFrame(rows)

def main() -> int:
    created=datetime.now(timezone.utc).isoformat()
    out=out_dir()
    paths=[dir11()/"gold_v3_11_summary.json", dir11()/"gold_v3_11_rule_expression_preview_rows.csv", dir11()/"gold_v3_11_boundary_consensus_diagnostics.csv"]
    inv_df=input_inventory(paths)
    s11=read_json(paths[0])
    inputs_ok=bool(inv_df["exists"].all())
    upstream_ok=s11.get("status")==EXPECTED_11_STATUS
    if inputs_ok:
        rows=pd.read_csv(paths[1])
        diag=pd.read_csv(paths[2])
        packet=rows[rows["readiness_label"].isin(REVIEW_READY_LABELS)].copy()
        deferred=rows[~rows["readiness_label"].isin(REVIEW_READY_LABELS)].copy()
        if not packet.empty:
            packet["human_decision"] = "PENDING_HUMAN_REVIEW"
            packet["allowed_decisions"] = "APPROVE_FOR_NEXT_AUDIT_ONLY_REPLAY|REJECT|REQUEST_MORE_AUDIT"
            packet["auto_approved"] = False
            packet["final_candidate_approved"] = False
            packet["live_deployable"] = False
            packet=packet.sort_values(["readiness_label","review_score"], ascending=[True,False])
        readiness_summary=rows.groupby(["readiness_label","feature_family"], dropna=False).agg(
            rows=("feature_column","count"),
            profiles=("profile_id", lambda x: len(set(x))),
            features=("feature_column", lambda x: len(set(x))),
            max_review_score=("review_score","max"),
            avg_test_lift_mean=("test_lift_mean","mean"),
            avg_test_result_mean=("test_avg_result_mean","mean"),
        ).reset_index().sort_values(["readiness_label","max_review_score"], ascending=[True,False])
    else:
        rows=pd.DataFrame(); diag=pd.DataFrame(); packet=pd.DataFrame(); deferred=pd.DataFrame(); readiness_summary=pd.DataFrame()
    packet_ok=inputs_ok and upstream_ok and not packet.empty
    status="GOLD_V3_12_DEPLOYABILITY_REVIEW_PACKET_READY_AUDIT_ONLY" if packet_ok else ("GOLD_V3_12_DEPLOYABILITY_REVIEW_PACKET_INPUT_REVIEW_REQUIRED_AUDIT_ONLY" if not (inputs_ok and upstream_ok) else "GOLD_V3_12_DEPLOYABILITY_REVIEW_PACKET_BLOCKED_AUDIT_ONLY")
    decision_df=pd.DataFrame([
        ["inputs_present",inputs_ok,True,"PASS" if inputs_ok else "FAIL"],
        ["upstream_11_ok",upstream_ok,True,"PASS" if upstream_ok else "FAIL"],
        ["review_ready_packet_rows",len(packet),">0","PASS" if len(packet)>0 else "FAIL"],
        ["deferred_rows",len(deferred),">=0","PASS"],
        ["auto_approval",False,False,"PASS"],
        ["final_candidate_approval",False,False,"PASS"],
        ["threshold_finalization",False,False,"PASS"],
        ["model_training",False,False,"PASS"],
        ["signals_generated",False,False,"PASS"],
        ["zip_output_created",False,False,"PASS"],
        ["external_actions",False,False,"PASS"],
    ],columns=["decision_item","observed","required","status"])
    blocker_df=pd.DataFrame([
        ["G3-12-001","11 inputs","CLOSED" if inputs_ok and upstream_ok else "OPEN","HARD","11 preview rows and diagnostics required."],
        ["G3-12-002","review packet","CLOSED" if len(packet)>0 else "OPEN","HARD","At least one review-ready row is required for a packet."],
        ["G3-12-003","human decision","OPEN_HUMAN_ACTION_REQUIRED","HARD","Packet rows remain PENDING_HUMAN_REVIEW."],
        ["G3-12-004","final approval","CLOSED_BLOCKED_BY_POLICY","HARD","No final candidate approval in this step."],
        ["G3-12-005","threshold finalization","CLOSED_BLOCKED_BY_POLICY","HARD","No threshold finalization in this step."],
        ["G3-12-006","signal/live","CLOSED_BLOCKED_BY_POLICY","HARD","No signals or live integration."],
        ["G3-12-007","zip output","CLOSED_DISABLED","INFO","ZIP output disabled."],
        ["G3-12-008","external actions","CLOSED","HARD","No external actions performed."],
    ],columns=["blocker_id","component","status","severity","detail"])
    summary={"created_utc":created,"step":STEP,"status":status,"audit_only":True,"source_recovery_approved":False,"input_preview_rows":int(len(rows)),"deployability_review_packet_rows":int(len(packet)),"deferred_rows":int(len(deferred)),"readiness_summary_rows":int(len(readiness_summary)),"packet_readiness_counts":packet["readiness_label"].value_counts().to_dict() if not packet.empty else {},"deferred_readiness_counts":deferred["readiness_label"].value_counts().to_dict() if not deferred.empty else {},"top_packet_rows":packet.head(20).to_dict(orient="records") if not packet.empty else [],"human_decision_required":True,"auto_approval":False,"final_candidate_approval":False,"threshold_finalization":False,"model_training":False,"signals_generated":False,"zip_output_created":False,"external_actions":ACTIONS}
    inv_df.to_csv(out/"gold_v3_12_input_inventory.csv",index=False,encoding="utf-8-sig")
    packet.to_csv(out/"gold_v3_12_deployability_review_packet.csv",index=False,encoding="utf-8-sig")
    deferred.to_csv(out/"gold_v3_12_deferred_candidate_diagnostics.csv",index=False,encoding="utf-8-sig")
    readiness_summary.to_csv(out/"gold_v3_12_readiness_summary.csv",index=False,encoding="utf-8-sig")
    decision_df.to_csv(out/"gold_v3_12_decision_matrix.csv",index=False,encoding="utf-8-sig")
    blocker_df.to_csv(out/"gold_v3_12_blocker_matrix.csv",index=False,encoding="utf-8-sig")
    write_json(out/"gold_v3_12_summary.json",summary)
    report="\n".join(["# GOLD V3 12 deployability review packet audit-only report","",f"Created UTC: {created}",f"Status: `{status}`","","## Deployability review packet",md(packet),"","## Readiness summary",md(readiness_summary),"","## Decision matrix",md(decision_df),"","## Blockers",md(blocker_df),"","## Safety","- GOLD V3 only; no V2 artifacts used.","- Human decision packet only; no auto approval.","- APPROVE_FOR_NEXT_AUDIT_ONLY_REPLAY is not final approval and not live deployment approval.","- No threshold finalization, model training, signals, or ZIP.","- External actions remain OFF."])
    (out/"GOLD_V3_12_DEPLOYABILITY_REVIEW_PACKET_AUDIT_ONLY_REPORT.md").write_text(report,encoding="utf-8")
    print(json.dumps({"status":status,"output_dir":str(out),"zip_output_created":False},ensure_ascii=False,indent=2))
    print("No ZIP, auto approval, final candidate approval, threshold finalization, model training, signals, Discord, MT5, AI API, live hook, live evaluator, or final signal action was performed.")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
