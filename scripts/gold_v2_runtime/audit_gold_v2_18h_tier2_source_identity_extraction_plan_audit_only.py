#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

STEP = "18H_TIER2_SOURCE_IDENTITY_EXTRACTION_PLAN_AUDIT_ONLY"
OUT_DIR = "gold_v2_18h_tier2_source_identity_extraction_plan_audit_only"
REPORT = "GOLD_V2_18H_TIER2_ROW_LEVEL_SOURCE_IDENTITY_EXTRACTION_PLAN_AUDIT_ONLY_REPORT.md"
SUCCESS = "TIER2_ROW_LEVEL_SOURCE_IDENTITY_EXTRACTION_PLAN_READY_AUDIT_ONLY_SOURCE_RECOVERY_BLOCKED"
EXPECTED_18G = "TIER2_SOURCE_ARTIFACT_CONTENT_INSPECTION_EXECUTED_AUDIT_ONLY_SOURCE_RECOVERY_BLOCKED"
IN_DIR = "gold_v2_18g_tier2_source_artifact_content_inspection_execution_audit_only"
REQ_FIELDS = ["manifest_row_id", "component", "source_identity_type", "source_role", "source_row_number_1based", "source_key", "source_row_hash", "strategy_id", "source_status"]
CANDIDATE_MAP = {
    "manifest_row_id": ["tier2_key", "own_manifest_match", "entry_time", "direction", "strategy_id"],
    "component": ["component", "component_desc"],
    "source_identity_type": ["reconciliation_frame_role", "final_status", "own_manifest_match_label"],
    "source_role": ["reconciliation_frame_role", "dataset", "dataset_final"],
    "source_row_number_1based": ["cluster_id", "top_candidate_id", "entry_time", "tier2_key"],
    "source_key": ["tier2_key", "entry_time", "direction", "strategy_id", "cluster_id"],
    "source_row_hash": ["tier2_key", "entry_time", "direction", "strategy_id", "cluster_id", "top_candidate_id"],
    "strategy_id": ["strategy_id"],
    "source_status": ["final_status", "outcome", "own_manifest_match_label"],
}


def root() -> Path:
    return Path(__file__).resolve().parents[2]


def fx() -> Path:
    r = root()
    return (r.parents[1] if len(r.parents) >= 2 else r.parent) / "FX_OUTPUTS"


def lp(path: Path) -> Path:
    p = path if path.is_absolute() else path.resolve()
    if os.name != "nt":
        return p
    s = str(p)
    if s.startswith("\\\\?\\"):
        return Path(s)
    if s.startswith("\\\\"):
        return Path("\\\\?\\UNC\\" + s[2:])
    return Path("\\\\?\\" + s)


def ensure(path: Path) -> None:
    lp(path.parent).mkdir(parents=True, exist_ok=True)


def wcsv(df: pd.DataFrame, path: Path) -> None:
    ensure(path)
    df.to_csv(lp(path), index=False, encoding="utf-8-sig")


def wtxt(path: Path, txt: str) -> None:
    ensure(path)
    lp(path).write_text(txt, encoding="utf-8")


def wjson(path: Path, obj: dict[str, Any]) -> None:
    wtxt(path, json.dumps(obj, ensure_ascii=False, indent=2))


def rjson(path: Path) -> dict[str, Any]:
    return json.loads(lp(path).read_text(encoding="utf-8"))


def rcsv(path: Path) -> pd.DataFrame:
    for enc in ("utf-8-sig", "utf-8", "cp932"):
        try:
            return pd.read_csv(lp(path), encoding=enc)
        except Exception:
            pass
    return pd.read_csv(lp(path))


def mdtable(df: pd.DataFrame, limit: int = 80) -> str:
    if df.empty:
        return "_No rows._"
    cols = list(df.columns)
    rows = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for _, r in df.head(limit).iterrows():
        rows.append("| " + " | ".join(str(r[c]).replace("|", "\\|").replace("\n", " ") for c in cols) + " |")
    return "\n".join(rows)


def norm(v: Any) -> str:
    return str(v).strip().lower().replace("-", "_").replace(" ", "_")


def split_cols(v: Any) -> list[str]:
    if pd.isna(v):
        return []
    return [c for c in str(v).split(";") if c]


def main() -> int:
    base = fx() / IN_DIR
    out = fx() / OUT_DIR
    lp(out).mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()
    inputs = {
        "summary_18g": base / "gold_v2_18g_tier2_source_artifact_content_inspection_execution_summary.json",
        "checks_18g": base / "gold_v2_18g_content_inspection_checks.csv",
        "artifacts_18g": base / "gold_v2_18g_inspected_artifact_results.csv",
        "field_presence_18g": base / "gold_v2_18g_required_identity_field_presence.csv",
        "next_gates_18g": base / "gold_v2_18g_required_next_gates.csv",
        "blockers_18g": base / "gold_v2_18g_blockers.csv",
        "safety_18g": base / "gold_v2_18g_safety_matrix.csv",
    }
    audit = pd.DataFrame([{"role": k, "path": str(v), "required": True, "exists": lp(v).exists()} for k, v in inputs.items()])
    wcsv(audit, out / "gold_v2_18h_input_audit.csv")
    if not audit["exists"].all():
        summary = {"created_utc": now, "step": STEP, "status": "18H_STOP_MISSING_INPUTS", "audit_only": True, "source_recovery_executed": False}
        wjson(out / "gold_v2_18h_tier2_source_identity_extraction_plan_summary.json", summary)
        return 2
    summary18g = rjson(inputs["summary_18g"])
    checks18g = rcsv(inputs["checks_18g"])
    artifacts = rcsv(inputs["artifacts_18g"])
    presence = rcsv(inputs["field_presence_18g"])
    blockers = rcsv(inputs["blockers_18g"])
    safety18g = rcsv(inputs["safety_18g"])
    checks = []
    checks.append(["18H-C001", "18G status", summary18g.get("status"), EXPECTED_18G, "PASS" if summary18g.get("status") == EXPECTED_18G else "STOP"])
    checks.append(["18H-C002", "18G checks STOP rows", int((checks18g["status"].astype(str) == "STOP").sum()), 0, "PASS" if int((checks18g["status"].astype(str) == "STOP").sum()) == 0 else "STOP"])
    checks.append(["18H-C003", "18G safety STOP rows", int((safety18g["status"].astype(str) == "STOP").sum()), 0, "PASS" if int((safety18g["status"].astype(str) == "STOP").sum()) == 0 else "STOP"])
    checks.append(["18H-C004", "18G source recovery executed", bool(summary18g.get("source_recovery_executed", False)), False, "PASS" if not bool(summary18g.get("source_recovery_executed", False)) else "STOP"])
    plan_rows = []
    ranking_rows = []
    for _, a in artifacts.iterrows():
        rel = str(a.get("relative_path", ""))
        cols = split_cols(a.get("columns", ""))
        colset = {norm(c) for c in cols}
        present_count = 0
        derivable_count = 0
        missing_count = 0
        for field in REQ_FIELDS:
            candidates = CANDIDATE_MAP[field]
            direct = field in colset
            usable = [c for c in candidates if norm(c) in colset]
            if direct:
                status = "DIRECT_COLUMN_PRESENT"
                present_count += 1
            elif usable:
                status = "DERIVATION_CANDIDATE_COLUMNS_PRESENT"
                derivable_count += 1
            else:
                status = "MISSING_NO_SCHEMA_CANDIDATE"
                missing_count += 1
            plan_rows.append({"relative_path": rel, "filename": a.get("filename", ""), "field": field, "mapping_status": status, "direct_column": field if direct else "", "candidate_columns_present": ";".join(usable), "source_recovery_executed": False, "implementation_allowed": False, "final_signal_allowed": False})
        ranking_rows.append({"relative_path": rel, "filename": a.get("filename", ""), "inspection_status": a.get("inspection_status", ""), "row_count": a.get("row_count", ""), "column_count": a.get("column_count", ""), "direct_required_fields": present_count, "derivable_required_fields": derivable_count, "missing_required_fields": missing_count, "recommended_priority": (missing_count, -present_count, -derivable_count), "source_recovery_executed": False})
    mapping = pd.DataFrame(plan_rows)
    ranking = pd.DataFrame(ranking_rows).sort_values(["missing_required_fields", "direct_required_fields", "derivable_required_fields"], ascending=[True, False, False])
    missing = mapping[mapping["mapping_status"].eq("MISSING_NO_SCHEMA_CANDIDATE")].copy()
    nextg = pd.DataFrame([
        ["18I", "TIER2_ROW_LEVEL_SOURCE_IDENTITY_EXTRACTION_DRY_RUN_DESIGN_AUDIT_ONLY", "Design a dry-run extraction using only mapped columns; no recovery execution.", True],
        ["SOURCE_RECOVERY", "TIER2_SOURCE_IDENTITY_RECOVERY_EXECUTION", "Blocked after 18H.", False],
        ["LIVE", "MEDIUM_FULL_SET_LIVE_EVALUATOR", "Blocked.", False],
    ], columns=["next_step", "name", "purpose", "allowed_after_18h_success"])
    blockers = blockers.copy()
    blockers["carried_forward_by"] = STEP
    blockers["source_recovery_executed"] = False
    blockers["implementation_allowed"] = False
    blockers["live_or_final_allowed"] = False
    safety = pd.DataFrame([
        ["audit_only", True, True, "PASS"],
        ["extraction_plan_only", True, True, "PASS"],
        ["source_recovery_executed", False, False, "PASS"],
        ["implementation_allowed", False, False, "PASS"],
        ["oh_lc_replay_allowed", False, False, "PASS"],
        ["live_enabled", False, False, "PASS"],
        ["final_signal_allowed", False, False, "PASS"],
        ["discord_send_allowed", False, False, "PASS"],
        ["mt5_order_allowed", False, False, "PASS"],
        ["ai_api_allowed", False, False, "PASS"],
        ["live_hook_allowed", False, False, "PASS"],
        ["no_signal_discord_notified", False, False, "PASS"],
    ], columns=["safety_item", "observed", "expected", "status"])
    checkdf = pd.DataFrame(checks, columns=["check_id", "check", "observed", "expected", "status"])
    ok = int((checkdf["status"].astype(str) == "STOP").sum()) == 0
    status = SUCCESS if ok else "18H_STOP_REVIEW_OUTPUTS"
    for name, df in [
        ("gold_v2_18h_plan_checks.csv", checkdf),
        ("gold_v2_18h_identity_field_mapping_plan.csv", mapping),
        ("gold_v2_18h_candidate_artifact_ranking.csv", ranking),
        ("gold_v2_18h_missing_required_fields.csv", missing),
        ("gold_v2_18h_required_next_gates.csv", nextg),
        ("gold_v2_18h_blockers.csv", blockers),
        ("gold_v2_18h_safety_matrix.csv", safety),
    ]:
        wcsv(df, out / name)
    summary = {"created_utc": now, "step": STEP, "status": status, "audit_only": True, "extraction_plan_ready": ok, "mapping_rows": int(len(mapping)), "candidate_artifacts": int(len(ranking)), "missing_required_field_rows": int(len(missing)), "source_recovery_executed": False, "implementation_allowed": False, "oh_lc_replay_allowed": False, "live_enabled": False, "final_signal_allowed": False, "external_actions": {"discord_send_allowed": False, "mt5_order_allowed": False, "ai_api_allowed": False, "live_hook_allowed": False}, "no_signal_discord_notified": False, "next_recommended_step": "18I_TIER2_ROW_LEVEL_SOURCE_IDENTITY_EXTRACTION_DRY_RUN_DESIGN_AUDIT_ONLY" if ok else "STOP_REVIEW_18H_OUTPUTS"}
    wjson(out / "gold_v2_18h_tier2_source_identity_extraction_plan_summary.json", summary)
    report = ["# GOLD V2 18H TIER2 row-level source identity extraction plan audit-only report", "", f"Created UTC: {now}", f"Status: `{status}`", "", "## Final decision", "- 18H created an extraction plan only.", "- It did not recover source identity, compute row hashes, reconstruct from OHLC, implement predicates/arbitration, run replay, enable live/final, or enable external actions.", "", "## Checks", mdtable(checkdf), "", "## Candidate artifact ranking", mdtable(ranking), "", "## Identity field mapping plan", mdtable(mapping), "", "## Missing required fields", mdtable(missing), "", "## Next gates", mdtable(nextg), "", "## Blockers", mdtable(blockers), "", "## Safety", mdtable(safety)]
    wtxt(out / REPORT, "\n".join(report))
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
