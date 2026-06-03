#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Map GOLD V2 frozen rule-source manifests to live evaluator mapping JSON.

Audit-only step 12.

This script is intentionally conservative:
  * It does not infer CoreA/CoreB rules from historical ledgers.
  * It does not convert entry_time matches into live signals.
  * It only maps conditions that are explicitly present in frozen source manifests
    in an evaluator-compatible form.
  * Any missing, textual-only, or unsupported condition is emitted as
    UNMAPPED_CONDITION and blocks live evaluator readiness.

No Discord notification, MT5 order, AI API call, or live hook is performed.
NO_SIGNAL notification policy remains DO_NOT_NOTIFY_ON_NO_SIGNAL.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import pandas as pd


POLICY_DEFAULT = "configs/gold_v2/gold_v2_coreA_coreB_medium_policy_20260603.json"
COREA_FROZEN_DEFAULT = "configs/gold_v2/frozen_coreA_fold4_ABC_CAP5_rules_20260603.json"
COREB_FROZEN_DEFAULT = "configs/gold_v2/frozen_coreB_rr125_buy_confluence_rules_20260603.json"
MEDIUM_FROZEN_DEFAULT = "configs/gold_v2/frozen_medium_rules_20260603.json"

COREA_MAPPING_OUT = "live_evaluator_mapping_coreA_20260603.json"
COREB_MAPPING_OUT = "live_evaluator_mapping_coreB_20260603.json"
MEDIUM_MAPPING_OUT = "live_evaluator_mapping_medium_20260603.json"

SUPPORTED_CONDITION_SUFFIXES = {
    "_min": ">=",
    "_max": "<=",
    "_eq": "==",
}


@dataclass
class AuditRow:
    component: str
    check_name: str
    status: str
    message: str
    detail: str = ""


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Map GOLD V2 frozen rule sources to live evaluator mappings in audit-only mode"
    )
    p.add_argument("--policy", default=POLICY_DEFAULT)
    p.add_argument("--corea-frozen", default=COREA_FROZEN_DEFAULT)
    p.add_argument("--coreb-frozen", default=COREB_FROZEN_DEFAULT)
    p.add_argument("--medium-frozen", default=MEDIUM_FROZEN_DEFAULT)
    p.add_argument("--output-config-dir", default="configs/gold_v2")
    p.add_argument("--audit-output-dir", default=None)
    p.add_argument(
        "--allow-unmapped-exit-zero",
        action="store_true",
        help="Write audit outputs and exit 0 even when UNMAPPED_CONDITION exists. Default blocks with exit code 2.",
    )
    p.add_argument(
        "--skip-source-file-sha-verify",
        action="store_true",
        help="Do not recalculate sha256 for manifest source_files that are accessible on disk.",
    )
    return p.parse_args(argv)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def files_dir_from_repo() -> Path:
    root = repo_root()
    if len(root.parents) >= 2:
        return root.parents[1]
    return root.parent


def default_audit_output_dir() -> Path:
    return files_dir_from_repo() / "FX_OUTPUTS" / "gold_v2_live_evaluator_mapping_audit_only"


def resolve_repo_path(text: str) -> Path:
    p = Path(text)
    if p.is_absolute():
        return p
    return (repo_root() / p).resolve()


def resolve_manifest_source_path(text: Any) -> Optional[Path]:
    if text is None:
        return None
    path_text = str(text)
    if not path_text:
        return None
    p = Path(path_text)
    if p.is_absolute():
        return p
    normalized = path_text.replace("\\", "/")
    if normalized.startswith("Files/"):
        return (files_dir_from_repo() / normalized[len("Files/"):]).resolve()
    return (repo_root() / p).resolve()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b=""):
            h.update(chunk)
    return h.hexdigest()


def read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")


def add_audit(rows: List[AuditRow], component: str, check_name: str, ok: bool, message: str, detail: str = "") -> None:
    rows.append(AuditRow(component, check_name, "OK" if ok else "ERROR", message, detail))


def load_required_json(component: str, path: Path, audit_rows: List[AuditRow]) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    if not path.exists():
        add_audit(audit_rows, component, "json_exists", False, f"missing: {path}")
        return None, "SOURCE_JSON_MISSING"
    add_audit(audit_rows, component, "json_exists", True, str(path))
    try:
        data = read_json(path)
    except Exception as exc:
        add_audit(audit_rows, component, "json_parse", False, "JSON parse failed", repr(exc))
        return None, "SOURCE_JSON_PARSE_ERROR"
    add_audit(audit_rows, component, "json_parse", True, "JSON parsed")
    return data, None


def validate_policy_safety(policy: Dict[str, Any], audit_rows: List[AuditRow]) -> bool:
    safety = policy.get("safety", {})
    ok = True
    for key in ["ai_api_enabled", "discord_enabled", "mt5_order_enabled", "live_hook_enabled"]:
        flag_ok = safety.get(key) is False
        ok = ok and flag_ok
        add_audit(audit_rows, "POLICY", f"safety_{key}_false", flag_ok, f"{key}={safety.get(key)!r}")
    audit_ok = safety.get("audit_only") is True
    ok = ok and audit_ok
    add_audit(audit_rows, "POLICY", "safety_audit_only_true", audit_ok, f"audit_only={safety.get('audit_only')!r}")
    return ok


def validate_manifest_common(component: str, manifest: Optional[Dict[str, Any]], audit_rows: List[AuditRow]) -> bool:
    if manifest is None:
        return False
    status_ok = manifest.get("status") == "FROZEN_RULE_SOURCE_READY"
    add_audit(audit_rows, component, "frozen_status_ready", status_ok, f"status={manifest.get('status')!r}")
    approx_ok = manifest.get("approximation_allowed") is False
    add_audit(audit_rows, component, "approximation_disallowed", approx_ok, f"approximation_allowed={manifest.get('approximation_allowed')!r}")
    external_ok = manifest.get("external_actions_allowed") is False
    add_audit(audit_rows, component, "external_actions_disallowed", external_ok, f"external_actions_allowed={manifest.get('external_actions_allowed')!r}")
    return status_ok and approx_ok and external_ok


def audit_source_files(component: str, manifest: Optional[Dict[str, Any]], audit_rows: List[AuditRow], *, skip_sha_verify: bool) -> List[Dict[str, Any]]:
    if manifest is None:
        return []
    out: List[Dict[str, Any]] = []
    for idx, src in enumerate(manifest.get("source_files", []) or []):
        rec = dict(src) if isinstance(src, dict) else {"raw": src}
        rec["source_index"] = idx
        rec["manifest_status"] = rec.get("status")
        rec["manifest_sha256"] = rec.get("sha256")
        source_path = resolve_manifest_source_path(rec.get("path"))
        rec["resolved_path"] = str(source_path) if source_path else None
        if source_path is None:
            rec["disk_status"] = "NO_PATH"
            add_audit(audit_rows, component, f"source_file_{idx}_path", False, "source file path missing")
        elif not source_path.exists():
            rec["disk_status"] = "NOT_ACCESSIBLE_FOR_MAPPING_SHA_VERIFY"
            add_audit(audit_rows, component, f"source_file_{idx}_accessible", True, f"not accessible here; using frozen manifest path={source_path}")
        elif skip_sha_verify:
            rec["disk_status"] = "ACCESSIBLE_SHA_VERIFY_SKIPPED"
            add_audit(audit_rows, component, f"source_file_{idx}_accessible", True, f"accessible sha skipped: {source_path}")
        else:
            actual = sha256_file(source_path)
            rec["disk_status"] = "ACCESSIBLE_SHA_VERIFIED" if actual == rec.get("sha256") else "ACCESSIBLE_SHA_MISMATCH"
            rec["actual_sha256"] = actual
            sha_ok = actual == rec.get("sha256")
            add_audit(audit_rows, component, f"source_file_{idx}_sha_match", sha_ok, f"path={source_path}", f"manifest={rec.get('sha256')} actual={actual}")
        out.append(rec)
    return out


def source_file_fingerprints(source_files: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [
        {
            "path": src.get("path"),
            "resolved_path": src.get("resolved_path"),
            "manifest_status": src.get("manifest_status") or src.get("status"),
            "sha256": src.get("manifest_sha256") or src.get("sha256"),
            "row_count": src.get("row_count"),
            "columns": src.get("columns", []),
            "disk_status": src.get("disk_status"),
            "actual_sha256": src.get("actual_sha256"),
        }
        for src in source_files
    ]


def find_explicit_mapping_block(manifest: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    definition = manifest.get("definition", {}) if isinstance(manifest.get("definition"), dict) else {}
    for item in [
        manifest.get("live_evaluator_mapping"),
        manifest.get("evaluator_mapping"),
        definition.get("live_evaluator_mapping"),
        definition.get("evaluator_mapping"),
    ]:
        if isinstance(item, dict) and item:
            return item
    return None


def normalize_explicit_conditions(component: str, mapping_block: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    unmapped: List[Dict[str, Any]] = []
    conditions = mapping_block.get("conditions")
    if not isinstance(conditions, list) or not conditions:
        unmapped.append({"component": component, "condition_id": "explicit_conditions_schema", "status": "UNMAPPED_CONDITION", "reason": "No explicit live_evaluator_mapping.conditions list exists in the frozen manifest.", "blocking": True})
        return [], unmapped
    out: List[Dict[str, Any]] = []
    for i, cond in enumerate(conditions):
        if not isinstance(cond, dict):
            unmapped.append({"component": component, "condition_id": f"condition_{i}", "status": "UNMAPPED_CONDITION", "reason": "Condition is not an object.", "raw_condition": repr(cond), "blocking": True})
            continue
        field = cond.get("field")
        op = cond.get("operator")
        value = cond.get("value")
        if not field or op not in {">=", "<=", "==", ">", "<", "in"}:
            unmapped.append({"component": component, "condition_id": f"condition_{i}", "status": "UNMAPPED_CONDITION", "reason": "Condition lacks a supported explicit field/operator/value schema.", "raw_condition": cond, "blocking": True})
            continue
        out.append({"condition_id": cond.get("condition_id") or f"{component}_explicit_{i}", "field": str(field), "operator": str(op), "value": value, "source": cond.get("source", "frozen_manifest.live_evaluator_mapping"), "mapping_status": "MAPPED_EXPLICIT_CONDITION"})
    return out, unmapped


def build_unmapped(component: str, condition_id: str, reason: str, raw: Any = None) -> Dict[str, Any]:
    rec: Dict[str, Any] = {"component": component, "condition_id": condition_id, "status": "UNMAPPED_CONDITION", "reason": reason, "blocking": True}
    if raw is not None:
        rec["raw_source"] = raw
    return rec


def build_coreA_mapping(manifest: Optional[Dict[str, Any]], policy: Dict[str, Any], source_files: List[Dict[str, Any]]) -> Dict[str, Any]:
    component = "HIGH_A_CoreA_fold4_ABC_CAP5"
    unmapped: List[Dict[str, Any]] = []
    mapped_conditions: List[Dict[str, Any]] = []
    required_features: List[str] = []
    if manifest is None:
        unmapped.append(build_unmapped(component, "frozen_manifest", "CoreA frozen manifest is missing."))
    else:
        explicit = find_explicit_mapping_block(manifest)
        if explicit:
            mapped_conditions, unmapped = normalize_explicit_conditions(component, explicit)
            required_features = [str(x) for x in explicit.get("required_features", [])] if isinstance(explicit.get("required_features"), list) else []
        else:
            definition = manifest.get("definition", {})
            unmapped.extend([
                build_unmapped(component, "fold4_rules", "Frozen CoreA manifest names fold4_rules but does not contain explicit live-evaluable fold4 rule conditions.", definition.get("ruleset") if isinstance(definition, dict) else definition),
                build_unmapped(component, "ABC_entry_gate", "Frozen CoreA manifest names ABC entry gate but does not contain explicit A/B/C gate predicates.", definition.get("entry_gate") if isinstance(definition, dict) else definition),
                build_unmapped(component, "A_CAP5_BC_CAP3_classification", "Sizing/classification cannot be mapped without explicit A/B/C classification conditions.", definition.get("sizing") if isinstance(definition, dict) else definition),
                build_unmapped(component, "variant_defined_tp_sl_policy", "TP/SL are variant-defined in the manifest, but no explicit live variant selector is present.", definition.get("known_tp_sl_policy") if isinstance(definition, dict) else definition),
            ])
    mapping_status = "MAPPING_READY" if mapped_conditions and not unmapped else "MAPPING_BLOCKED_UNMAPPED_CONDITION"
    return {
        "mapping_id": "LIVE_EVALUATOR_MAPPING_GOLD_V2_COREA_20260603",
        "component": component,
        "policy_id": policy.get("policy_id"),
        "frozen_policy_id": manifest.get("policy_id") if manifest else None,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": mapping_status,
        "audit_only": True,
        "approximation_allowed": False,
        "external_actions_allowed": False,
        "historical_entry_time_match_allowed": False,
        "source_of_truth": {"type": manifest.get("source_of_truth_type") if manifest else None, "frozen_manifest_required": True, "source_files": source_file_fingerprints(source_files)},
        "policy_snapshot": {"priority": policy.get("coreA", {}).get("priority"), "name": policy.get("coreA", {}).get("name"), "sizing": policy.get("coreA", {}).get("sizing"), "lot_multiplier": policy.get("coreA", {}).get("lot_multiplier")},
        "required_features": required_features,
        "mapped_conditions": mapped_conditions,
        "unmapped_conditions": unmapped,
        "live_evaluator_ready": mapping_status == "MAPPING_READY",
        "final_signal_allowed": False,
        "blocked_reason": None if mapping_status == "MAPPING_READY" else "CoreA has UNMAPPED_CONDITION entries; do not connect to live evaluator.",
    }


def build_coreB_mapping(manifest: Optional[Dict[str, Any]], policy: Dict[str, Any], source_files: List[Dict[str, Any]]) -> Dict[str, Any]:
    component = "HIGH_B_CoreB_RR125_BUY_CONFLUENCE"
    unmapped: List[Dict[str, Any]] = []
    mapped_conditions: List[Dict[str, Any]] = []
    required_features: List[str] = []
    if manifest is None:
        unmapped.append(build_unmapped(component, "frozen_manifest", "CoreB frozen manifest is missing."))
    else:
        explicit = find_explicit_mapping_block(manifest)
        if explicit:
            mapped_conditions, unmapped = normalize_explicit_conditions(component, explicit)
            required_features = [str(x) for x in explicit.get("required_features", [])] if isinstance(explicit.get("required_features"), list) else []
        else:
            definition = manifest.get("definition", {})
            unmapped.extend([
                build_unmapped(component, "RR1_source_BUY_rule_definitions", "Frozen CoreB manifest references RR1.0-derived BUY rules but does not include explicit selected-rule predicates.", definition.get("source_rules") if isinstance(definition, dict) else definition),
                build_unmapped(component, "same_count_confluence_derivation", "same_count>=15 is explicit, but the live same_count derivation and source rule universe are not explicit in the manifest.", {"same_count_min": definition.get("same_count_min")} if isinstance(definition, dict) else definition),
                build_unmapped(component, "rr125_tp_sl_conversion", "TP=1.25*SL is explicit, but the live SL source/variant selector is not explicitly mappable.", definition.get("tp_policy") if isinstance(definition, dict) else definition),
            ])
    mapping_status = "MAPPING_READY" if mapped_conditions and not unmapped else "MAPPING_BLOCKED_UNMAPPED_CONDITION"
    return {
        "mapping_id": "LIVE_EVALUATOR_MAPPING_GOLD_V2_COREB_20260603",
        "component": component,
        "policy_id": policy.get("policy_id"),
        "frozen_policy_id": manifest.get("policy_id") if manifest else None,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": mapping_status,
        "audit_only": True,
        "approximation_allowed": False,
        "external_actions_allowed": False,
        "historical_entry_time_match_allowed": False,
        "source_of_truth": {"type": manifest.get("source_of_truth_type") if manifest else None, "frozen_manifest_required": True, "source_files": source_file_fingerprints(source_files)},
        "policy_snapshot": {"priority": policy.get("coreB", {}).get("priority"), "name": policy.get("coreB", {}).get("name"), "direction": policy.get("coreB", {}).get("direction"), "rr": policy.get("coreB", {}).get("rr"), "same_count_min": policy.get("coreB", {}).get("same_count_min"), "sizing": policy.get("coreB", {}).get("sizing"), "lot_multiplier": policy.get("coreB", {}).get("lot_multiplier")},
        "required_features": required_features,
        "mapped_conditions": mapped_conditions,
        "unmapped_conditions": unmapped,
        "live_evaluator_ready": mapping_status == "MAPPING_READY",
        "final_signal_allowed": False,
        "blocked_reason": None if mapping_status == "MAPPING_READY" else "CoreB has UNMAPPED_CONDITION entries; do not connect to live evaluator.",
    }


def parse_threshold_conditions(component: str, rule_name: str, conditions: Dict[str, Any], *, source: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[str]]:
    mapped: List[Dict[str, Any]] = []
    unmapped: List[Dict[str, Any]] = []
    features: List[str] = []
    if not isinstance(conditions, dict) or not conditions:
        unmapped.append(build_unmapped(component, f"{rule_name}.conditions", "Rule has no explicit threshold condition object.", conditions))
        return mapped, unmapped, features
    for key, expected in conditions.items():
        matched = False
        for suffix, op in SUPPORTED_CONDITION_SUFFIXES.items():
            if str(key).endswith(suffix):
                field = str(key)[: -len(suffix)]
                features.append(field)
                mapped.append({"condition_id": f"{rule_name}.{key}", "rule_name": rule_name, "field": field, "operator": op, "value": expected, "source": source, "mapping_status": "MAPPED_EXPLICIT_THRESHOLD"})
                matched = True
                break
        if not matched:
            unmapped.append(build_unmapped(component, f"{rule_name}.{key}", "Unsupported condition key. Only *_min, *_max, and *_eq are live-mappable in step 12.", {key: expected}))
    return mapped, unmapped, sorted(set(features))


def build_medium_mapping(manifest: Optional[Dict[str, Any]], policy: Dict[str, Any], source_files: List[Dict[str, Any]]) -> Dict[str, Any]:
    component = "MEDIUM_REFINED_FEATURE_GATES"
    mapped_rules: List[Dict[str, Any]] = []
    unmapped: List[Dict[str, Any]] = []
    required_features: List[str] = []
    rules = None
    if manifest is not None:
        definition = manifest.get("definition", {})
        if isinstance(definition, dict):
            rules = definition.get("rules")
    if not isinstance(rules, list) or not rules:
        unmapped.append(build_unmapped(component, "medium.rules", "Frozen MEDIUM manifest does not contain explicit definition.rules.", manifest.get("definition") if manifest else None))
    else:
        policy_priority_order = policy.get("medium", {}).get("priority_order", [])
        for idx, rule in enumerate(rules):
            if not isinstance(rule, dict):
                unmapped.append(build_unmapped(component, f"medium.rule_{idx}", "Rule is not an object.", rule))
                continue
            name = str(rule.get("name") or f"RULE_{idx}")
            direction = str(rule.get("direction") or "")
            mapped_conditions, rule_unmapped, features = parse_threshold_conditions(component, name, rule.get("conditions", {}), source="frozen_medium_manifest.definition.rules")
            required_features.extend(features)
            unmapped.extend(rule_unmapped)
            mapped_rules.append({
                "rule_name": name,
                "priority_index": policy_priority_order.index(name) if name in policy_priority_order else idx,
                "direction": direction,
                "lot_multiplier_candidate": policy.get("medium", {}).get("default_lot_multiplier", 0.5),
                "conditions": mapped_conditions,
                "unmapped_conditions": rule_unmapped,
                "feature_gate_evaluable": bool(mapped_conditions) and not rule_unmapped,
                "signal_eligible_without_core_arbitration": False,
                "blocked_reason": "MEDIUM feature gates are mappable, but final signal eligibility remains blocked until CoreA/CoreB arbitration is mapped.",
            })
    has_unmapped = bool(unmapped)
    has_mapped = any(rule.get("feature_gate_evaluable") for rule in mapped_rules)
    mapping_status = "MAPPED_FEATURE_GATES_ONLY_BLOCKED_FOR_FINAL_SIGNAL" if has_mapped and not has_unmapped else "MAPPING_BLOCKED_UNMAPPED_CONDITION"
    return {
        "mapping_id": "LIVE_EVALUATOR_MAPPING_GOLD_V2_MEDIUM_20260603",
        "component": component,
        "policy_id": policy.get("policy_id"),
        "frozen_policy_id": manifest.get("policy_id") if manifest else None,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": mapping_status,
        "audit_only": True,
        "approximation_allowed": False,
        "external_actions_allowed": False,
        "historical_entry_time_match_allowed": False,
        "source_of_truth": {"type": manifest.get("source_of_truth_type") if manifest else None, "frozen_manifest_required": True, "source_files": source_file_fingerprints(source_files)},
        "policy_snapshot": {"priority": policy.get("medium", {}).get("priority"), "default_lot_multiplier": policy.get("medium", {}).get("default_lot_multiplier"), "precedence_rule": policy.get("medium", {}).get("precedence_rule"), "priority_order": policy.get("medium", {}).get("priority_order")},
        "required_features": sorted(set(required_features)),
        "mapped_rules": sorted(mapped_rules, key=lambda r: int(r.get("priority_index", 9999))),
        "unmapped_conditions": unmapped,
        "live_evaluator_ready": False,
        "feature_gate_ready": has_mapped and not has_unmapped,
        "final_signal_allowed": False,
        "blocked_reason": "MEDIUM cannot become a final signal until CoreA/CoreB mapping and arbitration are explicitly implemented.",
    }


def flatten_unmapped(mappings: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for m in mappings:
        for item in m.get("unmapped_conditions", []) or []:
            rec = dict(item)
            rec.setdefault("component", m.get("component"))
            rec["mapping_id"] = m.get("mapping_id")
            rows.append(rec)
        for rule in m.get("mapped_rules", []) or []:
            for item in rule.get("unmapped_conditions", []) or []:
                rec = dict(item)
                rec.setdefault("component", m.get("component"))
                rec["mapping_id"] = m.get("mapping_id")
                rec["rule_name"] = rule.get("rule_name")
                rows.append(rec)
    return rows


def build_summary(*, policy_path: Path, corea_path: Path, coreb_path: Path, medium_path: Path, config_dir: Path, audit_dir: Path, policy_ok: bool, mappings: List[Dict[str, Any]], audit_rows: List[AuditRow]) -> Dict[str, Any]:
    unmapped_rows = flatten_unmapped(mappings)
    blocking_unmapped = [r for r in unmapped_rows if r.get("blocking") is True]
    return {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "BLOCKED_UNMAPPED_CONDITION" if blocking_unmapped or not policy_ok else "MAPPING_AUDIT_READY",
        "policy_path": str(policy_path),
        "corea_frozen_path": str(corea_path),
        "coreb_frozen_path": str(coreb_path),
        "medium_frozen_path": str(medium_path),
        "output_config_dir": str(config_dir),
        "audit_output_dir": str(audit_dir),
        "audit_only": True,
        "external_actions": {"discord_send_allowed": False, "mt5_order_allowed": False, "ai_api_allowed": False, "live_hook_allowed": False},
        "no_signal_discord_policy": "DO_NOT_NOTIFY_ON_NO_SIGNAL",
        "mapping_statuses": {m.get("component"): m.get("status") for m in mappings},
        "unmapped_condition_count": int(len(unmapped_rows)),
        "blocking_unmapped_condition_count": int(len(blocking_unmapped)),
        "policy_safety_ok": bool(policy_ok),
        "live_evaluator_connection_allowed": False,
        "stop_condition": "UNMAPPED_CONDITION exists; do not run live evaluator mapping as a signal source." if blocking_unmapped else None,
        "audit_error_count": int(sum(1 for r in audit_rows if r.status != "OK")),
    }


def build_report(summary: Dict[str, Any], mappings: List[Dict[str, Any]], unmapped_rows: List[Dict[str, Any]]) -> str:
    lines: List[str] = []
    lines.append("# GOLD V2 live evaluator mapping audit-only report")
    lines.append("")
    lines.append(f"Created UTC: {summary['created_utc']}")
    lines.append(f"Status: `{summary['status']}`")
    lines.append(f"Audit only: `{summary['audit_only']}`")
    lines.append("")
    lines.append("## External actions")
    lines.append("")
    for key, value in summary["external_actions"].items():
        lines.append(f"- {key}: `{value}`")
    lines.append(f"- no_signal_discord_policy: `{summary['no_signal_discord_policy']}`")
    lines.append("")
    lines.append("## Mapping status")
    lines.append("")
    for mapping in mappings:
        lines.append(f"### {mapping['component']}")
        lines.append(f"- status: `{mapping['status']}`")
        lines.append(f"- live_evaluator_ready: `{mapping.get('live_evaluator_ready')}`")
        if "feature_gate_ready" in mapping:
            lines.append(f"- feature_gate_ready: `{mapping.get('feature_gate_ready')}`")
        lines.append(f"- final_signal_allowed: `{mapping.get('final_signal_allowed')}`")
        lines.append(f"- blocked_reason: {mapping.get('blocked_reason') or '-'}")
        src_files = mapping.get("source_of_truth", {}).get("source_files", [])
        if src_files:
            lines.append("- source files:")
            for src in src_files:
                lines.append(f"  - `{src.get('path')}` status=`{src.get('manifest_status')}` rows=`{src.get('row_count')}` sha256=`{src.get('sha256')}`")
        lines.append("")
    lines.append("## UNMAPPED_CONDITION")
    lines.append("")
    if not unmapped_rows:
        lines.append("_No unmapped conditions._")
    else:
        lines.append("| component | condition_id | reason | blocking |")
        lines.append("| --- | --- | --- | --- |")
        for row in unmapped_rows:
            reason = str(row.get("reason", "")).replace("|", "\\|")
            lines.append(f"| {row.get('component')} | `{row.get('condition_id')}` | {reason} | `{row.get('blocking')}` |")
    lines.append("")
    lines.append("## Stop condition")
    lines.append("")
    lines.append(summary.get("stop_condition") or "No blocking unmapped condition was found, but live evaluator connection remains a later explicit step.")
    lines.append("")
    lines.append("No Discord notification, MT5 order, AI API call, or live hook is performed.")
    return "\n".join(lines)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    policy_path = resolve_repo_path(args.policy)
    corea_path = resolve_repo_path(args.corea_frozen)
    coreb_path = resolve_repo_path(args.coreb_frozen)
    medium_path = resolve_repo_path(args.medium_frozen)
    config_dir = resolve_repo_path(args.output_config_dir)
    audit_dir = Path(args.audit_output_dir).expanduser().resolve() if args.audit_output_dir else default_audit_output_dir()
    config_dir.mkdir(parents=True, exist_ok=True)
    audit_dir.mkdir(parents=True, exist_ok=True)

    audit_rows: List[AuditRow] = []
    policy, policy_error = load_required_json("POLICY", policy_path, audit_rows)
    if policy is None:
        policy = {}
    policy_ok = policy_error is None and validate_policy_safety(policy, audit_rows)

    corea, _ = load_required_json("HIGH_A_CoreA_fold4_ABC_CAP5", corea_path, audit_rows)
    coreb, _ = load_required_json("HIGH_B_CoreB_RR125_BUY_CONFLUENCE", coreb_path, audit_rows)
    medium, _ = load_required_json("MEDIUM_REFINED_FEATURE_GATES", medium_path, audit_rows)

    corea_ok = validate_manifest_common("HIGH_A_CoreA_fold4_ABC_CAP5", corea, audit_rows)
    coreb_ok = validate_manifest_common("HIGH_B_CoreB_RR125_BUY_CONFLUENCE", coreb, audit_rows)
    medium_ok = validate_manifest_common("MEDIUM_REFINED_FEATURE_GATES", medium, audit_rows)

    corea_sources = audit_source_files("HIGH_A_CoreA_fold4_ABC_CAP5", corea, audit_rows, skip_sha_verify=bool(args.skip_source_file_sha_verify))
    coreb_sources = audit_source_files("HIGH_B_CoreB_RR125_BUY_CONFLUENCE", coreb, audit_rows, skip_sha_verify=bool(args.skip_source_file_sha_verify))
    medium_sources = audit_source_files("MEDIUM_REFINED_FEATURE_GATES", medium, audit_rows, skip_sha_verify=bool(args.skip_source_file_sha_verify))

    if not corea_ok:
        corea = corea if corea is not None else None
    if not coreb_ok:
        coreb = coreb if coreb is not None else None
    if not medium_ok:
        medium = medium if medium is not None else None

    mappings = [
        build_coreA_mapping(corea, policy, corea_sources),
        build_coreB_mapping(coreb, policy, coreb_sources),
        build_medium_mapping(medium, policy, medium_sources),
    ]

    for filename, obj in [(COREA_MAPPING_OUT, mappings[0]), (COREB_MAPPING_OUT, mappings[1]), (MEDIUM_MAPPING_OUT, mappings[2])]:
        write_json(config_dir / filename, obj)
        write_json(audit_dir / filename, obj)

    unmapped_rows = flatten_unmapped(mappings)
    summary = build_summary(policy_path=policy_path, corea_path=corea_path, coreb_path=coreb_path, medium_path=medium_path, config_dir=config_dir, audit_dir=audit_dir, policy_ok=policy_ok, mappings=mappings, audit_rows=audit_rows)

    status_rows = []
    for mapping in mappings:
        status_rows.append({
            "component": mapping.get("component"),
            "mapping_id": mapping.get("mapping_id"),
            "status": mapping.get("status"),
            "live_evaluator_ready": mapping.get("live_evaluator_ready"),
            "feature_gate_ready": mapping.get("feature_gate_ready"),
            "final_signal_allowed": mapping.get("final_signal_allowed"),
            "unmapped_condition_count": len(mapping.get("unmapped_conditions", []) or []),
            "blocked_reason": mapping.get("blocked_reason"),
        })

    pd.DataFrame(status_rows).to_csv(audit_dir / "gold_v2_live_evaluator_mapping_status.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame([asdict(r) for r in audit_rows]).to_csv(audit_dir / "gold_v2_live_evaluator_mapping_audit_checks.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(unmapped_rows).to_csv(audit_dir / "gold_v2_live_evaluator_mapping_unmapped_conditions.csv", index=False, encoding="utf-8-sig")
    write_json(audit_dir / "gold_v2_live_evaluator_mapping_summary.json", summary)
    (audit_dir / "GOLD_V2_LIVE_EVALUATOR_MAPPING_AUDIT_ONLY_REPORT.md").write_text(build_report(summary, mappings, unmapped_rows), encoding="utf-8")

    print(f"[DONE] status={summary['status']} audit_dir={audit_dir}")
    print(pd.DataFrame(status_rows).to_string(index=False))
    if unmapped_rows:
        print("")
        print("[STOP] UNMAPPED_CONDITION detected. Live evaluator connection remains blocked.")
        print(f"unmapped_condition_count={len(unmapped_rows)}")
        print("No Discord notification, MT5 order, AI API call, or live hook was performed.")
        return 0 if args.allow_unmapped_exit_zero else 2
    if not policy_ok:
        print("")
        print("[STOP] Policy safety check failed. External actions remain blocked.")
        return 2
    print("")
    print("[OK] Mapping audit completed. This step only writes mapping JSON; live evaluator connection is still a later explicit step.")
    print("No Discord notification, MT5 order, AI API call, or live hook was performed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
