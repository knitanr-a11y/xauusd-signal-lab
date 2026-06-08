#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import hashlib, json, math, zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import pandas as pd

STEP = "25C99_TEMPORAL_GEOMETRY_OBSERVABILITY_LEAKAGE_AUDIT_ONLY"
OUT_NAME = "gold_v2_25c99_temporal_geometry_observability_leakage_audit_only"
INPUTS = ["25c98_summary.json", "25c98_temporal_feature_rows.csv", "25c98_temporal_signature_summary.csv", "25c98_strict_collision_temporal_rows.csv", "25c98_decision_matrix.csv", "25c98_blocker_matrix.csv"]
EXPECTED_25C98_STATUS = "TEMPORAL_GEOMETRY_PROFIT_COLLISION_RESOLVED_CANDIDATE_AUDIT_ONLY_HUMAN_REVIEW_REQUIRED_LIVE_BLOCKED"
EXPECTED_FEATURE_ROWS = 250
EXPECTED_STRICT_ROWS = 4
ACTIONS = {"discord_send_allowed": False, "mt5_order_allowed": False, "ai_api_allowed": False, "live_hook_allowed": False, "live_evaluator_allowed": False, "final_signal_allowed": False}
BASE_FIELDS = ["selector", "top_candidate_id", "component_count", "component_unique_origins", "candidate_ids", "origin_ids", "candidate_id_eq_top_candidate_id_class", "max_profit_raw_row_class", "min_profit_raw_row_class", "first_component_sort_raw_row_class", "last_component_sort_raw_row_class", "profit_mean_class", "profit_median_class"]
ENTRY_OFFSET_FIELD = "entry_offset_from_component_min_min_class"


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


def md(df: pd.DataFrame, n: int = 40) -> str:
    if df.empty: return "_No rows._"
    d = df.head(n).fillna("")
    lines = ["| " + " | ".join(map(str, d.columns)) + " |", "| " + " | ".join(["---"] * len(d.columns)) + " |"]
    for _, r in d.iterrows(): lines.append("| " + " | ".join(str(r[c]).replace("|", "\\|").replace("\n", " ") for c in d.columns) + " |")
    return "\n".join(lines)


def add_flags(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    for c in ["entry_time", "component_min_entry", "component_max_entry", "component_max_exit"]:
        d[c + "_dt"] = pd.to_datetime(d[c], errors="coerce")
    d["entry_offset_ex_ante_candidate"] = d["component_min_entry_dt"].le(d["entry_time_dt"])
    d["component_entry_span_future_looking"] = d["component_max_entry_dt"].gt(d["entry_time_dt"])
    d["component_exit_span_future_looking"] = d["component_max_exit_dt"].gt(d["entry_time_dt"])
    d["component_tail_future_looking"] = d["component_max_exit_dt"].gt(d["entry_time_dt"])
    d["component_entry_tail_future_looking"] = d["component_max_entry_dt"].gt(d["entry_time_dt"])
    d["any_future_geometry_used_by_25c98_all_geometry"] = d[["component_entry_span_future_looking", "component_exit_span_future_looking", "component_tail_future_looking", "component_entry_tail_future_looking"]].any(axis=1)
    return d


def field_obs(rows: pd.DataFrame, strict: pd.DataFrame) -> pd.DataFrame:
    checks = [
        ("entry_offset_from_component_min_min", "ex_ante_candidate", "entry_offset_ex_ante_candidate", True),
        ("component_entry_span_min", "future_looking_if_component_max_entry_after_entry", "component_entry_span_future_looking", True),
        ("component_exit_span_min", "future_looking_if_component_max_exit_after_entry", "component_exit_span_future_looking", True),
        ("component_tail_after_top_entry_min", "future_looking_if_component_max_exit_after_entry", "component_tail_future_looking", True),
        ("component_entry_tail_after_top_entry_min", "future_looking_if_component_max_entry_after_entry", "component_entry_tail_future_looking", True),
    ]
    out = []
    for field, rule, flag, expected in checks:
        out.append({"field": field, "classification_rule": rule, "all_rows_true_count": int(rows[flag].sum()) if flag in rows else 0, "all_rows_total": int(len(rows)), "strict_rows_true_count": int(strict[flag].sum()) if flag in strict else 0, "strict_rows_total": int(len(strict))})
    return pd.DataFrame(out)


def summarize_entry_offset(rows: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    cols = BASE_FIELDS + [ENTRY_OFFSET_FIELD]
    missing = [c for c in cols if c not in rows.columns]
    if missing:
        return pd.DataFrame([{"signature_name": "strict_plus_entry_offset_ex_ante_only", "groups": 0, "collision_groups": 0, "rows_in_collision_groups": 0, "max_top_profit_classes": 0, "missing_columns": ";".join(missing)}]), pd.DataFrame(), pd.DataFrame()
    g = rows.groupby(cols, dropna=False).agg(rows=("top_row_index", "nunique"), top_profit_classes=("top_profit_class", "nunique"), top_profit_values=("top_profit_class", lambda s: ";".join(sorted(set(map(str, s)))))).reset_index()
    bad = g[g["top_profit_classes"] > 1].copy()
    summary = pd.DataFrame([{"signature_name": "strict_plus_entry_offset_ex_ante_only", "groups": int(len(g)), "collision_groups": int(len(bad)), "rows_in_collision_groups": int(bad["rows"].sum()) if not bad.empty else 0, "max_top_profit_classes": int(g["top_profit_classes"].max()) if not g.empty else 0, "missing_columns": ""}])
    if bad.empty: return summary, pd.DataFrame(), pd.DataFrame()
    keys = bad[cols].drop_duplicates()
    collision_rows = rows.merge(keys, on=cols, how="inner")
    return summary, bad, collision_rows


def main() -> int:
    created = datetime.now(timezone.utc).isoformat(); out = out_dir(); paths = {n: find_file(n) for n in INPUTS}
    inv = inventory(paths); s98 = read_json(paths["25c98_summary.json"])
    rows = read_csv(paths["25c98_temporal_feature_rows.csv"])
    strict = read_csv(paths["25c98_strict_collision_temporal_rows.csv"])
    inputs_ok = bool(inv["exists"].all()) if not inv.empty else False
    upstream_ok = s98.get("status") == EXPECTED_25C98_STATUS
    rows_ok = len(rows) == EXPECTED_FEATURE_ROWS
    strict_ok = len(strict) == EXPECTED_STRICT_ROWS
    flagged = add_flags(rows) if not rows.empty else pd.DataFrame()
    strict_flagged = add_flags(strict) if not strict.empty else pd.DataFrame()
    obs = field_obs(flagged, strict_flagged) if not flagged.empty else pd.DataFrame()
    sig, cg, cr = summarize_entry_offset(flagged) if not flagged.empty else (pd.DataFrame(), pd.DataFrame(), pd.DataFrame())
    entry_offset_collisions = int(sig["collision_groups"].iloc[0]) if not sig.empty else 0
    strict_entry_offset_ex_ante_ok = bool(strict_flagged["entry_offset_ex_ante_candidate"].all()) if not strict_flagged.empty else False
    strict_future_count = int(strict_flagged["any_future_geometry_used_by_25c98_all_geometry"].sum()) if not strict_flagged.empty else 0
    all_future_count = int(flagged["any_future_geometry_used_by_25c98_all_geometry"].sum()) if not flagged.empty else 0
    if not (inputs_ok and upstream_ok and rows_ok and strict_ok):
        status = "TEMPORAL_GEOMETRY_OBSERVABILITY_INPUT_REVIEW_REQUIRED_AUDIT_ONLY"
    elif entry_offset_collisions == 0 and strict_entry_offset_ex_ante_ok:
        status = "TEMPORAL_ENTRY_OFFSET_DISAMBIGUATOR_CANDIDATE_AUDIT_ONLY_HUMAN_REVIEW_REQUIRED_LIVE_BLOCKED"
    else:
        status = "TEMPORAL_GEOMETRY_RESOLUTION_REQUIRES_FUTURE_GEOMETRY_AUDIT_ONLY_LIVE_BLOCKED"
    decision = pd.DataFrame([
        ["inputs_present", inputs_ok, True, "PASS" if inputs_ok else "FAIL"],
        ["upstream_25c98_ok", upstream_ok, True, "PASS" if upstream_ok else "FAIL"],
        ["temporal_feature_rows", len(rows), EXPECTED_FEATURE_ROWS, "PASS" if rows_ok else "FAIL"],
        ["strict_collision_temporal_rows", len(strict), EXPECTED_STRICT_ROWS, "PASS" if strict_ok else "FAIL"],
        ["entry_offset_signature_collision_groups", entry_offset_collisions, 0, "PASS" if entry_offset_collisions == 0 else "BLOCKED"],
        ["strict_rows_entry_offset_ex_ante", strict_entry_offset_ex_ante_ok, True, "PASS" if strict_entry_offset_ex_ante_ok else "BLOCKED"],
        ["strict_rows_with_future_geometry_in_25c98_all_geometry", strict_future_count, 0, "INFO" if strict_future_count else "PASS"],
        ["all_rows_with_future_geometry_in_25c98_all_geometry", all_future_count, 0, "INFO" if all_future_count else "PASS"],
        ["coreb_live_evaluator_allowed", False, False, "PASS"],
        ["final_signal_allowed", False, False, "PASS"],
        ["a002_used", False, False, "PASS"],
        ["source_recovery_approved", False, False, "PASS"],
    ], columns=["decision_item", "observed", "required", "status"])
    blockers = pd.DataFrame([
        ["B99-001", "inputs/25c98-status", "CLOSED" if inputs_ok and upstream_ok and rows_ok and strict_ok else "OPEN", "HARD", "25C98 artifacts and expected candidate status must be present."],
        ["B99-002", "future_geometry_leakage", "OPEN" if strict_future_count > 0 else "CLOSED", "HARD", "25C98 all-geometry includes future-looking fields; do not promote."],
        ["B99-003", "entry_offset_disambiguator", "REVIEW" if entry_offset_collisions == 0 and strict_entry_offset_ex_ante_ok else "OPEN", "HARD", "Entry-offset-only resolves tested signature collisions; human review required." if entry_offset_collisions == 0 and strict_entry_offset_ex_ante_ok else "Entry-offset-only did not fully resolve collisions."],
        ["B99-004", "representative_profit_binding", "OPEN", "HARD", "Profit representative source remains unresolved."],
        ["B99-005", "CoreB live evaluator", "OPEN", "HARD", "Live remains blocked."],
        ["B99-006", "A002", "CLOSED_FOR_COREB_MAIN_PATH", "INFO", "A002 is auxiliary-only and not used."],
    ], columns=["blocker_id", "component", "status", "severity", "detail"])
    summary = {"created_utc": created, "step": STEP, "status": status, "audit_only": True, "source_recovery_approved": False, "upstream_25c98_ok": upstream_ok, "inputs_present": inputs_ok, "temporal_feature_rows": int(len(rows)), "strict_collision_temporal_rows": int(len(strict)), "entry_offset_signature_collision_groups": entry_offset_collisions, "strict_rows_entry_offset_ex_ante": strict_entry_offset_ex_ante_ok, "strict_rows_with_future_geometry_in_25c98_all_geometry": strict_future_count, "all_rows_with_future_geometry_in_25c98_all_geometry": all_future_count, "coreb_live_evaluator_allowed": False, "final_signal_allowed": False, "a002_used": False, "external_actions": ACTIONS}
    inv.to_csv(out / "25c99_input_inventory.csv", index=False, encoding="utf-8-sig")
    obs.to_csv(out / "25c99_temporal_field_observability.csv", index=False, encoding="utf-8-sig")
    flagged.to_csv(out / "25c99_row_observability_flags.csv", index=False, encoding="utf-8-sig")
    sig.to_csv(out / "25c99_ex_ante_entry_offset_signature_summary.csv", index=False, encoding="utf-8-sig")
    cg.to_csv(out / "25c99_ex_ante_entry_offset_collision_groups.csv", index=False, encoding="utf-8-sig")
    cr.to_csv(out / "25c99_ex_ante_entry_offset_collision_rows.csv", index=False, encoding="utf-8-sig")
    strict_flagged.to_csv(out / "25c99_strict_collision_observability_rows.csv", index=False, encoding="utf-8-sig")
    decision.to_csv(out / "25c99_decision_matrix.csv", index=False, encoding="utf-8-sig")
    blockers.to_csv(out / "25c99_blocker_matrix.csv", index=False, encoding="utf-8-sig")
    write_json(out / "25c99_summary.json", summary)
    report = "\n".join(["# GOLD V2 25C99 temporal geometry observability leakage audit-only report", "", f"Created UTC: {created}", f"Status: `{status}`", "", "## Decision matrix", md(decision), "", "## Temporal field observability", md(obs), "", "## Entry offset signature summary", md(sig), "", "## Strict collision observability rows", md(strict_flagged), "", "## Blockers", md(blockers), "", "## Safety", "- audit_only: true", "- future geometry not promoted", "- entry-offset uniqueness not promoted", "- A002 not used", "- source recovery not approved", "- live evaluator/final signal/external actions remain OFF", "- NO_SIGNAL must not notify Discord"])
    (out / "GOLD_V2_25C99_TEMPORAL_GEOMETRY_OBSERVABILITY_LEAKAGE_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")
    zip_path = fx_outputs() / f"{OUT_NAME}.zip"
    if zip_path.exists(): zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for p in out.iterdir(): z.write(p, arcname=p.name)
    print(json.dumps({"status": status, "output_dir": str(out), "zip": str(zip_path)}, ensure_ascii=False, indent=2, allow_nan=False))
    print("No Discord, MT5, AI API, live hook, live evaluator, or final signal action was performed.")
    return 0 if status.endswith("LIVE_BLOCKED") or status.endswith("AUDIT_ONLY") else 2


if __name__ == "__main__":
    raise SystemExit(main())
