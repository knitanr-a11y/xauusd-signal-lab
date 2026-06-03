#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""GOLD V2 12G: map frozen CoreB source definition to audit-only mapping.

This writes live_evaluator_mapping_coreB_20260603.json in an audit-only,
final-signal-blocked state. It does not connect step 13 or perform external
actions.
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
COREB_FROZEN_DEFAULT = "configs/gold_v2/frozen_coreB_rr125_buy_confluence_rules_20260603.json"
COREB_SOURCE_DEF_DEFAULT = "configs/gold_v2/frozen_coreB_live_evaluator_source_definition_20260603.json"
COREB_MAPPING_DEFAULT = "configs/gold_v2/live_evaluator_mapping_coreB_20260603.json"
COREB_COMPONENT = "HIGH_B_CoreB_RR125_BUY_CONFLUENCE"
SOURCE_STATUS_READY = "FROZEN_COREB_LIVE_EVALUATOR_SOURCE_DEFINITION_READY_AUDIT_ONLY"
MAPPING_STATUS_READY_BLOCKED = "MAPPING_READY_AUDIT_ONLY_FINAL_SIGNAL_BLOCKED"
EXTERNAL_ACTIONS_OFF = {"discord_send_allowed": False, "mt5_order_allowed": False, "ai_api_allowed": False, "live_hook_allowed": False}

@dataclass
class PolicyCheck:
    check_name: str
    status: str
    message: str
    detail: str = ""


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Map CoreB frozen source definition to audit-only live evaluator mapping")
    p.add_argument("--policy", default=POLICY_DEFAULT)
    p.add_argument("--coreb-frozen", default=COREB_FROZEN_DEFAULT)
    p.add_argument("--coreb-source-definition", default=COREB_SOURCE_DEF_DEFAULT)
    p.add_argument("--coreb-mapping", default=COREB_MAPPING_DEFAULT)
    p.add_argument("--audit-output-dir", default=None)
    return p.parse_args(argv)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def files_dir_from_repo() -> Path:
    root = repo_root()
    return root.parents[1] if len(root.parents) >= 2 else root.parent


def default_audit_output_dir() -> Path:
    return files_dir_from_repo() / "FX_OUTPUTS" / "gold_v2_coreb_live_evaluator_mapping_from_source_definition_audit_only"


def resolve_repo_path(text: str) -> Path:
    p = Path(text)
    return p if p.is_absolute() else (repo_root() / p).resolve()


def read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")


def add_check(rows: List[PolicyCheck], name: str, ok: bool, message: str, detail: str = "") -> None:
    rows.append(PolicyCheck(name, "OK" if ok else "ERROR", message, detail))


def load_json_or_none(label: str, path: Path, checks: List[PolicyCheck]) -> Optional[Dict[str, Any]]:
    if not path.exists():
        add_check(checks, f"{label}_exists", False, f"missing: {path}")
        return None
    add_check(checks, f"{label}_exists", True, str(path))
    try:
        return read_json(path)
    except Exception as exc:
        add_check(checks, f"{label}_parse", False, "JSON parse failed", repr(exc))
        return None


def validate_policy_safety(policy: Dict[str, Any], checks: List[PolicyCheck]) -> bool:
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


def validate_source_definition(src: Dict[str, Any], checks: List[PolicyCheck]) -> bool:
    ok = True
    status_ok = src.get("status") == SOURCE_STATUS_READY
    add_check(checks, "source_definition_status_ready", status_ok, str(src.get("status")))
    ok = ok and status_ok
    audit_ok = src.get("audit_only") is True
    add_check(checks, "source_definition_audit_only", audit_ok, str(src.get("audit_only")))
    ok = ok and audit_ok
    comp_ok = src.get("component") == COREB_COMPONENT
    add_check(checks, "source_definition_component", comp_ok, str(src.get("component")))
    ok = ok and comp_ok
    rules = src.get("source_rule_universe", []) or []
    count_ok = len(rules) > 0 and len(rules) == int(src.get("rule_universe_count", -1))
    add_check(checks, "source_rule_universe_count", count_ok, f"rules={len(rules)} declared={src.get('rule_universe_count')}")
    ok = ok and count_ok
    for idx, rule in enumerate(rules):
        rule_ok = True
        if rule.get("freeze_ready_candidate") is not True:
            rule_ok = False
        if rule.get("direction") != "BUY":
            rule_ok = False
        try:
            rr_ok = abs(float(rule.get("rr")) - 1.25) < 1e-9
        except Exception:
            rr_ok = False
        if not rr_ok:
            rule_ok = False
        if not rule.get("predicates"):
            rule_ok = False
        if not rule_ok:
            add_check(checks, f"rule_{idx:04d}_valid", False, str(rule.get("rule_id")), json.dumps(rule, ensure_ascii=False)[:500])
            ok = False
    if ok:
        add_check(checks, "all_source_rules_valid", True, f"rules={len(rules)}")
    return ok


def flatten_rules(rules: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for rule in rules:
        out.append({
            "rule_id": rule.get("rule_id"),
            "candidate_id": rule.get("candidate_id"),
            "origin_id": rule.get("origin_id"),
            "direction": rule.get("direction"),
            "variant": rule.get("variant"),
            "tp_pips": rule.get("tp_pips"),
            "sl_pips": rule.get("sl_pips"),
            "rr": rule.get("rr"),
            "rr_bucket": rule.get("rr_bucket"),
            "policy": rule.get("policy"),
            "predicate_count": len(rule.get("predicates", []) or []),
            "freeze_ready_candidate": rule.get("freeze_ready_candidate"),
        })
    return out


def flatten_conditions(rules: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for rule in rules:
        for idx, pred in enumerate(rule.get("predicates", []) or []):
            out.append({
                "rule_id": rule.get("rule_id"),
                "predicate_index": idx,
                "source_column": pred.get("source_column"),
                "condition_index": pred.get("condition_index"),
                "field": pred.get("field"),
                "operator": pred.get("operator"),
                "value": pred.get("value"),
                "raw_text": pred.get("raw_text"),
            })
    return out


def build_mapping(source_def: Dict[str, Any], previous_mapping: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    rules = source_def.get("source_rule_universe", []) or []
    mapped_conditions = []
    for rule in rules:
        for pred in rule.get("predicates", []) or []:
            mapped_conditions.append({
                "rule_id": rule.get("rule_id"),
                "field": pred.get("field"),
                "operator": pred.get("operator"),
                "value": pred.get("value"),
                "source_column": pred.get("source_column"),
                "raw_text": pred.get("raw_text"),
            })
    return {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": MAPPING_STATUS_READY_BLOCKED,
        "audit_only": True,
        "component": COREB_COMPONENT,
        "mapping_id": "LIVE_EVALUATOR_MAPPING_GOLD_V2_COREB_20260603",
        "priority": "HIGH_B",
        "source_policy": source_def.get("source_policy"),
        "source_definition_path": str(resolve_repo_path(COREB_SOURCE_DEF_DEFAULT)),
        "source_definition_status": source_def.get("status"),
        "direction": "BUY",
        "rule_universe_count": len(rules),
        "same_count_min": int(source_def.get("same_count_min", 15)),
        "same_count_derivation": {
            "method": "count simultaneous hits across mapped CoreB rules",
            "source_rule_universe_count": len(rules),
            "minimum_count": int(source_def.get("same_count_min", 15)),
            "entry_time_history_reuse_allowed": False,
        },
        "rr_policy": source_def.get("rr_policy"),
        "sizing": source_def.get("sizing", "CAP3"),
        "lot_multiplier_candidate": source_def.get("lot_multiplier_candidate", 1.0),
        "mapped_rules": rules,
        "mapped_conditions": mapped_conditions,
        "unmapped_conditions": [],
        "source_files": source_def.get("source_files", []),
        "previous_mapping_status": previous_mapping.get("status") if previous_mapping else None,
        "previous_unmapped_condition_count": len(previous_mapping.get("unmapped_conditions", []) or []) if previous_mapping else None,
        "live_evaluator_ready": True,
        "component_signal_allowed": False,
        "live_evaluator_connection_allowed": False,
        "final_signal_allowed": False,
        "blocked_reason": "CoreB mapping is audit-ready, but final signal and live connection remain blocked until CoreA/arbitration/preflight are resolved.",
        "step13_allowed": False,
        "external_actions": dict(EXTERNAL_ACTIONS_OFF),
        "no_signal_discord_policy": "DO_NOT_NOTIFY_ON_NO_SIGNAL",
    }


def build_report(summary: Dict[str, Any]) -> str:
    lines = ["# GOLD V2 CoreB live evaluator mapping from source definition audit-only report", "", f"Created UTC: {summary['created_utc']}", f"Status: `{summary['status']}`", f"Audit only: `{summary['audit_only']}`", f"live_evaluator_ready: `{summary['live_evaluator_ready']}`", f"live_evaluator_connection_allowed: `{summary['live_evaluator_connection_allowed']}`", f"final_signal_allowed: `{summary['final_signal_allowed']}`", "", "## External actions", ""]
    for key, value in EXTERNAL_ACTIONS_OFF.items():
        lines.append(f"- {key}: `{value}`")
    lines += ["- no_signal_discord_policy: `DO_NOT_NOTIFY_ON_NO_SIGNAL`", "", "## CoreB mapping", "", f"- rule_universe_count: `{summary['rule_universe_count']}`", f"- mapped_condition_count: `{summary['mapped_condition_count']}`", f"- unmapped_condition_count: `{summary['unmapped_condition_count']}`", f"- output_mapping_path: `{summary['output_mapping_path']}`", "", "## Important", "", "CoreB is audit mapping-ready, but final signal and step 13 remain blocked until CoreA/arbitration/preflight are resolved."]
    return "\n".join(lines)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    audit_dir = Path(args.audit_output_dir).expanduser().resolve() if args.audit_output_dir else default_audit_output_dir()
    audit_dir.mkdir(parents=True, exist_ok=True)
    checks: List[PolicyCheck] = []
    policy = load_json_or_none("policy", resolve_repo_path(args.policy), checks) or {}
    policy_ok = validate_policy_safety(policy, checks) if policy else False
    coreb_frozen = load_json_or_none("coreb_frozen", resolve_repo_path(args.coreb_frozen), checks)
    source_def = load_json_or_none("coreb_source_definition", resolve_repo_path(args.coreb_source_definition), checks)
    previous_mapping_path = resolve_repo_path(args.coreb_mapping)
    previous_mapping = load_json_or_none("previous_coreb_mapping", previous_mapping_path, checks)
    source_ok = validate_source_definition(source_def, checks) if source_def else False
    if not (policy_ok and source_ok and source_def):
        pd.DataFrame([asdict(c) for c in checks]).to_csv(audit_dir / "gold_v2_coreb_live_evaluator_mapping_policy_checks.csv", index=False, encoding="utf-8-sig")
        print("[STOP] CoreB source definition mapping validation failed.")
        return 2
    mapping = build_mapping(source_def, previous_mapping)
    write_json(audit_dir / "previous_live_evaluator_mapping_coreB_20260603.json", previous_mapping or {})
    write_json(previous_mapping_path, mapping)
    write_json(audit_dir / "live_evaluator_mapping_coreB_20260603.json", mapping)
    rules_flat = flatten_rules(mapping["mapped_rules"])
    cond_flat = flatten_conditions(mapping["mapped_rules"])
    pd.DataFrame(rules_flat).to_csv(audit_dir / "gold_v2_coreb_live_evaluator_mapping_rules.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(cond_flat).to_csv(audit_dir / "gold_v2_coreb_live_evaluator_mapping_conditions.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame([asdict(c) for c in checks]).to_csv(audit_dir / "gold_v2_coreb_live_evaluator_mapping_policy_checks.csv", index=False, encoding="utf-8-sig")
    summary = {
        "created_utc": mapping["created_utc"],
        "status": mapping["status"],
        "audit_only": True,
        "policy_safety_ok": bool(policy_ok),
        "source_definition_ok": bool(source_ok),
        "component": COREB_COMPONENT,
        "rule_universe_count": int(mapping["rule_universe_count"]),
        "mapped_condition_count": int(len(mapping["mapped_conditions"])),
        "unmapped_condition_count": int(len(mapping["unmapped_conditions"])),
        "previous_mapping_status": mapping.get("previous_mapping_status"),
        "previous_unmapped_condition_count": mapping.get("previous_unmapped_condition_count"),
        "output_mapping_path": str(previous_mapping_path),
        "audit_output_dir": str(audit_dir),
        "live_evaluator_ready": True,
        "component_signal_allowed": False,
        "live_evaluator_connection_allowed": False,
        "final_signal_allowed": False,
        "step13_allowed": False,
        "external_actions": dict(EXTERNAL_ACTIONS_OFF),
        "no_signal_discord_policy": "DO_NOT_NOTIFY_ON_NO_SIGNAL",
    }
    write_json(audit_dir / "gold_v2_coreb_live_evaluator_mapping_from_source_definition_summary.json", summary)
    (audit_dir / "GOLD_V2_COREB_LIVE_EVALUATOR_MAPPING_FROM_SOURCE_DEFINITION_AUDIT_ONLY_REPORT.md").write_text(build_report(summary), encoding="utf-8")
    print(f"[DONE] status={summary['status']} audit_dir={audit_dir}")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print("No Discord notification, MT5 order, AI API call, or live hook was performed.")
    print("CoreB is audit mapping-ready only. Step 13 remains blocked.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
