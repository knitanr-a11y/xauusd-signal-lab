#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

STEP = "18S_TIER2_SOURCE_IDENTITY_HUMAN_REVIEW_PACKET_LOAD_SMOKE_AUDIT_ONLY"
OUT_DIR = "gold_v2_18s_tier2_source_identity_human_review_packet_load_smoke_audit_only"
IN18R = "gold_v2_18r_tier2_source_identity_human_review_packet_audit_only"
IN18Q = "gold_v2_18q_tier2_source_identity_human_review_decision_planning_audit_only"
IN18P = "gold_v2_18p_tier2_source_identity_dry_run_readiness_package_audit_only"
IN18O = "gold_v2_18o_tier2_source_identity_dry_run_blocker_review_audit_only"
IN18N = "gold_v2_18n_tier2_source_identity_dry_run_reconciliation_audit_only"
IN18M = "gold_v2_18m_tier2_source_identity_dry_run_content_audit_only"
IN18L = "gold_v2_18l_tier2_source_identity_dry_run_load_smoke_audit_only"
IN18K = "gold_v2_18k_tier2_source_identity_dry_run_implementation_audit_only"
REPORT = "GOLD_V2_18S_TIER2_SOURCE_IDENTITY_HUMAN_REVIEW_PACKET_LOAD_SMOKE_AUDIT_ONLY_REPORT.md"
SUCCESS = "TIER2_SOURCE_IDENTITY_HUMAN_REVIEW_PACKET_LOAD_SMOKE_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"
EXPECTED_18R = "TIER2_SOURCE_IDENTITY_HUMAN_REVIEW_PACKET_READY_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"
FORBIDDEN_GATES = ["SOURCE_IDENTITY_FINALIZATION", "SOURCE_RECOVERY", "LIVE", "FINAL_SIGNAL"]
FORBIDDEN_SUMMARY_FLAGS = [
    "source_recovery_executed",
    "source_identity_finalized",
    "source_identity_recovered",
    "ledger_is_source_of_truth",
    "live_or_final_implementation_allowed",
    "oh_lc_replay_allowed",
    "live_enabled",
    "final_signal_allowed",
    "no_signal_discord_notified",
]
AFFIRMATIVE_APPROVAL_MARKERS = [
    "approval granted",
    "approval_granted: true",
    "approved by this script",
    "script approved",
    "decision made by this script",
    "decision_made: true",
    "source-of-truth accepted",
    "source of truth accepted",
    "source-of-truth acceptance granted",
    "source identity finalization approved",
    "source recovery approved",
    "live readiness granted",
    "final signal readiness granted",
    "ready for live trading",
    "live evaluator enabled",
    "final signal enabled",
]
REQUIRED_MARKDOWN_NEGATIONS = [
    "not approval",
    "not source recovery",
    "not source identity finalization",
    "not source-of-truth acceptance",
    "not live readiness",
    "not final signal readiness",
]


def root() -> Path:
    return Path(__file__).resolve().parents[2]


def fx() -> Path:
    r = root()
    return (r.parents[1] if len(r.parents) >= 2 else r.parent) / "FX_OUTPUTS"


def lp(path: Path) -> Path:
    p = path if path.is_absolute() else path.resolve()
    if os.name != "nt":
        return p
    s = str(p)
    if s.startswith("\\\\?\\"):
        return Path(s)
    if s.startswith("\\\\"):
        return Path("\\\\?\\UNC\\" + s[2:])
    return Path("\\\\?\\" + s)


def ensure(path: Path) -> None:
    lp(path.parent).mkdir(parents=True, exist_ok=True)


def wcsv(df: pd.DataFrame, path: Path) -> None:
    ensure(path)
    df.to_csv(lp(path), index=False, encoding="utf-8-sig")


def wtxt(path: Path, text: str) -> None:
    ensure(path)
    lp(path).write_text(text, encoding="utf-8")


def wjson(path: Path, obj: dict[str, Any]) -> None:
    wtxt(path, json.dumps(obj, ensure_ascii=False, indent=2))


def rjson(path: Path) -> dict[str, Any]:
    return json.loads(lp(path).read_text(encoding="utf-8"))


def rcsv(path: Path) -> pd.DataFrame:
    last: Exception | None = None
    for enc in ("utf-8-sig", "utf-8", "cp932"):
        try:
            return pd.read_csv(lp(path), encoding=enc, keep_default_na=False)
        except Exception as exc:
            last = exc
    raise RuntimeError(f"csv read failed: {path}: {last}")


def truthy(v: Any) -> bool:
    if isinstance(v, bool):
        return v
    return str(v).strip().lower() in {"1", "true", "yes", "y"}


def stop_count(df: pd.DataFrame) -> int:
    if "status" not in df.columns:
        return 999
    return int((df["status"].astype(str) == "STOP").sum())


def ck(cid: str, name: str, observed: Any, expected: Any, ok: bool) -> dict[str, Any]:
    return {"check_id": cid, "check": name, "observed": observed, "expected": expected, "status": "PASS" if ok else "STOP"}


def mdtable(df: pd.DataFrame, limit: int = 80) -> str:
    if df.empty:
        return "_No rows._"
    cols = list(df.columns)
    out = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for _, row in df.head(limit).iterrows():
        out.append("| " + " | ".join(str(row[c]).replace("|", "\\|").replace("\n", " ") for c in cols) + " |")
    if len(df) > limit:
        out.append(f"\n_Showing first {limit} of {len(df)} rows._")
    return "\n".join(out)


def forbidden_summary_true(summary: dict[str, Any]) -> int:
    n = 0
    for key in FORBIDDEN_SUMMARY_FLAGS:
        n += int(bool(summary.get(key, False)))
    ext = summary.get("external_actions", {})
    if isinstance(ext, dict):
        n += sum(int(bool(v)) for v in ext.values())
    else:
        n += 1
    return n


def affirmative_approval_language_found(markdown_text: str) -> bool:
    lowered = markdown_text.lower()
    return any(marker in lowered for marker in AFFIRMATIVE_APPROVAL_MARKERS)


def required_negation_language_present(markdown_text: str) -> bool:
    lowered = markdown_text.lower()
    return all(marker in lowered for marker in REQUIRED_MARKDOWN_NEGATIONS)


def safety(success: bool) -> pd.DataFrame:
    return pd.DataFrame([
        ["audit_only", True, True, "PASS"],
        ["packet_load_smoke_only", True, True, "PASS"],
        ["decision_made", False, False, "PASS"],
        ["approval_granted", False, False, "PASS"],
        ["ledger_is_source_of_truth", False, False, "PASS"],
        ["source_recovery_executed", False, False, "PASS"],
        ["source_identity_finalized", False, False, "PASS"],
        ["source_identity_recovered", False, False, "PASS"],
        ["live_or_final_implementation_allowed", False, False, "PASS"],
        ["oh_lc_replay_allowed", False, False, "PASS"],
        ["discord_send_allowed", False, False, "PASS"],
        ["mt5_order_allowed", False, False, "PASS"],
        ["ai_api_allowed", False, False, "PASS"],
        ["live_hook_allowed", False, False, "PASS"],
        ["no_signal_discord_notified", False, False, "PASS"],
        ["next_gate_18t_only_after_success", bool(success), bool(success), "PASS"],
    ], columns=["safety_item", "observed", "expected", "status"])


def next_gates(success: bool) -> pd.DataFrame:
    return pd.DataFrame([
        ["18T", "TIER2_SOURCE_IDENTITY_HUMAN_REVIEW_PACKET_CONTENT_AUDIT_ONLY", "Inspect human-review packet content more deeply; still not source-of-truth.", bool(success)],
        ["SOURCE_IDENTITY_FINALIZATION", "TIER2_SOURCE_IDENTITY_FINALIZATION", "Blocked after 18S.", False],
        ["SOURCE_RECOVERY", "TIER2_SOURCE_IDENTITY_RECOVERY_EXECUTION", "Blocked after 18S.", False],
        ["LIVE", "MEDIUM_FULL_SET_LIVE_EVALUATOR", "Blocked.", False],
        ["FINAL_SIGNAL", "MEDIUM_FINAL_SIGNAL", "Blocked.", False],
    ], columns=["next_step", "name", "purpose", "allowed_after_18s_success"])


def stop_conditions() -> pd.DataFrame:
    return pd.DataFrame([
        ["18S-S001", "required inputs missing", "STOP"],
        ["18S-S002", "18R status not passed", "STOP"],
        ["18S-S003", "18R made decision or granted approval", "STOP"],
        ["18S-S004", "any upstream STOP row present", "STOP"],
        ["18S-S005", "packet files missing", "STOP"],
        ["18S-S006", "markdown empty or has affirmative approval/final readiness language", "STOP"],
        ["18S-S007", "manual questions are not manual-only", "STOP"],
        ["18S-S008", "blocked actions are not blocked", "STOP"],
        ["18S-S009", "forbidden gate allowed", "STOP"],
        ["18S-S010", "forbidden safety flag true", "STOP"],
    ], columns=["stop_id", "condition", "action"])


def main() -> int:
    out = fx() / OUT_DIR
    lp(out).mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()
    p18r = fx() / IN18R
    p18q = fx() / IN18Q
    p18p = fx() / IN18P
    p18o = fx() / IN18O
    p18n = fx() / IN18N
    p18m = fx() / IN18M
    p18l = fx() / IN18L
    p18k = fx() / IN18K
    inputs = {
        "summary_18r": p18r / "gold_v2_18r_tier2_source_identity_human_review_packet_summary.json",
        "input_audit_18r": p18r / "gold_v2_18r_input_audit.csv",
        "packet_checks_18r": p18r / "gold_v2_18r_packet_checks.csv",
        "packet_index_18r": p18r / "gold_v2_18r_human_review_packet_index.csv",
        "packet_markdown_18r": p18r / "gold_v2_18r_human_review_packet_markdown.md",
        "manual_questions_18r": p18r / "gold_v2_18r_manual_decision_questions.csv",
        "blocked_actions_18r": p18r / "gold_v2_18r_actions_still_blocked.csv",
        "next_gates_18r": p18r / "gold_v2_18r_required_next_gates.csv",
        "safety_18r": p18r / "gold_v2_18r_safety_matrix.csv",
        "report_18r": p18r / "GOLD_V2_18R_TIER2_SOURCE_IDENTITY_HUMAN_REVIEW_PACKET_AUDIT_ONLY_REPORT.md",
        "summary_18q": p18q / "gold_v2_18q_tier2_source_identity_human_review_decision_planning_summary.json",
        "summary_18p": p18p / "gold_v2_18p_tier2_source_identity_dry_run_readiness_package_summary.json",
        "summary_18o": p18o / "gold_v2_18o_tier2_source_identity_dry_run_blocker_review_summary.json",
        "summary_18n": p18n / "gold_v2_18n_tier2_source_identity_dry_run_reconciliation_summary.json",
        "summary_18m": p18m / "gold_v2_18m_tier2_source_identity_dry_run_content_summary.json",
        "summary_18l": p18l / "gold_v2_18l_tier2_source_identity_dry_run_load_smoke_summary.json",
        "summary_18k": p18k / "gold_v2_18k_tier2_source_identity_dry_run_implementation_summary.json",
    }
    input_audit = pd.DataFrame([{"role": k, "path": str(v), "required": True, "exists": lp(v).exists()} for k, v in inputs.items()])
    wcsv(input_audit, out / "gold_v2_18s_input_audit.csv")
    if not input_audit["exists"].all():
        status = "18S_STOP_MISSING_INPUTS"
        checks = pd.DataFrame([ck("18S-C000", "required inputs exist", False, True, False)])
        wcsv(checks, out / "gold_v2_18s_load_checks.csv")
        wcsv(safety(False), out / "gold_v2_18s_safety_matrix.csv")
        summary = {"created_utc": now, "step": STEP, "status": status, "audit_only": True, "packet_load_smoke_passed": False, "next_recommended_step": "STOP_REVIEW_18S_INPUTS"}
        wjson(out / "gold_v2_18s_tier2_source_identity_human_review_packet_load_smoke_summary.json", summary)
        wtxt(out / REPORT, "# GOLD V2 18S TIER2 source identity human review packet load-smoke audit-only report\n\nStatus: `18S_STOP_MISSING_INPUTS`\n")
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 2
    s18r = rjson(inputs["summary_18r"])
    summaries = {"18K": rjson(inputs["summary_18k"]), "18L": rjson(inputs["summary_18l"]), "18M": rjson(inputs["summary_18m"]), "18N": rjson(inputs["summary_18n"]), "18O": rjson(inputs["summary_18o"]), "18P": rjson(inputs["summary_18p"]), "18Q": rjson(inputs["summary_18q"]), "18R": s18r}
    packet_checks_18r = rcsv(inputs["packet_checks_18r"])
    packet_index = rcsv(inputs["packet_index_18r"])
    manual_questions = rcsv(inputs["manual_questions_18r"])
    blocked_actions = rcsv(inputs["blocked_actions_18r"])
    gates = rcsv(inputs["next_gates_18r"])
    safe18r = rcsv(inputs["safety_18r"])
    markdown = lp(inputs["packet_markdown_18r"]).read_text(encoding="utf-8")
    _ = lp(inputs["report_18r"]).read_text(encoding="utf-8")

    upstream_stop = stop_count(packet_checks_18r) + stop_count(safe18r)
    packet_file_rows = []
    if {"file", "status"}.issubset(packet_index.columns):
        for _, row in packet_index.iterrows():
            f = str(row["file"])
            exists = lp(p18r / f).exists()
            packet_file_rows.append({"packet_file": f, "index_status": row["status"], "exists": exists, "status": "PASS" if exists else "STOP"})
    packet_file_audit = pd.DataFrame(packet_file_rows)
    markdown_nonempty = bool(markdown.strip())
    markdown_audit_only = "audit-only" in markdown.lower()
    markdown_required_negations = required_negation_language_present(markdown)
    approval_bad = affirmative_approval_language_found(markdown)
    markdown_audit = pd.DataFrame([
        ["18S-MD001", "markdown non-empty", markdown_nonempty, True, "PASS" if markdown_nonempty else "STOP"],
        ["18S-MD002", "markdown contains audit-only language", markdown_audit_only, True, "PASS" if markdown_audit_only else "STOP"],
        ["18S-MD003", "markdown contains required negative readiness language", markdown_required_negations, True, "PASS" if markdown_required_negations else "STOP"],
        ["18S-MD004", "markdown has no affirmative approval/final readiness language", approval_bad, False, "PASS" if not approval_bad else "STOP"],
    ], columns=["markdown_check_id", "check", "observed", "expected", "status"])
    manual_bad = 999
    if "script_decision_status" in manual_questions.columns:
        manual_bad = int((manual_questions["script_decision_status"].astype(str) != "NO_SCRIPT_DECISION").sum())
    manual_audit = pd.DataFrame([[
        "18S-Q001", "manual questions remain no-script-decision", manual_bad, 0, "PASS" if manual_bad == 0 else "STOP"
    ]], columns=["question_check_id", "check", "observed", "expected", "status"])
    blocked_bad = 999
    if "status" in blocked_actions.columns:
        blocked_bad = int((blocked_actions["status"].astype(str) != "BLOCKED").sum())
    blocked_audit = pd.DataFrame([[
        "18S-A001", "blocked actions remain BLOCKED", blocked_bad, 0, "PASS" if blocked_bad == 0 else "STOP"
    ]], columns=["action_check_id", "check", "observed", "expected", "status"])
    forbidden_gate_true = 999
    if {"next_step", "allowed_after_18r_success"}.issubset(gates.columns):
        forbidden = gates[gates["next_step"].astype(str).isin(FORBIDDEN_GATES)]
        forbidden_gate_true = int(forbidden["allowed_after_18r_success"].map(truthy).sum())
    forbidden_summary_total = sum(forbidden_summary_true(v) for v in summaries.values())
    load_checks = pd.DataFrame([
        ck("18S-C001", "18R status", s18r.get("status"), EXPECTED_18R, s18r.get("status") == EXPECTED_18R),
        ck("18S-C002", "18R human_review_packet_ready", s18r.get("human_review_packet_ready"), True, bool(s18r.get("human_review_packet_ready", False))),
        ck("18S-C003", "18R decision_made", s18r.get("decision_made"), False, s18r.get("decision_made") is False),
        ck("18S-C004", "18R approval_granted", s18r.get("approval_granted"), False, s18r.get("approval_granted") is False),
        ck("18S-C005", "18R total_stop_rows", s18r.get("total_stop_rows"), 0, s18r.get("total_stop_rows") == 0),
        ck("18S-C006", "18R upstream STOP rows", upstream_stop, 0, upstream_stop == 0),
        ck("18S-C007", "packet file STOP rows", stop_count(packet_file_audit), 0, stop_count(packet_file_audit) == 0),
        ck("18S-C008", "markdown STOP rows", stop_count(markdown_audit), 0, stop_count(markdown_audit) == 0),
        ck("18S-C009", "manual question STOP rows", stop_count(manual_audit), 0, stop_count(manual_audit) == 0),
        ck("18S-C010", "blocked action STOP rows", stop_count(blocked_audit), 0, stop_count(blocked_audit) == 0),
        ck("18S-C011", "forbidden gates allowed", forbidden_gate_true, 0, forbidden_gate_true == 0),
        ck("18S-C012", "forbidden summary flags true across 18K-18R", forbidden_summary_total, 0, forbidden_summary_total == 0),
    ])
    total_stop = sum(stop_count(df) for df in [load_checks, packet_file_audit, markdown_audit, manual_audit, blocked_audit])
    success = total_stop == 0
    status = SUCCESS if success else "18S_STOP_REVIEW_PACKET_LOAD_SMOKE_OUTPUTS"
    sm = safety(success)
    for name, df in [
        ("gold_v2_18s_load_checks.csv", load_checks),
        ("gold_v2_18s_packet_file_audit.csv", packet_file_audit),
        ("gold_v2_18s_markdown_audit.csv", markdown_audit),
        ("gold_v2_18s_manual_question_audit.csv", manual_audit),
        ("gold_v2_18s_blocked_action_audit.csv", blocked_audit),
        ("gold_v2_18s_required_next_gates.csv", next_gates(success)),
        ("gold_v2_18s_stop_conditions.csv", stop_conditions()),
        ("gold_v2_18s_safety_matrix.csv", sm),
    ]:
        wcsv(df, out / name)
    summary = {
        "created_utc": now,
        "step": STEP,
        "status": status,
        "audit_only": True,
        "packet_load_smoke_passed": success,
        "decision_made": False,
        "approval_granted": False,
        "upstream_18r_status": s18r.get("status"),
        "packet_files_checked": int(len(packet_file_audit)),
        "manual_questions_checked": int(len(manual_questions)),
        "blocked_actions_checked": int(len(blocked_actions)),
        "total_stop_rows": total_stop,
        "source_recovery_executed": False,
        "source_identity_finalized": False,
        "source_identity_recovered": False,
        "ledger_is_source_of_truth": False,
        "live_or_final_implementation_allowed": False,
        "oh_lc_replay_allowed": False,
        "live_enabled": False,
        "final_signal_allowed": False,
        "external_actions": {"discord_send_allowed": False, "mt5_order_allowed": False, "ai_api_allowed": False, "live_hook_allowed": False},
        "no_signal_discord_notified": False,
        "next_recommended_step": "18T_TIER2_SOURCE_IDENTITY_HUMAN_REVIEW_PACKET_CONTENT_AUDIT_ONLY" if success else "STOP_REVIEW_18S_OUTPUTS",
    }
    wjson(out / "gold_v2_18s_tier2_source_identity_human_review_packet_load_smoke_summary.json", summary)
    report = [
        "# GOLD V2 18S TIER2 source identity human review packet load-smoke audit-only report",
        "",
        f"Created UTC: {now}",
        f"Status: `{status}`",
        "",
        "## Final decision",
        "- 18S load-smoke checked the 18R human-review packet only.",
        "- No decision or approval was made by this script.",
        "- Source recovery, identity finalization/recovery, OHLC replay, live/final paths, Discord, MT5, AI API, live hook, and NO_SIGNAL Discord remain disabled.",
        "",
        "## Load checks",
        mdtable(load_checks),
        "",
        "## Packet file audit",
        mdtable(packet_file_audit),
        "",
        "## Markdown audit",
        mdtable(markdown_audit),
        "",
        "## Manual question audit",
        mdtable(manual_audit),
        "",
        "## Blocked action audit",
        mdtable(blocked_audit),
        "",
        "## Next gates",
        mdtable(next_gates(success)),
        "",
        "## Safety",
        mdtable(sm),
    ]
    wtxt(out / REPORT, "\n".join(report))
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if success else 2


if __name__ == "__main__":
    raise SystemExit(main())
