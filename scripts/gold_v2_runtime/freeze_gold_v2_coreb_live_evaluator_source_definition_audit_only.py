#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""GOLD V2 12F: freeze CoreB live evaluator source definition audit-only.

This creates a CoreB-only frozen source definition JSON from 12E outputs.
It does not mark live evaluator mappings as ready and does not connect step 13.
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
COREB_MAPPING_DEFAULT = "configs/gold_v2/live_evaluator_mapping_coreB_20260603.json"
COREB_COMPONENT = "HIGH_B_CoreB_RR125_BUY_CONFLUENCE"
STATUS_READY = "FROZEN_COREB_LIVE_EVALUATOR_SOURCE_DEFINITION_READY_AUDIT_ONLY"
EXTERNAL_ACTIONS_OFF = {"discord_send_allowed": False, "mt5_order_allowed": False, "ai_api_allowed": False, "live_hook_allowed": False}

@dataclass
class PolicyCheck:
    check_name: str
    status: str
    message: str
    detail: str = ""


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Freeze CoreB live evaluator source definition audit-only")
    p.add_argument("--policy", default=POLICY_DEFAULT)
    p.add_argument("--coreb-frozen", default=COREB_FROZEN_DEFAULT)
    p.add_argument("--coreb-mapping", default=COREB_MAPPING_DEFAULT)
    p.add_argument("--readiness-dir", default=None)
    p.add_argument("--output-config-dir", default="configs/gold_v2")
    p.add_argument("--audit-output-dir", default=None)
    return p.parse_args(argv)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def files_dir_from_repo() -> Path:
    root = repo_root()
    return root.parents[1] if len(root.parents) >= 2 else root.parent


def default_readiness_dir() -> Path:
    return files_dir_from_repo() / "FX_OUTPUTS" / "gold_v2_coreb_source_rule_universe_freeze_readiness_audit_only"


def default_audit_output_dir() -> Path:
    return files_dir_from_repo() / "FX_OUTPUTS" / "gold_v2_coreb_live_evaluator_source_definition_freeze_audit_only"


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


def read_csv_required(label: str, path: Path, checks: List[PolicyCheck]) -> pd.DataFrame:
    if not path.exists():
        add_check(checks, f"{label}_exists", False, f"missing: {path}")
        return pd.DataFrame()
    add_check(checks, f"{label}_exists", True, str(path))
    try:
        df = pd.read_csv(path)
    except Exception as exc:
        add_check(checks, f"{label}_read", False, "CSV read failed", repr(exc))
        return pd.DataFrame()
    add_check(checks, f"{label}_read", True, f"rows={len(df)} cols={len(df.columns)}")
    return df


def to_json_scalar(value: Any) -> Any:
    if pd.isna(value):
        return None
    if isinstance(value, (int, float, str, bool)):
        return value
    try:
        return value.item()
    except Exception:
        return str(value)


def predicate_rows_for_rule(rule_id: str, cond_df: pd.DataFrame) -> List[Dict[str, Any]]:
    if cond_df.empty:
        return []
    out: List[Dict[str, Any]] = []
    sub = cond_df[cond_df["rule_id"].astype(str) == str(rule_id)].copy()
    sort_cols = [c for c in ["source_column", "condition_index"] if c in sub.columns]
    if sort_cols:
        sub = sub.sort_values(sort_cols)
    for _, row in sub.iterrows():
        out.append({
            "source_column": to_json_scalar(row.get("source_column")),
            "condition_index": to_json_scalar(row.get("condition_index")),
            "field": to_json_scalar(row.get("field")),
            "operator": to_json_scalar(row.get("operator")),
            "value": to_json_scalar(row.get("value")),
            "raw_text": to_json_scalar(row.get("raw_text")),
        })
    return out


def build_rule_definitions(rule_df: pd.DataFrame, cond_df: pd.DataFrame) -> List[Dict[str, Any]]:
    rules: List[Dict[str, Any]] = []
    for _, row in rule_df.sort_values("rule_id").iterrows():
        rule_id = str(row["rule_id"])
        predicates = predicate_rows_for_rule(rule_id, cond_df)
        base_pred = [p for p in predicates if p.get("source_column") == "base_condition"]
        filter_pred = [p for p in predicates if p.get("source_column") == "added_filter_text"]
        rules.append({
            "rule_id": rule_id,
            "candidate_id": to_json_scalar(row.get("candidate_id")),
            "origin_id": to_json_scalar(row.get("origin_id")),
            "direction": to_json_scalar(row.get("direction")),
            "variant": to_json_scalar(row.get("variant")),
            "tp_pips": to_json_scalar(row.get("tp_pips")),
            "sl_pips": to_json_scalar(row.get("sl_pips")),
            "rr": to_json_scalar(row.get("rr")),
            "rr_bucket": to_json_scalar(row.get("rr_bucket")),
            "policy": to_json_scalar(row.get("policy")),
            "raw_signal_row_count": to_json_scalar(row.get("raw_signal_row_count")),
            "source_text": {
                "base_condition": to_json_scalar(row.get("base_condition")),
                "added_filter_text": to_json_scalar(row.get("added_filter_text")),
            },
            "predicates": predicates,
            "base_condition_predicates": base_pred,
            "added_filter_predicates": filter_pred,
            "freeze_ready_candidate": bool(row.get("freeze_ready_candidate")),
        })
    return rules


def build_report(summary: Dict[str, Any]) -> str:
    lines = ["# GOLD V2 CoreB live evaluator source definition freeze audit-only report", "", f"Created UTC: {summary['created_utc']}", f"Status: `{summary['status']}`", f"Audit only: `{summary['audit_only']}`", f"live_evaluator_mapping_ready: `{summary['live_evaluator_mapping_ready']}`", f"final_signal_allowed: `{summary['final_signal_allowed']}`", "", "## External actions", ""]
    for key, value in EXTERNAL_ACTIONS_OFF.items():
        lines.append(f"- {key}: `{value}`")
    lines += ["- no_signal_discord_policy: `DO_NOT_NOTIFY_ON_NO_SIGNAL`", "", "## Frozen CoreB source definition", "", f"- rule_universe_count: `{summary['rule_universe_count']}`", f"- condition_row_count: `{summary['condition_row_count']}`", f"- same_count_min: `{summary['same_count_min']}`", f"- output_config_path: `{summary['output_config_path']}`", "", "## Important", "", "This JSON is a frozen source definition for a later mapping step. It is not a live evaluator mapping and does not permit step 13."]
    return "\n".join(lines)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    readiness_dir = Path(args.readiness_dir).expanduser().resolve() if args.readiness_dir else default_readiness_dir()
    output_config_dir = resolve_repo_path(args.output_config_dir)
    audit_dir = Path(args.audit_output_dir).expanduser().resolve() if args.audit_output_dir else default_audit_output_dir()
    output_config_dir.mkdir(parents=True, exist_ok=True)
    audit_dir.mkdir(parents=True, exist_ok=True)
    checks: List[PolicyCheck] = []

    policy = load_json_or_none("policy", resolve_repo_path(args.policy), checks) or {}
    policy_ok = validate_policy_safety(policy, checks) if policy else False
    coreb_frozen = load_json_or_none("coreb_frozen", resolve_repo_path(args.coreb_frozen), checks)
    coreb_mapping = load_json_or_none("coreb_mapping", resolve_repo_path(args.coreb_mapping), checks)
    readiness = load_json_or_none("readiness_summary", readiness_dir / "gold_v2_coreb_source_rule_universe_freeze_readiness_summary.json", checks)
    rule_df = read_csv_required("rule_candidates", readiness_dir / "gold_v2_coreb_source_rule_universe_candidates.csv", checks)
    cond_df = read_csv_required("condition_rows", readiness_dir / "gold_v2_coreb_source_rule_condition_rows.csv", checks)
    gaps_df = read_csv_required("freeze_readiness_gaps", readiness_dir / "gold_v2_coreb_freeze_readiness_gaps.csv", checks)
    if gaps_df.empty:
        add_check(checks, "freeze_readiness_gaps_empty_ok", True, "gap file has no rows")

    readiness_ok = bool(readiness and readiness.get("status") == "COREB_SOURCE_RULE_UNIVERSE_FREEZE_READY_AUDIT_ONLY" and int(readiness.get("blocking_gap_count", -1)) == 0)
    add_check(checks, "readiness_status_ok", readiness_ok, str(readiness.get("status") if readiness else None))
    if not rule_df.empty and "freeze_ready_candidate" in rule_df.columns:
        all_rules_ready = bool(rule_df["freeze_ready_candidate"].astype(str).str.lower().isin(["true", "1"]).all())
    else:
        all_rules_ready = False
    add_check(checks, "all_rules_freeze_ready", all_rules_ready, f"rows={len(rule_df)}")

    rules = build_rule_definitions(rule_df, cond_df) if all_rules_ready else []
    frozen_def = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": STATUS_READY if policy_ok and readiness_ok and all_rules_ready else "FROZEN_COREB_LIVE_EVALUATOR_SOURCE_DEFINITION_NOT_READY",
        "audit_only": True,
        "component": COREB_COMPONENT,
        "source_policy": "FROZEN_GOLD_V2_COREB_RR125_BUY_CONFLUENCE_20260603",
        "definition_type": "COREB_LIVE_EVALUATOR_SOURCE_DEFINITION",
        "direction": "BUY",
        "same_count_min": 15,
        "same_count_derivation": {
            "method": "count simultaneous hits across frozen CoreB source_rule_universe",
            "source_rule_universe_count": len(rules),
            "minimum_count": 15,
            "note": "Do not use historical entry_time as future signal source. Recompute hits live from predicates.",
        },
        "rr_policy": {
            "tp_formula": "1.25 * sl_pips",
            "rr": 1.25,
            "direction": "BUY",
        },
        "sizing": "CAP3",
        "lot_multiplier_candidate": 1.0,
        "rule_universe_count": len(rules),
        "source_rule_universe": rules,
        "source_files": coreb_frozen.get("source_files", []) if coreb_frozen else [],
        "readiness_summary": readiness,
        "source_mapping_status_before_freeze": coreb_mapping.get("status") if coreb_mapping else None,
        "source_unmapped_condition_count_before_freeze": int(len(coreb_mapping.get("unmapped_conditions", []) or [])) if coreb_mapping else None,
        "live_evaluator_mapping_ready": False,
        "final_signal_allowed": False,
        "step12_rerun_required": True,
        "external_actions": dict(EXTERNAL_ACTIONS_OFF),
        "no_signal_discord_policy": "DO_NOT_NOTIFY_ON_NO_SIGNAL",
        "important_note": "This is a frozen source definition, not a live mapping. Step 12 must consume this and still pass all no-approx checks before any evaluator connection.",
    }

    config_path = output_config_dir / "frozen_coreB_live_evaluator_source_definition_20260603.json"
    write_json(config_path, frozen_def)
    write_json(audit_dir / "frozen_coreB_live_evaluator_source_definition_20260603.json", frozen_def)

    rules_flat = []
    conditions_flat = []
    for rule in rules:
        rules_flat.append({k: v for k, v in rule.items() if k not in {"predicates", "base_condition_predicates", "added_filter_predicates", "source_text"}} | {"base_condition": rule["source_text"].get("base_condition"), "added_filter_text": rule["source_text"].get("added_filter_text")})
        for pred in rule.get("predicates", []):
            conditions_flat.append({"rule_id": rule["rule_id"], **pred})
    pd.DataFrame(rules_flat).to_csv(audit_dir / "gold_v2_coreb_live_evaluator_source_definition_rules.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(conditions_flat).to_csv(audit_dir / "gold_v2_coreb_live_evaluator_source_definition_conditions.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame([asdict(c) for c in checks]).to_csv(audit_dir / "gold_v2_coreb_live_evaluator_source_definition_policy_checks.csv", index=False, encoding="utf-8-sig")

    summary = {
        "created_utc": frozen_def["created_utc"],
        "status": frozen_def["status"],
        "audit_only": True,
        "policy_safety_ok": bool(policy_ok),
        "readiness_ok": bool(readiness_ok),
        "all_rules_ready": bool(all_rules_ready),
        "rule_universe_count": int(len(rules)),
        "condition_row_count": int(len(conditions_flat)),
        "same_count_min": 15,
        "output_config_path": str(config_path),
        "audit_output_dir": str(audit_dir),
        "live_evaluator_mapping_ready": False,
        "final_signal_allowed": False,
        "step12_rerun_required": True,
        "external_actions": dict(EXTERNAL_ACTIONS_OFF),
        "no_signal_discord_policy": "DO_NOT_NOTIFY_ON_NO_SIGNAL",
    }
    write_json(audit_dir / "gold_v2_coreb_live_evaluator_source_definition_freeze_summary.json", summary)
    (audit_dir / "GOLD_V2_COREB_LIVE_EVALUATOR_SOURCE_DEFINITION_FREEZE_AUDIT_ONLY_REPORT.md").write_text(build_report(summary), encoding="utf-8")

    print(f"[DONE] status={summary['status']} audit_dir={audit_dir}")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print("No Discord notification, MT5 order, AI API call, or live hook was performed.")
    print("This is not a live mapping. Step 12 must be rerun/updated to consume the frozen CoreB source definition.")
    if not policy_ok or not readiness_ok or not all_rules_ready:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
