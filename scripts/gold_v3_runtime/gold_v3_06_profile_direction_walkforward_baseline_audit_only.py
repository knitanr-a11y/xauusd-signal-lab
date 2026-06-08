#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import hashlib, json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import pandas as pd

STEP = "GOLD_V3_06_PROFILE_DIRECTION_WALKFORWARD_BASELINE_AUDIT_ONLY"
OUT_NAME = "06_profile_direction_walkforward_baseline_audit_only"
EXPECTED_05_STATUS = "GOLD_V3_05_LABEL_FEATURE_JOIN_WALKFORWARD_READY_AUDIT_ONLY"
ACTIONS = {"discord_send_allowed": False, "mt5_order_allowed": False, "ai_api_allowed": False, "live_hook_allowed": False, "live_evaluator_allowed": False, "final_signal_allowed": False}
USECOLS = ["entry_month", "profile_id", "direction", "label_outcome", "label_price_distance_result_usd"]


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


def group_metrics(df: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
    rows=[]
    if df.empty:
        return pd.DataFrame()
    for keys, x in df.groupby(group_cols, dropna=False):
        if not isinstance(keys, tuple):
            keys = (keys,)
        row = {c: v for c, v in zip(group_cols, keys)}
        n = len(x)
        tp = int((x["label_outcome"] == "TP").sum())
        sl = int((x["label_outcome"] == "SL").sum())
        timeout = int((x["label_outcome"] == "TIMEOUT").sum())
        result = pd.to_numeric(x["label_price_distance_result_usd"], errors="coerce")
        avg = float(result.mean()) if n else 0.0
        total = float(result.sum()) if n else 0.0
        row.update({
            "rows": n,
            "tp_count": tp,
            "sl_count": sl,
            "timeout_count": timeout,
            "other_count": n - tp - sl - timeout,
            "tp_rate": tp / n if n else 0.0,
            "sl_rate": sl / n if n else 0.0,
            "timeout_rate": timeout / n if n else 0.0,
            "avg_result_usd": avg,
            "sum_result_usd": total,
            "positive_avg_result": avg > 0,
        })
        rows.append(row)
    return pd.DataFrame(rows)


def build_fold_split_baseline(labels: pd.DataFrame, folds: pd.DataFrame) -> pd.DataFrame:
    rows=[]
    for _, f in folds.iterrows():
        fold_id = f["fold_id"]
        train_months = [m for m in str(f["train_months"]).split(";") if m]
        split_defs = [
            ("train", train_months),
            ("validation", [f["validation_month"]]),
            ("test", [f["test_month"]]),
        ]
        for split_name, months in split_defs:
            part = labels[labels["entry_month"].isin(months)].copy()
            m = group_metrics(part, ["profile_id", "direction"])
            if m.empty:
                continue
            m.insert(0, "fold_id", fold_id)
            m.insert(1, "split", split_name)
            m.insert(2, "months", ";".join(months))
            rows.append(m)
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()


def build_test_stability(fold_split: pd.DataFrame) -> pd.DataFrame:
    test = fold_split[fold_split["split"].eq("test")].copy()
    rows=[]
    for keys, x in test.groupby(["profile_id", "direction"], dropna=False):
        profile_id, direction = keys
        folds = len(x)
        pos = int((x["avg_result_usd"] > 0).sum())
        rows.append({
            "profile_id": profile_id,
            "direction": direction,
            "test_folds": folds,
            "test_positive_folds": pos,
            "test_positive_fold_rate": pos / folds if folds else 0.0,
            "test_avg_result_mean": float(x["avg_result_usd"].mean()) if folds else 0.0,
            "test_avg_result_min": float(x["avg_result_usd"].min()) if folds else 0.0,
            "test_avg_result_max": float(x["avg_result_usd"].max()) if folds else 0.0,
            "test_sum_result_total": float(x["sum_result_usd"].sum()) if folds else 0.0,
            "test_rows_total": int(x["rows"].sum()) if folds else 0,
        })
    return pd.DataFrame(rows).sort_values(["test_positive_fold_rate", "test_avg_result_mean", "test_sum_result_total"], ascending=[False, False, False]) if rows else pd.DataFrame()


def main() -> int:
    created = datetime.now(timezone.utc).isoformat()
    out = out_dir()
    paths = [dir05()/"gold_v3_05_summary.json", dir05()/"gold_v3_05_label_feature_join_rows.csv", dir05()/"gold_v3_05_walkforward_fold_matrix.csv"]
    inv_df = input_inventory(paths)
    s05 = read_json(paths[0])
    inputs_ok = bool(inv_df["exists"].all())
    upstream_ok = s05.get("status") == EXPECTED_05_STATUS
    if inputs_ok:
        labels = pd.read_csv(paths[1], usecols=USECOLS)
        folds = pd.read_csv(paths[2])
        fold_split = build_fold_split_baseline(labels, folds)
        test_stability = build_test_stability(fold_split)
        month_summary = group_metrics(labels, ["entry_month", "profile_id", "direction"])
    else:
        labels = pd.DataFrame(); folds = pd.DataFrame(); fold_split = pd.DataFrame(); test_stability = pd.DataFrame(); month_summary = pd.DataFrame()
    if not (inputs_ok and upstream_ok):
        status = "GOLD_V3_06_PROFILE_DIRECTION_BASELINE_INPUT_REVIEW_REQUIRED_AUDIT_ONLY"
    elif labels.empty or folds.empty or fold_split.empty or test_stability.empty:
        status = "GOLD_V3_06_PROFILE_DIRECTION_BASELINE_BLOCKED_AUDIT_ONLY"
    else:
        status = "GOLD_V3_06_PROFILE_DIRECTION_BASELINE_READY_AUDIT_ONLY"
    decision_df = pd.DataFrame([
        ["inputs_present", inputs_ok, True, "PASS" if inputs_ok else "FAIL"],
        ["upstream_05_ok", upstream_ok, True, "PASS" if upstream_ok else "FAIL"],
        ["label_rows_read", len(labels), ">0", "PASS" if len(labels)>0 else "FAIL"],
        ["walkforward_folds_read", len(folds), ">0", "PASS" if len(folds)>0 else "FAIL"],
        ["fold_split_baseline_rows", len(fold_split), ">0", "PASS" if len(fold_split)>0 else "FAIL"],
        ["test_stability_rows", len(test_stability), ">0", "PASS" if len(test_stability)>0 else "FAIL"],
        ["candidate_selection", False, False, "PASS"],
        ["threshold_optimization", False, False, "PASS"],
        ["model_training", False, False, "PASS"],
        ["signals_generated", False, False, "PASS"],
        ["zip_output_created", False, False, "PASS"],
        ["external_actions", False, False, "PASS"],
    ], columns=["decision_item", "observed", "required", "status"])
    blocker_df = pd.DataFrame([
        ["G3-06-001", "05 inputs", "CLOSED" if inputs_ok and upstream_ok else "OPEN", "HARD", "05 ready summary, joined rows, and fold matrix required."],
        ["G3-06-002", "baseline diagnostics", "CLOSED" if len(fold_split)>0 and len(test_stability)>0 else "OPEN", "HARD", "Fold split and test stability summaries must be created."],
        ["G3-06-003", "candidate/model/signal", "CLOSED_BLOCKED_BY_POLICY", "HARD", "No candidate selection, threshold optimization, model training, or signals in this step."],
        ["G3-06-004", "zip output", "CLOSED_DISABLED", "INFO", "ZIP output disabled."],
        ["G3-06-005", "external actions", "CLOSED", "HARD", "No external actions performed."],
    ], columns=["blocker_id", "component", "status", "severity", "detail"])
    summary = {
        "created_utc": created,
        "step": STEP,
        "status": status,
        "audit_only": True,
        "source_recovery_approved": False,
        "label_rows_read": int(len(labels)),
        "folds_read": int(len(folds)),
        "fold_split_baseline_rows": int(len(fold_split)),
        "test_stability_rows": int(len(test_stability)),
        "top_test_stability_rows": test_stability.head(10).to_dict(orient="records") if not test_stability.empty else [],
        "candidate_selection": False,
        "threshold_optimization": False,
        "model_training": False,
        "signals_generated": False,
        "zip_output_created": False,
        "external_actions": ACTIONS,
    }
    inv_df.to_csv(out/"gold_v3_06_input_inventory.csv", index=False, encoding="utf-8-sig")
    fold_split.to_csv(out/"gold_v3_06_fold_split_profile_direction_baseline.csv", index=False, encoding="utf-8-sig")
    test_stability.to_csv(out/"gold_v3_06_profile_direction_test_stability_summary.csv", index=False, encoding="utf-8-sig")
    month_summary.to_csv(out/"gold_v3_06_month_profile_direction_summary.csv", index=False, encoding="utf-8-sig")
    decision_df.to_csv(out/"gold_v3_06_decision_matrix.csv", index=False, encoding="utf-8-sig")
    blocker_df.to_csv(out/"gold_v3_06_blocker_matrix.csv", index=False, encoding="utf-8-sig")
    write_json(out/"gold_v3_06_summary.json", summary)
    report = "\n".join([
        "# GOLD V3 06 profile-direction walk-forward baseline audit-only report",
        "",
        f"Created UTC: {created}",
        f"Status: `{status}`",
        "",
        "## Top test stability rows",
        md(test_stability.head(20)),
        "",
        "## Decision matrix",
        md(decision_df),
        "",
        "## Blockers",
        md(blocker_df),
        "",
        "## Safety",
        "- GOLD V3 only; no V2 artifacts used.",
        "- No candidate selection, threshold optimization, model training, or signals.",
        "- No ZIP output.",
        "- External actions remain OFF.",
    ])
    (out/"GOLD_V3_06_PROFILE_DIRECTION_WALKFORWARD_BASELINE_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")
    print(json.dumps({"status": status, "output_dir": str(out), "zip_output_created": False}, ensure_ascii=False, indent=2))
    print("No ZIP, candidate selection, threshold optimization, model training, signals, Discord, MT5, AI API, live hook, live evaluator, or final signal action was performed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
