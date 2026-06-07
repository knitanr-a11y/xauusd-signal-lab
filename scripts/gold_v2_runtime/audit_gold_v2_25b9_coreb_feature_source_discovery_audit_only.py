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

STEP = "25B9_COREB_FEATURE_SOURCE_DISCOVERY_AUDIT_ONLY"
PASS_REVIEW_STATUS = "COREB_FEATURE_SOURCE_DISCOVERY_COMPLETED_AUDIT_ONLY_CANDIDATE_REVIEW_REQUIRED"
PASS_NOT_ACCEPTED_STATUS = "COREB_FEATURE_SOURCE_DISCOVERY_COMPLETED_AUDIT_ONLY_SOURCE_NOT_ACCEPTED"
STOP_STATUS = "25B9_STOP_MISSING_INPUT_OR_UNSAFE_STATE_AUDIT_ONLY"
IN25B8 = "gold_v2_25b8_coreb_condition_object_dry_run_plan_audit_only"
OUT_DIR = "gold_v2_25b9_coreb_feature_source_discovery_audit_only"

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
TEXT_SUFFIXES = {".py", ".json", ".md", ".txt", ".yaml", ".yml", ".bat", ".ps1"}
TABLE_SUFFIXES = {".csv", ".parquet"}
SKIP_DIRS = {".git", "__pycache__", ".venv", "venv", "node_modules"}
MAX_TEXT_BYTES = 5_000_000
MAX_CSV_BYTES_FOR_HEADER = 200_000_000


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="25B9 CoreB feature source discovery audit-only")
    p.add_argument("--scan-root", action="append", default=None, help="Additional scan root; can be repeated")
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


def safety_problems(s25b8: dict[str, Any]) -> list[str]:
    problems = []
    if s25b8.get("status") != "COREB_CONDITION_OBJECT_DRY_RUN_PLAN_COMPLETED_AUDIT_ONLY_FEATURE_SOURCE_REQUIRED":
        problems.append("25B8 status mismatch")
    if int(s25b8.get("total_stop_rows", -1)) != 0:
        problems.append("25B8 stop rows not zero")
    for k, expected in SAFETY_FLAGS.items():
        if s25b8.get(k) != expected:
            problems.append(f"safety flag mismatch: {k}")
    for k in ["coreb_live_evaluator_unblocked", "source_recovery_executed", "source_mutation_executed", "same_count_exact_parity_proven", "cluster_membership_parity_proven", "target_key_parity_proven"]:
        if bool(s25b8.get(k)):
            problems.append(f"unsafe prior state: {k}")
    return problems


def required_features(manifest: pd.DataFrame) -> list[str]:
    if "field" not in manifest.columns:
        return []
    return sorted(set(str(x) for x in manifest["field"].dropna().tolist() if str(x)))


def iter_files(root: Path) -> list[Path]:
    out: list[Path] = []
    if not lp(root).exists():
        return out
    for cur, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for name in files:
            p = Path(cur) / name
            if p.suffix.lower() in TEXT_SUFFIXES | TABLE_SUFFIXES:
                out.append(p)
    return out


def csv_header(path: Path) -> list[str]:
    try:
        if lp(path).stat().st_size > MAX_CSV_BYTES_FOR_HEADER:
            # pandas still reads only header, but keep explicit conservative note in caller.
            pass
        return list(pd.read_csv(lp(path), nrows=0, encoding="utf-8-sig").columns)
    except Exception:
        try:
            return list(pd.read_csv(lp(path), nrows=0, encoding="cp932").columns)
        except Exception:
            return []


def parquet_schema(path: Path) -> list[str]:
    try:
        return list(pd.read_parquet(lp(path), columns=[]).columns)
    except Exception:
        try:
            return list(pd.read_parquet(lp(path)).head(0).columns)
        except Exception:
            return []


def text_hits(path: Path, features: list[str]) -> tuple[list[str], str]:
    try:
        if lp(path).stat().st_size > MAX_TEXT_BYTES:
            return [], "SKIPPED_TEXT_TOO_LARGE"
        text = lp(path).read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return [], "READ_ERROR"
    hits = [f for f in features if f in text]
    return hits, "PASS_TEXT_SEARCH"


def file_kind(path: Path) -> str:
    s = path.suffix.lower()
    if s in {".csv", ".parquet"}:
        return "table_candidate"
    if s == ".py":
        return "builder_script_candidate"
    if s in TEXT_SUFFIXES:
        return "text_metadata_candidate"
    return "other"


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    out_dir = Path(args.output_dir).expanduser().resolve() if args.output_dir else fx_outputs() / OUT_DIR
    lp(out_dir).mkdir(parents=True, exist_ok=True)
    in25b8 = fx_outputs() / IN25B8
    required = {
        "25b8_summary": in25b8 / "gold_v2_25b8_coreb_condition_object_dry_run_plan_summary.json",
        "required_feature_manifest": in25b8 / "gold_v2_25b8_required_feature_manifest.csv",
        "missing_feature_source_requirements": in25b8 / "gold_v2_25b8_missing_feature_source_requirements.csv",
    }
    input_audit = pd.DataFrame([{"role": k, "path": str(v), "required": True, "exists": lp(v).exists(), "status": "PASS" if lp(v).exists() else "STOP"} for k, v in required.items()])
    write_csv(out_dir / "gold_v2_25b9_input_audit.csv", input_audit)
    if not bool(input_audit["exists"].all()):
        summary = {"created_utc": datetime.now(timezone.utc).isoformat(), "step": STEP, "status": STOP_STATUS, "audit_only": True, "total_stop_rows": int((input_audit["status"] == "STOP").sum()), **SAFETY_FLAGS}
        write_json(out_dir / "gold_v2_25b9_coreb_feature_source_discovery_summary.json", summary)
        return 2

    s25b8 = read_json(required["25b8_summary"])
    problems = safety_problems(s25b8)
    manifest = read_csv(required["required_feature_manifest"])
    features = required_features(manifest)
    scan_roots = [repo_root(), fx_outputs()]
    if args.scan_root:
        scan_roots.extend(Path(x).expanduser().resolve() for x in args.scan_root)
    unique_roots = []
    for r in scan_roots:
        if str(r) not in [str(x) for x in unique_roots]:
            unique_roots.append(r)
    root_audit = pd.DataFrame([{"scan_root": str(r), "exists": lp(r).exists()} for r in unique_roots])
    write_csv(out_dir / "gold_v2_25b9_scan_root_audit.csv", root_audit)

    rows = []
    for root in unique_roots:
        for p in iter_files(root):
            suffix = p.suffix.lower()
            try:
                size = int(lp(p).stat().st_size)
            except Exception:
                size = 0
            cols: list[str] = []
            hits: list[str] = []
            read_status = "UNREAD"
            if suffix == ".csv":
                cols = csv_header(p)
                hits = [f for f in features if f in cols]
                read_status = "PASS_CSV_HEADER" if cols else "CSV_HEADER_READ_FAILED"
            elif suffix == ".parquet":
                cols = parquet_schema(p)
                hits = [f for f in features if f in cols]
                read_status = "PASS_PARQUET_SCHEMA" if cols else "PARQUET_SCHEMA_READ_FAILED"
            elif suffix in TEXT_SUFFIXES:
                hits, read_status = text_hits(p, features)
            if hits or any(token in p.name.lower() for token in ["feature", "schema", "column", "builder", "gold_v2", "coreb"]):
                rows.append({
                    "path": str(p),
                    "root": str(root),
                    "suffix": suffix,
                    "kind": file_kind(p),
                    "bytes": size,
                    "read_status": read_status,
                    "column_count": len(cols),
                    "required_feature_hits": len(hits),
                    "required_feature_hit_list": ";".join(hits),
                    "coverage_ratio": (len(hits) / len(features)) if features else 0.0,
                    "columns_preview": ";".join(cols[:80]),
                })
    inventory = pd.DataFrame(rows)
    if not inventory.empty:
        inventory = inventory.sort_values(["required_feature_hits", "kind", "path"], ascending=[False, True, True]).reset_index(drop=True)
    write_csv(out_dir / "gold_v2_25b9_feature_source_candidate_inventory.csv", inventory)

    coverage_rows = []
    for _, r in inventory.iterrows() if not inventory.empty else []:
        hits = [x for x in str(r.get("required_feature_hit_list", "")).split(";") if x]
        missing = sorted(set(features) - set(hits))
        coverage_rows.append({
            "path": r.get("path", ""),
            "kind": r.get("kind", ""),
            "required_feature_hits": len(hits),
            "required_feature_count": len(features),
            "missing_feature_count": len(missing),
            "complete_coverage": len(missing) == 0 and len(features) > 0,
            "missing_features_preview": ";".join(missing[:50]),
        })
    coverage = pd.DataFrame(coverage_rows)
    if not coverage.empty:
        coverage = coverage.sort_values(["complete_coverage", "required_feature_hits"], ascending=[False, False])
    write_csv(out_dir / "gold_v2_25b9_feature_coverage_by_candidate.csv", coverage)

    builders = inventory[inventory["kind"].astype(str).eq("builder_script_candidate")].copy() if not inventory.empty else pd.DataFrame()
    write_csv(out_dir / "gold_v2_25b9_builder_script_hits.csv", builders)

    complete_candidates = coverage[coverage["complete_coverage"] == True] if not coverage.empty else pd.DataFrame()
    union_hits = set()
    if not inventory.empty:
        for s in inventory["required_feature_hit_list"].astype(str):
            union_hits.update(x for x in s.split(";") if x)
    missing_after = sorted(set(features) - union_hits)
    missing_df = pd.DataFrame([{"field": f, "found_in_any_candidate": False} for f in missing_after])
    write_csv(out_dir / "gold_v2_25b9_missing_features_after_discovery.csv", missing_df)

    unnecessary = [
        "25B8 report/summary/input_audit/next_step_plan already processed",
        "25B7 and older report/summary files already processed",
        "rr125_raw_signal_ledger.csv alone: confirmed missing 38/38 required feature fields",
        "rr125_top_ledgers.csv alone: target-only, not feature source",
    ]
    necessary = []
    if not complete_candidates.empty:
        for i, row in complete_candidates.head(5).iterrows():
            necessary.append(f"candidate complete feature source review: {row['path']}")
    else:
        necessary.extend([
            "feature table containing all required fields, especially donch_pos_96, abs_ret_72_atr, ret_96_atr, range_96_atr",
            "M5 feature table containing m5_dist_low_32_atr, m5_ret_96_atr, m5_range_8_atr, m5_abs_ret_96_atr",
            "feature schema/columns summary if table is too large",
            "feature builder script that creates the required fields",
        ])
    file_request = pd.DataFrame(
        [{"section": "不要・貼らなくてOK", "rank": i + 1, "item": item} for i, item in enumerate(unnecessary)]
        + [{"section": "必要・貼ってほしい", "rank": i + 1, "item": item} for i, item in enumerate(necessary)]
    )
    write_csv(out_dir / "gold_v2_25b9_file_request_list.csv", file_request)

    next_plan = pd.DataFrame([
        {"rank": 1, "next_step": "manual upload of requested feature source candidates", "allowed_now": True, "purpose": "review candidate feature source before non-key dry-run"},
        {"rank": 2, "next_step": "25C0_COREB_FEATURE_SOURCE_INTAKE_AUDIT_ONLY", "allowed_now": True, "purpose": "only after user provides candidate feature file/schema/builder"},
        {"rank": 3, "next_step": "CoreB non-key dry-run implementation", "allowed_now": False, "purpose": "blocked until feature source accepted"},
        {"rank": 4, "next_step": "CoreB live evaluator", "allowed_now": False, "purpose": "still blocked"},
    ])
    write_csv(out_dir / "gold_v2_25b9_next_step_plan.csv", next_plan)

    status = PASS_REVIEW_STATUS if not complete_candidates.empty else PASS_NOT_ACCEPTED_STATUS
    if problems:
        status = STOP_STATUS
    summary = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "step": STEP,
        "status": status,
        "audit_only": True,
        "status_problems": problems,
        "required_feature_count": int(len(features)),
        "candidate_inventory_rows": int(len(inventory)),
        "complete_coverage_candidates": int(len(complete_candidates)),
        "max_required_feature_hits": int(coverage["required_feature_hits"].max()) if not coverage.empty else 0,
        "missing_features_after_discovery": int(len(missing_after)),
        "top_candidate_paths": coverage.head(10)["path"].astype(str).tolist() if not coverage.empty else [],
        "coreb_live_evaluator_unblocked": False,
        "source_recovery_executed": False,
        "source_mutation_executed": False,
        "same_count_exact_parity_proven": False,
        "cluster_membership_parity_proven": False,
        "target_key_parity_proven": False,
        "next_recommended_step": "25C0_COREB_FEATURE_SOURCE_INTAKE_AUDIT_ONLY_AFTER_USER_UPLOAD" if complete_candidates.empty else "25C0_COREB_FEATURE_SOURCE_CANDIDATE_REVIEW_AUDIT_ONLY",
        "total_stop_rows": int(len(problems)),
        **SAFETY_FLAGS,
    }
    write_json(out_dir / "gold_v2_25b9_coreb_feature_source_discovery_summary.json", summary)

    request_text = "\n".join(
        ["【不要・貼らなくてOK】"]
        + [f"{i+1}. {x}" for i, x in enumerate(unnecessary)]
        + ["", "【必要・貼ってほしい】"]
        + [f"{i+1}. {x}" for i, x in enumerate(necessary)]
    )
    report = "\n".join([
        "# GOLD V2 25B9 CoreB feature source discovery audit-only report",
        "",
        f"Created UTC: {summary['created_utc']}",
        f"Step: `{STEP}`",
        f"Status: `{status}`",
        "",
        "## Boundary",
        "",
        "25B9 discovers candidate feature sources only. It does not rebuild features, run CoreB replay, mutate sources, or unblock CoreB.",
        "",
        "## Input audit",
        "",
        md_table(input_audit),
        "",
        "## Scan root audit",
        "",
        md_table(root_audit),
        "",
        "## Candidate inventory top rows",
        "",
        md_table(inventory, max_rows=40),
        "",
        "## Feature coverage by candidate",
        "",
        md_table(coverage, max_rows=40),
        "",
        "## Missing features after discovery",
        "",
        md_table(missing_df, max_rows=60),
        "",
        "## File request list",
        "",
        "```text",
        request_text,
        "```",
        "",
        "## Next step plan",
        "",
        md_table(next_plan),
        "",
        "## Safety",
        "",
        "CoreB remains blocked. Source recovery/live/final/external actions remain off.",
    ])
    lp(out_dir / "GOLD_V2_25B9_COREB_FEATURE_SOURCE_DISCOVERY_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")

    print(json.dumps({"status": status, "output_dir": str(out_dir), "candidate_inventory_rows": int(len(inventory)), "complete_coverage_candidates": int(len(complete_candidates)), "max_required_feature_hits": summary["max_required_feature_hits"], "missing_features_after_discovery": int(len(missing_after))}, ensure_ascii=False, indent=2))
    return 0 if not problems else 2


if __name__ == "__main__":
    raise SystemExit(main())
