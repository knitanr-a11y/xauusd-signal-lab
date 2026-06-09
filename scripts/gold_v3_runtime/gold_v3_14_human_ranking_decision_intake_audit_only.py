#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GOLD V3 14 human ranking decision intake audit-only runtime script.

This stage reads GOLD V3 stage-13 ranking decision outputs, creates or validates
human decision intake rows, and prepares an audit-only replay-plan preview for
rows explicitly marked APPROVE_FOR_NEXT_AUDIT_ONLY_REPLAY.

It intentionally does not execute replay, approve final candidates, finalize
thresholds, train models, generate signals, create ZIP output, call AI APIs,
notify Discord, place MT5 orders, enable live hooks/evaluators, or create final
signals.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
import traceback
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence


STEP = "GOLD_V3_14_HUMAN_RANKING_DECISION_INTAKE_AUDIT_ONLY"
UPSTREAM_READY_STATUS = "GOLD_V3_13_RANKING_DECISION_TEMPLATE_READY_AUDIT_ONLY"
READY_STATUS = "GOLD_V3_14_HUMAN_RANKING_DECISION_INTAKE_READY_AUDIT_ONLY"
INPUT_REVIEW_STATUS = "GOLD_V3_14_HUMAN_RANKING_DECISION_INTAKE_INPUT_REVIEW_REQUIRED_AUDIT_ONLY"
BLOCKED_STATUS = "GOLD_V3_14_HUMAN_RANKING_DECISION_INTAKE_BLOCKED_AUDIT_ONLY"
EXCEPTION_STATUS = "GOLD_V3_14_HUMAN_RANKING_DECISION_INTAKE_EXCEPTION_AUDIT_ONLY"

EXPECTED_RANKED_ROWS = 8
EXPECTED_FAMILY_ROWS = 4
UPSTREAM_NAME = "13_ranking_decision_template_audit_only"
OUT_NAME = "14_human_ranking_decision_intake_audit_only"

PENDING_DECISION = "PENDING_HUMAN_REVIEW"
APPROVE_FOR_REPLAY = "APPROVE_FOR_NEXT_AUDIT_ONLY_REPLAY"
REJECT = "REJECT"
REQUEST_MORE_AUDIT = "REQUEST_MORE_AUDIT"
ALLOWED_DECISIONS = [APPROVE_FOR_REPLAY, REJECT, REQUEST_MORE_AUDIT]
ALLOWED_DECISIONS_TEXT = " | ".join(ALLOWED_DECISIONS)

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

INPUTS = [
    ("gold_v3_13_summary", "gold_v3_13_summary.json", True),
    ("gold_v3_13_decision_template", "gold_v3_13_decision_template.csv", True),
    ("gold_v3_13_ranked_rule_candidate_rows", "gold_v3_13_ranked_rule_candidate_rows.csv", True),
    ("gold_v3_13_ranked_candidate_family_groups", "gold_v3_13_ranked_candidate_family_groups.csv", True),
    ("gold_v3_13_deferred_narrowing_candidates", "gold_v3_13_deferred_narrowing_candidates.csv", True),
    ("gold_v3_13_blocker_matrix", "gold_v3_13_blocker_matrix.csv", True),
]

INVENTORY_FIELDS = ["input_label", "path", "required", "exists", "size_bytes", "sha256"]
DECISION_FIELDS = ["decision_key", "value", "detail"]
BLOCKER_FIELDS = ["blocker_id", "blocker_name", "status", "detail"]

INTAKE_FIELDS = [
    "rank",
    "source_packet_row_number",
    "candidate_group_id",
    "profile_id",
    "direction",
    "feature_column",
    "rule_expression_preview",
    "readiness_label",
    "risk_flags",
    "recommended_review_bucket",
    "same_condition_overlap",
    "same_condition_overlap_note",
    "ranking_is_proxy_only",
    "estimated_trades_per_day_proxy",
    "estimated_trades_per_day_source",
    "pf_winrate_priority_score_proxy",
    "narrowing_potential_score_proxy",
    "human_decision",
    "allowed_decisions",
    "human_note",
    "reviewer",
    "reviewed_at_utc",
    "decision_validation_status",
    "decision_validation_detail",
    "approval_semantics",
]

REPLAY_PLAN_FIELDS = [
    "plan_row_number",
    "source_rank",
    "source_packet_row_number",
    "candidate_group_id",
    "entry_family_key",
    "entry_family_count_note",
    "profile_id",
    "direction",
    "feature_column",
    "rule_expression_preview",
    "human_decision",
    "human_note",
    "reviewer",
    "reviewed_at_utc",
    "replay_plan_status",
    "replay_execution_allowed_in_stage14",
    "required_next_stage",
    "ranking_is_proxy_only",
    "true_metrics_to_recompute",
    "must_not_claim",
    "blocked_actions",
]

REPORT_NAME = "GOLD_V3_14_HUMAN_RANKING_DECISION_INTAKE_AUDIT_ONLY_REPORT.md"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def repo_root_default() -> Path:
    return Path(__file__).resolve().parents[2]


def files_root(repo_root: Path) -> Path:
    # Match the GOLD V3 runtime convention used by the repaired stage-13 script.
    return repo_root.parents[1] if len(repo_root.parents) >= 2 else repo_root.parent


def v3_root_candidates(repo_root: Path) -> list[Path]:
    primary = files_root(repo_root) / "FX_OUTPUTS" / "gold_v3"
    legacy = repo_root / "Files" / "FX_OUTPUTS" / "gold_v3"
    candidates: list[Path] = []
    for p in [primary, legacy]:
        if p not in candidates:
            candidates.append(p)
    return candidates


def select_v3_root(repo_root: Path) -> tuple[Path, str]:
    candidates = v3_root_candidates(repo_root)
    for p in candidates:
        upstream = p / UPSTREAM_NAME
        if (upstream / "gold_v3_13_summary.json").exists() or (upstream / "gold_v3_13_decision_template.csv").exists():
            return p, "selected_existing_stage13_root"
    return candidates[0], "selected_primary_gold_v3_root_no_stage13_inputs_found"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_json(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")


def write_csv(path: Path, rows: Sequence[dict[str, Any]], fields: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(fields), extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fields})


def md(value: Any) -> str:
    return str(value).replace("\n", " ").replace("\r", " ").replace("|", "/")


def inventory_rows(input_dir: Path, extra_inputs: Sequence[tuple[str, Path, bool]] | None = None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for label, filename, required in INPUTS:
        path = input_dir / filename
        rows.append({
            "input_label": label,
            "path": str(path),
            "required": required,
            "exists": path.exists(),
            "size_bytes": path.stat().st_size if path.exists() else "",
            "sha256": sha256_file(path) if path.exists() else "",
        })
    for label, path, required in extra_inputs or []:
        rows.append({
            "input_label": label,
            "path": str(path),
            "required": required,
            "exists": path.exists(),
            "size_bytes": path.stat().st_size if path.exists() else "",
            "sha256": sha256_file(path) if path.exists() else "",
        })
    return rows


def row_key(row: dict[str, Any]) -> str:
    rank = str(row.get("rank", "")).strip()
    if rank:
        return f"rank:{rank}"
    parts = [
        str(row.get("source_packet_row_number", "")).strip(),
        str(row.get("candidate_group_id", "")).strip(),
        str(row.get("profile_id", "")).strip(),
        str(row.get("feature_column", "")).strip(),
        str(row.get("rule_expression_preview", "")).strip(),
    ]
    return "compound:" + "||".join(parts)


def normalize_decision(value: Any) -> str:
    raw = str(value or "").strip()
    if not raw:
        return PENDING_DECISION
    upper = raw.upper()
    if upper in {PENDING_DECISION, "PENDING", "PENDING_REVIEW"}:
        return PENDING_DECISION
    if upper in ALLOWED_DECISIONS:
        return upper
    return raw


def resolve_optional_decision_input(repo_root: Path, output_dir: Path, raw_path: str) -> tuple[Path | None, str]:
    if raw_path:
        p = Path(raw_path)
        if not p.is_absolute():
            p = repo_root / p
        return p.resolve(), "cli_human_decision_input"
    default_existing = output_dir / "gold_v3_14_human_decision_intake_template.csv"
    if default_existing.exists():
        return default_existing, "existing_stage14_intake_template"
    return None, "no_optional_human_decision_input_found"


def source_value(row: dict[str, Any], keys: Sequence[str], default: str = "") -> str:
    for key in keys:
        value = row.get(key)
        if value not in (None, ""):
            return str(value)
    return default


def build_human_lookup(human_rows: Sequence[dict[str, str]]) -> dict[str, dict[str, str]]:
    lookup: dict[str, dict[str, str]] = {}
    for row in human_rows:
        lookup[row_key(row)] = row
    return lookup


def build_intake_rows(source_rows: Sequence[dict[str, str]], human_rows: Sequence[dict[str, str]]) -> tuple[list[dict[str, Any]], list[str]]:
    human_lookup = build_human_lookup(human_rows)
    invalid: list[str] = []
    output: list[dict[str, Any]] = []

    for src in source_rows:
        hrow = human_lookup.get(row_key(src), {})
        decision = normalize_decision(source_value(hrow, ["human_decision"], source_value(src, ["human_decision"], PENDING_DECISION)))
        validation_status = "VALID"
        validation_detail = "decision accepted for audit-only intake"

        if decision == PENDING_DECISION:
            validation_status = "PENDING_HUMAN_REVIEW"
            validation_detail = "human decision not provided yet"
        elif decision not in ALLOWED_DECISIONS:
            validation_status = "INVALID"
            validation_detail = f"human_decision must be one of: {ALLOWED_DECISIONS_TEXT}"
            invalid.append(f"rank={src.get('rank', '')} decision={decision}")

        ranking_proxy = source_value(src, ["ranking_is_proxy_only"], "true")
        row = {
            "rank": source_value(src, ["rank"]),
            "source_packet_row_number": source_value(src, ["source_packet_row_number"]),
            "candidate_group_id": source_value(src, ["candidate_group_id"]),
            "profile_id": source_value(src, ["profile_id"]),
            "direction": source_value(src, ["direction"]),
            "feature_column": source_value(src, ["feature_column"]),
            "rule_expression_preview": source_value(src, ["rule_expression_preview"]),
            "readiness_label": source_value(src, ["readiness_label"]),
            "risk_flags": source_value(src, ["risk_flags"], "none") or "none",
            "recommended_review_bucket": source_value(src, ["recommended_review_bucket"]),
            "same_condition_overlap": source_value(src, ["same_condition_overlap"]),
            "same_condition_overlap_note": source_value(src, ["same_condition_overlap_note"]),
            "ranking_is_proxy_only": ranking_proxy,
            "estimated_trades_per_day_proxy": source_value(src, ["estimated_trades_per_day"]),
            "estimated_trades_per_day_source": source_value(src, ["estimated_trade_days_source"]),
            "pf_winrate_priority_score_proxy": source_value(src, ["pf_winrate_priority_score"]),
            "narrowing_potential_score_proxy": source_value(src, ["narrowing_potential_score"]),
            "human_decision": decision,
            "allowed_decisions": ALLOWED_DECISIONS_TEXT,
            "human_note": source_value(hrow, ["human_note"], source_value(src, ["human_note"])),
            "reviewer": source_value(hrow, ["reviewer"], source_value(src, ["reviewer"])),
            "reviewed_at_utc": source_value(hrow, ["reviewed_at_utc"], source_value(src, ["reviewed_at_utc"])),
            "decision_validation_status": validation_status,
            "decision_validation_detail": validation_detail,
            "approval_semantics": "APPROVE_FOR_NEXT_AUDIT_ONLY_REPLAY is audit-only replay preparation only; not final approval and not live approval",
        }
        output.append(row)

    output.sort(key=lambda r: int(str(r.get("rank") or "999999").strip() or "999999"))
    return output, invalid


def entry_family_key(row: dict[str, Any]) -> str:
    group = str(row.get("candidate_group_id", "")).strip()
    direction = str(row.get("direction", "")).strip()
    feature = str(row.get("feature_column", "")).strip()
    expr = str(row.get("rule_expression_preview", "")).strip()
    return f"{group}||{direction}||{feature}||{expr}"


def build_family_notes(intake_rows: Sequence[dict[str, Any]]) -> dict[str, str]:
    family_to_profiles: dict[str, set[str]] = defaultdict(set)
    for row in intake_rows:
        family_to_profiles[entry_family_key(row)].add(str(row.get("profile_id", "")).strip())
    notes: dict[str, str] = {}
    for key, profiles in family_to_profiles.items():
        if "GROUP_H1_ATR56_HIGH_VOL" in key:
            notes[key] = (
                "same h1_atr56 >= 9.95812 entry family; multiple TP/SL profiles are not independent entry ideas; "
                f"profile_count={len([p for p in profiles if p])}"
            )
        elif len([p for p in profiles if p]) > 1:
            notes[key] = f"same entry family with multiple exit profiles; profile_count={len([p for p in profiles if p])}"
        else:
            notes[key] = "unique entry family in stage-13 ranked rows"
    return notes


def build_replay_plan_preview(intake_rows: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    family_notes = build_family_notes(intake_rows)
    approved = [row for row in intake_rows if row.get("human_decision") == APPROVE_FOR_REPLAY]
    rows: list[dict[str, Any]] = []
    for idx, row in enumerate(approved, 1):
        family_key = entry_family_key(row)
        rows.append({
            "plan_row_number": idx,
            "source_rank": row.get("rank", ""),
            "source_packet_row_number": row.get("source_packet_row_number", ""),
            "candidate_group_id": row.get("candidate_group_id", ""),
            "entry_family_key": family_key,
            "entry_family_count_note": family_notes.get(family_key, ""),
            "profile_id": row.get("profile_id", ""),
            "direction": row.get("direction", ""),
            "feature_column": row.get("feature_column", ""),
            "rule_expression_preview": row.get("rule_expression_preview", ""),
            "human_decision": row.get("human_decision", ""),
            "human_note": row.get("human_note", ""),
            "reviewer": row.get("reviewer", ""),
            "reviewed_at_utc": row.get("reviewed_at_utc", ""),
            "replay_plan_status": "PREVIEW_ONLY_READY_FOR_SEPARATE_AUDIT_REPLAY_STAGE",
            "replay_execution_allowed_in_stage14": False,
            "required_next_stage": "separate explicit audit-only replay execution instruction required",
            "ranking_is_proxy_only": row.get("ranking_is_proxy_only", "true"),
            "true_metrics_to_recompute": "true trade frequency; true win rate; true PF; drawdown; execution behavior; fold/date stability",
            "must_not_claim": "do not claim true PF, true win rate, or true trades/day from stage-13 proxy ranking",
            "blocked_actions": "replay execution; final approval; threshold finalization; model training; signal generation; ZIP; AI API; Discord; MT5; live hook; live evaluator; final signal",
        })
    return rows


def decide_status(
    input_ok: bool,
    stage13_ok: bool,
    row_counts_ok: bool,
    invalid_decisions: Sequence[str],
    intake_rows: Sequence[dict[str, Any]],
) -> str:
    if not input_ok or not stage13_ok or not row_counts_ok:
        return BLOCKED_STATUS
    if invalid_decisions:
        return INPUT_REVIEW_STATUS
    if not any(row.get("human_decision") in ALLOWED_DECISIONS for row in intake_rows):
        return INPUT_REVIEW_STATUS
    return READY_STATUS


def blocker_rows(
    input_ok: bool,
    stage13_ok: bool,
    row_counts_ok: bool,
    invalid_decisions: Sequence[str],
    non_pending_count: int,
    replay_plan_rows: int,
    legacy_quarantine_ok: bool,
) -> list[dict[str, Any]]:
    if invalid_decisions:
        human_status = "OPEN_INVALID_HUMAN_DECISION"
        human_detail = "; ".join(invalid_decisions[:10])
    elif non_pending_count <= 0:
        human_status = "OPEN_HUMAN_ACTION_REQUIRED"
        human_detail = "no APPROVE/REJECT/REQUEST_MORE_AUDIT decision provided yet"
    else:
        human_status = "CLOSED"
        human_detail = f"valid human decisions received: {non_pending_count}"

    replay_plan_ok = input_ok and stage13_ok and row_counts_ok and not invalid_decisions
    replay_plan_status = "CLOSED" if replay_plan_ok else "OPEN_BLOCKER"
    replay_plan_detail = (
        f"replay-plan preview rows written for approved rows only: {replay_plan_rows}; execution remains prohibited"
        if replay_plan_ok else
        "cannot trust replay-plan preview until inputs and human decision validation are clean"
    )

    return [
        {
            "blocker_id": "G3-14-001",
            "blocker_name": "stage-13 inputs",
            "status": "CLOSED" if input_ok and stage13_ok else "OPEN_BLOCKER",
            "detail": "required stage-13 files exist and summary status is READY" if input_ok and stage13_ok else "missing/invalid stage-13 inputs or non-ready summary",
        },
        {
            "blocker_id": "G3-14-002",
            "blocker_name": "stage-13 row counts",
            "status": "CLOSED" if row_counts_ok else "OPEN_BLOCKER",
            "detail": f"ranked rows must be {EXPECTED_RANKED_ROWS} and family rows must be {EXPECTED_FAMILY_ROWS}",
        },
        {
            "blocker_id": "G3-14-003",
            "blocker_name": "human decision intake",
            "status": human_status,
            "detail": human_detail,
        },
        {
            "blocker_id": "G3-14-004",
            "blocker_name": "approval semantics",
            "status": "CLOSED",
            "detail": "APPROVE_FOR_NEXT_AUDIT_ONLY_REPLAY is not final approval and not live approval; REQUEST_MORE_AUDIT is not approval",
        },
        {
            "blocker_id": "G3-14-005",
            "blocker_name": "replay plan preview",
            "status": replay_plan_status,
            "detail": replay_plan_detail,
        },
        {
            "blocker_id": "G3-14-006",
            "blocker_name": "replay execution",
            "status": "CLOSED_BLOCKED_BY_POLICY",
            "detail": "replay execution is prohibited in stage 14 unless a separate explicit instruction starts a later replay stage",
        },
        {
            "blocker_id": "G3-14-007",
            "blocker_name": "final approval",
            "status": "CLOSED_BLOCKED_BY_POLICY",
            "detail": "final candidate approval remains prohibited",
        },
        {
            "blocker_id": "G3-14-008",
            "blocker_name": "threshold finalization",
            "status": "CLOSED_BLOCKED_BY_POLICY",
            "detail": "threshold finalization remains prohibited",
        },
        {
            "blocker_id": "G3-14-009",
            "blocker_name": "model training",
            "status": "CLOSED_BLOCKED_BY_POLICY",
            "detail": "model training remains prohibited",
        },
        {
            "blocker_id": "G3-14-010",
            "blocker_name": "signal/live",
            "status": "CLOSED_BLOCKED_BY_POLICY",
            "detail": "signal generation/live hook/live evaluator/final signal remain OFF",
        },
        {
            "blocker_id": "G3-14-011",
            "blocker_name": "zip output",
            "status": "CLOSED_DISABLED",
            "detail": "ZIP output remains disabled",
        },
        {
            "blocker_id": "G3-14-012",
            "blocker_name": "external actions",
            "status": "CLOSED",
            "detail": "Discord/MT5/AI API/live integrations remain OFF",
        },
        {
            "blocker_id": "G3-14-013",
            "blocker_name": "quarantined legacy artifacts",
            "status": "CLOSED" if legacy_quarantine_ok else "OPEN_BLOCKER",
            "detail": "Stage 14 uses only GOLD V3 Stage 13 outputs; no quarantined legacy artifacts are read or used",
        },
    ]


def decision_matrix_rows(
    selected_root: Path,
    root_reason: str,
    optional_decision_input: Path | None,
    optional_decision_input_reason: str,
    intake_rows: Sequence[dict[str, Any]],
    replay_plan_rows: Sequence[dict[str, Any]],
    invalid_decisions: Sequence[str],
) -> list[dict[str, Any]]:
    counts = defaultdict(int)
    for row in intake_rows:
        counts[str(row.get("human_decision", ""))] += 1

    approved_family_keys = {entry_family_key(row) for row in intake_rows if row.get("human_decision") == APPROVE_FOR_REPLAY}
    h1_approved_profiles = [
        str(row.get("profile_id", ""))
        for row in intake_rows
        if row.get("human_decision") == APPROVE_FOR_REPLAY and row.get("candidate_group_id") == "GROUP_H1_ATR56_HIGH_VOL"
    ]

    return [
        {"decision_key": "selected_gold_v3_output_root", "value": str(selected_root), "detail": root_reason},
        {"decision_key": "stage13_only_source_of_truth", "value": True, "detail": "Stage 14 reads only GOLD V3 Stage 13 outputs"},
        {"decision_key": "optional_human_decision_input", "value": str(optional_decision_input) if optional_decision_input else "", "detail": optional_decision_input_reason},
        {"decision_key": "allowed_decisions", "value": ALLOWED_DECISIONS_TEXT, "detail": "APPROVE is for next audit-only replay preparation only"},
        {"decision_key": "pending_human_review_rows", "value": counts[PENDING_DECISION], "detail": "rows still awaiting decision"},
        {"decision_key": "approve_for_next_audit_only_replay_rows", "value": counts[APPROVE_FOR_REPLAY], "detail": "not final approval; not live approval"},
        {"decision_key": "reject_rows", "value": counts[REJECT], "detail": "excluded from replay-plan preview"},
        {"decision_key": "request_more_audit_rows", "value": counts[REQUEST_MORE_AUDIT], "detail": "not approval; excluded from replay-plan preview"},
        {"decision_key": "invalid_human_decision_rows", "value": len(invalid_decisions), "detail": "; ".join(invalid_decisions[:10])},
        {"decision_key": "replay_plan_preview_rows", "value": len(replay_plan_rows), "detail": "preview only; no replay executed"},
        {"decision_key": "approved_entry_family_count", "value": len(approved_family_keys), "detail": "family count deduplicates shared entry conditions"},
        {"decision_key": "h1_atr56_approved_profile_count", "value": len(h1_approved_profiles), "detail": "shared h1_atr56 entry family; profiles are not independent entry ideas"},
        {"decision_key": "auto_approval", "value": False, "detail": "stage 14 never auto-approves"},
        {"decision_key": "final_candidate_approval", "value": False, "detail": "blocked by policy"},
        {"decision_key": "threshold_finalization", "value": False, "detail": "blocked by policy"},
        {"decision_key": "replay_executed", "value": False, "detail": "blocked by policy"},
        {"decision_key": "model_training", "value": False, "detail": "blocked by policy"},
        {"decision_key": "signals_generated", "value": False, "detail": "blocked by policy"},
        {"decision_key": "zip_output_created", "value": False, "detail": "disabled"},
        {"decision_key": "external_actions", "value": False, "detail": "Discord/MT5/AI/live all OFF"},
    ]


def report(summary: dict[str, Any], intake_rows: Sequence[dict[str, Any]], replay_rows: Sequence[dict[str, Any]], blocker_matrix: Sequence[dict[str, Any]]) -> str:
    lines = [
        "# GOLD V3 14 human ranking decision intake audit-only report",
        "",
        f"Created UTC: `{summary.get('created_at_utc', '')}`",
        f"Status: `{summary.get('status', '')}`",
        "",
        "## Scope",
        "",
        "This stage reads GOLD V3 Stage 13 ranking decision outputs, creates or validates a human decision intake template, and writes an audit-only replay-plan preview for rows explicitly marked `APPROVE_FOR_NEXT_AUDIT_ONLY_REPLAY`.",
        "",
        "No replay execution, final approval, threshold finalization, model training, signal generation, ZIP output, AI API call, Discord notification, MT5 order, live hook, live evaluator, or final signal action was performed.",
        "",
        "## Path resolution",
        "",
        f"- selected_gold_v3_output_root: `{summary.get('selected_gold_v3_output_root', '')}`",
        f"- path_resolution_note: `{summary.get('path_resolution_note', '')}`",
        f"- optional_human_decision_input: `{summary.get('optional_human_decision_input', '')}`",
        "",
        "## Counts",
        "",
    ]
    for key in [
        "stage13_ranked_rows",
        "stage13_decision_template_rows",
        "stage13_candidate_family_group_rows",
        "human_intake_rows",
        "pending_human_review_rows",
        "approve_for_next_audit_only_replay_rows",
        "reject_rows",
        "request_more_audit_rows",
        "invalid_human_decision_rows",
        "replay_plan_preview_rows",
        "approved_entry_family_count",
    ]:
        lines.append(f"- {key}: `{summary.get(key, '')}`")

    lines += [
        "",
        "## Human decision intake",
        "",
        "| rank | group | profile | feature | decision | validation | proxy bucket | risk |",
        "|---:|---|---|---|---|---|---|---|",
    ]
    for row in intake_rows:
        lines.append(
            f"| {md(row.get('rank',''))} | {md(row.get('candidate_group_id',''))} | {md(row.get('profile_id',''))} | {md(row.get('feature_column',''))} | {md(row.get('human_decision',''))} | {md(row.get('decision_validation_status',''))} | {md(row.get('recommended_review_bucket',''))} | {md(row.get('risk_flags',''))} |"
        )

    lines += [
        "",
        "## Replay-plan preview rows",
        "",
        "| plan | source rank | group | profile | entry family note | status |",
        "|---:|---:|---|---|---|---|",
    ]
    if replay_rows:
        for row in replay_rows:
            lines.append(
                f"| {md(row.get('plan_row_number',''))} | {md(row.get('source_rank',''))} | {md(row.get('candidate_group_id',''))} | {md(row.get('profile_id',''))} | {md(row.get('entry_family_count_note',''))} | {md(row.get('replay_plan_status',''))} |"
            )
    else:
        lines.append("|  |  |  |  | no approved rows yet | preview empty by design |")

    lines += [
        "",
        "## Blockers",
        "",
        "| blocker_id | blocker_name | status | detail |",
        "|---|---|---|---|",
    ]
    for block in blocker_matrix:
        lines.append(
            f"| {md(block.get('blocker_id',''))} | {md(block.get('blocker_name',''))} | {md(block.get('status',''))} | {md(block.get('detail',''))} |"
        )

    lines += [
        "",
        "## Decision policy",
        "",
        "`APPROVE_FOR_NEXT_AUDIT_ONLY_REPLAY` is only approval to prepare a later audit-only replay. It is not final candidate approval, not live approval, and it does not permit Stage 14 to execute replay.",
        "",
        "`REQUEST_MORE_AUDIT` is not approval.",
        "",
        "Stage 13 ranking fields remain proxy-only. True PF, true win rate, true trades/day, drawdown, and execution behavior must be recomputed in a separate explicitly authorized audit-only replay stage.",
        "",
        "`GROUP_H1_ATR56_HIGH_VOL` rows share the same `h1_atr56 >= 9.95812` entry family and differ only by TP/SL/horizon profile. They are not counted as independent entry ideas.",
        "",
    ]
    return "\n".join(lines)


def write_all_outputs(
    output_dir: Path,
    inventory: Sequence[dict[str, Any]],
    intake_rows: Sequence[dict[str, Any]],
    replay_rows: Sequence[dict[str, Any]],
    decision_rows: Sequence[dict[str, Any]],
    blockers: Sequence[dict[str, Any]],
    summary: dict[str, Any],
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(output_dir / "gold_v3_14_input_inventory.csv", inventory, INVENTORY_FIELDS)
    write_csv(output_dir / "gold_v3_14_human_decision_intake_template.csv", intake_rows, INTAKE_FIELDS)
    write_csv(output_dir / "gold_v3_14_replay_plan_preview.csv", replay_rows, REPLAY_PLAN_FIELDS)
    write_csv(output_dir / "gold_v3_14_decision_matrix.csv", decision_rows, DECISION_FIELDS)
    write_csv(output_dir / "gold_v3_14_blocker_matrix.csv", blockers, BLOCKER_FIELDS)
    write_json(output_dir / "gold_v3_14_summary.json", summary)
    (output_dir / REPORT_NAME).write_text(report(summary, intake_rows, replay_rows, blockers), encoding="utf-8")


def empty_summary(selected_root: Path, root_reason: str, status: str, blocked_reason: str) -> dict[str, Any]:
    return {
        "created_at_utc": utc_now(),
        "step": STEP,
        "status": status,
        "blocked_reason": blocked_reason,
        "selected_gold_v3_output_root": str(selected_root),
        "path_resolution_note": root_reason,
        "upstream_stage13_status": "",
        "stage13_ranked_rows": 0,
        "stage13_decision_template_rows": 0,
        "stage13_candidate_family_group_rows": 0,
        "human_intake_rows": 0,
        "pending_human_review_rows": 0,
        "approve_for_next_audit_only_replay_rows": 0,
        "reject_rows": 0,
        "request_more_audit_rows": 0,
        "invalid_human_decision_rows": 0,
        "replay_plan_preview_rows": 0,
        "approved_entry_family_count": 0,
        "ranking_is_proxy_only": True,
        "human_decision_required": True,
        "old_gold_disc8_quarantined": True,
        "quarantined_legacy_artifacts_read": False,
        "gold_v2_live_sot_used": False,
        **FALSE_FLAGS,
    }


def write_blocked(output_dir: Path, inventory: Sequence[dict[str, Any]], selected_root: Path, root_reason: str, reason: str) -> None:
    blockers = blocker_rows(False, False, False, [], 0, 0, True)
    decisions = decision_matrix_rows(selected_root, root_reason, None, "not evaluated due to blocked inputs", [], [], [])
    summary = empty_summary(selected_root, root_reason, BLOCKED_STATUS, reason)
    write_all_outputs(output_dir, inventory, [], [], decisions, blockers, summary)


def run(repo_root: Path, human_decision_input: str = "") -> int:
    repo_root = repo_root.resolve()
    selected_root, root_reason = select_v3_root(repo_root)
    input_dir = selected_root / UPSTREAM_NAME
    output_dir = selected_root / OUT_NAME
    output_dir.mkdir(parents=True, exist_ok=True)

    optional_input, optional_reason = resolve_optional_decision_input(repo_root, output_dir, human_decision_input)
    extra_inventory = []
    if optional_input is not None:
        extra_inventory.append(("optional_human_decision_input", optional_input, False))

    inventory = inventory_rows(input_dir, extra_inventory)
    required_missing = [str(row["input_label"]) for row in inventory if row.get("required") is True and not row.get("exists")]
    if required_missing:
        reason = "missing required stage13 inputs: " + ", ".join(required_missing)
        write_blocked(output_dir, inventory, selected_root, root_reason, reason)
        print("[GOLD_V3_14] BLOCKED: " + reason)
        return 2

    summary_path = input_dir / "gold_v3_13_summary.json"
    decision_template_path = input_dir / "gold_v3_13_decision_template.csv"
    ranked_path = input_dir / "gold_v3_13_ranked_rule_candidate_rows.csv"
    families_path = input_dir / "gold_v3_13_ranked_candidate_family_groups.csv"

    stage13_summary = read_json(summary_path)
    upstream_status = str(stage13_summary.get("status", ""))
    decision_template = read_csv(decision_template_path)
    ranked_rows = read_csv(ranked_path)
    family_rows = read_csv(families_path)

    stage13_ok = upstream_status == UPSTREAM_READY_STATUS
    row_counts_ok = (
        len(ranked_rows) == EXPECTED_RANKED_ROWS
        and len(decision_template) == EXPECTED_RANKED_ROWS
        and len(family_rows) == EXPECTED_FAMILY_ROWS
        and bool(stage13_summary.get("human_decision_required", True)) is True
    )
    input_ok = stage13_ok and row_counts_ok

    human_rows: list[dict[str, str]] = []
    optional_input_used = ""
    if optional_input is not None and optional_input.exists():
        human_rows = read_csv(optional_input)
        optional_input_used = str(optional_input)
    else:
        human_rows = decision_template

    intake_rows, invalid_decisions = build_intake_rows(decision_template, human_rows)
    replay_rows = build_replay_plan_preview(intake_rows)

    non_pending_count = sum(1 for row in intake_rows if row.get("human_decision") in ALLOWED_DECISIONS)
    counts = defaultdict(int)
    for row in intake_rows:
        counts[str(row.get("human_decision", ""))] += 1
    approved_family_keys = {entry_family_key(row) for row in intake_rows if row.get("human_decision") == APPROVE_FOR_REPLAY}

    status = decide_status(input_ok, stage13_ok, row_counts_ok, invalid_decisions, intake_rows)
    blocked_reason = ""
    if not stage13_ok:
        blocked_reason = f"stage13 status is not READY: {upstream_status}"
    elif not row_counts_ok:
        blocked_reason = (
            "stage13 row count or human_decision_required check failed: "
            f"ranked={len(ranked_rows)} decision_template={len(decision_template)} family={len(family_rows)} "
            f"human_decision_required={stage13_summary.get('human_decision_required', '')}"
        )
    elif invalid_decisions:
        blocked_reason = "invalid human decision values"
    elif non_pending_count == 0:
        blocked_reason = "human decision content not provided yet; intake template generated"

    blockers = blocker_rows(input_ok, stage13_ok, row_counts_ok, invalid_decisions, non_pending_count, len(replay_rows), True)
    decisions = decision_matrix_rows(selected_root, root_reason, optional_input, optional_reason, intake_rows, replay_rows, invalid_decisions)

    summary = {
        "created_at_utc": utc_now(),
        "step": STEP,
        "status": status,
        "blocked_reason": blocked_reason,
        "selected_gold_v3_output_root": str(selected_root),
        "path_resolution_note": root_reason,
        "upstream_stage13_status": upstream_status,
        "optional_human_decision_input": optional_input_used,
        "optional_human_decision_input_reason": optional_reason,
        "stage13_ranked_rows": len(ranked_rows),
        "expected_stage13_ranked_rows": EXPECTED_RANKED_ROWS,
        "stage13_decision_template_rows": len(decision_template),
        "stage13_candidate_family_group_rows": len(family_rows),
        "expected_candidate_family_group_rows": EXPECTED_FAMILY_ROWS,
        "human_intake_rows": len(intake_rows),
        "pending_human_review_rows": counts[PENDING_DECISION],
        "approve_for_next_audit_only_replay_rows": counts[APPROVE_FOR_REPLAY],
        "reject_rows": counts[REJECT],
        "request_more_audit_rows": counts[REQUEST_MORE_AUDIT],
        "invalid_human_decision_rows": len(invalid_decisions),
        "replay_plan_preview_rows": len(replay_rows),
        "approved_entry_family_count": len(approved_family_keys),
        "ranking_is_proxy_only": True,
        "human_decision_required": True,
        "allowed_decisions": ALLOWED_DECISIONS_TEXT,
        "approve_for_next_audit_only_replay_is_final_approval": False,
        "approve_for_next_audit_only_replay_is_live_approval": False,
        "request_more_audit_is_approval": False,
        "h1_atr56_shared_entry_family_note": "h1_atr56 >= 9.95812 rows are shared entry-family TP/SL profiles, not independent entry ideas",
        "old_gold_disc8_quarantined": True,
        "quarantined_legacy_artifacts_read": False,
        "gold_v2_live_sot_used": False,
        **FALSE_FLAGS,
    }

    write_all_outputs(output_dir, inventory, intake_rows, replay_rows, decisions, blockers, summary)
    print(json.dumps({
        "status": status,
        "blocked_reason": blocked_reason,
        "human_intake_rows": len(intake_rows),
        "approve_for_next_audit_only_replay_rows": counts[APPROVE_FOR_REPLAY],
        "replay_plan_preview_rows": len(replay_rows),
        "replay_executed": False,
        "final_candidate_approval": False,
        "output_dir": str(output_dir),
        "zip_output_created": False,
    }, ensure_ascii=True, indent=2))
    return 0 if status == READY_STATUS else 2


def write_exception(repo_root: Path, exc: BaseException) -> None:
    repo_root = repo_root.resolve()
    try:
        selected_root, root_reason = select_v3_root(repo_root)
    except Exception:
        selected_root, root_reason = repo_root / "Files" / "FX_OUTPUTS" / "gold_v3", "exception_fallback_repo_root_files"
    input_dir = selected_root / UPSTREAM_NAME
    output_dir = selected_root / OUT_NAME
    output_dir.mkdir(parents=True, exist_ok=True)
    inventory = inventory_rows(input_dir)
    blockers = blocker_rows(False, False, False, [f"{exc.__class__.__name__}: {exc}"], 0, 0, True)
    decisions = decision_matrix_rows(selected_root, root_reason, None, "not evaluated due to exception", [], [], [str(exc)])
    summary = empty_summary(selected_root, root_reason, EXCEPTION_STATUS, f"{exc.__class__.__name__}: {exc}")
    write_all_outputs(output_dir, inventory, [], [], decisions, blockers, summary)
    (output_dir / "gold_v3_14_exception.txt").write_text(traceback.format_exc(), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default="")
    parser.add_argument(
        "--human-decision-input",
        default="",
        help=(
            "Optional CSV path containing edited human_decision values. If omitted, "
            "the script reads an existing stage-14 intake template when present, otherwise stage-13 pending decisions."
        ),
    )
    args = parser.parse_args(argv)
    repo_root = Path(args.repo_root).resolve() if args.repo_root else repo_root_default()
    try:
        return run(repo_root, args.human_decision_input)
    except Exception as exc:
        write_exception(repo_root, exc)
        print(
            "[GOLD_V3_14] EXCEPTION. See selected FX_OUTPUTS/gold_v3/14_human_ranking_decision_intake_audit_only/gold_v3_14_exception.txt",
            file=sys.stderr,
        )
        print(traceback.format_exc(), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
