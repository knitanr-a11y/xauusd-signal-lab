#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GOLD V3 13 ranking decision template audit-only.

Reads GOLD V3 stage 12 deployability review packet outputs and creates a
ranking-oriented human decision template. This script is audit-only:
no approval, no replay, no model training, no signal generation, no ZIP,
no Discord, no MT5, no AI API, no live hook, no live evaluator.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

STAGE12_READY_STATUS = "GOLD_V3_12_DEPLOYABILITY_REVIEW_PACKET_READY_AUDIT_ONLY"
READY_STATUS = "GOLD_V3_13_RANKING_DECISION_TEMPLATE_READY_AUDIT_ONLY"
BLOCKED_STATUS = "GOLD_V3_13_RANKING_DECISION_TEMPLATE_BLOCKED_AUDIT_ONLY"
EXPECTED_PACKET_ROWS = 8
ALLOWED_DECISIONS = "APPROVE_FOR_NEXT_AUDIT_ONLY_REPLAY | REJECT | REQUEST_MORE_AUDIT"

EXTERNAL_FLAGS_FALSE = {
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

FALLBACK_ESTIMATED_TRADE_DAYS = 151.0
FALLBACK_ESTIMATED_TRADE_DAYS_SOURCE = (
    "fallback_from_gold_v3_12_summary_input_preview_rows_proxy; "
    "not_exact_calendar_days; recompute_exactly_in_replay"
)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def repo_root_from_script() -> Path:
    return Path(__file__).resolve().parents[1]


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


def write_csv(path: Path, rows: List[Dict[str, Any]], fieldnames: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k, "") for k in fieldnames})


def write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")


def to_float(row: Dict[str, Any], key: str, default: float = 0.0) -> float:
    val = row.get(key, "")
    if val is None or val == "":
        return default
    try:
        out = float(val)
        if math.isnan(out) or math.isinf(out):
            return default
        return out
    except Exception:
        return default


def to_int(row: Dict[str, Any], key: str, default: int = 0) -> int:
    try:
        return int(round(to_float(row, key, float(default))))
    except Exception:
        return default


def clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, v))


def norm(value: float, values: Iterable[float]) -> float:
    vals = [v for v in values if not math.isnan(v) and not math.isinf(v)]
    if not vals:
        return 0.0
    lo, hi = min(vals), max(vals)
    if hi == lo:
        return 1.0 if value > 0 else 0.0
    return clamp((value - lo) / (hi - lo))


def first_present(row: Dict[str, Any], keys: Iterable[str], default: str = "") -> str:
    for k in keys:
        v = row.get(k)
        if v not in (None, ""):
            return str(v)
    return default


def infer_feature_column(row: Dict[str, Any]) -> str:
    return first_present(row, ["feature_column", "feature", "rule_feature", "column", "metric"], "UNKNOWN_FEATURE")


def infer_profile_id(row: Dict[str, Any]) -> str:
    direct = first_present(row, ["profile_id", "strategy_id", "candidate_id", "tp_sl_profile"], "")
    if direct:
        return direct
    text = " ".join(str(row.get(k, "")) for k in row.keys())
    m = re.search(r"USDPRICE_TP\d+_SL\d+_H\d+", text)
    if m:
        return m.group(0)
    m = re.search(r"TP\d+_SL\d+_H\d+", text)
    if m:
        return m.group(0)
    return "UNKNOWN_PROFILE"


def infer_direction(row: Dict[str, Any]) -> str:
    return first_present(row, ["direction", "side"], "UNKNOWN_DIRECTION")


def infer_rule_expression(row: Dict[str, Any]) -> str:
    return first_present(row, ["rule_expression_preview", "rule_expression", "condition", "expression"], "")


def condition_signature(row: Dict[str, Any]) -> str:
    feature = infer_feature_column(row)
    expr = infer_rule_expression(row)
    direction = infer_direction(row)
    return f"{direction}||{feature}||{expr}"


def group_id_for(row: Dict[str, Any]) -> str:
    feature = infer_feature_column(row)
    expr = infer_rule_expression(row)
    if feature == "h1_atr56" or "h1_atr56 >= 9.95812" in expr:
        return "GROUP_H1_ATR56_HIGH_VOL"
    if feature == "m15_atr28" or "m15_atr28" in expr:
        return "GROUP_M15_ATR28_MID_VOL_RANGE"
    if feature == "h4_ret4" or "h4_ret4" in expr:
        return "GROUP_H4_RET4_MOMENTUM"
    if feature == "h1_ret16" or "h1_ret16" in expr:
        return "GROUP_H1_RET16_MOMENTUM_NEG_FOLD"
    safe_feature = re.sub(r"[^A-Za-z0-9_]+", "_", feature).strip("_").upper() or "UNKNOWN"
    digest = hashlib.sha1(condition_signature(row).encode("utf-8")).hexdigest()[:8].upper()
    return f"GROUP_{safe_feature}_{digest}"


def frequency_bucket(trades_per_day: float) -> str:
    if trades_per_day >= 2.0:
        return "TARGET_2PLUS_PER_DAY_PROXY"
    if trades_per_day >= 1.0:
        return "MEDIUM_1PLUS_PER_DAY_PROXY"
    if trades_per_day > 0.0:
        return "LOW_UNDER_1_PER_DAY_PROXY"
    return "UNKNOWN_FREQUENCY_PROXY"


def risk_has(risk_flags: str, token: str) -> bool:
    return token.lower() in str(risk_flags).lower()


def review_bucket(row: Dict[str, Any]) -> str:
    risk_flags = str(row.get("risk_flags", ""))
    pscore = float(row["pf_winrate_priority_score"])
    nscore = float(row["narrowing_potential_score"])
    tpd = float(row["estimated_trades_per_day"])
    fold_rate = float(row["positive_test_fold_rate"])
    readiness = str(row.get("readiness_label", ""))
    if "RAW_PRICE_LEVEL" in readiness or risk_has(risk_flags, "raw_price"):
        return "DEFER_RAW_PRICE_LEVEL_RISK"
    if "BUCKET_UNSTABLE" in readiness:
        return "DEFER_BUCKET_UNSTABLE"
    if pscore >= 70.0 and tpd >= 2.0 and not risk_has(risk_flags, "negative"):
        return "PRIORITY_A_HIGH_QUALITY_AND_FREQUENCY"
    if pscore >= 55.0 and fold_rate >= 0.9:
        return "PRIORITY_B_HIGH_QUALITY_LOW_FREQUENCY_OR_RISK"
    if nscore >= 45.0:
        return "PRIORITY_C_NARROWING_POTENTIAL"
    return "DEFER_LOW_PRIORITY"


def build_inventory(paths: List[Tuple[str, Path]]) -> List[Dict[str, Any]]:
    rows = []
    for label, path in paths:
        rows.append({
            "input_label": label,
            "path": str(path),
            "exists": path.exists(),
            "size_bytes": path.stat().st_size if path.exists() else "",
            "sha256": sha256_file(path) if path.exists() else "",
        })
    return rows


def make_blockers(
    status_ready: bool,
    packet_rows_ok: bool,
    deferred_exists: bool,
    template_rows_ok: bool,
    family_rows_ok: bool,
    h1_overlap_disclosed: bool,
) -> List[Dict[str, Any]]:
    def closed(flag: bool, fail_status: str = "OPEN_BLOCKER") -> str:
        return "CLOSED" if flag else fail_status

    return [
        {"blocker_id": "G3-13-001", "blocker_name": "12 inputs", "status": closed(status_ready and packet_rows_ok and deferred_exists), "detail": "stage12 summary READY, packet row count 8, deferred diagnostics exists"},
        {"blocker_id": "G3-13-002", "blocker_name": "ranking template rows", "status": closed(template_rows_ok), "detail": "ranking template rows must equal 8"},
        {"blocker_id": "G3-13-003", "blocker_name": "family grouping", "status": closed(family_rows_ok and h1_overlap_disclosed), "detail": "candidate family grouping written and h1_atr56 overlap disclosed when present"},
        {"blocker_id": "G3-13-004", "blocker_name": "human decision", "status": "OPEN_HUMAN_ACTION_REQUIRED", "detail": "decision fields remain pending"},
        {"blocker_id": "G3-13-005", "blocker_name": "replay execution", "status": "CLOSED_BLOCKED_BY_POLICY", "detail": "replay remains prohibited in stage 13"},
        {"blocker_id": "G3-13-006", "blocker_name": "final approval", "status": "CLOSED_BLOCKED_BY_POLICY", "detail": "final candidate approval remains prohibited"},
        {"blocker_id": "G3-13-007", "blocker_name": "threshold finalization", "status": "CLOSED_BLOCKED_BY_POLICY", "detail": "threshold finalization remains prohibited"},
        {"blocker_id": "G3-13-008", "blocker_name": "model training", "status": "CLOSED_BLOCKED_BY_POLICY", "detail": "model training remains prohibited"},
        {"blocker_id": "G3-13-009", "blocker_name": "signal/live", "status": "CLOSED_BLOCKED_BY_POLICY", "detail": "signal generation/live hook/live evaluator/final signal remain OFF"},
        {"blocker_id": "G3-13-010", "blocker_name": "zip output", "status": "CLOSED_DISABLED", "detail": "ZIP output disabled"},
        {"blocker_id": "G3-13-011", "blocker_name": "external actions", "status": "CLOSED", "detail": "Discord/MT5/AI API/live integrations remain OFF"},
    ]


def render_report(summary: Dict[str, Any], top_rows: List[Dict[str, Any]], group_rows: List[Dict[str, Any]], blockers: List[Dict[str, Any]]) -> str:
    lines: List[str] = []
    lines.append("# GOLD V3 13 ranking decision template audit-only report")
    lines.append("")
    lines.append(f"Created UTC: `{summary['created_at_utc']}`")
    lines.append(f"Status: `{summary['status']}`")
    lines.append("")
    lines.append("## Scope")
    lines.append("")
    lines.append("This stage creates a ranking-oriented audit-only decision template from the GOLD V3 12 deployability packet.")
    lines.append("It does not approve candidates, finalize thresholds, replay, train, generate signals, create ZIP output, call AI APIs, notify Discord, place MT5 orders, or enable live hooks/evaluators.")
    lines.append("")
    lines.append("## Counts")
    lines.append("")
    for key in ["packet_rows", "ranking_template_rows", "candidate_family_group_rows", "deferred_rows"]:
        lines.append(f"- {key}: `{summary.get(key)}`")
    lines.append("")
    lines.append("## Top proxy-ranked candidates")
    lines.append("")
    lines.append("| rank | candidate_group_id | profile_id | feature | est trades/day | priority score | narrowing score | bucket | risk |")
    lines.append("|---:|---|---|---|---:|---:|---:|---|---|")
    for r in top_rows[:8]:
        lines.append(
            "| {rank} | {candidate_group_id} | {profile_id} | {feature_column} | {estimated_trades_per_day} | {pf_winrate_priority_score} | {narrowing_potential_score} | {recommended_review_bucket} | {risk_flags} |".format(**r)
        )
    lines.append("")
    lines.append("## Candidate family groups")
    lines.append("")
    lines.append("| candidate_group_id | rows | profiles | condition | overlap note |")
    lines.append("|---|---:|---|---|---|")
    for g in group_rows:
        lines.append("| {candidate_group_id} | {group_rows} | {profiles} | {condition_preview} | {same_condition_overlap_note} |".format(**g))
    lines.append("")
    lines.append("## Blockers")
    lines.append("")
    lines.append("| blocker_id | blocker_name | status | detail |")
    lines.append("|---|---|---|---|")
    for b in blockers:
        lines.append("| {blocker_id} | {blocker_name} | {status} | {detail} |".format(**b))
    lines.append("")
    lines.append("## Decision policy")
    lines.append("")
    lines.append("All rows remain `PENDING_HUMAN_REVIEW`. `APPROVE_FOR_NEXT_AUDIT_ONLY_REPLAY` is not final approval and not live approval. `REQUEST_MORE_AUDIT` is not approval.")
    lines.append("")
    return "\n".join(lines)


def run(repo_root: Path) -> int:
    input_dir = repo_root / "Files" / "FX_OUTPUTS" / "gold_v3" / "12_deployability_review_packet_audit_only"
    output_dir = repo_root / "Files" / "FX_OUTPUTS" / "gold_v3" / "13_ranking_decision_template_audit_only"
    output_dir.mkdir(parents=True, exist_ok=True)

    summary_path = input_dir / "gold_v3_12_summary.json"
    packet_path = input_dir / "gold_v3_12_deployability_review_packet.csv"
    deferred_path = input_dir / "gold_v3_12_deferred_candidate_diagnostics.csv"

    inventory = build_inventory([
        ("gold_v3_12_summary", summary_path),
        ("gold_v3_12_deployability_review_packet", packet_path),
        ("gold_v3_12_deferred_candidate_diagnostics", deferred_path),
    ])
    write_csv(output_dir / "gold_v3_13_input_inventory.csv", inventory, ["input_label", "path", "exists", "size_bytes", "sha256"])

    missing = [r["input_label"] for r in inventory if not r["exists"]]
    if missing:
        base_summary = {
            "created_at_utc": utc_now_iso(),
            "status": BLOCKED_STATUS,
            "blocked_reason": f"missing inputs: {', '.join(missing)}",
            **EXTERNAL_FLAGS_FALSE,
        }
        write_json(output_dir / "gold_v3_13_summary.json", base_summary)
        return 2

    stage12_summary = read_json(summary_path)
    packet_rows = read_csv(packet_path)
    deferred_rows = read_csv(deferred_path)

    stage12_status = str(stage12_summary.get("status", ""))
    status_ready = stage12_status == STAGE12_READY_STATUS
    packet_rows_ok = len(packet_rows) == EXPECTED_PACKET_ROWS
    deferred_exists = deferred_path.exists()

    numeric_keys = ["positive_test_fold_rate", "test_avg_result_mean", "test_lift_mean", "test_rows_total"]
    metric_parse_ok = all(any(str(r.get(k, "")).strip() for r in packet_rows) for k in numeric_keys)

    avg_values = [to_float(r, "test_avg_result_mean") for r in packet_rows]
    lift_values = [to_float(r, "test_lift_mean") for r in packet_rows]
    sum_values = []
    row_values = [to_float(r, "test_rows_total") for r in packet_rows]

    prelim: List[Dict[str, Any]] = []
    sig_counts: Dict[str, int] = defaultdict(int)
    group_counts: Dict[str, int] = defaultdict(int)
    for r in packet_rows:
        sig_counts[condition_signature(r)] += 1
        group_counts[group_id_for(r)] += 1

    for idx, r in enumerate(packet_rows, start=1):
        feature = infer_feature_column(r)
        profile_id = infer_profile_id(r)
        direction = infer_direction(r)
        expr = infer_rule_expression(r)
        risk_flags = first_present(r, ["risk_flags"], "none")
        group_id = group_id_for(r)
        sig = condition_signature(r)
        folds = to_int(r, "folds")
        positive_folds = to_int(r, "positive_test_folds")
        fold_rate = to_float(r, "positive_test_fold_rate")
        avg_result = to_float(r, "test_avg_result_mean")
        min_result = to_float(r, "test_avg_result_min")
        max_result = to_float(r, "test_avg_result_max")
        lift = to_float(r, "test_lift_mean")
        test_rows = to_float(r, "test_rows_total")
        test_sum = to_float(r, "test_sum_result_total", avg_result * test_rows)
        sum_values.append(test_sum)

        estimated_days = FALLBACK_ESTIMATED_TRADE_DAYS
        estimated_tpd = test_rows / estimated_days if estimated_days > 0 else 0.0
        same_overlap = sig_counts[sig]
        overlap_note = "unique_condition"
        if same_overlap > 1:
            overlap_note = f"same entry condition appears in {same_overlap} rows; compare exit profiles, do not count as independent entry ideas"

        prelim.append({
            "source_packet_row_number": idx,
            "candidate_group_id": group_id,
            "profile_id": profile_id,
            "direction": direction,
            "feature_column": feature,
            "rule_expression_preview": expr,
            "readiness_label": first_present(r, ["readiness_label"], ""),
            "risk_flags": risk_flags or "none",
            "folds": folds,
            "positive_test_folds": positive_folds,
            "positive_test_fold_rate": fold_rate,
            "test_avg_result_mean": avg_result,
            "test_avg_result_min": min_result,
            "test_avg_result_max": max_result,
            "test_lift_mean": lift,
            "test_sum_result_total": test_sum,
            "test_rows_total": test_rows,
            "estimated_trade_days": estimated_days,
            "estimated_trade_days_source": FALLBACK_ESTIMATED_TRADE_DAYS_SOURCE,
            "estimated_trades_per_day": estimated_tpd,
            "frequency_bucket": frequency_bucket(estimated_tpd),
            "same_condition_overlap": same_overlap,
            "same_condition_overlap_note": overlap_note,
        })

    sum_values_for_norm = [r["test_sum_result_total"] for r in prelim]
    rows_for_norm = [r["test_rows_total"] for r in prelim]

    output_rows: List[Dict[str, Any]] = []
    for r in prelim:
        fold_score = clamp(float(r["positive_test_fold_rate"]))
        avg_score = norm(float(r["test_avg_result_mean"]), avg_values)
        lift_score = norm(float(r["test_lift_mean"]), lift_values)
        sum_score = norm(float(r["test_sum_result_total"]), sum_values_for_norm)
        freq_score = clamp(float(r["estimated_trades_per_day"]) / 2.0)
        risk_flags = str(r["risk_flags"])
        risk_penalty = 0.0
        if risk_has(risk_flags, "negative"):
            risk_penalty += 12.0
        if risk_has(risk_flags, "absolute") or risk_has(risk_flags, "raw_price"):
            risk_penalty += 8.0
        if int(r["same_condition_overlap"]) > 1:
            risk_penalty += 3.0
        priority = 100.0 * (
            0.28 * fold_score
            + 0.25 * avg_score
            + 0.22 * lift_score
            + 0.15 * sum_score
            + 0.10 * freq_score
        ) - risk_penalty
        priority = max(0.0, priority)

        narrowing = 100.0 * (
            0.25 * norm(float(r["test_rows_total"]), rows_for_norm)
            + 0.25 * lift_score
            + 0.20 * avg_score
            + 0.15 * (1.0 - fold_score)
            + 0.15 * (1.0 if int(r["same_condition_overlap"]) > 1 else 0.0)
        )
        if risk_has(risk_flags, "negative") or risk_has(risk_flags, "absolute"):
            narrowing += 8.0
        narrowing = max(0.0, min(100.0, narrowing))

        out = dict(r)
        out["pf_winrate_priority_score"] = round(priority, 6)
        out["narrowing_potential_score"] = round(narrowing, 6)
        out["estimated_trades_per_day"] = round(float(out["estimated_trades_per_day"]), 6)
        out["test_sum_result_total"] = round(float(out["test_sum_result_total"]), 6)
        out["ranking_is_proxy_only"] = True
        out["human_decision"] = "PENDING_HUMAN_REVIEW"
        out["allowed_decisions"] = ALLOWED_DECISIONS
        out["human_note"] = ""
        out["reviewer"] = ""
        out["reviewed_at_utc"] = ""
        out["recommended_review_bucket"] = review_bucket(out)
        output_rows.append(out)

    output_rows.sort(key=lambda x: (float(x["pf_winrate_priority_score"]), float(x["narrowing_potential_score"])), reverse=True)
    for i, row in enumerate(output_rows, start=1):
        row["rank"] = i

    groups: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in output_rows:
        groups[row["candidate_group_id"]].append(row)

    group_rows: List[Dict[str, Any]] = []
    for gid, rows in groups.items():
        best = max(rows, key=lambda x: float(x["pf_winrate_priority_score"]))
        profiles = ";".join(sorted({str(x["profile_id"]) for x in rows}))
        conditions = "; ".join(sorted({str(x["rule_expression_preview"]) for x in rows if str(x["rule_expression_preview"]).strip()}))
        risk_union = ";".join(sorted({str(x["risk_flags"]) for x in rows if str(x["risk_flags"]).strip()}))
        group_rows.append({
            "candidate_group_id": gid,
            "group_rows": len(rows),
            "profiles": profiles,
            "direction_values": ";".join(sorted({str(x["direction"]) for x in rows})),
            "feature_columns": ";".join(sorted({str(x["feature_column"]) for x in rows})),
            "condition_preview": conditions,
            "best_profile_id_by_proxy": best["profile_id"],
            "best_rank_by_proxy": best["rank"],
            "best_pf_winrate_priority_score": best["pf_winrate_priority_score"],
            "max_narrowing_potential_score": max(float(x["narrowing_potential_score"]) for x in rows),
            "total_test_rows_proxy_sum": round(sum(float(x["test_rows_total"]) for x in rows), 6),
            "max_estimated_trades_per_day": max(float(x["estimated_trades_per_day"]) for x in rows),
            "risk_flags_union": risk_union or "none",
            "same_condition_overlap_note": best["same_condition_overlap_note"] if len(rows) > 1 else "unique_condition",
            "human_decision": "PENDING_HUMAN_REVIEW",
            "allowed_decisions": ALLOWED_DECISIONS,
            "human_note": "",
        })
    group_rows.sort(key=lambda x: (float(x["best_pf_winrate_priority_score"]), float(x["max_narrowing_potential_score"])), reverse=True)

    h1_overlap_disclosed = any(
        g["candidate_group_id"] == "GROUP_H1_ATR56_HIGH_VOL" and int(g["group_rows"]) >= 2 and "same entry condition" in g["same_condition_overlap_note"]
        for g in group_rows
    ) or not any(r["candidate_group_id"] == "GROUP_H1_ATR56_HIGH_VOL" for r in output_rows)

    template_rows_ok = len(output_rows) == EXPECTED_PACKET_ROWS
    family_rows_ok = len(group_rows) > 0
    all_pending = all(r["human_decision"] == "PENDING_HUMAN_REVIEW" for r in output_rows)
    no_forbidden_enabled = all(v is False for v in EXTERNAL_FLAGS_FALSE.values())

    blockers = make_blockers(
        status_ready=status_ready,
        packet_rows_ok=packet_rows_ok,
        deferred_exists=deferred_exists,
        template_rows_ok=template_rows_ok,
        family_rows_ok=family_rows_ok,
        h1_overlap_disclosed=h1_overlap_disclosed,
    )

    success = all([
        status_ready,
        packet_rows_ok,
        deferred_exists,
        metric_parse_ok,
        template_rows_ok,
        family_rows_ok,
        h1_overlap_disclosed,
        all_pending,
        no_forbidden_enabled,
    ])

    status = READY_STATUS if success else BLOCKED_STATUS
    decision_rows = [
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

    template_fields = [
        "rank", "source_packet_row_number", "candidate_group_id", "profile_id", "direction", "feature_column",
        "rule_expression_preview", "readiness_label", "risk_flags", "folds", "positive_test_folds",
        "positive_test_fold_rate", "test_avg_result_mean", "test_avg_result_min", "test_avg_result_max",
        "test_lift_mean", "test_sum_result_total", "test_rows_total", "estimated_trade_days",
        "estimated_trade_days_source", "estimated_trades_per_day", "frequency_bucket",
        "pf_winrate_priority_score", "narrowing_potential_score", "recommended_review_bucket",
        "same_condition_overlap", "same_condition_overlap_note", "ranking_is_proxy_only",
        "human_decision", "allowed_decisions", "human_note", "reviewer", "reviewed_at_utc",
    ]
    group_fields = [
        "candidate_group_id", "group_rows", "profiles", "direction_values", "feature_columns",
        "condition_preview", "best_profile_id_by_proxy", "best_rank_by_proxy",
        "best_pf_winrate_priority_score", "max_narrowing_potential_score",
        "total_test_rows_proxy_sum", "max_estimated_trades_per_day", "risk_flags_union",
        "same_condition_overlap_note", "human_decision", "allowed_decisions", "human_note",
    ]
    blocker_fields = ["blocker_id", "blocker_name", "status", "detail"]
    decision_fields = ["decision_key", "value", "detail"]

    write_csv(output_dir / "gold_v3_13_ranking_decision_template.csv", output_rows, template_fields)
    write_csv(output_dir / "gold_v3_13_candidate_family_group_summary.csv", group_rows, group_fields)
    write_csv(output_dir / "gold_v3_13_blocker_matrix.csv", blockers, blocker_fields)
    write_csv(output_dir / "gold_v3_13_decision_matrix.csv", decision_rows, decision_fields)

    summary = {
        "created_at_utc": utc_now_iso(),
        "status": status,
        "stage12_status": stage12_status,
        "packet_rows": len(packet_rows),
        "expected_packet_rows": EXPECTED_PACKET_ROWS,
        "deferred_rows": len(deferred_rows),
        "ranking_template_rows": len(output_rows),
        "candidate_family_group_rows": len(group_rows),
        "metric_parse_ok": metric_parse_ok,
        "h1_atr56_overlap_disclosed": h1_overlap_disclosed,
        "human_decision_required": True,
        "ranking_is_proxy_only": True,
        "estimated_trade_days_source": FALLBACK_ESTIMATED_TRADE_DAYS_SOURCE,
        "top_candidate_group_id_by_proxy": output_rows[0]["candidate_group_id"] if output_rows else "",
        "top_profile_id_by_proxy": output_rows[0]["profile_id"] if output_rows else "",
        "allowed_decisions": ALLOWED_DECISIONS,
        "old_gold_disc8_quarantined": True,
        "gold_v2_live_sot_used": False,
        **EXTERNAL_FLAGS_FALSE,
        "outputs": {
            "report": str(output_dir / "GOLD_V3_13_RANKING_DECISION_TEMPLATE_AUDIT_ONLY_REPORT.md"),
            "summary": str(output_dir / "gold_v3_13_summary.json"),
            "input_inventory": str(output_dir / "gold_v3_13_input_inventory.csv"),
            "ranking_decision_template": str(output_dir / "gold_v3_13_ranking_decision_template.csv"),
            "candidate_family_group_summary": str(output_dir / "gold_v3_13_candidate_family_group_summary.csv"),
            "decision_matrix": str(output_dir / "gold_v3_13_decision_matrix.csv"),
            "blocker_matrix": str(output_dir / "gold_v3_13_blocker_matrix.csv"),
        },
    }

    write_json(output_dir / "gold_v3_13_summary.json", summary)
    report = render_report(summary, output_rows, group_rows, blockers)
    (output_dir / "GOLD_V3_13_RANKING_DECISION_TEMPLATE_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")

    print(json.dumps({
        "status": status,
        "packet_rows": len(packet_rows),
        "ranking_template_rows": len(output_rows),
        "candidate_family_group_rows": len(group_rows),
        "top_candidate_group_id_by_proxy": summary["top_candidate_group_id_by_proxy"],
        "top_profile_id_by_proxy": summary["top_profile_id_by_proxy"],
        "output_dir": str(output_dir),
        "external_actions_all_false": no_forbidden_enabled,
    }, ensure_ascii=False, indent=2))
    return 0 if success else 2


def main(argv: List[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", default="", help="Repository root. Defaults to parent of scripts directory.")
    args = ap.parse_args(argv)
    repo_root = Path(args.repo_root).resolve() if args.repo_root else repo_root_from_script()
    return run(repo_root)


if __name__ == "__main__":
    sys.exit(main())
