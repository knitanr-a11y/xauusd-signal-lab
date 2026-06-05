#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

STEP = "18O_TIER2_SOURCE_IDENTITY_DRY_RUN_BLOCKER_REVIEW_AUDIT_ONLY"
OUT_DIR = "gold_v2_18o_tier2_source_identity_dry_run_blocker_review_audit_only"
IN18N = "gold_v2_18n_tier2_source_identity_dry_run_reconciliation_audit_only"
IN18M = "gold_v2_18m_tier2_source_identity_dry_run_content_audit_only"
IN18L = "gold_v2_18l_tier2_source_identity_dry_run_load_smoke_audit_only"
IN18K = "gold_v2_18k_tier2_source_identity_dry_run_implementation_audit_only"
REPORT = "GOLD_V2_18O_TIER2_SOURCE_IDENTITY_DRY_RUN_BLOCKER_REVIEW_AUDIT_ONLY_REPORT.md"
SUCCESS = "TIER2_SOURCE_IDENTITY_DRY_RUN_BLOCKER_REVIEW_COMPLETED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"
EXPECTED_18N = "TIER2_SOURCE_IDENTITY_DRY_RUN_RECONCILIATION_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"
REQUIRED_BLOCKER_IDS = ["18N-B001", "18N-B002", "18N-B003", "18N-B004", "18N-B005", "18N-B006", "18N-B007"]
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
        ["blocker_review_only", True, True, "PASS"],
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
        ["next_gate_18p_only_after_success", bool(success), bool(success), "PASS"],
    ], columns=["safety_item", "observed", "expected", "status"])


def next_gates(success: bool) -> pd.DataFrame:
    return pd.DataFrame([
        ["18P", "TIER2_SOURCE_IDENTITY_DRY_RUN_READINESS_PACKAGE_AUDIT_ONLY", "Package audit evidence and open blockers for human review; still not source-of-truth.", bool(success)],
        ["SOURCE_IDENTITY_FINALIZATION", "TIER2_SOURCE_IDENTITY_FINALIZATION", "Blocked after 18O.", False],
        ["SOURCE_RECOVERY", "TIER2_SOURCE_IDENTITY_RECOVERY_EXECUTION", "Blocked after 18O.", False],
        ["LIVE", "MEDIUM_FULL_SET_LIVE_EVALUATOR", "Blocked.", False],
        ["FINAL_SIGNAL", "MEDIUM_FINAL_SIGNAL", "Blocked.", False],
    ], columns=["next_step", "name", "purpose", "allowed_after_18o_success"])


def stop_conditions() -> pd.DataFrame:
    return pd.DataFrame([
        ["18O-S001", "required inputs missing", "STOP"],
        ["18O-S002", "18N status not passed", "STOP"],
        ["18O-S003", "any upstream STOP row present", "STOP"],
        ["18O-S004", "required blocker missing", "STOP"],
        ["18O-S005", "forbidden gate allowed", "STOP"],
        ["18O-S006", "forbidden safety flag true", "STOP"],
        ["18O-S007", "ledger or output marked source-of-truth", "STOP"],
    ], columns=["stop_id", "condition", "action"])


def main() -> int:
    out = fx() / OUT_DIR
    lp(out).mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()
    p18n = fx() / IN18N
    p18m = fx() / IN18M
    p18l = fx() / IN18L
    p18k = fx() / IN18K
    inputs = {
        "summary_18n": p18n / "gold_v2_18n_tier2_source_identity_dry_run_reconciliation_summary.json",
        "input_audit_18n": p18n / "gold_v2_18n_input_audit.csv",
        "reconciliation_checks_18n": p18n / "gold_v2_18n_reconciliation_checks.csv",
        "distribution_reconciliation_18n": p18n / "gold_v2_18n_distribution_reconciliation.csv",
        "row_count_reconciliation_18n": p18n / "gold_v2_18n_row_count_reconciliation.csv",
        "upstream_stop_audit_18n": p18n / "gold_v2_18n_upstream_stop_audit.csv",
        "next_gates_18n": p18n / "gold_v2_18n_required_next_gates.csv",
        "blockers_18n": p18n / "gold_v2_18n_blockers.csv",
        "safety_18n": p18n / "gold_v2_18n_safety_matrix.csv",
        "report_18n": p18n / "GOLD_V2_18N_TIER2_SOURCE_IDENTITY_DRY_RUN_RECONCILIATION_AUDIT_ONLY_REPORT.md",
        "summary_18m": p18m / "gold_v2_18m_tier2_source_identity_dry_run_content_summary.json",
        "summary_18l": p18l / "gold_v2_18l_tier2_source_identity_dry_run_load_smoke_summary.json",
        "summary_18k": p18k / "gold_v2_18k_tier2_source_identity_dry_run_implementation_summary.json",
    }
    input_audit = pd.DataFrame([{"role": k, "path": str(v), "required": True, "exists": lp(v).exists()} for k, v in inputs.items()])
    wcsv(input_audit, out / "gold_v2_18o_input_audit.csv")
    if not input_audit["exists"].all():
        status = "18O_STOP_MISSING_INPUTS"
        checks = pd.DataFrame([ck("18O-C000", "required inputs exist", False, True, False)])
        wcsv(checks, out / "gold_v2_18o_blocker_review_checks.csv")
        wcsv(safety(False), out / "gold_v2_18o_safety_matrix.csv")
        summary = {"created_utc": now, "step": STEP, "status": status, "audit_only": True, "blocker_review_completed": False, "next_recommended_step": "STOP_REVIEW_18O_INPUTS"}
        wjson(out / "gold_v2_18o_tier2_source_identity_dry_run_blocker_review_summary.json", summary)
        wtxt(out / REPORT, "# GOLD V2 18O TIER2 source identity dry-run blocker review audit-only report\n\nStatus: `18O_STOP_MISSING_INPUTS`\n")
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 2
    s18n = rjson(inputs["summary_18n"])
    s18m = rjson(inputs["summary_18m"])
    s18l = rjson(inputs["summary_18l"])
    s18k = rjson(inputs["summary_18k"])
    rec = rcsv(inputs["reconciliation_checks_18n"])
    dist = rcsv(inputs["distribution_reconciliation_18n"])
    rows = rcsv(inputs["row_count_reconciliation_18n"])
    upstream = rcsv(inputs["upstream_stop_audit_18n"])
    gates = rcsv(inputs["next_gates_18n"])
    blockers = rcsv(inputs["blockers_18n"])
    safe18n = rcsv(inputs["safety_18n"])
    _ = lp(inputs["report_18n"]).read_text(encoding="utf-8")

    upstream_stop = sum(stop_count(df) for df in [rec, dist, rows, upstream, safe18n])
    blocker_ids = set(blockers["blocker_id"].astype(str)) if "blocker_id" in blockers.columns else set()
    missing_blockers = [b for b in REQUIRED_BLOCKER_IDS if b not in blocker_ids]
    forbidden_gate_true = 999
    if {"next_step", "allowed_after_18n_success"}.issubset(gates.columns):
        forbidden = gates[gates["next_step"].astype(str).isin(FORBIDDEN_GATES)]
        forbidden_gate_true = int(forbidden["allowed_after_18n_success"].map(truthy).sum())
    summary_forbidden_true = forbidden_summary_true(s18n) + forbidden_summary_true(s18m) + forbidden_summary_true(s18l) + forbidden_summary_true(s18k)
    checks = pd.DataFrame([
        ck("18O-C001", "18N status", s18n.get("status"), EXPECTED_18N, s18n.get("status") == EXPECTED_18N),
        ck("18O-C002", "18N reconciliation_passed", s18n.get("reconciliation_passed"), True, bool(s18n.get("reconciliation_passed", False))),
        ck("18O-C003", "18N total_stop_rows", s18n.get("total_stop_rows"), 0, s18n.get("total_stop_rows") == 0),
        ck("18O-C004", "18N upstream STOP rows", upstream_stop, 0, upstream_stop == 0),
        ck("18O-C005", "required blockers missing", len(missing_blockers), 0, len(missing_blockers) == 0),
        ck("18O-C006", "forbidden gates allowed", forbidden_gate_true, 0, forbidden_gate_true == 0),
        ck("18O-C007", "summary forbidden flags true across 18K-18N", summary_forbidden_true, 0, summary_forbidden_true == 0),
    ])
    blocker_inventory = blockers.copy()
    blocker_inventory["still_blocked_after_18o"] = True
    blocker_inventory["resolved_by_18o"] = False
    evidence_inventory = pd.DataFrame([
        ["18K", s18k.get("status"), s18k.get("candidate_identity_rows"), s18k.get("total_stop_rows", s18k.get("implementation_checks_stop_rows", 0)), "READ"],
        ["18L", s18l.get("status"), s18l.get("candidate_identity_rows"), s18l.get("total_stop_rows", 0), "READ"],
        ["18M", s18m.get("status"), s18m.get("candidate_identity_rows"), s18m.get("total_stop_rows", 0), "READ"],
        ["18N", s18n.get("status"), s18n.get("candidate_identity_rows"), s18n.get("total_stop_rows", 0), "READ"],
    ], columns=["step", "status", "candidate_identity_rows", "stop_rows", "evidence_status"])
    total_stop = stop_count(checks)
    success = total_stop == 0
    status = SUCCESS if success else "18O_STOP_REVIEW_BLOCKER_OUTPUTS"
    sm = safety(success)
    for name, df in [
        ("gold_v2_18o_blocker_review_checks.csv", checks),
        ("gold_v2_18o_blocker_inventory.csv", blocker_inventory),
        ("gold_v2_18o_evidence_inventory.csv", evidence_inventory),
        ("gold_v2_18o_required_next_gates.csv", next_gates(success)),
        ("gold_v2_18o_stop_conditions.csv", stop_conditions()),
        ("gold_v2_18o_safety_matrix.csv", sm),
    ]:
        wcsv(df, out / name)
    summary = {
        "created_utc": now,
        "step": STEP,
        "status": status,
        "audit_only": True,
        "blocker_review_completed": success,
        "upstream_18n_status": s18n.get("status"),
        "candidate_identity_rows": s18n.get("candidate_identity_rows"),
        "expected_candidate_identity_rows": s18n.get("expected_candidate_identity_rows"),
        "required_blockers": len(REQUIRED_BLOCKER_IDS),
        "missing_required_blockers": len(missing_blockers),
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
        "next_recommended_step": "18P_TIER2_SOURCE_IDENTITY_DRY_RUN_READINESS_PACKAGE_AUDIT_ONLY" if success else "STOP_REVIEW_18O_OUTPUTS",
    }
    wjson(out / "gold_v2_18o_tier2_source_identity_dry_run_blocker_review_summary.json", summary)
    report = [
        "# GOLD V2 18O TIER2 source identity dry-run blocker review audit-only report",
        "",
        f"Created UTC: {now}",
        f"Status: `{status}`",
        "",
        "## Final decision",
        "- 18O reviewed remaining blockers after 18N reconciliation.",
        "- No blocker was resolved by source recovery or identity finalization.",
        "- Source recovery, identity finalization/recovery, OHLC replay, live/final paths, Discord, MT5, AI API, live hook, and NO_SIGNAL Discord remain disabled.",
        "",
        "## Blocker review checks",
        mdtable(checks),
        "",
        "## Blocker inventory",
        mdtable(blocker_inventory),
        "",
        "## Evidence inventory",
        mdtable(evidence_inventory),
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
