#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

STEP = "24F_SOURCE_RECOVERY_ARTIFACT_LIST_REVIEW_AUDIT_ONLY"
OUT_DIR = "gold_v2_24f_source_recovery_artifact_list_review_audit_only"
IN24E = "gold_v2_24e_source_recovery_artifact_list_intake_audit_only"
EXPECTED_24E_STATUS = "SOURCE_RECOVERY_ARTIFACT_LIST_INTAKE_VALIDATED_AUDIT_ONLY_SOURCE_RECOVERY_EXECUTION_STILL_BLOCKED"
PASS_STATUS = "SOURCE_RECOVERY_ARTIFACT_LIST_REVIEW_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_EXECUTION_STILL_BLOCKED"
REQUEST_MORE_STATUS = "SOURCE_RECOVERY_ARTIFACT_LIST_REVIEW_REQUEST_MORE_EVIDENCE_AUDIT_ONLY_SOURCE_RECOVERY_EXECUTION_STILL_BLOCKED"
STOP_STATUS = "24F_STOP_SOURCE_RECOVERY_ARTIFACT_LIST_REVIEW_INPUTS_OR_SAFETY"

REPORT_FILE = "GOLD_V2_24F_SOURCE_RECOVERY_ARTIFACT_LIST_REVIEW_AUDIT_ONLY_REPORT.md"
SUMMARY_FILE = "gold_v2_24f_source_recovery_artifact_list_review_summary.json"
INPUT_AUDIT_FILE = "gold_v2_24f_input_audit.csv"
REFERENCE_REVIEW_FILE = "gold_v2_24f_artifact_reference_review.csv"
CONTENT_CHECKS_FILE = "gold_v2_24f_artifact_content_review_checks.csv"
INTEGRATED_CHECKS_FILE = "gold_v2_24f_integrated_checks.csv"
REQUIRED_NEXT_GATES_FILE = "gold_v2_24f_required_next_gates.csv"
SAFETY_MATRIX_FILE = "gold_v2_24f_safety_matrix.csv"

REQUIRED_24E_FILES = {
    "24e_report": "GOLD_V2_24E_SOURCE_RECOVERY_ARTIFACT_LIST_INTAKE_AUDIT_ONLY_REPORT.md",
    "24e_summary": "gold_v2_24e_source_recovery_artifact_list_intake_summary.json",
    "24e_input_audit": "gold_v2_24e_input_audit.csv",
    "24e_artifact_list_input": "gold_v2_24e_artifact_list_input.csv",
    "24e_artifact_list_intake_result": "gold_v2_24e_artifact_list_intake_result.csv",
    "24e_integrated_checks": "gold_v2_24e_integrated_checks.csv",
    "24e_required_next_gates": "gold_v2_24e_required_next_gates.csv",
    "24e_safety_matrix": "gold_v2_24e_safety_matrix.csv",
}
EXPECTED_CATEGORIES = ["source_identity_lineage_docs", "candidate_source_files", "old_gold_disc8_quarantine_evidence"]
FORBIDDEN_GATES = {"SOURCE_IDENTITY_FINALIZATION", "SOURCE_RECOVERY", "LIVE", "FINAL_SIGNAL", "DISCORD_SEND", "MT5_ORDER", "AI_API", "LIVE_HOOK"}
EXPECTED_STILL_BLOCKED = ["SOURCE_IDENTITY_FINALIZATION", "SOURCE_RECOVERY", "LIVE", "FINAL_SIGNAL", "DISCORD_SEND", "MT5_ORDER", "AI_API", "LIVE_HOOK"]
FALSE_SUMMARY_FLAGS = [
    "source_recovery_approved", "source_recovery_executed", "source_identity_finalized", "source_identity_recovered",
    "ledger_is_source_of_truth", "live_or_final_implementation_allowed", "oh_lc_replay_allowed", "live_enabled",
    "final_signal_allowed", "no_signal_discord_notified", "ai_api_called", "discord_sent", "mt5_order_sent",
    "live_hook_enabled", "source_recovery_execution_performed", "source_recovery_approval_granted", "source_identity_finalization_performed",
]
EXTERNAL_ACTION_KEYS = ["discord_send_allowed", "mt5_order_allowed", "ai_api_allowed", "live_hook_allowed"]
EXTERNAL_ACTIONS = {"discord_send_allowed": False, "mt5_order_allowed": False, "ai_api_allowed": False, "live_hook_allowed": False}


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def files_root() -> Path:
    root = repo_root()
    return root.parents[1] if len(root.parents) >= 2 else root.parent


def fx_outputs_root() -> Path:
    return files_root() / "FX_OUTPUTS"


def long_path(path: Path) -> Path:
    path = path if path.is_absolute() else path.resolve()
    if os.name != "nt":
        return path
    raw = str(path)
    if raw.startswith("\\\\?\\"):
        return Path(raw)
    if raw.startswith("\\\\"):
        return Path("\\\\?\\UNC\\" + raw[2:])
    return Path("\\\\?\\" + raw)


def truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return bool(value)
    return str(value).strip().lower() in {"1", "true", "yes", "y", "allowed", "pass", "ready"}


def falsey(value: Any) -> bool:
    if isinstance(value, bool):
        return not value
    if value is None:
        return True
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return not bool(value)
    return str(value).strip().lower() in {"", "0", "false", "no", "n", "blocked", "none", "null"}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with long_path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_text(path: Path, text: str) -> None:
    long_path(path.parent).mkdir(parents=True, exist_ok=True)
    long_path(path).write_text(text, encoding="utf-8")


def write_json(path: Path, obj: dict[str, Any]) -> None:
    write_text(path, json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False))


def write_csv(path: Path, df: pd.DataFrame) -> None:
    long_path(path.parent).mkdir(parents=True, exist_ok=True)
    df.to_csv(long_path(path), index=False, encoding="utf-8-sig")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(long_path(path).read_text(encoding="utf-8"))


def read_csv(path: Path) -> pd.DataFrame:
    last: Exception | None = None
    for enc in ("utf-8-sig", "utf-8", "cp932"):
        try:
            return pd.read_csv(long_path(path), encoding=enc, keep_default_na=False)
        except Exception as exc:
            last = exc
    raise RuntimeError(f"CSV read failed: {path}: {last}")


def stop_rows(df: pd.DataFrame) -> int:
    return 0 if df.empty or "status" not in df.columns else int((df["status"].astype(str).str.upper() == "STOP").sum())


def md_table(df: pd.DataFrame, limit: int = 120) -> str:
    if df.empty:
        return "_No rows._"
    view = df.head(limit).copy()
    cols = list(view.columns)
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for _, row in view.iterrows():
        lines.append("| " + " | ".join(str(row[c]).replace("|", "\\|").replace("\n", " ") for c in cols) + " |")
    return "\n".join(lines)


def check_row(cid: str, check: str, observed: Any, expected: Any, ok: bool) -> dict[str, Any]:
    return {"check_id": cid, "check": check, "observed": observed, "expected": expected, "status": "PASS" if ok else "STOP"}


def get_external(summary: dict[str, Any], key: str) -> Any:
    ext = summary.get("external_actions", {})
    return ext.get(key, False) if isinstance(ext, dict) else False


def count_true_forbidden_summary_flags(summary: dict[str, Any]) -> int:
    return int(sum(1 for k in FALSE_SUMMARY_FLAGS if truthy(summary.get(k, False))) + sum(1 for k in EXTERNAL_ACTION_KEYS if truthy(get_external(summary, k))))


def allowed_next_steps(gates: pd.DataFrame, col: str) -> list[str]:
    if gates.empty or "next_step" not in gates.columns or col not in gates.columns:
        return []
    return gates.loc[gates[col].map(truthy), "next_step"].astype(str).tolist()


def forbidden_allowed_detail(gates: pd.DataFrame, col: str) -> str:
    if gates.empty or "next_step" not in gates.columns or col not in gates.columns:
        return "missing next_step/allowed column"
    sub = gates[gates["next_step"].astype(str).isin(FORBIDDEN_GATES)]
    if sub.empty:
        return "no forbidden gate rows found"
    allowed = sub[sub[col].map(truthy)]
    return "all forbidden gates blocked" if allowed.empty else ",".join(allowed["next_step"].astype(str).tolist())


def build_input_audit(paths: dict[str, Path]) -> pd.DataFrame:
    rows = []
    for role, path in paths.items():
        rows.append({"role": role, "path": str(path), "required": True, "exists": long_path(path).exists(), "source_of_truth_role": "24E hardened validated output", "notes": "24F reviews this artifact only; no source recovery/live/AI/external execution."})
    return pd.DataFrame(rows)


def read_text_sample(path: Path, max_bytes: int = 2_000_000) -> str:
    try:
        return long_path(path).read_bytes()[:max_bytes].decode("utf-8", errors="ignore")
    except Exception:
        return ""


def content_keywords_for(category: str) -> list[str]:
    if category == "source_identity_lineage_docs":
        return ["source identity", "source_row_hash", "source rows", "dry-run", "audit-only", "tier2"]
    if category == "old_gold_disc8_quarantine_evidence":
        return ["old gold", "disc8", "quarantine", "htf", "open-time", "confirmed", "source of truth"]
    return []


def review_artifact_content(row: pd.Series) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    category = str(row.get("artifact_category", ""))
    resolved = Path(str(row.get("resolved_artifact_path", "")))
    result = {
        "intake_id": row.get("intake_id", ""),
        "artifact_category": category,
        "resolved_artifact_path": str(resolved),
        "artifact_review_status": "REVIEW_NOT_STARTED",
        "csv_rows": "",
        "csv_columns": "",
        "keyword_hits": "",
        "review_notes": "",
    }
    checks: list[dict[str, Any]] = []
    exists = long_path(resolved).exists() and long_path(resolved).is_file()
    checks.append(check_row(f"24F-ART-{row.get('intake_id','')}-EXISTS", f"{category} artifact exists", exists, True, exists))
    if not exists:
        result["artifact_review_status"] = "MISSING_ARTIFACT"
        return checks, result
    suffix = resolved.suffix.lower()
    if category == "candidate_source_files":
        if suffix == ".csv":
            try:
                df = read_csv(resolved)
                result["csv_rows"] = int(len(df))
                result["csv_columns"] = int(len(df.columns))
                has_rows = len(df) > 0
                expected_cols = [c for c in ["entry_time", "direction", "strategy_id", "tier2_key", "cluster_id", "top_candidate_id", "source_row_hash"] if c in df.columns]
                checks.append(check_row(f"24F-ART-{row.get('intake_id','')}-CSV-ROWS", "candidate source CSV has rows", len(df), ">0", has_rows))
                checks.append(check_row(f"24F-ART-{row.get('intake_id','')}-CSV-COLS", "candidate source CSV has source-identity relevant columns", ";".join(expected_cols), "one or more expected columns", len(expected_cols) > 0))
                result["keyword_hits"] = ";".join(expected_cols)
                result["artifact_review_status"] = "REVIEWABLE_CANDIDATE_SOURCE_FILE" if has_rows and len(expected_cols) > 0 else "REQUEST_MORE_EVIDENCE_CANDIDATE_SOURCE_FILE"
                result["review_notes"] = "CSV source rows reviewed for non-empty row count and source-identity relevant columns."
            except Exception as exc:
                checks.append(check_row(f"24F-ART-{row.get('intake_id','')}-CSV-READ", "candidate source CSV readable", str(exc), "readable", False))
                result["artifact_review_status"] = "REQUEST_MORE_EVIDENCE_CSV_READ_FAILED"
                result["review_notes"] = str(exc)
        else:
            checks.append(check_row(f"24F-ART-{row.get('intake_id','')}-SOURCE-FILE-TYPE", "candidate source artifact file type", suffix, ".csv preferred", suffix in {".csv", ".json", ".jsonl", ".parquet"}))
            result["artifact_review_status"] = "REVIEWABLE_CANDIDATE_SOURCE_FILE" if suffix in {".csv", ".json", ".jsonl", ".parquet"} else "REQUEST_MORE_EVIDENCE_UNEXPECTED_SOURCE_FILE_TYPE"
            result["review_notes"] = "Non-CSV source artifact accepted only as reviewable reference, not executable recovery."
    else:
        text = read_text_sample(resolved)
        lower = text.lower()
        hits = [k for k in content_keywords_for(category) if k.lower() in lower]
        checks.append(check_row(f"24F-ART-{row.get('intake_id','')}-KEYWORDS", f"{category} content keyword hits", ";".join(hits), "category-specific evidence terms", len(hits) >= 2))
        result["keyword_hits"] = ";".join(hits)
        result["artifact_review_status"] = "REVIEWABLE_DOCUMENT_ARTIFACT" if len(hits) >= 2 else "REQUEST_MORE_EVIDENCE_DOCUMENT_KEYWORDS_WEAK"
        result["review_notes"] = "Document reviewed for category-specific evidence terms only; semantic final acceptance remains later audit work."
    return checks, result


def build_required_next_gates(ok: bool, artifact_review_passed: bool) -> pd.DataFrame:
    allow_24g = bool(ok and artifact_review_passed)
    return pd.DataFrame([
        {"next_step": "24G_SOURCE_RECOVERY_EXECUTION_DECISION_OPTIONS_AUDIT_ONLY", "name": "Prepare decision options", "purpose": "Prepare explicit decision options for later human review. Does not execute recovery.", "allowed_after_24f_success": allow_24g, "required_human_decision_value_later": "NONE_FOR_24G_OPTIONS", "still_blocked_reason": "" if allow_24g else "Artifact list review did not fully pass."},
        {"next_step": "REQUEST_MORE_EVIDENCE", "name": "Request more evidence", "purpose": "Ask for better existing artifacts without executing recovery.", "allowed_after_24f_success": bool(ok and not artifact_review_passed), "required_human_decision_value_later": "NONE", "still_blocked_reason": "" if ok and not artifact_review_passed else "Not needed if artifact review passed or 24F failed."},
        {"next_step": "SOURCE_RECOVERY", "name": "Execute source recovery", "purpose": "Would run recovery actions rather than audit-only review.", "allowed_after_24f_success": False, "required_human_decision_value_later": "APPROVE_SOURCE_RECOVERY_EXECUTION", "still_blocked_reason": "24F is review only and does not grant recovery approval."},
        {"next_step": "SOURCE_IDENTITY_FINALIZATION", "name": "Finalize source identity", "purpose": "Would finalize source identity.", "allowed_after_24f_success": False, "required_human_decision_value_later": "APPROVE_SOURCE_IDENTITY_FINALIZATION", "still_blocked_reason": "24F does not grant finalization approval."},
        {"next_step": "LIVE", "name": "Enable live evaluator/use", "purpose": "Would create or enable live behavior.", "allowed_after_24f_success": False, "required_human_decision_value_later": "APPROVE_LIVE_EVALUATOR_IMPLEMENTATION", "still_blocked_reason": "GOLD V2 remains audit-only."},
        {"next_step": "FINAL_SIGNAL", "name": "Enable final signal", "purpose": "Would produce final signal behavior.", "allowed_after_24f_success": False, "required_human_decision_value_later": "APPROVE_FINAL_SIGNAL", "still_blocked_reason": "Final signal remains blocked."},
        {"next_step": "DISCORD_SEND", "name": "Send Discord notification", "purpose": "Would send externally.", "allowed_after_24f_success": False, "required_human_decision_value_later": "APPROVE_DISCORD_SEND", "still_blocked_reason": "Discord remains blocked; NO_SIGNAL must not notify."},
        {"next_step": "MT5_ORDER", "name": "Place MT5 order", "purpose": "Would place order.", "allowed_after_24f_success": False, "required_human_decision_value_later": "APPROVE_MT5_ORDER", "still_blocked_reason": "MT5 remains blocked."},
        {"next_step": "AI_API", "name": "Call AI API", "purpose": "Would call external AI API.", "allowed_after_24f_success": False, "required_human_decision_value_later": "APPROVE_AI_API_REVIEW", "still_blocked_reason": "AI API remains blocked."},
        {"next_step": "LIVE_HOOK", "name": "Enable live hook", "purpose": "Would enable live hook.", "allowed_after_24f_success": False, "required_human_decision_value_later": "APPROVE_LIVE_HOOK", "still_blocked_reason": "Live hook remains blocked."},
    ])


def build_safety_matrix(summary24e: dict[str, Any], ok: bool, artifact_review_passed: bool) -> pd.DataFrame:
    rows = []
    def add(item: str, obs: Any, exp: Any, passed: bool, notes: str) -> None:
        rows.append({"safety_item": item, "observed": obs, "expected": exp, "status": "PASS" if passed else "STOP", "notes": notes})
    add("audit_only", True, True, True, "24F writes audit artifacts only.")
    add("artifact_list_review_only", True, True, True, "24F reviews references only and never executes recovery.")
    add("artifact_review_passed", artifact_review_passed, True, True, "If false, request more evidence rather than STOP when upstream is safe.")
    for key in ["source_recovery_approved", "source_recovery_executed", "source_identity_finalized", "source_identity_recovered", "live_or_final_implementation_allowed", "live_enabled", "final_signal_allowed", "no_signal_discord_notified"]:
        obs = summary24e.get(key, False)
        add(key, obs, False, falsey(obs), "Forbidden summary flag must remain false.")
    for key in EXTERNAL_ACTION_KEYS:
        obs = get_external(summary24e, key)
        add(key, obs, False, falsey(obs), "External action must remain disabled.")
    add("old_gold_disc8_quarantined", True, True, True, "Old GOLD/DISC8 remain quarantined by policy.")
    add("source_recovery_execution_performed", False, False, True, "24F never executes source recovery.")
    add("source_recovery_approval_granted", False, False, True, "24F never grants source recovery approval.")
    add("source_identity_finalization_performed", False, False, True, "24F never finalizes source identity.")
    add("ai_api_called", False, False, True, "24F never calls AI API.")
    add("discord_sent", False, False, True, "24F never sends Discord.")
    add("mt5_order_sent", False, False, True, "24F never sends MT5 order.")
    add("live_hook_enabled", False, False, True, "24F never enables live hook.")
    add("overall_24f_inputs_safe", ok, True, bool(ok), "Upstream and 24F safety must pass.")
    return pd.DataFrame(rows)


def build_report(summary: dict[str, Any], input_audit: pd.DataFrame, checks: pd.DataFrame, reference_review: pd.DataFrame, content_checks: pd.DataFrame, gates: pd.DataFrame, safety: pd.DataFrame) -> str:
    return "\n".join([
        "# GOLD V2 24F source recovery artifact list review audit-only report", "", f"Created UTC: {summary['created_utc']}", f"Step: `{STEP}`", f"Status: `{summary['status']}`", "",
        "## Boundary", "", "- 24F is audit-only.", "- 24F reviews 24E hash-verified artifact references.", "- 24F does not approve or execute source recovery.", "- Source identity finalization/recovery, live evaluator, final signal, Discord, MT5, AI API, and live hook remain blocked.", "- Old GOLD/DISC8 remain quarantined.", "",
        "## Outcome", "", f"- Total STOP rows: `{summary['total_stop_rows']}`", f"- Artifact review passed: `{summary['artifact_review_passed']}`", f"- Reviewable artifact rows: `{summary['reviewable_artifact_rows']}` / 3", f"- Next recommended step: `{summary['next_recommended_step']}`", "",
        "## Input audit", "", md_table(input_audit), "", "## Integrated checks", "", md_table(checks), "", "## Artifact reference review", "", md_table(reference_review), "", "## Artifact content review checks", "", md_table(content_checks), "", "## Required next gates", "", md_table(gates), "", "## Safety matrix", "", md_table(safety), "", "## Explicit non-actions", "", "- Source recovery approved: `false`", "- Source recovery executed: `false`", "- Source identity finalized/recovered: `false`", "- AI API called: `false`", "- Discord notification sent: `false`", "- MT5 order sent: `false`", "- Live hook enabled: `false`",
    ])


def main() -> int:
    base = fx_outputs_root(); source = base / IN24E; out = base / OUT_DIR
    long_path(out).mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()
    paths = {role: source / filename for role, filename in REQUIRED_24E_FILES.items()}
    input_audit = build_input_audit(paths); write_csv(out / INPUT_AUDIT_FILE, input_audit)
    inputs_ok = bool(input_audit["exists"].map(truthy).all()) if not input_audit.empty else False
    missing_roles = input_audit.loc[~input_audit["exists"].map(truthy), "role"].astype(str).tolist() if not input_audit.empty else list(REQUIRED_24E_FILES.keys())
    checks = [check_row("24F-C000", "Required 24E artifacts exist", ",".join(missing_roles) if missing_roles else "all present", "all present", inputs_ok)]
    summary24e: dict[str, Any] = {}
    intake = pd.DataFrame(); gates24e = pd.DataFrame(); checks24e = pd.DataFrame(); safety24e = pd.DataFrame(); input24e = pd.DataFrame()
    if inputs_ok:
        summary24e = read_json(paths["24e_summary"])
        input24e = read_csv(paths["24e_input_audit"])
        intake = read_csv(paths["24e_artifact_list_intake_result"])
        checks24e = read_csv(paths["24e_integrated_checks"])
        gates24e = read_csv(paths["24e_required_next_gates"])
        safety24e = read_csv(paths["24e_safety_matrix"])
        allowed_after_24e = allowed_next_steps(gates24e, "allowed_after_24e_success")
        forbidden_detail = forbidden_allowed_detail(gates24e, "allowed_after_24e_success")
        category_counts = intake["artifact_category"].astype(str).value_counts().to_dict() if "artifact_category" in intake.columns else {}
        exact_categories = {c: int(category_counts.get(c, 0)) for c in EXPECTED_CATEGORIES}
        valid_status_rows = int((intake.get("status", pd.Series(dtype=str)).astype(str) == "VALID_FOR_24F_AUDIT_ONLY_REVIEW_HASH_VERIFIED").sum()) if not intake.empty else 0
        hash_match_rows = int(intake.get("artifact_hash_matches", pd.Series(dtype=bool)).map(truthy).sum()) if not intake.empty and "artifact_hash_matches" in intake.columns else 0
        artifact_exists_rows = int(intake.get("artifact_exists", pd.Series(dtype=bool)).map(truthy).sum()) if not intake.empty and "artifact_exists" in intake.columns else 0
        missing_required_24e_inputs = int((input24e["required"].map(truthy) & ~input24e["exists"].map(truthy)).sum()) if {"required", "exists"}.issubset(input24e.columns) else 999
        checks.extend([
            check_row("24F-C001", "24E status is validated", summary24e.get("status"), EXPECTED_24E_STATUS, summary24e.get("status") == EXPECTED_24E_STATUS),
            check_row("24F-C002", "24E artifact list supplied", summary24e.get("artifact_list_supplied"), True, truthy(summary24e.get("artifact_list_supplied", False))),
            check_row("24F-C003", "24E artifact list validated", summary24e.get("artifact_list_validated"), True, truthy(summary24e.get("artifact_list_validated", False))),
            check_row("24F-C004", "24E valid artifact rows", summary24e.get("valid_artifact_rows"), 3, int(summary24e.get("valid_artifact_rows", -1)) == 3),
            check_row("24F-C005", "24E invalid artifact rows", summary24e.get("invalid_artifact_rows"), 0, int(summary24e.get("invalid_artifact_rows", 999)) == 0),
            check_row("24F-C006", "24E artifact exists rows", artifact_exists_rows, 3, artifact_exists_rows == 3),
            check_row("24F-C007", "24E artifact hash match rows", hash_match_rows, 3, hash_match_rows == 3),
            check_row("24F-C008", "24E intake statuses are all hash verified", valid_status_rows, 3, valid_status_rows == 3),
            check_row("24F-C009", "24E categories exactly once", exact_categories, {c: 1 for c in EXPECTED_CATEGORIES}, all(v == 1 for v in exact_categories.values()) and len(intake) == 3),
            check_row("24F-C010", "24E integrated/safety STOP rows zero", stop_rows(checks24e) + stop_rows(safety24e), 0, stop_rows(checks24e) + stop_rows(safety24e) == 0),
            check_row("24F-C011", "24E required inputs complete", missing_required_24e_inputs, 0, missing_required_24e_inputs == 0),
            check_row("24F-C012", "24E allowed next only 24F", allowed_after_24e, ["24F_SOURCE_RECOVERY_ARTIFACT_LIST_REVIEW_AUDIT_ONLY"], allowed_after_24e == ["24F_SOURCE_RECOVERY_ARTIFACT_LIST_REVIEW_AUDIT_ONLY"]),
            check_row("24F-C013", "24E forbidden gates remain blocked", forbidden_detail, "all forbidden gates blocked", forbidden_detail == "all forbidden gates blocked"),
            check_row("24F-C014", "24E forbidden summary/external flags remain false", count_true_forbidden_summary_flags(summary24e), 0, count_true_forbidden_summary_flags(summary24e) == 0),
        ])
    checks_df = pd.DataFrame(checks)

    content_check_rows: list[dict[str, Any]] = []
    review_rows: list[dict[str, Any]] = []
    if inputs_ok and not intake.empty:
        for _, row in intake.iterrows():
            cks, rv = review_artifact_content(row)
            content_check_rows.extend(cks)
            review_rows.append(rv)
    content_checks_df = pd.DataFrame(content_check_rows)
    reference_review_df = pd.DataFrame(review_rows)
    reviewable_rows = int(reference_review_df["artifact_review_status"].astype(str).str.startswith("REVIEWABLE").sum()) if not reference_review_df.empty and "artifact_review_status" in reference_review_df.columns else 0
    artifact_review_passed = bool(reviewable_rows == 3 and stop_rows(content_checks_df) == 0)
    upstream_ok = bool(inputs_ok and stop_rows(checks_df) == 0)
    safety_df = build_safety_matrix(summary24e, upstream_ok, artifact_review_passed)
    total_stop_rows = stop_rows(checks_df) + stop_rows(safety_df)
    ok = bool(upstream_ok and total_stop_rows == 0)
    if not ok:
        status = STOP_STATUS
    elif artifact_review_passed:
        status = PASS_STATUS
    else:
        status = REQUEST_MORE_STATUS
    gates_df = build_required_next_gates(ok, artifact_review_passed)
    summary = {
        "created_utc": now,
        "step": STEP,
        "status": status,
        "audit_only": True,
        "source_recovery_artifact_list_review_only": True,
        "source_of_truth": "24E hardened validated artifacts under FX_OUTPUTS/" + IN24E,
        "upstream_status": summary24e.get("status", "UNKNOWN_MISSING_24E_SUMMARY"),
        "required_24e_inputs_ok": inputs_ok,
        "missing_inputs": missing_roles,
        "artifact_reference_rows": int(len(intake)),
        "reviewable_artifact_rows": reviewable_rows,
        "artifact_review_passed": artifact_review_passed,
        "content_review_stop_rows": stop_rows(content_checks_df),
        "total_stop_rows": int(total_stop_rows),
        "source_recovery_approved": False,
        "source_recovery_executed": False,
        "source_identity_finalized": False,
        "source_identity_recovered": False,
        "ledger_is_source_of_truth": False,
        "live_or_final_implementation_allowed": False,
        "oh_lc_replay_allowed": False,
        "live_enabled": False,
        "final_signal_allowed": False,
        "external_actions": EXTERNAL_ACTIONS,
        "no_signal_discord_notified": False,
        "old_gold_disc8_quarantined": True,
        "ai_api_called": False,
        "discord_sent": False,
        "mt5_order_sent": False,
        "live_hook_enabled": False,
        "source_recovery_execution_performed": False,
        "source_recovery_approval_granted": False,
        "source_identity_finalization_performed": False,
        "still_blocked_after_24f": EXPECTED_STILL_BLOCKED,
        "required_next_allowed": allowed_next_steps(gates_df, "allowed_after_24f_success"),
        "next_recommended_step": "24G_SOURCE_RECOVERY_EXECUTION_DECISION_OPTIONS_AUDIT_ONLY" if ok and artifact_review_passed else ("REQUEST_MORE_EVIDENCE" if ok else "STOP_REVIEW_24F_INPUTS_AND_24E_OUTPUTS"),
        "do_not_execute_source_recovery_in_24f": True,
        "outputs": {
            "input_audit": str(out / INPUT_AUDIT_FILE),
            "artifact_reference_review": str(out / REFERENCE_REVIEW_FILE),
            "content_review_checks": str(out / CONTENT_CHECKS_FILE),
            "integrated_checks": str(out / INTEGRATED_CHECKS_FILE),
            "required_next_gates": str(out / REQUIRED_NEXT_GATES_FILE),
            "safety_matrix": str(out / SAFETY_MATRIX_FILE),
            "summary": str(out / SUMMARY_FILE),
            "report": str(out / REPORT_FILE),
        },
    }
    write_csv(out / REFERENCE_REVIEW_FILE, reference_review_df)
    write_csv(out / CONTENT_CHECKS_FILE, content_checks_df)
    write_csv(out / INTEGRATED_CHECKS_FILE, checks_df)
    write_csv(out / REQUIRED_NEXT_GATES_FILE, gates_df)
    write_csv(out / SAFETY_MATRIX_FILE, safety_df)
    write_json(out / SUMMARY_FILE, summary)
    write_text(out / REPORT_FILE, build_report(summary, input_audit, checks_df, reference_review_df, content_checks_df, gates_df, safety_df))
    print(json.dumps(summary, ensure_ascii=False, indent=2, allow_nan=False))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
