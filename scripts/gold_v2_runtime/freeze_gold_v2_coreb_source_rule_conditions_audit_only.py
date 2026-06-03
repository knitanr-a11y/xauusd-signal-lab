#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import pandas as pd

COMPONENT = "HIGH_B_CoreB_RR125_BUY_CONFLUENCE"
READY_STATUS = "FROZEN_COREB_RR125_SOURCE_RULE_CONDITIONS_READY_AUDIT_ONLY"
SOURCE_POLICY = "RR125_from_RR1_rules"
COND_RE = re.compile(r"(?P<field>[A-Za-z_][A-Za-z0-9_]*)\s*(?P<op>>=|<=|==|>|<)\s*(?P<value>-?\d+(?:\.\d+)?)")
REQUIRED = ["policy", "candidate_id", "origin_id", "direction", "variant", "tp_pips", "sl_pips", "rr", "rr_bucket", "base_condition", "added_filter_text", "train_score"]

def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]

def files_dir() -> Path:
    root = repo_root()
    return root.parents[1] if len(root.parents) >= 2 else root.parent

def resolve_repo(text: str) -> Path:
    p = Path(text).expanduser()
    return p.resolve() if p.is_absolute() else (repo_root() / p).resolve()

def resolve_files(text: str) -> Path:
    p = Path(text).expanduser()
    if p.is_absolute():
        return p.resolve()
    norm = str(p).replace("\\", "/")
    if norm.startswith("Files/"):
        return (files_dir() / norm[len("Files/"):]).resolve()
    return (repo_root() / p).resolve()

def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw-ledger", default=None)
    ap.add_argument("--output-config", default="configs/gold_v2/frozen_coreB_rr125_source_rule_conditions_20260603.json")
    ap.add_argument("--audit-output-dir", default=None)
    return ap.parse_args(argv)

def write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")

def parse_condition(text: Any, rule_id: str, source_column: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    if pd.isna(text) or not str(text).strip():
        return [], [{"rule_id": rule_id, "source_column": source_column, "error_type": "EMPTY", "raw_text": ""}]
    objects: List[Dict[str, Any]] = []
    errors: List[Dict[str, Any]] = []
    parts = [x.strip() for x in re.split(r"\bAND\b", str(text), flags=re.I) if x.strip()]
    for idx, part in enumerate(parts):
        m = COND_RE.fullmatch(part)
        if not m:
            errors.append({"rule_id": rule_id, "source_column": source_column, "condition_index": idx, "error_type": "UNPARSED", "raw_text": part})
        else:
            objects.append({"rule_id": rule_id, "source_column": source_column, "condition_index": idx, "field": m.group("field"), "operator": m.group("op"), "value": float(m.group("value")), "raw_text": part})
    return objects, errors

def scalar(value: Any) -> Any:
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass
    return value

def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    out_dir = Path(args.audit_output_dir).expanduser().resolve() if args.audit_output_dir else files_dir() / "FX_OUTPUTS" / "gold_v2_coreb_source_rule_conditions_freeze_audit_only"
    out_dir.mkdir(parents=True, exist_ok=True)
    raw = resolve_files(args.raw_ledger) if args.raw_ledger else files_dir() / "FX_OUTPUTS" / "gold_v2_rr125_second_core_probe_outputs" / "rr125_raw_signal_ledger.csv"
    rules: List[Dict[str, Any]] = []
    conditions: List[Dict[str, Any]] = []
    errors: List[Dict[str, Any]] = []
    status = "PENDING"
    if not raw.exists():
        status = "RULE_SOURCE_MISSING"
        df = pd.DataFrame()
    else:
        df = pd.read_csv(raw)
        missing = [c for c in REQUIRED if c not in df.columns]
        if missing:
            status = "RULE_SOURCE_MISSING"
            errors.append({"error_type": "MISSING_COLUMNS", "raw_text": ",".join(missing)})
    if status == "PENDING":
        df = df.copy()
        df["_rr"] = pd.to_numeric(df["rr"], errors="coerce")
        universe = df[df["policy"].astype(str).str.contains(SOURCE_POLICY, na=False) & df["direction"].astype(str).str.upper().eq("BUY") & (df["_rr"].sub(1.25).abs() < 1e-9)].copy()
        universe = universe[universe["base_condition"].astype(str).str.strip().ne("") & universe["added_filter_text"].astype(str).str.strip().ne("")]
        if universe.empty:
            status = "UNMAPPED_SOURCE_RULE_CONDITIONS"
        else:
            group_cols = REQUIRED
            grouped = universe.groupby(group_cols, dropna=False).size().reset_index(name="source_row_count")
            for idx, row in grouped.iterrows():
                rule_id = f"COREB_SRC_RULE_{idx:04d}"
                base_obj, base_err = parse_condition(row["base_condition"], rule_id, "base_condition")
                add_obj, add_err = parse_condition(row["added_filter_text"], rule_id, "added_filter_text")
                conditions.extend(base_obj + add_obj)
                errors.extend(base_err + add_err)
                rules.append({k: scalar(row[k]) for k in REQUIRED} | {"rule_id": rule_id, "source_row_count": int(row["source_row_count"]), "base_condition_objects": base_obj, "added_filter_condition_objects": add_obj})
            if any(e.get("source_column") == "base_condition" for e in errors):
                status = "UNPARSED_BASE_CONDITION"
            elif any(e.get("source_column") == "added_filter_text" for e in errors):
                status = "UNPARSED_ADDED_FILTER_TEXT"
            else:
                status = READY_STATUS
    pd.DataFrame(rules).to_csv(out_dir / "gold_v2_coreb_source_rule_conditions.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(conditions).to_csv(out_dir / "gold_v2_coreb_source_rule_condition_objects.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(errors).to_csv(out_dir / "gold_v2_coreb_source_rule_condition_parse_errors.csv", index=False, encoding="utf-8-sig")
    summary = {"created_utc": datetime.now(timezone.utc).isoformat(), "status": status, "audit_only": True, "component": COMPONENT, "source_rule_policy": SOURCE_POLICY, "raw_ledger": str(raw), "source_rule_condition_count": len(rules), "condition_object_count": len(conditions), "parse_error_count": len(errors), "entry_time_history_reuse_allowed": False, "historical_same_count_reuse_allowed": False, "live_evaluator_mapping_ready": False, "signal_eligible": False, "final_signal_allowed": False, "output_dir": str(out_dir)}
    if status == READY_STATUS:
        config = dict(summary)
        config["source_rule_conditions"] = rules
        out_config = resolve_repo(args.output_config)
        write_json(out_config, config)
        summary["output_config"] = str(out_config)
        summary["output_config_written"] = True
    else:
        summary["output_config_written"] = False
    write_json(out_dir / "gold_v2_coreb_source_rule_conditions_freeze_summary.json", summary)
    report = "# GOLD V2 CoreB source rule conditions freeze audit-only report\n\n" + "\n".join(f"- {k}: `{v}`" for k, v in summary.items() if k != "source_rule_conditions")
    (out_dir / "GOLD_V2_COREB_SOURCE_RULE_CONDITIONS_FREEZE_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if status == READY_STATUS else 2

if __name__ == "__main__":
    raise SystemExit(main())
