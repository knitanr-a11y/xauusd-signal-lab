#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations
import json, math, hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import numpy as np
import pandas as pd

STEP = "17G_MEDIUM_FULL_SET_CANDIDATE_MAPPING_AUDIT_ONLY"
OUT_DIR_NAME = "gold_v2_17g_medium_full_set_candidate_mapping_audit_only"
REPORT_NAME = "GOLD_V2_17G_MEDIUM_FULL_SET_CANDIDATE_MAPPING_AUDIT_ONLY_REPORT.md"
SUCCESS_STATUS = "MEDIUM_FULL_SET_CANDIDATE_MAPPING_READY_AUDIT_ONLY_LIVE_BLOCKED"
STOP_STATUS = "MEDIUM_FULL_SET_CANDIDATE_MAPPING_STOPPED_AUDIT_ONLY"
EXPECTED_17F_STATUS = "MEDIUM_FULL_SET_CANDIDATE_MAPPING_PLAN_READY_AUDIT_ONLY_LIVE_BLOCKED"
EXPECTED_FREEZE_STATUS = "SOURCE_ROW_FREEZE_PREVIEW_WRITTEN_NOT_EXECUTABLE_RULE_NOT_LIVE"
EXTERNAL_ACTIONS = {"discord_send_allowed": False, "mt5_order_allowed": False, "ai_api_allowed": False, "live_hook_allowed": False}
INPUTS = {
    "summary_17f": ("gold_v2_17f_medium_full_set_candidate_mapping_plan_audit_only", "gold_v2_17f_medium_full_set_candidate_mapping_plan_summary.json"),
    "plan_17f": ("gold_v2_17f_medium_full_set_candidate_mapping_plan_audit_only", "gold_v2_17f_candidate_mapping_plan.csv"),
    "next_gates_17f": ("gold_v2_17f_medium_full_set_candidate_mapping_plan_audit_only", "gold_v2_17f_required_next_gates.csv"),
    "safety_17f": ("gold_v2_17f_medium_full_set_candidate_mapping_plan_audit_only", "gold_v2_17f_safety_matrix.csv"),
    "tier2_13l_summary": ("gold_v2_13l_medium_tier2_hvt_candidate_mapping_load_smoke_audit", "gold_v2_13l_load_smoke_summary.json"),
    "range96_index": ("gold_v2_17c_range96_refined_reconciliation_audit_only", "gold_v2_17c_range96_candidate_source_freeze_index.csv"),
    "range96_freeze": ("gold_v2_17c_range96_refined_reconciliation_audit_only", "gold_v2_17c_range96_candidate_source_freeze_preview.json"),
    "vol_index": ("gold_v2_17d_vol_trmean32_refined_reconciliation_audit_only", "gold_v2_17d_vol_trmean32_candidate_source_freeze_index.csv"),
    "vol_freeze": ("gold_v2_17d_vol_trmean32_refined_reconciliation_audit_only", "gold_v2_17d_vol_trmean32_candidate_source_freeze_preview.json"),
}
EXPECTED_COUNTS = {
    "RANGE96_REFINED": {"rule_ledger_rows": 51, "combined_ledger_rows": 117, "index_rows": 168},
    "VOL_TRMEAN32_REFINED": {"rule_ledger_rows": 36, "combined_ledger_rows": 104, "index_rows": 140},
    "TIER2_HVT": {"index_rows": 1},
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


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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


def stop_for_missing(out: Path, now: str, audit: pd.DataFrame) -> int:
    missing = audit[audit["required"].eq(True) & ~audit["exists"].eq(True)]
    blockers = pd.DataFrame([
        ["17G-BINPUT", "MEDIUM_FULL_SET", "HARD", "OPEN", "required inputs", "Missing: " + "|".join(missing["role"].astype(str))],
        ["17G-B099", "SAFETY", "SAFETY", "OPEN", "external actions", "All external actions remain false."],
    ], columns=["blocker_id", "component", "severity", "status", "blocked_item", "required_resolution"])
    write_csv(blockers, out / "gold_v2_17g_blockers.csv")
    write_json(out / "gold_v2_17g_medium_full_set_candidate_mapping_summary.json", {"created_utc": now, "step": STEP, "status": STOP_STATUS, "audit_only": True, "missing_required_inputs": missing[["role", "path"]].to_dict("records"), "medium_live_evaluator_allowed": False, "final_signal_allowed": False, "external_actions": EXTERNAL_ACTIONS})
    (out / REPORT_NAME).write_text("\n".join(["# GOLD V2 17G MEDIUM full-set candidate mapping audit-only report", "", f"Created UTC: {now}", f"Status: `{STOP_STATUS}`", "", markdown_table(audit), "", markdown_table(blockers)]), encoding="utf-8")
    print(json.dumps({"status": STOP_STATUS, "output_dir": str(out)}, ensure_ascii=False, indent=2))
    return 2


def add_check(rows: list[list[Any]], cid: str, check: str, observed: Any, expected: Any) -> None:
    rows.append([cid, check, observed, expected, "PASS" if observed == expected else "STOP"])


def build_manifest(tier2_summary: dict[str, Any], range_idx: pd.DataFrame, vol_idx: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    tier2_status = str(tier2_summary.get("status") or tier2_summary.get("gate_status") or tier2_summary.get("load_smoke_status") or tier2_summary.get("overall_status") or "")
    rows.append({
        "manifest_row_id": "TIER2_HVT|13L_SUMMARY_CHAIN_REFERENCE|000001",
        "component": "TIER2_HVT",
        "source_step": "13L",
        "source_identity_type": "13L_SUMMARY_CHAIN_REFERENCE",
        "source_role": "summary_reference",
        "source_row_number_1based": 1,
        "source_key": "13L_SUMMARY_CHAIN_REFERENCE",
        "strategy_id": "TIER2_HVT",
        "source_row_hash": hashlib.sha256(json.dumps(clean(tier2_summary), ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest(),
        "source_status": tier2_status,
        "live_executable": False,
        "final_signal_allowed": False,
    })
    for source_step, comp, df in [("17C", "RANGE96_REFINED", range_idx), ("17D", "VOL_TRMEAN32_REFINED", vol_idx)]:
        for i, row in df.reset_index(drop=True).iterrows():
            source_role = str(row.get("source_role", ""))
            row_no = int(row.get("source_row_number_1based", i + 1))
            source_hash = str(row.get("source_row_hash", ""))
            rows.append({
                "manifest_row_id": f"{comp}|{source_role}|{row_no:06d}|{source_hash[:12]}",
                "component": comp,
                "source_step": source_step,
                "source_identity_type": "SOURCE_ROW_HASH",
                "source_role": source_role,
                "source_row_number_1based": row_no,
                "source_key": str(row.get("source_key", "")),
                "strategy_id": str(row.get("strategy_id", comp)),
                "source_row_hash": source_hash,
                "source_status": "SOURCE_ROW_FREEZE_PREVIEW",
                "live_executable": False,
                "final_signal_allowed": False,
            })
    return pd.DataFrame(rows)


def main() -> int:
    out = output_dir()
    now = datetime.now(timezone.utc).isoformat()
    audit = input_audit()
    write_csv(audit, out / "gold_v2_17g_input_audit.csv")
    if len(audit[audit["required"].eq(True) & ~audit["exists"].eq(True)]):
        return stop_for_missing(out, now, audit)

    summary_17f = read_json(input_path("summary_17f"))
    plan_17f = read_csv(input_path("plan_17f"))
    gates_17f = read_csv(input_path("next_gates_17f"))
    safety_17f = read_csv(input_path("safety_17f"))
    tier2_summary = read_json(input_path("tier2_13l_summary"))
    range_idx = read_csv(input_path("range96_index"))
    range_freeze = read_json(input_path("range96_freeze"))
    vol_idx = read_csv(input_path("vol_index"))
    vol_freeze = read_json(input_path("vol_freeze"))

    checks: list[list[Any]] = []
    add_check(checks, "17G-C001", "17F status", str(summary_17f.get("status", "")), EXPECTED_17F_STATUS)
    add_check(checks, "17G-C002", "17F safety STOP rows", int(safety_17f[safety_17f["status"].astype(str).eq("STOP")].shape[0]), 0)
    add_check(checks, "17G-C003", "17F live evaluator allowed", bool_value(summary_17f.get("medium_live_evaluator_allowed", False)), False)
    add_check(checks, "17G-C004", "17F final signal allowed", bool_value(summary_17f.get("final_signal_allowed", False)), False)
    add_check(checks, "17G-C005", "17F has three planned components", int(plan_17f.shape[0]), 3)
    add_check(checks, "17G-C006", "17F next gates include 17H", bool("17H" in set(gates_17f.get("gate", pd.Series(dtype=str)).astype(str))), True)
    for comp, obj, df, label in [("RANGE96_REFINED", range_freeze, range_idx, "17C"), ("VOL_TRMEAN32_REFINED", vol_freeze, vol_idx, "17D")]:
        exp = EXPECTED_COUNTS[comp]
        counts = obj.get("observed_counts", {}) or {}
        add_check(checks, f"17G-{label}-FREEZE", f"{comp} freeze status", str(obj.get("candidate_status", "")), EXPECTED_FREEZE_STATUS)
        add_check(checks, f"17G-{label}-RULE", f"{comp} rule rows", int(counts.get("rule_ledger_rows", -1)), exp["rule_ledger_rows"])
        add_check(checks, f"17G-{label}-COMBINED", f"{comp} combined rows", int(counts.get("combined_ledger_rows", -1)), exp["combined_ledger_rows"])
        add_check(checks, f"17G-{label}-INDEX", f"{comp} freeze index rows", int(df.shape[0]), exp["index_rows"])
        add_check(checks, f"17G-{label}-LIVE", f"{comp} live evaluator allowed", bool_value(obj.get("medium_live_evaluator_allowed", False)), False)
        add_check(checks, f"17G-{label}-FINAL", f"{comp} final signal allowed", bool_value(obj.get("final_signal_allowed", False)), False)

    manifest = build_manifest(tier2_summary, range_idx, vol_idx)
    counts_df = manifest.groupby("component", dropna=False).size().reset_index(name="manifest_rows")
    for comp, exp in EXPECTED_COUNTS.items():
        obs = int(counts_df[counts_df["component"].eq(comp)]["manifest_rows"].iloc[0]) if len(counts_df[counts_df["component"].eq(comp)]) else 0
        add_check(checks, f"17G-MANIFEST-{comp}", f"manifest rows {comp}", obs, exp["index_rows"])
    add_check(checks, "17G-MANIFEST-TOTAL", "manifest total rows", int(manifest.shape[0]), 309)
    mapping_checks = pd.DataFrame(checks, columns=["check_id", "check", "observed", "expected", "status"])
    safety = pd.DataFrame([
        ["audit_only", True, True, "PASS"],
        ["medium_live_evaluator_allowed", False, False, "PASS"],
        ["final_signal_allowed", False, False, "PASS"],
        ["discord_send_allowed", False, False, "PASS"],
        ["mt5_order_allowed", False, False, "PASS"],
        ["ai_api_allowed", False, False, "PASS"],
        ["live_hook_allowed", False, False, "PASS"],
    ], columns=["safety_item", "observed", "expected", "status"])
    ok = mapping_checks[mapping_checks["status"].eq("STOP")].empty and safety[safety["status"].eq("STOP")].empty
    status = SUCCESS_STATUS if ok else STOP_STATUS
    blockers_rows = []
    for _, row in mapping_checks[mapping_checks["status"].eq("STOP")].iterrows():
        blockers_rows.append(["17G-BMAP", "MEDIUM_FULL_SET", "HARD", "OPEN", row["check"], f"observed={row['observed']} expected={row['expected']}"])
    blockers_rows += [
        ["17G-B010", "MEDIUM_FULL_SET", "HARD", "OPEN", "load-smoke", "17H must load and verify this manifest before dry-run planning."],
        ["17G-B020", "MEDIUM_FULL_SET", "HARD", "OPEN", "executable live rule", "17G is manifest mapping only; no executable rules are allowed."],
        ["17G-B099", "SAFETY", "SAFETY", "OPEN", "external actions", "Keep final_signal_allowed=false, Discord=false, MT5=false, AI=false, live_hook=false. NO_SIGNAL must not notify Discord."],
    ]
    blockers = pd.DataFrame(blockers_rows, columns=["blocker_id", "component", "severity", "status", "blocked_item", "required_resolution"])
    write_csv(manifest, out / "gold_v2_17g_full_set_candidate_manifest.csv")
    write_csv(counts_df, out / "gold_v2_17g_component_counts.csv")
    write_csv(mapping_checks, out / "gold_v2_17g_mapping_checks.csv")
    write_csv(blockers, out / "gold_v2_17g_blockers.csv")
    write_csv(safety, out / "gold_v2_17g_safety_matrix.csv")
    summary = {"created_utc": now, "step": STEP, "status": status, "audit_only": True, "manifest_written": True, "manifest_rows": int(manifest.shape[0]), "component_counts": counts_df.to_dict("records"), "tier2_handling": "13L_SUMMARY_CHAIN_REFERENCE_NO_OHLC_REDISCOVERY", "range96_handling": "17C_SOURCE_ROW_FREEZE_INDEX", "vol_trmean32_handling": "17D_SOURCE_ROW_FREEZE_INDEX", "medium_live_evaluator_allowed": False, "final_signal_allowed": False, "external_actions": EXTERNAL_ACTIONS, "next_recommended_step": "17H_MEDIUM_FULL_SET_LOAD_SMOKE_AUDIT_ONLY" if ok else "STOP_REVIEW_17G_OUTPUTS"}
    write_json(out / "gold_v2_17g_medium_full_set_candidate_mapping_summary.json", summary)
    report = ["# GOLD V2 17G MEDIUM full-set candidate mapping audit-only report", "", f"Created UTC: {now}", f"Status: `{status}`", "", "## Final decision", "- 17G writes a full-set candidate manifest only.", "- TIER2_HVT is preserved as a 13L summary-chain reference unless a row-level audited 13L artifact is provided later.", "- RANGE96_REFINED and VOL_TRMEAN32_REFINED are mapped from 17C/17D source-row freeze indexes.", "- No OHLC rediscovery, no approximate conditions, no executable rule, and no external actions are enabled.", "", "## Input audit", markdown_table(audit), "", "## Mapping checks", markdown_table(mapping_checks), "", "## Component counts", markdown_table(counts_df), "", "## Blockers", markdown_table(blockers), "", "## Safety", markdown_table(safety)]
    (out / REPORT_NAME).write_text("\n".join(report), encoding="utf-8")
    print(json.dumps(clean({"status": status, "output_dir": str(out), "next_recommended_step": summary["next_recommended_step"]}), ensure_ascii=False, indent=2))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
