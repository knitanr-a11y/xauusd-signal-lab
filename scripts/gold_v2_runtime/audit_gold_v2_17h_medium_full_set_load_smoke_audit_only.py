#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations
import json, math, hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import numpy as np
import pandas as pd

STEP = "17H_MEDIUM_FULL_SET_LOAD_SMOKE_AUDIT_ONLY"
OUT_DIR_NAME = "gold_v2_17h_medium_full_set_load_smoke_audit_only"
REPORT_NAME = "GOLD_V2_17H_MEDIUM_FULL_SET_LOAD_SMOKE_AUDIT_ONLY_REPORT.md"
SUCCESS_STATUS = "MEDIUM_FULL_SET_LOAD_SMOKE_PASSED_AUDIT_ONLY_LIVE_BLOCKED"
STOP_STATUS = "MEDIUM_FULL_SET_LOAD_SMOKE_STOPPED_AUDIT_ONLY"
EXPECTED_17G_STATUS = "MEDIUM_FULL_SET_CANDIDATE_MAPPING_READY_AUDIT_ONLY_LIVE_BLOCKED"
EXTERNAL_ACTIONS = {"discord_send_allowed": False, "mt5_order_allowed": False, "ai_api_allowed": False, "live_hook_allowed": False}
EXPECTED_COUNTS = {"TIER2_HVT": 1, "RANGE96_REFINED": 168, "VOL_TRMEAN32_REFINED": 140}
EXPECTED_TOTAL = 309
REQUIRED_COLUMNS = ["manifest_row_id", "component", "source_step", "source_identity_type", "source_role", "source_row_number_1based", "source_key", "strategy_id", "source_row_hash", "source_status", "live_executable", "final_signal_allowed"]
INPUTS = {
    "summary_17g": ("gold_v2_17g_medium_full_set_candidate_mapping_audit_only", "gold_v2_17g_medium_full_set_candidate_mapping_summary.json"),
    "manifest_17g": ("gold_v2_17g_medium_full_set_candidate_mapping_audit_only", "gold_v2_17g_full_set_candidate_manifest.csv"),
    "component_counts_17g": ("gold_v2_17g_medium_full_set_candidate_mapping_audit_only", "gold_v2_17g_component_counts.csv"),
    "mapping_checks_17g": ("gold_v2_17g_medium_full_set_candidate_mapping_audit_only", "gold_v2_17g_mapping_checks.csv"),
    "safety_17g": ("gold_v2_17g_medium_full_set_candidate_mapping_audit_only", "gold_v2_17g_safety_matrix.csv"),
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
        ["17H-BINPUT", "MEDIUM_FULL_SET", "HARD", "OPEN", "required inputs", "Missing: " + "|".join(missing["role"].astype(str))],
        ["17H-B099", "SAFETY", "SAFETY", "OPEN", "external actions", "All external actions remain false."],
    ], columns=["blocker_id", "component", "severity", "status", "blocked_item", "required_resolution"])
    write_csv(blockers, out / "gold_v2_17h_blockers.csv")
    write_json(out / "gold_v2_17h_medium_full_set_load_smoke_summary.json", {"created_utc": now, "step": STEP, "status": STOP_STATUS, "audit_only": True, "missing_required_inputs": missing[["role", "path"]].to_dict("records"), "medium_live_evaluator_allowed": False, "final_signal_allowed": False, "external_actions": EXTERNAL_ACTIONS})
    (out / REPORT_NAME).write_text("\n".join(["# GOLD V2 17H MEDIUM full-set load-smoke audit-only report", "", f"Created UTC: {now}", f"Status: `{STOP_STATUS}`", "", markdown_table(audit), "", markdown_table(blockers)]), encoding="utf-8")
    print(json.dumps({"status": STOP_STATUS, "output_dir": str(out)}, ensure_ascii=False, indent=2))
    return 2


def add_check(rows: list[list[Any]], cid: str, check: str, observed: Any, expected: Any) -> None:
    rows.append([cid, check, observed, expected, "PASS" if observed == expected else "STOP"])


def main() -> int:
    out = output_dir()
    now = datetime.now(timezone.utc).isoformat()
    audit = input_audit()
    write_csv(audit, out / "gold_v2_17h_input_audit.csv")
    if len(audit[audit["required"].eq(True) & ~audit["exists"].eq(True)]):
        return stop_for_missing(out, now, audit)

    summary_17g = read_json(input_path("summary_17g"))
    manifest = read_csv(input_path("manifest_17g"))
    component_counts_17g = read_csv(input_path("component_counts_17g"))
    mapping_checks_17g = read_csv(input_path("mapping_checks_17g"))
    safety_17g = read_csv(input_path("safety_17g"))

    checks: list[list[Any]] = []
    add_check(checks, "17H-C001", "17G status", str(summary_17g.get("status", "")), EXPECTED_17G_STATUS)
    add_check(checks, "17H-C002", "17G mapping STOP rows", int(mapping_checks_17g[mapping_checks_17g["status"].astype(str).eq("STOP")].shape[0]), 0)
    add_check(checks, "17H-C003", "17G safety STOP rows", int(safety_17g[safety_17g["status"].astype(str).eq("STOP")].shape[0]), 0)
    add_check(checks, "17H-C004", "17G manifest_written", bool_value(summary_17g.get("manifest_written", False)), True)
    add_check(checks, "17H-C005", "manifest total rows", int(manifest.shape[0]), EXPECTED_TOTAL)
    for col in REQUIRED_COLUMNS:
        add_check(checks, f"17H-COL-{col}", f"required column {col}", col in manifest.columns, True)
    if set(REQUIRED_COLUMNS).issubset(set(manifest.columns)):
        add_check(checks, "17H-ID-NONEMPTY", "manifest_row_id non-empty", int(manifest["manifest_row_id"].astype(str).str.len().gt(0).sum()), EXPECTED_TOTAL)
        add_check(checks, "17H-ID-UNIQUE", "manifest_row_id unique", int(manifest["manifest_row_id"].nunique(dropna=False)), EXPECTED_TOTAL)
        add_check(checks, "17H-HASH-NONEMPTY", "source_row_hash non-empty", int(manifest["source_row_hash"].astype(str).str.len().gt(0).sum()), EXPECTED_TOTAL)
        add_check(checks, "17H-LIVE-FALSE", "live_executable all false", int((manifest["live_executable"].map(bool_value) == False).sum()), EXPECTED_TOTAL)
        add_check(checks, "17H-FINAL-FALSE", "final_signal_allowed all false", int((manifest["final_signal_allowed"].map(bool_value) == False).sum()), EXPECTED_TOTAL)
        add_check(checks, "17H-TIER2-TYPE", "TIER2 summary reference rows", int(manifest[manifest["component"].astype(str).eq("TIER2_HVT") & manifest["source_identity_type"].astype(str).eq("13L_SUMMARY_CHAIN_REFERENCE")].shape[0]), 1)
        add_check(checks, "17H-RANGE96-TYPE", "RANGE96 source hash rows", int(manifest[manifest["component"].astype(str).eq("RANGE96_REFINED") & manifest["source_identity_type"].astype(str).eq("SOURCE_ROW_HASH")].shape[0]), EXPECTED_COUNTS["RANGE96_REFINED"])
        add_check(checks, "17H-VOL-TYPE", "VOL source hash rows", int(manifest[manifest["component"].astype(str).eq("VOL_TRMEAN32_REFINED") & manifest["source_identity_type"].astype(str).eq("SOURCE_ROW_HASH")].shape[0]), EXPECTED_COUNTS["VOL_TRMEAN32_REFINED"])
    counts = manifest.groupby("component", dropna=False).size().reset_index(name="observed_manifest_rows") if "component" in manifest.columns else pd.DataFrame(columns=["component", "observed_manifest_rows"])
    expected_df = pd.DataFrame([[k, v] for k, v in EXPECTED_COUNTS.items()], columns=["component", "expected_manifest_rows"])
    count_check = expected_df.merge(counts, on="component", how="left").fillna({"observed_manifest_rows": 0})
    count_check["observed_manifest_rows"] = count_check["observed_manifest_rows"].astype(int)
    count_check["status"] = np.where(count_check["observed_manifest_rows"].eq(count_check["expected_manifest_rows"]), "PASS", "STOP")
    for _, row in count_check.iterrows():
        add_check(checks, f"17H-COUNT-{row['component']}", f"component count {row['component']}", int(row["observed_manifest_rows"]), int(row["expected_manifest_rows"]))
    load_checks = pd.DataFrame(checks, columns=["check_id", "check", "observed", "expected", "status"])
    safety = pd.DataFrame([
        ["audit_only", True, True, "PASS"],
        ["medium_live_evaluator_allowed", False, False, "PASS"],
        ["final_signal_allowed", False, False, "PASS"],
        ["discord_send_allowed", False, False, "PASS"],
        ["mt5_order_allowed", False, False, "PASS"],
        ["ai_api_allowed", False, False, "PASS"],
        ["live_hook_allowed", False, False, "PASS"],
    ], columns=["safety_item", "observed", "expected", "status"])
    ok = load_checks[load_checks["status"].eq("STOP")].empty and safety[safety["status"].eq("STOP")].empty
    status = SUCCESS_STATUS if ok else STOP_STATUS
    blockers_rows = []
    for _, row in load_checks[load_checks["status"].eq("STOP")].iterrows():
        blockers_rows.append(["17H-BLOAD", "MEDIUM_FULL_SET", "HARD", "OPEN", row["check"], f"observed={row['observed']} expected={row['expected']}"])
    blockers_rows += [
        ["17H-B010", "MEDIUM_FULL_SET", "HARD", "OPEN", "dry-run gate", "17I must remain audit-only and must not enable final/live/external actions."],
        ["17H-B020", "MEDIUM_FULL_SET", "HARD", "OPEN", "executable live rule", "17H is load-smoke only; no executable rules are allowed."],
        ["17H-B099", "SAFETY", "SAFETY", "OPEN", "external actions", "Keep final_signal_allowed=false, Discord=false, MT5=false, AI=false, live_hook=false. NO_SIGNAL must not notify Discord."],
    ]
    blockers = pd.DataFrame(blockers_rows, columns=["blocker_id", "component", "severity", "status", "blocked_item", "required_resolution"])
    write_csv(load_checks, out / "gold_v2_17h_manifest_load_checks.csv")
    write_csv(count_check, out / "gold_v2_17h_component_counts_check.csv")
    write_csv(blockers, out / "gold_v2_17h_blockers.csv")
    write_csv(safety, out / "gold_v2_17h_safety_matrix.csv")
    summary = {"created_utc": now, "step": STEP, "status": status, "audit_only": True, "manifest_load_smoke_passed": ok, "manifest_rows": int(manifest.shape[0]), "component_counts": count_check.to_dict("records"), "medium_live_evaluator_allowed": False, "final_signal_allowed": False, "external_actions": EXTERNAL_ACTIONS, "next_recommended_step": "17I_MEDIUM_FULL_SET_DRY_RUN_GATE_AUDIT_ONLY" if ok else "STOP_REVIEW_17H_OUTPUTS"}
    write_json(out / "gold_v2_17h_medium_full_set_load_smoke_summary.json", summary)
    report = ["# GOLD V2 17H MEDIUM full-set load-smoke audit-only report", "", f"Created UTC: {now}", f"Status: `{status}`", "", "## Final decision", "- 17H load-smokes the 17G manifest only.", "- It does not create executable rules and does not enable final/live/external actions.", "- All manifest identities must remain source references, not live predicates.", "", "## Input audit", markdown_table(audit), "", "## Manifest load checks", markdown_table(load_checks), "", "## Component counts", markdown_table(count_check), "", "## Blockers", markdown_table(blockers), "", "## Safety", markdown_table(safety)]
    (out / REPORT_NAME).write_text("\n".join(report), encoding="utf-8")
    print(json.dumps(clean({"status": status, "output_dir": str(out), "next_recommended_step": summary["next_recommended_step"]}), ensure_ascii=False, indent=2))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
