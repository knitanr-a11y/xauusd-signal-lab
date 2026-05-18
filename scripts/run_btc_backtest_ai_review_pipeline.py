#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""Run BTC backtest AI review pipeline, isolated from live AI review outputs.

This wrapper is intentionally separate from:
- data/runtime_logs/trade_ai_review_btc/
- live BTC multi order ledger review

Pipeline:
1. Convert backtest trades.csv to live-compatible trade_outcome_ledger.csv.
2. Build pre/post feature snapshots using M15 pre=100 and post=20.
3. Build OpenAI-ready AI review payloads.
4. Run AI review from payloads unless --skip-ai-review.
5. Summarize hypothesis tags.
6. Export a target-tag hypothesis summary for BTC D1_LOW_BREAK_SELL.

Default target hypothesis tags:
- ema_distance_too_large
- m15_signal_candle_large
- near_recent_low
- range_edge_entry

Safety:
- Does not place, modify, or close orders.
- Does not read or write live order ledgers.
- Does not modify strategy rules.
- AI output is hypothesis tagging only.
- Backtest summary is auxiliary information, not a replacement for live results.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MQL5_FILES_DIR = Path(r"C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files")
DEFAULT_OUT_DIR = Path("data/runtime_logs/trade_ai_review_backtest_btc")
DEFAULT_TARGET_TAGS = [
    "ema_distance_too_large",
    "m15_signal_candle_large",
    "near_recent_low",
    "range_edge_entry",
]


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


def csv_count(path: Path) -> int:
    if not path_exists(path):
        return 0
    try:
        return int(len(read_csv(path)))
    except Exception:
        return 0


def jsonl_count(path: Path) -> int:
    if not path_exists(path):
        return 0
    n = 0
    with open(windows_long_path(path), "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                n += 1
    return n


def utc_now_text() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")


def run_cmd(label: str, cmd: list[str], *, cwd: Path = REPO_ROOT, allow_failure: bool = False) -> dict[str, Any]:
    print("=" * 80, flush=True)
    print(f"[STEP] {label}", flush=True)
    print("[CMD] " + " ".join(cmd), flush=True)
    started = time.perf_counter()
    completed = subprocess.run(cmd, cwd=str(cwd), text=True, encoding="utf-8", errors="replace")
    elapsed = round(time.perf_counter() - started, 3)
    ok = completed.returncode == 0 or allow_failure
    print(f"[STEP] {label} returncode={completed.returncode} elapsed_seconds={elapsed} ok={ok}", flush=True)
    return {
        "label": label,
        "cmd": cmd,
        "returncode": int(completed.returncode),
        "elapsed_seconds": elapsed,
        "allow_failure": bool(allow_failure),
        "ok": bool(ok),
    }


def clean_str(x: Any) -> str:
    if x is None:
        return ""
    try:
        if pd.isna(x):
            return ""
    except Exception:
        pass
    return str(x).strip()


def csv_path(csv_dir: Path, explicit: str, filename: str) -> str:
    if explicit:
        return explicit
    return str(csv_dir / filename)


def optional_existing_csv(path_text: str) -> str:
    return path_text if path_text and path_exists(Path(path_text)) else ""


def canonical_tag(tag: Any) -> str:
    return clean_str(tag).strip().lower().replace(" ", "_").replace("-", "_")


def parse_target_tags(text: str) -> list[str]:
    if not text:
        return list(DEFAULT_TARGET_TAGS)
    tags = [canonical_tag(x) for x in text.replace(";", ",").split(",")]
    return [t for t in tags if t]


def build_target_tag_summary(tag_summary_csv: Path, output_csv: Path, output_json: Path, *, strategy_id: str, target_tags: list[str]) -> dict[str, Any]:
    if not path_exists(tag_summary_csv):
        empty = pd.DataFrame()
        write_csv(empty, output_csv)
        summary = {
            "created_at_utc": utc_now_text(),
            "tag_summary_csv": str(tag_summary_csv),
            "output_csv": str(output_csv),
            "target_strategy_id": strategy_id,
            "target_tags": target_tags,
            "rows": 0,
            "notes": "tag_summary_csv not found",
        }
        write_json(output_json, summary)
        return summary

    df = read_csv(tag_summary_csv)
    if df.empty:
        out = df.copy()
    else:
        work = df.copy()
        if "tag_name" not in work.columns:
            work["tag_name"] = ""
        if "strategy_id" not in work.columns:
            work["strategy_id"] = ""
        work["_tag_norm"] = work["tag_name"].map(canonical_tag)
        work["_strategy_norm"] = work["strategy_id"].map(lambda x: clean_str(x).upper())
        strategy_norm = clean_str(strategy_id).upper()
        target_set = set(target_tags)
        out = work[(work["_tag_norm"].isin(target_set)) & ((work["_strategy_norm"] == strategy_norm) | (strategy_norm == ""))].copy()
        out = out.drop(columns=[c for c in ["_tag_norm", "_strategy_norm"] if c in out.columns])

    write_csv(out, output_csv)
    records: list[dict[str, Any]] = []
    if not out.empty:
        for _, row in out.iterrows():
            records.append({
                "symbol": clean_str(row.get("symbol")),
                "strategy_id": clean_str(row.get("strategy_id")),
                "tag_name": clean_str(row.get("tag_name")),
                "trade_count": int(row.get("trade_count") or 0),
                "win_count": int(row.get("win_count") or 0),
                "loss_count": int(row.get("loss_count") or 0),
                "win_rate": row.get("win_rate"),
                "avg_r": row.get("avg_r"),
                "total_r": row.get("total_r"),
                "profit_factor": row.get("profit_factor"),
                "tag_status": clean_str(row.get("tag_status")),
                "should_investigate": bool(row.get("should_investigate")),
                "investigation_reason": clean_str(row.get("investigation_reason")),
            })

    summary = {
        "schema_version": "btc_backtest_ai_review_target_tag_summary_v1",
        "created_at_utc": utc_now_text(),
        "tag_summary_csv": str(tag_summary_csv),
        "output_csv": str(output_csv),
        "target_strategy_id": strategy_id,
        "target_tags": target_tags,
        "rows": int(len(out)),
        "records": records,
        "hypothesis_note": "Backtest tag stats are auxiliary evidence only. They do not change live rules by themselves.",
    }
    write_json(output_json, summary)
    return summary


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run isolated BTC backtest AI review pipeline.")
    p.add_argument("--backtest-trades-csv", required=True, help="Backtest trades.csv. Required because filenames differ by experiment.")
    p.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    p.add_argument("--mql5-files-dir", type=Path, default=DEFAULT_MQL5_FILES_DIR)
    p.add_argument("--symbol", default="BTC")
    p.add_argument("--broker-symbol", default="BTCUSD#")
    p.add_argument("--strategy-id", default="D1_LOW_BREAK_SELL")
    p.add_argument("--strategy-key", default="")
    p.add_argument("--direction", default="", help="Optional BUY/SELL filter. Leave empty to trust trades.csv or strategy default.")
    p.add_argument("--m15-csv", default="")
    p.add_argument("--m5-csv", default="")
    p.add_argument("--h1-csv", default="")
    p.add_argument("--h4-csv", default="")
    p.add_argument("--d1-csv", default="")
    p.add_argument("--m15-file", default="btcusdsharp_m15.csv")
    p.add_argument("--m5-file", default="btcusdsharp_m5.csv")
    p.add_argument("--h1-file", default="btcusdsharp_h1.csv")
    p.add_argument("--h4-file", default="btcusdsharp_h4.csv")
    p.add_argument("--d1-file", default="btcusdsharp_d1.csv")
    p.add_argument("--pre-m15-bars", type=int, default=100)
    p.add_argument("--post-m15-bars", type=int, default=20)
    p.add_argument("--max-losses", type=int, default=100)
    p.add_argument("--max-wins", type=int, default=100)
    p.add_argument("--max-breakevens", type=int, default=30)
    p.add_argument("--include-unknown", action="store_true")
    p.add_argument("--sample-policy", choices=["newest", "oldest", "random"], default="newest")
    p.add_argument("--sample-seed", type=int, default=42)
    p.add_argument("--prefer-net-r", action=argparse.BooleanOptionalAction, default=True)
    p.add_argument("--spread-cost-r-column", default="")
    p.add_argument("--min-sample", type=int, default=5)
    p.add_argument("--model", default="gpt-5-mini")
    p.add_argument("--max-review-items", type=int, default=0, help="0 = all sampled payloads")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--skip-ai-review", action="store_true", help="Use an existing review JSONL if present; otherwise summary will have 0 review rows.")
    p.add_argument("--overwrite-review-jsonl", action=argparse.BooleanOptionalAction, default=True)
    p.add_argument("--include-open-trades-in-summary", action="store_true")
    p.add_argument("--target-tags", default=",".join(DEFAULT_TARGET_TAGS))
    return p.parse_args()


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
        "payload_jsonl": args.out_dir / "trade_ai_review_payloads.jsonl",
        "payload_json": args.out_dir / "trade_ai_review_payloads_summary.json",
        "review_jsonl": args.out_dir / "trade_ai_review_ledger.jsonl",
        "review_json": args.out_dir / "trade_ai_review_run_summary.json",
        "tag_summary_csv": args.out_dir / "trade_ai_tag_summary.csv",
        "tag_summary_json": args.out_dir / "trade_ai_tag_summary.json",
        "target_tag_summary_csv": args.out_dir / "btc_d1_low_break_sell_target_tag_summary.csv",
        "target_tag_summary_json": args.out_dir / "btc_d1_low_break_sell_target_tag_summary.json",
        "pipeline_summary_json": args.out_dir / "btc_backtest_ai_review_pipeline_summary.json",
    }
    for pth in paths.values():
        pth.parent.mkdir(parents=True, exist_ok=True)

    if not path_exists(args.backtest_trades_csv):
        raise SystemExit(f"backtest trades CSV not found: {args.backtest_trades_csv}")

    m15_csv = csv_path(args.mql5_files_dir, args.m15_csv, args.m15_file)
    m5_csv = csv_path(args.mql5_files_dir, args.m5_csv, args.m5_file)
    h1_csv = csv_path(args.mql5_files_dir, args.h1_csv, args.h1_file)
    h4_csv = csv_path(args.mql5_files_dir, args.h4_csv, args.h4_file)
    d1_csv = csv_path(args.mql5_files_dir, args.d1_csv, args.d1_file)

    if not path_exists(m15_csv):
        raise SystemExit(f"BTC M15 CSV not found: {m15_csv}. Pass --m15-csv with the actual BTC M15 file.")

    print("=" * 80, flush=True)
    print("BTC backtest AI review pipeline", flush=True)
    print(f"out_dir={args.out_dir}", flush=True)
    print(f"backtest_trades_csv={args.backtest_trades_csv}", flush=True)
    print(f"symbol={args.symbol} broker_symbol={args.broker_symbol}", flush=True)
    print(f"strategy_id={args.strategy_id}", flush=True)
    print(f"m15_csv={m15_csv}", flush=True)
    print(f"m5_csv={optional_existing_csv(m5_csv)}", flush=True)
    print(f"h1_csv={optional_existing_csv(h1_csv)}", flush=True)
    print(f"h4_csv={optional_existing_csv(h4_csv)}", flush=True)
    print(f"d1_csv={optional_existing_csv(d1_csv)}", flush=True)
    print(f"dry_run={args.dry_run} skip_ai_review={args.skip_ai_review}", flush=True)
    print("=" * 80, flush=True)

    steps: list[dict[str, Any]] = []

    outcome_cmd = [
        sys.executable, str(REPO_ROOT / "scripts" / "build_trade_outcome_ledger_from_backtest_trades.py"),
        "--backtest-trades-csv", str(args.backtest_trades_csv),
        "--output-csv", str(paths["trade_outcome_csv"]),
        "--output-json", str(paths["trade_outcome_json"]),
        "--symbol", str(args.symbol),
        "--broker-symbol", str(args.broker_symbol),
        "--strategy-id", str(args.strategy_id),
        "--max-losses", str(args.max_losses),
        "--max-wins", str(args.max_wins),
        "--max-breakevens", str(args.max_breakevens),
        "--sample-policy", str(args.sample_policy),
        "--sample-seed", str(args.sample_seed),
    ]
    if args.strategy_key:
        outcome_cmd.extend(["--strategy-key", str(args.strategy_key)])
    if args.direction:
        outcome_cmd.extend(["--direction", str(args.direction)])
    if not args.prefer_net_r:
        outcome_cmd.append("--no-prefer-net-r")
    if args.spread_cost_r_column:
        outcome_cmd.extend(["--spread-cost-r-column", str(args.spread_cost_r_column)])
    if args.include_unknown:
        outcome_cmd.append("--include-unknown")
    steps.append(run_cmd("build_trade_outcome_ledger_from_backtest_trades", outcome_cmd))
    if not steps[-1]["ok"]:
        return 1

    snapshot_cmd = [
        sys.executable, str(REPO_ROOT / "scripts" / "build_trade_feature_snapshots.py"),
        "--trade-outcome-csv", str(paths["trade_outcome_csv"]),
        "--m15-csv", str(m15_csv),
        "--output-csv", str(paths["feature_snapshot_csv"]),
        "--output-jsonl", str(paths["feature_snapshot_jsonl"]),
        "--output-json", str(paths["feature_snapshot_json"]),
        "--pre-m15-bars", str(args.pre_m15_bars),
        "--post-m15-bars", str(args.post_m15_bars),
    ]
    for flag, value in [
        ("--m5-csv", optional_existing_csv(m5_csv)),
        ("--h1-csv", optional_existing_csv(h1_csv)),
        ("--h4-csv", optional_existing_csv(h4_csv)),
        ("--d1-csv", optional_existing_csv(d1_csv)),
    ]:
        if value:
            snapshot_cmd.extend([flag, value])
    steps.append(run_cmd("build_trade_feature_snapshots", snapshot_cmd))
    if not steps[-1]["ok"]:
        return 2

    payload_cmd = [
        sys.executable, str(REPO_ROOT / "scripts" / "build_trade_ai_review_payloads.py"),
        "--feature-snapshot-jsonl", str(paths["feature_snapshot_jsonl"]),
        "--output-jsonl", str(paths["payload_jsonl"]),
        "--output-json", str(paths["payload_json"]),
        "--max-pre-m15-bars-in-prompt", str(args.pre_m15_bars),
        "--max-post-m15-bars-in-prompt", str(args.post_m15_bars),
    ]
    steps.append(run_cmd("build_trade_ai_review_payloads", payload_cmd))
    if not steps[-1]["ok"]:
        return 3

    if not args.skip_ai_review:
        review_cmd = [
            sys.executable, str(REPO_ROOT / "scripts" / "run_trade_ai_review_from_payloads.py"),
            "--payload-jsonl", str(paths["payload_jsonl"]),
            "--output-jsonl", str(paths["review_jsonl"]),
            "--output-json", str(paths["review_json"]),
            "--model", str(args.model),
        ]
        if args.overwrite_review_jsonl:
            review_cmd.append("--overwrite")
        if args.max_review_items and args.max_review_items > 0:
            review_cmd.extend(["--max-items", str(args.max_review_items)])
        if args.dry_run:
            review_cmd.append("--dry-run")
        steps.append(run_cmd("run_trade_ai_review_from_payloads", review_cmd))
        if not steps[-1]["ok"]:
            return 4
    else:
        print("[INFO] skip_ai_review=True; using existing review JSONL if present", flush=True)

    if not path_exists(paths["review_jsonl"]):
        write_text(paths["review_jsonl"], "")

    summary_cmd = [
        sys.executable, str(REPO_ROOT / "scripts" / "summarize_trade_ai_review_ledger.py"),
        "--trade-outcome-csv", str(paths["trade_outcome_csv"]),
        "--ai-review-jsonl", str(paths["review_jsonl"]),
        "--output-csv", str(paths["tag_summary_csv"]),
        "--output-json", str(paths["tag_summary_json"]),
        "--min-sample", str(args.min_sample),
    ]
    if args.include_open_trades_in_summary:
        summary_cmd.append("--include-open-trades")
    steps.append(run_cmd("summarize_trade_ai_review_ledger", summary_cmd))
    if not steps[-1]["ok"]:
        return 5

    target_tags = parse_target_tags(args.target_tags)
    target_tag_summary = build_target_tag_summary(
        paths["tag_summary_csv"],
        paths["target_tag_summary_csv"],
        paths["target_tag_summary_json"],
        strategy_id=args.strategy_id,
        target_tags=target_tags,
    )

    outcome_summary = read_json(paths["trade_outcome_json"])
    feature_summary = read_json(paths["feature_snapshot_json"])
    payload_summary = read_json(paths["payload_json"])
    review_summary = read_json(paths["review_json"])
    tag_summary = read_json(paths["tag_summary_json"])

    pipeline_summary = {
        "schema_version": "btc_backtest_ai_review_pipeline_v1",
        "created_at_utc": utc_now_text(),
        "cycle_ok": True,
        "out_dir": str(args.out_dir),
        "paths": {k: str(v) for k, v in paths.items()},
        "inputs": {
            "backtest_trades_csv": str(args.backtest_trades_csv),
            "symbol": args.symbol,
            "broker_symbol": args.broker_symbol,
            "strategy_id": args.strategy_id,
            "strategy_key": args.strategy_key or args.strategy_id,
            "direction": args.direction,
            "m15_csv": m15_csv,
            "m5_csv": optional_existing_csv(m5_csv),
            "h1_csv": optional_existing_csv(h1_csv),
            "h4_csv": optional_existing_csv(h4_csv),
            "d1_csv": optional_existing_csv(d1_csv),
            "pre_m15_bars": int(args.pre_m15_bars),
            "post_m15_bars": int(args.post_m15_bars),
            "prefer_net_r": bool(args.prefer_net_r),
            "spread_cost_r_column": args.spread_cost_r_column,
        },
        "sampling": {
            "max_losses": int(args.max_losses),
            "max_wins": int(args.max_wins),
            "max_breakevens": int(args.max_breakevens),
            "include_unknown": bool(args.include_unknown),
            "sample_policy": args.sample_policy,
            "sample_seed": int(args.sample_seed),
        },
        "key_metrics": {
            "outcome_rows": csv_count(paths["trade_outcome_csv"]),
            "outcome_rows_before_sampling": outcome_summary.get("rows_after_unknown_filter"),
            "outcome_rows_after_filters": outcome_summary.get("rows_after_filters"),
            "sampled_outcome_counts": outcome_summary.get("sampled_outcome_counts"),
            "feature_snapshot_rows": csv_count(paths["feature_snapshot_csv"]),
            "payload_rows_jsonl": jsonl_count(paths["payload_jsonl"]),
            "review_rows_jsonl": jsonl_count(paths["review_jsonl"]),
            "review_rows_written": review_summary.get("rows_written"),
            "review_error_rows": review_summary.get("error_rows"),
            "tag_summary_rows": csv_count(paths["tag_summary_csv"]),
            "should_investigate_rows": tag_summary.get("should_investigate_rows"),
            "target_tag_summary_rows": target_tag_summary.get("rows"),
        },
        "target_hypothesis": {
            "strategy_id": args.strategy_id,
            "tags": target_tags,
            "summary_json": str(paths["target_tag_summary_json"]),
            "summary_csv": str(paths["target_tag_summary_csv"]),
            "records": target_tag_summary.get("records", []),
        },
        "safety": {
            "orders_sent": False,
            "mt5_history_read_only": False,
            "live_order_ledgers_read": False,
            "live_outputs_modified": False,
            "strategy_rules_modified": False,
            "ai_hypothesis_only": True,
            "single_trade_rule_change_allowed": False,
            "backtest_is_auxiliary": True,
        },
        "component_summaries": {
            "outcome": outcome_summary,
            "feature": feature_summary,
            "payload": payload_summary,
            "review": review_summary,
            "tag": tag_summary,
        },
        "steps": steps,
        "timing": {"total_seconds": round(time.perf_counter() - started, 3)},
    }
    write_json(paths["pipeline_summary_json"], pipeline_summary)

    print("=" * 80, flush=True)
    print("BTC backtest AI review pipeline summary", flush=True)
    print(json.dumps({
        "cycle_ok": True,
        "outcome_rows": pipeline_summary["key_metrics"]["outcome_rows"],
        "payload_rows_jsonl": pipeline_summary["key_metrics"]["payload_rows_jsonl"],
        "review_rows_jsonl": pipeline_summary["key_metrics"]["review_rows_jsonl"],
        "review_error_rows": pipeline_summary["key_metrics"].get("review_error_rows"),
        "tag_summary_rows": pipeline_summary["key_metrics"]["tag_summary_rows"],
        "should_investigate_rows": pipeline_summary["key_metrics"].get("should_investigate_rows"),
        "target_tag_summary_rows": pipeline_summary["key_metrics"].get("target_tag_summary_rows"),
        "target_tag_summary_csv": str(paths["target_tag_summary_csv"]),
        "pipeline_summary_json": str(paths["pipeline_summary_json"]),
    }, ensure_ascii=False, indent=2, sort_keys=True), flush=True)
    print("=" * 80, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
