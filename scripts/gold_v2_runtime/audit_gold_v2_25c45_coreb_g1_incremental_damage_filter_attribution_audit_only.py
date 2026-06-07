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

STEP = "25C45_COREB_G1_INCREMENTAL_DAMAGE_FILTER_ATTRIBUTION_AUDIT_ONLY"
STATUS = "COREB_G1_INCREMENTAL_DAMAGE_FILTER_ATTRIBUTION_COMPLETED_AUDIT_ONLY_RETENTION_PLAN_REQUIRED"
STOP_MISSING = "25C45_STOP_MISSING_INPUT_AUDIT_ONLY"
STOP_CONTRACT = "25C45_STOP_25C44_CONTRACT_UNSAFE_AUDIT_ONLY"
STOP_ATTR = "25C45_STOP_ATTRIBUTION_INCOMPLETE_AUDIT_ONLY"
OUT_DIR = "gold_v2_25c45_coreb_g1_incremental_damage_filter_attribution_audit_only"
IN44 = "gold_v2_25c44_coreb_g1_right_only_damage_route_plan_audit_only"
IN43 = "gold_v2_25c43_coreb_g1_right_only_driver_review_audit_only"
IN36 = "gold_v2_25c36_coreb_g1_over_narrowing_adjustment_plan_audit_only"
IN10 = "gold_v2_25c10_coreb_target_filter_contract_replay_dry_run_audit_only"
EXPECTED_STEP_44 = "25C44_COREB_G1_RIGHT_ONLY_DAMAGE_ROUTE_PLAN_AUDIT_ONLY"
EXPECTED_STATUS_44 = "COREB_G1_RIGHT_ONLY_DAMAGE_ROUTE_PLAN_READY_AUDIT_ONLY_FILTER_ATTRIBUTION_REQUIRED"
EXPECTED_NEXT_44 = "25C45_COREB_G1_INCREMENTAL_DAMAGE_FILTER_ATTRIBUTION_AUDIT_ONLY"
NEXT_STEP = "25C46_COREB_G1_RETENTION_AWARE_RECOVERY_PLAN_AUDIT_ONLY"
DAMAGE_CLASS = "INCREMENTAL_DAMAGE_FROM_BASELINE_BOTH"
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


def norm_key(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for c in KEY:
        if c not in out.columns:
            out[c] = ""
        out[c] = out[c].astype(str)
    return out


def exists_row(role: str, p: Path) -> dict:
    ok = lp(p).exists()
    return {"role": role, "path": str(p), "exists": ok, "status": "PASS" if ok else "STOP"}


def file_request_df() -> pd.DataFrame:
    keep = [
        "01_25c45_GOLD_V2_COREB_G1_INCREMENTAL_DAMAGE_FILTER_ATTRIBUTION_AUDIT_ONLY_REPORT.md",
        "02_25c45_coreb_g1_incremental_damage_filter_attribution_summary.json",
        "03_25c45_input_audit.csv",
        "04_25c45_incremental_damage_key_filter_attribution_rows.csv",
        "05_25c45_filter_damage_by_variant_matrix.csv",
        "06_25c45_variant_excluded_filter_damage_matrix.csv",
        "07_25c45_filter_retention_candidate_matrix.csv",
        "08_25c45_attribution_quality_matrix.csv",
        "09_25c45_execution_boundary_matrix.csv",
        "10_25c45_acceptance_gate_matrix.csv",
        "11_25c45_next_step_plan.csv",
    ]
    drop = ["raw OHLC", "old GOLD/DISC8 files", "source recovery files", "new dry-run outputs", "AI review ledgers", "full 25C42 full-row CSV"]
    return pd.DataFrame(
        [{"section": "00_不要_貼らなくてOK", "rank": i + 1, "item": x} for i, x in enumerate(drop)]
        + [{"section": "必要・見るファイル", "rank": i + 1, "item": x} for i, x in enumerate(keep)]
    )


def write_stop(out: Path, status: str, input_audit: pd.DataFrame, diag: pd.DataFrame, stop_rows: int) -> int:
    write_csv(out / "00_不要_25c45_file_request_list.csv", file_request_df())
    for name in [
        "04_25c45_incremental_damage_key_filter_attribution_rows.csv",
        "05_25c45_filter_damage_by_variant_matrix.csv",
        "06_25c45_variant_excluded_filter_damage_matrix.csv",
        "07_25c45_filter_retention_candidate_matrix.csv",
        "08_25c45_attribution_quality_matrix.csv",
        "09_25c45_execution_boundary_matrix.csv",
        "10_25c45_acceptance_gate_matrix.csv",
    ]:
        write_csv(out / name, diag)
    write_csv(out / "11_25c45_next_step_plan.csv", pd.DataFrame([{"rank": 1, "next_step": "STOP", "allowed_now": False, "purpose": status}]))
    summary = {"created_utc": datetime.now(timezone.utc).isoformat(), "step": STEP, "status": status, "audit_only": True, "filter_attribution_executed": False, "dry_run_executed": False, "condition_changed": False, "source_recovery_executed": False, "source_mutation_executed": False, "coreb_live_evaluator_unblocked": False, "discord_notification_sent": False, "mt5_order_sent": False, "ai_api_called": False, "live_hook_executed": False, "final_signal_created": False, "no_signal_discord_notify": False, "total_stop_rows": int(stop_rows)}
    write_json(out / "02_25c45_coreb_g1_incremental_damage_filter_attribution_summary.json", summary)
    report = "\n".join(["# GOLD V2 25C45 CoreB G1 incremental damage filter attribution audit-only report", "", f"Created UTC: {summary['created_utc']}", f"Step: `{STEP}`", f"Status: `{status}`", "", "## Diagnostic", "", md_table(diag), "", "## Input audit", "", md_table(input_audit), "", "## Safety", "", "Stop status written. No dry-run, source recovery, live evaluator, Discord, MT5, AI API, live hook, or final signal executed."])
    lp(out / "01_25c45_GOLD_V2_COREB_G1_INCREMENTAL_DAMAGE_FILTER_ATTRIBUTION_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")
    return 2


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output-dir", default=None)
    args = ap.parse_args(argv)
    out = Path(args.output_dir).resolve() if args.output_dir else fx_outputs() / OUT_DIR
    lp(out).mkdir(parents=True, exist_ok=True)

    b44, b43, b36, b10 = fx_outputs() / IN44, fx_outputs() / IN43, fx_outputs() / IN36, fx_outputs() / IN10
    req = {
        "s44": b44 / "02_25c44_coreb_g1_right_only_damage_route_plan_summary.json",
        "class43": b43 / "04_25c43_right_only_driver_classification_matrix.csv",
        "bundles36": b36 / "04_25c36_adjusted_bundle_candidate_matrix.csv",
        "members36": b36 / "05_25c36_adjusted_bundle_membership.csv",
        "signals10": b10 / "04_25c10_filter_replay_signal_rows.csv",
    }
    input_audit = pd.DataFrame([exists_row(k, v) for k, v in req.items()])
    write_csv(out / "03_25c45_input_audit.csv", input_audit)
    if not bool(input_audit["exists"].all()):
        return write_stop(out, STOP_MISSING, input_audit, input_audit, int((input_audit["status"] == "STOP").sum()))

    s44 = read_json(req["s44"])
    contract = pd.DataFrame([
        {"contract_id": "C001", "check": "25C44 step matches expected", "observed": s44.get("step"), "status": "PASS" if s44.get("step") == EXPECTED_STEP_44 else "STOP"},
        {"contract_id": "C002", "check": "25C44 status filter attribution required", "observed": s44.get("status"), "status": "PASS" if s44.get("status") == EXPECTED_STATUS_44 else "STOP"},
        {"contract_id": "C003", "check": "25C44 audit_only true", "observed": s44.get("audit_only"), "status": "PASS" if as_bool(s44.get("audit_only", False)) else "STOP"},
        {"contract_id": "C004", "check": "25C44 selected route is filter attribution", "observed": s44.get("selected_route"), "status": "PASS" if s44.get("selected_route") == "INCREMENTAL_DAMAGE_FILTER_ATTRIBUTION_FIRST" else "STOP"},
        {"contract_id": "C005", "check": "25C44 next recommended step is 25C45", "observed": s44.get("next_recommended_step"), "status": "PASS" if s44.get("next_recommended_step") == EXPECTED_NEXT_44 else "STOP"},
        {"contract_id": "C006", "check": "25C44 dry_run false", "observed": s44.get("dry_run_executed"), "status": "PASS" if not as_bool(s44.get("dry_run_executed", True)) else "STOP"},
    ])
    if bool((contract["status"] == "STOP").any()):
        return write_stop(out, STOP_CONTRACT, input_audit, contract, int((contract["status"] == "STOP").sum()))

    class43 = norm_key(read_csv(req["class43"]))
    bundles = read_csv(req["bundles36"])
    members = read_csv(req["members36"])
    signals = norm_key(read_csv(req["signals10"]))
    if "filter" not in signals.columns:
        return write_stop(out, STOP_ATTR, input_audit, pd.DataFrame([{"check": "25C10 signals include filter column", "observed": False, "status": "STOP"}]), 1)

    damage = norm_key(class43[class43["driver_class"].astype(str).eq(DAMAGE_CLASS)].copy())
    unique_incremental_damage_keys = int(damage[KEYV].drop_duplicates().shape[0])
    sig = signals[KEY + ["filter"]].drop_duplicates().copy()
    sig["filter"] = sig["filter"].astype(str)
    attr = damage.merge(sig, on=KEY, how="left")
    attr["filter_attributed"] = attr["filter"].astype(str).ne("")

    excluded_rows = []
    for _, b in bundles.iterrows():
        bid = str(b["adjusted_bundle_id"])
        variant = bid + "_" + str(b["bundle_name"])
        for f in members[members["adjusted_bundle_id"].astype(str).eq(bid)]["filter"].astype(str).tolist():
            excluded_rows.append({"variant": variant, "filter": f, "filter_excluded_by_variant": True})
    excluded = pd.DataFrame(excluded_rows)
    if excluded.empty:
        return write_stop(out, STOP_ATTR, input_audit, pd.DataFrame([{"check": "25C36 excluded filter membership non-empty", "observed": False, "status": "STOP"}]), 1)

    attr = attr.merge(excluded, on=["variant", "filter"], how="left")
    attr["filter_excluded_by_variant"] = attr["filter_excluded_by_variant"].fillna(False).astype(bool)
    attr["cleanly_attributed"] = attr["filter_attributed"] & attr["filter_excluded_by_variant"]
    write_csv(out / "04_25c45_incremental_damage_key_filter_attribution_rows.csv", attr.sort_values(["variant"] + KEY + ["filter"]))

    by_filter = attr.groupby(["variant", "filter"], dropna=False).agg(
        filter_attribution_rows=("entry_time", "count"),
        unique_damaged_keys_for_filter=("entry_time", "nunique"),
        filter_excluded_by_variant=("filter_excluded_by_variant", "max"),
        cleanly_attributed_rows=("cleanly_attributed", "sum"),
    ).reset_index().sort_values(["variant", "filter_attribution_rows"], ascending=[True, False])
    write_csv(out / "05_25c45_filter_damage_by_variant_matrix.csv", by_filter)

    key_clean = attr.groupby(KEYV, dropna=False).agg(
        filter_attribution_rows=("filter", "count"),
        any_filter_attributed=("filter_attributed", "max"),
        any_cleanly_attributed=("cleanly_attributed", "max"),
    ).reset_index()
    unique_cleanly_attributed_damage_keys = int(key_clean["any_cleanly_attributed"].sum())
    unique_unattributed_damage_keys = int((~key_clean["any_filter_attributed"].astype(bool)).sum())
    unique_not_cleanly_attributed_damage_keys = int((~key_clean["any_cleanly_attributed"].astype(bool)).sum())

    variant_summary = key_clean.groupby("variant", dropna=False).agg(
        unique_incremental_damage_keys=("entry_time", "count"),
        unique_cleanly_attributed_damage_keys=("any_cleanly_attributed", "sum"),
        filter_attribution_rows=("filter_attribution_rows", "sum"),
    ).reset_index()
    variant_summary["clean_key_attribution_rate_pct"] = (variant_summary["unique_cleanly_attributed_damage_keys"] / variant_summary["unique_incremental_damage_keys"].replace(0, pd.NA) * 100).round(2).fillna(0)
    write_csv(out / "06_25c45_variant_excluded_filter_damage_matrix.csv", variant_summary)

    retention = by_filter[by_filter["filter_excluded_by_variant"].astype(bool)].copy()
    retention["retention_priority"] = retention.groupby("variant")["filter_attribution_rows"].rank(method="dense", ascending=False).astype(int)
    retention["candidate_action"] = "RETAIN_OR_REVIEW_FILTER_BEFORE_NEXT_BUNDLE"
    retention["approval_status"] = "NOT_APPROVED_PLAN_INPUT_ONLY"
    write_csv(out / "07_25c45_filter_retention_candidate_matrix.csv", retention)

    filter_attribution_rows = int(len(attr))
    cleanly_attributed_rows = int(attr["cleanly_attributed"].sum())
    unattributed_rows = int((~attr["filter_attributed"]).sum())
    attributed_not_excluded_rows = int((attr["filter_attributed"] & ~attr["filter_excluded_by_variant"]).sum())
    quality = pd.DataFrame([
        {"quality_id": "Q001", "check": "unique incremental damage keys loaded", "observed": unique_incremental_damage_keys, "status": "PASS" if unique_incremental_damage_keys > 0 else "STOP"},
        {"quality_id": "Q002", "check": "filter attribution rows created", "observed": filter_attribution_rows, "status": "PASS" if filter_attribution_rows >= unique_incremental_damage_keys and unique_incremental_damage_keys > 0 else "STOP"},
        {"quality_id": "Q003", "check": "all unique damaged keys have clean attribution", "observed": unique_not_cleanly_attributed_damage_keys, "status": "PASS" if unique_not_cleanly_attributed_damage_keys == 0 else "STOP"},
        {"quality_id": "Q004", "check": "all attribution rows have baseline filter", "observed": unattributed_rows, "status": "PASS" if unattributed_rows == 0 else "STOP"},
        {"quality_id": "Q005", "check": "all attributed rows are excluded by variant", "observed": attributed_not_excluded_rows, "status": "PASS" if attributed_not_excluded_rows == 0 else "STOP"},
    ])
    write_csv(out / "08_25c45_attribution_quality_matrix.csv", quality)
    if bool((quality["status"] == "STOP").any()):
        return write_stop(out, STOP_ATTR, input_audit, quality, int((quality["status"] == "STOP").sum()))

    boundary = pd.DataFrame([
        {"boundary": "filter_attribution_review", "allowed": True, "observed": True},
        {"boundary": "read_25c43_damage_keys", "allowed": True, "observed": True},
        {"boundary": "read_25c10_filter_rows", "allowed": True, "observed": True},
        {"boundary": "run_new_dry_run", "allowed": False, "observed": False},
        {"boundary": "new_variant_search", "allowed": False, "observed": False},
        {"boundary": "change_coreb_conditions", "allowed": False, "observed": False},
        {"boundary": "source_recovery", "allowed": False, "observed": False},
        {"boundary": "source_mutation", "allowed": False, "observed": False},
        {"boundary": "approve_variant", "allowed": False, "observed": False},
        {"boundary": "coreb_live_evaluator_unblock", "allowed": False, "observed": False},
        {"boundary": "discord_notification", "allowed": False, "observed": False},
        {"boundary": "mt5_order", "allowed": False, "observed": False},
        {"boundary": "ai_api_call", "allowed": False, "observed": False},
        {"boundary": "live_hook", "allowed": False, "observed": False},
        {"boundary": "final_signal", "allowed": False, "observed": False},
        {"boundary": "no_signal_discord_notify", "allowed": False, "observed": False},
    ])
    write_csv(out / "09_25c45_execution_boundary_matrix.csv", boundary)
    gates = pd.DataFrame([
        {"gate_id": "G001", "gate": "25C44 contract safe", "observed": True, "status": "PASS"},
        {"gate_id": "G002", "gate": "filter attribution complete", "observed": True, "status": "PASS"},
        {"gate_id": "G003", "gate": "retention-aware recovery plan can be planned now", "observed": True, "status": "PASS"},
        {"gate_id": "G004", "gate": "future dry-run allowed now", "observed": False, "status": "BLOCKED_PLAN_AND_ACCEPTANCE_REQUIRED"},
        {"gate_id": "G005", "gate": "CoreB live evaluator unblock", "observed": False, "status": "BLOCKED"},
        {"gate_id": "G006", "gate": "external actions / AI API", "observed": False, "status": "BLOCKED"},
    ])
    write_csv(out / "10_25c45_acceptance_gate_matrix.csv", gates)
    next_plan = pd.DataFrame([
        {"rank": 1, "next_step": NEXT_STEP, "allowed_now": True, "purpose": "design retention-aware recovery plan using attributed filters; no dry-run", "requires_human_acceptance_before_execution": False, "execution_allowed_in_25c45": False},
        {"rank": 2, "next_step": "future retention-aware dry-run", "allowed_now": False, "purpose": "blocked until 25C46 plan and explicit acceptance", "requires_human_acceptance_before_execution": True, "execution_allowed_in_25c45": False},
        {"rank": 3, "next_step": "CoreB live evaluator / final signal / Discord / MT5 / AI API", "allowed_now": False, "purpose": "blocked because no exact match and no source recovery approval", "requires_human_acceptance_before_execution": True, "execution_allowed_in_25c45": False},
    ])
    write_csv(out / "11_25c45_next_step_plan.csv", next_plan)
    write_csv(out / "00_不要_25c45_file_request_list.csv", file_request_df())

    summary = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "step": STEP,
        "status": STATUS,
        "audit_only": True,
        "filter_attribution_executed": True,
        "dry_run_executed": False,
        "condition_changed": False,
        "source_recovery_executed": False,
        "source_mutation_executed": False,
        "best_variant_approved": False,
        "coreb_live_evaluator_unblocked": False,
        "discord_notification_sent": False,
        "mt5_order_sent": False,
        "ai_api_called": False,
        "live_hook_executed": False,
        "final_signal_created": False,
        "no_signal_discord_notify": False,
        "unique_incremental_damage_keys": unique_incremental_damage_keys,
        "filter_attribution_rows": filter_attribution_rows,
        "unique_cleanly_attributed_damage_keys": unique_cleanly_attributed_damage_keys,
        "cleanly_attributed_rows": cleanly_attributed_rows,
        "unattributed_rows": unattributed_rows,
        "unique_unattributed_damage_keys": unique_unattributed_damage_keys,
        "attributed_not_excluded_rows": attributed_not_excluded_rows,
        "unique_not_cleanly_attributed_damage_keys": unique_not_cleanly_attributed_damage_keys,
        "retention_candidate_rows": int(len(retention)),
        "next_recommended_step": NEXT_STEP,
        "requires_human_acceptance_before_next_dry_run": True,
        "total_stop_rows": 0,
    }
    write_json(out / "02_25c45_coreb_g1_incremental_damage_filter_attribution_summary.json", summary)
    reqdf = file_request_df()
    report = "\n".join([
        "# GOLD V2 25C45 CoreB G1 incremental damage filter attribution audit-only report", "",
        f"Created UTC: {summary['created_utc']}", f"Step: `{STEP}`", f"Status: `{STATUS}`", "",
        "## Scope", "", "This step attributes incremental damage keys to baseline replay filters only. It does not run a dry-run, search variants, change conditions, approve variants, or unblock live behavior.", "",
        "## Count semantics", "", f"- Unique incremental damage keys: {unique_incremental_damage_keys}", f"- Filter attribution rows: {filter_attribution_rows}", "- One damaged key can map to multiple baseline filters, so attribution rows can exceed unique damaged keys.", "",
        "## 25C44 contract audit", "", md_table(contract), "", "## Attribution quality", "", md_table(quality), "", "## Filter damage by variant", "", md_table(by_filter), "", "## Variant attribution summary", "", md_table(variant_summary), "", "## Retention candidates", "", md_table(retention), "", "## Execution boundaries", "", md_table(boundary), "", "## Acceptance gates", "", md_table(gates), "", "## File request list", "", "```text", "00_不要_貼らなくてOK", *[f"00-{i+1}. {x}" for i, x in enumerate(reqdf[reqdf["section"].eq("00_不要_貼らなくてOK")]["item"].tolist())], "", "必要・見るファイル", *[f"{i+1:02d}. {x}" for i, x in enumerate(reqdf[reqdf["section"].eq("必要・見るファイル")]["item"].tolist())], "```", "", "## Next step plan", "", md_table(next_plan), "", "## Safety", "", "- 25C45 is attribution-only and does not approve any variant.", "- CoreB live evaluator, Discord, MT5, AI API, live hook, and final signal remain blocked.", "- Future dry-run remains blocked until retention-aware plan and separate explicit human acceptance.", "- NO_SIGNAL must not notify Discord."
    ])
    lp(out / "01_25c45_GOLD_V2_COREB_G1_INCREMENTAL_DAMAGE_FILTER_ATTRIBUTION_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")
    print(json.dumps({"status": STATUS, "unique_incremental_damage_keys": unique_incremental_damage_keys, "filter_attribution_rows": filter_attribution_rows, "unique_cleanly_attributed_damage_keys": unique_cleanly_attributed_damage_keys, "retention_candidate_rows": int(len(retention)), "next_recommended_step": NEXT_STEP, "dry_run_executed": False, "ai_api_called": False}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
