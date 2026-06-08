#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import hashlib, json, math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import numpy as np
import pandas as pd

STEP = "GOLD_V3_08_BUCKET_BOUNDARY_PROVENANCE_AUDIT_ONLY"
OUT_NAME = "08_bucket_boundary_provenance_audit_only"
EXPECTED_05_STATUS = "GOLD_V3_05_LABEL_FEATURE_JOIN_WALKFORWARD_READY_AUDIT_ONLY"
EXPECTED_07_STATUS = "GOLD_V3_07_FEATURE_BUCKET_SCAN_READY_AUDIT_ONLY"
ACTIONS = {"discord_send_allowed": False, "mt5_order_allowed": False, "ai_api_allowed": False, "live_hook_allowed": False, "live_evaluator_allowed": False, "final_signal_allowed": False}


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


def dir07() -> Path:
    return v3_output_root() / "07_feature_bucket_lift_scan_audit_only"


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


def md(df: pd.DataFrame, n: int = 80) -> str:
    if df.empty: return "_No rows._"
    d = df.head(n).fillna("")
    lines = ["| " + " | ".join(map(str, d.columns)) + " |", "| " + " | ".join(["---"] * len(d.columns)) + " |"]
    for _, r in d.iterrows():
        lines.append("| " + " | ".join(str(r[c]).replace("|", "\\|").replace("\n", " ")[:500] for c in d.columns) + " |")
    return "\n".join(lines)


def input_inventory(paths: list[Path]) -> pd.DataFrame:
    rows=[]
    for p in paths:
        rows.append({"path":str(p),"filename":p.name,"exists":p.exists(),"bytes":p.stat().st_size if p.exists() else 0,"sha256":sha256_file(p) if p.exists() else ""})
    return pd.DataFrame(rows)


def edges_from_train(s: pd.Series) -> list[float]:
    q = pd.to_numeric(s, errors="coerce").dropna().quantile([0, .2, .4, .6, .8, 1.0]).astype(float).tolist()
    edges=[]
    for v in q:
        if math.isfinite(v) and (not edges or v > edges[-1]):
            edges.append(v)
    return edges


def bucket_bounds(edges: list[float], bucket_id: str) -> tuple[str, str, bool]:
    if len(edges) < 2 or not str(bucket_id).startswith("B"):
        return "", "", False
    idx = int(str(bucket_id)[1:]) - 1
    if idx < 0 or idx >= len(edges)-1:
        return "", "", False
    lower = "-inf" if idx == 0 else f"{edges[idx]:.12g}"
    upper = "inf" if idx == len(edges)-2 else f"{edges[idx+1]:.12g}"
    return lower, upper, True


def join_unique_boundary_values(values: pd.Series) -> str:
    """Return stable printable boundary values without mixing str/float comparisons."""
    cleaned = []
    for v in values.dropna().tolist():
        if isinstance(v, float):
            cleaned.append(f"{v:.12g}")
        else:
            cleaned.append(str(v))
    return ";".join(sorted(set(cleaned), key=lambda x: (x not in {"-inf", "inf"}, x)))[:1000]


def main() -> int:
    created = datetime.now(timezone.utc).isoformat()
    out = out_dir()
    paths = [
        dir05()/"gold_v3_05_summary.json",
        dir05()/"gold_v3_05_label_feature_join_rows.csv",
        dir05()/"gold_v3_05_walkforward_fold_matrix.csv",
        dir07()/"gold_v3_07_summary.json",
        dir07()/"gold_v3_07_top_feature_bucket_candidates.csv",
        dir07()/"gold_v3_07_fold_feature_bucket_scan.csv",
    ]
    inv_df = input_inventory(paths)
    s05 = read_json(paths[0]); s07 = read_json(paths[3])
    inputs_ok = bool(inv_df["exists"].all())
    upstream_ok = s05.get("status") == EXPECTED_05_STATUS and s07.get("status") == EXPECTED_07_STATUS
    if inputs_ok:
        top = pd.read_csv(paths[4])
        scan = pd.read_csv(paths[5])
        folds = pd.read_csv(paths[2])
        selected = scan.merge(top[["profile_id","direction","feature_column"]].drop_duplicates(), on=["profile_id","direction","feature_column"], how="inner")
        needed_feats = sorted(selected["feature_column"].dropna().unique().tolist())
        usecols = ["entry_month","profile_id","direction"] + needed_feats
        data = pd.read_csv(paths[1], usecols=usecols)
        for c in needed_feats:
            data[c] = pd.to_numeric(data[c], errors="coerce")
        fold_map = {r["fold_id"]: [m for m in str(r["train_months"]).split(";") if m] for _, r in folds.iterrows()}
        rows=[]
        for _, r in selected.iterrows():
            train_months = fold_map.get(r["fold_id"], [])
            feat = r["feature_column"]
            train = data[data["entry_month"].isin(train_months) & data["profile_id"].eq(r["profile_id"]) & data["direction"].eq(r["direction"])]
            edges = edges_from_train(train[feat]) if feat in train.columns else []
            lower, upper, ok = bucket_bounds(edges, r["bucket_id"])
            rows.append({
                "fold_id": r["fold_id"], "profile_id": r["profile_id"], "direction": r["direction"], "feature_column": feat,
                "bucket_id": r["bucket_id"], "train_months": ";".join(train_months), "train_rows": len(train),
                "edge_count": len(edges), "edges_json": json.dumps(edges, ensure_ascii=False), "bucket_lower": lower, "bucket_upper": upper,
                "boundary_valid": ok, "validation_month": r.get("validation_month", ""), "test_month": r.get("test_month", ""),
                "test_avg_result_usd": r.get("test_avg_result_usd", None), "test_lift_vs_baseline_avg_usd": r.get("test_lift_vs_baseline_avg_usd", None),
            })
        boundary_df = pd.DataFrame(rows)
        if not boundary_df.empty:
            stab = boundary_df.groupby(["profile_id","direction","feature_column"], dropna=False).agg(
                folds=("fold_id","nunique"), valid_boundaries=("boundary_valid","sum"), train_rows_min=("train_rows","min"),
                lower_values=("bucket_lower", join_unique_boundary_values),
                upper_values=("bucket_upper", join_unique_boundary_values),
                test_avg_result_mean=("test_avg_result_usd","mean"), test_lift_mean=("test_lift_vs_baseline_avg_usd","mean"),
            ).reset_index()
            stab["all_boundaries_valid"] = stab["folds"].eq(stab["valid_boundaries"])
            stab = stab.sort_values(["all_boundaries_valid","test_lift_mean","test_avg_result_mean"], ascending=[False,False,False])
        else:
            stab = pd.DataFrame()
    else:
        top=pd.DataFrame(); selected=pd.DataFrame(); boundary_df=pd.DataFrame(); stab=pd.DataFrame(); needed_feats=[]
    status = "GOLD_V3_08_BUCKET_BOUNDARY_PROVENANCE_READY_AUDIT_ONLY" if inputs_ok and upstream_ok and not boundary_df.empty and bool(boundary_df["boundary_valid"].all()) else ("GOLD_V3_08_BUCKET_BOUNDARY_PROVENANCE_INPUT_REVIEW_REQUIRED_AUDIT_ONLY" if not (inputs_ok and upstream_ok) else "GOLD_V3_08_BUCKET_BOUNDARY_PROVENANCE_BLOCKED_AUDIT_ONLY")
    decision_df = pd.DataFrame([
        ["inputs_present", inputs_ok, True, "PASS" if inputs_ok else "FAIL"],
        ["upstream_05_07_ok", upstream_ok, True, "PASS" if upstream_ok else "FAIL"],
        ["selected_scan_rows", len(boundary_df), ">0", "PASS" if len(boundary_df)>0 else "FAIL"],
        ["features_recomputed", len(needed_feats), ">0", "PASS" if len(needed_feats)>0 else "FAIL"],
        ["all_boundaries_valid", bool(boundary_df["boundary_valid"].all()) if not boundary_df.empty else False, True, "PASS" if (not boundary_df.empty and bool(boundary_df["boundary_valid"].all())) else "FAIL"],
        ["test_used_to_define_boundary", False, False, "PASS"],
        ["final_candidate_approval", False, False, "PASS"],
        ["signals_generated", False, False, "PASS"],
        ["zip_output_created", False, False, "PASS"],
        ["external_actions", False, False, "PASS"],
    ], columns=["decision_item","observed","required","status"])
    blocker_df = pd.DataFrame([
        ["G3-08-001","05/07 inputs","CLOSED" if inputs_ok and upstream_ok else "OPEN","HARD","05 joined rows/folds and 07 scan outputs required."],
        ["G3-08-002","bucket boundary provenance","CLOSED" if not boundary_df.empty and bool(boundary_df["boundary_valid"].all()) else "OPEN","HARD","Selected buckets must have persisted train-derived boundaries."],
        ["G3-08-003","candidate/signal","CLOSED_BLOCKED_BY_POLICY","HARD","No final candidate approval or signals in this step."],
        ["G3-08-004","zip output","CLOSED_DISABLED","INFO","ZIP output disabled."],
        ["G3-08-005","external actions","CLOSED","HARD","No external actions performed."],
    ], columns=["blocker_id","component","status","severity","detail"])
    summary={"created_utc":created,"step":STEP,"status":status,"audit_only":True,"source_recovery_approved":False,"selected_boundary_rows":int(len(boundary_df)),"features_recomputed":len(needed_feats),"all_boundaries_valid":bool(boundary_df["boundary_valid"].all()) if not boundary_df.empty else False,"final_candidate_approval":False,"signals_generated":False,"zip_output_created":False,"external_actions":ACTIONS}
    inv_df.to_csv(out/"gold_v3_08_input_inventory.csv", index=False, encoding="utf-8-sig")
    boundary_df.to_csv(out/"gold_v3_08_selected_bucket_boundary_rows.csv", index=False, encoding="utf-8-sig")
    stab.to_csv(out/"gold_v3_08_boundary_stability_summary.csv", index=False, encoding="utf-8-sig")
    decision_df.to_csv(out/"gold_v3_08_decision_matrix.csv", index=False, encoding="utf-8-sig")
    blocker_df.to_csv(out/"gold_v3_08_blocker_matrix.csv", index=False, encoding="utf-8-sig")
    write_json(out/"gold_v3_08_summary.json", summary)
    report="\n".join(["# GOLD V3 08 bucket boundary provenance audit-only report","",f"Created UTC: {created}",f"Status: `{status}`","","## Boundary stability",md(stab.head(40)),"","## Decision matrix",md(decision_df),"","## Blockers",md(blocker_df),"","## Safety","- GOLD V3 only; no V2 artifacts used.","- Boundaries recomputed from train months only.","- No final candidate approval, no signals, no ZIP.","- External actions remain OFF."])
    (out/"GOLD_V3_08_BUCKET_BOUNDARY_PROVENANCE_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")
    print(json.dumps({"status": status, "output_dir": str(out), "zip_output_created": False}, ensure_ascii=False, indent=2))
    print("No ZIP, final candidate approval, signals, Discord, MT5, AI API, live hook, live evaluator, or final signal action was performed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
