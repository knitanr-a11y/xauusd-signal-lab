#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""GOLD V2 25C86 frozen same-count condition replay audit-only.

Tests whether CoreB same_count is reproduced as the count of frozen
same-count source rules passing on the required feature snapshot row.

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

STEP = "25C86_FROZEN_SAME_COUNT_CONDITION_REPLAY_AUDIT_ONLY"
OUT_DIR_NAME = "gold_v2_25c86_frozen_same_count_condition_replay_audit_only"
EXTERNAL_ACTIONS = {"discord_send_allowed": False, "mt5_order_allowed": False, "ai_api_allowed": False, "live_hook_allowed": False}

INPUT_NAMES = [
    "25c85_summary.json",
    "rr125_top_ledgers.csv",
    "gold_v2_13c_coreb_rr125_selected_top_ledgers.csv",
    "frozen_coreB_combined_evaluator_definition_20260604.json",
    "frozen_coreB_same_count_source_universe_20260604.json",
    "frozen_coreB_rr125_source_rule_conditions_20260603.json",
    "gold_v2_coreb_combined_required_feature_snapshot.csv",
    "gold_v2_coreb_combined_selected_conditions.csv",
    "gold_v2_coreb_combined_same_count_conditions.csv",
]


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def files_root() -> Path:
    r = repo_root()
    return r.parents[1] if len(r.parents) >= 2 else r.parent


def fx_outputs() -> Path:
    return files_root() / "FX_OUTPUTS"


def out_dir() -> Path:
    out = fx_outputs() / OUT_DIR_NAME
    out.mkdir(parents=True, exist_ok=True)
    return out


def find_file(name: str) -> Path | None:
    candidates = [repo_root() / "configs" / "gold_v2" / name, repo_root() / name, fx_outputs() / name]
    for c in candidates:
        if c.exists():
            return c
    if fx_outputs().exists():
        found = sorted(fx_outputs().rglob(name))
        if found:
            return found[0]
    if repo_root().exists():
        found = sorted(repo_root().rglob(name))
        if found:
            return found[0]
    return None


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


def read_json(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def read_csv(path: Path | None) -> pd.DataFrame:
    if path is None or not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def inventory(paths: dict[str, Path | None]) -> pd.DataFrame:
    rows = []
    for name, path in paths.items():
        row: dict[str, Any] = {"filename": name, "exists": bool(path and path.exists()), "path": str(path) if path else ""}
        if path and path.exists():
            row["bytes"] = path.stat().st_size
            row["sha256"] = sha256_file(path)
            if path.suffix.lower() == ".csv":
                try:
                    row["row_count"] = len(pd.read_csv(path))
                    row["columns"] = ";".join(pd.read_csv(path, nrows=0).columns)
                except Exception as exc:
                    row["read_error"] = repr(exc)
            elif path.suffix.lower() == ".json":
                row["json_keys"] = ";".join(list(read_json(path).keys())[:20])
        rows.append(row)
    return pd.DataFrame(rows)


def normalize_condition_df(df: pd.DataFrame, rule_set: str) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["rule_set", "rule_id", "field", "operator", "value"])
    d = df.copy()
    rename = {"op": "operator", "threshold": "value", "feature": "field"}
    d = d.rename(columns={k: v for k, v in rename.items() if k in d.columns})
    if "rule_id" not in d.columns:
        if "candidate_id" in d.columns:
            d["rule_id"] = d["candidate_id"].astype(str)
        else:
            d["rule_id"] = [f"{rule_set}_{i:04d}" for i in range(len(d))]
    if "rule_set" not in d.columns:
        d["rule_set"] = rule_set
    need = ["rule_set", "rule_id", "field", "operator", "value"]
    for c in need:
        if c not in d.columns:
            d[c] = ""
    return d[need + [c for c in d.columns if c not in need]].copy()


def extract_condition_objects_from_json(obj: Any, rule_set: str) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []

    def walk(x: Any, inherited_rule: str | None = None) -> None:
        if isinstance(x, dict):
            rid = str(x.get("rule_id") or x.get("candidate_id") or inherited_rule or "")
            # condition object shape
            field = x.get("field") or x.get("feature")
            op = x.get("operator") or x.get("op")
            val = x.get("value") or x.get("threshold")
            if field is not None and op is not None and val is not None:
                rows.append({"rule_set": rule_set, "rule_id": rid or f"{rule_set}_{len(rows):04d}", "field": field, "operator": op, "value": val})
            for key in ["conditions", "condition_objects", "base_condition_objects", "rules", "source_rules", "conditions_flat"]:
                if key in x:
                    walk(x[key], rid or inherited_rule)
            # Also traverse nested dict/list broadly, but avoid double just metadata scalar.
            for v in x.values():
                if isinstance(v, (dict, list)):
                    walk(v, rid or inherited_rule)
        elif isinstance(x, list):
            for v in x:
                walk(v, inherited_rule)

    walk(obj, None)
    return normalize_condition_df(pd.DataFrame(rows), rule_set)


def condition_passes(row: pd.Series, cond: pd.Series) -> bool:
    field = str(cond.get("field"))
    op = str(cond.get("operator"))
    try:
        val = float(cond.get("value"))
        x = float(row.get(field, math.nan))
    except Exception:
        return False
    if math.isnan(x):
        return False
    if op == ">":
        return x > val
    if op == ">=":
        return x >= val
    if op == "<":
        return x < val
    if op == "<=":
        return x <= val
    if op == "==":
        return x == val
    return False


def rule_counts_for_snapshot(feat: pd.DataFrame, conditions: pd.DataFrame, prefix: str) -> pd.DataFrame:
    if feat.empty or conditions.empty:
        return pd.DataFrame()
    rows = []
    groups = list(conditions.groupby("rule_id", dropna=False))
    time_col = "time" if "time" in feat.columns else "entry_time" if "entry_time" in feat.columns else None
    for idx, frow in feat.iterrows():
        passed_rules = 0
        total_rules = 0
        for rid, group in groups:
            if group.empty:
                continue
            total_rules += 1
            if all(condition_passes(frow, c) for _, c in group.iterrows()):
                passed_rules += 1
        rows.append({
            "feature_row_index": idx,
            "time": frow.get(time_col, "") if time_col else "",
            f"{prefix}_passed_rules": passed_rules,
            f"{prefix}_total_rules": total_rules,
        })
    return pd.DataFrame(rows)


def coreb_top(top: pd.DataFrame) -> pd.DataFrame:
    if top.empty:
        return top
    return top[(top["policy"].astype(str).eq("RR125_from_RR1_rules")) & (top["filter"].astype(str).eq("same_count>=15"))].copy()


def join_and_compare(top125: pd.DataFrame, feat_counts: pd.DataFrame) -> pd.DataFrame:
    if top125.empty or feat_counts.empty:
        return pd.DataFrame([{"check": "input_present", "status": "FAIL"}])
    top = top125.copy()
    top["entry_time_norm"] = pd.to_datetime(top["entry_time"], errors="coerce").dt.strftime("%Y-%m-%d %H:%M:%S")
    fc = feat_counts.copy()
    fc["entry_time_norm"] = pd.to_datetime(fc["time"], errors="coerce").dt.strftime("%Y-%m-%d %H:%M:%S")
    joined = top.merge(fc, on="entry_time_norm", how="left")
    rows = []
    for pred_col in [c for c in joined.columns if c.endswith("_passed_rules")]:
        for target_col in ["same_count", "source_rule_count"]:
            if target_col not in joined.columns:
                continue
            pred = pd.to_numeric(joined[pred_col], errors="coerce")
            target = pd.to_numeric(joined[target_col], errors="coerce")
            exact = int((pred == target).sum())
            rows.append({
                "prediction_column": pred_col,
                "target_column": target_col,
                "joined_rows": int(len(joined)),
                "non_null_predictions": int(pred.notna().sum()),
                "exact_rows": exact,
                "exact_ratio": float(exact / len(joined)) if len(joined) else 0.0,
                "mae": float((pred - target).abs().mean()) if pred.notna().any() else None,
                "status": "FULL" if exact == len(joined) else "PARTIAL_OR_FAIL",
            })
    return pd.DataFrame(rows).sort_values(["exact_rows", "exact_ratio"], ascending=False)


def md(df: pd.DataFrame, max_rows: int = 40) -> str:
    if df.empty:
        return "_No rows._"
    d = df.head(max_rows).fillna("").copy()
    lines = ["| " + " | ".join(map(str, d.columns)) + " |", "| " + " | ".join(["---"] * len(d.columns)) + " |"]
    for _, r in d.iterrows():
        lines.append("| " + " | ".join(str(r[c]).replace("|", "\\|").replace("\n", " ") for c in d.columns) + " |")
    return "\n".join(lines)


def main() -> int:
    out = out_dir()
    created = datetime.now(timezone.utc).isoformat()
    paths = {name: find_file(name) for name in INPUT_NAMES}
    inv = inventory(paths)
    s85 = read_json(paths["25c85_summary.json"])
    top = read_csv(paths["rr125_top_ledgers.csv"])
    top125 = coreb_top(top)
    feat = read_csv(paths["gold_v2_coreb_combined_required_feature_snapshot.csv"])

    selected_csv_conditions = normalize_condition_df(read_csv(paths["gold_v2_coreb_combined_selected_conditions.csv"]), "selected")
    same_csv_conditions = normalize_condition_df(read_csv(paths["gold_v2_coreb_combined_same_count_conditions.csv"]), "same_count")
    selected_json_conditions = extract_condition_objects_from_json(read_json(paths["frozen_coreB_rr125_source_rule_conditions_20260603.json"]), "selected_json")
    same_json_conditions = extract_condition_objects_from_json(read_json(paths["frozen_coreB_same_count_source_universe_20260604.json"]), "same_count_json")

    condition_inventory = pd.DataFrame([
        ["selected_csv", len(selected_csv_conditions), selected_csv_conditions["rule_id"].nunique() if not selected_csv_conditions.empty else 0],
        ["same_count_csv", len(same_csv_conditions), same_csv_conditions["rule_id"].nunique() if not same_csv_conditions.empty else 0],
        ["selected_json", len(selected_json_conditions), selected_json_conditions["rule_id"].nunique() if not selected_json_conditions.empty else 0],
        ["same_count_json", len(same_json_conditions), same_json_conditions["rule_id"].nunique() if not same_json_conditions.empty else 0],
    ], columns=["condition_source", "condition_rows", "rule_count"])

    count_frames = []
    if not selected_csv_conditions.empty:
        count_frames.append(rule_counts_for_snapshot(feat, selected_csv_conditions, "selected_csv"))
    if not same_csv_conditions.empty:
        count_frames.append(rule_counts_for_snapshot(feat, same_csv_conditions, "same_count_csv"))
    if not selected_json_conditions.empty:
        count_frames.append(rule_counts_for_snapshot(feat, selected_json_conditions, "selected_json"))
    if not same_json_conditions.empty:
        count_frames.append(rule_counts_for_snapshot(feat, same_json_conditions, "same_count_json"))

    if count_frames:
        feat_counts = count_frames[0]
        for extra in count_frames[1:]:
            feat_counts = feat_counts.merge(extra, on=["feature_row_index", "time"], how="outer")
    else:
        feat_counts = pd.DataFrame()

    compare = join_and_compare(top125, feat_counts)
    full_match = bool((compare.get("status", pd.Series(dtype=str)).astype(str) == "FULL").any()) if not compare.empty else False
    upstream_ok = s85.get("status") in {"LOCAL_SOURCE_GENERATOR_NOT_FOUND_PARTIAL_LOGIC_ONLY_AUDIT_ONLY_LIVE_BLOCKED", "LOCAL_SOURCE_GENERATOR_CANDIDATE_FOUND_REVIEW_REQUIRED_AUDIT_ONLY_LIVE_BLOCKED"}
    inputs_ok = bool(inv["exists"].all()) if not inv.empty else False

    if full_match:
        status = "FROZEN_SAME_COUNT_CONDITION_REPLAY_MATCHED_TOP125_AUDIT_ONLY_HUMAN_REVIEW_REQUIRED_LIVE_BLOCKED"
        next_step = "HUMAN_REVIEW_FROZEN_CONDITION_REPLAY_BEFORE_ANY_LIVE_STEP"
    else:
        status = "FROZEN_SAME_COUNT_CONDITION_REPLAY_NOT_MATCHED_AUDIT_ONLY_LIVE_BLOCKED"
        next_step = "REVIEW_FEATURE_SNAPSHOT_TIME_ALIGNMENT_OR_DEFINE_NEW_COREB_COMPATIBLE_POLICY"
    if not upstream_ok or not inputs_ok:
        status = "FROZEN_SAME_COUNT_CONDITION_REPLAY_INPUT_REVIEW_REQUIRED_AUDIT_ONLY"
        next_step = "REVIEW_25C86_INPUTS"

    decision = pd.DataFrame([
        ["upstream_25c85_ok", upstream_ok, True, "PASS" if upstream_ok else "FAIL"],
        ["inputs_present", inputs_ok, True, "PASS" if inputs_ok else "FAIL"],
        ["top125_rows", len(top125), 125, "PASS" if len(top125) == 125 else "FAIL"],
        ["feature_rows", len(feat), ">0", "PASS" if len(feat) > 0 else "FAIL"],
        ["same_count_condition_replay_full_match", full_match, True, "PASS" if full_match else "BLOCKED"],
        ["coreb_live_evaluator_allowed", False, False, "PASS"],
        ["a002_used", False, False, "PASS"],
    ], columns=["decision_item", "observed", "required", "status"])

    summary = {
        "created_utc": created,
        "step": STEP,
        "status": status,
        "audit_only": True,
        "upstream_25c85_ok": upstream_ok,
        "inputs_ok": inputs_ok,
        "top125_rows": int(len(top125)),
        "feature_rows": int(len(feat)),
        "condition_sources": condition_inventory.to_dict(orient="records"),
        "full_match_found": full_match,
        "coreb_historical_sot_report_allowed": True,
        "coreb_live_evaluator_allowed": False,
        "final_signal_allowed": False,
        "a002_used": False,
        "source_recovery_approved": False,
        "external_actions": EXTERNAL_ACTIONS,
        "next_recommended_step": next_step,
    }

    inv.to_csv(out / "25c86_input_inventory.csv", index=False, encoding="utf-8-sig")
    condition_inventory.to_csv(out / "25c86_condition_inventory.csv", index=False, encoding="utf-8-sig")
    feat_counts.to_csv(out / "25c86_feature_rule_hit_counts.csv", index=False, encoding="utf-8-sig")
    compare.to_csv(out / "25c86_top125_same_count_comparison.csv", index=False, encoding="utf-8-sig")
    decision.to_csv(out / "25c86_decision_matrix.csv", index=False, encoding="utf-8-sig")
    write_json(out / "25c86_summary.json", summary)

    report = "\n".join([
        "# GOLD V2 25C86 frozen same-count condition replay audit-only report",
        "",
        f"Created UTC: {created}",
        f"Status: `{status}`",
        "",
        "## Input inventory",
        md(inv, 30),
        "",
        "## Condition inventory",
        md(condition_inventory, 20),
        "",
        "## Top125 same-count comparison",
        md(compare, 40),
        "",
        "## Decision matrix",
        md(decision, 20),
        "",
        "## Safety",
        "- audit_only: true",
        "- A002 not used",
        "- source recovery not approved",
        "- live/final/external actions remain OFF",
    ])
    (out / "GOLD_V2_25C86_FROZEN_SAME_COUNT_CONDITION_REPLAY_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")

    zip_path = fx_outputs() / "gold_v2_25c86_frozen_same_count_condition_replay_audit_only.zip"
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
