#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""Run the full GOLD multi-strategy trade AI review pipeline.

This is the same evaluation shape used for Mochipoyo GOLD:

1. multi order ledger + MT5 history -> deterministic trade outcome ledger
2. outcome ledger + candle CSVs -> feature snapshots
3. feature snapshots -> OpenAI-ready review payloads
4. payloads -> AI hypothesis review ledger
5. outcome ledger + review ledger -> tag summary
6. multi Discord runner reads that tag summary on future signals

Safety / scope:
- This script does not place orders.
- This script does not change signal rules.
- This script does not change lot size.
- This script does not edit the multi order ledger.
- AI output is hypothesis tags only; a single trade must never change rules.

Operational requirement:
- MT5 history CSVs must already be exported to:
    data/runtime_logs/trade_ai_review/mt5_history/mt5_history_positions.csv
    data/runtime_logs/trade_ai_review/mt5_history/mt5_history_deals.csv
  or equivalent paths supplied by arguments.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CSV_DIR = Path(r"C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files")
DEFAULT_OUT_DIR = Path("data/runtime_logs/trade_ai_review/gold_multi")
DEFAULT_MULTI_ORDER_LEDGER = Path("data/runtime_state/gold/multi_strategy/guarded_demo_order_ledger.csv")
DEFAULT_MT5_POSITIONS = Path("data/runtime_logs/trade_ai_review/mt5_history/mt5_history_positions.csv")
DEFAULT_MT5_DEALS = Path("data/runtime_logs/trade_ai_review/mt5_history/mt5_history_deals.csv")
SUMMARY_NAME = "gold_multi_trade_ai_review_pipeline_summary.json"


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


def path_exists(path: str | Path) -> bool:
    return Path(windows_long_path(path)).exists()


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(windows_long_path(path), "w", encoding="utf-8", newline="") as f:
        f.write(text)


def write_json(path: Path, obj: dict[str, Any]) -> None:
    write_text(path, json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True, default=str))


def read_json(path: Path) -> dict[str, Any]:
    try:
        with open(windows_long_path(path), "r", encoding="utf-8") as f:
            obj = json.load(f)
        return obj if isinstance(obj, dict) else {}
    except Exception:
        return {}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path_exists(path):
        return []
    rows: list[dict[str, Any]] = []
    with open(windows_long_path(path), "r", encoding="utf-8") as f:
        for line in f:
            text = line.strip()
            if not text:
                continue
            try:
                obj = json.loads(text)
            except Exception:
                continue
            if isinstance(obj, dict):
                rows.append(obj)
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(windows_long_path(path), "w", encoding="utf-8", newline="") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True, default=str) + "\n")
    return len(rows)


def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value or 0)
    except Exception:
        try:
            return int(float(value))
        except Exception:
            return default


def run_cmd(label: str, cmd: list[str]) -> tuple[int, float]:
    print("=" * 80, flush=True)
    print(f"[STEP] {label}", flush=True)
    print("[CMD] " + " ".join(str(x) for x in cmd), flush=True)
    started = time.perf_counter()
    completed = subprocess.run([str(x) for x in cmd], cwd=str(REPO_ROOT), text=True, encoding="utf-8", errors="replace")
    elapsed = round(time.perf_counter() - started, 3)
    print(f"[STEP] {label} returncode={completed.returncode} elapsed_seconds={elapsed}", flush=True)
    return int(completed.returncode), elapsed


def existing_review_keys(review_jsonl: Path) -> set[str]:
    keys: set[str] = set()
    for row in read_jsonl(review_jsonl):
        for key_name in ["trade_id", "order_key", "payload_key"]:
            value = str(row.get(key_name, "") or "").strip()
            if value:
                keys.add(f"{key_name}:{value}")
    return keys


def payload_key_set(payload: dict[str, Any]) -> set[str]:
    keys: set[str] = set()
    trade = payload.get("trade", {}) if isinstance(payload.get("trade"), dict) else {}
    compact = payload.get("compact_features", {}) if isinstance(payload.get("compact_features"), dict) else {}
    for source in [payload, trade, compact]:
        for key_name in ["trade_id", "order_key", "payload_key"]:
            value = str(source.get(key_name, "") or "").strip()
            if value:
                keys.add(f"{key_name}:{value}")
    return keys


def filter_payloads_for_unreviewed(source_jsonl: Path, output_jsonl: Path, review_jsonl: Path, *, overwrite_reviews: bool, max_items: int) -> dict[str, Any]:
    payloads = read_jsonl(source_jsonl)
    if overwrite_reviews:
        selected = payloads
        already = set()
    else:
        already = existing_review_keys(review_jsonl)
        selected = [p for p in payloads if payload_key_set(p).isdisjoint(already)]
    if max_items > 0:
        selected = selected[:max_items]
    written = write_jsonl(output_jsonl, selected)
    return {
        "payloads_in": len(payloads),
        "existing_review_keys": len(already),
        "payloads_to_review": written,
        "overwrite_reviews": bool(overwrite_reviews),
        "max_items": int(max_items),
        "output_jsonl": str(output_jsonl),
    }


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run full GOLD multi trade AI review pipeline.")
    p.add_argument("--csv-dir", type=Path, default=DEFAULT_CSV_DIR)
    p.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    p.add_argument("--multi-order-ledger-csv", type=Path, default=DEFAULT_MULTI_ORDER_LEDGER)
    p.add_argument("--mt5-positions-csv", type=Path, default=DEFAULT_MT5_POSITIONS)
    p.add_argument("--mt5-deals-csv", type=Path, default=DEFAULT_MT5_DEALS)
    p.add_argument("--m5-csv", type=Path, default=None)
    p.add_argument("--m15-csv", type=Path, default=None)
    p.add_argument("--h1-csv", type=Path, default=None)
    p.add_argument("--h4-csv", type=Path, default=None)
    p.add_argument("--d1-csv", type=Path, default=None)
    p.add_argument("--model", default="gpt-5-mini")
    p.add_argument("--dry-run", action="store_true", help="Use deterministic placeholder reviews instead of OpenAI API.")
    p.add_argument("--overwrite-reviews", action="store_true", help="Overwrite review ledger and review all payloads again. Default skips already reviewed trades.")
    p.add_argument("--max-items", type=int, default=0, help="Max new payloads to review. 0 = all new payloads.")
    p.add_argument("--min-sample", type=int, default=5)
    p.add_argument("--pre-m15-bars", type=int, default=100)
    p.add_argument("--post-m15-bars", type=int, default=20)
    p.add_argument("--pre-h1-bars", type=int, default=100)
    p.add_argument("--pre-h4-bars", type=int, default=60)
    p.add_argument("--pre-d1-bars", type=int, default=40)
    return p.parse_args()


def resolve_candle_paths(args: argparse.Namespace) -> dict[str, Path]:
    return {
        "m5": args.m5_csv or (args.csv_dir / "goldsharp_m5.csv"),
        "m15": args.m15_csv or (args.csv_dir / "goldsharp_m15.csv"),
        "h1": args.h1_csv or (args.csv_dir / "goldsharp_h1.csv"),
        "h4": args.h4_csv or (args.csv_dir / "goldsharp_h4.csv"),
        "d1": args.d1_csv or (args.csv_dir / "goldsharp_d1.csv"),
    }


def main() -> int:
    args = parse_args()
    started = time.perf_counter()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    candle_paths = resolve_candle_paths(args)
    paths = {
        "outcome_csv": args.out_dir / "gold_multi_trade_outcome_ledger.csv",
        "outcome_json": args.out_dir / "gold_multi_trade_outcome_ledger_summary.json",
        "feature_csv": args.out_dir / "gold_multi_trade_feature_snapshot.csv",
        "feature_jsonl": args.out_dir / "gold_multi_trade_feature_snapshot.jsonl",
        "feature_json": args.out_dir / "gold_multi_trade_feature_snapshot_summary.json",
        "payload_jsonl": args.out_dir / "gold_multi_trade_ai_review_payloads.jsonl",
        "payload_json": args.out_dir / "gold_multi_trade_ai_review_payloads_summary.json",
        "payload_to_review_jsonl": args.out_dir / "gold_multi_trade_ai_review_payloads_to_review.jsonl",
        "review_jsonl": args.out_dir / "gold_multi_trade_ai_review_ledger.jsonl",
        "review_json": args.out_dir / "gold_multi_trade_ai_review_run_summary.json",
        "tag_summary_csv": args.out_dir / "gold_multi_trade_ai_tag_summary.csv",
        "tag_summary_json": args.out_dir / "gold_multi_trade_ai_tag_summary.json",
        "summary_json": args.out_dir / SUMMARY_NAME,
    }

    missing_required = []
    for label, path in [
        ("multi_order_ledger", args.multi_order_ledger_csv),
        ("mt5_positions", args.mt5_positions_csv),
        ("m15_csv", candle_paths["m15"]),
    ]:
        if not path_exists(path):
            missing_required.append({"label": label, "path": str(path)})
    if missing_required:
        summary = {
            "schema_version": "gold_multi_trade_ai_review_pipeline_v1",
            "cycle_ok": False,
            "reason": "MISSING_REQUIRED_INPUTS",
            "missing_required": missing_required,
            "paths": {k: str(v) for k, v in paths.items()},
        }
        write_json(paths["summary_json"], summary)
        print("run_gold_multi_trade_ai_review_pipeline")
        print("ERROR: missing required inputs")
        for item in missing_required:
            print(f"missing {item['label']}: {item['path']}")
        print(f"summary_json: {paths['summary_json']}")
        return 2

    steps: list[dict[str, Any]] = []

    rc, sec = run_cmd("build_trade_outcome_ledger_from_order_ledger", [
        sys.executable, REPO_ROOT / "scripts" / "build_trade_outcome_ledger_from_order_ledger.py",
        "--order-ledger-csv", args.multi_order_ledger_csv,
        "--mt5-positions-csv", args.mt5_positions_csv,
        "--mt5-deals-csv", args.mt5_deals_csv,
        "--output-csv", paths["outcome_csv"],
        "--output-json", paths["outcome_json"],
    ])
    steps.append({"name": "outcome", "returncode": rc, "seconds": sec, "summary": read_json(paths["outcome_json"])})
    if rc != 0:
        final = {"cycle_ok": False, "reason": "OUTCOME_STEP_FAILED", "steps": steps, "paths": {k: str(v) for k, v in paths.items()}}
        write_json(paths["summary_json"], final)
        return 1

    feature_cmd = [
        sys.executable, REPO_ROOT / "scripts" / "build_trade_feature_snapshots.py",
        "--trade-outcome-csv", paths["outcome_csv"],
        "--m15-csv", candle_paths["m15"],
        "--output-csv", paths["feature_csv"],
        "--output-jsonl", paths["feature_jsonl"],
        "--output-json", paths["feature_json"],
        "--pre-m15-bars", str(args.pre_m15_bars),
        "--post-m15-bars", str(args.post_m15_bars),
        "--pre-h1-bars", str(args.pre_h1_bars),
        "--pre-h4-bars", str(args.pre_h4_bars),
        "--pre-d1-bars", str(args.pre_d1_bars),
    ]
    optional_tf_args = [("--m5-csv", candle_paths["m5"]), ("--h1-csv", candle_paths["h1"]), ("--h4-csv", candle_paths["h4"]), ("--d1-csv", candle_paths["d1"])]
    for opt, path in optional_tf_args:
        if path_exists(path):
            feature_cmd.extend([opt, path])
    rc, sec = run_cmd("build_trade_feature_snapshots", feature_cmd)
    steps.append({"name": "features", "returncode": rc, "seconds": sec, "summary": read_json(paths["feature_json"])})
    if rc != 0:
        final = {"cycle_ok": False, "reason": "FEATURE_STEP_FAILED", "steps": steps, "paths": {k: str(v) for k, v in paths.items()}}
        write_json(paths["summary_json"], final)
        return 1

    rc, sec = run_cmd("build_trade_ai_review_payloads", [
        sys.executable, REPO_ROOT / "scripts" / "build_trade_ai_review_payloads.py",
        "--feature-snapshot-jsonl", paths["feature_jsonl"],
        "--output-jsonl", paths["payload_jsonl"],
        "--output-json", paths["payload_json"],
        "--max-pre-m15-bars-in-prompt", str(args.pre_m15_bars),
        "--max-post-m15-bars-in-prompt", str(args.post_m15_bars),
        "--max-pre-h1-bars-in-prompt", str(args.pre_h1_bars),
        "--max-pre-h4-bars-in-prompt", str(args.pre_h4_bars),
        "--max-pre-d1-bars-in-prompt", str(args.pre_d1_bars),
    ])
    steps.append({"name": "payloads", "returncode": rc, "seconds": sec, "summary": read_json(paths["payload_json"])})
    if rc != 0:
        final = {"cycle_ok": False, "reason": "PAYLOAD_STEP_FAILED", "steps": steps, "paths": {k: str(v) for k, v in paths.items()}}
        write_json(paths["summary_json"], final)
        return 1

    filter_report = filter_payloads_for_unreviewed(
        paths["payload_jsonl"],
        paths["payload_to_review_jsonl"],
        paths["review_jsonl"],
        overwrite_reviews=bool(args.overwrite_reviews),
        max_items=int(args.max_items),
    )
    steps.append({"name": "filter_unreviewed_payloads", "returncode": 0, "seconds": 0.0, "summary": filter_report})

    review_rc: int | str = "SKIPPED_NO_NEW_PAYLOADS"
    review_sec = 0.0
    review_summary: dict[str, Any] = {
        "rows_in": 0,
        "rows_written": 0,
        "error_rows": 0,
        "reason": "SKIPPED_NO_NEW_PAYLOADS",
    }
    if filter_report["payloads_to_review"] > 0:
        review_cmd = [
            sys.executable, REPO_ROOT / "scripts" / "run_trade_ai_review_from_payloads.py",
            "--payload-jsonl", paths["payload_to_review_jsonl"],
            "--output-jsonl", paths["review_jsonl"],
            "--output-json", paths["review_json"],
            "--model", args.model,
        ]
        if args.overwrite_reviews:
            review_cmd.append("--overwrite")
        if args.dry_run:
            review_cmd.append("--dry-run")
        review_rc, review_sec = run_cmd("run_trade_ai_review_from_payloads", review_cmd)
        review_summary = read_json(paths["review_json"])
    else:
        write_json(paths["review_json"], review_summary)
        print("[INFO] AI review step skipped because there are no new multi payloads to review", flush=True)
    steps.append({"name": "ai_review", "returncode": review_rc, "seconds": review_sec, "summary": review_summary})
    if review_rc not in [0, "SKIPPED_NO_NEW_PAYLOADS"]:
        final = {"cycle_ok": False, "reason": "AI_REVIEW_STEP_FAILED", "steps": steps, "paths": {k: str(v) for k, v in paths.items()}}
        write_json(paths["summary_json"], final)
        return 1

    rc, sec = run_cmd("summarize_trade_ai_review_ledger", [
        sys.executable, REPO_ROOT / "scripts" / "summarize_trade_ai_review_ledger.py",
        "--trade-outcome-csv", paths["outcome_csv"],
        "--ai-review-jsonl", paths["review_jsonl"],
        "--output-csv", paths["tag_summary_csv"],
        "--output-json", paths["tag_summary_json"],
        "--min-sample", str(args.min_sample),
    ])
    steps.append({"name": "summarize", "returncode": rc, "seconds": sec, "summary": read_json(paths["tag_summary_json"])})
    if rc != 0:
        final = {"cycle_ok": False, "reason": "SUMMARY_STEP_FAILED", "steps": steps, "paths": {k: str(v) for k, v in paths.items()}}
        write_json(paths["summary_json"], final)
        return 1

    final = {
        "schema_version": "gold_multi_trade_ai_review_pipeline_v1",
        "cycle_ok": True,
        "reason": "GOLD_MULTI_TRADE_AI_REVIEW_PIPELINE_PASS",
        "dry_run": bool(args.dry_run),
        "model": str(args.model),
        "out_dir": str(args.out_dir),
        "multi_order_ledger_csv": str(args.multi_order_ledger_csv),
        "mt5_positions_csv": str(args.mt5_positions_csv),
        "mt5_deals_csv": str(args.mt5_deals_csv),
        "candle_paths": {k: str(v) for k, v in candle_paths.items()},
        "key_metrics": {
            "outcome_rows": safe_int(steps[0].get("summary", {}), "rows_out", 0),
            "feature_rows": safe_int(steps[1].get("summary", {}), "rows_out_csv", 0),
            "payload_rows": safe_int(steps[2].get("summary", {}), "rows_out", 0),
            "payloads_to_review": int(filter_report.get("payloads_to_review", 0)),
            "review_rows_written": safe_int(review_summary, "rows_written", 0),
            "review_error_rows": safe_int(review_summary, "error_rows", 0),
            "tag_summary_rows": safe_int(steps[-1].get("summary", {}), "summary_rows", 0),
            "should_investigate_rows": safe_int(steps[-1].get("summary", {}), "should_investigate_rows", 0),
        },
        "paths": {k: str(v) for k, v in paths.items()},
        "steps": steps,
        "timing": {"total_seconds": round(time.perf_counter() - started, 3)},
    }
    write_json(paths["summary_json"], final)

    print("=" * 80, flush=True)
    print("GOLD multi trade AI review pipeline summary", flush=True)
    print(json.dumps({
        "cycle_ok": final["cycle_ok"],
        "reason": final["reason"],
        "dry_run": final["dry_run"],
        "key_metrics": final["key_metrics"],
        "tag_summary_csv": str(paths["tag_summary_csv"]),
        "review_jsonl": str(paths["review_jsonl"]),
        "summary_json": str(paths["summary_json"]),
    }, ensure_ascii=False, indent=2, sort_keys=True, default=str), flush=True)
    print("=" * 80, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
