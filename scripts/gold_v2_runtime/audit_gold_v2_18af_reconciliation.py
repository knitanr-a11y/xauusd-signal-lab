#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

STEP = "18AF_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_READINESS_PACKAGE_RECONCILIATION_AUDIT_ONLY"
OUT_DIR = "gold_v2_18af_tier2_source_identity_human_decision_intake_readiness_package_reconciliation_audit_only"
IN18AC = "gold_v2_18ac_tier2_source_identity_human_decision_intake_readiness_package_audit_only"
IN18AD = "gold_v2_18ad_tier2_source_identity_human_decision_intake_readiness_package_load_smoke_audit_only"
IN18AE = "gold_v2_18ae_tier2_source_identity_human_decision_intake_readiness_package_content_audit_only"
REPORT = "GOLD_V2_18AF_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_READINESS_PACKAGE_RECONCILIATION_AUDIT_ONLY_REPORT.md"
SUCCESS = "TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_READINESS_PACKAGE_RECONCILIATION_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"
EXPECTED_18AE = "TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_READINESS_PACKAGE_CONTENT_AUDIT_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"
FORBIDDEN_GATES = {"SOURCE_IDENTITY_FINALIZATION", "SOURCE_RECOVERY", "LIVE", "FINAL_SIGNAL"}
FORBIDDEN_FLAGS = [
    "source_recovery_executed", "source_identity_finalized", "source_identity_recovered",
    "ledger_is_source_of_truth", "live_or_final_implementation_allowed", "oh_lc_replay_allowed",
    "live_enabled", "final_signal_allowed", "no_signal_discord_notified",
]
REF_DIRS = [IN18AC, IN18AD, IN18AE]


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def fx_outputs() -> Path:
    root = repo_root()
    return (root.parents[1] if len(root.parents) >= 2 else root.parent) / "FX_OUTPUTS"


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


def ensure_parent(path: Path) -> None:
    lp(path.parent).mkdir(parents=True, exist_ok=True)


def write_text(path: Path, text: str) -> None:
    ensure_parent(path)
    lp(path).write_text(text, encoding="utf-8")


def write_json(path: Path, obj: dict[str, Any]) -> None:
    write_text(path, json.dumps(obj, ensure_ascii=False, indent=2))


def write_csv(path: Path, df: pd.DataFrame) -> None:
    ensure_parent(path)
    df.to_csv(lp(path), index=False, encoding="utf-8-sig")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(lp(path).read_text(encoding="utf-8"))


def read_csv(path: Path) -> pd.DataFrame:
    last: Exception | None = None
    for enc in ("utf-8-sig", "utf-8", "cp932"):
        try:
            return pd.read_csv(lp(path), encoding=enc, keep_default_na=False)
        except Exception as exc:
            last = exc
    raise RuntimeError(f"CSV read failed: {path}: {last}")


def truthy(v: Any) -> bool:
    if isinstance(v, bool):
        return v
    return str(v).strip().lower() in {"1", "true", "yes", "y"}


def stop_count(df: pd.DataFrame) -> int:
    if "status" not in df.columns:
        return 999
    return int((df["status"].astype(str) == "STOP").sum())


def check_row(cid: str, name: str, observed: Any, expected: Any, ok: bool) -> dict[str, Any]:
    return {"check_id": cid, "check": name, "observed": observed, "expected": expected, "status": "PASS" if ok else "STOP"}


def md_table(df: pd.DataFrame, limit: int = 80) -> str:
    if df.empty:
        return "_No rows._"
    cols = list(df.columns)
    rows = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for _, row in df.head(limit).iterrows():
        rows.append("| " + " | ".join(str(row[c]).replace("|", "\\|").replace("\n", " ") for c in cols) + " |")
    return "\n".join(rows)


def forbidden_gate_count(df: pd.DataFrame, allowed_col: str) -> int:
    if {"next_step", allowed_col}.issubset(df.columns):
        return int(df[df["next_step"].astype(str).isin(FORBIDDEN_GATES)][allowed_col].map(truthy).sum())
    return 999


def forbidden_summary_count(s: dict[str, Any]) -> int:
    n = sum(int(bool(s.get(k, False))) for k in FORBIDDEN_FLAGS)
    ext = s.get("external_actions", {})
    n += sum(int(bool(v)) for v in ext.values()) if isinstance(ext, dict) else 1
    return n


def reference_summaries() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    base = fx_outputs()
    for name in REF_DIRS:
        d = base / name
        if not lp(d).exists():
            continue
        for f in d.glob("*summary.json"):
            try:
                out.append(read_json(f))
                break
            except Exception:
                pass
    return out


def next_gates(success: bool) -> pd.DataFrame:
    return pd.DataFrame([
        ["18AG", "TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_READINESS_PACKAGE_BLOCKER_REVIEW_AUDIT_ONLY", "Review blockers after package reconciliation only.", bool(success)],
        ["SOURCE_IDENTITY_FINALIZATION", "TIER2_SOURCE_IDENTITY_FINALIZATION", "Blocked after 18AF.", False],
        ["SOURCE_RECOVERY", "TIER2_SOURCE_IDENTITY_RECOVERY_EXECUTION", "Blocked after 18AF.", False],
        ["LIVE", "MEDIUM_FULL_SET_LIVE_EVALUATOR", "Blocked.", False],
        ["FINAL_SIGNAL", "MEDIUM_FINAL_SIGNAL", "Blocked.", False],
    ], columns=["next_step", "name", "purpose", "allowed_after_18af_success"])


def safety_matrix(success: bool) -> pd.DataFrame:
    return pd.DataFrame([
        ["audit_only", True, True, "PASS"],
        ["package_reconciliation_only", True, True, "PASS"],
        ["decision_collected", False, False, "PASS"],
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
        ["next_gate_18ag_only_after_success", bool(success), bool(success), "PASS"],
    ], columns=["safety_item", "observed", "expected", "status"])


def stop_conditions() -> pd.DataFrame:
    return pd.DataFrame([
        ["18AF-S001", "required inputs missing", "STOP"],
        ["18AF-S002", "18AE status not passed", "STOP"],
        ["18AF-S003", "decision collected or approval already made", "STOP"],
        ["18AF-S004", "upstream STOP rows present", "STOP"],
        ["18AF-S005", "package index reconciliation failed", "STOP"],
        ["18AF-S006", "blocker summary reconciliation failed", "STOP"],
        ["18AF-S007", "forbidden gate allowed", "STOP"],
        ["18AF-S008", "forbidden safety flag true", "STOP"],
    ], columns=["stop_id", "condition", "action"])


def main() -> int:
    base = fx_outputs()
    out = base / OUT_DIR
    lp(out).mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()
    p18ac, p18ad, p18ae = base / IN18AC, base / IN18AD, base / IN18AE
    inputs = {
        "summary_18ae": p18ae / "gold_v2_18ae_tier2_source_identity_human_decision_intake_readiness_package_content_audit_summary.json",
        "checks_18ae": p18ae / "gold_v2_18ae_content_checks.csv",
        "index_content_18ae": p18ae / "gold_v2_18ae_package_index_content_audit.csv",
        "blocker_content_18ae": p18ae / "gold_v2_18ae_blocker_summary_content_audit.csv",
        "gates_18ae": p18ae / "gold_v2_18ae_required_next_gates.csv",
        "safety_18ae": p18ae / "gold_v2_18ae_safety_matrix.csv",
        "report_18ae": p18ae / "GOLD_V2_18AE_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_READINESS_PACKAGE_CONTENT_AUDIT_ONLY_REPORT.md",
        "summary_18ad": p18ad / "gold_v2_18ad_tier2_source_identity_human_decision_intake_readiness_package_load_smoke_summary.json",
        "index_load_18ad": p18ad / "gold_v2_18ad_package_index_load_audit.csv",
        "blocker_load_18ad": p18ad / "gold_v2_18ad_blocker_summary_load_audit.csv",
        "summary_18ac": p18ac / "gold_v2_18ac_tier2_source_identity_human_decision_intake_readiness_package_summary.json",
        "index_18ac": p18ac / "gold_v2_18ac_evidence_package_index.csv",
        "blocker_18ac": p18ac / "gold_v2_18ac_blocker_package_summary.csv",
    }
    input_audit = pd.DataFrame([{"role": k, "path": str(v), "required": True, "exists": lp(v).exists()} for k, v in inputs.items()])
    write_csv(out / "gold_v2_18af_input_audit.csv", input_audit)
    if not bool(input_audit["exists"].all()):
        checks = pd.DataFrame([check_row("18AF-C000", "required inputs exist", False, True, False)])
        sm = safety_matrix(False)
        write_csv(out / "gold_v2_18af_reconciliation_checks.csv", checks)
        write_csv(out / "gold_v2_18af_safety_matrix.csv", sm)
        summary = {"created_utc": now, "step": STEP, "status": "18AF_STOP_MISSING_INPUTS", "audit_only": True, "package_reconciliation_passed": False, "decision_collected": False, "decision_made": False, "approval_granted": False, "total_stop_rows": 1, "next_recommended_step": "STOP_REVIEW_18AF_INPUTS"}
        write_json(out / "gold_v2_18af_tier2_source_identity_human_decision_intake_readiness_package_reconciliation_summary.json", summary)
        write_text(out / REPORT, "# GOLD V2 18AF readiness package reconciliation audit-only report\n\nStatus: `18AF_STOP_MISSING_INPUTS`\n")
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 2

    s18ae, s18ad, s18ac = read_json(inputs["summary_18ae"]), read_json(inputs["summary_18ad"]), read_json(inputs["summary_18ac"])
    checks18ae = read_csv(inputs["checks_18ae"])
    index_content = read_csv(inputs["index_content_18ae"])
    blocker_content = read_csv(inputs["blocker_content_18ae"])
    gates18ae = read_csv(inputs["gates_18ae"])
    safe18ae = read_csv(inputs["safety_18ae"])
    index_load = read_csv(inputs["index_load_18ad"])
    blocker_load = read_csv(inputs["blocker_load_18ad"])
    index_ac = read_csv(inputs["index_18ac"])
    blocker_ac = read_csv(inputs["blocker_18ac"])

    ac_index_count = int(len(index_ac))
    ad_index_pass = int((index_load.get("status", pd.Series(dtype=str)).astype(str) == "PASS").sum())
    index_content_stop = stop_count(index_content)
    index_recon = pd.DataFrame([
        check_row("18AF-I001", "18AC package index rows vs 18AD pass rows", ac_index_count, ad_index_pass, ac_index_count == ad_index_pass),
        check_row("18AF-I002", "18AE package index content STOP rows", index_content_stop, 0, index_content_stop == 0),
    ])
    write_csv(out / "gold_v2_18af_package_index_reconciliation.csv", index_recon)

    ac_items = {str(r.get("item", "")): str(r.get("observed", "")) for _, r in blocker_ac.iterrows()}
    load_items = {str(r.get("item", "")): str(r.get("observed", "")) for _, r in blocker_load.iterrows()}
    blocker_content_stop = stop_count(blocker_content)
    key_items = ["blocker_rows", "must_remain_blocked_false_rows", "script_can_clear_true_rows", "template_decision_value"]
    item_mismatch = sum(1 for k in key_items if ac_items.get(k) != load_items.get(k))
    blocker_recon = pd.DataFrame([
        check_row("18AF-B001", "18AC vs 18AD blocker summary mismatches", item_mismatch, 0, item_mismatch == 0),
        check_row("18AF-B002", "18AE blocker content STOP rows", blocker_content_stop, 0, blocker_content_stop == 0),
    ])
    write_csv(out / "gold_v2_18af_blocker_summary_reconciliation.csv", blocker_recon)

    no_decision = all(s.get("decision_collected", False) is False and s.get("decision_made") is False and s.get("approval_granted") is False for s in [s18ac, s18ad, s18ae])
    upstream_stop = stop_count(checks18ae) + stop_count(safe18ae)
    forbidden_gates = forbidden_gate_count(gates18ae, "allowed_after_18ae_success")
    forbidden_flags = sum(forbidden_summary_count(s) for s in reference_summaries())
    checks = pd.DataFrame([
        check_row("18AF-C001", "18AE status", s18ae.get("status"), EXPECTED_18AE, s18ae.get("status") == EXPECTED_18AE),
        check_row("18AF-C002", "18AE package_content_audit_passed", s18ae.get("package_content_audit_passed"), True, bool(s18ae.get("package_content_audit_passed", False))),
        check_row("18AF-C003", "18AE total_stop_rows", s18ae.get("total_stop_rows"), 0, s18ae.get("total_stop_rows") == 0),
        check_row("18AF-C004", "18AC/18AD/18AE no decision/approval", no_decision, True, no_decision),
        check_row("18AF-C005", "upstream STOP rows", upstream_stop, 0, upstream_stop == 0),
        check_row("18AF-C006", "package index reconciliation STOP rows", stop_count(index_recon), 0, stop_count(index_recon) == 0),
        check_row("18AF-C007", "blocker summary reconciliation STOP rows", stop_count(blocker_recon), 0, stop_count(blocker_recon) == 0),
        check_row("18AF-C008", "forbidden gates allowed", forbidden_gates, 0, forbidden_gates == 0),
        check_row("18AF-C009", "forbidden summary flags true", forbidden_flags, 0, forbidden_flags == 0),
    ])
    total_stop = stop_count(checks)
    success = total_stop == 0
    status = SUCCESS if success else "18AF_STOP_REVIEW_PACKAGE_RECONCILIATION_OUTPUTS"
    sm = safety_matrix(success)
    gates = next_gates(success)
    write_csv(out / "gold_v2_18af_reconciliation_checks.csv", checks)
    write_csv(out / "gold_v2_18af_required_next_gates.csv", gates)
    write_csv(out / "gold_v2_18af_stop_conditions.csv", stop_conditions())
    write_csv(out / "gold_v2_18af_safety_matrix.csv", sm)
    summary = {
        "created_utc": now,
        "step": STEP,
        "status": status,
        "audit_only": True,
        "package_reconciliation_passed": success,
        "decision_collected": False,
        "decision_made": False,
        "approval_granted": False,
        "upstream_18ae_status": s18ae.get("status"),
        "package_index_rows": ac_index_count,
        "total_stop_rows": int(total_stop),
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
        "next_recommended_step": "18AG_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_READINESS_PACKAGE_BLOCKER_REVIEW_AUDIT_ONLY" if success else "STOP_REVIEW_18AF_OUTPUTS",
    }
    write_json(out / "gold_v2_18af_tier2_source_identity_human_decision_intake_readiness_package_reconciliation_summary.json", summary)
    report = [
        "# GOLD V2 18AF TIER2 source identity human decision intake readiness package reconciliation audit-only report",
        "",
        f"Created UTC: {now}",
        f"Status: `{status}`",
        "",
        "## Final decision",
        "- 18AF reconciled 18AC/18AD/18AE readiness package evidence only.",
        "- No decision was collected and no approval was made by this script.",
        "- Source recovery, identity finalization/recovery, OHLC replay, live/final paths, Discord, MT5, AI API, live hook, and NO_SIGNAL Discord remain disabled.",
        "",
        "## Reconciliation checks",
        md_table(checks),
        "",
        "## Package index reconciliation",
        md_table(index_recon),
        "",
        "## Blocker summary reconciliation",
        md_table(blocker_recon),
        "",
        "## Next gates",
        md_table(gates),
        "",
        "## Safety",
        md_table(sm),
    ]
    write_text(out / REPORT, "\n".join(report))
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if success else 2


if __name__ == "__main__":
    raise SystemExit(main())
