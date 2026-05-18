#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""Build live-compatible trade_outcome_ledger.csv from backtest trades.csv.

This script is deterministic and does not call AI.

Purpose:
- Convert historical/backtest trades into the same ledger shape used by the
  live trade AI review pipeline.
- Keep backtest review outputs separate from live review outputs.
- Preserve strategy/symbol/direction/outcome fields so existing snapshot,
  payload, AI review and tag summary scripts can be reused as-is.

Important:
- Backtest rows are marked MATCHED / EXECUTED because the trade result is
  already known from the backtest.
- AI review remains HYPOTHESIS_TAGGING_ONLY in downstream scripts.
- This script does not change strategy rules and does not connect to MT5.

Typical BTC first run:
python scripts/build_trade_outcome_ledger_from_backtest_trades.py ^
  --backtest-trades-csv data/results/btc_d1_low_break_sell_trades.csv ^
  --output-csv data/runtime_logs/trade_ai_review_backtest_btc/trade_outcome_ledger.csv ^
  --output-json data/runtime_logs/trade_ai_review_backtest_btc/trade_outcome_ledger_summary.json ^
  --symbol BTC ^
  --strategy-id D1_LOW_BREAK_SELL
"""
from __future__ import annotations

import argparse
import math
import re
from pathlib import Path
from typing import Any

import pandas as pd

from build_trade_outcome_ledger_from_order_ledger import OUTCOME_COLUMNS
from trade_ai_review_utils import (
    OUTCOME_LEDGER_SCHEMA_VERSION,
    canonical_trade_id,
    classify_outcome,
    clean_float,
    clean_int,
    clean_str,
    infer_close_reason,
    normalize_direction,
    parse_time_any,
    profit_r_from_prices,
    read_csv,
    row_get,
    side_price_distance,
    stop_distance,
    take_distance,
    time_to_text,
    utc_now_text,
    write_csv,
    write_json,
)

NET_R_COLUMNS = [
    "net_profit_r",
    "net_r",
    "profit_r_net",
    "r_net",
    "net_R",
    "R_net",
    "net_result_r",
    "result_r_net",
    "profit_r_after_spread",
    "net_profit_r_after_spread",
    "profit_r_spread_adjusted",
    "spread_adjusted_profit_r",
]

GROSS_R_COLUMNS = [
    "profit_r",
    "r",
    "R",
    "result_r",
    "realized_r",
    "rr_result",
    "trade_r",
    "pnl_r",
    "gross_profit_r",
    "gross_r",
]

PROFIT_COLUMNS = [
    "net_profit",
    "profit",
    "pnl",
    "pl",
    "pnl_amount",
    "profit_amount",
]

ENTRY_TIME_COLUMNS = [
    "entry_time",
    "signal_close_time",
    "open_time",
    "time",
    "timestamp",
    "datetime",
]

CLOSE_TIME_COLUMNS = [
    "close_time",
    "exit_time",
    "closed_at",
    "end_time",
    "settled_time",
]

ENTRY_PRICE_COLUMNS = [
    "entry_price",
    "entry",
    "open_price",
    "price",
    "fill_price",
    "entry_price_reference",
]

SL_PRICE_COLUMNS = [
    "sl_price",
    "stop_loss",
    "sl",
    "stop_price",
]

TP_PRICE_COLUMNS = [
    "tp_price",
    "take_profit",
    "tp",
    "target_price",
]

CLOSE_PRICE_COLUMNS = [
    "close_price",
    "exit_price",
    "settle_price",
    "final_price",
]

OUTCOME_COLUMNS_CANDIDATES = [
    "outcome",
    "result",
    "status",
    "exit_reason",
    "close_reason",
    "label",
]

STRATEGY_COLUMNS = [
    "strategy_id",
    "strategy_key",
    "strategy",
    "pair_name",
    "condition_id",
    "router_strategy_id",
    "router_strategy_slot",
    "model",
    "setup",
]

SYMBOL_COLUMNS = [
    "symbol",
    "broker_symbol",
    "instrument",
    "ticker",
    "pair",
]

DIRECTION_COLUMNS = [
    "direction",
    "side",
    "order_type",
    "signal_side",
    "trade_side",
]

ID_COLUMNS = [
    "trade_id",
    "order_key",
    "payload_key",
    "signal_key",
    "id",
    "uuid",
]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build live-compatible trade_outcome_ledger.csv from backtest trades.csv.")
    p.add_argument("--backtest-trades-csv", required=True, help="Backtest trades.csv to convert.")
    p.add_argument("--output-csv", required=True, help="Output live-compatible trade_outcome_ledger.csv.")
    p.add_argument("--output-json", default="", help="Optional summary JSON.")
    p.add_argument("--symbol", default="BTC", help="Grouping symbol filter/default, e.g. BTC or GOLD. Empty disables symbol filter.")
    p.add_argument("--broker-symbol", default="", help="Broker symbol to write when the source row has no broker_symbol.")
    p.add_argument("--strategy-id", default="D1_LOW_BREAK_SELL", help="Strategy filter/default. Empty disables strategy filter.")
    p.add_argument("--strategy-key", default="", help="Optional strategy_key override/default. Defaults to --strategy-id.")
    p.add_argument("--direction", default="", help="Optional direction filter/default: BUY or SELL.")
    p.add_argument("--prefer-net-r", action=argparse.BooleanOptionalAction, default=True, help="Prefer net/spread-adjusted R columns when present.")
    p.add_argument("--spread-cost-r-column", default="", help="Optional spread cost R column to subtract when only gross R exists.")
    p.add_argument("--max-losses", type=int, default=100, help="Max LOSS/SMALL_LOSS rows. 0 or negative = all.")
    p.add_argument("--max-wins", type=int, default=100, help="Max WIN/SMALL_WIN rows. 0 or negative = all.")
    p.add_argument("--max-breakevens", type=int, default=30, help="Max BREAKEVEN rows. 0 or negative = all.")
    p.add_argument("--include-unknown", action="store_true", help="Include UNKNOWN outcome rows.")
    p.add_argument("--max-unknown", type=int, default=30)
    p.add_argument("--sample-policy", choices=["newest", "oldest", "random"], default="newest")
    p.add_argument("--sample-seed", type=int, default=42)
    p.add_argument("--small-r", type=float, default=0.10)
    p.add_argument("--small-profit-abs", type=float, default=0.0)
    p.add_argument("--close-reason-tolerance", type=float, default=1e-6)
    return p.parse_args()


def normalize_grouping_symbol(value: Any, default: str = "") -> str:
    text = clean_str(value).upper()
    if not text:
        return clean_str(default).upper()
    for sep in ["#", ".", "_"]:
        if sep in text:
            text = text.split(sep)[0]
    if text.startswith("XAUUSD") or text.startswith("GOLD"):
        return "GOLD"
    if text.startswith("BTC"):
        return "BTC"
    return text


def safe_key_text(value: Any) -> str:
    text = clean_str(value)
    text = re.sub(r"\s+", "_", text)
    text = re.sub(r"[^A-Za-z0-9_.|:#@+-]+", "_", text)
    return text.strip("_")


def first_present(row: pd.Series, names: list[str], default: Any = "") -> Any:
    return row_get(row, names, default)


def first_text(row: pd.Series, names: list[str], default: str = "") -> str:
    return clean_str(first_present(row, names, default), default)


def first_float(row: pd.Series, names: list[str], default: float | None = None) -> float | None:
    return clean_float(first_present(row, names, default), default)


def first_int(row: pd.Series, names: list[str], default: int = 0) -> int:
    return clean_int(first_present(row, names, default), default)


def parse_outcome_text(value: Any) -> str:
    text = clean_str(value).upper()
    if not text:
        return ""
    normalized = text.replace("-", "_").replace(" ", "_")
    win_tokens = {
        "WIN",
        "WON",
        "TP",
        "TAKE_PROFIT",
        "TAKEPROFIT",
        "PROFIT",
        "TARGET",
        "HIT_TP",
        "TP_HIT",
    }
    loss_tokens = {
        "LOSS",
        "LOST",
        "SL",
        "STOP",
        "STOP_LOSS",
        "STOPLOSS",
        "HIT_SL",
        "SL_HIT",
    }
    be_tokens = {
        "BE",
        "B/E",
        "BREAKEVEN",
        "BREAK_EVEN",
        "EVEN",
        "FLAT",
        "DRAW",
    }
    small_win_tokens = {"SMALL_WIN", "TINY_WIN"}
    small_loss_tokens = {"SMALL_LOSS", "TINY_LOSS"}
    if normalized in small_win_tokens:
        return "SMALL_WIN"
    if normalized in small_loss_tokens:
        return "SMALL_LOSS"
    if normalized in win_tokens or any(token in normalized for token in ["TAKE_PROFIT", "TP_HIT", "HIT_TP"]):
        return "WIN"
    if normalized in loss_tokens or any(token in normalized for token in ["STOP_LOSS", "SL_HIT", "HIT_SL"]):
        return "LOSS"
    if normalized in be_tokens:
        return "BREAKEVEN"
    if "WIN" in normalized:
        return "WIN"
    if "LOSS" in normalized:
        return "LOSS"
    return ""


def infer_close_reason_from_text(value: Any) -> str:
    text = clean_str(value).upper().replace("-", "_").replace(" ", "_")
    if not text:
        return ""
    if "TP" in text or "TAKE_PROFIT" in text or "TARGET" in text:
        return "TP"
    if "SL" in text or "STOP_LOSS" in text or "STOP" in text:
        return "SL"
    if "BE" in text or "BREAKEVEN" in text or "BREAK_EVEN" in text:
        return "BREAKEVEN"
    return ""


def choose_profit_r(row: pd.Series, direction: str, entry: float | None, sl: float | None, close: float | None, args: argparse.Namespace) -> tuple[float | None, str]:
    if args.prefer_net_r:
        for col in NET_R_COLUMNS:
            value = first_float(row, [col], None)
            if value is not None:
                return value, col

    for col in GROSS_R_COLUMNS:
        value = first_float(row, [col], None)
        if value is None:
            continue
        source = col
        if args.prefer_net_r and args.spread_cost_r_column:
            spread_cost = first_float(row, [args.spread_cost_r_column], None)
            if spread_cost is not None:
                value = value - abs(float(spread_cost))
                source = f"{col}-abs({args.spread_cost_r_column})"
        return value, source

    value = profit_r_from_prices(direction, entry, sl, close)
    if value is not None:
        return value, "prices"

    return None, ""


def planned_rr(direction: str, entry: float | None, sl: float | None, tp: float | None, row: pd.Series) -> float | None:
    existing = first_float(row, ["rr_planned", "planned_rr", "rr", "risk_reward", "reward_risk"], None)
    if existing is not None:
        return existing
    sd = stop_distance(direction, entry, sl)
    td = take_distance(direction, entry, tp)
    if sd is None or td is None or abs(sd) <= 1e-12:
        return None
    return abs(float(td)) / abs(float(sd))


def profit_points_from_row(row: pd.Series, direction: str, entry: float | None, close: float | None) -> float | None:
    existing = first_float(row, ["profit_points", "points", "pips", "price_profit", "gross_points", "net_points"], None)
    if existing is not None:
        return existing
    return side_price_distance(direction, entry, close)


def holding_minutes_from_row(row: pd.Series, entry_time: str, close_time: str) -> float | None:
    existing = first_float(row, ["holding_minutes", "duration_minutes", "hold_minutes"], None)
    if existing is not None:
        return existing
    entry_dt = parse_time_any(entry_time)
    close_dt = parse_time_any(close_time)
    if entry_dt is None or close_dt is None:
        return None
    return (close_dt - entry_dt).total_seconds() / 60.0


def make_generated_trade_key(symbol: str, strategy_id: str, direction: str, entry_time: str, row_index: int) -> str:
    raw = f"BACKTEST|{symbol}|{strategy_id}|{direction}|{entry_time}|row={row_index}"
    return safe_key_text(raw)


def build_one_row(source_row: pd.Series, row_index: int, args: argparse.Namespace, seen_ids: set[str]) -> dict[str, Any]:
    now = utc_now_text()

    broker_symbol = first_text(source_row, ["broker_symbol", "mt5_symbol", "raw_symbol", "instrument"], args.broker_symbol)
    raw_symbol = first_text(source_row, SYMBOL_COLUMNS, broker_symbol or args.symbol)
    symbol = normalize_grouping_symbol(raw_symbol, args.symbol)
    if args.symbol:
        symbol = normalize_grouping_symbol(symbol, args.symbol)

    strategy_default = clean_str(args.strategy_key) or clean_str(args.strategy_id)
    strategy_id = first_text(source_row, STRATEGY_COLUMNS, strategy_default)
    strategy_key = first_text(source_row, ["strategy_key", "strategy", "pair_name", "setup"], clean_str(args.strategy_key) or strategy_id)
    pair_name = first_text(source_row, ["pair_name", "strategy", "strategy_key"], strategy_key or strategy_id)
    condition_id = first_text(source_row, ["condition_id", "router_strategy_id"], strategy_id)
    router_strategy_slot = first_text(source_row, ["router_strategy_slot", "slot", "strategy_slot"], strategy_key or strategy_id)
    router_strategy_id = first_text(source_row, ["router_strategy_id", "condition_id"], strategy_id)

    direction = normalize_direction(first_present(source_row, DIRECTION_COLUMNS, args.direction))
    if not direction and args.direction:
        direction = normalize_direction(args.direction)

    entry_time = time_to_text(first_present(source_row, ENTRY_TIME_COLUMNS, ""))
    close_time = time_to_text(first_present(source_row, CLOSE_TIME_COLUMNS, ""))
    entry_price = first_float(source_row, ENTRY_PRICE_COLUMNS, None)
    entry_price_reference = first_float(source_row, ["entry_price_reference", "signal_price", "reference_price"], entry_price)
    sl_price = first_float(source_row, SL_PRICE_COLUMNS, None)
    tp_price = first_float(source_row, TP_PRICE_COLUMNS, None)
    close_price = first_float(source_row, CLOSE_PRICE_COLUMNS, None)

    profit_r, profit_r_source = choose_profit_r(source_row, direction, entry_price, sl_price, close_price, args)
    profit = first_float(source_row, PROFIT_COLUMNS, None)
    commission = first_float(source_row, ["commission", "commissions"], 0.0)
    swap = first_float(source_row, ["swap", "storage"], 0.0)
    net_profit = first_float(source_row, ["net_profit", "net_pnl", "net_pl"], None)
    if net_profit is None and profit is not None:
        net_profit = float(profit) + float(commission or 0.0) + float(swap or 0.0)

    outcome_text = ""
    for name in OUTCOME_COLUMNS_CANDIDATES:
        outcome_text = parse_outcome_text(first_present(source_row, [name], ""))
        if outcome_text:
            break
    if not outcome_text:
        outcome_text = classify_outcome(net_profit if net_profit is not None else profit, profit_r, small_r=args.small_r, small_profit_abs=args.small_profit_abs)

    close_reason = first_text(source_row, ["close_reason", "exit_reason", "reason"], "")
    close_reason = infer_close_reason_from_text(close_reason) or infer_close_reason(direction, close_price, sl_price, tp_price, tolerance=float(args.close_reason_tolerance))
    if close_reason == "UNKNOWN" and outcome_text == "WIN":
        close_reason = "TP"
    elif close_reason == "UNKNOWN" and outcome_text == "LOSS":
        close_reason = "SL"

    order_key = first_text(source_row, ["order_key"], "")
    payload_key = first_text(source_row, ["payload_key"], "")
    signal_key = first_text(source_row, ["signal_key"], "")
    explicit_trade_id = first_text(source_row, ID_COLUMNS, "")
    if not order_key:
        order_key = explicit_trade_id or make_generated_trade_key(symbol, strategy_id, direction, entry_time, row_index)
    if not payload_key:
        payload_key = first_text(source_row, ["payload_id"], order_key)
    if not signal_key:
        signal_key = first_text(source_row, ["signal_id"], payload_key or order_key)

    row: dict[str, Any] = {
        "schema_version": OUTCOME_LEDGER_SCHEMA_VERSION,
        "created_at_utc": now,
        "updated_at_utc": now,
        "trade_id": explicit_trade_id,
        "match_status": "MATCHED",
        "match_method": "BACKTEST_TRADES_CSV",
        "execution_status": "EXECUTED",
        "send_status_text": "BACKTEST_EXECUTED",
        "account_login": first_int(source_row, ["account_login", "login"], 0),
        "account_server": first_text(source_row, ["account_server", "server"], ""),
        "broker_symbol": broker_symbol or raw_symbol,
        "symbol": symbol,
        "strategy_key": strategy_key or strategy_id,
        "strategy_alias": first_text(source_row, ["strategy_alias", "alias"], ""),
        "strategy_id": strategy_id or strategy_key,
        "condition_id": condition_id or strategy_id or strategy_key,
        "router_strategy_slot": router_strategy_slot or strategy_key or strategy_id,
        "router_strategy_id": router_strategy_id or strategy_id or strategy_key,
        "pair_name": pair_name or strategy_key or strategy_id,
        "candidate_rank": first_text(source_row, ["candidate_rank", "rank"], ""),
        "direction": direction,
        "lot": first_float(source_row, ["lot", "volume", "size"], None),
        "order_key": order_key,
        "payload_key": payload_key,
        "signal_key": signal_key,
        "position_ticket": first_int(source_row, ["position_ticket", "position_id", "ticket"], 0),
        "order_ticket": first_int(source_row, ["order_ticket", "order_id"], 0),
        "deal_ticket": first_int(source_row, ["deal_ticket", "deal_id"], 0),
        "entry_order_ticket": first_int(source_row, ["entry_order_ticket"], 0),
        "entry_deal_ticket": first_int(source_row, ["entry_deal_ticket"], 0),
        "close_order_ticket": first_int(source_row, ["close_order_ticket"], 0),
        "close_deal_ticket": first_int(source_row, ["close_deal_ticket"], 0),
        "entry_time": entry_time,
        "entry_price": entry_price,
        "entry_price_reference": entry_price_reference,
        "sl_price": sl_price,
        "tp_price": tp_price,
        "close_time": close_time,
        "close_price": close_price,
        "profit": profit,
        "profit_points": profit_points_from_row(source_row, direction, entry_price, close_price),
        "profit_r": profit_r,
        "commission": commission,
        "swap": swap,
        "net_profit": net_profit,
        "outcome": outcome_text,
        "close_reason": close_reason,
        "holding_minutes": holding_minutes_from_row(source_row, entry_time, close_time),
        "mfe_points": first_float(source_row, ["mfe_points", "max_favorable", "max_favorable_points"], None),
        "mae_points": first_float(source_row, ["mae_points", "max_adverse", "max_adverse_points"], None),
        "mfe_r": first_float(source_row, ["mfe_r", "max_favorable_r"], None),
        "mae_r": first_float(source_row, ["mae_r", "max_adverse_r"], None),
        "stop_distance": stop_distance(direction, entry_price, sl_price),
        "take_distance": take_distance(direction, entry_price, tp_price),
        "rr_planned": planned_rr(direction, entry_price, sl_price, tp_price, source_row),
        "spread_at_entry": first_float(source_row, ["spread_at_entry", "spread", "entry_spread"], None),
        "slippage_entry": first_float(source_row, ["slippage_entry", "entry_slippage"], None),
        "slippage_close": first_float(source_row, ["slippage_close", "close_slippage", "exit_slippage"], None),
        "source_order_ledger_csv": args.backtest_trades_csv,
        "source_order_ledger_row_index": row_index,
        "source_mt5_positions_csv": "",
        "source_mt5_position_row_index": 0,
        "source_mt5_deals_csv": "",
        "notes": f"backtest trade row converted to live-compatible outcome ledger; profit_r_source={profit_r_source or 'unknown'}; AI hypothesis only",
    }

    row["trade_id"] = clean_str(row.get("trade_id")) or canonical_trade_id(row)
    original_trade_id = row["trade_id"]
    if original_trade_id in seen_ids:
        row["trade_id"] = f"{original_trade_id}#btrow{row_index}"
        row["order_key"] = f"{clean_str(row.get('order_key'), original_trade_id)}#btrow{row_index}"
        row["payload_key"] = f"{clean_str(row.get('payload_key'), original_trade_id)}#btrow{row_index}"
        row["signal_key"] = f"{clean_str(row.get('signal_key'), original_trade_id)}#btrow{row_index}"
    seen_ids.add(clean_str(row["trade_id"]))

    return {col: row.get(col, "") for col in OUTCOME_COLUMNS}


def outcome_bucket(outcome: Any) -> str:
    text = clean_str(outcome).upper()
    if text in {"LOSS", "SMALL_LOSS"}:
        return "loss"
    if text in {"WIN", "SMALL_WIN"}:
        return "win"
    if text == "BREAKEVEN":
        return "breakeven"
    return "unknown"


def sort_for_sampling(df: pd.DataFrame, policy: str, seed: int) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    out = df.copy()
    if "entry_time" in out.columns:
        out["_entry_time_sort"] = pd.to_datetime(out["entry_time"], errors="coerce")
    else:
        out["_entry_time_sort"] = pd.NaT
    out["_source_order_ledger_row_index_sort"] = pd.to_numeric(out.get("source_order_ledger_row_index", pd.Series(range(1, len(out) + 1))), errors="coerce")
    if policy == "random":
        return out.sample(frac=1.0, random_state=int(seed)).drop(columns=[c for c in ["_entry_time_sort", "_source_order_ledger_row_index_sort"] if c in out.columns])
    return out.sort_values(["_entry_time_sort", "_source_order_ledger_row_index_sort"], na_position="last").drop(columns=[c for c in ["_entry_time_sort", "_source_order_ledger_row_index_sort"] if c in out.columns])


def cap_bucket(df: pd.DataFrame, cap: int, policy: str, seed: int) -> pd.DataFrame:
    if df.empty or cap <= 0 or len(df) <= cap:
        return df.copy()
    ordered = sort_for_sampling(df, policy, seed)
    if policy == "newest":
        return ordered.tail(cap).copy()
    return ordered.head(cap).copy()


def apply_filters(raw: pd.DataFrame, args: argparse.Namespace) -> tuple[pd.DataFrame, dict[str, Any]]:
    df = raw.copy()
    report: dict[str, Any] = {"rows_before_filters": int(len(df))}

    if args.symbol:
        symbol_filter = normalize_grouping_symbol(args.symbol, args.symbol)
        symbol_values = df.apply(lambda row: normalize_grouping_symbol(first_present(row, SYMBOL_COLUMNS, args.symbol), args.symbol), axis=1)
        df = df[symbol_values == symbol_filter].copy()
        report["rows_after_symbol_filter"] = int(len(df))
        report["symbol_filter"] = symbol_filter

    if args.strategy_id:
        strategy_filter = clean_str(args.strategy_id).upper()
        strategy_values = df.apply(lambda row: first_text(row, STRATEGY_COLUMNS, args.strategy_id).upper(), axis=1)
        df = df[strategy_values == strategy_filter].copy()
        report["rows_after_strategy_filter"] = int(len(df))
        report["strategy_filter"] = strategy_filter

    if args.direction:
        direction_filter = normalize_direction(args.direction)
        direction_values = df.apply(lambda row: normalize_direction(first_present(row, DIRECTION_COLUMNS, args.direction)), axis=1)
        df = df[direction_values == direction_filter].copy()
        report["rows_after_direction_filter"] = int(len(df))
        report["direction_filter"] = direction_filter

    return df, report


def main() -> int:
    args = parse_args()
    raw = read_csv(args.backtest_trades_csv)
    filtered, filter_report = apply_filters(raw, args)

    rows: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for i, (_, source_row) in enumerate(filtered.iterrows(), start=1):
        source_index = int(source_row.name) + 1 if isinstance(source_row.name, (int, float)) and not math.isnan(float(source_row.name)) else i
        rows.append(build_one_row(source_row, source_index, args, seen_ids))

    full_out = pd.DataFrame(rows, columns=OUTCOME_COLUMNS)
    if not args.include_unknown and not full_out.empty:
        full_out = full_out[full_out["outcome"].map(outcome_bucket) != "unknown"].copy()

    buckets = {
        "loss": full_out[full_out["outcome"].map(outcome_bucket) == "loss"].copy() if not full_out.empty else pd.DataFrame(columns=OUTCOME_COLUMNS),
        "win": full_out[full_out["outcome"].map(outcome_bucket) == "win"].copy() if not full_out.empty else pd.DataFrame(columns=OUTCOME_COLUMNS),
        "breakeven": full_out[full_out["outcome"].map(outcome_bucket) == "breakeven"].copy() if not full_out.empty else pd.DataFrame(columns=OUTCOME_COLUMNS),
        "unknown": full_out[full_out["outcome"].map(outcome_bucket) == "unknown"].copy() if not full_out.empty else pd.DataFrame(columns=OUTCOME_COLUMNS),
    }

    sampled_parts = [
        cap_bucket(buckets["loss"], args.max_losses, args.sample_policy, args.sample_seed),
        cap_bucket(buckets["win"], args.max_wins, args.sample_policy, args.sample_seed + 1),
        cap_bucket(buckets["breakeven"], args.max_breakevens, args.sample_policy, args.sample_seed + 2),
    ]
    if args.include_unknown:
        sampled_parts.append(cap_bucket(buckets["unknown"], args.max_unknown, args.sample_policy, args.sample_seed + 3))

    sampled = pd.concat(sampled_parts, ignore_index=True, sort=False) if sampled_parts else pd.DataFrame(columns=OUTCOME_COLUMNS)
    if not sampled.empty:
        sampled["_entry_time_sort"] = pd.to_datetime(sampled["entry_time"], errors="coerce")
        sampled["_source_order_ledger_row_index_sort"] = pd.to_numeric(sampled["source_order_ledger_row_index"], errors="coerce")
        sampled = sampled.sort_values(["_entry_time_sort", "_source_order_ledger_row_index_sort"], na_position="last").drop(columns=["_entry_time_sort", "_source_order_ledger_row_index_sort"]).reset_index(drop=True)

    write_csv(sampled, args.output_csv)

    summary = {
        "script": "build_trade_outcome_ledger_from_backtest_trades.py",
        "created_at_utc": utc_now_text(),
        "backtest_trades_csv": args.backtest_trades_csv,
        "output_csv": args.output_csv,
        "rows_in_raw": int(len(raw)),
        "rows_after_filters": int(len(filtered)),
        "rows_after_unknown_filter": int(len(full_out)),
        "rows_out_sampled": int(len(sampled)),
        "filter_report": filter_report,
        "sampling": {
            "sample_policy": args.sample_policy,
            "sample_seed": int(args.sample_seed),
            "max_losses": int(args.max_losses),
            "max_wins": int(args.max_wins),
            "max_breakevens": int(args.max_breakevens),
            "include_unknown": bool(args.include_unknown),
            "max_unknown": int(args.max_unknown),
        },
        "prefer_net_r": bool(args.prefer_net_r),
        "spread_cost_r_column": args.spread_cost_r_column,
        "full_outcome_counts": full_out["outcome"].value_counts(dropna=False).to_dict() if "outcome" in full_out.columns and not full_out.empty else {},
        "sampled_outcome_counts": sampled["outcome"].value_counts(dropna=False).to_dict() if "outcome" in sampled.columns and not sampled.empty else {},
        "strategy_id_counts": sampled["strategy_id"].value_counts(dropna=False).to_dict() if "strategy_id" in sampled.columns and not sampled.empty else {},
        "symbol_counts": sampled["symbol"].value_counts(dropna=False).to_dict() if "symbol" in sampled.columns and not sampled.empty else {},
        "direction_counts": sampled["direction"].value_counts(dropna=False).to_dict() if "direction" in sampled.columns and not sampled.empty else {},
        "match_status_counts": sampled["match_status"].value_counts(dropna=False).to_dict() if "match_status" in sampled.columns and not sampled.empty else {},
        "execution_status_counts": sampled["execution_status"].value_counts(dropna=False).to_dict() if "execution_status" in sampled.columns and not sampled.empty else {},
        "notes": [
            "Backtest rows are marked MATCHED/EXECUTED for compatibility with summarize_trade_ai_review_ledger.py closed-trade filtering.",
            "Backtest outputs must be kept separate from live outputs.",
            "AI review downstream is hypothesis tagging only and must not change rules from one trade.",
        ],
    }
    if args.output_json:
        write_json(args.output_json, summary)

    print("build_trade_outcome_ledger_from_backtest_trades")
    print(f"rows_in_raw: {summary['rows_in_raw']}")
    print(f"rows_after_filters: {summary['rows_after_filters']}")
    print(f"rows_after_unknown_filter: {summary['rows_after_unknown_filter']}")
    print(f"rows_out_sampled: {summary['rows_out_sampled']}")
    print(f"sampled_outcome_counts: {summary['sampled_outcome_counts']}")
    print(f"output_csv: {args.output_csv}")
    if args.output_json:
        print(f"output_json: {args.output_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
