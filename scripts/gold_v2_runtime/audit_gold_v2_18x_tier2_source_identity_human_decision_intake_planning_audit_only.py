#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

STEP = "18X_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_PLANNING_AUDIT_ONLY"
OUT_DIR = "gold_v2_18x_tier2_source_identity_human_decision_intake_planning_audit_only"
IN18W = "gold_v2_18w_tier2_source_identity_human_review_decision_packet_audit_only"
IN18V = "gold_v2_18v_tier2_source_identity_human_review_blocker_summary_audit_only"
IN18U = "gold_v2_18u_tier2_source_identity_human_review_packet_reconciliation_audit_only"
IN18T = "gold_v2_18t_tier2_source_identity_human_review_packet_content_audit_only"
IN18S = "gold_v2_18s_tier2_source_identity_human_review_packet_load_smoke_audit_only"
IN18R = "gold_v2_18r_tier2_source_identity_human_review_packet_audit_only"
IN18Q = "gold_v2_18q_tier2_source_identity_human_review_decision_planning_audit_only"
IN18P = "gold_v2_18p_tier2_source_identity_dry_run_readiness_package_audit_only"
IN18O = "gold_v2_18o_tier2_source_identity_dry_run_blocker_review_audit_only"
IN18N = "gold_v2_18n_tier2_source_identity_dry_run_reconciliation_audit_only"
IN18M = "gold_v2_18m_tier2_source_identity_dry_run_content_audit_only"
IN18L = "gold_v2_18l_tier2_source_identity_dry_run_load_smoke_audit_only"
IN18K = "gold_v2_18k_tier2_source_identity_dry_run_implementation_audit_only"
REPORT = "GOLD_V2_18X_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_PLANNING_AUDIT_ONLY_REPORT.md"
SUCCESS = "TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_PLANNING_READY_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"
EXPECTED_18W = "TIER2_SOURCE_IDENTITY_HUMAN_REVIEW_DECISION_PACKET_PREPARED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"
FORBIDDEN_GATES = {"SOURCE_IDENTITY_FINALIZATION", "SOURCE_RECOVERY", "LIVE", "FINAL_SIGNAL"}
FORBIDDEN_SUMMARY_FLAGS = ["source_recovery_executed", "source_identity_finalized", "source_identity_recovered", "ledger_is_source_of_truth", "live_or_final_implementation_allowed", "oh_lc_replay_allowed", "live_enabled", "final_signal_allowed", "no_signal_discord_notified"]


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
    ensure(path); df.to_csv(lp(path), index=False, encoding="utf-8-sig")


def wtxt(path: Path, text: str) -> None:
    ensure(path); lp(path).write_text(text, encoding="utf-8")


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
    return int((df["status"].astype(str) == "STOP").sum()) if "status" in df.columns else 999


def ck(cid: str, name: str, observed: Any, expected: Any, ok: bool) -> dict[str, Any]:
    return {"check_id": cid, "check": name, "observed": observed, "expected": expected, "status": "PASS" if ok else "STOP"}


def mdtable(df: pd.DataFrame, limit: int = 100) -> str:
    if df.empty:
        return "_No rows._"
    cols = list(df.columns)
    out = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for _, row in df.head(limit).iterrows():
        out.append("| " + " | ".join(str(row[c]).replace("|", "\\|").replace("\n", " ") for c in cols) + " |")
    return "\n".join(out)


def forbidden_gate_count(df: pd.DataFrame, col: str) -> int:
    if {"next_step", col}.issubset(df.columns):
        return int(df[df["next_step"].astype(str).isin(FORBIDDEN_GATES)][col].map(truthy).sum())
    return 999


def summary_forbidden_true(summary: dict[str, Any]) -> int:
    n = sum(int(bool(summary.get(k, False))) for k in FORBIDDEN_SUMMARY_FLAGS)
    ext = summary.get("external_actions", {})
    n += sum(int(bool(v)) for v in ext.values()) if isinstance(ext, dict) else 1
    return n


def next_gates(success: bool) -> pd.DataFrame:
    return pd.DataFrame([
        ["18Y", "TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_LOAD_SMOKE_AUDIT_ONLY", "Load-smoke decision intake template and validation tables only.", bool(success)],
        ["SOURCE_IDENTITY_FINALIZATION", "TIER2_SOURCE_IDENTITY_FINALIZATION", "Blocked after 18X.", False],
        ["SOURCE_RECOVERY", "TIER2_SOURCE_IDENTITY_RECOVERY_EXECUTION", "Blocked after 18X.", False],
        ["LIVE", "MEDIUM_FULL_SET_LIVE_EVALUATOR", "Blocked.", False],
        ["FINAL_SIGNAL", "MEDIUM_FINAL_SIGNAL", "Blocked.", False],
    ], columns=["next_step", "name", "purpose", "allowed_after_18x_success"])


def safety(success: bool) -> pd.DataFrame:
    return pd.DataFrame([
        ["audit_only", True, True, "PASS"], ["intake_planning_only", True, True, "PASS"],
        ["decision_collected", False, False, "PASS"], ["decision_made", False, False, "PASS"], ["approval_granted", False, False, "PASS"],
        ["ledger_is_source_of_truth", False, False, "PASS"], ["source_recovery_executed", False, False, "PASS"],
        ["source_identity_finalized", False, False, "PASS"], ["source_identity_recovered", False, False, "PASS"],
        ["live_or_final_implementation_allowed", False, False, "PASS"], ["oh_lc_replay_allowed", False, False, "PASS"],
        ["discord_send_allowed", False, False, "PASS"], ["mt5_order_allowed", False, False, "PASS"],
        ["ai_api_allowed", False, False, "PASS"], ["live_hook_allowed", False, False, "PASS"],
        ["no_signal_discord_notified", False, False, "PASS"], ["next_gate_18y_only_after_success", bool(success), bool(success), "PASS"],
    ], columns=["safety_item", "observed", "expected", "status"])


def stop_conditions() -> pd.DataFrame:
    return pd.DataFrame([
        ["18X-S001", "required inputs missing", "STOP"], ["18X-S002", "18W status not passed", "STOP"],
        ["18X-S003", "decision or approval already made", "STOP"], ["18X-S004", "upstream STOP rows present", "STOP"],
        ["18X-S005", "human-only options invalid", "STOP"], ["18X-S006", "intake fields or allowed values missing", "STOP"],
        ["18X-S007", "forbidden gate allowed", "STOP"], ["18X-S008", "forbidden safety flag true", "STOP"],
    ], columns=["stop_id", "condition", "action"])


def main() -> int:
    out = fx() / OUT_DIR
    lp(out).mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()
    p18w, p18v = fx()/IN18W, fx()/IN18V
    refs = [fx()/x for x in [IN18K, IN18L, IN18M, IN18N, IN18O, IN18P, IN18Q, IN18R, IN18S, IN18T, IN18U, IN18V, IN18W]]
    inputs = {
        "summary_18w": p18w / "gold_v2_18w_tier2_source_identity_human_review_decision_packet_summary.json",
        "checks_18w": p18w / "gold_v2_18w_decision_packet_checks.csv",
        "options_18w": p18w / "gold_v2_18w_human_decision_options.csv",
        "packet_18w": p18w / "gold_v2_18w_decision_packet_markdown.md",
        "gates_18w": p18w / "gold_v2_18w_required_next_gates.csv",
        "safety_18w": p18w / "gold_v2_18w_safety_matrix.csv",
        "report_18w": p18w / "GOLD_V2_18W_TIER2_SOURCE_IDENTITY_HUMAN_REVIEW_DECISION_PACKET_AUDIT_ONLY_REPORT.md",
        "remaining_blockers_18v": p18v / "gold_v2_18v_remaining_blockers.csv",
        "manual_summary_18v": p18v / "gold_v2_18v_manual_decision_summary.csv",
    }
    input_audit = pd.DataFrame([{"role": k, "path": str(v), "required": True, "exists": lp(v).exists()} for k, v in inputs.items()])
    wcsv(input_audit, out / "gold_v2_18x_input_audit.csv")
    if not input_audit["exists"].all():
        checks = pd.DataFrame([ck("18X-C000", "required inputs exist", False, True, False)])
        wcsv(checks, out / "gold_v2_18x_intake_planning_checks.csv")
        sm = safety(False); wcsv(sm, out / "gold_v2_18x_safety_matrix.csv")
        summary = {"created_utc": now, "step": STEP, "status": "18X_STOP_MISSING_INPUTS", "audit_only": True, "intake_planning_ready": False, "next_recommended_step": "STOP_REVIEW_18X_INPUTS"}
        wjson(out / "gold_v2_18x_tier2_source_identity_human_decision_intake_planning_summary.json", summary)
        wtxt(out / REPORT, "# GOLD V2 18X human decision intake planning audit-only report\n\nStatus: `18X_STOP_MISSING_INPUTS`\n")
        print(json.dumps(summary, ensure_ascii=False, indent=2)); return 2

    s18w = rjson(inputs["summary_18w"])
    checks18w, options, gates18w, safe18w = rcsv(inputs["checks_18w"]), rcsv(inputs["options_18w"]), rcsv(inputs["gates_18w"]), rcsv(inputs["safety_18w"])
    blockers, manual_summary = rcsv(inputs["remaining_blockers_18v"]), rcsv(inputs["manual_summary_18v"])
    required_fields = pd.DataFrame([
        ["decision_id", "string", "must be unique", True],
        ["decision_timestamp_utc", "string", "ISO-8601 UTC timestamp supplied by human process", True],
        ["decision_value", "enum", "one of allowed decision values", True],
        ["human_reviewer", "string", "named human reviewer or operator", True],
        ["evidence_acknowledged", "boolean", "must be true in future intake", True],
        ["explicit_phrase", "string", "must exactly match future expected phrase", True],
        ["notes", "string", "optional human notes", False],
    ], columns=["field", "type", "requirement", "required"])
    allowed_values = pd.DataFrame([
        ["DEFER", "No approval; keep all blockers", False],
        ["REQUEST_MORE_AUDIT", "No approval; request more audit-only work", False],
        ["REJECT_SOURCE_RECOVERY", "No approval; reject source recovery/finalization", False],
        ["EXPLICIT_APPROVAL_CANDIDATE", "Potential future explicit approval candidate; still must be validated by later guarded step", False],
    ], columns=["decision_value", "meaning", "executes_action_in_18x"])
    template = {
        "decision_id": "UNSET",
        "decision_timestamp_utc": None,
        "decision_value": "UNSET",
        "human_reviewer": "UNSET",
        "evidence_acknowledged": False,
        "explicit_phrase": "UNSET",
        "notes": "",
        "script_validation_status": "TEMPLATE_ONLY_NOT_A_DECISION",
        "source_recovery_executed": False,
        "source_identity_finalized": False,
        "live_enabled": False,
    }
    wcsv(required_fields, out / "gold_v2_18x_required_intake_fields.csv")
    wcsv(allowed_values, out / "gold_v2_18x_allowed_decision_values.csv")
    wjson(out / "gold_v2_18x_human_decision_template.json", template)
    options_human_only = bool((options.get("decision_owner", pd.Series(dtype=str)).astype(str) == "HUMAN_ONLY").all()) if not options.empty else False
    options_no_exec = not bool(options.get("script_executes_action", pd.Series(dtype=bool)).map(truthy).any()) if not options.empty else False
    blockers_still = bool(blockers.get("still_blocking_after_18v", pd.Series(dtype=bool)).map(truthy).all()) if not blockers.empty else False
    required_field_count = int(required_fields["required"].map(truthy).sum())
    allowed_value_count = int(len(allowed_values))
    upstream_stop = stop_count(checks18w) + stop_count(safe18w)
    forbidden_gates = forbidden_gate_count(gates18w, "allowed_after_18w_success")
    summaries = []
    for p in refs:
        if lp(p).exists():
            found = list(lp(p).glob("*summary.json"))
            if found:
                summaries.append(rjson(found[0]))
    forbidden_flags = sum(summary_forbidden_true(s) for s in summaries)
    checks = pd.DataFrame([
        ck("18X-C001", "18W status", s18w.get("status"), EXPECTED_18W, s18w.get("status") == EXPECTED_18W),
        ck("18X-C002", "18W decision_packet_prepared", s18w.get("decision_packet_prepared"), True, bool(s18w.get("decision_packet_prepared", False))),
        ck("18X-C003", "18W total_stop_rows", s18w.get("total_stop_rows"), 0, s18w.get("total_stop_rows") == 0),
        ck("18X-C004", "18W decision_made", s18w.get("decision_made"), False, s18w.get("decision_made") is False),
        ck("18X-C005", "18W approval_granted", s18w.get("approval_granted"), False, s18w.get("approval_granted") is False),
        ck("18X-C006", "upstream STOP rows", upstream_stop, 0, upstream_stop == 0),
        ck("18X-C007", "human decision options are HUMAN_ONLY", options_human_only, True, options_human_only),
        ck("18X-C008", "human decision options execute no action", options_no_exec, True, options_no_exec),
        ck("18X-C009", "blockers remain present", len(blockers), ">0", len(blockers) > 0),
        ck("18X-C010", "blockers still blocking", blockers_still, True, blockers_still),
        ck("18X-C011", "required intake fields defined", required_field_count, ">=6", required_field_count >= 6),
        ck("18X-C012", "allowed decision values defined", allowed_value_count, ">=4", allowed_value_count >= 4),
        ck("18X-C013", "template is unset", template["decision_value"], "UNSET", template["decision_value"] == "UNSET"),
        ck("18X-C014", "forbidden gates allowed", forbidden_gates, 0, forbidden_gates == 0),
        ck("18X-C015", "forbidden summary flags true", forbidden_flags, 0, forbidden_flags == 0),
    ])
    total_stop = stop_count(checks)
    success = total_stop == 0
    status = SUCCESS if success else "18X_STOP_REVIEW_INTAKE_PLANNING_OUTPUTS"
    sm = safety(success)
    gates = next_gates(success)
    for name, df in [
        ("gold_v2_18x_intake_planning_checks.csv", checks),
        ("gold_v2_18x_required_next_gates.csv", gates),
        ("gold_v2_18x_stop_conditions.csv", stop_conditions()),
        ("gold_v2_18x_safety_matrix.csv", sm),
    ]:
        wcsv(df, out / name)
    summary = {
        "created_utc": now, "step": STEP, "status": status, "audit_only": True,
        "intake_planning_ready": success, "decision_collected": False, "decision_made": False, "approval_granted": False,
        "upstream_18w_status": s18w.get("status"), "required_intake_fields": int(len(required_fields)),
        "allowed_decision_values": int(len(allowed_values)), "template_written": True, "total_stop_rows": int(total_stop),
        "source_recovery_executed": False, "source_identity_finalized": False, "source_identity_recovered": False,
        "ledger_is_source_of_truth": False, "live_or_final_implementation_allowed": False, "oh_lc_replay_allowed": False,
        "live_enabled": False, "final_signal_allowed": False,
        "external_actions": {"discord_send_allowed": False, "mt5_order_allowed": False, "ai_api_allowed": False, "live_hook_allowed": False},
        "no_signal_discord_notified": False,
        "next_recommended_step": "18Y_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_LOAD_SMOKE_AUDIT_ONLY" if success else "STOP_REVIEW_18X_OUTPUTS",
    }
    wjson(out / "gold_v2_18x_tier2_source_identity_human_decision_intake_planning_summary.json", summary)
    report = [
        "# GOLD V2 18X TIER2 source identity human decision intake planning audit-only report", "", f"Created UTC: {now}", f"Status: `{status}`", "",
        "## Final decision", "- 18X planned human-decision intake only.", "- No decision was collected and no approval was made by this script.", "- Source recovery, identity finalization/recovery, OHLC replay, live/final paths, Discord, MT5, AI API, live hook, and NO_SIGNAL Discord remain disabled.", "",
        "## Intake planning checks", mdtable(checks), "", "## Required intake fields", mdtable(required_fields), "", "## Allowed decision values", mdtable(allowed_values), "", "## Next gates", mdtable(gates), "", "## Safety", mdtable(sm),
    ]
    wtxt(out / REPORT, "\n".join(report))
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if success else 2


if __name__ == "__main__":
    raise SystemExit(main())
