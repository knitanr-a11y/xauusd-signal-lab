#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import hashlib, json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import pandas as pd

STEP = "GOLD_V3_10_CANDIDATE_FAMILY_REVIEW_CARD_AUDIT_ONLY"
OUT_NAME = "10_candidate_family_review_card_audit_only"
EXPECTED_09_STATUS = "GOLD_V3_09_HUMAN_REVIEW_CANDIDATE_SHORTLIST_READY_AUDIT_ONLY"
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

def dir09() -> Path: return v3_output_root() / "09_human_review_candidate_shortlist_audit_only"

def dir08() -> Path: return v3_output_root() / "08_bucket_boundary_provenance_audit_only"

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

def feature_family(feature: str) -> str:
    f = str(feature).lower()
    if "dist_ema" in f: return "ema_distance"
    if "ema" in f and "dist" not in f: return "raw_ema_price_level"
    if "atr" in f: return "volatility_atr"
    if "range" in f or f.endswith("_tr") or "_tr" in f: return "volatility_range_tr"
    if "body" in f or "wick" in f: return "candle_body_wick"
    if "ret" in f: return "momentum_return"
    if "rsi" in f or "stoch" in f or "macd" in f: return "oscillator"
    return "other"

def risk_flags(row: pd.Series) -> str:
    flags=[]
    fam=row.get("feature_family", "")
    if fam == "raw_ema_price_level": flags.append("raw_price_level_stationarity_risk")
    if fam in {"volatility_atr", "volatility_range_tr"}: flags.append("absolute_volatility_regime_risk")
    if not bool(row.get("boundary_strict_valid", False)): flags.append("boundary_missing_risk")
    if float(row.get("test_avg_result_min", 0)) < 0: flags.append("has_negative_test_fold")
    return ";".join(flags) if flags else "none"

def review_action(row: pd.Series) -> str:
    flags=str(row.get("risk_flags", ""))
    if "boundary_missing_risk" in flags: return "REJECT_BOUNDARY_MISSING"
    if "raw_price_level_stationarity_risk" in flags: return "REVIEW_ONLY_STATIONARITY_RISK"
    if float(row.get("positive_test_fold_rate",0)) >= 1.0 and float(row.get("test_lift_mean",0)) > 0:
        return "HIGH_PRIORITY_REVIEW"
    return "STANDARD_REVIEW"

def main() -> int:
    created=datetime.now(timezone.utc).isoformat()
    out=out_dir()
    paths=[dir09()/"gold_v3_09_summary.json", dir09()/"gold_v3_09_human_review_candidate_shortlist.csv", dir08()/"gold_v3_08_selected_bucket_boundary_rows.csv"]
    inv_df=input_inventory(paths)
    s09=read_json(paths[0])
    inputs_ok=bool(inv_df["exists"].all())
    upstream_ok=s09.get("status")==EXPECTED_09_STATUS and bool(s09.get("shortlist_boundary_strict_valid"))
    if inputs_ok:
        shortlist=pd.read_csv(paths[1])
        boundary_rows=pd.read_csv(paths[2])
        rows=shortlist.copy()
        rows["feature_family"] = rows["feature_column"].map(feature_family)
        rows["risk_flags"] = rows.apply(risk_flags, axis=1)
        rows["review_action"] = rows.apply(review_action, axis=1)
        rows = rows.sort_values(["review_action","review_score"], ascending=[True,False])
        fam_summary=rows.groupby(["feature_family","review_action"], dropna=False).agg(
            candidates=("feature_column","count"),
            profiles=("profile_id", lambda x: len(set(x))),
            features=("feature_column", lambda x: len(set(x))),
            max_review_score=("review_score","max"),
            avg_test_lift_mean=("test_lift_mean","mean"),
            avg_test_result_mean=("test_avg_result_mean","mean"),
            total_test_rows=("test_rows_total","sum"),
        ).reset_index().sort_values(["max_review_score","avg_test_lift_mean"], ascending=[False,False])
        rep=rows.sort_values(["feature_family","review_score"], ascending=[True,False]).groupby("feature_family", dropna=False).head(5).copy()
        keys=rep[["profile_id","direction","feature_column"]].drop_duplicates()
        boundary_card=boundary_rows.merge(keys, on=["profile_id","direction","feature_column"], how="inner")
    else:
        shortlist=pd.DataFrame(); boundary_rows=pd.DataFrame(); rows=pd.DataFrame(); fam_summary=pd.DataFrame(); rep=pd.DataFrame(); boundary_card=pd.DataFrame()
    review_rows_ok = inputs_ok and upstream_ok and not rows.empty and bool(rows["boundary_strict_valid"].all())
    status="GOLD_V3_10_CANDIDATE_FAMILY_REVIEW_CARD_READY_AUDIT_ONLY" if review_rows_ok else ("GOLD_V3_10_CANDIDATE_FAMILY_REVIEW_CARD_INPUT_REVIEW_REQUIRED_AUDIT_ONLY" if not (inputs_ok and upstream_ok) else "GOLD_V3_10_CANDIDATE_FAMILY_REVIEW_CARD_BLOCKED_AUDIT_ONLY")
    decision_df=pd.DataFrame([
        ["inputs_present",inputs_ok,True,"PASS" if inputs_ok else "FAIL"],
        ["upstream_09_ok",upstream_ok,True,"PASS" if upstream_ok else "FAIL"],
        ["candidate_review_rows",len(rows),">0","PASS" if len(rows)>0 else "FAIL"],
        ["all_review_rows_boundary_strict_valid", bool(rows["boundary_strict_valid"].all()) if not rows.empty else False, True, "PASS" if (not rows.empty and bool(rows["boundary_strict_valid"].all())) else "FAIL"],
        ["family_summary_rows",len(fam_summary),">0","PASS" if len(fam_summary)>0 else "FAIL"],
        ["representative_review_rows",len(rep),">0","PASS" if len(rep)>0 else "FAIL"],
        ["final_candidate_approval",False,False,"PASS"],
        ["threshold_finalization",False,False,"PASS"],
        ["model_training",False,False,"PASS"],
        ["signals_generated",False,False,"PASS"],
        ["zip_output_created",False,False,"PASS"],
        ["external_actions",False,False,"PASS"],
    ],columns=["decision_item","observed","required","status"])
    blocker_df=pd.DataFrame([
        ["G3-10-001","09 inputs","CLOSED" if inputs_ok and upstream_ok else "OPEN","HARD","09 strict-boundary shortlist required."],
        ["G3-10-002","review cards","CLOSED" if review_rows_ok else "OPEN","HARD","Review rows require strict boundaries."],
        ["G3-10-003","final approval","CLOSED_BLOCKED_BY_POLICY","HARD","Review cards only; no final candidate approval."],
        ["G3-10-004","signal/live","CLOSED_BLOCKED_BY_POLICY","HARD","No signals or live integration."],
        ["G3-10-005","zip output","CLOSED_DISABLED","INFO","ZIP output disabled."],
        ["G3-10-006","external actions","CLOSED","HARD","No external actions performed."],
    ],columns=["blocker_id","component","status","severity","detail"])
    summary={"created_utc":created,"step":STEP,"status":status,"audit_only":True,"source_recovery_approved":False,"candidate_review_rows":int(len(rows)),"feature_family_summary_rows":int(len(fam_summary)),"representative_review_rows":int(len(rep)),"boundary_card_rows":int(len(boundary_card)),"review_action_counts":rows["review_action"].value_counts().to_dict() if not rows.empty else {},"top_representative_rows":rep.head(20).to_dict(orient="records") if not rep.empty else [],"final_candidate_approval":False,"threshold_finalization":False,"model_training":False,"signals_generated":False,"zip_output_created":False,"external_actions":ACTIONS}
    inv_df.to_csv(out/"gold_v3_10_input_inventory.csv",index=False,encoding="utf-8-sig")
    rows.to_csv(out/"gold_v3_10_candidate_family_review_rows.csv",index=False,encoding="utf-8-sig")
    fam_summary.to_csv(out/"gold_v3_10_feature_family_summary.csv",index=False,encoding="utf-8-sig")
    rep.to_csv(out/"gold_v3_10_representative_review_rows.csv",index=False,encoding="utf-8-sig")
    boundary_card.to_csv(out/"gold_v3_10_boundary_card_rows.csv",index=False,encoding="utf-8-sig")
    decision_df.to_csv(out/"gold_v3_10_decision_matrix.csv",index=False,encoding="utf-8-sig")
    blocker_df.to_csv(out/"gold_v3_10_blocker_matrix.csv",index=False,encoding="utf-8-sig")
    write_json(out/"gold_v3_10_summary.json",summary)
    report="\n".join(["# GOLD V3 10 candidate family review card audit-only report","",f"Created UTC: {created}",f"Status: `{status}`","","## Feature family summary",md(fam_summary),"","## Representative review rows",md(rep.head(40)),"","## Decision matrix",md(decision_df),"","## Blockers",md(blocker_df),"","## Safety","- GOLD V3 only; no V2 artifacts used.","- Review cards only; no final candidate approval.","- Raw price-level EMA candidates are marked with stationarity risk.","- No threshold finalization, no model training, no signals.","- No ZIP output.","- External actions remain OFF."])
    (out/"GOLD_V3_10_CANDIDATE_FAMILY_REVIEW_CARD_AUDIT_ONLY_REPORT.md").write_text(report,encoding="utf-8")
    print(json.dumps({"status":status,"output_dir":str(out),"zip_output_created":False},ensure_ascii=False,indent=2))
    print("No ZIP, final candidate approval, threshold finalization, model training, signals, Discord, MT5, AI API, live hook, live evaluator, or final signal action was performed.")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
