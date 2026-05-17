#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""Run BTC trade AI review pipeline using the same architecture as GOLD.

This is the BTC counterpart of the GOLD AI review pipeline:
1. Export read-only MT5 closed trade history for BTC broker symbols.
2. Build deterministic trade_outcome_ledger.csv from one or more BTC order ledgers.
3. Normalize BTC symbol labels to BTC for review/tag grouping.
4. Build feature snapshots with pre-entry M15=100 bars and post-entry M15=20 bars.
5. Build OpenAI-ready AI review payloads.
6. Run AI review from payloads using OPENAI_API_KEY from .env unless --dry-run.
7. Summarize AI hypothesis tags into trade_ai_tag_summary.csv.

Safety:
- Does not place, modify, or close orders.
- Does not edit strategy rules.
- AI output is hypothesis tagging only.
- should_change_strategy_from_this_single_trade is forced False by the review runner.

Default order ledger:
- data/runtime_state/btc/multi_strategy/guarded_demo_order_ledger.csv

Optional manual BTC smoke-test ledgers can be added with --include-manual-ledgers
or explicit --order-ledger-csv arguments.
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
DEFAULT_OUT_DIR = Path("data/runtime_logs/trade_ai_review_btc")
DEFAULT_BTC_MULTI_LEDGER = Path("data/runtime_state/btc/multi_strategy/guarded_demo_order_ledger.csv")
MANUAL_BTC_LEDGERS = [
    Path("data/r/btc_manual_demo_order_send_smoke_test/btc_manual_demo_order_ledger.csv"),
    Path("data/r/btc_manual_demo_order_send_smoke_test_send_once/btc_manual_demo_send_once_order_ledger.csv"),
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


def read_csv_len(path: Path) -> int:
    if not path_exists(path):
        return 0
    try:
        return int(len(read_csv(path)))
    except Exception:
        return 0


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


def parse_order_ledgers(values: list[str], *, include_manual_ledgers: bool) -> list[Path]:
    if values:
        paths = [Path(v) for v in values]
    else:
        paths = [DEFAULT_BTC_MULTI_LEDGER]
    if include_manual_ledgers:
        for ledger in MANUAL_BTC_LEDGERS:
            if ledger not in paths:
                paths.append(ledger)
    return paths


def existing_order_ledgers(paths: list[Path], *, allow_missing: bool) -> tuple[list[Path], list[str]]:
    existing: list[Path] = []
    missing: list[str] = []
    for path in paths:
        if path_exists(path):
            existing.append(path)
        else:
            missing.append(str(path))
    if missing and not allow_missing:
        raise FileNotFoundError("missing order ledger(s): " + ", ".join(missing))
    return existing, missing


def csv_path(csv_dir: Path, explicit: str, filename: str) -> str:
    if explicit:
        return explicit
    return str(csv_dir / filename)


def optional_existing_csv(path_text: str) -> str:
    return path_text if path_text and path_exists(Path(path_text)) else ""


def normalize_btc_symbol_text(value: Any) -> str:
    text = str(value or "").upper().strip()
    return "BTC" if text.startswith("BTC") else text


def normalize_btc_outcome_symbols(path: Path) -> None:
    if not path_exists(path):
        return
    df = read_csv(path)
    if df.empty:
        return
    if "symbol" in df.columns:
        df["symbol"] = df["symbol"].map(normalize_btc_symbol_text)
    if "broker_symbol" in df.columns:
        if "symbol" not in df.columns:
            df["symbol"] = df["broker_symbol"].map(normalize_btc_symbol_text)
        else:
            blank = df["symbol"].astype(str).str.strip().eq("")
            df.loc[blank, "symbol"] = df.loc[blank, "broker_symbol"].map(normalize_btc_symbol_text)
    write_csv(df, path)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run unified BTC AI review pipeline.")
    p.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    p.add_argument("--mql5-files-dir", type=Path, default=DEFAULT_MQL5_FILES_DIR)
    p.add_argument("--order-ledger-csv", action="append", default=[], help="BTC order ledger CSV. Repeat to override defaults.")
    p.add_argument("--include-manual-ledgers", action="store_true", help="Also include older BTC manual smoke-test ledgers.")
    p.add_argument("--allow-missing-order-ledger", action="store_true")
    p.add_argument("--expected-login", type=int, default=75539039)
    p.add_argument("--broker-symbols", default="BTCUSD#", help="BTC broker symbols for MT5 history export, comma-separated.")
    p.add_argument("--lookback-days", type=int, default=60)
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
    p.add_argument("--min-sample", type=int, default=5)
    p.add_argument("--model", default="gpt-5-mini")
    p.add_argument("--max-review-items", type=int, default=0, help="0 = all payloads")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--overwrite-review-jsonl", action=argparse.BooleanOptionalAction, default=True)
    p.add_argument("--skip-mt5-export", action="store_true", help="Use existing mt5_history/*.csv files.")
    p.add_argument("--skip-ai-review", action="store_true", help="Build outcome/features/payloads/summary from existing review ledger without API call.")
    p.add_argument("--include-open-trades-in-summary", action="store_true")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    started = time.perf_counter()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    mt5_dir = args.out_dir / "mt5_history"
    paths = {
        "mt5_dir": mt5_dir,
        "mt5_positions_csv": mt5_dir / "mt5_history_positions.csv",
        "mt5_deals_csv": mt5_dir / "mt5_history_deals.csv",
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
        "pipeline_summary_json": args.out_dir / "btc_ai_review_pipeline_summary.json",
    }
    for pth in paths.values():
        pth.parent.mkdir(parents=True, exist_ok=True)

    requested_ledgers = parse_order_ledgers(args.order_ledger_csv, include_manual_ledgers=bool(args.include_manual_ledgers))
    order_ledgers, missing_ledgers = existing_order_ledgers(requested_ledgers, allow_missing=bool(args.allow_missing_order_ledger))
    if not order_ledgers:
        raise SystemExit("No existing BTC order ledger CSVs found. Expected default: data/runtime_state/btc/multi_strategy/guarded_demo_order_ledger.csv")

    m15_csv = csv_path(args.mql5_files_dir, args.m15_csv, args.m15_file)
    m5_csv = csv_path(args.mql5_files_dir, args.m5_csv, args.m5_file)
    h1_csv = csv_path(args.mql5_files_dir, args.h1_csv, args.h1_file)
    h4_csv = csv_path(args.mql5_files_dir, args.h4_csv, args.h4_file)
    d1_csv = csv_path(args.mql5_files_dir, args.d1_csv, args.d1_file)
    if not path_exists(Path(m15_csv)):
        raise SystemExit(f"BTC M15 CSV not found: {m15_csv}. Pass --m15-csv with the actual BTC M15 file.")
    steps: list[dict[str, Any]] = []

    print("=" * 80, flush=True)
    print("Unified BTC AI review pipeline", flush=True)
    print(f"out_dir={args.out_dir}", flush=True)
    print(f"order_ledgers={[str(p) for p in order_ledgers]}", flush=True)
    if missing_ledgers:
        print(f"missing_order_ledgers_allowed={missing_ledgers}", flush=True)
    print(f"m15_csv={m15_csv}", flush=True)
    print(f"m5_csv={optional_existing_csv(m5_csv)}", flush=True)
    print(f"h1_csv={optional_existing_csv(h1_csv)}", flush=True)
    print(f"h4_csv={optional_existing_csv(h4_csv)}", flush=True)
    print(f"d1_csv={optional_existing_csv(d1_csv)}", flush=True)
    print(f"dry_run={args.dry_run} skip_ai_review={args.skip_ai_review}", flush=True)
    print("=" * 80, flush=True)

    if not args.skip_mt5_export:
        steps.append(run_cmd("export_mt5_closed_trade_history", [
            sys.executable, str(REPO_ROOT / "scripts" / "export_mt5_closed_trade_history.py"),
            "--out-dir", str(paths["mt5_dir"]),
            "--lookback-days", str(args.lookback_days),
            "--symbols", str(args.broker_symbols),
            "--expected-login", str(args.expected_login),
        ]))
        if not steps[-1]["ok"]:
            raise SystemExit(1)
    else:
        print("[INFO] skip_mt5_export=True; using existing MT5 history CSVs", flush=True)

    if not path_exists(paths["mt5_positions_csv"]):
        raise SystemExit(f"MT5 positions CSV not found: {paths['mt5_positions_csv']}")

    outcome_cmd = [sys.executable, str(REPO_ROOT / "scripts" / "build_trade_outcome_ledger_from_order_ledger.py")]
    for ledger in order_ledgers:
        outcome_cmd.extend(["--order-ledger-csv", str(ledger)])
    outcome_cmd.extend([
        "--mt5-positions-csv", str(paths["mt5_positions_csv"]),
        "--mt5-deals-csv", str(paths["mt5_deals_csv"]),
        "--output-csv", str(paths["trade_outcome_csv"]),
        "--output-json", str(paths["trade_outcome_json"]),
    ])
    steps.append(run_cmd("build_trade_outcome_ledger", outcome_cmd))
    if not steps[-1]["ok"]:
        raise SystemExit(1)
    normalize_btc_outcome_symbols(paths["trade_outcome_csv"])

    snapshot_cmd = [
        sys.executable, str(REPO_ROOT / "scripts" / "build_trade_feature_snapshots.py"),
        "--trade-outcome-csv", str(paths["trade_outcome_csv"]),
        "--m15-csv", str(m15_csv),
        "--output-csv", str(paths["feature_snapshot_csv"]),
        "--output-jsonl", str(paths["feature_snapshot_jsonl"]),
        "--output-json", str(paths["feature_snapshot_json"]),
        "--pre-m15-bars", "100",
        "--post-m15-bars", "20",
    ]
    if optional_existing_csv(m5_csv):
        snapshot_cmd.extend(["--m5-csv", str(m5_csv)])
    if optional_existing_csv(h1_csv):
        snapshot_cmd.extend(["--h1-csv", str(h1_csv)])
    if optional_existing_csv(h4_csv):
        snapshot_cmd.extend(["--h4-csv", str(h4_csv)])
    if optional_existing_csv(d1_csv):
        snapshot_cmd.extend(["--d1-csv", str(d1_csv)])
    steps.append(run_cmd("build_trade_feature_snapshots", snapshot_cmd))
    if not steps[-1]["ok"]:
        raise SystemExit(1)

    steps.append(run_cmd("build_trade_ai_review_payloads", [
        sys.executable, str(REPO_ROOT / "scripts" / "build_trade_ai_review_payloads.py"),
        "--feature-snapshot-jsonl", str(paths["feature_snapshot_jsonl"]),
        "--output-jsonl", str(paths["payload_jsonl"]),
        "--output-json", str(paths["payload_json"]),
        "--max-pre-m15-bars-in-prompt", "100",
        "--max-post-m15-bars-in-prompt", "20",
    ]))
    if not steps[-1]["ok"]:
        raise SystemExit(1)

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
            raise SystemExit(1)
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
        raise SystemExit(1)

    outcome_summary = read_json(paths["trade_outcome_json"])
    review_summary = read_json(paths["review_json"])
    tag_summary = read_json(paths["tag_summary_json"])
    pipeline_summary = {
        "schema_version": "btc_ai_review_pipeline_v2_multi_strategy_default",
        "created_at_utc": utc_now_text(),
        "cycle_ok": True,
        "out_dir": str(args.out_dir),
        "order_ledgers": [str(p) for p in order_ledgers],
        "missing_order_ledgers": missing_ledgers,
        "paths": {k: str(v) for k, v in paths.items()},
        "inputs": {
            "m15_csv": m15_csv,
            "m5_csv": optional_existing_csv(m5_csv),
            "h1_csv": optional_existing_csv(h1_csv),
            "h4_csv": optional_existing_csv(h4_csv),
            "d1_csv": optional_existing_csv(d1_csv),
            "broker_symbols": args.broker_symbols,
            "lookback_days": int(args.lookback_days),
        },
        "key_metrics": {
            "outcome_rows": read_csv_len(paths["trade_outcome_csv"]),
            "outcome_matched_rows": outcome_summary.get("matched_rows"),
            "outcome_unmatched_rows": outcome_summary.get("unmatched_rows"),
            "feature_snapshot_rows": read_csv_len(paths["feature_snapshot_csv"]),
            "payload_rows": read_csv_len(paths["payload_jsonl"]),
            "review_rows_written": review_summary.get("rows_written"),
            "review_error_rows": review_summary.get("error_rows"),
            "tag_summary_rows": read_csv_len(paths["tag_summary_csv"]),
            "should_investigate_rows": tag_summary.get("should_investigate_rows"),
        },
        "safety": {
            "orders_sent": False,
            "mt5_history_read_only": True,
            "strategy_rules_modified": False,
            "ai_hypothesis_only": True,
            "single_trade_rule_change_allowed": False,
        },
        "steps": steps,
        "timing": {"total_seconds": round(time.perf_counter() - started, 3)},
    }
    write_json(paths["pipeline_summary_json"], pipeline_summary)

    print("=" * 80, flush=True)
    print("Unified BTC AI review pipeline summary", flush=True)
    print(json.dumps({
        "cycle_ok": True,
        "outcome_rows": pipeline_summary["key_metrics"]["outcome_rows"],
        "outcome_matched_rows": pipeline_summary["key_metrics"].get("outcome_matched_rows"),
        "payload_rows": pipeline_summary["key_metrics"]["payload_rows"],
        "review_rows_written": pipeline_summary["key_metrics"].get("review_rows_written"),
        "review_error_rows": pipeline_summary["key_metrics"].get("review_error_rows"),
        "tag_summary_rows": pipeline_summary["key_metrics"]["tag_summary_rows"],
        "should_investigate_rows": pipeline_summary["key_metrics"].get("should_investigate_rows"),
        "tag_summary_csv": str(paths["tag_summary_csv"]),
        "pipeline_summary_json": str(paths["pipeline_summary_json"]),
    }, ensure_ascii=False, indent=2, sort_keys=True), flush=True)
    print("=" * 80, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
