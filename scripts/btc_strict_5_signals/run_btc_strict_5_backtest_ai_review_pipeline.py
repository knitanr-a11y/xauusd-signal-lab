#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""Run AI review for all BTC strict-5 backtest trades.

This pipeline is for BACKTEST AI review, not live post-trade AI review.
It evaluates the deterministic BTC strict-5 backtest trade ledger and writes
AI hypothesis tags for every closed backtest trade by default.

Flow:
1. Convert btc_strict_5_backtest_trades.csv to trade_outcome_ledger.csv.
2. Build feature snapshots with M15/M5/H1/H4 candle context.
3. Build OpenAI-ready payload JSONL.
4. Run AI review for all payloads unless --dry-run is passed.
5. Summarize AI hypothesis tags.

Safety / contract:
- no MT5 call
- no order_send
- no Discord send
- no runtime trading ledger mutation
- D1 is not used by this BTC strict-5 backtest AI review by default
- AI output is hypothesis tagging only and must not directly change rules
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
SCRIPTS_DIR = REPO_ROOT / "scripts"
DEFAULT_MQL5_FILES_DIR = Path(r"C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files")
DEFAULT_BACKTEST_DIR = Path("data/research_results/btc_strict_5_signal_candidates")
DEFAULT_OUT_DIR = Path("data/research_results/btc_strict_5_backtest_ai_review")
SCHEMA_VERSION = "btc_strict_5_backtest_ai_review_pipeline_v1"


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


def resolve_repo_path(path: str | Path) -> Path:
    p = Path(path)
    if p.is_absolute():
        return p
    return REPO_ROOT / p


def ensure_parent(path: str | Path) -> None:
    Path(windows_long_path(Path(path).parent)).mkdir(parents=True, exist_ok=True)


def utc_now_text() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")


def read_csv_auto(path: str | Path) -> pd.DataFrame:
    return pd.read_csv(windows_long_path(path), encoding="utf-8-sig", sep=None, engine="python")


def write_csv(df: pd.DataFrame, path: str | Path) -> None:
    ensure_parent(path)
    df.to_csv(windows_long_path(path), index=False, encoding="utf-8-sig")


def write_json(path: str | Path, obj: dict[str, Any]) -> None:
    ensure_parent(path)
    with open(windows_long_path(path), "w", encoding="utf-8", newline="") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2, sort_keys=True, default=str)


def read_json_or_empty(path: str | Path) -> dict[str, Any]:
    try:
        with open(windows_long_path(path), "r", encoding="utf-8") as f:
            obj = json.load(f)
        return obj if isinstance(obj, dict) else {}
    except Exception:
        return {}


def jsonl_count(path: str | Path) -> int:
    p = Path(path)
    if not p.exists():
        return 0
    n = 0
    with open(windows_long_path(p), "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                n += 1
    return n


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


def clean_float(value: Any, default: float | None = None) -> float | None:
    if value is None or value == "":
        return default
    try:
        if pd.isna(value):
            return default
    except Exception:
        pass
    try:
        return float(value)
    except Exception:
        return default


def time_text(value: Any) -> str:
    ts = pd.to_datetime(value, errors="coerce")
    if pd.isna(ts):
        return clean_str(value)
    return pd.Timestamp(ts).strftime("%Y-%m-%d %H:%M:%S")


def stable_key(prefix: str, row: pd.Series) -> str:
    strategy_id = clean_str(row.get("strategy_id"), clean_str(row.get("candidate_base"), "BTC_STRICT5_UNKNOWN"))
    direction = clean_str(row.get("direction"), "UNKNOWN")
    signal_time = time_text(row.get("signal_time"))
    return "|".join([prefix, "BTC", "STRICT5_BACKTEST", strategy_id, direction, signal_time])


def derive_entry_price(row: pd.Series) -> float | None:
    direction = clean_str(row.get("direction")).upper()
    if direction == "BUY":
        return clean_float(row.get("entry_ask"), clean_float(row.get("entry_price_reference")))
    if direction == "SELL":
        return clean_float(row.get("entry_bid"), clean_float(row.get("entry_price_reference")))
    return clean_float(row.get("entry_price_reference"), clean_float(row.get("entry_bid"), clean_float(row.get("entry_ask"))))


def derive_close_price(row: pd.Series) -> float | None:
    direction = clean_str(row.get("direction")).upper()
    if direction == "BUY":
        return clean_float(row.get("close_bid"), clean_float(row.get("close_price")))
    if direction == "SELL":
        return clean_float(row.get("close_ask"), clean_float(row.get("close_price")))
    return clean_float(row.get("close_price"), clean_float(row.get("close_bid"), clean_float(row.get("close_ask"))))


def normalize_outcome(value: Any, profit_r: Any) -> str:
    text = clean_str(value).upper()
    if text in {"WIN", "LOSS", "BREAKEVEN", "OPEN", "UNKNOWN"}:
        return text
    if text in {"HORIZON_EXIT", "TIME_EXIT"}:
        r = clean_float(profit_r, 0.0) or 0.0
        if r > 1e-12:
            return "SMALL_WIN"
        if r < -1e-12:
            return "SMALL_LOSS"
        return "BREAKEVEN"
    r = clean_float(profit_r)
    if r is None:
        return "UNKNOWN"
    if r > 1e-12:
        return "WIN"
    if r < -1e-12:
        return "LOSS"
    return "BREAKEVEN"


def convert_backtest_trades_to_outcome(backtest_trades_csv: Path, output_csv: Path) -> dict[str, Any]:
    src = read_csv_auto(backtest_trades_csv)
    rows: list[dict[str, Any]] = []
    for _, row in src.iterrows():
        profit_r = clean_float(row.get("profit_r"), clean_float(row.get("net_profit_r")))
        outcome = normalize_outcome(row.get("outcome"), profit_r)
        strategy_id = clean_str(row.get("strategy_id"), clean_str(row.get("candidate_base"), "BTC_STRICT5_UNKNOWN"))
        candidate_base = clean_str(row.get("candidate_base"), strategy_id)
        direction = clean_str(row.get("direction")).upper()
        entry_price = derive_entry_price(row)
        close_price = derive_close_price(row)
        trade_id = clean_str(row.get("trade_id"), stable_key("TRADE", row))
        out = {
            "created_at_utc": utc_now_text(),
            "source": "btc_strict_5_backtest",
            "trade_id": trade_id,
            "order_key": clean_str(row.get("order_key"), stable_key("ORDER", row)),
            "payload_key": clean_str(row.get("payload_key"), stable_key("PAYLOAD", row)),
            "signal_key": clean_str(row.get("signal_key"), stable_key("SIGNAL", row)),
            "symbol": "BTC",
            "broker_symbol": clean_str(row.get("broker_symbol"), "BTCUSD#"),
            "strategy_key": strategy_id,
            "strategy_alias": candidate_base,
            "strategy_id": strategy_id,
            "condition_id": strategy_id,
            "router_strategy_slot": candidate_base,
            "router_strategy_id": strategy_id,
            "pair_name": candidate_base,
            "candidate_rank": clean_str(row.get("candidate_rank"), ""),
            "direction": direction,
            "lot": clean_float(row.get("lot"), 0.0),
            "entry_time": time_text(row.get("entry_time")),
            "entry_price": entry_price,
            "entry_price_reference": clean_float(row.get("entry_price_reference"), entry_price),
            "sl_price": clean_float(row.get("sl_price")),
            "tp_price": clean_float(row.get("tp_price")),
            "close_time": time_text(row.get("close_time")),
            "close_price": close_price,
            "profit": clean_float(row.get("profit_price_net"), clean_float(row.get("profit"))),
            "profit_points": clean_float(row.get("profit_pips_net"), clean_float(row.get("profit_points"))),
            "profit_r": profit_r,
            "net_profit": clean_float(row.get("profit_price_net"), clean_float(row.get("net_profit"))),
            "outcome": outcome,
            "raw_backtest_outcome": clean_str(row.get("outcome")),
            "close_reason": clean_str(row.get("close_reason")),
            "holding_minutes": clean_float(row.get("holding_minutes")),
            "match_status": "MATCHED",
            "match_method": "BACKTEST_M5_FIRST_TOUCH",
            "execution_status": "EXECUTED",
            "signal_time": time_text(row.get("signal_time")),
            "base_close_time": time_text(row.get("base_close_time")),
            "tp_price_distance": clean_float(row.get("tp_price_distance")),
            "sl_price_distance": clean_float(row.get("sl_price_distance")),
            "tp_pips": clean_float(row.get("tp_pips")),
            "sl_pips": clean_float(row.get("sl_pips")),
            "rr": clean_float(row.get("rr")),
            "m5_first_touch_outcome": clean_str(row.get("outcome")),
            "m5_first_touch_time": time_text(row.get("close_time")),
            "m5_mfe_points": clean_float(row.get("mfe_price")),
            "m5_mae_points": clean_float(row.get("mae_price")),
            "m5_mfe_r": clean_float(row.get("mfe_r")),
            "m5_mae_r": clean_float(row.get("mae_r")),
            "strict_no_future_ok": bool(row.get("strict_no_future_ok", True)),
            "h1_confirmed_ok": bool(row.get("h1_confirmed_ok", True)),
            "h4_confirmed_ok": bool(row.get("h4_confirmed_ok", True)),
            "d1_used": False,
            "notes": "BTC strict 5 backtest trade converted for AI hypothesis review. D1 not used.",
        }
        rows.append(out)
    out_df = pd.DataFrame(rows)
    write_csv(out_df, output_csv)
    return {
        "input_rows": int(len(src)),
        "output_rows": int(len(out_df)),
        "strategies": sorted(out_df["strategy_id"].dropna().astype(str).unique().tolist()) if not out_df.empty else [],
        "outcome_counts": out_df["outcome"].value_counts().to_dict() if not out_df.empty else {},
        "d1_used": False,
    }


def run_cmd(label: str, cmd: list[str], *, cwd: Path = REPO_ROOT) -> dict[str, Any]:
    print("=" * 100, flush=True)
    print(f"[STEP] {label}", flush=True)
    print("[CMD] " + " ".join(cmd), flush=True)
    started = time.perf_counter()
    proc = subprocess.run(cmd, cwd=str(cwd), text=True, encoding="utf-8", errors="replace")
    elapsed = round(time.perf_counter() - started, 3)
    print(f"[STEP] {label} returncode={proc.returncode} elapsed_seconds={elapsed}", flush=True)
    return {"label": label, "cmd": cmd, "returncode": int(proc.returncode), "elapsed_seconds": elapsed, "ok": proc.returncode == 0}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run BTC strict 5 backtest AI review for all backtest trades.")
    p.add_argument("--backtest-trades-csv", type=Path, default=DEFAULT_BACKTEST_DIR / "btc_strict_5_backtest_trades.csv")
    p.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    p.add_argument("--mql5-files-dir", type=Path, default=DEFAULT_MQL5_FILES_DIR)
    p.add_argument("--m15-csv", default="")
    p.add_argument("--m5-csv", default="")
    p.add_argument("--h1-csv", default="")
    p.add_argument("--h4-csv", default="")
    p.add_argument("--model", default="gpt-5-mini")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--max-review-items", type=int, default=0, help="0 = all. Default evaluates all 295 rows.")
    p.add_argument("--min-sample", type=int, default=5)
    p.add_argument("--pre-m15-bars", type=int, default=100)
    p.add_argument("--post-m15-bars", type=int, default=20)
    p.add_argument("--pre-h1-bars", type=int, default=80)
    p.add_argument("--pre-h4-bars", type=int, default=40)
    p.add_argument("--overwrite", action=argparse.BooleanOptionalAction, default=True)
    return p.parse_args()


def choose_input_path(explicit: str, root: Path, filename: str) -> Path:
    return Path(explicit) if explicit else root / filename


def main() -> int:
    args = parse_args()
    started = time.perf_counter()
    out_dir = resolve_repo_path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    backtest_trades_csv = resolve_repo_path(args.backtest_trades_csv)
    mql5_dir = args.mql5_files_dir
    m15_csv = choose_input_path(args.m15_csv, mql5_dir, "btcusdsharp_m15.csv")
    m5_csv = choose_input_path(args.m5_csv, mql5_dir, "btcusdsharp_m5.csv")
    h1_csv = choose_input_path(args.h1_csv, mql5_dir, "btcusdsharp_h1.csv")
    h4_csv = choose_input_path(args.h4_csv, mql5_dir, "btcusdsharp_h4.csv")

    paths = {
        "trade_outcome_csv": out_dir / "trade_outcome_ledger.csv",
        "feature_snapshot_csv": out_dir / "trade_feature_snapshot.csv",
        "feature_snapshot_jsonl": out_dir / "trade_feature_snapshot.jsonl",
        "feature_snapshot_json": out_dir / "trade_feature_snapshot_summary.json",
        "payload_jsonl": out_dir / "trade_ai_review_payloads.jsonl",
        "payload_json": out_dir / "trade_ai_review_payloads_summary.json",
        "review_jsonl": out_dir / "trade_ai_review_ledger.jsonl",
        "review_json": out_dir / "trade_ai_review_run_summary.json",
        "tag_summary_csv": out_dir / "trade_ai_tag_summary.csv",
        "tag_summary_json": out_dir / "trade_ai_tag_summary.json",
        "pipeline_summary_json": out_dir / "btc_strict_5_backtest_ai_review_pipeline_summary.json",
    }

    if not backtest_trades_csv.exists():
        raise SystemExit(f"backtest trades CSV not found: {backtest_trades_csv}\nRun run_btc_strict_5_backtest_from_csv.py first.")

    steps: list[dict[str, Any]] = []
    outcome_report = convert_backtest_trades_to_outcome(backtest_trades_csv, paths["trade_outcome_csv"])
    print("=" * 100, flush=True)
    print("[STEP] convert_backtest_trades_to_outcome", flush=True)
    print(json.dumps(outcome_report, ensure_ascii=False, indent=2, sort_keys=True, default=str), flush=True)

    steps.append(run_cmd("build_trade_feature_snapshots", [
        sys.executable, str(SCRIPTS_DIR / "build_trade_feature_snapshots.py"),
        "--trade-outcome-csv", str(paths["trade_outcome_csv"]),
        "--m15-csv", str(m15_csv),
        "--m5-csv", str(m5_csv),
        "--h1-csv", str(h1_csv),
        "--h4-csv", str(h4_csv),
        "--output-csv", str(paths["feature_snapshot_csv"]),
        "--output-jsonl", str(paths["feature_snapshot_jsonl"]),
        "--output-json", str(paths["feature_snapshot_json"]),
        "--pre-m15-bars", str(args.pre_m15_bars),
        "--post-m15-bars", str(args.post_m15_bars),
        "--pre-h1-bars", str(args.pre_h1_bars),
        "--pre-h4-bars", str(args.pre_h4_bars),
    ]))
    if not steps[-1]["ok"]:
        return 1

    steps.append(run_cmd("build_trade_ai_review_payloads", [
        sys.executable, str(SCRIPTS_DIR / "build_trade_ai_review_payloads.py"),
        "--feature-snapshot-jsonl", str(paths["feature_snapshot_jsonl"]),
        "--output-jsonl", str(paths["payload_jsonl"]),
        "--output-json", str(paths["payload_json"]),
        "--max-pre-m15-bars-in-prompt", str(args.pre_m15_bars),
        "--max-post-m15-bars-in-prompt", str(args.post_m15_bars),
        "--max-pre-h1-bars-in-prompt", str(args.pre_h1_bars),
        "--max-pre-h4-bars-in-prompt", str(args.pre_h4_bars),
        "--max-pre-d1-bars-in-prompt", "0",
    ]))
    if not steps[-1]["ok"]:
        return 1

    review_cmd = [
        sys.executable, str(SCRIPTS_DIR / "run_trade_ai_review_from_payloads.py"),
        "--payload-jsonl", str(paths["payload_jsonl"]),
        "--output-jsonl", str(paths["review_jsonl"]),
        "--output-json", str(paths["review_json"]),
        "--model", str(args.model),
        "--max-items", str(args.max_review_items),
    ]
    if args.overwrite:
        review_cmd.append("--overwrite")
    if args.dry_run:
        review_cmd.append("--dry-run")
    steps.append(run_cmd("run_trade_ai_review_from_payloads", review_cmd))
    if not steps[-1]["ok"]:
        return 1

    steps.append(run_cmd("summarize_trade_ai_review_ledger", [
        sys.executable, str(SCRIPTS_DIR / "summarize_trade_ai_review_ledger.py"),
        "--trade-outcome-csv", str(paths["trade_outcome_csv"]),
        "--ai-review-jsonl", str(paths["review_jsonl"]),
        "--output-csv", str(paths["tag_summary_csv"]),
        "--output-json", str(paths["tag_summary_json"]),
        "--min-sample", str(args.min_sample),
    ]))
    if not steps[-1]["ok"]:
        return 1

    summary = {
        "schema_version": SCHEMA_VERSION,
        "created_at_utc": utc_now_text(),
        "cycle_ok": all(step.get("ok") for step in steps),
        "dry_run": bool(args.dry_run),
        "model": str(args.model),
        "max_review_items": int(args.max_review_items),
        "d1_used": False,
        "d1_csv": "NOT_USED",
        "safety": {
            "mt5_calls": False,
            "order_send": False,
            "discord_send": False,
            "runtime_trading_ledger_mutation": False,
            "ai_review_is_hypothesis_only": True,
            "should_change_strategy_from_single_trade_forced_false_by_review_runner": True,
        },
        "inputs": {
            "backtest_trades_csv": str(backtest_trades_csv),
            "m15_csv": str(m15_csv),
            "m5_csv": str(m5_csv),
            "h1_csv": str(h1_csv),
            "h4_csv": str(h4_csv),
        },
        "outputs": {k: str(v) for k, v in paths.items()},
        "rows": {
            "backtest_trades": int(outcome_report.get("input_rows", 0)),
            "trade_outcomes": int(outcome_report.get("output_rows", 0)),
            "feature_snapshot_jsonl": jsonl_count(paths["feature_snapshot_jsonl"]),
            "payload_jsonl": jsonl_count(paths["payload_jsonl"]),
            "review_jsonl": jsonl_count(paths["review_jsonl"]),
            "tag_summary_rows": int(len(read_csv_auto(paths["tag_summary_csv"]))) if Path(paths["tag_summary_csv"]).exists() else 0,
        },
        "outcome_report": outcome_report,
        "steps": steps,
        "elapsed_seconds": round(time.perf_counter() - started, 3),
    }
    write_json(paths["pipeline_summary_json"], summary)
    print("=" * 100, flush=True)
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True, default=str), flush=True)
    print("=" * 100, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
