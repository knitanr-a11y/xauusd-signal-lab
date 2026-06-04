#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""13C-4 audit: find/restore original CoreB clustering script or freeze CoreB as non-live SOT.

This audit searches the local repository for a likely original CoreB clustering
implementation. It treats generated 13C audit scripts as non-original evidence.
If no original cluster-membership algorithm or row-level membership ledger is
found, CoreB remains historical SOT only and live CoreB remains blocked.

Audit-only. No Discord, MT5, AI API, or live hook.
"""
from __future__ import annotations

import json
import math
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Sequence

import pandas as pd

EXTERNAL_ACTIONS = {"discord_send_allowed": False, "mt5_order_allowed": False, "ai_api_allowed": False, "live_hook_allowed": False}
KEYWORDS = ["rr125_top_ledgers", "rr125_raw_signal_ledger", "same_count", "cluster_id", "source_rule_count", "RR125_from_RR1_rules", "connected_component", "cluster membership", "top_ledgers"]
GENERATED_HINTS = ["audit_gold_v2_13c", "13c2", "13c3", "13c4", "freeze_coreb_same_count_source_universe", "combined_evaluator_replay"]
TEXT_SUFFIXES = {".py", ".md", ".json", ".bat", ".txt", ".yml", ".yaml", ".ps1"}


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def files_dir_from_repo() -> Path:
    root = repo_root()
    return root.parents[1] if len(root.parents) >= 2 else root.parent


def fx_outputs() -> Path:
    return files_dir_from_repo() / "FX_OUTPUTS"


def output_dir() -> Path:
    p = fx_outputs() / "gold_v2_13c4_coreb_original_clustering_script_search_audit_only"
    p.mkdir(parents=True, exist_ok=True)
    return p


def safe_read_text(path: Path, max_bytes: int = 1_000_000) -> str:
    try:
        data = path.read_bytes()[:max_bytes]
        return data.decode("utf-8", errors="ignore")
    except Exception:
        return ""


def find_file(name: str) -> Optional[Path]:
    matches = list(fx_outputs().rglob(name))
    return matches[0] if matches else None


def load_13c3_summary() -> dict[str, Any]:
    p = find_file("gold_v2_13c3_coreb_reconstruct_source_cluster_membership_summary.json")
    if p and p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {}


def scan_repo(root: Path) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    skip_parts = {".git", "__pycache__", ".venv", "venv", "node_modules"}
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        if any(part in skip_parts for part in path.parts):
            continue
        rel = str(path.relative_to(root)).replace("\\", "/")
        text = safe_read_text(path)
        lower = text.lower()
        path_lower = rel.lower()
        hits = [kw for kw in KEYWORDS if kw.lower() in lower or kw.lower() in path_lower]
        if not hits:
            continue
        generated = any(h in path_lower for h in GENERATED_HINTS)
        has_top = "rr125_top_ledgers" in lower or "top_ledgers" in lower
        has_raw = "rr125_raw_signal_ledger" in lower
        has_cluster = "cluster_id" in lower or "cluster" in lower
        has_same = "same_count" in lower
        has_write_top = bool(re.search(r"to_csv\s*\([^\n]*(rr125_top_ledgers|top_ledgers)", lower))
        has_group = "groupby" in lower
        has_interval = "connected" in lower or "component" in lower or "interval" in lower
        original_score = sum([has_top, has_raw, has_cluster, has_same, has_write_top, has_group, has_interval]) - (4 if generated else 0)
        rows.append({
            "path": rel,
            "suffix": path.suffix,
            "keyword_hits": "|".join(hits),
            "hit_count": len(hits),
            "generated_or_audit_file": generated,
            "has_rr125_top_ledgers": has_top,
            "has_rr125_raw_signal_ledger": has_raw,
            "has_cluster_logic_word": has_cluster,
            "has_same_count": has_same,
            "has_write_top_ledgers_hint": has_write_top,
            "has_groupby": has_group,
            "has_interval_component_words": has_interval,
            "original_algorithm_candidate_score": original_score,
        })
    return pd.DataFrame(rows).sort_values(["original_algorithm_candidate_score", "hit_count", "path"], ascending=[False, False, True]) if rows else pd.DataFrame(columns=["path"])


def markdown_table(df: pd.DataFrame, cols: Optional[Sequence[str]] = None, max_rows: int = 50) -> str:
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
    root = repo_root()
    out = output_dir()
    created = datetime.now(timezone.utc).isoformat()
    s13c3 = load_13c3_summary()
    hits = scan_repo(root)
    hits.to_csv(out / "gold_v2_13c4_local_repo_search_hits.csv", index=False, encoding="utf-8-sig")

    if not hits.empty:
        candidates = hits[(~hits["generated_or_audit_file"]) & (hits["original_algorithm_candidate_score"] >= 5)].copy()
    else:
        candidates = pd.DataFrame()
    candidates.to_csv(out / "gold_v2_13c4_original_algorithm_candidate_files.csv", index=False, encoding="utf-8-sig")

    source_universe_candidates = hits[hits["path"].astype(str).str.contains("freeze_coreb_same_count_source_universe", case=False, na=False)].copy() if not hits.empty else pd.DataFrame()
    source_universe_candidates.to_csv(out / "gold_v2_13c4_same_count_source_universe_freeze_hits.csv", index=False, encoding="utf-8-sig")

    decision = pd.DataFrame([
        {"option": "A_restore_original_clustering_script", "status": "FOUND" if len(candidates) else "NOT_FOUND", "allowed_for_live": bool(len(candidates)), "reason": "High-confidence non-generated clustering script candidate found." if len(candidates) else "No high-confidence non-generated original clustering script found in local repo scan."},
        {"option": "B_freeze_coreb_as_historical_non_live_sot", "status": "RECOMMENDED_TEMPORARY_DECISION" if not len(candidates) else "NOT_NEEDED_YET", "allowed_for_live": False, "reason": "CoreB remains valid historical SOT but live CoreB remains blocked until original algorithm/membership ledger is restored."},
        {"option": "C_approximate_same_count_with_window_or_component", "status": "FORBIDDEN", "allowed_for_live": False, "reason": "13C-3 showed fixed-window and connected-component approximations do not reproduce source same_count."},
        {"option": "D_use_top_ledgers_cluster_id_same_count_as_live_trigger", "status": "FORBIDDEN", "allowed_for_live": False, "reason": "Historical top-ledger rows are audit SOT only and cannot trigger future live signals."},
    ])
    decision.to_csv(out / "gold_v2_13c4_decision_matrix.csv", index=False, encoding="utf-8-sig")

    status = "COREB_ORIGINAL_CLUSTERING_SCRIPT_FOUND_REVIEW_REQUIRED_AUDIT_ONLY" if len(candidates) else "COREB_ORIGINAL_CLUSTERING_SCRIPT_NOT_FOUND_LIVE_COREB_BLOCKED_AUDIT_ONLY"
    manifest = {
        "created_utc": created,
        "status": status,
        "audit_only": True,
        "upstream_13c3_status": s13c3.get("status"),
        "target_rows": s13c3.get("target_rows"),
        "best_static_window_exact_same_count_rows": s13c3.get("best_static_window_exact_same_count_rows"),
        "connected_component_exact_same_count_rows": s13c3.get("connected_component_exact_same_count_rows"),
        "local_repo_search_hit_files": int(len(hits)),
        "original_algorithm_candidate_files": int(len(candidates)),
        "same_count_source_universe_freeze_hit_files": int(len(source_universe_candidates)),
        "found_original_cluster_membership_algorithm": bool(len(candidates)),
        "found_row_level_cluster_membership_ledger": False,
        "coreb_historical_sot_allowed": True,
        "coreb_live_evaluator_allowed": bool(len(candidates)),
        "final_signal_allowed": False,
        "step13_allowed": False,
        "external_actions": EXTERNAL_ACTIONS,
        "decision": "Review candidate original clustering script before any live use." if len(candidates) else "Freeze CoreB as historical/non-live SOT for now; do not implement approximate live same_count.",
        "next_recommended_step": "13C5_REVIEW_RESTORED_CLUSTERING_SCRIPT_PARITY_AUDIT_ONLY" if len(candidates) else "13D_MEDIUM_FEATURE_ARBITRATION_AUDIT_ONLY",
    }
    (out / "gold_v2_13c4_coreb_clustering_script_search_summary.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")

    report = [
        "# GOLD V2 13C-4 CoreB original clustering script search / non-live freeze audit-only report", "",
        f"Created UTC: {created}", f"Status: `{status}`", "",
        "## Final decision",
        "- 13C-3 result is valid.",
        "- CoreB historical SOT is allowed to remain in reports.",
        "- CoreB live evaluator remains blocked unless an original clustering algorithm candidate is found and replay-parity audited.",
        "- Historical `cluster_id`, `same_count`, and `top_ledgers` must not be used as live triggers.",
        "- Discord, MT5, AI API, and live hook remain disabled.", "",
        "## 13C-3 carry-over evidence",
        markdown_table(pd.DataFrame([{"target_rows": manifest.get("target_rows"), "best_static_window_exact_same_count_rows": manifest.get("best_static_window_exact_same_count_rows"), "connected_component_exact_same_count_rows": manifest.get("connected_component_exact_same_count_rows")}]), max_rows=10), "",
        "## Original algorithm candidate files",
        markdown_table(candidates, ["path", "keyword_hits", "generated_or_audit_file", "original_algorithm_candidate_score"], max_rows=30), "",
        "## same-count source-universe freeze hits, not original membership algorithm",
        markdown_table(source_universe_candidates, ["path", "keyword_hits", "generated_or_audit_file", "original_algorithm_candidate_score"], max_rows=30), "",
        "## Decision matrix", markdown_table(decision, ["option", "status", "allowed_for_live", "reason"], max_rows=20), "",
        "## Safety", "- coreb_live_evaluator_allowed: false unless candidate algorithm found and reviewed", "- final_signal_allowed: false", "- step13_allowed: false", "- Discord/MT5/AI/live_hook: false", "",
        "## Next recommended step", f"`{manifest['next_recommended_step']}`", "",
    ]
    (out / "GOLD_V2_13C4_COREB_ORIGINAL_CLUSTERING_SCRIPT_SEARCH_AUDIT_ONLY_REPORT.md").write_text("\n".join(report), encoding="utf-8")

    zip_path = fx_outputs() / "gold_v2_13c4_coreb_original_clustering_script_search_audit.zip"
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for p in out.iterdir():
            z.write(p, arcname=p.name)

    print(json.dumps({"status": status, "output_dir": str(out), "original_algorithm_candidate_files": int(len(candidates)), "zip": str(zip_path)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
