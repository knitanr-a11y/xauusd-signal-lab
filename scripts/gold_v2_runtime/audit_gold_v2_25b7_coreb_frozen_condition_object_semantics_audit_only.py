#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Sequence

import pandas as pd

STEP = "25B7_COREB_FROZEN_CONDITION_OBJECT_SEMANTICS_AUDIT_ONLY"
PASS_STATUS = "COREB_FROZEN_CONDITION_OBJECT_SEMANTICS_REVIEW_COMPLETED_AUDIT_ONLY_COREB_STILL_BLOCKED"
STOP_STATUS = "25B7_STOP_MISSING_INPUT_OR_UNSAFE_STATE_AUDIT_ONLY"
IN25B6 = "gold_v2_25b6_coreb_dry_run_parity_review_audit_only"
IN25B3 = "gold_v2_25b3_coreb_source_shortlist_content_audit_only"
OUT_DIR = "gold_v2_25b7_coreb_frozen_condition_object_semantics_audit_only"

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
KEY_COLS = ["policy", "candidate_id", "origin_id", "direction", "variant", "rr_bucket"]
CONFIG_NAMES = {
    "selected_source_rule_conditions": "frozen_coreB_rr125_source_rule_conditions_20260603.json",
    "same_count_source_universe": "frozen_coreB_same_count_source_universe_20260604.json",
    "combined_evaluator_definition": "frozen_coreB_combined_evaluator_definition_20260604.json",
    "buy_confluence_policy": "frozen_coreB_rr125_buy_confluence_rules_20260603.json",
}


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="25B7 CoreB frozen condition object semantics audit-only")
    p.add_argument("--output-dir", default=None)
    return p.parse_args(argv)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def files_dir_from_repo() -> Path:
    root = repo_root()
    return root.parents[1] if len(root.parents) >= 2 else root.parent


def fx_outputs() -> Path:
    return files_dir_from_repo() / "FX_OUTPUTS"


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


def read_json(path: Path) -> Any:
    return json.loads(lp(path).read_text(encoding="utf-8-sig"))


def write_csv(path: Path, df: pd.DataFrame) -> None:
    lp(path.parent).mkdir(parents=True, exist_ok=True)
    df.to_csv(lp(path), index=False, encoding="utf-8-sig")


def write_json(path: Path, obj: dict[str, Any]) -> None:
    lp(path.parent).mkdir(parents=True, exist_ok=True)
    lp(path).write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with lp(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def md_table(df: pd.DataFrame, max_rows: int = 80) -> str:
    if df.empty:
        return "_No rows._"
    view = df.head(max_rows)
    cols = list(view.columns)
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for _, r in view.iterrows():
        lines.append("| " + " | ".join(str(r[c]).replace("|", "\\|").replace("\n", " ") for c in cols) + " |")
    if len(df) > max_rows:
        lines.append(f"| ... | truncated {len(df)-max_rows} more rows |" + " |" * max(0, len(cols)-2))
    return "\n".join(lines)


def path_from_file_audit(file_audit: pd.DataFrame, name: str) -> Path:
    m = file_audit[file_audit["normalized_path"].astype(str).str.contains(name, case=False, regex=False, na=False)]
    if m.empty:
        return Path("")
    return Path(str(m.iloc[0]["absolute_path"]))


def safe_str(v: Any, limit: int = 500) -> str:
    if isinstance(v, (dict, list)):
        return json.dumps(v, ensure_ascii=False, sort_keys=True)[:limit]
    return str(v)[:limit]


def condition_signature(obj: Any) -> str:
    return hashlib.sha256(json.dumps(obj, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")).hexdigest()


def collect_condition_objects(node: Any, prefix: str = "") -> list[tuple[str, dict[str, Any]]]:
    out: list[tuple[str, dict[str, Any]]] = []
    if isinstance(node, dict):
        lower_keys = {str(k).lower() for k in node.keys()}
        if any(k in lower_keys for k in ["field", "operator", "op", "value", "threshold", "min", "max", "conditions", "condition"]):
            out.append((prefix or "$", node))
        for k, v in node.items():
            next_prefix = f"{prefix}.{k}" if prefix else str(k)
            out.extend(collect_condition_objects(v, next_prefix))
    elif isinstance(node, list):
        for i, v in enumerate(node):
            out.extend(collect_condition_objects(v, f"{prefix}[{i}]"))
    return out


def top_rule_list(obj: dict[str, Any]) -> tuple[str, list[Any]]:
    for key in ["source_rule_conditions", "source_universe_rules", "selected_rules", "same_count_source_rules"]:
        v = obj.get(key)
        if isinstance(v, list):
            return key, v
    return "", []


def audit_config(role: str, path: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    obj = read_json(path)
    list_key, rules = top_rule_list(obj if isinstance(obj, dict) else {})
    file_rows = [{
        "config_role": role,
        "path": str(path),
        "exists": lp(path).exists(),
        "bytes": int(lp(path).stat().st_size) if lp(path).exists() else 0,
        "sha256": sha256_file(path) if lp(path).exists() else "",
        "top_level_keys": ";".join(obj.keys()) if isinstance(obj, dict) else "",
        "primary_rule_list_key": list_key,
        "primary_rule_rows": len(rules),
    }]
    cond_rows: list[dict[str, Any]] = []
    for rule_index, rule in enumerate(rules):
        if not isinstance(rule, dict):
            continue
        key_vals = {k: str(rule.get(k, "")) for k in KEY_COLS}
        rule_id = str(rule.get("rule_id", rule.get("id", rule_index)))
        conds = collect_condition_objects(rule)
        rule_sig = condition_signature(rule)
        if not conds:
            cond_rows.append({
                "config_role": role,
                "rule_list_key": list_key,
                "rule_index": rule_index,
                "rule_id": rule_id,
                **key_vals,
                "condition_path": "<NO_CONDITION_OBJECT_FOUND>",
                "condition_signature": rule_sig,
                "operator": "",
                "field": "",
                "value_preview": "",
                "condition_json_preview": json.dumps(rule, ensure_ascii=False, sort_keys=True, default=str)[:1000],
            })
        for cond_path, cond in conds:
            field = cond.get("field", cond.get("name", cond.get("column", cond.get("metric", ""))))
            op = cond.get("operator", cond.get("op", cond.get("comparison", cond.get("type", ""))))
            value = cond.get("value", cond.get("threshold", cond.get("min", cond.get("max", ""))))
            cond_rows.append({
                "config_role": role,
                "rule_list_key": list_key,
                "rule_index": rule_index,
                "rule_id": rule_id,
                **key_vals,
                "condition_path": cond_path,
                "condition_signature": condition_signature(cond),
                "rule_signature": rule_sig,
                "operator": safe_str(op),
                "field": safe_str(field),
                "value_preview": safe_str(value),
                "condition_json_preview": json.dumps(cond, ensure_ascii=False, sort_keys=True, default=str)[:1000],
            })
    return file_rows, cond_rows


def safety_problems(s25b6: dict[str, Any]) -> list[str]:
    problems = []
    if s25b6.get("status") != "COREB_DRY_RUN_PARITY_REVIEW_COMPLETED_AUDIT_ONLY_COREB_STILL_BLOCKED":
        problems.append("25B6 status mismatch")
    if int(s25b6.get("total_stop_rows", -1)) != 0:
        problems.append("25B6 stop rows not zero")
    for k, expected in SAFETY_FLAGS.items():
        if s25b6.get(k) != expected:
            problems.append(f"safety flag mismatch: {k}")
    if bool(s25b6.get("coreb_live_evaluator_unblocked")):
        problems.append("CoreB live unexpectedly unblocked")
    if bool(s25b6.get("source_recovery_executed")):
        problems.append("source recovery unexpectedly executed")
    if bool(s25b6.get("source_mutation_executed")):
        problems.append("source mutation unexpectedly executed")
    return problems


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    out_dir = Path(args.output_dir).expanduser().resolve() if args.output_dir else fx_outputs() / OUT_DIR
    lp(out_dir).mkdir(parents=True, exist_ok=True)
    s25b6_path = fx_outputs() / IN25B6 / "gold_v2_25b6_coreb_dry_run_parity_review_summary.json"
    file_audit_path = fx_outputs() / IN25B3 / "gold_v2_25b3_shortlist_file_content_audit.csv"
    inputs = pd.DataFrame([
        {"role": "25b6_summary", "path": str(s25b6_path), "required": True, "exists": lp(s25b6_path).exists(), "status": "PASS" if lp(s25b6_path).exists() else "STOP"},
        {"role": "25b3_file_audit", "path": str(file_audit_path), "required": True, "exists": lp(file_audit_path).exists(), "status": "PASS" if lp(file_audit_path).exists() else "STOP"},
    ])
    write_csv(out_dir / "gold_v2_25b7_input_audit.csv", inputs)
    if not bool(inputs["exists"].all()):
        summary = {"created_utc": datetime.now(timezone.utc).isoformat(), "step": STEP, "status": STOP_STATUS, "audit_only": True, "total_stop_rows": int((inputs["status"] == "STOP").sum()), **SAFETY_FLAGS}
        write_json(out_dir / "gold_v2_25b7_coreb_frozen_condition_object_semantics_summary.json", summary)
        return 2

    s25b6 = read_json(s25b6_path)
    problems = safety_problems(s25b6)
    file_audit = read_csv(file_audit_path)

    file_rows: list[dict[str, Any]] = []
    cond_rows: list[dict[str, Any]] = []
    for role, filename in CONFIG_NAMES.items():
        path = path_from_file_audit(file_audit, filename)
        exists = bool(str(path)) and lp(path).exists()
        if not exists:
            problems.append(f"missing config: {role}")
            file_rows.append({"config_role": role, "path": str(path), "exists": False})
            continue
        fr, cr = audit_config(role, path)
        file_rows.extend(fr)
        cond_rows.extend(cr)

    config_audit = pd.DataFrame(file_rows)
    inventory = pd.DataFrame(cond_rows)
    write_csv(out_dir / "gold_v2_25b7_config_file_audit.csv", config_audit)
    write_csv(out_dir / "gold_v2_25b7_condition_object_inventory.csv", inventory)

    if not inventory.empty:
        path_counts = inventory.groupby(["config_role", "rule_list_key", "condition_path"], dropna=False).size().reset_index(name="rows").sort_values(["config_role", "rows"], ascending=[True, False])
        op_value = inventory.groupby(["config_role", "field", "operator", "value_preview"], dropna=False).size().reset_index(name="rows").sort_values(["config_role", "rows"], ascending=[True, False])
        key_group = inventory.groupby(["config_role"] + KEY_COLS, dropna=False).agg(
            rule_rows=("rule_index", "nunique"),
            condition_objects=("condition_signature", "count"),
            unique_condition_signatures=("condition_signature", "nunique"),
            unique_rule_signatures=("rule_signature", "nunique"),
            condition_paths=("condition_path", lambda s: ";".join(sorted(set(map(str, s)))[:20])),
        ).reset_index()
        key_loss = key_group[key_group["unique_rule_signatures"] > 1].copy()
        key_loss["loss_classification"] = "MULTIPLE_RULE_SIGNATURES_COLLAPSE_TO_SAME_KEY_COLS"
    else:
        path_counts = pd.DataFrame()
        op_value = pd.DataFrame()
        key_loss = pd.DataFrame()

    write_csv(out_dir / "gold_v2_25b7_condition_path_counts.csv", path_counts)
    write_csv(out_dir / "gold_v2_25b7_operator_value_matrix.csv", op_value)
    write_csv(out_dir / "gold_v2_25b7_key_only_loss_matrix.csv", key_loss)

    has_non_key_conditions = False
    if not inventory.empty:
        non_key_fields = inventory["field"].astype(str).replace("", pd.NA).dropna()
        has_non_key_conditions = len(non_key_fields) > 0
    collapsed_groups = int(len(key_loss)) if not key_loss.empty else 0
    feasibility = pd.DataFrame([
        {"review_item": "condition_objects_available", "observed": len(inventory), "supports_non_key_dry_run": len(inventory) > 0, "blocks_coreb_unblock": True},
        {"review_item": "non_key_condition_fields_present", "observed": has_non_key_conditions, "supports_non_key_dry_run": has_non_key_conditions, "blocks_coreb_unblock": True},
        {"review_item": "key_only_collision_groups", "observed": collapsed_groups, "supports_non_key_dry_run": collapsed_groups > 0, "blocks_coreb_unblock": True},
        {"review_item": "target_parity_already_proven", "observed": False, "supports_non_key_dry_run": False, "blocks_coreb_unblock": True},
        {"review_item": "source_recovery_allowed_now", "observed": False, "supports_non_key_dry_run": False, "blocks_coreb_unblock": True},
    ])
    write_csv(out_dir / "gold_v2_25b7_semantics_feasibility_matrix.csv", feasibility)

    next_plan = pd.DataFrame([
        {"rank": 1, "next_step": "25B8_COREB_CONDITION_OBJECT_DRY_RUN_PLAN_AUDIT_ONLY", "allowed_now": True, "purpose": "Plan a non-key-only dry-run from condition objects without executing source recovery"},
        {"rank": 2, "next_step": "CoreB source recovery execution", "allowed_now": False, "purpose": "Still blocked until non-key semantics and parity are proven"},
        {"rank": 3, "next_step": "CoreB live evaluator", "allowed_now": False, "purpose": "Still blocked"},
    ])
    write_csv(out_dir / "gold_v2_25b7_next_step_plan.csv", next_plan)

    status = PASS_STATUS if not problems else STOP_STATUS
    summary = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "step": STEP,
        "status": status,
        "audit_only": True,
        "status_problems": problems,
        "config_files": int(len(config_audit)),
        "condition_object_rows": int(len(inventory)),
        "condition_path_rows": int(len(path_counts)),
        "operator_value_rows": int(len(op_value)),
        "key_only_loss_groups": collapsed_groups,
        "has_non_key_condition_fields": bool(has_non_key_conditions),
        "coreb_live_evaluator_unblocked": False,
        "source_recovery_executed": False,
        "source_mutation_executed": False,
        "same_count_exact_parity_proven": False,
        "cluster_membership_parity_proven": False,
        "target_key_parity_proven": False,
        "next_recommended_step": "25B8_COREB_CONDITION_OBJECT_DRY_RUN_PLAN_AUDIT_ONLY",
        "total_stop_rows": int(len(problems)),
        **SAFETY_FLAGS,
    }
    write_json(out_dir / "gold_v2_25b7_coreb_frozen_condition_object_semantics_summary.json", summary)

    report = "\n".join([
        "# GOLD V2 25B7 CoreB frozen condition object semantics audit-only report",
        "",
        f"Created UTC: {summary['created_utc']}",
        f"Step: `{STEP}`",
        f"Status: `{status}`",
        "",
        "## Boundary",
        "",
        "25B7 inspects frozen condition objects only. It does not run a new CoreB replay or unblock CoreB.",
        "",
        "## Input audit",
        "",
        md_table(inputs),
        "",
        "## Config file audit",
        "",
        md_table(config_audit),
        "",
        "## Summary findings",
        "",
        md_table(pd.DataFrame([{
            "condition_object_rows": len(inventory),
            "condition_path_rows": len(path_counts),
            "operator_value_rows": len(op_value),
            "key_only_loss_groups": collapsed_groups,
            "has_non_key_condition_fields": has_non_key_conditions,
        }])),
        "",
        "## Top condition path counts",
        "",
        md_table(path_counts, max_rows=40),
        "",
        "## Key-only loss groups",
        "",
        md_table(key_loss, max_rows=40),
        "",
        "## Semantics feasibility matrix",
        "",
        md_table(feasibility),
        "",
        "## Next step plan",
        "",
        md_table(next_plan),
        "",
        "## Safety",
        "",
        "CoreB remains blocked. Source recovery/live/final/external actions remain off.",
    ])
    lp(out_dir / "GOLD_V2_25B7_COREB_FROZEN_CONDITION_OBJECT_SEMANTICS_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")

    print(json.dumps({"status": status, "output_dir": str(out_dir), "condition_object_rows": int(len(inventory)), "key_only_loss_groups": collapsed_groups, "next_recommended_step": summary["next_recommended_step"]}, ensure_ascii=False, indent=2))
    return 0 if not problems else 2


if __name__ == "__main__":
    raise SystemExit(main())
