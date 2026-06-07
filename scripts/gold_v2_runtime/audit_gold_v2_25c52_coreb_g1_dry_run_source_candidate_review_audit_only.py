#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import csv
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Sequence

import pandas as pd

STEP = "25C52_COREB_G1_DRY_RUN_SOURCE_CANDIDATE_REVIEW_AUDIT_ONLY"
STATUS = "COREB_G1_DRY_RUN_SOURCE_CANDIDATE_REVIEW_READY_AUDIT_ONLY_SOURCE_BOUND_FOR_PLANNING_EXECUTION_BLOCKED"
STOP_MISSING = "25C52_STOP_MISSING_INPUT_AUDIT_ONLY"
STOP_CONTRACT = "25C52_STOP_25C51_CONTRACT_UNSAFE_AUDIT_ONLY"
STOP_CANDIDATE = "25C52_STOP_SOURCE_CANDIDATE_UNSAFE_AUDIT_ONLY"
IN51 = "gold_v2_25c51_coreb_g1_dry_run_source_concretion_review_audit_only"
OUT_DIR = "gold_v2_25c52_coreb_g1_dry_run_source_candidate_review_audit_only"
EXPECTED_51_STEP = "25C51_COREB_G1_DRY_RUN_SOURCE_CONCRETION_REVIEW_AUDIT_ONLY"
EXPECTED_51_STATUS = "COREB_G1_DRY_RUN_SOURCE_CONCRETION_REVIEW_READY_AUDIT_ONLY_SOURCE_CANDIDATE_REVIEW_REQUIRED"
EXPECTED_NEXT_IN_51 = STEP
NEXT_STEP = "25C53_COREB_G1_DRY_RUN_PREFLIGHT_SPEC_AUDIT_ONLY"
EXPECTED_FILTERS = ["same_count>=2&unique_origins>=2", "unique_origins>=2"]
EXPECTED_TOP_CANDIDATE = "gold_v2_25c10_coreb_target_filter_contract_replay_dry_run_audit_only/04_25c10_filter_replay_signal_rows.csv"


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def files_root() -> Path:
    r = repo_root()
    return r.parents[1] if len(r.parents) >= 2 else r.parent


def fx_outputs() -> Path:
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


def as_bool(v: object) -> bool:
    return v if isinstance(v, bool) else str(v).strip().lower() in {"true", "1", "yes", "y"}


def as_int(v: object) -> Optional[int]:
    try:
        return int(v)
    except Exception:
        return None


def md_table(df: pd.DataFrame, n: int = 100) -> str:
    if df.empty:
        return "_No rows._"
    v = df.head(n).copy()
    cols = list(v.columns)
    rows = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for _, r in v.iterrows():
        rows.append("| " + " | ".join(str(r[c]).replace("|", "\\|") for c in cols) + " |")
    return "\n".join(rows)


def exists_row(role: str, p: Path) -> dict:
    ok = lp(p).exists()
    return {"role": role, "path": str(p), "exists": ok, "status": "PASS" if ok else "STOP"}


def file_request_df() -> pd.DataFrame:
    skip = ["raw OHLC", "old GOLD/DISC8", "24-series source recovery execution", "new replay/dry-run outputs", "AI ledgers", "Discord/MT5/live artifacts"]
    keep = [
        "FX_OUTPUTS/gold_v2_25c51_coreb_g1_dry_run_source_concretion_review_audit_only/02_25c51_dry_run_source_concretion_review_summary.json",
        "FX_OUTPUTS/gold_v2_25c51_coreb_g1_dry_run_source_concretion_review_audit_only/06_25c51_source_candidate_matrix.csv",
        "FX_OUTPUTS/gold_v2_25c51_coreb_g1_dry_run_source_concretion_review_audit_only/07_25c51_source_selection_matrix.csv",
        "FX_OUTPUTS/gold_v2_25c10_coreb_target_filter_contract_replay_dry_run_audit_only/04_25c10_filter_replay_signal_rows.csv",
        "FX_OUTPUTS/gold_v2_25c52_coreb_g1_dry_run_source_candidate_review_audit_only/01_25c52_GOLD_V2_COREB_G1_DRY_RUN_SOURCE_CANDIDATE_REVIEW_AUDIT_ONLY_REPORT.md",
        "FX_OUTPUTS/gold_v2_25c52_coreb_g1_dry_run_source_candidate_review_audit_only/02_25c52_dry_run_source_candidate_review_summary.json",
        "FX_OUTPUTS/gold_v2_25c52_coreb_g1_dry_run_source_candidate_review_audit_only/05_25c52_candidate_file_metadata.csv",
        "FX_OUTPUTS/gold_v2_25c52_coreb_g1_dry_run_source_candidate_review_audit_only/07_25c52_source_binding_matrix.csv",
    ]
    return pd.DataFrame(
        [{"section": "00_不要_貼らなくてOK", "rank": i + 1, "item": x} for i, x in enumerate(skip)]
        + [{"section": "必要・見るファイル", "rank": i + 1, "item": x} for i, x in enumerate(keep)]
    )


def execution_boundary_matrix() -> pd.DataFrame:
    rows = [
        ("variant_approval", False, False),
        ("replay_execution", False, False),
        ("dry_run_execution", False, False),
        ("condition_change", False, False),
        ("source_change_or_recovery", False, False),
        ("source_confirmed_for_execution", False, False),
        ("coreb_live_evaluator_unblock", False, False),
        ("discord_notification", False, False),
        ("mt5_order", False, False),
        ("ai_api_call", False, False),
        ("live_hook", False, False),
        ("final_signal", False, False),
        ("no_signal_discord_notify", False, False),
    ]
    return pd.DataFrame([{"boundary_id": f"X{i+1:03d}", "boundary": b, "allowed": a, "observed": o, "status": "PASS" if a == o else "STOP"} for i, (b, a, o) in enumerate(rows)])


def stop_outputs(out: Path, status: str, input_audit: pd.DataFrame, diag: pd.DataFrame, summary51: Optional[dict] = None) -> int:
    summary51 = summary51 or {}
    write_csv(out / "00_不要_25c52_file_request_list.csv", file_request_df())
    write_csv(out / "03_25c52_input_audit.csv", input_audit)
    write_csv(out / "04_25c52_contract_audit.csv", diag)
    write_csv(out / "05_25c52_candidate_file_metadata.csv", diag)
    write_csv(out / "06_25c52_candidate_header_review.csv", diag)
    write_csv(out / "07_25c52_source_binding_matrix.csv", diag)
    boundary = execution_boundary_matrix()
    write_csv(out / "08_25c52_execution_boundary_matrix.csv", boundary)
    gates = pd.DataFrame([
        {"gate_id": "G001", "gate": "25C51 contract safe", "observed": False, "status": "STOP"},
        {"gate_id": "G002", "gate": "source binding for planning", "observed": False, "status": "BLOCKED"},
        {"gate_id": "G003", "gate": "future dry-run execution", "observed": False, "status": "BLOCKED"},
    ])
    write_csv(out / "09_25c52_gates.csv", gates)
    next_plan = pd.DataFrame([{"rank": 1, "next_step": "STOP", "allowed_now": False, "purpose": status, "execution_allowed_in_25c52": False}])
    write_csv(out / "10_25c52_next_step_plan.csv", next_plan)
    notes = pd.DataFrame([
        {"note_id": "N001", "note": "25C52 stopped safely.", "status": status},
        {"note_id": "N002", "note": "No approval, replay, dry-run, source change, live/external action, AI, notification, order, or final signal executed.", "status": "PASS"},
    ])
    write_csv(out / "11_25c52_handoff_notes.csv", notes)
    summary = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "step": STEP,
        "status": status,
        "audit_only": True,
        "source_candidate_review_only": True,
        "input_25c51_step": summary51.get("step"),
        "input_25c51_status": summary51.get("status"),
        "source_binding_status": "STOP",
        "source_confirmed_for_execution": False,
        "future_dry_run_execution_allowed": False,
        "variant_approved": False,
        "replay_executed": False,
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
        "no_signal_discord_notify": False,
        "next_recommended_step": "STOP",
        "total_stop_rows": int((diag.get("status", pd.Series(dtype=str)).astype(str) == "STOP").sum()) if isinstance(diag, pd.DataFrame) else 1,
    }
    write_json(out / "02_25c52_dry_run_source_candidate_review_summary.json", summary)
    report = "\n".join([
        "# GOLD V2 25C52 CoreB G1 dry-run source candidate review audit-only report", "",
        f"Created UTC: {summary['created_utc']}", f"Step: `{STEP}`", f"Status: `{status}`", "",
        "## Stop diagnostic", "", md_table(diag), "",
        "## Input audit", "", md_table(input_audit), "",
        "## Safety", "", "Stopped safely. No dry-run or external action was performed.",
    ])
    lp(out / "01_25c52_GOLD_V2_COREB_G1_DRY_RUN_SOURCE_CANDIDATE_REVIEW_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")
    print(json.dumps({"status": status, "ai_api_called": False, "dry_run_executed": False}, ensure_ascii=False, indent=2))
    return 2


def contract_audit(summary51: dict, contract51: pd.DataFrame, candidates51: pd.DataFrame, selection51: pd.DataFrame, boundary51: pd.DataFrame, gates51: pd.DataFrame, next51: pd.DataFrame) -> pd.DataFrame:
    expected = {
        "step": EXPECTED_51_STEP,
        "status": EXPECTED_51_STATUS,
        "audit_only": True,
        "source_concretion_review_only": True,
        "representative_variant_code": "A002",
        "representative_approval_status": "NOT_APPROVED_REVIEW_ONLY",
        "source_confirmed": False,
        "source_candidate_review_required": True,
        "future_dry_run_execution_allowed": False,
        "top_source_candidate_path": EXPECTED_TOP_CANDIDATE,
        "next_recommended_step": EXPECTED_NEXT_IN_51,
        "total_stop_rows": 0,
    }
    rows = []
    for i, (k, exp) in enumerate(expected.items(), 1):
        obs = summary51.get(k)
        if isinstance(exp, bool):
            ok = as_bool(obs) == exp
        elif isinstance(exp, int):
            ok = as_int(obs) == exp
        else:
            ok = obs == exp
        rows.append({"contract_id": f"C{i:03d}", "check": k, "observed": obs, "expected": exp, "status": "PASS" if ok else "STOP"})
    filters = summary51.get("representative_filters", [])
    rows.append({"contract_id": "C013", "check": "representative_filters exact", "observed": ";".join(filters) if isinstance(filters, list) else filters, "expected": ";".join(EXPECTED_FILTERS), "status": "PASS" if filters == EXPECTED_FILTERS else "STOP"})
    false_flags = ["variant_approved", "replay_executed", "dry_run_executed", "condition_changed", "source_recovery_executed", "source_mutation_executed", "coreb_live_evaluator_unblocked", "discord_notification_sent", "mt5_order_sent", "ai_api_called", "live_hook_executed", "final_signal_created", "no_signal_discord_notify"]
    for flag in false_flags:
        rows.append({"contract_id": f"F{len(rows)+1:03d}", "check": flag, "observed": summary51.get(flag), "expected": False, "status": "PASS" if summary51.get(flag) is False else "STOP"})
    stop_count = int(contract51[contract51.get("status", pd.Series(dtype=str)).astype(str).eq("STOP")].shape[0])
    candidate_top_ok = (not candidates51.empty and as_int(candidates51.iloc[0].get("candidate_rank")) == 1 and str(candidates51.iloc[0].get("relative_path")) == EXPECTED_TOP_CANDIDATE)
    selection_ok = (not selection51.empty and str(selection51.iloc[0].get("candidate_path")) == EXPECTED_TOP_CANDIDATE and not as_bool(selection51.iloc[0].get("source_confirmed")) and not as_bool(selection51.iloc[0].get("future_dry_run_execution_allowed")))
    boundary_ok = int(boundary51[boundary51.get("status", pd.Series(dtype=str)).astype(str).eq("STOP")].shape[0]) == 0
    gate_ok = "SOURCE_CANDIDATE_REVIEW_REQUIRED" in gates51.get("status", pd.Series(dtype=str)).astype(str).tolist()
    next_ok = (not next51.empty and str(next51.iloc[0].get("next_step")) == EXPECTED_NEXT_IN_51 and as_bool(next51.iloc[0].get("allowed_now")) and not as_bool(next51.iloc[0].get("execution_allowed_in_25c51")))
    rows += [
        {"contract_id": f"M{len(rows)+1:03d}", "check": "25C51 contract has no STOP", "observed": stop_count, "expected": 0, "status": "PASS" if stop_count == 0 else "STOP"},
        {"contract_id": f"M{len(rows)+2:03d}", "check": "25C51 top candidate path expected", "observed": candidates51.iloc[0].to_dict() if not candidates51.empty else {}, "expected": EXPECTED_TOP_CANDIDATE, "status": "PASS" if candidate_top_ok else "STOP"},
        {"contract_id": f"M{len(rows)+3:03d}", "check": "25C51 selection requires review and blocks execution", "observed": selection51.iloc[0].to_dict() if not selection51.empty else {}, "expected": "review required, execution false", "status": "PASS" if selection_ok else "STOP"},
        {"contract_id": f"M{len(rows)+4:03d}", "check": "25C51 execution boundary has no STOP", "observed": boundary_ok, "expected": True, "status": "PASS" if boundary_ok else "STOP"},
        {"contract_id": f"M{len(rows)+5:03d}", "check": "25C51 gates include source candidate review required", "observed": gate_ok, "expected": True, "status": "PASS" if gate_ok else "STOP"},
        {"contract_id": f"M{len(rows)+6:03d}", "check": "25C51 next plan allows 25C52 only", "observed": next51.iloc[0].to_dict() if not next51.empty else {}, "expected": "25C52 allowed_now True and execution false", "status": "PASS" if next_ok else "STOP"},
    ]
    return pd.DataFrame(rows)


def resolve_candidate(search_root: str, candidate_rel: str) -> Path:
    root = Path(search_root)
    return (root / candidate_rel.replace("/", os.sep)).resolve()


def review_candidate_file(candidate_path: Path, search_root: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    exists = lp(candidate_path).exists()
    size = lp(candidate_path).stat().st_size if exists else 0
    under_root = False
    try:
        candidate_path.relative_to(search_root.resolve())
        under_root = True
    except Exception:
        under_root = False
    metadata = pd.DataFrame([{
        "candidate_path": str(candidate_path),
        "exists": exists,
        "extension": candidate_path.suffix.lower(),
        "file_size_bytes": int(size),
        "under_fx_outputs": under_root,
        "metadata_status": "PASS" if exists and candidate_path.suffix.lower() == ".csv" and size > 0 and under_root else "STOP",
    }])
    header_rows = []
    if exists:
        header = []
        readable = False
        used_encoding = None
        for enc in ("utf-8-sig", "utf-8", "cp932"):
            try:
                with lp(candidate_path).open("r", encoding=enc, newline="") as f:
                    reader = csv.reader(f)
                    header = next(reader)
                readable = True
                used_encoding = enc
                break
            except Exception:
                continue
        header_rows.append({
            "candidate_path": str(candidate_path),
            "header_readable": readable,
            "encoding": used_encoding or "UNREADABLE",
            "column_count": len(header),
            "columns_joined": ";".join(header[:80]),
            "header_status": "PASS" if readable and len(header) > 0 else "STOP",
        })
    else:
        header_rows.append({"candidate_path": str(candidate_path), "header_readable": False, "encoding": "MISSING", "column_count": 0, "columns_joined": "", "header_status": "STOP"})
    header_df = pd.DataFrame(header_rows)
    metadata_ok = metadata.iloc[0]["metadata_status"] == "PASS"
    header_ok = header_df.iloc[0]["header_status"] == "PASS"
    binding = pd.DataFrame([{
        "binding_rank": 1,
        "candidate_path": str(candidate_path),
        "source_binding_status": "SOURCE_BOUND_FOR_FUTURE_AUDIT_PLANNING_ONLY" if metadata_ok and header_ok else "SOURCE_BINDING_BLOCKED_REVIEW_REQUIRED",
        "source_confirmed_for_execution": False,
        "future_dry_run_execution_allowed": False,
        "approval_status": "NOT_APPROVED_REVIEW_ONLY",
        "review_note": "Candidate is bound only for future audit planning; execution remains blocked." if metadata_ok and header_ok else "Candidate metadata/header failed; review required.",
        "status": "PASS" if metadata_ok and header_ok else "STOP",
    }])
    return metadata, header_df, binding


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input-dir", default=None)
    ap.add_argument("--output-dir", default=None)
    args = ap.parse_args(argv)

    input_dir = Path(args.input_dir).resolve() if args.input_dir else fx_outputs() / IN51
    out = Path(args.output_dir).resolve() if args.output_dir else fx_outputs() / OUT_DIR
    lp(out).mkdir(parents=True, exist_ok=True)

    req = {
        "summary51": input_dir / "02_25c51_dry_run_source_concretion_review_summary.json",
        "contract51": input_dir / "04_25c51_contract_audit.csv",
        "candidates51": input_dir / "06_25c51_source_candidate_matrix.csv",
        "selection51": input_dir / "07_25c51_source_selection_matrix.csv",
        "boundary51": input_dir / "08_25c51_execution_boundary_matrix.csv",
        "gates51": input_dir / "09_25c51_gates.csv",
        "next51": input_dir / "10_25c51_next_step_plan.csv",
        "notes51": input_dir / "11_25c51_handoff_notes.csv",
    }
    input_audit = pd.DataFrame([exists_row(k, v) for k, v in req.items()])
    write_csv(out / "03_25c52_input_audit.csv", input_audit)
    if not input_audit["exists"].all():
        return stop_outputs(out, STOP_MISSING, input_audit, input_audit)

    summary51 = read_json(req["summary51"])
    contract51 = read_csv(req["contract51"])
    candidates51 = read_csv(req["candidates51"])
    selection51 = read_csv(req["selection51"])
    boundary51 = read_csv(req["boundary51"])
    gates51 = read_csv(req["gates51"])
    next51 = read_csv(req["next51"])
    notes51 = read_csv(req["notes51"])

    contract = contract_audit(summary51, contract51, candidates51, selection51, boundary51, gates51, next51)
    if contract["status"].astype(str).eq("STOP").any():
        return stop_outputs(out, STOP_CONTRACT, input_audit, contract, summary51)

    search_root = Path(str(summary51.get("search_root"))).resolve()
    candidate_rel = str(summary51.get("top_source_candidate_path"))
    candidate_path = resolve_candidate(str(search_root), candidate_rel)
    metadata, header_review, binding = review_candidate_file(candidate_path, search_root)
    if binding["status"].astype(str).eq("STOP").any():
        return stop_outputs(out, STOP_CANDIDATE, input_audit, pd.concat([metadata, header_review, binding], ignore_index=True), summary51)

    boundary = execution_boundary_matrix()
    gates = pd.DataFrame([
        {"gate_id": "G001", "gate": "25C51 contract safe", "observed": True, "status": "PASS"},
        {"gate_id": "G002", "gate": "candidate file metadata/header readable", "observed": True, "status": "PASS"},
        {"gate_id": "G003", "gate": "source bound for future audit planning", "observed": True, "status": "PASS"},
        {"gate_id": "G004", "gate": "source confirmed for execution", "observed": False, "status": "EXECUTION_CONFIRMATION_BLOCKED"},
        {"gate_id": "G005", "gate": "future dry-run execution", "observed": False, "status": "BLOCKED"},
        {"gate_id": "G006", "gate": "live/external actions", "observed": False, "status": "BLOCKED"},
    ])
    next_plan = pd.DataFrame([
        {"rank": 1, "next_step": NEXT_STEP, "allowed_now": True, "purpose": "write dry-run preflight specification only; no execution", "execution_allowed_in_25c52": False, "requires_human_acceptance_before_execution": False},
        {"rank": 2, "next_step": "future dry-run execution", "allowed_now": False, "purpose": "blocked until preflight spec/review and later explicit acceptance", "execution_allowed_in_25c52": False, "requires_human_acceptance_before_execution": True},
        {"rank": 3, "next_step": "source recovery / live / external / AI / notification / order / final signal", "allowed_now": False, "purpose": "blocked", "execution_allowed_in_25c52": False, "requires_human_acceptance_before_execution": True},
    ])
    notes = pd.DataFrame([
        {"note_id": "N001", "note": "25C52 used 25C51 outputs as source of truth.", "status": "PASS"},
        {"note_id": "N002", "note": "Top candidate file exists and header is readable.", "status": "PASS"},
        {"note_id": "N003", "note": "Source is bound only for future audit planning; not confirmed for execution.", "status": "PASS"},
        {"note_id": "N004", "note": "A002 remains NOT_APPROVED_REVIEW_ONLY and future dry-run execution remains blocked.", "status": "PASS"},
    ])

    write_csv(out / "00_不要_25c52_file_request_list.csv", file_request_df())
    write_csv(out / "03_25c52_input_audit.csv", input_audit)
    write_csv(out / "04_25c52_contract_audit.csv", contract)
    write_csv(out / "05_25c52_candidate_file_metadata.csv", metadata)
    write_csv(out / "06_25c52_candidate_header_review.csv", header_review)
    write_csv(out / "07_25c52_source_binding_matrix.csv", binding)
    write_csv(out / "08_25c52_execution_boundary_matrix.csv", boundary)
    write_csv(out / "09_25c52_gates.csv", gates)
    write_csv(out / "10_25c52_next_step_plan.csv", next_plan)
    write_csv(out / "11_25c52_handoff_notes.csv", notes)

    summary = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "step": STEP,
        "status": STATUS,
        "audit_only": True,
        "source_candidate_review_only": True,
        "input_25c51_step": summary51.get("step"),
        "input_25c51_status": summary51.get("status"),
        "representative_variant_code": "A002",
        "representative_filters": EXPECTED_FILTERS,
        "representative_approval_status": "NOT_APPROVED_REVIEW_ONLY",
        "candidate_path": str(candidate_path),
        "candidate_relative_path": candidate_rel,
        "candidate_file_exists": bool(metadata.iloc[0]["exists"]),
        "candidate_header_readable": bool(header_review.iloc[0]["header_readable"]),
        "candidate_column_count": int(header_review.iloc[0]["column_count"]),
        "source_binding_status": str(binding.iloc[0]["source_binding_status"]),
        "source_bound_for_future_audit_planning": True,
        "source_confirmed_for_execution": False,
        "future_dry_run_execution_allowed": False,
        "variant_approved": False,
        "replay_executed": False,
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
        "no_signal_discord_notify": False,
        "next_recommended_step": NEXT_STEP,
        "total_stop_rows": 0,
    }
    write_json(out / "02_25c52_dry_run_source_candidate_review_summary.json", summary)
    report = "\n".join([
        "# GOLD V2 25C52 CoreB G1 dry-run source candidate review audit-only report", "",
        f"Created UTC: {summary['created_utc']}", f"Step: `{STEP}`", f"Status: `{STATUS}`", "",
        "## Scope", "", "25C52 reviews and binds the top source candidate for future audit planning only. It does not confirm the source for execution and does not execute dry-run.", "",
        "## 25C51 contract audit", "", md_table(contract), "",
        "## Candidate file metadata", "", md_table(metadata), "",
        "## Candidate header review", "", md_table(header_review), "",
        "## Source binding matrix", "", md_table(binding), "",
        "## Execution boundary matrix", "", md_table(boundary), "",
        "## Gates", "", md_table(gates), "",
        "## Next step plan", "", md_table(next_plan), "",
        "## Handoff notes", "", md_table(notes), "",
        "## Safety", "", "A002 remains NOT_APPROVED_REVIEW_ONLY. Source is bound for future audit planning only, not confirmed for execution. Dry-run execution, replay, source mutation, live/external actions, AI API, Discord, MT5, live hook, and final signal remain OFF. NO_SIGNAL must not notify Discord.",
    ])
    lp(out / "01_25c52_GOLD_V2_COREB_G1_DRY_RUN_SOURCE_CANDIDATE_REVIEW_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")
    print(json.dumps({"status": STATUS, "candidate_relative_path": candidate_rel, "source_binding_status": summary["source_binding_status"], "source_confirmed_for_execution": False, "future_dry_run_execution_allowed": False, "next_recommended_step": NEXT_STEP, "ai_api_called": False, "dry_run_executed": False}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
