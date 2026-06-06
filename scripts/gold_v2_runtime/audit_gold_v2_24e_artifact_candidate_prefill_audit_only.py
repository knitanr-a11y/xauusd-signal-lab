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

STEP = "24E_ARTIFACT_CANDIDATE_PREFILL_AUDIT_ONLY"
OUT_DIR = "gold_v2_24e_artifact_candidate_prefill_audit_only"
TEMPLATE_24E_DIR = "gold_v2_24e_source_recovery_artifact_list_intake_audit_only"
TEMPLATE_24D_DIR = "gold_v2_24d_source_recovery_gap_resolution_plan_audit_only"
TEMPLATE_24E_FILE = "gold_v2_24e_artifact_list_input_template.csv"
TEMPLATE_24D_FILE = "gold_v2_24d_artifact_request_template.csv"

INVENTORY_FILE = "gold_v2_24e_artifact_candidate_inventory.csv"
REVIEW_MATRIX_FILE = "gold_v2_24e_artifact_candidate_prefill_review_matrix.csv"
PREFILL_FILE = "gold_v2_24e_artifact_list_input_candidate_prefill_DO_NOT_USE_UNREVIEWED.csv"
SUMMARY_FILE = "gold_v2_24e_artifact_candidate_prefill_summary.json"
REPORT_FILE = "GOLD_V2_24E_ARTIFACT_CANDIDATE_PREFILL_AUDIT_ONLY_REPORT.md"

READY_STATUS = "24E_ARTIFACT_CANDIDATE_PREFILL_READY_AUDIT_ONLY_REVIEW_REQUIRED"
INCOMPLETE_STATUS = "24E_ARTIFACT_CANDIDATE_PREFILL_INCOMPLETE_AUDIT_ONLY_MISSING_EXISTING_ARTIFACTS"
STOP_STATUS = "24E_ARTIFACT_CANDIDATE_PREFILL_STOP_TEMPLATE_MISSING_OR_INVALID"

REQUIRED_VALUE_COLUMNS = ["artifact_path", "artifact_hash", "artifact_role", "source_identity_scope", "upstream_sot_reference"]
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


def write_text(path: Path, text: str) -> None:
    long_path(path.parent).mkdir(parents=True, exist_ok=True)
    long_path(path).write_text(text, encoding="utf-8")


def write_json(path: Path, obj: dict[str, Any]) -> None:
    write_text(path, json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False))


def write_csv(path: Path, df: pd.DataFrame) -> None:
    long_path(path.parent).mkdir(parents=True, exist_ok=True)
    df.to_csv(long_path(path), index=False, encoding="utf-8-sig")


def read_csv(path: Path) -> pd.DataFrame:
    last: Exception | None = None
    for enc in ("utf-8-sig", "utf-8", "cp932"):
        try:
            return pd.read_csv(long_path(path), encoding=enc, keep_default_na=False)
        except Exception as exc:
            last = exc
    raise RuntimeError(f"CSV read failed: {path}: {last}")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with long_path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def git_blob_sha1_file(path: Path) -> str:
    data = long_path(path).read_bytes()
    return hashlib.sha1(f"blob {len(data)}\0".encode("utf-8") + data).hexdigest()


def safe_rel(path: Path) -> str:
    for base in (repo_root(), fx_outputs_root(), files_root()):
        try:
            rel = path.resolve().relative_to(base.resolve())
            if base == repo_root():
                return str(rel).replace("\\", "/")
            if base == fx_outputs_root():
                return "FX_OUTPUTS/" + str(rel).replace("\\", "/")
            return str(rel).replace("\\", "/")
        except Exception:
            pass
    return str(path)


def file_meta(path: Path, category: str, role: str, priority: int, reason: str, upstream: str, scope: str, quarantine_note: str = "") -> dict[str, Any]:
    exists = False
    is_file = False
    bytes_size = 0
    sha256 = ""
    blob = ""
    row_count: Any = ""
    column_count: Any = ""
    status = "MISSING"
    try:
        exists = long_path(path).exists()
        is_file = long_path(path).is_file() if exists else False
        if is_file:
            bytes_size = int(long_path(path).stat().st_size)
            sha256 = sha256_file(path)
            blob = git_blob_sha1_file(path)
            status = "EXISTS_HASHED"
            if path.suffix.lower() == ".csv":
                try:
                    df = read_csv(path)
                    row_count = int(len(df))
                    column_count = int(len(df.columns))
                except Exception as exc:
                    row_count = "CSV_READ_ERROR"
                    column_count = str(exc)
    except Exception as exc:
        status = f"ERROR:{exc}"
    return {
        "artifact_category": category,
        "candidate_role": role,
        "priority": priority,
        "path": str(path),
        "relative_or_fx_path": safe_rel(path),
        "exists": exists,
        "is_file": is_file,
        "status": status,
        "bytes": bytes_size,
        "sha256": sha256,
        "git_blob_sha1": blob,
        "row_count": row_count,
        "column_count": column_count,
        "source_identity_scope": scope,
        "upstream_sot_reference": upstream,
        "quarantine_note": quarantine_note,
        "selection_reason": reason,
        "source_recovery_approved": False,
        "execution_approved": False,
    }


def find_first_by_name(filename: str) -> list[Path]:
    matches: list[Path] = []
    for root in (fx_outputs_root(), repo_root()):
        try:
            matches.extend([p for p in root.rglob(filename) if p.is_file()])
        except Exception:
            pass
    unique: list[Path] = []
    seen: set[str] = set()
    for p in matches:
        key = str(p.resolve())
        if key not in seen:
            seen.add(key)
            unique.append(p)
    return unique


def candidate_specs() -> list[dict[str, Any]]:
    rr = repo_root()
    fx = fx_outputs_root()
    specs: list[dict[str, Any]] = []

    def add(category: str, role: str, path: Path, priority: int, reason: str, upstream: str, scope: str, quarantine_note: str = "") -> None:
        specs.append({"category": category, "role": role, "path": path, "priority": priority, "reason": reason, "upstream": upstream, "scope": scope, "quarantine_note": quarantine_note})

    add(
        "source_identity_lineage_docs",
        "lineage_handoff_doc",
        rr / "docs/gold_v2/NEXT_CHAT_HANDOFF_GOLD_V2_18J_DONE_18K_NEXT_AUDIT_ONLY_20260605.md",
        10,
        "Existing handoff documenting Tier2 dry-run source identity artifacts, source_row_hash candidate columns, and selected future input artifacts.",
        "18J/18I audited source identity dry-run design lineage",
        "tier2_source_identity_lineage",
    )
    add(
        "source_identity_lineage_docs",
        "source_identity_design_script",
        rr / "scripts/gold_v2_runtime/audit_gold_v2_18i_tier2_source_identity_extraction_dry_run_design_audit_only.py",
        20,
        "Existing audit-only script defining required source identity fields and source_row_hash design. It is not source recovery execution.",
        "18I source identity extraction dry-run design script",
        "tier2_source_identity_lineage",
    )
    add(
        "source_identity_lineage_docs",
        "sot_to_live_gap_handoff_doc",
        rr / "docs/gold_v2/NEXT_CHAT_HANDOFF_GOLD_V2_13A_13D_MEDIUM_TIER2_RECONCILIATION_20260605.md",
        30,
        "Existing handoff documenting final SOT ledger, component blockers, and Tier2 source rows lineage.",
        "13A-13D audited SOT/live gap lineage",
        "gold_v2_final_sot_and_tier2_lineage",
    )

    source_files = [
        ("tier2_source_rows_primary", fx / "gold_v2_13d2_medium_tier2_hvt_source_definition_reconciliation_audit_only/gold_v2_13d2_tier2_source_rows.csv", 10, "18J selected this as PRIMARY future dry-run input artifact."),
        ("tier2_reconciled_source_rows_backup", fx / "gold_v2_13d3_freeze_medium_tier2_hvt_reconciled_rule_audit_only/gold_v2_13d3_tier2_source_rows_with_reconciled_match.csv", 20, "18J selected this as BACKUP source identity input artifact."),
        ("tier2_final_manifest_mismatch_rows_backup", fx / "gold_v2_13d2_medium_tier2_hvt_source_definition_reconciliation_audit_only/gold_v2_13d2_tier2_final_manifest_mismatch_rows.csv", 30, "18J selected this as BACKUP mismatch source artifact."),
        ("tier2_manifest_match_rows_backup", fx / "gold_v2_13d2_medium_tier2_hvt_source_definition_reconciliation_audit_only/gold_v2_13d2_tier2_manifest_match_rows.csv", 40, "18J selected this as BACKUP match source artifact."),
        ("tier2_manifest_mismatch_rows_backup", fx / "gold_v2_13d2_medium_tier2_hvt_source_definition_reconciliation_audit_only/gold_v2_13d2_tier2_manifest_mismatch_rows.csv", 50, "18J selected this as BACKUP mismatch source artifact."),
        ("final_portfolio_sot_ledger_reference", fx / "gold_v2_final_portfolio_sot_freeze_audit_only/gold_v2_final_portfolio_2025_2026_sot_ledger.csv", 90, "Historical final portfolio SOT reference only; candidate_source_files should prefer row-level Tier2 source files if present."),
    ]
    for role, path, priority, reason in source_files:
        add(
            "candidate_source_files",
            role,
            path,
            priority,
            reason,
            "18J selected artifacts / 13D2 source definition reconciliation outputs",
            "tier2_candidate_source_files",
        )

    for filename in [
        "gold_v2_13d2_tier2_source_rows.csv",
        "gold_v2_13d3_tier2_source_rows_with_reconciled_match.csv",
        "gold_v2_13d2_tier2_final_manifest_mismatch_rows.csv",
        "gold_v2_13d2_tier2_manifest_match_rows.csv",
        "gold_v2_13d2_tier2_manifest_mismatch_rows.csv",
    ]:
        for i, found in enumerate(find_first_by_name(filename)):
            add(
                "candidate_source_files",
                f"discovered_{filename}_{i+1}",
                found,
                15 + i,
                f"Discovered existing artifact by filename search: {filename}",
                "dynamic FX_OUTPUTS/repo filename discovery",
                "tier2_candidate_source_files",
            )

    q_note = "Old GOLD/DISC8 remain quarantined due suspected HTF open-time mismatch; not active source-of-truth. This row is quarantine evidence only."
    add(
        "old_gold_disc8_quarantine_evidence",
        "primary_quarantine_policy_handoff_doc",
        rr / "docs/gold_v2/NEXT_CHAT_HANDOFF_GOLD_V2_COREA_COREB_MEDIUM_LIVE_RULES_20260603.md",
        10,
        "Existing handoff explicitly states old GOLD/DISC8 must not return as source-of-truth and HTF must use confirmed bars only.",
        "GOLD V2 CoreA/CoreB/MEDIUM live-rule handoff quarantine policy",
        "old_gold_disc8_quarantine_evidence",
        q_note,
    )
    add(
        "old_gold_disc8_quarantine_evidence",
        "request_more_audit_quarantine_handoff_doc",
        rr / "docs/gold_v2/NEXT_CHAT_HANDOFF_GOLD_V2_22G_DONE_23A_FAST_TRACK_INTEGRATED_AUDIT_FINAL_20260606.md",
        20,
        "Existing handoff repeats old GOLD/DISC8 quarantine and REQUEST_MORE_AUDIT is not approval.",
        "22G/23A fast-track integrated audit handoff quarantine policy",
        "old_gold_disc8_quarantine_evidence",
        q_note,
    )
    add(
        "old_gold_disc8_quarantine_evidence",
        "source_identity_blocker_handoff_doc",
        rr / "docs/gold_v2/NEXT_CHAT_HANDOFF_GOLD_V2_19L_TO_19M_20260606.md",
        30,
        "Existing handoff confirms blockers remain in force after 19L, including source recovery/finalization/live/external actions.",
        "19L blocker review handoff",
        "old_gold_disc8_quarantine_evidence",
        q_note,
    )
    return specs


def load_template() -> tuple[pd.DataFrame, Path | None, str]:
    candidates = [
        fx_outputs_root() / TEMPLATE_24E_DIR / TEMPLATE_24E_FILE,
        fx_outputs_root() / TEMPLATE_24D_DIR / TEMPLATE_24D_FILE,
    ]
    for p in candidates:
        if long_path(p).exists():
            return read_csv(p), p, "FOUND"
    return pd.DataFrame(), None, "MISSING"


def select_candidates(template: pd.DataFrame, inventory: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows: list[dict[str, Any]] = []
    prefill = template.copy()
    for col in ["artifact_path", "artifact_hash", "artifact_role", "source_identity_scope", "upstream_sot_reference", "quarantine_note", "execution_approved", "source_recovery_approved", "status"]:
        if col not in prefill.columns:
            prefill[col] = ""
    for idx, t in prefill.iterrows():
        category = str(t.get("artifact_category", ""))
        sub = inventory[(inventory["artifact_category"].astype(str) == category) & (inventory["exists"].astype(bool)) & (inventory["is_file"].astype(bool))].copy()
        sub = sub.sort_values(["priority", "relative_or_fx_path"], ascending=[True, True]) if not sub.empty else sub
        if sub.empty:
            rec = {
                "intake_id": t.get("intake_id", ""), "source_gap_id": t.get("source_gap_id", ""), "source_evidence_id": t.get("source_evidence_id", ""),
                "artifact_category": category, "selected": False, "review_status": "NO_EXISTING_ARTIFACT_FOUND", "selected_path": "", "selected_sha256": "", "selected_git_blob_sha1": "", "selected_role": "", "source_identity_scope": "", "upstream_sot_reference": "", "quarantine_note": "", "notes": "Leave this 24E row unfilled until an already-existing artifact is located.",
            }
        else:
            best = sub.iloc[0]
            prefill.at[idx, "artifact_path"] = str(best["relative_or_fx_path"])
            prefill.at[idx, "artifact_hash"] = str(best["sha256"])
            prefill.at[idx, "artifact_role"] = str(best["candidate_role"])
            prefill.at[idx, "source_identity_scope"] = str(best["source_identity_scope"])
            prefill.at[idx, "upstream_sot_reference"] = str(best["upstream_sot_reference"])
            prefill.at[idx, "quarantine_note"] = str(best.get("quarantine_note", ""))
            prefill.at[idx, "execution_approved"] = False
            prefill.at[idx, "source_recovery_approved"] = False
            prefill.at[idx, "status"] = "CANDIDATE_PREFILL_REVIEW_REQUIRED_DO_NOT_USE_AS_APPROVAL"
            rec = {
                "intake_id": t.get("intake_id", ""), "source_gap_id": t.get("source_gap_id", ""), "source_evidence_id": t.get("source_evidence_id", ""),
                "artifact_category": category, "selected": True, "review_status": "CANDIDATE_SELECTED_REVIEW_REQUIRED", "selected_path": str(best["relative_or_fx_path"]), "selected_sha256": str(best["sha256"]), "selected_git_blob_sha1": str(best["git_blob_sha1"]), "selected_role": str(best["candidate_role"]), "source_identity_scope": str(best["source_identity_scope"]), "upstream_sot_reference": str(best["upstream_sot_reference"]), "quarantine_note": str(best.get("quarantine_note", "")), "notes": str(best["selection_reason"]),
            }
        rows.append(rec)
    return pd.DataFrame(rows), prefill


def md_table(df: pd.DataFrame, limit: int = 80) -> str:
    if df.empty:
        return "_No rows._"
    view = df.head(limit).copy()
    cols = list(view.columns)
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for _, row in view.iterrows():
        lines.append("| " + " | ".join(str(row[c]).replace("|", "\\|").replace("\n", " ") for c in cols) + " |")
    return "\n".join(lines)


def build_report(summary: dict[str, Any], inventory: pd.DataFrame, review: pd.DataFrame, prefill: pd.DataFrame) -> str:
    lines = [
        "# GOLD V2 24E artifact candidate prefill audit-only report",
        "",
        f"Created UTC: {summary['created_utc']}",
        f"Step: `{STEP}`",
        f"Status: `{summary['status']}`",
        "",
        "## Boundary",
        "",
        "- This step is audit-only.",
        "- It scans already-existing artifacts and computes hashes.",
        "- It does not create evidence.",
        "- It does not overwrite `gold_v2_24e_artifact_list_input.csv`.",
        "- It writes only a candidate prefill draft that requires review.",
        "- 24E hardened must still be rerun and must verify existence/hash before 24F.",
        "- Source recovery, source identity finalization, live, final signal, Discord, MT5, AI API, and live hook remain blocked.",
        "",
        "## Outcome",
        "",
        f"- template_status: `{summary['template_status']}`",
        f"- template_rows: `{summary['template_rows']}`",
        f"- candidate_inventory_rows: `{summary['candidate_inventory_rows']}`",
        f"- selected_rows: `{summary['selected_rows']}` / 3",
        f"- candidate_prefill_complete: `{summary['candidate_prefill_complete']}`",
        f"- next_recommended_step: `{summary['next_recommended_step']}`",
        "",
        "## Review matrix",
        "",
        md_table(review),
        "",
        "## Candidate prefill draft",
        "",
        md_table(prefill),
        "",
        "## Candidate inventory",
        "",
        md_table(inventory[["artifact_category", "candidate_role", "priority", "relative_or_fx_path", "exists", "status", "sha256", "row_count", "column_count", "selection_reason"]] if not inventory.empty else inventory, 120),
        "",
        "## Non-actions",
        "",
        "- source_recovery_approved: false",
        "- source_recovery_executed: false",
        "- source_identity_finalized: false",
        "- final_signal_allowed: false",
        "- discord_sent: false",
        "- mt5_order_sent: false",
        "- ai_api_called: false",
        "- live_hook_enabled: false",
    ]
    return "\n".join(lines)


def main() -> int:
    out = fx_outputs_root() / OUT_DIR
    long_path(out).mkdir(parents=True, exist_ok=True)
    created = datetime.now(timezone.utc).isoformat()
    template, template_path, template_status = load_template()
    if template_status != "FOUND" or len(template) != 3 or "intake_id" not in template.columns or "artifact_category" not in template.columns:
        inventory = pd.DataFrame()
        review = pd.DataFrame()
        prefill = pd.DataFrame()
        status = STOP_STATUS
        summary = {
            "created_utc": created,
            "step": STEP,
            "status": status,
            "audit_only": True,
            "template_status": template_status,
            "template_path": str(template_path) if template_path else "",
            "template_rows": int(len(template)),
            "candidate_inventory_rows": 0,
            "selected_rows": 0,
            "candidate_prefill_complete": False,
            "real_24e_input_written": False,
            "source_recovery_approved": False,
            "source_recovery_executed": False,
            "source_identity_finalized": False,
            "final_signal_allowed": False,
            "external_actions": EXTERNAL_ACTIONS,
            "next_recommended_step": "RERUN_24E_HARDENED_TO_GENERATE_TEMPLATE_OR_REVIEW_24D_OUTPUTS",
        }
        write_json(out / SUMMARY_FILE, summary)
        write_text(out / REPORT_FILE, build_report(summary, inventory, review, prefill))
        return 2

    inventory = pd.DataFrame([file_meta(s["path"], s["category"], s["role"], int(s["priority"]), s["reason"], s["upstream"], s["scope"], s.get("quarantine_note", "")) for s in candidate_specs()])
    inventory = inventory.drop_duplicates(subset=["artifact_category", "relative_or_fx_path", "candidate_role"]).sort_values(["artifact_category", "priority", "relative_or_fx_path"])
    review, prefill = select_candidates(template, inventory)

    selected_rows = int(review["selected"].astype(bool).sum()) if "selected" in review.columns else 0
    complete = selected_rows == 3
    status = READY_STATUS if complete else INCOMPLETE_STATUS
    next_step = "REVIEW_CANDIDATE_PREFILL_THEN_COPY_TO_24E_INPUT_AND_RERUN_24E_HARDENED" if complete else "LOCATE_MISSING_EXISTING_ARTIFACTS_THEN_RERUN_PREFILL"
    summary = {
        "created_utc": created,
        "step": STEP,
        "status": status,
        "audit_only": True,
        "template_status": template_status,
        "template_path": str(template_path) if template_path else "",
        "template_rows": int(len(template)),
        "candidate_inventory_rows": int(len(inventory)),
        "existing_candidate_rows": int(inventory["exists"].astype(bool).sum()) if not inventory.empty else 0,
        "selected_rows": selected_rows,
        "candidate_prefill_complete": bool(complete),
        "candidate_prefill_file": str(out / PREFILL_FILE),
        "real_24e_input_written": False,
        "real_24e_input_path": str(fx_outputs_root() / TEMPLATE_24E_DIR / "gold_v2_24e_artifact_list_input.csv"),
        "source_recovery_approved": False,
        "source_recovery_executed": False,
        "source_identity_finalized": False,
        "source_identity_recovered": False,
        "ledger_is_source_of_truth": False,
        "live_or_final_implementation_allowed": False,
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
        "required_next_allowed": [next_step],
        "next_recommended_step": next_step,
        "must_rerun_24e_hardened_after_copy": True,
        "does_not_allow_24f_by_itself": True,
    }

    write_csv(out / INVENTORY_FILE, inventory)
    write_csv(out / REVIEW_MATRIX_FILE, review)
    write_csv(out / PREFILL_FILE, prefill)
    write_json(out / SUMMARY_FILE, summary)
    write_text(out / REPORT_FILE, build_report(summary, inventory, review, prefill))
    print(json.dumps(summary, ensure_ascii=False, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
