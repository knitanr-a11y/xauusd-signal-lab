#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GOLD V3 13 ranking decision template audit-only runtime script."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import sys
import traceback
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Tuple

STAGE12_READY_STATUS = "GOLD_V3_12_DEPLOYABILITY_REVIEW_PACKET_READY_AUDIT_ONLY"
READY_STATUS = "GOLD_V3_13_RANKING_DECISION_TEMPLATE_READY_AUDIT_ONLY"
BLOCKED_STATUS = "GOLD_V3_13_RANKING_DECISION_TEMPLATE_BLOCKED_AUDIT_ONLY"
EXCEPTION_STATUS = "GOLD_V3_13_RANKING_DECISION_TEMPLATE_EXCEPTION_AUDIT_ONLY"
EXPECTED_PACKET_ROWS = 8
ALLOWED_DECISIONS = "APPROVE_FOR_NEXT_AUDIT_ONLY_REPLAY | REJECT | REQUEST_MORE_AUDIT"
INPUT_REL = Path("Files") / "FX_OUTPUTS" / "gold_v3" / "12_deployability_review_packet_audit_only"
OUTPUT_REL = Path("Files") / "FX_OUTPUTS" / "gold_v3" / "13_ranking_decision_template_audit_only"
FALLBACK_ESTIMATED_TRADE_DAYS = 151.0
FALLBACK_ESTIMATED_TRADE_DAYS_SOURCE = "fallback_from_gold_v3_12_summary_input_preview_rows_proxy; not_exact_calendar_days; recompute_exactly_in_replay"

FALSE_FLAGS = {
    "auto_approval": False,
    "final_candidate_approval": False,
    "threshold_finalization": False,
    "replay_executed": False,
    "model_training": False,
    "signals_generated": False,
    "zip_output_created": False,
    "ai_api_called": False,
    "discord_enabled": False,
    "mt5_enabled": False,
    "live_hook_enabled": False,
    "live_evaluator_enabled": False,
    "final_signal_enabled": False,
}

TEMPLATE_FIELDS = [
    "rank", "source_packet_row_number", "candidate_group_id", "profile_id", "direction", "feature_column",
    "rule_expression_preview", "readiness_label", "risk_flags", "folds", "positive_test_folds",
    "positive_test_fold_rate", "test_avg_result_mean", "test_avg_result_min", "test_avg_result_max",
    "test_lift_mean", "test_sum_result_total", "test_rows_total", "estimated_trade_days",
    "estimated_trade_days_source", "estimated_trades_per_day", "frequency_bucket",
    "pf_winrate_priority_score", "narrowing_potential_score", "recommended_review_bucket",
    "same_condition_overlap", "same_condition_overlap_note", "ranking_is_proxy_only",
    "human_decision", "allowed_decisions", "human_note", "reviewer", "reviewed_at_utc",
]
GROUP_FIELDS = [
    "candidate_group_id", "group_rows", "profiles", "direction_values", "feature_columns", "condition_preview",
    "best_profile_id_by_proxy", "best_rank_by_proxy", "best_pf_winrate_priority_score",
    "max_narrowing_potential_score", "total_test_rows_proxy_sum", "max_estimated_trades_per_day",
    "risk_flags_union", "same_condition_overlap_note", "human_decision", "allowed_decisions", "human_note",
]
BLOCKER_FIELDS = ["blocker_id", "blocker_name", "status", "detail"]
DECISION_FIELDS = ["decision_key", "value", "detail"]
INVENTORY_FIELDS = ["input_label", "path", "exists", "size_bytes", "sha256"]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def repo_root_default() -> Path:
    return Path(__file__).resolve().parents[2]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def read_csv(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")


def write_csv(path: Path, rows: Sequence[Dict[str, Any]], fields: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(fields), extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fields})


def as_float(row: Dict[str, Any], key: str, default: float = 0.0) -> float:
    value = row.get(key, "")
    if value in (None, ""):
        return default
    try:
        out = float(str(value).replace(",", ""))
        return default if math.isnan(out) or math.isinf(out) else out
    except Exception:
        return default


def as_int(row: Dict[str, Any], key: str, default: int = 0) -> int:
    return int(round(as_float(row, key, float(default))))


def first_present(row: Dict[str, Any], keys: Iterable[str], default: str = "") -> str:
    for key in keys:
        value = row.get(key)
        if value not in (None, ""):
            return str(value)
    return default


def clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))


def normalize(value: float, values: Iterable[float]) -> float:
    vals = [v for v in values if not math.isnan(v) and not math.isinf(v)]
    if not vals:
        return 0.0
    lo, hi = min(vals), max(vals)
    if hi == lo:
        return 1.0 if value > 0 else 0.0
    return clamp((value - lo) / (hi - lo))


def infer_expr(row: Dict[str, Any]) -> str:
    return first_present(row, ["rule_expression_preview", "rule_expression", "condition", "expression"], "")


def infer_feature(row: Dict[str, Any]) -> str:
    explicit = first_present(row, ["feature_column", "feature", "rule_feature", "column", "metric"], "")
    if explicit:
        return explicit
    expr = infer_expr(row)
    for name in ["h1_atr56", "m15_atr28", "h4_ret4", "h1_ret16"]:
        if name in expr:
            return name
    return "UNKNOWN_FEATURE"


def infer_profile(row: Dict[str, Any]) -> str:
    explicit = first_present(row, ["profile_id", "strategy_id", "candidate_id", "tp_sl_profile"], "")
    if explicit:
        return explicit
    joined = " ".join(str(v) for v in row.values())
    match = re.search(r"USDPRICE_TP\d+_SL\d+_H\d+", joined) or re.search(r"TP\d+_SL\d+_H\d+", joined)
    return match.group(0) if match else "UNKNOWN_PROFILE"


def infer_direction(row: Dict[str, Any]) -> str:
    return first_present(row, ["direction", "side"], "UNKNOWN_DIRECTION")


def signature(row: Dict[str, Any]) -> str:
    return f"{infer_direction(row)}||{infer_feature(row)}||{infer_expr(row)}"


def group_id(row: Dict[str, Any]) -> str:
    feature = infer_feature(row)
    expr = infer_expr(row)
    if feature == "h1_atr56" or "h1_atr56" in expr:
        return "GROUP_H1_ATR56_HIGH_VOL"
    if feature == "m15_atr28" or "m15_atr28" in expr:
        return "GROUP_M15_ATR28_MID_VOL_RANGE"
    if feature == "h4_ret4" or "h4_ret4" in expr:
        return "GROUP_H4_RET4_MOMENTUM"
    if feature == "h1_ret16" or "h1_ret16" in expr:
        return "GROUP_H1_RET16_MOMENTUM_NEG_FOLD"
    safe = re.sub(r"[^A-Za-z0-9_]+", "_", feature).strip("_").upper() or "UNKNOWN"
    return f"GROUP_{safe}"


def has_risk(risk: str, token: str) -> bool:
    return token.lower() in str(risk).lower()


def frequency_bucket(tpd: float) -> str:
    if tpd >= 2.0:
        return "TARGET_2PLUS_PER_DAY_PROXY"
    if tpd >= 1.0:
        return "MEDIUM_1PLUS_PER_DAY_PROXY"
    if tpd > 0.0:
        return "LOW_UNDER_1_PER_DAY_PROXY"
    return "UNKNOWN_FREQUENCY_PROXY"


def recommended_bucket(row: Dict[str, Any]) -> str:
    risk = str(row.get("risk_flags", ""))
    priority = float(row.get("pf_winrate_priority_score", 0.0))
    narrowing = float(row.get("narrowing_potential_score", 0.0))
    tpd = float(row.get("estimated_trades_per_day", 0.0))
    fold_rate = float(row.get("positive_test_fold_rate", 0.0))
    readiness = str(row.get("readiness_label", ""))
    if "RAW_PRICE_LEVEL" in readiness or has_risk(risk, "raw_price"):
        return "DEFER_RAW_PRICE_LEVEL_RISK"
    if "BUCKET_UNSTABLE" in readiness:
        return "DEFER_BUCKET_UNSTABLE"
    if priority >= 70.0 and tpd >= 2.0 and not has_risk(risk, "negative"):
        return "PRIORITY_A_HIGH_QUALITY_AND_FREQUENCY"
    if priority >= 55.0 and fold_rate >= 0.9:
        return "PRIORITY_B_HIGH_QUALITY_LOW_FREQUENCY_OR_RISK"
    if narrowing >= 45.0:
        return "PRIORITY_C_NARROWING_POTENTIAL"
    return "DEFER_LOW_PRIORITY"


def md(value: Any) -> str:
    return str(value).replace("\n", " ").replace("\r", " ").replace("|", "/")


def inventory_rows(inputs: Sequence[Tuple[str, Path]]) -> List[Dict[str, Any]]:
    rows = []
    for label, path in inputs:
        rows.append({
            "input_label": label,
            "path": str(path),
            "exists": path.exists(),
            "size_bytes": path.stat().st_size if path.exists() else "",
            "sha256": sha256_file(path) if path.exists() else "",
        })
    return rows


def blockers(status_ready: bool, packet_ok: bool, deferred_ok: bool, template_ok: bool, family_ok: bool, h1_ok: bool) -> List[Dict[str, Any]]:
    def c(ok: bool) -> str:
        return "CLOSED" if ok else "OPEN_BLOCKER"
    return [
        {"blocker_id": "G3-13-001", "blocker_name": "12 inputs", "status": c(status_ready and packet_ok and deferred_ok), "detail": "stage12 summary READY, packet row count 8, deferred diagnostics exists"},
        {"blocker_id": "G3-13-002", "blocker_name": "ranking template rows", "status": c(template_ok), "detail": "ranking template rows must equal 8"},
        {"blocker_id": "G3-13-003", "blocker_name": "family grouping", "status": c(family_ok and h1_ok), "detail": "candidate family grouping written and h1_atr56 overlap disclosed when present"},
        {"blocker_id": "G3-13-004", "blocker_name": "human decision", "status": "OPEN_HUMAN_ACTION_REQUIRED", "detail": "decision fields remain pending"},
        {"blocker_id": "G3-13-005", "blocker_name": "replay execution", "status": "CLOSED_BLOCKED_BY_POLICY", "detail": "replay remains prohibited in stage 13"},
        {"blocker_id": "G3-13-006", "blocker_name": "final approval", "status": "CLOSED_BLOCKED_BY_POLICY", "detail": "final candidate approval remains prohibited"},
        {"blocker_id": "G3-13-007", "blocker_name": "threshold finalization", "status": "CLOSED_BLOCKED_BY_POLICY", "detail": "threshold finalization remains prohibited"},
        {"blocker_id": "G3-13-008", "blocker_name": "model training", "status": "CLOSED_BLOCKED_BY_POLICY", "detail": "model training remains prohibited"},
        {"blocker_id": "G3-13-009", "blocker_name": "signal/live", "status": "CLOSED_BLOCKED_BY_POLICY", "detail": "signal generation/live hook/live evaluator/final signal remain OFF"},
        {"blocker_id": "G3-13-010", "blocker_name": "zip output", "status": "CLOSED_DISABLED", "detail": "ZIP output disabled"},
        {"blocker_id": "G3-13-011", "blocker_name": "external actions", "status": "CLOSED", "detail": "Discord/MT5/AI API/live integrations remain OFF"},
    ]


def decision_rows() -> List[Dict[str, Any]]:
    return [
        {"decision_key": "auto_approval", "value": False, "detail": "stage 13 never auto-approves"},
        {"decision_key": "final_candidate_approval", "value": False, "detail": "blocked by policy"},
        {"decision_key": "threshold_finalization", "value": False, "detail": "blocked by policy"},
        {"decision_key": "replay_executed", "value": False, "detail": "blocked by policy"},
        {"decision_key": "model_training", "value": False, "detail": "blocked by policy"},
        {"decision_key": "signals_generated", "value": False, "detail": "blocked by policy"},
        {"decision_key": "zip_output_created", "value": False, "detail": "disabled"},
        {"decision_key": "external_actions", "value": False, "detail": "Discord/MT5/AI/live all OFF"},
        {"decision_key": "human_decision_required", "value": True, "detail": "template is ready only for later human review"},
    ]


def build_rows(packet: Sequence[Dict[str, str]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], bool]:
    sig_count = defaultdict(int)
    for row in packet:
        sig_count[signature(row)] += 1

    prelim = []
    for i, src in enumerate(packet, 1):
        avg = as_float(src, "test_avg_result_mean")
        test_rows = as_float(src, "test_rows_total")
        est_tpd = test_rows / FALLBACK_ESTIMATED_TRADE_DAYS if FALLBACK_ESTIMATED_TRADE_DAYS else 0.0
        sig = signature(src)
        overlap = sig_count[sig]
        prelim.append({
            "source_packet_row_number": i,
            "candidate_group_id": group_id(src),
            "profile_id": infer_profile(src),
            "direction": infer_direction(src),
            "feature_column": infer_feature(src),
            "rule_expression_preview": infer_expr(src),
            "readiness_label": first_present(src, ["readiness_label"], ""),
            "risk_flags": first_present(src, ["risk_flags"], "none") or "none",
            "folds": as_int(src, "folds"),
            "positive_test_folds": as_int(src, "positive_test_folds"),
            "positive_test_fold_rate": as_float(src, "positive_test_fold_rate"),
            "test_avg_result_mean": avg,
            "test_avg_result_min": as_float(src, "test_avg_result_min"),
            "test_avg_result_max": as_float(src, "test_avg_result_max"),
            "test_lift_mean": as_float(src, "test_lift_mean"),
            "test_sum_result_total": as_float(src, "test_sum_result_total", avg * test_rows),
            "test_rows_total": test_rows,
            "estimated_trade_days": FALLBACK_ESTIMATED_TRADE_DAYS,
            "estimated_trade_days_source": FALLBACK_ESTIMATED_TRADE_DAYS_SOURCE,
            "estimated_trades_per_day": est_tpd,
            "frequency_bucket": frequency_bucket(est_tpd),
            "same_condition_overlap": overlap,
            "same_condition_overlap_note": "unique_condition" if overlap <= 1 else f"same entry condition appears in {overlap} rows; compare exit profiles, do not count as independent entry ideas",
        })

    avg_vals = [float(r["test_avg_result_mean"]) for r in prelim]
    lift_vals = [float(r["test_lift_mean"]) for r in prelim]
    sum_vals = [float(r["test_sum_result_total"]) for r in prelim]
    row_vals = [float(r["test_rows_total"]) for r in prelim]

    output = []
    for row in prelim:
        fold_score = clamp(float(row["positive_test_fold_rate"]))
        avg_score = normalize(float(row["test_avg_result_mean"]), avg_vals)
        lift_score = normalize(float(row["test_lift_mean"]), lift_vals)
        sum_score = normalize(float(row["test_sum_result_total"]), sum_vals)
        freq_score = clamp(float(row["estimated_trades_per_day"]) / 2.0)
        risk = str(row["risk_flags"])
        penalty = 0.0
        if has_risk(risk, "negative"):
            penalty += 12.0
        if has_risk(risk, "absolute") or has_risk(risk, "raw_price"):
            penalty += 8.0
        if int(row["same_condition_overlap"]) > 1:
            penalty += 3.0
        priority = max(0.0, 100.0 * (0.28 * fold_score + 0.25 * avg_score + 0.22 * lift_score + 0.15 * sum_score + 0.10 * freq_score) - penalty)
        narrowing = 100.0 * (0.25 * normalize(float(row["test_rows_total"]), row_vals) + 0.25 * lift_score + 0.20 * avg_score + 0.15 * (1.0 - fold_score) + 0.15 * (1.0 if int(row["same_condition_overlap"]) > 1 else 0.0))
        if has_risk(risk, "negative") or has_risk(risk, "absolute"):
            narrowing += 8.0
        row["pf_winrate_priority_score"] = round(priority, 6)
        row["narrowing_potential_score"] = round(max(0.0, min(100.0, narrowing)), 6)
        row["estimated_trades_per_day"] = round(float(row["estimated_trades_per_day"]), 6)
        row["test_sum_result_total"] = round(float(row["test_sum_result_total"]), 6)
        row["ranking_is_proxy_only"] = True
        row["human_decision"] = "PENDING_HUMAN_REVIEW"
        row["allowed_decisions"] = ALLOWED_DECISIONS
        row["human_note"] = ""
        row["reviewer"] = ""
        row["reviewed_at_utc"] = ""
        row["recommended_review_bucket"] = recommended_bucket(row)
        output.append(row)

    output.sort(key=lambda r: (float(r["pf_winrate_priority_score"]), float(r["narrowing_potential_score"])), reverse=True)
    for rank, row in enumerate(output, 1):
        row["rank"] = rank

    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in output:
        grouped[str(row["candidate_group_id"])].append(row)

    groups = []
    for gid, members in grouped.items():
        best = max(members, key=lambda r: float(r["pf_winrate_priority_score"]))
        groups.append({
            "candidate_group_id": gid,
            "group_rows": len(members),
            "profiles": ";".join(sorted({str(r["profile_id"]) for r in members})),
            "direction_values": ";".join(sorted({str(r["direction"]) for r in members})),
            "feature_columns": ";".join(sorted({str(r["feature_column"]) for r in members})),
            "condition_preview": "; ".join(sorted({str(r["rule_expression_preview"]) for r in members if str(r["rule_expression_preview"]).strip()})),
            "best_profile_id_by_proxy": best["profile_id"],
            "best_rank_by_proxy": best["rank"],
            "best_pf_winrate_priority_score": best["pf_winrate_priority_score"],
            "max_narrowing_potential_score": max(float(r["narrowing_potential_score"]) for r in members),
            "total_test_rows_proxy_sum": round(sum(float(r["test_rows_total"]) for r in members), 6),
            "max_estimated_trades_per_day": max(float(r["estimated_trades_per_day"]) for r in members),
            "risk_flags_union": ";".join(sorted({str(r["risk_flags"]) for r in members if str(r["risk_flags"]).strip()})) or "none",
            "same_condition_overlap_note": best["same_condition_overlap_note"] if len(members) > 1 else "unique_condition",
            "human_decision": "PENDING_HUMAN_REVIEW",
            "allowed_decisions": ALLOWED_DECISIONS,
            "human_note": "",
        })
    groups.sort(key=lambda r: (float(r["best_pf_winrate_priority_score"]), float(r["max_narrowing_potential_score"])), reverse=True)
    has_h1 = any(r["candidate_group_id"] == "GROUP_H1_ATR56_HIGH_VOL" for r in output)
    h1_ok = not has_h1 or any(g["candidate_group_id"] == "GROUP_H1_ATR56_HIGH_VOL" and int(g["group_rows"]) >= 2 and "same entry condition" in str(g["same_condition_overlap_note"]) for g in groups)
    return output, groups, h1_ok


def report(summary: Dict[str, Any], rows: Sequence[Dict[str, Any]], groups: Sequence[Dict[str, Any]], blocker_rows: Sequence[Dict[str, Any]]) -> str:
    lines = [
        "# GOLD V3 13 ranking decision template audit-only report", "",
        f"Created UTC: `{summary.get('created_at_utc', '')}`",
        f"Status: `{summary.get('status', '')}`", "",
        "## Scope", "",
        "This stage creates a ranking-oriented audit-only decision template from the GOLD V3 12 deployability packet.",
        "No approval, replay, training, signal generation, ZIP output, AI API, Discord, MT5, live hook, live evaluator, or final signal action was performed.", "",
        "## Counts", "",
    ]
    for key in ["packet_rows", "expected_packet_rows", "ranking_template_rows", "candidate_family_group_rows", "deferred_rows"]:
        lines.append(f"- {key}: `{summary.get(key, '')}`")
    lines += ["", "## Top proxy-ranked candidates", "", "| rank | group | profile | feature | est trades/day | priority | narrowing | bucket | risk |", "|---:|---|---|---|---:|---:|---:|---|---|"]
    for row in rows[:8]:
        lines.append(f"| {md(row.get('rank',''))} | {md(row.get('candidate_group_id',''))} | {md(row.get('profile_id',''))} | {md(row.get('feature_column',''))} | {md(row.get('estimated_trades_per_day',''))} | {md(row.get('pf_winrate_priority_score',''))} | {md(row.get('narrowing_potential_score',''))} | {md(row.get('recommended_review_bucket',''))} | {md(row.get('risk_flags',''))} |")
    lines += ["", "## Candidate family groups", "", "| group | rows | profiles | condition | overlap note |", "|---|---:|---|---|---|"]
    for group in groups:
        lines.append(f"| {md(group.get('candidate_group_id',''))} | {md(group.get('group_rows',''))} | {md(group.get('profiles',''))} | {md(group.get('condition_preview',''))} | {md(group.get('same_condition_overlap_note',''))} |")
    lines += ["", "## Blockers", "", "| blocker_id | blocker_name | status | detail |", "|---|---|---|---|"]
    for block in blocker_rows:
        lines.append(f"| {md(block.get('blocker_id',''))} | {md(block.get('blocker_name',''))} | {md(block.get('status',''))} | {md(block.get('detail',''))} |")
    lines += ["", "## Decision policy", "", "All rows remain `PENDING_HUMAN_REVIEW`. `APPROVE_FOR_NEXT_AUDIT_ONLY_REPLAY` is not final approval and not live approval. `REQUEST_MORE_AUDIT` is not approval.", ""]
    return "\n".join(lines)


def write_blocked(output_dir: Path, inventory: List[Dict[str, Any]], reason: str, stage12_status: str = "", packet_count: int = 0, deferred_count: int = 0) -> None:
    block_rows = blockers(stage12_status == STAGE12_READY_STATUS, packet_count == EXPECTED_PACKET_ROWS, deferred_count >= 0, False, False, False)
    summary = {
        "created_at_utc": utc_now(),
        "status": BLOCKED_STATUS,
        "blocked_reason": reason,
        "stage12_status": stage12_status,
        "packet_rows": packet_count,
        "expected_packet_rows": EXPECTED_PACKET_ROWS,
        "deferred_rows": deferred_count,
        "ranking_template_rows": 0,
        "candidate_family_group_rows": 0,
        "human_decision_required": True,
        "ranking_is_proxy_only": True,
        "old_gold_disc8_quarantined": True,
        "gold_v2_live_sot_used": False,
        **FALSE_FLAGS,
    }
    write_csv(output_dir / "gold_v3_13_input_inventory.csv", inventory, INVENTORY_FIELDS)
    write_csv(output_dir / "gold_v3_13_ranking_decision_template.csv", [], TEMPLATE_FIELDS)
    write_csv(output_dir / "gold_v3_13_candidate_family_group_summary.csv", [], GROUP_FIELDS)
    write_csv(output_dir / "gold_v3_13_decision_matrix.csv", decision_rows(), DECISION_FIELDS)
    write_csv(output_dir / "gold_v3_13_blocker_matrix.csv", block_rows, BLOCKER_FIELDS)
    write_json(output_dir / "gold_v3_13_summary.json", summary)
    (output_dir / "GOLD_V3_13_RANKING_DECISION_TEMPLATE_AUDIT_ONLY_REPORT.md").write_text(report(summary, [], [], block_rows), encoding="utf-8")


def run(repo_root: Path) -> int:
    repo_root = repo_root.resolve()
    input_dir = repo_root / INPUT_REL
    output_dir = repo_root / OUTPUT_REL
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = input_dir / "gold_v3_12_summary.json"
    packet_path = input_dir / "gold_v3_12_deployability_review_packet.csv"
    deferred_path = input_dir / "gold_v3_12_deferred_candidate_diagnostics.csv"
    inputs = [("gold_v3_12_summary", summary_path), ("gold_v3_12_deployability_review_packet", packet_path), ("gold_v3_12_deferred_candidate_diagnostics", deferred_path)]
    inventory = inventory_rows(inputs)
    missing = [str(r["input_label"]) for r in inventory if not r["exists"]]
    if missing:
        reason = "missing required stage12 inputs: " + ", ".join(missing)
        write_blocked(output_dir, inventory, reason)
        print("[GOLD_V3_13] BLOCKED: " + reason)
        return 2

    stage12 = read_json(summary_path)
    packet = read_csv(packet_path)
    deferred = read_csv(deferred_path)
    stage12_status = str(stage12.get("status", ""))
    if stage12_status != STAGE12_READY_STATUS:
        reason = f"stage12 status is not READY: {stage12_status}"
        write_blocked(output_dir, inventory, reason, stage12_status, len(packet), len(deferred))
        print("[GOLD_V3_13] BLOCKED: " + reason)
        return 2
    if len(packet) != EXPECTED_PACKET_ROWS:
        reason = f"stage12 packet row count is {len(packet)}, expected {EXPECTED_PACKET_ROWS}"
        write_blocked(output_dir, inventory, reason, stage12_status, len(packet), len(deferred))
        print("[GOLD_V3_13] BLOCKED: " + reason)
        return 2

    rows, groups, h1_ok = build_rows(packet)
    template_ok = len(rows) == EXPECTED_PACKET_ROWS
    family_ok = len(groups) > 0
    block_rows = blockers(True, True, True, template_ok, family_ok, h1_ok)
    success = template_ok and family_ok and h1_ok and all(r.get("human_decision") == "PENDING_HUMAN_REVIEW" for r in rows)
    status = READY_STATUS if success else BLOCKED_STATUS
    summary = {
        "created_at_utc": utc_now(),
        "status": status,
        "stage12_status": stage12_status,
        "packet_rows": len(packet),
        "expected_packet_rows": EXPECTED_PACKET_ROWS,
        "deferred_rows": len(deferred),
        "ranking_template_rows": len(rows),
        "candidate_family_group_rows": len(groups),
        "h1_atr56_overlap_disclosed": h1_ok,
        "human_decision_required": True,
        "ranking_is_proxy_only": True,
        "estimated_trade_days_source": FALLBACK_ESTIMATED_TRADE_DAYS_SOURCE,
        "top_candidate_group_id_by_proxy": rows[0].get("candidate_group_id", "") if rows else "",
        "top_profile_id_by_proxy": rows[0].get("profile_id", "") if rows else "",
        "allowed_decisions": ALLOWED_DECISIONS,
        "old_gold_disc8_quarantined": True,
        "gold_v2_live_sot_used": False,
        **FALSE_FLAGS,
    }
    write_csv(output_dir / "gold_v3_13_input_inventory.csv", inventory, INVENTORY_FIELDS)
    write_csv(output_dir / "gold_v3_13_ranking_decision_template.csv", rows, TEMPLATE_FIELDS)
    write_csv(output_dir / "gold_v3_13_candidate_family_group_summary.csv", groups, GROUP_FIELDS)
    write_csv(output_dir / "gold_v3_13_decision_matrix.csv", decision_rows(), DECISION_FIELDS)
    write_csv(output_dir / "gold_v3_13_blocker_matrix.csv", block_rows, BLOCKER_FIELDS)
    write_json(output_dir / "gold_v3_13_summary.json", summary)
    (output_dir / "GOLD_V3_13_RANKING_DECISION_TEMPLATE_AUDIT_ONLY_REPORT.md").write_text(report(summary, rows, groups, block_rows), encoding="utf-8")
    print(json.dumps({"status": status, "packet_rows": len(packet), "ranking_template_rows": len(rows), "candidate_family_group_rows": len(groups), "top_candidate_group_id_by_proxy": summary["top_candidate_group_id_by_proxy"], "top_profile_id_by_proxy": summary["top_profile_id_by_proxy"], "output_dir": str(output_dir), "external_actions_all_false": all(v is False for v in FALSE_FLAGS.values())}, ensure_ascii=True, indent=2))
    return 0 if success else 2


def write_exception(repo_root: Path, exc: BaseException) -> None:
    output_dir = repo_root.resolve() / OUTPUT_REL
    output_dir.mkdir(parents=True, exist_ok=True)
    text = traceback.format_exc()
    write_json(output_dir / "gold_v3_13_summary.json", {"created_at_utc": utc_now(), "status": EXCEPTION_STATUS, "exception_type": exc.__class__.__name__, "exception_message": str(exc), "human_decision_required": True, "ranking_is_proxy_only": True, "old_gold_disc8_quarantined": True, "gold_v2_live_sot_used": False, **FALSE_FLAGS})
    (output_dir / "gold_v3_13_exception.txt").write_text(text, encoding="utf-8")


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default="")
    args = parser.parse_args(argv)
    repo_root = Path(args.repo_root).resolve() if args.repo_root else repo_root_default()
    try:
        return run(repo_root)
    except Exception as exc:
        write_exception(repo_root, exc)
        print("[GOLD_V3_13] EXCEPTION. See Files/FX_OUTPUTS/gold_v3/13_ranking_decision_template_audit_only/gold_v3_13_exception.txt", file=sys.stderr)
        print(traceback.format_exc(), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
