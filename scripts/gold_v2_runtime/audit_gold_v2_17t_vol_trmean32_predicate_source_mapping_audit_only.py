#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

STEP = "17T_VOL_TRMEAN32_PREDICATE_SOURCE_MAPPING_AUDIT_ONLY"
OUT_DIR_NAME = "gold_v2_17t_vol_trmean32_predicate_source_mapping_audit_only"
REPORT_NAME = "GOLD_V2_17T_VOL_TRMEAN32_PREDICATE_SOURCE_MAPPING_AUDIT_ONLY_REPORT.md"
SUCCESS_STATUS = "VOL_TRMEAN32_PREDICATE_SOURCE_MAPPING_READY_AUDIT_ONLY_LIVE_BLOCKED"
STOP_STATUS = "VOL_TRMEAN32_PREDICATE_SOURCE_MAPPING_STOPPED_AUDIT_ONLY"
EXPECTED_17S_STATUS = "RANGE96_PREDICATE_SOURCE_MAPPING_READY_AUDIT_ONLY_LIVE_BLOCKED"
EXPECTED_VOL_ROWS = 140
REQUIRED_COLS = [
    "manifest_row_id",
    "component",
    "source_step",
    "source_identity_type",
    "source_role",
    "source_row_number_1based",
    "source_key",
    "strategy_id",
    "source_row_hash",
    "source_status",
    "live_executable",
    "final_signal_allowed",
]
INPUTS = {
    "summary_17s": ("gold_v2_17s_range96_predicate_source_mapping_audit_only", "gold_v2_17s_range96_predicate_source_mapping_summary.json"),
    "checks_17s": ("gold_v2_17s_range96_predicate_source_mapping_audit_only", "gold_v2_17s_range96_source_mapping_checks.csv"),
    "next_gates_17s": ("gold_v2_17s_range96_predicate_source_mapping_audit_only", "gold_v2_17s_required_next_gates.csv"),
    "safety_17s": ("gold_v2_17s_range96_predicate_source_mapping_audit_only", "gold_v2_17s_safety_matrix.csv"),
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


def bool_value(value: Any) -> bool:
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def clean(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean(v) for v in value]
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, (np.floating, float)):
        return None if math.isnan(float(value)) else float(value)
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass
    return value


def write_json(path: Path, obj: dict[str, Any]) -> None:
    path.write_text(json.dumps(clean(obj), ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")


def write_csv(df: pd.DataFrame, path: Path) -> None:
    df.to_csv(path, index=False, encoding="utf-8-sig")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def markdown_table(df: pd.DataFrame, limit: int = 80) -> str:
    if df.empty:
        return "_No rows._"
    lines = ["| " + " | ".join(map(str, df.columns)) + " |", "| " + " | ".join(["---"] * len(df.columns)) + " |"]
    for _, row in df.head(limit).iterrows():
        lines.append("| " + " | ".join(str(row[c]).replace("|", "\\|").replace("\n", " ") for c in df.columns) + " |")
    return "\n".join(lines)


def input_audit() -> pd.DataFrame:
    rows = []
    for role in INPUTS:
        path = ip(role)
        row = {"role": role, "path": str(path), "required": True, "exists": path.exists()}
        if path.exists():
            row["sha256"] = sha256_file(path)
            row["bytes"] = path.stat().st_size
        rows.append(row)
    return pd.DataFrame(rows)


def add_check(rows: list[list[Any]], cid: str, check: str, observed: Any, expected: Any) -> None:
    rows.append([cid, check, observed, expected, "PASS" if observed == expected else "STOP"])


def stop_missing(out: Path, now: str, audit: pd.DataFrame) -> int:
    missing = audit[audit["required"].eq(True) & ~audit["exists"].eq(True)]
    blockers = pd.DataFrame(
        [["17T-BINPUT", "VOL_TRMEAN32_REFINED", "HARD", "OPEN", "required inputs", "Missing: " + "|".join(missing["role"].astype(str))]],
        columns=["blocker_id", "component", "severity", "status", "blocked_item", "required_resolution"],
    )
    write_csv(blockers, out / "gold_v2_17t_blockers.csv")
    write_json(out / "gold_v2_17t_vol_trmean32_predicate_source_mapping_summary.json", {"created_utc": now, "step": STEP, "status": STOP_STATUS, "audit_only": True, "missing_required_inputs": missing[["role", "path"]].to_dict("records"), "medium_live_evaluator_allowed": False, "final_signal_allowed": False})
    (out / REPORT_NAME).write_text("\n".join(["# GOLD V2 17T VOL_TRMEAN32 predicate source mapping audit-only report", "", f"Created UTC: {now}", f"Status: `{STOP_STATUS}`", "", markdown_table(audit), "", markdown_table(blockers)]), encoding="utf-8")
    print(json.dumps({"status": STOP_STATUS, "output_dir": str(out)}, ensure_ascii=False, indent=2))
    return 2


def main() -> int:
    out = out_dir()
    now = datetime.now(timezone.utc).isoformat()
    audit = input_audit()
    write_csv(audit, out / "gold_v2_17t_input_audit.csv")
    if len(audit[audit["required"].eq(True) & ~audit["exists"].eq(True)]):
        return stop_missing(out, now, audit)

    summary_17s = read_json(ip("summary_17s"))
    checks_17s = read_csv(ip("checks_17s"))
    next_gates_17s = read_csv(ip("next_gates_17s"))
    safety_17s = read_csv(ip("safety_17s"))
    manifest = read_csv(ip("manifest_17g"))
    vol = manifest[manifest.get("component", pd.Series(dtype=str)).astype(str).eq("VOL_TRMEAN32_REFINED")].copy() if "component" in manifest.columns else pd.DataFrame()

    checks: list[list[Any]] = []
    add_check(checks, "17T-C001", "17S status", str(summary_17s.get("status", "")), EXPECTED_17S_STATUS)
    add_check(checks, "17T-C002", "17S RANGE96 mapping ready", bool_value(summary_17s.get("range96_predicate_source_mapping_ready", False)), True)
    add_check(checks, "17T-C003", "17S predicate implementation allowed", bool_value(summary_17s.get("predicate_implementation_allowed", False)), False)
    add_check(checks, "17T-C004", "17S executable parity implemented", bool_value(summary_17s.get("executable_parity_implemented", False)), False)
    add_check(checks, "17T-C005", "17S final signal allowed", bool_value(summary_17s.get("final_signal_allowed", False)), False)
    add_check(checks, "17T-C006", "17S checks STOP rows", int(checks_17s[checks_17s["status"].astype(str).eq("STOP")].shape[0]), 0)
    add_check(checks, "17T-C007", "17S safety STOP rows", int(safety_17s[safety_17s["status"].astype(str).eq("STOP")].shape[0]), 0)
    add_check(checks, "17T-C008", "17S next gates include 17T", bool("17T" in set(next_gates_17s.get("next_step", pd.Series(dtype=str)).astype(str))), True)
    add_check(checks, "17T-C009", "VOL_TRMEAN32_REFINED manifest rows", int(vol.shape[0]), EXPECTED_VOL_ROWS)
    for col in REQUIRED_COLS:
        add_check(checks, f"17T-COL-{col}", f"manifest column {col}", col in manifest.columns, True)
    if not vol.empty:
        add_check(checks, "17T-VOL-LIVE", "VOL live_executable true rows", int(vol["live_executable"].map(bool_value).sum()) if "live_executable" in vol.columns else -1, 0)
        add_check(checks, "17T-VOL-FINAL", "VOL final_signal_allowed true rows", int(vol["final_signal_allowed"].map(bool_value).sum()) if "final_signal_allowed" in vol.columns else -1, 0)

    if not vol.empty:
        vol["vol_trmean32_predicate_source_mapping_status"] = "VOL_TRMEAN32_SOURCE_IDENTITY_OBSERVED_AUDIT_ONLY_NOT_IMPLEMENTED"
        vol["predicate_implementation_allowed"] = False
        vol["medium_live_evaluator_allowed"] = False
        vol["final_signal_allowed"] = False
    requirements = pd.DataFrame([
        ["VOL_TRMEAN32_REFINED", "audited_vol_trmean32_predicate_source_mapping_artifact", EXPECTED_VOL_ROWS, "observed_source_identities_require_future_predicate_mapping", False, False, False],
        ["VOL_TRMEAN32_REFINED", "vol_trmean32_executable_predicate_implementation", EXPECTED_VOL_ROWS, "blocked_not_implemented", False, False, False],
    ], columns=["component", "source_artifact_class", "affected_rows", "requirement_status", "predicate_implementation_allowed", "medium_live_evaluator_allowed", "final_signal_allowed"])
    next_required = pd.DataFrame([
        ["17U", "MEDIUM_FULL_SET_ARBITRATION_PARITY_PLAN_AUDIT_ONLY", "Plan arbitration parity only; no implementation.", True],
        ["17T_IMPL", "VOL_TRMEAN32_EXECUTABLE_PREDICATE_IMPLEMENTATION", "Blocked; source mapping is not implementation.", False],
        ["LIVE", "MEDIUM_FULL_SET_LIVE_EVALUATOR", "Blocked.", False],
    ], columns=["next_step", "name", "purpose", "allowed_after_17t_success"])
    mapping_checks = pd.DataFrame(checks, columns=["check_id", "check", "observed", "expected", "status"])
    safety = pd.DataFrame([
        ["audit_only", True, True, "PASS"],
        ["source_mapping_only", True, True, "PASS"],
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
    ok = mapping_checks[mapping_checks["status"].eq("STOP")].empty and safety[safety["status"].eq("STOP")].empty
    status = SUCCESS_STATUS if ok else STOP_STATUS
    blockers = pd.DataFrame([
        ["17T-B010", "VOL_TRMEAN32_REFINED", "HARD", "OPEN", "predicate implementation", "VOL_TRMEAN32 predicate implementation remains blocked."],
        ["17T-B020", "MEDIUM_FULL_SET", "HARD", "OPEN", "arbitration parity", "Medium full-set arbitration parity planning is still required."],
        ["17T-B099", "SAFETY", "SAFETY", "OPEN", "external actions", "Keep all external actions false. NO_SIGNAL must not notify Discord."],
    ], columns=["blocker_id", "component", "severity", "status", "blocked_item", "required_resolution"])
    write_csv(mapping_checks, out / "gold_v2_17t_vol_trmean32_source_mapping_checks.csv")
    write_csv(vol, out / "gold_v2_17t_vol_trmean32_current_identity_rows.csv")
    write_csv(requirements, out / "gold_v2_17t_vol_trmean32_required_source_artifacts.csv")
    write_csv(next_required, out / "gold_v2_17t_required_next_gates.csv")
    write_csv(blockers, out / "gold_v2_17t_blockers.csv")
    write_csv(safety, out / "gold_v2_17t_safety_matrix.csv")
    summary = {"created_utc": now, "step": STEP, "status": status, "audit_only": True, "vol_trmean32_predicate_source_mapping_ready": ok, "vol_trmean32_manifest_rows": int(vol.shape[0]), "predicate_implementation_allowed": False, "executable_parity_implemented": False, "dry_run_execution_allowed": False, "medium_live_evaluator_allowed": False, "final_signal_allowed": False, "external_actions": {"discord_send_allowed": False, "mt5_order_allowed": False, "ai_api_allowed": False, "live_hook_allowed": False}, "no_signal_discord_notified": False, "next_recommended_step": "17U_MEDIUM_FULL_SET_ARBITRATION_PARITY_PLAN_AUDIT_ONLY" if ok else "STOP_REVIEW_17T_OUTPUTS"}
    write_json(out / "gold_v2_17t_vol_trmean32_predicate_source_mapping_summary.json", summary)
    report = ["# GOLD V2 17T VOL_TRMEAN32 predicate source mapping audit-only report", "", f"Created UTC: {now}", f"Status: `{status}`", "", "## Final decision", "- 17T maps VOL_TRMEAN32 source identities only.", "- It does not implement predicates, evaluate OHLC, create final signals, or enable live/external actions.", "", "## Input audit", markdown_table(audit), "", "## VOL_TRMEAN32 source mapping checks", markdown_table(mapping_checks), "", "## VOL_TRMEAN32 current identity rows", markdown_table(vol), "", "## Required source artifacts", markdown_table(requirements), "", "## Required next gates", markdown_table(next_required), "", "## Blockers", markdown_table(blockers), "", "## Safety", markdown_table(safety)]
    (out / REPORT_NAME).write_text("\n".join(report), encoding="utf-8")
    print(json.dumps(clean({"status": status, "output_dir": str(out), "next_recommended_step": summary["next_recommended_step"]}), ensure_ascii=False, indent=2))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
