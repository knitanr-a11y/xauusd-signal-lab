#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations
import json, math, hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import numpy as np
import pandas as pd

STEP = "17E_MEDIUM_FULL_SET_POST_17C_17D_CONSOLIDATION_AUDIT_ONLY"
OUT_DIR_NAME = "gold_v2_17e_medium_full_set_post_17c_17d_consolidation_audit_only"
REPORT_NAME = "GOLD_V2_17E_MEDIUM_FULL_SET_POST_17C_17D_CONSOLIDATION_AUDIT_ONLY_REPORT.md"
SUCCESS_STATUS = "MEDIUM_FULL_SET_POST_17C_17D_CONSOLIDATED_AUDIT_ONLY_LIVE_BLOCKED"
STOP_STATUS = "MEDIUM_FULL_SET_POST_17C_17D_CONSOLIDATION_STOPPED_AUDIT_ONLY"
EXTERNAL_ACTIONS = {"discord_send_allowed": False, "mt5_order_allowed": False, "ai_api_allowed": False, "live_hook_allowed": False}
INPUTS = {
    "tier2_13l_summary": ("gold_v2_13l_medium_tier2_hvt_candidate_mapping_load_smoke_audit", "gold_v2_13l_load_smoke_summary.json"),
    "range96_17c_summary": ("gold_v2_17c_range96_refined_reconciliation_audit_only", "gold_v2_17c_range96_reconciliation_summary.json"),
    "range96_17c_freeze_preview": ("gold_v2_17c_range96_refined_reconciliation_audit_only", "gold_v2_17c_range96_candidate_source_freeze_preview.json"),
    "vol_17d_summary": ("gold_v2_17d_vol_trmean32_refined_reconciliation_audit_only", "gold_v2_17d_vol_trmean32_reconciliation_summary.json"),
    "vol_17d_freeze_preview": ("gold_v2_17d_vol_trmean32_refined_reconciliation_audit_only", "gold_v2_17d_vol_trmean32_candidate_source_freeze_preview.json"),
    "matrix_17a": ("gold_v2_17a_medium_full_set_source_arbitration_audit_only", "gold_v2_17a_medium_arbitration_matrix.csv"),
    "matrix_17b": ("gold_v2_17b_medium_non_tier2_component_replay_planning_audit_only", "gold_v2_17b_replay_planning_matrix.csv"),
}
EXPECTED = {
    "TIER2_HVT": {"status": "MEDIUM_TIER2_HVT_CANDIDATE_MAPPING_LOAD_SMOKE_PASSED"},
    "RANGE96_REFINED": {"status": "RANGE96_REFINED_SOURCE_RECONCILIATION_READY_FOR_CANDIDATE_SOURCE_FREEZE_AUDIT_ONLY", "rule_ledger_rows": 51, "combined_ledger_rows": 117},
    "VOL_TRMEAN32_REFINED": {"status": "VOL_TRMEAN32_REFINED_SOURCE_RECONCILIATION_READY_FOR_CANDIDATE_SOURCE_FREEZE_AUDIT_ONLY", "rule_ledger_rows": 36, "combined_ledger_rows": 104},
}


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def fx_outputs() -> Path:
    root = repo_root()
    return (root.parents[1] if len(root.parents) >= 2 else root.parent) / "FX_OUTPUTS"


def output_dir() -> Path:
    p = fx_outputs() / OUT_DIR_NAME
    p.mkdir(parents=True, exist_ok=True)
    return p


def input_path(role: str) -> Path:
    folder, name = INPUTS[role]
    return fx_outputs() / folder / name


def clean(v: Any) -> Any:
    if isinstance(v, dict):
        return {str(k): clean(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [clean(x) for x in v]
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating, float)):
        if math.isnan(float(v)):
            return None
        return float(v)
    try:
        if pd.isna(v):
            return None
    except Exception:
        pass
    return v


def write_json(path: Path, obj: dict[str, Any]) -> None:
    path.write_text(json.dumps(clean(obj), ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")


def write_csv(df: pd.DataFrame, path: Path) -> None:
    df.to_csv(path, index=False, encoding="utf-8-sig")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path)


def bool_value(v: Any) -> bool:
    if isinstance(v, (bool, np.bool_)):
        return bool(v)
    return str(v).strip().lower() in {"true", "1", "yes", "y"}


def markdown_table(df: pd.DataFrame, limit: int = 80) -> str:
    if df.empty:
        return "_No rows._"
    lines = ["| " + " | ".join(map(str, df.columns)) + " |", "| " + " | ".join(["---"] * len(df.columns)) + " |"]
    for _, row in df.head(limit).iterrows():
        lines.append("| " + " | ".join(str(row[c]).replace("|", "\\|").replace("\n", " ") for c in df.columns) + " |")
    return "\n".join(lines)


def input_audit() -> pd.DataFrame:
    rows = []
    for role in INPUTS:
        path = input_path(role)
        row = {"role": role, "path": str(path), "required": True, "exists": path.exists()}
        if path.exists():
            row["sha256"] = sha256_file(path)
            row["bytes"] = path.stat().st_size
        rows.append(row)
    return pd.DataFrame(rows)


def get_status(obj: dict[str, Any]) -> str:
    return str(obj.get("status") or obj.get("gate_status") or obj.get("load_smoke_status") or obj.get("overall_status") or "")


def safe_false(obj: dict[str, Any], key: str) -> bool:
    return bool_value(obj.get(key, False)) is False


def component_row(df: pd.DataFrame, component: str) -> pd.Series | None:
    if "component" not in df.columns:
        return None
    sub = df[df["component"].astype(str).eq(component)]
    return None if sub.empty else sub.iloc[0]


def build_after_missing(out: Path, now: str, audit: pd.DataFrame) -> int:
    missing = audit[audit["required"].eq(True) & ~audit["exists"].eq(True)]
    blockers = pd.DataFrame([
        ["17E-BINPUT", "MEDIUM_FULL_SET", "HARD", "OPEN", "required inputs", "Missing: " + "|".join(missing["role"].astype(str))],
        ["17E-B099", "SAFETY", "SAFETY", "OPEN", "external actions", "All external actions remain false."],
    ], columns=["blocker_id", "component", "severity", "status", "blocked_item", "required_resolution"])
    write_csv(blockers, out / "gold_v2_17e_blockers.csv")
    write_json(out / "gold_v2_17e_medium_full_set_consolidation_summary.json", {"created_utc": now, "step": STEP, "status": STOP_STATUS, "audit_only": True, "missing_required_inputs": missing[["role", "path"]].to_dict("records"), "medium_live_evaluator_allowed": False, "final_signal_allowed": False, "external_actions": EXTERNAL_ACTIONS})
    (out / REPORT_NAME).write_text("\n".join(["# GOLD V2 17E MEDIUM full-set post 17C/17D consolidation audit-only report", "", f"Created UTC: {now}", f"Status: `{STOP_STATUS}`", "", markdown_table(audit), "", markdown_table(blockers)]), encoding="utf-8")
    print(json.dumps({"status": STOP_STATUS, "output_dir": str(out)}, ensure_ascii=False, indent=2))
    return 2


def main() -> int:
    out = output_dir()
    now = datetime.now(timezone.utc).isoformat()
    audit = input_audit()
    write_csv(audit, out / "gold_v2_17e_input_audit.csv")
    if len(audit[audit["required"].eq(True) & ~audit["exists"].eq(True)]):
        return build_after_missing(out, now, audit)

    tier2 = read_json(input_path("tier2_13l_summary"))
    r17c = read_json(input_path("range96_17c_summary"))
    r17c_freeze = read_json(input_path("range96_17c_freeze_preview"))
    v17d = read_json(input_path("vol_17d_summary"))
    v17d_freeze = read_json(input_path("vol_17d_freeze_preview"))
    m17a = read_csv(input_path("matrix_17a"))
    m17b = read_csv(input_path("matrix_17b"))

    status_rows = []
    checks = []
    def add_check(cid: str, comp: str, check: str, observed: Any, expected: Any) -> None:
        checks.append([cid, comp, check, observed, expected, "PASS" if observed == expected else "STOP"])

    tier2_status = get_status(tier2)
    add_check("17E-TIER2-STATUS", "TIER2_HVT", "13L status", tier2_status, EXPECTED["TIER2_HVT"]["status"])
    status_rows.append(["TIER2_HVT", "13L", tier2_status, "candidate mapping/load-smoke", "not final signal", False, False])

    for comp, obj, freeze, prefix in [
        ("RANGE96_REFINED", r17c, r17c_freeze, "17C"),
        ("VOL_TRMEAN32_REFINED", v17d, v17d_freeze, "17D"),
    ]:
        exp = EXPECTED[comp]
        obs_status = get_status(obj)
        counts = obj.get("observed_counts", {}) or {}
        add_check(f"17E-{prefix}-STATUS", comp, f"{prefix} status", obs_status, exp["status"])
        add_check(f"17E-{prefix}-RULE", comp, "rule_ledger_rows", int(counts.get("rule_ledger_rows", -1)), exp["rule_ledger_rows"])
        add_check(f"17E-{prefix}-COMBINED", comp, "combined_ledger_rows", int(counts.get("combined_ledger_rows", -1)), exp["combined_ledger_rows"])
        add_check(f"17E-{prefix}-KEYS", comp, "rule_keys_missing_in_combined", int(obj.get("rule_keys_missing_in_combined", -1)), 0)
        add_check(f"17E-{prefix}-SAFETY-LIVE", comp, "medium_live_evaluator_allowed", bool_value(obj.get("medium_live_evaluator_allowed", False)), False)
        add_check(f"17E-{prefix}-SAFETY-FINAL", comp, "final_signal_allowed", bool_value(obj.get("final_signal_allowed", False)), False)
        add_check(f"17E-{prefix}-FREEZE", comp, "freeze preview candidate status", str(freeze.get("candidate_status", "")), "SOURCE_ROW_FREEZE_PREVIEW_WRITTEN_NOT_EXECUTABLE_RULE_NOT_LIVE")
        row_a = component_row(m17a, comp)
        row_b = component_row(m17b, comp)
        add_check(f"17E-{prefix}-17A-ROW", comp, "17A component row exists", row_a is not None, True)
        add_check(f"17E-{prefix}-17B-ROW", comp, "17B component row exists", row_b is not None, True)
        if row_a is not None:
            add_check(f"17E-{prefix}-17A-RULE", comp, "17A rule_ledger_rows", int(row_a.get("rule_ledger_rows", -1)), exp["rule_ledger_rows"])
            add_check(f"17E-{prefix}-17A-COMBINED", comp, "17A combined_ledger_rows", int(row_a.get("combined_ledger_rows", -1)), exp["combined_ledger_rows"])
            add_check(f"17E-{prefix}-17A-STATUS", comp, "17A arbitration_status", str(row_a.get("arbitration_status", "")), "NEEDS_REPLAY_PARITY")
        if row_b is not None:
            add_check(f"17E-{prefix}-17B-RULE", comp, "17B rule_ledger_rows", int(row_b.get("rule_ledger_rows", -1)), exp["rule_ledger_rows"])
            add_check(f"17E-{prefix}-17B-COMBINED", comp, "17B combined_ledger_rows", int(row_b.get("combined_ledger_rows", -1)), exp["combined_ledger_rows"])
            add_check(f"17E-{prefix}-17B-PLAN", comp, "17B planned_step", str(row_b.get("planned_step", "")), prefix)
            add_check(f"17E-{prefix}-17B-STATUS", comp, "17B planning_status", str(row_b.get("planning_status", "")), "PLAN_READY")
        status_rows.append([comp, prefix, obs_status, "source reconciliation + freeze preview", "not executable live rule", bool_value(obj.get("medium_live_evaluator_allowed", False)), bool_value(obj.get("final_signal_allowed", False))])

    safety = pd.DataFrame([
        ["audit_only", True, True, "PASS"],
        ["medium_live_evaluator_allowed", False, False, "PASS"],
        ["final_signal_allowed", False, False, "PASS"],
        ["discord_send_allowed", False, False, "PASS"],
        ["mt5_order_allowed", False, False, "PASS"],
        ["ai_api_allowed", False, False, "PASS"],
        ["live_hook_allowed", False, False, "PASS"],
    ], columns=["safety_item", "observed", "expected", "status"])
    component_status = pd.DataFrame(status_rows, columns=["component", "source_step", "status", "readiness", "live_note", "medium_live_evaluator_allowed", "final_signal_allowed"])
    readiness = pd.DataFrame(checks, columns=["check_id", "component", "check", "observed", "expected", "status"])
    ok = readiness[readiness["status"].eq("STOP")].empty and safety[safety["status"].eq("STOP")].empty
    status = SUCCESS_STATUS if ok else STOP_STATUS

    blockers_rows = []
    for _, row in readiness[readiness["status"].eq("STOP")].iterrows():
        blockers_rows.append(["17E-BREADY", row["component"], "HARD", "OPEN", row["check"], f"observed={row['observed']} expected={row['expected']}"])
    blockers_rows += [
        ["17E-B010", "MEDIUM_FULL_SET", "HARD", "OPEN", "executable full-set rule", "17E is consolidation only; candidate mapping/load-smoke design must be a later audit-only step."],
        ["17E-B020", "MEDIUM_FULL_SET", "HARD", "OPEN", "live evaluator", "CoreA/CoreB/MEDIUM live parity and executable rules remain unapproved."],
        ["17E-B099", "SAFETY", "SAFETY", "OPEN", "external actions", "Keep final_signal_allowed=false, Discord=false, MT5=false, AI=false, live_hook=false. NO_SIGNAL must not notify Discord."],
    ]
    blockers = pd.DataFrame(blockers_rows, columns=["blocker_id", "component", "severity", "status", "blocked_item", "required_resolution"])
    next_steps = pd.DataFrame([
        ["17F", "MEDIUM_FULL_SET_CANDIDATE_MAPPING_PLAN_AUDIT_ONLY", "allowed_after_17E_success", ok, "Design only; no final/live/external actions."],
        ["LIVE", "MEDIUM_LIVE_EVALUATOR", "blocked", False, "Executable rule parity/load-smoke/dry-run gates are not completed."],
    ], columns=["next_step", "name", "status", "allowed_now", "note"])

    write_csv(component_status, out / "gold_v2_17e_component_status_matrix.csv")
    write_csv(readiness, out / "gold_v2_17e_readiness_checks.csv")
    write_csv(next_steps, out / "gold_v2_17e_next_steps.csv")
    write_csv(blockers, out / "gold_v2_17e_blockers.csv")
    write_csv(safety, out / "gold_v2_17e_safety_matrix.csv")
    summary = {"created_utc": now, "step": STEP, "status": status, "audit_only": True, "tier2_hvt_status": tier2_status, "range96_status": get_status(r17c), "vol_trmean32_status": get_status(v17d), "readiness_ok": ok, "medium_full_set_consolidated": ok, "medium_live_evaluator_allowed": False, "final_signal_allowed": False, "external_actions": EXTERNAL_ACTIONS, "next_recommended_step": "17F_MEDIUM_FULL_SET_CANDIDATE_MAPPING_PLAN_AUDIT_ONLY" if ok else "STOP_REVIEW_17E_OUTPUTS"}
    write_json(out / "gold_v2_17e_medium_full_set_consolidation_summary.json", summary)
    report = ["# GOLD V2 17E MEDIUM full-set post 17C/17D consolidation audit-only report", "", f"Created UTC: {now}", f"Status: `{status}`", "", "## Final decision", "- 17E consolidates TIER2_HVT, RANGE96_REFINED, and VOL_TRMEAN32_REFINED readiness only.", "- No OHLC rediscovery or approximate live rule was implemented.", "- No final signal, Discord, MT5, AI API, or live hook was enabled.", "", "## Input audit", markdown_table(audit), "", "## Component status matrix", markdown_table(component_status), "", "## Readiness checks", markdown_table(readiness), "", "## Next steps", markdown_table(next_steps), "", "## Blockers", markdown_table(blockers), "", "## Safety", markdown_table(safety)]
    (out / REPORT_NAME).write_text("\n".join(report), encoding="utf-8")
    print(json.dumps(clean({"status": status, "output_dir": str(out), "next_recommended_step": summary["next_recommended_step"]}), ensure_ascii=False, indent=2))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
