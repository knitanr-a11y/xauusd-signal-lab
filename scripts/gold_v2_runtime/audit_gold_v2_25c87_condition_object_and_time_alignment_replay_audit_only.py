#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""GOLD V2 25C87 condition object and time-alignment replay audit-only.

Tests whether CoreB same_count/source_rule_count can be explained by individual
condition-object hit counts and feature snapshot time offsets.

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

STEP = "25C87_CONDITION_OBJECT_AND_TIME_ALIGNMENT_REPLAY_AUDIT_ONLY"
OUT_DIR_NAME = "gold_v2_25c87_condition_object_and_time_alignment_replay_audit_only"
OFFSETS_MIN = [-1440, -720, -240, -120, -60, -30, -15, 0, 15, 30, 60, 120, 240, 720, 1440]
EXTERNAL_ACTIONS = {"discord_send_allowed": False, "mt5_order_allowed": False, "ai_api_allowed": False, "live_hook_allowed": False}

INPUT_NAMES = [
    "25c86_summary.json",
    "rr125_top_ledgers.csv",
    "gold_v2_13c_coreb_rr125_selected_top_ledgers.csv",
    "gold_v2_coreb_combined_required_feature_snapshot.csv",
    "gold_v2_coreb_combined_selected_conditions.csv",
    "gold_v2_coreb_combined_same_count_conditions.csv",
    "frozen_coreB_rr125_source_rule_conditions_20260603.json",
    "frozen_coreB_same_count_source_universe_20260604.json",
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
                row["row_count"] = len(pd.read_csv(path))
                row["columns"] = ";".join(pd.read_csv(path, nrows=0).columns)
            elif path.suffix.lower() == ".json":
                row["json_keys"] = ";".join(list(read_json(path).keys())[:20])
        rows.append(row)
    return pd.DataFrame(rows)


def normalize_condition_df(df: pd.DataFrame, rule_set: str) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["condition_source", "condition_id", "rule_id", "field", "operator", "value"])
    d = df.rename(columns={"feature": "field", "op": "operator", "threshold": "value"}).copy()
    if "rule_id" not in d.columns:
        d["rule_id"] = [f"{rule_set}_rule_{i:04d}" for i in range(len(d))]
    for col in ["field", "operator", "value"]:
        if col not in d.columns:
            d[col] = ""
    d["condition_source"] = rule_set
    if "condition_index" in d.columns:
        d["condition_id"] = d["rule_id"].astype(str) + "#" + d["condition_index"].astype(str)
    else:
        d["condition_id"] = [f"{rule_set}_cond_{i:04d}" for i in range(len(d))]
    return d[["condition_source", "condition_id", "rule_id", "field", "operator", "value"]].copy()


def json_conditions(obj: Any, source: str) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []

    def walk(x: Any, rid: str | None = None) -> None:
        if isinstance(x, dict):
            nrid = str(x.get("rule_id") or x.get("candidate_id") or rid or "")
            field = x.get("field") or x.get("feature")
            op = x.get("operator") or x.get("op")
            val = x.get("value") or x.get("threshold")
            if field is not None and op is not None and val is not None:
                rows.append({"condition_source": source, "condition_id": f"{source}_cond_{len(rows):04d}", "rule_id": nrid or f"{source}_rule_unknown", "field": field, "operator": op, "value": val})
            for v in x.values():
                if isinstance(v, (list, dict)):
                    walk(v, nrid)
        elif isinstance(x, list):
            for v in x:
                walk(v, rid)

    walk(obj)
    return normalize_condition_df(pd.DataFrame(rows), source)


def condition_pass(row: pd.Series, cond: pd.Series) -> bool:
    field = str(cond["field"])
    op = str(cond["operator"])
    try:
        x = float(row.get(field, math.nan))
        v = float(cond["value"])
    except Exception:
        return False
    if math.isnan(x):
        return False
    if op == ">":
        return x > v
    if op == ">=":
        return x >= v
    if op == "<":
        return x < v
    if op == "<=":
        return x <= v
    if op == "==":
        return x == v
    return False


def object_hit_counts(feat: pd.DataFrame, conds: pd.DataFrame, prefix: str) -> pd.DataFrame:
    if feat.empty or conds.empty:
        return pd.DataFrame()
    time_col = "time" if "time" in feat.columns else "entry_time" if "entry_time" in feat.columns else None
    rows = []
    for idx, frow in feat.iterrows():
        hit = 0
        for _, cond in conds.iterrows():
            if condition_pass(frow, cond):
                hit += 1
        rows.append({"feature_row_index": idx, "time": frow.get(time_col, "") if time_col else "", f"{prefix}_condition_hits": hit, f"{prefix}_condition_total": len(conds)})
    return pd.DataFrame(rows)


def coreb_top(top: pd.DataFrame) -> pd.DataFrame:
    if top.empty:
        return top
    return top[(top["policy"].astype(str).eq("RR125_from_RR1_rules")) & (top["filter"].astype(str).eq("same_count>=15"))].copy()


def offset_compare(top125: pd.DataFrame, counts: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    if top125.empty or counts.empty:
        return pd.DataFrame(), pd.DataFrame()
    fc = counts.copy()
    fc["time_norm"] = pd.to_datetime(fc["time"], errors="coerce").dt.strftime("%Y-%m-%d %H:%M:%S")
    top = top125.copy()
    top["entry_dt"] = pd.to_datetime(top["entry_time"], errors="coerce")
    pred_cols = [c for c in fc.columns if c.endswith("_condition_hits")]
    rows = []
    samples = []
    for offset in OFFSETS_MIN:
        t = top.copy()
        t["join_time_norm"] = (t["entry_dt"] + pd.to_timedelta(offset, unit="m")).dt.strftime("%Y-%m-%d %H:%M:%S")
        joined = t.merge(fc, left_on="join_time_norm", right_on="time_norm", how="left")
        for pred_col in pred_cols:
            for target_col in ["same_count", "source_rule_count"]:
                pred = pd.to_numeric(joined[pred_col], errors="coerce") if pred_col in joined.columns else pd.Series(dtype="float64")
                target = pd.to_numeric(joined[target_col], errors="coerce")
                exact = int((pred == target).sum())
                nonnull = int(pred.notna().sum())
                diff = (pred - target).abs()
                rows.append({"offset_min": offset, "prediction_column": pred_col, "target_column": target_col, "joined_rows": len(joined), "non_null_predictions": nonnull, "exact_rows": exact, "exact_ratio": exact / len(joined) if len(joined) else 0.0, "mae": float(diff.mean()) if diff.notna().any() else None, "status": "FULL" if exact == len(joined) else "PARTIAL_OR_FAIL"})
                if exact > 0:
                    smp = joined.loc[(pred == target), ["dataset", "entry_time", "join_time_norm", "cluster_id", "profit", "same_count", "source_rule_count", pred_col]].head(20).copy()
                    smp["offset_min"] = offset
                    smp["prediction_column"] = pred_col
                    smp["target_column"] = target_col
                    samples.append(smp)
    summary = pd.DataFrame(rows).sort_values(["exact_rows", "non_null_predictions"], ascending=False)
    sample_df = pd.concat(samples, ignore_index=True) if samples else pd.DataFrame()
    return summary, sample_df


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
    s86 = read_json(paths["25c86_summary.json"])
    top125 = coreb_top(read_csv(paths["rr125_top_ledgers.csv"]))
    feat = read_csv(paths["gold_v2_coreb_combined_required_feature_snapshot.csv"])

    conds = []
    conds.append(normalize_condition_df(read_csv(paths["gold_v2_coreb_combined_selected_conditions.csv"]), "selected_csv"))
    conds.append(normalize_condition_df(read_csv(paths["gold_v2_coreb_combined_same_count_conditions.csv"]), "same_count_csv"))
    conds.append(json_conditions(read_json(paths["frozen_coreB_rr125_source_rule_conditions_20260603.json"]), "selected_json"))
    conds.append(json_conditions(read_json(paths["frozen_coreB_same_count_source_universe_20260604.json"]), "same_count_json"))
    condition_inventory = pd.DataFrame([[c.iloc[0]["condition_source"] if not c.empty else "EMPTY", len(c), c["rule_id"].nunique() if not c.empty else 0] for c in conds], columns=["condition_source", "condition_rows", "rule_count"])

    count_frames = []
    for c in conds:
        if not c.empty:
            prefix = str(c.iloc[0]["condition_source"])
            count_frames.append(object_hit_counts(feat, c, prefix))
    if count_frames:
        counts = count_frames[0]
        for extra in count_frames[1:]:
            counts = counts.merge(extra, on=["feature_row_index", "time"], how="outer")
    else:
        counts = pd.DataFrame()

    offset_summary, exact_samples = offset_compare(top125, counts)
    full_match = bool((offset_summary.get("status", pd.Series(dtype=str)).astype(str) == "FULL").any()) if not offset_summary.empty else False
    best_exact = int(offset_summary.iloc[0]["exact_rows"]) if not offset_summary.empty else 0
    best_nonnull = int(offset_summary.iloc[0]["non_null_predictions"]) if not offset_summary.empty else 0
    upstream_ok = s86.get("status") == "FROZEN_SAME_COUNT_CONDITION_REPLAY_NOT_MATCHED_AUDIT_ONLY_LIVE_BLOCKED"
    inputs_ok = bool(inv["exists"].all()) if not inv.empty else False

    if full_match:
        status = "CONDITION_OBJECT_TIME_ALIGNMENT_REPLAY_MATCHED_AUDIT_ONLY_HUMAN_REVIEW_REQUIRED_LIVE_BLOCKED"
        next_step = "HUMAN_REVIEW_CONDITION_OBJECT_ALIGNMENT_BEFORE_ANY_LIVE"
    else:
        status = "CONDITION_OBJECT_TIME_ALIGNMENT_REPLAY_NOT_MATCHED_AUDIT_ONLY_LIVE_BLOCKED"
        next_step = "REVIEW_FEATURE_SNAPSHOT_GRAIN_OR_RECONSTRUCT_FROM_SOURCE_UNIVERSE_RULES"
    if not upstream_ok or not inputs_ok:
        status = "CONDITION_OBJECT_TIME_ALIGNMENT_REPLAY_INPUT_REVIEW_REQUIRED_AUDIT_ONLY"
        next_step = "REVIEW_25C87_INPUTS"

    decision = pd.DataFrame([
        ["upstream_25c86_ok", upstream_ok, True, "PASS" if upstream_ok else "FAIL"],
        ["inputs_present", inputs_ok, True, "PASS" if inputs_ok else "FAIL"],
        ["top125_rows", len(top125), 125, "PASS" if len(top125) == 125 else "FAIL"],
        ["feature_rows", len(feat), ">0", "PASS" if len(feat) > 0 else "FAIL"],
        ["best_exact_rows", best_exact, 125, "PASS" if best_exact == 125 else "BLOCKED"],
        ["best_non_null_predictions", best_nonnull, 125, "PASS" if best_nonnull == 125 else "REVIEW"],
        ["coreb_live_evaluator_allowed", False, False, "PASS"],
        ["a002_used", False, False, "PASS"],
    ], columns=["decision_item", "observed", "required", "status"])

    summary = {"created_utc": created, "step": STEP, "status": status, "audit_only": True, "upstream_25c86_ok": upstream_ok, "inputs_ok": inputs_ok, "top125_rows": int(len(top125)), "feature_rows": int(len(feat)), "best_exact_rows": best_exact, "best_non_null_predictions": best_nonnull, "full_match_found": full_match, "coreb_historical_sot_report_allowed": True, "coreb_live_evaluator_allowed": False, "final_signal_allowed": False, "a002_used": False, "source_recovery_approved": False, "external_actions": {"discord_send_allowed": False, "mt5_order_allowed": False, "ai_api_allowed": False, "live_hook_allowed": False}, "next_recommended_step": next_step}

    inv.to_csv(out / "25c87_input_inventory.csv", index=False, encoding="utf-8-sig")
    condition_inventory.to_csv(out / "25c87_condition_inventory.csv", index=False, encoding="utf-8-sig")
    counts.to_csv(out / "25c87_feature_condition_object_hit_counts.csv", index=False, encoding="utf-8-sig")
    offset_summary.to_csv(out / "25c87_offset_comparison_summary.csv", index=False, encoding="utf-8-sig")
    exact_samples.to_csv(out / "25c87_exact_match_samples.csv", index=False, encoding="utf-8-sig")
    decision.to_csv(out / "25c87_decision_matrix.csv", index=False, encoding="utf-8-sig")
    write_json(out / "25c87_summary.json", summary)

    report = "\n".join(["# GOLD V2 25C87 condition object and time-alignment replay audit-only report", "", f"Created UTC: {created}", f"Status: `{status}`", "", "## Condition inventory", md(condition_inventory), "", "## Offset comparison summary", md(offset_summary, 40), "", "## Decision matrix", md(decision), "", "## Safety", "- audit_only: true", "- A002 not used", "- source recovery not approved", "- live/final/external actions remain OFF"])
    (out / "GOLD_V2_25C87_CONDITION_OBJECT_AND_TIME_ALIGNMENT_REPLAY_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")

    zip_path = fx_outputs() / "gold_v2_25c87_condition_object_and_time_alignment_replay_audit_only.zip"
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
