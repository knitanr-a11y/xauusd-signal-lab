#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

STEP = "18M_TIER2_SOURCE_IDENTITY_DRY_RUN_CONTENT_AUDIT_ONLY"
OUT_DIR = "gold_v2_18m_tier2_source_identity_dry_run_content_audit_only"
IN18L = "gold_v2_18l_tier2_source_identity_dry_run_load_smoke_audit_only"
IN18K = "gold_v2_18k_tier2_source_identity_dry_run_implementation_audit_only"
REPORT = "GOLD_V2_18M_TIER2_SOURCE_IDENTITY_DRY_RUN_CONTENT_AUDIT_ONLY_REPORT.md"
SUCCESS = "TIER2_SOURCE_IDENTITY_DRY_RUN_CONTENT_AUDIT_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"
EXPECTED_18L = "TIER2_SOURCE_IDENTITY_DRY_RUN_LOAD_SMOKE_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"
EXPECTED_ROWS = 104
LEDGER_LABEL = "DRY_RUN_CANDIDATE_IDENTITY_LEDGER_NOT_SOURCE_OF_TRUTH"
DRY_STATUS = "DRY_RUN_CANDIDATE_ONLY_NOT_SOURCE_OF_TRUTH"
HASH_SCOPE = "DRY_RUN_CANDIDATE_ONLY_NOT_FINAL_SOURCE_IDENTITY"
HASH_PREFIX = "dryrun_sha256:"
ALLOWED_DIRECTIONS = {"BUY", "SELL"}
ALLOWED_OUTCOMES = {"WIN", "LOSS", "BREAKEVEN", "SMALL_WIN", "SMALL_LOSS", "UNKNOWN", "NO_OUTCOME"}
REQUIRED_NON_EMPTY = [
    "ledger_label",
    "artifact_role",
    "relative_path",
    "source_filename",
    "source_row_index0",
    "source_row_number_1based",
    "manifest_row_id",
    "component",
    "source_identity_type",
    "source_role",
    "source_key",
    "source_row_hash",
    "source_row_hash_scope",
    "strategy_id",
    "source_status",
    "entry_time",
    "direction",
    "outcome",
    "dry_run_status",
]
OPTIONAL_CAN_BE_EMPTY = ["tp", "sl"]
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


def ck(cid: str, name: str, observed: Any, expected: Any, ok: bool) -> dict[str, Any]:
    return {"check_id": cid, "check": name, "observed": observed, "expected": expected, "status": "PASS" if ok else "STOP"}


def distribution(df: pd.DataFrame, col: str) -> pd.DataFrame:
    if col not in df.columns:
        return pd.DataFrame(columns=[col, "count"])
    return df.groupby(col, dropna=False).size().reset_index(name="count").sort_values("count", ascending=False)


def safety_matrix(success: bool) -> pd.DataFrame:
    rows = [
        ["audit_only", True, True, "PASS"],
        ["content_audit_only", True, True, "PASS"],
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
        ["next_gate_18n_only_after_success", bool(success), bool(success), "PASS"],
    ]
    return pd.DataFrame(rows, columns=["safety_item", "observed", "expected", "status"])


def next_gates(success: bool) -> pd.DataFrame:
    return pd.DataFrame([
        ["18N", "TIER2_SOURCE_IDENTITY_DRY_RUN_RECONCILIATION_AUDIT_ONLY", "Reconcile 18M content audit summaries against earlier audit expectations; still not source-of-truth.", bool(success)],
        ["SOURCE_IDENTITY_FINALIZATION", "TIER2_SOURCE_IDENTITY_FINALIZATION", "Blocked after 18M.", False],
        ["SOURCE_RECOVERY", "TIER2_SOURCE_IDENTITY_RECOVERY_EXECUTION", "Blocked after 18M.", False],
        ["LIVE", "MEDIUM_FULL_SET_LIVE_EVALUATOR", "Blocked.", False],
        ["FINAL_SIGNAL", "MEDIUM_FINAL_SIGNAL", "Blocked.", False],
    ], columns=["next_step", "name", "purpose", "allowed_after_18m_success"])


def blockers() -> pd.DataFrame:
    return pd.DataFrame([
        ["18M-B001", "18K ledger remains dry-run candidate only", "LEDGER_NOT_SOURCE_OF_TRUTH_REQUIRED"],
        ["18M-B002", "source identity finalization remains blocked", "SOURCE_IDENTITY_FINALIZED_FALSE_REQUIRED"],
        ["18M-B003", "source recovery execution remains blocked", "SOURCE_RECOVERY_EXECUTED_FALSE_REQUIRED"],
        ["18M-B004", "OHLC replay/reconstruction remains blocked", "OHLC_REPLAY_ALLOWED_FALSE_REQUIRED"],
        ["18M-B005", "live/final evaluator/signal remains blocked", "LIVE_FINAL_FALSE_REQUIRED"],
        ["18M-B006", "Discord/MT5/AI API/live hook remain blocked", "EXTERNAL_ACTIONS_FALSE_REQUIRED"],
        ["18M-B007", "NO_SIGNAL Discord notification remains blocked", "NO_SIGNAL_DISCORD_FALSE_REQUIRED"],
    ], columns=["blocker_id", "blocker", "required_condition"])


def main() -> int:
    out = fx() / OUT_DIR
    lp(out).mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()
    p18l = fx() / IN18L
    p18k = fx() / IN18K
    inputs = {
        "summary_18l": p18l / "gold_v2_18l_tier2_source_identity_dry_run_load_smoke_summary.json",
        "input_audit_18l": p18l / "gold_v2_18l_input_audit.csv",
        "load_checks_18l": p18l / "gold_v2_18l_load_checks.csv",
        "ledger_column_audit_18l": p18l / "gold_v2_18l_ledger_column_audit.csv",
        "ledger_safety_audit_18l": p18l / "gold_v2_18l_ledger_safety_audit.csv",
        "row_count_audit_18l": p18l / "gold_v2_18l_row_count_audit.csv",
        "next_gates_18l": p18l / "gold_v2_18l_required_next_gates.csv",
        "blockers_18l": p18l / "gold_v2_18l_blockers.csv",
        "safety_18l": p18l / "gold_v2_18l_safety_matrix.csv",
        "report_18l": p18l / "GOLD_V2_18L_TIER2_SOURCE_IDENTITY_DRY_RUN_LOAD_SMOKE_AUDIT_ONLY_REPORT.md",
        "ledger_18k": p18k / "gold_v2_18k_dry_run_candidate_identity_rows.csv",
    }
    input_audit = pd.DataFrame([{"role": k, "path": str(v), "required": True, "exists": lp(v).exists()} for k, v in inputs.items()])
    wcsv(input_audit, out / "gold_v2_18m_input_audit.csv")
    if not input_audit["exists"].all():
        status = "18M_STOP_MISSING_INPUTS"
        checks = pd.DataFrame([ck("18M-C000", "required inputs exist", False, True, False)])
        wcsv(checks, out / "gold_v2_18m_content_checks.csv")
        wcsv(safety_matrix(False), out / "gold_v2_18m_safety_matrix.csv")
        summary = {"created_utc": now, "step": STEP, "status": status, "audit_only": True, "content_audit_passed": False, "next_recommended_step": "STOP_REVIEW_18M_INPUTS"}
        wjson(out / "gold_v2_18m_tier2_source_identity_dry_run_content_summary.json", summary)
        wtxt(out / REPORT, "# GOLD V2 18M TIER2 source identity dry-run content audit-only report\n\nStatus: `18M_STOP_MISSING_INPUTS`\n")
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 2
    s18l = rjson(inputs["summary_18l"])
    load18l = rcsv(inputs["load_checks_18l"])
    col18l = rcsv(inputs["ledger_column_audit_18l"])
    safe18l = rcsv(inputs["ledger_safety_audit_18l"])
    row18l = rcsv(inputs["row_count_audit_18l"])
    safety18l = rcsv(inputs["safety_18l"])
    gates18l = rcsv(inputs["next_gates_18l"])
    ledger = rcsv(inputs["ledger_18k"])
    _ = lp(inputs["report_18l"]).read_text(encoding="utf-8")

    upstream_stop = sum(stop_count(df) for df in [load18l, col18l, safe18l, row18l, safety18l])
    rows = len(ledger)
    field_rows = []
    for col in REQUIRED_NON_EMPTY:
        present = col in ledger.columns
        empty = int((ledger[col].astype(str).str.strip() == "").sum()) if present else rows
        field_rows.append({"field": col, "required_non_empty": True, "present": present, "empty_rows": empty, "expected_empty_rows": 0, "status": "PASS" if present and empty == 0 else "STOP"})
    for col in OPTIONAL_CAN_BE_EMPTY:
        present = col in ledger.columns
        empty = int((ledger[col].astype(str).str.strip() == "").sum()) if present else rows
        field_rows.append({"field": col, "required_non_empty": False, "present": present, "empty_rows": empty, "expected_empty_rows": "ALLOW_EMPTY", "status": "PASS" if present else "STOP"})
    field_audit = pd.DataFrame(field_rows)

    idx_ok = False
    if {"source_row_index0", "source_row_number_1based"}.issubset(ledger.columns):
        idx0 = pd.to_numeric(ledger["source_row_index0"], errors="coerce")
        idx1 = pd.to_numeric(ledger["source_row_number_1based"], errors="coerce")
        idx_ok = bool(((idx0 + 1) == idx1).all())
    hash_unique = int(ledger["source_row_hash"].nunique()) if "source_row_hash" in ledger.columns else 0
    hash_prefix_rows = int(ledger["source_row_hash"].astype(str).str.startswith(HASH_PREFIX).sum()) if "source_row_hash" in ledger.columns else 0
    label_rows = int((ledger["ledger_label"].astype(str) == LEDGER_LABEL).sum()) if "ledger_label" in ledger.columns else 0
    dry_rows = int((ledger["dry_run_status"].astype(str) == DRY_STATUS).sum()) if "dry_run_status" in ledger.columns else 0
    scope_rows = int((ledger["source_row_hash_scope"].astype(str) == HASH_SCOPE).sum()) if "source_row_hash_scope" in ledger.columns else 0
    direction_bad = int((~ledger["direction"].astype(str).isin(ALLOWED_DIRECTIONS)).sum()) if "direction" in ledger.columns else rows
    outcome_bad = int((~ledger["outcome"].astype(str).isin(ALLOWED_OUTCOMES)).sum()) if "outcome" in ledger.columns else rows
    flag_rows = []
    for col in FALSE_FLAGS:
        if col in ledger.columns:
            true_rows = int(ledger[col].map(truthy).sum())
            false_rows = rows - true_rows
        else:
            true_rows = -1
            false_rows = -1
        flag_rows.append({"flag": col, "true_rows": true_rows, "expected_true_rows": 0, "false_rows": false_rows, "expected_false_rows": rows, "status": "PASS" if true_rows == 0 and false_rows == rows else "STOP"})
    flag_audit = pd.DataFrame(flag_rows)
    value_audit = pd.DataFrame([
        ["direction", direction_bad, 0, "PASS" if direction_bad == 0 else "STOP"],
        ["outcome", outcome_bad, 0, "PASS" if outcome_bad == 0 else "STOP"],
        ["ledger_label", rows - label_rows, 0, "PASS" if label_rows == rows == EXPECTED_ROWS else "STOP"],
        ["dry_run_status", rows - dry_rows, 0, "PASS" if dry_rows == rows == EXPECTED_ROWS else "STOP"],
        ["source_row_hash_scope", rows - scope_rows, 0, "PASS" if scope_rows == rows == EXPECTED_ROWS else "STOP"],
    ], columns=["field", "bad_rows", "expected_bad_rows", "status"])
    identity_audit = pd.DataFrame([
        ["18M-I001", "source_row_index0 + 1 == source_row_number_1based", idx_ok, True, "PASS" if idx_ok else "STOP"],
        ["18M-I002", "source_row_hash prefix rows", hash_prefix_rows, EXPECTED_ROWS, "PASS" if hash_prefix_rows == EXPECTED_ROWS else "STOP"],
        ["18M-I003", "source_row_hash unique count", hash_unique, EXPECTED_ROWS, "PASS" if hash_unique == EXPECTED_ROWS else "STOP"],
    ], columns=["identity_check_id", "check", "observed", "expected", "status"])
    checks = pd.DataFrame([
        ck("18M-C001", "18L status", s18l.get("status"), EXPECTED_18L, s18l.get("status") == EXPECTED_18L),
        ck("18M-C002", "18L load_smoke_passed", s18l.get("load_smoke_passed"), True, bool(s18l.get("load_smoke_passed", False))),
        ck("18M-C003", "18L upstream STOP rows", upstream_stop, 0, upstream_stop == 0),
        ck("18M-C004", "ledger row count", rows, EXPECTED_ROWS, rows == EXPECTED_ROWS),
        ck("18M-C005", "required field STOP rows", stop_count(field_audit), 0, stop_count(field_audit) == 0),
        ck("18M-C006", "value domain STOP rows", stop_count(value_audit), 0, stop_count(value_audit) == 0),
        ck("18M-C007", "row identity STOP rows", stop_count(identity_audit), 0, stop_count(identity_audit) == 0),
        ck("18M-C008", "forbidden ledger flags STOP rows", stop_count(flag_audit), 0, stop_count(flag_audit) == 0),
        ck("18M-C009", "ledger_is_source_of_truth remains false", s18l.get("ledger_is_source_of_truth"), False, s18l.get("ledger_is_source_of_truth") is False),
    ])
    total_stop = sum(stop_count(df) for df in [checks, field_audit, value_audit, identity_audit, flag_audit])
    success = total_stop == 0
    status = SUCCESS if success else "18M_STOP_REVIEW_CONTENT_AUDIT_OUTPUTS"
    safety = safety_matrix(success)
    outputs = {
        "gold_v2_18m_content_checks.csv": checks,
        "gold_v2_18m_required_field_completeness.csv": field_audit,
        "gold_v2_18m_value_domain_audit.csv": value_audit,
        "gold_v2_18m_row_identity_integrity_audit.csv": identity_audit,
        "gold_v2_18m_distribution_by_artifact_role.csv": distribution(ledger, "artifact_role"),
        "gold_v2_18m_distribution_by_component.csv": distribution(ledger, "component"),
        "gold_v2_18m_distribution_by_direction.csv": distribution(ledger, "direction"),
        "gold_v2_18m_distribution_by_outcome.csv": distribution(ledger, "outcome"),
        "gold_v2_18m_distribution_by_source_status.csv": distribution(ledger, "source_status"),
        "gold_v2_18m_required_next_gates.csv": next_gates(success),
        "gold_v2_18m_blockers.csv": blockers(),
        "gold_v2_18m_safety_matrix.csv": safety,
    }
    for name, df in outputs.items():
        wcsv(df, out / name)
    summary = {
        "created_utc": now,
        "step": STEP,
        "status": status,
        "audit_only": True,
        "content_audit_passed": success,
        "upstream_18l_status": s18l.get("status"),
        "candidate_identity_rows": rows,
        "expected_candidate_identity_rows": EXPECTED_ROWS,
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
        "next_recommended_step": "18N_TIER2_SOURCE_IDENTITY_DRY_RUN_RECONCILIATION_AUDIT_ONLY" if success else "STOP_REVIEW_18M_OUTPUTS",
    }
    wjson(out / "gold_v2_18m_tier2_source_identity_dry_run_content_summary.json", summary)
    report = [
        "# GOLD V2 18M TIER2 source identity dry-run content audit-only report",
        "",
        f"Created UTC: {now}",
        f"Status: `{status}`",
        "",
        "## Final decision",
        "- 18M content-audited the 18K dry-run candidate identity ledger only.",
        "- The ledger remains not source-of-truth.",
        "- Source recovery, identity finalization/recovery, OHLC replay, live/final paths, Discord, MT5, AI API, live hook, and NO_SIGNAL Discord remain disabled.",
        "",
        "## Content checks",
        mdtable(checks),
        "",
        "## Required field completeness",
        mdtable(field_audit),
        "",
        "## Value domain audit",
        mdtable(value_audit),
        "",
        "## Row identity integrity audit",
        mdtable(identity_audit),
        "",
        "## Safety flags",
        mdtable(flag_audit),
        "",
        "## Outcome distribution",
        mdtable(distribution(ledger, "outcome")),
        "",
        "## Next gates",
        mdtable(next_gates(success)),
        "",
        "## Safety",
        mdtable(safety),
    ]
    wtxt(out / REPORT, "\n".join(report))
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if success else 2


if __name__ == "__main__":
    raise SystemExit(main())
