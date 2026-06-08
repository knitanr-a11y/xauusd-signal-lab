#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import hashlib, json, math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import pandas as pd

STEP = "GOLD_V3_09_HUMAN_REVIEW_CANDIDATE_SHORTLIST_AUDIT_ONLY"
OUT_NAME = "09_human_review_candidate_shortlist_audit_only"
EXPECTED_07_STATUS = "GOLD_V3_07_FEATURE_BUCKET_SCAN_READY_AUDIT_ONLY"
EXPECTED_08_STATUS = "GOLD_V3_08_BUCKET_BOUNDARY_PROVENANCE_READY_AUDIT_ONLY"
ACTIONS = {"discord_send_allowed": False, "mt5_order_allowed": False, "ai_api_allowed": False, "live_hook_allowed": False, "live_evaluator_allowed": False, "final_signal_allowed": False}

MIN_FOLDS = 6
MIN_POS_RATE = 0.80
MIN_ROWS = 3000


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def files_root() -> Path:
    r = repo_root()
    return r.parents[1] if len(r.parents) >= 2 else r.parent


def v3_output_root() -> Path:
    return files_root() / "FX_OUTPUTS" / "gold_v3"


def out_dir() -> Path:
    p = v3_output_root() / OUT_NAME
    p.mkdir(parents=True, exist_ok=True)
    return p


def dir07() -> Path:
    return v3_output_root() / "07_feature_bucket_lift_scan_audit_only"


def dir08() -> Path:
    return v3_output_root() / "08_bucket_boundary_provenance_audit_only"


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(1024*1024), b""):
            h.update(b)
    return h.hexdigest()


def read_json(p: Path) -> dict[str, Any]:
    if not p.exists(): return {}
    try: return json.loads(p.read_text(encoding="utf-8"))
    except Exception: return {}


def clean(x: Any) -> Any:
    if isinstance(x, dict): return {str(k): clean(v) for k, v in x.items()}
    if isinstance(x, list): return [clean(v) for v in x]
    try:
        if pd.isna(x): return None
    except Exception: pass
    return x.isoformat() if hasattr(x, "isoformat") else x


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


def review_score(row: pd.Series) -> float:
    return float(row["positive_test_fold_rate"])*100.0 + float(row["test_lift_mean"])*10.0 + float(row["test_avg_result_mean"]) + math.log10(float(row["test_rows_total"])+1.0)


def reject_reason(row: pd.Series) -> str:
    reasons=[]
    if int(row.get("folds",0)) < MIN_FOLDS: reasons.append("folds_lt_min")
    if float(row.get("positive_test_fold_rate",0)) < MIN_POS_RATE: reasons.append("positive_rate_lt_min")
    if float(row.get("test_avg_result_mean",0)) <= 0: reasons.append("test_avg_not_positive")
    if float(row.get("test_lift_mean",0)) <= 0: reasons.append("lift_not_positive")
    if int(row.get("test_rows_total",0)) < MIN_ROWS: reasons.append("rows_lt_min")
    if not bool(row.get("all_boundaries_valid", False)): reasons.append("boundary_invalid")
    return ";".join(reasons) if reasons else "PASS"


def main() -> int:
    created=datetime.now(timezone.utc).isoformat()
    out=out_dir()
    paths=[
        dir07()/"gold_v3_07_summary.json",
        dir07()/"gold_v3_07_feature_bucket_test_stability_summary.csv",
        dir08()/"gold_v3_08_summary.json",
        dir08()/"gold_v3_08_boundary_stability_summary.csv",
        dir08()/"gold_v3_08_selected_bucket_boundary_rows.csv",
    ]
    inv_df=input_inventory(paths)
    s07=read_json(paths[0]); s08=read_json(paths[2])
    inputs_ok=bool(inv_df["exists"].all())
    upstream_ok=s07.get("status")==EXPECTED_07_STATUS and s08.get("status")==EXPECTED_08_STATUS
    if inputs_ok:
        stab07=pd.read_csv(paths[1])
        stab08=pd.read_csv(paths[3])
        boundary_rows=pd.read_csv(paths[4])
        joined=stab07.merge(stab08[["profile_id","direction","feature_column","all_boundaries_valid","lower_values","upper_values"]], on=["profile_id","direction","feature_column"], how="left")
        joined["reject_reason"] = joined.apply(reject_reason, axis=1)
        joined["review_score"] = joined.apply(review_score, axis=1)
        shortlist=joined[joined["reject_reason"].eq("PASS")].copy().sort_values(["review_score","positive_test_fold_rate","test_lift_mean","test_avg_result_mean"], ascending=[False,False,False,False])
        rejected=joined[~joined["reject_reason"].eq("PASS")].copy().sort_values(["review_score"], ascending=False)
        preview_keys=shortlist[["profile_id","direction","feature_column"]].drop_duplicates().head(30)
        boundary_preview=boundary_rows.merge(preview_keys, on=["profile_id","direction","feature_column"], how="inner")
    else:
        stab07=pd.DataFrame(); stab08=pd.DataFrame(); boundary_rows=pd.DataFrame(); joined=pd.DataFrame(); shortlist=pd.DataFrame(); rejected=pd.DataFrame(); boundary_preview=pd.DataFrame()
    status="GOLD_V3_09_HUMAN_REVIEW_CANDIDATE_SHORTLIST_READY_AUDIT_ONLY" if inputs_ok and upstream_ok and not shortlist.empty else ("GOLD_V3_09_HUMAN_REVIEW_CANDIDATE_SHORTLIST_INPUT_REVIEW_REQUIRED_AUDIT_ONLY" if not (inputs_ok and upstream_ok) else "GOLD_V3_09_HUMAN_REVIEW_CANDIDATE_SHORTLIST_BLOCKED_AUDIT_ONLY")
    decision_df=pd.DataFrame([
        ["inputs_present",inputs_ok,True,"PASS" if inputs_ok else "FAIL"],
        ["upstream_07_08_ok",upstream_ok,True,"PASS" if upstream_ok else "FAIL"],
        ["candidate_stability_rows",len(joined),">0","PASS" if len(joined)>0 else "FAIL"],
        ["shortlist_rows",len(shortlist),">0","PASS" if len(shortlist)>0 else "FAIL"],
        ["boundary_preview_rows",len(boundary_preview),">0","PASS" if len(boundary_preview)>0 else "FAIL"],
        ["final_candidate_approval",False,False,"PASS"],
        ["threshold_finalization",False,False,"PASS"],
        ["model_training",False,False,"PASS"],
        ["signals_generated",False,False,"PASS"],
        ["zip_output_created",False,False,"PASS"],
        ["external_actions",False,False,"PASS"],
    ],columns=["decision_item","observed","required","status"])
    blocker_df=pd.DataFrame([
        ["G3-09-001","07/08 inputs","CLOSED" if inputs_ok and upstream_ok else "OPEN","HARD","07 stability and 08 boundary provenance required."],
        ["G3-09-002","human review shortlist","CLOSED" if len(shortlist)>0 else "OPEN","HARD","Shortlist rows required for human review."],
        ["G3-09-003","final approval","CLOSED_BLOCKED_BY_POLICY","HARD","This step is review shortlist only; no final candidate approval."],
        ["G3-09-004","signal/live","CLOSED_BLOCKED_BY_POLICY","HARD","No signals or live integration."],
        ["G3-09-005","zip output","CLOSED_DISABLED","INFO","ZIP output disabled."],
        ["G3-09-006","external actions","CLOSED","HARD","No external actions performed."],
    ],columns=["blocker_id","component","status","severity","detail"])
    summary={"created_utc":created,"step":STEP,"status":status,"audit_only":True,"source_recovery_approved":False,"candidate_stability_rows":int(len(joined)),"shortlist_rows":int(len(shortlist)),"rejected_rows":int(len(rejected)),"boundary_preview_rows":int(len(boundary_preview)),"top_shortlist_rows":shortlist.head(20).to_dict(orient="records") if not shortlist.empty else [],"final_candidate_approval":False,"threshold_finalization":False,"model_training":False,"signals_generated":False,"zip_output_created":False,"external_actions":ACTIONS}
    inv_df.to_csv(out/"gold_v3_09_input_inventory.csv",index=False,encoding="utf-8-sig")
    shortlist.to_csv(out/"gold_v3_09_human_review_candidate_shortlist.csv",index=False,encoding="utf-8-sig")
    rejected.to_csv(out/"gold_v3_09_rejected_candidate_diagnostics.csv",index=False,encoding="utf-8-sig")
    boundary_preview.to_csv(out/"gold_v3_09_boundary_preview_rows.csv",index=False,encoding="utf-8-sig")
    decision_df.to_csv(out/"gold_v3_09_decision_matrix.csv",index=False,encoding="utf-8-sig")
    blocker_df.to_csv(out/"gold_v3_09_blocker_matrix.csv",index=False,encoding="utf-8-sig")
    write_json(out/"gold_v3_09_summary.json",summary)
    report="\n".join(["# GOLD V3 09 human review candidate shortlist audit-only report","",f"Created UTC: {created}",f"Status: `{status}`","","## Shortlist top rows",md(shortlist.head(40)),"","## Decision matrix",md(decision_df),"","## Blockers",md(blocker_df),"","## Safety","- GOLD V3 only; no V2 artifacts used.","- Human review shortlist only; no final approval.","- No threshold finalization, no model training, no signals.","- No ZIP output.","- External actions remain OFF."])
    (out/"GOLD_V3_09_HUMAN_REVIEW_CANDIDATE_SHORTLIST_AUDIT_ONLY_REPORT.md").write_text(report,encoding="utf-8")
    print(json.dumps({"status":status,"output_dir":str(out),"zip_output_created":False},ensure_ascii=False,indent=2))
    print("No ZIP, final candidate approval, threshold finalization, model training, signals, Discord, MT5, AI API, live hook, live evaluator, or final signal action was performed.")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
