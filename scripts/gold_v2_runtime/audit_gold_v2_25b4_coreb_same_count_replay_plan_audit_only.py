#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Sequence

import pandas as pd

STEP = "25B4_COREB_SAME_COUNT_REPLAY_PLAN_AUDIT_ONLY"
IN_DIR = "gold_v2_25b3_coreb_source_shortlist_content_audit_only"
OUT_DIR = "gold_v2_25b4_coreb_same_count_replay_plan_audit_only"
PASS_STATUS = "COREB_SAME_COUNT_REPLAY_PLAN_READY_AUDIT_ONLY_EXECUTION_BLOCKED"
STOP_STATUS = "25B4_STOP_MISSING_25B3_INPUT_OR_UNSAFE_STATE_AUDIT_ONLY"

SAFETY_FLAGS = {
    "source_recovery_execution_allowed_now": False,
    "source_mutation_allowed": False,
    "source_identity_finalization_allowed_now": False,
    "live_evaluator_final_signal_allowed": False,
    "final_signal_allowed": False,
    "discord_send_allowed": False,
    "mt5_order_allowed": False,
    "ai_api_allowed": False,
    "live_hook_allowed": False,
    "no_signal_discord_notification_allowed": False,
    "old_gold_disc8_quarantined": True,
    "source_recovery_chain_status": "PAUSED_AT_24AF",
}

REQUIRED_INPUTS = {
    "summary": "gold_v2_25b3_coreb_source_shortlist_content_summary.json",
    "file_audit": "gold_v2_25b3_shortlist_file_content_audit.csv",
    "csv_profile": "gold_v2_25b3_csv_profile.csv",
    "json_profile": "gold_v2_25b3_json_profile.csv",
    "json_key_inventory": "gold_v2_25b3_json_key_inventory.csv",
    "linkage": "gold_v2_25b3_coreb_source_linkage_matrix.csv",
    "unblock_gaps": "gold_v2_25b3_unblock_gap_matrix.csv",
}
REQUIRED_ROLES = {
    "SOURCE_UNIVERSE_RAW_LEDGER",
    "SOURCE_UNIVERSE_FROZEN_CONFIG",
    "FROZEN_RULE_CONDITION_CONFIG",
    "COMBINED_EVALUATOR_DEFINITION",
    "TARGET_TOP_LEDGER_ONLY",
}


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="25B4 CoreB replay plan audit-only")
    p.add_argument("--input-dir", default=None)
    p.add_argument("--output-dir", default=None)
    return p.parse_args(argv)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def files_dir_from_repo() -> Path:
    root = repo_root()
    return root.parents[1] if len(root.parents) >= 2 else root.parent


def fx_outputs() -> Path:
    return files_dir_from_repo() / "FX_OUTPUTS"


def default_input_dir() -> Path:
    return fx_outputs() / IN_DIR


def default_output_dir() -> Path:
    return fx_outputs() / OUT_DIR


def lp(path: Path) -> Path:
    if os.name != "nt":
        return path
    s = str(path)
    if s.startswith("\\\\?\\"):
        return Path(s)
    if s.startswith("\\\\"):
        return Path("\\\\?\\UNC\\" + s[2:])
    return Path("\\\\?\\" + s)


def read_csv(path: Path) -> pd.DataFrame:
    last: Exception | None = None
    for enc in ("utf-8-sig", "utf-8", "cp932"):
        try:
            return pd.read_csv(lp(path), encoding=enc, keep_default_na=False)
        except Exception as exc:
            last = exc
    raise RuntimeError(f"Could not read CSV {path}: {last}")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(lp(path).read_text(encoding="utf-8-sig"))


def write_csv(path: Path, df: pd.DataFrame) -> None:
    lp(path.parent).mkdir(parents=True, exist_ok=True)
    df.to_csv(lp(path), index=False, encoding="utf-8-sig")


def write_json(path: Path, obj: dict[str, Any]) -> None:
    lp(path.parent).mkdir(parents=True, exist_ok=True)
    lp(path).write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")


def md_table(df: pd.DataFrame, max_rows: int = 80) -> str:
    if df.empty:
        return "_No rows._"
    view = df.head(max_rows)
    cols = list(view.columns)
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for _, r in view.iterrows():
        lines.append("| " + " | ".join(str(r[c]).replace("|", "\\|").replace("\n", " ") for c in cols) + " |")
    return "\n".join(lines)


def find_csv_profile(csv_profile: pd.DataFrame, contains: str) -> dict[str, Any]:
    if csv_profile.empty or "normalized_path" not in csv_profile.columns:
        return {}
    m = csv_profile[csv_profile["normalized_path"].astype(str).str.contains(contains, case=False, regex=False, na=False)]
    return m.iloc[0].to_dict() if not m.empty else {}


def json_value(keys: pd.DataFrame, normalized_contains: str, json_path: str) -> str:
    if keys.empty:
        return ""
    m = keys[
        keys["normalized_path"].astype(str).str.contains(normalized_contains, case=False, regex=False, na=False)
        & (keys["json_path"].astype(str) == json_path)
    ]
    if m.empty:
        return ""
    return str(m.iloc[0].get("value_preview", ""))


def status_problems(summary: dict[str, Any]) -> list[str]:
    problems: list[str] = []
    if summary.get("status") != "COREB_SOURCE_SHORTLIST_CONTENT_AUDIT_COMPLETED_AUDIT_ONLY_REPLAY_PLAN_REQUIRED":
        problems.append("25B3 status mismatch")
    if int(summary.get("total_stop_rows", -1)) != 0:
        problems.append("25B3 stop rows not zero")
    false_keys = [
        "coreb_live_evaluator_unblocked", "replay_executed", "same_count_recomputed",
        "same_count_exact_parity_proven", "cluster_membership_parity_proven",
        "source_recovery_executed", "source_mutation_executed",
        "source_recovery_execution_allowed_now", "source_mutation_allowed",
        "source_identity_finalization_allowed_now", "live_evaluator_final_signal_allowed",
        "final_signal_allowed", "discord_send_allowed", "mt5_order_allowed", "ai_api_allowed",
        "live_hook_allowed", "no_signal_discord_notification_allowed",
    ]
    for k in false_keys:
        if bool(summary.get(k)) is not False:
            problems.append(f"unsafe flag not false: {k}")
    if summary.get("old_gold_disc8_quarantined") is not True:
        problems.append("old_gold_disc8_quarantined mismatch")
    if summary.get("source_recovery_chain_status") != "PAUSED_AT_24AF":
        problems.append("source recovery chain status mismatch")
    return problems


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    in_dir = Path(args.input_dir).expanduser().resolve() if args.input_dir else default_input_dir()
    out_dir = Path(args.output_dir).expanduser().resolve() if args.output_dir else default_output_dir()
    lp(out_dir).mkdir(parents=True, exist_ok=True)

    input_rows = []
    for role, filename in REQUIRED_INPUTS.items():
        p = in_dir / filename
        input_rows.append({"role": role, "path": str(p), "required": True, "exists": lp(p).exists(), "status": "PASS" if lp(p).exists() else "STOP"})
    input_audit = pd.DataFrame(input_rows)
    write_csv(out_dir / "gold_v2_25b4_input_audit.csv", input_audit)
    if not bool(input_audit["exists"].all()):
        summary = {"created_utc": datetime.now(timezone.utc).isoformat(), "step": STEP, "status": STOP_STATUS, "audit_only": True, "total_stop_rows": int((input_audit["status"] == "STOP").sum()), **SAFETY_FLAGS}
        write_json(out_dir / "gold_v2_25b4_coreb_same_count_replay_plan_summary.json", summary)
        return 2

    s25b3 = read_json(in_dir / REQUIRED_INPUTS["summary"])
    csv_profile = read_csv(in_dir / REQUIRED_INPUTS["csv_profile"])
    json_keys = read_csv(in_dir / REQUIRED_INPUTS["json_key_inventory"])
    linkage = read_csv(in_dir / REQUIRED_INPUTS["linkage"])
    unblock_gaps_25b3 = read_csv(in_dir / REQUIRED_INPUTS["unblock_gaps"])

    problems = status_problems(s25b3)
    observed_roles = set(linkage.get("evidence_role", pd.Series(dtype=str)).astype(str).tolist())
    missing_roles = sorted(REQUIRED_ROLES - observed_roles)
    if missing_roles:
        problems.append("missing roles: " + ",".join(missing_roles))

    raw = find_csv_profile(csv_profile, "rr125_raw_signal_ledger.csv")
    top = find_csv_profile(csv_profile, "rr125_top_ledgers.csv")
    constants = {
        "raw_signal_ledger_rows": raw.get("rows", ""),
        "target_top_ledgers_rows": top.get("rows", ""),
        "source_universe_rule_count": json_value(json_keys, "frozen_coreB_same_count_source_universe", "source_universe_rule_count"),
        "source_rule_condition_count": json_value(json_keys, "frozen_coreB_rr125_source_rule_conditions", "source_rule_condition_count"),
        "selected_rule_count": json_value(json_keys, "frozen_coreB_combined_evaluator_definition", "selected_rule_count"),
        "same_count_source_rule_count": json_value(json_keys, "frozen_coreB_combined_evaluator_definition", "same_count_source_rule_count"),
        "selected_condition_count": json_value(json_keys, "frozen_coreB_combined_evaluator_definition", "selected_condition_count"),
        "same_count_source_condition_count": json_value(json_keys, "frozen_coreB_combined_evaluator_definition", "same_count_source_condition_count"),
        "required_field_count": json_value(json_keys, "frozen_coreB_combined_evaluator_definition", "required_field_count"),
        "same_count_min": json_value(json_keys, "frozen_coreB_combined_evaluator_definition", "same_count_min") or json_value(json_keys, "frozen_coreB_same_count_source_universe", "same_count_min"),
        "entry_logic": json_value(json_keys, "frozen_coreB_combined_evaluator_definition", "entry_logic"),
        "direction": json_value(json_keys, "frozen_coreB_combined_evaluator_definition", "direction"),
        "rr": json_value(json_keys, "frozen_coreB_combined_evaluator_definition", "rr"),
    }
    for k, v in constants.items():
        if str(v) == "":
            problems.append("missing constant: " + k)

    replay_input_contract = pd.DataFrame([
        {"input_id": "IN-RAW", "role": "raw_signal_ledger", "path_hint": "rr125_raw_signal_ledger.csv", "expected": constants["raw_signal_ledger_rows"], "allowed_use": "source universe input", "blocked_use": "target fitting"},
        {"input_id": "IN-SCU", "role": "same_count_source_universe_config", "path_hint": "frozen_coreB_same_count_source_universe_20260604.json", "expected": constants["source_universe_rule_count"], "allowed_use": "same_count source rule universe", "blocked_use": "history reuse"},
        {"input_id": "IN-SEL", "role": "selected_rule_conditions_config", "path_hint": "frozen_coreB_rr125_source_rule_conditions_20260603.json", "expected": constants["source_rule_condition_count"], "allowed_use": "selected rule side", "blocked_use": "same_count substitute"},
        {"input_id": "IN-POL", "role": "policy_config", "path_hint": "frozen_coreB_rr125_buy_confluence_rules_20260603.json", "expected": "config", "allowed_use": "policy cross-check", "blocked_use": "override evaluator"},
        {"input_id": "IN-COMBO", "role": "combined_evaluator_definition", "path_hint": "frozen_coreB_combined_evaluator_definition_20260604.json", "expected": f"selected={constants['selected_rule_count']};source={constants['same_count_source_rule_count']}", "allowed_use": "later dry-run contract", "blocked_use": "live connection"},
        {"input_id": "IN-TARGET", "role": "target_top_ledger_only", "path_hint": "rr125_top_ledgers.csv", "expected": constants["target_top_ledgers_rows"], "allowed_use": "target comparison", "blocked_use": "membership inference"},
    ])
    algorithm_contract = pd.DataFrame([
        {"step_id": "ALG-001", "later_action": "load frozen inputs", "status_now": "PLAN_ONLY"},
        {"step_id": "ALG-002", "later_action": "evaluate selected rules", "status_now": "NOT_EXECUTED"},
        {"step_id": "ALG-003", "later_action": "evaluate same_count source universe rules", "status_now": "NOT_EXECUTED"},
        {"step_id": "ALG-004", "later_action": "apply entry logic", "status_now": f"NOT_EXECUTED; {constants['entry_logic']}"},
        {"step_id": "ALG-005", "later_action": "compare to target keys", "status_now": "NOT_EXECUTED"},
    ])
    target_key_contract = pd.DataFrame([
        {"target_id": "TGT-TOP", "target": "rr125_top_ledgers.csv", "key_fields": "dataset,entry_time,top_direction,top_candidate_id,policy,filter", "value_fields": "same_count,unique_origins,source_rule_count,cluster_id,profit,rr_bucket", "expected_rows": constants["target_top_ledgers_rows"]},
        {"target_id": "TGT-FINAL", "target": "final CoreB contribution", "key_fields": "dataset,entry_time,direction,source keys", "value_fields": "same_count,cluster/membership if accepted", "expected_rows": 125},
    ])
    parity_gate_matrix = pd.DataFrame([
        {"gate_id": "G001", "gate": "25B3 status clean", "expected": "PASS", "current": "PASS" if not problems else "REVIEW", "required": True},
        {"gate_id": "G002", "gate": "raw ledger rows", "expected": 16875, "current": constants["raw_signal_ledger_rows"], "required": True},
        {"gate_id": "G003", "gate": "target top ledger rows", "expected": 2811, "current": constants["target_top_ledgers_rows"], "required": True},
        {"gate_id": "G004", "gate": "selected rules", "expected": 12, "current": constants["selected_rule_count"], "required": True},
        {"gate_id": "G005", "gate": "same_count source rules", "expected": 33, "current": constants["same_count_source_rule_count"], "required": True},
        {"gate_id": "G006", "gate": "entry logic", "expected": "selected_rule_hit AND same_count_source_hit_count >= 15", "current": constants["entry_logic"], "required": True},
        {"gate_id": "G007", "gate": "later replay", "expected": "not in 25B4", "current": "NOT_EXECUTED", "required": True},
        {"gate_id": "G008", "gate": "final CoreB 125-row parity", "expected": 125, "current": "NOT_PROVEN", "required": True},
        {"gate_id": "G009", "gate": "same_count exact value parity", "expected": "all target rows", "current": "NOT_PROVEN", "required": True},
        {"gate_id": "G010", "gate": "cluster/membership parity if accepted", "expected": "all target rows", "current": "NOT_PROVEN", "required": True},
    ])
    forbidden_methods = pd.DataFrame([
        {"method": "post_hoc_fit_to_target", "forbidden": True},
        {"method": "static_window_same_count", "forbidden": True},
        {"method": "raw_entry_time_count_as_same_count", "forbidden": True},
        {"method": "interval_or_component_membership_substitute", "forbidden": True},
        {"method": "selected_hit_count_as_same_count", "forbidden": True},
        {"method": "manual_cluster_id_assignment", "forbidden": True},
        {"method": "old_gold_disc8_artifacts", "forbidden": True},
        {"method": "external_or_final_signal_action", "forbidden": True},
    ])
    execution_blockers = pd.DataFrame([
        {"blocker_id": "B001", "blocker": "25B4 is plan only", "status": "OPEN"},
        {"blocker_id": "B002", "blocker": "same_count exact parity not proven", "status": "OPEN"},
        {"blocker_id": "B003", "blocker": "cluster/membership semantics not proven", "status": "OPEN"},
        {"blocker_id": "B004", "blocker": "final CoreB 125-row parity not proven", "status": "OPEN"},
        {"blocker_id": "B005", "blocker": "safety flags remain off", "status": "SAFETY_OPEN"},
    ])
    next_step_contract = pd.DataFrame([
        {"rank": 1, "next_step": "25B5_COREB_SAME_COUNT_REPLAY_DRY_RUN_IMPLEMENTATION_AUDIT_ONLY", "allowed_now": False, "prerequisite": "human acceptance of 25B4 plan"},
        {"rank": 2, "next_step": "manual review of source evidence", "allowed_now": True, "prerequisite": "review 25B3/25B4 outputs"},
        {"rank": 3, "next_step": "CoreB live evaluator", "allowed_now": False, "prerequisite": "exact parity gates all pass"},
    ])

    status = STOP_STATUS if problems else PASS_STATUS
    write_csv(out_dir / "gold_v2_25b4_replay_input_contract.csv", replay_input_contract)
    write_csv(out_dir / "gold_v2_25b4_replay_algorithm_contract.csv", algorithm_contract)
    write_csv(out_dir / "gold_v2_25b4_target_key_contract.csv", target_key_contract)
    write_csv(out_dir / "gold_v2_25b4_parity_gate_matrix.csv", parity_gate_matrix)
    write_csv(out_dir / "gold_v2_25b4_forbidden_methods.csv", forbidden_methods)
    write_csv(out_dir / "gold_v2_25b4_execution_blockers.csv", execution_blockers)
    write_csv(out_dir / "gold_v2_25b4_next_step_contract.csv", next_step_contract)

    summary = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "step": STEP,
        "status": status,
        "audit_only": True,
        "plan_only": True,
        "status_problems": problems,
        "observed_required_roles": sorted(observed_roles),
        "missing_required_roles": missing_roles,
        "required_constants": {k: str(v) for k, v in constants.items()},
        "replay_executed": False,
        "same_count_recomputed": False,
        "same_count_exact_parity_proven": False,
        "cluster_membership_parity_proven": False,
        "coreb_live_evaluator_unblocked": False,
        "source_recovery_executed": False,
        "source_mutation_executed": False,
        "next_recommended_step": "25B5_COREB_SAME_COUNT_REPLAY_DRY_RUN_IMPLEMENTATION_AUDIT_ONLY_AFTER_HUMAN_ACCEPTANCE",
        "total_stop_rows": int(len(problems)),
        **SAFETY_FLAGS,
    }
    write_json(out_dir / "gold_v2_25b4_coreb_same_count_replay_plan_summary.json", summary)

    report = "\n".join([
        "# GOLD V2 25B4 CoreB same_count replay plan audit-only report",
        "",
        f"Created UTC: {summary['created_utc']}",
        f"Step: `{STEP}`",
        f"Status: `{status}`",
        "",
        "## Boundary",
        "",
        "25B4 is plan-only. It records the later replay contract and keeps execution blocked.",
        "",
        "## Input audit",
        "",
        md_table(input_audit),
        "",
        "## Required constants",
        "",
        md_table(pd.DataFrame([{"constant": k, "value": v} for k, v in constants.items()])),
        "",
        "## Replay input contract",
        "",
        md_table(replay_input_contract),
        "",
        "## Replay algorithm contract",
        "",
        md_table(algorithm_contract),
        "",
        "## Target key contract",
        "",
        md_table(target_key_contract),
        "",
        "## Parity gate matrix",
        "",
        md_table(parity_gate_matrix),
        "",
        "## Forbidden methods",
        "",
        md_table(forbidden_methods),
        "",
        "## Execution blockers",
        "",
        md_table(execution_blockers),
        "",
        "## 25B3 gaps carried forward",
        "",
        md_table(unblock_gaps_25b3),
        "",
        "## Next step contract",
        "",
        md_table(next_step_contract),
    ])
    lp(out_dir / "GOLD_V2_25B4_COREB_SAME_COUNT_REPLAY_PLAN_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")

    print(json.dumps({"status": status, "plan_only": True, "output_dir": str(out_dir), "total_stop_rows": int(len(problems))}, ensure_ascii=False, indent=2))
    return 0 if not problems else 2


if __name__ == "__main__":
    raise SystemExit(main())
