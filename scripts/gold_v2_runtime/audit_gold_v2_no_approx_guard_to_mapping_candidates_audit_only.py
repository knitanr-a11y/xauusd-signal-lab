#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""GOLD V2 12D: NO_APPROX_GUARD to mapping candidates audit-only.

Candidate rows are not live rules. This script does not connect step 13 and
never sends Discord, places MT5 orders, calls AI API, or calls live hooks.
"""
from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import pandas as pd

GUARD_DOC_DEFAULT = "docs/gold_v2/GOLD_V2_COREA_COREB_MEDIUM_SIGNAL_CONDITIONS_NO_APPROX_GUARD_20260603.md"
POLICY_DEFAULT = "configs/gold_v2/gold_v2_coreA_coreB_medium_policy_20260603.json"
COREA_MAPPING_DEFAULT = "configs/gold_v2/live_evaluator_mapping_coreA_20260603.json"
COREB_MAPPING_DEFAULT = "configs/gold_v2/live_evaluator_mapping_coreB_20260603.json"
MEDIUM_MAPPING_DEFAULT = "configs/gold_v2/live_evaluator_mapping_medium_20260603.json"

COREA_COMPONENT = "HIGH_A_CoreA_fold4_ABC_CAP5"
COREB_COMPONENT = "HIGH_B_CoreB_RR125_BUY_CONFLUENCE"
MEDIUM_COMPONENT = "MEDIUM_REFINED_FEATURE_GATES"
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
    p = argparse.ArgumentParser(description="Audit NO_APPROX_GUARD into non-live mapping candidates")
    p.add_argument("--guard-doc", default=GUARD_DOC_DEFAULT)
    p.add_argument("--policy", default=POLICY_DEFAULT)
    p.add_argument("--corea-mapping", default=COREA_MAPPING_DEFAULT)
    p.add_argument("--coreb-mapping", default=COREB_MAPPING_DEFAULT)
    p.add_argument("--medium-mapping", default=MEDIUM_MAPPING_DEFAULT)
    p.add_argument("--candidate-inventory-dir", default=None)
    p.add_argument("--audit-output-dir", default=None)
    p.add_argument("--max-text-candidates", type=int, default=500)
    p.add_argument("--max-variant-candidates", type=int, default=500)
    return p.parse_args(argv)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def files_dir_from_repo() -> Path:
    root = repo_root()
    return root.parents[1] if len(root.parents) >= 2 else root.parent


def default_candidate_inventory_dir() -> Path:
    return files_dir_from_repo() / "FX_OUTPUTS" / "gold_v2_candidate_rule_definition_inventory_audit_only"


def default_audit_output_dir() -> Path:
    return files_dir_from_repo() / "FX_OUTPUTS" / "gold_v2_no_approx_guard_mapping_candidates_audit_only"


def resolve_repo_path(text: str) -> Path:
    p = Path(text)
    return p if p.is_absolute() else (repo_root() / p).resolve()


def add_check(rows: List[AuditCheck], name: str, ok: bool, message: str, detail: str = "") -> None:
    rows.append(AuditCheck(name, "OK" if ok else "ERROR", message, detail))


def read_json_or_none(label: str, path: Path, checks: List[AuditCheck]) -> Optional[Dict[str, Any]]:
    if not path.exists():
        add_check(checks, f"{label}_exists", False, f"missing: {path}")
        return None
    add_check(checks, f"{label}_exists", True, str(path))
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        add_check(checks, f"{label}_parse", False, "JSON parse failed", repr(exc))
        return None


def read_text_or_none(label: str, path: Path, checks: List[AuditCheck]) -> Optional[str]:
    if not path.exists():
        add_check(checks, f"{label}_exists", False, f"missing: {path}")
        return None
    add_check(checks, f"{label}_exists", True, str(path))
    try:
        return path.read_text(encoding="utf-8")
    except Exception as exc:
        add_check(checks, f"{label}_read", False, "text read failed", repr(exc))
        return None


def write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")


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


def mapping_unmapped_count(mapping: Optional[Dict[str, Any]]) -> int:
    return int(len(mapping.get("unmapped_conditions", []) or [])) if mapping else 0


def parse_scalar(text: str) -> Any:
    if re.fullmatch(r"-?\d+", text):
        return int(text)
    if re.fullmatch(r"-?\d+\.\d+", text):
        return float(text)
    return text


def parse_condition_text(text: str) -> Tuple[List[Dict[str, Any]], List[str]]:
    rows: List[Dict[str, Any]] = []
    missed: List[str] = []
    for idx, part in enumerate([p.strip() for p in re.split(r"\bAND\b", str(text), flags=re.I) if p.strip()]):
        m = COMPARISON_RE.fullmatch(part)
        if not m:
            missed.append(part)
            continue
        rows.append({"field": m.group("field"), "operator": m.group("op"), "value": parse_scalar(m.group("value")), "raw_text": part, "condition_index": idx})
    return rows, missed


def parse_variant_text(text: str) -> Dict[str, Any]:
    m = VARIANT_RE.search(str(text) if text is not None else "")
    if not m:
        return {"parsed": False}
    rr = m.group("rr")
    rr_val = float(rr.replace("p", ".")) if rr else None
    return {"parsed": True, "direction": m.group("direction").upper(), "tp": float(m.group("tp")), "sl": float(m.group("sl")), "rr": rr_val}


def guard_corea_candidates() -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    comp = COREA_COMPONENT
    candidates: List[Dict[str, Any]] = []
    gaps: List[Dict[str, Any]] = []
    for i, raw in enumerate(["10-day lookback", "tail_hard", "top5", "all consensus", "stack allowed only KEEP", "otherwise REJECT"]):
        gaps.append({"component": comp, "candidate_group": "CoreA_A_gate", "condition_id": f"A_text_{i}", "candidate_status": "CANDIDATE_TEXT_ONLY_REQUIRES_SOURCE_DEFINITION", "reason": "A gate is textual in guard doc and still needs executable source predicates.", "raw_text": raw, "blocking": True})
    candidates.append({"component": comp, "candidate_group": "CoreA_B_gate_dependency", "condition_id": "B_requires_CoreA_rejected", "field": "CoreA_A_gate_status", "operator": "==", "value": "REJECTED", "source": "NO_APPROX_GUARD.CoreA.B", "candidate_status": "CANDIDATE_DEPENDENCY_NOT_EXECUTABLE_UNTIL_A_GATE_DEFINED", "blocking_dependency": True, "raw_text": "CoreA rejected"})
    for group, exprs in {"CoreA_B_gate": ["regime == MID_MIXED", "trend_eff96 >= 0.633155", "rr >= 1.5"], "CoreA_C_gate": ["range96 >= 100.43", "range96 <= 117.86"]}.items():
        for i, expr in enumerate(exprs):
            parsed, missed = parse_condition_text(expr)
            for cond in parsed:
                cond.update({"component": comp, "candidate_group": group, "condition_id": f"{group}_{i}_{cond['field']}", "source": f"NO_APPROX_GUARD.{group}", "candidate_status": "CANDIDATE_EXPLICIT_CONDITION_FROM_GUARD_TEXT", "blocking_dependency": group == "CoreA_B_gate"})
                candidates.append(cond)
            for raw in missed:
                gaps.append({"component": comp, "candidate_group": group, "condition_id": f"unparsed_{i}", "candidate_status": "UNPARSED_GUARD_TEXT", "raw_text": raw, "blocking": True})
    return candidates, gaps


def guard_coreb_candidates() -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    comp = COREB_COMPONENT
    candidates = [
        {"component": comp, "candidate_group": "CoreB_fixed_guard_conditions", "condition_id": "CoreB_FIXED_direction", "field": "direction", "operator": "==", "value": "BUY", "source": "NO_APPROX_GUARD.CoreB", "candidate_status": "CANDIDATE_EXPLICIT_CONDITION_FROM_GUARD_TEXT", "blocking_dependency": False},
        {"component": comp, "candidate_group": "CoreB_fixed_guard_conditions", "condition_id": "CoreB_FIXED_same_count_min", "field": "same_count", "operator": ">=", "value": 15, "source": "NO_APPROX_GUARD.CoreB", "candidate_status": "CANDIDATE_EXPLICIT_CONDITION_FROM_GUARD_TEXT", "blocking_dependency": True},
        {"component": comp, "candidate_group": "CoreB_fixed_guard_conditions", "condition_id": "CoreB_FIXED_tp_policy", "field": "tp_width_formula", "operator": "==", "value": "1.25 * SL width", "source": "NO_APPROX_GUARD.CoreB", "candidate_status": "CANDIDATE_EXPLICIT_CONDITION_FROM_GUARD_TEXT", "blocking_dependency": True},
        {"component": comp, "candidate_group": "CoreB_fixed_guard_conditions", "condition_id": "CoreB_FIXED_sizing", "field": "sizing", "operator": "==", "value": "CAP3", "source": "NO_APPROX_GUARD.CoreB", "candidate_status": "CANDIDATE_EXPLICIT_CONDITION_FROM_GUARD_TEXT", "blocking_dependency": False},
    ]
    gaps = [
        {"component": comp, "candidate_group": "CoreB_source_rr1_buy_rules", "condition_id": "RR1_source_BUY_rule_universe", "candidate_status": "CANDIDATE_REQUIRES_SOURCE_RULE_UNIVERSE_FREEZE", "reason": "Original RR1.0 BUY source rule universe must be frozen; candidate_id/origin_id alone is not enough.", "blocking": True},
        {"component": comp, "candidate_group": "CoreB_same_count_derivation", "condition_id": "same_count_source_universe", "candidate_status": "CANDIDATE_REQUIRES_SOURCE_RULE_UNIVERSE_FREEZE", "reason": "same_count>=15 is explicit but live same_count universe must be frozen.", "blocking": True},
    ]
    return candidates, gaps


def guard_medium_candidates() -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    comp = MEDIUM_COMPONENT
    candidates: List[Dict[str, Any]] = []
    gaps: List[Dict[str, Any]] = []
    exprs = [("RANGE96_REFINED", "range96 >= 129.6835"), ("RANGE96_REFINED", "trend_eff96 <= 0.355591"), ("RANGE96_REFINED", "top_direction == SELL"), ("VOL_TRMEAN32_REFINED", "tr_mean_32 >= 10.867578"), ("VOL_TRMEAN32_REFINED", "ret96 <= -2.725"), ("VOL_TRMEAN32_REFINED", "range96 >= 176.453"), ("TIER2_HVT", "trend_eff96 <= 0.4"), ("TIER2_HVT", "ret96 <= -25.0"), ("TIER2_HVT", "tr_mean_32 >= 10.867578")]
    for i, (group, expr) in enumerate(exprs):
        parsed, missed = parse_condition_text(expr)
        for cond in parsed:
            cond.update({"component": comp, "candidate_group": group, "condition_id": f"{group}_{i}_{cond['field']}", "source": "NO_APPROX_GUARD.MEDIUM", "candidate_status": "CANDIDATE_EXPLICIT_CONDITION_FROM_GUARD_TEXT", "blocking_dependency": cond["field"] == "top_direction"})
            candidates.append(cond)
        for raw in missed:
            gaps.append({"component": comp, "candidate_group": group, "condition_id": f"unparsed_{i}", "candidate_status": "UNPARSED_GUARD_TEXT", "raw_text": raw, "blocking": True})
    gaps.extend([
        {"component": comp, "candidate_group": "MEDIUM_arbitration", "condition_id": "high_arbitration_required", "candidate_status": "CANDIDATE_REQUIRES_COREA_COREB_ARBITRATION", "reason": "MEDIUM cannot become final signal before CoreA/CoreB arbitration.", "blocking": True},
        {"component": comp, "candidate_group": "MEDIUM_direction_probe", "condition_id": "probe_direction_unmapped", "candidate_status": "UNMAPPED_DIRECTION_FOR_PROBE_RULES", "reason": "PROBE direction must not be inferred.", "blocking": True},
        {"component": comp, "candidate_group": "MEDIUM_tier2_static", "condition_id": "tier2_static_unmapped", "candidate_status": "UNMAPPED_TIER2_STATIC", "reason": "Tier2 static additional conditions are not strict predicates here.", "blocking": True},
    ])
    return candidates, gaps


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame()


def source_text_candidates(text_df: pd.DataFrame, max_rows: int) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    candidates: List[Dict[str, Any]] = []
    gaps: List[Dict[str, Any]] = []
    if text_df.empty or "component" not in text_df.columns:
        return candidates, gaps
    df = text_df[(text_df["component"].astype(str) == COREB_COMPONENT) & (text_df.get("column", "").astype(str).isin(["base_condition", "added_filter_text"]))].head(max_rows)
    for idx, row in df.iterrows():
        full = str(row.get("sample_text", ""))
        parsed, missed = parse_condition_text(full)
        for j, cond in enumerate(parsed):
            cond.update({"component": COREB_COMPONENT, "candidate_group": f"CoreB_text_{row.get('column')}", "condition_id": f"CoreB_text_{idx}_{j}_{cond['field']}", "source": "12C_candidate_text_samples", "candidate_status": "CANDIDATE_PARSED_FROM_SOURCE_TEXT_SAMPLE", "blocking_dependency": True, "raw_text_full": full})
            candidates.append(cond)
        for j, raw in enumerate(missed):
            gaps.append({"component": COREB_COMPONENT, "candidate_group": f"CoreB_text_{row.get('column')}", "condition_id": f"CoreB_unparsed_text_{idx}_{j}", "candidate_status": "UNPARSED_SOURCE_TEXT_SAMPLE", "raw_text": raw, "raw_text_full": full, "blocking": True})
    return candidates, gaps


def variant_candidates(variant_df: pd.DataFrame, max_rows: int) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    if variant_df.empty:
        return rows
    for idx, rec in variant_df.head(max_rows).iterrows():
        text = str(rec.get("variant_text", ""))
        parsed = parse_variant_text(text)
        if not parsed.get("parsed"):
            continue
        rows.append({"component": str(rec.get("component", "")), "candidate_group": "variant_tp_sl_rr_candidate", "condition_id": f"variant_{idx}", "variant_text": text, "direction": parsed["direction"], "tp": parsed["tp"], "sl": parsed["sl"], "rr": parsed["rr"], "count": rec.get("count"), "source": "12C_candidate_variant_inventory", "candidate_status": "CANDIDATE_PARSED_VARIANT_NOT_LIVE_SELECTOR", "blocking_dependency": True, "raw_text": text})
    return rows


def packet(component: str, mapping: Optional[Dict[str, Any]], candidates: List[Dict[str, Any]], gaps: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {"component": component, "source_mapping_status": mapping.get("status") if mapping else None, "source_unmapped_condition_count": mapping_unmapped_count(mapping), "candidate_count": sum(1 for c in candidates if c.get("component") == component), "blocking_gap_count": sum(1 for g in gaps if g.get("component") == component), "candidate_status": "CANDIDATES_EXIST_BUT_NOT_STRICT_MAPPING", "live_evaluator_connection_allowed": False, "final_signal_allowed": False}


def build_report(summary: Dict[str, Any], packets: List[Dict[str, Any]], gaps: List[Dict[str, Any]]) -> str:
    lines = ["# GOLD V2 NO_APPROX_GUARD to mapping candidates audit-only report", "", f"Created UTC: {summary['created_utc']}", f"Status: `{summary['status']}`", f"Audit only: `{summary['audit_only']}`", f"live_evaluator_connection_allowed: `{summary['live_evaluator_connection_allowed']}`", "", "## External actions", ""]
    for k, v in EXTERNAL_ACTIONS_OFF.items():
        lines.append(f"- {k}: `{v}`")
    lines += ["- no_signal_discord_policy: `DO_NOT_NOTIFY_ON_NO_SIGNAL`", "", "## Component candidate packets", "", "| component | source_mapping_status | source_unmapped_condition_count | candidate_count | blocking_gap_count |", "| --- | --- | ---: | ---: | ---: |"]
    for p in packets:
        lines.append(f"| {p['component']} | `{p['source_mapping_status']}` | {p['source_unmapped_condition_count']} | {p['candidate_count']} | {p['blocking_gap_count']} |")
    lines += ["", "## Important", "", "These are candidates only. Do not connect step 13. A later explicit freezing step must write strict live_evaluator_mapping.conditions and rerun step 12 until no blocking UNMAPPED_CONDITION remains."]
    return "\n".join(lines)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    out_dir = Path(args.audit_output_dir).expanduser().resolve() if args.audit_output_dir else default_audit_output_dir()
    cand_dir = Path(args.candidate_inventory_dir).expanduser().resolve() if args.candidate_inventory_dir else default_candidate_inventory_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    checks: List[AuditCheck] = []

    guard_text = read_text_or_none("guard_doc", resolve_repo_path(args.guard_doc), checks) or ""
    policy = read_json_or_none("policy", resolve_repo_path(args.policy), checks) or {}
    policy_ok = validate_policy_safety(policy, checks) if policy else False
    corea = read_json_or_none("corea_mapping", resolve_repo_path(args.corea_mapping), checks)
    coreb = read_json_or_none("coreb_mapping", resolve_repo_path(args.coreb_mapping), checks)
    medium = read_json_or_none("medium_mapping", resolve_repo_path(args.medium_mapping), checks)

    text_df = read_csv(cand_dir / "gold_v2_candidate_text_samples.csv")
    variant_df = read_csv(cand_dir / "gold_v2_candidate_variant_inventory.csv")
    add_check(checks, "candidate_text_samples_exists", not text_df.empty, str(cand_dir / "gold_v2_candidate_text_samples.csv"))
    add_check(checks, "candidate_variant_inventory_exists", not variant_df.empty, str(cand_dir / "gold_v2_candidate_variant_inventory.csv"))

    candidates: List[Dict[str, Any]] = []
    gaps: List[Dict[str, Any]] = []
    for fn in [guard_corea_candidates, guard_coreb_candidates, guard_medium_candidates]:
        c, g = fn()
        candidates.extend(c)
        gaps.extend(g)
    c, g = source_text_candidates(text_df, int(args.max_text_candidates))
    candidates.extend(c)
    gaps.extend(g)
    candidates.extend(variant_candidates(variant_df, int(args.max_variant_candidates)))

    packets = [packet(COREA_COMPONENT, corea, candidates, gaps), packet(COREB_COMPONENT, coreb, candidates, gaps), packet(MEDIUM_COMPONENT, medium, candidates, gaps)]
    summary = {"created_utc": datetime.now(timezone.utc).isoformat(), "status": "NO_APPROX_GUARD_MAPPING_CANDIDATES_READY_BUT_NOT_STRICT_MAPPING", "audit_only": True, "policy_safety_ok": bool(policy_ok), "guard_doc_path": str(resolve_repo_path(args.guard_doc)), "candidate_inventory_dir": str(cand_dir), "output_dir": str(out_dir), "external_actions": dict(EXTERNAL_ACTIONS_OFF), "no_signal_discord_policy": "DO_NOT_NOTIFY_ON_NO_SIGNAL", "candidate_count": len(candidates), "blocking_gap_count": len(gaps), "component_packets": packets, "live_evaluator_connection_allowed": False, "final_signal_allowed": False, "important_note": "Candidate rows are not strict mapping. Step 13 remains blocked until explicit frozen live_evaluator_mapping.conditions pass step 12 with no blocking UNMAPPED_CONDITION."}

    pd.DataFrame(candidates).to_csv(out_dir / "gold_v2_no_approx_mapping_candidate_conditions.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(gaps).to_csv(out_dir / "gold_v2_no_approx_mapping_candidate_blocking_gaps.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(packets).to_csv(out_dir / "gold_v2_no_approx_component_candidate_packets.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame([asdict(x) for x in checks]).to_csv(out_dir / "gold_v2_no_approx_guard_candidate_audit_checks.csv", index=False, encoding="utf-8-sig")
    for p in packets:
        obj = dict(p)
        obj["candidate_conditions"] = [c for c in candidates if c.get("component") == p["component"]]
        obj["blocking_gaps"] = [g for g in gaps if g.get("component") == p["component"]]
        obj["audit_only"] = True
        obj["external_actions"] = dict(EXTERNAL_ACTIONS_OFF)
        write_json(out_dir / f"candidate_packet_{p['component']}.json", obj)
    write_json(out_dir / "gold_v2_no_approx_guard_mapping_candidates_summary.json", summary)
    (out_dir / "GOLD_V2_NO_APPROX_GUARD_MAPPING_CANDIDATES_AUDIT_ONLY_REPORT.md").write_text(build_report(summary, packets, gaps), encoding="utf-8")

    print(f"[DONE] status={summary['status']} audit_dir={out_dir}")
    print(pd.DataFrame(packets).to_string(index=False))
    print("No Discord notification, MT5 order, AI API call, or live hook was performed.")
    print("Candidate rows are not live rules. Step 13 remains blocked until step 12 has no blocking UNMAPPED_CONDITION.")
    if not policy_ok or not guard_text or corea is None or coreb is None:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
