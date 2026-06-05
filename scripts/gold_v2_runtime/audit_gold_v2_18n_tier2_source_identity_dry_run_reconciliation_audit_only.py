#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

STEP = "18N_TIER2_SOURCE_IDENTITY_DRY_RUN_RECONCILIATION_AUDIT_ONLY"
OUT_DIR = "gold_v2_18n_tier2_source_identity_dry_run_reconciliation_audit_only"
IN18M = "gold_v2_18m_tier2_source_identity_dry_run_content_audit_only"
IN18L = "gold_v2_18l_tier2_source_identity_dry_run_load_smoke_audit_only"
IN18K = "gold_v2_18k_tier2_source_identity_dry_run_implementation_audit_only"
REPORT = "GOLD_V2_18N_TIER2_SOURCE_IDENTITY_DRY_RUN_RECONCILIATION_AUDIT_ONLY_REPORT.md"
SUCCESS = "TIER2_SOURCE_IDENTITY_DRY_RUN_RECONCILIATION_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"
EXPECTED_18M = "TIER2_SOURCE_IDENTITY_DRY_RUN_CONTENT_AUDIT_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"
EXPECTED_ROWS = 104
EXPECTED_ARTIFACTS = 5
FALSE_FLAGS = [
    "source_recovery_executed",
    "source_identity_finalized",
    "source_identity_recovered",
    "live_or_final_implementation_allowed",
    "oh_lc_replay_allowed",
    "discord_send_allowed",
    "mt5_order_allowed",
    "ai_api_allowed",
    "live_hook_allowed",
    "no_signal_discord_notified",
]
DIST_FILES = {
    "artifact_role": "gold_v2_18m_distribution_by_artifact_role.csv",
    "component": "gold_v2_18m_distribution_by_component.csv",
    "direction": "gold_v2_18m_distribution_by_direction.csv",
    "outcome": "gold_v2_18m_distribution_by_outcome.csv",
    "source_status": "gold_v2_18m_distribution_by_source_status.csv",
}


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


def distribution(df: pd.DataFrame, col: str) -> pd.DataFrame:
    if col not in df.columns:
        return pd.DataFrame(columns=[col, "count"])
    return df.groupby(col, dropna=False).size().reset_index(name="count").sort_values(["count", col], ascending=[False, True]).reset_index(drop=True)


def norm_dist(df: pd.DataFrame, key_col: str) -> pd.DataFrame:
    if key_col not in df.columns or "count" not in df.columns:
        return pd.DataFrame(columns=[key_col, "count"])
    d = df[[key_col, "count"]].copy()
    d[key_col] = d[key_col].astype(str)
    d["count"] = pd.to_numeric(d["count"], errors="coerce").fillna(-1).astype(int)
    return d.sort_values([key_col, "count"]).reset_index(drop=True)


def safety(success: bool) -> pd.DataFrame:
    return pd.DataFrame([
        ["audit_only", True, True, "PASS"],
        ["reconciliation_audit_only", True, True, "PASS"],
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
        ["next_gate_18o_only_after_success", bool(success), bool(success), "PASS"],
    ], columns=["safety_item", "observed", "expected", "status"])


def next_gates(success: bool) -> pd.DataFrame:
    return pd.DataFrame([
        ["18O", "TIER2_SOURCE_IDENTITY_DRY_RUN_BLOCKER_REVIEW_AUDIT_ONLY", "Review remaining blockers and missing evidence; still not source-of-truth.", bool(success)],
        ["SOURCE_IDENTITY_FINALIZATION", "TIER2_SOURCE_IDENTITY_FINALIZATION", "Blocked after 18N.", False],
        ["SOURCE_RECOVERY", "TIER2_SOURCE_IDENTITY_RECOVERY_EXECUTION", "Blocked after 18N.", False],
        ["LIVE", "MEDIUM_FULL_SET_LIVE_EVALUATOR", "Blocked.", False],
        ["FINAL_SIGNAL", "MEDIUM_FINAL_SIGNAL", "Blocked.", False],
    ], columns=["next_step", "name", "purpose", "allowed_after_18n_success"])


def blockers() -> pd.DataFrame:
    return pd.DataFrame([
        ["18N-B001", "source identity finalization remains blocked", "SOURCE_IDENTITY_FINALIZED_FALSE_REQUIRED"],
        ["18N-B002", "source recovery execution remains blocked", "SOURCE_RECOVERY_EXECUTED_FALSE_REQUIRED"],
        ["18N-B003", "source identity recovered flag remains blocked", "SOURCE_IDENTITY_RECOVERED_FALSE_REQUIRED"],
        ["18N-B004", "OHLC replay/reconstruction remains blocked", "OHLC_REPLAY_ALLOWED_FALSE_REQUIRED"],
        ["18N-B005", "live/final evaluator/signal remains blocked", "LIVE_FINAL_FALSE_REQUIRED"],
        ["18N-B006", "Discord/MT5/AI API/live hook remain blocked", "EXTERNAL_ACTIONS_FALSE_REQUIRED"],
        ["18N-B007", "NO_SIGNAL Discord notification remains blocked", "NO_SIGNAL_DISCORD_FALSE_REQUIRED"],
    ], columns=["blocker_id", "blocker", "required_condition"])


def main() -> int:
    out = fx() / OUT_DIR
    lp(out).mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()
    p18m = fx() / IN18M
    p18l = fx() / IN18L
    p18k = fx() / IN18K
    inputs = {
        "summary_18m": p18m / "gold_v2_18m_tier2_source_identity_dry_run_content_summary.json",
        "content_checks_18m": p18m / "gold_v2_18m_content_checks.csv",
        "field_completeness_18m": p18m / "gold_v2_18m_required_field_completeness.csv",
        "value_domain_18m": p18m / "gold_v2_18m_value_domain_audit.csv",
        "row_identity_18m": p18m / "gold_v2_18m_row_identity_integrity_audit.csv",
        "safety_18m": p18m / "gold_v2_18m_safety_matrix.csv",
        "gates_18m": p18m / "gold_v2_18m_required_next_gates.csv",
        "report_18m": p18m / "GOLD_V2_18M_TIER2_SOURCE_IDENTITY_DRY_RUN_CONTENT_AUDIT_ONLY_REPORT.md",
        "summary_18l": p18l / "gold_v2_18l_tier2_source_identity_dry_run_load_smoke_summary.json",
        "summary_18k": p18k / "gold_v2_18k_tier2_source_identity_dry_run_implementation_summary.json",
        "ledger_18k": p18k / "gold_v2_18k_dry_run_candidate_identity_rows.csv",
        "row_counts_18k": p18k / "gold_v2_18k_artifact_row_counts.csv",
    }
    for col, fname in DIST_FILES.items():
        inputs[f"dist_18m_{col}"] = p18m / fname
    input_audit = pd.DataFrame([{"role": k, "path": str(v), "required": True, "exists": lp(v).exists()} for k, v in inputs.items()])
    wcsv(input_audit, out / "gold_v2_18n_input_audit.csv")
    if not input_audit["exists"].all():
        status = "18N_STOP_MISSING_INPUTS"
        checks = pd.DataFrame([ck("18N-C000", "required inputs exist", False, True, False)])
        wcsv(checks, out / "gold_v2_18n_reconciliation_checks.csv")
        wcsv(safety(False), out / "gold_v2_18n_safety_matrix.csv")
        summary = {"created_utc": now, "step": STEP, "status": status, "audit_only": True, "reconciliation_passed": False, "next_recommended_step": "STOP_REVIEW_18N_INPUTS"}
        wjson(out / "gold_v2_18n_tier2_source_identity_dry_run_reconciliation_summary.json", summary)
        wtxt(out / REPORT, "# GOLD V2 18N TIER2 source identity dry-run reconciliation audit-only report\n\nStatus: `18N_STOP_MISSING_INPUTS`\n")
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 2
    s18m = rjson(inputs["summary_18m"])
    s18l = rjson(inputs["summary_18l"])
    s18k = rjson(inputs["summary_18k"])
    ledger = rcsv(inputs["ledger_18k"])
    row_counts = rcsv(inputs["row_counts_18k"])
    content = rcsv(inputs["content_checks_18m"])
    field = rcsv(inputs["field_completeness_18m"])
    value = rcsv(inputs["value_domain_18m"])
    identity = rcsv(inputs["row_identity_18m"])
    safety18m = rcsv(inputs["safety_18m"])
    gates18m = rcsv(inputs["gates_18m"])
    _ = lp(inputs["report_18m"]).read_text(encoding="utf-8")

    upstream_stop = sum(stop_count(df) for df in [content, field, value, identity, safety18m])
    row_expected_sum = int(pd.to_numeric(row_counts.get("expected_row_count", pd.Series(dtype=int)), errors="coerce").fillna(0).sum()) if not row_counts.empty else 0
    row_actual_sum = int(pd.to_numeric(row_counts.get("actual_row_count", pd.Series(dtype=int)), errors="coerce").fillna(0).sum()) if not row_counts.empty else 0
    artifact_count = len(row_counts)
    ledger_rows = len(ledger)
    row_recon = pd.DataFrame([
        ["18N-R001", "18M candidate_identity_rows", s18m.get("candidate_identity_rows"), EXPECTED_ROWS, "PASS" if s18m.get("candidate_identity_rows") == EXPECTED_ROWS else "STOP"],
        ["18N-R002", "18K ledger rows", ledger_rows, EXPECTED_ROWS, "PASS" if ledger_rows == EXPECTED_ROWS else "STOP"],
        ["18N-R003", "18K artifact count", artifact_count, EXPECTED_ARTIFACTS, "PASS" if artifact_count == EXPECTED_ARTIFACTS else "STOP"],
        ["18N-R004", "18K expected row sum", row_expected_sum, EXPECTED_ROWS, "PASS" if row_expected_sum == EXPECTED_ROWS else "STOP"],
        ["18N-R005", "18K actual row sum", row_actual_sum, EXPECTED_ROWS, "PASS" if row_actual_sum == EXPECTED_ROWS else "STOP"],
        ["18N-R006", "18M rows equal 18K ledger rows", s18m.get("candidate_identity_rows"), ledger_rows, "PASS" if s18m.get("candidate_identity_rows") == ledger_rows == EXPECTED_ROWS else "STOP"],
    ], columns=["row_reconciliation_id", "check", "observed", "expected", "status"])
    dist_rows = []
    for col, fname in DIST_FILES.items():
        d18m = norm_dist(rcsv(inputs[f"dist_18m_{col}"]), col)
        dcalc = norm_dist(distribution(ledger, col), col)
        merged = d18m.merge(dcalc, on=col, how="outer", suffixes=("_18m", "_ledger")).fillna(0)
        merged["count_18m"] = pd.to_numeric(merged["count_18m"], errors="coerce").fillna(0).astype(int)
        merged["count_ledger"] = pd.to_numeric(merged["count_ledger"], errors="coerce").fillna(0).astype(int)
        mismatches = int((merged["count_18m"] != merged["count_ledger"]).sum())
        total18m = int(merged["count_18m"].sum())
        totalledger = int(merged["count_ledger"].sum())
        dist_rows.append({"distribution": col, "mismatched_keys": mismatches, "total_18m": total18m, "total_ledger": totalledger, "expected_total": EXPECTED_ROWS, "status": "PASS" if mismatches == 0 and total18m == totalledger == EXPECTED_ROWS else "STOP"})
    dist_recon = pd.DataFrame(dist_rows)
    flag_true = 0
    for key in ["source_recovery_executed", "source_identity_finalized", "source_identity_recovered", "ledger_is_source_of_truth", "live_or_final_implementation_allowed", "oh_lc_replay_allowed", "live_enabled", "final_signal_allowed", "no_signal_discord_notified"]:
        flag_true += int(bool(s18m.get(key, False)))
    ext = s18m.get("external_actions", {})
    flag_true += sum(int(bool(v)) for v in ext.values()) if isinstance(ext, dict) else 1
    gates_forbidden_true = 0
    if {"next_step", "allowed_after_18m_success"}.issubset(gates18m.columns):
        forbidden = gates18m[gates18m["next_step"].astype(str).isin(["SOURCE_IDENTITY_FINALIZATION", "SOURCE_RECOVERY", "LIVE", "FINAL_SIGNAL"])]
        gates_forbidden_true = int(forbidden["allowed_after_18m_success"].map(truthy).sum())
    upstream_stop_audit = pd.DataFrame([
        ["content_checks_18m", stop_count(content), 0, "PASS" if stop_count(content) == 0 else "STOP"],
        ["field_completeness_18m", stop_count(field), 0, "PASS" if stop_count(field) == 0 else "STOP"],
        ["value_domain_18m", stop_count(value), 0, "PASS" if stop_count(value) == 0 else "STOP"],
        ["row_identity_18m", stop_count(identity), 0, "PASS" if stop_count(identity) == 0 else "STOP"],
        ["safety_18m", stop_count(safety18m), 0, "PASS" if stop_count(safety18m) == 0 else "STOP"],
    ], columns=["upstream_audit", "stop_rows", "expected_stop_rows", "status"])
    checks = pd.DataFrame([
        ck("18N-C001", "18M status", s18m.get("status"), EXPECTED_18M, s18m.get("status") == EXPECTED_18M),
        ck("18N-C002", "18M content_audit_passed", s18m.get("content_audit_passed"), True, bool(s18m.get("content_audit_passed", False))),
        ck("18N-C003", "18M upstream STOP rows", upstream_stop, 0, upstream_stop == 0),
        ck("18N-C004", "18L status exists", s18l.get("status"), "non_empty", bool(s18l.get("status"))),
        ck("18N-C005", "18K status exists", s18k.get("status"), "non_empty", bool(s18k.get("status"))),
        ck("18N-C006", "row reconciliation STOP rows", stop_count(row_recon), 0, stop_count(row_recon) == 0),
        ck("18N-C007", "distribution reconciliation STOP rows", stop_count(dist_recon), 0, stop_count(dist_recon) == 0),
        ck("18N-C008", "summary forbidden flags true", flag_true, 0, flag_true == 0),
        ck("18N-C009", "forbidden gates allowed", gates_forbidden_true, 0, gates_forbidden_true == 0),
    ])
    total_stop = sum(stop_count(df) for df in [checks, row_recon, dist_recon, upstream_stop_audit])
    success = total_stop == 0
    status = SUCCESS if success else "18N_STOP_REVIEW_RECONCILIATION_OUTPUTS"
    sm = safety(success)
    for name, df in [
        ("gold_v2_18n_reconciliation_checks.csv", checks),
        ("gold_v2_18n_distribution_reconciliation.csv", dist_recon),
        ("gold_v2_18n_row_count_reconciliation.csv", row_recon),
        ("gold_v2_18n_upstream_stop_audit.csv", upstream_stop_audit),
        ("gold_v2_18n_required_next_gates.csv", next_gates(success)),
        ("gold_v2_18n_blockers.csv", blockers()),
        ("gold_v2_18n_safety_matrix.csv", sm),
    ]:
        wcsv(df, out / name)
    summary = {
        "created_utc": now,
        "step": STEP,
        "status": status,
        "audit_only": True,
        "reconciliation_passed": success,
        "upstream_18m_status": s18m.get("status"),
        "upstream_18l_status": s18l.get("status"),
        "upstream_18k_status": s18k.get("status"),
        "candidate_identity_rows": ledger_rows,
        "expected_candidate_identity_rows": EXPECTED_ROWS,
        "source_artifacts": artifact_count,
        "expected_source_artifacts": EXPECTED_ARTIFACTS,
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
        "next_recommended_step": "18O_TIER2_SOURCE_IDENTITY_DRY_RUN_BLOCKER_REVIEW_AUDIT_ONLY" if success else "STOP_REVIEW_18N_OUTPUTS",
    }
    wjson(out / "gold_v2_18n_tier2_source_identity_dry_run_reconciliation_summary.json", summary)
    report = [
        "# GOLD V2 18N TIER2 source identity dry-run reconciliation audit-only report",
        "",
        f"Created UTC: {now}",
        f"Status: `{status}`",
        "",
        "## Final decision",
        "- 18N reconciled 18M audit outputs against 18K/18L audit-only outputs.",
        "- No ledger or distribution was promoted to source-of-truth.",
        "- Source recovery, identity finalization/recovery, OHLC replay, live/final paths, Discord, MT5, AI API, live hook, and NO_SIGNAL Discord remain disabled.",
        "",
        "## Reconciliation checks",
        mdtable(checks),
        "",
        "## Row-count reconciliation",
        mdtable(row_recon),
        "",
        "## Distribution reconciliation",
        mdtable(dist_recon),
        "",
        "## Upstream STOP audit",
        mdtable(upstream_stop_audit),
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
