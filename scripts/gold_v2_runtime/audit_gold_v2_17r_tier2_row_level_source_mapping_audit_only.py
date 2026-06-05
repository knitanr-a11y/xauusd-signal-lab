#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations
import hashlib, json, math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import numpy as np
import pandas as pd

STEP = "17R_TIER2_ROW_LEVEL_SOURCE_MAPPING_AUDIT_ONLY"
OUT_DIR_NAME = "gold_v2_17r_tier2_row_level_source_mapping_audit_only"
REPORT_NAME = "GOLD_V2_17R_TIER2_ROW_LEVEL_SOURCE_MAPPING_AUDIT_ONLY_REPORT.md"
SUCCESS_STATUS = "TIER2_ROW_LEVEL_SOURCE_MAPPING_GAP_CONFIRMED_AUDIT_ONLY_LIVE_BLOCKED"
STOP_STATUS = "TIER2_ROW_LEVEL_SOURCE_MAPPING_STOPPED_AUDIT_ONLY"
EXPECTED_17Q_STATUS = "MEDIUM_FULL_SET_COMPONENT_PARITY_SOURCE_MAPPING_READY_AUDIT_ONLY_LIVE_BLOCKED"
REQUIRED_COLS = ["manifest_row_id", "component", "source_step", "source_identity_type", "source_key", "source_row_hash", "live_executable", "final_signal_allowed"]
INPUTS = {
    "summary_17q": ("gold_v2_17q_medium_full_set_component_parity_source_mapping_audit_only", "gold_v2_17q_medium_full_set_component_parity_source_mapping_summary.json"),
    "checks_17q": ("gold_v2_17q_medium_full_set_component_parity_source_mapping_audit_only", "gold_v2_17q_source_mapping_checks.csv"),
    "mapping_matrix_17q": ("gold_v2_17q_medium_full_set_component_parity_source_mapping_audit_only", "gold_v2_17q_component_source_mapping_matrix.csv"),
    "requirements_17q": ("gold_v2_17q_medium_full_set_component_parity_source_mapping_audit_only", "gold_v2_17q_source_artifact_requirements.csv"),
    "next_gates_17q": ("gold_v2_17q_medium_full_set_component_parity_source_mapping_audit_only", "gold_v2_17q_required_next_gates.csv"),
    "safety_17q": ("gold_v2_17q_medium_full_set_component_parity_source_mapping_audit_only", "gold_v2_17q_safety_matrix.csv"),
    "manifest_17g": ("gold_v2_17g_medium_full_set_candidate_mapping_audit_only", "gold_v2_17g_full_set_candidate_manifest.csv"),
}


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def fx_outputs() -> Path:
    root = repo_root()
    return (root.parents[1] if len(root.parents) >= 2 else root.parent) / "FX_OUTPUTS"


def out_dir() -> Path:
    p = fx_outputs() / OUT_DIR_NAME
    p.mkdir(parents=True, exist_ok=True)
    return p


def ip(role: str) -> Path:
    folder, name = INPUTS[role]
    return fx_outputs() / folder / name


def b(v: Any) -> bool:
    if isinstance(v, (bool, np.bool_)):
        return bool(v)
    return str(v).strip().lower() in {"true", "1", "yes", "y"}


def clean(v: Any) -> Any:
    if isinstance(v, dict):
        return {str(k): clean(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [clean(x) for x in v]
    if isinstance(v, np.integer):
        return int(v)
    if isinstance(v, (np.floating, float)):
        return None if math.isnan(float(v)) else float(v)
    try:
        if pd.isna(v):
            return None
    except Exception:
        pass
    return v


def wcsv(df: pd.DataFrame, path: Path) -> None:
    df.to_csv(path, index=False, encoding="utf-8-sig")


def wjson(path: Path, obj: dict[str, Any]) -> None:
    path.write_text(json.dumps(clean(obj), ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")


def rjson(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def rcsv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def md(df: pd.DataFrame) -> str:
    if df.empty:
        return "_No rows._"
    lines = ["| " + " | ".join(map(str, df.columns)) + " |", "| " + " | ".join(["---"] * len(df.columns)) + " |"]
    for _, row in df.head(80).iterrows():
        lines.append("| " + " | ".join(str(row[c]).replace("|", "\\|").replace("\n", " ") for c in df.columns) + " |")
    return "\n".join(lines)


def audit_inputs() -> pd.DataFrame:
    rows = []
    for role in INPUTS:
        path = ip(role)
        row = {"role": role, "path": str(path), "required": True, "exists": path.exists()}
        if path.exists():
            row.update({"sha256": sha(path), "bytes": path.stat().st_size})
        rows.append(row)
    return pd.DataFrame(rows)


def chk(rows: list[list[Any]], cid: str, name: str, obs: Any, exp: Any) -> None:
    rows.append([cid, name, obs, exp, "PASS" if obs == exp else "STOP"])


def main() -> int:
    out = out_dir()
    now = datetime.now(timezone.utc).isoformat()
    audit = audit_inputs()
    wcsv(audit, out / "gold_v2_17r_input_audit.csv")
    if len(audit[~audit["exists"].eq(True)]):
        summary = {"created_utc": now, "step": STEP, "status": STOP_STATUS, "audit_only": True, "missing_inputs": audit[~audit["exists"].eq(True)]["role"].tolist()}
        wjson(out / "gold_v2_17r_tier2_row_level_source_mapping_summary.json", summary)
        (out / REPORT_NAME).write_text("\n".join(["# GOLD V2 17R TIER2 row-level source mapping audit-only report", "", f"Created UTC: {now}", f"Status: `{STOP_STATUS}`", "", md(audit)]), encoding="utf-8")
        print(json.dumps(clean(summary), ensure_ascii=False, indent=2))
        return 2

    s17q = rjson(ip("summary_17q"))
    c17q = rcsv(ip("checks_17q"))
    m17q = rcsv(ip("mapping_matrix_17q"))
    req17q = rcsv(ip("requirements_17q"))
    gates17q = rcsv(ip("next_gates_17q"))
    safe17q = rcsv(ip("safety_17q"))
    manifest = rcsv(ip("manifest_17g"))
    tier2 = manifest[manifest.get("component", pd.Series(dtype=str)).astype(str).eq("TIER2_HVT")].copy() if "component" in manifest.columns else pd.DataFrame()
    identity_type = str(tier2["source_identity_type"].iloc[0]) if len(tier2) and "source_identity_type" in tier2.columns else ""
    row_level = "ROW_LEVEL" in identity_type.upper() and "SUMMARY" not in identity_type.upper()
    summary_chain = "SUMMARY" in identity_type.upper() or "13L" in identity_type.upper()
    gap_confirmed = (not row_level) and summary_chain

    rows: list[list[Any]] = []
    chk(rows, "17R-C001", "17Q status", str(s17q.get("status", "")), EXPECTED_17Q_STATUS)
    chk(rows, "17R-C002", "17Q source_mapping_ready", b(s17q.get("source_mapping_ready", False)), True)
    chk(rows, "17R-C003", "17Q predicate_implementation_allowed", b(s17q.get("predicate_implementation_allowed", False)), False)
    chk(rows, "17R-C004", "17Q executable_parity_implemented", b(s17q.get("executable_parity_implemented", False)), False)
    chk(rows, "17R-C005", "17Q final_signal_allowed", b(s17q.get("final_signal_allowed", False)), False)
    chk(rows, "17R-C006", "17Q check STOP rows", int(c17q[c17q["status"].astype(str).eq("STOP")].shape[0]), 0)
    chk(rows, "17R-C007", "17Q safety STOP rows", int(safe17q[safe17q["status"].astype(str).eq("STOP")].shape[0]), 0)
    chk(rows, "17R-C008", "17Q next gates include 17R", bool("17R" in set(gates17q.get("next_step", pd.Series(dtype=str)).astype(str))), True)
    chk(rows, "17R-C009", "TIER2_HVT manifest rows", int(tier2.shape[0]), 1)
    for col in REQUIRED_COLS:
        chk(rows, f"17R-COL-{col}", f"manifest column {col}", col in manifest.columns, True)
    chk(rows, "17R-TIER2-SUMMARY", "summary-chain identity present", summary_chain, True)
    chk(rows, "17R-TIER2-ROWLEVEL", "row-level identity available", row_level, False)
    chk(rows, "17R-TIER2-GAP", "row-level gap confirmed", gap_confirmed, True)
    checks = pd.DataFrame(rows, columns=["check_id", "check", "observed", "expected", "status"])

    if not tier2.empty:
        tier2["tier2_row_level_source_identity_available"] = row_level
        tier2["tier2_source_gap_status"] = "TIER2_ROW_LEVEL_SOURCE_IDENTITY_MISSING_CONFIRMED" if gap_confirmed else "REVIEW_REQUIRED"
        tier2["predicate_implementation_allowed"] = False
        tier2["medium_live_evaluator_allowed"] = False
        tier2["final_signal_allowed"] = False
    requirements = pd.DataFrame([
        ["TIER2_HVT", "current_source_identity_type", identity_type, "observed_current_state", False, False, False],
        ["TIER2_HVT", "audited_tier2_row_level_source_identity_artifact", "required", "missing_confirmed_by_17r", False, False, False],
    ], columns=["component", "source_artifact_class", "value", "requirement_status", "predicate_implementation_allowed", "medium_live_evaluator_allowed", "final_signal_allowed"])
    gates = pd.DataFrame([
        ["17S", "RANGE96_PREDICATE_SOURCE_MAPPING_AUDIT_ONLY", "Map RANGE96 source only; no implementation.", True],
        ["TIER2_FIX", "TIER2_ROW_LEVEL_SOURCE_IDENTITY_ARTIFACT_AUDIT_ONLY", "Still required before TIER2 parity.", False],
        ["LIVE", "MEDIUM_FULL_SET_LIVE_EVALUATOR", "Blocked.", False],
    ], columns=["next_step", "name", "purpose", "allowed_after_17r_success"])
    safety = pd.DataFrame([
        ["audit_only", True, True, "PASS"],
        ["source_mapping_only", True, True, "PASS"],
        ["tier2_row_level_source_identity_available", row_level, False, "PASS" if row_level is False else "STOP"],
        ["predicate_implementation_allowed", False, False, "PASS"],
        ["executable_parity_implemented", False, False, "PASS"],
        ["dry_run_execution_allowed", False, False, "PASS"],
        ["medium_live_evaluator_allowed", False, False, "PASS"],
        ["final_signal_allowed", False, False, "PASS"],
        ["discord_send_allowed", False, False, "PASS"],
        ["mt5_order_allowed", False, False, "PASS"],
        ["ai_api_allowed", False, False, "PASS"],
        ["live_hook_allowed", False, False, "PASS"],
        ["no_signal_discord_notified", False, False, "PASS"],
    ], columns=["safety_item", "observed", "expected", "status"])
    ok = checks[checks["status"].eq("STOP")].empty and safety[safety["status"].eq("STOP")].empty
    status = SUCCESS_STATUS if ok else STOP_STATUS
    blockers = pd.DataFrame([
        ["17R-B010", "TIER2_HVT", "HARD", "OPEN", "row-level source identity", "Audited row-level source identity is still required before parity."],
        ["17R-B020", "MEDIUM_FULL_SET", "HARD", "OPEN", "predicate implementation", "Still blocked."],
        ["17R-B099", "SAFETY", "SAFETY", "OPEN", "external actions", "Keep all external actions false. NO_SIGNAL must not notify Discord."],
    ], columns=["blocker_id", "component", "severity", "status", "blocked_item", "required_resolution"])
    wcsv(checks, out / "gold_v2_17r_tier2_source_mapping_checks.csv")
    wcsv(tier2, out / "gold_v2_17r_tier2_current_identity_rows.csv")
    wcsv(requirements, out / "gold_v2_17r_tier2_required_source_artifacts.csv")
    wcsv(gates, out / "gold_v2_17r_required_next_gates.csv")
    wcsv(blockers, out / "gold_v2_17r_blockers.csv")
    wcsv(safety, out / "gold_v2_17r_safety_matrix.csv")
    summary = {"created_utc": now, "step": STEP, "status": status, "audit_only": True, "tier2_row_level_source_mapping_gap_confirmed": ok and gap_confirmed, "tier2_manifest_rows": int(tier2.shape[0]), "tier2_source_identity_type": identity_type, "tier2_row_level_source_identity_available": row_level, "tier2_summary_chain_reference_present": summary_chain, "predicate_implementation_allowed": False, "executable_parity_implemented": False, "dry_run_execution_allowed": False, "medium_live_evaluator_allowed": False, "final_signal_allowed": False, "external_actions": {"discord_send_allowed": False, "mt5_order_allowed": False, "ai_api_allowed": False, "live_hook_allowed": False}, "no_signal_discord_notified": False, "next_recommended_step": "17S_RANGE96_PREDICATE_SOURCE_MAPPING_AUDIT_ONLY" if ok else "STOP_REVIEW_17R_OUTPUTS"}
    wjson(out / "gold_v2_17r_tier2_row_level_source_mapping_summary.json", summary)
    report = ["# GOLD V2 17R TIER2 row-level source mapping audit-only report", "", f"Created UTC: {now}", f"Status: `{status}`", "", "## Final decision", "- 17R audits TIER2 source identity only.", "- Current TIER2 row-level availability is recorded without implementing predicates or final/live paths.", "", "## Input audit", md(audit), "", "## TIER2 source mapping checks", md(checks), "", "## TIER2 current identity rows", md(tier2), "", "## Required source artifacts", md(requirements), "", "## Required next gates", md(gates), "", "## Blockers", md(blockers), "", "## Safety", md(safety), "", "## 17Q mapping carry-forward", md(m17q), "", "## 17Q source requirements carry-forward", md(req17q)]
    (out / REPORT_NAME).write_text("\n".join(report), encoding="utf-8")
    print(json.dumps(clean({"status": status, "output_dir": str(out), "next_recommended_step": summary["next_recommended_step"]}), ensure_ascii=False, indent=2))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
