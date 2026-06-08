#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import hashlib, json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import pandas as pd

STEP = "GOLD_V3_05_LABEL_FEATURE_JOIN_WALKFORWARD_SPLIT_AUDIT_ONLY"
OUT_NAME = "05_label_feature_join_walkforward_split_audit_only"
EXPECTED_03_STATUS = "GOLD_V3_03_LABEL_OUTCOME_EVALUATION_READY_AUDIT_ONLY"
EXPECTED_04_STATUS = "GOLD_V3_04_ENTRYTIME_FEATURE_MATRIX_READY_AUDIT_ONLY"
FORBIDDEN_FEATURE_TOKENS = ["outcome", "profit", "result", "touch", "tp", "sl", "timeout", "future", "label", "horizon"]
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


def dir03() -> Path:
    return v3_output_root() / "03_label_outcome_evaluation_audit_only"


def dir04() -> Path:
    return v3_output_root() / "04_entrytime_feature_matrix_audit_only"


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


def md(df: pd.DataFrame, n: int=80) -> str:
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


def month_str(s: pd.Series) -> pd.Series:
    return pd.to_datetime(s, utc=True, errors="coerce").dt.strftime("%Y-%m")


def build_folds(months: list[str], joined: pd.DataFrame) -> pd.DataFrame:
    rows=[]
    months=sorted(months)
    for i in range(2, len(months)):
        test_m=months[i]
        val_m=months[i-1]
        train_months=months[:i-1]
        train_mask=joined["entry_month"].isin(train_months)
        val_mask=joined["entry_month"].eq(val_m)
        test_mask=joined["entry_month"].eq(test_m)
        rows.append({
            "fold_id": f"WF_{test_m}",
            "train_start_month": train_months[0] if train_months else "",
            "train_end_month": train_months[-1] if train_months else "",
            "validation_month": val_m,
            "test_month": test_m,
            "train_rows": int(train_mask.sum()),
            "validation_rows": int(val_mask.sum()),
            "test_rows": int(test_mask.sum()),
            "train_months": ";".join(train_months),
        })
    return pd.DataFrame(rows)


def main() -> int:
    created=datetime.now(timezone.utc).isoformat()
    out=out_dir()
    paths=[dir03()/"gold_v3_03_summary.json", dir03()/"gold_v3_03_evaluated_label_rows.csv", dir04()/"gold_v3_04_summary.json", dir04()/"gold_v3_04_entry_feature_rows.csv"]
    inv_df=input_inventory(paths)
    s03=read_json(paths[0]); s04=read_json(paths[2])
    inputs_ok=bool(inv_df["exists"].all())
    upstream_ok=(s03.get("status")==EXPECTED_03_STATUS and s04.get("status")==EXPECTED_04_STATUS)
    if inputs_ok:
        labels=pd.read_csv(paths[1])
        feats=pd.read_csv(paths[3])
        before=len(labels)
        joined=labels.merge(feats, on=["feature_bar_open_utc","entry_time_utc"], how="left", validate="many_to_one", suffixes=("","_feature"))
        joined["entry_month"]=month_str(joined["entry_time_utc"])
    else:
        labels=pd.DataFrame(); feats=pd.DataFrame(); joined=pd.DataFrame(); before=0
    join_missing=0 if joined.empty else int(joined[[c for c in feats.columns if c not in ["feature_bar_open_utc","entry_time_utc"]][0]].isna().sum()) if len(feats.columns)>2 else 0
    label_cols=set(labels.columns)
    feature_cols=[c for c in feats.columns if c not in ["feature_bar_open_utc","entry_time_utc"]]
    forbidden=[c for c in feature_cols if any(tok in c.lower() for tok in FORBIDDEN_FEATURE_TOKENS)]
    col_inv=pd.DataFrame([{"feature_column":c,"forbidden_token_hit":any(tok in c.lower() for tok in FORBIDDEN_FEATURE_TOKENS)} for c in feature_cols])
    month_counts=joined.groupby("entry_month").size().reset_index(name="rows") if not joined.empty else pd.DataFrame(columns=["entry_month","rows"])
    months=[m for m in month_counts["entry_month"].dropna().tolist()]
    fold_df=build_folds(months, joined) if months else pd.DataFrame()
    if not (inputs_ok and upstream_ok): status="GOLD_V3_05_LABEL_FEATURE_JOIN_INPUT_REVIEW_REQUIRED_AUDIT_ONLY"
    elif joined.empty or join_missing>0 or forbidden or fold_df.empty: status="GOLD_V3_05_LABEL_FEATURE_JOIN_WALKFORWARD_BLOCKED_AUDIT_ONLY"
    else: status="GOLD_V3_05_LABEL_FEATURE_JOIN_WALKFORWARD_READY_AUDIT_ONLY"
    decision_df=pd.DataFrame([
        ["inputs_present",inputs_ok,True,"PASS" if inputs_ok else "FAIL"],
        ["upstream_03_04_ok",upstream_ok,True,"PASS" if upstream_ok else "FAIL"],
        ["label_rows_joined",len(joined),before,"PASS" if len(joined)==before else "FAIL"],
        ["join_missing_feature_rows",join_missing,0,"PASS" if join_missing==0 else "FAIL"],
        ["forbidden_feature_columns",len(forbidden),0,"PASS" if len(forbidden)==0 else "FAIL"],
        ["walkforward_folds_nonempty",len(fold_df)>0,True,"PASS" if len(fold_df)>0 else "FAIL"],
        ["candidate_selection",False,False,"PASS"],
        ["model_training",False,False,"PASS"],
        ["signals_generated",False,False,"PASS"],
        ["zip_output_created",False,False,"PASS"],
        ["external_actions",False,False,"PASS"],
    ],columns=["decision_item","observed","required","status"])
    blocker_df=pd.DataFrame([
        ["G3-05-001","03/04 inputs","CLOSED" if inputs_ok and upstream_ok else "OPEN","HARD","03 labels and 04 features required."],
        ["G3-05-002","label-feature join","CLOSED" if join_missing==0 and len(joined)==before else "OPEN","HARD","Every label row must join to one feature row."],
        ["G3-05-003","feature leakage inventory","CLOSED" if len(forbidden)==0 else "OPEN","HARD","No outcome/profit/result/touch/tp/sl/timeout/future/label/horizon tokens in feature columns."],
        ["G3-05-004","walk-forward splits","CLOSED" if len(fold_df)>0 else "OPEN","HARD","Walk-forward folds must be created before exploration."],
        ["G3-05-005","candidate/model/signal","CLOSED_BLOCKED_BY_POLICY","HARD","No candidate selection, model training, or signals in this step."],
        ["G3-05-006","zip output","CLOSED_DISABLED","INFO","ZIP output disabled."],
        ["G3-05-007","external actions","CLOSED","HARD","No external actions performed."],
    ],columns=["blocker_id","component","status","severity","detail"])
    summary={"created_utc":created,"step":STEP,"status":status,"audit_only":True,"source_recovery_approved":False,"label_rows":int(len(labels)),"feature_rows":int(len(feats)),"joined_rows":int(len(joined)),"join_missing_feature_rows":join_missing,"feature_columns":len(feature_cols),"forbidden_feature_columns":forbidden,"months":months,"fold_count":int(len(fold_df)),"candidate_selection":False,"model_training":False,"signals_generated":False,"zip_output_created":False,"external_actions":ACTIONS}
    inv_df.to_csv(out/"gold_v3_05_input_inventory.csv",index=False,encoding="utf-8-sig")
    joined.to_csv(out/"gold_v3_05_label_feature_join_rows.csv",index=False,encoding="utf-8-sig")
    col_inv.to_csv(out/"gold_v3_05_feature_column_inventory.csv",index=False,encoding="utf-8-sig")
    month_counts.to_csv(out/"gold_v3_05_month_row_counts.csv",index=False,encoding="utf-8-sig")
    fold_df.to_csv(out/"gold_v3_05_walkforward_fold_matrix.csv",index=False,encoding="utf-8-sig")
    decision_df.to_csv(out/"gold_v3_05_decision_matrix.csv",index=False,encoding="utf-8-sig")
    blocker_df.to_csv(out/"gold_v3_05_blocker_matrix.csv",index=False,encoding="utf-8-sig")
    write_json(out/"gold_v3_05_summary.json",summary)
    report="\n".join(["# GOLD V3 05 label-feature join and walk-forward split audit-only report","",f"Created UTC: {created}",f"Status: `{status}`","","## Month row counts",md(month_counts),"","## Walk-forward folds",md(fold_df),"","## Decision matrix",md(decision_df),"","## Blockers",md(blocker_df),"","## Safety","- GOLD V3 only; no V2 artifacts used.","- No candidate selection, no model training, no signals.","- No ZIP output.","- External actions remain OFF."])
    (out/"GOLD_V3_05_LABEL_FEATURE_JOIN_WALKFORWARD_SPLIT_AUDIT_ONLY_REPORT.md").write_text(report,encoding="utf-8")
    print(json.dumps({"status":status,"output_dir":str(out),"zip_output_created":False},ensure_ascii=False,indent=2))
    print("No ZIP, candidate selection, model training, signals, Discord, MT5, AI API, live hook, live evaluator, or final signal action was performed.")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
