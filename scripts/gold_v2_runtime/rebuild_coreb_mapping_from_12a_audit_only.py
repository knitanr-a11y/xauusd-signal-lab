#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse, json
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "configs/gold_v2/frozen_coreB_rr125_source_rule_conditions_20260603.json"
DST = ROOT / "configs/gold_v2/live_evaluator_mapping_coreB_20260603.json"
READY = "FROZEN_COREB_RR125_SOURCE_RULE_CONDITIONS_READY_AUDIT_ONLY"
COMPONENT = "HIGH_B_CoreB_RR125_BUY_CONFLUENCE"

def files_dir() -> Path:
    return ROOT.parents[1] if len(ROOT.parents) >= 2 else ROOT.parent

def out_dir() -> Path:
    p = files_dir() / "FX_OUTPUTS" / "gold_v2_coreb_mapping_rebuilt_from_12a_audit_only"
    p.mkdir(parents=True, exist_ok=True)
    return p

def read_json(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))

def write_json(p: Path, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")

def flat_conditions(rules):
    rows = []
    for r in rules:
        for key in ["base_condition_objects", "added_filter_condition_objects"]:
            for obj in r.get(key, []) or []:
                x = dict(obj)
                x["rule_id"] = r.get("rule_id")
                x["candidate_id"] = r.get("candidate_id")
                x["origin_id"] = r.get("origin_id")
                x["variant"] = r.get("variant")
                rows.append(x)
    return rows

def main():
    out = out_dir()
    if not SRC.exists():
        summary = {"status":"COREB_12A_SOURCE_FILE_MISSING", "source":str(SRC), "written":False}
        write_json(out / "gold_v2_coreb_mapping_rebuilt_from_12a_summary.json", summary)
        return 2
    src = read_json(SRC)
    rules = src.get("source_rule_conditions", []) or []
    conds = flat_conditions(rules)
    ok = src.get("status") == READY and src.get("component") == COMPONENT and rules and conds
    if not ok:
        summary = {"status":"COREB_12A_SOURCE_NOT_READY", "source_status":src.get("status"), "rules":len(rules), "conditions":len(conds), "written":False}
        write_json(out / "gold_v2_coreb_mapping_rebuilt_from_12a_summary.json", summary)
        return 2
    prev = read_json(DST) if DST.exists() else {}
    mapping = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "MAPPING_READY_AUDIT_ONLY_FINAL_SIGNAL_BLOCKED",
        "audit_only": True,
        "component": COMPONENT,
        "mapping_id": "COREB_MAPPING_FROM_12A_20260604",
        "source_12a_path": str(SRC),
        "source_12a_status": src.get("status"),
        "source_rule_policy": src.get("source_rule_policy"),
        "direction": "BUY",
        "rr": 1.25,
        "same_count_min": 15,
        "mapped_rules": rules,
        "mapped_conditions": conds,
        "unmapped_conditions": [],
        "mapped_rule_count": len(rules),
        "mapped_condition_count": len(conds),
        "required_field_count": len({c.get("field") for c in conds if c.get("field")}),
        "history_time_reuse_allowed": False,
        "history_count_reuse_allowed": False,
        "live_evaluator_ready": True,
        "component_signal_allowed": False,
        "live_evaluator_connection_allowed": False,
        "final_signal_allowed": False,
        "step13_allowed": False,
        "feature_preflight_required": True
    }
    write_json(out / "previous_live_evaluator_mapping_coreB_20260603.json", prev)
    write_json(DST, mapping)
    write_json(out / "live_evaluator_mapping_coreB_20260603.json", mapping)
    pd.DataFrame(rules).to_csv(out / "gold_v2_coreb_mapping_rebuilt_from_12a_rules.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(conds).to_csv(out / "gold_v2_coreb_mapping_rebuilt_from_12a_conditions.csv", index=False, encoding="utf-8-sig")
    summary = {"created_utc":mapping["created_utc"], "status":mapping["status"], "written":True, "previous_status":prev.get("status"), "mapped_rule_count":len(rules), "mapped_condition_count":len(conds), "required_field_count":mapping["required_field_count"], "final_signal_allowed":False, "step13_allowed":False, "output_dir":str(out)}
    write_json(out / "gold_v2_coreb_mapping_rebuilt_from_12a_summary.json", summary)
    (out / "GOLD_V2_COREB_MAPPING_REBUILT_FROM_12A_AUDIT_ONLY_REPORT.md").write_text("# GOLD V2 CoreB mapping rebuilt from 12A audit-only report\n\n" + "\n".join(f"- {k}: `{v}`" for k,v in summary.items()), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
