#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Format Mochipoyo dry-run payload rows into simple Discord message text.

Default output is intentionally trader-facing and compact:
- first line is SYMBOL + BUY/SELL
- no internal Candidate/Quality/Caution jargon
- Entry / SL / TP / RR are prominent
- warnings are written in plain Japanese

This script does not send Discord messages.
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


def entry_time_short(row: pd.Series) -> str:
    raw = val(row, "entry_time")
    try:
        t = pd.to_datetime(raw)
        return t.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return raw


def timeframe_label(row: pd.Series) -> str:
    pair = val(row, "pair_name")
    parts = pair.split("_")
    # Examples: GOLD_H4_M5_SCALP / BTC_H4_M15_DAYTRADE
    if len(parts) >= 3:
        return f"{parts[1]} → {parts[2]}"
    return pair


def granville_jp(row: pd.Series) -> str:
    g = val(row, "context_granville_type")
    d = val(row, "direction").upper()
    if g == "BUY_2":
        return "グランビル2 / 押し目買い"
    if g == "BUY_3":
        return "グランビル3 / 押し目買い"
    if g == "SELL_2":
        return "グランビル2 / 戻り売り"
    if g == "SELL_3":
        return "グランビル3 / 戻り売り"
    if d == "BUY":
        return f"{g} / 買い候補"
    if d == "SELL":
        return f"{g} / 売り候補"
    return g


def direction_emoji(direction: str) -> str:
    d = direction.upper()
    if d == "BUY":
        return "📈"
    if d == "SELL":
        return "📉"
    return "📌"


def symbol_emoji(symbol: str) -> str:
    s = symbol.upper()
    if s == "BTC":
        return "🟧"
    if s == "GOLD":
        return "🟨"
    return "⬜"


def reason_items(row: pd.Series, max_items: int = 5) -> list[str]:
    text = val(row, "reason_text", "")
    tokens = [x.strip() for x in text.split(";") if x.strip()]
    mapping = {
        "context_ema_bull": "上位足EMAは上方向",
        "context_ema_bear": "上位足EMAは下方向",
        "context_ema_slope_up": "上位足EMAの傾きが上向き",
        "context_ema_slope_down": "上位足EMAの傾きが下向き",
        "base_ema_bull": "下位足EMAも上方向",
        "base_ema_bear": "下位足EMAも下方向",
        "granville_buy_2_like": "グランビル2系の押し目買い",
        "granville_sell_2_like": "グランビル2系の戻り売り",
        "granville_buy_3": "グランビル3の押し目買い",
        "granville_sell_3": "グランビル3の戻り売り",
        "context_rci_turn_up": "上位足RCIが上向き反転",
        "context_rci_turn_down": "上位足RCIが下向き反転",
        "base_rci_turn_up": "下位足RCIが上向き反転",
        "base_rci_turn_down": "下位足RCIが下向き反転",
        "base_hidden_bullish": "下位足ヒドゥン強気ダイバージェンス",
        "base_hidden_bearish": "下位足ヒドゥン弱気ダイバージェンス",
        "context_hidden_bullish": "上位足ヒドゥン強気ダイバージェンス",
        "context_hidden_bearish": "上位足ヒドゥン弱気ダイバージェンス",
        "base_regular_bullish": "下位足通常強気ダイバージェンス",
        "base_regular_bearish": "下位足通常弱気ダイバージェンス",
        "context_regular_bullish": "上位足通常強気ダイバージェンス",
        "context_regular_bearish": "上位足通常弱気ダイバージェンス",
        "base_pullback_to_ema_band": "下位足がEMA帯まで押し戻り",
        "context_retrace_to_ema_band": "上位足がEMA帯まで戻り",
    }
    preferred_order = [
        "context_ema_bull", "context_ema_bear", "context_ema_slope_up", "context_ema_slope_down",
        "granville_buy_3", "granville_sell_3", "granville_buy_2_like", "granville_sell_2_like",
        "context_rci_turn_up", "context_rci_turn_down", "base_rci_turn_up", "base_rci_turn_down",
        "context_hidden_bullish", "context_hidden_bearish", "base_hidden_bullish", "base_hidden_bearish",
        "context_regular_bullish", "context_regular_bearish", "base_regular_bullish", "base_regular_bearish",
        "base_pullback_to_ema_band", "context_retrace_to_ema_band", "base_ema_bull", "base_ema_bear",
    ]
    selected = []
    for key in preferred_order:
        if key in tokens and mapping[key] not in selected:
            selected.append(mapping[key])
        if len(selected) >= max_items:
            return selected
    for tok in tokens:
        label = mapping.get(tok, tok)
        if label not in selected:
            selected.append(label)
        if len(selected) >= max_items:
            break
    return selected or ["根拠情報なし"]


def warning_items(row: pd.Series) -> list[str]:
    caution = val(row, "caution_labels", "NONE")
    symbol = val(row, "symbol").upper()
    out = []
    if "BUY_2_EARLY_ENTRY" in caution:
        if symbol == "BTC":
            out.append("グランビル2の買いなので早入り注意。M15が本当に反転しているか確認。")
        else:
            out.append("グランビル2の買いなので早入り注意。下位足の反転確認を優先。")
    elif "SELL_2_EARLY_ENTRY" in caution:
        if symbol == "BTC":
            out.append("グランビル2の売りなので早入り注意。上ヒゲ・RCI反転・M15崩れを確認。")
        else:
            out.append("グランビル2の売りなので早入り注意。下位足の崩れ確認を優先。")
    elif "GRANVILLE_2_LIKE" in caution:
        out.append("グランビル2系なので、反転が早すぎないか確認。")
    if "SPREAD_TO_SL_HIGH" in caution:
        out.append("BTCのSpread/SLが高め。エントリー価格とSL幅に注意。")
    if not out:
        out.append("特になし")
    return out


def compact_message(row: pd.Series) -> str:
    symbol = val(row, "symbol").upper()
    direction = val(row, "direction").upper()
    price_digits = 2 if symbol == "BTC" else 3
    lines = [
        f"{symbol_emoji(symbol)} **{symbol} {direction}** {direction_emoji(direction)}",
        "━━━━━━━━━━━━━━",
        f"時間: `{entry_time_short(row)}`",
        f"足: `{timeframe_label(row)}`",
        f"形: `{granville_jp(row)}`",
        "",
        f"Entry: `{fnum(row, 'entry_price', price_digits)}`",
        f"SL:    `{fnum(row, 'sl_price', price_digits)}`",
        f"TP:    `{fnum(row, 'tp_price', price_digits)}`",
        f"RR:    `{fnum(row, 'rr', 2)}`",
    ]
    if symbol == "BTC":
        lines += [
            "",
            f"スプレッド: `{fnum(row, 'mode_spread_price', 2)}`",
            f"Spread/SL: `{fnum(row, 'spread_to_sl_ratio', 3)}`",
            f"実質RR: `{fnum(row, 'effective_rr_after_spread', 3)}`",
        ]
    lines += [
        "",
        "根拠:",
    ]
    for item in reason_items(row):
        lines.append(f"・{item}")
    lines += [
        "",
        "注意:",
    ]
    for item in warning_items(row):
        lines.append(f"・{item}")
    return "\n".join(lines)


def detailed_message(row: pd.Series) -> str:
    # Internal/debug view. Kept available with --style detailed.
    symbol = val(row, "symbol").upper()
    direction = val(row, "direction").upper()
    price_digits = 2 if symbol == "BTC" else 3
    lines = [
        f"{symbol_emoji(symbol)} **{symbol} {direction} / DETAIL**",
        "━━━━━━━━━━━━━━",
        f"Candidate: `{val(row, 'candidate_name')}`",
        f"Payload: `{val(row, 'payload_id')}`",
        f"Pair: `{val(row, 'pair_name')}`  Slice: `{val(row, 'selected_slice')}`",
        f"Rank: `{val(row, 'candidate_rank')}`",
        f"Entry time: `{entry_time_short(row)}`",
        f"Entry: `{fnum(row, 'entry_price', price_digits)}`  SL: `{fnum(row, 'sl_price', price_digits)}`  TP: `{fnum(row, 'tp_price', price_digits)}`  RR: `{fnum(row, 'rr', 2)}`",
        f"Granville: `{val(row, 'context_granville_type')}`",
        f"EMA: context=`{val(row, 'context_ema_order')}` / base=`{val(row, 'base_ema_order')}`",
        f"Scores: `{fnum(row, 'total_score', 1)}` / `{fnum(row, 'context_score', 1)}` / `{fnum(row, 'base_score', 1)}`",
        f"Reason: {val(row, 'reason_text')}",
    ]
    if symbol == "BTC":
        lines += [
            f"Spread: points=`{fnum(row, 'mode_spread_points', 0)}` price=`{fnum(row, 'mode_spread_price', 2)}`",
            f"Spread/SL: `{fnum(row, 'spread_to_sl_ratio', 4)}` Effective RR: `{fnum(row, 'effective_rr_after_spread', 3)}`",
        ]
    return "\n".join(lines)


def format_row(row: pd.Series, style: str) -> str:
    if style == "detailed":
        return detailed_message(row)
    return compact_message(row)


def main() -> int:
    p = argparse.ArgumentParser(description="Format Mochipoyo dry-run payload rows into Discord message text.")
    p.add_argument("--input-csv", required=True, help="Payload CSV or ledger CSV")
    p.add_argument("--output-txt", required=True)
    p.add_argument("--output-json", default=None)
    p.add_argument("--max-rows", type=int, default=20)
    p.add_argument("--symbol", default=None, help="Optional GOLD or BTC filter")
    p.add_argument("--style", choices=["compact", "detailed"], default="compact")
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
            "style": args.style,
            "message": format_row(row, args.style),
        })

    out_txt = Path(args.output_txt)
    out_txt.parent.mkdir(parents=True, exist_ok=True)
    text = ("\n\n" + "=" * 40 + "\n\n").join(m["message"] for m in messages)
    out_txt.write_text(text.strip() + "\n", encoding="utf-8")

    out_json = Path(args.output_json) if args.output_json else out_txt.with_suffix(".json")
    out_json.write_text(json.dumps({"source": str(src), "rows": int(len(df)), "style": args.style, "messages": messages}, ensure_ascii=False, indent=2), encoding="utf-8")

    print("format_mochipoyo_discord_messages")
    print(f"source: {src}")
    print(f"rows: {len(df)}")
    print(f"style: {args.style}")
    print(f"output_txt: {out_txt}")
    print(f"output_json: {out_json}")
    print("preview:")
    print(messages[-1]["message"] if messages else "empty")
    print("done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
