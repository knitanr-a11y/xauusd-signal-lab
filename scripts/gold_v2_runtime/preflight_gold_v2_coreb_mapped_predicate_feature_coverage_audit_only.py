#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""GOLD V2 12I: CoreB mapped predicate feature coverage preflight audit.

Header-only audit. Does not create signals, connect step 13, or perform
external actions.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set

import pandas as pd

POLICY_DEFAULT = "configs/gold_v2/gold_v2_coreA_coreB_medium_policy_20260603.json"
COREB_MAPPING_DEFAULT = "configs/gold_v2/live_evaluator_mapping_coreB_20260603.json"
COREB_COMPONENT = "HIGH_B_CoreB_RR125_BUY_CONFLUENCE"
EXTERNAL_ACTIONS_OFF = {"discord_send_allowed": False, "mt5_order_allowed": False, "ai_api_allowed": False, "live_hook_allowed": False}

@dataclass
class AuditCheck:
    check_name: str
    status: str
    message: str
    detail: str = ""


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Preflight CoreB mapped predicate feature coverage audit-only")
    p.add_argument("--policy", default=POLICY_DEFAULT)
    p.add_argument("--coreb-mapping", default=COREB_MAPPING_DEFAULT)
    p.add_argument("--feature-csv", action="append", default=[])
    p.add_argument("--search-root", default=None)
    p.add_argument("--audit-output-dir", default=None)
    p.add_argument("--max-candidate-files", type=int, default=300)
    return p.parse_args(argv)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def files_dir_from_repo() -> Path:
    root = repo_root()
    return root.parents[1] if len(root.parents) >= 2 else root.parent


def default_search_root() -> Path:
    return files_dir_from_repo() / "FX_OUTPUTS"


def default_audit_output_dir() -> Path:
    return files_dir_from_repo() / "FX_OUTPUTS" / "gold_v2_coreb_mapped_predicate_feature_coverage_preflight_audit_only"


def resolve_repo_path(text: str) -> Path:
    p = Path(text)
    return p if p.is_absolute() else (repo_root() / p).resolve()


def add_check(rows: List[AuditCheck], name: str, ok: bool, message: str, detail: str = "") -> None:
    rows.append(AuditCheck(name, "OK" if ok else "ERROR", message, detail))


def load_json(label: str, path: Path, checks: List[AuditCheck]) -> Optional[Dict[str, Any]]:
    if not path.exists():
        add_check(checks, f"{label}_exists", False, f"missing: {path}")
        return None
    add_check(checks, f"{label}_exists", True, str(path))
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        add_check(checks, f"{label}_parse", False, "JSON parse failed", repr(exc))
        return None


def write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")


def validate_policy(policy: Dict[str, Any], checks: List[AuditCheck]) -> bool:
    safety = policy.get("safety", {})
    ok = True
    for key in ["ai_api_enabled", "discord_enabled", "mt5_order_enabled", "live_hook_enabled"]:
        v_ok = safety.get(key) is False
        add_check(checks, f"safety_{key}_false", v_ok, f"{key}={safety.get(key)!r}")
        ok = ok and v_ok
    audit_ok = safety.get("audit_only") is True
    add_check(checks, "safety_audit_only_true", audit_ok, f"audit_only={safety.get('audit_only')!r}")
    ok = ok and audit_ok
    return ok


def extract_required_fields(mapping: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for idx, cond in enumerate(mapping.get("mapped_conditions", []) or []):
        field = cond.get("field")
        if not field:
            continue
        rows.append({
            "field": str(field),
            "rule_id": cond.get("rule_id"),
            "source_column": cond.get("source_column"),
            "operator": cond.get("operator"),
            "value": cond.get("value"),
            "raw_text": cond.get("raw_text"),
            "mapped_condition_index": idx,
        })
    return rows


def candidate_files(explicit_files: Sequence[str], search_root: Path, max_files: int) -> List[Path]:
    paths: List[Path] = []
    for item in explicit_files:
        p = Path(item).expanduser()
        if not p.is_absolute():
            p = (repo_root() / p).resolve()
        paths.append(p)
    if paths:
        return paths
    if not search_root.exists():
        return []
    found = []
    for p in search_root.rglob("*.csv"):
        name = p.name.lower()
        if any(skip in name for skip in ["ledger", "audit", "report", "summary", "mapping", "conditions", "blockers"]):
            continue
        found.append(p)
        if len(found) >= max_files:
            break
    return found


def read_header(path: Path) -> Optional[List[str]]:
    try:
        return list(pd.read_csv(path, nrows=0).columns)
    except Exception:
        return None


def coverage_for_file(path: Path, required: Set[str]) -> Dict[str, Any]:
    header = read_header(path)
    if header is None:
        return {"feature_file": str(path), "readable": False, "column_count": None, "required_field_count": len(required), "matched_field_count": 0, "missing_field_count": len(required), "coverage_ratio": 0.0}
    cols = set(map(str, header))
    matched = required & cols
    missing = required - cols
    return {"feature_file": str(path), "readable": True, "column_count": len(header), "required_field_count": len(required), "matched_field_count": len(matched), "missing_field_count": len(missing), "coverage_ratio": len(matched) / len(required) if required else 0.0}


def build_report(summary: Dict[str, Any]) -> str:
    lines = ["# GOLD V2 CoreB mapped predicate feature coverage preflight audit-only report", "", f"Created UTC: {summary['created_utc']}", f"Status: `{summary['status']}`", f"Audit only: `{summary['audit_only']}`", f"selected_feature_file: `{summary.get('selected_feature_file')}`", f"required_field_count: `{summary['required_field_count']}`", f"matched_field_count: `{summary['matched_field_count']}`", f"missing_field_count: `{summary['missing_field_count']}`", "", "## Safety", "", f"live_evaluator_connection_allowed: `{summary['live_evaluator_connection_allowed']}`", f"final_signal_allowed: `{summary['final_signal_allowed']}`", f"step13_allowed: `{summary['step13_allowed']}`", f"notification_should_send: `{summary['notification_should_send']}`", "", "## External actions", ""]
    for k, v in EXTERNAL_ACTIONS_OFF.items():
        lines.append(f"- {k}: `{v}`")
    lines += ["- no_signal_discord_policy: `DO_NOT_NOTIFY_ON_NO_SIGNAL`", "", "## Important", "", "This is a header-only preflight. It does not evaluate signals and does not permit step 13."]
    return "\n".join(lines)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    out = Path(args.audit_output_dir).expanduser().resolve() if args.audit_output_dir else default_audit_output_dir()
    out.mkdir(parents=True, exist_ok=True)
    checks: List[AuditCheck] = []
    policy = load_json("policy", resolve_repo_path(args.policy), checks) or {}
    policy_ok = validate_policy(policy, checks) if policy else False
    mapping = load_json("coreb_mapping", resolve_repo_path(args.coreb_mapping), checks)
    mapping_ok = bool(mapping and mapping.get("status") == "MAPPING_READY_AUDIT_ONLY_FINAL_SIGNAL_BLOCKED" and mapping.get("component") == COREB_COMPONENT)
    add_check(checks, "coreb_mapping_ready_audit_only", mapping_ok, str(mapping.get("status") if mapping else None))
    required_rows = extract_required_fields(mapping or {})
    required_fields = sorted({r["field"] for r in required_rows})
    required_df = pd.DataFrame(required_rows)
    if not required_df.empty:
        required_df.to_csv(out / "gold_v2_coreb_required_predicate_fields.csv", index=False, encoding="utf-8-sig")
    else:
        pd.DataFrame(columns=["field"]).to_csv(out / "gold_v2_coreb_required_predicate_fields.csv", index=False, encoding="utf-8-sig")
    search_root = Path(args.search_root).expanduser().resolve() if args.search_root else default_search_root()
    files = candidate_files(args.feature_csv, search_root, int(args.max_candidate_files))
    coverage_rows = [coverage_for_file(p, set(required_fields)) for p in files]
    coverage_df = pd.DataFrame(coverage_rows)
    coverage_df.to_csv(out / "gold_v2_coreb_candidate_feature_file_coverage.csv", index=False, encoding="utf-8-sig")
    if not coverage_df.empty:
        coverage_df = coverage_df.sort_values(["matched_field_count", "coverage_ratio", "column_count"], ascending=[False, False, False])
        selected = coverage_df.iloc[0].to_dict()
    else:
        selected = None
    selected_cols: Set[str] = set()
    if selected and selected.get("readable"):
        header = read_header(Path(str(selected["feature_file"]))) or []
        selected_cols = set(map(str, header))
    field_cov = []
    for f in required_fields:
        field_cov.append({"field": f, "present_in_selected_feature_file": f in selected_cols, "selected_feature_file": selected.get("feature_file") if selected else None})
    field_cov_df = pd.DataFrame(field_cov)
    field_cov_df.to_csv(out / "gold_v2_coreb_selected_feature_field_coverage.csv", index=False, encoding="utf-8-sig")
    missing_df = field_cov_df[field_cov_df["present_in_selected_feature_file"] == False].copy() if not field_cov_df.empty else pd.DataFrame(columns=["field"])
    missing_df.to_csv(out / "gold_v2_coreb_missing_feature_fields.csv", index=False, encoding="utf-8-sig")
    matched = int((field_cov_df["present_in_selected_feature_file"] == True).sum()) if not field_cov_df.empty else 0
    missing = int((field_cov_df["present_in_selected_feature_file"] == False).sum()) if not field_cov_df.empty else len(required_fields)
    if not policy_ok or not mapping_ok:
        status = "COREB_PREDICATE_FEATURE_COVERAGE_BLOCKED_POLICY_OR_MAPPING"
    elif not selected:
        status = "COREB_PREDICATE_FEATURE_COVERAGE_BLOCKED_NO_FEATURE_DATA"
    elif missing > 0:
        status = "COREB_PREDICATE_FEATURE_COVERAGE_BLOCKED_MISSING_FIELDS"
    else:
        status = "COREB_PREDICATE_FEATURE_COVERAGE_READY_AUDIT_ONLY"
    summary = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "audit_only": True,
        "policy_safety_ok": bool(policy_ok),
        "mapping_ok": bool(mapping_ok),
        "search_root": str(search_root),
        "candidate_feature_file_count": len(files),
        "selected_feature_file": selected.get("feature_file") if selected else None,
        "required_field_count": len(required_fields),
        "matched_field_count": matched,
        "missing_field_count": missing,
        "live_evaluator_connection_allowed": False,
        "final_signal_allowed": False,
        "step13_allowed": False,
        "notification_should_send": False,
        "external_actions": dict(EXTERNAL_ACTIONS_OFF),
        "no_signal_discord_policy": "DO_NOT_NOTIFY_ON_NO_SIGNAL",
        "output_dir": str(out),
    }
    pd.DataFrame([asdict(c) for c in checks]).to_csv(out / "gold_v2_coreb_feature_coverage_audit_checks.csv", index=False, encoding="utf-8-sig")
    write_json(out / "gold_v2_coreb_mapped_predicate_feature_coverage_preflight_summary.json", summary)
    (out / "GOLD_V2_COREB_MAPPED_PREDICATE_FEATURE_COVERAGE_PREFLIGHT_AUDIT_ONLY_REPORT.md").write_text(build_report(summary), encoding="utf-8")
    print(f"[DONE] status={status} audit_dir={out}")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print("No Discord notification, MT5 order, AI API call, or live hook was performed.")
    print("Header-only preflight. Step 13 remains blocked.")
    if not policy_ok or not mapping_ok:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
