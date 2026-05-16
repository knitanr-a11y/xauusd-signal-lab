#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""Build trade_outcome_ledger.csv from strategy order ledgers and MT5 history.

This script is deterministic and does not call AI.

Inputs:
- one or more order ledger CSVs from existing GOLD/BTC senders
- mt5_history_positions.csv exported by export_mt5_closed_trade_history.py
- optional mt5_history_deals.csv for richer fallback matching

Matching priority:
1. position_ticket / position_id
2. order_ticket / entry_order_ticket / close_order_ticket
3. deal_ticket / entry_deal_ticket / close_deal_ticket
4. symbol + direction + closest entry time fallback

The output is the factual ledger used by the AI review pipeline. AI comments and
hypothesis tags are intentionally stored elsewhere.
"""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import pandas as pd

from trade_ai_review_utils import (
    OUTCOME_LEDGER_SCHEMA_VERSION,
    canonical_trade_id,
    classify_outcome,
    clean_float,
    clean_int,
    clean_str,
    infer_close_reason,
    normalize_direction,
    normalize_symbol_from_broker,
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

OUTCOME_COLUMNS = [
    "schema_version",
    "created_at_utc",
    "updated_at_utc",
    "trade_id",
    "match_status",
    "match_method",
    "account_login",
    "account_server",
    "broker_symbol",
    "symbol",
    "strategy_key",
    "strategy_alias",
    "strategy_id",
    "condition_id",
    "router_strategy_slot",
    "router_strategy_id",
    "pair_name",
    "candidate_rank",
    "direction",
    "lot",
    "order_key",
    "payload_key",
    "signal_key",
    "position_ticket",
    "order_ticket",
    "deal_ticket",
    "entry_order_ticket",
    "entry_deal_ticket",
    "close_order_ticket",
    "close_deal_ticket",
    "entry_time",
    "entry_price",
    "entry_price_reference",
    "sl_price",
    "tp_price",
    "close_time",
    "close_price",
    "profit",
    "profit_points",
    "profit_r",
    "commission",
    "swap",
    "net_profit",
    "outcome",
    "close_reason",
    "holding_minutes",
    "mfe_points",
    "mae_points",
    "mfe_r",
    "mae_r",
    "stop_distance",
    "take_distance",
    "rr_planned",
    "spread_at_entry",
    "slippage_entry",
    "slippage_close",
    "source_order_ledger_csv",
    "source_order_ledger_row_index",
    "source_mt5_positions_csv",
    "source_mt5_position_row_index",
    "source_mt5_deals_csv",
    "notes",
]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build deterministic trade outcome ledger from sender order ledgers and MT5 history.")
    p.add_argument("--order-ledger-csv", action="append", required=True, help="Order ledger CSV. Repeat for GOLD/BTC/multi-strategy ledgers.")
    p.add_argument("--mt5-positions-csv", required=True, help="mt5_history_positions.csv from export_mt5_closed_trade_history.py")
    p.add_argument("--mt5-deals-csv", default="", help="Optional mt5_history_deals.csv")
    p.add_argument("--output-csv", required=True)
    p.add_argument("--output-json", default=None)
    p.add_argument("--time-match-tolerance-minutes", type=float, default=180.0)
    p.add_argument("--close-reason-tolerance", type=float, default=0.30, help="Price tolerance for TP/SL close reason inference.")
    p.add_argument("--small-r", type=float, default=0.10)
    p.add_argument("--small-profit-abs", type=float, default=0.0)
    return p.parse_args()


def load_order_ledgers(paths: list[str]) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for path in paths:
        df = read_csv(path)
        if df.empty:
            continue
        df = df.copy()
        df["source_order_ledger_csv"] = str(path)
        df["source_order_ledger_row_index"] = range(1, len(df) + 1)
        frames.append(df)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True, sort=False)


def normalize_positions(df: pd.DataFrame, source_path: str) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    out = df.copy()
    out["source_mt5_positions_csv"] = str(source_path)
    out["source_mt5_position_row_index"] = range(1, len(out) + 1)
    for col in ["position_id", "entry_order_ticket", "entry_deal_ticket", "close_order_ticket", "close_deal_ticket"]:
        if col in out.columns:
            out[col + "_int"] = out[col].map(lambda x: clean_int(x, 0))
    for col in ["entry_time", "close_time"]:
        if col in out.columns:
            out[col + "_dt"] = out[col].map(parse_time_any)
    if "symbol" in out.columns:
        out["broker_symbol_norm"] = out["symbol"].map(clean_str)
        out["symbol_norm"] = out["symbol"].map(normalize_symbol_from_broker)
    else:
        out["broker_symbol_norm"] = ""
        out["symbol_norm"] = ""
    if "direction" in out.columns:
        out["direction_norm"] = out["direction"].map(normalize_direction)
    else:
        out["direction_norm"] = ""
    return out


def normalize_order_row(row: pd.Series) -> dict[str, Any]:
    broker_symbol = clean_str(row_get(row, ["broker_symbol", "symbol"], ""))
    symbol = clean_str(row_get(row, ["symbol"], normalize_symbol_from_broker(broker_symbol)))
    if not symbol or symbol == broker_symbol:
        symbol = normalize_symbol_from_broker(broker_symbol)
    direction = normalize_direction(row_get(row, ["direction", "order_type"], ""))
    entry_price_reference = clean_float(row_get(row, ["entry_price_reference", "entry_price", "price", "current_execution_price"], None))
    entry_price = clean_float(row_get(row, ["price", "current_execution_price", "entry_price", "entry_price_reference"], entry_price_reference))
    sl_price = clean_float(row_get(row, ["sl_price", "sl"], None))
    tp_price = clean_float(row_get(row, ["tp_price", "tp"], None))
    entry_time = row_get(row, ["entry_time", "sent_at", "created_at_utc", "signal_close_time"], "")
    return {
        "account_login": clean_int(row_get(row, ["account_login", "login"], 0), 0),
        "account_server": clean_str(row_get(row, ["account_server", "server"], "")),
        "broker_symbol": broker_symbol,
        "symbol": symbol,
        "strategy_key": clean_str(row_get(row, ["strategy_key", "pair_name", "router_strategy_slot"], "")),
        "strategy_alias": clean_str(row_get(row, ["strategy_alias"], "")),
        "strategy_id": clean_str(row_get(row, ["strategy_id", "router_strategy_id"], "")),
        "condition_id": clean_str(row_get(row, ["condition_id"], "")),
        "router_strategy_slot": clean_str(row_get(row, ["router_strategy_slot"], "")),
        "router_strategy_id": clean_str(row_get(row, ["router_strategy_id"], "")),
        "pair_name": clean_str(row_get(row, ["pair_name"], "")),
        "candidate_rank": clean_str(row_get(row, ["candidate_rank"], "")),
        "direction": direction,
        "lot": clean_float(row_get(row, ["lot", "volume"], None)),
        "order_key": clean_str(row_get(row, ["order_key"], "")),
        "payload_key": clean_str(row_get(row, ["payload_key"], "")),
        "signal_key": clean_str(row_get(row, ["signal_key"], "")),
        "position_ticket": clean_int(row_get(row, ["position_ticket", "position"], 0), 0),
        "order_ticket": clean_int(row_get(row, ["order_ticket", "order", "order_id"], 0), 0),
        "deal_ticket": clean_int(row_get(row, ["deal_ticket", "deal", "deal_id"], 0), 0),
        "entry_time": time_to_text(entry_time),
        "entry_time_dt": parse_time_any(entry_time),
        "entry_price": entry_price,
        "entry_price_reference": entry_price_reference,
        "sl_price": sl_price,
        "tp_price": tp_price,
        "spread_at_entry": clean_float(row_get(row, ["spread_at_entry", "spread"], None)),
        "slippage_entry": clean_float(row_get(row, ["slippage_entry"], None)),
        "source_order_ledger_csv": clean_str(row_get(row, ["source_order_ledger_csv"], "")),
        "source_order_ledger_row_index": clean_int(row_get(row, ["source_order_ledger_row_index"], 0), 0),
    }


def find_position_match(order: dict[str, Any], positions: pd.DataFrame, tolerance_minutes: float) -> tuple[pd.Series | None, str]:
    if positions.empty:
        return None, "NO_MT5_POSITIONS"

    candidates = positions.copy()

    pos_ticket = clean_int(order.get("position_ticket"), 0)
    if pos_ticket and "position_id_int" in candidates.columns:
        hit = candidates[candidates["position_id_int"] == pos_ticket]
        if not hit.empty:
            return hit.iloc[0], "position_ticket"

    order_ticket = clean_int(order.get("order_ticket"), 0)
    if order_ticket:
        mask = pd.Series(False, index=candidates.index)
        for col in ["entry_order_ticket_int", "close_order_ticket_int"]:
            if col in candidates.columns:
                mask = mask | (candidates[col] == order_ticket)
        hit = candidates[mask]
        if not hit.empty:
            return hit.iloc[0], "order_ticket"

    deal_ticket = clean_int(order.get("deal_ticket"), 0)
    if deal_ticket:
        mask = pd.Series(False, index=candidates.index)
        for col in ["entry_deal_ticket_int", "close_deal_ticket_int"]:
            if col in candidates.columns:
                mask = mask | (candidates[col] == deal_ticket)
        hit = candidates[mask]
        if not hit.empty:
            return hit.iloc[0], "deal_ticket"

    symbol = clean_str(order.get("symbol"), normalize_symbol_from_broker(order.get("broker_symbol")))
    broker_symbol = clean_str(order.get("broker_symbol"))
    direction = normalize_direction(order.get("direction"))
    if symbol:
        candidates = candidates[(candidates["symbol_norm"] == symbol) | (candidates["broker_symbol_norm"] == broker_symbol)].copy()
    if direction:
        candidates = candidates[candidates["direction_norm"] == direction].copy()
    entry_dt = order.get("entry_time_dt")
    if entry_dt is not None and not candidates.empty and "entry_time_dt" in candidates.columns:
        candidates["entry_time_diff_minutes"] = candidates["entry_time_dt"].map(lambda x: abs((x - entry_dt).total_seconds()) / 60.0 if x is not None and not pd.isna(x) else float("inf"))
        candidates = candidates[candidates["entry_time_diff_minutes"] <= float(tolerance_minutes)].copy()
        if not candidates.empty:
            return candidates.sort_values("entry_time_diff_minutes").iloc[0], "symbol_direction_time"

    return None, "NO_MATCH"


def position_value(pos: pd.Series | None, names: list[str], default: Any = "") -> Any:
    if pos is None:
        return default
    for name in names:
        if name in pos.index:
            value = pos.get(name)
            try:
                if pd.isna(value):
                    continue
            except Exception:
                pass
            return value
    return default


def build_outcome_row(order_row: pd.Series, positions: pd.DataFrame, args: argparse.Namespace) -> dict[str, Any]:
    now = utc_now_text()
    order = normalize_order_row(order_row)
    pos, match_method = find_position_match(order, positions, args.time_match_tolerance_minutes)
    matched = pos is not None

    entry_price = clean_float(position_value(pos, ["entry_price"], order.get("entry_price")), order.get("entry_price"))
    close_price = clean_float(position_value(pos, ["close_price"], None))
    sl_price = clean_float(order.get("sl_price"))
    tp_price = clean_float(order.get("tp_price"))
    direction = normalize_direction(order.get("direction"))
    profit = clean_float(position_value(pos, ["profit"], None))
    commission = clean_float(position_value(pos, ["commission"], None), 0.0)
    swap = clean_float(position_value(pos, ["swap"], None), 0.0)
    net_profit = clean_float(position_value(pos, ["net_profit"], None), None)
    if net_profit is None and profit is not None:
        net_profit = float(profit) + float(commission or 0.0) + float(swap or 0.0)
    profit_points = side_price_distance(direction, entry_price, close_price)
    profit_r = profit_r_from_prices(direction, entry_price, sl_price, close_price)
    sd = stop_distance(direction, entry_price, sl_price)
    td = take_distance(direction, entry_price, tp_price)
    rr = None if sd is None or td is None or abs(sd) <= 1e-12 else abs(float(td)) / abs(float(sd))
    outcome = classify_outcome(net_profit if net_profit is not None else profit, profit_r, small_r=args.small_r, small_profit_abs=args.small_profit_abs)
    close_reason = infer_close_reason(direction, close_price, sl_price, tp_price, tolerance=float(args.close_reason_tolerance))
    entry_time = time_to_text(position_value(pos, ["entry_time"], order.get("entry_time")))
    close_time = time_to_text(position_value(pos, ["close_time"], ""))
    entry_dt = parse_time_any(entry_time)
    close_dt = parse_time_any(close_time)
    holding_minutes = None
    if entry_dt is not None and close_dt is not None:
        holding_minutes = (close_dt - entry_dt).total_seconds() / 60.0

    row = {
        "schema_version": OUTCOME_LEDGER_SCHEMA_VERSION,
        "created_at_utc": now,
        "updated_at_utc": now,
        "match_status": "MATCHED" if matched else "UNMATCHED_OPEN_OR_MISSING_HISTORY",
        "match_method": match_method,
        **{k: order.get(k, "") for k in [
            "account_login", "account_server", "broker_symbol", "symbol", "strategy_key", "strategy_alias",
            "strategy_id", "condition_id", "router_strategy_slot", "router_strategy_id", "pair_name",
            "candidate_rank", "direction", "lot", "order_key", "payload_key", "signal_key",
        ]},
        "position_ticket": clean_int(position_value(pos, ["position_id"], order.get("position_ticket", 0)), 0),
        "order_ticket": order.get("order_ticket", 0),
        "deal_ticket": order.get("deal_ticket", 0),
        "entry_order_ticket": clean_int(position_value(pos, ["entry_order_ticket"], 0), 0),
        "entry_deal_ticket": clean_int(position_value(pos, ["entry_deal_ticket"], 0), 0),
        "close_order_ticket": clean_int(position_value(pos, ["close_order_ticket"], 0), 0),
        "close_deal_ticket": clean_int(position_value(pos, ["close_deal_ticket"], 0), 0),
        "entry_time": entry_time,
        "entry_price": entry_price,
        "entry_price_reference": order.get("entry_price_reference"),
        "sl_price": sl_price,
        "tp_price": tp_price,
        "close_time": close_time,
        "close_price": close_price,
        "profit": profit,
        "profit_points": profit_points,
        "profit_r": profit_r,
        "commission": commission,
        "swap": swap,
        "net_profit": net_profit,
        "outcome": outcome if matched else "OPEN",
        "close_reason": close_reason if matched else "OPEN",
        "holding_minutes": holding_minutes,
        "mfe_points": None,
        "mae_points": None,
        "mfe_r": None,
        "mae_r": None,
        "stop_distance": sd,
        "take_distance": td,
        "rr_planned": rr,
        "spread_at_entry": order.get("spread_at_entry"),
        "slippage_entry": order.get("slippage_entry"),
        "slippage_close": None,
        "source_order_ledger_csv": order.get("source_order_ledger_csv"),
        "source_order_ledger_row_index": order.get("source_order_ledger_row_index"),
        "source_mt5_positions_csv": position_value(pos, ["source_mt5_positions_csv"], args.mt5_positions_csv if matched else ""),
        "source_mt5_position_row_index": clean_int(position_value(pos, ["source_mt5_position_row_index"], 0), 0),
        "source_mt5_deals_csv": args.mt5_deals_csv,
        "notes": "deterministic outcome ledger; AI review not applied",
    }
    row["trade_id"] = canonical_trade_id(row)
    return {col: row.get(col, "") for col in OUTCOME_COLUMNS}


def main() -> int:
    args = parse_args()
    orders = load_order_ledgers(args.order_ledger_csv)
    positions_raw = read_csv(args.mt5_positions_csv)
    positions = normalize_positions(positions_raw, args.mt5_positions_csv)

    rows: list[dict[str, Any]] = []
    for _, order_row in orders.iterrows():
        rows.append(build_outcome_row(order_row, positions, args))

    out = pd.DataFrame(rows, columns=OUTCOME_COLUMNS)
    write_csv(out, args.output_csv)

    summary = {
        "script": "build_trade_outcome_ledger_from_order_ledger.py",
        "created_at_utc": utc_now_text(),
        "order_ledger_csv": args.order_ledger_csv,
        "mt5_positions_csv": args.mt5_positions_csv,
        "mt5_deals_csv": args.mt5_deals_csv,
        "output_csv": args.output_csv,
        "rows_in_order_ledgers": int(len(orders)),
        "rows_in_mt5_positions": int(len(positions)),
        "rows_out": int(len(out)),
        "matched_rows": int((out["match_status"] == "MATCHED").sum()) if not out.empty else 0,
        "open_or_unmatched_rows": int((out["match_status"] != "MATCHED").sum()) if not out.empty else 0,
        "outcome_counts": out["outcome"].value_counts(dropna=False).to_dict() if "outcome" in out.columns and not out.empty else {},
        "match_method_counts": out["match_method"].value_counts(dropna=False).to_dict() if "match_method" in out.columns and not out.empty else {},
    }
    if args.output_json:
        write_json(args.output_json, summary)

    print("build_trade_outcome_ledger_from_order_ledger")
    print(f"rows_in_order_ledgers: {summary['rows_in_order_ledgers']}")
    print(f"rows_in_mt5_positions: {summary['rows_in_mt5_positions']}")
    print(f"rows_out: {summary['rows_out']}")
    print(f"matched_rows: {summary['matched_rows']}")
    print(f"open_or_unmatched_rows: {summary['open_or_unmatched_rows']}")
    print(f"output_csv: {args.output_csv}")
    if args.output_json:
        print(f"output_json: {args.output_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
