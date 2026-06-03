#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""GOLD V2 12H: consolidate live evaluator mapping status audit-only.

Read-only audit. Does not modify mappings, connect step 13, or perform any
external actions.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import pandas as pd

POLICY_DEFAULT = "configs/gold_v2/gold_v2_coreA_coreB_medium_policy_20260603.json"
COREA_MAPPING_DEFAULT = "configs/gold_v2/live_evaluator_mapping_coreA_20260603.json"
COREB_MAPPING_DEFAULT = "configs/gold_v2/live_evaluator_mapping_coreB_20260603.json"
MEDIUM_MAPPING_DEFAULT = "configs/gold_v2/live_evaluator_mapping_medium_20260603.json"
COREB_SOURCE_DEF_DEFAULT = "configs/gold_v2/frozen_coreB_live_evaluator_source_definition_20260603.json"
EXTERNAL_ACTIONS_OFF = {"discord_send_allowed": False, "mt5_order_allowed": False, "ai_api_allowed": False, "live_hook_allowed": False}

@dataclass
class AuditCheck:
    check_name: str
    status: str
    message: str
    detail: str = ""


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Consolidate GOLD V2 live evaluator mapping status audit-only")
    p.add_argument("--policy", default=POLICY_DEFAULT)
    p.add_argument("--corea-mapping", default=COREA_MAPPING_DEFAULT)
    p.add_argument("--coreb-mapping", default=COREB_MAPPING_DEFAULT)
    p.add_argument("--medium-mapping", default=MEDIUM_MAPPING_DEFAULT)
    p.add_argument("--coreb-source-definition", default=COREB_SOURCE_DEF_DEFAULT)
    p.add_argument("--audit-output-dir", default=None)
    return p.parse_args(argv)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def files_dir_from_repo() -> Path:
    root = repo_root()
    return root.parents[1] if len(root.parents) >= 2 else root.parent


def default_audit_output_dir() -> Path:
    return files_dir_from_repo() / "FX_OUTPUTS" / "gold_v2_live_evaluator_mapping_consolidated_status_audit_only"


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


def bool_value(obj: Dict[str, Any], key: str, default: bool = False) -> bool:
    value = obj.get(key, default)
    return bool(value) if value is not None else default


def component_row(name: str, mapping: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not mapping:
        return {
            "component": name,
            "mapping_status": "MAPPING_FILE_MISSING_OR_UNREADABLE",
            "mapping_id": None,
            "live_evaluator_ready": False,
            "feature_gate_ready": False,
            "component_signal_allowed": False,
            "live_evaluator_connection_allowed": False,
            "final_signal_allowed": False,
            "unmapped_condition_count": None,
            "mapped_rule_count": None,
            "mapped_condition_count": None,
            "blocked_reason": "mapping file missing or unreadable",
        }
    unmapped = mapping.get("unmapped_conditions", []) or []
    mapped_rules = mapping.get("mapped_rules", []) or []
    mapped_conditions = mapping.get("mapped_conditions", []) or []
    return {
        "component": mapping.get("component", name),
        "mapping_status": mapping.get("status"),
        "mapping_id": mapping.get("mapping_id"),
        "live_evaluator_ready": bool_value(mapping, "live_evaluator_ready", False),
        "feature_gate_ready": bool_value(mapping, "feature_gate_ready", False),
        "component_signal_allowed": bool_value(mapping, "component_signal_allowed", False),
        "live_evaluator_connection_allowed": bool_value(mapping, "live_evaluator_connection_allowed", False),
        "final_signal_allowed": bool_value(mapping, "final_signal_allowed", False),
        "unmapped_condition_count": len(unmapped),
        "mapped_rule_count": len(mapped_rules),
        "mapped_condition_count": len(mapped_conditions),
        "blocked_reason": mapping.get("blocked_reason", ""),
    }


def remaining_blockers(rows: List[Dict[str, Any]], coreb_source_def: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    blockers: List[Dict[str, Any]] = []
    for row in rows:
        component = row["component"]
        status = str(row.get("mapping_status"))
        if row.get("unmapped_condition_count") not in {0, None}:
            blockers.append({"component": component, "blocker_type": "UNMAPPED_CONDITION_REMAINS", "detail": f"unmapped_condition_count={row.get('unmapped_condition_count')}", "blocks_final_signal": True})
        if not row.get("live_evaluator_ready") and component != "MEDIUM_REFINED_FEATURE_GATES":
            blockers.append({"component": component, "blocker_type": "LIVE_EVALUATOR_NOT_READY", "detail": status, "blocks_final_signal": True})
        if component == "MEDIUM_REFINED_FEATURE_GATES":
            blockers.append({"component": component, "blocker_type": "HIGH_ARBITRATION_REQUIRED", "detail": "MEDIUM cannot become a final signal until CoreA/CoreB arbitration is explicitly mapped.", "blocks_final_signal": True})
        if component == "HIGH_B_CoreB_RR125_BUY_CONFLUENCE" and status == "MAPPING_READY_AUDIT_ONLY_FINAL_SIGNAL_BLOCKED":
            blockers.append({"component": component, "blocker_type": "AUDIT_READY_ONLY", "detail": "CoreB is mapping-ready for audit but component_signal_allowed/live connection/final signal remain false.", "blocks_final_signal": True})
    if not coreb_source_def:
        blockers.append({"component": "HIGH_B_CoreB_RR125_BUY_CONFLUENCE", "blocker_type": "COREB_SOURCE_DEFINITION_NOT_FOUND", "detail": "Optional source definition missing; CoreB mapping should still be checked from mapping JSON.", "blocks_final_signal": False})
    blockers.extend([
        {"component": "GLOBAL", "blocker_type": "EXTERNAL_ACTIONS_OFF", "detail": "Discord/MT5/AI/live hook are OFF by policy.", "blocks_final_signal": True},
        {"component": "GLOBAL", "blocker_type": "STEP13_BLOCKED", "detail": "Step 13 remains blocked until CoreA/arbitration/preflight are resolved.", "blocks_final_signal": True},
    ])
    return blockers


def consolidated_status(rows: List[Dict[str, Any]]) -> str:
    coreb_ready = any(r.get("component") == "HIGH_B_CoreB_RR125_BUY_CONFLUENCE" and r.get("mapping_status") == "MAPPING_READY_AUDIT_ONLY_FINAL_SIGNAL_BLOCKED" and r.get("unmapped_condition_count") == 0 for r in rows)
    any_final = any(bool(r.get("final_signal_allowed")) for r in rows)
    if coreb_ready and not any_final:
        return "PARTIAL_MAPPING_COREB_READY_COREA_MEDIUM_BLOCKED_AUDIT_ONLY"
    return "MAPPING_CONSOLIDATED_AUDIT_ONLY_NOT_READY"


def build_report(summary: Dict[str, Any], rows: List[Dict[str, Any]], blockers: List[Dict[str, Any]]) -> str:
    lines = ["# GOLD V2 live evaluator mapping consolidated status audit-only report", "", f"Created UTC: {summary['created_utc']}", f"Status: `{summary['status']}`", f"Audit only: `{summary['audit_only']}`", f"live_evaluator_connection_allowed: `{summary['live_evaluator_connection_allowed']}`", f"final_signal_allowed: `{summary['final_signal_allowed']}`", f"step13_allowed: `{summary['step13_allowed']}`", "", "## External actions", ""]
    for k, v in EXTERNAL_ACTIONS_OFF.items():
        lines.append(f"- {k}: `{v}`")
    lines += ["- no_signal_discord_policy: `DO_NOT_NOTIFY_ON_NO_SIGNAL`", "", "## Component status", "", "| component | status | ready | unmapped | rules | conditions | final allowed |", "| --- | --- | ---: | ---: | ---: | ---: | ---: |"]
    for row in rows:
        lines.append(f"| {row['component']} | `{row['mapping_status']}` | {row['live_evaluator_ready']} | {row['unmapped_condition_count']} | {row['mapped_rule_count']} | {row['mapped_condition_count']} | {row['final_signal_allowed']} |")
    lines += ["", "## Remaining blockers", "", "| component | blocker_type | detail |", "| --- | --- | --- |"]
    for b in blockers:
        lines.append(f"| {b['component']} | `{b['blocker_type']}` | {b['detail']} |")
    lines += ["", "## Important", "", "This is a read-only audit. It does not modify mappings and does not permit step 13."]
    return "\n".join(lines)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    out = Path(args.audit_output_dir).expanduser().resolve() if args.audit_output_dir else default_audit_output_dir()
    out.mkdir(parents=True, exist_ok=True)
    checks: List[AuditCheck] = []
    policy = load_json("policy", resolve_repo_path(args.policy), checks) or {}
    policy_ok = validate_policy(policy, checks) if policy else False
    corea = load_json("corea_mapping", resolve_repo_path(args.corea_mapping), checks)
    coreb = load_json("coreb_mapping", resolve_repo_path(args.coreb_mapping), checks)
    medium = load_json("medium_mapping", resolve_repo_path(args.medium_mapping), checks)
    coreb_source_def = load_json("coreb_source_definition", resolve_repo_path(args.coreb_source_definition), checks)
    rows = [component_row("HIGH_A_CoreA_fold4_ABC_CAP5", corea), component_row("HIGH_B_CoreB_RR125_BUY_CONFLUENCE", coreb), component_row("MEDIUM_REFINED_FEATURE_GATES", medium)]
    blockers = remaining_blockers(rows, coreb_source_def)
    status = consolidated_status(rows)
    any_final = any(bool(r.get("final_signal_allowed")) for r in rows)
    summary = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "audit_only": True,
        "policy_safety_ok": bool(policy_ok),
        "component_count": len(rows),
        "coreb_mapping_ready_audit_only": any(r.get("component") == "HIGH_B_CoreB_RR125_BUY_CONFLUENCE" and r.get("mapping_status") == "MAPPING_READY_AUDIT_ONLY_FINAL_SIGNAL_BLOCKED" for r in rows),
        "remaining_blocker_count": len(blockers),
        "component_statuses": rows,
        "live_evaluator_connection_allowed": False,
        "final_signal_allowed": False if not any_final else False,
        "step13_allowed": False,
        "notification_should_send": False,
        "external_actions": dict(EXTERNAL_ACTIONS_OFF),
        "no_signal_discord_policy": "DO_NOT_NOTIFY_ON_NO_SIGNAL",
        "output_dir": str(out),
    }
    pd.DataFrame(rows).to_csv(out / "gold_v2_live_evaluator_mapping_component_status.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(blockers).to_csv(out / "gold_v2_live_evaluator_mapping_remaining_blockers.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame([asdict(c) for c in checks]).to_csv(out / "gold_v2_live_evaluator_mapping_consolidated_audit_checks.csv", index=False, encoding="utf-8-sig")
    write_json(out / "gold_v2_live_evaluator_mapping_consolidated_status_summary.json", summary)
    (out / "GOLD_V2_LIVE_EVALUATOR_MAPPING_CONSOLIDATED_STATUS_AUDIT_ONLY_REPORT.md").write_text(build_report(summary, rows, blockers), encoding="utf-8")
    print(f"[DONE] status={status} audit_dir={out}")
    print(pd.DataFrame(rows).to_string(index=False))
    print("No Discord notification, MT5 order, AI API call, or live hook was performed.")
    print("Step 13 remains blocked.")
    if not policy_ok or corea is None or coreb is None or medium is None:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
