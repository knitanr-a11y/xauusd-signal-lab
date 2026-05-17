#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""BTC AI review pipeline wrapper that enforces the same review contract as GOLD.

This wrapper keeps the existing BTC pipeline but fixes two BTC-specific issues
before the actual AI review is run:

1. BTC multi-strategy order ledgers can contain empty strategy_id/strategy_key
   after MT5 outcome matching. We infer a stable strategy name from order_key /
   payload_key, e.g. D1_LOW_BREAK_SELL, so tag_summary is grouped by strategy.
2. JSONL row counts are counted as JSONL lines, not with CSV parsing.

Flow:
- Run run_btc_ai_review_pipeline.py with --skip-ai-review to export MT5 history
  and build the initial deterministic outcome ledger.
- Normalize BTC outcome rows and fill strategy_id/strategy_key/pair_name.
- Rebuild feature snapshots from the corrected outcome ledger.
- Build payloads using M15 pre=100 / post=20.
- Run AI review using .env OPENAI_API_KEY unless --dry-run is passed through.
- Summarize tags.

No orders are placed. No strategy rules are changed.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_PIPELINE = REPO_ROOT / "scripts" / "run_btc_ai_review_pipeline.py"


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


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(windows_long_path(path), encoding="utf-8-sig", sep=None, engine="python")


def write_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(windows_long_path(path), index=False, encoding="utf-8-sig")


def utc_now_text() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")


def clean_str(x: Any) -> str:
    if x is None:
        return ""
    try:
        if pd.isna(x):
            return ""
    except Exception:
        pass
    return str(x).strip()


def jsonl_count(path: Path) -> int:
    if not path_exists(path):
        return 0
    n = 0
    with open(windows_long_path(path), "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                n += 1
    return n


def csv_count(path: Path) -> int:
    if not path_exists(path):
        return 0
    try:
        return int(len(read_csv(path)))
    except Exception:
        return 0


def run_cmd(label: str, cmd: list[str], *, cwd: Path = REPO_ROOT) -> dict[str, Any]:
    print("=" * 80, flush=True)
    print(f"[STEP] {label}", flush=True)
    print("[CMD] " + " ".join(cmd), flush=True)
    started = time.perf_counter()
    completed = subprocess.run(cmd, cwd=str(cwd), text=True, encoding="utf-8", errors="replace")
    elapsed = round(time.perf_counter() - started, 3)
    print(f"[STEP] {label} returncode={completed.returncode} elapsed_seconds={elapsed}", flush=True)
    return {"label": label, "cmd": cmd, "returncode": int(completed.returncode), "elapsed_seconds": elapsed, "ok": completed.returncode == 0}


def infer_btc_strategy_from_key(*values: Any) -> str:
    for value in values:
        text = clean_str(value)
        if not text:
            continue
        upper = text.upper()
        # Example: BTC_MULTI_BTCUSD#_SELL_D1_LOW_BREAK_SELL_20260514_0600_ORDER
        parts = [p for p in re.split(r"[_|]", upper) if p]
        if "BTC" not in parts and not upper.startswith("BTC_MULTI"):
            continue
        direction_idx = -1
        for i, part in enumerate(parts):
            if part in {"BUY", "SELL"}:
                direction_idx = i
                break
        if direction_idx >= 0:
            tail: list[str] = []
            for part in parts[direction_idx + 1:]:
                if part in {"ORDER", "PAYLOAD", "SIGNAL"}:
                    break
                if re.fullmatch(r"20\d{6}", part):
                    break
                if re.fullmatch(r"\d{4,6}", part):
                    break
                if part in {"BUY", "SELL"} and tail:
                    tail.append(part)
                    break
                tail.append(part)
            if tail:
                return "_".join(tail)
        for candidate in ["D1_LOW_BREAK_SELL", "D1_HIGH_BREAK_BUY", "BTC_MULTI"]:
            if candidate in upper:
                return candidate
    return "BTC_MULTI_UNKNOWN"


def normalize_btc_outcome(path: Path) -> dict[str, Any]:
    df = read_csv(path)
    if df.empty:
        return {"rows": 0, "strategy_filled_rows": 0, "strategies": []}
    for col in ["symbol", "strategy_id", "strategy_key", "pair_name"]:
        if col not in df.columns:
            df[col] = ""
    df["symbol"] = "BTC"
    filled = 0
    strategies: set[str] = set()
    for idx, row in df.iterrows():
        current = clean_str(row.get("strategy_id")) or clean_str(row.get("strategy_key")) or clean_str(row.get("pair_name"))
        inferred = current or infer_btc_strategy_from_key(row.get("order_key"), row.get("payload_key"), row.get("trade_id"), row.get("signal_key"))
        if not current and inferred:
            filled += 1
        if inferred:
            df.at[idx, "strategy_id"] = inferred
            df.at[idx, "strategy_key"] = inferred
            df.at[idx, "pair_name"] = inferred
            strategies.add(inferred)
    write_csv(df, path)
    return {"rows": int(len(df)), "strategy_filled_rows": int(filled), "strategies": sorted(strategies)}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run BTC AI review pipeline with strategy-field normalization before AI review.")
    p.add_argument("--out-dir", default="data/runtime_logs/trade_ai_review_btc")
    p.add_argument("--model", default="gpt-5-mini")
    p.add_argument("--min-sample", default="5")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--max-review-items", type=int, default=0)
    p.add_argument("base_args", nargs=argparse.REMAINDER, help="Arguments passed through to run_btc_ai_review_pipeline.py. Use after --.")
    return p.parse_args()


def remove_arg_pair(args: list[str], flag: str) -> list[str]:
    out: list[str] = []
    skip = False
    for i, arg in enumerate(args):
        if skip:
            skip = False
            continue
        if arg == flag:
            skip = True
            continue
        out.append(arg)
    return out


def main() -> int:
    args = parse_args()
    started = time.perf_counter()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    base_args = list(args.base_args or [])
    if base_args and base_args[0] == "--":
        base_args = base_args[1:]
    base_args = remove_arg_pair(base_args, "--out-dir")
    base_args = remove_arg_pair(base_args, "--model")
    base_args = remove_arg_pair(base_args, "--min-sample")
    base_args = [a for a in base_args if a not in {"--skip-ai-review", "--dry-run"}]

    paths = {
        "pipeline_summary_json": out_dir / "btc_ai_review_pipeline_summary.json",
        "same_spec_summary_json": out_dir / "btc_ai_review_pipeline_same_spec_summary.json",
        "trade_outcome_csv": out_dir / "trade_outcome_ledger.csv",
        "feature_snapshot_csv": out_dir / "trade_feature_snapshot.csv",
        "feature_snapshot_jsonl": out_dir / "trade_feature_snapshot.jsonl",
        "feature_snapshot_json": out_dir / "trade_feature_snapshot_summary.json",
        "payload_jsonl": out_dir / "trade_ai_review_payloads.jsonl",
        "payload_json": out_dir / "trade_ai_review_payloads_summary.json",
        "review_jsonl": out_dir / "trade_ai_review_ledger.jsonl",
        "review_json": out_dir / "trade_ai_review_run_summary.json",
        "tag_summary_csv": out_dir / "trade_ai_tag_summary.csv",
        "tag_summary_json": out_dir / "trade_ai_tag_summary.json",
    }

    steps: list[dict[str, Any]] = []
    base_cmd = [sys.executable, str(BASE_PIPELINE), "--out-dir", str(out_dir), "--model", str(args.model), "--min-sample", str(args.min_sample), "--skip-ai-review"] + base_args
    steps.append(run_cmd("btc_base_pipeline_without_ai_review", base_cmd))
    if not steps[-1]["ok"]:
        return 1

    base_summary = read_json(paths["pipeline_summary_json"])
    inputs = base_summary.get("inputs", {}) if isinstance(base_summary.get("inputs"), dict) else {}
    m15_csv = clean_str(inputs.get("m15_csv"))
    m5_csv = clean_str(inputs.get("m5_csv"))
    h1_csv = clean_str(inputs.get("h1_csv"))
    h4_csv = clean_str(inputs.get("h4_csv"))
    d1_csv = clean_str(inputs.get("d1_csv"))
    if not m15_csv:
        print("ERROR: base summary missing m15_csv", flush=True)
        return 2

    normalization = normalize_btc_outcome(paths["trade_outcome_csv"])

    snapshot_cmd = [
        sys.executable, str(REPO_ROOT / "scripts" / "build_trade_feature_snapshots.py"),
        "--trade-outcome-csv", str(paths["trade_outcome_csv"]),
        "--m15-csv", m15_csv,
        "--output-csv", str(paths["feature_snapshot_csv"]),
        "--output-jsonl", str(paths["feature_snapshot_jsonl"]),
        "--output-json", str(paths["feature_snapshot_json"]),
        "--pre-m15-bars", "100",
        "--post-m15-bars", "20",
    ]
    for flag, value in [("--m5-csv", m5_csv), ("--h1-csv", h1_csv), ("--h4-csv", h4_csv), ("--d1-csv", d1_csv)]:
        if value:
            snapshot_cmd.extend([flag, value])
    steps.append(run_cmd("rebuild_trade_feature_snapshots_after_btc_strategy_normalization", snapshot_cmd))
    if not steps[-1]["ok"]:
        return 3

    steps.append(run_cmd("build_trade_ai_review_payloads", [
        sys.executable, str(REPO_ROOT / "scripts" / "build_trade_ai_review_payloads.py"),
        "--feature-snapshot-jsonl", str(paths["feature_snapshot_jsonl"]),
        "--output-jsonl", str(paths["payload_jsonl"]),
        "--output-json", str(paths["payload_json"]),
        "--max-pre-m15-bars-in-prompt", "100",
        "--max-post-m15-bars-in-prompt", "20",
    ]))
    if not steps[-1]["ok"]:
        return 4

    review_cmd = [
        sys.executable, str(REPO_ROOT / "scripts" / "run_trade_ai_review_from_payloads.py"),
        "--payload-jsonl", str(paths["payload_jsonl"]),
        "--output-jsonl", str(paths["review_jsonl"]),
        "--output-json", str(paths["review_json"]),
        "--model", str(args.model),
        "--overwrite",
    ]
    if args.max_review_items > 0:
        review_cmd.extend(["--max-items", str(args.max_review_items)])
    if args.dry_run:
        review_cmd.append("--dry-run")
    steps.append(run_cmd("run_trade_ai_review_from_payloads", review_cmd))
    if not steps[-1]["ok"]:
        return 5

    steps.append(run_cmd("summarize_trade_ai_review_ledger", [
        sys.executable, str(REPO_ROOT / "scripts" / "summarize_trade_ai_review_ledger.py"),
        "--trade-outcome-csv", str(paths["trade_outcome_csv"]),
        "--ai-review-jsonl", str(paths["review_jsonl"]),
        "--output-csv", str(paths["tag_summary_csv"]),
        "--output-json", str(paths["tag_summary_json"]),
        "--min-sample", str(args.min_sample),
    ]))
    if not steps[-1]["ok"]:
        return 6

    review_summary = read_json(paths["review_json"])
    tag_summary = read_json(paths["tag_summary_json"])
    summary = {
        "schema_version": "btc_ai_review_pipeline_same_spec_v1",
        "created_at_utc": utc_now_text(),
        "cycle_ok": True,
        "out_dir": str(out_dir),
        "normalization": normalization,
        "key_metrics": {
            "outcome_rows": csv_count(paths["trade_outcome_csv"]),
            "feature_snapshot_rows": csv_count(paths["feature_snapshot_csv"]),
            "payload_rows_jsonl": jsonl_count(paths["payload_jsonl"]),
            "review_rows_jsonl": jsonl_count(paths["review_jsonl"]),
            "review_rows_written": review_summary.get("rows_written"),
            "review_error_rows": review_summary.get("error_rows"),
            "tag_summary_rows": csv_count(paths["tag_summary_csv"]),
            "should_investigate_rows": tag_summary.get("should_investigate_rows"),
        },
        "safety": {
            "orders_sent": False,
            "mt5_history_read_only": True,
            "strategy_rules_modified": False,
            "ai_hypothesis_only": True,
            "single_trade_rule_change_allowed": False,
        },
        "base_pipeline_summary_json": str(paths["pipeline_summary_json"]),
        "paths": {k: str(v) for k, v in paths.items()},
        "steps": steps,
        "timing": {"total_seconds": round(time.perf_counter() - started, 3)},
    }
    write_json(paths["same_spec_summary_json"], summary)
    print("=" * 80, flush=True)
    print("BTC same-spec AI review pipeline summary", flush=True)
    print(json.dumps({
        "cycle_ok": True,
        "normalization": normalization,
        "key_metrics": summary["key_metrics"],
        "tag_summary_csv": str(paths["tag_summary_csv"]),
        "summary_json": str(paths["same_spec_summary_json"]),
    }, ensure_ascii=False, indent=2, sort_keys=True), flush=True)
    print("=" * 80, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
