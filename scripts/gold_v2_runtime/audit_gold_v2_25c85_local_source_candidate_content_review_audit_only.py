#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""GOLD V2 25C85 local source candidate content review audit-only.

Reads local candidate paths emitted by 25C84 keyword scan and classifies
whether any file appears to contain actual raw-to-top generator logic.
A002 is not used. No live/final/external action is allowed.
"""
from __future__ import annotations

import hashlib
import json
import math
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

STEP = "25C85_LOCAL_SOURCE_CANDIDATE_CONTENT_REVIEW_AUDIT_ONLY"
OUT_DIR_NAME = "gold_v2_25c85_local_source_candidate_content_review_audit_only"
UPSTREAM_DIR_NAME = "gold_v2_25c84_deep_cluster_representative_reconstruction_audit_only"
EXTERNAL_ACTIONS = {
    "discord_send_allowed": False,
    "mt5_order_allowed": False,
    "ai_api_allowed": False,
    "live_hook_allowed": False,
}

TERMS = [
    "rr125_raw_signal_ledger",
    "rr125_top_ledgers",
    "same_count",
    "source_rule_count",
    "cluster_id",
    "top_candidate_id",
    "groupby",
    "connected_components",
]


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def files_root() -> Path:
    r = repo_root()
    return r.parents[1] if len(r.parents) >= 2 else r.parent


def fx_outputs() -> Path:
    return files_root() / "FX_OUTPUTS"


def upstream_dir() -> Path:
    return fx_outputs() / UPSTREAM_DIR_NAME


def out_dir() -> Path:
    out = fx_outputs() / OUT_DIR_NAME
    out.mkdir(parents=True, exist_ok=True)
    return out


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def clean_json(x: Any) -> Any:
    if isinstance(x, dict):
        return {str(k): clean_json(v) for k, v in x.items()}
    if isinstance(x, list):
        return [clean_json(v) for v in x]
    if isinstance(x, float):
        if math.isnan(x):
            return None
        if math.isinf(x):
            return "inf" if x > 0 else "-inf"
    try:
        if pd.isna(x):
            return None
    except Exception:
        pass
    return x


def write_json(path: Path, obj: dict[str, Any]) -> None:
    path.write_text(json.dumps(clean_json(obj), ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def classify_file(rel_path: str) -> dict[str, Any]:
    root = repo_root()
    path = root / rel_path
    row: dict[str, Any] = {"path": rel_path, "exists": path.exists() and path.is_file()}
    if not row["exists"]:
        row["classification"] = "MISSING_LOCAL_PATH"
        return row
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception as exc:
        row["classification"] = "READ_ERROR"
        row["error"] = repr(exc)
        return row
    low = text.lower()
    row["bytes"] = path.stat().st_size
    row["sha256"] = sha256_file(path)
    row["is_audit_file"] = "audit" in path.name.lower() or "audit_only" in path.name.lower()
    row["is_config"] = path.suffix.lower() == ".json"
    for term in TERMS:
        row[f"hit_{term}"] = low.count(term.lower())
    row["has_raw_read_term"] = row["hit_rr125_raw_signal_ledger"] > 0
    row["has_top_write_term"] = row["hit_rr125_top_ledgers"] > 0
    row["has_cluster_terms"] = row["hit_cluster_id"] > 0
    row["has_same_count_terms"] = row["hit_same_count"] > 0 or row["hit_source_rule_count"] > 0
    row["has_grouping_terms"] = row["hit_groupby"] > 0 or row["hit_connected_components"] > 0
    generator_like = bool(row["has_raw_read_term"] and row["has_top_write_term"] and row["has_cluster_terms"] and row["has_same_count_terms"] and row["has_grouping_terms"])
    if generator_like and not row["is_audit_file"]:
        row["classification"] = "POSSIBLE_SOURCE_GENERATOR_REVIEW_REQUIRED"
    elif generator_like:
        row["classification"] = "AUDIT_GENERATED_OR_READER_WITH_GENERATOR_LIKE_TERMS"
    elif row["has_raw_read_term"] and row["has_same_count_terms"] and row["has_grouping_terms"]:
        row["classification"] = "PARTIAL_RAW_GROUPING_LOGIC"
    elif row["is_config"] and row["has_same_count_terms"]:
        row["classification"] = "CONFIG_OR_FREEZE_DEFINITION_NOT_GENERATOR"
    elif row["is_audit_file"]:
        row["classification"] = "AUDIT_OR_READER_ONLY"
    else:
        row["classification"] = "KEYWORD_HIT_ONLY"
    row["total_review_hits"] = sum(int(row.get(f"hit_{term}", 0)) for term in TERMS)
    return row


def context_snippets(rel_path: str, max_snips: int = 6) -> list[dict[str, Any]]:
    root = repo_root()
    path = root / rel_path
    if not path.exists() or not path.is_file():
        return []
    text = path.read_text(encoding="utf-8", errors="ignore")
    lines = text.splitlines()
    rows: list[dict[str, Any]] = []
    for i, line in enumerate(lines):
        if not any(term.lower() in line.lower() for term in TERMS):
            continue
        start = max(0, i - 2)
        end = min(len(lines), i + 3)
        rows.append({
            "path": rel_path,
            "start_line": start + 1,
            "end_line": end,
            "snippet": "\n".join(lines[start:end])[:1500],
        })
        if len(rows) >= max_snips:
            break
    return rows


def input_inventory() -> pd.DataFrame:
    rows = []
    for filename in ["25c84_summary.json", "25c84_logic_keyword_scan.csv"]:
        p = upstream_dir() / filename
        row: dict[str, Any] = {"filename": filename, "exists": p.exists(), "path": str(p)}
        if p.exists():
            row["bytes"] = p.stat().st_size
            row["sha256"] = sha256_file(p)
        rows.append(row)
    return pd.DataFrame(rows)


def md(df: pd.DataFrame, max_rows: int = 50) -> str:
    if df.empty:
        return "_No rows._"
    d = df.head(max_rows).fillna("").copy()
    lines = ["| " + " | ".join(map(str, d.columns)) + " |", "| " + " | ".join(["---"] * len(d.columns)) + " |"]
    for _, r in d.iterrows():
        lines.append("| " + " | ".join(str(r[c]).replace("|", "\\|").replace("\n", "<br>") for c in d.columns) + " |")
    return "\n".join(lines)


def main() -> int:
    out = out_dir()
    created = datetime.now(timezone.utc).isoformat()
    inv = input_inventory()
    s84 = read_json(upstream_dir() / "25c84_summary.json")
    scan = read_csv(upstream_dir() / "25c84_logic_keyword_scan.csv")

    rows = []
    snippets = []
    if not scan.empty and "path" in scan.columns:
        for rel_path in scan["path"].dropna().astype(str).head(100):
            rows.append(classify_file(rel_path))
            snippets.extend(context_snippets(rel_path))
    cls = pd.DataFrame(rows)
    if not cls.empty and "total_review_hits" in cls.columns:
        cls = cls.sort_values(["classification", "total_review_hits"], ascending=[True, False])
    snip_df = pd.DataFrame(snippets)

    possible_source = bool((cls.get("classification", pd.Series(dtype=str)).astype(str) == "POSSIBLE_SOURCE_GENERATOR_REVIEW_REQUIRED").any()) if not cls.empty else False
    partial_logic = bool(cls.get("classification", pd.Series(dtype=str)).astype(str).isin(["AUDIT_GENERATED_OR_READER_WITH_GENERATOR_LIKE_TERMS", "PARTIAL_RAW_GROUPING_LOGIC"]).any()) if not cls.empty else False
    upstream_ok = s84.get("status") == "DEEP_CLUSTER_REPRESENTATIVE_RECONSTRUCTION_NOT_RECOVERED_AUDIT_ONLY_LIVE_BLOCKED"

    decision = pd.DataFrame([
        ["true_source_generator_candidate_found", possible_source, "REVIEW_REQUIRED_IF_TRUE", "REVIEW" if possible_source else "NOT_FOUND"],
        ["partial_grouping_or_audit_logic_found", partial_logic, "USEFUL_BUT_NOT_SUFFICIENT", "FOUND" if partial_logic else "NOT_FOUND"],
        ["source_recovery_approved", False, False, "PASS"],
        ["coreb_live_evaluator_allowed", False, False, "PASS"],
        ["a002_used", False, False, "PASS"],
    ], columns=["decision_item", "observed", "required", "status"])

    if possible_source:
        status = "LOCAL_SOURCE_GENERATOR_CANDIDATE_FOUND_REVIEW_REQUIRED_AUDIT_ONLY_LIVE_BLOCKED"
        next_step = "MANUAL_REVIEW_SOURCE_GENERATOR_CANDIDATE_BEFORE_ANY_LIVE_STEP"
    else:
        status = "LOCAL_SOURCE_GENERATOR_NOT_FOUND_PARTIAL_LOGIC_ONLY_AUDIT_ONLY_LIVE_BLOCKED"
        next_step = "DEEPER_RECONSTRUCTION_FROM_PARTIAL_LOGIC_OR_NEW_POLICY_DECISION"
    if not upstream_ok or not bool(inv["exists"].all()):
        status = "LOCAL_SOURCE_CANDIDATE_CONTENT_REVIEW_INPUT_REVIEW_REQUIRED_AUDIT_ONLY"
        next_step = "REVIEW_25C85_INPUTS"

    plan = pd.DataFrame([
        ["25C86", next_step, "Do not enable live; do not treat partial logic as source recovery."],
        ["guardrail", "LIVE_REMAINS_BLOCKED", "Discord/MT5/AI/live hook/final signal remain OFF."],
    ], columns=["next_step", "action", "detail"])

    summary = {
        "created_utc": created,
        "step": STEP,
        "status": status,
        "audit_only": True,
        "upstream_25c84_ok": upstream_ok,
        "candidate_files_reviewed": int(len(cls)),
        "true_source_generator_candidate_found": possible_source,
        "partial_grouping_or_audit_logic_found": partial_logic,
        "source_recovery_approved": False,
        "coreb_historical_sot_report_allowed": True,
        "coreb_live_evaluator_allowed": False,
        "final_signal_allowed": False,
        "a002_used": False,
        "external_actions": EXTERNAL_ACTIONS,
        "next_recommended_step": next_step,
    }

    inv.to_csv(out / "25c85_input_inventory.csv", index=False, encoding="utf-8-sig")
    cls.to_csv(out / "25c85_candidate_file_classification.csv", index=False, encoding="utf-8-sig")
    snip_df.to_csv(out / "25c85_candidate_context_snippets.csv", index=False, encoding="utf-8-sig")
    decision.to_csv(out / "25c85_decision_matrix.csv", index=False, encoding="utf-8-sig")
    plan.to_csv(out / "25c85_next_step_plan.csv", index=False, encoding="utf-8-sig")
    write_json(out / "25c85_summary.json", summary)

    report = "\n".join([
        "# GOLD V2 25C85 local source candidate content review audit-only report",
        "",
        f"Created UTC: {created}",
        f"Status: `{status}`",
        "",
        "## Decision",
        "Keyword hits alone are not source recovery. This step classifies local candidate files from 25C84.",
        "",
        "## Input inventory",
        md(inv),
        "",
        "## Candidate classification",
        md(cls, 80),
        "",
        "## Context snippets",
        md(snip_df, 30),
        "",
        "## Decision matrix",
        md(decision),
        "",
        "## Next step plan",
        md(plan),
        "",
        "## Safety",
        "- audit_only: true",
        "- A002 not used",
        "- source recovery not approved",
        "- live/final/external actions remain OFF",
    ])
    (out / "GOLD_V2_25C85_LOCAL_SOURCE_CANDIDATE_CONTENT_REVIEW_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")

    zip_path = fx_outputs() / "gold_v2_25c85_local_source_candidate_content_review_audit_only.zip"
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for p in out.iterdir():
            z.write(p, arcname=p.name)

    print(json.dumps({"status": status, "output_dir": str(out), "zip": str(zip_path)}, ensure_ascii=False, indent=2, allow_nan=False))
    print("No Discord, MT5, AI API, live hook, live evaluator, or final signal action was performed.")
    return 0 if status.endswith("LIVE_BLOCKED") else 2


if __name__ == "__main__":
    raise SystemExit(main())
