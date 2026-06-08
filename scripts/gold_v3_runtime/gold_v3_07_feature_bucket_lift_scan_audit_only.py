#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import hashlib, json, math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import numpy as np
import pandas as pd

STEP = "GOLD_V3_07_FEATURE_BUCKET_LIFT_SCAN_AUDIT_ONLY"
OUT_NAME = "07_feature_bucket_lift_scan_audit_only"
EXPECTED_05_STATUS = "GOLD_V3_05_LABEL_FEATURE_JOIN_WALKFORWARD_READY_AUDIT_ONLY"
EXPECTED_06_STATUS = "GOLD_V3_06_PROFILE_DIRECTION_BASELINE_READY_AUDIT_ONLY"
ACTIONS = {"discord_send_allowed": False, "mt5_order_allowed": False, "ai_api_allowed": False, "live_hook_allowed": False, "live_evaluator_allowed": False, "final_signal_allowed": False}
MIN_VALIDATION_ROWS = 50
MIN_TEST_ROWS = 50
MAX_FEATURES = 96


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


def dir05() -> Path:
    return v3_output_root() / "05_label_feature_join_walkforward_split_audit_only"


def dir06() -> Path:
    return v3_output_root() / "06_profile_direction_walkforward_baseline_audit_only"


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(1024*1024), b""):
            h.update(b)
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


def read_json(p: Path) -> dict[str, Any]:
    if not p.exists(): return {}
    try: return json.loads(p.read_text(encoding="utf-8"))
    except Exception: return {}


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


def metric(part: pd.DataFrame) -> dict[str, Any]:
    n=len(part)
    if n == 0:
        return {"rows":0,"tp_count":0,"sl_count":0,"timeout_count":0,"avg_result_usd":0.0,"sum_result_usd":0.0,"tp_rate":0.0}
    res=pd.to_numeric(part["label_price_distance_result_usd"], errors="coerce")
    tp=int((part["label_outcome"]=="TP").sum())
    sl=int((part["label_outcome"]=="SL").sum())
    timeout=int((part["label_outcome"]=="TIMEOUT").sum())
    return {"rows":n,"tp_count":tp,"sl_count":sl,"timeout_count":timeout,"avg_result_usd":float(res.mean()),"sum_result_usd":float(res.sum()),"tp_rate":tp/n}


def edges_from_train(s: pd.Series) -> list[float]:
    q=s.dropna().quantile([0,0.2,0.4,0.6,0.8,1.0]).astype(float).tolist()
    edges=[]
    for v in q:
        if math.isfinite(v) and (not edges or v > edges[-1]):
            edges.append(v)
    return edges


def assign_bucket(s: pd.Series, edges: list[float]) -> pd.Series:
    if len(edges) < 2:
        return pd.Series([pd.NA]*len(s), index=s.index)
    bins=edges.copy()
    bins[0] = -np.inf
    bins[-1] = np.inf
    labels=[f"B{i+1}" for i in range(len(bins)-1)]
    return pd.cut(s, bins=bins, labels=labels, include_lowest=True)


def scan(data: pd.DataFrame, folds: pd.DataFrame, features: list[str]) -> pd.DataFrame:
    rows=[]
    for _, f in folds.iterrows():
        fold_id=f["fold_id"]
        train_months=[m for m in str(f["train_months"]).split(";") if m]
        val_month=str(f["validation_month"])
        test_month=str(f["test_month"])
        train_all=data[data["entry_month"].isin(train_months)]
        val_all=data[data["entry_month"].eq(val_month)]
        test_all=data[data["entry_month"].eq(test_month)]
        for profile_id in data["profile_id"].dropna().unique():
            for direction in data["direction"].dropna().unique():
                tr=train_all[(train_all["profile_id"].eq(profile_id)) & (train_all["direction"].eq(direction))]
                va=val_all[(val_all["profile_id"].eq(profile_id)) & (val_all["direction"].eq(direction))]
                te=test_all[(test_all["profile_id"].eq(profile_id)) & (test_all["direction"].eq(direction))]
                if tr.empty or va.empty or te.empty:
                    continue
                base_val=metric(va)
                base_test=metric(te)
                for feat in features:
                    if feat not in tr.columns:
                        continue
                    edges=edges_from_train(pd.to_numeric(tr[feat], errors="coerce"))
                    if len(edges)<2:
                        continue
                    va_b=assign_bucket(pd.to_numeric(va[feat], errors="coerce"), edges)
                    te_b=assign_bucket(pd.to_numeric(te[feat], errors="coerce"), edges)
                    best=None
                    for b in sorted([x for x in va_b.dropna().unique()]):
                        vm=metric(va[va_b.eq(b)])
                        if vm["rows"] < MIN_VALIDATION_ROWS:
                            continue
                        if best is None or vm["avg_result_usd"] > best["validation_avg_result_usd"]:
                            best={"bucket_id":str(b),"validation_rows":vm["rows"],"validation_avg_result_usd":vm["avg_result_usd"],"validation_sum_result_usd":vm["sum_result_usd"],"validation_tp_rate":vm["tp_rate"]}
                    if best is None:
                        continue
                    tm=metric(te[te_b.eq(best["bucket_id"])])
                    if tm["rows"] < MIN_TEST_ROWS:
                        continue
                    rows.append({
                        "fold_id":fold_id,
                        "profile_id":profile_id,
                        "direction":direction,
                        "feature_column":feat,
                        "bucket_id":best["bucket_id"],
                        "train_months":";".join(train_months),
                        "validation_month":val_month,
                        "test_month":test_month,
                        "validation_rows":best["validation_rows"],
                        "validation_avg_result_usd":best["validation_avg_result_usd"],
                        "validation_sum_result_usd":best["validation_sum_result_usd"],
                        "validation_tp_rate":best["validation_tp_rate"],
                        "test_rows":tm["rows"],
                        "test_avg_result_usd":tm["avg_result_usd"],
                        "test_sum_result_usd":tm["sum_result_usd"],
                        "test_tp_rate":tm["tp_rate"],
                        "test_positive_avg_result":tm["avg_result_usd"]>0,
                        "test_baseline_rows":base_test["rows"],
                        "test_baseline_avg_result_usd":base_test["avg_result_usd"],
                        "test_lift_vs_baseline_avg_usd":tm["avg_result_usd"]-base_test["avg_result_usd"],
                    })
    return pd.DataFrame(rows)


def stability(scan_df: pd.DataFrame) -> pd.DataFrame:
    rows=[]
    if scan_df.empty:
        return pd.DataFrame()
    for keys,x in scan_df.groupby(["profile_id","direction","feature_column"], dropna=False):
        profile,direction,feat=keys
        n=len(x)
        pos=int(x["test_positive_avg_result"].sum())
        rows.append({
            "profile_id":profile,
            "direction":direction,
            "feature_column":feat,
            "folds":n,
            "positive_test_folds":pos,
            "positive_test_fold_rate":pos/n if n else 0.0,
            "test_avg_result_mean":float(x["test_avg_result_usd"].mean()) if n else 0.0,
            "test_avg_result_min":float(x["test_avg_result_usd"].min()) if n else 0.0,
            "test_avg_result_max":float(x["test_avg_result_usd"].max()) if n else 0.0,
            "test_lift_mean":float(x["test_lift_vs_baseline_avg_usd"].mean()) if n else 0.0,
            "test_sum_result_total":float(x["test_sum_result_usd"].sum()) if n else 0.0,
            "test_rows_total":int(x["test_rows"].sum()) if n else 0,
        })
    return pd.DataFrame(rows).sort_values(["positive_test_fold_rate","test_lift_mean","test_avg_result_mean","test_sum_result_total"], ascending=[False,False,False,False])


def main() -> int:
    created=datetime.now(timezone.utc).isoformat()
    out=out_dir()
    paths=[dir05()/"gold_v3_05_summary.json", dir05()/"gold_v3_05_label_feature_join_rows.csv", dir05()/"gold_v3_05_feature_column_inventory.csv", dir05()/"gold_v3_05_walkforward_fold_matrix.csv", dir06()/"gold_v3_06_summary.json"]
    inv_df=input_inventory(paths)
    s05=read_json(paths[0]); s06=read_json(paths[4])
    inputs_ok=bool(inv_df["exists"].all())
    upstream_ok=(s05.get("status")=="GOLD_V3_05_LABEL_FEATURE_JOIN_WALKFORWARD_READY_AUDIT_ONLY" and s06.get("status")=="GOLD_V3_06_PROFILE_DIRECTION_BASELINE_READY_AUDIT_ONLY")
    if inputs_ok:
        feat_inv=pd.read_csv(paths[2])
        raw_feats=[c for c in feat_inv["feature_column"].dropna().tolist() if not bool(feat_inv.loc[feat_inv["feature_column"].eq(c),"forbidden_token_hit"].iloc[0])]
        use_feats=raw_feats[:MAX_FEATURES]
        usecols=["entry_month","profile_id","direction","label_outcome","label_price_distance_result_usd"]+use_feats
        data=pd.read_csv(paths[1], usecols=usecols)
        folds=pd.read_csv(paths[3])
        for f in use_feats:
            data[f]=pd.to_numeric(data[f], errors="coerce")
        scan_df=scan(data, folds, use_feats)
        stab_df=stability(scan_df)
        top_df=stab_df.head(200).copy()
    else:
        feat_inv=pd.DataFrame(); data=pd.DataFrame(); folds=pd.DataFrame(); use_feats=[]; scan_df=pd.DataFrame(); stab_df=pd.DataFrame(); top_df=pd.DataFrame()
    if not (inputs_ok and upstream_ok):
        status="GOLD_V3_07_FEATURE_BUCKET_SCAN_INPUT_REVIEW_REQUIRED_AUDIT_ONLY"
    elif scan_df.empty or stab_df.empty:
        status="GOLD_V3_07_FEATURE_BUCKET_SCAN_BLOCKED_AUDIT_ONLY"
    else:
        status="GOLD_V3_07_FEATURE_BUCKET_SCAN_READY_AUDIT_ONLY"
    decision_df=pd.DataFrame([
        ["inputs_present",inputs_ok,True,"PASS" if inputs_ok else "FAIL"],
        ["upstream_05_06_ok",upstream_ok,True,"PASS" if upstream_ok else "FAIL"],
        ["features_scanned",len(use_feats),">0","PASS" if len(use_feats)>0 else "FAIL"],
        ["fold_feature_bucket_scan_rows",len(scan_df),">0","PASS" if len(scan_df)>0 else "FAIL"],
        ["stability_summary_rows",len(stab_df),">0","PASS" if len(stab_df)>0 else "FAIL"],
        ["test_used_for_bucket_selection",False,False,"PASS"],
        ["final_candidate_approval",False,False,"PASS"],
        ["model_training",False,False,"PASS"],
        ["signals_generated",False,False,"PASS"],
        ["zip_output_created",False,False,"PASS"],
        ["external_actions",False,False,"PASS"],
    ],columns=["decision_item","observed","required","status"])
    blocker_df=pd.DataFrame([
        ["G3-07-001","05/06 inputs","CLOSED" if inputs_ok and upstream_ok else "OPEN","HARD","05 joined rows/folds and 06 baseline required."],
        ["G3-07-002","feature bucket scan","CLOSED" if len(scan_df)>0 else "OPEN","HARD","Fold feature bucket scan rows must be created."],
        ["G3-07-003","test leakage","CLOSED","HARD","Train creates bucket edges; validation selects bucket; test only reports."],
        ["G3-07-004","candidate/model/signal","CLOSED_BLOCKED_BY_POLICY","HARD","No final candidate approval, model training, or signals in this step."],
        ["G3-07-005","zip output","CLOSED_DISABLED","INFO","ZIP output disabled."],
        ["G3-07-006","external actions","CLOSED","HARD","No external actions performed."],
    ],columns=["blocker_id","component","status","severity","detail"])
    summary={"created_utc":created,"step":STEP,"status":status,"audit_only":True,"source_recovery_approved":False,"features_scanned":len(use_feats),"fold_feature_bucket_scan_rows":int(len(scan_df)),"stability_summary_rows":int(len(stab_df)),"top_rows":top_df.head(20).to_dict(orient="records") if not top_df.empty else [],"test_used_for_bucket_selection":False,"final_candidate_approval":False,"model_training":False,"signals_generated":False,"zip_output_created":False,"external_actions":ACTIONS}
    inv_df.to_csv(out/"gold_v3_07_input_inventory.csv",index=False,encoding="utf-8-sig")
    pd.DataFrame({"feature_column":use_feats}).to_csv(out/"gold_v3_07_feature_scan_inventory.csv",index=False,encoding="utf-8-sig")
    scan_df.to_csv(out/"gold_v3_07_fold_feature_bucket_scan.csv",index=False,encoding="utf-8-sig")
    stab_df.to_csv(out/"gold_v3_07_feature_bucket_test_stability_summary.csv",index=False,encoding="utf-8-sig")
    top_df.to_csv(out/"gold_v3_07_top_feature_bucket_candidates.csv",index=False,encoding="utf-8-sig")
    decision_df.to_csv(out/"gold_v3_07_decision_matrix.csv",index=False,encoding="utf-8-sig")
    blocker_df.to_csv(out/"gold_v3_07_blocker_matrix.csv",index=False,encoding="utf-8-sig")
    write_json(out/"gold_v3_07_summary.json",summary)
    report="\n".join(["# GOLD V3 07 feature bucket lift scan audit-only report","",f"Created UTC: {created}",f"Status: `{status}`","","## Top stability rows",md(top_df.head(30)),"","## Decision matrix",md(decision_df),"","## Blockers",md(blocker_df),"","## Safety","- GOLD V3 only; no V2 artifacts used.","- Train defines buckets; validation selects; test reports only.","- No final candidate approval, no model training, no signals.","- No ZIP output.","- External actions remain OFF."])
    (out/"GOLD_V3_07_FEATURE_BUCKET_LIFT_SCAN_AUDIT_ONLY_REPORT.md").write_text(report,encoding="utf-8")
    print(json.dumps({"status":status,"output_dir":str(out),"zip_output_created":False},ensure_ascii=False,indent=2))
    print("No ZIP, final candidate approval, model training, signals, Discord, MT5, AI API, live hook, live evaluator, or final signal action was performed.")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
