#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""13D2 audit: MEDIUM TIER2_HVT source definition reconciliation.

Audit-only. 13D outputs are the source of truth. This script does not perform
OHLC rediscovery and does not call AI API, Discord, MT5, or live hooks.

The MT5 Files path can be very long on Windows, so all file I/O uses a Windows
long-path prefix when needed.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

STEP = "13D2_MEDIUM_TIER2_HVT_SOURCE_DEFINITION_RECONCILIATION_AUDIT_ONLY"
OUT_NAME = "gold_v2_13d2_medium_tier2_hvt_source_definition_reconciliation_audit_only"
SRC13D = "gold_v2_13d_medium_feature_arbitration_audit_only"
COMP = "TIER2_HVT"
REPORT_NAME = "GOLD_V2_13D2_MEDIUM_TIER2_HVT_SOURCE_DEFINITION_RECONCILIATION_AUDIT_ONLY_REPORT.md"
EXPECTED = {
    "tier2_source_rows": 31,
    "tier2_final_rows": 13,
    "tier2_source_manifest_match_rows": 19,
    "tier2_source_manifest_mismatch_rows": 12,
    "tier2_final_manifest_match_rows": 2,
    "tier2_final_manifest_mismatch_rows": 11,
}
EXTERNAL = {"discord_send_allowed": False, "mt5_order_allowed": False, "ai_api_allowed": False, "live_hook_allowed": False}
NUMERIC = ["range96", "trend_eff96", "ret96", "tr_mean_32"]
REQ = ["component", "own_manifest_match", "range96", "trend_eff96", "ret96", "tr_mean_32", "regime", "dataset"]


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def fx_outputs() -> Path:
    root = repo_root()
    return (root.parents[1] if len(root.parents) >= 2 else root.parent) / "FX_OUTPUTS"


def long_path(path: Path | str) -> str:
    """Return a filesystem path usable beyond MAX_PATH on Windows."""
    p = Path(path)
    s = str(p.resolve(strict=False))
    if os.name != "nt" or s.startswith("\\\\?\\"):
        return s
    if s.startswith("\\\\"):
        return "\\\\?\\UNC\\" + s.lstrip("\\")
    return "\\\\?\\" + s


def exists(path: Path | str) -> bool:
    return os.path.exists(long_path(path))


def ensure_dir(path: Path) -> None:
    os.makedirs(long_path(path), exist_ok=True)


def out_dir() -> Path:
    p = fx_outputs() / OUT_NAME
    ensure_dir(p)
    return p


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(long_path(path), "rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()


def write_text(path: Path, text: str) -> None:
    ensure_dir(path.parent)
    with open(long_path(path), "w", encoding="utf-8", newline="") as f:
        f.write(text)


def write_csv(df: pd.DataFrame, path: Path) -> None:
    ensure_dir(path.parent)
    df.to_csv(long_path(path), index=False, encoding="utf-8-sig")


def read_csv_path(path: Path) -> pd.DataFrame:
    return pd.read_csv(long_path(path))


def read_json_path(path: Path) -> dict[str, Any]:
    with open(long_path(path), "r", encoding="utf-8") as f:
        return json.load(f)


INPUTS = [
    ("13d_source_rows_with_manifest_match", "gold_v2_13d_medium_source_rows_with_manifest_match.csv", True, SRC13D),
    ("13d_recomputed_final_rows", "gold_v2_13d_medium_recomputed_final_rows.csv", True, SRC13D),
    ("13d_final_sot_rule_summary", "gold_v2_13d_medium_final_sot_rule_summary.csv", True, SRC13D),
    ("13d_rule_manifest_inventory", "gold_v2_13d_medium_rule_manifest_inventory.csv", True, SRC13D),
    ("13d_rule_manifest_coverage", "gold_v2_13d_medium_rule_manifest_coverage.csv", True, SRC13D),
    ("frozen_medium_rules_reference", "frozen_medium_rules_20260603.json", False, None),
    ("final_portfolio_sot_reference", "gold_v2_final_portfolio_2025_2026_sot_ledger.csv", False, "gold_v2_final_portfolio_sot_freeze_audit_only"),
]


def find_input(name: str, folder: str | None = None) -> Path:
    candidates: list[Path] = []
    if folder:
        candidates.append(fx_outputs() / folder / name)
    if name.endswith(".json"):
        candidates.append(repo_root() / "configs" / "gold_v2" / name)
    candidates += [fx_outputs() / name, repo_root() / name]
    for p in candidates:
        if exists(p):
            return p
    try:
        hits = list(fx_outputs().rglob(name))
        if hits:
            return hits[0]
    except OSError:
        pass
    return candidates[0]


def read_csv(name: str, folder: str | None = None) -> pd.DataFrame:
    p = find_input(name, folder)
    if not exists(p):
        raise FileNotFoundError(str(p))
    return read_csv_path(p)


def read_optional_json(name: str, folder: str | None = None) -> dict[str, Any] | None:
    p = find_input(name, folder)
    return read_json_path(p) if exists(p) else None


def to_num(s: Any) -> pd.Series:
    return pd.to_numeric(s if isinstance(s, pd.Series) else pd.Series(s), errors="coerce")


def bools(s: pd.Series) -> pd.Series:
    if s.dtype == bool:
        return s.fillna(False)
    return s.astype(str).str.strip().str.lower().isin(["true", "1", "yes", "y", "t"])


def clean(v: Any) -> Any:
    if isinstance(v, dict):
        return {str(k): clean(x) for k, x in v.items()}
    if isinstance(v, list):
        return [clean(x) for x in v]
    if isinstance(v, tuple):
        return [clean(x) for x in v]
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating, float)):
        if math.isnan(float(v)):
            return None
        if math.isinf(float(v)):
            return "inf" if float(v) > 0 else "-inf"
        return float(v)
    if isinstance(v, pd.Timestamp):
        return v.isoformat()
    try:
        if pd.isna(v):
            return None
    except Exception:
        pass
    return v


def write_json(path: Path, obj: dict[str, Any]) -> None:
    write_text(path, json.dumps(clean(obj), ensure_ascii=False, indent=2, allow_nan=False))


def metrics(s: Any) -> dict[str, Any]:
    vals = to_num(s).dropna().astype(float).to_numpy()
    if len(vals) == 0:
        return {"count": 0, "win_rate_pct": None, "pf": None, "total_r": 0.0, "worst": None, "maxdd": 0.0, "max_loss_streak": 0}
    gw = float(vals[vals > 0].sum())
    gl = float(-vals[vals < 0].sum())
    pf = math.inf if gl == 0 and gw > 0 else (gw / gl if gl > 0 else math.nan)
    eq = np.cumsum(vals)
    dd = np.maximum(np.maximum.accumulate(np.r_[0.0, eq[:-1]]) - eq, 0.0)
    st = ms = 0
    for v in vals:
        if v < 0:
            st += 1
            ms = max(ms, st)
        else:
            st = 0
    return {"count": int(len(vals)), "win_rate_pct": float((vals > 0).mean() * 100), "pf": pf, "total_r": float(vals.sum()), "worst": float(vals.min()), "maxdd": float(dd.max()) if len(dd) else 0.0, "max_loss_streak": int(ms)}


def cell(v: Any) -> str:
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


def md_table(df: pd.DataFrame, cols: list[str] | None = None, n: int = 80) -> str:
    if cols:
        df = df[[c for c in cols if c in df.columns]].copy()
    df = df.head(n)
    if df.empty:
        return "_No rows._"
    lines = ["| " + " | ".join(map(str, df.columns)) + " |", "| " + " | ".join(["---"] * len(df.columns)) + " |"]
    for _, r in df.iterrows():
        lines.append("| " + " | ".join(cell(r[c]) for c in df.columns) + " |")
    return "\n".join(lines)


def input_audit() -> pd.DataFrame:
    rows = []
    for role, name, required, folder in INPUTS:
        p = find_input(name, folder)
        row: dict[str, Any] = {"role": role, "name": name, "required": required, "path": str(p), "exists": exists(p)}
        if exists(p):
            row["sha256"] = sha256_file(p)
            row["bytes"] = os.path.getsize(long_path(p))
            if p.suffix.lower() == ".csv":
                df = read_csv_path(p)
                row["rows"] = int(len(df))
                row["columns"] = int(len(df.columns))
                row["column_names"] = "|".join(map(str, df.columns))
            elif p.suffix.lower() == ".json":
                try:
                    obj = read_json_path(p)
                    row["json_keys"] = "|".join(obj.keys()) if isinstance(obj, dict) else ""
                except Exception as exc:
                    row["json_error"] = str(exc)
        rows.append(row)
    return pd.DataFrame(rows)


def standardize(df: pd.DataFrame, role: str) -> pd.DataFrame:
    d = df.copy()
    if "entry_time" not in d.columns and "top_entry_time" in d.columns:
        d["entry_time"] = d["top_entry_time"]
    if "direction" not in d.columns and "top_direction" in d.columns:
        d["direction"] = d["top_direction"]
    if "dataset_final" not in d.columns:
        d["dataset_final"] = d["dataset"].map({"2025_fold4": "2025", "2026_WF": "2026"}).fillna(d["dataset"].astype(str)) if "dataset" in d.columns else ""
    if "component" not in d.columns and "refined_rule" in d.columns:
        d["component"] = d["refined_rule"]
    d["entry_time_dt"] = pd.to_datetime(d.get("entry_time", pd.Series(pd.NaT, index=d.index)), errors="coerce")
    d["entry_month"] = d["entry_time_dt"].dt.strftime("%Y-%m").fillna("")
    d["own_manifest_match"] = bools(d["own_manifest_match"]) if "own_manifest_match" in d.columns else False
    if "profit_r" not in d.columns:
        pr = pd.Series(np.nan, index=d.index)
        if "selected_profit_r" in d.columns:
            pr = to_num(d["selected_profit_r"])
        if pr.isna().all() and "profit" in d.columns:
            pr = to_num(d["profit"])
        d["profit_r"] = pr
    d["outcome"] = np.select([to_num(d["profit_r"]) > 0, to_num(d["profit_r"]) < 0, to_num(d["profit_r"]).eq(0)], ["WIN", "LOSS", "BREAKEVEN"], default="UNKNOWN")
    d["strategy_id"] = COMP
    if "top_variant" in d.columns:
        d["strategy_id"] = d["strategy_id"].astype(str) + "|" + d["top_variant"].fillna("").astype(str)
    if "top_candidate_id" in d.columns:
        d["strategy_id"] = d["strategy_id"].astype(str) + "|" + d["top_candidate_id"].fillna("").astype(str)
    d["tier2_key"] = d["dataset_final"].astype(str) + "|" + d["entry_time_dt"].astype("int64").astype(str) + "|" + d.get("direction", pd.Series("", index=d.index)).astype(str)
    d["reconciliation_frame_role"] = role
    return d


def missing_fields(df: pd.DataFrame) -> list[str]:
    miss = [c for c in REQ if c not in df.columns]
    if "entry_time" not in df.columns and "top_entry_time" not in df.columns:
        miss.append("entry_time_or_top_entry_time")
    if "direction" not in df.columns and "top_direction" not in df.columns:
        miss.append("direction_or_top_direction")
    if "profit_r" not in df.columns and "selected_profit_r" not in df.columns and "profit" not in df.columns:
        miss.append("profit_r_or_selected_profit_r_or_profit")
    return sorted(set(miss))


def tier2_conditions(inv: pd.DataFrame, manifest: dict[str, Any] | None) -> dict[str, Any]:
    if "rule_name" in inv.columns:
        row = inv[inv["rule_name"].astype(str).eq(COMP)]
        if len(row) and "conditions_json" in row.columns:
            try:
                obj = json.loads(str(row["conditions_json"].iloc[0]))
                if isinstance(obj, dict):
                    return obj
            except Exception:
                pass
        if len(row):
            ignore = {"rule_name", "declared_direction", "conditions_json"}
            return {c: row[c].iloc[0] for c in row.columns if c not in ignore and not pd.isna(row[c].iloc[0])}
    if manifest:
        for r in manifest.get("definition", {}).get("rules", []):
            if r.get("name") == COMP and isinstance(r.get("conditions"), dict):
                return r["conditions"]
    return {}


def eval_cond(row: pd.Series, key: str, expected: Any) -> tuple[bool, str, str, Any]:
    if key.endswith("_min"):
        field, op = key[:-4], ">="
        actual = to_num(pd.Series([row[field]])).iloc[0] if field in row.index else np.nan
        return bool(pd.notna(actual) and float(actual) >= float(expected) - 1e-12), field, op, actual
    if key.endswith("_max"):
        field, op = key[:-4], "<="
        actual = to_num(pd.Series([row[field]])).iloc[0] if field in row.index else np.nan
        return bool(pd.notna(actual) and float(actual) <= float(expected) + 1e-12), field, op, actual
    field, op = key, "=="
    if field not in row.index:
        return False, field, op, "MISSING_FIELD"
    an = to_num(pd.Series([row[field]])).iloc[0]
    en = to_num(pd.Series([expected])).iloc[0]
    if pd.notna(an) and pd.notna(en):
        return bool(abs(float(an) - float(en)) <= 1e-12), field, op, an
    return str(row[field]) == str(expected), field, op, row[field]


def add_diagnostics(df: pd.DataFrame, conds: dict[str, Any]) -> pd.DataFrame:
    d = df.copy()
    failed_sets, failed_counts, diag_json = [], [], []
    for _, row in d.iterrows():
        failed, diags = [], []
        for key, exp in conds.items():
            ok, field, op, actual = eval_cond(row, str(key), exp)
            if not ok:
                failed.append(str(key))
            diags.append({"condition_key": str(key), "field": field, "operator": op, "expected": exp, "actual": clean(actual), "passed": ok})
        failed_sets.append("|".join(failed) if failed else "MANIFEST_MATCH")
        failed_counts.append(len(failed))
        diag_json.append(json.dumps(clean(diags), ensure_ascii=False))
    d["manifest_failed_condition_set"] = failed_sets
    d["manifest_failed_condition_count"] = failed_counts
    d["manifest_condition_diagnostics_json"] = diag_json
    d["rule_eval_match_from_conditions"] = d["manifest_failed_condition_count"].eq(0)
    return d


def ranges(df: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
    rows = []
    cols = [c for c in group_cols if c in df.columns] or ["_all"]
    work = df.copy()
    if cols == ["_all"]:
        work["_all"] = "ALL"
    for keys, g in work.groupby(cols, dropna=False):
        keys = keys if isinstance(keys, tuple) else (keys,)
        base = {c: k for c, k in zip(cols, keys)}
        base.update({"rows": len(g), **metrics(g["profit_r"])})
        for f in [c for c in NUMERIC if c in g.columns]:
            v = to_num(g[f]).dropna()
            row = dict(base, feature=f, non_null=len(v))
            if len(v):
                row.update({"min": float(v.min()), "p10": float(v.quantile(.10)), "median": float(v.median()), "p90": float(v.quantile(.90)), "max": float(v.max()), "mean": float(v.mean())})
            rows.append(row)
    return pd.DataFrame(rows)


def cat_summary(df: pd.DataFrame) -> pd.DataFrame:
    rows, cats = [], [c for c in ["dataset", "dataset_final", "regime", "top_direction", "direction", "entry_month", "top_candidate_id", "top_variant"] if c in df.columns]
    for status, g in df.groupby("own_manifest_match_label", dropna=False):
        for c in cats:
            vc = g[c].fillna("").astype(str).value_counts()
            rows.append({"own_manifest_match_label": status, "feature": c, "distinct_values": len(vc), "top_values": "|".join(f"{k}:{int(v)}" for k, v in vc.head(8).items())})
    return pd.DataFrame(rows)


def variant_candidates(df: pd.DataFrame) -> pd.DataFrame:
    cols = [c for c in ["final_status", "own_manifest_match_label", "manifest_failed_condition_set", "dataset_final", "regime", "top_direction", "top_variant"] if c in df.columns]
    rows = []
    for keys, g in df.groupby(cols, dropna=False):
        keys = keys if isinstance(keys, tuple) else (keys,)
        row = {c: k for c, k in zip(cols, keys)}
        row.update({"rows": len(g), **metrics(g["profit_r"])})
        for f in [c for c in NUMERIC if c in g.columns]:
            v = to_num(g[f]).dropna()
            if len(v):
                row[f"{f}_min"] = float(v.min())
                row[f"{f}_max"] = float(v.max())
                row[f"{f}_median"] = float(v.median())
        row["entry_time_min"] = g["entry_time_dt"].min()
        row["entry_time_max"] = g["entry_time_dt"].max()
        rows.append(row)
    return pd.DataFrame(rows).sort_values(["final_status", "own_manifest_match_label", "rows"], ascending=[True, True, False]) if rows else pd.DataFrame()


def diff_summary(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    m = df[df["own_manifest_match"]]
    x = df[~df["own_manifest_match"]]
    for f in [c for c in NUMERIC if c in df.columns]:
        mv, xv = to_num(m[f]).dropna(), to_num(x[f]).dropna()
        row = {"feature": f, "match_rows": len(mv), "mismatch_rows": len(xv)}
        if len(mv):
            row.update({"match_min": float(mv.min()), "match_median": float(mv.median()), "match_max": float(mv.max())})
        if len(xv):
            row.update({"mismatch_min": float(xv.min()), "mismatch_median": float(xv.median()), "mismatch_max": float(xv.max())})
        if len(mv) and len(xv):
            row["range_overlap"] = not (float(xv.max()) < float(mv.min()) or float(xv.min()) > float(mv.max()))
            row["median_delta_mismatch_minus_match"] = float(xv.median() - mv.median())
        rows.append(row)
    return pd.DataFrame(rows)


def envelope(df: pd.DataFrame) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for f in [c for c in NUMERIC if c in df.columns]:
        v = to_num(df[f]).dropna()
        if len(v):
            out[f"{f}_min"] = float(v.min())
            out[f"{f}_max"] = float(v.max())
    for c in ["regime", "top_direction"]:
        if c in df.columns:
            out[f"{c}_values"] = sorted(df[c].fillna("").astype(str).unique().tolist())
    return out


def blockers(missing: list[str], counts_ok: bool, src_mis: int, fin_mis: int, failed_sets: int) -> pd.DataFrame:
    rows = []
    if missing:
        rows.append(["13D2-B000", "MEDIUM_TIER2_HVT", "HARD", "OPEN", "required source fields", "MISSING_SOURCE_FIELD: " + "|".join(missing)])
    if not counts_ok:
        rows.append(["13D2-B001", "MEDIUM_TIER2_HVT", "HARD", "OPEN", "expected count reproduction", "Stop: TIER2 source/final match/mismatch counts did not reproduce 13D handoff."])
    if src_mis or fin_mis:
        rows.append(["13D2-B002", "MEDIUM_TIER2_HVT", "HARD", "OPEN", "frozen TIER2_HVT manifest mismatch", f"source mismatch={src_mis}; final mismatch={fin_mis}; resolve via 13D3."])
    rows.append(["13D2-B003", "MEDIUM", "HARD", "OPEN", "feature/asof parity", "13E must verify OHLC->feature parity at confirmed M15 close."])
    rows.append(["13D2-B004", "MEDIUM", "HARD", "OPEN", "HIGH arbitration dependency", "CoreA/CoreB arbitration remains unresolved; CoreB historical-only/live-blocked."])
    rows.append(["13D2-B005", "SAFETY", "SAFETY", "OPEN", "external actions", "Keep final_signal_allowed=false, Discord=false, MT5=false, AI=false, live_hook=false."])
    if failed_sets > 1:
        rows.append(["13D2-B007", "MEDIUM_TIER2_HVT", "HARD", "OPEN", "single manifest condition may be insufficient", f"Multiple failed-condition sets detected: {failed_sets}. Review variant split."])
    return pd.DataFrame(rows, columns=["blocker_id", "component", "severity", "status", "blocked_item", "required_resolution"])


def stop_report(out: Path, audit: pd.DataFrame, status: str, block: pd.DataFrame, extra: dict[str, Any]) -> int:
    write_csv(block, out / "gold_v2_13d2_tier2_blockers.csv")
    now = datetime.now(timezone.utc).isoformat()
    write_json(out / "gold_v2_13d2_medium_tier2_hvt_reconciliation_summary.json", {"created_utc": now, "step": STEP, "status": status, "audit_only": True, "final_signal_allowed": False, "step13_allowed": False, "medium_live_evaluator_allowed": False, "external_actions": EXTERNAL, **extra})
    report = ["# GOLD V2 13D2 MEDIUM TIER2_HVT source definition reconciliation audit-only report", "", f"Created UTC: {now}", f"Status: `{status}`", "", "## Final decision", "- 13D2 stopped before live-rule reconciliation.", "- No OHLC rediscovery was performed.", "- Discord, MT5, AI API, and live hook remain disabled.", "", "## Input audit", md_table(audit, ["role", "name", "required", "exists", "rows", "columns", "path"], 30), "", "## Blockers", md_table(block), "", "## Safety", "- final_signal_allowed: false", "- step13_allowed: false", "- medium_live_evaluator_allowed: false", "- Discord/MT5/AI/live_hook: false"]
    write_text(out / REPORT_NAME, "\n".join(report))
    return 2


def main() -> int:
    out = out_dir()
    audit = input_audit()
    write_csv(audit, out / "gold_v2_13d2_input_audit.csv")
    missing_inputs = audit[audit["required"].eq(True) & ~audit["exists"].eq(True)]
    if len(missing_inputs):
        b = blockers([], False, 0, 0, 0)
        b = pd.concat([pd.DataFrame([["13D2-BINPUT", "INPUT", "HARD", "OPEN", "required 13D output files", "Missing: " + "|".join(missing_inputs["role"].astype(str))]], columns=b.columns), b], ignore_index=True)
        return stop_report(out, audit, "MISSING_13D_REQUIRED_INPUT_AUDIT_ONLY", b, {"missing_required_inputs": missing_inputs[["role", "path"]].to_dict("records")})

    source_raw = read_csv("gold_v2_13d_medium_source_rows_with_manifest_match.csv", SRC13D)
    final_raw = read_csv("gold_v2_13d_medium_recomputed_final_rows.csv", SRC13D)
    inv = read_csv("gold_v2_13d_medium_rule_manifest_inventory.csv", SRC13D)
    _final_summary = read_csv("gold_v2_13d_medium_final_sot_rule_summary.csv", SRC13D)
    _coverage = read_csv("gold_v2_13d_medium_rule_manifest_coverage.csv", SRC13D)
    manifest = read_optional_json("frozen_medium_rules_20260603.json")

    missing = missing_fields(source_raw)
    if missing:
        return stop_report(out, audit, "MISSING_SOURCE_FIELD_AUDIT_ONLY", blockers(missing, False, 0, 0, 0), {"missing_source_fields": missing})

    source = standardize(source_raw, "13d_source_rows_with_manifest_match")
    final = standardize(final_raw, "13d_recomputed_final_rows")
    tier = source[source["component"].astype(str).eq(COMP)].copy()
    final_tier = final[final["component"].astype(str).eq(COMP)].copy()
    final_keys = set(final_tier["tier2_key"].astype(str))
    tier["final_retained"] = tier["tier2_key"].astype(str).isin(final_keys)
    tier["final_status"] = np.where(tier["final_retained"], "FINAL_SOT_RETAINED", "DROPPED_BY_MEDIUM_INTERNAL_PRIORITY_OR_HIGH")
    final_tier["final_retained"] = True
    final_tier["final_status"] = "FINAL_SOT_RETAINED"
    tier["own_manifest_match_label"] = np.where(tier["own_manifest_match"], "MANIFEST_MATCH", "MANIFEST_MISMATCH")
    final_tier["own_manifest_match_label"] = np.where(final_tier["own_manifest_match"], "MANIFEST_MATCH", "MANIFEST_MISMATCH")

    conds = tier2_conditions(inv, manifest)
    tier = add_diagnostics(tier, conds)
    final_tier = add_diagnostics(final_tier, conds)

    src_match = tier[tier["own_manifest_match"]].copy()
    src_mis = tier[~tier["own_manifest_match"]].copy()
    fin_match = final_tier[final_tier["own_manifest_match"]].copy()
    fin_mis = final_tier[~final_tier["own_manifest_match"]].copy()

    observed = {
        "tier2_source_rows": len(tier),
        "tier2_final_rows": len(final_tier),
        "tier2_source_manifest_match_rows": len(src_match),
        "tier2_source_manifest_mismatch_rows": len(src_mis),
        "tier2_final_manifest_match_rows": len(fin_match),
        "tier2_final_manifest_mismatch_rows": len(fin_mis),
    }
    count_checks = pd.DataFrame([{"metric": k, "observed": int(v), "expected": int(EXPECTED[k]), "ok": int(v) == int(EXPECTED[k])} for k, v in observed.items()])
    counts_ok = bool(count_checks["ok"].all())
    diag_consistent = int((tier["rule_eval_match_from_conditions"].astype(bool) == tier["own_manifest_match"].astype(bool)).sum())
    failed_sets = int(src_mis["manifest_failed_condition_set"].nunique()) if len(src_mis) else 0

    write_csv(tier, out / "gold_v2_13d2_tier2_source_rows.csv")
    write_csv(final_tier, out / "gold_v2_13d2_tier2_final_sot_rows.csv")
    write_csv(src_match, out / "gold_v2_13d2_tier2_manifest_match_rows.csv")
    write_csv(src_mis, out / "gold_v2_13d2_tier2_manifest_mismatch_rows.csv")
    write_csv(fin_mis, out / "gold_v2_13d2_tier2_final_manifest_mismatch_rows.csv")
    write_csv(count_checks, out / "gold_v2_13d2_tier2_expected_count_checks.csv")
    r_match = ranges(tier, ["own_manifest_match_label"])
    r_final = ranges(tier, ["final_status", "own_manifest_match_label"])
    vc = variant_candidates(tier)
    ds = diff_summary(tier)
    write_csv(r_match, out / "gold_v2_13d2_tier2_feature_range_by_match_status.csv")
    write_csv(r_final, out / "gold_v2_13d2_tier2_feature_range_by_final_status.csv")
    write_csv(cat_summary(tier), out / "gold_v2_13d2_tier2_categorical_summary_by_match_status.csv")
    write_csv(vc, out / "gold_v2_13d2_tier2_variant_candidate_conditions.csv")
    write_csv(ds, out / "gold_v2_13d2_tier2_match_vs_mismatch_diff_summary.csv")

    ex_cols = [c for c in ["dataset", "dataset_final", "entry_time", "direction", "top_direction", "strategy_id", "top_candidate_id", "top_variant", "range96", "trend_eff96", "ret96", "tr_mean_32", "regime", "profit_r", "outcome", "final_status", "own_manifest_match", "manifest_failed_condition_set", "manifest_condition_diagnostics_json"] if c in src_mis.columns]
    write_csv(src_mis[ex_cols], out / "gold_v2_13d2_tier2_mismatch_examples.csv")

    if not counts_ok:
        next_step = "STOP_REVIEW_13D_OUTPUTS_BEFORE_13D3"
        status = "TIER2_HVT_EXPECTED_COUNT_MISMATCH_STOPPED_AUDIT_ONLY"
    elif failed_sets <= 1:
        next_step = "13D3_FREEZE_MEDIUM_TIER2_HVT_RECONCILED_RULE_AUDIT_ONLY"
        status = "TIER2_HVT_RECONCILIATION_SINGLE_PATCH_PREVIEW_POSSIBLE_NOT_LIVE_AUDIT_ONLY"
    else:
        next_step = "13D3_SPLIT_MEDIUM_TIER2_HVT_VARIANTS_AUDIT_ONLY"
        status = "TIER2_HVT_RECONCILIATION_VARIANT_SPLIT_REVIEW_REQUIRED_AUDIT_ONLY"

    decision = pd.DataFrame([
        ["13D2-C001", "source TIER2_HVT rows", observed["tier2_source_rows"], EXPECTED["tier2_source_rows"], "PASS" if observed["tier2_source_rows"] == EXPECTED["tier2_source_rows"] else "STOP", "Required SOT count reproduction."],
        ["13D2-C002", "final TIER2_HVT rows", observed["tier2_final_rows"], EXPECTED["tier2_final_rows"], "PASS" if observed["tier2_final_rows"] == EXPECTED["tier2_final_rows"] else "STOP", "Required final SOT count reproduction."],
        ["13D2-C003", "manifest mismatch decomposition", f"source_mismatch={observed['tier2_source_manifest_mismatch_rows']}; final_mismatch={observed['tier2_final_manifest_mismatch_rows']}", "source_mismatch=12; final_mismatch=11", "PASS" if counts_ok else "STOP", "Counts must match 13D handoff exactly."],
        ["13D2-C004", "rule condition diagnostic consistency", diag_consistent, len(tier), "PASS" if diag_consistent == len(tier) else "REVIEW", "Diagnostics should agree with 13D own_manifest_match."],
        ["13D2-C005", "TIER2 definition decision", f"unique_failed_condition_sets={failed_sets}", "0/1/split review", "REVIEW", "VARIANT_SPLIT_LIKELY_OR_REQUIRED" if failed_sets > 1 else "SINGLE_RULE_PATCH_PREVIEW_POSSIBLE_BUT_NOT_LIVE_APPROVED"],
        ["13D2-C006", "live evaluator permission", "false", "false", "PASS", "13D2 is audit-only."],
        ["13D2-C007", "next recommended step", next_step, "13D3 branch or STOP", "INFO", next_step],
    ], columns=["check_id", "check", "observed", "expected", "status", "decision"])
    write_csv(decision, out / "gold_v2_13d2_tier2_reconciliation_decision_matrix.csv")
    block = blockers([], counts_ok, len(src_mis), len(fin_mis), failed_sets)
    write_csv(block, out / "gold_v2_13d2_tier2_blockers.csv")

    patch_preview = {
        "audit_only": True,
        "patch_applies_to_file": "configs/gold_v2/frozen_medium_rules_20260603.json",
        "patch_is_not_written": True,
        "original_tier2_conditions": conds,
        "source_31_envelope_preview": envelope(tier),
        "final_13_envelope_preview": envelope(final_tier),
        "mismatch_12_envelope_preview": envelope(src_mis),
        "final_mismatch_11_envelope_preview": envelope(fin_mis),
        "variant_previews_by_failed_condition_set": [
            {"variant_key": str(k), "source_rows": len(g), "final_rows": int(g["final_retained"].sum()), "envelope_conditions": envelope(g), "audit_note": "Not approved for live use without 13D3 replay and 13E feature/asof parity."}
            for k, g in src_mis.groupby("manifest_failed_condition_set", dropna=False)
        ],
        "hard_warnings": ["Audit-only preview, not a frozen live rule.", "No OHLC feature/asof parity is proven in 13D2.", "Discord, MT5, AI API, and live hook remain disabled."],
    }
    write_json(out / "gold_v2_13d2_tier2_candidate_rule_manifest_patch_preview.json", patch_preview)

    now = datetime.now(timezone.utc).isoformat()
    summary = {
        "created_utc": now,
        "step": STEP,
        "status": status,
        "audit_only": True,
        "source_of_truth": "13D output CSVs; no OHLC rediscovery",
        "expected_counts": EXPECTED,
        "observed_counts": observed,
        "counts_ok": counts_ok,
        "rule_eval_consistent_rows": diag_consistent,
        "rule_eval_consistent_with_13d_manifest_flag": diag_consistent == len(tier),
        "unique_failed_condition_sets": failed_sets,
        "tier2_source_metrics": metrics(tier["profit_r"]),
        "tier2_final_metrics": metrics(final_tier["profit_r"]),
        "original_tier2_conditions": conds,
        "next_recommended_step": next_step,
        "medium_live_evaluator_allowed": False,
        "final_signal_allowed": False,
        "step13_allowed": False,
        "external_actions": EXTERNAL,
    }
    write_json(out / "gold_v2_13d2_medium_tier2_hvt_reconciliation_summary.json", summary)

    report = [
        "# GOLD V2 13D2 MEDIUM TIER2_HVT source definition reconciliation audit-only report", "",
        f"Created UTC: {now}", f"Status: `{status}`", "",
        "## Final decision",
        "- 13D2 uses 13D source/final ledgers as source of truth.",
        "- No OHLC rediscovery or approximate live rule was implemented.",
        "- TIER2_HVT source/final rows are split by 13D `own_manifest_match` and failed-condition sets.",
        f"- Next recommended step: `{next_step}`",
        "- MEDIUM live evaluator remains blocked until 13D3 and 13E pass.",
        "- Discord, MT5, AI API, and live hook remain disabled.", "",
        "## Expected count checks", md_table(count_checks), "",
        "## Source/final metrics", md_table(pd.DataFrame([
            {"scope": "TIER2_SOURCE_31", **metrics(tier["profit_r"])},
            {"scope": "TIER2_FINAL_13", **metrics(final_tier["profit_r"])},
            {"scope": "TIER2_SOURCE_MANIFEST_MATCH", **metrics(src_match["profit_r"])},
            {"scope": "TIER2_SOURCE_MANIFEST_MISMATCH", **metrics(src_mis["profit_r"])},
            {"scope": "TIER2_FINAL_MANIFEST_MISMATCH", **metrics(fin_mis["profit_r"])},
        ])), "",
        "## Manifest condition diagnostics",
        f"- original condition keys: `{', '.join(map(str, conds.keys())) if conds else 'NOT_FOUND'}`",
        f"- rows where local diagnostics agree with 13D own_manifest_match: {diag_consistent} / {len(tier)}",
        f"- unique failed-condition sets among source mismatches: {failed_sets}", "",
        "## Feature ranges by manifest status", md_table(r_match, ["own_manifest_match_label", "feature", "rows", "non_null", "min", "p10", "median", "p90", "max", "mean"], 80), "",
        "## Feature ranges by final status", md_table(r_final, ["final_status", "own_manifest_match_label", "feature", "rows", "non_null", "min", "median", "max"], 120), "",
        "## Variant candidate conditions", md_table(vc, n=120), "",
        "## Reconciliation decision matrix", md_table(decision, n=30), "",
        "## Blockers", md_table(block, n=40), "",
        "## Safety",
        "- audit_only: true", "- medium_live_evaluator_allowed: false", "- final_signal_allowed: false", "- step13_allowed: false", "- Discord/MT5/AI/live_hook: false", "",
        "## First files to inspect",
        "- `gold_v2_13d2_medium_tier2_hvt_reconciliation_summary.json`",
        "- `gold_v2_13d2_tier2_expected_count_checks.csv`",
        "- `gold_v2_13d2_tier2_manifest_mismatch_rows.csv`",
        "- `gold_v2_13d2_tier2_variant_candidate_conditions.csv`",
        "- `gold_v2_13d2_tier2_reconciliation_decision_matrix.csv`", "",
    ]
    write_text(out / REPORT_NAME, "\n".join(report))

    zip_path = fx_outputs() / "gold_v2_13d2_medium_tier2_hvt_source_definition_reconciliation_audit.zip"
    if exists(zip_path):
        os.remove(long_path(zip_path))
    with zipfile.ZipFile(long_path(zip_path), "w", zipfile.ZIP_DEFLATED) as z:
        for p in out.iterdir():
            z.write(long_path(p), arcname=p.name)

    print(json.dumps(clean({"status": status, "output_dir": str(out), "zip": str(zip_path), **observed, "next_recommended_step": next_step, "audit_only": True, "external_actions": EXTERNAL}), ensure_ascii=False, indent=2, allow_nan=False))
    return 0 if counts_ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
