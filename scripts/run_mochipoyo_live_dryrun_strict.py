#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Strict dry-run live scanner for Mochipoyo GOLD/BTC fixed-preset candidates.

Compared with run_mochipoyo_live_dryrun.py, this version enforces the known
validated slice universe before applying fixed filters.

This prevents broad filter names such as total_score>=10.0 or base_score>=4.0
from matching unvalidated pairs/ranks during live dry-run.

No Discord send. No AI review. Ledger only.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

# Reuse the already-tested helpers from the base dry-run script.
from run_mochipoyo_live_dryrun import (  # type: ignore
    DEFAULT_BTC_OUT_PREFIX,
    DEFAULT_BTC_PAIRS_JSON,
    DEFAULT_BTC_PRESET_JSON,
    DEFAULT_GOLD_OUT_PREFIX,
    DEFAULT_GOLD_PAIRS_JSON,
    DEFAULT_GOLD_PRESET_JSON,
    SymbolConfig,
    append_ledger,
    apply_fixed_preset,
    build_scan_cmd,
    ensure_selected_slice,
    load_preset,
    recent_filter,
    run_cmd,
    to_payload_rows,
)

DEFAULT_ALLOWED_SLICES = {
    "GOLD": [
        "GOLD_H4_M5_SCALP|B|SELL",
        "GOLD_H4_M15_DAYTRADE|B|SELL",
        "GOLD_D1_H1_DAYTRADE|B|BUY",
        "GOLD_D1_H1_DAYTRADE|A|BUY",
        "GOLD_H4_M5_SCALP|A|SELL",
        "GOLD_H4_M15_DAYTRADE|B|BUY",
    ],
    "BTC": [
        "BTC_H4_M15_DAYTRADE|A|BUY",
        "BTC_H4_M15_DAYTRADE|A|SELL",
    ],
}


def parse_allowed_slices(text: str | None, symbol: str) -> list[str]:
    if text is None or not str(text).strip():
        return list(DEFAULT_ALLOWED_SLICES[symbol])
    return [x.strip() for x in str(text).split(",") if x.strip()]


def apply_allowed_slices(events: pd.DataFrame, allowed_slices: list[str]) -> pd.DataFrame:
    work = ensure_selected_slice(events)
    if not allowed_slices:
        return work.iloc[0:0].copy()
    return work[work["selected_slice"].astype(str).isin(set(allowed_slices))].copy()


def run_symbol_strict(cfg: SymbolConfig, args: argparse.Namespace, allowed_slices: list[str]) -> dict:
    out_prefix = Path(cfg.out_prefix)
    out_prefix.parent.mkdir(parents=True, exist_ok=True)
    candidates_csv = out_prefix.with_name(out_prefix.name + "_candidates.csv")
    events_csv = out_prefix.with_name(out_prefix.name + "_events.csv")
    allowed_events_csv = out_prefix.with_name(out_prefix.name + "_allowed_events.csv")
    payload_csv = out_prefix.with_name(out_prefix.name + "_payloads.csv")

    run_cmd(build_scan_cmd(args.python, cfg, candidates_csv), dry_run_commands=args.print_commands_only)
    run_cmd(
        [args.python, "scripts/filter_mochipoyo_candidate_events.py", "--input-csv", str(candidates_csv), "--output-csv", str(events_csv)],
        dry_run_commands=args.print_commands_only,
    )
    if args.print_commands_only:
        return {"symbol": cfg.symbol, "printed_commands_only": True, "allowed_slices": allowed_slices}

    events = pd.read_csv(events_csv, encoding="utf-8-sig")
    if "entry_time" in events.columns:
        events["entry_time"] = pd.to_datetime(events["entry_time"], errors="coerce")
    events = ensure_selected_slice(events)

    allowed_events = apply_allowed_slices(events, allowed_slices)
    allowed_events.to_csv(allowed_events_csv, index=False, encoding="utf-8-sig")

    preset = load_preset(cfg.preset_json)
    fixed = apply_fixed_preset(allowed_events, preset)
    recent = recent_filter(fixed, args.scan_recent_events)
    payloads = to_payload_rows(recent, cfg, preset)
    payloads.to_csv(payload_csv, index=False, encoding="utf-8-sig")
    ledger_added, ledger_duplicate_existing, ledger_duplicate_within_batch = append_ledger(payloads, Path(args.ledger_csv))

    return {
        "symbol": cfg.symbol,
        "candidates_csv": str(candidates_csv),
        "events_csv": str(events_csv),
        "allowed_events_csv": str(allowed_events_csv),
        "payload_csv": str(payload_csv),
        "allowed_slices": allowed_slices,
        "events_rows": int(len(events)),
        "allowed_events_rows": int(len(allowed_events)),
        "fixed_match_rows": int(len(fixed)),
        "payload_rows": int(len(payloads)),
        "ledger_added_rows": int(ledger_added),
        "ledger_duplicate_existing_rows": int(ledger_duplicate_existing),
        "ledger_duplicate_within_batch_rows": int(ledger_duplicate_within_batch),
    }


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run strict Mochipoyo live dry-run scanner with allowed slice gating.")
    p.add_argument("--symbols", default="GOLD,BTC", help="Comma-separated symbols: GOLD,BTC")
    p.add_argument("--ledger-csv", default="data/results/mochipoyo/live_dryrun/mochipoyo_live_dryrun_strict_ledger.csv")
    p.add_argument("--scan-recent-events", type=int, default=20)
    p.add_argument("--python", default=sys.executable)
    p.add_argument("--print-commands-only", action="store_true")
    p.add_argument("--gold-allowed-slices", default=None, help="Comma-separated override. Default uses validated GOLD slices.")
    p.add_argument("--btc-allowed-slices", default=None, help="Comma-separated override. Default uses BTC H4/M15 A BUY/SELL only.")

    p.add_argument("--gold-pairs-json", default=DEFAULT_GOLD_PAIRS_JSON)
    p.add_argument("--gold-preset-json", default=DEFAULT_GOLD_PRESET_JSON)
    p.add_argument("--gold-out-prefix", default=DEFAULT_GOLD_OUT_PREFIX.replace("gold_mochipoyo_live_dryrun", "gold_mochipoyo_live_dryrun_strict"))
    p.add_argument("--gold-m1-csv")
    p.add_argument("--gold-m5-csv")
    p.add_argument("--gold-m15-csv")
    p.add_argument("--gold-h1-csv")
    p.add_argument("--gold-h4-csv")
    p.add_argument("--gold-d1-csv")

    p.add_argument("--btc-pairs-json", default=DEFAULT_BTC_PAIRS_JSON)
    p.add_argument("--btc-preset-json", default=DEFAULT_BTC_PRESET_JSON)
    p.add_argument("--btc-out-prefix", default=DEFAULT_BTC_OUT_PREFIX.replace("btc_mochipoyo_live_dryrun", "btc_mochipoyo_live_dryrun_strict"))
    p.add_argument("--btc-m1-csv")
    p.add_argument("--btc-m5-csv")
    p.add_argument("--btc-m15-csv")
    p.add_argument("--btc-h1-csv")
    p.add_argument("--btc-h4-csv")
    p.add_argument("--btc-d1-csv")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    requested = {s.strip().upper() for s in args.symbols.split(",") if s.strip()}
    jobs: list[tuple[SymbolConfig, list[str]]] = []

    if "GOLD" in requested:
        jobs.append((
            SymbolConfig(
                "GOLD", args.gold_pairs_json, args.gold_preset_json, args.gold_out_prefix,
                args.gold_m1_csv, args.gold_m5_csv, args.gold_m15_csv, args.gold_h1_csv, args.gold_h4_csv, args.gold_d1_csv,
            ),
            parse_allowed_slices(args.gold_allowed_slices, "GOLD"),
        ))
    if "BTC" in requested:
        jobs.append((
            SymbolConfig(
                "BTC", args.btc_pairs_json, args.btc_preset_json, args.btc_out_prefix,
                args.btc_m1_csv, args.btc_m5_csv, args.btc_m15_csv, args.btc_h1_csv, args.btc_h4_csv, args.btc_d1_csv,
            ),
            parse_allowed_slices(args.btc_allowed_slices, "BTC"),
        ))
    if not jobs:
        raise RuntimeError("No valid symbols requested. Use --symbols GOLD,BTC")

    results = []
    for cfg, allowed in jobs:
        print("=" * 80)
        print(f"RUN STRICT SYMBOL: {cfg.symbol}")
        print("allowed_slices:")
        for s in allowed:
            print(f"  - {s}")
        results.append(run_symbol_strict(cfg, args, allowed))

    summary_path = Path(args.ledger_csv).with_suffix(".summary.json")
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary = {"mode": "STRICT_DRY_RUN_NO_DISCORD_NO_AI", "results": results, "ledger_csv": args.ledger_csv}
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print("=" * 80)
    print("run_mochipoyo_live_dryrun_strict")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"summary_json: {summary_path}")
    print("done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
