#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""GOLD V2 25B3 CoreB source shortlist content audit-only, fixed build.

This is the same audit-only 25B3 intent with the source-role summary bug fixed.
It reads only the 25B2 shortlist and profiles the six shortlisted CoreB files.
No replay, source mutation, live enabling, or external action is performed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Sequence

import pandas as pd

STEP = "25B3_COREB_SOURCE_SHORTLIST_CONTENT_AUDIT_ONLY"
IN_DIR = "gold_v2_25b2_coreb_cluster_candidate_triage_audit_only"
OUT_DIR = "gold_v2_25b3_coreb_source_shortlist_content_audit_only"
PASS_STATUS = "COREB_SOURCE_SHORTLIST_CONTENT_AUDIT_COMPLETED_AUDIT_ONLY_REPLAY_PLAN_REQUIRED"
STOP_STATUS = "25B3_STOP_INPUT_OR_SHORTLIST_FILE_MISSING_AUDIT_ONLY"
REQUIRED_SHORTLIST_COLS = ["normalized_path", "absolute_path", "triage_class", "review_priority", "next_action"]

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
    p = argparse.ArgumentParser(description="25B3 CoreB source shortlist content audit-only fixed")
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


def read_csv_any(path: Path, nrows: int | None = None) -> pd.DataFrame:
    last: Exception | None = None
    for enc in ("utf-8-sig", "utf-8", "cp932"):
        try:
            return pd.read_csv(lp(path), encoding=enc, keep_default_na=False, nrows=nrows)
        except Exception as exc:
            last = exc
    raise RuntimeError(f"Could not read CSV {path}: {last}")


def read_json_any(path: Path) -> Any:
    return json.loads(lp(path).read_text(encoding="utf-8-sig"))


def write_csv(path: Path, df: pd.DataFrame) -> None:
    lp(path.parent).mkdir(parents=True, exist_ok=True)
    df.to_csv(lp(path), index=False, encoding="utf-8-sig")


def write_json(path: Path, obj: dict[str, Any]) -> None:
    lp(path.parent).mkdir(parents=True, exist_ok=True)
    lp(path).write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with lp(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def resolve_abs_path(text: Any) -> Path:
    return Path(str(text or ""))


def fmt(v: Any) -> str:
    try:
        if pd.isna(v):
            return ""
    except Exception:
        pass
    if isinstance(v, float):
        if math.isinf(v):
            return "inf" if v > 0 else "-inf"
        return f"{v:.6g}"
    return str(v).replace("|", "\\|").replace("\n", " ")


def md_table(df: pd.DataFrame, max_rows: int = 80) -> str:
    if df.empty:
        return "_No rows._"
    view = df.head(max_rows)
    cols = list(view.columns)
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for _, r in view.iterrows():
        lines.append("| " + " | ".join(fmt(r[c]) for c in cols) + " |")
    if len(df) > max_rows:
        lines.append(f"| ... | truncated {len(df)-max_rows} more rows |" + " |" * max(0, len(cols) - 2))
    return "\n".join(lines)


def count_values(df: pd.DataFrame, col: str, max_items: int = 30) -> str:
    if col not in df.columns:
        return ""
    vc = df[col].astype(str).value_counts(dropna=False).head(max_items)
    return "; ".join(f"{idx}={int(val)}" for idx, val in vc.items())


def flatten_json(obj: Any, prefix: str = "", out: Optional[list[dict[str, Any]]] = None, limit: int = 5000) -> list[dict[str, Any]]:
    if out is None:
        out = []
    if len(out) >= limit:
        return out
    if isinstance(obj, dict):
        items = obj.items()
    elif isinstance(obj, list):
        items = list(enumerate(obj[:500]))
    else:
        out.append({"json_path": prefix or "$", "value_type": type(obj).__name__, "value_preview": str(obj)[:500]})
        return out
    for k, v in items:
        key = f"{prefix}.{k}" if prefix else str(k)
        if isinstance(v, (dict, list)):
            out.append({"json_path": key, "value_type": type(v).__name__, "value_preview": f"len={len(v)}"})
            flatten_json(v, key, out, limit)
        else:
            out.append({"json_path": key, "value_type": type(v).__name__, "value_preview": str(v)[:500]})
        if len(out) >= limit:
            break
    return out


def csv_profile(path: Path, normalized_path: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    df = read_csv_any(path)
    cols = list(df.columns)
    same_count_num = pd.to_numeric(df["same_count"], errors="coerce") if "same_count" in cols else pd.Series(dtype=float)
    row = {
        "normalized_path": normalized_path,
        "rows": int(len(df)),
        "columns": int(len(cols)),
        "column_names": ";".join(cols),
        "has_entry_time": "entry_time" in cols,
        "has_cluster_id": "cluster_id" in cols,
        "has_same_count": "same_count" in cols,
        "has_member_rows": any(c.lower() in {"member_id", "member_entry_time", "cluster_member_id", "membership"} for c in cols),
        "has_candidate_origin": all(c in cols for c in ["candidate_id", "origin_id"]),
        "dataset_counts": count_values(df, "dataset"),
        "policy_counts": count_values(df, "policy"),
        "filter_counts": count_values(df, "filter"),
        "direction_counts": count_values(df, "direction") or count_values(df, "top_direction"),
        "rr_bucket_counts": count_values(df, "rr_bucket"),
        "top_candidate_counts": count_values(df, "top_candidate_id"),
        "unique_entry_time": int(df["entry_time"].astype(str).nunique()) if "entry_time" in cols else "",
        "unique_cluster_id": int(df["cluster_id"].astype(str).nunique()) if "cluster_id" in cols else "",
        "same_count_min": float(same_count_num.min()) if "same_count" in cols and len(df) else "",
        "same_count_max": float(same_count_num.max()) if "same_count" in cols and len(df) else "",
        "same_count_ge15_rows": int((same_count_num >= 15).sum()) if "same_count" in cols else "",
    }
    samples: list[dict[str, Any]] = []
    for _, r in df.head(5).iterrows():
        samples.append({"normalized_path": normalized_path, "sample_row_json": json.dumps({c: r[c] for c in cols[:40]}, ensure_ascii=False, default=str)})
    return row, samples


def json_profile(path: Path, normalized_path: str) -> tuple[dict[str, Any], pd.DataFrame]:
    obj = read_json_any(path)
    flat = flatten_json(obj)
    flat_df = pd.DataFrame(flat)
    top_keys = list(obj.keys()) if isinstance(obj, dict) else []
    flat_text = json.dumps(obj, ensure_ascii=False)[:200000]
    linked_paths = sorted(set(re.findall(r"[A-Za-z]:\\\\[^\"']+|[A-Za-z]:\\[^\"']+", flat_text)))
    row = {
        "normalized_path": normalized_path,
        "top_level_type": type(obj).__name__,
        "top_level_keys": ";".join(map(str, top_keys)),
        "flattened_key_count": int(len(flat_df)),
        "status_values": "; ".join(str(x.get("value_preview", "")) for x in flat if str(x.get("json_path", "")).lower().endswith("status"))[:1000],
        "contains_same_count_source_universe": "same_count_source_universe" in flat_text,
        "contains_raw_ledger_link": "rr125_raw_signal_ledger.csv" in flat_text,
        "contains_top_ledgers_link": "rr125_top_ledgers.csv" in flat_text,
        "contains_selected_source_path": "selected_source_path" in flat_text,
        "contains_same_count_source_path": "same_count_source_path" in flat_text,
        "linked_path_count": int(len(linked_paths)),
        "linked_paths_preview": "; ".join(linked_paths[:20]),
    }
    if not flat_df.empty:
        flat_df.insert(0, "normalized_path", normalized_path)
    return row, flat_df


def classify_evidence(normalized_path: str, triage_class: str, csv_row: dict[str, Any] | None) -> dict[str, Any]:
    p = normalized_path.replace("/", "\\").lower()
    role = "UNKNOWN"
    if "rr125_raw_signal_ledger.csv" in p:
        role = "SOURCE_UNIVERSE_RAW_LEDGER"
    elif "frozen_coreb_same_count_source_universe" in p:
        role = "SOURCE_UNIVERSE_FROZEN_CONFIG"
    elif "frozen_coreb_rr125_source_rule_conditions" in p or "frozen_coreb_rr125_buy_confluence_rules" in p:
        role = "FROZEN_RULE_CONDITION_CONFIG"
    elif "frozen_coreb_combined_evaluator_definition" in p:
        role = "COMBINED_EVALUATOR_DEFINITION"
    elif "rr125_top_ledgers.csv" in p:
        role = "TARGET_TOP_LEDGER_ONLY"
    proves_membership = bool(csv_row and csv_row.get("has_member_rows"))
    return {
        "normalized_path": normalized_path,
        "triage_class": triage_class,
        "evidence_role": role,
        "can_be_used_as_source_universe_input": role in {"SOURCE_UNIVERSE_RAW_LEDGER", "SOURCE_UNIVERSE_FROZEN_CONFIG", "FROZEN_RULE_CONDITION_CONFIG", "COMBINED_EVALUATOR_DEFINITION"},
        "can_be_used_as_target_ledger": role == "TARGET_TOP_LEDGER_ONLY",
        "proves_row_level_membership_semantics_now": proves_membership,
        "proves_same_count_exact_parity_now": False,
        "coreb_live_unblock_evidence_now": False,
        "required_next_review": "manual content review then 25B4 replay plan; no replay execution in 25B3",
    }


def evidence_role_counts(linkage: pd.DataFrame) -> dict[str, int]:
    if linkage.empty or "evidence_role" not in linkage.columns:
        return {}
    counts = linkage["evidence_role"].astype(str).value_counts(dropna=False).sort_index()
    return {str(role): int(rows) for role, rows in counts.items()}


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    in_dir = Path(args.input_dir).expanduser().resolve() if args.input_dir else default_input_dir()
    out_dir = Path(args.output_dir).expanduser().resolve() if args.output_dir else default_output_dir()
    lp(out_dir).mkdir(parents=True, exist_ok=True)

    shortlist_path = in_dir / "gold_v2_25b2_priority_shortlist.csv"
    summary_path = in_dir / "gold_v2_25b2_coreb_cluster_candidate_triage_summary.json"
    inputs = pd.DataFrame([
        {"role": "25b2_priority_shortlist", "path": str(shortlist_path), "required": True, "exists": lp(shortlist_path).exists(), "status": "PASS" if lp(shortlist_path).exists() else "STOP"},
        {"role": "25b2_summary", "path": str(summary_path), "required": True, "exists": lp(summary_path).exists(), "status": "PASS" if lp(summary_path).exists() else "STOP"},
    ])
    write_csv(out_dir / "gold_v2_25b3_input_audit.csv", inputs)
    if not bool(inputs["exists"].all()):
        summary = {"created_utc": datetime.now(timezone.utc).isoformat(), "step": STEP, "status": STOP_STATUS, "audit_only": True, "total_stop_rows": int((inputs["status"] == "STOP").sum()), **SAFETY_FLAGS}
        write_json(out_dir / "gold_v2_25b3_coreb_source_shortlist_content_summary.json", summary)
        return 2

    shortlist = read_csv_any(shortlist_path)
    s25b2 = read_json_any(summary_path)
    missing_cols = [c for c in REQUIRED_SHORTLIST_COLS if c not in shortlist.columns]
    expected_rows = int(s25b2.get("priority_shortlist_rows", -1))
    row_match = int(len(shortlist)) == expected_rows

    file_rows: list[dict[str, Any]] = []
    csv_rows: list[dict[str, Any]] = []
    json_rows: list[dict[str, Any]] = []
    json_flat_frames: list[pd.DataFrame] = []
    sample_rows: list[dict[str, Any]] = []
    linkage_rows: list[dict[str, Any]] = []
    stop_count = 0

    for _, sr in shortlist.iterrows():
        npath = str(sr.get("normalized_path", ""))
        apath = resolve_abs_path(sr.get("absolute_path", ""))
        exists = lp(apath).exists()
        if not exists:
            stop_count += 1
        frow: dict[str, Any] = {
            "normalized_path": npath,
            "absolute_path": str(apath),
            "triage_class": sr.get("triage_class", ""),
            "review_priority": sr.get("review_priority", ""),
            "exists": bool(exists),
            "suffix": apath.suffix.lower(),
            "bytes": int(lp(apath).stat().st_size) if exists else "",
            "sha256": sha256_file(apath) if exists else "",
            "read_status": "PENDING" if exists else "STOP_MISSING",
        }
        csv_row = None
        if exists and apath.suffix.lower() == ".csv":
            try:
                csv_row, samples = csv_profile(apath, npath)
                csv_rows.append(csv_row)
                sample_rows.extend(samples)
                frow["read_status"] = "PASS_CSV_PROFILED"
            except Exception as exc:
                frow["read_status"] = f"STOP_CSV_READ_ERROR: {exc!r}"
                stop_count += 1
        elif exists and apath.suffix.lower() == ".json":
            try:
                json_row, flat_df = json_profile(apath, npath)
                json_rows.append(json_row)
                if not flat_df.empty:
                    json_flat_frames.append(flat_df)
                frow["read_status"] = "PASS_JSON_PROFILED"
            except Exception as exc:
                frow["read_status"] = f"STOP_JSON_READ_ERROR: {exc!r}"
                stop_count += 1
        elif exists:
            frow["read_status"] = "PASS_EXISTS_NOT_PROFILED"
        file_rows.append(frow)
        linkage_rows.append(classify_evidence(npath, str(sr.get("triage_class", "")), csv_row))

    file_audit = pd.DataFrame(file_rows)
    csv_profile_df = pd.DataFrame(csv_rows)
    json_profile_df = pd.DataFrame(json_rows)
    json_flat_df = pd.concat(json_flat_frames, ignore_index=True) if json_flat_frames else pd.DataFrame(columns=["normalized_path", "json_path", "value_type", "value_preview"])
    sample_df = pd.DataFrame(sample_rows)
    linkage = pd.DataFrame(linkage_rows)

    unblock_gaps = pd.DataFrame([
        {"gap_id": "25B3-G001", "gap": "CoreB replay not executed", "observed": False, "expected_before_unblock": True, "status": "OPEN", "detail": "25B3 is content inspection only."},
        {"gap_id": "25B3-G002", "gap": "replayed CoreB RR125 rows = 125", "observed": "not checked", "expected_before_unblock": "125", "status": "OPEN", "detail": "Requires later replay plan/execution."},
        {"gap_id": "25B3-G003", "gap": "same_count exact match rows = 125", "observed": "not checked", "expected_before_unblock": "125", "status": "OPEN", "detail": "No same_count approximation allowed."},
        {"gap_id": "25B3-G004", "gap": "cluster_id or membership exact match rows = 125", "observed": "not checked", "expected_before_unblock": "125 if applicable", "status": "OPEN", "detail": "Shortlist files do not by themselves prove row-level membership semantics."},
        {"gap_id": "25B3-G005", "gap": "human acceptance of original/source evidence", "observed": "not yet", "expected_before_unblock": "accepted", "status": "OPEN", "detail": "Needed before replay implementation."},
    ])
    next_plan = pd.DataFrame([
        {"rank": 1, "next_step": "25B4_COREB_SAME_COUNT_REPLAY_PLAN_AUDIT_ONLY", "purpose": "Write a replay plan from inspected source universe/configs to target top ledger, without executing replay yet.", "allowed_now": True, "blocked_actions": "no replay execution, no live signal, no external actions"},
        {"rank": 2, "next_step": "Manual review of 25B3 JSON key inventory and CSV profiles", "purpose": "Confirm whether source universe/configs are original enough to plan replay.", "allowed_now": True, "blocked_actions": "no source recovery execution"},
        {"rank": 3, "next_step": "CoreB live evaluator", "purpose": "Still blocked until replay/parity proves 125 exact rows and same_count/membership parity.", "allowed_now": False, "blocked_actions": "final signal / external actions"},
    ])

    if missing_cols:
        stop_count += 1
    if not row_match:
        stop_count += 1
    status = PASS_STATUS if stop_count == 0 else STOP_STATUS

    write_csv(out_dir / "gold_v2_25b3_shortlist_file_content_audit.csv", file_audit)
    write_csv(out_dir / "gold_v2_25b3_csv_profile.csv", csv_profile_df)
    write_csv(out_dir / "gold_v2_25b3_csv_sample_rows.csv", sample_df)
    write_csv(out_dir / "gold_v2_25b3_json_profile.csv", json_profile_df)
    write_csv(out_dir / "gold_v2_25b3_json_key_inventory.csv", json_flat_df)
    write_csv(out_dir / "gold_v2_25b3_coreb_source_linkage_matrix.csv", linkage)
    write_csv(out_dir / "gold_v2_25b3_unblock_gap_matrix.csv", unblock_gaps)
    write_csv(out_dir / "gold_v2_25b3_next_review_plan.csv", next_plan)

    summary = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "step": STEP,
        "status": status,
        "audit_only": True,
        "fixed_build": True,
        "bugfix": "source_role_counts now uses value_counts instead of misusing iterrows",
        "input_dir": str(in_dir),
        "output_dir": str(out_dir),
        "shortlist_rows": int(len(shortlist)),
        "expected_shortlist_rows_from_25b2_summary": expected_rows,
        "shortlist_row_count_matches_25b2_summary": bool(row_match),
        "missing_required_shortlist_columns": missing_cols,
        "missing_shortlist_files": int((file_audit["exists"] == False).sum()) if not file_audit.empty else 0,
        "profiled_csv_files": int(len(csv_profile_df)),
        "profiled_json_files": int(len(json_profile_df)),
        "source_role_counts": evidence_role_counts(linkage),
        "coreb_live_evaluator_unblocked": False,
        "replay_executed": False,
        "same_count_recomputed": False,
        "same_count_exact_parity_proven": False,
        "cluster_membership_parity_proven": False,
        "source_recovery_executed": False,
        "source_mutation_executed": False,
        "next_recommended_step": "25B4_COREB_SAME_COUNT_REPLAY_PLAN_AUDIT_ONLY",
        "total_stop_rows": int(stop_count),
        **SAFETY_FLAGS,
    }
    write_json(out_dir / "gold_v2_25b3_coreb_source_shortlist_content_summary.json", summary)

    report = "\n".join([
        "# GOLD V2 25B3 CoreB source shortlist content audit-only report",
        "",
        f"Created UTC: {summary['created_utc']}",
        f"Step: `{STEP}`",
        f"Status: `{status}`",
        "Fixed build: `true`",
        "",
        "## Boundary",
        "",
        "25B3 inspects only the 25B2 priority shortlist. It does not replay CoreB, reconstruct same_count, infer membership, fit cluster_id, mutate source artifacts, or enable signals/external actions.",
        "",
        "## Input audit",
        "",
        md_table(inputs),
        "",
        "## Shortlist row checks",
        "",
        f"- shortlist_rows: `{len(shortlist)}`",
        f"- expected_shortlist_rows_from_25B2_summary: `{expected_rows}`",
        f"- row_count_match: `{row_match}`",
        f"- missing_required_shortlist_columns: `{missing_cols}`",
        "",
        "## Shortlist file content audit",
        "",
        md_table(file_audit),
        "",
        "## CSV profile",
        "",
        md_table(csv_profile_df, max_rows=20),
        "",
        "## JSON profile",
        "",
        md_table(json_profile_df, max_rows=20),
        "",
        "## CoreB source linkage matrix",
        "",
        md_table(linkage),
        "",
        "## Unblock gap matrix",
        "",
        md_table(unblock_gaps),
        "",
        "## Next review plan",
        "",
        md_table(next_plan),
        "",
        "## Safety",
        "",
        "- CoreB live evaluator unblocked: `false`",
        "- replay executed: `false`",
        "- same_count recomputed: `false`",
        "- same_count exact parity proven: `false`",
        "- cluster membership parity proven: `false`",
        "- external actions / final signal: `false`",
    ])
    lp(out_dir / "GOLD_V2_25B3_COREB_SOURCE_SHORTLIST_CONTENT_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")

    print(json.dumps({
        "status": status,
        "fixed_build": True,
        "output_dir": str(out_dir),
        "shortlist_rows": int(len(shortlist)),
        "profiled_csv_files": int(len(csv_profile_df)),
        "profiled_json_files": int(len(json_profile_df)),
        "next_recommended_step": summary["next_recommended_step"],
    }, ensure_ascii=False, indent=2, allow_nan=False))
    return 0 if stop_count == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
