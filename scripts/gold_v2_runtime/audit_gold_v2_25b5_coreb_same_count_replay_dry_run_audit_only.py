#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Sequence

import pandas as pd

STEP = "25B5_COREB_SAME_COUNT_REPLAY_DRY_RUN_AUDIT_ONLY"
PASS_STATUS = "COREB_SAME_COUNT_REPLAY_DRY_RUN_COMPLETED_AUDIT_ONLY_PARITY_REVIEW_REQUIRED"
STOP_STATUS = "25B5_STOP_MISSING_INPUT_OR_UNSAFE_STATE_AUDIT_ONLY"
IN25B4 = "gold_v2_25b4_coreb_same_count_replay_plan_audit_only"
IN25B3 = "gold_v2_25b3_coreb_source_shortlist_content_audit_only"
OUT_DIR = "gold_v2_25b5_coreb_same_count_replay_dry_run_audit_only"

SAFETY_FLAGS = {
    "source_recovery_execution_allowed_now": False,
    "source_mutation_allowed": False,
    "source_identity_finalization_allowed_now": False,
    "live_evaluator_final_signal_allowed": False,
    "final_signal_allowed": False,
    "discord_send_allowed": False,
    "mt5_order_allowed": False,
    "ai_api_allowed": False,
    "live_hook_allowed": False,
    "no_signal_discord_notification_allowed": False,
    "old_gold_disc8_quarantined": True,
    "source_recovery_chain_status": "PAUSED_AT_24AF",
}
KEY_COLS = ["policy", "candidate_id", "origin_id", "direction", "variant", "rr_bucket"]
TARGET_KEY_COLS = ["dataset", "entry_time", "top_direction", "top_candidate_id", "policy", "filter"]


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="25B5 CoreB same_count replay dry-run audit-only")
    p.add_argument("--output-dir", default=None)
    return p.parse_args(argv)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def files_dir_from_repo() -> Path:
    root = repo_root()
    return root.parents[1] if len(root.parents) >= 2 else root.parent


def fx_outputs() -> Path:
    return files_dir_from_repo() / "FX_OUTPUTS"


def lp(path: Path) -> Path:
    if os.name != "nt":
        return path
    s = str(path)
    if s.startswith("\\\\?\\"):
        return Path(s)
    if s.startswith("\\\\"):
        return Path("\\\\?\\UNC\\" + s[2:])
    return Path("\\\\?\\" + s)


def read_csv(path: Path) -> pd.DataFrame:
    last: Exception | None = None
    for enc in ("utf-8-sig", "utf-8", "cp932"):
        try:
            return pd.read_csv(lp(path), encoding=enc, keep_default_na=False)
        except Exception as exc:
            last = exc
    raise RuntimeError(f"Could not read CSV {path}: {last}")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(lp(path).read_text(encoding="utf-8-sig"))


def write_csv(path: Path, df: pd.DataFrame) -> None:
    lp(path.parent).mkdir(parents=True, exist_ok=True)
    df.to_csv(lp(path), index=False, encoding="utf-8-sig")


def write_json(path: Path, obj: dict[str, Any]) -> None:
    lp(path.parent).mkdir(parents=True, exist_ok=True)
    lp(path).write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")


def md_table(df: pd.DataFrame, max_rows: int = 80) -> str:
    if df.empty:
        return "_No rows._"
    view = df.head(max_rows)
    cols = list(view.columns)
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for _, r in view.iterrows():
        lines.append("| " + " | ".join(str(r[c]).replace("|", "\\|").replace("\n", " ") for c in cols) + " |")
    if len(df) > max_rows:
        lines.append(f"| ... | truncated {len(df)-max_rows} more rows |" + " |" * max(0, len(cols)-2))
    return "\n".join(lines)


def path_from_file_audit(file_audit: pd.DataFrame, name: str) -> Path:
    m = file_audit[file_audit["normalized_path"].astype(str).str.contains(name, case=False, regex=False, na=False)]
    if m.empty:
        return Path("")
    return Path(str(m.iloc[0]["absolute_path"]))


def rule_keys_from_json(obj: dict[str, Any], list_key: str) -> pd.DataFrame:
    rows = []
    for item in obj.get(list_key, []):
        if isinstance(item, dict):
            rows.append({c: item.get(c, "") for c in KEY_COLS} | {"rule_id": item.get("rule_id", "")})
    return pd.DataFrame(rows)


def normalize_key_df(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for c in KEY_COLS:
        if c not in out.columns:
            out[c] = ""
        out[c] = out[c].astype(str)
    return out


def safety_problems(s25b4: dict[str, Any]) -> list[str]:
    problems = []
    if s25b4.get("status") != "COREB_SAME_COUNT_REPLAY_PLAN_READY_AUDIT_ONLY_EXECUTION_BLOCKED":
        problems.append("25B4 status mismatch")
    if int(s25b4.get("total_stop_rows", -1)) != 0:
        problems.append("25B4 stop rows not zero")
    for k, expected in SAFETY_FLAGS.items():
        if s25b4.get(k) != expected:
            problems.append(f"safety flag mismatch: {k}")
    for k in ["replay_executed", "same_count_recomputed", "same_count_exact_parity_proven", "cluster_membership_parity_proven", "coreb_live_evaluator_unblocked"]:
        if bool(s25b4.get(k)) is not False:
            problems.append(f"unsafe prior state: {k}")
    return problems


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    out_dir = Path(args.output_dir).expanduser().resolve() if args.output_dir else fx_outputs() / OUT_DIR
    lp(out_dir).mkdir(parents=True, exist_ok=True)
    in25b4 = fx_outputs() / IN25B4
    in25b3 = fx_outputs() / IN25B3

    required = {
        "25b4_summary": in25b4 / "gold_v2_25b4_coreb_same_count_replay_plan_summary.json",
        "25b3_file_audit": in25b3 / "gold_v2_25b3_shortlist_file_content_audit.csv",
    }
    input_audit = pd.DataFrame([{"role": k, "path": str(v), "required": True, "exists": lp(v).exists(), "status": "PASS" if lp(v).exists() else "STOP"} for k, v in required.items()])
    write_csv(out_dir / "gold_v2_25b5_input_audit.csv", input_audit)
    if not bool(input_audit["exists"].all()):
        summary = {"created_utc": datetime.now(timezone.utc).isoformat(), "step": STEP, "status": STOP_STATUS, "audit_only": True, "total_stop_rows": int((input_audit["status"] == "STOP").sum()), **SAFETY_FLAGS}
        write_json(out_dir / "gold_v2_25b5_coreb_same_count_replay_dry_run_summary.json", summary)
        return 2

    s25b4 = read_json(required["25b4_summary"])
    problems = safety_problems(s25b4)
    file_audit = read_csv(required["25b3_file_audit"])

    raw_path = path_from_file_audit(file_audit, "rr125_raw_signal_ledger.csv")
    top_path = path_from_file_audit(file_audit, "rr125_top_ledgers.csv")
    sel_path = path_from_file_audit(file_audit, "frozen_coreB_rr125_source_rule_conditions_20260603.json")
    scu_path = path_from_file_audit(file_audit, "frozen_coreB_same_count_source_universe_20260604.json")
    combo_path = path_from_file_audit(file_audit, "frozen_coreB_combined_evaluator_definition_20260604.json")
    path_rows = []
    for role, p in [("raw", raw_path), ("target", top_path), ("selected_rules", sel_path), ("same_count_universe", scu_path), ("combined", combo_path)]:
        ok = bool(str(p)) and lp(p).exists()
        if not ok:
            problems.append(f"missing resolved path: {role}")
        path_rows.append({"role": role, "path": str(p), "exists": ok})
    write_csv(out_dir / "gold_v2_25b5_resolved_paths.csv", pd.DataFrame(path_rows))

    if problems:
        summary = {"created_utc": datetime.now(timezone.utc).isoformat(), "step": STEP, "status": STOP_STATUS, "audit_only": True, "status_problems": problems, "total_stop_rows": int(len(problems)), **SAFETY_FLAGS}
        write_json(out_dir / "gold_v2_25b5_coreb_same_count_replay_dry_run_summary.json", summary)
        return 2

    raw = normalize_key_df(read_csv(raw_path))
    target = read_csv(top_path)
    selected_rules = rule_keys_from_json(read_json(sel_path), "source_rule_conditions")
    source_rules = rule_keys_from_json(read_json(scu_path), "source_universe_rules")
    combo = read_json(combo_path)
    selected_rules = normalize_key_df(selected_rules)
    source_rules = normalize_key_df(source_rules)

    sel_key = selected_rules[KEY_COLS].drop_duplicates()
    src_key = source_rules[KEY_COLS].drop_duplicates()
    raw_selected = raw.merge(sel_key.assign(selected_rule_hit=True), on=KEY_COLS, how="left")
    raw_selected["selected_rule_hit"] = raw_selected["selected_rule_hit"].fillna(False).astype(bool)
    raw_source = raw.merge(src_key.assign(source_rule_hit=True), on=KEY_COLS, how="left")
    raw_source["source_rule_hit"] = raw_source["source_rule_hit"].fillna(False).astype(bool)

    source_hit_counts = raw_source[raw_source["source_rule_hit"]].groupby(["dataset", "entry_time"]).agg(
        same_count_source_hit_count=("candidate_id", "size"),
        same_count_unique_origins=("origin_id", "nunique"),
    ).reset_index()
    selected_hits = raw_selected[raw_selected["selected_rule_hit"]].copy()
    dry = selected_hits.merge(source_hit_counts, on=["dataset", "entry_time"], how="left")
    dry["same_count_source_hit_count"] = pd.to_numeric(dry["same_count_source_hit_count"], errors="coerce").fillna(0).astype(int)
    dry["same_count_unique_origins"] = pd.to_numeric(dry["same_count_unique_origins"], errors="coerce").fillna(0).astype(int)
    dry["dry_run_signal"] = dry["same_count_source_hit_count"] >= int(combo.get("same_count_min", 15))
    dry["top_direction"] = dry["direction"]
    dry["top_candidate_id"] = dry["candidate_id"]
    dry["filter"] = "dry_run_selected_rule_hit_and_same_count_source_hit_count_ge15"

    dry_out_cols = [
        "dataset", "entry_time", "entry_month", "profit_r", "top_direction", "top_candidate_id", "policy", "rr_bucket",
        "candidate_id", "origin_id", "variant", "same_count_source_hit_count", "same_count_unique_origins", "dry_run_signal", "filter",
    ]
    dry_rows = dry[dry["dry_run_signal"]].copy()
    dry_rows = dry_rows[[c for c in dry_out_cols if c in dry_rows.columns]].sort_values(["dataset", "entry_time", "top_candidate_id", "policy"]).reset_index(drop=True)
    write_csv(out_dir / "gold_v2_25b5_dry_run_candidate_rows.csv", dry_rows)

    rule_key_audit = pd.DataFrame([
        {"check": "selected_rule_rows", "observed": len(selected_rules), "expected": combo.get("selected_rule_count", "")},
        {"check": "same_count_source_rule_rows", "observed": len(source_rules), "expected": combo.get("same_count_source_rule_count", "")},
        {"check": "selected_unique_keys", "observed": len(sel_key), "expected": len(sel_key)},
        {"check": "source_unique_keys", "observed": len(src_key), "expected": len(src_key)},
        {"check": "same_count_min", "observed": combo.get("same_count_min", ""), "expected": 15},
        {"check": "entry_logic", "observed": combo.get("entry_logic", ""), "expected": "selected_rule_hit AND same_count_source_hit_count >= 15"},
    ])
    write_csv(out_dir / "gold_v2_25b5_rule_key_audit.csv", rule_key_audit)

    raw_match_summary = pd.DataFrame([
        {"metric": "raw_rows", "value": len(raw)},
        {"metric": "selected_rule_hit_rows", "value": int(raw_selected["selected_rule_hit"].sum())},
        {"metric": "source_rule_hit_rows", "value": int(raw_source["source_rule_hit"].sum())},
        {"metric": "selected_hit_unique_entry_times", "value": int(selected_hits["entry_time"].nunique()) if not selected_hits.empty else 0},
        {"metric": "source_hit_unique_entry_times", "value": int(source_hit_counts["entry_time"].nunique()) if not source_hit_counts.empty else 0},
        {"metric": "dry_run_signal_rows", "value": len(dry_rows)},
        {"metric": "target_top_rows", "value": len(target)},
    ])
    write_csv(out_dir / "gold_v2_25b5_raw_match_summary.csv", raw_match_summary)

    target_ge15 = target[pd.to_numeric(target.get("same_count", pd.Series(dtype=float)), errors="coerce") >= 15].copy()
    dry_cmp = dry_rows.copy()
    if not dry_cmp.empty:
        dry_cmp["filter"] = "same_count>=15"
    cmp_keys = TARGET_KEY_COLS
    for c in cmp_keys:
        if c not in dry_cmp.columns:
            dry_cmp[c] = ""
        if c not in target_ge15.columns:
            target_ge15[c] = ""
        dry_cmp[c] = dry_cmp[c].astype(str)
        target_ge15[c] = target_ge15[c].astype(str)
    dry_key_df = dry_cmp[cmp_keys].drop_duplicates().assign(in_dry_run=True)
    tgt_key_df = target_ge15[cmp_keys].drop_duplicates().assign(in_target=True)
    compare = dry_key_df.merge(tgt_key_df, on=cmp_keys, how="outer")
    compare["in_dry_run"] = compare["in_dry_run"].fillna(False).astype(bool)
    compare["in_target"] = compare["in_target"].fillna(False).astype(bool)
    compare["parity_status"] = compare.apply(lambda r: "MATCH" if r["in_dry_run"] and r["in_target"] else ("EXTRA_DRY_RUN" if r["in_dry_run"] else "MISSING_DRY_RUN"), axis=1)
    write_csv(out_dir / "gold_v2_25b5_target_compare_same_count_ge15.csv", compare.sort_values(cmp_keys).reset_index(drop=True))

    parity_summary = pd.DataFrame([
        {"check": "target_ge15_unique_keys", "observed": len(tgt_key_df), "expected": "target"},
        {"check": "dry_run_unique_keys", "observed": len(dry_key_df), "expected": "diagnostic"},
        {"check": "matched_keys", "observed": int((compare["parity_status"] == "MATCH").sum()), "expected": len(tgt_key_df)},
        {"check": "missing_dry_run_keys", "observed": int((compare["parity_status"] == "MISSING_DRY_RUN").sum()), "expected": 0},
        {"check": "extra_dry_run_keys", "observed": int((compare["parity_status"] == "EXTRA_DRY_RUN").sum()), "expected": 0},
        {"check": "same_count_exact_value_parity", "observed": "not_checked_in_25b5_key_probe", "expected": "future_gate"},
        {"check": "cluster_membership_parity", "observed": "not_checked_in_25b5_key_probe", "expected": "future_gate_if_applicable"},
    ])
    write_csv(out_dir / "gold_v2_25b5_parity_summary.csv", parity_summary)

    blockers = pd.DataFrame([
        {"blocker_id": "25B5-B001", "blocker": "dry-run is diagnostic only", "status": "OPEN"},
        {"blocker_id": "25B5-B002", "blocker": "same_count exact value parity not proven", "status": "OPEN"},
        {"blocker_id": "25B5-B003", "blocker": "cluster/membership parity not proven", "status": "OPEN"},
        {"blocker_id": "25B5-B004", "blocker": "final CoreB 125-row parity not proven", "status": "OPEN"},
        {"blocker_id": "25B5-B005", "blocker": "external/live/final actions remain off", "status": "SAFETY_OPEN"},
    ])
    write_csv(out_dir / "gold_v2_25b5_execution_blockers.csv", blockers)

    parity_counts = compare["parity_status"].value_counts().to_dict() if not compare.empty else {}
    summary = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "step": STEP,
        "status": PASS_STATUS,
        "audit_only": True,
        "dry_run_only": True,
        "raw_rows": int(len(raw)),
        "target_top_rows": int(len(target)),
        "selected_rule_rows": int(len(selected_rules)),
        "same_count_source_rule_rows": int(len(source_rules)),
        "dry_run_signal_rows": int(len(dry_rows)),
        "target_ge15_unique_keys": int(len(tgt_key_df)),
        "dry_run_unique_keys": int(len(dry_key_df)),
        "target_compare_parity_counts": {str(k): int(v) for k, v in parity_counts.items()},
        "replay_executed": True,
        "replay_execution_scope": "dry_run_key_probe_only",
        "same_count_recomputed": False,
        "same_count_exact_parity_proven": False,
        "cluster_membership_parity_proven": False,
        "coreb_live_evaluator_unblocked": False,
        "source_mutation_executed": False,
        "next_recommended_step": "25B6_COREB_DRY_RUN_PARITY_REVIEW_AUDIT_ONLY",
        "total_stop_rows": 0,
        **SAFETY_FLAGS,
    }
    write_json(out_dir / "gold_v2_25b5_coreb_same_count_replay_dry_run_summary.json", summary)

    report = "\n".join([
        "# GOLD V2 25B5 CoreB same_count replay dry-run audit-only report",
        "",
        f"Created UTC: {summary['created_utc']}",
        f"Step: `{STEP}`",
        f"Status: `{PASS_STATUS}`",
        "",
        "## Boundary",
        "",
        "25B5 is a dry-run diagnostic probe only. It keeps CoreB blocked.",
        "",
        "## Input audit",
        "",
        md_table(input_audit),
        "",
        "## Rule key audit",
        "",
        md_table(rule_key_audit),
        "",
        "## Raw match summary",
        "",
        md_table(raw_match_summary),
        "",
        "## Parity summary",
        "",
        md_table(parity_summary),
        "",
        "## Execution blockers",
        "",
        md_table(blockers),
        "",
        "## Safety",
        "",
        "CoreB live remains blocked. No source mutation or external/final action is enabled.",
    ])
    lp(out_dir / "GOLD_V2_25B5_COREB_SAME_COUNT_REPLAY_DRY_RUN_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")

    print(json.dumps({"status": PASS_STATUS, "output_dir": str(out_dir), "dry_run_signal_rows": int(len(dry_rows)), "parity_counts": summary["target_compare_parity_counts"]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
