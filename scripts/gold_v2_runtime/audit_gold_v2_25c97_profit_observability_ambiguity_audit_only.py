#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import hashlib, json, math, zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import pandas as pd

STEP = "25C97_PROFIT_OBSERVABILITY_AMBIGUITY_AUDIT_ONLY"
OUT_NAME = "gold_v2_25c97_profit_observability_ambiguity_audit_only"
INPUTS = [
    "25c96_summary.json",
    "25c96_ratio_distribution.csv",
    "25c96_focus_class_breakdown.csv",
    "25c96_best_candidate_mismatch_rows.csv",
    "25c94_summary.json",
    "25c94_profit_binding_rows.csv",
    "25c94_selector_component_rows.csv",
]
EXPECTED_25C96_STATUS = "PROFIT_CLASS_MISMATCH_DIAGNOSTIC_READY_AUDIT_ONLY_LIVE_BLOCKED"
EXPECTED_BINDING_ROWS = 5250
EXPECTED_COMPONENT_ROWS = 250
ACTIONS = {"discord_send_allowed": False, "mt5_order_allowed": False, "ai_api_allowed": False, "live_hook_allowed": False, "live_evaluator_allowed": False, "final_signal_allowed": False}

SIGNATURES = {
    "extreme_no_id": ["selector", "candidate_id_eq_top_candidate_id_class", "max_profit_raw_row_class", "min_profit_raw_row_class"],
    "extreme_with_top_candidate": ["selector", "top_candidate_id", "candidate_id_eq_top_candidate_id_class", "max_profit_raw_row_class", "min_profit_raw_row_class"],
    "shape_extreme": ["selector", "component_count", "component_unique_origins", "candidate_id_eq_top_candidate_id_class", "max_profit_raw_row_class", "min_profit_raw_row_class"],
    "shape_extreme_with_candidate": ["selector", "top_candidate_id", "component_count", "component_unique_origins", "candidate_id_eq_top_candidate_id_class", "max_profit_raw_row_class", "min_profit_raw_row_class"],
    "full_observed_no_component_id": ["selector", "top_candidate_id", "component_count", "component_unique_origins", "candidate_ids", "origin_ids", "candidate_id_eq_top_candidate_id_class", "max_profit_raw_row_class", "min_profit_raw_row_class", "first_component_sort_raw_row_class", "last_component_sort_raw_row_class", "profit_mean_class", "profit_median_class"],
}
CLASS_COLS = ["top_profit", "candidate_id_eq_top_candidate_id", "max_profit_raw_row", "min_profit_raw_row", "first_component_sort_raw_row", "last_component_sort_raw_row", "profit_mean", "profit_median", "profit_sum"]


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


def cls(v: Any) -> str:
    try:
        f = float(v)
        if math.isnan(f): return "NA"
        return f"{round(f, 6):.6f}"
    except Exception:
        return "NA"


def md(df: pd.DataFrame, n: int = 40) -> str:
    if df.empty: return "_No rows._"
    d = df.head(n).fillna("")
    lines = ["| " + " | ".join(map(str, d.columns)) + " |", "| " + " | ".join(["---"] * len(d.columns)) + " |"]
    for _, r in d.iterrows():
        lines.append("| " + " | ".join(str(r[c]).replace("|", "\\|").replace("\n", " ") for c in d.columns) + " |")
    return "\n".join(lines)


def build_feature_rows(binding: pd.DataFrame, components: pd.DataFrame) -> pd.DataFrame:
    idx = ["top_row_index", "selector", "entry_time", "cluster_id", "top_candidate_id", "top_profit", "selected_component_id"]
    pivot = binding.pivot_table(index=idx, columns="binding_method", values="selected_profit", aggfunc="first").reset_index()
    pivot.columns.name = None
    merge_cols = ["top_row_index", "selector", "selected_component_id"]
    keep = merge_cols + ["component_count", "component_unique_origins", "candidate_ids", "origin_ids", "contains_top_candidate_candidate", "contains_top_candidate_origin", "contains_top_candidate_any"]
    keep = [c for c in keep if c in components.columns]
    out = pivot.merge(components[keep], on=merge_cols, how="left")
    for col in CLASS_COLS:
        if col in out.columns:
            out[col + "_class"] = out[col].apply(cls)
    return out


def summarize_signatures(rows: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    summary_rows = []
    collision_groups = []
    collision_rows = []
    for name, cols in SIGNATURES.items():
        present = [c for c in cols if c in rows.columns]
        if len(present) != len(cols):
            summary_rows.append({"signature_name": name, "signature_columns": ";".join(cols), "groups": 0, "collision_groups": 0, "rows_in_collision_groups": 0, "max_top_profit_classes": 0, "missing_columns": ";".join([c for c in cols if c not in rows.columns])})
            continue
        g = rows.groupby(present, dropna=False).agg(rows=("top_row_index", "nunique"), top_profit_classes=("top_profit_class", "nunique"), top_profit_values=("top_profit_class", lambda s: ";".join(sorted(set(map(str, s)))))).reset_index()
        bad = g[g["top_profit_classes"] > 1].copy()
        summary_rows.append({"signature_name": name, "signature_columns": ";".join(cols), "groups": int(len(g)), "collision_groups": int(len(bad)), "rows_in_collision_groups": int(bad["rows"].sum()) if not bad.empty else 0, "max_top_profit_classes": int(g["top_profit_classes"].max()) if not g.empty else 0, "missing_columns": ""})
        if not bad.empty:
            bad.insert(0, "signature_name", name)
            bad.insert(1, "signature_columns", ";".join(cols))
            collision_groups.append(bad)
            key_cols = present
            bad_keys = bad[key_cols].drop_duplicates()
            marked = rows.merge(bad_keys, on=key_cols, how="inner")
            marked.insert(0, "signature_name", name)
            marked.insert(1, "signature_columns", ";".join(cols))
            collision_rows.append(marked)
    return pd.DataFrame(summary_rows), (pd.concat(collision_groups, ignore_index=True) if collision_groups else pd.DataFrame()), (pd.concat(collision_rows, ignore_index=True) if collision_rows else pd.DataFrame())


def main() -> int:
    created = datetime.now(timezone.utc).isoformat(); out = out_dir(); paths = {n: find_file(n) for n in INPUTS}
    inv = inventory(paths); s96 = read_json(paths["25c96_summary.json"])
    binding = read_csv(paths["25c94_profit_binding_rows.csv"])
    components = read_csv(paths["25c94_selector_component_rows.csv"])

    inputs_ok = bool(inv["exists"].all()) if not inv.empty else False
    upstream_ok = s96.get("status") == EXPECTED_25C96_STATUS
    binding_ok = len(binding) == EXPECTED_BINDING_ROWS
    components_ok = len(components) == EXPECTED_COMPONENT_ROWS

    feature_rows = build_feature_rows(binding, components) if not binding.empty and not components.empty else pd.DataFrame()
    sig_summary, collision_groups, collision_rows = summarize_signatures(feature_rows) if not feature_rows.empty else (pd.DataFrame(), pd.DataFrame(), pd.DataFrame())
    total_collision_groups = int(sig_summary["collision_groups"].sum()) if not sig_summary.empty else 0
    strict_collision_groups = int(sig_summary[sig_summary["signature_name"].eq("full_observed_no_component_id")]["collision_groups"].sum()) if not sig_summary.empty else 0

    if not (inputs_ok and upstream_ok and binding_ok and components_ok):
        status = "PROFIT_OBSERVABILITY_AMBIGUITY_INPUT_REVIEW_REQUIRED_AUDIT_ONLY"
    elif total_collision_groups > 0:
        status = "PROFIT_OBSERVABILITY_AMBIGUITY_FOUND_AUDIT_ONLY_LIVE_BLOCKED"
    else:
        status = "PROFIT_OBSERVABILITY_SIGNATURE_UNIQUE_CANDIDATE_AUDIT_ONLY_HUMAN_REVIEW_REQUIRED_LIVE_BLOCKED"

    decision = pd.DataFrame([
        ["inputs_present", inputs_ok, True, "PASS" if inputs_ok else "FAIL"],
        ["upstream_25c96_ok", upstream_ok, True, "PASS" if upstream_ok else "FAIL"],
        ["25c94_profit_binding_rows", len(binding), EXPECTED_BINDING_ROWS, "PASS" if binding_ok else "FAIL"],
        ["25c94_selector_component_rows", len(components), EXPECTED_COMPONENT_ROWS, "PASS" if components_ok else "FAIL"],
        ["observed_profit_feature_rows", len(feature_rows), EXPECTED_COMPONENT_ROWS, "PASS" if len(feature_rows) == EXPECTED_COMPONENT_ROWS else "WARN"],
        ["signature_collision_groups", total_collision_groups, 0, "BLOCKED" if total_collision_groups > 0 else "PASS"],
        ["strict_full_observed_collision_groups", strict_collision_groups, 0, "BLOCKED" if strict_collision_groups > 0 else "PASS"],
        ["coreb_live_evaluator_allowed", False, False, "PASS"],
        ["final_signal_allowed", False, False, "PASS"],
        ["a002_used", False, False, "PASS"],
        ["source_recovery_approved", False, False, "PASS"],
    ], columns=["decision_item", "observed", "required", "status"])
    blockers = pd.DataFrame([
        ["B97-001", "inputs/25c96-status", "CLOSED" if inputs_ok and upstream_ok and binding_ok and components_ok else "OPEN", "HARD", "25C96 and 25C94 artifacts must be present."],
        ["B97-002", "profit_observability_ambiguity", "OPEN" if total_collision_groups > 0 else "CLOSED", "HARD", "Observed signatures map to multiple top profit values." if total_collision_groups > 0 else "No tested signature collision found; human review still required."],
        ["B97-003", "representative_profit_binding", "OPEN", "HARD", "Profit representative source remains unresolved."],
        ["B97-004", "CoreB live evaluator", "OPEN", "HARD", "Live remains blocked."],
        ["B97-005", "A002", "CLOSED_FOR_COREB_MAIN_PATH", "INFO", "A002 is auxiliary-only and not used."],
    ], columns=["blocker_id", "component", "status", "severity", "detail"])
    summary = {"created_utc": created, "step": STEP, "status": status, "audit_only": True, "source_recovery_approved": False, "upstream_25c96_ok": upstream_ok, "inputs_present": inputs_ok, "25c94_profit_binding_rows": int(len(binding)), "25c94_selector_component_rows": int(len(components)), "observed_profit_feature_rows": int(len(feature_rows)), "signature_collision_groups": total_collision_groups, "strict_full_observed_collision_groups": strict_collision_groups, "coreb_live_evaluator_allowed": False, "final_signal_allowed": False, "a002_used": False, "external_actions": ACTIONS}

    inv.to_csv(out / "25c97_input_inventory.csv", index=False, encoding="utf-8-sig")
    feature_rows.to_csv(out / "25c97_observed_profit_feature_rows.csv", index=False, encoding="utf-8-sig")
    sig_summary.to_csv(out / "25c97_signature_summary.csv", index=False, encoding="utf-8-sig")
    collision_groups.to_csv(out / "25c97_signature_collision_groups.csv", index=False, encoding="utf-8-sig")
    collision_rows.to_csv(out / "25c97_signature_collision_rows.csv", index=False, encoding="utf-8-sig")
    decision.to_csv(out / "25c97_decision_matrix.csv", index=False, encoding="utf-8-sig")
    blockers.to_csv(out / "25c97_blocker_matrix.csv", index=False, encoding="utf-8-sig")
    write_json(out / "25c97_summary.json", summary)
    report = "\n".join(["# GOLD V2 25C97 profit observability ambiguity audit-only report", "", f"Created UTC: {created}", f"Status: `{status}`", "", "## Decision matrix", md(decision), "", "## Signature summary", md(sig_summary), "", "## Collision groups", md(collision_groups), "", "## Blockers", md(blockers), "", "## Safety", "- audit_only: true", "- diagnostic only; no signature-based live logic promotion", "- A002 not used", "- source recovery not approved", "- live evaluator/final signal/external actions remain OFF", "- NO_SIGNAL must not notify Discord"])
    (out / "GOLD_V2_25C97_PROFIT_OBSERVABILITY_AMBIGUITY_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")
    zip_path = fx_outputs() / f"{OUT_NAME}.zip"
    if zip_path.exists(): zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for p in out.iterdir(): z.write(p, arcname=p.name)
    print(json.dumps({"status": status, "output_dir": str(out), "zip": str(zip_path)}, ensure_ascii=False, indent=2, allow_nan=False))
    print("No Discord, MT5, AI API, live hook, live evaluator, or final signal action was performed.")
    return 0 if status.endswith("LIVE_BLOCKED") or status.endswith("AUDIT_ONLY") else 2


if __name__ == "__main__":
    raise SystemExit(main())
