#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Live AI review pipeline for completed GOLD strict 7 demo trades.

The pipeline is post-trade only:
- build factual outcome rows from the strict 7 ledger and MT5 closed history
- filter AI-reviewable strict 7 outcomes into a review-only intermediate CSV
- build feature snapshots from the review-only intermediate CSV
- build AI review payloads
- evaluate only payloads that are not already present in the review ledger
- summarize all live strict 7 reviews

Backtest and live outputs are intentionally separate.
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
DEFAULT_OUT_DIR = Path("data/runtime_logs/trade_ai_review_live_gold_strict_7")
DEFAULT_LEDGER = Path("data/runtime_state/gold/strict_7/guarded_demo_order_ledger.csv")
SCHEMA_VERSION = "gold_strict_7_live_ai_review_pipeline_v1"

REVIEWABLE_OUTCOMES = {"WIN", "LOSS", "BREAKEVEN", "SMALL_WIN", "SMALL_LOSS"}
REVIEWABLE_EXECUTION_STATUSES = {"CLOSED", "EXECUTED"}
EXCLUDED_EXECUTION_STATUSES = {"SENT_NO_MT5_POSITION_MATCH", "NO_MT5_POSITION_MATCH"}


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


def write_text(path: Path, text: str) -> None:
    mkdirp(path.parent)
    with open(wpath(path), "w", encoding="utf-8", newline="") as f:
        f.write(text)


def write_json(path: Path, obj: dict[str, Any]) -> None:
    write_text(path, json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True, default=str))


def read_json(path: Path) -> dict[str, Any]:
    try:
        with open(wpath(path), "r", encoding="utf-8") as f:
            obj = json.load(f)
        return obj if isinstance(obj, dict) else {}
    except Exception:
        return {}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not exists(path):
        return []
    rows: list[dict[str, Any]] = []
    with open(wpath(path), "r", encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if s:
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


def csv_len(path: Path) -> int:
    if not exists(path):
        return 0
    try:
        return int(len(pd.read_csv(wpath(path), encoding="utf-8-sig")))
    except Exception:
        return 0


def read_csv(path: Path) -> pd.DataFrame:
    if not exists(path):
        return pd.DataFrame()
    return pd.read_csv(wpath(path), encoding="utf-8-sig")


def clean(value: Any) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass
    return str(value).strip()


def upper_col(df: pd.DataFrame, name: str) -> pd.Series:
    if name in df.columns:
        return df[name].fillna("").astype(str).str.strip().str.upper()
    return pd.Series([""] * len(df), index=df.index, dtype=str)


def reviewable_trade_mask(df: pd.DataFrame) -> pd.Series:
    exe = upper_col(df, "execution_status")
    out = upper_col(df, "outcome")
    return (
        exe.isin(REVIEWABLE_EXECUTION_STATUSES)
        & out.isin(REVIEWABLE_OUTCOMES)
        & ~exe.isin(EXCLUDED_EXECUTION_STATUSES)
    )


def utc_now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")


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


def payload_id(payload: dict[str, Any]) -> tuple[str, str, str]:
    trade = payload.get("trade", {}) if isinstance(payload.get("trade"), dict) else {}
    compact = payload.get("compact_features", {}) if isinstance(payload.get("compact_features"), dict) else {}
    trade_id = clean(payload.get("trade_id") or trade.get("trade_id") or compact.get("trade_id"))
    order_key = clean(payload.get("order_key") or trade.get("order_key") or compact.get("order_key"))
    payload_key = clean(payload.get("payload_key") or trade.get("payload_key") or compact.get("payload_key"))
    return trade_id, order_key, payload_key


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
        pending = pending[:max_pending]
    write_jsonl(pending_jsonl, pending)
    return {
        "payload_rows": int(len(payloads)),
        "existing_review_rows": int(len(reviews)),
        "pending_rows": int(len(pending)),
        "skipped_already_reviewed_rows": int(len(payloads) - len(pending)),
    }


def outcome_counts(path: Path) -> dict[str, Any]:
    df = read_csv(path)
    if df.empty:
        return {
            "rows": 0,
            "reviewable_trade_rows": 0,
            "reviewable_closed_rows": 0,
            "reviewable_executed_rows": 0,
            "excluded_no_mt5_position_match_rows": 0,
            "execution_status_counts": {},
            "outcome_counts": {},
            "reviewable_execution_status_counts": {},
            "reviewable_outcome_counts": {},
        }
    exe = upper_col(df, "execution_status")
    out = upper_col(df, "outcome")
    reviewable = reviewable_trade_mask(df)
    valid_outcome = out.isin(REVIEWABLE_OUTCOMES)
    excluded = exe.isin(EXCLUDED_EXECUTION_STATUSES)
    closed_reviewable = exe.eq("CLOSED") & valid_outcome & ~excluded
    executed_reviewable = exe.eq("EXECUTED") & valid_outcome & ~excluded
    return {
        "rows": int(len(df)),
        "reviewable_trade_rows": int(reviewable.sum()),
        "reviewable_closed_rows": int(closed_reviewable.sum()),
        "reviewable_executed_rows": int(executed_reviewable.sum()),
        "excluded_no_mt5_position_match_rows": int(excluded.sum()),
        "execution_status_counts": exe.value_counts(dropna=False).to_dict(),
        "outcome_counts": out.value_counts(dropna=False).to_dict(),
        "reviewable_execution_status_counts": exe[reviewable].value_counts(dropna=False).to_dict(),
        "reviewable_outcome_counts": out[reviewable].value_counts(dropna=False).to_dict(),
    }


def write_reviewable_trade_outcome_csv(source_csv: Path, reviewable_csv: Path) -> dict[str, Any]:
    df = read_csv(source_csv)
    mask = reviewable_trade_mask(df) if not df.empty else pd.Series([], dtype=bool)
    reviewable_df = df.loc[mask].copy() if not df.empty else df.copy()
    mkdirp(reviewable_csv.parent)
    reviewable_df.to_csv(wpath(reviewable_csv), index=False, encoding="utf-8-sig")

    exe = upper_col(df, "execution_status") if not df.empty else pd.Series([], dtype=str)
    out = upper_col(df, "outcome") if not df.empty else pd.Series([], dtype=str)
    excluded = exe.isin(EXCLUDED_EXECUTION_STATUSES) if not df.empty else pd.Series([], dtype=bool)
    return {
        "source_csv": str(source_csv),
        "reviewable_csv": str(reviewable_csv),
        "source_rows": int(len(df)),
        "reviewable_rows": int(len(reviewable_df)),
        "excluded_no_mt5_position_match_rows": int(excluded.sum()) if len(excluded) else 0,
        "reviewable_execution_status_counts": exe[mask].value_counts(dropna=False).to_dict() if len(mask) else {},
        "reviewable_outcome_counts": out[mask].value_counts(dropna=False).to_dict() if len(mask) else {},
        "rules": {
            "include_execution_statuses": sorted(REVIEWABLE_EXECUTION_STATUSES),
            "include_outcomes": sorted(REVIEWABLE_OUTCOMES),
            "exclude_execution_statuses": sorted(EXCLUDED_EXECUTION_STATUSES),
        },
    }


def csv_path(csv_dir: Path, explicit: str, filename: str) -> str:
    return explicit if explicit else str(csv_dir / filename)


def opt_existing(path_text: str) -> str:
    return path_text if path_text and exists(Path(path_text)) else ""


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run live AI review for completed GOLD strict 7 trades.")
    p.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    p.add_argument("--mql5-files-dir", type=Path, default=DEFAULT_MQL5_FILES_DIR)
    p.add_argument("--order-ledger-csv", type=Path, default=DEFAULT_LEDGER)
    p.add_argument("--expected-login", type=int, default=75539039)
    p.add_argument("--broker-symbols", default="GOLD#")
    p.add_argument("--lookback-days", type=int, default=90)
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
    p.add_argument("--max-pending", type=int, default=0)
    p.add_argument("--min-sample", type=int, default=3)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--skip-mt5-export", action="store_true")
    p.add_argument("--skip-ai-review", action="store_true")
    p.add_argument("--allow-partial-review", action=argparse.BooleanOptionalAction, default=True)
    p.add_argument("--allow-no-reviewable-trades-success", action=argparse.BooleanOptionalAction, default=True)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    t0 = time.perf_counter()
    mkdirp(args.out_dir)
    paths = {
        "mt5_dir": args.out_dir / "mt5_history",
        "mt5_positions_csv": args.out_dir / "mt5_history" / "mt5_history_positions.csv",
        "mt5_deals_csv": args.out_dir / "mt5_history" / "mt5_history_deals.csv",
        "outcome_csv": args.out_dir / "trade_outcome_ledger.csv",
        "reviewable_outcome_csv": args.out_dir / "trade_outcome_ledger_reviewable.csv",
        "outcome_json": args.out_dir / "trade_outcome_ledger_summary.json",
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
        "summary_json": args.out_dir / "gold_strict_7_live_ai_review_pipeline_summary.json",
    }
    for path in paths.values():
        mkdirp(path.parent)

    if not exists(args.order_ledger_csv):
        raise SystemExit(f"order ledger CSV not found: {args.order_ledger_csv}")

    m15_csv = csv_path(args.mql5_files_dir, args.m15_csv, args.m15_file)
    m5_csv = csv_path(args.mql5_files_dir, args.m5_csv, args.m5_file)
    h1_csv = csv_path(args.mql5_files_dir, args.h1_csv, args.h1_file)
    h4_csv = csv_path(args.mql5_files_dir, args.h4_csv, args.h4_file)
    d1_csv = csv_path(args.mql5_files_dir, args.d1_csv, args.d1_file)
    if not exists(m15_csv):
        raise SystemExit(f"M15 CSV not found: {m15_csv}")

    steps: list[dict[str, Any]] = []
    print("=" * 80, flush=True)
    print("GOLD strict 7 live AI review pipeline", flush=True)
    print(f"out_dir={args.out_dir}", flush=True)
    print(f"order_ledger_csv={args.order_ledger_csv}", flush=True)
    print(f"dry_run={args.dry_run} skip_ai_review={args.skip_ai_review}", flush=True)
    print("=" * 80, flush=True)

    if not args.skip_mt5_export:
        steps.append(cmd_run("export_mt5_closed_trade_history", [
            sys.executable, str(REPO_ROOT / "scripts" / "export_mt5_closed_trade_history.py"),
            "--out-dir", str(paths["mt5_dir"]),
            "--lookback-days", str(args.lookback_days),
            "--symbols", str(args.broker_symbols),
            "--expected-login", str(args.expected_login),
        ]))
        if not steps[-1]["ok"]:
            return 1

    if not exists(paths["mt5_positions_csv"]):
        raise SystemExit(f"MT5 positions CSV not found: {paths['mt5_positions_csv']}")

    steps.append(cmd_run("build_trade_outcome_ledger", [
        sys.executable, str(REPO_ROOT / "scripts" / "build_trade_outcome_ledger_from_order_ledger.py"),
        "--order-ledger-csv", str(args.order_ledger_csv),
        "--mt5-positions-csv", str(paths["mt5_positions_csv"]),
        "--mt5-deals-csv", str(paths["mt5_deals_csv"]),
        "--output-csv", str(paths["outcome_csv"]),
        "--output-json", str(paths["outcome_json"]),
    ]))
    if not steps[-1]["ok"]:
        return 2

    counts = outcome_counts(paths["outcome_csv"])
    reviewable_filter = write_reviewable_trade_outcome_csv(paths["outcome_csv"], paths["reviewable_outcome_csv"])
    if int(counts.get("reviewable_trade_rows", 0)) <= 0 and args.allow_no_reviewable_trades_success:
        if not exists(paths["review_jsonl"]):
            write_text(paths["review_jsonl"], "")
        summary = {
            "schema_version": SCHEMA_VERSION,
            "created_at_utc": utc_now(),
            "cycle_ok": True,
            "reason": "NO_REVIEWABLE_STRICT7_TRADE",
            "out_dir": str(args.out_dir),
            "paths": {k: str(v) for k, v in paths.items()},
            "outcome_counts": counts,
            "reviewable_filter": reviewable_filter,
            "key_metrics": {
                "outcome_rows": counts.get("rows", 0),
                "reviewable_trade_rows": 0,
                "reviewable_closed_rows": int(counts.get("reviewable_closed_rows", 0)),
                "reviewable_executed_rows": int(counts.get("reviewable_executed_rows", 0)),
                "reviewable_outcome_rows": csv_len(paths["reviewable_outcome_csv"]),
                "payload_rows": 0,
                "pending_rows": 0,
                "review_rows_final": len(read_jsonl(paths["review_jsonl"])),
            },
            "steps": steps,
            "timing": {"total_seconds": round(time.perf_counter() - t0, 3)},
        }
        write_json(paths["summary_json"], summary)
        print(json.dumps({"cycle_ok": True, "reason": summary["reason"], "summary_json": str(paths["summary_json"])}, ensure_ascii=False, indent=2), flush=True)
        return 0

    snapshot_cmd = [
        sys.executable, str(REPO_ROOT / "scripts" / "build_trade_feature_snapshots.py"),
        "--trade-outcome-csv", str(paths["reviewable_outcome_csv"]),
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
    if not args.skip_ai_review and int(pending["pending_rows"]) > 0:
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
            write_text(paths["review_jsonl"], "")
        print("[INFO] AI review skipped because pending_rows=0 or --skip-ai-review", flush=True)

    steps.append(cmd_run("summarize_trade_ai_review_ledger", [
        sys.executable, str(REPO_ROOT / "scripts" / "summarize_trade_ai_review_ledger.py"),
        "--trade-outcome-csv", str(paths["reviewable_outcome_csv"]),
        "--ai-review-jsonl", str(paths["review_jsonl"]),
        "--output-csv", str(paths["tag_csv"]),
        "--output-json", str(paths["tag_json"]),
        "--min-sample", str(args.min_sample),
    ]))
    if not steps[-1]["ok"]:
        return 5

    review_summary = read_json(paths["review_json"])
    tag_summary = read_json(paths["tag_json"])
    final_review_rows = len(read_jsonl(paths["review_jsonl"]))
    summary = {
        "schema_version": SCHEMA_VERSION,
        "created_at_utc": utc_now(),
        "cycle_ok": bool(all(s.get("ok") for s in steps)),
        "reason": "OK",
        "out_dir": str(args.out_dir),
        "order_ledger_csv": str(args.order_ledger_csv),
        "paths": {k: str(v) for k, v in paths.items()},
        "outcome_counts": counts,
        "reviewable_filter": reviewable_filter,
        "pending_summary": pending,
        "key_metrics": {
            "outcome_rows": csv_len(paths["outcome_csv"]),
            "reviewable_trade_rows": int(counts.get("reviewable_trade_rows", 0)),
            "reviewable_closed_rows": int(counts.get("reviewable_closed_rows", 0)),
            "reviewable_executed_rows": int(counts.get("reviewable_executed_rows", 0)),
            "reviewable_outcome_rows": csv_len(paths["reviewable_outcome_csv"]),
            "feature_snapshot_rows": csv_len(paths["snapshot_csv"]),
            "payload_rows": int(pending.get("payload_rows", 0)),
            "pending_rows": int(pending.get("pending_rows", 0)),
            "skipped_already_reviewed_rows": int(pending.get("skipped_already_reviewed_rows", 0)),
            "review_rows_final": final_review_rows,
            "review_rows_written_this_run": review_summary.get("rows_written", 0),
            "review_error_rows": review_summary.get("error_rows", 0),
            "tag_summary_rows": csv_len(paths["tag_csv"]),
            "should_investigate_rows": tag_summary.get("should_investigate_rows"),
        },
        "safety": {"post_trade_only": True, "ai_hypothesis_only": True, "backtest_outputs_modified": False},
        "steps": steps,
        "timing": {"total_seconds": round(time.perf_counter() - t0, 3)},
    }
    write_json(paths["summary_json"], summary)
    print("=" * 80, flush=True)
    print("GOLD strict 7 live AI review pipeline summary", flush=True)
    print(json.dumps({
        "cycle_ok": summary["cycle_ok"],
        "reason": summary["reason"],
        "outcome_rows": summary["key_metrics"]["outcome_rows"],
        "reviewable_trade_rows": summary["key_metrics"]["reviewable_trade_rows"],
        "reviewable_closed_rows": summary["key_metrics"]["reviewable_closed_rows"],
        "reviewable_executed_rows": summary["key_metrics"]["reviewable_executed_rows"],
        "reviewable_outcome_rows": summary["key_metrics"]["reviewable_outcome_rows"],
        "payload_rows": summary["key_metrics"]["payload_rows"],
        "pending_rows": summary["key_metrics"]["pending_rows"],
        "skipped_already_reviewed_rows": summary["key_metrics"]["skipped_already_reviewed_rows"],
        "review_rows_final": summary["key_metrics"]["review_rows_final"],
        "review_rows_written_this_run": summary["key_metrics"]["review_rows_written_this_run"],
        "review_error_rows": summary["key_metrics"]["review_error_rows"],
        "should_investigate_rows": summary["key_metrics"].get("should_investigate_rows"),
        "summary_json": str(paths["summary_json"]),
    }, ensure_ascii=False, indent=2, sort_keys=True), flush=True)
    print("=" * 80, flush=True)
    return 0 if summary["cycle_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
