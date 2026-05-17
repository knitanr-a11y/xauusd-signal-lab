#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""Run the shared GOLD trade AI review pipeline.

This is the full Mochipoyo-style AI evaluation cycle for GOLD order ledgers,
including both existing Mochipoyo GOLD and GOLD multi-strategy ledgers by default:

1. order ledgers + MT5 history -> trade_outcome_ledger.csv
2. trade_outcome_ledger + OHLCV candles -> trade_feature_snapshot.csv/jsonl
3. feature snapshots -> trade_ai_review_payloads.jsonl
4. payloads -> trade_ai_review_ledger.jsonl
5. AI review ledger + outcome ledger -> trade_ai_tag_summary.csv/json

Design principles:
- Does not place orders.
- Does not edit strategy rules.
- Does not change lot size.
- AI tags are hypothesis records only.
- One trade never changes a strategy.
- Shared output path is intentionally the same path read by live Discord warning
  code: data/runtime_logs/trade_ai_review/trade_ai_tag_summary.csv

Default order ledgers:
- data/mt5_demo_order_test/goldsharp_auto_trade_demo_prod_order_ledger.csv
- data/runtime_state/gold/multi_strategy/guarded_demo_order_ledger.csv

If one ledger does not exist locally, it is skipped unless explicitly supplied
with --order-ledger-csv.
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

import pandas as pd
from pandas.errors import EmptyDataError

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT_DIR = Path("data/runtime_logs/trade_ai_review")
DEFAULT_MOCHIPOYO_ORDER_LEDGER = Path("data/mt5_demo_order_test/goldsharp_auto_trade_demo_prod_order_ledger.csv")
DEFAULT_MULTI_ORDER_LEDGER = Path("data/runtime_state/gold/multi_strategy/guarded_demo_order_ledger.csv")
DEFAULT_MT5_HISTORY_DIR = DEFAULT_OUT_DIR / "mt5_history"
DEFAULT_MT5_POSITIONS = DEFAULT_MT5_HISTORY_DIR / "mt5_history_positions.csv"
DEFAULT_MT5_DEALS = DEFAULT_MT5_HISTORY_DIR / "mt5_history_deals.csv"
DEFAULT_CSV_DIR = Path(r"C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files")

CANDLE_CANDIDATES = {
    "m15": [
        DEFAULT_CSV_DIR / "goldsharp_m15.csv",
        DEFAULT_CSV_DIR / "GOLD_M15.csv",
        DEFAULT_CSV_DIR / "gold_m15.csv",
        DEFAULT_CSV_DIR / "xauusd_m15.csv",
    ],
    "m5": [
        DEFAULT_CSV_DIR / "goldsharp_m5.csv",
        DEFAULT_CSV_DIR / "GOLD_M5.csv",
        DEFAULT_CSV_DIR / "gold_m5.csv",
        DEFAULT_CSV_DIR / "xauusd_m5.csv",
    ],
    "h1": [
        DEFAULT_CSV_DIR / "goldsharp_h1.csv",
        DEFAULT_CSV_DIR / "GOLD_H1.csv",
        DEFAULT_CSV_DIR / "gold_h1.csv",
        DEFAULT_CSV_DIR / "xauusd_h1.csv",
    ],
    "h4": [
        DEFAULT_CSV_DIR / "goldsharp_h4.csv",
        DEFAULT_CSV_DIR / "GOLD_H4.csv",
        DEFAULT_CSV_DIR / "gold_h4.csv",
        DEFAULT_CSV_DIR / "xauusd_h4.csv",
    ],
    "d1": [
        DEFAULT_CSV_DIR / "goldsharp_d1.csv",
        DEFAULT_CSV_DIR / "GOLD_D1.csv",
        DEFAULT_CSV_DIR / "gold_d1.csv",
        DEFAULT_CSV_DIR / "xauusd_d1.csv",
    ],
}


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


def read_csv_empty_ok(path: str | Path) -> pd.DataFrame:
    try:
        return pd.read_csv(windows_long_path(path), encoding="utf-8-sig")
    except EmptyDataError:
        return pd.DataFrame()
    except FileNotFoundError:
        return pd.DataFrame()


def write_text(path: str | Path, text: str) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(windows_long_path(p), "w", encoding="utf-8", newline="") as f:
        f.write(text)


def write_json(path: str | Path, obj: dict[str, Any]) -> None:
    write_text(path, json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True, default=str))


def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value or 0)
    except Exception:
        try:
            return int(float(value))
        except Exception:
            return default


def resolve_candidate_path(explicit: str | Path, candidates: list[Path]) -> str:
    if explicit:
        return str(explicit)
    for path in candidates:
        if path_exists(path):
            return str(path)
    return ""


def run_cmd(label: str, cmd: list[str], *, cwd: Path = REPO_ROOT, allow_fail: bool = False) -> dict[str, Any]:
    print("=" * 80, flush=True)
    print(f"[STEP] {label}", flush=True)
    print("[CMD] " + " ".join(cmd), flush=True)
    started = time.perf_counter()
    proc = subprocess.run(cmd, cwd=str(cwd), text=True, encoding="utf-8", errors="replace")
    elapsed = round(time.perf_counter() - started, 3)
    print(f"[STEP] {label} returncode={proc.returncode} elapsed_seconds={elapsed}", flush=True)
    if proc.returncode != 0 and not allow_fail:
        raise RuntimeError(f"step failed: {label}; returncode={proc.returncode}")
    return {"label": label, "returncode": int(proc.returncode), "elapsed_seconds": elapsed, "cmd": cmd}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run full GOLD trade AI review pipeline for Mochipoyo + multi ledgers.")
    p.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    p.add_argument("--order-ledger-csv", action="append", default=[], help="Explicit order ledger. Repeatable. If supplied, default ledgers are not auto-added unless --include-default-ledgers is used.")
    p.add_argument("--include-default-ledgers", action=argparse.BooleanOptionalAction, default=True)
    p.add_argument("--include-mochipoyo-ledger", action=argparse.BooleanOptionalAction, default=True)
    p.add_argument("--include-multi-ledger", action=argparse.BooleanOptionalAction, default=True)
    p.add_argument("--mt5-positions-csv", default=str(DEFAULT_MT5_POSITIONS))
    p.add_argument("--mt5-deals-csv", default=str(DEFAULT_MT5_DEALS))
    p.add_argument("--m15-csv", default="")
    p.add_argument("--m5-csv", default="")
    p.add_argument("--h1-csv", default="")
    p.add_argument("--h4-csv", default="")
    p.add_argument("--d1-csv", default="")
    p.add_argument("--model", default="gpt-5-mini")
    p.add_argument("--max-items", type=int, default=0, help="0 = all payloads")
    p.add_argument("--min-sample", type=int, default=5)
    p.add_argument("--dry-run-ai", action="store_true", help="Do not call OpenAI; write deterministic placeholder AI reviews.")
    p.add_argument("--overwrite-ai-review", action=argparse.BooleanOptionalAction, default=True)
    p.add_argument("--skip-ai-review", action="store_true", help="Build outcome/snapshots/payloads/summary from existing AI review ledger without calling AI.")
    p.add_argument("--pre-m15-bars", type=int, default=100)
    p.add_argument("--post-m15-bars", type=int, default=20)
    return p.parse_args()


def collect_order_ledgers(args: argparse.Namespace) -> list[str]:
    paths: list[str] = []
    if args.order_ledger_csv and not args.include_default_ledgers:
        raw = [Path(p) for p in args.order_ledger_csv]
    else:
        raw: list[Path] = []
        if args.include_mochipoyo_ledger:
            raw.append(DEFAULT_MOCHIPOYO_ORDER_LEDGER)
        if args.include_multi_ledger:
            raw.append(DEFAULT_MULTI_ORDER_LEDGER)
        raw.extend(Path(p) for p in args.order_ledger_csv)
    seen: set[str] = set()
    for path in raw:
        text = str(path)
        if text in seen:
            continue
        seen.add(text)
        if path_exists(path):
            paths.append(text)
        else:
            print(f"[WARN] order ledger not found; skipped: {text}", flush=True)
    return paths


def json_summary_rows(path: Path) -> dict[str, Any]:
    if not path_exists(path):
        return {"exists": False, "rows": 0}
    df = read_csv_empty_ok(path)
    return {"exists": True, "rows": int(len(df)), "columns": list(df.columns)}


def main() -> int:
    args = parse_args()
    started = time.perf_counter()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    paths = {
        "trade_outcome_csv": args.out_dir / "trade_outcome_ledger.csv",
        "trade_outcome_json": args.out_dir / "trade_outcome_ledger_summary.json",
        "feature_snapshot_csv": args.out_dir / "trade_feature_snapshot.csv",
        "feature_snapshot_jsonl": args.out_dir / "trade_feature_snapshot.jsonl",
        "feature_snapshot_json": args.out_dir / "trade_feature_snapshot_summary.json",
        "review_payload_jsonl": args.out_dir / "trade_ai_review_payloads.jsonl",
        "review_payload_json": args.out_dir / "trade_ai_review_payloads_summary.json",
        "ai_review_jsonl": args.out_dir / "trade_ai_review_ledger.jsonl",
        "ai_review_json": args.out_dir / "trade_ai_review_run_summary.json",
        "tag_summary_csv": args.out_dir / "trade_ai_tag_summary.csv",
        "tag_summary_json": args.out_dir / "trade_ai_tag_summary.json",
        "pipeline_summary_json": args.out_dir / "gold_trade_ai_review_pipeline_summary.json",
    }

    order_ledgers = collect_order_ledgers(args)
    if not order_ledgers:
        raise SystemExit("No usable order ledgers found. Check default paths or pass --order-ledger-csv.")
    if not path_exists(args.mt5_positions_csv):
        raise SystemExit(f"MT5 positions CSV not found: {args.mt5_positions_csv}")

    candle_paths = {
        "m15": resolve_candidate_path(args.m15_csv, CANDLE_CANDIDATES["m15"]),
        "m5": resolve_candidate_path(args.m5_csv, CANDLE_CANDIDATES["m5"]),
        "h1": resolve_candidate_path(args.h1_csv, CANDLE_CANDIDATES["h1"]),
        "h4": resolve_candidate_path(args.h4_csv, CANDLE_CANDIDATES["h4"]),
        "d1": resolve_candidate_path(args.d1_csv, CANDLE_CANDIDATES["d1"]),
    }
    if not candle_paths["m15"]:
        raise SystemExit("M15 candle CSV not found. Pass --m15-csv explicitly.")

    steps: list[dict[str, Any]] = []
    outcome_cmd = [
        sys.executable, str(REPO_ROOT / "scripts" / "build_trade_outcome_ledger_from_order_ledger.py"),
    ]
    for ledger in order_ledgers:
        outcome_cmd.extend(["--order-ledger-csv", ledger])
    outcome_cmd.extend([
        "--mt5-positions-csv", str(args.mt5_positions_csv),
        "--mt5-deals-csv", str(args.mt5_deals_csv),
        "--output-csv", str(paths["trade_outcome_csv"]),
        "--output-json", str(paths["trade_outcome_json"]),
    ])
    steps.append(run_cmd("build_trade_outcome_ledger", outcome_cmd))

    snapshot_cmd = [
        sys.executable, str(REPO_ROOT / "scripts" / "build_trade_feature_snapshots.py"),
        "--trade-outcome-csv", str(paths["trade_outcome_csv"]),
        "--m15-csv", candle_paths["m15"],
        "--output-csv", str(paths["feature_snapshot_csv"]),
        "--output-jsonl", str(paths["feature_snapshot_jsonl"]),
        "--output-json", str(paths["feature_snapshot_json"]),
        "--pre-m15-bars", str(args.pre_m15_bars),
        "--post-m15-bars", str(args.post_m15_bars),
    ]
    for tf in ["m5", "h1", "h4", "d1"]:
        if candle_paths[tf]:
            snapshot_cmd.extend([f"--{tf}-csv", candle_paths[tf]])
    steps.append(run_cmd("build_trade_feature_snapshots", snapshot_cmd))

    payload_cmd = [
        sys.executable, str(REPO_ROOT / "scripts" / "build_trade_ai_review_payloads.py"),
        "--feature-snapshot-jsonl", str(paths["feature_snapshot_jsonl"]),
        "--output-jsonl", str(paths["review_payload_jsonl"]),
        "--output-json", str(paths["review_payload_json"]),
        "--max-pre-m15-bars-in-prompt", str(args.pre_m15_bars),
        "--max-post-m15-bars-in-prompt", str(args.post_m15_bars),
    ]
    steps.append(run_cmd("build_trade_ai_review_payloads", payload_cmd))

    if not args.skip_ai_review:
        review_cmd = [
            sys.executable, str(REPO_ROOT / "scripts" / "run_trade_ai_review_from_payloads.py"),
            "--payload-jsonl", str(paths["review_payload_jsonl"]),
            "--output-jsonl", str(paths["ai_review_jsonl"]),
            "--output-json", str(paths["ai_review_json"]),
            "--model", str(args.model),
        ]
        if args.max_items > 0:
            review_cmd.extend(["--max-items", str(args.max_items)])
        if args.dry_run_ai:
            review_cmd.append("--dry-run")
        if args.overwrite_ai_review:
            review_cmd.append("--overwrite")
        steps.append(run_cmd("run_trade_ai_review_from_payloads", review_cmd))
    else:
        print("[INFO] skip-ai-review set; using existing AI review ledger if present", flush=True)

    summarize_cmd = [
        sys.executable, str(REPO_ROOT / "scripts" / "summarize_trade_ai_review_ledger.py"),
        "--trade-outcome-csv", str(paths["trade_outcome_csv"]),
        "--ai-review-jsonl", str(paths["ai_review_jsonl"]),
        "--output-csv", str(paths["tag_summary_csv"]),
        "--output-json", str(paths["tag_summary_json"]),
        "--min-sample", str(args.min_sample),
    ]
    steps.append(run_cmd("summarize_trade_ai_review_ledger", summarize_cmd))

    summary = {
        "schema_version": "gold_trade_ai_review_pipeline_v1",
        "cycle_ok": True,
        "reason": "GOLD_TRADE_AI_REVIEW_PIPELINE_PASS",
        "out_dir": str(args.out_dir),
        "order_ledgers": order_ledgers,
        "mt5_positions_csv": str(args.mt5_positions_csv),
        "mt5_deals_csv": str(args.mt5_deals_csv),
        "candle_paths": candle_paths,
        "dry_run_ai": bool(args.dry_run_ai),
        "skip_ai_review": bool(args.skip_ai_review),
        "model": args.model,
        "max_items": int(args.max_items),
        "min_sample": int(args.min_sample),
        "outputs": {k: str(v) for k, v in paths.items()},
        "output_row_counts": {
            "trade_outcome": json_summary_rows(paths["trade_outcome_csv"]),
            "feature_snapshot": json_summary_rows(paths["feature_snapshot_csv"]),
            "tag_summary": json_summary_rows(paths["tag_summary_csv"]),
        },
        "steps": steps,
        "safety": {
            "places_orders": False,
            "edits_strategy_rules": False,
            "changes_lot": False,
            "ai_tags_are_hypotheses_only": True,
            "single_trade_changes_strategy": False,
            "shared_tag_summary_for_mochipoyo_and_multi": True,
        },
        "timing": {"total_seconds": round(time.perf_counter() - started, 3)},
    }
    write_json(paths["pipeline_summary_json"], summary)

    print("=" * 80, flush=True)
    print("GOLD trade AI review pipeline summary", flush=True)
    print(json.dumps({
        "cycle_ok": summary["cycle_ok"],
        "reason": summary["reason"],
        "out_dir": summary["out_dir"],
        "order_ledgers": summary["order_ledgers"],
        "trade_outcome_rows": summary["output_row_counts"]["trade_outcome"].get("rows"),
        "feature_snapshot_rows": summary["output_row_counts"]["feature_snapshot"].get("rows"),
        "tag_summary_rows": summary["output_row_counts"]["tag_summary"].get("rows"),
        "tag_summary_csv": str(paths["tag_summary_csv"]),
        "pipeline_summary_json": str(paths["pipeline_summary_json"]),
    }, ensure_ascii=False, indent=2, sort_keys=True, default=str), flush=True)
    print("=" * 80, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
