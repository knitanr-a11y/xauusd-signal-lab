#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

STEP = "18L_TIER2_SOURCE_IDENTITY_DRY_RUN_LOAD_SMOKE_AUDIT_ONLY"
OUT_DIR = "gold_v2_18l_tier2_source_identity_dry_run_load_smoke_audit_only"
IN_DIR = "gold_v2_18k_tier2_source_identity_dry_run_implementation_audit_only"
REPORT = "GOLD_V2_18L_TIER2_SOURCE_IDENTITY_DRY_RUN_LOAD_SMOKE_AUDIT_ONLY_REPORT.md"
SUCCESS = "TIER2_SOURCE_IDENTITY_DRY_RUN_LOAD_SMOKE_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"
EXPECTED_18K = "TIER2_SOURCE_IDENTITY_DRY_RUN_IMPLEMENTED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"
LEDGER_LABEL = "DRY_RUN_CANDIDATE_IDENTITY_LEDGER_NOT_SOURCE_OF_TRUTH"
DRY_STATUS = "DRY_RUN_CANDIDATE_ONLY_NOT_SOURCE_OF_TRUTH"
HASH_PREFIX = "dryrun_sha256:"
EXPECTED_ARTIFACTS = 5
EXPECTED_ROWS = 104
REQ_LEDGER_COLUMNS = [
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
    "tp",
    "sl",
    "outcome",
    "dry_run_status",
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


def truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def falsy_count(df: pd.DataFrame, col: str) -> int:
    if col not in df.columns:
        return -1
    return int((~df[col].map(truthy)).sum())


def true_count(df: pd.DataFrame, col: str) -> int:
    if col not in df.columns:
        return -1
    return int(df[col].map(truthy).sum())


def status_stop_count(df: pd.DataFrame) -> int:
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


def bool_check(check_id: str, name: str, observed: Any, expected: Any, ok: bool) -> dict[str, Any]:
    return {"check_id": check_id, "check": name, "observed": observed, "expected": expected, "status": "PASS" if ok else "STOP"}


def build_safety(success: bool) -> pd.DataFrame:
    rows = [
        ["audit_only", True, True, "PASS"],
        ["load_smoke_only", True, True, "PASS"],
        ["ledger_is_source_of_truth", False, False, "PASS"],
        ["source_recovery_executed", False, False, "PASS"],
        ["source_identity_finalized", False, False, "PASS"],
        ["source_identity_recovered", False, False, "PASS"],
        ["live_or_final_implementation_allowed", False, False, "PASS"],
        ["oh_lc_replay_allowed", False, False, "PASS"],
        ["live_enabled", False, False, "PASS"],
        ["final_signal_allowed", False, False, "PASS"],
        ["discord_send_allowed", False, False, "PASS"],
        ["mt5_order_allowed", False, False, "PASS"],
        ["ai_api_allowed", False, False, "PASS"],
        ["live_hook_allowed", False, False, "PASS"],
        ["no_signal_discord_notified", False, False, "PASS"],
        ["next_gate_18m_only_after_success", bool(success), bool(success), "PASS"],
    ]
    return pd.DataFrame(rows, columns=["safety_item", "observed", "expected", "status"])


def next_gates(success: bool) -> pd.DataFrame:
    return pd.DataFrame([
        ["18M", "TIER2_SOURCE_IDENTITY_DRY_RUN_CONTENT_AUDIT_ONLY", "Inspect dry-run candidate identity ledger content more deeply; still not source-of-truth.", bool(success)],
        ["SOURCE_IDENTITY_FINALIZATION", "TIER2_SOURCE_IDENTITY_FINALIZATION", "Blocked after 18L.", False],
        ["SOURCE_RECOVERY", "TIER2_SOURCE_IDENTITY_RECOVERY_EXECUTION", "Blocked after 18L.", False],
        ["LIVE", "MEDIUM_FULL_SET_LIVE_EVALUATOR", "Blocked.", False],
        ["FINAL_SIGNAL", "MEDIUM_FINAL_SIGNAL", "Blocked.", False],
    ], columns=["next_step", "name", "purpose", "allowed_after_18l_success"])


def blockers() -> pd.DataFrame:
    return pd.DataFrame([
        ["18L-B001", "18K ledger remains dry-run candidate only", "LEDGER_NOT_SOURCE_OF_TRUTH_REQUIRED"],
        ["18L-B002", "source identity finalization remains blocked", "SOURCE_IDENTITY_FINALIZED_FALSE_REQUIRED"],
        ["18L-B003", "source recovery execution remains blocked", "SOURCE_RECOVERY_EXECUTED_FALSE_REQUIRED"],
        ["18L-B004", "OHLC replay/reconstruction remains blocked", "OHLC_REPLAY_ALLOWED_FALSE_REQUIRED"],
        ["18L-B005", "live/final evaluator/signal remains blocked", "LIVE_FINAL_FALSE_REQUIRED"],
        ["18L-B006", "Discord/MT5/AI API/live hook remain blocked", "EXTERNAL_ACTIONS_FALSE_REQUIRED"],
        ["18L-B007", "NO_SIGNAL Discord notification remains blocked", "NO_SIGNAL_DISCORD_FALSE_REQUIRED"],
    ], columns=["blocker_id", "blocker", "required_condition"])


def stop_outputs(out: Path, now: str, status: str, audit: pd.DataFrame) -> int:
    checks = pd.DataFrame([bool_check("18L-C000", "stopped before loading all 18K outputs", status, "PASS_STATUS", False)])
    empty = pd.DataFrame()
    safety = build_safety(False)
    for name, df in [
        ("gold_v2_18l_load_checks.csv", checks),
        ("gold_v2_18l_ledger_column_audit.csv", empty),
        ("gold_v2_18l_ledger_safety_audit.csv", empty),
        ("gold_v2_18l_row_count_audit.csv", empty),
        ("gold_v2_18l_required_next_gates.csv", next_gates(False)),
        ("gold_v2_18l_blockers.csv", blockers()),
        ("gold_v2_18l_safety_matrix.csv", safety),
    ]:
        wcsv(df, out / name)
    summary = {
        "created_utc": now,
        "step": STEP,
        "status": status,
        "audit_only": True,
        "load_smoke_passed": False,
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
        "next_recommended_step": "STOP_REVIEW_18L_INPUTS",
    }
    wjson(out / "gold_v2_18l_tier2_source_identity_dry_run_load_smoke_summary.json", summary)
    report = [
        "# GOLD V2 18L TIER2 source identity dry-run load smoke audit-only report",
        "",
        f"Created UTC: {now}",
        f"Status: `{status}`",
        "",
        "## Final decision",
        "- 18L stopped before load-smoke success.",
        "- No source recovery, source identity finalization, source identity recovery, live/final path, OHLC replay, Discord, MT5, AI API, live hook, or NO_SIGNAL Discord action was enabled.",
        "",
        "## Input audit",
        mdtable(audit),
        "",
        "## Load checks",
        mdtable(checks),
        "",
        "## Safety",
        mdtable(safety),
    ]
    wtxt(out / REPORT, "\n".join(report))
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 2


def main() -> int:
    out = fx() / OUT_DIR
    lp(out).mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()
    base = fx() / IN_DIR
    inputs = {
        "summary_18k": base / "gold_v2_18k_tier2_source_identity_dry_run_implementation_summary.json",
        "input_audit_18k": base / "gold_v2_18k_input_audit.csv",
        "implementation_checks_18k": base / "gold_v2_18k_implementation_checks.csv",
        "ledger_18k": base / "gold_v2_18k_dry_run_candidate_identity_rows.csv",
        "artifact_row_counts_18k": base / "gold_v2_18k_artifact_row_counts.csv",
        "field_derivation_18k": base / "gold_v2_18k_dry_run_field_derivation_audit.csv",
        "validation_checks_18k": base / "gold_v2_18k_dry_run_validation_checks.csv",
        "next_gates_18k": base / "gold_v2_18k_required_next_gates.csv",
        "blockers_18k": base / "gold_v2_18k_blockers.csv",
        "safety_18k": base / "gold_v2_18k_safety_matrix.csv",
        "report_18k": base / "GOLD_V2_18K_TIER2_SOURCE_IDENTITY_DRY_RUN_IMPLEMENTATION_AUDIT_ONLY_REPORT.md",
    }
    audit = pd.DataFrame([{"role": k, "path": str(v), "required": True, "exists": lp(v).exists()} for k, v in inputs.items()])
    wcsv(audit, out / "gold_v2_18l_input_audit.csv")
    if not audit["exists"].all():
        return stop_outputs(out, now, "18L_STOP_MISSING_18K_INPUTS", audit)

    try:
        s18k = rjson(inputs["summary_18k"])
        input_audit = rcsv(inputs["input_audit_18k"])
        impl = rcsv(inputs["implementation_checks_18k"])
        ledger = rcsv(inputs["ledger_18k"])
        row_counts = rcsv(inputs["artifact_row_counts_18k"])
        deriv = rcsv(inputs["field_derivation_18k"])
        validation18k = rcsv(inputs["validation_checks_18k"])
        gates18k = rcsv(inputs["next_gates_18k"])
        safety18k = rcsv(inputs["safety_18k"])
        _ = lp(inputs["report_18k"]).read_text(encoding="utf-8")
    except Exception as exc:
        audit["load_error"] = str(exc)
        wcsv(audit, out / "gold_v2_18l_input_audit.csv")
        return stop_outputs(out, now, "18L_STOP_LOAD_FAILED", audit)

    ext = s18k.get("external_actions", {})
    summary_live_or_external = bool(
        s18k.get("source_recovery_executed", False)
        or s18k.get("source_identity_finalized", False)
        or s18k.get("source_identity_recovered", False)
        or s18k.get("ledger_is_source_of_truth", False)
        or s18k.get("live_or_final_implementation_allowed", False)
        or s18k.get("oh_lc_replay_allowed", False)
        or s18k.get("live_enabled", False)
        or s18k.get("final_signal_allowed", False)
        or s18k.get("no_signal_discord_notified", False)
        or any(bool(v) for v in ext.values())
    )
    artifact_match_false = int((row_counts.get("row_count_match", pd.Series(dtype=str)).astype(str) != "True").sum()) if not row_counts.empty else 999
    artifact_count = int(len(row_counts))
    expected_total = int(pd.to_numeric(row_counts.get("expected_row_count", pd.Series(dtype=int)), errors="coerce").fillna(0).sum()) if not row_counts.empty else 0
    actual_total = int(pd.to_numeric(row_counts.get("actual_row_count", pd.Series(dtype=int)), errors="coerce").fillna(0).sum()) if not row_counts.empty else 0
    ledger_rows = int(len(ledger))
    missing_cols = [c for c in REQ_LEDGER_COLUMNS if c not in ledger.columns]
    label_ok = int((ledger["ledger_label"].astype(str) == LEDGER_LABEL).sum()) if "ledger_label" in ledger.columns else 0
    status_ok = int((ledger["dry_run_status"].astype(str) == DRY_STATUS).sum()) if "dry_run_status" in ledger.columns else 0
    hash_ok = int(ledger["source_row_hash"].astype(str).str.startswith(HASH_PREFIX).sum()) if "source_row_hash" in ledger.columns else 0
    false_flag_rows = []
    for col in FALSE_FLAGS:
        false_flag_rows.append({
            "flag": col,
            "rows_true": true_count(ledger, col),
            "rows_false": falsy_count(ledger, col),
            "expected_true_rows": 0,
            "expected_false_rows": ledger_rows,
            "status": "PASS" if true_count(ledger, col) == 0 and falsy_count(ledger, col) == ledger_rows and ledger_rows > 0 else "STOP",
        })
    ledger_safety = pd.DataFrame(false_flag_rows)
    forbidden_true_total = int(ledger_safety["rows_true"].clip(lower=0).sum()) if not ledger_safety.empty else 999
    source_truth_ok = bool(s18k.get("ledger_is_source_of_truth", True) is False)

    column_audit = pd.DataFrame([
        {"column": c, "present": c in ledger.columns, "status": "PASS" if c in ledger.columns else "STOP"}
        for c in REQ_LEDGER_COLUMNS
    ])
    row_count_audit = pd.DataFrame([
        ["18L-R001", "artifact rows", artifact_count, EXPECTED_ARTIFACTS, "PASS" if artifact_count == EXPECTED_ARTIFACTS else "STOP"],
        ["18L-R002", "artifact row-count mismatches", artifact_match_false, 0, "PASS" if artifact_match_false == 0 else "STOP"],
        ["18L-R003", "expected source rows", expected_total, EXPECTED_ROWS, "PASS" if expected_total == EXPECTED_ROWS else "STOP"],
        ["18L-R004", "actual source rows", actual_total, EXPECTED_ROWS, "PASS" if actual_total == EXPECTED_ROWS else "STOP"],
        ["18L-R005", "ledger rows", ledger_rows, EXPECTED_ROWS, "PASS" if ledger_rows == EXPECTED_ROWS else "STOP"],
        ["18L-R006", "ledger rows equal actual source rows", ledger_rows, actual_total, "PASS" if ledger_rows == actual_total == EXPECTED_ROWS else "STOP"],
    ], columns=["row_count_id", "check", "observed", "expected", "status"])

    final_gates_blocked = True
    if not gates18k.empty and {"next_step", "allowed_after_18k_success"}.issubset(gates18k.columns):
        forbidden = gates18k[gates18k["next_step"].astype(str).isin(["SOURCE_IDENTITY_FINALIZATION", "SOURCE_RECOVERY", "LIVE", "FINAL_SIGNAL"])]
        final_gates_blocked = int(forbidden["allowed_after_18k_success"].map(truthy).sum()) == 0
    checks = pd.DataFrame([
        bool_check("18L-C001", "18K status", s18k.get("status"), EXPECTED_18K, s18k.get("status") == EXPECTED_18K),
        bool_check("18L-C002", "18K audit_only", s18k.get("audit_only"), True, bool(s18k.get("audit_only", False))),
        bool_check("18L-C003", "18K dry_run_implemented", s18k.get("dry_run_implemented"), True, bool(s18k.get("dry_run_implemented", False))),
        bool_check("18L-C004", "18K dry_run_executed", s18k.get("dry_run_executed"), True, bool(s18k.get("dry_run_executed", False))),
        bool_check("18L-C005", "18K source rows read", s18k.get("source_rows_read"), True, bool(s18k.get("source_rows_read", False))),
        bool_check("18L-C006", "18K row hash computed", s18k.get("row_hash_computed"), True, bool(s18k.get("row_hash_computed", False))),
        bool_check("18L-C007", "18K row hash scope", s18k.get("row_hash_scope"), "dry_run_candidate_identity_only_not_final_source_identity", s18k.get("row_hash_scope") == "dry_run_candidate_identity_only_not_final_source_identity"),
        bool_check("18L-C008", "18K implementation STOP rows", status_stop_count(impl), 0, status_stop_count(impl) == 0),
        bool_check("18L-C009", "18K validation STOP rows", status_stop_count(validation18k), 0, status_stop_count(validation18k) == 0),
        bool_check("18L-C010", "18K safety STOP rows", status_stop_count(safety18k), 0, status_stop_count(safety18k) == 0),
        bool_check("18L-C011", "18K input audit missing rows", int((input_audit.get("exists", pd.Series(dtype=str)).astype(str) != "True").sum()) if not input_audit.empty else 999, 0, (not input_audit.empty and int((input_audit.get("exists", pd.Series(dtype=str)).astype(str) != "True").sum()) == 0)),
        bool_check("18L-C012", "18K field derivation STOP rows", int(deriv.get("derivation_status", pd.Series(dtype=str)).astype(str).str.startswith("STOP").sum()) if not deriv.empty else 999, 0, (not deriv.empty and int(deriv.get("derivation_status", pd.Series(dtype=str)).astype(str).str.startswith("STOP").sum()) == 0)),
        bool_check("18L-C013", "summary forbidden flags true", summary_live_or_external, False, not summary_live_or_external),
        bool_check("18L-C014", "ledger_is_source_of_truth", s18k.get("ledger_is_source_of_truth"), False, source_truth_ok),
        bool_check("18L-C015", "ledger required column missing count", len(missing_cols), 0, len(missing_cols) == 0),
        bool_check("18L-C016", "ledger label rows", label_ok, ledger_rows, label_ok == ledger_rows == EXPECTED_ROWS),
        bool_check("18L-C017", "ledger dry-run status rows", status_ok, ledger_rows, status_ok == ledger_rows == EXPECTED_ROWS),
        bool_check("18L-C018", "ledger dry-run hash prefix rows", hash_ok, ledger_rows, hash_ok == ledger_rows == EXPECTED_ROWS),
        bool_check("18L-C019", "ledger forbidden true flags total", forbidden_true_total, 0, forbidden_true_total == 0),
        bool_check("18L-C020", "18K final/source/live gates blocked", final_gates_blocked, True, final_gates_blocked),
    ])
    all_frames = [checks, column_audit.rename(columns={"column": "check", "present": "observed"}), ledger_safety.rename(columns={"flag": "check", "rows_true": "observed", "expected_true_rows": "expected"}), row_count_audit.rename(columns={"row_count_id": "check_id"})]
    stop_total = sum(status_stop_count(df) for df in all_frames)
    success = stop_total == 0
    status = SUCCESS if success else "18L_STOP_REVIEW_LOAD_SMOKE_OUTPUTS"
    safety = build_safety(success)
    for name, df in [
        ("gold_v2_18l_load_checks.csv", checks),
        ("gold_v2_18l_ledger_column_audit.csv", column_audit),
        ("gold_v2_18l_ledger_safety_audit.csv", ledger_safety),
        ("gold_v2_18l_row_count_audit.csv", row_count_audit),
        ("gold_v2_18l_required_next_gates.csv", next_gates(success)),
        ("gold_v2_18l_blockers.csv", blockers()),
        ("gold_v2_18l_safety_matrix.csv", safety),
    ]:
        wcsv(df, out / name)
    summary = {
        "created_utc": now,
        "step": STEP,
        "status": status,
        "audit_only": True,
        "load_smoke_passed": success,
        "upstream_18k_status": s18k.get("status"),
        "candidate_identity_rows": ledger_rows,
        "expected_candidate_identity_rows": EXPECTED_ROWS,
        "source_artifacts": artifact_count,
        "expected_source_artifacts": EXPECTED_ARTIFACTS,
        "load_check_stop_rows": status_stop_count(checks),
        "ledger_column_stop_rows": status_stop_count(column_audit),
        "ledger_safety_stop_rows": status_stop_count(ledger_safety),
        "row_count_stop_rows": status_stop_count(row_count_audit),
        "total_stop_rows": stop_total,
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
        "next_recommended_step": "18M_TIER2_SOURCE_IDENTITY_DRY_RUN_CONTENT_AUDIT_ONLY" if success else "STOP_REVIEW_18L_OUTPUTS",
    }
    wjson(out / "gold_v2_18l_tier2_source_identity_dry_run_load_smoke_summary.json", summary)
    report = [
        "# GOLD V2 18L TIER2 source identity dry-run load smoke audit-only report",
        "",
        f"Created UTC: {now}",
        f"Status: `{status}`",
        "",
        "## Final decision",
        "- 18L load-smoke checked the 18K dry-run outputs only.",
        "- The 18K ledger remains a dry-run candidate identity ledger and is not source-of-truth.",
        "- Source recovery, source identity finalization/recovery, OHLC replay, live/final paths, Discord, MT5, AI API, live hook, and NO_SIGNAL Discord notification remain disabled.",
        "",
        "## Input audit",
        mdtable(audit),
        "",
        "## Load checks",
        mdtable(checks),
        "",
        "## Row count audit",
        mdtable(row_count_audit),
        "",
        "## Ledger column audit",
        mdtable(column_audit),
        "",
        "## Ledger safety audit",
        mdtable(ledger_safety),
        "",
        "## Next gates",
        mdtable(next_gates(success)),
        "",
        "## Blockers",
        mdtable(blockers()),
        "",
        "## Safety",
        mdtable(safety),
    ]
    wtxt(out / REPORT, "\n".join(report))
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if success else 2


if __name__ == "__main__":
    raise SystemExit(main())
