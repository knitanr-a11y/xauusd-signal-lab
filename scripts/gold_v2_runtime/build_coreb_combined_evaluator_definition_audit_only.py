#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
COMPONENT = "HIGH_B_CoreB_RR125_BUY_CONFLUENCE"
SEL = ROOT / "configs/gold_v2/frozen_coreB_rr125_source_rule_conditions_20260603.json"
UNI = ROOT / "configs/gold_v2/frozen_coreB_same_count_source_universe_20260604.json"
OUT = ROOT / "configs/gold_v2/frozen_coreB_combined_evaluator_definition_20260604.json"
SEL_READY = "FROZEN_COREB_RR125_SOURCE_RULE_CONDITIONS_READY_AUDIT_ONLY"
UNI_READY = "FROZEN_COREB_SAME_COUNT_SOURCE_UNIVERSE_READY_AUDIT_ONLY"
STATUS_READY = "FROZEN_COREB_COMBINED_EVALUATOR_DEFINITION_READY_AUDIT_ONLY_FINAL_SIGNAL_BLOCKED"

def files_dir() -> Path:
    return ROOT.parents[1] if len(ROOT.parents) >= 2 else ROOT.parent

def out_dir() -> Path:
    p = files_dir() / "FX_OUTPUTS" / "gold_v2_coreb_combined_evaluator_definition_audit_only"
    p.mkdir(parents=True, exist_ok=True)
    return p

def read_json(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))

def write_json(p: Path, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")

def flat(rules, a, b):
    rows = []
    for r in rules:
        for key in [a, b]:
            for c in r.get(key, []) or []:
                x = dict(c)
                x["rule_id"] = r.get("rule_id")
                x["candidate_id"] = r.get("candidate_id")
                x["origin_id"] = r.get("origin_id")
                x["variant"] = r.get("variant")
                rows.append(x)
    return rows

def main() -> int:
    out = out_dir()
    created = datetime.now(timezone.utc).isoformat()
    if not SEL.exists() or not UNI.exists():
        summary = {"created_utc":created,"status":"COREB_COMBINED_INPUT_MISSING","selected_exists":SEL.exists(),"same_count_exists":UNI.exists(),"output_config_written":False,"final_signal_allowed":False}
        write_json(out / "gold_v2_coreb_combined_evaluator_definition_summary.json", summary)
        return 2
    selected = read_json(SEL)
    universe = read_json(UNI)
    selected_rules = selected.get("source_rule_conditions", []) or []
    universe_rules = universe.get("source_universe_rules", []) or []
    selected_conditions = flat(selected_rules, "base_condition_objects", "added_filter_condition_objects")
    universe_conditions = flat(universe_rules, "base_condition_objects", "added_filter_condition_objects")
    errors = []
    if selected.get("status") != SEL_READY:
        errors.append("SELECTED_SOURCE_NOT_READY")
    if universe.get("status") != UNI_READY:
        errors.append("SAME_COUNT_SOURCE_NOT_READY")
    if len(selected_rules) == 0 or len(selected_conditions) == 0:
        errors.append("SELECTED_RULES_EMPTY")
    if len(universe_rules) < 15:
        errors.append("SAME_COUNT_UNIVERSE_LT_15")
    if universe.get("parse_error_count") != 0:
        errors.append("SAME_COUNT_SOURCE_PARSE_ERRORS")
    status = STATUS_READY if not errors else "COREB_COMBINED_EVALUATOR_DEFINITION_BLOCKED"
    required_fields = sorted({x.get("field") for x in selected_conditions + universe_conditions if x.get("field")})
    definition = {
        "created_utc": created,
        "status": status,
        "audit_only": True,
        "component": COMPONENT,
        "definition_id": "COREB_COMBINED_SELECTED12_SAMECOUNT33_20260604",
        "selected_source_path": str(SEL),
        "same_count_source_path": str(UNI),
        "selected_source_status": selected.get("status"),
        "same_count_source_status": universe.get("status"),
        "direction": "BUY",
        "rr": 1.25,
        "entry_logic": "selected_rule_hit AND same_count_source_hit_count >= 15",
        "same_count_min": 15,
        "selected_rule_count": len(selected_rules),
        "selected_condition_count": len(selected_conditions),
        "same_count_source_rule_count": len(universe_rules),
        "same_count_source_condition_count": len(universe_conditions),
        "required_field_count": len(required_fields),
        "required_fields": required_fields,
        "selected_rules": selected_rules,
        "same_count_source_rules": universe_rules,
        "entry_time_history_reuse_allowed": False,
        "historical_same_count_live_reuse_allowed": False,
        "component_evaluator_definition_ready": not errors,
        "component_signal_allowed": False,
        "live_evaluator_connection_allowed": False,
        "final_signal_allowed": False,
        "step13_allowed": False,
        "notification_should_send": False,
        "blocking_errors": errors
    }
    if not errors:
        write_json(OUT, definition)
        output_written = True
    else:
        output_written = False
    write_json(out / "frozen_coreB_combined_evaluator_definition_20260604.json", definition)
    pd.DataFrame(required_fields, columns=["field"]).to_csv(out / "gold_v2_coreb_combined_required_fields.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(selected_conditions).to_csv(out / "gold_v2_coreb_combined_selected_conditions.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(universe_conditions).to_csv(out / "gold_v2_coreb_combined_same_count_conditions.csv", index=False, encoding="utf-8-sig")
    summary = {k:definition[k] for k in ["created_utc","status","audit_only","component","definition_id","entry_logic","same_count_min","selected_rule_count","selected_condition_count","same_count_source_rule_count","same_count_source_condition_count","required_field_count","entry_time_history_reuse_allowed","historical_same_count_live_reuse_allowed","component_evaluator_definition_ready","component_signal_allowed","live_evaluator_connection_allowed","final_signal_allowed","step13_allowed","notification_should_send","blocking_errors"]}
    summary["output_config"] = str(OUT)
    summary["output_config_written"] = output_written
    summary["output_dir"] = str(out)
    write_json(out / "gold_v2_coreb_combined_evaluator_definition_summary.json", summary)
    (out / "GOLD_V2_COREB_COMBINED_EVALUATOR_DEFINITION_AUDIT_ONLY_REPORT.md").write_text("# GOLD V2 CoreB combined evaluator definition audit-only report\n\n" + "\n".join(f"- {k}: `{v}`" for k,v in summary.items()), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if not errors else 2

if __name__ == "__main__":
    raise SystemExit(main())
