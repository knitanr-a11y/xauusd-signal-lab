#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

STEP = "18P_TIER2_SOURCE_IDENTITY_DRY_RUN_READINESS_PACKAGE_AUDIT_ONLY"
OUT_DIR = "gold_v2_18p_tier2_source_identity_dry_run_readiness_package_audit_only"
IN18O = "gold_v2_18o_tier2_source_identity_dry_run_blocker_review_audit_only"
IN18N = "gold_v2_18n_tier2_source_identity_dry_run_reconciliation_audit_only"
IN18M = "gold_v2_18m_tier2_source_identity_dry_run_content_audit_only"
IN18L = "gold_v2_18l_tier2_source_identity_dry_run_load_smoke_audit_only"
IN18K = "gold_v2_18k_tier2_source_identity_dry_run_implementation_audit_only"
REPORT = "GOLD_V2_18P_TIER2_SOURCE_IDENTITY_DRY_RUN_READINESS_PACKAGE_AUDIT_ONLY_REPORT.md"
SUCCESS = "TIER2_SOURCE_IDENTITY_DRY_RUN_READINESS_PACKAGE_PREPARED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"
EXPECTED_18O = "TIER2_SOURCE_IDENTITY_DRY_RUN_BLOCKER_REVIEW_COMPLETED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"
REQUIRED_EVIDENCE_STEPS = ["18K", "18L", "18M", "18N"]
REQUIRED_BLOCKER_COUNT = 7
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


def safety(success: bool) -> pd.DataFrame:
    return pd.DataFrame([
        ["audit_only", True, True, "PASS"],
        ["readiness_package_only", True, True, "PASS"],
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
        ["next_gate_18q_only_after_success", bool(success), bool(success), "PASS"],
    ], columns=["safety_item", "observed", "expected", "status"])


def next_gates(success: bool) -> pd.DataFrame:
    return pd.DataFrame([
        ["18Q", "TIER2_SOURCE_IDENTITY_HUMAN_REVIEW_DECISION_PLANNING_AUDIT_ONLY", "Plan human decision checklist only; still not source-of-truth.", bool(success)],
        ["SOURCE_IDENTITY_FINALIZATION", "TIER2_SOURCE_IDENTITY_FINALIZATION", "Blocked after 18P.", False],
        ["SOURCE_RECOVERY", "TIER2_SOURCE_IDENTITY_RECOVERY_EXECUTION", "Blocked after 18P.", False],
        ["LIVE", "MEDIUM_FULL_SET_LIVE_EVALUATOR", "Blocked.", False],
        ["FINAL_SIGNAL", "MEDIUM_FINAL_SIGNAL", "Blocked.", False],
    ], columns=["next_step", "name", "purpose", "allowed_after_18p_success"])


def stop_conditions() -> pd.DataFrame:
    return pd.DataFrame([
        ["18P-S001", "required inputs missing", "STOP"],
        ["18P-S002", "18O status not passed", "STOP"],
        ["18P-S003", "any upstream STOP row present", "STOP"],
        ["18P-S004", "evidence inventory incomplete", "STOP"],
        ["18P-S005", "required blockers missing", "STOP"],
        ["18P-S006", "forbidden gate allowed", "STOP"],
        ["18P-S007", "forbidden safety flag true", "STOP"],
        ["18P-S008", "readiness package treated as approval", "STOP"],
    ], columns=["stop_id", "condition", "action"])


def main() -> int:
    out = fx() / OUT_DIR
    lp(out).mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()
    p18o = fx() / IN18O
    p18n = fx() / IN18N
    p18m = fx() / IN18M
    p18l = fx() / IN18L
    p18k = fx() / IN18K
    inputs = {
        "summary_18o": p18o / "gold_v2_18o_tier2_source_identity_dry_run_blocker_review_summary.json",
        "input_audit_18o": p18o / "gold_v2_18o_input_audit.csv",
        "blocker_review_checks_18o": p18o / "gold_v2_18o_blocker_review_checks.csv",
        "blocker_inventory_18o": p18o / "gold_v2_18o_blocker_inventory.csv",
        "evidence_inventory_18o": p18o / "gold_v2_18o_evidence_inventory.csv",
        "next_gates_18o": p18o / "gold_v2_18o_required_next_gates.csv",
        "stop_conditions_18o": p18o / "gold_v2_18o_stop_conditions.csv",
        "safety_18o": p18o / "gold_v2_18o_safety_matrix.csv",
        "report_18o": p18o / "GOLD_V2_18O_TIER2_SOURCE_IDENTITY_DRY_RUN_BLOCKER_REVIEW_AUDIT_ONLY_REPORT.md",
        "summary_18n": p18n / "gold_v2_18n_tier2_source_identity_dry_run_reconciliation_summary.json",
        "summary_18m": p18m / "gold_v2_18m_tier2_source_identity_dry_run_content_summary.json",
        "summary_18l": p18l / "gold_v2_18l_tier2_source_identity_dry_run_load_smoke_summary.json",
        "summary_18k": p18k / "gold_v2_18k_tier2_source_identity_dry_run_implementation_summary.json",
    }
    input_audit = pd.DataFrame([{"role": k, "path": str(v), "required": True, "exists": lp(v).exists()} for k, v in inputs.items()])
    wcsv(input_audit, out / "gold_v2_18p_input_audit.csv")
    if not input_audit["exists"].all():
        status = "18P_STOP_MISSING_INPUTS"
        checks = pd.DataFrame([ck("18P-C000", "required inputs exist", False, True, False)])
        wcsv(checks, out / "gold_v2_18p_readiness_checks.csv")
        wcsv(safety(False), out / "gold_v2_18p_safety_matrix.csv")
        summary = {"created_utc": now, "step": STEP, "status": status, "audit_only": True, "readiness_package_prepared": False, "next_recommended_step": "STOP_REVIEW_18P_INPUTS"}
        wjson(out / "gold_v2_18p_tier2_source_identity_dry_run_readiness_package_summary.json", summary)
        wtxt(out / REPORT, "# GOLD V2 18P TIER2 source identity dry-run readiness package audit-only report\n\nStatus: `18P_STOP_MISSING_INPUTS`\n")
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 2
    s18o = rjson(inputs["summary_18o"])
    summaries = {
        "18K": rjson(inputs["summary_18k"]),
        "18L": rjson(inputs["summary_18l"]),
        "18M": rjson(inputs["summary_18m"]),
        "18N": rjson(inputs["summary_18n"]),
        "18O": s18o,
    }
    checks18o = rcsv(inputs["blocker_review_checks_18o"])
    blockers18o = rcsv(inputs["blocker_inventory_18o"])
    evidence18o = rcsv(inputs["evidence_inventory_18o"])
    gates18o = rcsv(inputs["next_gates_18o"])
    safety18o = rcsv(inputs["safety_18o"])
    _ = lp(inputs["report_18o"]).read_text(encoding="utf-8")

    evidence_steps = set(evidence18o["step"].astype(str)) if "step" in evidence18o.columns else set()
    missing_evidence = [s for s in REQUIRED_EVIDENCE_STEPS if s not in evidence_steps]
    blocker_count = len(blockers18o)
    missing_blocker_count = max(0, REQUIRED_BLOCKER_COUNT - blocker_count)
    gates_forbidden_true = 999
    if {"next_step", "allowed_after_18o_success"}.issubset(gates18o.columns):
        forbidden = gates18o[gates18o["next_step"].astype(str).isin(FORBIDDEN_GATES)]
        gates_forbidden_true = int(forbidden["allowed_after_18o_success"].map(truthy).sum())
    forbidden_summary_total = sum(forbidden_summary_true(v) for v in summaries.values())
    upstream_stop = stop_count(checks18o) + stop_count(safety18o)
    readiness_checks = pd.DataFrame([
        ck("18P-C001", "18O status", s18o.get("status"), EXPECTED_18O, s18o.get("status") == EXPECTED_18O),
        ck("18P-C002", "18O blocker_review_completed", s18o.get("blocker_review_completed"), True, bool(s18o.get("blocker_review_completed", False))),
        ck("18P-C003", "18O total_stop_rows", s18o.get("total_stop_rows"), 0, s18o.get("total_stop_rows") == 0),
        ck("18P-C004", "18O upstream STOP rows", upstream_stop, 0, upstream_stop == 0),
        ck("18P-C005", "missing evidence steps", len(missing_evidence), 0, len(missing_evidence) == 0),
        ck("18P-C006", "required blocker missing count", missing_blocker_count, 0, missing_blocker_count == 0),
        ck("18P-C007", "forbidden gates allowed", gates_forbidden_true, 0, gates_forbidden_true == 0),
        ck("18P-C008", "forbidden summary flags true across 18K-18O", forbidden_summary_total, 0, forbidden_summary_total == 0),
    ])
    evidence_manifest = pd.DataFrame([
        [step, summaries[step].get("status"), summaries[step].get("candidate_identity_rows"), summaries[step].get("total_stop_rows", summaries[step].get("implementation_checks_stop_rows", 0)), "READY_FOR_HUMAN_REVIEW_PACKAGE"]
        for step in ["18K", "18L", "18M", "18N", "18O"]
    ], columns=["step", "status", "candidate_identity_rows", "stop_rows", "package_status"])
    open_blockers = blockers18o.copy()
    if not open_blockers.empty:
        open_blockers["human_review_required"] = True
        open_blockers["resolved_by_18p"] = False
    human_packet = pd.DataFrame([
        ["HP-001", "Review 18K-18O summaries and reports", "REQUIRED", "AUDIT_ONLY"],
        ["HP-002", "Confirm dry-run candidate ledger is not source-of-truth", "REQUIRED", "BLOCKING"],
        ["HP-003", "Confirm source recovery execution remains blocked", "REQUIRED", "BLOCKING"],
        ["HP-004", "Confirm source identity finalization remains blocked", "REQUIRED", "BLOCKING"],
        ["HP-005", "Confirm live/final/Discord/MT5/AI/live hook remain blocked", "REQUIRED", "BLOCKING"],
        ["HP-006", "Decide what evidence is needed before any future finalization planning", "REQUIRED", "PLANNING_ONLY"],
    ], columns=["packet_item_id", "review_item", "required", "scope"])
    total_stop = stop_count(readiness_checks)
    success = total_stop == 0
    status = SUCCESS if success else "18P_STOP_REVIEW_READINESS_PACKAGE_OUTPUTS"
    sm = safety(success)
    for name, df in [
        ("gold_v2_18p_readiness_checks.csv", readiness_checks),
        ("gold_v2_18p_evidence_manifest.csv", evidence_manifest),
        ("gold_v2_18p_open_blockers_for_human_review.csv", open_blockers),
        ("gold_v2_18p_human_review_packet.csv", human_packet),
        ("gold_v2_18p_required_next_gates.csv", next_gates(success)),
        ("gold_v2_18p_stop_conditions.csv", stop_conditions()),
        ("gold_v2_18p_safety_matrix.csv", sm),
    ]:
        wcsv(df, out / name)
    summary = {
        "created_utc": now,
        "step": STEP,
        "status": status,
        "audit_only": True,
        "readiness_package_prepared": success,
        "upstream_18o_status": s18o.get("status"),
        "evidence_steps_packaged": list(evidence_manifest["step"].astype(str)),
        "open_blockers_for_human_review": int(len(open_blockers)),
        "human_review_packet_items": int(len(human_packet)),
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
        "next_recommended_step": "18Q_TIER2_SOURCE_IDENTITY_HUMAN_REVIEW_DECISION_PLANNING_AUDIT_ONLY" if success else "STOP_REVIEW_18P_OUTPUTS",
    }
    wjson(out / "gold_v2_18p_tier2_source_identity_dry_run_readiness_package_summary.json", summary)
    report = [
        "# GOLD V2 18P TIER2 source identity dry-run readiness package audit-only report",
        "",
        f"Created UTC: {now}",
        f"Status: `{status}`",
        "",
        "## Final decision",
        "- 18P prepared a readiness package for human review only.",
        "- No blocker was resolved and no ledger was promoted to source-of-truth.",
        "- Source recovery, identity finalization/recovery, OHLC replay, live/final paths, Discord, MT5, AI API, live hook, and NO_SIGNAL Discord remain disabled.",
        "",
        "## Readiness checks",
        mdtable(readiness_checks),
        "",
        "## Evidence manifest",
        mdtable(evidence_manifest),
        "",
        "## Open blockers for human review",
        mdtable(open_blockers),
        "",
        "## Human review packet",
        mdtable(human_packet),
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
