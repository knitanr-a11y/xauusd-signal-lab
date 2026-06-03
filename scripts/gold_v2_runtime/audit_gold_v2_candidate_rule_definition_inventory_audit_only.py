#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""GOLD V2 12C: candidate rule-definition inventory audit.

This is audit-only. Candidate evidence is not a live rule.

The purpose is to expand 12B CANDIDATE_EVIDENCE_ONLY rows into a concrete
inventory of source columns, unique values, parsed variants, and text fields
that may later be used to author explicit frozen live-evaluator predicates.

This script does not:
  * infer CoreA/CoreB live rules
  * convert entry_time or ledger hits into live signals
  * mark step-12 mappings as MAPPING_READY
  * connect step 13
  * call Discord / MT5 / AI API / live hooks
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import pandas as pd


POLICY_DEFAULT = "configs/gold_v2/gold_v2_coreA_coreB_medium_policy_20260603.json"
COREA_FROZEN_DEFAULT = "configs/gold_v2/frozen_coreA_fold4_ABC_CAP5_rules_20260603.json"
COREB_FROZEN_DEFAULT = "configs/gold_v2/frozen_coreB_rr125_buy_confluence_rules_20260603.json"
MEDIUM_FROZEN_DEFAULT = "configs/gold_v2/frozen_medium_rules_20260603.json"
COREA_MAPPING_DEFAULT = "configs/gold_v2/live_evaluator_mapping_coreA_20260603.json"
COREB_MAPPING_DEFAULT = "configs/gold_v2/live_evaluator_mapping_coreB_20260603.json"
MEDIUM_MAPPING_DEFAULT = "configs/gold_v2/live_evaluator_mapping_medium_20260603.json"

EXTERNAL_ACTIONS_OFF = {
    "discord_send_allowed": False,
    "mt5_order_allowed": False,
    "ai_api_allowed": False,
    "live_hook_allowed": False,
}

COREA_COMPONENT = "HIGH_A_CoreA_fold4_ABC_CAP5"
COREB_COMPONENT = "HIGH_B_CoreB_RR125_BUY_CONFLUENCE"
MEDIUM_COMPONENT = "MEDIUM_REFINED_FEATURE_GATES"

COREA_COLUMNS = [
    "ruleset", "scenario", "period", "fold_id", "test_month", "view",
    "cluster_id", "cluster_start", "cluster_end", "top_entry_time", "top_exit_time",
    "top_candidate_id", "top_variant", "top_direction", "top_profit_r", "top_score",
    "same_direction_count", "opposite_direction_count", "same_direction_score_sum",
    "opposite_direction_score_sum", "unique_same_direction_origins",
    "unique_same_direction_variants", "stacked_same_direction_profit_r",
    "stacked_capped3_profit_r", "has_opposite_conflict", "entry_month",
    "close_time", "atr14", "tr_mean_32", "range96", "range192", "trend_eff96",
    "adx14", "ret96", "regime", "rr", "no_opposite", "is_A",
    "is_B_rr15_fixed", "is_C_fixed", "signal_ABC", "signal_fixed_ABC",
    "signal_trainC_ABC", "signal", "profit", "profit_fixed_ABC", "profit_A_only",
    "profit_A_Brr", "profit_cap1_from_members", "profit_cap3_from_members",
    "profit_cap5_from_members", "profit_uncap_from_members", "profit_origin1_from_members",
    "profit_origin1_cap5_from_members", "same_direction_count_from_members",
    "unique_origins_from_members", "component", "component_desc",
    "selected_profit_r",
]

COREB_COLUMNS = [
    "cluster_id", "entry_time", "entry_month", "profit", "top_direction",
    "same_count", "unique_origins", "top_candidate_id", "rr_bucket",
    "source_rule_count", "dataset", "policy", "filter", "entry_price",
    "exit_time", "profit_r", "candidate_id", "origin_id", "direction",
    "variant", "tp_pips", "sl_pips", "rr", "base_condition",
    "added_filter_text", "train_score",
]

TEXT_COLUMNS = [
    "base_condition", "added_filter_text", "variant", "top_variant", "component_desc",
    "ruleset", "scenario", "policy", "filter", "view", "signal",
]

VARIANT_RE = re.compile(
    r"(?P<direction>BUY|SELL)[_\- ]*TP(?P<tp>[0-9]+(?:\.[0-9]+)?)[_\- ]*SL(?P<sl>[0-9]+(?:\.[0-9]+)?)(?:[_\- ]*RR(?P<rr>[0-9]+(?:p[0-9]+)?|[0-9]+(?:\.[0-9]+)?))?",
    re.IGNORECASE,
)


@dataclass
class AuditCheck:
    check_name: str
    status: str
    message: str
    detail: str = ""


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Inventory GOLD V2 candidate rule-definition evidence without implementing live rules."
    )
    p.add_argument("--policy", default=POLICY_DEFAULT)
    p.add_argument("--corea-frozen", default=COREA_FROZEN_DEFAULT)
    p.add_argument("--coreb-frozen", default=COREB_FROZEN_DEFAULT)
    p.add_argument("--medium-frozen", default=MEDIUM_FROZEN_DEFAULT)
    p.add_argument("--corea-mapping", default=COREA_MAPPING_DEFAULT)
    p.add_argument("--coreb-mapping", default=COREB_MAPPING_DEFAULT)
    p.add_argument("--medium-mapping", default=MEDIUM_MAPPING_DEFAULT)
    p.add_argument("--audit-output-dir", default=None)
    p.add_argument("--max-unique-values", type=int, default=200)
    p.add_argument("--max-text-samples", type=int, default=500)
    p.add_argument("--skip-source-file-sha-verify", action="store_true")
    return p.parse_args(argv)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def files_dir_from_repo() -> Path:
    root = repo_root()
    if len(root.parents) >= 2:
        return root.parents[1]
    return root.parent


def default_audit_output_dir() -> Path:
    return files_dir_from_repo() / "FX_OUTPUTS" / "gold_v2_candidate_rule_definition_inventory_audit_only"


def resolve_repo_path(text: str) -> Path:
    path = Path(text)
    if path.is_absolute():
        return path
    return (repo_root() / path).resolve()


def resolve_manifest_source_path(value: Any) -> Optional[Path]:
    if value is None:
        return None
    text = str(value)
    if not text:
        return None
    path = Path(text)
    if path.is_absolute():
        return path
    normalized = text.replace("\\", "/")
    if normalized.startswith("Files/"):
        return (files_dir_from_repo() / normalized[len("Files/"):]).resolve()
    return (repo_root() / path).resolve()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")


def add_check(rows: List[AuditCheck], name: str, ok: bool, message: str, detail: str = "") -> None:
    rows.append(AuditCheck(name, "OK" if ok else "ERROR", message, detail))


def load_json_or_none(label: str, path: Path, checks: List[AuditCheck]) -> Optional[Dict[str, Any]]:
    if not path.exists():
        add_check(checks, f"{label}_exists", False, f"missing: {path}")
        return None
    add_check(checks, f"{label}_exists", True, str(path))
    try:
        obj = read_json(path)
    except Exception as exc:
        add_check(checks, f"{label}_parse", False, "JSON parse failed", repr(exc))
        return None
    add_check(checks, f"{label}_parse", True, "JSON parsed")
    return obj


def validate_policy_safety(policy: Dict[str, Any], checks: List[AuditCheck]) -> bool:
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


def source_records(component: str, manifest: Optional[Dict[str, Any]], *, skip_sha_verify: bool) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    if not manifest:
        return records

    for idx, src in enumerate(manifest.get("source_files", []) or []):
        rec = dict(src) if isinstance(src, dict) else {"raw": src}
        rec["component"] = component
        rec["source_index"] = idx
        path = resolve_manifest_source_path(rec.get("path"))
        rec["resolved_path"] = str(path) if path else None

        if path is None:
            rec["disk_status"] = "NO_PATH"
            records.append(rec)
            continue
        if not path.exists():
            rec["disk_status"] = "SOURCE_FILE_MISSING"
            records.append(rec)
            continue

        rec["disk_status"] = "ACCESSIBLE"
        try:
            header = list(pd.read_csv(path, nrows=0).columns)
            rec["columns_actual"] = header
        except Exception as exc:
            rec["disk_status"] = "SOURCE_FILE_UNREADABLE"
            rec["read_error"] = repr(exc)
            records.append(rec)
            continue

        if skip_sha_verify:
            rec["sha256_match"] = None
        else:
            try:
                actual = sha256_file(path)
                rec["actual_sha256"] = actual
                rec["sha256_match"] = actual == rec.get("sha256")
            except Exception as exc:
                rec["sha_error"] = repr(exc)
                rec["sha256_match"] = False
        records.append(rec)

    return records


def safe_read_csv(path: Path, use_columns: List[str]) -> pd.DataFrame:
    header = list(pd.read_csv(path, nrows=0).columns)
    selected = [col for col in use_columns if col in header]
    if not selected:
        return pd.DataFrame()
    return pd.read_csv(path, usecols=selected)


def normalize_value(value: Any) -> str:
    if pd.isna(value):
        return ""
    text = str(value)
    return text.replace("\r", " ").replace("\n", " ").strip()


def value_inventory(df: pd.DataFrame, *, component: str, source_index: int, path_text: str, max_unique: int) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    if df.empty:
        return rows

    for col in df.columns:
        series = df[col]
        non_null = series.dropna()
        unique_count = int(non_null.astype(str).nunique(dropna=True))
        counts = non_null.astype(str).value_counts(dropna=True).head(max_unique)
        for value, count in counts.items():
            rows.append(
                {
                    "component": component,
                    "source_index": source_index,
                    "path": path_text,
                    "column": col,
                    "unique_count_total": unique_count,
                    "value": str(value)[:1000],
                    "count": int(count),
                    "is_candidate_evidence_only": True,
                }
            )
    return rows


def parse_variant_text(text: str) -> Dict[str, Any]:
    match = VARIANT_RE.search(text or "")
    if not match:
        return {"parsed": False, "direction": None, "tp": None, "sl": None, "rr": None}
    rr = match.group("rr")
    rr_norm = rr.replace("p", ".") if rr else None
    return {
        "parsed": True,
        "direction": match.group("direction").upper(),
        "tp": float(match.group("tp")),
        "sl": float(match.group("sl")),
        "rr": float(rr_norm) if rr_norm else None,
    }


def variant_inventory(df: pd.DataFrame, *, component: str, source_index: int, path_text: str) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for col in ["top_variant", "variant"]:
        if col not in df.columns:
            continue
        counts = df[col].dropna().astype(str).value_counts(dropna=True)
        for value, count in counts.items():
            parsed = parse_variant_text(value)
            rows.append(
                {
                    "component": component,
                    "source_index": source_index,
                    "path": path_text,
                    "column": col,
                    "variant_text": value,
                    "count": int(count),
                    "parsed_variant": bool(parsed["parsed"]),
                    "parsed_direction": parsed["direction"],
                    "parsed_tp": parsed["tp"],
                    "parsed_sl": parsed["sl"],
                    "parsed_rr": parsed["rr"],
                    "is_candidate_evidence_only": True,
                }
            )
    return rows


def numeric_stats(df: pd.DataFrame, *, component: str, source_index: int, path_text: str) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    numeric_targets = [
        "same_count", "source_rule_count", "unique_origins",
        "same_direction_count", "opposite_direction_count",
        "unique_same_direction_origins", "unique_same_direction_variants",
        "tp_pips", "sl_pips", "rr", "profit_r", "top_profit_r", "top_score",
        "profit_cap3_from_members", "profit_cap5_from_members",
    ]
    for col in numeric_targets:
        if col not in df.columns:
            continue
        series = pd.to_numeric(df[col], errors="coerce").dropna()
        if series.empty:
            continue
        rows.append(
            {
                "component": component,
                "source_index": source_index,
                "path": path_text,
                "column": col,
                "count": int(series.shape[0]),
                "min": float(series.min()),
                "max": float(series.max()),
                "mean": float(series.mean()),
                "median": float(series.median()),
                "is_candidate_evidence_only": True,
            }
        )
    return rows


def text_samples(df: pd.DataFrame, *, component: str, source_index: int, path_text: str, max_samples: int) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for col in TEXT_COLUMNS:
        if col not in df.columns:
            continue
        values: List[str] = []
        seen = set()
        for raw in df[col].dropna().tolist():
            text = normalize_value(raw)
            if not text or text in seen:
                continue
            seen.add(text)
            values.append(text)
            if len(values) >= max_samples:
                break
        for text in values:
            rows.append(
                {
                    "component": component,
                    "source_index": source_index,
                    "path": path_text,
                    "column": col,
                    "sample_text": text[:1000],
                    "is_candidate_evidence_only": True,
                }
            )
    return rows


def inventory_component(
    component: str,
    sources: List[Dict[str, Any]],
    columns: List[str],
    *,
    max_unique: int,
    max_text_samples: int,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    value_rows: List[Dict[str, Any]] = []
    variant_rows: List[Dict[str, Any]] = []
    numeric_rows: List[Dict[str, Any]] = []
    text_rows: List[Dict[str, Any]] = []

    for rec in sources:
        if rec.get("disk_status") != "ACCESSIBLE" or not rec.get("resolved_path"):
            continue
        path = Path(str(rec["resolved_path"]))
        df = safe_read_csv(path, columns)
        if df.empty:
            continue
        value_rows.extend(value_inventory(df, component=component, source_index=int(rec.get("source_index", -1)), path_text=str(path), max_unique=max_unique))
        variant_rows.extend(variant_inventory(df, component=component, source_index=int(rec.get("source_index", -1)), path_text=str(path)))
        numeric_rows.extend(numeric_stats(df, component=component, source_index=int(rec.get("source_index", -1)), path_text=str(path)))
        text_rows.extend(text_samples(df, component=component, source_index=int(rec.get("source_index", -1)), path_text=str(path), max_samples=max_text_samples))
    return value_rows, variant_rows, numeric_rows, text_rows


def mapping_unmapped_count(mapping: Optional[Dict[str, Any]]) -> int:
    if not mapping:
        return 0
    return int(len(mapping.get("unmapped_conditions", []) or []))


def build_component_summary(component: str, mapping: Optional[Dict[str, Any]], sources: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "component": component,
        "mapping_status": mapping.get("status") if mapping else None,
        "unmapped_condition_count": mapping_unmapped_count(mapping),
        "source_file_count": len(sources),
        "accessible_source_file_count": sum(1 for row in sources if row.get("disk_status") == "ACCESSIBLE"),
        "all_sha256_match_or_skipped": all(row.get("sha256_match") in {True, None} for row in sources),
        "live_evaluator_connection_allowed": False,
    }


def build_report(summary: Dict[str, Any], component_rows: List[Dict[str, Any]]) -> str:
    lines: List[str] = []
    lines.append("# GOLD V2 candidate rule definition inventory audit-only report")
    lines.append("")
    lines.append(f"Created UTC: {summary['created_utc']}")
    lines.append(f"Status: `{summary['status']}`")
    lines.append(f"Audit only: `{summary['audit_only']}`")
    lines.append(f"live_evaluator_connection_allowed: `{summary['live_evaluator_connection_allowed']}`")
    lines.append("")
    lines.append("## External actions")
    lines.append("")
    for key, value in EXTERNAL_ACTIONS_OFF.items():
        lines.append(f"- {key}: `{value}`")
    lines.append("- no_signal_discord_policy: `DO_NOT_NOTIFY_ON_NO_SIGNAL`")
    lines.append("")
    lines.append("## Component summary")
    lines.append("")
    lines.append("| component | mapping_status | unmapped_condition_count | accessible_source_file_count |")
    lines.append("| --- | --- | ---: | ---: |")
    for row in component_rows:
        lines.append(f"| {row.get('component')} | `{row.get('mapping_status')}` | {row.get('unmapped_condition_count')} | {row.get('accessible_source_file_count')} |")
    lines.append("")
    lines.append("## Important")
    lines.append("")
    lines.append("This inventory is candidate evidence only. It is not a live rule definition and must not be used to connect step 13.")
    lines.append("")
    lines.append("A later explicit freezing step must author strict live_evaluator_mapping.conditions from accepted definitions, then rerun step 12 until there is no blocking UNMAPPED_CONDITION.")
    lines.append("")
    lines.append("No Discord notification, MT5 order, AI API call, or live hook is performed.")
    return "\n".join(lines)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    output_dir = Path(args.audit_output_dir).expanduser().resolve() if args.audit_output_dir else default_audit_output_dir()
    output_dir.mkdir(parents=True, exist_ok=True)

    checks: List[AuditCheck] = []
    policy = load_json_or_none("policy", resolve_repo_path(args.policy), checks) or {}
    policy_ok = validate_policy_safety(policy, checks) if policy else False

    corea_frozen = load_json_or_none("corea_frozen", resolve_repo_path(args.corea_frozen), checks)
    coreb_frozen = load_json_or_none("coreb_frozen", resolve_repo_path(args.coreb_frozen), checks)
    medium_frozen = load_json_or_none("medium_frozen", resolve_repo_path(args.medium_frozen), checks)

    corea_mapping = load_json_or_none("corea_mapping", resolve_repo_path(args.corea_mapping), checks)
    coreb_mapping = load_json_or_none("coreb_mapping", resolve_repo_path(args.coreb_mapping), checks)
    medium_mapping = load_json_or_none("medium_mapping", resolve_repo_path(args.medium_mapping), checks)

    corea_sources = source_records(COREA_COMPONENT, corea_frozen, skip_sha_verify=bool(args.skip_source_file_sha_verify))
    coreb_sources = source_records(COREB_COMPONENT, coreb_frozen, skip_sha_verify=bool(args.skip_source_file_sha_verify))
    medium_sources = source_records(MEDIUM_COMPONENT, medium_frozen, skip_sha_verify=bool(args.skip_source_file_sha_verify))

    corea_values, corea_variants, corea_numeric, corea_text = inventory_component(COREA_COMPONENT, corea_sources, COREA_COLUMNS, max_unique=int(args.max_unique_values), max_text_samples=int(args.max_text_samples))
    coreb_values, coreb_variants, coreb_numeric, coreb_text = inventory_component(COREB_COMPONENT, coreb_sources, COREB_COLUMNS, max_unique=int(args.max_unique_values), max_text_samples=int(args.max_text_samples))

    value_rows = corea_values + coreb_values
    variant_rows = corea_variants + coreb_variants
    numeric_rows = corea_numeric + coreb_numeric
    text_rows = corea_text + coreb_text

    component_rows = [
        build_component_summary(COREA_COMPONENT, corea_mapping, corea_sources),
        build_component_summary(COREB_COMPONENT, coreb_mapping, coreb_sources),
        build_component_summary(MEDIUM_COMPONENT, medium_mapping, medium_sources),
    ]

    summary = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "CANDIDATE_RULE_DEFINITION_INVENTORY_READY_BUT_NOT_STRICT_MAPPING",
        "audit_only": True,
        "policy_safety_ok": bool(policy_ok),
        "external_actions": dict(EXTERNAL_ACTIONS_OFF),
        "no_signal_discord_policy": "DO_NOT_NOTIFY_ON_NO_SIGNAL",
        "output_dir": str(output_dir),
        "component_summary": component_rows,
        "candidate_value_row_count": len(value_rows),
        "candidate_variant_row_count": len(variant_rows),
        "candidate_numeric_stat_row_count": len(numeric_rows),
        "candidate_text_sample_row_count": len(text_rows),
        "live_evaluator_connection_allowed": False,
        "important_note": "Candidate inventory is not a live rule. Do not connect step 13 until explicit live_evaluator_mapping.conditions are frozen and step 12 has no blocking UNMAPPED_CONDITION.",
    }

    pd.DataFrame(component_rows).to_csv(output_dir / "gold_v2_candidate_component_summary.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(corea_sources + coreb_sources + medium_sources).to_csv(output_dir / "gold_v2_candidate_source_file_audit.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(value_rows).to_csv(output_dir / "gold_v2_candidate_value_inventory.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(variant_rows).to_csv(output_dir / "gold_v2_candidate_variant_inventory.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(numeric_rows).to_csv(output_dir / "gold_v2_candidate_numeric_stats.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(text_rows).to_csv(output_dir / "gold_v2_candidate_text_samples.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame([asdict(check) for check in checks]).to_csv(output_dir / "gold_v2_candidate_inventory_audit_checks.csv", index=False, encoding="utf-8-sig")
    write_json(output_dir / "gold_v2_candidate_rule_definition_inventory_summary.json", summary)
    (output_dir / "GOLD_V2_CANDIDATE_RULE_DEFINITION_INVENTORY_AUDIT_ONLY_REPORT.md").write_text(build_report(summary, component_rows), encoding="utf-8")

    print(f"[DONE] status={summary['status']} audit_dir={output_dir}")
    print(pd.DataFrame(component_rows).to_string(index=False))
    print("")
    print("No Discord notification, MT5 order, AI API call, or live hook was performed.")
    print("Candidate inventory is not a live rule. Step 13 remains blocked until step 12 has no blocking UNMAPPED_CONDITION.")

    if not policy_ok:
        print("[STOP] Policy safety check failed.")
        return 2
    if corea_frozen is None or coreb_frozen is None or corea_mapping is None or coreb_mapping is None:
        print("[STOP] Required CoreA/CoreB frozen or mapping JSON is missing.")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
