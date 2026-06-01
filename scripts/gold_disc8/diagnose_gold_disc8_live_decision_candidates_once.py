#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""One-shot diagnostics for GOLD DISC8 live decision audit candidates.

This script does NOT call OpenAI, send Discord, or place MT5 orders.

It imports the common live decision audit module and reuses its feature loading,
manifest parsing, and strategy condition evaluation. It adds diagnostic outputs:
- scanned/fresh/stale row counts
- per-strategy maximum matched condition count
- near-miss rows
- missing/null feature counts

Use this when the forever loop reports candidates_detected=0.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]
for p in [SCRIPT_DIR, REPO_ROOT]:
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import run_gold_disc8_live_decision_audit_forever_aligned as core  # noqa: E402

DEFAULT_OUT_DIR = Path("data/runtime_logs/gold_disc8_live_decision_audit/latest")

STRATEGY_DIAG_COLUMNS = [
    "strategy_id", "direction", "condition_count", "attempt_rows", "fresh_attempt_rows",
    "stale_suppressed_rows", "full_match_rows_fresh", "full_match_rows_ignore_age",
    "max_matched_conditions_fresh", "max_matched_conditions_ignore_age",
    "nearest_entry_time", "nearest_age_minutes", "nearest_matched_conditions", "nearest_failed_conditions",
    "nearest_missing_features", "all_condition_features",
]

NEAR_MISS_COLUMNS = [
    "rank", "strategy_id", "direction", "entry_time", "age_minutes", "is_fresh",
    "matched_count", "failed_count", "condition_count", "matched_conditions", "failed_conditions", "missing_features",
]

FEATURE_NULL_COLUMNS = ["feature", "total_rows", "fresh_rows", "null_rows", "fresh_null_rows", "null_ratio", "fresh_null_ratio"]


def windows_long_path(path: str | Path) -> str:
    p = Path(path)
    if os.name != "nt":
        return str(p)
    text = str(p.resolve())
    if text.startswith("\\\\?\\"):
        return text
    if text.startswith("\\\\"):
        return "\\\\?\\UNC\\" + text.lstrip("\\")
    return "\\\\?\\" + text


def resolve_repo_path(path: str | Path) -> Path:
    p = Path(path)
    return p if p.is_absolute() else REPO_ROOT / p


def mkdirp(path: str | Path) -> None:
    Path(windows_long_path(path)).mkdir(parents=True, exist_ok=True)


def write_json(path: Path, obj: dict[str, Any]) -> None:
    mkdirp(path.parent)
    with open(windows_long_path(path), "w", encoding="utf-8", newline="") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2, sort_keys=True, default=str)


def write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    mkdirp(path.parent)
    with open(windows_long_path(path), "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({col: row.get(col, "") for col in columns})


def clean(value: Any, default: str = "") -> str:
    return core.clean(value, default)


def feature_value_missing(row: pd.Series, feature: str) -> bool:
    value = core.get_feature(row, feature)
    return core.as_float(value) is None


def missing_features(row: pd.Series, strategy: dict[str, Any]) -> list[str]:
    out = []
    for cond in strategy.get("conditions", []):
        if feature_value_missing(row, cond.feature):
            out.append(cond.feature)
    return sorted(set(out))


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="One-shot diagnostics for GOLD DISC8 live decision candidates.")
    p.add_argument("--csv-dir", type=Path, default=core.DEFAULT_MQL5_FILES_DIR)
    p.add_argument("--manifest-json", type=Path, default=core.DEFAULT_MANIFEST_JSON)
    p.add_argument("--gate-rules-json", type=Path, default=core.DEFAULT_GATE_RULES_JSON)
    p.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    p.add_argument("--scan-recent-bars", type=int, default=36)
    p.add_argument("--bar-offset", type=int, default=0)
    p.add_argument("--max-signal-age-minutes", type=float, default=15.0)
    p.add_argument("--mt5-to-local-hours", type=float, default=6.0)
    p.add_argument("--tail-m15", type=int, default=3000)
    p.add_argument("--tail-h1", type=int, default=1500)
    p.add_argument("--tail-h4", type=int, default=800)
    p.add_argument("--tail-d1", type=int, default=500)
    p.add_argument("--near-miss-top-n", type=int, default=80)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    out_dir = resolve_repo_path(args.out_dir)
    mkdirp(out_dir)

    manifest_json = core.read_json(args.manifest_json)
    gate_rules = core.read_json(args.gate_rules_json)
    manifest = core.parse_manifest(manifest_json)
    frame, info = core.build_feature_frame(args)

    if args.bar_offset < 0:
        raise RuntimeError("bar_offset must be >= 0")
    end_pos = len(frame) - int(args.bar_offset)
    if end_pos <= 0:
        scan = frame.iloc[0:0].copy()
    else:
        scan = frame.iloc[max(0, end_pos - int(args.scan_recent_bars)):end_pos].copy()

    now_local = pd.Timestamp.now()
    scan = scan.copy()
    scan["_age_minutes"] = [
        core.minutes_since_local_est(v, mt5_to_local_hours=float(args.mt5_to_local_hours), now_local=now_local)
        for v in scan.get("time", pd.Series(dtype=object)).tolist()
    ]
    if args.max_signal_age_minutes > 0:
        fresh_mask = scan["_age_minutes"].isna() | (scan["_age_minutes"] <= float(args.max_signal_age_minutes))
    else:
        fresh_mask = pd.Series([True] * len(scan), index=scan.index)
    fresh = scan[fresh_mask].copy()
    stale = scan[~fresh_mask].copy()

    near_rows: list[dict[str, Any]] = []
    strategy_rows: list[dict[str, Any]] = []
    feature_set: set[str] = set()

    for strategy in manifest:
        sid = clean(strategy.get("strategy_id"))
        direction = clean(strategy.get("direction"))
        cond_features = [cond.feature for cond in strategy.get("conditions", [])]
        feature_set.update(cond_features)
        condition_count = len(strategy.get("conditions", []))
        best_fresh: dict[str, Any] | None = None
        best_any: dict[str, Any] | None = None
        full_fresh = 0
        full_any = 0
        stale_strategy_rows = 0
        for _, bar in scan.iterrows():
            ok, matched, failed = core.evaluate_strategy(bar, strategy)
            is_fresh = bool(fresh_mask.loc[bar.name])
            if ok:
                full_any += 1
                if is_fresh:
                    full_fresh += 1
                else:
                    stale_strategy_rows += 1
            miss = missing_features(bar, strategy)
            rec = {
                "strategy_id": sid,
                "direction": direction,
                "entry_time": clean(bar.get("time")),
                "age_minutes": "" if core.as_float(bar.get("_age_minutes")) is None else round(float(bar.get("_age_minutes")), 3),
                "is_fresh": is_fresh,
                "matched_count": len(matched),
                "failed_count": len(failed),
                "condition_count": condition_count,
                "matched_conditions": " | ".join(matched),
                "failed_conditions": " | ".join(failed),
                "missing_features": " | ".join(miss),
            }
            near_rows.append(rec)
            if best_any is None or (len(matched), -len(failed)) > (int(best_any["matched_count"]), -int(best_any["failed_count"])):
                best_any = rec
            if is_fresh and (best_fresh is None or (len(matched), -len(failed)) > (int(best_fresh["matched_count"]), -int(best_fresh["failed_count"]))):
                best_fresh = rec
        nearest = best_fresh or best_any or {}
        strategy_rows.append({
            "strategy_id": sid,
            "direction": direction,
            "condition_count": condition_count,
            "attempt_rows": int(len(scan)),
            "fresh_attempt_rows": int(len(fresh)),
            "stale_suppressed_rows": int(len(stale)),
            "full_match_rows_fresh": int(full_fresh),
            "full_match_rows_ignore_age": int(full_any),
            "max_matched_conditions_fresh": int(best_fresh["matched_count"]) if best_fresh else 0,
            "max_matched_conditions_ignore_age": int(best_any["matched_count"]) if best_any else 0,
            "nearest_entry_time": nearest.get("entry_time", ""),
            "nearest_age_minutes": nearest.get("age_minutes", ""),
            "nearest_matched_conditions": nearest.get("matched_conditions", ""),
            "nearest_failed_conditions": nearest.get("failed_conditions", ""),
            "nearest_missing_features": nearest.get("missing_features", ""),
            "all_condition_features": " | ".join(cond_features),
        })

    near_sorted = sorted(
        near_rows,
        key=lambda r: (int(r.get("matched_count", 0)), -int(r.get("failed_count", 999)), bool(r.get("is_fresh"))),
        reverse=True,
    )[: int(args.near_miss_top_n)]
    for i, r in enumerate(near_sorted, start=1):
        r["rank"] = i

    feature_rows: list[dict[str, Any]] = []
    for feature in sorted(feature_set):
        total = int(len(scan))
        fresh_n = int(len(fresh))
        null_n = int(sum(feature_value_missing(row, feature) for _, row in scan.iterrows()))
        fresh_null_n = int(sum(feature_value_missing(row, feature) for _, row in fresh.iterrows()))
        feature_rows.append({
            "feature": feature,
            "total_rows": total,
            "fresh_rows": fresh_n,
            "null_rows": null_n,
            "fresh_null_rows": fresh_null_n,
            "null_ratio": None if total == 0 else null_n / total,
            "fresh_null_ratio": None if fresh_n == 0 else fresh_null_n / fresh_n,
        })

    outputs = {
        "summary_json": out_dir / "gold_disc8_live_decision_diagnostics_summary.json",
        "strategy_diagnostics_csv": out_dir / "gold_disc8_live_decision_strategy_diagnostics.csv",
        "near_miss_csv": out_dir / "gold_disc8_live_decision_near_miss_rows.csv",
        "feature_null_csv": out_dir / "gold_disc8_live_decision_feature_null_summary.csv",
    }
    write_csv(outputs["strategy_diagnostics_csv"], strategy_rows, STRATEGY_DIAG_COLUMNS)
    write_csv(outputs["near_miss_csv"], near_sorted, NEAR_MISS_COLUMNS)
    write_csv(outputs["feature_null_csv"], feature_rows, FEATURE_NULL_COLUMNS)

    summary = {
        "script": "diagnose_gold_disc8_live_decision_candidates_once.py",
        "cycle_ok": True,
        "no_ai_api_call": True,
        "no_discord_send": True,
        "no_mt5_order_send": True,
        "created_at": core.ts_text(),
        "csv_dir": str(args.csv_dir),
        "manifest_json": str(args.manifest_json),
        "gate_rules_json": str(args.gate_rules_json),
        "requires_pre_send_tagger": bool(gate_rules.get("requires_pre_send_tagger", True)),
        "scan_recent_bars": int(args.scan_recent_bars),
        "bar_offset": int(args.bar_offset),
        "max_signal_age_minutes": float(args.max_signal_age_minutes),
        "mt5_to_local_hours": float(args.mt5_to_local_hours),
        "scanned_rows": int(len(scan)),
        "fresh_rows": int(len(fresh)),
        "stale_suppressed_rows": int(len(stale)),
        "candidate_match_attempts": int(len(scan) * len(manifest)),
        "full_match_rows_fresh_total": int(sum(r["full_match_rows_fresh"] for r in strategy_rows)),
        "full_match_rows_ignore_age_total": int(sum(r["full_match_rows_ignore_age"] for r in strategy_rows)),
        "max_matched_conditions_fresh_any_strategy": max([int(r["max_matched_conditions_fresh"]) for r in strategy_rows] or [0]),
        "max_matched_conditions_ignore_age_any_strategy": max([int(r["max_matched_conditions_ignore_age"]) for r in strategy_rows] or [0]),
        "strategies_with_full_match_fresh": [r["strategy_id"] for r in strategy_rows if int(r["full_match_rows_fresh"]) > 0],
        "strategies_with_full_match_ignore_age": [r["strategy_id"] for r in strategy_rows if int(r["full_match_rows_ignore_age"]) > 0],
        "latest_m15_time": info.get("latest_m15_time", ""),
        **{k: v for k, v in info.items() if k != "latest_m15_time"},
        "outputs": {k: str(v) for k, v in outputs.items()},
    }
    write_json(outputs["summary_json"], summary)

    print("=" * 100)
    print("GOLD DISC8 live decision diagnostics")
    print("=" * 100)
    print(json.dumps(summary, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
