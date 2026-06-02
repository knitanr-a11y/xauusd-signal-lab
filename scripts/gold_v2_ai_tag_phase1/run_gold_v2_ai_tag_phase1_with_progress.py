#!/usr/bin/env python3
"""
GOLD V2 AI tag Phase 1 runner with progress logging.

Intended path usage from the clean GitHub clone:
  scripts/gold_v2_ai_tag_phase1/bat/02_RUN_AI_TAG_PHASE1.bat

Outputs are intentionally written outside the repository, normally:
  Files/FX_OUTPUTS/gold_v2_ai_tag_phase1/

This script:
- reads an existing .env file, but only uses OPENAI_API_KEY / OPENAI_MODEL if present
- does NOT use Discord webhook values
- does NOT send MT5 orders
- writes progress to console and log file
- writes output incrementally so partial progress is not lost
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

SYSTEM_PROMPT = """
You are a live-like XAUUSD signal risk tagger. You receive only information available at signal time.
You must not use future outcome, exit result, or profit. Assign concise risk/quality tags and stack permission.
Return strict JSON matching the schema. Do not write analysis outside JSON.

Decision policy:
- BLOCK only when the snapshot shows severe risk.
- REVIEW when risk is notable but not enough for BLOCK.
- ALLOW when acceptable.
- stack_permission must be no more aggressive than CAP_3 unless this is explicitly audit-only.
- For MID_MIXED SELL, high same_direction_count, high confluence crowding, or low origin diversity, prefer CAP_1/CAP_2/CAP_3 or REVIEW/BLOCK depending on severity.
""".strip()

OUTPUT_COLUMNS = [
    "snapshot_id",
    "api_status",
    "api_error",
    "elapsed_sec",
    "model",
    "decision",
    "stack_permission",
    "risk_score",
    "confidence",
    "quality_tags",
    "risk_tags",
    "block_tags",
    "reason_code",
    "reason_short",
    "raw_json",
]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run GOLD V2 AI tag Phase 1 with progress logging.")
    p.add_argument("--input", required=True, help="Path to gold_v2_ai_phase1_input_snapshots.csv")
    p.add_argument("--schema", required=True, help="Path to gold_v2_ai_tag_schema.json")
    p.add_argument("--output", required=True, help="Path to output AI tag CSV")
    p.add_argument("--env-file", default="", help="Optional .env file path. Only OPENAI_API_KEY/OPENAI_MODEL are used.")
    p.add_argument("--model", default="", help="OpenAI model. If omitted, uses OPENAI_MODEL or gpt-5-mini.")
    p.add_argument("--timeout-sec", type=float, default=8.0)
    p.add_argument("--sleep-sec", type=float, default=0.2)
    p.add_argument("--max-rows", type=int, default=0, help="0 means all rows")
    p.add_argument("--resume", action="store_true", help="Skip snapshot_ids already present in output CSV")
    p.add_argument("--dry-run", action="store_true", help="No API call. Writes REVIEW/CAP_3 placeholders.")
    p.add_argument("--log-file", default="", help="Optional log file path")
    return p.parse_args()


def now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def log_line(message: str, log_path: Optional[Path] = None) -> None:
    text = f"[{now_text()}] {message}"
    print(text, flush=True)
    if log_path:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(text + "\n")


def load_dotenv_file(path: str, log_path: Optional[Path] = None) -> None:
    if not path:
        return
    env_path = Path(path)
    if not env_path.exists():
        log_line(f"WARN .env file not found: {env_path}", log_path)
        return
    line_re = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)\s*$")
    loaded_keys: List[str] = []
    with open(env_path, "r", encoding="utf-8-sig") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            m = line_re.match(line)
            if not m:
                continue
            key, val = m.group(1), m.group(2)
            if key not in {"OPENAI_API_KEY", "OPENAI_MODEL"}:
                # Explicitly ignore Discord/MT5/etc. Never print secret values.
                continue
            if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                val = val[1:-1]
            if key not in os.environ or not os.environ.get(key):
                os.environ[key] = val
                loaded_keys.append(key)
    if loaded_keys:
        log_line(f"Loaded from .env: {', '.join(loaded_keys)}", log_path)
    else:
        log_line("No OPENAI_API_KEY/OPENAI_MODEL loaded from .env, or already set in environment.", log_path)


def load_schema(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        obj = json.load(f)
    if "schema" not in obj or "name" not in obj:
        raise ValueError("schema file must contain {name, schema, strict}")
    return obj


def response_to_text(resp: Any) -> str:
    if hasattr(resp, "output_text") and resp.output_text:
        return str(resp.output_text)
    if isinstance(resp, dict) and resp.get("output_text"):
        return str(resp["output_text"])

    out = getattr(resp, "output", None) or (resp.get("output") if isinstance(resp, dict) else None)
    if out:
        parts: List[str] = []
        for item in out:
            content = getattr(item, "content", None) or (item.get("content") if isinstance(item, dict) else None)
            if not content:
                continue
            for c in content:
                txt = getattr(c, "text", None) or (c.get("text") if isinstance(c, dict) else None)
                if txt:
                    parts.append(str(txt))
        if parts:
            return "".join(parts)
    raise RuntimeError("Could not extract output text from OpenAI response")


def call_openai(prompt_text: str, schema_obj: Dict[str, Any], model: str, timeout_sec: float) -> Dict[str, Any]:
    from openai import OpenAI

    client = OpenAI(timeout=timeout_sec)
    resp = client.responses.create(
        model=model,
        input=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt_text},
        ],
        text={
            "format": {
                "type": "json_schema",
                "name": schema_obj["name"],
                "schema": schema_obj["schema"],
                "strict": bool(schema_obj.get("strict", True)),
            }
        },
        max_output_tokens=280,
        temperature=0,
    )
    txt = response_to_text(resp)
    return json.loads(txt)


def fallback_block(snapshot_id: str, reason: str) -> Dict[str, Any]:
    return {
        "snapshot_id": snapshot_id,
        "decision": "BLOCK",
        "stack_permission": "BLOCK",
        "risk_score": 5,
        "confidence": 0.0,
        "quality_tags": [],
        "risk_tags": [],
        "block_tags": ["BLOCK_FAKE_CONFLUENCE"],
        "reason_code": "BLOCK_DUE_TO_API_ERROR_OR_TIMEOUT",
        "reason_short": reason[:180],
    }


def normalize_result(result: Dict[str, Any], snapshot_id: str, model: str, status: str, error: str, elapsed: float) -> Dict[str, Any]:
    result = dict(result)
    result.setdefault("snapshot_id", snapshot_id)
    result.setdefault("decision", "REVIEW")
    result.setdefault("stack_permission", "CAP_3")
    result.setdefault("risk_score", 0)
    result.setdefault("confidence", 0.0)
    result.setdefault("quality_tags", [])
    result.setdefault("risk_tags", [])
    result.setdefault("block_tags", [])
    result.setdefault("reason_code", "REVIEW_MIXED_CONTEXT")
    result.setdefault("reason_short", "")
    raw_json = json.dumps(result, ensure_ascii=False)
    return {
        "snapshot_id": str(result.get("snapshot_id", snapshot_id)),
        "api_status": status,
        "api_error": error,
        "elapsed_sec": round(elapsed, 4),
        "model": model,
        "decision": str(result.get("decision", "REVIEW")),
        "stack_permission": str(result.get("stack_permission", "CAP_3")),
        "risk_score": result.get("risk_score", 0),
        "confidence": result.get("confidence", 0.0),
        "quality_tags": json.dumps(result.get("quality_tags", []), ensure_ascii=False),
        "risk_tags": json.dumps(result.get("risk_tags", []), ensure_ascii=False),
        "block_tags": json.dumps(result.get("block_tags", []), ensure_ascii=False),
        "reason_code": str(result.get("reason_code", "")),
        "reason_short": str(result.get("reason_short", "")),
        "raw_json": raw_json,
    }


def read_done_snapshot_ids(output_path: Path) -> set[str]:
    if not output_path.exists():
        return set()
    try:
        df = pd.read_csv(output_path)
        if "snapshot_id" not in df.columns:
            return set()
        return set(df["snapshot_id"].dropna().astype(str).tolist())
    except Exception:
        return set()


def append_csv_row(path: Path, row: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    exists = path.exists() and path.stat().st_size > 0
    with open(path, "a", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_COLUMNS)
        if not exists:
            writer.writeheader()
        writer.writerow({k: row.get(k, "") for k in OUTPUT_COLUMNS})


def main() -> int:
    args = parse_args()
    log_path = Path(args.log_file) if args.log_file else Path(args.output).with_suffix(".run.log")
    output_path = Path(args.output)

    log_line("GOLD V2 AI tag Phase 1 runner started", log_path)
    log_line("MT5 order_send: disabled / Discord send: disabled", log_path)

    load_dotenv_file(args.env_file, log_path)
    if not args.dry_run and not os.environ.get("OPENAI_API_KEY"):
        log_line("ERROR OPENAI_API_KEY is not set. Check .env path or environment.", log_path)
        return 2

    model = args.model or os.environ.get("OPENAI_MODEL") or "gpt-5-mini"
    log_line(f"model={model} timeout_sec={args.timeout_sec} dry_run={args.dry_run}", log_path)
    log_line(f"input={Path(args.input).resolve()}", log_path)
    log_line(f"output={output_path.resolve()}", log_path)

    df = pd.read_csv(args.input)
    if args.max_rows and args.max_rows > 0:
        df = df.head(args.max_rows).copy()
    if "snapshot_id" not in df.columns or "prompt_text" not in df.columns:
        log_line("ERROR input CSV must contain snapshot_id and prompt_text columns", log_path)
        return 3

    schema_obj = load_schema(args.schema)
    done_ids = read_done_snapshot_ids(output_path) if args.resume else set()
    if done_ids:
        log_line(f"resume enabled: {len(done_ids)} snapshot_ids already in output", log_path)

    total = len(df)
    processed = 0
    ok_count = 0
    err_count = 0
    skipped_count = 0

    request_preview_path = output_path.with_suffix(".requests.jsonl")
    with open(request_preview_path, "a", encoding="utf-8") as req_f:
        for pos, (_, row) in enumerate(df.iterrows(), start=1):
            snapshot_id = str(row["snapshot_id"])
            prompt_text = str(row["prompt_text"])

            if snapshot_id in done_ids:
                skipped_count += 1
                log_line(f"[{pos}/{total}] SKIP snapshot_id={snapshot_id} already exists", log_path)
                continue

            log_line(f"[{pos}/{total}] START snapshot_id={snapshot_id}", log_path)
            req_f.write(json.dumps({
                "snapshot_id": snapshot_id,
                "model": model,
                "system_prompt": SYSTEM_PROMPT,
                "user_prompt": prompt_text,
                "schema_name": schema_obj["name"],
            }, ensure_ascii=False) + "\n")
            req_f.flush()

            start = time.perf_counter()
            status = "OK"
            error = ""
            try:
                if args.dry_run:
                    status = "DRY_RUN"
                    result = {
                        "snapshot_id": snapshot_id,
                        "decision": "REVIEW",
                        "stack_permission": "CAP_3",
                        "risk_score": 0,
                        "confidence": 0.0,
                        "quality_tags": [],
                        "risk_tags": [],
                        "block_tags": [],
                        "reason_code": "REVIEW_MIXED_CONTEXT",
                        "reason_short": "DRY_RUN_NO_API_CALL",
                    }
                else:
                    result = call_openai(prompt_text, schema_obj, model, args.timeout_sec)
                elapsed = time.perf_counter() - start
                out_row = normalize_result(result, snapshot_id, model, status, error, elapsed)
                append_csv_row(output_path, out_row)
                processed += 1
                ok_count += int(status in {"OK", "DRY_RUN"})
                log_line(
                    f"[{pos}/{total}] DONE snapshot_id={snapshot_id} status={status} "
                    f"elapsed={elapsed:.3f}s decision={out_row['decision']} stack={out_row['stack_permission']}",
                    log_path,
                )
            except Exception as exc:
                elapsed = time.perf_counter() - start
                status = "ERROR"
                error = repr(exc)
                result = fallback_block(snapshot_id, "API_ERROR_OR_TIMEOUT_BLOCK")
                out_row = normalize_result(result, snapshot_id, model, status, error, elapsed)
                append_csv_row(output_path, out_row)
                processed += 1
                err_count += 1
                log_line(f"[{pos}/{total}] ERROR snapshot_id={snapshot_id} elapsed={elapsed:.3f}s error={error}", log_path)

            if args.sleep_sec > 0:
                time.sleep(args.sleep_sec)

    log_line(
        f"DONE total_rows={total} processed={processed} skipped={skipped_count} ok={ok_count} errors={err_count}",
        log_path,
    )
    log_line(f"wrote output: {output_path}", log_path)
    log_line(f"wrote request preview: {request_preview_path}", log_path)
    return 0 if err_count == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
