#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""GOLD specialist 8 validation-trade AI review pipeline.

This pipeline is for verification/backtest/shadow-style trade outcome CSVs, not for
live MT5 history reconciliation.  It prepares deterministic feature snapshots,
OpenAI-ready payloads, pending-only AI review requests, and tag summaries.

All generated files are kept under data/gold_specialist_8 by default.
Run-specific heavy outputs use YYYY/MM/YYYYMMDD_HHMMSS folders to avoid clutter.

AI review is hypothesis-tagging only.  It must not directly change strategy rules.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from trade_ai_review_utils import read_csv, read_jsonl, write_csv, write_json, write_jsonl  # noqa: E402

SCHEMA_VERSION = "gold_specialist_8_validation_ai_review_pipeline_v1"
DEFAULT_MQL5_FILES_DIR = Path(r"C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files")
DEFAULT_TRADE_OUTCOME_CSV = Path("data/gold_specialist_8/verification/trade_outcomes/gold_specialist_8_validation_trade_outcome_ledger.csv")
DEFAULT_OUT_ROOT = Path("data/gold_specialist_8/verification/ai_review_validation")
REVIEWABLE_OUTCOMES = {"WIN", "LOSS", "BREAKEVEN", "SMALL_WIN", "SMALL_LOSS"}
OPEN_OR_UNRESOLVED_OUTCOMES = {"", "OPEN", "UNKNOWN", "TIMEOUT", "UNRESOLVED", "PENDING", "NO_M1_PATH", "INVALID_INPUT"}


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


def local_stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def run_dir_from_root(out_root: Path, stamp: str) -> Path:
    return out_root / stamp[:4] / stamp[4:6] / stamp


def clean_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    try:
        if pd.isna(value):
            return default
    except Exception:
        pass
    text = str(value).strip()
    return text if text else default


def clean_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass
    try:
        return float(value)
    except Exception:
        return None


def first_existing(row: pd.Series, names: list[str], default: Any = "") -> Any:
    lower = {str(c).lower(): str(c) for c in row.index}
    for name in names:
        col = name if name in row.index else lower.get(name.lower())
        if col is None:
            continue
        value = row.get(col, default)
        try:
            if pd.isna(value):
                continue
        except Exception:
            pass
        if clean_str(value) or not isinstance(value, str):
            return value
    return default


def normalize_direction(value: Any) -> str:
    text = clean_str(value).upper()
    if text in {"BUY", "LONG", "0"}:
        return "BUY"
    if text in {"SELL", "SHORT", "1"}:
        return "SELL"
    if "BUY" in text:
        return "BUY"
    if "SELL" in text or "SHORT" in text:
        return "SELL"
    return text


def parse_time_text(value: Any) -> str:
    text = clean_str(value)
    if not text:
        return ""
    ts = pd.to_datetime(text, errors="coerce")
    if pd.isna(ts):
        return text
    return pd.Timestamp(ts).strftime("%Y-%m-%d %H:%M:%S")


def classify_outcome(value: Any) -> str:
    text = clean_str(value).upper()
    if text in {"TP", "TAKE_PROFIT"}:
        return "WIN"
    if text in {"SL", "STOP_LOSS"}:
        return "LOSS"
    return text


def canonical_trade_id(row: pd.Series, i: int) -> str:
    for names in [
        ["trade_id"],
        ["group_trade_id"],
        ["component_trade_id"],
        ["order_key"],
        ["payload_key"],
        ["signal_key"],
    ]:
        value = clean_str(first_existing(row, names))
        if value:
            return value
    strategy = clean_str(first_existing(row, ["strategy_id", "component_strategy_id", "leader_strategy_id"]))
    direction = normalize_direction(first_existing(row, ["direction"]))
    entry_time = parse_time_text(first_existing(row, ["entry_time", "signal_time"]))
    return "GOLD_SPECIALIST_8_VALIDATION|" + "|".join([strategy, direction, entry_time, str(i)])


def normalize_validation_trade_rows(df: pd.DataFrame, *, review_target: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for i, row in df.iterrows():
        source_role = clean_str(first_existing(row, ["review_target", "record_type", "ledger_type", "component_role"])).lower()
        is_component = bool(clean_str(first_existing(row, ["component_strategy_id"]))) or source_role in {"component", "component_signal"}
        is_group = bool(clean_str(first_existing(row, ["group_trade_id"]))) and not is_component
        if review_target == "component" and not is_component:
            continue
        if review_target == "group" and is_component:
            continue

        outcome = classify_outcome(first_existing(row, [
            "outcome",
            "standalone_virtual_outcome",
            "component_outcome",
            "group_outcome",
            "virtual_outcome",
            "mt5_outcome",
        ]))
        profit_r = clean_float(first_existing(row, [
            "profit_r",
            "standalone_virtual_profit_r",
            "component_profit_r",
            "group_profit_r",
            "virtual_r",
            "r_multiple",
        ]))
        strategy_id = clean_str(first_existing(row, ["strategy_id", "component_strategy_id", "leader_strategy_id", "strategy_key"]))
        direction = normalize_direction(first_existing(row, ["direction", "side"]))
        entry_time = parse_time_text(first_existing(row, ["entry_time", "signal_time", "opened_at", "created_at"]))
        entry_price = clean_float(first_existing(row, ["entry_price", "entry_price_reference", "price", "open_price"]))
        tp_price = clean_float(first_existing(row, ["tp_price", "tp", "take_profit"]))
        sl_price = clean_float(first_existing(row, ["sl_price", "sl", "stop_loss"]))
        close_time = parse_time_text(first_existing(row, ["close_time", "standalone_virtual_close_time", "group_close_time", "virtual_close_time"]))
        close_price = clean_float(first_existing(row, ["close_price", "standalone_virtual_close_price", "group_close_price", "virtual_close_price"]))
        trade_id = canonical_trade_id(row, int(i))
        order_key = clean_str(first_existing(row, ["order_key", "group_trade_id", "component_signal_key", "signal_key"]), trade_id)
        payload_key = clean_str(first_existing(row, ["payload_key"]), "PAYLOAD|" + trade_id)
        signal_key = clean_str(first_existing(row, ["signal_key", "component_signal_key"]), order_key)
        reject_reasons = []
        if outcome not in REVIEWABLE_OUTCOMES:
            reject_reasons.append("non_reviewable_outcome=" + (outcome or "EMPTY"))
        if not strategy_id:
            reject_reasons.append("missing_strategy_id")
        if direction not in {"BUY", "SELL"}:
            reject_reasons.append("missing_or_invalid_direction")
        if not entry_time:
            reject_reasons.append("missing_entry_time")
        if entry_price is None:
            reject_reasons.append("missing_entry_price")
        if tp_price is None:
            reject_reasons.append("missing_tp_price")
        if sl_price is None:
            reject_reasons.append("missing_sl_price")
        if reject_reasons:
            bad = row.to_dict()
            bad["reject_reasons"] = ";".join(reject_reasons)
            rejected.append(bad)
            continue
        out = dict(row.to_dict())
        out.update({
            "trade_id": trade_id,
            "order_key": order_key,
            "payload_key": payload_key,
            "signal_key": signal_key,
            "symbol": clean_str(first_existing(row, ["symbol"]), "GOLD"),
            "broker_symbol": clean_str(first_existing(row, ["broker_symbol", "mt5_symbol"]), "GOLD#"),
            "strategy_key": clean_str(first_existing(row, ["strategy_key", "strategy_id", "component_strategy_id"]), strategy_id),
            "strategy_id": strategy_id,
            "direction": direction,
            "outcome": outcome,
            "profit_r": profit_r,
            "entry_time": entry_time,
            "entry_price": entry_price,
            "entry_price_reference": entry_price,
            "tp_price": tp_price,
            "sl_price": sl_price,
            "close_time": close_time,
            "close_price": close_price,
            "review_target_type": "component" if is_component else ("group" if is_group else "trade"),
            "gold_specialist_8_review_source": "validation_trade_outcome_csv",
        })
        rows.append(out)
    return pd.DataFrame(rows), pd.DataFrame(rejected)


def key_from_payload(payload: dict[str, Any]) -> str:
    trade = payload.get("trade", {}) if isinstance(payload.get("trade"), dict) else {}
    compact = payload.get("compact_features", {}) if isinstance(payload.get("compact_features"), dict) else {}
    for source in [payload, trade, compact]:
        for name in ["trade_id", "order_key", "payload_key"]:
            value = clean_str(source.get(name) if isinstance(source, dict) else "")
            if value:
                return name + "|" + value
    return ""


def key_from_review(review: dict[str, Any]) -> str:
    for name in ["trade_id", "order_key", "payload_key"]:
        value = clean_str(review.get(name))
        if value:
            return name + "|" + value
    return ""


def filter_pending_payloads(payload_jsonl: Path, review_ledger_jsonl: Path, pending_jsonl: Path) -> dict[str, int]:
    payloads = read_jsonl(payload_jsonl) if exists(payload_jsonl) else []
    reviews = read_jsonl(review_ledger_jsonl) if exists(review_ledger_jsonl) else []
    reviewed = {k for k in (key_from_review(r) for r in reviews) if k}
    pending = []
    skipped = 0
    seen = set()
    for payload in payloads:
        key = key_from_payload(payload)
        if key and key in seen:
            skipped += 1
            continue
        if key and key in reviewed:
            skipped += 1
            continue
        if key:
            seen.add(key)
        pending.append(payload)
    write_jsonl(pending_jsonl, pending)
    return {"payload_rows": len(payloads), "reviewed_rows_existing": len(reviews), "pending_rows": len(pending), "skipped_already_reviewed_or_duplicate_rows": skipped}


def csv_path(root: Path, explicit: str, filename: str) -> str:
    return explicit if explicit else str(root / filename)


def cmd_run(label: str, cmd: list[str], *, allow_failure: bool = False) -> dict[str, Any]:
    print("=" * 100, flush=True)
    print(f"[STEP] {label}", flush=True)
    print("[CMD] " + " ".join(cmd), flush=True)
    t0 = time.perf_counter()
    proc = subprocess.run(cmd, cwd=str(REPO_ROOT), text=True, encoding="utf-8", errors="replace")
    elapsed = round(time.perf_counter() - t0, 3)
    ok = proc.returncode == 0 or allow_failure
    print(f"[STEP] {label} returncode={proc.returncode} elapsed_seconds={elapsed} ok={ok}", flush=True)
    return {"label": label, "cmd": cmd, "returncode": int(proc.returncode), "elapsed_seconds": elapsed, "allow_failure": bool(allow_failure), "ok": bool(ok)}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="GOLD specialist 8 validation AI review pipeline.")
    p.add_argument("--trade-outcome-csv", type=Path, default=DEFAULT_TRADE_OUTCOME_CSV)
    p.add_argument("--out-root", type=Path, default=DEFAULT_OUT_ROOT)
    p.add_argument("--run-stamp", default="")
    p.add_argument("--review-ledger-jsonl", type=Path, default=Path(""), help="Persistent review ledger. Default: out-root/trade_ai_review_ledger.jsonl")
    p.add_argument("--review-target", choices=["all", "group", "component"], default="all")
    p.add_argument("--mql5-files-dir", type=Path, default=DEFAULT_MQL5_FILES_DIR)
    p.add_argument("--m15-file", default="goldsharp_m15.csv")
    p.add_argument("--m5-file", default="goldsharp_m5.csv")
    p.add_argument("--h1-file", default="goldsharp_h1.csv")
    p.add_argument("--h4-file", default="goldsharp_h4.csv")
    p.add_argument("--d1-file", default="goldsharp_d1.csv")
    p.add_argument("--gold-m15-csv", default="")
    p.add_argument("--gold-m5-csv", default="")
    p.add_argument("--gold-h1-csv", default="")
    p.add_argument("--gold-h4-csv", default="")
    p.add_argument("--gold-d1-csv", default="")
    p.add_argument("--model", default="gpt-5-mini")
    p.add_argument("--max-items", type=int, default=0)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--overwrite-review-ledger", action="store_true")
    p.add_argument("--min-sample", type=int, default=5)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    stamp = args.run_stamp.strip() or local_stamp()
    out_root = args.out_root
    run_dir = run_dir_from_root(out_root, stamp)
    mkdirp(run_dir)
    review_ledger_jsonl = args.review_ledger_jsonl if str(args.review_ledger_jsonl) else out_root / "trade_ai_review_ledger.jsonl"
    if not exists(review_ledger_jsonl):
        mkdirp(review_ledger_jsonl.parent)
        with open(wpath(review_ledger_jsonl), "w", encoding="utf-8", newline="") as f:
            f.write("")

    summary_json = run_dir / "gold_specialist_8_validation_ai_review_pipeline_summary.json"
    latest_summary_json = out_root / "latest_gold_specialist_8_validation_ai_review_pipeline_summary.json"
    latest_run_dir_txt = out_root / "latest_run_dir.txt"
    normalized_csv = run_dir / "gold_specialist_8_validation_trade_outcome_normalized.csv"
    reviewable_csv = run_dir / "gold_specialist_8_validation_trade_outcome_reviewable.csv"
    rejected_csv = run_dir / "gold_specialist_8_validation_trade_outcome_rejected.csv"
    feature_csv = run_dir / "trade_feature_snapshot.csv"
    feature_jsonl = run_dir / "trade_feature_snapshot.jsonl"
    feature_summary_json = run_dir / "trade_feature_snapshot_summary.json"
    payload_jsonl = run_dir / "trade_ai_review_payloads.jsonl"
    payload_summary_json = run_dir / "trade_ai_review_payloads_summary.json"
    pending_jsonl = run_dir / "trade_ai_review_payloads_pending.jsonl"
    review_run_summary_json = run_dir / "trade_ai_review_run_summary.json"
    tag_summary_csv = run_dir / "trade_ai_tag_summary.csv"
    tag_summary_json = run_dir / "trade_ai_tag_summary.json"

    if not exists(args.trade_outcome_csv):
        summary = {
            "schema_version": SCHEMA_VERSION,
            "created_at_utc": utc_now(),
            "cycle_ok": True,
            "reason": "NO_VALIDATION_TRADE_OUTCOME_CSV_YET",
            "trade_outcome_csv": str(args.trade_outcome_csv),
            "out_root": str(out_root),
            "run_dir": str(run_dir),
            "key_metrics": {"input_rows": 0, "reviewable_rows": 0, "pending_rows": 0, "review_rows_final": 0},
        }
        write_json(summary_json, summary)
        write_json(latest_summary_json, summary)
        with open(wpath(latest_run_dir_txt), "w", encoding="utf-8", newline="") as f:
            f.write(str(run_dir))
        print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)
        return 0

    raw = read_csv(args.trade_outcome_csv)
    normalized, rejected = normalize_validation_trade_rows(raw, review_target=args.review_target)
    write_csv(normalized, normalized_csv)
    reviewable = normalized[normalized["outcome"].astype(str).str.upper().isin(REVIEWABLE_OUTCOMES)].copy() if not normalized.empty else normalized.copy()
    write_csv(reviewable, reviewable_csv)
    write_csv(rejected, rejected_csv)

    steps: list[dict[str, Any]] = []
    if reviewable.empty:
        summary = {
            "schema_version": SCHEMA_VERSION,
            "created_at_utc": utc_now(),
            "cycle_ok": True,
            "reason": "NO_REVIEWABLE_VALIDATION_TRADES",
            "trade_outcome_csv": str(args.trade_outcome_csv),
            "normalized_csv": str(normalized_csv),
            "reviewable_csv": str(reviewable_csv),
            "rejected_csv": str(rejected_csv),
            "run_dir": str(run_dir),
            "key_metrics": {"input_rows": int(len(raw)), "normalized_rows": int(len(normalized)), "reviewable_rows": 0, "rejected_rows": int(len(rejected)), "pending_rows": 0},
        }
        write_json(summary_json, summary)
        write_json(latest_summary_json, summary)
        with open(wpath(latest_run_dir_txt), "w", encoding="utf-8", newline="") as f:
            f.write(str(run_dir))
        print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)
        return 0

    mql5 = args.mql5_files_dir
    paths = {
        "m15": csv_path(mql5, args.gold_m15_csv, args.m15_file),
        "m5": csv_path(mql5, args.gold_m5_csv, args.m5_file),
        "h1": csv_path(mql5, args.gold_h1_csv, args.h1_file),
        "h4": csv_path(mql5, args.gold_h4_csv, args.h4_file),
        "d1": csv_path(mql5, args.gold_d1_csv, args.d1_file),
    }
    steps.append(cmd_run("build feature snapshots", [
        sys.executable, str(SCRIPTS_DIR / "build_trade_feature_snapshots.py"),
        "--trade-outcome-csv", str(reviewable_csv),
        "--m15-csv", paths["m15"],
        "--m5-csv", paths["m5"],
        "--h1-csv", paths["h1"],
        "--h4-csv", paths["h4"],
        "--d1-csv", paths["d1"],
        "--output-csv", str(feature_csv),
        "--output-jsonl", str(feature_jsonl),
        "--output-json", str(feature_summary_json),
    ]))
    if not steps[-1]["ok"]:
        write_json(summary_json, {"schema_version": SCHEMA_VERSION, "cycle_ok": False, "reason": "FEATURE_SNAPSHOT_FAILED", "steps": steps})
        return 1

    steps.append(cmd_run("build AI review payloads", [
        sys.executable, str(SCRIPTS_DIR / "build_trade_ai_review_payloads.py"),
        "--feature-snapshot-jsonl", str(feature_jsonl),
        "--output-jsonl", str(payload_jsonl),
        "--output-json", str(payload_summary_json),
    ]))
    if not steps[-1]["ok"]:
        write_json(summary_json, {"schema_version": SCHEMA_VERSION, "cycle_ok": False, "reason": "PAYLOAD_BUILD_FAILED", "steps": steps})
        return 1

    pending_report = filter_pending_payloads(payload_jsonl, review_ledger_jsonl, pending_jsonl)
    if pending_report["pending_rows"] > 0:
        review_cmd = [
            sys.executable, str(SCRIPTS_DIR / "run_trade_ai_review_from_payloads.py"),
            "--payload-jsonl", str(pending_jsonl),
            "--output-jsonl", str(review_ledger_jsonl),
            "--output-json", str(review_run_summary_json),
            "--model", str(args.model),
        ]
        if args.max_items:
            review_cmd.extend(["--max-items", str(args.max_items)])
        if args.dry_run:
            review_cmd.append("--dry-run")
        if args.overwrite_review_ledger:
            review_cmd.append("--overwrite")
        steps.append(cmd_run("run AI review", review_cmd))
        if not steps[-1]["ok"]:
            write_json(summary_json, {"schema_version": SCHEMA_VERSION, "cycle_ok": False, "reason": "AI_REVIEW_FAILED", "steps": steps})
            return 1
    else:
        write_json(review_run_summary_json, {"created_at_utc": utc_now(), "reason": "NO_PENDING_PAYLOADS", **pending_report})

    steps.append(cmd_run("summarize AI review tags", [
        sys.executable, str(SCRIPTS_DIR / "summarize_trade_ai_review_ledger.py"),
        "--trade-outcome-csv", str(reviewable_csv),
        "--ai-review-jsonl", str(review_ledger_jsonl),
        "--output-csv", str(tag_summary_csv),
        "--output-json", str(tag_summary_json),
        "--min-sample", str(args.min_sample),
    ], allow_failure=True))

    final_reviews = read_jsonl(review_ledger_jsonl) if exists(review_ledger_jsonl) else []
    summary = {
        "schema_version": SCHEMA_VERSION,
        "created_at_utc": utc_now(),
        "cycle_ok": True,
        "reason": "OK",
        "trade_outcome_csv": str(args.trade_outcome_csv),
        "out_root": str(out_root),
        "run_dir": str(run_dir),
        "latest_run_dir_txt": str(latest_run_dir_txt),
        "review_ledger_jsonl": str(review_ledger_jsonl),
        "normalized_csv": str(normalized_csv),
        "reviewable_csv": str(reviewable_csv),
        "rejected_csv": str(rejected_csv),
        "feature_csv": str(feature_csv),
        "feature_jsonl": str(feature_jsonl),
        "payload_jsonl": str(payload_jsonl),
        "pending_jsonl": str(pending_jsonl),
        "tag_summary_csv": str(tag_summary_csv),
        "tag_summary_json": str(tag_summary_json),
        "steps": steps,
        "pending_report": pending_report,
        "key_metrics": {
            "input_rows": int(len(raw)),
            "normalized_rows": int(len(normalized)),
            "reviewable_rows": int(len(reviewable)),
            "rejected_rows": int(len(rejected)),
            "payload_rows": int(pending_report.get("payload_rows", 0)),
            "pending_rows": int(pending_report.get("pending_rows", 0)),
            "review_rows_final": int(len(final_reviews)),
        },
        "safety": {
            "strategy_rules_modified": False,
            "ai_review_role": "HYPOTHESIS_TAGGING_ONLY",
            "live_loop": False,
            "mt5_order_send": False,
        },
    }
    write_json(summary_json, summary)
    write_json(latest_summary_json, summary)
    with open(wpath(latest_run_dir_txt), "w", encoding="utf-8", newline="") as f:
        f.write(str(run_dir))
    print(json.dumps({"cycle_ok": True, "reason": "OK", "run_dir": str(run_dir), "key_metrics": summary["key_metrics"]}, ensure_ascii=False, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
