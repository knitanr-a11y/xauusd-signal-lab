#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

BTC6_ID = "BTC6_M15_TWO_PIVOT_P3_BROAD_N_236_886"
PIP_USD = 10.0
DEFAULT_LOT = 0.01
DEFAULT_SPREAD_USD = 30.0
TRADE_COLUMNS = [
    "signal_key", "candidate_id", "status", "direction", "lot", "signal_close_time",
    "planned_entry_time", "actual_entry_time", "entry_bar_time", "reference_entry_bid",
    "actual_entry_bid", "effective_entry_price", "sl_price", "tp_price", "planned_rr",
    "effective_risk_usd", "effective_reward_usd", "effective_rr", "last_processed_m5_time",
    "latest_mark_time", "latest_mark_bid", "unrealized_pips", "unrealized_r",
    "mfe_pips", "mae_pips", "exit_time", "exit_reason", "exit_chart_price",
    "pnl_pips", "r_multiple", "pnl_account_currency", "unrealized_account_currency", "account_currency",
    "registered_at_utc", "opened_at_utc", "closed_at_utc",
]
EVENT_COLUMNS = [
    "event_id", "event_recorded_at_utc", "market_time", "event_type", "signal_key",
    "status", "direction", "lot", "actual_entry_bid", "sl_price", "tp_price",
    "exit_reason", "pnl_pips", "r_multiple", "mfe_pips", "mae_pips",
    "pnl_account_currency", "account_currency",
]
DISCORD_COLUMNS = [
    "payload_id", "payload_key", "symbol", "broker_symbol", "direction",
    "signal_close_time", "entry_time", "entry_price", "sl_price", "tp_price", "rr",
    "pair_name", "candidate_name", "candidate_rank", "selected_slice", "reason_text",
    "caution_labels", "mode_spread_price", "mode_spread_points", "spread_to_sl_ratio",
    "effective_rr_after_spread", "strategy_id", "strategy_slot",
]


def utc_now_text() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")


def timestamp_text(value: Any) -> str:
    if value in (None, "") or pd.isna(value):
        return ""
    return pd.Timestamp(value).strftime("%Y-%m-%d %H:%M:%S")


def read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True, default=str), encoding="utf-8")


def read_csv_flexible(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path, encoding="utf-8-sig", sep=None, engine="python")
    except Exception:
        return pd.read_csv(path, encoding="utf-8-sig")


def write_csv(frame: pd.DataFrame, path: Path, columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    output = frame.copy()
    for column in columns:
        if column not in output.columns:
            output[column] = ""
    output[columns].to_csv(path, index=False, encoding="utf-8-sig")


def append_csv_rows(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    frame = pd.DataFrame(rows)
    for column in columns:
        if column not in frame.columns:
            frame[column] = ""
    frame[columns].to_csv(path, mode="a", header=not path.exists(), index=False, encoding="utf-8-sig")


def normalize_m5(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        raise ValueError("M5 CSV is empty")
    frame = frame.copy()
    frame.columns = [str(column).strip().lower() for column in frame.columns]
    required = {"time", "open", "high", "low", "close"}
    missing = sorted(required.difference(frame.columns))
    if missing:
        raise ValueError(f"M5 CSV missing columns: {missing}")
    frame["time"] = pd.to_datetime(frame["time"], errors="raise")
    for column in ["open", "high", "low", "close"]:
        frame[column] = pd.to_numeric(frame[column], errors="raise")
    return frame.sort_values("time").drop_duplicates("time", keep="last").reset_index(drop=True)


def effective_prices(direction: str, entry_bid: float, chart_price: float, spread_usd: float) -> tuple[float, float]:
    direction = direction.upper()
    if direction == "LONG":
        return entry_bid + spread_usd, chart_price
    if direction == "SHORT":
        return entry_bid, chart_price + spread_usd
    raise ValueError(f"invalid direction: {direction}")


def pnl_price_for_chart_exit(direction: str, entry_bid: float, exit_chart_price: float, spread_usd: float) -> float:
    open_effective, close_effective = effective_prices(direction, entry_bid, exit_chart_price, spread_usd)
    return close_effective - open_effective if direction.upper() == "LONG" else open_effective - close_effective


def bar_excursions(direction: str, entry_bid: float, high: float, low: float, spread_usd: float) -> tuple[float, float]:
    direction = direction.upper()
    if direction == "LONG":
        best = high - (entry_bid + spread_usd)
        worst = low - (entry_bid + spread_usd)
    elif direction == "SHORT":
        best = entry_bid - (low + spread_usd)
        worst = entry_bid - (high + spread_usd)
    else:
        raise ValueError(f"invalid direction: {direction}")
    return best / PIP_USD, worst / PIP_USD


def exit_hit(direction: str, high: float, low: float, sl: float, tp: float) -> tuple[str, float] | None:
    direction = direction.upper()
    stop_hit = low <= sl if direction == "LONG" else high >= sl
    target_hit = high >= tp if direction == "LONG" else low <= tp
    if stop_hit:
        return "SL", sl
    if target_hit:
        return "TP", tp
    return None


def make_event(trade: dict[str, Any], event_type: str, market_time: Any) -> dict[str, Any]:
    event_id = f"{trade['signal_key']}::{event_type}::{timestamp_text(market_time).replace(' ', 'T')}"
    return {
        "event_id": event_id,
        "event_recorded_at_utc": utc_now_text(),
        "market_time": timestamp_text(market_time),
        "event_type": event_type,
        "signal_key": trade["signal_key"],
        "status": trade["status"],
        "direction": trade["direction"],
        "lot": trade["lot"],
        "actual_entry_bid": trade.get("actual_entry_bid", ""),
        "sl_price": trade["sl_price"],
        "tp_price": trade["tp_price"],
        "exit_reason": trade.get("exit_reason", ""),
        "pnl_pips": trade.get("pnl_pips", ""),
        "r_multiple": trade.get("r_multiple", ""),
        "mfe_pips": trade.get("mfe_pips", ""),
        "mae_pips": trade.get("mae_pips", ""),
        "pnl_account_currency": trade.get("pnl_account_currency", ""),
        "account_currency": trade.get("account_currency", ""),
    }


def process_trade(trade: dict[str, Any], m5: pd.DataFrame, spread_usd: float) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    events: list[dict[str, Any]] = []
    status = str(trade.get("status", "PENDING_ENTRY"))
    planned_time = pd.Timestamp(trade["planned_entry_time"])

    if status == "PENDING_ENTRY":
        eligible = m5[m5["time"] >= planned_time]
        if eligible.empty:
            return trade, events
        entry_row = eligible.iloc[0]
        entry_bid = float(entry_row["open"])
        direction = str(trade["direction"]).upper()
        sl = float(trade["sl_price"])
        tp = float(trade["tp_price"])
        open_effective, stop_effective = effective_prices(direction, entry_bid, sl, spread_usd)
        _, target_effective = effective_prices(direction, entry_bid, tp, spread_usd)
        risk = open_effective - stop_effective if direction == "LONG" else stop_effective - open_effective
        reward = target_effective - open_effective if direction == "LONG" else open_effective - target_effective
        if risk <= 0 or reward <= 0:
            trade.update({
                "status": "REJECTED_INVALID_LIVE_PRICES",
                "actual_entry_time": timestamp_text(entry_row["time"]),
                "actual_entry_bid": entry_bid,
                "closed_at_utc": utc_now_text(),
                "exit_reason": "INVALID_LIVE_PRICES",
            })
            events.append(make_event(trade, "REJECTED", entry_row["time"]))
            return trade, events
        trade.update({
            "status": "OPEN",
            "actual_entry_time": timestamp_text(entry_row["time"]),
            "entry_bar_time": timestamp_text(entry_row["time"]),
            "actual_entry_bid": entry_bid,
            "effective_entry_price": open_effective,
            "effective_risk_usd": risk,
            "effective_reward_usd": reward,
            "effective_rr": reward / risk,
            "mfe_pips": 0.0,
            "mae_pips": 0.0,
            "opened_at_utc": utc_now_text(),
            "last_processed_m5_time": "",
        })
        events.append(make_event(trade, "SHADOW_OPEN", entry_row["time"]))
        status = "OPEN"

    if status != "OPEN":
        return trade, events

    entry_bar_time = pd.Timestamp(trade["entry_bar_time"])
    last_processed = trade.get("last_processed_m5_time", "")
    bars = m5[m5["time"] >= entry_bar_time]
    if last_processed:
        bars = bars[bars["time"] > pd.Timestamp(last_processed)]
    direction = str(trade["direction"]).upper()
    entry_bid = float(trade["actual_entry_bid"])
    sl = float(trade["sl_price"])
    tp = float(trade["tp_price"])
    risk = float(trade["effective_risk_usd"])
    mfe = float(trade.get("mfe_pips", 0.0) or 0.0)
    mae = float(trade.get("mae_pips", 0.0) or 0.0)

    for _, bar in bars.iterrows():
        high = float(bar["high"])
        low = float(bar["low"])
        best, worst = bar_excursions(direction, entry_bid, high, low, spread_usd)
        mfe = max(mfe, best)
        mae = min(mae, worst)
        trade["mfe_pips"] = mfe
        trade["mae_pips"] = mae
        trade["last_processed_m5_time"] = timestamp_text(bar["time"])
        hit = exit_hit(direction, high, low, sl, tp)
        if hit is not None:
            reason, chart_price = hit
            pnl_price = pnl_price_for_chart_exit(direction, entry_bid, chart_price, spread_usd)
            pnl_pips = pnl_price / PIP_USD
            exit_time = pd.Timestamp(bar["time"]) + pd.Timedelta(minutes=5)
            trade.update({
                "status": "CLOSED",
                "exit_time": timestamp_text(exit_time),
                "exit_reason": reason,
                "exit_chart_price": chart_price,
                "pnl_pips": pnl_pips,
                "r_multiple": pnl_price / risk,
                "unrealized_pips": 0.0,
                "unrealized_r": 0.0,
                "latest_mark_time": timestamp_text(exit_time),
                "latest_mark_bid": chart_price,
                "closed_at_utc": utc_now_text(),
            })
            events.append(make_event(trade, f"SHADOW_CLOSED_{reason}", exit_time))
            return trade, events

    latest = m5.iloc[-1]
    mark_price = float(latest["close"])
    unrealized_price = pnl_price_for_chart_exit(direction, entry_bid, mark_price, spread_usd)
    trade.update({
        "latest_mark_time": timestamp_text(pd.Timestamp(latest["time"]) + pd.Timedelta(minutes=5)),
        "latest_mark_bid": mark_price,
        "unrealized_pips": unrealized_price / PIP_USD,
        "unrealized_r": unrealized_price / risk,
    })
    return trade, events


def register_candidates(existing: dict[str, dict[str, Any]], candidates: pd.DataFrame, lot: float) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    events: list[dict[str, Any]] = []
    if candidates.empty:
        return existing, events
    for _, row in candidates.iterrows():
        candidate_id = str(row.get("strategy_id", row.get("candidate_name", "")))
        if candidate_id != BTC6_ID:
            continue
        signal_key = str(row["signal_key"])
        if signal_key in existing:
            continue
        trade = {
            "signal_key": signal_key,
            "candidate_id": BTC6_ID,
            "status": "PENDING_ENTRY",
            "direction": str(row["direction"]).upper(),
            "lot": float(lot),
            "signal_close_time": timestamp_text(row.get("signal_close_time", row["entry_time"])),
            "planned_entry_time": timestamp_text(row["entry_time"]),
            "actual_entry_time": "",
            "entry_bar_time": "",
            "reference_entry_bid": float(row["entry_price_reference"]),
            "actual_entry_bid": "",
            "effective_entry_price": "",
            "sl_price": float(row["sl_price"]),
            "tp_price": float(row["tp_price"]),
            "planned_rr": float(row.get("rr", 0.0) or 0.0),
            "effective_risk_usd": "",
            "effective_reward_usd": "",
            "effective_rr": "",
            "last_processed_m5_time": "",
            "latest_mark_time": "",
            "latest_mark_bid": "",
            "unrealized_pips": 0.0,
            "unrealized_r": 0.0,
            "mfe_pips": 0.0,
            "mae_pips": 0.0,
            "exit_time": "",
            "exit_reason": "",
            "exit_chart_price": "",
            "pnl_pips": "",
            "r_multiple": "",
            "pnl_account_currency": "",
            "unrealized_account_currency": "",
            "account_currency": "",
            "registered_at_utc": utc_now_text(),
            "opened_at_utc": "",
            "closed_at_utc": "",
        }
        existing[signal_key] = trade
        events.append(make_event(trade, "SIGNAL_REGISTERED", trade["planned_entry_time"]))
    return existing, events


def max_drawdown(values: list[float]) -> float:
    equity = 0.0
    peak = 0.0
    drawdown = 0.0
    for value in values:
        equity += value
        peak = max(peak, equity)
        drawdown = max(drawdown, peak - equity)
    return drawdown


def summarize(trades: list[dict[str, Any]]) -> dict[str, Any]:
    closed = [trade for trade in trades if trade.get("status") == "CLOSED"]
    closed.sort(key=lambda trade: str(trade.get("exit_time", "")))
    open_trades = [trade for trade in trades if trade.get("status") == "OPEN"]
    pnl = [float(trade.get("pnl_pips", 0.0) or 0.0) for trade in closed]
    multiples = [float(trade.get("r_multiple", 0.0) or 0.0) for trade in closed]
    gross_profit = sum(value for value in pnl if value > 0)
    gross_loss = -sum(value for value in pnl if value < 0)
    return {
        "registered_trades": len(trades),
        "pending_trades": sum(1 for trade in trades if trade.get("status") == "PENDING_ENTRY"),
        "open_trades": len(open_trades),
        "closed_trades": len(closed),
        "wins": sum(1 for value in pnl if value > 0),
        "losses": sum(1 for value in pnl if value < 0),
        "win_rate_pct": (100.0 * sum(1 for value in pnl if value > 0) / len(pnl)) if pnl else None,
        "profit_factor": gross_profit / gross_loss if gross_loss > 0 else None,
        "total_pips": sum(pnl),
        "total_r": sum(multiples),
        "max_drawdown_r": max_drawdown(multiples),
        "open_unrealized_pips": sum(float(trade.get("unrealized_pips", 0.0) or 0.0) for trade in open_trades),
        "open_unrealized_r": sum(float(trade.get("unrealized_r", 0.0) or 0.0) for trade in open_trades),
        "closed_account_pnl": sum(float(trade.get("pnl_account_currency", 0.0) or 0.0) for trade in closed),
        "open_unrealized_account_pnl": sum(float(trade.get("unrealized_account_currency", 0.0) or 0.0) for trade in open_trades),
    }


def event_to_discord(event: dict[str, Any], trade: dict[str, Any], spread_usd: float) -> dict[str, Any]:
    event_type = str(event["event_type"])
    if event_type == "SHADOW_OPEN":
        reason = (
            f"BTC6 SHADOW OPEN | virtual lot {trade['lot']:.2f} | effective RR {float(trade['effective_rr']):.3f} | "
            "no broker order"
        )
        selected_slice = "SHADOW_OPEN"
    elif event_type.startswith("SHADOW_CLOSED"):
        account_text = ""
        if trade.get("pnl_account_currency") not in (None, ""):
            account_text = f" | account P/L {float(trade['pnl_account_currency']):.2f} {trade.get('account_currency', '')}"
        reason = (
            f"BTC6 SHADOW {trade['exit_reason']} | virtual lot {trade['lot']:.2f} | "
            f"P/L {float(trade['pnl_pips']):.2f} pips / {float(trade['r_multiple']):.3f}R | "
            f"MFE {float(trade['mfe_pips']):.2f} / MAE {float(trade['mae_pips']):.2f} pips{account_text}"
        )
        selected_slice = "SHADOW_CLOSED"
    else:
        reason = f"BTC6 SHADOW event: {event_type}"
        selected_slice = "SHADOW_EVENT"
    entry = float(trade.get("actual_entry_bid") or trade.get("reference_entry_bid") or 0.0)
    sl = float(trade["sl_price"])
    tp = float(trade["tp_price"])
    sl_dist = abs(entry - sl)
    return {
        "payload_id": event["event_id"],
        "payload_key": event["event_id"],
        "symbol": "BTC",
        "broker_symbol": "BTCUSD#",
        "direction": trade["direction"],
        "signal_close_time": trade["signal_close_time"],
        "entry_time": event["market_time"],
        "entry_price": entry,
        "sl_price": sl,
        "tp_price": tp,
        "rr": trade.get("effective_rr") or trade.get("planned_rr") or 0.0,
        "pair_name": "BTC6_SHADOW_LIVE",
        "candidate_name": BTC6_ID,
        "candidate_rank": "YOUTUBE_SHADOW",
        "selected_slice": selected_slice,
        "reason_text": reason,
        "caution_labels": "SHADOW_LIVE_NO_BROKER_ORDER",
        "mode_spread_price": spread_usd,
        "mode_spread_points": spread_usd,
        "spread_to_sl_ratio": spread_usd / sl_dist if sl_dist > 0 else 0.0,
        "effective_rr_after_spread": trade.get("effective_rr") or 0.0,
        "strategy_id": BTC6_ID,
        "strategy_slot": "BTC6_SHADOW_LIVE",
    }


def enrich_account_values(trades: list[dict[str, Any]], broker_symbol: str, spread_usd: float) -> dict[str, Any]:
    result = {"available": False, "account_currency": "", "error": ""}
    try:
        import MetaTrader5 as mt5  # type: ignore
        if not mt5.initialize():
            result["error"] = f"MT5 initialize failed: {mt5.last_error()}"
            return result
        account = mt5.account_info()
        result["account_currency"] = str(getattr(account, "currency", "") or "") if account is not None else ""
        if not mt5.symbol_select(broker_symbol, True):
            result["error"] = f"symbol_select failed: {broker_symbol}"
            mt5.shutdown()
            return result
        for trade in trades:
            if trade.get("status") not in {"OPEN", "CLOSED"}:
                continue
            direction = str(trade["direction"]).upper()
            order_type = mt5.ORDER_TYPE_BUY if direction == "LONG" else mt5.ORDER_TYPE_SELL
            entry_bid = float(trade["actual_entry_bid"])
            open_effective, _ = effective_prices(direction, entry_bid, entry_bid, spread_usd)
            if trade.get("status") == "CLOSED":
                chart_exit = float(trade["exit_chart_price"])
                _, close_effective = effective_prices(direction, entry_bid, chart_exit, spread_usd)
                value = mt5.order_calc_profit(order_type, broker_symbol, float(trade["lot"]), open_effective, close_effective)
                trade["pnl_account_currency"] = "" if value is None else float(value)
                trade["unrealized_account_currency"] = 0.0
            else:
                chart_mark = float(trade["latest_mark_bid"])
                _, close_effective = effective_prices(direction, entry_bid, chart_mark, spread_usd)
                value = mt5.order_calc_profit(order_type, broker_symbol, float(trade["lot"]), open_effective, close_effective)
                trade["unrealized_account_currency"] = "" if value is None else float(value)
            trade["account_currency"] = result["account_currency"]
        result["available"] = True
        mt5.shutdown()
    except Exception as exc:
        result["error"] = repr(exc)
    return result


def run(args: argparse.Namespace) -> dict[str, Any]:
    args.out_dir.mkdir(parents=True, exist_ok=True)
    m5 = normalize_m5(read_csv_flexible(args.m5_csv))
    candidates = read_csv_flexible(args.candidates_csv)
    state = read_json(args.state_json, {"schema_version": "btc6_shadow_state_v1", "trades": {}})
    trades_by_key = state.get("trades", {}) if isinstance(state.get("trades"), dict) else {}
    trades_by_key, new_events = register_candidates(trades_by_key, candidates, args.lot)
    all_new_events = list(new_events)
    for signal_key in sorted(trades_by_key):
        trade, events = process_trade(trades_by_key[signal_key], m5, args.spread_usd)
        trades_by_key[signal_key] = trade
        all_new_events.extend(events)

    trades = list(trades_by_key.values())
    mt5_valuation = enrich_account_values(trades, args.broker_symbol, args.spread_usd)

    existing_event_ids: set[str] = set()
    if args.events_ledger_csv.exists():
        existing = read_csv_flexible(args.events_ledger_csv)
        if "event_id" in existing.columns:
            existing_event_ids = set(existing["event_id"].astype(str))
    unique_events = [event for event in all_new_events if event["event_id"] not in existing_event_ids]
    for event in unique_events:
        trade = trades_by_key[event["signal_key"]]
        event["pnl_account_currency"] = trade.get("pnl_account_currency", "")
        event["account_currency"] = trade.get("account_currency", "")
    append_csv_rows(args.events_ledger_csv, unique_events, EVENT_COLUMNS)

    trades.sort(key=lambda trade: (str(trade.get("planned_entry_time", "")), str(trade.get("signal_key", ""))))
    write_csv(pd.DataFrame(trades), args.trades_ledger_csv, TRADE_COLUMNS)
    write_csv(pd.DataFrame(trades), args.out_dir / "btc6_shadow_trade_snapshot.csv", TRADE_COLUMNS)

    discord_rows = []
    for event in unique_events:
        if event["event_type"] in {"REJECTED", "SIGNAL_REGISTERED"}:
            continue
        trade = trades_by_key[event["signal_key"]]
        discord_rows.append(event_to_discord(event, trade, args.spread_usd))
    write_csv(pd.DataFrame(discord_rows), args.out_dir / "btc6_shadow_discord_events.csv", DISCORD_COLUMNS)

    state = {
        "schema_version": "btc6_shadow_state_v1",
        "updated_at_utc": utc_now_text(),
        "lot": args.lot,
        "spread_usd": args.spread_usd,
        "same_bar_priority": "SL_FIRST",
        "trades": trades_by_key,
    }
    write_json(args.state_json, state)
    metrics = summarize(trades)
    summary = {
        "schema_version": "btc6_shadow_manager_v1",
        "cycle_at_utc": utc_now_text(),
        "cycle_ok": True,
        "candidate_id": BTC6_ID,
        "mode": "SHADOW_LIVE_NO_BROKER_ORDER",
        "lot": args.lot,
        "spread_usd": args.spread_usd,
        "latest_closed_m5_open_time": timestamp_text(m5.iloc[-1]["time"]),
        "new_events": len(unique_events),
        "new_event_types": [event["event_type"] for event in unique_events],
        "discord_event_rows": len(discord_rows),
        "metrics": metrics,
        "mt5_valuation": mt5_valuation,
        "paths": {
            "state_json": str(args.state_json),
            "events_ledger_csv": str(args.events_ledger_csv),
            "trades_ledger_csv": str(args.trades_ledger_csv),
            "snapshot_csv": str(args.out_dir / "btc6_shadow_trade_snapshot.csv"),
            "discord_events_csv": str(args.out_dir / "btc6_shadow_discord_events.csv"),
        },
    }
    write_json(args.out_dir / "latest_btc6_shadow_manager_result.json", summary)
    return summary


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Track BTC6 as a persistent shadow-live position using closed M5 bars.")
    parser.add_argument("--candidates-csv", type=Path, required=True)
    parser.add_argument("--m5-csv", type=Path, required=True)
    parser.add_argument("--state-json", type=Path, required=True)
    parser.add_argument("--events-ledger-csv", type=Path, required=True)
    parser.add_argument("--trades-ledger-csv", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--lot", type=float, default=DEFAULT_LOT)
    parser.add_argument("--spread-usd", type=float, default=DEFAULT_SPREAD_USD)
    parser.add_argument("--broker-symbol", default="BTCUSD#")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        summary = run(args)
    except Exception as exc:
        summary = {
            "schema_version": "btc6_shadow_manager_v1",
            "cycle_at_utc": utc_now_text(),
            "cycle_ok": False,
            "error": repr(exc),
        }
        args.out_dir.mkdir(parents=True, exist_ok=True)
        write_json(args.out_dir / "latest_btc6_shadow_manager_result.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True, default=str))
    return 0 if summary.get("cycle_ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
