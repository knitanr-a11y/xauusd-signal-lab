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

STEP = "25C51_COREB_G1_DRY_RUN_SOURCE_CONCRETION_REVIEW_AUDIT_ONLY"
STATUS = "COREB_G1_DRY_RUN_SOURCE_CONCRETION_REVIEW_READY_AUDIT_ONLY_SOURCE_CANDIDATE_REVIEW_REQUIRED"
STOP_MISSING = "25C51_STOP_MISSING_INPUT_AUDIT_ONLY"
STOP_CONTRACT = "25C51_STOP_25C50_CONTRACT_UNSAFE_AUDIT_ONLY"
STOP_SEARCH = "25C51_STOP_SOURCE_SEARCH_UNSAFE_AUDIT_ONLY"
IN50 = "gold_v2_25c50_coreb_g1_representative_dry_run_readiness_review_audit_only"
OUT_DIR = "gold_v2_25c51_coreb_g1_dry_run_source_concretion_review_audit_only"
EXPECTED_50_STEP = "25C50_COREB_G1_REPRESENTATIVE_DRY_RUN_READINESS_REVIEW_AUDIT_ONLY"
EXPECTED_50_STATUS = "COREB_G1_REPRESENTATIVE_DRY_RUN_READINESS_REVIEW_READY_AUDIT_ONLY_SOURCE_CONCRETION_REQUIRED"
EXPECTED_NEXT_IN_50 = STEP
NEXT_STEP = "25C52_COREB_G1_DRY_RUN_SOURCE_CANDIDATE_REVIEW_AUDIT_ONLY"
EXPECTED_FILTERS = ["same_count>=2&unique_origins>=2", "unique_origins>=2"]
SEARCH_TERMS = ["25c10", "replay", "signal", "rows", "coreb", "g1", "baseline"]
PREFERRED_EXTENSIONS = {".csv", ".json", ".md"}


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
        "FX_OUTPUTS/gold_v2_25c50_coreb_g1_representative_dry_run_readiness_review_audit_only/02_25c50_representative_dry_run_readiness_review_summary.json",
        "FX_OUTPUTS/gold_v2_25c50_coreb_g1_representative_dry_run_readiness_review_audit_only/06_25c50_unresolved_source_matrix.csv",
        "FX_OUTPUTS/gold_v2_25c51_coreb_g1_dry_run_source_concretion_review_audit_only/01_25c51_GOLD_V2_COREB_G1_DRY_RUN_SOURCE_CONCRETION_REVIEW_AUDIT_ONLY_REPORT.md",
        "FX_OUTPUTS/gold_v2_25c51_coreb_g1_dry_run_source_concretion_review_audit_only/02_25c51_dry_run_source_concretion_review_summary.json",
        "FX_OUTPUTS/gold_v2_25c51_coreb_g1_dry_run_source_concretion_review_audit_only/06_25c51_source_candidate_matrix.csv",
        "FX_OUTPUTS/gold_v2_25c51_coreb_g1_dry_run_source_concretion_review_audit_only/07_25c51_source_selection_matrix.csv",
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
        ("coreb_live_evaluator_unblock", False, False),
        ("discord_notification", False, False),
        ("mt5_order", False, False),
        ("ai_api_call", False, False),
        ("live_hook", False, False),
        ("final_signal", False, False),
        ("no_signal_discord_notify", False, False),
    ]
    return pd.DataFrame([{"boundary_id": f"X{i+1:03d}", "boundary": b, "allowed": a, "observed": o, "status": "PASS" if a == o else "STOP"} for i, (b, a, o) in enumerate(rows)])


def stop_outputs(out: Path, status: str, input_audit: pd.DataFrame, diag: pd.DataFrame, summary50: Optional[dict] = None) -> int:
    summary50 = summary50 or {}
    write_csv(out / "00_不要_25c51_file_request_list.csv", file_request_df())
    write_csv(out / "03_25c51_input_audit.csv", input_audit)
    write_csv(out / "04_25c51_contract_audit.csv", diag)
    write_csv(out / "05_25c51_source_search_spec_matrix.csv", diag)
    write_csv(out / "06_25c51_source_candidate_matrix.csv", diag)
    write_csv(out / "07_25c51_source_selection_matrix.csv", diag)
    boundary = execution_boundary_matrix()
    write_csv(out / "08_25c51_execution_boundary_matrix.csv", boundary)
    gates = pd.DataFrame([
        {"gate_id": "G001", "gate": "25C50 contract safe", "observed": False, "status": "STOP"},
        {"gate_id": "G002", "gate": "source candidate review", "observed": False, "status": "BLOCKED"},
        {"gate_id": "G003", "gate": "future dry-run execution", "observed": False, "status": "BLOCKED"},
    ])
    write_csv(out / "09_25c51_gates.csv", gates)
    next_plan = pd.DataFrame([{"rank": 1, "next_step": "STOP", "allowed_now": False, "purpose": status, "execution_allowed_in_25c51": False}])
    write_csv(out / "10_25c51_next_step_plan.csv", next_plan)
    notes = pd.DataFrame([
        {"note_id": "N001", "note": "25C51 stopped safely.", "status": status},
        {"note_id": "N002", "note": "No approval, replay, dry-run, source change, live/external action, AI, notification, order, or final signal executed.", "status": "PASS"},
    ])
    write_csv(out / "11_25c51_handoff_notes.csv", notes)
    summary = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "step": STEP,
        "status": status,
        "audit_only": True,
        "source_concretion_review_only": True,
        "input_25c50_step": summary50.get("step"),
        "input_25c50_status": summary50.get("status"),
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
    write_json(out / "02_25c51_dry_run_source_concretion_review_summary.json", summary)
    report = "\n".join([
        "# GOLD V2 25C51 CoreB G1 dry-run source concretion review audit-only report", "",
        f"Created UTC: {summary['created_utc']}", f"Step: `{STEP}`", f"Status: `{status}`", "",
        "## Stop diagnostic", "", md_table(diag), "",
        "## Input audit", "", md_table(input_audit), "",
        "## Safety", "", "Stopped safely. No dry-run or external action was performed.",
    ])
    lp(out / "01_25c51_GOLD_V2_COREB_G1_DRY_RUN_SOURCE_CONCRETION_REVIEW_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")
    print(json.dumps({"status": status, "ai_api_called": False, "dry_run_executed": False}, ensure_ascii=False, indent=2))
    return 2


def contract_audit(summary50: dict, contract50: pd.DataFrame, readiness50: pd.DataFrame, unresolved50: pd.DataFrame, boundary50: pd.DataFrame, gates50: pd.DataFrame, next50: pd.DataFrame) -> pd.DataFrame:
    expected = {
        "step": EXPECTED_50_STEP,
        "status": "COREB_G1_REPRESENTATIVE_DRY_RUN_READINESS_REVIEW_READY_AUDIT_ONLY_SOURCE_CONCRETION_REQUIRED",
        "audit_only": True,
        "readiness_review_only": True,
        "representative_variant_code": "A002",
        "representative_approval_status": "NOT_APPROVED_REVIEW_ONLY",
        "dry_run_spec_ready_for_manual_review": True,
        "source_concretion_required": True,
        "exact_baseline_replay_signal_source_confirmed": False,
        "future_dry_run_execution_allowed": False,
        "next_recommended_step": EXPECTED_NEXT_IN_50,
        "total_stop_rows": 0,
    }
    rows = []
    for i, (k, exp) in enumerate(expected.items(), 1):
        obs = summary50.get(k)
        if isinstance(exp, bool):
            ok = as_bool(obs) == exp
        elif isinstance(exp, int):
            ok = as_int(obs) == exp
        else:
            ok = obs == exp
        rows.append({"contract_id": f"C{i:03d}", "check": k, "observed": obs, "expected": exp, "status": "PASS" if ok else "STOP"})
    filters = summary50.get("representative_filters", [])
    rows.append({"contract_id": "C013", "check": "representative_filters exact", "observed": ";".join(filters) if isinstance(filters, list) else filters, "expected": ";".join(EXPECTED_FILTERS), "status": "PASS" if filters == EXPECTED_FILTERS else "STOP"})
    false_flags = ["variant_approved", "replay_executed", "dry_run_executed", "condition_changed", "source_recovery_executed", "source_mutation_executed", "coreb_live_evaluator_unblocked", "discord_notification_sent", "mt5_order_sent", "ai_api_called", "live_hook_executed", "final_signal_created", "no_signal_discord_notify"]
    for flag in false_flags:
        rows.append({"contract_id": f"F{len(rows)+1:03d}", "check": flag, "observed": summary50.get(flag), "expected": False, "status": "PASS" if summary50.get(flag) is False else "STOP"})
    stop_count = int(contract50[contract50.get("status", pd.Series(dtype=str)).astype(str).eq("STOP")].shape[0])
    readiness_blocked = "SOURCE_CONCRETION_REQUIRED" in readiness50.get("readiness_state", pd.Series(dtype=str)).astype(str).tolist()
    unresolved_present = (not unresolved50.empty and "audited baseline replay signal source" in unresolved50.get("required_input", pd.Series(dtype=str)).astype(str).tolist())
    boundary_ok = int(boundary50[boundary50.get("status", pd.Series(dtype=str)).astype(str).eq("STOP")].shape[0]) == 0
    gate_ok = "SOURCE_CONCRETION_REQUIRED" in gates50.get("status", pd.Series(dtype=str)).astype(str).tolist()
    next_ok = (not next50.empty and str(next50.iloc[0].get("next_step")) == EXPECTED_NEXT_IN_50 and as_bool(next50.iloc[0].get("allowed_now")) and not as_bool(next50.iloc[0].get("execution_allowed_in_25c50")))
    rows += [
        {"contract_id": f"M{len(rows)+1:03d}", "check": "25C50 contract has no STOP", "observed": stop_count, "expected": 0, "status": "PASS" if stop_count == 0 else "STOP"},
        {"contract_id": f"M{len(rows)+2:03d}", "check": "25C50 readiness requires source concretion", "observed": readiness_blocked, "expected": True, "status": "PASS" if readiness_blocked else "STOP"},
        {"contract_id": f"M{len(rows)+3:03d}", "check": "25C50 unresolved baseline source row present", "observed": unresolved_present, "expected": True, "status": "PASS" if unresolved_present else "STOP"},
        {"contract_id": f"M{len(rows)+4:03d}", "check": "25C50 execution boundary has no STOP", "observed": boundary_ok, "expected": True, "status": "PASS" if boundary_ok else "STOP"},
        {"contract_id": f"M{len(rows)+5:03d}", "check": "25C50 gates include source concretion required", "observed": gate_ok, "expected": True, "status": "PASS" if gate_ok else "STOP"},
        {"contract_id": f"M{len(rows)+6:03d}", "check": "25C50 next plan allows 25C51 only", "observed": next50.iloc[0].to_dict() if not next50.empty else {}, "expected": "25C51 allowed_now True and execution false", "status": "PASS" if next_ok else "STOP"},
    ]
    return pd.DataFrame(rows)


def search_spec_matrix(search_root: Path) -> pd.DataFrame:
    return pd.DataFrame([
        {"spec_id": "S001", "search_root": str(search_root), "term": term, "scope": "FX_OUTPUTS_PATH_NAME_ONLY", "allowed": True, "notes": "Path/name scoring only; no replay/dry-run execution."}
        for term in SEARCH_TERMS
    ])


def scan_candidates(search_root: Path) -> pd.DataFrame:
    rows = []
    if not lp(search_root).exists():
        return pd.DataFrame([{"candidate_rank": 1, "path": str(search_root), "exists": False, "score": 0, "status": "SEARCH_ROOT_MISSING"}])
    candidates = []
    for p in search_root.rglob("*"):
        try:
            if not p.is_file() or p.suffix.lower() not in PREFERRED_EXTENSIONS:
                continue
            rel = str(p.relative_to(search_root)).replace("\\", "/")
            lower = rel.lower()
            hits = [t for t in SEARCH_TERMS if t in lower]
            score = len(hits)
            if score <= 0:
                continue
            bonus = 0
            if "25c10" in lower:
                bonus += 5
            if "replay" in lower and "signal" in lower:
                bonus += 3
            if "rows" in lower:
                bonus += 2
            candidates.append({
                "relative_path": rel,
                "absolute_path": str(p),
                "extension": p.suffix.lower(),
                "matched_terms": ";".join(hits),
                "raw_term_hits": score,
                "bonus_score": bonus,
                "total_score": score + bonus,
                "file_size_bytes": p.stat().st_size,
                "status": "SOURCE_CANDIDATE_REVIEW_REQUIRED",
            })
        except Exception:
            continue
    if not candidates:
        return pd.DataFrame([{"candidate_rank": 1, "relative_path": "NO_CANDIDATE_FOUND", "absolute_path": "", "extension": "", "matched_terms": "", "raw_term_hits": 0, "bonus_score": 0, "total_score": 0, "file_size_bytes": 0, "status": "NO_CANDIDATE_FOUND_REVIEW_REQUIRED"}])
    df = pd.DataFrame(candidates).sort_values(["total_score", "raw_term_hits", "file_size_bytes", "relative_path"], ascending=[False, False, False, True]).reset_index(drop=True)
    df.insert(0, "candidate_rank", range(1, len(df) + 1))
    return df.head(100)


def selection_matrix(candidates: pd.DataFrame) -> pd.DataFrame:
    if candidates.empty or str(candidates.iloc[0].get("relative_path", "")) == "NO_CANDIDATE_FOUND":
        return pd.DataFrame([{
            "selection_rank": 1,
            "candidate_rank": None,
            "candidate_path": "NO_CANDIDATE_FOUND",
            "selection_status": "NO_SOURCE_CANDIDATE_FOUND_REVIEW_REQUIRED",
            "source_confirmed": False,
            "future_dry_run_execution_allowed": False,
        }])
    top = candidates.iloc[0]
    return pd.DataFrame([{
        "selection_rank": 1,
        "candidate_rank": int(top.get("candidate_rank", 1)),
        "candidate_path": top.get("relative_path"),
        "matched_terms": top.get("matched_terms"),
        "total_score": top.get("total_score"),
        "selection_status": "TOP_SOURCE_CANDIDATE_REVIEW_REQUIRED_NOT_CONFIRMED",
        "source_confirmed": False,
        "future_dry_run_execution_allowed": False,
        "review_requirement": "Human/artifact review must confirm exact audited baseline replay signal source before execution.",
    }])


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input-dir", default=None)
    ap.add_argument("--search-root", default=None)
    ap.add_argument("--output-dir", default=None)
    args = ap.parse_args(argv)

    input_dir = Path(args.input_dir).resolve() if args.input_dir else fx_outputs() / IN50
    search_root = Path(args.search_root).resolve() if args.search_root else fx_outputs()
    out = Path(args.output_dir).resolve() if args.output_dir else fx_outputs() / OUT_DIR
    lp(out).mkdir(parents=True, exist_ok=True)

    req = {
        "summary50": input_dir / "02_25c50_representative_dry_run_readiness_review_summary.json",
        "contract50": input_dir / "04_25c50_contract_audit.csv",
        "readiness50": input_dir / "05_25c50_readiness_matrix.csv",
        "unresolved50": input_dir / "06_25c50_unresolved_source_matrix.csv",
        "boundary50": input_dir / "07_25c50_execution_boundary_matrix.csv",
        "gates50": input_dir / "08_25c50_gates.csv",
        "next50": input_dir / "09_25c50_next_step_plan.csv",
        "notes50": input_dir / "10_25c50_handoff_notes.csv",
    }
    input_audit = pd.DataFrame([exists_row(k, v) for k, v in req.items()])
    write_csv(out / "03_25c51_input_audit.csv", input_audit)
    if not input_audit["exists"].all():
        return stop_outputs(out, STOP_MISSING, input_audit, input_audit)

    summary50 = read_json(req["summary50"])
    contract50 = read_csv(req["contract50"])
    readiness50 = read_csv(req["readiness50"])
    unresolved50 = read_csv(req["unresolved50"])
    boundary50 = read_csv(req["boundary50"])
    gates50 = read_csv(req["gates50"])
    next50 = read_csv(req["next50"])
    notes50 = read_csv(req["notes50"])

    contract = contract_audit(summary50, contract50, readiness50, unresolved50, boundary50, gates50, next50)
    if contract["status"].astype(str).eq("STOP").any():
        return stop_outputs(out, STOP_CONTRACT, input_audit, contract, summary50)

    spec = search_spec_matrix(search_root)
    candidates = scan_candidates(search_root)
    if candidates.empty:
        return stop_outputs(out, STOP_SEARCH, input_audit, candidates, summary50)
    selection = selection_matrix(candidates)
    boundary = execution_boundary_matrix()
    gates = pd.DataFrame([
        {"gate_id": "G001", "gate": "25C50 contract safe", "observed": True, "status": "PASS"},
        {"gate_id": "G002", "gate": "source candidate search completed", "observed": True, "status": "PASS"},
        {"gate_id": "G003", "gate": "source candidate confirmed", "observed": False, "status": "SOURCE_CANDIDATE_REVIEW_REQUIRED"},
        {"gate_id": "G004", "gate": "future dry-run execution", "observed": False, "status": "BLOCKED"},
        {"gate_id": "G005", "gate": "live/external actions", "observed": False, "status": "BLOCKED"},
    ])
    next_plan = pd.DataFrame([
        {"rank": 1, "next_step": NEXT_STEP, "allowed_now": True, "purpose": "review/bind top source candidate only; no execution", "execution_allowed_in_25c51": False, "requires_human_acceptance_before_execution": False},
        {"rank": 2, "next_step": "future dry-run execution", "allowed_now": False, "purpose": "blocked until source candidate review and later explicit acceptance", "execution_allowed_in_25c51": False, "requires_human_acceptance_before_execution": True},
        {"rank": 3, "next_step": "source recovery / live / external / AI / notification / order / final signal", "allowed_now": False, "purpose": "blocked", "execution_allowed_in_25c51": False, "requires_human_acceptance_before_execution": True},
    ])
    notes = pd.DataFrame([
        {"note_id": "N001", "note": "25C51 used 25C50 outputs as source of truth.", "status": "PASS"},
        {"note_id": "N002", "note": "Candidate search used local FX_OUTPUTS path/name scoring only.", "status": "PASS"},
        {"note_id": "N003", "note": "Top candidate is not confirmed and must be reviewed before any execution.", "status": "SOURCE_CANDIDATE_REVIEW_REQUIRED"},
        {"note_id": "N004", "note": "A002 remains NOT_APPROVED_REVIEW_ONLY.", "status": "PASS"},
    ])

    write_csv(out / "00_不要_25c51_file_request_list.csv", file_request_df())
    write_csv(out / "03_25c51_input_audit.csv", input_audit)
    write_csv(out / "04_25c51_contract_audit.csv", contract)
    write_csv(out / "05_25c51_source_search_spec_matrix.csv", spec)
    write_csv(out / "06_25c51_source_candidate_matrix.csv", candidates)
    write_csv(out / "07_25c51_source_selection_matrix.csv", selection)
    write_csv(out / "08_25c51_execution_boundary_matrix.csv", boundary)
    write_csv(out / "09_25c51_gates.csv", gates)
    write_csv(out / "10_25c51_next_step_plan.csv", next_plan)
    write_csv(out / "11_25c51_handoff_notes.csv", notes)

    summary = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "step": STEP,
        "status": STATUS,
        "audit_only": True,
        "source_concretion_review_only": True,
        "input_25c50_step": summary50.get("step"),
        "input_25c50_status": summary50.get("status"),
        "representative_variant_code": "A002",
        "representative_filters": EXPECTED_FILTERS,
        "representative_approval_status": "NOT_APPROVED_REVIEW_ONLY",
        "search_root": str(search_root),
        "source_candidate_rows": int(len(candidates)),
        "top_source_candidate_path": selection.iloc[0].get("candidate_path") if not selection.empty else None,
        "source_confirmed": False,
        "source_candidate_review_required": True,
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
    write_json(out / "02_25c51_dry_run_source_concretion_review_summary.json", summary)
    report = "\n".join([
        "# GOLD V2 25C51 CoreB G1 dry-run source concretion review audit-only report", "",
        f"Created UTC: {summary['created_utc']}", f"Step: `{STEP}`", f"Status: `{STATUS}`", "",
        "## Scope", "", "25C51 searches candidate audited baseline replay signal sources by local FX_OUTPUTS path/name scoring only. It does not confirm a source and does not execute dry-run.", "",
        "## 25C50 contract audit", "", md_table(contract), "",
        "## Source search spec", "", md_table(spec), "",
        "## Source candidate matrix", "", md_table(candidates, 50), "",
        "## Source selection matrix", "", md_table(selection), "",
        "## Execution boundary matrix", "", md_table(boundary), "",
        "## Gates", "", md_table(gates), "",
        "## Next step plan", "", md_table(next_plan), "",
        "## Handoff notes", "", md_table(notes), "",
        "## Safety", "", "A002 remains NOT_APPROVED_REVIEW_ONLY. Source candidate is not confirmed. Dry-run execution, replay, source mutation, live/external actions, AI API, Discord, MT5, live hook, and final signal remain OFF. NO_SIGNAL must not notify Discord.",
    ])
    lp(out / "01_25c51_GOLD_V2_COREB_G1_DRY_RUN_SOURCE_CONCRETION_REVIEW_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")
    print(json.dumps({"status": STATUS, "top_source_candidate_path": summary["top_source_candidate_path"], "source_confirmed": False, "future_dry_run_execution_allowed": False, "next_recommended_step": NEXT_STEP, "ai_api_called": False, "dry_run_executed": False}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
