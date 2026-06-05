#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

STEP = "18I_TIER2_SOURCE_IDENTITY_EXTRACTION_DRY_RUN_DESIGN_AUDIT_ONLY"
OUT_DIR = "gold_v2_18i_tier2_source_identity_extraction_dry_run_design_audit_only"
REPORT = "GOLD_V2_18I_TIER2_ROW_LEVEL_SOURCE_IDENTITY_EXTRACTION_DRY_RUN_DESIGN_AUDIT_ONLY_REPORT.md"
SUCCESS = "TIER2_ROW_LEVEL_SOURCE_IDENTITY_EXTRACTION_DRY_RUN_DESIGN_READY_AUDIT_ONLY_SOURCE_RECOVERY_BLOCKED"
EXPECTED_18H = "TIER2_ROW_LEVEL_SOURCE_IDENTITY_EXTRACTION_PLAN_READY_AUDIT_ONLY_SOURCE_RECOVERY_BLOCKED"
IN_DIR = "gold_v2_18h_tier2_source_identity_extraction_plan_audit_only"
REQ_FIELDS = ["manifest_row_id", "component", "source_identity_type", "source_role", "source_row_number_1based", "source_key", "source_row_hash", "strategy_id", "source_status"]


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


def wtxt(path: Path, txt: str) -> None:
    ensure(path)
    lp(path).write_text(txt, encoding="utf-8")


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


def cell(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    return "" if text.lower() == "nan" else text


def pick_columns(row: pd.Series) -> str:
    direct = cell(row.get("direct_column", ""))
    derived = cell(row.get("candidate_columns_present", ""))
    return direct or derived


def mdtable(df: pd.DataFrame, limit: int = 80) -> str:
    if df.empty:
        return "_No rows._"
    cols = list(df.columns)
    out = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for _, row in df.head(limit).iterrows():
        out.append("| " + " | ".join(str(row[c]).replace("|", "\\|").replace("\n", " ") for c in cols) + " |")
    return "\n".join(out)


def main() -> int:
    base = fx() / IN_DIR
    out = fx() / OUT_DIR
    lp(out).mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()
    inputs = {
        "summary_18h": base / "gold_v2_18h_tier2_source_identity_extraction_plan_summary.json",
        "checks_18h": base / "gold_v2_18h_plan_checks.csv",
        "mapping_18h": base / "gold_v2_18h_identity_field_mapping_plan.csv",
        "ranking_18h": base / "gold_v2_18h_candidate_artifact_ranking.csv",
        "blockers_18h": base / "gold_v2_18h_blockers.csv",
        "safety_18h": base / "gold_v2_18h_safety_matrix.csv",
    }
    audit = pd.DataFrame([{"role": k, "path": str(v), "required": True, "exists": lp(v).exists()} for k, v in inputs.items()])
    wcsv(audit, out / "gold_v2_18i_input_audit.csv")
    if not audit["exists"].all():
        wjson(out / "gold_v2_18i_tier2_source_identity_extraction_dry_run_design_summary.json", {"created_utc": now, "step": STEP, "status": "18I_STOP_MISSING_INPUTS", "audit_only": True})
        return 2

    s18h = rjson(inputs["summary_18h"])
    checks18h = rcsv(inputs["checks_18h"])
    mapping = rcsv(inputs["mapping_18h"])
    ranking = rcsv(inputs["ranking_18h"])
    blockers = rcsv(inputs["blockers_18h"])
    safety18h = rcsv(inputs["safety_18h"])

    stop_checks_18h = int((checks18h["status"].astype(str) == "STOP").sum())
    stop_safety_18h = int((safety18h["status"].astype(str) == "STOP").sum())
    checks = pd.DataFrame([
        ["18I-C001", "18H status", s18h.get("status"), EXPECTED_18H, "PASS" if s18h.get("status") == EXPECTED_18H else "STOP"],
        ["18I-C002", "18H checks STOP rows", stop_checks_18h, 0, "PASS" if stop_checks_18h == 0 else "STOP"],
        ["18I-C003", "18H safety STOP rows", stop_safety_18h, 0, "PASS" if stop_safety_18h == 0 else "STOP"],
        ["18I-C004", "18H source recovery executed", bool(s18h.get("source_recovery_executed", False)), False, "PASS" if not bool(s18h.get("source_recovery_executed", False)) else "STOP"],
    ], columns=["check_id", "check", "observed", "expected", "status"])

    selected = ranking[ranking["inspection_status"].astype(str).str.contains("CSV", na=False)].copy()
    selected = selected.sort_values(["missing_required_fields", "direct_required_fields", "derivable_required_fields"], ascending=[True, False, False]).head(5).copy()
    selected["selection_role"] = ["PRIMARY" if i == 0 else "BACKUP" for i in range(len(selected))]
    selected["dry_run_design_only"] = True
    selected["source_recovery_executed"] = False

    recipe_rows = []
    for _, art in selected.iterrows():
        rel = str(art["relative_path"])
        sub = mapping[mapping["relative_path"].astype(str).eq(rel)]
        for field in REQ_FIELDS:
            m = sub[sub["field"].astype(str).eq(field)]
            if m.empty:
                status, cols, action = "NOT_AVAILABLE_IN_18H_PLAN", "", "BLOCK_DRY_RUN_FIELD"
            else:
                row = m.iloc[0]
                status = str(row.get("mapping_status", ""))
                cols = pick_columns(row)
                if status == "DIRECT_COLUMN_PRESENT":
                    action = "COPY_DIRECT_COLUMN_IN_FUTURE_DRY_RUN"
                elif status == "DERIVATION_CANDIDATE_COLUMNS_PRESENT":
                    action = "DERIVE_FIELD_IN_FUTURE_DRY_RUN_FROM_CANDIDATES"
                else:
                    action = "BLOCK_DRY_RUN_FIELD"
            recipe_rows.append({"relative_path": rel, "filename": art.get("filename", ""), "selection_role": art.get("selection_role", ""), "field": field, "mapping_status": status, "candidate_columns": cols, "future_dry_run_action": action, "dry_run_implemented": False, "source_recovery_executed": False, "row_hash_computed": False, "implementation_allowed": False, "final_signal_allowed": False})
    recipe = pd.DataFrame(recipe_rows)

    stop_conditions = pd.DataFrame([
        ["18I-S001", "attempt to read source data rows during 18I", "STOP"],
        ["18I-S002", "attempt to compute source_row_hash during 18I", "STOP"],
        ["18I-S003", "attempt to finalize or recover source identity during 18I", "STOP"],
        ["18I-S004", "attempt to reconstruct from OHLC", "STOP"],
        ["18I-S005", "attempt to enable implementation or replay", "STOP"],
        ["18I-S006", "attempt to enable live/final/external actions", "STOP"],
        ["18I-S007", "NO_SIGNAL Discord notification true", "STOP"],
    ], columns=["stop_id", "condition", "action"])
    nextg = pd.DataFrame([
        ["18J", "TIER2_ROW_LEVEL_SOURCE_IDENTITY_EXTRACTION_DRY_RUN_IMPLEMENTATION_PLAN_AUDIT_ONLY", "Plan a future dry-run implementation; no execution yet.", True],
        ["DRY_RUN_EXECUTION", "TIER2_SOURCE_IDENTITY_EXTRACTION_DRY_RUN_EXECUTION", "Blocked after 18I.", False],
        ["SOURCE_RECOVERY", "TIER2_SOURCE_IDENTITY_RECOVERY_EXECUTION", "Blocked after 18I.", False],
        ["LIVE", "MEDIUM_FULL_SET_LIVE_EVALUATOR", "Blocked.", False],
    ], columns=["next_step", "name", "purpose", "allowed_after_18i_success"])
    blockers = blockers.copy()
    blockers["carried_forward_by"] = STEP
    blockers["dry_run_implemented"] = False
    blockers["source_recovery_executed"] = False
    blockers["implementation_allowed"] = False
    blockers["live_or_final_allowed"] = False
    safety = pd.DataFrame([
        ["audit_only", True, True, "PASS"],
        ["dry_run_design_only", True, True, "PASS"],
        ["source_rows_read", False, False, "PASS"],
        ["row_hash_computed", False, False, "PASS"],
        ["source_recovery_executed", False, False, "PASS"],
        ["implementation_allowed", False, False, "PASS"],
        ["oh_lc_replay_allowed", False, False, "PASS"],
        ["live_enabled", False, False, "PASS"],
        ["final_signal_allowed", False, False, "PASS"],
        ["discord_send_allowed", False, False, "PASS"],
        ["mt5_order_allowed", False, False, "PASS"],
        ["ai_api_allowed", False, False, "PASS"],
        ["live_hook_allowed", False, False, "PASS"],
        ["no_signal_discord_notified", False, False, "PASS"],
    ], columns=["safety_item", "observed", "expected", "status"])

    ok = int((checks["status"].astype(str) == "STOP").sum()) == 0
    status = SUCCESS if ok else "18I_STOP_REVIEW_OUTPUTS"
    for name, df in [
        ("gold_v2_18i_design_checks.csv", checks),
        ("gold_v2_18i_selected_artifact_design.csv", selected),
        ("gold_v2_18i_dry_run_field_recipe.csv", recipe),
        ("gold_v2_18i_dry_run_stop_conditions.csv", stop_conditions),
        ("gold_v2_18i_required_next_gates.csv", nextg),
        ("gold_v2_18i_blockers.csv", blockers),
        ("gold_v2_18i_safety_matrix.csv", safety),
    ]:
        wcsv(df, out / name)
    summary = {"created_utc": now, "step": STEP, "status": status, "audit_only": True, "dry_run_design_ready": ok, "selected_artifacts": int(len(selected)), "recipe_rows": int(len(recipe)), "dry_run_implemented": False, "source_rows_read": False, "row_hash_computed": False, "source_recovery_executed": False, "implementation_allowed": False, "oh_lc_replay_allowed": False, "live_enabled": False, "final_signal_allowed": False, "external_actions": {"discord_send_allowed": False, "mt5_order_allowed": False, "ai_api_allowed": False, "live_hook_allowed": False}, "no_signal_discord_notified": False, "next_recommended_step": "18J_TIER2_ROW_LEVEL_SOURCE_IDENTITY_EXTRACTION_DRY_RUN_IMPLEMENTATION_PLAN_AUDIT_ONLY" if ok else "STOP_REVIEW_18I_OUTPUTS"}
    wjson(out / "gold_v2_18i_tier2_source_identity_extraction_dry_run_design_summary.json", summary)
    report = ["# GOLD V2 18I TIER2 row-level source identity extraction dry-run design audit-only report", "", f"Created UTC: {now}", f"Status: `{status}`", "", "## Final decision", "- 18I created a dry-run design only.", "- It did not read source rows, compute row hashes, recover identity, reconstruct from OHLC, implement predicates/arbitration, run replay, enable live/final, or enable external actions.", "", "## Checks", mdtable(checks), "", "## Selected artifact design", mdtable(selected), "", "## Dry-run field recipe", mdtable(recipe), "", "## Stop conditions", mdtable(stop_conditions), "", "## Next gates", mdtable(nextg), "", "## Blockers", mdtable(blockers), "", "## Safety", mdtable(safety)]
    wtxt(out / REPORT, "\n".join(report))
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
