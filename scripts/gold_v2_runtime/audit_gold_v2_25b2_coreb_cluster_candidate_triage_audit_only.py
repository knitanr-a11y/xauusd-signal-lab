#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""GOLD V2 25B2 CoreB cluster candidate triage audit-only.

Second-pass triage over 25B candidate inventory. This script does not reconstruct
same_count, does not replay CoreB, does not mutate artifacts, does not call AI,
does not send Discord, does not place MT5 orders, and does not enable live/final
signals.
"""
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Sequence

import pandas as pd

STEP = "25B2_COREB_CLUSTER_CANDIDATE_TRIAGE_AUDIT_ONLY"
IN_DIR = "gold_v2_25b_coreb_cluster_source_recovery_audit_only"
OUT_DIR = "gold_v2_25b2_coreb_cluster_candidate_triage_audit_only"
PASS_STATUS = "COREB_CLUSTER_CANDIDATE_TRIAGE_COMPLETED_AUDIT_ONLY_COREB_STILL_BLOCKED"
STOP_STATUS = "25B2_STOP_INPUT_MISMATCH_OR_MISSING_25B_OUTPUTS_AUDIT_ONLY"

REQUIRED_INV_COLUMNS = [
    "scope", "relative_path", "absolute_path", "suffix", "candidate_bucket",
    "matched_keywords", "columns", "snippet",
]

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


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="25B2 CoreB cluster candidate triage audit-only")
    p.add_argument("--input-dir", default=None)
    p.add_argument("--output-dir", default=None)
    return p.parse_args(argv)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def files_dir_from_repo() -> Path:
    root = repo_root()
    return root.parents[1] if len(root.parents) >= 2 else root.parent


def fx_outputs() -> Path:
    return files_dir_from_repo() / "FX_OUTPUTS"


def default_input_dir() -> Path:
    return fx_outputs() / IN_DIR


def default_output_dir() -> Path:
    return fx_outputs() / OUT_DIR


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
    raise RuntimeError(f"Could not read {path}: {last}")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(lp(path).read_text(encoding="utf-8"))


def write_csv(path: Path, df: pd.DataFrame) -> None:
    lp(path.parent).mkdir(parents=True, exist_ok=True)
    df.to_csv(lp(path), index=False, encoding="utf-8-sig")


def write_json(path: Path, obj: dict[str, Any]) -> None:
    lp(path.parent).mkdir(parents=True, exist_ok=True)
    lp(path).write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")


def norm_path(text: Any) -> str:
    s = str(text or "").replace("/", "\\")
    s = s.replace("\\\\?\\", "")
    markers = ["\\FX_OUTPUTS\\", "\\xauusd-signal-lab-clean\\xauusd-signal-lab\\", "\\xauusd-signal-lab\\"]
    for m in markers:
        if m in s:
            return s.split(m, 1)[1]
    return s


def low(row: pd.Series, field: str) -> str:
    return str(row.get(field, "") or "").lower()


def contains_any(text: str, needles: list[str]) -> bool:
    return any(n.lower() in text for n in needles)


def triage_row(row: pd.Series) -> tuple[str, int, str, str]:
    path = norm_path(row.get("relative_path", ""))
    p = path.lower()
    bucket = low(row, "candidate_bucket")
    cols = low(row, "columns")
    kw = low(row, "matched_keywords")
    snippet = low(row, "snippet")
    combined = " ".join([p, bucket, cols, kw, snippet])

    # Self/current and docs/handoff first.
    if "gold_v2_25b2" in p or "audit_gold_v2_25b2" in p:
        return "AUDIT_SCRIPT_NOT_ORIGINAL", 0, "25B2 self/current artifact is not original source evidence", "do_not_review"
    if p.endswith(".md") or "docs\\" in p or "handoff" in p or "spec" in p or "report.md" in p:
        return "DOC_OR_HANDOFF_NOT_ORIGINAL", 5, "documentation can guide review but is not row-level source evidence", "read_context_only"

    # Prior audit products and audit scripts should not be trusted as original algorithms.
    if "audit_gold_v2_13" in p or "audit_gold_v2_14" in p or "audit_gold_v2_15" in p or "audit_gold_v2_16" in p or "audit_gold_v2_18" in p or "audit_gold_v2_24" in p or "audit_gold_v2_25" in p:
        return "AUDIT_SCRIPT_NOT_ORIGINAL", 10, "audit script may describe attempted replay/search, not original generator", "inspect_only_if_needed"
    if contains_any(p, ["audit_only", "_audit", "input_audit", "summary.json", "decision_matrix", "blockers", "checks", "candidate_inventory", "candidate_file_review"]):
        if contains_any(p, ["13c4", "13c5", "14a", "14d", "original_clustering"]):
            return "PRIOR_COREB_SEARCH_AUDIT_RECORD", 60, "prior CoreB search/review artifact may point to source candidates but is not itself original evidence", "inspect_for_pointers"
        return "AUDIT_OUTPUT_OR_POST_HOC", 10, "audit-generated or post-hoc output", "do_not_review_first"

    # Strong CoreB source-universe and config candidates.
    if "rr125_raw_signal_ledger.csv" in p:
        return "RAW_SIGNAL_LEDGER_SOURCE_UNIVERSE_CANDIDATE", 100, "raw RR125 signal ledger is a plausible source universe input for CoreB rules/same_count", "review_first"
    if "frozen_coreb_same_count_source_universe_20260604.json" in p:
        return "FROZEN_SOURCE_UNIVERSE_CONFIG_OR_FREEZER", 95, "frozen same_count source universe config may define rule universe but still not membership parity", "review_first"
    if "freeze_coreb_same_count_source_universe_audit_only.py" in p:
        return "FROZEN_SOURCE_UNIVERSE_CONFIG_OR_FREEZER", 92, "freezer script may explain source-universe derivation; not cluster membership parity by itself", "review_first"
    if "frozen_coreb_rr125_source_rule_conditions_20260603.json" in p or "frozen_coreb_rr125_buy_confluence_rules_20260603.json" in p:
        return "FROZEN_SOURCE_RULE_CONDITION_CONFIG", 88, "frozen CoreB source rule conditions can support predicate replay but not cluster membership alone", "review_first"
    if "frozen_coreb_combined_evaluator_definition_20260604.json" in p or "build_coreb_combined_evaluator_definition" in p:
        return "COMBINED_EVALUATOR_DEFINITION_OR_REPLAY", 80, "combined evaluator definition may connect selected rules and same_count universe; replay parity still unproven", "review_after_source_universe"
    if "replay_coreb_combined_evaluator" in p or "coreb_combined_evaluator_replay" in p:
        return "COMBINED_EVALUATOR_DEFINITION_OR_REPLAY", 55, "replay attempt is useful diagnostic but not original source evidence", "inspect_after_configs"

    # Target top-ledger is historical SOT target, not membership generator.
    if "rr125_top_ledgers.csv" in p or ("cluster_id" in cols and "same_count" in cols and "top_ledgers" in kw):
        return "COREB_TARGET_TOP_LEDGER_NOT_MEMBERSHIP", 70, "target rows contain same_count/cluster_id but not row-level membership derivation", "use_as_target_only"

    # Downstream AI snapshots can contain source_universe text but are not generator.
    if "gold_v2_ai_tag_phase" in p:
        return "AI_TAG_SNAPSHOT_DOWNSTREAM_NOT_CLUSTER_SOURCE", 25, "AI tag snapshot is downstream truth/input, not original cluster generator", "do_not_review_first"

    # CoreA/MEDIUM ledgers are not CoreB source.
    if contains_any(p, ["abc_stack", "corea", "medium", "tier2", "range96", "vol_trmean32", "core_tier2"]):
        return "COREA_OR_MEDIUM_LEDGER_NOT_COREB_CLUSTER_SOURCE", 20, "contains cluster_id-like fields for other components, not CoreB same_count membership", "do_not_review_first"

    # Potential source-universe files missed by name.
    if "source_universe" in combined or "same_count_source_universe" in combined:
        return "UNRESOLVED_MANUAL_REVIEW_CANDIDATE", 65, "mentions source universe outside excluded audit/doc buckets; manual review needed", "manual_review"
    if bucket in {"original_algorithm_candidate", "row_level_membership_candidate", "source_universe_candidate"}:
        return "UNRESOLVED_MANUAL_REVIEW_CANDIDATE", 50, "25B classified as valid-like but 25B2 could not prove original evidence class", "manual_review_later"
    return "MENTION_ONLY_NOT_ENOUGH", 0, "keyword mention only or insufficient context", "do_not_review"


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


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    in_dir = Path(args.input_dir).expanduser().resolve() if args.input_dir else default_input_dir()
    out_dir = Path(args.output_dir).expanduser().resolve() if args.output_dir else default_output_dir()
    lp(out_dir).mkdir(parents=True, exist_ok=True)

    inv_path = in_dir / "gold_v2_25b_coreb_cluster_candidate_inventory.csv"
    summary_path = in_dir / "gold_v2_25b_coreb_cluster_recovery_summary.json"
    evidence_path = in_dir / "gold_v2_25b_coreb_cluster_evidence_matrix.csv"
    req_path = in_dir / "gold_v2_25b_coreb_replay_requirements.csv"

    input_rows = []
    for role, path in [("inventory", inv_path), ("summary", summary_path), ("evidence", evidence_path), ("requirements", req_path)]:
        input_rows.append({"role": role, "path": str(path), "required": True, "exists": lp(path).exists(), "status": "PASS" if lp(path).exists() else "STOP"})
    input_audit = pd.DataFrame(input_rows)
    write_csv(out_dir / "gold_v2_25b2_input_audit.csv", input_audit)

    if not bool(input_audit["exists"].all()):
        summary = {"created_utc": datetime.now(timezone.utc).isoformat(), "step": STEP, "status": STOP_STATUS, "audit_only": True, "total_stop_rows": int((~input_audit["exists"]).sum()), **SAFETY_FLAGS}
        write_json(out_dir / "gold_v2_25b2_coreb_cluster_candidate_triage_summary.json", summary)
        return 2

    inv = read_csv(inv_path)
    s25b = read_json(summary_path)
    missing_cols = [c for c in REQUIRED_INV_COLUMNS if c not in inv.columns]
    expected_rows = int(s25b.get("candidate_rows", -1))
    row_match = int(len(inv)) == expected_rows

    triage_records = []
    for _, row in inv.iterrows():
        triage_class, priority, reason, action = triage_row(row)
        rec = row.to_dict()
        rec["normalized_path"] = norm_path(row.get("relative_path", ""))
        rec["triage_class"] = triage_class
        rec["review_priority"] = int(priority)
        rec["triage_reason"] = reason
        rec["next_action"] = action
        rec["coreb_live_unblock_evidence_now"] = False
        triage_records.append(rec)
    triage = pd.DataFrame(triage_records)
    triage = triage.sort_values(["review_priority", "triage_class", "normalized_path"], ascending=[False, True, True]).reset_index(drop=True)

    shortlist = triage[triage["review_priority"].astype(int) >= 65].copy()
    false_positive = triage[triage["review_priority"].astype(int) < 65].copy()

    bucket_counts = triage.groupby("triage_class").size().reset_index(name="rows").sort_values(["rows", "triage_class"], ascending=[False, True])
    priority_counts = triage.groupby(["next_action", "triage_class"]).size().reset_index(name="rows").sort_values(["next_action", "rows"], ascending=[True, False])

    next_plan = pd.DataFrame([
        {"rank": 1, "action": "Inspect raw source universe first", "target": "rr125_raw_signal_ledger.csv plus frozen_coreB_same_count_source_universe_20260604.json/freezer", "allowed_now": True, "must_not_do": "Do not fit same_count or clusters to 125 rows."},
        {"rank": 2, "action": "Inspect frozen CoreB rule condition configs", "target": "frozen_coreB_rr125_source_rule_conditions_20260603.json and frozen_coreB_rr125_buy_confluence_rules_20260603.json", "allowed_now": True, "must_not_do": "Do not treat rule predicates as cluster membership semantics."},
        {"rank": 3, "action": "Inspect combined evaluator definition/replay only as diagnostic", "target": "frozen_coreB_combined_evaluator_definition_20260604.json and replay_coreb_combined_evaluator_audit_only.py", "allowed_now": True, "must_not_do": "Do not promote replay attempt to source truth without parity proof."},
        {"rank": 4, "action": "Use rr125_top_ledgers as target only", "target": "rr125_top_ledgers.csv", "allowed_now": True, "must_not_do": "Do not infer membership from target rows alone."},
        {"rank": 5, "action": "Keep CoreB live blocked", "target": "CoreB RR125_BUY_CONFLUENCE", "allowed_now": True, "must_not_do": "Do not enable live evaluator or final signal."},
    ])

    write_csv(out_dir / "gold_v2_25b2_candidate_triage.csv", triage)
    write_csv(out_dir / "gold_v2_25b2_priority_shortlist.csv", shortlist)
    write_csv(out_dir / "gold_v2_25b2_false_positive_buckets.csv", false_positive)
    write_csv(out_dir / "gold_v2_25b2_triage_class_counts.csv", bucket_counts)
    write_csv(out_dir / "gold_v2_25b2_next_review_plan.csv", next_plan)

    total_stop = int(bool(missing_cols)) + int(not row_match)
    status = PASS_STATUS if total_stop == 0 else STOP_STATUS
    summary = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "step": STEP,
        "status": status,
        "audit_only": True,
        "input_dir": str(in_dir),
        "output_dir": str(out_dir),
        "inventory_rows": int(len(inv)),
        "expected_candidate_rows_from_25b_summary": expected_rows,
        "inventory_row_count_matches_25b_summary": bool(row_match),
        "missing_required_inventory_columns": missing_cols,
        "triage_rows": int(len(triage)),
        "priority_shortlist_rows": int(len(shortlist)),
        "triage_class_counts": {str(r["triage_class"]): int(r["rows"]) for _, r in bucket_counts.iterrows()},
        "coreb_live_evaluator_unblocked": False,
        "replay_executed": False,
        "same_count_exact_parity_proven": False,
        "cluster_membership_parity_proven": False,
        "source_recovery_executed": False,
        "source_mutation_executed": False,
        "total_stop_rows": total_stop,
        **SAFETY_FLAGS,
    }
    write_json(out_dir / "gold_v2_25b2_coreb_cluster_candidate_triage_summary.json", summary)

    report = "\n".join([
        "# GOLD V2 25B2 CoreB cluster candidate triage audit-only report",
        "",
        f"Created UTC: {summary['created_utc']}",
        f"Step: `{STEP}`",
        f"Status: `{status}`",
        "",
        "## Boundary",
        "",
        "25B2 triages the 25B candidate inventory only. It does not reconstruct same_count, replay CoreB, mutate source artifacts, call AI APIs, send Discord, place MT5 orders, connect live hooks, or enable final signals.",
        "",
        "## Input audit",
        "",
        md_table(input_audit),
        "",
        "## Row-count checks",
        "",
        f"- inventory_rows: `{len(inv)}`",
        f"- expected_candidate_rows_from_25b_summary: `{expected_rows}`",
        f"- row_count_match: `{row_match}`",
        f"- missing_required_inventory_columns: `{missing_cols}`",
        "",
        "## Triage class counts",
        "",
        md_table(bucket_counts),
        "",
        "## Priority shortlist",
        "",
        md_table(shortlist[["review_priority", "triage_class", "next_action", "normalized_path", "candidate_bucket", "matched_keywords"]] if not shortlist.empty else shortlist, max_rows=120),
        "",
        "## Next review plan",
        "",
        md_table(next_plan),
        "",
        "## Safety",
        "",
        "- CoreB live evaluator unblocked: `false`",
        "- replay executed: `false`",
        "- same_count exact parity proven: `false`",
        "- cluster membership parity proven: `false`",
        "- Discord / MT5 / AI API / live hook / final signal: `false`",
        "- NO_SIGNAL Discord notification: `false`",
    ])
    lp(out_dir / "GOLD_V2_25B2_COREB_CLUSTER_CANDIDATE_TRIAGE_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")

    print(json.dumps({"status": status, "output_dir": str(out_dir), "inventory_rows": int(len(inv)), "priority_shortlist_rows": int(len(shortlist)), "coreb_live_evaluator_unblocked": False}, ensure_ascii=False, indent=2, allow_nan=False))
    return 0 if total_stop == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
