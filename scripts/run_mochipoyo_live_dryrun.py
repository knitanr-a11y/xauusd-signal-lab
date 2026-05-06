#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dry-run live scanner for Mochipoyo GOLD/BTC fixed-preset candidates.

This script intentionally does not send Discord messages and does not call AI.
It produces notification payload rows and appends them to a ledger CSV.

Flow:
1. Run scan_mochipoyo_multi_tf_candidates.py for GOLD and/or BTC.
2. Run filter_mochipoyo_candidate_events.py.
3. Apply fixed preset filters.
4. Keep recent candidate events only.
5. Add quality/caution labels.
6. Append payload rows to a ledger CSV.

This is a live dry-run bridge, not an outcome backtest.
"""
from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd


DEFAULT_GOLD_PAIRS_JSON = "config/mochipoyo/gold_mochipoyo_full_pairs.json"
DEFAULT_BTC_PAIRS_JSON = "config/mochipoyo/btc_mochipoyo_full_pairs.json"
DEFAULT_GOLD_PRESET_JSON = "config/mochipoyo/gold_mochipoyo_rr12_refined_fixed_filters.json"
DEFAULT_BTC_PRESET_JSON = "config/mochipoyo/btc_mochipoyo_h4_m15_a_net_refined_fixed_filters.json"

DEFAULT_GOLD_OUT_PREFIX = "data/results/mochipoyo/live_dryrun/gold_mochipoyo_live_dryrun"
DEFAULT_BTC_OUT_PREFIX = "data/results/mochipoyo/live_dryrun/btc_mochipoyo_live_dryrun"


@dataclass(frozen=True)
class SymbolConfig:
    symbol: str
    pairs_json: str
    preset_json: str
    out_prefix: str
    m1_csv: str | None = None
    m5_csv: str | None = None
    m15_csv: str | None = None
    h1_csv: str | None = None
    h4_csv: str | None = None
    d1_csv: str | None = None


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def sniff_sep(path: Path) -> str:
    sample = path.read_text(encoding="utf-8-sig", errors="replace")[:4096]
    try:
        return csv.Sniffer().sniff(sample, delimiters=";,\t,").delimiter
    except csv.Error:
        return ";" if sample.count(";") >= sample.count(",") else ","


def read_ohlc_csv(path: str | None) -> pd.DataFrame:
    if not path:
        return pd.DataFrame()
    p = Path(path)
    if not p.exists():
        return pd.DataFrame()
    df = pd.read_csv(p, sep=sniff_sep(p), encoding="utf-8-sig")
    df.columns = [str(c).strip().lower() for c in df.columns]
    if "time" not in df.columns:
        return pd.DataFrame()
    df["time"] = pd.to_datetime(df["time"], errors="coerce")
    df = df.dropna(subset=["time"]).sort_values("time").reset_index(drop=True)
    return df


def run_cmd(cmd: list[str], *, dry_run_commands: bool) -> None:
    print("CMD:", " ".join(cmd))
    if dry_run_commands:
        return
    proc = subprocess.run(
        cmd,
        cwd=str(repo_root()),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
        errors="replace",
    )
    if proc.stdout:
        print(proc.stdout)
    if proc.stderr:
        print(proc.stderr, file=sys.stderr)
    if proc.returncode != 0:
        raise RuntimeError(f"Command failed returncode={proc.returncode}: {' '.join(cmd)}")


def build_scan_cmd(py: str, cfg: SymbolConfig, candidates_csv: Path) -> list[str]:
    cmd = [py, "scripts/scan_mochipoyo_multi_tf_candidates.py", "--symbol", cfg.symbol]
    for opt, value in [
        ("--m1-csv", cfg.m1_csv),
        ("--m5-csv", cfg.m5_csv),
        ("--m15-csv", cfg.m15_csv),
        ("--h1-csv", cfg.h1_csv),
        ("--h4-csv", cfg.h4_csv),
        ("--d1-csv", cfg.d1_csv),
    ]:
        if value:
            cmd.extend([opt, value])
    cmd.extend(["--pairs-json", cfg.pairs_json, "--output-csv", str(candidates_csv), "--require-divergence"])
    return cmd


def load_preset(path: str) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def contains_token(series: pd.Series, token: str) -> pd.Series:
    return series.fillna("").astype(str).str.contains(token, regex=False)


def apply_name_filter(df: pd.DataFrame, name: str) -> pd.DataFrame:
    mask = pd.Series(True, index=df.index)
    parts = str(name).split("|")
    if name == "ALL":
        return df.copy()
    if name.startswith("token_all="):
        token_part = parts[0].replace("token_all=", "", 1)
        for tok in token_part.split("+"):
            if tok:
                mask &= contains_token(df["reason_text"], tok)
        parts = parts[1:]
    for part in parts:
        if not part:
            continue
        if part.startswith("slice="):
            # Supported shape in older GOLD filters: slice=PAIR|RANK|DIRECTION|...
            # If present as its own first part after split, reconstruct is impossible here.
            # The current fixed-filter sets should not depend on this abbreviated parser.
            return df.iloc[0:0].copy()
        if part.startswith("direction="):
            mask &= df["direction"].astype(str) == part.replace("direction=", "", 1)
        elif part.startswith("token="):
            mask &= contains_token(df["reason_text"], part.replace("token=", "", 1))
        elif part.startswith("total_score>="):
            mask &= pd.to_numeric(df["total_score"], errors="coerce") >= float(part.replace("total_score>=", "", 1))
        elif part.startswith("context_score>="):
            mask &= pd.to_numeric(df["context_score"], errors="coerce") >= float(part.replace("context_score>=", "", 1))
        elif part.startswith("base_score>="):
            mask &= pd.to_numeric(df["base_score"], errors="coerce") >= float(part.replace("base_score>=", "", 1))
        elif part.startswith("spread_to_sl<="):
            if "spread_to_sl_ratio" not in df.columns:
                return df.iloc[0:0].copy()
            mask &= pd.to_numeric(df["spread_to_sl_ratio"], errors="coerce") <= float(part.replace("spread_to_sl<=", "", 1))
        elif part.startswith("effective_rr>="):
            if "effective_rr_after_spread" not in df.columns:
                return df.iloc[0:0].copy()
            mask &= pd.to_numeric(df["effective_rr_after_spread"], errors="coerce") >= float(part.replace("effective_rr>=", "", 1))
        else:
            return df.iloc[0:0].copy()
    return df[mask].copy()


def apply_fixed_preset(events: pd.DataFrame, preset: dict[str, Any]) -> pd.DataFrame:
    parts = []
    for item in preset.get("fixed_filters", []):
        name = str(item.get("name", ""))
        if not name:
            continue
        g = apply_name_filter(events, name)
        if g.empty:
            continue
        g = g.copy()
        g["source_filter_rank"] = int(item.get("rank", 9999))
        g["source_filter_name"] = name
        parts.append(g)
    if not parts:
        return events.iloc[0:0].copy()
    union = pd.concat(parts, ignore_index=True)
    cols = [c for c in ["entry_time", "pair_name", "candidate_rank", "direction", "entry_price", "base_time", "signal_time"] if c in union.columns]
    if cols:
        union = union.drop_duplicates(subset=cols, keep="first")
    exclude = set(preset.get("portfolio", {}).get("exclude_slices", []))
    if "selected_slice" not in union.columns and {"pair_name", "candidate_rank", "direction"}.issubset(union.columns):
        union["selected_slice"] = union.apply(lambda r: f"{r['pair_name']}|{r['candidate_rank']}|{r['direction']}", axis=1)
    if exclude and "selected_slice" in union.columns:
        union = union[~union["selected_slice"].isin(exclude)].copy()
    return union.sort_values("entry_time", kind="mergesort").reset_index(drop=True)


def add_labels(df: pd.DataFrame, symbol: str) -> pd.DataFrame:
    out = df.copy()
    reason = out.get("reason_text", pd.Series("", index=out.index)).fillna("").astype(str)
    direction = out.get("direction", pd.Series("", index=out.index)).fillna("").astype(str)
    quality = []
    caution = []
    for idx in out.index:
        text = reason.loc[idx]
        d = direction.loc[idx]
        labels = []
        cautions = []
        buy2 = "granville_buy_2_like" in text
        sell2 = "granville_sell_2_like" in text
        g3 = ("granville_buy_3" in text) or ("granville_sell_3" in text)
        if symbol == "BTC":
            if d == "BUY" and not buy2:
                labels.append("QUALITY_HIGH_NO_BUY_2_LIKE")
            elif g3:
                labels.append("QUALITY_HIGH_GRANVILLE_3")
            else:
                labels.append("QUALITY_STANDARD")
        else:
            if not buy2 and not sell2:
                labels.append("QUALITY_HIGH_NO_GRANVILLE_2_LIKE")
            elif g3:
                labels.append("QUALITY_HIGH_GRANVILLE_3")
            else:
                labels.append("QUALITY_STANDARD")
        if buy2 or sell2:
            cautions.append("GRANVILLE_2_LIKE")
        if buy2:
            cautions.append("BUY_2_EARLY_ENTRY")
        if sell2:
            cautions.append("SELL_2_EARLY_ENTRY")
        if symbol == "BTC" and "spread_to_sl_ratio" in out.columns:
            try:
                spr = float(out.at[idx, "spread_to_sl_ratio"])
                if spr > 0.07:
                    cautions.append("SPREAD_TO_SL_HIGH")
            except Exception:
                pass
        quality.append(";".join(labels))
        caution.append(";".join(cautions) if cautions else "NONE")
    out["quality_labels"] = quality
    out["caution_labels"] = caution
    return out


def recent_filter(df: pd.DataFrame, scan_recent_bars: int, base_tf_col: str = "base_tf") -> pd.DataFrame:
    if df.empty or "entry_time" not in df.columns:
        return df.copy()
    out = df.copy()
    out["entry_time"] = pd.to_datetime(out["entry_time"], errors="coerce")
    out = out.dropna(subset=["entry_time"]).sort_values("entry_time").reset_index(drop=True)
    if scan_recent_bars <= 0:
        return out
    # Approximation for dry-run: keep last N event rows after fixed-preset filtering.
    # Exact bar-based recent filtering can be tightened after payload shape is confirmed.
    return out.tail(scan_recent_bars).copy()


def to_payload_rows(df: pd.DataFrame, cfg: SymbolConfig, preset: dict[str, Any]) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    out = df.copy()
    out["payload_id"] = [str(uuid.uuid4()) for _ in range(len(out))]
    out["candidate_name"] = preset.get("candidate_name", cfg.symbol + "_MOCHIPOYO")
    out["symbol"] = cfg.symbol
    out["notification_mode"] = "DRY_RUN_NO_DISCORD_NO_AI"
    out["created_at_utc"] = pd.Timestamp.utcnow().strftime("%Y-%m-%d %H:%M:%S%z")
    out = add_labels(out, cfg.symbol)
    preferred = [
        "created_at_utc", "payload_id", "notification_mode", "symbol", "candidate_name",
        "entry_time", "pair_name", "selected_slice", "candidate_rank", "direction", "entry_price",
        "quality_labels", "caution_labels", "context_granville_type", "context_ema_order", "base_ema_order",
        "total_score", "context_score", "base_score", "reason_text", "source_filter_rank", "source_filter_name",
        "context_close_time", "base_close_time", "signal_close_time",
        "mode_spread_points", "mode_spread_price", "spread_to_sl_ratio", "effective_rr_after_spread",
    ]
    cols = [c for c in preferred if c in out.columns] + [c for c in out.columns if c not in preferred]
    return out[cols]


def append_ledger(rows: pd.DataFrame, ledger_csv: Path) -> None:
    ledger_csv.parent.mkdir(parents=True, exist_ok=True)
    if rows.empty:
        return
    if ledger_csv.exists():
        old = pd.read_csv(ledger_csv, encoding="utf-8-sig")
        all_cols = list(dict.fromkeys(list(old.columns) + list(rows.columns)))
        old = old.reindex(columns=all_cols)
        rows = rows.reindex(columns=all_cols)
        combined = pd.concat([old, rows], ignore_index=True)
        combined.to_csv(ledger_csv, index=False, encoding="utf-8-sig")
    else:
        rows.to_csv(ledger_csv, index=False, encoding="utf-8-sig")


def run_symbol(cfg: SymbolConfig, args: argparse.Namespace) -> dict[str, Any]:
    root = repo_root()
    out_prefix = Path(cfg.out_prefix)
    out_prefix.parent.mkdir(parents=True, exist_ok=True)
    candidates_csv = out_prefix.with_name(out_prefix.name + "_candidates.csv")
    events_csv = out_prefix.with_name(out_prefix.name + "_events.csv")
    payload_csv = out_prefix.with_name(out_prefix.name + "_payloads.csv")

    run_cmd(build_scan_cmd(args.python, cfg, candidates_csv), dry_run_commands=args.print_commands_only)
    run_cmd([args.python, "scripts/filter_mochipoyo_candidate_events.py", "--input-csv", str(candidates_csv), "--output-csv", str(events_csv)], dry_run_commands=args.print_commands_only)

    if args.print_commands_only:
        return {"symbol": cfg.symbol, "printed_commands_only": True}

    events = pd.read_csv(events_csv, encoding="utf-8-sig")
    if "entry_time" in events.columns:
        events["entry_time"] = pd.to_datetime(events["entry_time"], errors="coerce")
    preset = load_preset(cfg.preset_json)
    fixed = apply_fixed_preset(events, preset)
    recent = recent_filter(fixed, args.scan_recent_events)
    payloads = to_payload_rows(recent, cfg, preset)
    payloads.to_csv(payload_csv, index=False, encoding="utf-8-sig")
    append_ledger(payloads, Path(args.ledger_csv))

    return {
        "symbol": cfg.symbol,
        "candidates_csv": str(candidates_csv),
        "events_csv": str(events_csv),
        "payload_csv": str(payload_csv),
        "events_rows": int(len(events)),
        "fixed_match_rows": int(len(fixed)),
        "payload_rows": int(len(payloads)),
    }


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run Mochipoyo live dry-run scanner.")
    p.add_argument("--symbols", default="GOLD,BTC", help="Comma-separated symbols: GOLD,BTC")
    p.add_argument("--ledger-csv", default="data/results/mochipoyo/live_dryrun/mochipoyo_live_dryrun_ledger.csv")
    p.add_argument("--scan-recent-events", type=int, default=20, help="Keep last N fixed-preset event rows for dry-run payload output.")
    p.add_argument("--python", default=sys.executable)
    p.add_argument("--print-commands-only", action="store_true")

    p.add_argument("--gold-pairs-json", default=DEFAULT_GOLD_PAIRS_JSON)
    p.add_argument("--gold-preset-json", default=DEFAULT_GOLD_PRESET_JSON)
    p.add_argument("--gold-out-prefix", default=DEFAULT_GOLD_OUT_PREFIX)
    p.add_argument("--gold-m1-csv")
    p.add_argument("--gold-m5-csv")
    p.add_argument("--gold-m15-csv")
    p.add_argument("--gold-h1-csv")
    p.add_argument("--gold-h4-csv")
    p.add_argument("--gold-d1-csv")

    p.add_argument("--btc-pairs-json", default=DEFAULT_BTC_PAIRS_JSON)
    p.add_argument("--btc-preset-json", default=DEFAULT_BTC_PRESET_JSON)
    p.add_argument("--btc-out-prefix", default=DEFAULT_BTC_OUT_PREFIX)
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
    configs = []
    if "GOLD" in requested:
        configs.append(SymbolConfig("GOLD", args.gold_pairs_json, args.gold_preset_json, args.gold_out_prefix, args.gold_m1_csv, args.gold_m5_csv, args.gold_m15_csv, args.gold_h1_csv, args.gold_h4_csv, args.gold_d1_csv))
    if "BTC" in requested:
        configs.append(SymbolConfig("BTC", args.btc_pairs_json, args.btc_preset_json, args.btc_out_prefix, args.btc_m1_csv, args.btc_m5_csv, args.btc_m15_csv, args.btc_h1_csv, args.btc_h4_csv, args.btc_d1_csv))
    if not configs:
        raise RuntimeError("No valid symbols requested. Use --symbols GOLD,BTC")

    results = []
    for cfg in configs:
        print("=" * 80)
        print(f"RUN SYMBOL: {cfg.symbol}")
        results.append(run_symbol(cfg, args))

    summary_path = Path(args.ledger_csv).with_suffix(".summary.json")
    summary = {"mode": "DRY_RUN_NO_DISCORD_NO_AI", "results": results, "ledger_csv": args.ledger_csv}
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print("=" * 80)
    print("run_mochipoyo_live_dryrun")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"summary_json: {summary_path}")
    print("done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
