#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Freeze GOLD V2 rule source definitions from local audited exploration files.

This script creates local JSON rule-source manifests under configs/gold_v2.
It does not infer or reimplement missing rules. It records source files,
checksums, schemas, known frozen policy thresholds, and lineage so later live
rule evaluators can refuse to run unless the expected source-of-truth is present.

No Discord notification, MT5 order, AI API, or live hook is used.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import pandas as pd


COREA_OUT = "frozen_coreA_fold4_ABC_CAP5_rules_20260603.json"
COREB_OUT = "frozen_coreB_rr125_buy_confluence_rules_20260603.json"
MEDIUM_OUT = "frozen_medium_rules_20260603.json"


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Freeze GOLD V2 rule source manifests")
    p.add_argument("--core-dir", default=None)
    p.add_argument("--rr125-dir", default=None)
    p.add_argument("--medium-dir", default=None)
    p.add_argument("--config-dir", default="configs/gold_v2")
    p.add_argument("--audit-output-dir", default=None)
    return p.parse_args(argv)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def files_dir_from_repo() -> Path:
    root = repo_root()
    if len(root.parents) >= 2:
        return root.parents[1]
    return root.parent


def default_core_dir() -> Path:
    return files_dir_from_repo() / "FX_OUTPUTS" / "gold_v2_ABC_stack_cap_2025_2026_validation_outputs"


def default_rr125_dir() -> Path:
    return files_dir_from_repo() / "FX_OUTPUTS" / "gold_v2_rr125_second_core_probe_outputs"


def default_medium_dir() -> Path:
    return files_dir_from_repo() / "FX_OUTPUTS" / "gold_v2_coreb_refined_probe_outputs"


def default_audit_output_dir() -> Path:
    return files_dir_from_repo() / "FX_OUTPUTS" / "gold_v2_frozen_rule_sources_audit_only"


def resolve_repo_path(text: str) -> Path:
    p = Path(text)
    if p.is_absolute():
        return p
    return (repo_root() / p).resolve()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_csv_meta(path: Path, required: bool = True) -> Dict[str, Any]:
    if not path.exists():
        if required:
            return {"path": str(path), "exists": False, "status": "MISSING_REQUIRED"}
        return {"path": str(path), "exists": False, "status": "MISSING_OPTIONAL"}
    try:
        df = pd.read_csv(path)
    except Exception as exc:
        return {"path": str(path), "exists": True, "status": "READ_ERROR", "error": str(exc), "sha256": sha256_file(path)}
    meta = {
        "path": str(path),
        "exists": True,
        "status": "OK",
        "sha256": sha256_file(path),
        "row_count": int(len(df)),
        "columns": list(df.columns),
    }
    for col in ["dataset", "cluster_id", "direction", "priority", "component", "source", "top_variant", "policy", "rule_name", "candidate_id", "origin_id", "entry_time"]:
        if col in df.columns:
            try:
                meta[f"unique_{col}"] = int(df[col].nunique(dropna=True))
                meta[f"sample_{col}"] = [str(x) for x in df[col].dropna().astype(str).head(10).tolist()]
            except Exception:
                pass
    return meta


def all_ok(metas: List[Dict[str, Any]], require_all: bool = True) -> bool:
    if require_all:
        return all(m.get("status") == "OK" for m in metas)
    return any(m.get("status") == "OK" for m in metas)


def build_core_manifest(core_dir: Path, created_utc: str) -> Dict[str, Any]:
    files = [
        read_csv_meta(core_dir / "abc_stack_cap_2025_fold4_cluster_ledger.csv", required=True),
        read_csv_meta(core_dir / "abc_stack_cap_2026_cluster_ledger.csv", required=True),
    ]
    return {
        "policy_id": "FROZEN_GOLD_V2_COREA_FOLD4_ABC_CAP5_20260603",
        "created_utc": created_utc,
        "status": "FROZEN_RULE_SOURCE_READY" if all_ok(files) else "FROZEN_RULE_SOURCE_INCOMPLETE",
        "component": "HIGH_A_CoreA_fold4_ABC_CAP5",
        "source_of_truth_type": "audited_cluster_ledger_manifest",
        "approximation_allowed": False,
        "external_actions_allowed": False,
        "definition": {
            "ruleset": "fold4_rules",
            "entry_gate": "ABC",
            "sizing": "A_CAP5_BC_CAP3",
            "priority": "HIGH_A",
            "default_lot_multiplier_candidate": 1.0,
            "known_tp_sl_policy": "variant-defined; historical CoreA examples include TP150_SL150 for current latest candidate",
            "live_evaluator_requirement": "Must evaluate frozen fold4+ABC rules from explicit rule definitions. Do not infer from historical hit ledgers alone.",
        },
        "source_files": files,
        "blocked_until_evaluator_mapping_exists": True,
    }


def build_coreb_manifest(rr_dir: Path, created_utc: str) -> Dict[str, Any]:
    files = [
        read_csv_meta(rr_dir / "rr125_top_ledgers.csv", required=True),
        read_csv_meta(rr_dir / "rr125_raw_signal_ledger.csv", required=False),
    ]
    return {
        "policy_id": "FROZEN_GOLD_V2_COREB_RR125_BUY_CONFLUENCE_20260603",
        "created_utc": created_utc,
        "status": "FROZEN_RULE_SOURCE_READY" if all_ok(files, require_all=False) and files[0].get("status") == "OK" else "FROZEN_RULE_SOURCE_INCOMPLETE",
        "component": "HIGH_B_CoreB_RR125_BUY_CONFLUENCE",
        "source_of_truth_type": "rr125_probe_manifest",
        "approximation_allowed": False,
        "external_actions_allowed": False,
        "definition": {
            "source_rules": "BUY rules originally selected at RR1.0",
            "direction": "BUY_ONLY",
            "tp_policy": "TP = 1.25 * SL",
            "same_count_min": 15,
            "sizing": "CAP3",
            "priority": "HIGH_B",
            "default_lot_multiplier_candidate": 1.0,
            "confluence_with_coreA_buy_extra_lot": 0.5,
            "live_evaluator_requirement": "Must evaluate source BUY RR1.0 rules plus same_count>=15 using explicit selected-rule definitions. Do not infer from final ledgers alone.",
        },
        "source_files": files,
        "blocked_until_evaluator_mapping_exists": True,
    }


def build_medium_manifest(medium_dir: Path, created_utc: str) -> Dict[str, Any]:
    files = [read_csv_meta(medium_dir / "coreb_refined_rule_ledgers.csv", required=False)]
    return {
        "policy_id": "FROZEN_GOLD_V2_MEDIUM_REFINED_RULES_20260603",
        "created_utc": created_utc,
        "status": "FROZEN_RULE_SOURCE_READY",
        "component": "MEDIUM_REFined_FEATURE_GATES",
        "source_of_truth_type": "feature_threshold_manifest",
        "approximation_allowed": False,
        "external_actions_allowed": False,
        "definition": {
            "priority": "MEDIUM",
            "default_lot_multiplier_candidate": 0.5,
            "arbitration": "HIGH_A > HIGH_B > MEDIUM; MEDIUM cannot override HIGH or direction conflict rules",
            "rules": [
                {
                    "name": "RANGE96_REFINED",
                    "direction": "SELL",
                    "conditions": {"range96_min": 129.6835, "trend_eff96_max": 0.355591},
                },
                {
                    "name": "VOL_TRMEAN32_REFINED",
                    "direction": "PROBE",
                    "conditions": {"tr_mean_32_min": 10.867578, "ret96_max": -2.725, "range96_min": 176.453},
                },
                {
                    "name": "TIER2_HVT",
                    "direction": "PROBE",
                    "conditions": {"trend_eff96_max": 0.4, "ret96_max": -25.0, "tr_mean_32_min": 10.867578},
                },
            ],
            "live_evaluator_requirement": "MEDIUM gates may be evaluated from features, but final signal eligibility requires CoreA/CoreB arbitration.",
        },
        "source_files": files,
        "blocked_until_core_arbitration_exists": True,
    }


def write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")


def build_report(core: Dict[str, Any], coreb: Dict[str, Any], medium: Dict[str, Any]) -> str:
    lines: List[str] = []
    lines.append("# GOLD V2 frozen rule sources audit-only report")
    lines.append("")
    for obj in [core, coreb, medium]:
        lines.append(f"## {obj['component']}")
        lines.append(f"- policy_id: `{obj['policy_id']}`")
        lines.append(f"- status: `{obj['status']}`")
        lines.append(f"- approximation_allowed: `{obj['approximation_allowed']}`")
        for src in obj.get("source_files", []):
            lines.append(f"  - {src.get('path')}: `{src.get('status')}` rows={src.get('row_count', '-')}")
        lines.append("")
    lines.append("No external action is performed. These files are manifests for later evaluator mapping.")
    return "\n".join(lines)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    core_dir = Path(args.core_dir).expanduser().resolve() if args.core_dir else default_core_dir()
    rr_dir = Path(args.rr125_dir).expanduser().resolve() if args.rr125_dir else default_rr125_dir()
    medium_dir = Path(args.medium_dir).expanduser().resolve() if args.medium_dir else default_medium_dir()
    config_dir = resolve_repo_path(args.config_dir)
    audit_dir = Path(args.audit_output_dir).expanduser().resolve() if args.audit_output_dir else default_audit_output_dir()
    config_dir.mkdir(parents=True, exist_ok=True)
    audit_dir.mkdir(parents=True, exist_ok=True)
    created_utc = datetime.now(timezone.utc).isoformat()

    core = build_core_manifest(core_dir, created_utc)
    coreb = build_coreb_manifest(rr_dir, created_utc)
    medium = build_medium_manifest(medium_dir, created_utc)

    outputs = {
        COREA_OUT: core,
        COREB_OUT: coreb,
        MEDIUM_OUT: medium,
    }
    for name, obj in outputs.items():
        write_json(config_dir / name, obj)
        write_json(audit_dir / name, obj)

    summary = {
        "created_utc": created_utc,
        "config_dir": str(config_dir),
        "audit_dir": str(audit_dir),
        "core_status": core["status"],
        "coreb_status": coreb["status"],
        "medium_status": medium["status"],
        "all_required_ready": core["status"] == "FROZEN_RULE_SOURCE_READY" and coreb["status"] == "FROZEN_RULE_SOURCE_READY" and medium["status"] == "FROZEN_RULE_SOURCE_READY",
        "important_note": "These are frozen source manifests, not full live evaluator mappings. Approximate reimplementation remains forbidden.",
    }
    write_json(audit_dir / "gold_v2_frozen_rule_sources_summary.json", summary)
    (audit_dir / "GOLD_V2_FROZEN_RULE_SOURCES_AUDIT_ONLY_REPORT.md").write_text(build_report(core, coreb, medium), encoding="utf-8")

    print(f"[DONE] config_dir={config_dir}")
    print(f"core_status={core['status']}")
    print(f"coreb_status={coreb['status']}")
    print(f"medium_status={medium['status']}")
    print(f"all_required_ready={summary['all_required_ready']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
