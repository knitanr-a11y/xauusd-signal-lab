#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""13C-5 audit: review restored CoreB clustering script candidates.

13C-4 may find files that mention rr125_top_ledgers / same_count / cluster_id.
This 13C-5 step performs a stricter classification:
  - ORIGINAL_CLUSTERING_CANDIDATE: code appears to generate cluster_id/same_count/top_ledgers from raw ledger
  - SOT_READER_ONLY: reads/filters already-created top_ledgers, not original generation
  - SOURCE_DEFINITION_OR_DOC: config/docs/spec only
  - AUDIT_GENERATED: audit/freeze helper generated after the source exploration

If no ORIGINAL_CLUSTERING_CANDIDATE is found, CoreB remains historical SOT only
and live CoreB remains blocked. No approximation is allowed.

Audit-only. No Discord, MT5, AI API, or live hook.
"""
from __future__ import annotations

import json
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Sequence

import pandas as pd

EXTERNAL_ACTIONS = {"discord_send_allowed": False, "mt5_order_allowed": False, "ai_api_allowed": False, "live_hook_allowed": False}
TEXT_SUFFIXES = {".py", ".md", ".json", ".bat", ".txt", ".yml", ".yaml", ".ps1"}
KEYWORDS = ["rr125_top_ledgers", "rr125_raw_signal_ledger", "same_count", "cluster_id", "source_rule_count", "RR125_from_RR1_rules", "top_ledgers"]
GENERATED_PATTERNS = ["audit_gold_v2_13", "gold_v2_13", "freeze_gold_v2_final_portfolio", "evaluate_gold_v2_coreA_coreB_medium", "freeze_coreb_same_count_source_universe", "combined_evaluator_replay"]


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def files_dir_from_repo() -> Path:
    root = repo_root()
    return root.parents[1] if len(root.parents) >= 2 else root.parent


def fx_outputs() -> Path:
    return files_dir_from_repo() / "FX_OUTPUTS"


def output_dir() -> Path:
    p = fx_outputs() / "gold_v2_13c5_coreb_review_restored_clustering_script_parity_audit_only"
    p.mkdir(parents=True, exist_ok=True)
    return p


def safe_read(path: Path, max_bytes: int = 2_000_000) -> str:
    try:
        return path.read_bytes()[:max_bytes].decode("utf-8", errors="ignore")
    except Exception:
        return ""


def maybe_read_json(path: Path) -> dict[str, Any]:
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def find_file(name: str) -> Optional[Path]:
    matches = list(fx_outputs().rglob(name))
    return matches[0] if matches else None


def classify_file(path: Path, root: Path) -> dict[str, Any]:
    rel = str(path.relative_to(root)).replace("\\", "/")
    text = safe_read(path)
    lower = text.lower()
    path_lower = rel.lower()
    hits = [k for k in KEYWORDS if k.lower() in lower or k.lower() in path_lower]
    if not hits:
        return {}
    is_py = path.suffix.lower() == ".py"
    is_doc_or_config = path.suffix.lower() in {".md", ".json", ".txt", ".yml", ".yaml"}
    generated = any(pat.lower() in path_lower for pat in GENERATED_PATTERNS)
    reads_top = "rr125_top_ledgers" in lower or "top_ledgers" in lower
    reads_raw = "rr125_raw_signal_ledger" in lower
    filters_same_count = "same_count>=15" in lower or "same_count >= 15" in lower
    writes_top = bool(re.search(r"to_csv\s*\([^\n]*(rr125_top_ledgers|top_ledgers)", lower)) or "rr125_top_ledgers.csv" in lower and "to_csv" in lower
    assigns_cluster_id = bool(re.search(r"\[\s*[\"']cluster_id[\"']\s*\]\s*=", text)) or bool(re.search(r"\.assign\s*\([^\)]*cluster_id", lower))
    assigns_same_count = bool(re.search(r"\[\s*[\"']same_count[\"']\s*\]\s*=", text)) or bool(re.search(r"\.assign\s*\([^\)]*same_count", lower))
    has_groupby = "groupby" in lower
    has_membership_words = any(w in lower for w in ["membership", "member", "cluster_members", "component", "connected", "overlap"])
    has_raw_to_top_pipeline = reads_raw and writes_top and assigns_cluster_id and assigns_same_count
    if is_py and has_raw_to_top_pipeline and has_groupby and not generated:
        cls = "ORIGINAL_CLUSTERING_CANDIDATE"
        live_candidate = True
        reason = "Python file appears to read raw ledger and write top_ledgers with cluster_id and same_count assignment. Must replay-audit before live use."
    elif is_py and reads_top and not writes_top:
        cls = "SOT_READER_ONLY"
        live_candidate = False
        reason = "Reads/filters already-created top_ledgers; does not generate source cluster membership."
    elif is_py and "same_count_source_universe" in path_lower:
        cls = "SOURCE_UNIVERSE_RULE_FREEZE_NOT_CLUSTER_MEMBERSHIP"
        live_candidate = False
        reason = "Freezes source-universe rules from raw ledger, but does not reconstruct source cluster membership/same_count."
    elif is_doc_or_config:
        cls = "SOURCE_DEFINITION_OR_DOC"
        live_candidate = False
        reason = "Configuration/documentation only; may describe source, but is not executable clustering algorithm."
    elif generated:
        cls = "AUDIT_GENERATED_OR_POST_HOC"
        live_candidate = False
        reason = "Generated audit/freeze helper or post-hoc SOT script; not the original clustering script."
    else:
        cls = "MENTIONS_KEYWORDS_ONLY"
        live_candidate = False
        reason = "Mentions relevant terms but lacks raw->clustered top-ledger generation evidence."
    return {
        "path": rel,
        "suffix": path.suffix,
        "classification": cls,
        "live_algorithm_candidate": live_candidate,
        "keyword_hits": "|".join(hits),
        "generated_or_post_hoc": generated,
        "reads_raw_signal_ledger": reads_raw,
        "reads_or_mentions_top_ledgers": reads_top,
        "filters_same_count_ge15": filters_same_count,
        "writes_top_ledgers_hint": writes_top,
        "assigns_cluster_id_hint": assigns_cluster_id,
        "assigns_same_count_hint": assigns_same_count,
        "has_groupby": has_groupby,
        "has_membership_words": has_membership_words,
        "reason": reason,
    }


def scan_repo() -> pd.DataFrame:
    root = repo_root()
    skip = {".git", "__pycache__", ".venv", "venv", "node_modules"}
    rows: list[dict[str, Any]] = []
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        if any(part in skip for part in path.parts):
            continue
        rec = classify_file(path, root)
        if rec:
            rows.append(rec)
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).sort_values(["live_algorithm_candidate", "classification", "path"], ascending=[False, True, True])


def markdown_table(df: pd.DataFrame, cols: Optional[Sequence[str]] = None, max_rows: int = 80) -> str:
    if cols is not None:
        df = df[[c for c in cols if c in df.columns]].copy()
    df = df.head(max_rows)
    if df.empty:
        return "_No rows._"
    headers = [str(c) for c in df.columns]
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for _, row in df.iterrows():
        lines.append("| " + " | ".join(str(row[c]).replace("|", "\\|").replace("\n", " ") for c in df.columns) + " |")
    return "\n".join(lines)


def main() -> int:
    out = output_dir()
    created = datetime.now(timezone.utc).isoformat()
    review = scan_repo()
    if review.empty:
        review = pd.DataFrame(columns=["path", "classification", "live_algorithm_candidate", "reason"])
    review.to_csv(out / "gold_v2_13c5_candidate_file_review.csv", index=False, encoding="utf-8-sig")

    counts = review.groupby("classification").size().reset_index(name="file_count") if not review.empty else pd.DataFrame(columns=["classification", "file_count"])
    counts.to_csv(out / "gold_v2_13c5_candidate_classification_counts.csv", index=False, encoding="utf-8-sig")

    live_candidates = review[review["live_algorithm_candidate"].astype(bool)].copy() if "live_algorithm_candidate" in review.columns else pd.DataFrame()
    live_candidates.to_csv(out / "gold_v2_13c5_live_algorithm_candidate_files.csv", index=False, encoding="utf-8-sig")

    s13c3 = maybe_read_json(find_file("gold_v2_13c3_coreb_reconstruct_source_cluster_membership_summary.json") or Path("__missing__"))
    s13c4 = maybe_read_json(find_file("gold_v2_13c4_coreb_clustering_script_search_summary.json") or Path("__missing__"))

    decision = pd.DataFrame([
        {"decision_item": "13C4 candidate files found", "value": int(s13c4.get("original_algorithm_candidate_files", 0)), "verdict": "REQUIRES_DEEP_REVIEW", "detail": "13C4 keyword score may produce false positives."},
        {"decision_item": "13C5 true original clustering candidates", "value": int(len(live_candidates)), "verdict": "FOUND" if len(live_candidates) else "NOT_FOUND", "detail": "Requires raw->top_ledgers generation with cluster_id and same_count assignment."},
        {"decision_item": "CoreB live evaluator", "value": False if not len(live_candidates) else "BLOCKED_UNTIL_PARITY_REPLAY", "verdict": "BLOCKED", "detail": "No live CoreB until original clustering script is replayed and reproduces 125 rows."},
        {"decision_item": "CoreB historical SOT", "value": True, "verdict": "ALLOWED", "detail": "Historical reports may retain CoreB source ledger rows."},
        {"decision_item": "Approximate same_count", "value": False, "verdict": "FORBIDDEN", "detail": "13C3 showed window/component approximations fail."},
    ])
    decision.to_csv(out / "gold_v2_13c5_decision_matrix.csv", index=False, encoding="utf-8-sig")

    status = "COREB_ORIGINAL_CLUSTERING_SCRIPT_CONFIRMED_REPLAY_REQUIRED_AUDIT_ONLY" if len(live_candidates) else "COREB_ORIGINAL_CLUSTERING_SCRIPT_NOT_CONFIRMED_COREB_LIVE_BLOCKED_AUDIT_ONLY"
    manifest = {
        "created_utc": created,
        "status": status,
        "audit_only": True,
        "upstream_13c3_status": s13c3.get("status"),
        "upstream_13c4_status": s13c4.get("status"),
        "upstream_13c4_candidate_files": s13c4.get("original_algorithm_candidate_files"),
        "reviewed_keyword_hit_files": int(len(review)),
        "true_original_clustering_candidate_files": int(len(live_candidates)),
        "candidate_classification_counts": counts.to_dict(orient="records"),
        "coreb_historical_sot_allowed": True,
        "coreb_live_evaluator_allowed": False,
        "coreb_live_evaluator_status": "BLOCKED_UNTIL_ORIGINAL_ALGORITHM_FOUND_AND_REPLAYED" if not len(live_candidates) else "BLOCKED_UNTIL_REPLAY_PARITY_PROVEN",
        "final_signal_allowed": False,
        "step13_allowed": False,
        "external_actions": EXTERNAL_ACTIONS,
        "next_recommended_step": "13D_MEDIUM_FEATURE_ARBITRATION_AUDIT_ONLY" if not len(live_candidates) else "13C6_REPLAY_CONFIRMED_COREB_CLUSTERING_ALGORITHM_AUDIT_ONLY",
    }
    (out / "gold_v2_13c5_review_restored_clustering_script_parity_summary.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")

    report = [
        "# GOLD V2 13C-5 review restored CoreB clustering script candidates audit-only report", "",
        f"Created UTC: {created}", f"Status: `{status}`", "",
        "## Final decision",
        "- 13C-4 keyword candidates were reviewed with stricter raw->clustered-top-ledger criteria.",
        "- Files that only read `rr125_top_ledgers` are classified as SOT readers, not original clustering generators.",
        "- Config/docs are source definitions, not executable membership algorithms.",
        "- Unless a true original clustering generator is found and replayed, CoreB remains historical SOT only and live CoreB stays blocked.",
        "- Discord, MT5, AI API, and live hook remain disabled.", "",
        "## Upstream carry-over", markdown_table(pd.DataFrame([{"13c3_status": s13c3.get("status"), "13c4_status": s13c4.get("status"), "13c4_candidate_files": s13c4.get("original_algorithm_candidate_files"), "13c3_best_window_exact": s13c3.get("best_static_window_exact_same_count_rows"), "13c3_component_exact": s13c3.get("connected_component_exact_same_count_rows")}]), max_rows=10), "",
        "## Candidate classification counts", markdown_table(counts, ["classification", "file_count"], max_rows=30), "",
        "## True live algorithm candidate files", markdown_table(live_candidates, ["path", "classification", "reason"], max_rows=30), "",
        "## Reviewed candidate files", markdown_table(review, ["path", "classification", "live_algorithm_candidate", "reads_raw_signal_ledger", "reads_or_mentions_top_ledgers", "writes_top_ledgers_hint", "assigns_cluster_id_hint", "assigns_same_count_hint", "reason"], max_rows=80), "",
        "## Decision matrix", markdown_table(decision, ["decision_item", "value", "verdict", "detail"], max_rows=20), "",
        "## Safety", "- coreb_live_evaluator_allowed: false", "- final_signal_allowed: false", "- step13_allowed: false", "- Discord/MT5/AI/live_hook: false", "",
        "## Next recommended step", f"`{manifest['next_recommended_step']}`", "",
    ]
    (out / "GOLD_V2_13C5_REVIEW_RESTORED_CLUSTERING_SCRIPT_PARITY_AUDIT_ONLY_REPORT.md").write_text("\n".join(report), encoding="utf-8")

    zip_path = fx_outputs() / "gold_v2_13c5_review_restored_clustering_script_parity_audit.zip"
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for p in out.iterdir():
            z.write(p, arcname=p.name)

    print(json.dumps({"status": status, "output_dir": str(out), "zip": str(zip_path), "true_original_candidates": int(len(live_candidates))}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
