#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""Run DISC8 OpenAI reviews with visible progress and incremental writes.

Why this exists:
- The generic runner prints summary at the end, which makes long all-night runs look stalled.
- This DISC8 runner prints START/OK/ERROR per payload.
- It appends one review immediately after each successful model response.
- If interrupted, rerun the wrapper pipeline; pending-only logic will skip completed payloads.

Safety:
- HYPOTHESIS_TAGGING_ONLY review contract is inherited from payloads.
- The normalized output still forces should_change_strategy_from_this_single_trade=False.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from run_trade_ai_review_from_payloads import (  # type: ignore
    call_openai,
    default_model_after_dotenv,
    dry_run_review,
    load_dotenv_if_present,
    normalize_review,
)
from trade_ai_review_utils import (  # type: ignore
    append_jsonl,
    clean_str,
    read_jsonl,
    utc_now_text,
    write_json,
    write_jsonl,
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run DISC8 AI reviews with progress and incremental output.")
    p.add_argument("--payload-jsonl", required=True)
    p.add_argument("--output-jsonl", required=True)
    p.add_argument("--output-json", default="")
    p.add_argument("--env-file", default="", help="Optional .env path. Default searches current directory and repo root.")
    p.add_argument("--no-dotenv", action="store_true", help="Do not load OPENAI_* values from .env.")
    p.add_argument("--dotenv-override", action="store_true", help="Allow .env to override existing OPENAI_* environment variables.")
    p.add_argument("--model", default="", help="Default: OPENAI_MODEL from env/.env, else gpt-5-mini.")
    p.add_argument("--max-items", type=int, default=0, help="0 = all")
    p.add_argument("--dry-run", action="store_true", help="Write deterministic placeholder reviews without calling OpenAI.")
    p.add_argument("--overwrite", action="store_true", help="Overwrite output JSONL before the run.")
    p.add_argument("--temperature", type=float, default=None, help="Optional. Omitted by default.")
    p.add_argument("--progress-every", type=int, default=1, help="Print progress every N rows. 1 = every row.")
    args = p.parse_args()
    if not args.no_dotenv:
        args.dotenv_report = load_dotenv_if_present(args.env_file, override=bool(args.dotenv_override))
    else:
        args.dotenv_report = {
            "dotenv_loaded": False,
            "dotenv_path": "",
            "dotenv_checked_paths": [],
            "dotenv_loaded_keys": [],
            "openai_api_key_present": bool(os.environ.get("OPENAI_API_KEY")),
            "openai_model_from_env_present": bool(os.environ.get("OPENAI_MODEL")),
        }
    if not args.model:
        args.model = default_model_after_dotenv()
    return args


def progress(i: int, total: int, message: str, every: int) -> None:
    if every <= 0:
        return
    if i == 1 or i == total or i % every == 0:
        now = utc_now_text()
        print(f"[DISC8_AI_PROGRESS] {now} {i}/{total} {message}", flush=True)


def main() -> int:
    args = parse_args()
    payloads = read_jsonl(Path(args.payload_jsonl))
    if args.max_items and args.max_items > 0:
        payloads = payloads[: int(args.max_items)]
    total = int(len(payloads))

    output_jsonl = Path(args.output_jsonl)
    if args.overwrite:
        write_jsonl(output_jsonl, [])

    run_mode = "DRY_RUN" if args.dry_run else "OPENAI_API"
    print("=" * 80, flush=True)
    print("DISC8 progress AI review runner", flush=True)
    print(f"payload_jsonl={args.payload_jsonl}", flush=True)
    print(f"output_jsonl={args.output_jsonl}", flush=True)
    print(f"rows_in={total}", flush=True)
    print(f"run_mode={run_mode}", flush=True)
    print(f"model={args.model}", flush=True)
    print(f"dotenv_loaded={getattr(args, 'dotenv_report', {}).get('dotenv_loaded')}", flush=True)
    print(f"openai_api_key_present={getattr(args, 'dotenv_report', {}).get('openai_api_key_present')}", flush=True)
    print("=" * 80, flush=True)

    rows_written_this_run = 0
    errors: list[dict[str, Any]] = []
    t0 = time.perf_counter()

    for i, payload in enumerate(payloads, start=1):
        trade_id = clean_str(payload.get("trade_id"))
        strategy_id = clean_str((payload.get("trade") or {}).get("strategy_id")) if isinstance(payload.get("trade"), dict) else ""
        outcome = clean_str((payload.get("trade") or {}).get("outcome")) if isinstance(payload.get("trade"), dict) else ""
        progress(i, total, f"START trade_id={trade_id} strategy={strategy_id} outcome={outcome}", int(args.progress_every))
        one_t0 = time.perf_counter()
        try:
            if args.dry_run:
                review = dry_run_review(payload, model=args.model)
            else:
                raw_review, raw_response = call_openai(payload, model=args.model, temperature=args.temperature)
                review = normalize_review(raw_review, payload, model=args.model, run_mode="OPENAI_API", raw_response=raw_response)
            append_jsonl(output_jsonl, [review])
            rows_written_this_run += 1
            elapsed_one = round(time.perf_counter() - one_t0, 3)
            progress(i, total, f"OK trade_id={trade_id} elapsed_seconds={elapsed_one}", int(args.progress_every))
        except Exception as exc:
            elapsed_one = round(time.perf_counter() - one_t0, 3)
            err = {
                "created_at_utc": utc_now_text(),
                "row_index": i,
                "trade_id": trade_id,
                "strategy_id": strategy_id,
                "outcome": outcome,
                "run_mode": run_mode,
                "elapsed_seconds": elapsed_one,
                "error": repr(exc),
            }
            errors.append(err)
            print(f"[DISC8_AI_ERROR] {i}/{total} trade_id={trade_id} elapsed_seconds={elapsed_one} error={repr(exc)}", flush=True)

    total_elapsed = round(time.perf_counter() - t0, 3)
    final_total_file_rows = int(len(read_jsonl(output_jsonl)))
    dotenv_report = dict(getattr(args, "dotenv_report", {}))
    summary = {
        "script": "run_disc8_trade_ai_review_from_payloads_progress.py",
        "created_at_utc": utc_now_text(),
        "payload_jsonl": args.payload_jsonl,
        "output_jsonl": args.output_jsonl,
        "output_mode": "overwrite_then_incremental_append" if args.overwrite else "incremental_append",
        "model": args.model,
        "temperature_sent": args.temperature is not None,
        "temperature": args.temperature,
        "dry_run": bool(args.dry_run),
        "run_mode": run_mode,
        "dotenv": dotenv_report,
        "rows_in": total,
        "rows_written_this_run": int(rows_written_this_run),
        "rows_written_total_file": final_total_file_rows,
        "error_rows": int(len(errors)),
        "errors": errors,
        "elapsed_seconds": total_elapsed,
    }
    if args.output_json:
        write_json(Path(args.output_json), summary)

    print("=" * 80, flush=True)
    print("DISC8 progress AI review runner summary", flush=True)
    print(f"rows_in={summary['rows_in']}", flush=True)
    print(f"rows_written_this_run={summary['rows_written_this_run']}", flush=True)
    print(f"rows_written_total_file={summary['rows_written_total_file']}", flush=True)
    print(f"error_rows={summary['error_rows']}", flush=True)
    print(f"elapsed_seconds={summary['elapsed_seconds']}", flush=True)
    print(f"output_jsonl={args.output_jsonl}", flush=True)
    print(f"output_json={args.output_json}", flush=True)
    print("=" * 80, flush=True)
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
