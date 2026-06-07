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

STEP = "25C46_COREB_G1_FILTER_COVERAGE_REVIEW_AUDIT_ONLY"
LOGICAL_STEP_ALIAS = "25C46_COREB_G1_RETENTION_AWARE_RECOVERY_PLAN_AUDIT_ONLY"
STATUS = "COREB_G1_FILTER_COVERAGE_REVIEW_READY_AUDIT_ONLY"
STOP_MISSING = "25C46_STOP_MISSING_INPUT_AUDIT_ONLY"
STOP_CONTRACT = "25C46_STOP_25C45_CONTRACT_UNSAFE_AUDIT_ONLY"
STOP_COVERAGE = "25C46_STOP_NO_FULL_KNOWN_KEY_COVERAGE_AUDIT_ONLY"
OUT_DIR = "gold_v2_25c46_coreb_g1_filter_coverage_review_audit_only"
IN45 = "gold_v2_25c45_coreb_g1_incremental_damage_filter_attribution_audit_only"
EXPECTED_25C45_STEP = "25C45_COREB_G1_INCREMENTAL_DAMAGE_FILTER_ATTRIBUTION_AUDIT_ONLY"
EXPECTED_25C45_STATUS = "COREB_G1_INCREMENTAL_DAMAGE_FILTER_ATTRIBUTION_COMPLETED_AUDIT_ONLY_RETENTION_PLAN_REQUIRED"
EXPECTED_25C45_NEXT = LOGICAL_STEP_ALIAS
NEXT_STEP = "25C47_COREB_G1_FILTER_COVERAGE_NEXT_PLAN_AUDIT_ONLY"
EXPECTED_UNIQUE_DAMAGE_KEYS = 360
EXPECTED_FILTER_ATTRIBUTION_ROWS = 1260
EXPECTED_UNIQUE_CLEANLY_ATTRIBUTED_KEYS = 360
EXPECTED_UNIQUE_NOT_CLEANLY_ATTRIBUTED_KEYS = 0
KEY = ["dataset", "entry_time", "policy"]
KEYV = ["variant"] + KEY


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


def md_table(df: pd.DataFrame, n: int = 80) -> str:
    if df.empty:
        return "_No rows._"
    v = df.head(n).copy()
    cols = list(v.columns)
    rows = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for _, r in v.iterrows():
        rows.append("| " + " | ".join(str(r[c]).replace("|", "\\|") for c in cols) + " |")
    return "\n".join(rows)


def as_bool(v: object) -> bool:
    return v if isinstance(v, bool) else str(v).strip().lower() in {"true", "1", "yes", "y"}


def exists_row(role: str, p: Path) -> dict:
    ok = lp(p).exists()
    return {"role": role, "path": str(p), "exists": ok, "status": "PASS" if ok else "STOP"}


def variant_code(v: object) -> str:
    return str(v).split("_", 1)[0]


def tie_rank(v: object) -> int:
    code = variant_code(v)
    if code == "A002":
        return 0
    if code == "A004":
        return 1
    return 0


def norm_key_columns(df: pd.DataFrame, required_extra: Optional[list[str]] = None) -> pd.DataFrame:
    out = df.copy()
    required = KEYV + (required_extra or [])
    for c in required:
        if c not in out.columns:
            raise ValueError(f"missing required column: {c}")
        if c in KEYV or c in {"filter"}:
            out[c] = out[c].astype(str)
    return out


def file_request_df() -> pd.DataFrame:
    skip = [
        "raw OHLC",
        "old GOLD/DISC8 files",
        "24-series source recovery files",
        "new replay outputs",
        "new dry-run outputs",
        "AI review ledgers",
        "Discord/MT5/live artifacts",
    ]
    keep = [
        "FX_OUTPUTS/gold_v2_25c45_coreb_g1_incremental_damage_filter_attribution_audit_only/02_25c45_coreb_g1_incremental_damage_filter_attribution_summary.json",
        "FX_OUTPUTS/gold_v2_25c45_coreb_g1_incremental_damage_filter_attribution_audit_only/04_25c45_incremental_damage_key_filter_attribution_rows.csv",
        "FX_OUTPUTS/gold_v2_25c45_coreb_g1_incremental_damage_filter_attribution_audit_only/07_25c45_filter_retention_candidate_matrix.csv",
        "FX_OUTPUTS/gold_v2_25c45_coreb_g1_incremental_damage_filter_attribution_audit_only/08_25c45_attribution_quality_matrix.csv",
        "FX_OUTPUTS/gold_v2_25c46_coreb_g1_filter_coverage_review_audit_only/01_25c46_GOLD_V2_COREB_G1_FILTER_COVERAGE_REVIEW_AUDIT_ONLY_REPORT.md",
        "FX_OUTPUTS/gold_v2_25c46_coreb_g1_filter_coverage_review_audit_only/02_25c46_filter_coverage_review_summary.json",
        "FX_OUTPUTS/gold_v2_25c46_coreb_g1_filter_coverage_review_audit_only/04_25c46_coverage_matrix.csv",
        "FX_OUTPUTS/gold_v2_25c46_coreb_g1_filter_coverage_review_audit_only/05_25c46_selected_coverage_plan.csv",
    ]
    return pd.DataFrame(
        [{"section": "00_不要_貼らなくてOK", "rank": i + 1, "item": x} for i, x in enumerate(skip)]
        + [{"section": "必要・見るファイル", "rank": i + 1, "item": x} for i, x in enumerate(keep)]
    )


def safety_limits_df() -> pd.DataFrame:
    return pd.DataFrame([
        {"limit_id": "L001", "boundary": "review_plan_only", "allowed": True, "observed": True, "status": "PASS"},
        {"limit_id": "L002", "boundary": "read_corrected_25c45_artifacts", "allowed": True, "observed": True, "status": "PASS"},
        {"limit_id": "L003", "boundary": "coverage_by_unique_key_only", "allowed": True, "observed": True, "status": "PASS"},
        {"limit_id": "L004", "boundary": "treat_1260_as_unique_damage_keys", "allowed": False, "observed": False, "status": "PASS"},
        {"limit_id": "L005", "boundary": "sum_filter_rows_as_row_level_damage", "allowed": False, "observed": False, "status": "PASS"},
        {"limit_id": "L006", "boundary": "replay_execution", "allowed": False, "observed": False, "status": "PASS"},
        {"limit_id": "L007", "boundary": "condition_change", "allowed": False, "observed": False, "status": "PASS"},
        {"limit_id": "L008", "boundary": "source_change_or_source_recovery", "allowed": False, "observed": False, "status": "PASS"},
        {"limit_id": "L009", "boundary": "approve_a002_a004_or_any_variant", "allowed": False, "observed": False, "status": "PASS"},
        {"limit_id": "L010", "boundary": "coreb_live_evaluator_unblock", "allowed": False, "observed": False, "status": "PASS"},
        {"limit_id": "L011", "boundary": "discord_notification", "allowed": False, "observed": False, "status": "PASS"},
        {"limit_id": "L012", "boundary": "mt5_order", "allowed": False, "observed": False, "status": "PASS"},
        {"limit_id": "L013", "boundary": "ai_api_call", "allowed": False, "observed": False, "status": "PASS"},
        {"limit_id": "L014", "boundary": "live_hook", "allowed": False, "observed": False, "status": "PASS"},
        {"limit_id": "L015", "boundary": "final_signal", "allowed": False, "observed": False, "status": "PASS"},
        {"limit_id": "L016", "boundary": "no_signal_discord_notify", "allowed": False, "observed": False, "status": "PASS"},
    ])


def stop_outputs(
    out: Path,
    status: str,
    input_audit: pd.DataFrame,
    diagnostic: pd.DataFrame,
    stop_rows: int,
    observed_summary: Optional[dict] = None,
) -> int:
    observed_summary = observed_summary or {}
    reqdf = file_request_df()
    write_csv(out / "00_不要_25c46_file_request_list.csv", reqdf)
    write_csv(out / "03_25c46_input_audit.csv", input_audit)
    write_csv(out / "04_25c46_coverage_matrix.csv", diagnostic)
    write_csv(out / "05_25c46_selected_coverage_plan.csv", diagnostic)
    write_csv(out / "06_25c46_notes.csv", pd.DataFrame([
        {"note_id": "N001", "note": "25C46 stopped before coverage review completion.", "status": status},
        {"note_id": "N002", "note": "No replay, recovery, live path, external path, AI review, notification, order, or final signal was executed.", "status": "PASS"},
    ]))
    limits = safety_limits_df()
    write_csv(out / "07_25c46_limits.csv", limits)
    gates = pd.DataFrame([
        {"gate_id": "G001", "gate": "25C45 corrected contract safe", "observed": False, "status": "STOP"},
        {"gate_id": "G002", "gate": "full known-key coverage candidate exists", "observed": False, "status": "BLOCKED"},
        {"gate_id": "G003", "gate": "25C47 may start", "observed": False, "status": "BLOCKED_UNTIL_25C46_ARTIFACT_REVIEW"},
    ])
    write_csv(out / "08_25c46_gates.csv", gates)
    next_plan = pd.DataFrame([
        {"rank": 1, "next_step": "STOP", "allowed_now": False, "purpose": status, "requires_artifact_review_before_start": True},
        {"rank": 2, "next_step": NEXT_STEP, "allowed_now": False, "purpose": "blocked because 25C46 did not complete", "requires_artifact_review_before_start": True},
    ])
    write_csv(out / "09_25c46_next_step_plan.csv", next_plan)
    summary = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "step": STEP,
        "logical_step_alias": LOGICAL_STEP_ALIAS,
        "status": status,
        "audit_only": True,
        "review_plan_only": True,
        "input_25c45_step": observed_summary.get("step"),
        "input_25c45_status": observed_summary.get("status"),
        "input_25c45_next_recommended_step": observed_summary.get("next_recommended_step"),
        "unique_incremental_damage_keys": observed_summary.get("unique_incremental_damage_keys"),
        "filter_attribution_rows": observed_summary.get("filter_attribution_rows"),
        "unique_cleanly_attributed_damage_keys": observed_summary.get("unique_cleanly_attributed_damage_keys"),
        "unique_not_cleanly_attributed_damage_keys": observed_summary.get("unique_not_cleanly_attributed_damage_keys"),
        "replay_executed": False,
        "dry_run_executed": False,
        "condition_changed": False,
        "source_recovery_executed": False,
        "source_mutation_executed": False,
        "variant_approved": False,
        "coreb_live_evaluator_unblocked": False,
        "discord_notification_sent": False,
        "mt5_order_sent": False,
        "ai_api_called": False,
        "live_hook_executed": False,
        "final_signal_created": False,
        "no_signal_discord_notify": False,
        "next_recommended_step": "STOP",
        "total_stop_rows": int(stop_rows),
    }
    write_json(out / "02_25c46_filter_coverage_review_summary.json", summary)
    report = "\n".join([
        "# GOLD V2 25C46 CoreB G1 filter coverage review audit-only report", "",
        f"Created UTC: {summary['created_utc']}",
        f"Step: `{STEP}`",
        f"Logical step alias: `{LOGICAL_STEP_ALIAS}`",
        f"Status: `{status}`", "",
        "## Stop diagnostic", "", md_table(diagnostic), "",
        "## Input audit", "", md_table(input_audit), "",
        "## Safety", "",
        "Stopped safely. No replay, condition change, source change, recovery, live path, external path, AI review, Discord notification, MT5 order, or final signal was executed.",
    ])
    lp(out / "01_25c46_GOLD_V2_COREB_G1_FILTER_COVERAGE_REVIEW_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")
    print(json.dumps({"status": status, "total_stop_rows": int(stop_rows), "ai_api_called": False, "replay_executed": False}, ensure_ascii=False, indent=2))
    return 2


def contract_audit(summary45: dict, quality: pd.DataFrame, attr: pd.DataFrame, retention: pd.DataFrame) -> pd.DataFrame:
    quality_stop_rows = 0
    if "status" in quality.columns:
        quality_stop_rows = int(quality[quality["status"].astype(str).eq("STOP")].shape[0])
    observed_unique_attr_keys = int(attr[KEYV].drop_duplicates().shape[0]) if all(c in attr.columns for c in KEYV) else -1
    rows = [
        {"contract_id": "C001", "check": "25C45 step matches expected", "observed": summary45.get("step"), "expected": EXPECTED_25C45_STEP, "status": "PASS" if summary45.get("step") == EXPECTED_25C45_STEP else "STOP"},
        {"contract_id": "C002", "check": "25C45 status matches corrected completion", "observed": summary45.get("status"), "expected": EXPECTED_25C45_STATUS, "status": "PASS" if summary45.get("status") == EXPECTED_25C45_STATUS else "STOP"},
        {"contract_id": "C003", "check": "25C45 audit_only true", "observed": summary45.get("audit_only"), "expected": True, "status": "PASS" if as_bool(summary45.get("audit_only", False)) else "STOP"},
        {"contract_id": "C004", "check": "25C45 next step is logical 25C46 alias", "observed": summary45.get("next_recommended_step"), "expected": EXPECTED_25C45_NEXT, "status": "PASS" if summary45.get("next_recommended_step") == EXPECTED_25C45_NEXT else "STOP"},
        {"contract_id": "C005", "check": "unique_incremental_damage_keys uses corrected key count", "observed": summary45.get("unique_incremental_damage_keys"), "expected": EXPECTED_UNIQUE_DAMAGE_KEYS, "status": "PASS" if int(summary45.get("unique_incremental_damage_keys", -1)) == EXPECTED_UNIQUE_DAMAGE_KEYS else "STOP"},
        {"contract_id": "C006", "check": "filter_attribution_rows remains attribution row count", "observed": summary45.get("filter_attribution_rows"), "expected": EXPECTED_FILTER_ATTRIBUTION_ROWS, "status": "PASS" if int(summary45.get("filter_attribution_rows", -1)) == EXPECTED_FILTER_ATTRIBUTION_ROWS else "STOP"},
        {"contract_id": "C007", "check": "unique_cleanly_attributed_damage_keys corrected", "observed": summary45.get("unique_cleanly_attributed_damage_keys"), "expected": EXPECTED_UNIQUE_CLEANLY_ATTRIBUTED_KEYS, "status": "PASS" if int(summary45.get("unique_cleanly_attributed_damage_keys", -1)) == EXPECTED_UNIQUE_CLEANLY_ATTRIBUTED_KEYS else "STOP"},
        {"contract_id": "C008", "check": "unique_not_cleanly_attributed_damage_keys corrected", "observed": summary45.get("unique_not_cleanly_attributed_damage_keys"), "expected": EXPECTED_UNIQUE_NOT_CLEANLY_ATTRIBUTED_KEYS, "status": "PASS" if int(summary45.get("unique_not_cleanly_attributed_damage_keys", -1)) == EXPECTED_UNIQUE_NOT_CLEANLY_ATTRIBUTED_KEYS else "STOP"},
        {"contract_id": "C009", "check": "attribution CSV unique keys match corrected key count", "observed": observed_unique_attr_keys, "expected": EXPECTED_UNIQUE_DAMAGE_KEYS, "status": "PASS" if observed_unique_attr_keys == EXPECTED_UNIQUE_DAMAGE_KEYS else "STOP"},
        {"contract_id": "C010", "check": "attribution CSV row count matches attribution rows", "observed": int(len(attr)), "expected": EXPECTED_FILTER_ATTRIBUTION_ROWS, "status": "PASS" if int(len(attr)) == EXPECTED_FILTER_ATTRIBUTION_ROWS else "STOP"},
        {"contract_id": "C011", "check": "retention candidate matrix non-empty", "observed": int(len(retention)), "expected": "> 0", "status": "PASS" if int(len(retention)) > 0 else "STOP"},
        {"contract_id": "C012", "check": "25C45 quality matrix has no STOP", "observed": quality_stop_rows, "expected": 0, "status": "PASS" if quality_stop_rows == 0 else "STOP"},
        {"contract_id": "C013", "check": "25C45 did not execute dry-run", "observed": summary45.get("dry_run_executed"), "expected": False, "status": "PASS" if not as_bool(summary45.get("dry_run_executed", False)) else "STOP"},
        {"contract_id": "C014", "check": "25C45 did not call AI API", "observed": summary45.get("ai_api_called"), "expected": False, "status": "PASS" if not as_bool(summary45.get("ai_api_called", False)) else "STOP"},
    ]
    return pd.DataFrame(rows)


def build_coverage_matrix(attr: pd.DataFrame, retention: pd.DataFrame) -> pd.DataFrame:
    attr = norm_key_columns(attr, ["filter"])
    retention = retention.copy()
    for c in ["variant", "filter", "retention_priority"]:
        if c not in retention.columns:
            raise ValueError(f"missing required retention column: {c}")
    retention["variant"] = retention["variant"].astype(str)
    retention["filter"] = retention["filter"].astype(str)
    retention["retention_priority"] = pd.to_numeric(retention["retention_priority"], errors="coerce")
    if retention["retention_priority"].isna().any():
        raise ValueError("retention_priority contains non-numeric value")
    retention["retention_priority"] = retention["retention_priority"].astype(int)

    known_keys = attr[KEYV].drop_duplicates().copy()
    rows: list[dict] = []
    for variant in sorted(known_keys["variant"].astype(str).unique().tolist()):
        variant_keys = known_keys[known_keys["variant"].astype(str).eq(variant)].copy()
        total_unique_keys = int(len(variant_keys))
        rv = retention[retention["variant"].astype(str).eq(variant)].copy()
        av = attr[attr["variant"].astype(str).eq(variant)].copy()
        for cutoff in sorted(rv["retention_priority"].drop_duplicates().astype(int).tolist()):
            retained = rv[rv["retention_priority"].le(cutoff)].copy()
            retained_filters = sorted(retained["filter"].astype(str).drop_duplicates().tolist())
            covered = av[av["filter"].astype(str).isin(retained_filters)][KEYV].drop_duplicates().copy()
            covered_unique_keys = int(len(covered))
            open_unique_keys = int(total_unique_keys - covered_unique_keys)
            rows.append({
                "variant": variant,
                "variant_code": variant_code(variant),
                "retention_priority_cutoff": int(cutoff),
                "total_unique_damage_keys": total_unique_keys,
                "covered_unique_keys": covered_unique_keys,
                "open_unique_keys": open_unique_keys,
                "coverage_rate_pct": round((covered_unique_keys / total_unique_keys * 100) if total_unique_keys else 0.0, 6),
                "full_known_key_coverage": bool(open_unique_keys == 0 and total_unique_keys > 0),
                "retained_filter_count": int(len(retained_filters)),
                "retained_filters": ";".join(retained_filters),
                "approval_status": "NOT_APPROVED_REVIEW_ONLY",
                "coverage_key_semantics": "variant+dataset+entry_time+policy",
            })
    return pd.DataFrame(rows).sort_values(["variant", "retention_priority_cutoff"]).reset_index(drop=True)


def select_plan(coverage: pd.DataFrame) -> pd.DataFrame:
    full = coverage[coverage["full_known_key_coverage"].astype(bool)].copy()
    if full.empty:
        return full
    full["_tie_rank"] = full["variant"].map(tie_rank)
    full = full.sort_values(
        ["total_unique_damage_keys", "retained_filter_count", "_tie_rank", "variant", "retention_priority_cutoff"],
        ascending=[True, True, True, True, True],
    ).reset_index(drop=True)
    full.insert(0, "selected_plan_rank", range(1, len(full) + 1))
    full["selected_representative"] = full["selected_plan_rank"].eq(1)
    full["selection_rule"] = "full coverage -> min unique damaged keys -> min retained filters -> A002 before A004 when tied"
    full["approval_status"] = "NOT_APPROVED_REVIEW_ONLY"
    full["execution_allowed_now"] = False
    full["requires_artifact_review_before_25c47"] = True
    return full.drop(columns=["_tie_rank"])


def build_report(summary: dict, input_audit: pd.DataFrame, contract: pd.DataFrame, coverage: pd.DataFrame, selected: pd.DataFrame, notes: pd.DataFrame, limits: pd.DataFrame, gates: pd.DataFrame, next_plan: pd.DataFrame, reqdf: pd.DataFrame) -> str:
    return "\n".join([
        "# GOLD V2 25C46 CoreB G1 filter coverage review audit-only report", "",
        f"Created UTC: {summary['created_utc']}",
        f"Step: `{STEP}`",
        f"Logical step alias: `{LOGICAL_STEP_ALIAS}`",
        f"Status: `{summary['status']}`", "",
        "## Scope", "",
        "25C46 is a filter coverage review / plan-only step. It reads corrected 25C45 artifacts and computes coverage by unique damaged key. It does not run replay, change conditions, approve variants, recover sources, unblock live behavior, call AI, notify Discord, place MT5 orders, or create final signals.", "",
        "## Count semantics", "",
        f"- Unique damaged-key population: {summary['known_unique_damage_keys']}",
        f"- Filter attribution rows: {summary['filter_attribution_rows']}",
        "- Coverage key: `variant + dataset + entry_time + policy`.",
        "- Filter-attribution rows are not summed as row-level damage.", "",
        "## Input audit", "", md_table(input_audit), "",
        "## 25C45 contract audit", "", md_table(contract), "",
        "## Coverage matrix", "", md_table(coverage), "",
        "## Selected representative coverage plan", "", md_table(selected), "",
        "## Notes", "", md_table(notes), "",
        "## Limits", "", md_table(limits), "",
        "## Gates", "", md_table(gates), "",
        "## File request list", "", "```text",
        "00_不要_貼らなくてOK",
        *[f"00-{i + 1}. {x}" for i, x in enumerate(reqdf[reqdf["section"].eq("00_不要_貼らなくてOK")]["item"].tolist())],
        "", "必要・見るファイル",
        *[f"{i + 1:02d}. {x}" for i, x in enumerate(reqdf[reqdf["section"].eq("必要・見るファイル")]["item"].tolist())],
        "```", "",
        "## Next step plan", "", md_table(next_plan), "",
        "## Safety", "",
        "- A002/A004 are not approved by this step; A002 can only be a representative candidate when tied.",
        "- 25C47 must not start until these 25C46 artifacts are produced and reviewed.",
        "- Discord, MT5, AI API, live hook, live evaluator unblock, and final signal remain OFF.",
        "- NO_SIGNAL must not notify Discord.",
    ])


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input-dir", default=None, help="Optional explicit 25C45 output directory")
    ap.add_argument("--output-dir", default=None, help="Optional explicit 25C46 output directory")
    args = ap.parse_args(argv)

    input_dir = Path(args.input_dir).resolve() if args.input_dir else fx_outputs() / IN45
    out = Path(args.output_dir).resolve() if args.output_dir else fx_outputs() / OUT_DIR
    lp(out).mkdir(parents=True, exist_ok=True)

    req = {
        "summary45": input_dir / "02_25c45_coreb_g1_incremental_damage_filter_attribution_summary.json",
        "attribution_rows45": input_dir / "04_25c45_incremental_damage_key_filter_attribution_rows.csv",
        "retention_candidates45": input_dir / "07_25c45_filter_retention_candidate_matrix.csv",
        "quality45": input_dir / "08_25c45_attribution_quality_matrix.csv",
    }
    input_audit = pd.DataFrame([exists_row(k, v) for k, v in req.items()])
    write_csv(out / "03_25c46_input_audit.csv", input_audit)
    if not bool(input_audit["exists"].all()):
        return stop_outputs(out, STOP_MISSING, input_audit, input_audit, int((input_audit["status"] == "STOP").sum()))

    summary45 = read_json(req["summary45"])
    attr = read_csv(req["attribution_rows45"])
    retention = read_csv(req["retention_candidates45"])
    quality = read_csv(req["quality45"])

    try:
        attr = norm_key_columns(attr, ["filter"])
    except Exception as e:
        diag = pd.DataFrame([{"check": "attribution required columns", "observed": str(e), "status": "STOP"}])
        return stop_outputs(out, STOP_CONTRACT, input_audit, diag, 1, summary45)

    contract = contract_audit(summary45, quality, attr, retention)
    if bool((contract["status"] == "STOP").any()):
        return stop_outputs(out, STOP_CONTRACT, input_audit, contract, int((contract["status"] == "STOP").sum()), summary45)

    try:
        coverage = build_coverage_matrix(attr, retention)
    except Exception as e:
        diag = pd.DataFrame([{"check": "coverage matrix build", "observed": str(e), "status": "STOP"}])
        return stop_outputs(out, STOP_CONTRACT, input_audit, diag, 1, summary45)

    selected = select_plan(coverage)
    if selected.empty:
        write_csv(out / "04_25c46_coverage_matrix.csv", coverage)
        diag = pd.DataFrame([{"check": "full known-key coverage candidate exists", "observed": False, "status": "STOP"}])
        return stop_outputs(out, STOP_COVERAGE, input_audit, diag, 1, summary45)

    selected_one = selected[selected["selected_representative"].astype(bool)].head(1).iloc[0].to_dict()
    notes = pd.DataFrame([
        {"note_id": "N001", "note": "Coverage was computed by unique key only: variant+dataset+entry_time+policy.", "status": "PASS"},
        {"note_id": "N002", "note": "filter_attribution_rows=1260 is not treated as a damaged-key population.", "status": "PASS"},
        {"note_id": "N003", "note": "Selected row is a representative coverage plan only and is not approval of A002/A004 or any variant.", "status": "PASS"},
        {"note_id": "N004", "note": "A002 is preferred over A004 only when tied by the documented selection rule.", "status": "PASS"},
        {"note_id": "N005", "note": "No replay, condition change, source change, recovery, live path, external path, AI review, notification, order, or final signal executed.", "status": "PASS"},
    ])
    limits = safety_limits_df()
    gates = pd.DataFrame([
        {"gate_id": "G001", "gate": "25C45 corrected contract safe", "observed": True, "status": "PASS"},
        {"gate_id": "G002", "gate": "coverage uses unique damaged keys only", "observed": True, "status": "PASS"},
        {"gate_id": "G003", "gate": "full known-key coverage candidate exists", "observed": True, "status": "PASS"},
        {"gate_id": "G004", "gate": "variant approval", "observed": False, "status": "BLOCKED_NOT_IN_25C46"},
        {"gate_id": "G005", "gate": "future replay or dry-run", "observed": False, "status": "BLOCKED_REQUIRES_SEPARATE_ACCEPTANCE"},
        {"gate_id": "G006", "gate": "25C47 may start", "observed": False, "status": "BLOCKED_UNTIL_25C46_ARTIFACT_REVIEW"},
        {"gate_id": "G007", "gate": "live/external/AI actions", "observed": False, "status": "BLOCKED"},
    ])
    next_plan = pd.DataFrame([
        {"rank": 1, "next_step": NEXT_STEP, "allowed_now": False, "purpose": "review 25C46 output artifacts first; next step remains audit-only planning", "requires_artifact_review_before_start": True, "execution_allowed_in_25c46": False},
        {"rank": 2, "next_step": "future replay/dry-run/condition change/source change", "allowed_now": False, "purpose": "not part of 25C46; requires separate explicit acceptance", "requires_artifact_review_before_start": True, "execution_allowed_in_25c46": False},
        {"rank": 3, "next_step": "CoreB live evaluator / final signal / Discord / MT5 / AI API", "allowed_now": False, "purpose": "blocked until explicitly approved after later audit stages", "requires_artifact_review_before_start": True, "execution_allowed_in_25c46": False},
    ])

    write_csv(out / "00_不要_25c46_file_request_list.csv", file_request_df())
    write_csv(out / "03_25c46_input_audit.csv", input_audit)
    write_csv(out / "04_25c46_coverage_matrix.csv", coverage)
    write_csv(out / "05_25c46_selected_coverage_plan.csv", selected)
    write_csv(out / "06_25c46_notes.csv", notes)
    write_csv(out / "07_25c46_limits.csv", limits)
    write_csv(out / "08_25c46_gates.csv", gates)
    write_csv(out / "09_25c46_next_step_plan.csv", next_plan)

    summary = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "step": STEP,
        "logical_step_alias": LOGICAL_STEP_ALIAS,
        "status": STATUS,
        "audit_only": True,
        "review_plan_only": True,
        "input_25c45_dir": str(input_dir),
        "output_dir": str(out),
        "input_25c45_step": summary45.get("step"),
        "input_25c45_status": summary45.get("status"),
        "input_25c45_next_recommended_step": summary45.get("next_recommended_step"),
        "known_unique_damage_keys": int(attr[KEYV].drop_duplicates().shape[0]),
        "unique_incremental_damage_keys": int(summary45.get("unique_incremental_damage_keys")),
        "filter_attribution_rows": int(summary45.get("filter_attribution_rows")),
        "unique_cleanly_attributed_damage_keys": int(summary45.get("unique_cleanly_attributed_damage_keys")),
        "cleanly_attributed_rows": int(summary45.get("cleanly_attributed_rows")),
        "unique_not_cleanly_attributed_damage_keys": int(summary45.get("unique_not_cleanly_attributed_damage_keys")),
        "coverage_rows": int(len(coverage)),
        "full_coverage_candidate_rows": int(selected.shape[0]),
        "selected_variant": selected_one.get("variant"),
        "selected_variant_code": selected_one.get("variant_code"),
        "selected_retention_priority_cutoff": int(selected_one.get("retention_priority_cutoff")),
        "selected_total_unique_damage_keys": int(selected_one.get("total_unique_damage_keys")),
        "selected_covered_unique_keys": int(selected_one.get("covered_unique_keys")),
        "selected_open_unique_keys": int(selected_one.get("open_unique_keys")),
        "selected_retained_filter_count": int(selected_one.get("retained_filter_count")),
        "selected_approval_status": "NOT_APPROVED_REVIEW_ONLY",
        "a002_a004_approval_status": "NOT_APPROVED_REVIEW_ONLY",
        "replay_executed": False,
        "dry_run_executed": False,
        "condition_changed": False,
        "source_recovery_executed": False,
        "source_mutation_executed": False,
        "variant_approved": False,
        "best_variant_approved": False,
        "coreb_live_evaluator_unblocked": False,
        "discord_notification_sent": False,
        "mt5_order_sent": False,
        "ai_api_called": False,
        "live_hook_executed": False,
        "final_signal_created": False,
        "no_signal_discord_notify": False,
        "next_recommended_step": NEXT_STEP,
        "requires_25c46_artifact_review_before_25c47": True,
        "total_stop_rows": 0,
    }
    write_json(out / "02_25c46_filter_coverage_review_summary.json", summary)
    report = build_report(summary, input_audit, contract, coverage, selected, notes, limits, gates, next_plan, file_request_df())
    lp(out / "01_25c46_GOLD_V2_COREB_G1_FILTER_COVERAGE_REVIEW_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")

    print(json.dumps({
        "status": STATUS,
        "step": STEP,
        "logical_step_alias": LOGICAL_STEP_ALIAS,
        "known_unique_damage_keys": summary["known_unique_damage_keys"],
        "filter_attribution_rows": summary["filter_attribution_rows"],
        "coverage_rows": summary["coverage_rows"],
        "full_coverage_candidate_rows": summary["full_coverage_candidate_rows"],
        "selected_variant": summary["selected_variant"],
        "selected_approval_status": summary["selected_approval_status"],
        "next_recommended_step": NEXT_STEP,
        "ai_api_called": False,
        "replay_executed": False,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
