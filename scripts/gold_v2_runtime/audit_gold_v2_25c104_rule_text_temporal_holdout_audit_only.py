#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import hashlib, json, math, zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import pandas as pd

STEP = "25C104_RULE_TEXT_TEMPORAL_HOLDOUT_AUDIT_ONLY"
OUT_NAME = "gold_v2_25c104_rule_text_temporal_holdout_audit_only"
INPUTS = ["25c103_summary.json", "25c103_reduced_feature_rows.csv", "25c103_reduced_discriminator_summary.csv", "25c103_decision_matrix.csv", "25c103_blocker_matrix.csv"]
EXPECTED_25C103_STATUS = "RULE_TEXT_REDUCED_DISCRIMINATOR_CANDIDATE_AUDIT_ONLY_HUMAN_REVIEW_REQUIRED_LIVE_BLOCKED"
EXPECTED_ROWS = 250
EXPECTED_DISC_ROWS = 14
ACTIONS = {"discord_send_allowed": False, "mt5_order_allowed": False, "ai_api_allowed": False, "live_hook_allowed": False, "live_evaluator_allowed": False, "final_signal_allowed": False}
PREFIX_SIG = ["selector", "top_candidate_id", "prefix_component_count", "prefix_component_unique_origins", "prefix_candidate_ids", "prefix_origin_ids", "prefix_candidate_id_eq_top_candidate_id_class", "prefix_max_profit_raw_row_class", "prefix_min_profit_raw_row_class", "prefix_first_component_sort_raw_row_class", "prefix_last_component_sort_raw_row_class", "prefix_profit_mean_class", "prefix_profit_median_class", "entry_offset_from_component_min_min_class"]
KEYS = {
    "prefix_only": PREFIX_SIG,
    "prefix_plus_filter_family_set": PREFIX_SIG + ["filter_family_set"],
    "prefix_plus_filter_feature_name_set": PREFIX_SIG + ["filter_feature_name_set"],
    "prefix_plus_filter_operator_feature_set": PREFIX_SIG + ["filter_operator_feature_set"],
    "selector_top_candidate_filter_family_only": ["selector", "top_candidate_id", "filter_family_set"],
}


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
    if isinstance(x, float):
        if math.isnan(x): return None
        if math.isinf(x): return "inf" if x > 0 else "-inf"
    try:
        if pd.isna(x): return None
    except Exception:
        pass
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
    rows = []
    for n, p in paths.items():
        r = {"filename": n, "exists": bool(p and p.exists()), "path": str(p) if p else ""}
        if p and p.exists():
            r["bytes"] = p.stat().st_size; r["sha256"] = sha256_file(p)
            if p.suffix.lower() == ".csv":
                r["row_count"] = len(pd.read_csv(p)); r["columns"] = ";".join(pd.read_csv(p, nrows=0).columns)
        rows.append(r)
    return pd.DataFrame(rows)


def md(df: pd.DataFrame, n: int = 40) -> str:
    if df.empty: return "_No rows._"
    d = df.head(n).fillna("")
    lines = ["| " + " | ".join(map(str, d.columns)) + " |", "| " + " | ".join(["---"] * len(d.columns)) + " |"]
    for _, r in d.iterrows():
        lines.append("| " + " | ".join(str(r[c]).replace("|", "\\|").replace("\n", " ") for c in d.columns) + " |")
    return "\n".join(lines)


def collision_summary(df: pd.DataFrame, key_name: str, cols: list[str]) -> dict[str, Any]:
    missing = [c for c in cols if c not in df.columns]
    if missing:
        return {"key_name": key_name, "groups": 0, "collision_groups": 0, "rows_in_collision_groups": 0, "max_top_profit_classes": 0, "unique_ratio": None, "missing_columns": ";".join(missing)}
    g = df.groupby(cols, dropna=False).agg(rows=("top_row_index", "nunique"), top_profit_classes=("top_profit_class", "nunique")).reset_index()
    bad = g[g["top_profit_classes"] > 1]
    return {"key_name": key_name, "groups": int(len(g)), "collision_groups": int(len(bad)), "rows_in_collision_groups": int(bad["rows"].sum()) if not bad.empty else 0, "max_top_profit_classes": int(g["top_profit_classes"].max()) if not g.empty else 0, "unique_ratio": len(g) / len(df) if len(df) else None, "missing_columns": ""}


def holdout(df: pd.DataFrame, key_name: str, cols: list[str]) -> pd.DataFrame:
    rows = []
    months = sorted(df["entry_month_holdout"].dropna().astype(str).unique())
    for m in months:
        train = df[df["entry_month_holdout"].astype(str) != m].copy()
        test = df[df["entry_month_holdout"].astype(str) == m].copy()
        grp = train.groupby(cols, dropna=False).agg(classes=("top_profit_class", lambda s: sorted(set(map(str, s))))).reset_index()
        grp["train_unique"] = grp["classes"].apply(lambda x: len(x) == 1)
        grp["pred_top_profit_class"] = grp["classes"].apply(lambda x: x[0] if len(x) == 1 else None)
        joined = test.merge(grp[cols + ["train_unique", "pred_top_profit_class"]], on=cols, how="left")
        seen = joined["pred_top_profit_class"].notna()
        conflicted = joined["train_unique"].eq(False)
        correct = seen & joined["pred_top_profit_class"].astype(str).eq(joined["top_profit_class"].astype(str))
        rows.append({"key_name": key_name, "holdout_month": m, "test_rows": int(len(test)), "seen_key_rows": int(seen.sum()), "unseen_key_rows": int((~seen & ~conflicted).sum()), "conflicted_train_key_rows": int(conflicted.sum()), "correct_seen_rows": int(correct.sum()), "seen_coverage": float(seen.sum() / len(test)) if len(test) else None, "seen_accuracy": float(correct.sum() / seen.sum()) if seen.sum() else None})
    return pd.DataFrame(rows)


def main() -> int:
    created = datetime.now(timezone.utc).isoformat(); out = out_dir(); paths = {n: find_file(n) for n in INPUTS}
    inv = inventory(paths); s103 = read_json(paths["25c103_summary.json"])
    df = read_csv(paths["25c103_reduced_feature_rows.csv"])
    disc = read_csv(paths["25c103_reduced_discriminator_summary.csv"])
    inputs_ok = bool(inv["exists"].all()) if not inv.empty else False
    upstream_ok = s103.get("status") == EXPECTED_25C103_STATUS
    rows_ok = len(df) == EXPECTED_ROWS
    disc_ok = len(disc) == EXPECTED_DISC_ROWS
    if not df.empty:
        df["entry_month_holdout"] = pd.to_datetime(df["entry_time"], errors="coerce").dt.to_period("M").astype(str)
    coll_rows, h_rows = [], []
    for name, cols in KEYS.items():
        coll_rows.append(collision_summary(df, name, cols))
        if not df.empty and all(c in df.columns for c in cols):
            h_rows.append(holdout(df, name, cols))
    coll_df = pd.DataFrame(coll_rows)
    hold_df = pd.concat(h_rows, ignore_index=True) if h_rows else pd.DataFrame()
    if not hold_df.empty:
        agg = hold_df.groupby("key_name").agg(test_rows=("test_rows", "sum"), seen_key_rows=("seen_key_rows", "sum"), unseen_key_rows=("unseen_key_rows", "sum"), conflicted_train_key_rows=("conflicted_train_key_rows", "sum"), correct_seen_rows=("correct_seen_rows", "sum")).reset_index()
        agg["seen_coverage"] = agg["seen_key_rows"] / agg["test_rows"]
        agg["seen_accuracy"] = agg.apply(lambda r: r["correct_seen_rows"] / r["seen_key_rows"] if r["seen_key_rows"] else None, axis=1)
        agg = agg.merge(coll_df[["key_name", "collision_groups", "unique_ratio"]], on="key_name", how="left")
    else:
        agg = pd.DataFrame()
    target = agg[agg["key_name"].eq("prefix_plus_filter_family_set")].iloc[0].to_dict() if not agg.empty and agg["key_name"].eq("prefix_plus_filter_family_set").any() else {}
    target_collision_zero = int(target.get("collision_groups", 999)) == 0 if target else False
    target_cov = float(target.get("seen_coverage", 0) or 0) if target else 0.0
    target_acc = float(target.get("seen_accuracy", 0) or 0) if target and target.get("seen_accuracy") is not None else 0.0
    if not (inputs_ok and upstream_ok and rows_ok and disc_ok):
        status = "RULE_TEXT_TEMPORAL_HOLDOUT_INPUT_REVIEW_REQUIRED_AUDIT_ONLY"
    elif not target_collision_zero:
        status = "RULE_TEXT_TEMPORAL_HOLDOUT_UNRESOLVED_AUDIT_ONLY_LIVE_BLOCKED"
    elif target_cov < 0.50:
        status = "RULE_TEXT_TEMPORAL_HOLDOUT_COVERAGE_BLOCKED_AUDIT_ONLY_LIVE_BLOCKED"
    elif target_acc >= 0.95:
        status = "RULE_TEXT_TEMPORAL_HOLDOUT_CANDIDATE_AUDIT_ONLY_HUMAN_REVIEW_REQUIRED_LIVE_BLOCKED"
    else:
        status = "RULE_TEXT_TEMPORAL_HOLDOUT_COVERAGE_BLOCKED_AUDIT_ONLY_LIVE_BLOCKED"
    decision = pd.DataFrame([
        ["inputs_present", inputs_ok, True, "PASS" if inputs_ok else "FAIL"],
        ["upstream_25c103_ok", upstream_ok, True, "PASS" if upstream_ok else "FAIL"],
        ["reduced_feature_rows", len(df), EXPECTED_ROWS, "PASS" if rows_ok else "FAIL"],
        ["reduced_discriminator_summary_rows", len(disc), EXPECTED_DISC_ROWS, "PASS" if disc_ok else "FAIL"],
        ["prefix_plus_filter_family_collision_groups", target.get("collision_groups"), 0, "PASS" if target_collision_zero else "BLOCKED"],
        ["prefix_plus_filter_family_holdout_seen_coverage", target_cov, ">=0.50", "PASS" if target_cov >= 0.50 else "BLOCKED"],
        ["prefix_plus_filter_family_holdout_seen_accuracy", target_acc, ">=0.95", "PASS" if target_acc >= 0.95 else "BLOCKED"],
        ["coreb_live_evaluator_allowed", False, False, "PASS"],
        ["final_signal_allowed", False, False, "PASS"],
        ["a002_used", False, False, "PASS"],
        ["source_recovery_approved", False, False, "PASS"],
    ], columns=["decision_item", "observed", "required", "status"])
    blockers = pd.DataFrame([
        ["B104-001", "inputs/25c103", "CLOSED" if inputs_ok and upstream_ok and rows_ok else "OPEN", "HARD", "25C103 artifacts must be present."],
        ["B104-002", "temporal_holdout_coverage", "OPEN" if target_cov < 0.50 else "REVIEW", "HARD", "Rule-text key has low leave-month-out seen coverage." if target_cov < 0.50 else "Rule-text key has acceptable coverage; human review required."],
        ["B104-003", "historical_key_uniqueness", "OPEN", "HARD", "High key cardinality may indicate historical memorization."],
        ["B104-004", "representative_profit_binding", "OPEN", "HARD", "Profit representative source remains unresolved."],
        ["B104-005", "CoreB live evaluator", "OPEN", "HARD", "Live remains blocked."],
        ["B104-006", "A002", "CLOSED_FOR_COREB_MAIN_PATH", "INFO", "A002 is auxiliary-only and not used."],
    ], columns=["blocker_id", "component", "status", "severity", "detail"])
    summary = {"created_utc": created, "step": STEP, "status": status, "audit_only": True, "source_recovery_approved": False, "upstream_25c103_ok": upstream_ok, "inputs_present": inputs_ok, "reduced_feature_rows": int(len(df)), "reduced_discriminator_summary_rows": int(len(disc)), "target_key": "prefix_plus_filter_family_set", "target_collision_groups": int(target.get("collision_groups", -1)) if target else None, "target_unique_ratio": target.get("unique_ratio"), "target_holdout_seen_coverage": target_cov, "target_holdout_seen_accuracy": target_acc, "target_holdout_seen_key_rows": int(target.get("seen_key_rows", 0)) if target else 0, "target_holdout_test_rows": int(target.get("test_rows", 0)) if target else 0, "coreb_live_evaluator_allowed": False, "final_signal_allowed": False, "a002_used": False, "external_actions": ACTIONS}
    inv.to_csv(out / "25c104_input_inventory.csv", index=False, encoding="utf-8-sig")
    coll_df.to_csv(out / "25c104_key_collision_cardinality_summary.csv", index=False, encoding="utf-8-sig")
    hold_df.to_csv(out / "25c104_month_holdout_detail.csv", index=False, encoding="utf-8-sig")
    agg.to_csv(out / "25c104_holdout_aggregate.csv", index=False, encoding="utf-8-sig")
    decision.to_csv(out / "25c104_decision_matrix.csv", index=False, encoding="utf-8-sig")
    blockers.to_csv(out / "25c104_blocker_matrix.csv", index=False, encoding="utf-8-sig")
    write_json(out / "25c104_summary.json", summary)
    report = "\n".join(["# GOLD V2 25C104 rule-text temporal holdout audit-only report", "", f"Created UTC: {created}", f"Status: `{status}`", "", "## Decision matrix", md(decision), "", "## Key collision/cardinality summary", md(coll_df), "", "## Holdout aggregate", md(agg), "", "## Blockers", md(blockers), "", "## Safety", "- audit_only: true", "- temporal holdout only; no live promotion", "- historical uniqueness not promoted", "- A002 not used", "- source recovery not approved", "- live evaluator/final signal/external actions remain OFF", "- NO_SIGNAL must not notify Discord"])
    (out / "GOLD_V2_25C104_RULE_TEXT_TEMPORAL_HOLDOUT_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")
    zip_path = fx_outputs() / f"{OUT_NAME}.zip"
    if zip_path.exists(): zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for p in out.iterdir(): z.write(p, arcname=p.name)
    print(json.dumps({"status": status, "output_dir": str(out), "zip": str(zip_path)}, ensure_ascii=False, indent=2, allow_nan=False))
    print("No Discord, MT5, AI API, live hook, live evaluator, or final signal action was performed.")
    return 0 if status.endswith("LIVE_BLOCKED") or status.endswith("AUDIT_ONLY") else 2

if __name__ == "__main__":
    raise SystemExit(main())
