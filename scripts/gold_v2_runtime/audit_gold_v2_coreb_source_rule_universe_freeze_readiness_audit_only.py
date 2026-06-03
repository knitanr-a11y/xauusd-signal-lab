#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""GOLD V2 12E: CoreB source rule universe freeze-readiness audit.

Audit-only. This script does not create live evaluator mappings, does not
connect step 13, and does not call Discord/MT5/AI/live hooks.
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
COREB_FROZEN_DEFAULT = "configs/gold_v2/frozen_coreB_rr125_buy_confluence_rules_20260603.json"
COREB_MAPPING_DEFAULT = "configs/gold_v2/live_evaluator_mapping_coreB_20260603.json"
COREB_COMPONENT = "HIGH_B_CoreB_RR125_BUY_CONFLUENCE"
EXTERNAL_ACTIONS_OFF = {"discord_send_allowed": False, "mt5_order_allowed": False, "ai_api_allowed": False, "live_hook_allowed": False}
COMPARISON_RE = re.compile(r"(?P<field>[A-Za-z_][A-Za-z0-9_]*)\s*(?P<op>>=|<=|==|>|<)\s*(?P<value>-?\d+(?:\.\d+)?|[A-Za-z_][A-Za-z0-9_]*)", re.I)
VARIANT_RE = re.compile(r"(?P<direction>BUY|SELL)[_\- ]*TP(?P<tp>\d+(?:\.\d+)?)[_\- ]*SL(?P<sl>\d+(?:\.\d+)?)(?:[_\- ]*RR(?P<rr>\d+(?:p\d+)?|\d+(?:\.\d+)?))?", re.I)

@dataclass
class AuditCheck:
    check_name: str
    status: str
    message: str
    detail: str = ""


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Audit GOLD V2 CoreB source rule universe freeze readiness")
    p.add_argument("--policy", default=POLICY_DEFAULT)
    p.add_argument("--coreb-frozen", default=COREB_FROZEN_DEFAULT)
    p.add_argument("--coreb-mapping", default=COREB_MAPPING_DEFAULT)
    p.add_argument("--audit-output-dir", default=None)
    p.add_argument("--skip-source-file-sha-verify", action="store_true")
    return p.parse_args(argv)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def files_dir_from_repo() -> Path:
    root = repo_root()
    return root.parents[1] if len(root.parents) >= 2 else root.parent


def default_audit_output_dir() -> Path:
    return files_dir_from_repo() / "FX_OUTPUTS" / "gold_v2_coreb_source_rule_universe_freeze_readiness_audit_only"


def resolve_repo_path(text: str) -> Path:
    p = Path(text)
    return p if p.is_absolute() else (repo_root() / p).resolve()


def resolve_manifest_source_path(value: Any) -> Optional[Path]:
    if value is None:
        return None
    text = str(value)
    if not text:
        return None
    p = Path(text)
    if p.is_absolute():
        return p
    norm = text.replace("\\", "/")
    if norm.startswith("Files/"):
        return (files_dir_from_repo() / norm[len("Files/"):]).resolve()
    return (repo_root() / p).resolve()


def add_check(rows: List[AuditCheck], name: str, ok: bool, message: str, detail: str = "") -> None:
    rows.append(AuditCheck(name, "OK" if ok else "ERROR", message, detail))


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


def load_json_or_none(label: str, path: Path, checks: List[AuditCheck]) -> Optional[Dict[str, Any]]:
    if not path.exists():
        add_check(checks, f"{label}_exists", False, f"missing: {path}")
        return None
    add_check(checks, f"{label}_exists", True, str(path))
    try:
        return read_json(path)
    except Exception as exc:
        add_check(checks, f"{label}_parse", False, "JSON parse failed", repr(exc))
        return None


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


def parse_scalar(text: str) -> Any:
    if re.fullmatch(r"-?\d+", text):
        return int(text)
    if re.fullmatch(r"-?\d+\.\d+", text):
        return float(text)
    return text


def parse_condition_text(text: Any) -> Tuple[List[Dict[str, Any]], List[str]]:
    if pd.isna(text):
        return [], []
    rows: List[Dict[str, Any]] = []
    misses: List[str] = []
    for idx, part in enumerate([p.strip() for p in re.split(r"\bAND\b", str(text), flags=re.I) if p.strip()]):
        m = COMPARISON_RE.fullmatch(part)
        if not m:
            misses.append(part)
            continue
        rows.append({"field": m.group("field"), "operator": m.group("op"), "value": parse_scalar(m.group("value")), "raw_text": part, "condition_index": idx})
    return rows, misses


def parse_variant_text(text: Any) -> Dict[str, Any]:
    m = VARIANT_RE.search(str(text) if text is not None and not pd.isna(text) else "")
    if not m:
        return {"parsed": False}
    rr = m.group("rr")
    rr_val = float(rr.replace("p", ".")) if rr else None
    return {"parsed": True, "direction": m.group("direction").upper(), "tp": float(m.group("tp")), "sl": float(m.group("sl")), "rr": rr_val}


def source_file_records(manifest: Optional[Dict[str, Any]], checks: List[AuditCheck], *, skip_sha_verify: bool) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    if not manifest:
        return records
    for idx, src in enumerate(manifest.get("source_files", []) or []):
        rec = dict(src) if isinstance(src, dict) else {"raw": src}
        rec["source_index"] = idx
        path = resolve_manifest_source_path(rec.get("path"))
        rec["resolved_path"] = str(path) if path else None
        basename = Path(str(rec.get("path", ""))).name.lower()
        if "raw" in basename:
            rec["source_kind"] = "raw_signal_ledger"
        elif "top" in basename:
            rec["source_kind"] = "top_ledger"
        else:
            rec["source_kind"] = "unknown"
        if path is None:
            rec["disk_status"] = "NO_PATH"
            add_check(checks, f"source_{idx}_path", False, "source path missing")
            records.append(rec)
            continue
        if not path.exists():
            rec["disk_status"] = "SOURCE_FILE_MISSING"
            add_check(checks, f"source_{idx}_exists", False, str(path))
            records.append(rec)
            continue
        rec["disk_status"] = "ACCESSIBLE"
        add_check(checks, f"source_{idx}_exists", True, str(path))
        try:
            header = list(pd.read_csv(path, nrows=0).columns)
            rec["columns_actual"] = header
        except Exception as exc:
            rec["disk_status"] = "SOURCE_FILE_UNREADABLE"
            rec["read_error"] = repr(exc)
            add_check(checks, f"source_{idx}_read_header", False, str(path), repr(exc))
        if not skip_sha_verify and rec.get("disk_status") == "ACCESSIBLE":
            try:
                actual = sha256_file(path)
                rec["actual_sha256"] = actual
                rec["sha256_match"] = actual == rec.get("sha256")
            except Exception as exc:
                rec["sha_error"] = repr(exc)
                rec["sha256_match"] = False
        else:
            rec["sha256_match"] = None
        records.append(rec)
    return records


def read_csv_or_empty(path: Path) -> pd.DataFrame:
    try:
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame()


def build_rule_universe(raw_df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame, List[Dict[str, Any]]]:
    required = ["candidate_id", "origin_id", "direction", "variant", "tp_pips", "sl_pips", "rr", "rr_bucket", "base_condition", "added_filter_text", "policy"]
    for col in required:
        if col not in raw_df.columns:
            raw_df[col] = None
    group_cols = required
    grouped = raw_df.groupby(group_cols, dropna=False).size().reset_index(name="raw_signal_row_count")
    universe_rows: List[Dict[str, Any]] = []
    condition_rows: List[Dict[str, Any]] = []
    gaps: List[Dict[str, Any]] = []
    for idx, row in grouped.iterrows():
        base_parsed, base_misses = parse_condition_text(row.get("base_condition"))
        filter_parsed, filter_misses = parse_condition_text(row.get("added_filter_text"))
        variant = parse_variant_text(row.get("variant"))
        direction_ok = str(row.get("direction", "")).upper() == "BUY"
        variant_ok = bool(variant.get("parsed")) and variant.get("direction") == "BUY"
        rr_val = pd.to_numeric(pd.Series([row.get("rr")]), errors="coerce").iloc[0]
        rr125_ok = pd.notna(rr_val) and abs(float(rr_val) - 1.25) < 1e-9
        tp_val = pd.to_numeric(pd.Series([row.get("tp_pips")]), errors="coerce").iloc[0]
        sl_val = pd.to_numeric(pd.Series([row.get("sl_pips")]), errors="coerce").iloc[0]
        tp_sl_ok = pd.notna(tp_val) and pd.notna(sl_val) and sl_val != 0 and abs(float(tp_val) / float(sl_val) - 1.25) < 1e-9
        identifiers_ok = all(str(row.get(c, "")).strip() not in {"", "nan", "None"} for c in ["candidate_id", "origin_id"])
        base_ok = bool(base_parsed) and not base_misses
        filter_ok = not filter_misses
        freeze_ready = direction_ok and variant_ok and rr125_ok and tp_sl_ok and identifiers_ok and base_ok and filter_ok
        rule_id = f"COREB_RULE_{idx:04d}"
        universe_rows.append({
            "rule_id": rule_id,
            "candidate_id": row.get("candidate_id"),
            "origin_id": row.get("origin_id"),
            "direction": row.get("direction"),
            "variant": row.get("variant"),
            "tp_pips": row.get("tp_pips"),
            "sl_pips": row.get("sl_pips"),
            "rr": row.get("rr"),
            "rr_bucket": row.get("rr_bucket"),
            "policy": row.get("policy"),
            "base_condition": row.get("base_condition"),
            "added_filter_text": row.get("added_filter_text"),
            "raw_signal_row_count": int(row.get("raw_signal_row_count", 0)),
            "direction_ok": direction_ok,
            "variant_ok": variant_ok,
            "rr125_ok": rr125_ok,
            "tp_sl_policy_ok": tp_sl_ok,
            "identifiers_ok": identifiers_ok,
            "base_condition_parse_ok": base_ok,
            "added_filter_parse_ok": filter_ok,
            "freeze_ready_candidate": freeze_ready,
            "is_candidate_evidence_only": True,
        })
        for source_col, parsed in [("base_condition", base_parsed), ("added_filter_text", filter_parsed)]:
            for j, cond in enumerate(parsed):
                condition_rows.append({"rule_id": rule_id, "source_column": source_col, "condition_index": j, "field": cond["field"], "operator": cond["operator"], "value": cond["value"], "raw_text": cond["raw_text"], "is_candidate_evidence_only": True})
        for source_col, misses in [("base_condition", base_misses), ("added_filter_text", filter_misses)]:
            for miss in misses:
                gaps.append({"component": COREB_COMPONENT, "rule_id": rule_id, "gap_type": "UNPARSED_CONDITION_TEXT", "source_column": source_col, "raw_text": miss, "blocking": True})
        if not freeze_ready:
            for key, ok in [("direction_ok", direction_ok), ("variant_ok", variant_ok), ("rr125_ok", rr125_ok), ("tp_sl_policy_ok", tp_sl_ok), ("identifiers_ok", identifiers_ok), ("base_condition_parse_ok", base_ok), ("added_filter_parse_ok", filter_ok)]:
                if not ok:
                    gaps.append({"component": COREB_COMPONENT, "rule_id": rule_id, "gap_type": key, "source_column": "rule_universe", "raw_text": str(row.to_dict())[:1000], "blocking": True})
    return pd.DataFrame(universe_rows), pd.DataFrame(condition_rows), gaps


def build_same_count_audit(top_df: pd.DataFrame) -> Tuple[pd.DataFrame, List[Dict[str, Any]]]:
    gaps: List[Dict[str, Any]] = []
    if top_df.empty:
        return pd.DataFrame(), [{"component": COREB_COMPONENT, "gap_type": "TOP_LEDGER_MISSING", "blocking": True}]
    for col in ["top_direction", "same_count", "source_rule_count", "unique_origins", "policy", "cluster_id", "top_candidate_id", "rr_bucket"]:
        if col not in top_df.columns:
            top_df[col] = None
    df = top_df.copy()
    df["same_count_num"] = pd.to_numeric(df["same_count"], errors="coerce")
    df["same_count_min15"] = df["same_count_num"] >= 15
    df["top_direction_buy"] = df["top_direction"].astype(str).str.upper().eq("BUY")
    df["required_fields_present"] = df[["same_count", "source_rule_count", "unique_origins", "policy"]].notna().all(axis=1)
    df["same_count_freeze_ready_candidate"] = df["same_count_min15"] & df["top_direction_buy"] & df["required_fields_present"]
    summary = df.groupby(["top_direction_buy", "same_count_min15", "required_fields_present", "same_count_freeze_ready_candidate"], dropna=False).size().reset_index(name="row_count")
    if not bool(df["same_count_freeze_ready_candidate"].any()):
        gaps.append({"component": COREB_COMPONENT, "gap_type": "NO_SAME_COUNT_READY_ROWS", "reason": "No top ledger rows satisfy BUY + same_count>=15 + required fields present.", "blocking": True})
    return summary, gaps


def build_variant_audit(universe: pd.DataFrame) -> pd.DataFrame:
    if universe.empty:
        return pd.DataFrame()
    cols = ["variant", "direction", "tp_pips", "sl_pips", "rr", "raw_signal_row_count", "direction_ok", "variant_ok", "rr125_ok", "tp_sl_policy_ok", "freeze_ready_candidate"]
    return universe.groupby([c for c in cols if c != "raw_signal_row_count"], dropna=False)["raw_signal_row_count"].sum().reset_index().sort_values("raw_signal_row_count", ascending=False)


def build_report(summary: Dict[str, Any]) -> str:
    lines = ["# GOLD V2 CoreB source rule universe freeze-readiness audit-only report", "", f"Created UTC: {summary['created_utc']}", f"Status: `{summary['status']}`", f"Audit only: `{summary['audit_only']}`", f"live_evaluator_connection_allowed: `{summary['live_evaluator_connection_allowed']}`", "", "## External actions", ""]
    for k, v in EXTERNAL_ACTIONS_OFF.items():
        lines.append(f"- {k}: `{v}`")
    lines += ["- no_signal_discord_policy: `DO_NOT_NOTIFY_ON_NO_SIGNAL`", "", "## CoreB readiness", "", f"- source_rule_candidate_count: `{summary['source_rule_candidate_count']}`", f"- freeze_ready_rule_candidate_count: `{summary['freeze_ready_rule_candidate_count']}`", f"- condition_row_count: `{summary['condition_row_count']}`", f"- same_count_ready_row_groups: `{summary['same_count_ready_row_groups']}`", f"- blocking_gap_count: `{summary['blocking_gap_count']}`", "", "## Important", "", "This is not a live mapping. If readiness is good, the next step is to freeze an explicit CoreB live-evaluator source definition JSON, then rerun step 12. Do not connect step 13 while blocking UNMAPPED_CONDITION remains."]
    return "\n".join(lines)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    out = Path(args.audit_output_dir).expanduser().resolve() if args.audit_output_dir else default_audit_output_dir()
    out.mkdir(parents=True, exist_ok=True)
    checks: List[AuditCheck] = []
    policy = load_json_or_none("policy", resolve_repo_path(args.policy), checks) or {}
    policy_ok = validate_policy_safety(policy, checks) if policy else False
    coreb_frozen = load_json_or_none("coreb_frozen", resolve_repo_path(args.coreb_frozen), checks)
    coreb_mapping = load_json_or_none("coreb_mapping", resolve_repo_path(args.coreb_mapping), checks)
    source_recs = source_file_records(coreb_frozen, checks, skip_sha_verify=bool(args.skip_source_file_sha_verify))
    raw_df = pd.DataFrame()
    top_df = pd.DataFrame()
    for rec in source_recs:
        if rec.get("disk_status") != "ACCESSIBLE" or not rec.get("resolved_path"):
            continue
        df = read_csv_or_empty(Path(str(rec["resolved_path"])))
        if rec.get("source_kind") == "raw_signal_ledger":
            raw_df = df
        elif rec.get("source_kind") == "top_ledger":
            top_df = df
    universe, condition_rows, gaps = build_rule_universe(raw_df)
    same_count_audit, same_gaps = build_same_count_audit(top_df)
    gaps.extend(same_gaps)
    variant_audit = build_variant_audit(universe)
    if raw_df.empty:
        gaps.append({"component": COREB_COMPONENT, "gap_type": "RAW_SIGNAL_LEDGER_MISSING", "blocking": True})
    if not universe.empty and not bool(universe["freeze_ready_candidate"].all()):
        gaps.append({"component": COREB_COMPONENT, "gap_type": "NOT_ALL_RULE_CANDIDATES_FREEZE_READY", "reason": "Some source rule candidates fail direction/variant/RR/TP-SL/parse/identifier checks.", "blocking": True})
    freeze_ready_count = int(universe["freeze_ready_candidate"].sum()) if not universe.empty and "freeze_ready_candidate" in universe else 0
    status = "COREB_SOURCE_RULE_UNIVERSE_FREEZE_READY_AUDIT_ONLY" if policy_ok and coreb_frozen and not raw_df.empty and freeze_ready_count > 0 else "COREB_SOURCE_RULE_UNIVERSE_FREEZE_NOT_READY"
    summary = {"created_utc": datetime.now(timezone.utc).isoformat(), "status": status, "audit_only": True, "policy_safety_ok": bool(policy_ok), "external_actions": dict(EXTERNAL_ACTIONS_OFF), "no_signal_discord_policy": "DO_NOT_NOTIFY_ON_NO_SIGNAL", "output_dir": str(out), "source_rule_candidate_count": int(len(universe)), "freeze_ready_rule_candidate_count": freeze_ready_count, "condition_row_count": int(len(condition_rows)), "same_count_ready_row_groups": int(same_count_audit["same_count_freeze_ready_candidate"].sum()) if not same_count_audit.empty and "same_count_freeze_ready_candidate" in same_count_audit else 0, "blocking_gap_count": int(len(gaps)), "source_mapping_status": coreb_mapping.get("status") if coreb_mapping else None, "source_unmapped_condition_count": int(len(coreb_mapping.get("unmapped_conditions", []) or [])) if coreb_mapping else None, "live_evaluator_connection_allowed": False, "final_signal_allowed": False, "important_note": "Audit-only readiness. Do not connect step 13. Freeze explicit CoreB live-evaluator source definitions first, then rerun step 12."}
    universe.to_csv(out / "gold_v2_coreb_source_rule_universe_candidates.csv", index=False, encoding="utf-8-sig")
    condition_rows.to_csv(out / "gold_v2_coreb_source_rule_condition_rows.csv", index=False, encoding="utf-8-sig")
    variant_audit.to_csv(out / "gold_v2_coreb_variant_policy_audit.csv", index=False, encoding="utf-8-sig")
    same_count_audit.to_csv(out / "gold_v2_coreb_same_count_derivation_audit.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(gaps).to_csv(out / "gold_v2_coreb_freeze_readiness_gaps.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(source_recs).to_csv(out / "gold_v2_coreb_source_file_audit.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame([asdict(c) for c in checks]).to_csv(out / "gold_v2_coreb_source_rule_universe_audit_checks.csv", index=False, encoding="utf-8-sig")
    write_json(out / "gold_v2_coreb_source_rule_universe_freeze_readiness_summary.json", summary)
    (out / "GOLD_V2_COREB_SOURCE_RULE_UNIVERSE_FREEZE_READINESS_AUDIT_ONLY_REPORT.md").write_text(build_report(summary), encoding="utf-8")
    print(f"[DONE] status={status} audit_dir={out}")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print("No Discord notification, MT5 order, AI API call, or live hook was performed.")
    print("This is not a live mapping. Step 13 remains blocked until step 12 has no blocking UNMAPPED_CONDITION.")
    if not policy_ok or coreb_frozen is None or raw_df.empty:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
