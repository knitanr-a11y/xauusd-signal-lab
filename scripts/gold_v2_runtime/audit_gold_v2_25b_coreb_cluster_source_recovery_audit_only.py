#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""GOLD V2 25B CoreB cluster source recovery audit-only.

This script searches the repository and known FX_OUTPUTS artifacts for original
CoreB same_count / cluster_id / membership source-of-truth evidence.
It is intentionally audit-only and does not approximate, replay, fit, mutate,
call AI APIs, send Discord, place MT5 orders, connect live hooks, or enable
final signals.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Sequence

import pandas as pd

STEP = "25B_COREB_CLUSTER_SOURCE_RECOVERY_AUDIT_ONLY"
OUT_DIR_NAME = "gold_v2_25b_coreb_cluster_source_recovery_audit_only"
PASS_STATUS = "COREB_CLUSTER_SOURCE_RECOVERY_AUDIT_COMPLETED_AUDIT_ONLY_REPLAY_NOT_YET_AUTHORIZED"
BLOCKED_STATUS = "COREB_CLUSTER_SOURCE_RECOVERY_BLOCKED_OR_INSUFFICIENT_AUDIT_ONLY"

KEYWORDS = [
    "same_count", "cluster_id", "membership", "cluster_membership", "confluence",
    "RR125", "RR1.25", "BUY_CONFLUENCE", "same_count_source_universe",
    "source_universe", "cluster ledger", "top cluster", "top_ledgers",
]

VALID_EVIDENCE_TYPES = {
    "ORIGINAL_ALGORITHM_CANDIDATE",
    "ROW_LEVEL_MEMBERSHIP_CANDIDATE",
    "SOURCE_UNIVERSE_CANDIDATE",
}

AUDIT_ONLY_FALSE_FLAGS = {
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
}

TEXT_EXTENSIONS = {
    ".py", ".bat", ".ps1", ".md", ".txt", ".json", ".yaml", ".yml", ".csv", ".tsv", ".ini", ".cfg"
}
SKIP_DIR_PARTS = {".git", "__pycache__", ".pytest_cache", ".mypy_cache", ".venv", "venv", "node_modules"}


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="25B CoreB cluster source recovery audit-only")
    p.add_argument("--output-dir", default=None)
    p.add_argument("--max-file-bytes", type=int, default=8_000_000)
    p.add_argument("--max-snippet-chars", type=int, default=700)
    return p.parse_args(argv)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def files_dir_from_repo() -> Path:
    root = repo_root()
    return root.parents[1] if len(root.parents) >= 2 else root.parent


def fx_outputs() -> Path:
    return files_dir_from_repo() / "FX_OUTPUTS"


def default_output_dir() -> Path:
    return fx_outputs() / OUT_DIR_NAME


def lp(path: Path) -> Path:
    if os.name != "nt":
        return path
    s = str(path)
    if s.startswith("\\\\?\\"):
        return Path(s)
    if s.startswith("\\\\"):
        return Path("\\\\?\\UNC\\" + s[2:])
    return Path("\\\\?\\" + s)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with lp(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_text_sample(path: Path, max_bytes: int) -> str:
    data = lp(path).read_bytes()[:max_bytes]
    for enc in ("utf-8-sig", "utf-8", "cp932", "latin-1"):
        try:
            return data.decode(enc, errors="replace")
        except Exception:
            pass
    return ""


def is_text_candidate(path: Path, max_file_bytes: int) -> bool:
    try:
        if not lp(path).is_file():
            return False
        if path.suffix.lower() not in TEXT_EXTENSIONS:
            return False
        if lp(path).stat().st_size > max_file_bytes:
            return False
        return True
    except Exception:
        return False


def iter_scan_files(root: Path, max_file_bytes: int):
    if not lp(root).exists():
        return
    for dirpath, dirnames, filenames in os.walk(lp(root)):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIR_PARTS]
        for name in filenames:
            p = Path(dirpath) / name
            if is_text_candidate(p, max_file_bytes):
                yield p


def context_snippet(text: str, keyword: str, max_chars: int) -> str:
    low = text.lower()
    idx = low.find(keyword.lower())
    if idx < 0:
        return ""
    start = max(0, idx - max_chars // 2)
    end = min(len(text), idx + max_chars // 2)
    return text[start:end].replace("\r", " ").replace("\n", " ").strip()


def detect_columns(path: Path) -> dict[str, Any]:
    out: dict[str, Any] = {"columns": [], "row_count_sampled": "", "csv_readable": False}
    if path.suffix.lower() not in {".csv", ".tsv"}:
        return out
    try:
        sep = "\t" if path.suffix.lower() == ".tsv" else ","
        df = pd.read_csv(lp(path), nrows=2000, sep=sep, encoding="utf-8-sig", keep_default_na=False)
        out["columns"] = list(df.columns)
        out["row_count_sampled"] = int(len(df))
        out["csv_readable"] = True
    except Exception:
        try:
            with lp(path).open("r", encoding="utf-8-sig", errors="replace", newline="") as f:
                reader = csv.reader(f)
                out["columns"] = next(reader, [])
                out["csv_readable"] = True
        except Exception:
            pass
    return out


def classify_hit(rel: str, path: Path, text: str, cols: list[str], matched: list[str]) -> tuple[str, str, bool, bool, bool, bool]:
    low_rel = rel.lower()
    low_text = text.lower()
    low_cols = {c.lower() for c in cols}

    audit_generated = any(x in low_rel for x in ["25a", "25b", "24a", "24b", "24c", "24d", "24e", "24f", "13a", "13b", "13c", "13d", "audit", "handoff", "spec", "blocker", "report", "summary"])
    doc_like = path.suffix.lower() in {".md", ".txt"}
    script_like = path.suffix.lower() in {".py", ".bat", ".ps1"}
    row_membership = bool({"cluster_id", "member_entry_time", "member_id", "membership", "cluster_membership"} & low_cols) or "row-level cluster membership" in low_text
    source_universe = "same_count_source_universe" in low_text or "source_universe" in low_text or any("source_universe" in c for c in low_cols)
    original_algo_terms = script_like and ("same_count" in low_text or "cluster" in low_text) and any(term in low_text for term in ["groupby", "cluster_id", "membership", "source_universe", "same_count >= 15", "same_count>=15"])
    summary_only = ("summary" in low_rel or "report" in low_rel or doc_like) and not row_membership and not original_algo_terms

    if audit_generated and not (original_algo_terms or row_membership or source_universe):
        return "AUDIT_GENERATED_OR_POST_HOC", "audit/spec/report/handoff hit without original row-level semantics", row_membership, source_universe, original_algo_terms, summary_only
    if original_algo_terms:
        return "ORIGINAL_ALGORITHM_CANDIDATE", "script contains same_count/cluster logic terms; requires human review before trust", row_membership, source_universe, original_algo_terms, summary_only
    if row_membership:
        return "ROW_LEVEL_MEMBERSHIP_CANDIDATE", "file appears to contain row-level cluster membership fields", row_membership, source_universe, original_algo_terms, summary_only
    if source_universe:
        return "SOURCE_UNIVERSE_CANDIDATE", "file mentions source universe; must prove membership semantics", row_membership, source_universe, original_algo_terms, summary_only
    if summary_only:
        return "SUMMARY_ONLY_NOT_ENOUGH", "summary/doc/report-level evidence without row-level membership", row_membership, source_universe, original_algo_terms, summary_only
    if doc_like:
        return "DOC_ONLY", "documentation mention only", row_membership, source_universe, original_algo_terms, summary_only
    return "MENTIONS_KEYWORDS_ONLY", "keyword mention only; insufficient by itself", row_membership, source_universe, original_algo_terms, summary_only


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
        lines.append(f"| ... | truncated {len(df) - max_rows} more rows |" + " |" * max(0, len(cols) - 2))
    return "\n".join(lines)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    fx = fx_outputs()
    out = Path(args.output_dir).expanduser().resolve() if args.output_dir else default_output_dir()
    lp(out).mkdir(parents=True, exist_ok=True)

    scan_roots = [("repo", root), ("fx_outputs", fx)]
    inventory_rows: list[dict[str, Any]] = []
    scanned_files = 0

    for scope, scan_root in scan_roots:
        for path in iter_scan_files(scan_root, args.max_file_bytes) or []:
            scanned_files += 1
            try:
                text = read_text_sample(path, args.max_file_bytes)
                rel = str(path.relative_to(scan_root)) if path.is_relative_to(scan_root) else str(path)
                matched = [kw for kw in KEYWORDS if kw.lower() in text.lower() or kw.lower() in rel.lower()]
                if not matched:
                    continue
                colinfo = detect_columns(path)
                cols = [str(c) for c in colinfo.get("columns", [])]
                category, reason, row_membership, source_universe, original_algo, summary_only = classify_hit(rel, path, text, cols, matched)
                snippet = ""
                for kw in matched:
                    snippet = context_snippet(text, kw, args.max_snippet_chars)
                    if snippet:
                        break
                inventory_rows.append({
                    "scope": scope,
                    "relative_path": rel,
                    "absolute_path": str(path),
                    "suffix": path.suffix.lower(),
                    "bytes": int(lp(path).stat().st_size),
                    "sha256": sha256_file(path),
                    "matched_keywords": ";".join(matched),
                    "candidate_bucket": category,
                    "classification_reason": reason,
                    "has_row_level_membership_terms": bool(row_membership),
                    "has_source_universe_terms": bool(source_universe),
                    "has_original_algorithm_terms": bool(original_algo),
                    "summary_only": bool(summary_only),
                    "csv_readable": bool(colinfo.get("csv_readable", False)),
                    "sampled_rows": colinfo.get("row_count_sampled", ""),
                    "columns": ";".join(cols[:80]),
                    "snippet": snippet,
                })
            except Exception as exc:
                inventory_rows.append({
                    "scope": scope,
                    "relative_path": str(path),
                    "absolute_path": str(path),
                    "suffix": path.suffix.lower(),
                    "bytes": "",
                    "sha256": "",
                    "matched_keywords": "",
                    "candidate_bucket": "SCAN_ERROR",
                    "classification_reason": repr(exc),
                    "has_row_level_membership_terms": False,
                    "has_source_universe_terms": False,
                    "has_original_algorithm_terms": False,
                    "summary_only": False,
                    "csv_readable": False,
                    "sampled_rows": "",
                    "columns": "",
                    "snippet": "",
                })

    inventory = pd.DataFrame(inventory_rows)
    if inventory.empty:
        inventory = pd.DataFrame(columns=[
            "scope", "relative_path", "absolute_path", "suffix", "bytes", "sha256", "matched_keywords",
            "candidate_bucket", "classification_reason", "has_row_level_membership_terms", "has_source_universe_terms",
            "has_original_algorithm_terms", "summary_only", "csv_readable", "sampled_rows", "columns", "snippet",
        ])
    inventory = inventory.sort_values(["candidate_bucket", "scope", "relative_path"], kind="stable").reset_index(drop=True)

    bucket_counts = {str(k): int(v) for k, v in inventory.groupby("candidate_bucket").size().items()} if not inventory.empty else {}
    valid_candidates = inventory[inventory["candidate_bucket"].isin(VALID_EVIDENCE_TYPES)].copy() if not inventory.empty else pd.DataFrame()

    evidence_rows = []
    if valid_candidates.empty:
        evidence_rows.append({
            "evidence_gate": "25B-E001_VALID_ORIGINAL_EVIDENCE_FOUND",
            "observed": 0,
            "expected": ">=1 original algorithm / row membership / source universe candidate",
            "status": "BLOCKED",
            "reason": "No candidate bucket currently qualifies as sufficient original evidence by itself.",
        })
    else:
        for bucket, g in valid_candidates.groupby("candidate_bucket"):
            evidence_rows.append({
                "evidence_gate": f"25B-EVIDENCE-{bucket}",
                "observed": int(len(g)),
                "expected": "human review + later replay parity required",
                "status": "REVIEW_REQUIRED",
                "reason": "Candidate exists but is not trusted until original-vs-post-hoc and 125-row parity are proven.",
            })
    evidence_rows.extend([
        {"evidence_gate": "25B-E002_EXPECTED_COREB_RR125_ROWS", "observed": "not replayed in 25B", "expected": 125, "status": "NOT_PROVEN", "reason": "25B inventories evidence only; replay is a later gate if valid original evidence is confirmed."},
        {"evidence_gate": "25B-E003_SAME_COUNT_EXACT_MATCH_ROWS", "observed": "not replayed in 25B", "expected": 125, "status": "NOT_PROVEN", "reason": "No approximation or post-hoc fitting allowed."},
        {"evidence_gate": "25B-E004_CLUSTER_ID_OR_MEMBERSHIP_MATCH_ROWS", "observed": "not replayed in 25B", "expected": 125, "status": "NOT_PROVEN", "reason": "Requires recovered original membership semantics."},
    ])
    evidence = pd.DataFrame(evidence_rows)

    replay_requirements = pd.DataFrame([
        {"requirement_id": "25B-R001", "requirement": "original CoreB same_count / clustering script or equivalent row-level source", "required_before_unblock": True, "current_25b_action": "inventory and classify candidates only"},
        {"requirement_id": "25B-R002", "requirement": "replayed CoreB RR125 rows = 125", "required_before_unblock": True, "current_25b_action": "not executed"},
        {"requirement_id": "25B-R003", "requirement": "missing source keys = 0 and extra replay keys = 0", "required_before_unblock": True, "current_25b_action": "not executed"},
        {"requirement_id": "25B-R004", "requirement": "same_count exact match rows = 125", "required_before_unblock": True, "current_25b_action": "not executed"},
        {"requirement_id": "25B-R005", "requirement": "cluster_id or membership exact match rows = 125 if cluster_id is part of source truth", "required_before_unblock": True, "current_25b_action": "not executed"},
        {"requirement_id": "25B-R006", "requirement": "static windows / raw entry_time counts / connected components / heuristic counts / post-hoc fitting remain forbidden", "required_before_unblock": True, "current_25b_action": "enforced as report stop condition"},
    ])

    write_csv(out / "gold_v2_25b_coreb_cluster_candidate_inventory.csv", inventory)
    write_csv(out / "gold_v2_25b_coreb_cluster_evidence_matrix.csv", evidence)
    write_csv(out / "gold_v2_25b_coreb_replay_requirements.csv", replay_requirements)

    sufficient_now = False
    status = PASS_STATUS if sufficient_now else BLOCKED_STATUS
    summary = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "step": STEP,
        "status": status,
        "audit_only": True,
        "search_only_inventory": True,
        "repo_root": str(root),
        "fx_outputs_root": str(fx),
        "output_dir": str(out),
        "scanned_text_files": int(scanned_files),
        "candidate_rows": int(len(inventory)),
        "candidate_bucket_counts": bucket_counts,
        "valid_candidate_rows_requiring_review": int(len(valid_candidates)),
        "coreb_live_evaluator_unblocked": False,
        "same_count_approximation_allowed": False,
        "replay_executed": False,
        "expected_coreb_rr125_rows": 125,
        "same_count_exact_parity_proven": False,
        "cluster_membership_parity_proven": False,
        "stop_conditions_active": [
            "no original algorithm candidate is found or candidates require review",
            "audit-generated/post-hoc files are insufficient",
            "summary-level cluster data without row membership is insufficient",
            "candidate algorithm replay to 125 rows is not proven in 25B",
            "same_count exact parity is not proven in 25B",
            "any fitting/approximation after seeing SOT rows remains forbidden",
        ],
        **AUDIT_ONLY_FALSE_FLAGS,
        "old_gold_disc8_quarantined": True,
        "source_recovery_chain_status": "PAUSED_AT_24AF",
        "do_not_proceed_to_24ag_without_explicit_request": True,
    }
    write_json(out / "gold_v2_25b_coreb_cluster_recovery_summary.json", summary)

    top_cols = ["scope", "relative_path", "candidate_bucket", "matched_keywords", "classification_reason", "columns"]
    report = "\n".join([
        "# GOLD V2 25B CoreB cluster source recovery audit-only report",
        "",
        f"Created UTC: {summary['created_utc']}",
        f"Step: `{STEP}`",
        f"Status: `{status}`",
        "",
        "## Boundary",
        "",
        "25B searches and inventories candidate evidence only. It does not approximate same_count, does not replay/finalize CoreB, does not mutate source artifacts, does not enable live evaluator signals, and does not call Discord / MT5 / AI API / live hooks.",
        "",
        "## Candidate bucket counts",
        "",
        md_table(pd.DataFrame([{"candidate_bucket": k, "rows": v} for k, v in bucket_counts.items()]).sort_values("candidate_bucket") if bucket_counts else pd.DataFrame()),
        "",
        "## Candidate inventory preview",
        "",
        md_table(inventory[top_cols] if not inventory.empty else inventory, max_rows=120),
        "",
        "## Evidence matrix",
        "",
        md_table(evidence),
        "",
        "## Replay requirements",
        "",
        md_table(replay_requirements),
        "",
        "## Stop conditions",
        "",
        "- CoreB remains blocked unless original clustering/membership evidence is found and later replay proves exact 125-row parity.",
        "- Static windows, raw entry_time counts, interval cover counts, connected components, heuristic confluence counts, feature-rule hit counts pretending to be same_count, and post-hoc fitting are forbidden.",
        "",
        "## Explicit non-actions",
        "",
        "- source recovery execution: `false`",
        "- source mutation: `false`",
        "- source identity finalization: `false`",
        "- live evaluator final signal: `false`",
        "- Discord / MT5 / AI API / live hook: `false`",
        "- NO_SIGNAL Discord notification: `false`",
    ])
    lp(out / "GOLD_V2_25B_COREB_CLUSTER_SOURCE_RECOVERY_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")

    print(json.dumps({"status": status, "output_dir": str(out), "candidate_rows": int(len(inventory)), "valid_candidate_rows_requiring_review": int(len(valid_candidates)), "coreb_live_evaluator_unblocked": False}, ensure_ascii=False, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
