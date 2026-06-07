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

STEP = "25C40_COREB_G1_RIGHT_ONLY_RECOVERY_INPUT_AVAILABILITY_AUDIT_ONLY"
STATUS_READY = "COREB_G1_RIGHT_ONLY_RECOVERY_INPUT_AVAILABILITY_AUDIT_COMPLETED_AUDIT_ONLY_DRIVER_REVIEW_READY"
STATUS_EXPORT_REQUIRED = "COREB_G1_RIGHT_ONLY_RECOVERY_INPUT_AVAILABILITY_AUDIT_COMPLETED_AUDIT_ONLY_ROW_LEVEL_EXPORT_PLAN_REQUIRED"
STOP = "25C40_STOP_MISSING_INPUT_AUDIT_ONLY"
STOP_CONTRACT = "25C40_STOP_25C39_CONTRACT_UNSAFE_AUDIT_ONLY"

OUT_DIR = "gold_v2_25c40_coreb_g1_right_only_recovery_input_availability_audit_only"
IN39 = "gold_v2_25c39_coreb_g1_remaining_mismatch_route_plan_audit_only"
IN38 = "gold_v2_25c38_coreb_g1_adjusted_narrowing_result_review_audit_only"
IN37 = "gold_v2_25c37_coreb_g1_adjusted_narrowing_dry_run_audit_only"

EXPECTED_STEP_39 = "25C39_COREB_G1_REMAINING_MISMATCH_ROUTE_PLAN_AUDIT_ONLY"
EXPECTED_STATUS_39 = "COREB_G1_REMAINING_MISMATCH_ROUTE_PLAN_READY_AUDIT_ONLY_NEXT_AUDIT_REQUIRED"
EXPECTED_ROUTE_39 = "RIGHT_ONLY_RECOVERY_INPUT_AVAILABILITY_AUDIT_FIRST"
EXPECTED_NEXT_39 = "25C40_COREB_G1_RIGHT_ONLY_RECOVERY_INPUT_AVAILABILITY_AUDIT_ONLY"


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


def inspect_csv(path: Path, role: str, expected_merge: str = "right_only") -> dict:
    row = {
        "role": role,
        "path": str(path),
        "exists": lp(path).exists(),
        "readable": False,
        "row_count": 0,
        "columns": "",
        "has_variant": False,
        "has_dataset": False,
        "has_entry_time": False,
        "has_policy": False,
        "has_merge": False,
        "has_right_only_count": False,
        "contains_right_only_rows": False,
        "right_only_row_count": 0,
        "row_level_right_only_available": False,
        "aggregate_right_only_available": False,
        "evidence_grade": "MISSING",
        "note": "file missing",
    }
    if not row["exists"]:
        return row
    try:
        df = read_csv(path)
    except Exception as e:
        row["note"] = f"read failed: {e}"
        return row
    cols = [str(c) for c in df.columns]
    colset = set(cols)
    row.update({
        "readable": True,
        "row_count": int(len(df)),
        "columns": ";".join(cols),
        "has_variant": "variant" in colset,
        "has_dataset": "dataset" in colset,
        "has_entry_time": "entry_time" in colset,
        "has_policy": "policy" in colset,
        "has_merge": "_merge" in colset,
        "has_right_only_count": "right_only" in colset or "right_only_increase" in colset,
    })
    if "_merge" in colset:
        right_mask = df["_merge"].astype(str).str.lower().eq(expected_merge.lower())
        row["contains_right_only_rows"] = bool(right_mask.any())
        row["right_only_row_count"] = int(right_mask.sum())
    row_level = all(row[f"has_{c}"] for c in ["variant", "dataset", "entry_time", "policy", "merge"]) and row["contains_right_only_rows"]
    aggregate = row["has_right_only_count"] or (row["has_merge"] and "entry_rows" in colset)
    row["row_level_right_only_available"] = bool(row_level)
    row["aggregate_right_only_available"] = bool(aggregate)
    if row_level:
        row["evidence_grade"] = "ROW_LEVEL_RIGHT_ONLY_READY"
        row["note"] = "contains variant/dataset/entry_time/policy/_merge right_only rows"
    elif aggregate:
        row["evidence_grade"] = "AGGREGATE_ONLY"
        row["note"] = "right_only information exists only as counts or grouped aggregates; row-level driver review is not ready"
    elif row["has_entry_time"] and row["has_merge"]:
        row["evidence_grade"] = "ROW_LEVEL_NOT_RIGHT_ONLY"
        row["note"] = "row-level file exists but does not contain right_only rows"
    else:
        row["evidence_grade"] = "NO_RIGHT_ONLY_EVIDENCE"
        row["note"] = "no usable right_only evidence columns detected"
    return row


def contract_rows_from_25c39(s39: dict, next_plan: pd.DataFrame) -> list[dict]:
    checks = [
        ("C001", "25C39 step matches expected", s39.get("step") == EXPECTED_STEP_39, s39.get("step")),
        ("C002", "25C39 status is next-audit-required", s39.get("status") == EXPECTED_STATUS_39, s39.get("status")),
        ("C003", "25C39 audit_only true", as_bool(s39.get("audit_only", False)) is True, s39.get("audit_only")),
        ("C004", "25C39 plan_only true", as_bool(s39.get("plan_only", False)) is True, s39.get("plan_only")),
        ("C005", "25C39 dry_run_executed false", as_bool(s39.get("dry_run_executed", True)) is False, s39.get("dry_run_executed")),
        ("C006", "25C39 condition_changed false", as_bool(s39.get("condition_changed", True)) is False, s39.get("condition_changed")),
        ("C007", "25C39 source recovery false", as_bool(s39.get("source_recovery_executed", True)) is False, s39.get("source_recovery_executed")),
        ("C008", "25C39 source mutation false", as_bool(s39.get("source_mutation_executed", True)) is False, s39.get("source_mutation_executed")),
        ("C009", "25C39 CoreB live unblock false", as_bool(s39.get("coreb_live_evaluator_unblocked", True)) is False, s39.get("coreb_live_evaluator_unblocked")),
        ("C010", "25C39 AI API false", as_bool(s39.get("ai_api_called", True)) is False, s39.get("ai_api_called")),
        ("C011", "25C39 selected route is right_only input availability audit", s39.get("selected_route") == EXPECTED_ROUTE_39, s39.get("selected_route")),
        ("C012", "25C39 next recommended step is 25C40", s39.get("next_recommended_step") == EXPECTED_NEXT_39, s39.get("next_recommended_step")),
        ("C013", "25C39 future dry-run still requires human acceptance", as_bool(s39.get("requires_human_acceptance_before_next_dry_run", False)) is True, s39.get("requires_human_acceptance_before_next_dry_run")),
    ]
    rows = [{"contract_id": cid, "check": check, "observed": observed, "status": "PASS" if passed else "STOP"} for cid, check, passed, observed in checks]
    if not next_plan.empty and {"next_step", "allowed_now"}.issubset(next_plan.columns):
        m = next_plan[next_plan["next_step"].astype(str).eq(EXPECTED_NEXT_39)]
        passed = not m.empty and as_bool(m.iloc[0]["allowed_now"]) is True
        rows.append({
            "contract_id": "C014",
            "check": "25C39 next plan allows 25C40 now",
            "observed": "" if m.empty else str(m.iloc[0].to_dict()),
            "status": "PASS" if passed else "STOP",
        })
    else:
        rows.append({"contract_id": "C014", "check": "25C39 next plan allows 25C40 now", "observed": "schema missing", "status": "STOP"})
    return rows


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output-dir", default=None)
    ap.add_argument("--fx-output-root", default=None)
    args = ap.parse_args(argv)

    fx_root = Path(args.fx_output_root).resolve() if args.fx_output_root else default_fx_outputs()
    out = Path(args.output_dir).resolve() if args.output_dir else fx_root / OUT_DIR
    lp(out).mkdir(parents=True, exist_ok=True)

    base39 = fx_root / IN39
    req = {
        "s39": base39 / "02_25c39_coreb_g1_remaining_mismatch_route_plan_summary.json",
        "route_recommendation": base39 / "05_25c39_route_recommendation_matrix.csv",
        "execution_boundary": base39 / "06_25c39_execution_boundary_matrix.csv",
        "acceptance_gates": base39 / "07_25c39_acceptance_gate_matrix.csv",
        "next_plan": base39 / "08_25c39_next_step_plan.csv",
    }
    input_audit = pd.DataFrame([{"role": k, "path": str(v), "exists": lp(v).exists(), "status": status_from_exists(v)} for k, v in req.items()])
    write_csv(out / "03_25c40_input_audit.csv", input_audit)

    if not bool(input_audit["exists"].all()):
        summary = {
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "step": STEP,
            "status": STOP,
            "audit_only": True,
            "input_availability_audit_only": True,
            "dry_run_executed": False,
            "condition_changed": False,
            "source_recovery_executed": False,
            "source_mutation_executed": False,
            "coreb_live_evaluator_unblocked": False,
            "discord_notification_sent": False,
            "mt5_order_sent": False,
            "ai_api_called": False,
            "live_hook_executed": False,
            "final_signal_created": False,
            "total_stop_rows": int((input_audit["status"] == "STOP").sum()),
        }
        write_json(out / "02_25c40_coreb_g1_right_only_recovery_input_availability_summary.json", summary)
        return 2

    s39 = read_json(req["s39"])
    route_rec = read_csv(req["route_recommendation"])
    boundary39 = read_csv(req["execution_boundary"])
    gates39 = read_csv(req["acceptance_gates"])
    next39 = read_csv(req["next_plan"])

    contract_rows = contract_rows_from_25c39(s39, next39)
    contract_audit = pd.DataFrame(contract_rows)
    if bool((contract_audit["status"] == "STOP").any()):
        write_csv(out / "04_25c40_right_only_evidence_availability_matrix.csv", pd.DataFrame())
        write_csv(out / "05_25c40_row_level_recovery_readiness_matrix.csv", pd.DataFrame())
        write_csv(out / "06_25c40_missing_artifact_export_requirement_matrix.csv", contract_audit)
        write_csv(out / "07_25c40_execution_boundary_matrix.csv", pd.DataFrame())
        write_csv(out / "08_25c40_acceptance_gate_matrix.csv", contract_audit)
        write_csv(out / "09_25c40_next_step_plan.csv", pd.DataFrame([{"rank": 1, "next_step": "STOP", "allowed_now": False, "purpose": "25C39 contract unsafe"}]))
        summary = {
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "step": STEP,
            "status": STOP_CONTRACT,
            "audit_only": True,
            "input_availability_audit_only": True,
            "dry_run_executed": False,
            "condition_changed": False,
            "source_recovery_executed": False,
            "source_mutation_executed": False,
            "coreb_live_evaluator_unblocked": False,
            "discord_notification_sent": False,
            "mt5_order_sent": False,
            "ai_api_called": False,
            "live_hook_executed": False,
            "final_signal_created": False,
            "total_stop_rows": int((contract_audit["status"] == "STOP").sum()),
        }
        write_json(out / "02_25c40_coreb_g1_right_only_recovery_input_availability_summary.json", summary)
        return 2

    candidates = [
        (fx_root / IN37 / "05_25c37_variant_compare_matrix.csv", "25C37 variant compare matrix"),
        (fx_root / IN37 / "06_25c37_variant_delta_matrix.csv", "25C37 variant delta matrix"),
        (fx_root / IN37 / "07_25c37_variant_by_dataset_policy.csv", "25C37 variant by dataset/policy aggregate"),
        (fx_root / IN37 / "08_25c37_best_variant_left_only_samples.csv", "25C37 best variant left_only sample rows"),
        (fx_root / IN37 / "09_25c37_acceptance_gate_matrix.csv", "25C37 acceptance gates"),
        (fx_root / IN38 / "04_25c38_adjusted_variant_tradeoff_matrix.csv", "25C38 adjusted variant tradeoff aggregate"),
        (fx_root / IN38 / "05_25c38_best_variant_review_matrix.csv", "25C38 best variant review aggregate"),
        (fx_root / IN38 / "06_25c38_remaining_mismatch_decision_matrix.csv", "25C38 decision matrix"),
        (fx_root / IN39 / "05_25c39_route_recommendation_matrix.csv", "25C39 route recommendation matrix"),
    ]

    existing_candidate_paths = {p for p, _ in candidates}
    for d in [fx_root / IN37, fx_root / IN38, fx_root / IN39]:
        if lp(d).exists():
            for p in sorted(d.glob("*right_only*.csv")):
                if p not in existing_candidate_paths:
                    candidates.append((p, "auto-scanned right_only-named CSV"))
                    existing_candidate_paths.add(p)

    evidence = pd.DataFrame([inspect_csv(path, role) for path, role in candidates])
    write_csv(out / "04_25c40_right_only_evidence_availability_matrix.csv", evidence)

    row_level_files = evidence[evidence["row_level_right_only_available"] == True] if not evidence.empty else pd.DataFrame()
    aggregate_files = evidence[evidence["aggregate_right_only_available"] == True] if not evidence.empty else pd.DataFrame()
    row_level_ready = not row_level_files.empty
    aggregate_available = not aggregate_files.empty

    readiness = pd.DataFrame([
        {"readiness_id": "R001", "check": "aggregate right_only counts available", "observed": aggregate_available, "status": "PASS" if aggregate_available else "MISSING"},
        {"readiness_id": "R002", "check": "row-level right_only keys available", "observed": row_level_ready, "status": "PASS" if row_level_ready else "MISSING"},
        {"readiness_id": "R003", "check": "right_only rows include variant/dataset/entry_time/policy/_merge", "observed": row_level_ready, "status": "PASS" if row_level_ready else "MISSING"},
        {"readiness_id": "R004", "check": "driver review can start without new export", "observed": row_level_ready, "status": "READY" if row_level_ready else "BLOCKED_EXPORT_PLAN_REQUIRED"},
        {"readiness_id": "R005", "check": "dry-run needed in 25C40", "observed": False, "status": "PASS"},
        {"readiness_id": "R006", "check": "AI API needed in 25C40", "observed": False, "status": "PASS"},
    ])
    write_csv(out / "05_25c40_row_level_recovery_readiness_matrix.csv", readiness)

    missing = pd.DataFrame([
        {
            "requirement_id": "REQ001",
            "required_artifact": "right_only row-level compare rows for each adjusted variant",
            "required_columns": "variant;dataset;entry_time;policy;_merge",
            "available_now": row_level_ready,
            "current_best_available": "aggregate counts only" if aggregate_available and not row_level_ready else ("row-level right_only exists" if row_level_ready else "none"),
            "why_needed": "identify which target-matching rows became right_only after adjusted narrowing",
            "safe_next_action": "25C41_COREB_G1_RIGHT_ONLY_ROW_LEVEL_EXPORT_PLAN_AUDIT_ONLY" if not row_level_ready else "25C41_COREB_G1_RIGHT_ONLY_DRIVER_REVIEW_AUDIT_ONLY",
            "dry_run_allowed": False,
            "source_recovery_allowed": False,
        },
        {
            "requirement_id": "REQ002",
            "required_artifact": "baseline vs adjusted variant row-level merge classification",
            "required_columns": "variant;dataset;entry_time;policy;_merge;baseline_presence;adjusted_presence;target_presence",
            "available_now": False,
            "current_best_available": "not exported by 25C37/25C38/25C39 standard outputs",
            "why_needed": "separate harmless narrowing from target-damaging narrowing before proposing another bundle",
            "safe_next_action": "plan export contract only; no execution without later gate if recomputation is required",
            "dry_run_allowed": False,
            "source_recovery_allowed": False,
        },
    ])
    write_csv(out / "06_25c40_missing_artifact_export_requirement_matrix.csv", missing)

    boundary = pd.DataFrame([
        {"boundary": "input_availability_audit", "allowed": True, "observed": True},
        {"boundary": "read_25c39_outputs", "allowed": True, "observed": True},
        {"boundary": "read_existing_25c37_25c38_artifacts", "allowed": True, "observed": True},
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
    write_csv(out / "07_25c40_execution_boundary_matrix.csv", boundary)

    gates = pd.DataFrame([
        {"gate_id": "G001", "gate": "25C39 contract safe", "observed": True, "status": "PASS"},
        {"gate_id": "G002", "gate": "aggregate right_only evidence available", "observed": aggregate_available, "status": "PASS" if aggregate_available else "MISSING"},
        {"gate_id": "G003", "gate": "row-level right_only evidence available", "observed": row_level_ready, "status": "PASS" if row_level_ready else "BLOCKED_EXPORT_PLAN_REQUIRED"},
        {"gate_id": "G004", "gate": "driver review can execute now", "observed": row_level_ready, "status": "PASS" if row_level_ready else "BLOCKED"},
        {"gate_id": "G005", "gate": "future row-level export/recompute allowed now", "observed": False, "status": "BLOCKED_PLAN_REQUIRED"},
        {"gate_id": "G006", "gate": "future dry-run execution allowed now", "observed": False, "status": "BLOCKED_HUMAN_ACCEPTANCE_REQUIRED"},
        {"gate_id": "G007", "gate": "CoreB live evaluator unblock", "observed": False, "status": "BLOCKED"},
        {"gate_id": "G008", "gate": "external actions / AI API", "observed": False, "status": "BLOCKED"},
    ])
    write_csv(out / "08_25c40_acceptance_gate_matrix.csv", gates)

    if row_level_ready:
        next1 = "25C41_COREB_G1_RIGHT_ONLY_DRIVER_REVIEW_AUDIT_ONLY"
        purpose1 = "use existing row-level right_only artifact to identify target-damaging drivers; no dry-run"
        status = STATUS_READY
    else:
        next1 = "25C41_COREB_G1_RIGHT_ONLY_ROW_LEVEL_EXPORT_PLAN_AUDIT_ONLY"
        purpose1 = "define exact row-level export contract needed for right_only driver review; no dry-run"
        status = STATUS_EXPORT_REQUIRED

    next_plan = pd.DataFrame([
        {"rank": 1, "next_step": next1, "allowed_now": True, "purpose": purpose1, "requires_human_acceptance_before_execution": False, "execution_allowed_in_25c40": False},
        {"rank": 2, "next_step": "future right_only row-level export/recompute", "allowed_now": False, "purpose": "requires 25C41 export contract and explicit acceptance if recomputation/export execution is needed", "requires_human_acceptance_before_execution": True, "execution_allowed_in_25c40": False},
        {"rank": 3, "next_step": "future adjusted narrowing dry-run", "allowed_now": False, "purpose": "requires driver review, a separate plan, and explicit human acceptance gate", "requires_human_acceptance_before_execution": True, "execution_allowed_in_25c40": False},
        {"rank": 4, "next_step": "CoreB live evaluator / final signal / Discord / MT5 / AI API", "allowed_now": False, "purpose": "blocked because no exact match and no source recovery approval", "requires_human_acceptance_before_execution": True, "execution_allowed_in_25c40": False},
    ])
    write_csv(out / "09_25c40_next_step_plan.csv", next_plan)

    unnecessary = ["raw OHLC", "old GOLD/DISC8 files", "source recovery files", "new dry-run outputs", "AI review ledgers"]
    necessary = [
        "01_25c40_GOLD_V2_COREB_G1_RIGHT_ONLY_RECOVERY_INPUT_AVAILABILITY_AUDIT_ONLY_REPORT.md",
        "02_25c40_coreb_g1_right_only_recovery_input_availability_summary.json",
        "03_25c40_input_audit.csv",
        "04_25c40_right_only_evidence_availability_matrix.csv",
        "05_25c40_row_level_recovery_readiness_matrix.csv",
        "06_25c40_missing_artifact_export_requirement_matrix.csv",
        "07_25c40_execution_boundary_matrix.csv",
        "08_25c40_acceptance_gate_matrix.csv",
        "09_25c40_next_step_plan.csv",
    ]
    write_csv(
        out / "00_不要_25c40_file_request_list.csv",
        pd.DataFrame(
            [{"section": "00_不要_貼らなくてOK", "rank": i + 1, "item": x} for i, x in enumerate(unnecessary)]
            + [{"section": "必要・見るファイル", "rank": i + 1, "item": x} for i, x in enumerate(necessary)]
        ),
    )

    summary = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "step": STEP,
        "status": status,
        "audit_only": True,
        "input_availability_audit_only": True,
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
        "aggregate_right_only_evidence_available": aggregate_available,
        "row_level_right_only_evidence_available": row_level_ready,
        "row_level_right_only_file_count": int(len(row_level_files)) if not row_level_files.empty else 0,
        "right_only_driver_review_ready": row_level_ready,
        "row_level_export_plan_required": not row_level_ready,
        "selected_route_from_25c39": s39.get("selected_route"),
        "next_recommended_step": next1,
        "requires_human_acceptance_before_next_dry_run": True,
        "total_stop_rows": 0,
    }
    write_json(out / "02_25c40_coreb_g1_right_only_recovery_input_availability_summary.json", summary)

    report = "\n".join([
        "# GOLD V2 25C40 CoreB G1 right_only recovery input availability audit-only report",
        "",
        f"Created UTC: {summary['created_utc']}",
        f"Step: `{STEP}`",
        f"Status: `{status}`",
        "",
        "## Scope",
        "",
        "This is an input availability audit only. It checks existing 25C37/25C38/25C39 artifacts for row-level right_only evidence and does not run a new dry-run.",
        "",
        "## 25C39 contract audit",
        "",
        md_table(contract_audit),
        "",
        "## Right-only evidence availability matrix",
        "",
        md_table(evidence),
        "",
        "## Row-level recovery readiness matrix",
        "",
        md_table(readiness),
        "",
        "## Missing artifact / export requirement matrix",
        "",
        md_table(missing),
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
        "- 25C40 does not execute a dry-run, source recovery, source mutation, condition change, live evaluator, Discord, MT5, AI API, live hook, or final signal.",
        "- If row-level right_only evidence is missing, the next step is an export plan only, not an export execution.",
        "- Future dry-run remains blocked until a separate explicit human acceptance gate.",
        "- NO_SIGNAL must not notify Discord.",
    ])
    lp(out / "01_25c40_GOLD_V2_COREB_G1_RIGHT_ONLY_RECOVERY_INPUT_AVAILABILITY_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")

    print(json.dumps({
        "status": status,
        "aggregate_right_only_evidence_available": aggregate_available,
        "row_level_right_only_evidence_available": row_level_ready,
        "next_recommended_step": next1,
        "dry_run_executed": False,
        "ai_api_called": False,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
