#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""GOLD V2 12B: audit unresolved CoreA/CoreB mapping conditions.

Audit-only. This script does not create live signals, does not infer rules from
entry_time, and does not enable Discord/MT5/AI/live hooks.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import pandas as pd


POLICY_DEFAULT = "configs/gold_v2/gold_v2_coreA_coreB_medium_policy_20260603.json"
COREA_FROZEN_DEFAULT = "configs/gold_v2/frozen_coreA_fold4_ABC_CAP5_rules_20260603.json"
COREB_FROZEN_DEFAULT = "configs/gold_v2/frozen_coreB_rr125_buy_confluence_rules_20260603.json"
MEDIUM_FROZEN_DEFAULT = "configs/gold_v2/frozen_medium_rules_20260603.json"
COREA_MAPPING_DEFAULT = "configs/gold_v2/live_evaluator_mapping_coreA_20260603.json"
COREB_MAPPING_DEFAULT = "configs/gold_v2/live_evaluator_mapping_coreB_20260603.json"
MEDIUM_MAPPING_DEFAULT = "configs/gold_v2/live_evaluator_mapping_medium_20260603.json"

EXTERNAL_ACTIONS_OFF = {
    "discord_send_allowed": False,
    "mt5_order_allowed": False,
    "ai_api_allowed": False,
    "live_hook_allowed": False,
}

EVIDENCE_COLUMNS = {
    "HIGH_A_CoreA_fold4_ABC_CAP5": {
        "fold4_rules": [
            "ruleset", "fold_id", "period", "test_month", "component",
            "component_desc", "scenario", "view", "signal", "signal_ABC",
        ],
        "ABC_entry_gate": [
            "signal_ABC", "signal_fixed_ABC", "signal_trainC_ABC",
            "is_A", "is_B_rr15_fixed", "is_C_fixed", "no_opposite",
            "has_opposite_conflict",
        ],
        "A_CAP5_BC_CAP3_classification": [
            "is_A", "is_B_rr15_fixed", "is_C_fixed", "profit_cap5_from_members",
            "profit_cap3_from_members", "same_direction_count_from_members",
            "unique_origins_from_members",
        ],
        "variant_defined_tp_sl_policy": [
            "top_variant", "top_direction", "top_candidate_id", "rr",
            "top_profit_r", "top_score",
        ],
    },
    "HIGH_B_CoreB_RR125_BUY_CONFLUENCE": {
        "RR1_source_BUY_rule_definitions": [
            "base_condition", "added_filter_text", "candidate_id", "origin_id",
            "direction", "variant", "policy", "rr", "rr_bucket",
        ],
        "same_count_confluence_derivation": [
            "same_count", "source_rule_count", "unique_origins", "cluster_id",
            "top_direction", "top_candidate_id", "filter",
        ],
        "rr125_tp_sl_conversion": [
            "tp_pips", "sl_pips", "rr", "rr_bucket", "variant", "policy",
            "profit_r",
        ],
    },
}

TEXT_SAMPLE_COLUMNS = [
    "base_condition",
    "added_filter_text",
    "variant",
    "top_variant",
    "component_desc",
    "ruleset",
    "policy",
    "filter",
]


@dataclass
class AuditCheck:
    check_name: str
    status: str
    message: str
    detail: str = ""


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit GOLD V2 unresolved live evaluator mapping conditions without implementing them."
    )
    parser.add_argument("--policy", default=POLICY_DEFAULT)
    parser.add_argument("--corea-frozen", default=COREA_FROZEN_DEFAULT)
    parser.add_argument("--coreb-frozen", default=COREB_FROZEN_DEFAULT)
    parser.add_argument("--medium-frozen", default=MEDIUM_FROZEN_DEFAULT)
    parser.add_argument("--corea-mapping", default=COREA_MAPPING_DEFAULT)
    parser.add_argument("--coreb-mapping", default=COREB_MAPPING_DEFAULT)
    parser.add_argument("--medium-mapping", default=MEDIUM_MAPPING_DEFAULT)
    parser.add_argument("--audit-output-dir", default=None)
    parser.add_argument("--sample-rows", type=int, default=20)
    parser.add_argument("--skip-source-file-sha-verify", action="store_true")
    return parser.parse_args(argv)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def files_dir_from_repo() -> Path:
    root = repo_root()
    if len(root.parents) >= 2:
        return root.parents[1]
    return root.parent


def default_audit_output_dir() -> Path:
    return files_dir_from_repo() / "FX_OUTPUTS" / "gold_v2_unmapped_rule_source_definition_audit_only"


def resolve_repo_path(text: str) -> Path:
    path = Path(text)
    if path.is_absolute():
        return path
    return (repo_root() / path).resolve()


def resolve_manifest_source_path(value: Any) -> Optional[Path]:
    if value is None:
        return None
    text = str(value)
    if not text:
        return None
    path = Path(text)
    if path.is_absolute():
        return path
    normalized = text.replace("\\", "/")
    if normalized.startswith("Files/"):
        return (files_dir_from_repo() / normalized[len("Files/"):]).resolve()
    return (repo_root() / path).resolve()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")


def add_check(rows: List[AuditCheck], name: str, ok: bool, message: str, detail: str = "") -> None:
    rows.append(AuditCheck(name, "OK" if ok else "ERROR", message, detail))


def load_json_or_none(label: str, path: Path, checks: List[AuditCheck]) -> Optional[Dict[str, Any]]:
    if not path.exists():
        add_check(checks, f"{label}_exists", False, f"missing: {path}")
        return None
    add_check(checks, f"{label}_exists", True, str(path))
    try:
        obj = read_json(path)
    except Exception as exc:
        add_check(checks, f"{label}_parse", False, "JSON parse failed", repr(exc))
        return None
    add_check(checks, f"{label}_parse", True, "JSON parsed")
    return obj


def validate_policy_safety(policy: Dict[str, Any], checks: List[AuditCheck]) -> bool:
    safety = policy.get("safety", {})
    ok = True
    for key in ["ai_api_enabled", "discord_enabled", "mt5_order_enabled", "live_hook_enabled"]:
        flag_ok = safety.get(key) is False
        ok = ok and flag_ok
        add_check(checks, f"safety_{key}_false", flag_ok, f"{key}={safety.get(key)!r}")
    audit_ok = safety.get("audit_only") is True
    ok = ok and audit_ok
    add_check(checks, "safety_audit_only_true", audit_ok, f"audit_only={safety.get('audit_only')!r}")
    return ok


def explicit_mapping_ready(mapping: Optional[Dict[str, Any]]) -> bool:
    if not mapping:
        return False
    return mapping.get("status") == "MAPPING_READY" and bool(mapping.get("mapped_conditions")) and not bool(mapping.get("unmapped_conditions"))


def get_unmapped_conditions(mapping: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not mapping:
        return []
    rows: List[Dict[str, Any]] = []
    for item in mapping.get("unmapped_conditions", []) or []:
        if isinstance(item, dict):
            rows.append(dict(item))
    return rows


def read_csv_header(path: Path) -> Tuple[Optional[List[str]], Optional[str]]:
    try:
        df = pd.read_csv(path, nrows=0)
        return list(df.columns), None
    except Exception as exc:
        return None, repr(exc)


def read_csv_sample(path: Path, columns: List[str], sample_rows: int) -> Tuple[pd.DataFrame, Optional[str]]:
    try:
        if columns:
            df = pd.read_csv(path, usecols=lambda c: c in set(columns), nrows=max(sample_rows * 5, sample_rows))
        else:
            df = pd.read_csv(path, nrows=sample_rows)
        return df.head(sample_rows), None
    except Exception as exc:
        return pd.DataFrame(), repr(exc)


def source_file_records(component: str, manifest: Optional[Dict[str, Any]], *, skip_sha_verify: bool) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    if not manifest:
        return records
    for idx, src in enumerate(manifest.get("source_files", []) or []):
        rec = dict(src) if isinstance(src, dict) else {"raw": src}
        rec["component"] = component
        rec["source_index"] = idx
        path = resolve_manifest_source_path(rec.get("path"))
        rec["resolved_path"] = str(path) if path else None
        if path is None:
            rec["disk_status"] = "NO_PATH"
            records.append(rec)
            continue
        if not path.exists():
            rec["disk_status"] = "SOURCE_FILE_MISSING_OR_UNREADABLE"
            records.append(rec)
            continue

        rec["disk_status"] = "ACCESSIBLE"
        header, header_error = read_csv_header(path)
        rec["columns_actual"] = header or []
        if header_error:
            rec["disk_status"] = "SOURCE_FILE_MISSING_OR_UNREADABLE"
            rec["read_error"] = header_error
        if not skip_sha_verify:
            try:
                actual_sha = sha256_file(path)
                rec["actual_sha256"] = actual_sha
                rec["sha256_match"] = actual_sha == rec.get("sha256")
            except Exception as exc:
                rec["sha_error"] = repr(exc)
                rec["sha256_match"] = False
        else:
            rec["sha256_match"] = None
        records.append(rec)
    return records


def collect_evidence_for_condition(
    component: str,
    condition_id: str,
    source_records: List[Dict[str, Any]],
    sample_rows: int,
) -> Tuple[str, str, List[Dict[str, Any]], List[Dict[str, Any]]]:
    wanted_columns = EVIDENCE_COLUMNS.get(component, {}).get(condition_id, [])
    source_evidence: List[Dict[str, Any]] = []
    text_samples: List[Dict[str, Any]] = []

    accessible_any = False
    evidence_any = False
    text_any = False

    for rec in source_records:
        path_text = rec.get("resolved_path")
        columns_actual = rec.get("columns_actual") or rec.get("columns") or []
        if rec.get("disk_status") not in {"ACCESSIBLE"} or not path_text:
            source_evidence.append({
                "component": component,
                "condition_id": condition_id,
                "source_index": rec.get("source_index"),
                "path": rec.get("path"),
                "resolved_path": path_text,
                "disk_status": rec.get("disk_status"),
                "evidence_columns_present": "",
                "evidence_columns_missing": ",".join(wanted_columns),
                "classification": "SOURCE_FILE_MISSING_OR_UNREADABLE",
            })
            continue

        accessible_any = True
        present = [c for c in wanted_columns if c in columns_actual]
        missing = [c for c in wanted_columns if c not in columns_actual]
        text_cols = [c for c in TEXT_SAMPLE_COLUMNS if c in columns_actual]
        if present:
            evidence_any = True
        source_evidence.append({
            "component": component,
            "condition_id": condition_id,
            "source_index": rec.get("source_index"),
            "path": rec.get("path"),
            "resolved_path": path_text,
            "disk_status": rec.get("disk_status"),
            "row_count": rec.get("row_count"),
            "manifest_sha256": rec.get("sha256"),
            "sha256_match": rec.get("sha256_match"),
            "evidence_columns_present": ",".join(present),
            "evidence_columns_missing": ",".join(missing),
            "text_columns_present": ",".join(text_cols),
            "classification": "CANDIDATE_EVIDENCE_ONLY" if present else "UNRESOLVED_SOURCE_DEFINITION_MISSING",
        })

        if text_cols:
            df, err = read_csv_sample(Path(path_text), text_cols, sample_rows)
            if err is None and not df.empty:
                text_any = True
                for _, row in df.iterrows():
                    for col in text_cols:
                        val = row.get(col)
                        if pd.isna(val):
                            continue
                        value = str(val)
                        if not value:
                            continue
                        text_samples.append({
                            "component": component,
                            "condition_id": condition_id,
                            "source_index": rec.get("source_index"),
                            "path": rec.get("path"),
                            "column": col,
                            "sample_text": value[:500],
                        })

    if not accessible_any:
        return (
            "SOURCE_FILE_MISSING_OR_UNREADABLE",
            "Required source CSV files were not accessible/readable for this condition.",
            source_evidence,
            text_samples,
        )

    if evidence_any:
        if text_any:
            reason = "Source ledgers contain evidence columns and text samples, but not strict live_evaluator_mapping.conditions."
        else:
            reason = "Source ledgers contain evidence columns, but not strict live_evaluator_mapping.conditions."
        return "CANDIDATE_EVIDENCE_ONLY", reason, source_evidence, text_samples

    return (
        "UNRESOLVED_SOURCE_DEFINITION_MISSING",
        "No explicit mapping block and no useful evidence columns were found for this condition.",
        source_evidence,
        text_samples,
    )


def explicit_mapping_status_for_component(mapping: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if explicit_mapping_ready(mapping):
        return {
            "resolution_status": "RESOLVED_EXPLICIT_MAPPING_FOUND",
            "resolution_reason": "Step-12 mapping already contains explicit mapped_conditions and no unmapped_conditions.",
            "live_evaluator_connection_allowed": False,
        }
    return None


def build_resolution_rows(
    component: str,
    mapping: Optional[Dict[str, Any]],
    source_records: List[Dict[str, Any]],
    sample_rows: int,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    unmapped_rows = get_unmapped_conditions(mapping)
    resolution_rows: List[Dict[str, Any]] = []
    evidence_rows: List[Dict[str, Any]] = []
    text_rows: List[Dict[str, Any]] = []

    explicit_status = explicit_mapping_status_for_component(mapping)
    if not unmapped_rows:
        if explicit_status:
            resolution_rows.append({
                "component": component,
                "condition_id": "",
                **explicit_status,
                "blocking": False,
            })
        else:
            resolution_rows.append({
                "component": component,
                "condition_id": "",
                "resolution_status": "NOT_APPLICABLE",
                "resolution_reason": "No blocking unmapped condition exists for this component.",
                "blocking": False,
                "live_evaluator_connection_allowed": False,
            })
        return resolution_rows, evidence_rows, text_rows

    for item in unmapped_rows:
        condition_id = str(item.get("condition_id") or "")
        status, reason, evidence, samples = collect_evidence_for_condition(
            component,
            condition_id,
            source_records,
            sample_rows,
        )
        resolution_rows.append({
            "component": component,
            "condition_id": condition_id,
            "original_unmapped_reason": item.get("reason"),
            "resolution_status": status,
            "resolution_reason": reason,
            "blocking": True,
            "live_evaluator_connection_allowed": False,
        })
        evidence_rows.extend(evidence)
        text_rows.extend(samples)

    return resolution_rows, evidence_rows, text_rows


def build_report(summary: Dict[str, Any], resolution_rows: List[Dict[str, Any]]) -> str:
    lines: List[str] = []
    lines.append("# GOLD V2 unmapped rule source definition audit-only report")
    lines.append("")
    lines.append(f"Created UTC: {summary['created_utc']}")
    lines.append(f"Status: `{summary['status']}`")
    lines.append(f"Audit only: `{summary['audit_only']}`")
    lines.append(f"live_evaluator_connection_allowed: `{summary['live_evaluator_connection_allowed']}`")
    lines.append("")
    lines.append("## External actions")
    lines.append("")
    for key, value in EXTERNAL_ACTIONS_OFF.items():
        lines.append(f"- {key}: `{value}`")
    lines.append("- no_signal_discord_policy: `DO_NOT_NOTIFY_ON_NO_SIGNAL`")
    lines.append("")
    lines.append("## Resolution audit")
    lines.append("")
    lines.append("| component | condition_id | resolution_status | blocking |")
    lines.append("| --- | --- | --- | --- |")
    for row in resolution_rows:
        lines.append(
            f"| {row.get('component')} | `{row.get('condition_id')}` | "
            f"`{row.get('resolution_status')}` | `{row.get('blocking')}` |"
        )
    lines.append("")
    lines.append("## Important")
    lines.append("")
    lines.append("Candidate evidence is not a live rule. Do not connect step 13 until strict explicit live evaluator predicates are frozen and step 12 no longer reports blocking UNMAPPED_CONDITION.")
    lines.append("")
    lines.append("No Discord notification, MT5 order, AI API call, or live hook is performed.")
    return "\n".join(lines)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    output_dir = Path(args.audit_output_dir).expanduser().resolve() if args.audit_output_dir else default_audit_output_dir()
    output_dir.mkdir(parents=True, exist_ok=True)

    checks: List[AuditCheck] = []

    policy = load_json_or_none("policy", resolve_repo_path(args.policy), checks) or {}
    policy_ok = validate_policy_safety(policy, checks) if policy else False

    corea_frozen = load_json_or_none("corea_frozen", resolve_repo_path(args.corea_frozen), checks)
    coreb_frozen = load_json_or_none("coreb_frozen", resolve_repo_path(args.coreb_frozen), checks)
    medium_frozen = load_json_or_none("medium_frozen", resolve_repo_path(args.medium_frozen), checks)

    corea_mapping = load_json_or_none("corea_mapping", resolve_repo_path(args.corea_mapping), checks)
    coreb_mapping = load_json_or_none("coreb_mapping", resolve_repo_path(args.coreb_mapping), checks)
    medium_mapping = load_json_or_none("medium_mapping", resolve_repo_path(args.medium_mapping), checks)

    corea_sources = source_file_records("HIGH_A_CoreA_fold4_ABC_CAP5", corea_frozen, skip_sha_verify=bool(args.skip_source_file_sha_verify))
    coreb_sources = source_file_records("HIGH_B_CoreB_RR125_BUY_CONFLUENCE", coreb_frozen, skip_sha_verify=bool(args.skip_source_file_sha_verify))
    medium_sources = source_file_records("MEDIUM_REFINED_FEATURE_GATES", medium_frozen, skip_sha_verify=bool(args.skip_source_file_sha_verify))

    resolution_rows: List[Dict[str, Any]] = []
    evidence_rows: List[Dict[str, Any]] = []
    text_rows: List[Dict[str, Any]] = []

    for component, mapping, sources in [
        ("HIGH_A_CoreA_fold4_ABC_CAP5", corea_mapping, corea_sources),
        ("HIGH_B_CoreB_RR125_BUY_CONFLUENCE", coreb_mapping, coreb_sources),
        ("MEDIUM_REFINED_FEATURE_GATES", medium_mapping, medium_sources),
    ]:
        rr, er, tr = build_resolution_rows(component, mapping, sources, int(args.sample_rows))
        resolution_rows.extend(rr)
        evidence_rows.extend(er)
        text_rows.extend(tr)

    blocking_rows = [r for r in resolution_rows if r.get("blocking") is True]
    unresolved_rows = [
        r for r in blocking_rows
        if r.get("resolution_status") != "RESOLVED_EXPLICIT_MAPPING_FOUND"
    ]

    summary = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "UNRESOLVED_SOURCE_DEFINITION_REMAINS" if unresolved_rows else "ALL_UNMAPPED_HAVE_EXPLICIT_MAPPING_EVIDENCE",
        "audit_only": True,
        "policy_safety_ok": bool(policy_ok),
        "external_actions": dict(EXTERNAL_ACTIONS_OFF),
        "no_signal_discord_policy": "DO_NOT_NOTIFY_ON_NO_SIGNAL",
        "output_dir": str(output_dir),
        "blocking_unmapped_condition_count": int(len(blocking_rows)),
        "unresolved_source_definition_count": int(len(unresolved_rows)),
        "candidate_evidence_only_count": int(sum(1 for r in resolution_rows if r.get("resolution_status") == "CANDIDATE_EVIDENCE_ONLY")),
        "source_definition_missing_count": int(sum(1 for r in resolution_rows if r.get("resolution_status") == "UNRESOLVED_SOURCE_DEFINITION_MISSING")),
        "source_file_unreadable_count": int(sum(1 for r in resolution_rows if r.get("resolution_status") == "SOURCE_FILE_MISSING_OR_UNREADABLE")),
        "explicit_mapping_found_count": int(sum(1 for r in resolution_rows if r.get("resolution_status") == "RESOLVED_EXPLICIT_MAPPING_FOUND")),
        "live_evaluator_connection_allowed": False,
        "important_note": "Candidate evidence is not a live rule. Do not connect step 13 until step 12 has no blocking UNMAPPED_CONDITION.",
    }

    pd.DataFrame(resolution_rows).to_csv(output_dir / "gold_v2_unmapped_condition_resolution_audit.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(evidence_rows).to_csv(output_dir / "gold_v2_unmapped_source_column_evidence.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(text_rows).to_csv(output_dir / "gold_v2_unmapped_candidate_text_samples.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(corea_sources + coreb_sources + medium_sources).to_csv(output_dir / "gold_v2_unmapped_source_file_audit.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame([asdict(c) for c in checks]).to_csv(output_dir / "gold_v2_unmapped_audit_checks.csv", index=False, encoding="utf-8-sig")
    write_json(output_dir / "gold_v2_unmapped_rule_source_definition_summary.json", summary)
    (output_dir / "GOLD_V2_UNMAPPED_RULE_SOURCE_DEFINITION_AUDIT_ONLY_REPORT.md").write_text(
        build_report(summary, resolution_rows),
        encoding="utf-8",
    )

    print(f"[DONE] status={summary['status']} audit_dir={output_dir}")
    print(pd.DataFrame(resolution_rows).to_string(index=False))
    print("")
    print("No Discord notification, MT5 order, AI API call, or live hook was performed.")
    print("Candidate evidence is not a live rule. Step 13 remains blocked until step 12 has no blocking UNMAPPED_CONDITION.")

    if not policy_ok:
        print("[STOP] Policy safety check failed.")
        return 2
    if corea_mapping is None or coreb_mapping is None or corea_frozen is None or coreb_frozen is None:
        print("[STOP] Required CoreA/CoreB frozen or mapping JSON is missing.")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
