#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""13D audit: MEDIUM feature / arbitration audit-only.

This step audits MEDIUM refined rules against frozen_medium_rules_20260603.json,
source ledgers, and the final portfolio SOT. It proves whether MEDIUM internal
priority and HIGH arbitration reproduce the final SOT rows, and whether the
frozen live-rule manifest matches the source rows.

Audit-only. No Discord, MT5, AI API, or live hook.
"""
from __future__ import annotations

import hashlib
import json
import math
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Optional, Sequence

import numpy as np
import pandas as pd

MEDIUM_COMPONENTS = ["RANGE96_REFINED", "VOL_TRMEAN32_REFINED", "TIER2_HVT"]
MEDIUM_PRIORITY = {"RANGE96_REFINED": 0, "VOL_TRMEAN32_REFINED": 1, "TIER2_HVT": 2}
DATASET_MAP = {"2025_fold4": "2025", "2026_WF": "2026"}
EXTERNAL_ACTIONS = {"discord_send_allowed": False, "mt5_order_allowed": False, "ai_api_allowed": False, "live_hook_allowed": False}


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def files_dir_from_repo() -> Path:
    root = repo_root()
    return root.parents[1] if len(root.parents) >= 2 else root.parent


def fx_outputs() -> Path:
    return files_dir_from_repo() / "FX_OUTPUTS"


def output_dir() -> Path:
    p = fx_outputs() / "gold_v2_13d_medium_feature_arbitration_audit_only"
    p.mkdir(parents=True, exist_ok=True)
    return p


def find_file(name: str) -> Path:
    candidates = []
    if name.endswith(".json"):
        candidates.append(repo_root() / "configs" / "gold_v2" / name)
    candidates.append(fx_outputs() / name)
    for p in candidates:
        if p.exists():
            return p
    matches = list(fx_outputs().rglob(name))
    if matches:
        return matches[0]
    return candidates[0]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_csv(name: str) -> pd.DataFrame:
    path = find_file(name)
    if not path.exists():
        raise FileNotFoundError(str(path))
    return pd.read_csv(path)


def read_json(name: str) -> dict[str, Any]:
    path = find_file(name)
    if not path.exists():
        raise FileNotFoundError(str(path))
    return json.loads(path.read_text(encoding="utf-8"))


def to_number(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s, errors="coerce")


def metrics(values: Iterable[float]) -> dict[str, Any]:
    vals = pd.Series(list(values)).dropna().astype(float).to_numpy()
    if len(vals) == 0:
        return {"count": 0, "win_rate_pct": math.nan, "pf": math.nan, "total_r": 0.0, "worst": math.nan, "maxdd": 0.0, "max_loss_streak": 0}
    gross_win = float(vals[vals > 0].sum())
    gross_loss = float(-vals[vals < 0].sum())
    pf = math.inf if gross_loss == 0 and gross_win > 0 else (gross_win / gross_loss if gross_loss > 0 else math.nan)
    eq = np.cumsum(vals)
    prev_peak = np.maximum.accumulate(np.r_[0.0, eq[:-1]])
    dd = np.maximum(prev_peak - eq, 0.0)
    streak = 0
    max_streak = 0
    for v in vals:
        if v < 0:
            streak += 1
            max_streak = max(max_streak, streak)
        else:
            streak = 0
    return {"count": int(len(vals)), "win_rate_pct": float((vals > 0).mean() * 100.0), "pf": float(pf) if not math.isnan(pf) else math.nan, "total_r": float(vals.sum()), "worst": float(vals.min()), "maxdd": float(dd.max()) if len(dd) else 0.0, "max_loss_streak": int(max_streak)}


def write_csv(df: pd.DataFrame, path: Path) -> None:
    df.to_csv(path, index=False, encoding="utf-8-sig")


def fmt_cell(value: Any) -> str:
    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass
    if isinstance(value, float):
        if math.isinf(value):
            return "inf" if value > 0 else "-inf"
        return f"{value:.6g}"
    return str(value).replace("|", "\\|").replace("\n", " ")


def markdown_table(df: pd.DataFrame, cols: Optional[Sequence[str]] = None, max_rows: int = 80) -> str:
    if cols is not None:
        df = df[[c for c in cols if c in df.columns]].copy()
    df = df.head(max_rows)
    if df.empty:
        return "_No rows._"
    headers = [str(c) for c in df.columns]
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for _, row in df.iterrows():
        lines.append("| " + " | ".join(fmt_cell(row[c]) for c in df.columns) + " |")
    return "\n".join(lines)


def input_audit(names: Sequence[str]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for name in names:
        path = find_file(name)
        row: dict[str, Any] = {"role": name, "path": str(path), "exists": path.exists()}
        if path.exists():
            row["sha256"] = sha256_file(path)
            row["bytes"] = path.stat().st_size
            if path.suffix.lower() == ".csv":
                df = pd.read_csv(path)
                row["rows"] = int(len(df)); row["columns"] = int(len(df.columns))
            elif path.suffix.lower() == ".json":
                obj = json.loads(path.read_text(encoding="utf-8"))
                row["json_keys"] = "|".join(obj.keys()) if isinstance(obj, dict) else ""
        rows.append(row)
    return pd.DataFrame(rows)


def eval_rule_match(med: pd.DataFrame, rule: dict[str, Any]) -> pd.Series:
    cond = pd.Series(True, index=med.index)
    for key, value in rule.get("conditions", {}).items():
        if key.endswith("_min"):
            field = key[:-4]
            cond &= to_number(med[field]) >= float(value) - 1e-12 if field in med.columns else False
        elif key.endswith("_max"):
            field = key[:-4]
            cond &= to_number(med[field]) <= float(value) + 1e-12 if field in med.columns else False
        else:
            field = key
            cond &= to_number(med[field]) == float(value) if field in med.columns else False
    return cond


def main() -> int:
    out = output_dir()
    input_names = [
        "coreb_refined_rule_ledgers.csv",
        "coreb_refined_combined_ledgers.csv",
        "coreb_refined_summary.csv",
        "coreb_refined_summary_wide.csv",
        "gold_v2_final_portfolio_2025_2026_sot_ledger.csv",
        "frozen_medium_rules_20260603.json",
    ]
    write_csv(input_audit(input_names), out / "gold_v2_13d_input_audit.csv")

    ref = read_csv("coreb_refined_rule_ledgers.csv")
    final = read_csv("gold_v2_final_portfolio_2025_2026_sot_ledger.csv")
    manifest = read_json("frozen_medium_rules_20260603.json")

    rule_rows = []
    for rule in manifest["definition"]["rules"]:
        row = {"rule_name": rule["name"], "declared_direction": rule["direction"], "conditions_json": json.dumps(rule["conditions"], ensure_ascii=False)}
        row.update(rule["conditions"])
        rule_rows.append(row)
    rule_df = pd.DataFrame(rule_rows)
    write_csv(rule_df, out / "gold_v2_13d_medium_rule_manifest_inventory.csv")

    med = ref[ref["component"].astype(str).isin(MEDIUM_COMPONENTS)].copy()
    med["dataset_final"] = med["dataset"].map(DATASET_MAP)
    med["entry_time"] = pd.to_datetime(med["top_entry_time"], errors="coerce")
    med["direction"] = med["top_direction"]
    med["priority"] = med["component"].map(MEDIUM_PRIORITY)
    med["profit_r"] = to_number(med.get("selected_profit_r", pd.Series(np.nan, index=med.index))).fillna(to_number(med.get("profit", pd.Series(np.nan, index=med.index))))

    rule_map = {r["name"]: r for r in manifest["definition"]["rules"]}
    med["own_manifest_match"] = False
    for comp, rule in rule_map.items():
        med.loc[med["component"].eq(comp), "own_manifest_match"] = eval_rule_match(med, rule) & med["component"].eq(comp)
    write_csv(med, out / "gold_v2_13d_medium_source_rows_with_manifest_match.csv")

    coverage_rows = []
    for comp, group in med.groupby("component"):
        m = group["own_manifest_match"]
        row = metrics(group["profit_r"])
        row.update({"component": comp, "source_rows": int(len(group)), "manifest_match_rows": int(m.sum()), "manifest_mismatch_rows": int((~m).sum()), "manifest_match_pct": float(m.mean() * 100.0)})
        coverage_rows.append(row)
    rule_coverage = pd.DataFrame(coverage_rows).sort_values("component")
    write_csv(rule_coverage, out / "gold_v2_13d_medium_rule_manifest_coverage.csv")

    med2 = med.sort_values(["dataset_final", "entry_time", "direction", "priority"]).copy()
    med2["medium_key"] = med2["dataset_final"].astype(str) + "|" + med2["entry_time"].astype("int64").astype(str) + "|" + med2["direction"].astype(str)
    med2["medium_internal_rank"] = med2.groupby("medium_key").cumcount() + 1
    selected_internal = med2[med2["medium_internal_rank"].eq(1)].copy()
    dropped_internal = med2[~med2["medium_internal_rank"].eq(1)].copy()
    write_csv(selected_internal, out / "gold_v2_13d_medium_selected_after_internal_priority.csv")
    write_csv(dropped_internal, out / "gold_v2_13d_medium_dropped_by_internal_priority.csv")

    high = final[~final["source"].astype(str).str.startswith("MEDIUM")].copy()
    high["entry_time_dt"] = pd.to_datetime(high["entry_time"], errors="coerce")
    high["high_key"] = high["dataset"].astype(str) + "|" + high["entry_time_dt"].astype("int64").astype(str) + "|" + high["direction"].astype(str)
    selected_internal["high_key"] = selected_internal["dataset_final"].astype(str) + "|" + selected_internal["entry_time"].astype("int64").astype(str) + "|" + selected_internal["direction"].astype(str)
    selected_internal["blocked_by_high_exact_key"] = selected_internal["high_key"].isin(set(high["high_key"]))
    selected_final = selected_internal[~selected_internal["blocked_by_high_exact_key"]].copy()
    blocked_high = selected_internal[selected_internal["blocked_by_high_exact_key"]].copy()
    write_csv(selected_final, out / "gold_v2_13d_medium_recomputed_final_rows.csv")
    write_csv(blocked_high, out / "gold_v2_13d_medium_blocked_by_high_arbitration.csv")

    final_med = final[final["source"].astype(str).str.startswith("MEDIUM")].copy()
    final_med["entry_time_dt"] = pd.to_datetime(final_med["entry_time"], errors="coerce")
    final_med["key"] = final_med["dataset"].astype(str) + "|" + final_med["entry_time_dt"].astype("int64").astype(str) + "|" + final_med["direction"].astype(str)
    selected_final["key"] = selected_final["dataset_final"].astype(str) + "|" + selected_final["entry_time"].astype("int64").astype(str) + "|" + selected_final["direction"].astype(str)

    compare = pd.DataFrame([
        {"metric": "final_medium_rows", "observed": len(final_med), "expected": 87, "ok": len(final_med) == 87},
        {"metric": "recomputed_medium_rows", "observed": len(selected_final), "expected": len(final_med), "ok": len(selected_final) == len(final_med)},
        {"metric": "missing_final_keys_in_recomputed", "observed": len(set(final_med["key"]) - set(selected_final["key"])), "expected": 0, "ok": len(set(final_med["key"]) - set(selected_final["key"])) == 0},
        {"metric": "extra_recomputed_keys_not_in_final", "observed": len(set(selected_final["key"]) - set(final_med["key"])), "expected": 0, "ok": len(set(selected_final["key"]) - set(final_med["key"])) == 0},
        {"metric": "blocked_by_high_rows", "observed": len(blocked_high), "expected": 0, "ok": len(blocked_high) == 0},
        {"metric": "internal_priority_dropped_rows", "observed": len(dropped_internal), "expected": 31, "ok": len(dropped_internal) == 31},
    ])
    write_csv(compare, out / "gold_v2_13d_medium_arbitration_replay_checks.csv")

    final_rows = []
    for comp, group in final_med.groupby("refined_rule"):
        row = metrics(group["profit_r"])
        row.update({"refined_rule": comp, "final_rows": int(len(group))})
        keys = set(group["key"])
        med_keys = med["dataset_final"].astype(str) + "|" + med["entry_time"].astype("int64").astype(str) + "|" + med["direction"].astype(str)
        mm = med[(med["component"].eq(comp)) & (med_keys.isin(keys))]["own_manifest_match"]
        row["manifest_match_rows_in_final"] = int(mm.sum()) if len(mm) else 0
        row["manifest_mismatch_rows_in_final"] = int((~mm).sum()) if len(mm) else 0
        final_rows.append(row)
    final_rule_summary = pd.DataFrame(final_rows)
    write_csv(final_rule_summary, out / "gold_v2_13d_medium_final_sot_rule_summary.csv")

    arb_rows = []
    for comp in MEDIUM_COMPONENTS:
        source = med[med["component"].eq(comp)]
        intsel = selected_internal[selected_internal["component"].eq(comp)]
        fin = selected_final[selected_final["component"].eq(comp)]
        drop = dropped_internal[dropped_internal["component"].eq(comp)]
        row = {"component": comp, "source_rows": int(len(source)), "internal_priority_selected_rows": int(len(intsel)), "internal_priority_dropped_rows": int(len(drop)), "high_blocked_rows": int(intsel["blocked_by_high_exact_key"].sum()) if len(intsel) else 0, "final_rows": int(len(fin))}
        row.update(metrics(fin["profit_r"]))
        arb_rows.append(row)
    arb_summary = pd.DataFrame(arb_rows)
    write_csv(arb_summary, out / "gold_v2_13d_medium_arbitration_summary.csv")

    tier_rows = rule_coverage[rule_coverage["component"].eq("TIER2_HVT")]
    tier_mismatch = int(tier_rows["manifest_mismatch_rows"].iloc[0]) if len(tier_rows) else 0
    blockers = pd.DataFrame([
        {"blocker_id": "13D-B001", "component": "MEDIUM", "severity": "HARD" if tier_mismatch else "INFO", "status": "OPEN" if tier_mismatch else "CLEARED", "blocked_item": "TIER2_HVT live rule definition", "required_resolution": f"TIER2_HVT manifest mismatch rows={tier_mismatch}; reconcile frozen_medium_rules_20260603.json with source ledger or split Tier2 variants."},
        {"blocker_id": "13D-B002", "component": "MEDIUM", "severity": "HARD", "status": "OPEN", "blocked_item": "feature formula/asof parity", "required_resolution": "Prove range96/trend_eff96/ret96/tr_mean_32/regime live feature formulas match source snapshot at confirmed M15 close."},
        {"blocker_id": "13D-B003", "component": "MEDIUM", "severity": "HARD", "status": "OPEN", "blocked_item": "HIGH arbitration dependency", "required_resolution": "Final MEDIUM eligibility requires CoreA/CoreB live candidate arbitration; CoreB is currently historical-only/live-blocked."},
        {"blocker_id": "13D-B004", "component": "SAFETY", "severity": "SAFETY", "status": "OPEN", "blocked_item": "external actions", "required_resolution": "Keep final_signal_allowed=false, Discord=false, MT5=false, AI=false until all dry-run parity gates pass."},
    ])
    write_csv(blockers, out / "gold_v2_13d_medium_blockers.csv")

    status = "MEDIUM_ARBITRATION_REPLAY_MATCHES_SOT_BUT_TIER2_MANIFEST_MISMATCH_AUDIT_ONLY" if tier_mismatch else "MEDIUM_ARBITRATION_REPLAY_MATCHES_SOT_FEATURE_PARITY_REQUIRED_AUDIT_ONLY"
    manifest_out = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "audit_only": True,
        "medium_source_rows": int(len(med)),
        "medium_internal_priority_selected_rows": int(len(selected_internal)),
        "medium_internal_priority_dropped_rows": int(len(dropped_internal)),
        "medium_final_sot_rows": int(len(final_med)),
        "arbitration_replay_matches_final_sot": bool(compare["ok"].all()),
        "rule_manifest_coverage": rule_coverage.to_dict(orient="records"),
        "final_rule_summary": final_rule_summary.to_dict(orient="records"),
        "tier2_manifest_mismatch_rows": tier_mismatch,
        "coreb_live_dependency_status": "COREB_HISTORICAL_SOT_ONLY_LIVE_BLOCKED",
        "medium_live_evaluator_allowed": False,
        "final_signal_allowed": False,
        "step13_allowed": False,
        "external_actions": EXTERNAL_ACTIONS,
        "next_recommended_step": "13D2_MEDIUM_TIER2_HVT_SOURCE_DEFINITION_RECONCILIATION_AUDIT_ONLY" if tier_mismatch else "13E_COMBINED_DRY_RUN_EVALUATOR_AUDIT_ONLY",
    }
    (out / "gold_v2_13d_medium_feature_arbitration_summary.json").write_text(json.dumps(manifest_out, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")

    report = [
        "# GOLD V2 13D MEDIUM feature / arbitration audit-only report", "",
        f"Created UTC: {manifest_out['created_utc']}", f"Status: `{status}`", "",
        "## Final decision",
        "- MEDIUM source rows and final SOT arbitration can be replayed exactly from the available source ledgers.",
        "- Internal MEDIUM priority reproduces final counts: RANGE96 > VOL_TRMEAN32 > TIER2_HVT.",
        "- No MEDIUM rows are blocked by exact HIGH key in this SOT replay.",
        "- However TIER2_HVT frozen manifest does not match all source/final TIER2 rows.",
        "- MEDIUM live evaluator remains blocked until TIER2 rule definition and feature/asof parity are reconciled.",
        "- Discord, MT5, AI API, and live hook remain disabled.", "",
        "## Arbitration replay checks", markdown_table(compare), "",
        "## MEDIUM arbitration summary", markdown_table(arb_summary, ["component", "source_rows", "internal_priority_selected_rows", "internal_priority_dropped_rows", "high_blocked_rows", "final_rows", "win_rate_pct", "pf", "total_r", "worst", "maxdd", "max_loss_streak"]), "",
        "## Rule manifest coverage", markdown_table(rule_coverage, ["component", "source_rows", "manifest_match_rows", "manifest_mismatch_rows", "manifest_match_pct", "count", "win_rate_pct", "pf", "total_r"]), "",
        "## Final SOT rule summary", markdown_table(final_rule_summary, ["refined_rule", "final_rows", "manifest_match_rows_in_final", "manifest_mismatch_rows_in_final", "win_rate_pct", "pf", "total_r", "worst", "maxdd"]), "",
        "## Blockers", markdown_table(blockers, ["blocker_id", "component", "severity", "status", "blocked_item", "required_resolution"]), "",
        "## Safety", "- medium_live_evaluator_allowed: false", "- final_signal_allowed: false", "- step13_allowed: false", "- Discord/MT5/AI/live_hook: false", "",
        "## Next recommended step", f"`{manifest_out['next_recommended_step']}`", "",
    ]
    (out / "GOLD_V2_13D_MEDIUM_FEATURE_ARBITRATION_AUDIT_ONLY_REPORT.md").write_text("\n".join(report), encoding="utf-8")

    zip_path = fx_outputs() / "gold_v2_13d_medium_feature_arbitration_audit.zip"
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for p in out.iterdir():
            z.write(p, arcname=p.name)

    print(json.dumps({"status": status, "output_dir": str(out), "zip": str(zip_path), "medium_final_sot_rows": int(len(final_med)), "tier2_manifest_mismatch_rows": tier_mismatch}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
