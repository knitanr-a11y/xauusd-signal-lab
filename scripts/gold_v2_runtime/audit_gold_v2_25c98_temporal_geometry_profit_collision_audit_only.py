#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import hashlib, json, math, zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import pandas as pd

STEP = "25C98_TEMPORAL_GEOMETRY_PROFIT_COLLISION_AUDIT_ONLY"
OUT_NAME = "gold_v2_25c98_temporal_geometry_profit_collision_audit_only"
INPUTS = ["25c97_summary.json", "25c97_signature_collision_rows.csv", "25c97_signature_collision_groups.csv", "25c97_observed_profit_feature_rows.csv", "25c94_selector_component_rows.csv"]
EXPECTED_25C97_STATUS = "PROFIT_OBSERVABILITY_AMBIGUITY_FOUND_AUDIT_ONLY_LIVE_BLOCKED"
EXPECTED_FEATURE_ROWS = 250
EXPECTED_COMPONENT_ROWS = 250
ACTIONS = {"discord_send_allowed": False, "mt5_order_allowed": False, "ai_api_allowed": False, "live_hook_allowed": False, "live_evaluator_allowed": False, "final_signal_allowed": False}
BASE_FIELDS = ["selector", "top_candidate_id", "component_count", "component_unique_origins", "candidate_ids", "origin_ids", "candidate_id_eq_top_candidate_id_class", "max_profit_raw_row_class", "min_profit_raw_row_class", "first_component_sort_raw_row_class", "last_component_sort_raw_row_class", "profit_mean_class", "profit_median_class"]
GEOM_FIELDS = ["entry_offset_from_component_min_min_class", "component_entry_span_min_class", "component_exit_span_min_class", "component_tail_after_top_entry_min_class", "component_entry_tail_after_top_entry_min_class"]
SIGNATURES = {
    "strict_plus_entry_offset": BASE_FIELDS + ["entry_offset_from_component_min_min_class"],
    "strict_plus_entry_span": BASE_FIELDS + ["component_entry_span_min_class"],
    "strict_plus_exit_span": BASE_FIELDS + ["component_exit_span_min_class"],
    "strict_plus_all_geometry": BASE_FIELDS + GEOM_FIELDS,
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
    except Exception: return "NA"


def md(df: pd.DataFrame, n: int = 40) -> str:
    if df.empty: return "_No rows._"
    d = df.head(n).fillna("")
    lines = ["| " + " | ".join(map(str, d.columns)) + " |", "| " + " | ".join(["---"] * len(d.columns)) + " |"]
    for _, r in d.iterrows(): lines.append("| " + " | ".join(str(r[c]).replace("|", "\\|").replace("\n", " ") for c in d.columns) + " |")
    return "\n".join(lines)


def enrich(features: pd.DataFrame, comp: pd.DataFrame) -> pd.DataFrame:
    keep = ["top_row_index", "selector", "selected_component_id", "entry_time", "component_min_entry", "component_max_entry", "component_max_exit"]
    keep = [c for c in keep if c in comp.columns]
    out = features.merge(comp[keep], on=["top_row_index", "selector", "selected_component_id", "entry_time"], how="left", suffixes=("", "_component"))
    out["entry_dt"] = pd.to_datetime(out["entry_time"], errors="coerce")
    out["component_min_entry_dt"] = pd.to_datetime(out["component_min_entry"], errors="coerce")
    out["component_max_entry_dt"] = pd.to_datetime(out["component_max_entry"], errors="coerce")
    out["component_max_exit_dt"] = pd.to_datetime(out["component_max_exit"], errors="coerce")
    out["entry_offset_from_component_min_min"] = (out["entry_dt"] - out["component_min_entry_dt"]).dt.total_seconds() / 60.0
    out["component_entry_span_min"] = (out["component_max_entry_dt"] - out["component_min_entry_dt"]).dt.total_seconds() / 60.0
    out["component_exit_span_min"] = (out["component_max_exit_dt"] - out["component_min_entry_dt"]).dt.total_seconds() / 60.0
    out["component_tail_after_top_entry_min"] = (out["component_max_exit_dt"] - out["entry_dt"]).dt.total_seconds() / 60.0
    out["component_entry_tail_after_top_entry_min"] = (out["component_max_entry_dt"] - out["entry_dt"]).dt.total_seconds() / 60.0
    for c in [g[:-6] for g in GEOM_FIELDS]: out[c + "_class"] = out[c].apply(cls)
    return out


def summarize(rows: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    sr, cg, cr = [], [], []
    for name, cols in SIGNATURES.items():
        missing = [c for c in cols if c not in rows.columns]
        if missing:
            sr.append({"signature_name": name, "groups": 0, "collision_groups": 0, "rows_in_collision_groups": 0, "max_top_profit_classes": 0, "missing_columns": ";".join(missing)})
            continue
        g = rows.groupby(cols, dropna=False).agg(rows=("top_row_index", "nunique"), top_profit_classes=("top_profit_class", "nunique"), top_profit_values=("top_profit_class", lambda s: ";".join(sorted(set(map(str, s)))))).reset_index()
        bad = g[g["top_profit_classes"] > 1].copy()
        sr.append({"signature_name": name, "groups": int(len(g)), "collision_groups": int(len(bad)), "rows_in_collision_groups": int(bad["rows"].sum()) if not bad.empty else 0, "max_top_profit_classes": int(g["top_profit_classes"].max()) if not g.empty else 0, "missing_columns": ""})
        if not bad.empty:
            bad.insert(0, "signature_name", name); cg.append(bad)
            keys = bad[cols].drop_duplicates()
            marked = rows.merge(keys, on=cols, how="inner")
            marked.insert(0, "signature_name", name); cr.append(marked)
    return pd.DataFrame(sr), (pd.concat(cg, ignore_index=True) if cg else pd.DataFrame()), (pd.concat(cr, ignore_index=True) if cr else pd.DataFrame())


def main() -> int:
    created = datetime.now(timezone.utc).isoformat(); out = out_dir(); paths = {n: find_file(n) for n in INPUTS}
    inv = inventory(paths); s97 = read_json(paths["25c97_summary.json"])
    features = read_csv(paths["25c97_observed_profit_feature_rows.csv"])
    comp = read_csv(paths["25c94_selector_component_rows.csv"])
    coll = read_csv(paths["25c97_signature_collision_rows.csv"])
    inputs_ok = bool(inv["exists"].all()) if not inv.empty else False
    upstream_ok = s97.get("status") == EXPECTED_25C97_STATUS
    features_ok = len(features) == EXPECTED_FEATURE_ROWS
    comp_ok = len(comp) == EXPECTED_COMPONENT_ROWS
    strict_collision_groups = int(s97.get("strict_full_observed_collision_groups", 0) or 0)
    temporal = enrich(features, comp) if not features.empty and not comp.empty else pd.DataFrame()
    ss, cg, cr = summarize(temporal) if not temporal.empty else (pd.DataFrame(), pd.DataFrame(), pd.DataFrame())
    collision_count = int(ss["collision_groups"].sum()) if not ss.empty else 0
    all_geom_collision = int(ss[ss["signature_name"].eq("strict_plus_all_geometry")]["collision_groups"].sum()) if not ss.empty else 0
    strict_temporal = temporal[temporal["top_row_index"].isin([31, 78])].copy() if not temporal.empty else pd.DataFrame()

    if not (inputs_ok and upstream_ok and features_ok and comp_ok and strict_collision_groups == 2):
        status = "TEMPORAL_GEOMETRY_PROFIT_COLLISION_INPUT_REVIEW_REQUIRED_AUDIT_ONLY"
    elif all_geom_collision > 0:
        status = "TEMPORAL_GEOMETRY_PROFIT_COLLISION_REMAINS_AUDIT_ONLY_LIVE_BLOCKED"
    else:
        status = "TEMPORAL_GEOMETRY_PROFIT_COLLISION_RESOLVED_CANDIDATE_AUDIT_ONLY_HUMAN_REVIEW_REQUIRED_LIVE_BLOCKED"

    decision = pd.DataFrame([
        ["inputs_present", inputs_ok, True, "PASS" if inputs_ok else "FAIL"],
        ["upstream_25c97_ok", upstream_ok, True, "PASS" if upstream_ok else "FAIL"],
        ["observed_profit_feature_rows", len(features), EXPECTED_FEATURE_ROWS, "PASS" if features_ok else "FAIL"],
        ["selector_component_rows", len(comp), EXPECTED_COMPONENT_ROWS, "PASS" if comp_ok else "FAIL"],
        ["upstream_strict_collision_groups", strict_collision_groups, 2, "PASS" if strict_collision_groups == 2 else "FAIL"],
        ["temporal_signature_collision_groups", collision_count, 0, "BLOCKED" if collision_count > 0 else "PASS"],
        ["strict_plus_all_geometry_collision_groups", all_geom_collision, 0, "BLOCKED" if all_geom_collision > 0 else "PASS"],
        ["coreb_live_evaluator_allowed", False, False, "PASS"],
        ["final_signal_allowed", False, False, "PASS"],
        ["a002_used", False, False, "PASS"],
        ["source_recovery_approved", False, False, "PASS"],
    ], columns=["decision_item", "observed", "required", "status"])
    blockers = pd.DataFrame([
        ["B98-001", "inputs/25c97-status", "CLOSED" if inputs_ok and upstream_ok and features_ok and comp_ok else "OPEN", "HARD", "25C97 and 25C94 artifacts must be present."],
        ["B98-002", "temporal_geometry_collision", "OPEN" if all_geom_collision > 0 else "REVIEW", "HARD", "Relative temporal geometry still collides." if all_geom_collision > 0 else "Relative geometry resolved tested strict collisions; human review required."],
        ["B98-003", "representative_profit_binding", "OPEN", "HARD", "Profit representative source remains unresolved."],
        ["B98-004", "CoreB live evaluator", "OPEN", "HARD", "Live remains blocked."],
        ["B98-005", "A002", "CLOSED_FOR_COREB_MAIN_PATH", "INFO", "A002 is auxiliary-only and not used."],
    ], columns=["blocker_id", "component", "status", "severity", "detail"])
    summary = {"created_utc": created, "step": STEP, "status": status, "audit_only": True, "source_recovery_approved": False, "upstream_25c97_ok": upstream_ok, "inputs_present": inputs_ok, "observed_profit_feature_rows": int(len(features)), "selector_component_rows": int(len(comp)), "upstream_strict_collision_groups": strict_collision_groups, "temporal_signature_collision_groups": collision_count, "strict_plus_all_geometry_collision_groups": all_geom_collision, "coreb_live_evaluator_allowed": False, "final_signal_allowed": False, "a002_used": False, "external_actions": ACTIONS}
    inv.to_csv(out / "25c98_input_inventory.csv", index=False, encoding="utf-8-sig")
    temporal.to_csv(out / "25c98_temporal_feature_rows.csv", index=False, encoding="utf-8-sig")
    ss.to_csv(out / "25c98_temporal_signature_summary.csv", index=False, encoding="utf-8-sig")
    cg.to_csv(out / "25c98_temporal_collision_groups.csv", index=False, encoding="utf-8-sig")
    cr.to_csv(out / "25c98_temporal_collision_rows.csv", index=False, encoding="utf-8-sig")
    strict_temporal.to_csv(out / "25c98_strict_collision_temporal_rows.csv", index=False, encoding="utf-8-sig")
    decision.to_csv(out / "25c98_decision_matrix.csv", index=False, encoding="utf-8-sig")
    blockers.to_csv(out / "25c98_blocker_matrix.csv", index=False, encoding="utf-8-sig")
    write_json(out / "25c98_summary.json", summary)
    report = "\n".join(["# GOLD V2 25C98 temporal geometry profit collision audit-only report", "", f"Created UTC: {created}", f"Status: `{status}`", "", "## Decision matrix", md(decision), "", "## Temporal signature summary", md(ss), "", "## Strict collision temporal rows", md(strict_temporal), "", "## Blockers", md(blockers), "", "## Safety", "- audit_only: true", "- diagnostic only; no temporal rule promotion", "- A002 not used", "- source recovery not approved", "- live evaluator/final signal/external actions remain OFF", "- NO_SIGNAL must not notify Discord"])
    (out / "GOLD_V2_25C98_TEMPORAL_GEOMETRY_PROFIT_COLLISION_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")
    zip_path = fx_outputs() / f"{OUT_NAME}.zip"
    if zip_path.exists(): zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for p in out.iterdir(): z.write(p, arcname=p.name)
    print(json.dumps({"status": status, "output_dir": str(out), "zip": str(zip_path)}, ensure_ascii=False, indent=2, allow_nan=False))
    print("No Discord, MT5, AI API, live hook, live evaluator, or final signal action was performed.")
    return 0 if status.endswith("LIVE_BLOCKED") or status.endswith("AUDIT_ONLY") else 2


if __name__ == "__main__":
    raise SystemExit(main())
