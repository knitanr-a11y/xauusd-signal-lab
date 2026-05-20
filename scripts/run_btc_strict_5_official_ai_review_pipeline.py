#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""BTC strict-5 official post-trade AI review wrapper.

This wrapper is intentionally thin and safe:
- It targets only the BTC strict-5 official guarded-demo order ledger.
- If the official order ledger does not exist yet, it writes a clear skip summary
  and exits 0 instead of failing noisily.
- If the ledger exists but has no rows, it also skips safely.
- If rows exist, it delegates to run_btc_ai_review_pipeline_same_spec.py.

No orders are placed. MT5 usage is read-only history export inside the delegated
AI-review pipeline. AI output is hypothesis tagging only.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_PIPELINE = REPO_ROOT / "scripts" / "run_btc_ai_review_pipeline_same_spec.py"
DEFAULT_ORDER_LEDGER = Path("data/runtime_state/btc/strict_5/official_guarded_demo_order_ledger.csv")
DEFAULT_OUT_DIR = Path("data/runtime_logs/trade_ai_review_btc_strict_5_official")
DEFAULT_NOT_USED_D1 = Path("data/runtime_state/btc/strict_5/NOT_USED_D1.csv")
SUMMARY_NAME = "btc_strict_5_official_ai_review_pipeline_summary.json"


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


def resolve(path: str | Path) -> Path:
    p = Path(path)
    return p if p.is_absolute() else REPO_ROOT / p


def mkdirp(path: str | Path) -> None:
    Path(windows_long_path(path)).mkdir(parents=True, exist_ok=True)


def write_text(path: str | Path, text: str) -> None:
    p = Path(path)
    mkdirp(p.parent)
    with open(windows_long_path(p), "w", encoding="utf-8", newline="") as f:
        f.write(text)


def write_json(path: str | Path, obj: dict[str, Any]) -> None:
    write_text(path, json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True, default=str))


def utc_now_text() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")


def csv_row_count(path: Path) -> int:
    if not path.exists():
        return 0
    try:
        with open(windows_long_path(path), "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            return sum(1 for _ in reader)
    except Exception:
        return 0


def run_cmd(cmd: list[str]) -> int:
    print("=" * 80, flush=True)
    print("[CMD] " + " ".join(cmd), flush=True)
    proc = subprocess.run(cmd, cwd=str(REPO_ROOT), text=True, encoding="utf-8", errors="replace")
    print(f"[CMD] returncode={proc.returncode}", flush=True)
    return int(proc.returncode)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run BTC strict-5 official post-trade AI review safely.")
    p.add_argument("--order-ledger-csv", type=Path, default=DEFAULT_ORDER_LEDGER)
    p.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    p.add_argument("--model", default="gpt-5-mini")
    p.add_argument("--min-sample", type=int, default=5)
    p.add_argument("--expected-login", type=int, default=75539039)
    p.add_argument("--broker-symbols", default="BTCUSD#")
    p.add_argument("--lookback-days", type=int, default=60)
    p.add_argument("--m15-file", default="btcusdsharp_m15.csv")
    p.add_argument("--m5-file", default="btcusdsharp_m5.csv")
    p.add_argument("--h1-file", default="btcusdsharp_h1.csv")
    p.add_argument("--h4-file", default="btcusdsharp_h4.csv")
    p.add_argument("--d1-csv", type=Path, default=DEFAULT_NOT_USED_D1)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--max-review-items", type=int, default=0)
    p.add_argument("--strict-missing-ledger", action="store_true", help="Return non-zero when the official order ledger is missing.")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    started = time.perf_counter()
    order_ledger = resolve(args.order_ledger_csv)
    out_dir = resolve(args.out_dir)
    d1_csv = resolve(args.d1_csv)
    mkdirp(out_dir)
    summary_path = out_dir / SUMMARY_NAME

    print("=" * 80, flush=True)
    print("BTC strict 5 official post-trade AI review wrapper", flush=True)
    print(f"order_ledger={order_ledger}", flush=True)
    print(f"out_dir={out_dir}", flush=True)
    print("D1: NOT_USED", flush=True)
    print("Safety: no order_send / MT5 history read-only / AI hypothesis only", flush=True)
    print("=" * 80, flush=True)

    if not order_ledger.exists():
        summary = {
            "schema_version": "btc_strict_5_official_ai_review_wrapper_v1",
            "created_at_utc": utc_now_text(),
            "cycle_ok": True,
            "status": "NO_ORDER_LEDGER_YET",
            "reason": "BTC strict 5 official guarded demo send has not created an order ledger yet.",
            "order_ledger_csv": str(order_ledger),
            "out_dir": str(out_dir),
            "ai_called": False,
            "mt5_history_export_called": False,
            "orders_sent": False,
            "elapsed_seconds": round(time.perf_counter() - started, 3),
        }
        write_json(summary_path, summary)
        print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True), flush=True)
        return 2 if args.strict_missing_ledger else 0

    order_rows = csv_row_count(order_ledger)
    if order_rows <= 0:
        summary = {
            "schema_version": "btc_strict_5_official_ai_review_wrapper_v1",
            "created_at_utc": utc_now_text(),
            "cycle_ok": True,
            "status": "ORDER_LEDGER_EMPTY",
            "reason": "Order ledger exists but has no rows to evaluate.",
            "order_ledger_csv": str(order_ledger),
            "order_rows": int(order_rows),
            "out_dir": str(out_dir),
            "ai_called": False,
            "mt5_history_export_called": False,
            "orders_sent": False,
            "elapsed_seconds": round(time.perf_counter() - started, 3),
        }
        write_json(summary_path, summary)
        print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True), flush=True)
        return 0

    cmd = [
        sys.executable, str(BASE_PIPELINE),
        "--out-dir", str(out_dir),
        "--model", str(args.model),
        "--min-sample", str(args.min_sample),
    ]
    if args.dry_run:
        cmd.append("--dry-run")
    if args.max_review_items > 0:
        cmd.extend(["--max-review-items", str(args.max_review_items)])
    cmd.extend([
        "--",
        "--order-ledger-csv", str(order_ledger),
        "--broker-symbols", str(args.broker_symbols),
        "--expected-login", str(args.expected_login),
        "--lookback-days", str(args.lookback_days),
        "--m15-file", str(args.m15_file),
        "--m5-file", str(args.m5_file),
        "--h1-file", str(args.h1_file),
        "--h4-file", str(args.h4_file),
        "--d1-csv", str(d1_csv),
    ])
    rc = run_cmd(cmd)
    summary = {
        "schema_version": "btc_strict_5_official_ai_review_wrapper_v1",
        "created_at_utc": utc_now_text(),
        "cycle_ok": rc == 0,
        "status": "PIPELINE_RAN" if rc == 0 else "PIPELINE_FAILED",
        "returncode": int(rc),
        "order_ledger_csv": str(order_ledger),
        "order_rows": int(order_rows),
        "out_dir": str(out_dir),
        "delegated_summary_json": str(out_dir / "btc_ai_review_pipeline_same_spec_summary.json"),
        "tag_summary_csv": str(out_dir / "trade_ai_tag_summary.csv"),
        "ai_called": not bool(args.dry_run),
        "orders_sent": False,
        "d1_used": False,
        "elapsed_seconds": round(time.perf_counter() - started, 3),
    }
    write_json(summary_path, summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True), flush=True)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
