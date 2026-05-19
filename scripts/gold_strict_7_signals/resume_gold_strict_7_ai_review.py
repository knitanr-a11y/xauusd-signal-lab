#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""Resume or summarize partial AI review for GOLD strict 7 backtest.

Use this after run_gold_strict_7_ai_review_pipeline.py partially succeeded and
then stopped because of API quota/rate errors.

This script does not rebuild trades/features/payloads. It uses existing files in:

    data/runtime_logs/trade_ai_review_backtest_gold_strict_7/

Modes:
- --summarize-only:
    summarize the already-written trade_ai_review_ledger.jsonl, even if partial.
- default:
    create trade_ai_review_payloads_pending.jsonl by excluding already-reviewed
    trade_ids/order_keys, call run_trade_ai_review_from_payloads.py on pending
    payloads in append mode, then summarize whatever is available.

Safety:
- No Discord send
- No MT5 call
- No order_send
- No live runtime ledger mutation
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

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT_DIR = Path("data/runtime_logs/trade_ai_review_backtest_gold_strict_7")


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


def ensure_parent(path: str | Path) -> None:
    Path(windows_long_path(Path(path).parent)).mkdir(parents=True, exist_ok=True)


def utc_now_text() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")


def read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path_exists(path):
        return rows
    with open(windows_long_path(path), "r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            text = line.strip()
            if not text:
                continue
            try:
                obj = json.loads(text)
            except Exception as exc:
                raise RuntimeError(f"invalid JSONL line {line_no} in {path}: {exc!r}") from exc
            if isinstance(obj, dict):
                rows.append(obj)
    return rows


def write_jsonl(path: str | Path, rows: list[dict[str, Any]]) -> int:
    ensure_parent(path)
    with open(windows_long_path(path), "w", encoding="utf-8", newline="") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True, default=str) + "\n")
    return len(rows)


def write_json(path: str | Path, obj: dict[str, Any]) -> None:
    ensure_parent(path)
    with open(windows_long_path(path), "w", encoding="utf-8", newline="") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2, sort_keys=True, default=str)


def read_json(path: str | Path) -> dict[str, Any]:
    try:
        with open(windows_long_path(path), "r", encoding="utf-8") as f:
            obj = json.load(f)
        return obj if isinstance(obj, dict) else {}
    except Exception:
        return {}


def clean_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def review_identity(row: dict[str, Any]) -> tuple[str, str, str]:
    trade_id = clean_str(row.get("trade_id"))
    order_key = clean_str(row.get("order_key"))
    payload_key = clean_str(row.get("payload_key"))
    return trade_id, order_key, payload_key


def payload_is_reviewed(payload: dict[str, Any], reviewed: set[tuple[str, str, str]], reviewed_trade_ids: set[str], reviewed_order_keys: set[str], reviewed_payload_keys: set[str]) -> bool:
    trade = payload.get("trade", {}) if isinstance(payload.get("trade"), dict) else {}
    compact = payload.get("compact_features", {}) if isinstance(payload.get("compact_features"), dict) else {}
    trade_id = clean_str(payload.get("trade_id"), clean_str(trade.get("trade_id"), clean_str(compact.get("trade_id"))))
    order_key = clean_str(payload.get("order_key"), clean_str(trade.get("order_key"), clean_str(compact.get("order_key"))))
    payload_key = clean_str(payload.get("payload_key"), clean_str(trade.get("payload_key"), clean_str(compact.get("payload_key"))))
    if (trade_id, order_key, payload_key) in reviewed:
        return True
    if trade_id and trade_id in reviewed_trade_ids:
        return True
    if order_key and order_key in reviewed_order_keys:
        return True
    if payload_key and payload_key in reviewed_payload_keys:
        return True
    return False


def build_pending_payloads(payload_jsonl: Path, review_jsonl: Path, pending_jsonl: Path, *, max_pending: int = 0) -> dict[str, Any]:
    payloads = read_jsonl(payload_jsonl)
    reviews = read_jsonl(review_jsonl)
    reviewed = {review_identity(r) for r in reviews}
    reviewed_trade_ids = {x[0] for x in reviewed if x[0]}
    reviewed_order_keys = {x[1] for x in reviewed if x[1]}
    reviewed_payload_keys = {x[2] for x in reviewed if x[2]}
    pending = [p for p in payloads if not payload_is_reviewed(p, reviewed, reviewed_trade_ids, reviewed_order_keys, reviewed_payload_keys)]
    if max_pending > 0:
        pending = pending[: int(max_pending)]
    write_jsonl(pending_jsonl, pending)
    return {
        "payload_rows": int(len(payloads)),
        "existing_review_rows": int(len(reviews)),
        "pending_rows_written": int(len(pending)),
        "pending_jsonl": str(pending_jsonl),
    }


def run_cmd(label: str, cmd: list[str], *, cwd: Path = REPO_ROOT, allow_failure: bool = False) -> dict[str, Any]:
    print("=" * 80, flush=True)
    print(f"[STEP] {label}", flush=True)
    print("[CMD] " + " ".join(cmd), flush=True)
    started = time.perf_counter()
    proc = subprocess.run(cmd, cwd=str(cwd), text=True, encoding="utf-8", errors="replace")
    elapsed = round(time.perf_counter() - started, 3)
    ok = proc.returncode == 0 or allow_failure
    print(f"[STEP] {label} returncode={proc.returncode} elapsed_seconds={elapsed} ok={ok}", flush=True)
    return {"label": label, "cmd": cmd, "returncode": int(proc.returncode), "elapsed_seconds": elapsed, "allow_failure": bool(allow_failure), "ok": bool(ok)}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Resume or summarize partial GOLD strict 7 AI review.")
    p.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    p.add_argument("--model", default="gpt-5-mini")
    p.add_argument("--max-pending", type=int, default=0, help="0 = all pending payloads")
    p.add_argument("--summarize-only", action="store_true")
    p.add_argument("--allow-partial", action=argparse.BooleanOptionalAction, default=True, help="continue to summary even if resumed AI review still hits quota")
    p.add_argument("--min-sample", type=int, default=5)
    p.add_argument("--dry-run", action="store_true")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    started = time.perf_counter()
    out_dir = Path(args.out_dir)
    paths = {
        "payload_jsonl": out_dir / "trade_ai_review_payloads.jsonl",
        "pending_payload_jsonl": out_dir / "trade_ai_review_payloads_pending.jsonl",
        "review_jsonl": out_dir / "trade_ai_review_ledger.jsonl",
        "review_json": out_dir / "trade_ai_review_resume_run_summary.json",
        "trade_outcome_csv": out_dir / "trade_outcome_ledger.csv",
        "tag_summary_csv": out_dir / "trade_ai_tag_summary.csv",
        "tag_summary_json": out_dir / "trade_ai_tag_summary.json",
        "resume_summary_json": out_dir / "gold_strict_7_ai_review_resume_summary.json",
    }
    if not path_exists(paths["payload_jsonl"]):
        raise SystemExit(f"payload JSONL not found: {paths['payload_jsonl']}")
    if not path_exists(paths["trade_outcome_csv"]):
        raise SystemExit(f"trade outcome CSV not found: {paths['trade_outcome_csv']}")
    if not path_exists(paths["review_jsonl"]):
        raise SystemExit(f"review JSONL not found: {paths['review_jsonl']}")

    steps: list[dict[str, Any]] = []
    pending_summary = build_pending_payloads(paths["payload_jsonl"], paths["review_jsonl"], paths["pending_payload_jsonl"], max_pending=int(args.max_pending))

    if not args.summarize_only and pending_summary["pending_rows_written"] > 0:
        review_cmd = [
            sys.executable,
            str(REPO_ROOT / "scripts" / "run_trade_ai_review_from_payloads.py"),
            "--payload-jsonl", str(paths["pending_payload_jsonl"]),
            "--output-jsonl", str(paths["review_jsonl"]),
            "--output-json", str(paths["review_json"]),
            "--model", str(args.model),
        ]
        # No --overwrite here. We intentionally append pending reviews.
        if args.dry_run:
            review_cmd.append("--dry-run")
        steps.append(run_cmd("run_trade_ai_review_from_payloads_pending_append", review_cmd, allow_failure=bool(args.allow_partial)))
    else:
        print("[INFO] AI review call skipped; summarize_only=True or no pending payloads", flush=True)

    summary_cmd = [
        sys.executable,
        str(REPO_ROOT / "scripts" / "summarize_trade_ai_review_ledger.py"),
        "--trade-outcome-csv", str(paths["trade_outcome_csv"]),
        "--ai-review-jsonl", str(paths["review_jsonl"]),
        "--output-csv", str(paths["tag_summary_csv"]),
        "--output-json", str(paths["tag_summary_json"]),
        "--min-sample", str(args.min_sample),
    ]
    steps.append(run_cmd("summarize_trade_ai_review_ledger_partial_or_complete", summary_cmd, allow_failure=False))
    if not steps[-1]["ok"]:
        return 2

    final_reviews = read_jsonl(paths["review_jsonl"])
    payloads = read_jsonl(paths["payload_jsonl"])
    tag_summary = read_json(paths["tag_summary_json"])
    resume_summary = {
        "schema_version": "gold_strict_7_ai_review_resume_v1",
        "created_at_utc": utc_now_text(),
        "cycle_ok": bool(all(s.get("ok") for s in steps)),
        "summarize_only": bool(args.summarize_only),
        "allow_partial": bool(args.allow_partial),
        "dry_run": bool(args.dry_run),
        "out_dir": str(out_dir),
        "paths": {k: str(v) for k, v in paths.items()},
        "pending_summary_before_resume": pending_summary,
        "final_counts": {
            "payload_rows": int(len(payloads)),
            "review_rows": int(len(final_reviews)),
            "remaining_payload_rows_after_resume": max(0, int(len(payloads)) - int(len(final_reviews))),
            "tag_summary_rows": int(len(read_jsonl(paths["review_jsonl"]))),
            "should_investigate_rows": tag_summary.get("should_investigate_rows"),
        },
        "tag_summary": tag_summary,
        "steps": steps,
        "timing": {"total_seconds": round(time.perf_counter() - started, 3)},
    }
    write_json(paths["resume_summary_json"], resume_summary)
    print("=" * 80, flush=True)
    print("GOLD strict 7 AI review resume summary", flush=True)
    print(json.dumps({
        "cycle_ok": resume_summary["cycle_ok"],
        "payload_rows": resume_summary["final_counts"]["payload_rows"],
        "review_rows": resume_summary["final_counts"]["review_rows"],
        "remaining_payload_rows_after_resume": resume_summary["final_counts"]["remaining_payload_rows_after_resume"],
        "should_investigate_rows": resume_summary["final_counts"].get("should_investigate_rows"),
        "tag_summary_csv": str(paths["tag_summary_csv"]),
        "resume_summary_json": str(paths["resume_summary_json"]),
    }, ensure_ascii=False, indent=2, sort_keys=True), flush=True)
    print("=" * 80, flush=True)
    return 0 if resume_summary["cycle_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
