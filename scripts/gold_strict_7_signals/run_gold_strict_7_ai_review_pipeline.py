#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""Run AI review pipeline for GOLD strict seven-signal backtest trades.

This wrapper is intentionally separated from live GOLD AI review outputs.

Default flow:
1. Read data/research_results/gold_strict_7_signal_candidates/gold_strict_7_candidates_trades.csv
2. Build a balanced, loss-weighted sample:
   - include all wins by default
   - include losses up to wins * --loss-win-ratio per strategy
   - keep breakevens if any, capped separately
3. Convert sampled trades into live-compatible trade_outcome_ledger.csv
4. Build feature snapshots with existing AI review tooling
5. Build AI review payloads
6. Run AI review from payloads, or dry-run placeholders when --dry-run
7. Summarize AI hypothesis tags

Safety:
- No Discord send
- No MT5 calls
- No order_send
- No live runtime ledger mutation
- AI review is HYPOTHESIS_TAGGING_ONLY
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
DEFAULT_MQL5_FILES_DIR = Path(r"C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files")
DEFAULT_TRADES_CSV = Path("data/research_results/gold_strict_7_signal_candidates/gold_strict_7_candidates_trades.csv")
DEFAULT_OUT_DIR = Path("data/runtime_logs/trade_ai_review_backtest_gold_strict_7")
EVALUATED_OUTCOMES = {"WIN", "LOSS", "BREAKEVEN", "SMALL_WIN", "SMALL_LOSS"}
WIN_OUTCOMES = {"WIN", "SMALL_WIN"}
LOSS_OUTCOMES = {"LOSS", "SMALL_LOSS"}
BREAKEVEN_OUTCOMES = {"BREAKEVEN"}


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


def read_csv(path: str | Path) -> pd.DataFrame:
    return pd.read_csv(windows_long_path(path), encoding="utf-8-sig", sep=None, engine="python")


def write_csv(df: pd.DataFrame, path: str | Path) -> None:
    ensure_parent(path)
    df.to_csv(windows_long_path(path), index=False, encoding="utf-8-sig")


def write_text(path: str | Path, text: str) -> None:
    ensure_parent(path)
    with open(windows_long_path(path), "w", encoding="utf-8", newline="") as f:
        f.write(text)


def write_json(path: str | Path, obj: dict[str, Any]) -> None:
    write_text(path, json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True, default=str))


def read_json(path: str | Path) -> dict[str, Any]:
    try:
        with open(windows_long_path(path), "r", encoding="utf-8") as f:
            obj = json.load(f)
        return obj if isinstance(obj, dict) else {}
    except Exception:
        return {}


def jsonl_count(path: str | Path) -> int:
    if not path_exists(path):
        return 0
    n = 0
    with open(windows_long_path(path), "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                n += 1
    return n


def csv_count(path: str | Path) -> int:
    if not path_exists(path):
        return 0
    try:
        return int(len(read_csv(path)))
    except Exception:
        return 0


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


def outcome_bucket(value: Any) -> str:
    text = clean_str(value).upper()
    if text in WIN_OUTCOMES:
        return "win"
    if text in LOSS_OUTCOMES:
        return "loss"
    if text in BREAKEVEN_OUTCOMES:
        return "breakeven"
    return "other"


def add_sampling_sort_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["_entry_time_sort"] = pd.to_datetime(out.get("entry_time"), errors="coerce")
    out["_abs_profit_r_sort"] = pd.to_numeric(out.get("profit_r"), errors="coerce").abs()
    return out


def deterministic_loss_sample(losses: pd.DataFrame, cap: int, seed: int) -> pd.DataFrame:
    """Return a deterministic mixed loss sample.

    We do not want only oldest/newest losses or only extreme losses.
    The sample uses thirds: worst R, newest, and deterministic random remainder.
    """
    if losses.empty or cap <= 0 or len(losses) <= cap:
        return losses.copy()
    work = add_sampling_sort_columns(losses)
    n_worst = max(1, cap // 3)
    n_newest = max(1, cap // 3)
    worst = work.sort_values("profit_r", ascending=True, kind="mergesort").head(n_worst)
    remaining = work.drop(index=worst.index, errors="ignore")
    newest = remaining.sort_values("_entry_time_sort", ascending=False, kind="mergesort").head(n_newest)
    remaining = remaining.drop(index=newest.index, errors="ignore")
    rest_cap = cap - len(worst) - len(newest)
    if rest_cap > 0 and not remaining.empty:
        random_part = remaining.sample(n=min(rest_cap, len(remaining)), random_state=int(seed))
        out = pd.concat([worst, newest, random_part], ignore_index=False, sort=False)
    else:
        out = pd.concat([worst, newest], ignore_index=False, sort=False)
    out = out.drop(columns=[c for c in ["_entry_time_sort", "_abs_profit_r_sort"] if c in out.columns], errors="ignore")
    return out


def build_balanced_sample(trades: pd.DataFrame, args: argparse.Namespace) -> tuple[pd.DataFrame, dict[str, Any]]:
    work = trades.copy()
    if "outcome" not in work.columns:
        raise RuntimeError("input trades CSV must contain outcome column")
    if "strategy_id" not in work.columns:
        raise RuntimeError("input trades CSV must contain strategy_id column")
    work["_bucket"] = work["outcome"].map(outcome_bucket)
    evaluated = work[work["_bucket"].isin(["win", "loss", "breakeven"])].copy()

    selected_parts: list[pd.DataFrame] = []
    per_strategy: dict[str, Any] = {}
    for strategy_id, group in evaluated.groupby("strategy_id", dropna=False):
        sid = clean_str(strategy_id, "UNKNOWN_STRATEGY")
        wins = group[group["_bucket"] == "win"].copy()
        losses = group[group["_bucket"] == "loss"].copy()
        bes = group[group["_bucket"] == "breakeven"].copy()
        if args.include_all_wins:
            selected_wins = wins.copy()
        else:
            cap = min(int(args.max_wins_per_strategy), len(wins)) if args.max_wins_per_strategy > 0 else len(wins)
            selected_wins = add_sampling_sort_columns(wins).sort_values("_entry_time_sort", kind="mergesort").tail(cap).drop(columns=["_entry_time_sort", "_abs_profit_r_sort"], errors="ignore")
        loss_cap_base = len(selected_wins) if len(selected_wins) > 0 else int(args.loss_cap_when_no_wins)
        loss_cap = int(round(float(args.loss_win_ratio) * float(loss_cap_base)))
        if args.max_losses_per_strategy > 0:
            loss_cap = min(loss_cap, int(args.max_losses_per_strategy))
        selected_losses = deterministic_loss_sample(losses, loss_cap, seed=int(args.sample_seed) + len(per_strategy) * 17)
        be_cap = min(len(bes), int(args.max_breakevens_per_strategy)) if args.max_breakevens_per_strategy >= 0 else len(bes)
        selected_bes = add_sampling_sort_columns(bes).sort_values("_entry_time_sort", kind="mergesort").tail(be_cap).drop(columns=["_entry_time_sort", "_abs_profit_r_sort"], errors="ignore") if be_cap > 0 else bes.iloc[0:0].copy()
        selected_parts.extend([selected_wins, selected_losses, selected_bes])
        per_strategy[sid] = {
            "source_wins": int(len(wins)),
            "source_losses": int(len(losses)),
            "source_breakevens": int(len(bes)),
            "selected_wins": int(len(selected_wins)),
            "selected_losses": int(len(selected_losses)),
            "selected_breakevens": int(len(selected_bes)),
            "loss_cap": int(loss_cap),
        }

    if selected_parts:
        selected = pd.concat(selected_parts, ignore_index=True, sort=False)
    else:
        selected = evaluated.iloc[0:0].copy()
    selected = selected.drop(columns=["_bucket"], errors="ignore")
    selected["_entry_time_sort"] = pd.to_datetime(selected.get("entry_time"), errors="coerce")
    selected = selected.sort_values(["_entry_time_sort", "strategy_id"], kind="mergesort").drop(columns=["_entry_time_sort"], errors="ignore").reset_index(drop=True)

    if args.max_total_items > 0 and len(selected) > int(args.max_total_items):
        # Preserve all wins first, then trim losses deterministically if a global cap is requested.
        tmp = selected.copy()
        tmp["_bucket"] = tmp["outcome"].map(outcome_bucket)
        wins = tmp[tmp["_bucket"] == "win"].copy()
        nonwins = tmp[tmp["_bucket"] != "win"].copy()
        remaining_cap = max(0, int(args.max_total_items) - len(wins))
        nonwins = deterministic_loss_sample(nonwins, remaining_cap, seed=int(args.sample_seed) + 999) if remaining_cap > 0 else nonwins.iloc[0:0].copy()
        selected = pd.concat([wins, nonwins], ignore_index=True, sort=False).drop(columns=["_bucket"], errors="ignore")
        selected["_entry_time_sort"] = pd.to_datetime(selected.get("entry_time"), errors="coerce")
        selected = selected.sort_values(["_entry_time_sort", "strategy_id"], kind="mergesort").drop(columns=["_entry_time_sort"], errors="ignore").reset_index(drop=True)

    selected["ai_review_sample_mode"] = str(args.sample_mode)
    selected["ai_review_sample_loss_win_ratio"] = float(args.loss_win_ratio)

    selected_bucket_counts = selected["outcome"].map(outcome_bucket).value_counts(dropna=False).to_dict() if not selected.empty else {}
    summary = {
        "schema_version": "gold_strict_7_ai_review_sample_v1",
        "created_at_utc": utc_now_text(),
        "sample_mode": args.sample_mode,
        "include_all_wins": bool(args.include_all_wins),
        "loss_win_ratio": float(args.loss_win_ratio),
        "max_total_items": int(args.max_total_items),
        "source_rows": int(len(trades)),
        "source_evaluated_rows": int(len(evaluated)),
        "selected_rows": int(len(selected)),
        "source_bucket_counts": evaluated["_bucket"].value_counts(dropna=False).to_dict() if not evaluated.empty else {},
        "selected_bucket_counts": selected_bucket_counts,
        "per_strategy": per_strategy,
    }
    return selected, summary


def csv_path(csv_dir: Path, explicit: str, filename: str) -> str:
    return explicit if explicit else str(csv_dir / filename)


def optional_existing(path_text: str) -> str:
    return path_text if path_text and path_exists(path_text) else ""


def run_cmd(label: str, cmd: list[str], *, cwd: Path = REPO_ROOT, allow_failure: bool = False) -> dict[str, Any]:
    print("=" * 80, flush=True)
    print(f"[STEP] {label}", flush=True)
    print("[CMD] " + " ".join(cmd), flush=True)
    started = time.perf_counter()
    completed = subprocess.run(cmd, cwd=str(cwd), text=True, encoding="utf-8", errors="replace")
    elapsed = round(time.perf_counter() - started, 3)
    ok = completed.returncode == 0 or allow_failure
    print(f"[STEP] {label} returncode={completed.returncode} elapsed_seconds={elapsed} ok={ok}", flush=True)
    return {"label": label, "cmd": cmd, "returncode": int(completed.returncode), "elapsed_seconds": elapsed, "allow_failure": bool(allow_failure), "ok": bool(ok)}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run GOLD strict 7 backtest AI review pipeline.")
    p.add_argument("--strict-7-trades-csv", type=Path, default=DEFAULT_TRADES_CSV)
    p.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    p.add_argument("--mql5-files-dir", type=Path, default=DEFAULT_MQL5_FILES_DIR)
    p.add_argument("--gold-m15-csv", default="")
    p.add_argument("--gold-m5-csv", default="")
    p.add_argument("--gold-h1-csv", default="")
    p.add_argument("--gold-h4-csv", default="")
    p.add_argument("--gold-d1-csv", default="")
    p.add_argument("--m15-file", default="goldsharp_m15.csv")
    p.add_argument("--m5-file", default="goldsharp_m5.csv")
    p.add_argument("--h1-file", default="goldsharp_h1.csv")
    p.add_argument("--h4-file", default="goldsharp_h4.csv")
    p.add_argument("--d1-file", default="goldsharp_d1.csv")
    p.add_argument("--sample-mode", choices=["balanced_loss_weighted", "all"], default="balanced_loss_weighted")
    p.add_argument("--loss-win-ratio", type=float, default=2.0)
    p.add_argument("--include-all-wins", action=argparse.BooleanOptionalAction, default=True)
    p.add_argument("--loss-cap-when-no-wins", type=int, default=20)
    p.add_argument("--max-wins-per-strategy", type=int, default=0, help="0 = no cap when --no-include-all-wins")
    p.add_argument("--max-losses-per-strategy", type=int, default=0, help="0 = no additional cap")
    p.add_argument("--max-breakevens-per-strategy", type=int, default=10)
    p.add_argument("--max-total-items", type=int, default=0, help="0 = no global cap")
    p.add_argument("--sample-seed", type=int, default=42)
    p.add_argument("--pre-m15-bars", type=int, default=100)
    p.add_argument("--post-m15-bars", type=int, default=20)
    p.add_argument("--pre-m5-bars", type=int, default=100)
    p.add_argument("--post-m5-bars", type=int, default=240)
    p.add_argument("--model", default="gpt-5-mini")
    p.add_argument("--max-review-items", type=int, default=0, help="0 = all sampled payloads")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--skip-ai-review", action="store_true")
    p.add_argument("--overwrite-review-jsonl", action=argparse.BooleanOptionalAction, default=True)
    p.add_argument("--min-sample", type=int, default=5)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    started = time.perf_counter()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    if not path_exists(args.strict_7_trades_csv):
        raise SystemExit(f"strict 7 trades CSV not found: {args.strict_7_trades_csv}")

    paths = {
        "sampled_trades_csv": args.out_dir / "gold_strict_7_ai_review_sampled_trades.csv",
        "sample_summary_json": args.out_dir / "gold_strict_7_ai_review_sample_summary.json",
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
        "pipeline_summary_json": args.out_dir / "gold_strict_7_ai_review_pipeline_summary.json",
    }

    print("=" * 80, flush=True)
    print("GOLD strict 7 AI review pipeline", flush=True)
    print(f"strict_7_trades_csv={args.strict_7_trades_csv}", flush=True)
    print(f"out_dir={args.out_dir}", flush=True)
    print(f"sample_mode={args.sample_mode} loss_win_ratio={args.loss_win_ratio} include_all_wins={args.include_all_wins}", flush=True)
    print(f"dry_run={args.dry_run} skip_ai_review={args.skip_ai_review}", flush=True)
    print("=" * 80, flush=True)

    trades = read_csv(args.strict_7_trades_csv)
    if args.sample_mode == "all":
        sampled = trades[trades["outcome"].map(outcome_bucket).isin(["win", "loss", "breakeven"])].copy()
        sample_summary = {"schema_version": "gold_strict_7_ai_review_sample_v1", "created_at_utc": utc_now_text(), "sample_mode": "all", "source_rows": int(len(trades)), "selected_rows": int(len(sampled)), "selected_bucket_counts": sampled["outcome"].map(outcome_bucket).value_counts(dropna=False).to_dict() if not sampled.empty else {}}
    else:
        sampled, sample_summary = build_balanced_sample(trades, args)
    write_csv(sampled, paths["sampled_trades_csv"])
    write_json(paths["sample_summary_json"], sample_summary)

    csv_dir = Path(args.mql5_files_dir)
    m15_csv = csv_path(csv_dir, args.gold_m15_csv, args.m15_file)
    m5_csv = csv_path(csv_dir, args.gold_m5_csv, args.m5_file)
    h1_csv = csv_path(csv_dir, args.gold_h1_csv, args.h1_file)
    h4_csv = csv_path(csv_dir, args.gold_h4_csv, args.h4_file)
    d1_csv = csv_path(csv_dir, args.gold_d1_csv, args.d1_file)
    if not path_exists(m15_csv):
        raise SystemExit(f"GOLD M15 CSV not found: {m15_csv}")

    steps: list[dict[str, Any]] = []
    outcome_cmd = [
        sys.executable, str(REPO_ROOT / "scripts" / "build_trade_outcome_ledger_from_backtest_trades.py"),
        "--backtest-trades-csv", str(paths["sampled_trades_csv"]),
        "--output-csv", str(paths["trade_outcome_csv"]),
        "--output-json", str(paths["trade_outcome_json"]),
        "--symbol", "GOLD",
        "--broker-symbol", "GOLD#",
        "--strategy-id", "",
        "--max-losses", "0",
        "--max-wins", "0",
        "--max-breakevens", "0",
        "--sample-policy", "oldest",
    ]
    steps.append(run_cmd("build_trade_outcome_ledger_from_backtest_trades", outcome_cmd))
    if not steps[-1]["ok"]:
        return 1

    snapshot_cmd = [
        sys.executable, str(REPO_ROOT / "scripts" / "build_trade_feature_snapshots.py"),
        "--trade-outcome-csv", str(paths["trade_outcome_csv"]),
        "--m15-csv", str(m15_csv),
        "--output-csv", str(paths["feature_snapshot_csv"]),
        "--output-jsonl", str(paths["feature_snapshot_jsonl"]),
        "--output-json", str(paths["feature_snapshot_json"]),
        "--pre-m15-bars", str(args.pre_m15_bars),
        "--post-m15-bars", str(args.post_m15_bars),
        "--pre-m5-bars", str(args.pre_m5_bars),
        "--post-m5-bars", str(args.post_m5_bars),
    ]
    for flag, value in [
        ("--m5-csv", optional_existing(m5_csv)),
        ("--h1-csv", optional_existing(h1_csv)),
        ("--h4-csv", optional_existing(h4_csv)),
        ("--d1-csv", optional_existing(d1_csv)),
    ]:
        if value:
            snapshot_cmd.extend([flag, value])
    steps.append(run_cmd("build_trade_feature_snapshots", snapshot_cmd))
    if not steps[-1]["ok"]:
        return 2

    payload_cmd = [
        sys.executable, str(REPO_ROOT / "scripts" / "build_trade_ai_review_payloads.py"),
        "--feature-snapshot-jsonl", str(paths["feature_snapshot_jsonl"]),
        "--output-jsonl", str(paths["payload_jsonl"]),
        "--output-json", str(paths["payload_json"]),
        "--max-pre-m15-bars-in-prompt", str(args.pre_m15_bars),
        "--max-post-m15-bars-in-prompt", str(args.post_m15_bars),
    ]
    steps.append(run_cmd("build_trade_ai_review_payloads", payload_cmd))
    if not steps[-1]["ok"]:
        return 3

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
        if args.max_review_items > 0:
            review_cmd.extend(["--max-items", str(args.max_review_items)])
        if args.dry_run:
            review_cmd.append("--dry-run")
        steps.append(run_cmd("run_trade_ai_review_from_payloads", review_cmd))
        if not steps[-1]["ok"]:
            return 4
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
    steps.append(run_cmd("summarize_trade_ai_review_ledger", summary_cmd))
    if not steps[-1]["ok"]:
        return 5

    outcome_summary = read_json(paths["trade_outcome_json"])
    feature_summary = read_json(paths["feature_snapshot_json"])
    payload_summary = read_json(paths["payload_json"])
    review_summary = read_json(paths["review_json"])
    tag_summary = read_json(paths["tag_summary_json"])
    pipeline_summary = {
        "schema_version": "gold_strict_7_ai_review_pipeline_v1",
        "created_at_utc": utc_now_text(),
        "cycle_ok": True,
        "out_dir": str(args.out_dir),
        "paths": {k: str(v) for k, v in paths.items()},
        "sample_summary": sample_summary,
        "inputs": {
            "strict_7_trades_csv": str(args.strict_7_trades_csv),
            "m15_csv": m15_csv,
            "m5_csv": optional_existing(m5_csv),
            "h1_csv": optional_existing(h1_csv),
            "h4_csv": optional_existing(h4_csv),
            "d1_csv": optional_existing(d1_csv),
        },
        "key_metrics": {
            "sampled_trades_rows": csv_count(paths["sampled_trades_csv"]),
            "outcome_rows": csv_count(paths["trade_outcome_csv"]),
            "feature_snapshot_rows": csv_count(paths["feature_snapshot_csv"]),
            "payload_rows_jsonl": jsonl_count(paths["payload_jsonl"]),
            "review_rows_jsonl": jsonl_count(paths["review_jsonl"]),
            "review_rows_written": review_summary.get("rows_written"),
            "review_error_rows": review_summary.get("error_rows"),
            "tag_summary_rows": csv_count(paths["tag_summary_csv"]),
            "should_investigate_rows": tag_summary.get("should_investigate_rows"),
        },
        "safety": {
            "discord_send": False,
            "mt5_calls": False,
            "order_send": False,
            "runtime_state_mutation": False,
            "ai_hypothesis_only": True,
            "single_trade_rule_change_allowed": False,
            "live_outputs_modified": False,
        },
        "component_summaries": {
            "outcome": outcome_summary,
            "feature": feature_summary,
            "payload": payload_summary,
            "review": review_summary,
            "tag": tag_summary,
        },
        "steps": steps,
        "timing": {"total_seconds": round(time.perf_counter() - started, 3)},
    }
    write_json(paths["pipeline_summary_json"], pipeline_summary)

    print("=" * 80, flush=True)
    print("GOLD strict 7 AI review pipeline summary", flush=True)
    print(json.dumps({
        "cycle_ok": True,
        "sampled_trades_rows": pipeline_summary["key_metrics"]["sampled_trades_rows"],
        "payload_rows_jsonl": pipeline_summary["key_metrics"]["payload_rows_jsonl"],
        "review_rows_jsonl": pipeline_summary["key_metrics"]["review_rows_jsonl"],
        "review_error_rows": pipeline_summary["key_metrics"].get("review_error_rows"),
        "tag_summary_rows": pipeline_summary["key_metrics"]["tag_summary_rows"],
        "should_investigate_rows": pipeline_summary["key_metrics"].get("should_investigate_rows"),
        "pipeline_summary_json": str(paths["pipeline_summary_json"]),
    }, ensure_ascii=False, indent=2, sort_keys=True), flush=True)
    print("=" * 80, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
