#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Sequence

import pandas as pd

STEP = "25C41_COREB_G1_RIGHT_ONLY_ROW_LEVEL_EXPORT_PLAN_AUDIT_ONLY"
STATUS = "COREB_G1_RIGHT_ONLY_ROW_LEVEL_EXPORT_PLAN_READY_AUDIT_ONLY_HUMAN_ACCEPTANCE_REQUIRED_BEFORE_EXPORT"
STOP = "25C41_STOP_MISSING_INPUT_AUDIT_ONLY"
STOP_CONTRACT = "25C41_STOP_25C40_CONTRACT_UNSAFE_AUDIT_ONLY"

OUT_DIR = "gold_v2_25c41_coreb_g1_right_only_row_level_export_plan_audit_only"
IN40 = "gold_v2_25c40_coreb_g1_right_only_recovery_input_availability_audit_only"

EXPECTED_STEP_40 = "25C40_COREB_G1_RIGHT_ONLY_RECOVERY_INPUT_AVAILABILITY_AUDIT_ONLY"
EXPECTED_STATUS_40 = "COREB_G1_RIGHT_ONLY_RECOVERY_INPUT_AVAILABILITY_AUDIT_COMPLETED_AUDIT_ONLY_ROW_LEVEL_EXPORT_PLAN_REQUIRED"
EXPECTED_NEXT_40 = "25C41_COREB_G1_RIGHT_ONLY_ROW_LEVEL_EXPORT_PLAN_AUDIT_ONLY"


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def files_root() -> Path:
    r = repo_root()
    return r.parents[1] if len(r.parents) >= 2 else r.parent


def default_fx_outputs() -> Path:
    return files_root() / "FX_OUTPUTS"


def lp(p: Path) -> Path:
    if os.name != "nt":
        return p
    s = str(p)
    if s.startswith("\\\\?\\"):
        return Path(s)
    if s.startswith("\\\\"):
        return Path("\\\\?\\UNC\\" + s[2:])
    return Path("\\\\?\\" + s)


def read_json(p: Path) -> dict:
    return json.loads(lp(p).read_text(encoding="utf-8-sig"))


def read_csv(p: Path) -> pd.DataFrame:
    last: Optional[Exception] = None
    for enc in ("utf-8-sig", "utf-8", "cp932"):
        try:
            return pd.read_csv(lp(p), encoding=enc, keep_default_na=False)
        except Exception as e:
            last = e
    raise RuntimeError(f"read failed {p}: {last}")


def write_csv(p: Path, df: pd.DataFrame) -> None:
    lp(p.parent).mkdir(parents=True, exist_ok=True)
    df.to_csv(lp(p), index=False, encoding="utf-8-sig")


def write_json(p: Path, obj: dict) -> None:
    lp(p.parent).mkdir(parents=True, exist_ok=True)
    lp(p).write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def md_table(df: pd.DataFrame, n: int = 80) -> str:
    if df.empty:
        return "_No rows._"
    v = df.head(n).copy()
    cols = list(v.columns)
    rows = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for _, r in v.iterrows():
        rows.append("| " + " | ".join(str(r[c]).replace("|", "\\|") for c in cols) + " |")
    return "\n".join(rows)


def as_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def status_from_exists(path: Path) -> str:
    return "PASS" if lp(path).exists() else "STOP"


def contract_rows_from_25c40(s40: dict, next_plan: pd.DataFrame) -> list[dict]:
    checks = [
        ("C001", "25C40 step matches expected", s40.get("step") == EXPECTED_STEP_40, s40.get("step")),
        ("C002", "25C40 status requires row-level export plan", s40.get("status") == EXPECTED_STATUS_40, s40.get("status")),
        ("C003", "25C40 audit_only true", as_bool(s40.get("audit_only", False)) is True, s40.get("audit_only")),
        ("C004", "25C40 input_availability_audit_only true", as_bool(s40.get("input_availability_audit_only", False)) is True, s40.get("input_availability_audit_only")),
        ("C005", "25C40 dry_run_executed false", as_bool(s40.get("dry_run_executed", True)) is False, s40.get("dry_run_executed")),
        ("C006", "25C40 condition_changed false", as_bool(s40.get("condition_changed", True)) is False, s40.get("condition_changed")),
        ("C007", "25C40 source recovery false", as_bool(s40.get("source_recovery_executed", True)) is False, s40.get("source_recovery_executed")),
        ("C008", "25C40 source mutation false", as_bool(s40.get("source_mutation_executed", True)) is False, s40.get("source_mutation_executed")),
        ("C009", "25C40 CoreB live unblock false", as_bool(s40.get("coreb_live_evaluator_unblocked", True)) is False, s40.get("coreb_live_evaluator_unblocked")),
        ("C010", "25C40 AI API false", as_bool(s40.get("ai_api_called", True)) is False, s40.get("ai_api_called")),
        ("C011", "25C40 row-level right_only evidence unavailable", as_bool(s40.get("row_level_right_only_evidence_available", True)) is False, s40.get("row_level_right_only_evidence_available")),
        ("C012", "25C40 row-level export plan required", as_bool(s40.get("row_level_export_plan_required", False)) is True, s40.get("row_level_export_plan_required")),
        ("C013", "25C40 next recommended step is 25C41", s40.get("next_recommended_step") == EXPECTED_NEXT_40, s40.get("next_recommended_step")),
        ("C014", "25C40 future dry-run still requires human acceptance", as_bool(s40.get("requires_human_acceptance_before_next_dry_run", False)) is True, s40.get("requires_human_acceptance_before_next_dry_run")),
    ]
    rows = [{"contract_id": cid, "check": check, "observed": observed, "status": "PASS" if passed else "STOP"} for cid, check, passed, observed in checks]
    if not next_plan.empty and {"next_step", "allowed_now"}.issubset(next_plan.columns):
        m = next_plan[next_plan["next_step"].astype(str).eq(EXPECTED_NEXT_40)]
        passed = not m.empty and as_bool(m.iloc[0]["allowed_now"]) is True
        rows.append({
            "contract_id": "C015",
            "check": "25C40 next plan allows 25C41 now",
            "observed": "" if m.empty else str(m.iloc[0].to_dict()),
            "status": "PASS" if passed else "STOP",
        })
    else:
        rows.append({"contract_id": "C015", "check": "25C40 next plan allows 25C41 now", "observed": "schema missing", "status": "STOP"})
    return rows


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output-dir", default=None)
    ap.add_argument("--fx-output-root", default=None)
    args = ap.parse_args(argv)

    fx_root = Path(args.fx_output_root).resolve() if args.fx_output_root else default_fx_outputs()
    out = Path(args.output_dir).resolve() if args.output_dir else fx_root / OUT_DIR
    lp(out).mkdir(parents=True, exist_ok=True)

    base40 = fx_root / IN40
    req = {
        "s40": base40 / "02_25c40_coreb_g1_right_only_recovery_input_availability_summary.json",
        "evidence": base40 / "04_25c40_right_only_evidence_availability_matrix.csv",
        "readiness": base40 / "05_25c40_row_level_recovery_readiness_matrix.csv",
        "requirements": base40 / "06_25c40_missing_artifact_export_requirement_matrix.csv",
        "gates": base40 / "08_25c40_acceptance_gate_matrix.csv",
        "next_plan": base40 / "09_25c40_next_step_plan.csv",
    }
    input_audit = pd.DataFrame([{"role": k, "path": str(v), "exists": lp(v).exists(), "status": status_from_exists(v)} for k, v in req.items()])
    write_csv(out / "03_25c41_input_audit.csv", input_audit)

    if not bool(input_audit["exists"].all()):
        summary = {
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "step": STEP,
            "status": STOP,
            "audit_only": True,
            "plan_only": True,
            "export_executed": False,
            "dry_run_executed": False,
            "condition_changed": False,
            "source_recovery_executed": False,
            "source_mutation_executed": False,
            "coreb_live_evaluator_unblocked": False,
            "ai_api_called": False,
            "total_stop_rows": int((input_audit["status"] == "STOP").sum()),
        }
        write_json(out / "02_25c41_coreb_g1_right_only_row_level_export_plan_summary.json", summary)
        return 2

    s40 = read_json(req["s40"])
    evidence = read_csv(req["evidence"])
    readiness = read_csv(req["readiness"])
    requirements = read_csv(req["requirements"])
    gates40 = read_csv(req["gates"])
    next40 = read_csv(req["next_plan"])

    contract_audit = pd.DataFrame(contract_rows_from_25c40(s40, next40))
    if bool((contract_audit["status"] == "STOP").any()):
        write_csv(out / "04_25c41_future_export_input_contract.csv", pd.DataFrame())
        write_csv(out / "05_25c41_future_export_output_schema_contract.csv", pd.DataFrame())
        write_csv(out / "06_25c41_future_export_reconciliation_contract.csv", contract_audit)
        write_csv(out / "07_25c41_execution_boundary_matrix.csv", pd.DataFrame())
        write_csv(out / "08_25c41_acceptance_gate_matrix.csv", contract_audit)
        write_csv(out / "09_25c41_next_step_plan.csv", pd.DataFrame([{"rank": 1, "next_step": "STOP", "allowed_now": False, "purpose": "25C40 contract unsafe"}]))
        summary = {
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "step": STEP,
            "status": STOP_CONTRACT,
            "audit_only": True,
            "plan_only": True,
            "export_executed": False,
            "dry_run_executed": False,
            "condition_changed": False,
            "source_recovery_executed": False,
            "source_mutation_executed": False,
            "coreb_live_evaluator_unblocked": False,
            "ai_api_called": False,
            "total_stop_rows": int((contract_audit["status"] == "STOP").sum()),
        }
        write_json(out / "02_25c41_coreb_g1_right_only_row_level_export_plan_summary.json", summary)
        return 2

    future_inputs = pd.DataFrame([
        {"input_id": "IN001", "required": True, "future_step": "25C42", "role": "25C36 summary", "path": "FX_OUTPUTS/gold_v2_25c36_coreb_g1_over_narrowing_adjustment_plan_audit_only/02_25c36_coreb_g1_over_narrowing_adjustment_plan_summary.json", "purpose": "verify accepted adjusted bundle source contract", "read_in_25c41": False},
        {"input_id": "IN002", "required": True, "future_step": "25C42", "role": "25C36 adjusted bundles", "path": "FX_OUTPUTS/gold_v2_25c36_coreb_g1_over_narrowing_adjustment_plan_audit_only/04_25c36_adjusted_bundle_candidate_matrix.csv", "purpose": "variant list and bundle metadata", "read_in_25c41": False},
        {"input_id": "IN003", "required": True, "future_step": "25C42", "role": "25C36 adjusted membership", "path": "FX_OUTPUTS/gold_v2_25c36_coreb_g1_over_narrowing_adjustment_plan_audit_only/05_25c36_adjusted_bundle_membership.csv", "purpose": "filters excluded per variant", "read_in_25c41": False},
        {"input_id": "IN004", "required": True, "future_step": "25C42", "role": "25C10 filter replay rows", "path": "FX_OUTPUTS/gold_v2_25c10_coreb_target_filter_contract_replay_dry_run_audit_only/04_25c10_filter_replay_signal_rows.csv", "purpose": "source replay rows used by 25C37 compare construction", "read_in_25c41": False},
        {"input_id": "IN005", "required": True, "future_step": "25C42", "role": "25C15 selected policy summary", "path": "FX_OUTPUTS/gold_v2_25c15_coreb_selected_policy_replay_contract_audit_only/02_25c15_coreb_selected_policy_replay_contract_summary.json", "purpose": "selected output policies", "read_in_25c41": False},
        {"input_id": "IN006", "required": True, "future_step": "25C42", "role": "25C7 target compare window summary", "path": "FX_OUTPUTS/gold_v2_25c7_coreb_target_compare_mismatch_triage_audit_only/02_25c7_coreb_target_compare_mismatch_triage_summary.json", "purpose": "feature_min_time and feature_max_time", "read_in_25c41": False},
        {"input_id": "IN007", "required": True, "future_step": "25C42", "role": "25B3 shortlist file audit", "path": "FX_OUTPUTS/gold_v2_25b3_coreb_source_shortlist_content_audit_only/gold_v2_25b3_shortlist_file_content_audit.csv", "purpose": "resolve audited target ledger path", "read_in_25c41": False},
    ])
    write_csv(out / "04_25c41_future_export_input_contract.csv", future_inputs)

    schema_rows = []
    cols = [
        ("variant", "string", True, "adjusted variant or BASELINE_CURRENT"),
        ("dataset", "string", True, "target/replay dataset key"),
        ("entry_time", "string", True, "entry time key as exported by source artifacts"),
        ("policy", "string", True, "selected policy key"),
        ("_merge", "string", True, "outer-merge classification: both/left_only/right_only"),
        ("replay_present", "bool", True, "row exists in adjusted replay side"),
        ("target_present", "bool", True, "row exists in target side"),
        ("baseline_merge", "string", True, "BASELINE_CURRENT merge class for the same key"),
        ("baseline_replay_present", "bool", True, "row exists in baseline replay side"),
        ("baseline_target_present", "bool", True, "row exists in baseline target side"),
        ("adjusted_replay_present", "bool", True, "row exists in adjusted replay side"),
        ("adjusted_target_present", "bool", True, "row exists in adjusted target side"),
        ("right_only_reason", "string", True, "why this key is target-only after adjustment"),
        ("source_step", "string", True, "step that produced the row-level export"),
        ("source_artifact", "string", True, "artifact path used to derive the row"),
    ]
    for i, (name, dtype, required, desc) in enumerate(cols, 1):
        schema_rows.append({"column_order": i, "column": name, "dtype": dtype, "required": required, "description": desc})
    schema = pd.DataFrame(schema_rows)
    write_csv(out / "05_25c41_future_export_output_schema_contract.csv", schema)

    recon = pd.DataFrame([
        {"variant": "A001_PRIMARY_PLUS_TOP_RETAINER_PLUS_SC8", "expected_both": 68, "expected_left_only": 369, "expected_right_only": 178, "source": "25C37/25C38 aggregate compare artifacts", "future_25c42_stop_if_mismatch": True},
        {"variant": "A002_PRIMARY_PLUS_TOP_RETAINER_PLUS_SC8U", "expected_both": 99, "expected_left_only": 545, "expected_right_only": 147, "source": "25C37/25C38 aggregate compare artifacts", "future_25c42_stop_if_mismatch": True},
        {"variant": "A003_PRIMARY_PLUS_TOP_RETAINER_PLUS_SC8_PAIR", "expected_both": 46, "expected_left_only": 225, "expected_right_only": 200, "source": "25C37/25C38 aggregate compare artifacts", "future_25c42_stop_if_mismatch": True},
        {"variant": "A004_PRIMARY_PLUS_TOP_RETAINER_PLUS_SC10_PAIR", "expected_both": 99, "expected_left_only": 545, "expected_right_only": 147, "source": "25C37/25C38 aggregate compare artifacts", "future_25c42_stop_if_mismatch": True},
    ])
    write_csv(out / "06_25c41_future_export_reconciliation_contract.csv", recon)

    boundary = pd.DataFrame([
        {"boundary": "define_future_export_contract", "allowed": True, "observed": True},
        {"boundary": "read_25c40_outputs", "allowed": True, "observed": True},
        {"boundary": "row_level_export_execution", "allowed": False, "observed": False},
        {"boundary": "recompute_coreb_compare", "allowed": False, "observed": False},
        {"boundary": "run_new_dry_run", "allowed": False, "observed": False},
        {"boundary": "change_coreb_conditions", "allowed": False, "observed": False},
        {"boundary": "source_recovery", "allowed": False, "observed": False},
        {"boundary": "source_mutation", "allowed": False, "observed": False},
        {"boundary": "coreb_live_evaluator_unblock", "allowed": False, "observed": False},
        {"boundary": "discord_notification", "allowed": False, "observed": False},
        {"boundary": "mt5_order", "allowed": False, "observed": False},
        {"boundary": "ai_api_call", "allowed": False, "observed": False},
        {"boundary": "live_hook", "allowed": False, "observed": False},
        {"boundary": "final_signal", "allowed": False, "observed": False},
        {"boundary": "no_signal_discord_notify", "allowed": False, "observed": False},
    ])
    write_csv(out / "07_25c41_execution_boundary_matrix.csv", boundary)

    gates = pd.DataFrame([
        {"gate_id": "G001", "gate": "25C40 contract safe", "observed": True, "status": "PASS"},
        {"gate_id": "G002", "gate": "row-level export contract created", "observed": True, "status": "PASS"},
        {"gate_id": "G003", "gate": "25C42 row-level export execution allowed now", "observed": False, "status": "BLOCKED_HUMAN_ACCEPTANCE_REQUIRED"},
        {"gate_id": "G004", "gate": "future dry-run execution allowed now", "observed": False, "status": "BLOCKED_HUMAN_ACCEPTANCE_REQUIRED"},
        {"gate_id": "G005", "gate": "CoreB live evaluator unblock", "observed": False, "status": "BLOCKED"},
        {"gate_id": "G006", "gate": "external actions / AI API", "observed": False, "status": "BLOCKED"},
    ])
    write_csv(out / "08_25c41_acceptance_gate_matrix.csv", gates)

    next_plan = pd.DataFrame([
        {"rank": 1, "next_step": "HUMAN_ACCEPT_25C41_BEFORE_25C42_RIGHT_ONLY_ROW_LEVEL_EXPORT", "allowed_now": False, "purpose": "explicit acceptance required before creating/executing any row-level export", "requires_human_acceptance_before_execution": True, "execution_allowed_in_25c41": False},
        {"rank": 2, "next_step": "25C42_COREB_G1_RIGHT_ONLY_ROW_LEVEL_EXPORT_AUDIT_ONLY", "allowed_now": False, "purpose": "future row-level export only after explicit acceptance", "requires_human_acceptance_before_execution": True, "execution_allowed_in_25c41": False},
        {"rank": 3, "next_step": "right_only driver review", "allowed_now": False, "purpose": "blocked until row-level export exists and reconciles", "requires_human_acceptance_before_execution": False, "execution_allowed_in_25c41": False},
        {"rank": 4, "next_step": "CoreB live evaluator / final signal / Discord / MT5 / AI API", "allowed_now": False, "purpose": "blocked because no exact match and no source recovery approval", "requires_human_acceptance_before_execution": True, "execution_allowed_in_25c41": False},
    ])
    write_csv(out / "09_25c41_next_step_plan.csv", next_plan)

    unnecessary = ["raw OHLC", "old GOLD/DISC8 files", "source recovery files", "row-level export output", "new dry-run outputs", "AI review ledgers"]
    necessary = [
        "01_25c41_GOLD_V2_COREB_G1_RIGHT_ONLY_ROW_LEVEL_EXPORT_PLAN_AUDIT_ONLY_REPORT.md",
        "02_25c41_coreb_g1_right_only_row_level_export_plan_summary.json",
        "03_25c41_input_audit.csv",
        "04_25c41_future_export_input_contract.csv",
        "05_25c41_future_export_output_schema_contract.csv",
        "06_25c41_future_export_reconciliation_contract.csv",
        "07_25c41_execution_boundary_matrix.csv",
        "08_25c41_acceptance_gate_matrix.csv",
        "09_25c41_next_step_plan.csv",
    ]
    write_csv(
        out / "00_不要_25c41_file_request_list.csv",
        pd.DataFrame(
            [{"section": "00_不要_貼らなくてOK", "rank": i + 1, "item": x} for i, x in enumerate(unnecessary)]
            + [{"section": "必要・見るファイル", "rank": i + 1, "item": x} for i, x in enumerate(necessary)]
        ),
    )

    summary = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "step": STEP,
        "status": STATUS,
        "audit_only": True,
        "plan_only": True,
        "export_contract_created": True,
        "export_executed": False,
        "dry_run_executed": False,
        "condition_changed": False,
        "full_coreb_parity": False,
        "source_recovery_executed": False,
        "source_mutation_executed": False,
        "coreb_live_evaluator_unblocked": False,
        "discord_notification_sent": False,
        "mt5_order_sent": False,
        "ai_api_called": False,
        "live_hook_executed": False,
        "final_signal_created": False,
        "no_signal_discord_notify": False,
        "future_export_output_dir": "FX_OUTPUTS/gold_v2_25c42_coreb_g1_right_only_row_level_export_audit_only/",
        "future_export_required_input_count": int(len(future_inputs)),
        "future_export_required_column_count": int(len(schema)),
        "future_export_reconciliation_variant_count": int(len(recon)),
        "next_recommended_step": "HUMAN_ACCEPT_25C41_BEFORE_25C42_RIGHT_ONLY_ROW_LEVEL_EXPORT",
        "requires_human_acceptance_before_25c42": True,
        "total_stop_rows": 0,
    }
    write_json(out / "02_25c41_coreb_g1_right_only_row_level_export_plan_summary.json", summary)

    report = "\n".join([
        "# GOLD V2 25C41 CoreB G1 right_only row-level export plan audit-only report",
        "",
        f"Created UTC: {summary['created_utc']}",
        f"Step: `{STEP}`",
        f"Status: `{STATUS}`",
        "",
        "## Scope",
        "",
        "This is an export contract plan only. It reads 25C40 outputs and does not export rows, recompute CoreB, or run a new dry-run.",
        "",
        "## 25C40 contract audit",
        "",
        md_table(contract_audit),
        "",
        "## Future export input contract",
        "",
        md_table(future_inputs),
        "",
        "## Future export output schema contract",
        "",
        md_table(schema),
        "",
        "## Future export reconciliation contract",
        "",
        md_table(recon),
        "",
        "## Execution boundaries",
        "",
        md_table(boundary),
        "",
        "## Acceptance gates",
        "",
        md_table(gates),
        "",
        "## File request list",
        "",
        "```text",
        "00_不要_貼らなくてOK",
        *[f"00-{i+1}. {x}" for i, x in enumerate(unnecessary)],
        "",
        "必要・見るファイル",
        *[f"{i+1:02d}. {x}" for i, x in enumerate(necessary)],
        "```",
        "",
        "## Next step plan",
        "",
        md_table(next_plan),
        "",
        "## Safety",
        "",
        "- 25C41 does not execute row-level export, recomputation, dry-run, source recovery, source mutation, condition change, live evaluator, Discord, MT5, AI API, live hook, or final signal.",
        "- 25C42 export remains blocked until explicit human acceptance.",
        "- Future dry-run remains blocked until a separate explicit human acceptance gate.",
        "- NO_SIGNAL must not notify Discord.",
    ])
    lp(out / "01_25c41_GOLD_V2_COREB_G1_RIGHT_ONLY_ROW_LEVEL_EXPORT_PLAN_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")

    print(json.dumps({
        "status": STATUS,
        "export_contract_created": True,
        "export_executed": False,
        "dry_run_executed": False,
        "ai_api_called": False,
        "next_recommended_step": summary["next_recommended_step"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
