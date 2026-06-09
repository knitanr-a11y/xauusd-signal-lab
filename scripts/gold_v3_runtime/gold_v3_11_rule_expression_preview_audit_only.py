#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import hashlib, json, math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import numpy as np
import pandas as pd

STEP = "GOLD_V3_11_RULE_EXPRESSION_PREVIEW_AUDIT_ONLY"
OUT_NAME = "11_rule_expression_preview_audit_only"
EXPECTED_10_STATUS = "GOLD_V3_10_CANDIDATE_FAMILY_REVIEW_CARD_READY_AUDIT_ONLY"
ACTIONS = {"discord_send_allowed": False, "mt5_order_allowed": False, "ai_api_allowed": False, "live_hook_allowed": False, "live_evaluator_allowed": False, "final_signal_allowed": False}


def repo_root() -> Path: return Path(__file__).resolve().parents[2]

def files_root() -> Path:
    r = repo_root()
    return r.parents[1] if len(r.parents) >= 2 else r.parent

def v3_output_root() -> Path: return files_root() / "FX_OUTPUTS" / "gold_v3"

def out_dir() -> Path:
    p = v3_output_root() / OUT_NAME
    p.mkdir(parents=True, exist_ok=True)
    return p

def dir10() -> Path: return v3_output_root() / "10_candidate_family_review_card_audit_only"

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

def parse_num(x: Any) -> float | None:
    if x is None: return None
    s=str(x).strip().lower()
    if s in {"", "nan", "none"}: return None
    if s == "-inf": return -math.inf
    if s == "inf": return math.inf
    try: return float(s)
    except Exception: return None

def finite_values(series: pd.Series) -> list[float]:
    vals=[]
    for x in series.dropna().tolist():
        v=parse_num(x)
        if v is not None and math.isfinite(v): vals.append(v)
    return vals

def dominant_bucket(s: pd.Series) -> str:
    vc=s.dropna().astype(str).value_counts()
    return vc.index[0] if len(vc) else ""

def threshold_type_for_group(g: pd.DataFrame) -> str:
    lower_inf=sum(str(x).strip().lower()=="-inf" for x in g["bucket_lower"].tolist())
    upper_inf=sum(str(x).strip().lower()=="inf" for x in g["bucket_upper"].tolist())
    n=len(g)
    if n == 0: return "missing"
    if lower_inf == n and upper_inf == 0: return "upper_bound"
    if upper_inf == n and lower_inf == 0: return "lower_bound"
    if lower_inf == 0 and upper_inf == 0: return "range"
    return "mixed"

def expression(feature: str, typ: str, lower: float | None, upper: float | None) -> str:
    if typ == "lower_bound" and lower is not None and math.isfinite(lower): return f"{feature} >= {lower:.6g}"
    if typ == "upper_bound" and upper is not None and math.isfinite(upper): return f"{feature} <= {upper:.6g}"
    if typ == "range" and lower is not None and upper is not None and math.isfinite(lower) and math.isfinite(upper): return f"{lower:.6g} <= {feature} <= {upper:.6g}"
    return "MANUAL_REVIEW_REQUIRED"

def readiness(row: pd.Series) -> str:
    if "raw_price_level_stationarity_risk" in str(row.get("risk_flags", "")):
        return "REVIEW_ONLY_NOT_DEPLOYABLE_RAW_PRICE_LEVEL"
    if row.get("threshold_type") == "mixed" or row.get("rule_expression_preview") == "MANUAL_REVIEW_REQUIRED":
        return "MANUAL_REVIEW_BOUNDARY_UNSTABLE"
    if "has_negative_test_fold" in str(row.get("risk_flags", "")):
        return "REVIEW_READY_WITH_NEGATIVE_FOLD_RISK"
    return "REVIEW_READY"

def main() -> int:
    created=datetime.now(timezone.utc).isoformat()
    out=out_dir()
    paths=[dir10()/"gold_v3_10_summary.json", dir10()/"gold_v3_10_candidate_family_review_rows.csv", dir10()/"gold_v3_10_boundary_card_rows.csv"]
    inv_df=input_inventory(paths)
    s10=read_json(paths[0])
    inputs_ok=bool(inv_df["exists"].all())
    upstream_ok=s10.get("status")==EXPECTED_10_STATUS
    if inputs_ok:
        reviews=pd.read_csv(paths[1])
        boundaries=pd.read_csv(paths[2])
        rows=[]
        for _, r in reviews.iterrows():
            g=boundaries[(boundaries["profile_id"].eq(r["profile_id"])) & (boundaries["direction"].eq(r["direction"])) & (boundaries["feature_column"].eq(r["feature_column"]))]
            typ=threshold_type_for_group(g)
            lower_vals=finite_values(g["bucket_lower"]) if not g.empty else []
            upper_vals=finite_values(g["bucket_upper"]) if not g.empty else []
            lower_med=float(np.median(lower_vals)) if lower_vals else None
            upper_med=float(np.median(upper_vals)) if upper_vals else None
            dom_bucket=dominant_bucket(g["bucket_id"]) if not g.empty else ""
            preview=expression(str(r["feature_column"]), typ, lower_med, upper_med)
            d=r.to_dict()
            d.update({
                "boundary_rows": int(len(g)),
                "dominant_bucket_id": dom_bucket,
                "threshold_type": typ,
                "preview_lower_median": lower_med,
                "preview_upper_median": upper_med,
                "rule_expression_preview": preview,
            })
            rows.append(d)
        expr_df=pd.DataFrame(rows)
        expr_df["readiness_label"] = expr_df.apply(readiness, axis=1)
        expr_df=expr_df.sort_values(["readiness_label","review_score"], ascending=[True,False])
        fam_summary=expr_df.groupby(["feature_family","readiness_label"], dropna=False).agg(
            rows=("feature_column","count"),
            features=("feature_column", lambda x: len(set(x))),
            profiles=("profile_id", lambda x: len(set(x))),
            max_review_score=("review_score","max"),
            avg_test_lift_mean=("test_lift_mean","mean"),
            avg_test_result_mean=("test_avg_result_mean","mean"),
        ).reset_index().sort_values(["max_review_score","avg_test_lift_mean"], ascending=[False,False])
        diag=expr_df[["profile_id","direction","feature_column","feature_family","boundary_rows","dominant_bucket_id","threshold_type","preview_lower_median","preview_upper_median","rule_expression_preview","readiness_label","risk_flags","review_score"]].copy()
    else:
        reviews=pd.DataFrame(); boundaries=pd.DataFrame(); expr_df=pd.DataFrame(); fam_summary=pd.DataFrame(); diag=pd.DataFrame()
    rows_ok=inputs_ok and upstream_ok and not expr_df.empty
    status="GOLD_V3_11_RULE_EXPRESSION_PREVIEW_READY_AUDIT_ONLY" if rows_ok else ("GOLD_V3_11_RULE_EXPRESSION_PREVIEW_INPUT_REVIEW_REQUIRED_AUDIT_ONLY" if not (inputs_ok and upstream_ok) else "GOLD_V3_11_RULE_EXPRESSION_PREVIEW_BLOCKED_AUDIT_ONLY")
    decision_df=pd.DataFrame([
        ["inputs_present",inputs_ok,True,"PASS" if inputs_ok else "FAIL"],
        ["upstream_10_ok",upstream_ok,True,"PASS" if upstream_ok else "FAIL"],
        ["rule_expression_preview_rows",len(expr_df),">0","PASS" if len(expr_df)>0 else "FAIL"],
        ["family_readiness_summary_rows",len(fam_summary),">0","PASS" if len(fam_summary)>0 else "FAIL"],
        ["final_candidate_approval",False,False,"PASS"],
        ["threshold_finalization",False,False,"PASS"],
        ["model_training",False,False,"PASS"],
        ["signals_generated",False,False,"PASS"],
        ["zip_output_created",False,False,"PASS"],
        ["external_actions",False,False,"PASS"],
    ],columns=["decision_item","observed","required","status"])
    blocker_df=pd.DataFrame([
        ["G3-11-001","10 inputs","CLOSED" if inputs_ok and upstream_ok else "OPEN","HARD","10 review card outputs required."],
        ["G3-11-002","preview expressions","CLOSED" if len(expr_df)>0 else "OPEN","HARD","Rule expression preview rows required."],
        ["G3-11-003","final approval","CLOSED_BLOCKED_BY_POLICY","HARD","Preview only; no final candidate approval."],
        ["G3-11-004","threshold finalization","CLOSED_BLOCKED_BY_POLICY","HARD","Median thresholds are preview-only, not live final thresholds."],
        ["G3-11-005","signal/live","CLOSED_BLOCKED_BY_POLICY","HARD","No signals or live integration."],
        ["G3-11-006","zip output","CLOSED_DISABLED","INFO","ZIP output disabled."],
        ["G3-11-007","external actions","CLOSED","HARD","No external actions performed."],
    ],columns=["blocker_id","component","status","severity","detail"])
    summary={"created_utc":created,"step":STEP,"status":status,"audit_only":True,"source_recovery_approved":False,"rule_expression_preview_rows":int(len(expr_df)),"family_readiness_summary_rows":int(len(fam_summary)),"readiness_counts":expr_df["readiness_label"].value_counts().to_dict() if not expr_df.empty else {},"top_preview_rows":expr_df.head(20).to_dict(orient="records") if not expr_df.empty else [],"final_candidate_approval":False,"threshold_finalization":False,"model_training":False,"signals_generated":False,"zip_output_created":False,"external_actions":ACTIONS}
    inv_df.to_csv(out/"gold_v3_11_input_inventory.csv",index=False,encoding="utf-8-sig")
    expr_df.to_csv(out/"gold_v3_11_rule_expression_preview_rows.csv",index=False,encoding="utf-8-sig")
    fam_summary.to_csv(out/"gold_v3_11_feature_family_readiness_summary.csv",index=False,encoding="utf-8-sig")
    diag.to_csv(out/"gold_v3_11_boundary_consensus_diagnostics.csv",index=False,encoding="utf-8-sig")
    decision_df.to_csv(out/"gold_v3_11_decision_matrix.csv",index=False,encoding="utf-8-sig")
    blocker_df.to_csv(out/"gold_v3_11_blocker_matrix.csv",index=False,encoding="utf-8-sig")
    write_json(out/"gold_v3_11_summary.json",summary)
    report="\n".join(["# GOLD V3 11 rule expression preview audit-only report","",f"Created UTC: {created}",f"Status: `{status}`","","## Family readiness summary",md(fam_summary),"","## Top preview rows",md(expr_df.head(40)),"","## Decision matrix",md(decision_df),"","## Blockers",md(blocker_df),"","## Safety","- GOLD V3 only; no V2 artifacts used.","- Preview expressions only; no final candidate approval.","- Median thresholds are preview-only, not final live thresholds.","- No model training, no signals, no ZIP.","- External actions remain OFF."])
    (out/"GOLD_V3_11_RULE_EXPRESSION_PREVIEW_AUDIT_ONLY_REPORT.md").write_text(report,encoding="utf-8")
    print(json.dumps({"status":status,"output_dir":str(out),"zip_output_created":False},ensure_ascii=False,indent=2))
    print("No ZIP, final candidate approval, threshold finalization, model training, signals, Discord, MT5, AI API, live hook, live evaluator, or final signal action was performed.")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
