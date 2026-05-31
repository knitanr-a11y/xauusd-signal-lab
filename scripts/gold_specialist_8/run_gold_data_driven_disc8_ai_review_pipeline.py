#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""DISC8 AI review pipeline wrapper.

This pipeline is intentionally scoped to the fixed AI review sample CSV:
  data/gold_specialist_8/verification/ai_review_data_driven/latest_ai_review_sample_80_loss45.csv

Safety design:
- never reads the full static_rule_trade_ledger.csv as review target
- never re-detects DISC signals from OHLC
- prepares snapshots/payloads from the fixed sample only
- pending-only by default; already-reviewed payloads are skipped
- AI call requires --run-ai; otherwise payload audit only
- max sample guard defaults to 640
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

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MQL5_FILES_DIR = Path("C:/Users/regen/AppData/Roaming/MetaQuotes/Terminal/2FA8A7E69CED7DC259B1AD86A247F675/MQL5/Files")
DEFAULT_SAMPLE_CSV = REPO_ROOT / "data" / "gold_specialist_8" / "verification" / "ai_review_data_driven" / "latest_ai_review_sample_80_loss45.csv"
DEFAULT_SAMPLE_AUDIT_JSON = REPO_ROOT / "data" / "gold_specialist_8" / "verification" / "ai_review_data_driven" / "latest_ai_review_sample_80_loss45_audit_summary.json"
DEFAULT_OUT_DIR = REPO_ROOT / "data" / "gold_specialist_8" / "verification" / "ai_review_data_driven" / "disc8_ai_review"
SCHEMA_VERSION = "gold_data_driven_disc8_ai_review_pipeline_v1"
EXPECTED_MAX_SAMPLE_ROWS = 640
EXPECTED_CANDIDATE_COUNT = 8


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


def read_json(path: Path) -> dict[str, Any]:
    if not exists(path):
        return {}
    with open(wpath(path), "r", encoding="utf-8") as f:
        obj = json.load(f)
    return obj if isinstance(obj, dict) else {}


def write_json(path: Path, obj: dict[str, Any]) -> None:
    mkdirp(path.parent)
    with open(wpath(path), "w", encoding="utf-8", newline="") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2, sort_keys=True, default=str)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not exists(path):
        return []
    rows: list[dict[str, Any]] = []
    with open(wpath(path), "r", encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if not s:
                continue
            obj = json.loads(s)
            if isinstance(obj, dict):
                rows.append(obj)
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> int:
    mkdirp(path.parent)
    with open(wpath(path), "w", encoding="utf-8", newline="") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True, default=str) + "\n")
    return len(rows)


def read_csv(path: Path) -> pd.DataFrame:
    if not exists(path):
        raise FileNotFoundError(f"CSV not found: {path}")
    return pd.read_csv(wpath(path), encoding="utf-8-sig")


def write_csv(df: pd.DataFrame, path: Path) -> None:
    mkdirp(path.parent)
    df.to_csv(wpath(path), index=False, encoding="utf-8-sig")


def utc_now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")


def clean(value: Any, default: str = "") -> str:
    if value is None:
        return default
    try:
        if pd.isna(value):
            return default
    except Exception:
        pass
    s = str(value).strip()
    return s if s else default


def sanitize(text: str) -> str:
    out = []
    for ch in text:
        if ch.isalnum() or ch in {"_", "-"}:
            out.append(ch)
        else:
            out.append("_")
    return "".join(out).strip("_")


def cmd_run(label: str, cmd: list[str], *, allow_failure: bool = False) -> dict[str, Any]:
    print("=" * 80, flush=True)
    print(f"[STEP] {label}", flush=True)
    print("[CMD] " + " ".join(cmd), flush=True)
    t0 = time.perf_counter()
    proc = subprocess.run(cmd, cwd=str(REPO_ROOT), text=True, encoding="utf-8", errors="replace")
    elapsed = round(time.perf_counter() - t0, 3)
    ok = proc.returncode == 0 or allow_failure
    print(f"[STEP] {label} returncode={proc.returncode} elapsed_seconds={elapsed} ok={ok}", flush=True)
    return {"label": label, "cmd": cmd, "returncode": int(proc.returncode), "elapsed_seconds": elapsed, "allow_failure": bool(allow_failure), "ok": bool(ok)}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run DISC8 fixed sample AI review pipeline.")
    p.add_argument("--sample-csv", type=Path, default=DEFAULT_SAMPLE_CSV)
    p.add_argument("--sample-audit-json", type=Path, default=DEFAULT_SAMPLE_AUDIT_JSON)
    p.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    p.add_argument("--mql5-files-dir", type=Path, default=DEFAULT_MQL5_FILES_DIR)
    p.add_argument("--m15-csv", default="")
    p.add_argument("--m5-csv", default="")
    p.add_argument("--h1-csv", default="")
    p.add_argument("--h4-csv", default="")
    p.add_argument("--d1-csv", default="")
    p.add_argument("--m15-file", default="goldsharp_m15.csv")
    p.add_argument("--m5-file", default="goldsharp_m5.csv")
    p.add_argument("--h1-file", default="goldsharp_h1.csv")
    p.add_argument("--h4-file", default="goldsharp_h4.csv")
    p.add_argument("--d1-file", default="goldsharp_d1.csv")
    p.add_argument("--pre-m15-bars", type=int, default=100)
    p.add_argument("--post-m15-bars", type=int, default=20)
    p.add_argument("--pre-m5-bars", type=int, default=100)
    p.add_argument("--post-m5-bars", type=int, default=240)
    p.add_argument("--model", default="gpt-5-mini")
    p.add_argument("--max-sample-rows", type=int, default=EXPECTED_MAX_SAMPLE_ROWS)
    p.add_argument("--max-pending", type=int, default=0, help="0 = all pending payloads")
    p.add_argument("--min-sample", type=int, default=3)
    p.add_argument("--run-ai", action="store_true", help="Actually call OpenAI for pending payloads. Omit for payload audit only.")
    p.add_argument("--dry-run", action="store_true", help="Write placeholder AI reviews without OpenAI API calls when --run-ai is used.")
    p.add_argument("--allow-partial-review", action=argparse.BooleanOptionalAction, default=True)
    return p.parse_args()


def csv_path(csv_dir: Path, explicit: str, filename: str) -> str:
    if explicit:
        return explicit
    p = csv_dir / filename
    if exists(p):
        return str(p)
    root_p = REPO_ROOT / filename
    if exists(root_p):
        return str(root_p)
    return str(p)


def opt_existing(path_text: str) -> str:
    return path_text if path_text and exists(Path(path_text)) else ""


def validate_sample(sample_csv: Path, audit_json: Path, max_rows: int) -> dict[str, Any]:
    df = read_csv(sample_csv)
    audit = read_json(audit_json)
    if df.empty:
        raise RuntimeError("sample CSV is empty")
    if len(df) > max_rows:
        raise RuntimeError(f"sample rows exceed guard: {len(df)} > {max_rows}")
    if "candidate_id" not in df.columns:
        raise RuntimeError("sample CSV must contain candidate_id")
    candidate_count = int(df["candidate_id"].astype(str).nunique())
    if candidate_count != EXPECTED_CANDIDATE_COUNT:
        raise RuntimeError(f"sample candidate count must be {EXPECTED_CANDIDATE_COUNT}, got {candidate_count}")
    if audit:
        if audit.get("ok") is not True:
            raise RuntimeError("sample audit JSON is not ok=true")
        if audit.get("api_used") is not False:
            raise RuntimeError("sample audit JSON says api_used is not false")
        if int(audit.get("sample_total", len(df))) != len(df):
            raise RuntimeError(f"sample audit row mismatch: audit={audit.get('sample_total')} csv={len(df)}")
        if int(audit.get("htf_future_bad_rows", 0) or 0) != 0:
            raise RuntimeError("sample audit JSON reports htf_future_bad_rows > 0")
    return {
        "sample_rows": int(len(df)),
        "candidate_count": candidate_count,
        "candidate_counts": df["candidate_id"].astype(str).value_counts().sort_index().to_dict(),
        "audit_json_found": bool(audit),
        "audit": audit,
    }


def adapt_sample_to_trade_outcome(sample_csv: Path, out_csv: Path) -> dict[str, Any]:
    df = read_csv(sample_csv).copy()
    if "candidate_id" not in df.columns:
        raise RuntimeError("sample CSV must contain candidate_id")
    if "entry_time" not in df.columns:
        raise RuntimeError("sample CSV must contain entry_time")
    df = df.reset_index(drop=True)
    adapted = df.copy()
    adapted["symbol"] = adapted.get("symbol", "GOLD")
    adapted["broker_symbol"] = adapted.get("broker_symbol", "GOLD")
    adapted["strategy_id"] = adapted["candidate_id"].astype(str)
    adapted["strategy_key"] = adapted["candidate_id"].astype(str)
    adapted["strategy_alias"] = adapted["candidate_id"].astype(str)
    adapted["condition_id"] = adapted["candidate_id"].astype(str)
    adapted["signal_key"] = adapted["candidate_id"].astype(str)
    adapted["trade_id"] = [
        "DISC8_" + sanitize(str(row.candidate_id)) + "_" + sanitize(str(row.entry_time)) + f"_{i:04d}"
        for i, row in adapted.reset_index(drop=True).iterrows()
    ]
    adapted["order_key"] = adapted["trade_id"]
    adapted["payload_key"] = adapted["trade_id"]
    if "exit_reason" in adapted.columns and "close_reason" not in adapted.columns:
        adapted["close_reason"] = adapted["exit_reason"]
    if "minutes_to_close" in adapted.columns and "holding_minutes" not in adapted.columns:
        adapted["holding_minutes"] = adapted["minutes_to_close"]
    if "entry_price_reference" not in adapted.columns and "entry_price" in adapted.columns:
        adapted["entry_price_reference"] = adapted["entry_price"]
    adapted["match_status"] = "BACKTEST_FIXED_SAMPLE"
    adapted["match_method"] = "DISC8_STATIC_REBACKTEST_SAMPLE_80_LOSS45"
    adapted["execution_status"] = "CLOSED"
    write_csv(adapted, out_csv)
    return {
        "input_csv": str(sample_csv),
        "output_csv": str(out_csv),
        "rows": int(len(adapted)),
        "candidate_counts": adapted["candidate_id"].astype(str).value_counts().sort_index().to_dict(),
    }


def payload_id(payload: dict[str, Any]) -> tuple[str, str, str]:
    trade = payload.get("trade", {}) if isinstance(payload.get("trade"), dict) else {}
    compact = payload.get("compact_features", {}) if isinstance(payload.get("compact_features"), dict) else {}
    return (
        clean(payload.get("trade_id") or trade.get("trade_id") or compact.get("trade_id")),
        clean(payload.get("order_key") or trade.get("order_key") or compact.get("order_key")),
        clean(payload.get("payload_key") or trade.get("payload_key") or compact.get("payload_key")),
    )


def review_id(review: dict[str, Any]) -> tuple[str, str, str]:
    return clean(review.get("trade_id")), clean(review.get("order_key")), clean(review.get("payload_key"))


def write_pending_payloads(payload_jsonl: Path, review_jsonl: Path, pending_jsonl: Path, max_pending: int) -> dict[str, Any]:
    payloads = read_jsonl(payload_jsonl)
    reviews = read_jsonl(review_jsonl)
    reviewed = {review_id(r) for r in reviews}
    trade_ids = {x[0] for x in reviewed if x[0]}
    order_keys = {x[1] for x in reviewed if x[1]}
    payload_keys = {x[2] for x in reviewed if x[2]}
    pending: list[dict[str, Any]] = []
    for payload in payloads:
        tid, ok, pk = payload_id(payload)
        if (tid, ok, pk) in reviewed or (tid and tid in trade_ids) or (ok and ok in order_keys) or (pk and pk in payload_keys):
            continue
        pending.append(payload)
    if max_pending > 0:
        pending = pending[: int(max_pending)]
    write_jsonl(pending_jsonl, pending)
    return {
        "payload_rows": int(len(payloads)),
        "existing_review_rows": int(len(reviews)),
        "pending_rows": int(len(pending)),
        "skipped_already_reviewed_rows": int(len(payloads) - len(pending)),
    }


def main() -> int:
    args = parse_args()
    t0 = time.perf_counter()
    mkdirp(args.out_dir)
    paths = {
        "review_trade_outcome_csv": args.out_dir / "disc8_review_trade_outcome_sample.csv",
        "snapshot_csv": args.out_dir / "trade_feature_snapshot.csv",
        "snapshot_jsonl": args.out_dir / "trade_feature_snapshot.jsonl",
        "snapshot_json": args.out_dir / "trade_feature_snapshot_summary.json",
        "payload_jsonl": args.out_dir / "trade_ai_review_payloads.jsonl",
        "payload_json": args.out_dir / "trade_ai_review_payloads_summary.json",
        "pending_jsonl": args.out_dir / "trade_ai_review_payloads_pending.jsonl",
        "review_jsonl": args.out_dir / "trade_ai_review_ledger.jsonl",
        "review_json": args.out_dir / "trade_ai_review_run_summary.json",
        "tag_csv": args.out_dir / "trade_ai_tag_summary.csv",
        "tag_json": args.out_dir / "trade_ai_tag_summary.json",
        "summary_json": args.out_dir / "gold_data_driven_disc8_ai_review_pipeline_summary.json",
    }
    for path in paths.values():
        mkdirp(path.parent)

    print("=" * 80, flush=True)
    print("GOLD data-driven DISC8 AI review pipeline", flush=True)
    print(f"sample_csv={args.sample_csv}", flush=True)
    print(f"out_dir={args.out_dir}", flush=True)
    print(f"run_ai={args.run_ai} dry_run={args.dry_run}", flush=True)
    print("=" * 80, flush=True)

    sample_validation = validate_sample(args.sample_csv, args.sample_audit_json, args.max_sample_rows)
    adapted = adapt_sample_to_trade_outcome(args.sample_csv, paths["review_trade_outcome_csv"])

    m15_csv = csv_path(args.mql5_files_dir, args.m15_csv, args.m15_file)
    m5_csv = csv_path(args.mql5_files_dir, args.m5_csv, args.m5_file)
    h1_csv = csv_path(args.mql5_files_dir, args.h1_csv, args.h1_file)
    h4_csv = csv_path(args.mql5_files_dir, args.h4_csv, args.h4_file)
    d1_csv = csv_path(args.mql5_files_dir, args.d1_csv, args.d1_file)
    if not exists(m15_csv):
        raise SystemExit(f"M15 CSV not found: {m15_csv}")

    steps: list[dict[str, Any]] = []
    snapshot_cmd = [
        sys.executable, str(REPO_ROOT / "scripts" / "build_trade_feature_snapshots.py"),
        "--trade-outcome-csv", str(paths["review_trade_outcome_csv"]),
        "--m15-csv", str(m15_csv),
        "--output-csv", str(paths["snapshot_csv"]),
        "--output-jsonl", str(paths["snapshot_jsonl"]),
        "--output-json", str(paths["snapshot_json"]),
        "--pre-m15-bars", str(args.pre_m15_bars),
        "--post-m15-bars", str(args.post_m15_bars),
        "--pre-m5-bars", str(args.pre_m5_bars),
        "--post-m5-bars", str(args.post_m5_bars),
    ]
    for flag, value in [("--m5-csv", m5_csv), ("--h1-csv", h1_csv), ("--h4-csv", h4_csv), ("--d1-csv", d1_csv)]:
        if opt_existing(value):
            snapshot_cmd.extend([flag, value])
    steps.append(cmd_run("build_trade_feature_snapshots", snapshot_cmd))
    if not steps[-1]["ok"]:
        return 3

    steps.append(cmd_run("build_trade_ai_review_payloads", [
        sys.executable, str(REPO_ROOT / "scripts" / "build_trade_ai_review_payloads.py"),
        "--feature-snapshot-jsonl", str(paths["snapshot_jsonl"]),
        "--output-jsonl", str(paths["payload_jsonl"]),
        "--output-json", str(paths["payload_json"]),
        "--max-pre-m15-bars-in-prompt", str(args.pre_m15_bars),
        "--max-post-m15-bars-in-prompt", str(args.post_m15_bars),
    ]))
    if not steps[-1]["ok"]:
        return 4

    pending = write_pending_payloads(paths["payload_jsonl"], paths["review_jsonl"], paths["pending_jsonl"], int(args.max_pending))

    if args.run_ai and int(pending["pending_rows"]) > 0:
        review_cmd = [
            sys.executable, str(REPO_ROOT / "scripts" / "run_trade_ai_review_from_payloads.py"),
            "--payload-jsonl", str(paths["pending_jsonl"]),
            "--output-jsonl", str(paths["review_jsonl"]),
            "--output-json", str(paths["review_json"]),
            "--model", str(args.model),
        ]
        if args.dry_run:
            review_cmd.append("--dry-run")
        steps.append(cmd_run("run_trade_ai_review_from_pending_payloads", review_cmd, allow_failure=bool(args.allow_partial_review)))
    else:
        if not exists(paths["review_jsonl"]):
            write_jsonl(paths["review_jsonl"], [])
        print("[INFO] AI review skipped. Use --run-ai to call OpenAI, or --run-ai --dry-run for placeholder reviews.", flush=True)

    # Summarize only when review ledger has rows. Otherwise write an empty marker summary.
    review_rows = len(read_jsonl(paths["review_jsonl"]))
    if review_rows > 0:
        steps.append(cmd_run("summarize_trade_ai_review_ledger", [
            sys.executable, str(REPO_ROOT / "scripts" / "summarize_trade_ai_review_ledger.py"),
            "--trade-outcome-csv", str(paths["review_trade_outcome_csv"]),
            "--ai-review-jsonl", str(paths["review_jsonl"]),
            "--output-csv", str(paths["tag_csv"]),
            "--output-json", str(paths["tag_json"]),
            "--min-sample", str(args.min_sample),
        ]))
        if not steps[-1]["ok"]:
            return 5
    else:
        write_csv(pd.DataFrame(), paths["tag_csv"])
        write_json(paths["tag_json"], {"rows": 0, "reason": "NO_REVIEW_ROWS_YET"})

    summary = {
        "schema_version": SCHEMA_VERSION,
        "created_at_utc": utc_now(),
        "cycle_ok": bool(all(s.get("ok") for s in steps)),
        "reason": "OK",
        "sample_validation": sample_validation,
        "adapted_sample": adapted,
        "run_ai": bool(args.run_ai),
        "dry_run": bool(args.dry_run),
        "model": str(args.model),
        "out_dir": str(args.out_dir),
        "paths": {k: str(v) for k, v in paths.items()},
        "csv_paths": {"m15": str(m15_csv), "m5": str(m5_csv), "h1": str(h1_csv), "h4": str(h4_csv), "d1": str(d1_csv)},
        "pending_summary": pending,
        "key_metrics": {
            "sample_rows": int(sample_validation["sample_rows"]),
            "payload_rows": int(pending["payload_rows"]),
            "pending_rows": int(pending["pending_rows"]),
            "review_rows_final": int(len(read_jsonl(paths["review_jsonl"]))),
        },
        "steps": steps,
        "timing": {"total_seconds": round(time.perf_counter() - t0, 3)},
    }
    write_json(paths["summary_json"], summary)
    print(json.dumps({
        "cycle_ok": summary["cycle_ok"],
        "run_ai": summary["run_ai"],
        "dry_run": summary["dry_run"],
        "sample_rows": summary["key_metrics"]["sample_rows"],
        "payload_rows": summary["key_metrics"]["payload_rows"],
        "pending_rows": summary["key_metrics"]["pending_rows"],
        "review_rows_final": summary["key_metrics"]["review_rows_final"],
        "summary_json": str(paths["summary_json"]),
    }, ensure_ascii=False, indent=2), flush=True)
    return 0 if summary["cycle_ok"] else 9


if __name__ == "__main__":
    raise SystemExit(main())
