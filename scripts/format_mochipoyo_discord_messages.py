#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Format Mochipoyo dry-run payload rows into Discord message text.

This script does not send Discord messages.
It reads a payload/ledger CSV and writes reviewable message text.

Use after run_mochipoyo_live_dryrun_strict.py.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


def val(row: pd.Series, name: str, default: str = "-") -> str:
    if name not in row.index:
        return default
    x = row.get(name)
    if pd.isna(x):
        return default
    s = str(x)
    return s if s else default


def fnum(row: pd.Series, name: str, ndigits: int = 2, default: str = "-") -> str:
    if name not in row.index:
        return default
    try:
        x = float(row.get(name))
    except Exception:
        return default
    if pd.isna(x):
        return default
    return f"{x:.{ndigits}f}"


def short_reason(text: str, limit: int = 260) -> str:
    text = str(text or "-").replace("\n", " ").strip()
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def format_gold(row: pd.Series) -> str:
    caution = val(row, "caution_labels")
    quality = val(row, "quality_labels")
    lines = [
        "🟨 **GOLD MOCHIPOYO SIGNAL / DRY-RUN**",
        f"Candidate: `{val(row, 'candidate_name')}`",
        f"Quality: `{quality}`",
        f"Caution: `{caution}`",
        "",
        f"Pair: `{val(row, 'pair_name')}`  Slice: `{val(row, 'selected_slice')}`",
        f"Direction: **{val(row, 'direction')}**  Rank: `{val(row, 'candidate_rank')}`",
        f"Entry time: `{val(row, 'entry_time')}`",
        f"Entry candidate: `{fnum(row, 'entry_price', 3)}`",
    ]
    if "sl_price" in row.index or "tp_price" in row.index:
        lines.append(f"SL/TP: `{fnum(row, 'sl_price', 3)}` / `{fnum(row, 'tp_price', 3)}`")
    lines += [
        "",
        f"Granville: `{val(row, 'context_granville_type')}`",
        f"EMA: context=`{val(row, 'context_ema_order')}` / base=`{val(row, 'base_ema_order')}`",
        f"Scores: total/context/base = `{fnum(row, 'total_score', 1)}` / `{fnum(row, 'context_score', 1)}` / `{fnum(row, 'base_score', 1)}`",
        f"Source filter: rank=`{val(row, 'source_filter_rank')}` name=`{val(row, 'source_filter_name')}`",
        "",
        f"Reason: {short_reason(val(row, 'reason_text'))}",
        f"Payload: `{val(row, 'payload_id')}`",
    ]
    if "GRANVILLE_2_LIKE" in caution:
        lines += [
            "",
            "⚠️ Granville 2-like: setup may be early. Confirm lower-timeframe reversal/continuation before entry.",
        ]
    return "\n".join(lines)


def format_btc(row: pd.Series) -> str:
    caution = val(row, "caution_labels")
    quality = val(row, "quality_labels")
    lines = [
        "🟧 **BTC MOCHIPOYO SIGNAL / DRY-RUN**",
        f"Candidate: `{val(row, 'candidate_name')}`",
        f"Quality: `{quality}`",
        f"Caution: `{caution}`",
        "",
        f"Pair: `{val(row, 'pair_name')}`  Slice: `{val(row, 'selected_slice')}`",
        f"Direction: **{val(row, 'direction')}**  Rank: `{val(row, 'candidate_rank')}`",
        f"Entry time: `{val(row, 'entry_time')}`",
        f"Entry candidate: `{fnum(row, 'entry_price', 2)}`",
        f"SL/TP: `{fnum(row, 'sl_price', 2)}` / `{fnum(row, 'tp_price', 2)}`  RR=`{fnum(row, 'rr', 2)}`",
        "",
        f"Spread: points=`{fnum(row, 'mode_spread_points', 0)}` price=`{fnum(row, 'mode_spread_price', 2)}`",
        f"Spread/SL: `{fnum(row, 'spread_to_sl_ratio', 4)}`  Effective RR: `{fnum(row, 'effective_rr_after_spread', 3)}`",
        f"Risk status: `{val(row, 'btc_live_risk_status')}`  touch_tf=`{val(row, 'touch_tf')}` sl_method=`{val(row, 'sl_method')}`",
        "",
        f"Granville: `{val(row, 'context_granville_type')}`",
        f"EMA: context=`{val(row, 'context_ema_order')}` / base=`{val(row, 'base_ema_order')}`",
        f"Scores: total/context/base = `{fnum(row, 'total_score', 1)}` / `{fnum(row, 'context_score', 1)}` / `{fnum(row, 'base_score', 1)}`",
        f"Source filter: rank=`{val(row, 'source_filter_rank')}` name=`{val(row, 'source_filter_name')}`",
        "",
        f"Reason: {short_reason(val(row, 'reason_text'))}",
        f"Payload: `{val(row, 'payload_id')}`",
    ]
    if "BUY_2_EARLY_ENTRY" in caution:
        lines += [
            "",
            "⚠️ BTC BUY_2 caution: pushback/pullback buy may be early. Check whether M15 has actually turned and whether spread-to-SL is acceptable.",
        ]
    elif "SELL_2_EARLY_ENTRY" in caution:
        lines += [
            "",
            "⚠️ BTC SELL_2 caution: return-sell may be early. Check upper wick/rejection, RCI turn, and M15 breakdown before entry.",
        ]
    elif "GRANVILLE_2_LIKE" in caution:
        lines += [
            "",
            "⚠️ Granville 2-like: setup may be early. Confirm lower-timeframe reversal/continuation before entry.",
        ]
    if "SPREAD_TO_SL_HIGH" in caution:
        lines += [
            "",
            "⚠️ Spread/SL is high for BTC. Be strict about entry price and stop distance.",
        ]
    return "\n".join(lines)


def format_row(row: pd.Series) -> str:
    symbol = val(row, "symbol").upper()
    if symbol == "BTC":
        return format_btc(row)
    return format_gold(row)


def main() -> int:
    p = argparse.ArgumentParser(description="Format Mochipoyo dry-run payload rows into Discord message text.")
    p.add_argument("--input-csv", required=True, help="Payload CSV or ledger CSV")
    p.add_argument("--output-txt", required=True)
    p.add_argument("--output-json", default=None)
    p.add_argument("--max-rows", type=int, default=20)
    p.add_argument("--symbol", default=None, help="Optional GOLD or BTC filter")
    args = p.parse_args()

    src = Path(args.input_csv)
    df = pd.read_csv(src, encoding="utf-8-sig")
    if args.symbol and "symbol" in df.columns:
        df = df[df["symbol"].astype(str).str.upper() == args.symbol.upper()].copy()
    if "entry_time" in df.columns:
        df["entry_time"] = pd.to_datetime(df["entry_time"], errors="coerce")
        df = df.sort_values("entry_time")
    if args.max_rows > 0:
        df = df.tail(args.max_rows)

    messages = []
    for i, (_, row) in enumerate(df.iterrows(), start=1):
        messages.append({
            "index": i,
            "payload_id": val(row, "payload_id"),
            "payload_key": val(row, "payload_key"),
            "symbol": val(row, "symbol"),
            "message": format_row(row),
        })

    out_txt = Path(args.output_txt)
    out_txt.parent.mkdir(parents=True, exist_ok=True)
    text = "\n\n" + ("\n\n" + "=" * 80 + "\n\n").join(m["message"] for m in messages)
    out_txt.write_text(text.strip() + "\n", encoding="utf-8")

    out_json = Path(args.output_json) if args.output_json else out_txt.with_suffix(".json")
    out_json.write_text(json.dumps({"source": str(src), "rows": int(len(df)), "messages": messages}, ensure_ascii=False, indent=2), encoding="utf-8")

    print("format_mochipoyo_discord_messages")
    print(f"source: {src}")
    print(f"rows: {len(df)}")
    print(f"output_txt: {out_txt}")
    print(f"output_json: {out_json}")
    print("preview:")
    print(messages[-1]["message"] if messages else "empty")
    print("done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
