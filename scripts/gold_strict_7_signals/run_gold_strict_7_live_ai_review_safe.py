#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Safe launcher for GOLD strict 7 live AI review.

If the strict 7 order ledger does not exist yet, this exits successfully with a
clear NO_ORDER_LEDGER_YET summary. Otherwise it delegates to the full live AI
review pipeline with the original arguments.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
PIPELINE = REPO_ROOT / "scripts" / "gold_strict_7_signals" / "run_gold_strict_7_live_ai_review_pipeline.py"
DEFAULT_OUT_DIR = Path("data/runtime_logs/trade_ai_review_live_gold_strict_7")
DEFAULT_LEDGER = Path("data/runtime_state/gold/strict_7/guarded_demo_order_ledger.csv")
SCHEMA_VERSION = "gold_strict_7_live_ai_review_safe_v1"


def wpath(path: str | Path) -> str:
    p = Path(path)
    if os.name != "nt":
        return str(p)
    text = str(p.resolve())
    if text.startswith("\\\\?\\"):
        return text
    if text.startswith("\\\\"):
        return "\\\\?\\UNC\\" + text.lstrip("\\")
    return "\\\\?\\" + text


def exists(path: str | Path) -> bool:
    return Path(wpath(path)).exists()


def mkdirp(path: str | Path) -> None:
    Path(wpath(path)).mkdir(parents=True, exist_ok=True)


def utc_now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")


def write_json(path: Path, obj: dict[str, Any]) -> None:
    mkdirp(path.parent)
    with open(wpath(path), "w", encoding="utf-8", newline="") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2, sort_keys=True, default=str)


def write_text(path: Path, text: str) -> None:
    mkdirp(path.parent)
    with open(wpath(path), "w", encoding="utf-8", newline="") as f:
        f.write(text)


def parse_args() -> tuple[argparse.Namespace, list[str]]:
    p = argparse.ArgumentParser(add_help=False)
    p.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    p.add_argument("--order-ledger-csv", type=Path, default=DEFAULT_LEDGER)
    return p.parse_known_args()


def main() -> int:
    args, unknown = parse_args()
    out_dir = args.out_dir
    summary_json = out_dir / "gold_strict_7_live_ai_review_pipeline_summary.json"
    review_jsonl = out_dir / "trade_ai_review_ledger.jsonl"
    pending_jsonl = out_dir / "trade_ai_review_payloads_pending.jsonl"
    tag_csv = out_dir / "trade_ai_tag_summary.csv"

    if not exists(args.order_ledger_csv):
        mkdirp(out_dir)
        if not exists(review_jsonl):
            write_text(review_jsonl, "")
        if not exists(pending_jsonl):
            write_text(pending_jsonl, "")
        if not exists(tag_csv):
            write_text(tag_csv, "")
        summary = {
            "schema_version": SCHEMA_VERSION,
            "created_at_utc": utc_now(),
            "cycle_ok": True,
            "reason": "NO_ORDER_LEDGER_YET",
            "order_ledger_csv": str(args.order_ledger_csv),
            "out_dir": str(out_dir),
            "key_metrics": {
                "outcome_rows": 0,
                "reviewable_closed_rows": 0,
                "payload_rows": 0,
                "pending_rows": 0,
                "skipped_already_reviewed_rows": 0,
                "review_rows_final": 0,
                "review_rows_written_this_run": 0,
                "review_error_rows": 0,
                "tag_summary_rows": 0,
                "should_investigate_rows": 0,
            },
            "note": "strict 7 order ledger has not been created yet; no completed trades are available for live AI review",
        }
        write_json(summary_json, summary)
        print("GOLD strict 7 live AI review safe")
        print("cycle_ok: True")
        print("reason: NO_ORDER_LEDGER_YET")
        print(f"order_ledger_csv: {args.order_ledger_csv}")
        print(f"summary_json: {summary_json}")
        return 0

    cmd = [sys.executable, str(PIPELINE), "--out-dir", str(out_dir), "--order-ledger-csv", str(args.order_ledger_csv), *unknown]
    print("GOLD strict 7 live AI review safe")
    print("order ledger found; delegating to full pipeline")
    print("CMD: " + " ".join(cmd))
    proc = subprocess.run(cmd, cwd=str(REPO_ROOT), text=True, encoding="utf-8", errors="replace")
    return int(proc.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
