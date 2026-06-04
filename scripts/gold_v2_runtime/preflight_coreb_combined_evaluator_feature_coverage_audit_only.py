#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DEFINITION = ROOT / "configs/gold_v2/frozen_coreB_combined_evaluator_definition_20260604.json"
READY = "FROZEN_COREB_COMBINED_EVALUATOR_DEFINITION_READY_AUDIT_ONLY_FINAL_SIGNAL_BLOCKED"
COMPONENT = "HIGH_B_CoreB_RR125_BUY_CONFLUENCE"
MAX_CANDIDATES = 3000

EXCLUDE_DIR_PARTS = {
    "gold_v2_coreb_combined_evaluator_feature_coverage_preflight_audit_only",
    "gold_v2_coreb_mapped_predicate_feature_coverage_preflight_audit_only",
    "gold_v2_coreb_combined_evaluator_definition_audit_only",
    "gold_v2_coreb_same_count_source_universe_freeze_audit_only",
    "gold_v2_coreb_source_rule_conditions_freeze_audit_only",
    "gold_v2_live_evaluator_mapping_consolidated_status_audit_only",
}
EXCLUDE_NAME_PARTS = [
    "mapping", "definition", "summary", "report", "audit", "required_fields",
    "conditions", "rules", "missing_feature_fields", "candidate_feature_file_coverage",
]


def files_dir() -> Path:
    return ROOT.parents[1] if len(ROOT.parents) >= 2 else ROOT.parent


def out_dir() -> Path:
    p = files_dir() / "FX_OUTPUTS" / "gold_v2_coreb_combined_evaluator_feature_coverage_preflight_audit_only"
    p.mkdir(parents=True, exist_ok=True)
    return p


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")


def search_roots() -> list[Path]:
    roots = [files_dir() / "FX_OUTPUTS", files_dir(), ROOT]
    deduped: list[Path] = []
    seen: set[str] = set()
    for r in roots:
        try:
            key = str(r.resolve())
        except Exception:
            key = str(r)
        if key not in seen and r.exists():
            seen.add(key)
            deduped.append(r)
    return deduped


def should_skip(path: Path) -> bool:
    low_name = path.name.lower()
    if path.suffix.lower() != ".csv":
        return True
    if any(part in low_name for part in EXCLUDE_NAME_PARTS):
        return True
    low_parts = {p.lower() for p in path.parts}
    if low_parts & EXCLUDE_DIR_PARTS:
        return True
    return False


def read_csv_header(path: Path) -> tuple[list[str], str | None]:
    attempts = [
        {"sep": None, "engine": "python", "nrows": 0},
        {"sep": ",", "nrows": 0},
        {"sep": ";", "nrows": 0},
        {"sep": "\t", "nrows": 0},
    ]
    last_error = None
    best_cols: list[str] = []
    for kwargs in attempts:
        try:
            df = pd.read_csv(path, **kwargs)
            cols = [str(c).strip() for c in df.columns]
            if len(cols) > len(best_cols):
                best_cols = cols
            if len(cols) > 1:
                return cols, None
        except Exception as exc:
            last_error = str(exc)
    if best_cols:
        return best_cols, None
    return [], last_error or "HEADER_READ_FAILED"


def collect_candidates(required: list[str]) -> tuple[list[dict], int]:
    required_set = set(required)
    rows: list[dict] = []
    scanned = 0
    for root in search_roots():
        for path in root.rglob("*.csv"):
            if scanned >= MAX_CANDIDATES:
                return rows, scanned
            if should_skip(path):
                continue
            scanned += 1
            cols, err = read_csv_header(path)
            col_set = set(cols)
            matched = sorted(required_set & col_set)
            missing = sorted(required_set - col_set)
            rows.append({
                "path": str(path),
                "filename": path.name,
                "column_count": len(cols),
                "matched_field_count": len(matched),
                "missing_field_count": len(missing),
                "is_full_match": len(missing) == 0 and len(required_set) > 0,
                "matched_fields": "|".join(matched),
                "missing_fields": "|".join(missing),
                "header_read_error": err or "",
            })
    return rows, scanned


def main() -> int:
    out = out_dir()
    created = datetime.now(timezone.utc).isoformat()
    if not DEFINITION.exists():
        summary = {
            "created_utc": created,
            "status": "COREB_COMBINED_EVALUATOR_DEFINITION_MISSING",
            "audit_only": True,
            "definition_path": str(DEFINITION),
            "selected_feature_file": None,
            "live_evaluator_connection_allowed": False,
            "final_signal_allowed": False,
            "step13_allowed": False,
            "notification_should_send": False,
        }
        write_json(out / "gold_v2_coreb_combined_evaluator_feature_coverage_preflight_summary.json", summary)
        return 2

    definition = read_json(DEFINITION)
    required = sorted({str(x).strip() for x in definition.get("required_fields", []) if str(x).strip()})
    pd.DataFrame(required, columns=["field"]).to_csv(out / "gold_v2_coreb_combined_required_fields.csv", index=False, encoding="utf-8-sig")

    definition_ok = definition.get("status") == READY and definition.get("component") == COMPONENT and len(required) > 0
    if not definition_ok:
        summary = {
            "created_utc": created,
            "status": "COREB_COMBINED_EVALUATOR_DEFINITION_NOT_READY",
            "audit_only": True,
            "definition_status": definition.get("status"),
            "component": definition.get("component"),
            "required_field_count": len(required),
            "selected_feature_file": None,
            "live_evaluator_connection_allowed": False,
            "final_signal_allowed": False,
            "step13_allowed": False,
            "notification_should_send": False,
        }
        write_json(out / "gold_v2_coreb_combined_evaluator_feature_coverage_preflight_summary.json", summary)
        return 2

    rows, scanned_count = collect_candidates(required)
    rows_sorted = sorted(rows, key=lambda r: (r["is_full_match"], r["matched_field_count"], -r["missing_field_count"]), reverse=True)
    pd.DataFrame(rows_sorted).to_csv(out / "gold_v2_coreb_combined_candidate_feature_file_coverage.csv", index=False, encoding="utf-8-sig")

    best = rows_sorted[0] if rows_sorted else None
    selected = next((r for r in rows_sorted if r["is_full_match"]), None)
    selected_path = selected["path"] if selected else None
    matched_fields = selected["matched_fields"].split("|") if selected and selected["matched_fields"] else []
    missing_fields = [] if selected else (best["missing_fields"].split("|") if best and best["missing_fields"] else required)

    pd.DataFrame(missing_fields, columns=["field"]).to_csv(out / "gold_v2_coreb_combined_missing_feature_fields.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(matched_fields, columns=["field"]).to_csv(out / "gold_v2_coreb_combined_selected_feature_field_coverage.csv", index=False, encoding="utf-8-sig")

    audit_checks = [
        {"check": "definition_ready", "ok": definition_ok, "detail": definition.get("status")},
        {"check": "required_fields_non_empty", "ok": len(required) > 0, "detail": len(required)},
        {"check": "selected_requires_full_match", "ok": selected is None or len(missing_fields) == 0, "detail": selected_path or "None"},
        {"check": "no_alias_or_approximation", "ok": True, "detail": "exact column names only"},
        {"check": "external_actions_off", "ok": True, "detail": "discord/mt5/ai/live_hook false"},
    ]
    pd.DataFrame(audit_checks).to_csv(out / "gold_v2_coreb_combined_feature_coverage_audit_checks.csv", index=False, encoding="utf-8-sig")

    if selected:
        status = "COREB_COMBINED_FEATURE_COVERAGE_READY_AUDIT_ONLY_FINAL_SIGNAL_BLOCKED"
    elif best and best["matched_field_count"] > 0:
        status = "COREB_COMBINED_FEATURE_COVERAGE_BLOCKED_MISSING_FEATURE_FIELDS"
    else:
        status = "COREB_COMBINED_FEATURE_COVERAGE_BLOCKED_NO_EXACT_MATCHING_FEATURE_FILE"

    summary = {
        "created_utc": created,
        "status": status,
        "audit_only": True,
        "policy_safety_ok": True,
        "definition_ok": definition_ok,
        "definition_id": definition.get("definition_id"),
        "entry_logic": definition.get("entry_logic"),
        "required_field_count": len(required),
        "matched_field_count": len(matched_fields) if selected else (best["matched_field_count"] if best else 0),
        "missing_field_count": len(missing_fields),
        "candidate_feature_file_count": len(rows_sorted),
        "scanned_csv_count": scanned_count,
        "selected_feature_file": selected_path,
        "selected_file_requires_full_match": True,
        "best_candidate_file": best["path"] if best else None,
        "best_candidate_matched_field_count": best["matched_field_count"] if best else 0,
        "best_candidate_missing_field_count": best["missing_field_count"] if best else len(required),
        "live_evaluator_connection_allowed": False,
        "final_signal_allowed": False,
        "step13_allowed": False,
        "notification_should_send": False,
        "external_actions": {
            "discord_send_allowed": False,
            "mt5_order_allowed": False,
            "ai_api_allowed": False,
            "live_hook_allowed": False,
        },
        "no_signal_discord_policy": "DO_NOT_NOTIFY_ON_NO_SIGNAL",
        "output_dir": str(out),
        "important_note": "Header-only exact-field preflight for 12M combined CoreB evaluator. Full match required. No aliases, approximations, signals, or external actions are used.",
    }
    write_json(out / "gold_v2_coreb_combined_evaluator_feature_coverage_preflight_summary.json", summary)
    report = [
        "# GOLD V2 CoreB combined evaluator feature coverage preflight audit-only report",
        "",
        f"Created UTC: {created}",
        f"Status: `{status}`",
        "Audit only: `True`",
        f"definition_id: `{definition.get('definition_id')}`",
        f"entry_logic: `{definition.get('entry_logic')}`",
        f"selected_feature_file: `{selected_path}`",
        f"required_field_count: `{len(required)}`",
        f"matched_field_count: `{summary['matched_field_count']}`",
        f"missing_field_count: `{len(missing_fields)}`",
        f"candidate_feature_file_count: `{len(rows_sorted)}`",
        "",
        "## Search roots",
    ]
    for r in search_roots():
        report.append(f"- `{r}`")
    report.extend([
        "",
        "## Safety",
        "live_evaluator_connection_allowed: `False`",
        "final_signal_allowed: `False`",
        "step13_allowed: `False`",
        "notification_should_send: `False`",
        "",
        "## Important",
        "This is a header-only exact-field preflight. It does not evaluate signals and does not permit step 13.",
        "A CSV is selected only when it has all required fields. No aliasing or approximation is used.",
    ])
    (out / "GOLD_V2_COREB_COMBINED_EVALUATOR_FEATURE_COVERAGE_PREFLIGHT_AUDIT_ONLY_REPORT.md").write_text("\n".join(report), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if selected else 2

if __name__ == "__main__":
    raise SystemExit(main())
