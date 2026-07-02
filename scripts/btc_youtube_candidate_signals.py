from __future__ import annotations

import importlib.util
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
RESEARCH_DIR = REPO_ROOT / "scripts" / "btc_ml_v1" / "research"

BROKER_SYMBOL = "BTCUSD#"
SYMBOL = "BTC"
SPREAD_USD = 30.0
PIP_USD = 10.0

BTC4_ID = "BTC4_RISK_CAP_400"
BTC5_ID = "BTC5_TWO_PIVOT_P2_CLEAN_N_382_786"
BTC6_ID = "BTC6_M15_TWO_PIVOT_P3_BROAD_N_236_886"

BTC4_TOTAL_LOT = 0.02
BTC4_LEG_LOT = 0.01
BTC5_LOT = 0.01
BTC6_LOT = 0.0

BTC4_TP1_MAGIC = 26070441
BTC4_TP2_MAGIC = 26070442
BTC5_MAGIC = 26070501

NOTIFICATION_COLUMNS = [
    "payload_key", "signal_key", "broker_symbol", "symbol", "direction",
    "lot", "entry_price_reference", "sl_price", "tp_price", "strategy_slot",
    "strategy_id", "candidate_name", "candidate_rank", "selected_slice",
    "entry_time", "signal_close_time", "rr", "spread_cost_usd", "reason_text",
    "caution_labels", "trade_enabled", "tp1_price", "tp2_price",
]

ORDER_COLUMNS = [
    "payload_key", "order_key", "signal_key", "broker_symbol", "symbol",
    "direction", "lot", "entry_price_reference", "sl_price", "tp_price",
    "magic_number", "strategy_key", "strategy_alias", "strategy_id",
    "condition_id", "router_strategy_slot", "router_strategy_id",
    "candidate_rank", "source", "entry_time", "rr", "horizon_hours",
    "spread_cost_usd", "order_role", "parent_signal_key",
]


@dataclass(frozen=True)
class DetectionResult:
    notification_candidates: pd.DataFrame
    order_payloads: pd.DataFrame
    latest_closed: dict[str, str]
    synthetic_entry_times: dict[str, str]
    counts: dict[str, int]


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _read_raw_ohlc(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    try:
        frame = pd.read_csv(path, sep=None, engine="python")
    except Exception:
        frame = pd.read_csv(path)
    frame.columns = [str(c).strip().lower() for c in frame.columns]
    required = {"time", "open", "high", "low", "close"}
    missing = sorted(required.difference(frame.columns))
    if missing:
        raise ValueError(f"{path}: missing columns {missing}")
    frame["time"] = pd.to_datetime(frame["time"], errors="raise")
    for column in ["open", "high", "low", "close"]:
        frame[column] = pd.to_numeric(frame[column], errors="raise")
    for column in ["tick_volume", "spread", "real_volume"]:
        if column not in frame.columns:
            frame[column] = 0
        frame[column] = pd.to_numeric(frame[column], errors="coerce").fillna(0)
    frame = frame.sort_values("time").drop_duplicates("time", keep="last").reset_index(drop=True)
    if frame.empty:
        raise ValueError(f"{path}: empty")
    return frame


def append_synthetic_entry_row(frame: pd.DataFrame, timeframe_minutes: int) -> tuple[pd.DataFrame, pd.Timestamp]:
    if timeframe_minutes <= 0:
        raise ValueError("timeframe_minutes must be positive")
    output = frame.copy()
    latest = pd.Timestamp(output.iloc[-1]["time"])
    synthetic_time = latest + pd.Timedelta(minutes=int(timeframe_minutes))
    if (output["time"] == synthetic_time).any():
        raise ValueError(f"synthetic entry time already exists: {synthetic_time}")
    last = output.iloc[-1].to_dict()
    close = float(last["close"])
    last.update({"time": synthetic_time, "open": close, "high": close, "low": close, "close": close})
    output = pd.concat([output, pd.DataFrame([last])], ignore_index=True)
    return output, synthetic_time


def _prepare_nwave_frame(raw: pd.DataFrame, engine: Any) -> pd.DataFrame:
    frame = raw.copy().sort_values("time").drop_duplicates("time").reset_index(drop=True)
    frame["ema20"] = engine.mt5_ema(frame["close"], 20)
    frame["ema200"] = engine.mt5_ema(frame["close"], 200)
    frame["atr14"] = engine.mt5_atr(frame["high"], frame["low"], frame["close"], 14)
    difference = frame["ema20"] - frame["ema200"]
    frame["raw_sign"] = np.where(difference > 0, 1, np.where(difference < 0, -1, 0))
    frame["sep_atr"] = difference.abs() / frame["atr14"]
    frame["touch200"] = (frame["low"] <= frame["ema200"]) & (frame["high"] >= frame["ema200"])
    return frame


def _timestamp_text(value: Any) -> str:
    return pd.Timestamp(value).strftime("%Y-%m-%d %H:%M:%S")


def _signal_key(candidate_id: str, direction: str, entry_time: Any) -> str:
    stamp = pd.Timestamp(entry_time).strftime("%Y%m%d_%H%M")
    return f"{candidate_id}_{direction}_{stamp}"


def _notification_row(
    *, candidate_id: str, direction: str, entry_time: Any, entry: float,
    stop: float, target: float, rr: float, lot: float, reason: str,
    trade_enabled: bool, tp1: float | None = None, tp2: float | None = None,
) -> dict[str, Any]:
    signal_key = _signal_key(candidate_id, direction, entry_time)
    signal_close_time = pd.Timestamp(entry_time) - pd.Timedelta(minutes=5 if candidate_id == BTC5_ID else 15 if candidate_id == BTC6_ID else 0)
    return {
        "payload_key": signal_key,
        "signal_key": signal_key,
        "broker_symbol": BROKER_SYMBOL,
        "symbol": SYMBOL,
        "direction": direction,
        "lot": lot,
        "entry_price_reference": entry,
        "sl_price": stop,
        "tp_price": target,
        "strategy_slot": candidate_id,
        "strategy_id": candidate_id,
        "candidate_name": candidate_id,
        "candidate_rank": "YOUTUBE",
        "selected_slice": "DEMO_FORWARD",
        "entry_time": _timestamp_text(entry_time),
        "signal_close_time": _timestamp_text(signal_close_time),
        "rr": rr,
        "spread_cost_usd": SPREAD_USD,
        "reason_text": reason,
        "caution_labels": "DEMO_ONLY" if trade_enabled else "MONITOR_ONLY_NO_ORDER",
        "trade_enabled": bool(trade_enabled),
        "tp1_price": "" if tp1 is None else tp1,
        "tp2_price": "" if tp2 is None else tp2,
    }


def _order_row(
    notification: dict[str, Any], *, role: str, lot: float, tp: float, magic: int,
) -> dict[str, Any]:
    parent = str(notification["signal_key"])
    payload_key = f"{parent}_{role}"
    return {
        "payload_key": payload_key,
        "order_key": payload_key,
        "signal_key": parent,
        "broker_symbol": notification["broker_symbol"],
        "symbol": notification["symbol"],
        "direction": notification["direction"],
        "lot": float(lot),
        "entry_price_reference": float(notification["entry_price_reference"]),
        "sl_price": float(notification["sl_price"]),
        "tp_price": float(tp),
        "magic_number": int(magic),
        "strategy_key": notification["strategy_slot"],
        "strategy_alias": notification["strategy_slot"],
        "strategy_id": notification["strategy_id"],
        "condition_id": notification["strategy_id"],
        "router_strategy_slot": notification["strategy_slot"],
        "router_strategy_id": notification["strategy_id"],
        "candidate_rank": "YOUTUBE",
        "source": "btc_youtube_candidate_signals",
        "entry_time": notification["entry_time"],
        "rr": float(notification["rr"]),
        "horizon_hours": 0,
        "spread_cost_usd": SPREAD_USD,
        "order_role": role,
        "parent_signal_key": parent,
    }


def _detect_btc5_or_btc6(raw: pd.DataFrame, *, candidate_id: str, timeframe_minutes: int) -> tuple[list[dict[str, Any]], list[dict[str, Any]], pd.Timestamp]:
    module_name = f"_btc_youtube_{candidate_id.lower()}"
    engine = _load_module(module_name, RESEARCH_DIR / "btc5_video_5m_ema200_nwave_candidate.py")
    if candidate_id == BTC6_ID:
        engine.AB_LOOKBACK_BARS = 96
        engine.N_RETRACE_MIN = 0.236
        engine.N_RETRACE_MAX = 0.886
        original_detect = engine.detect_pivots
        engine.detect_pivots = lambda frame: original_detect(frame, width=3)
    augmented, synthetic_time = append_synthetic_entry_row(raw, timeframe_minutes)
    frame = _prepare_nwave_frame(augmented, engine)
    plans = engine.generate_plans(frame)
    if plans.empty:
        return [], [], synthetic_time
    current = plans[pd.to_datetime(plans["entry_time"]) == synthetic_time].copy()
    notifications: list[dict[str, Any]] = []
    orders: list[dict[str, Any]] = []
    for _, plan in current.iterrows():
        direction = str(plan["direction"])
        entry = float(plan["entry_bid"])
        stop = float(plan["stop_chart"])
        target = float(plan["target_chart"])
        rr = float(plan["rr"])
        trade_enabled = candidate_id == BTC5_ID
        lot = BTC5_LOT if trade_enabled else BTC6_LOT
        notification = _notification_row(
            candidate_id=candidate_id,
            direction=direction,
            entry_time=synthetic_time,
            entry=entry,
            stop=stop,
            target=target,
            rr=rr,
            lot=lot,
            reason=(
                "YouTube M5 EMA200 touch / two-pivot N-wave breakout"
                if candidate_id == BTC5_ID
                else "YouTube M15 EMA200 touch / two-pivot N-wave breakout (monitor only)"
            ),
            trade_enabled=trade_enabled,
        )
        notifications.append(notification)
        if trade_enabled:
            orders.append(_order_row(notification, role="FULL", lot=BTC5_LOT, tp=target, magic=BTC5_MAGIC))
    return notifications, orders, synthetic_time


def _detect_btc4(h4_raw: pd.DataFrame, m5_raw: pd.DataFrame) -> tuple[list[dict[str, Any]], list[dict[str, Any]], pd.Timestamp]:
    engine = _load_module("_btc_youtube_btc4_engine", RESEARCH_DIR / "btc3_video_ema_method_exploration.py")
    m5_augmented, synthetic_time = append_synthetic_entry_row(m5_raw, 5)
    h4 = engine._add_h4_features(h4_raw.copy())
    m5 = m5_augmented.copy()
    m5_lookup = {pd.Timestamp(value): idx for idx, value in enumerate(m5["time"])}
    setups = engine._generate_setups(h4, invalidate_on_wick=False)
    pivot_highs, pivot_lows = engine._causal_pivots(h4, 3, 3)
    notifications: list[dict[str, Any]] = []
    orders: list[dict[str, Any]] = []
    for setup in setups:
        plan = engine._build_plan(
            h4, m5, m5_lookup, setup, spread_usd=SPREAD_USD,
            pivot_highs=pivot_highs, pivot_lows=pivot_lows, lookback_bars=500,
        )
        if plan is None or pd.Timestamp(plan["decision_time"]) != synthetic_time:
            continue
        if float(plan["risk_pips"]) > 400.0:
            continue
        direction = str(plan["direction"])
        entry = float(plan["entry_bid"])
        stop = float(plan["stop_chart"])
        tp1 = float(plan["tp1"])
        tp2 = float(plan["tp2"])
        rr = float((0.5 * plan["tp1_net_usd"] + 0.5 * plan["tp2_net_usd"]) / plan["risk_net_usd"])
        notification = _notification_row(
            candidate_id=BTC4_ID,
            direction=direction,
            entry_time=synthetic_time,
            entry=entry,
            stop=stop,
            target=tp2,
            rr=rr,
            lot=BTC4_TOTAL_LOT,
            reason="YouTube H4 EMA20/EMA200 touch breakout; split TP1/TP2, TP2 moves to BE after profitable TP1",
            trade_enabled=True,
            tp1=tp1,
            tp2=tp2,
        )
        notifications.append(notification)
        orders.extend([
            _order_row(notification, role="TP1", lot=BTC4_LEG_LOT, tp=tp1, magic=BTC4_TP1_MAGIC),
            _order_row(notification, role="TP2", lot=BTC4_LEG_LOT, tp=tp2, magic=BTC4_TP2_MAGIC),
        ])
    return notifications, orders, synthetic_time


def detect_youtube_candidates(*, m5_csv: Path, m15_csv: Path, h4_csv: Path) -> DetectionResult:
    m5_raw = _read_raw_ohlc(m5_csv)
    m15_raw = _read_raw_ohlc(m15_csv)
    h4_raw = _read_raw_ohlc(h4_csv)

    n4, o4, s4 = _detect_btc4(h4_raw, m5_raw)
    n5, o5, s5 = _detect_btc5_or_btc6(m5_raw, candidate_id=BTC5_ID, timeframe_minutes=5)
    n6, o6, s6 = _detect_btc5_or_btc6(m15_raw, candidate_id=BTC6_ID, timeframe_minutes=15)

    notification_df = pd.DataFrame(n4 + n5 + n6, columns=NOTIFICATION_COLUMNS)
    order_df = pd.DataFrame(o4 + o5 + o6, columns=ORDER_COLUMNS)
    if not notification_df.empty:
        notification_df = notification_df.sort_values(["entry_time", "strategy_slot", "direction"]).reset_index(drop=True)
    if not order_df.empty:
        order_df = order_df.sort_values(["entry_time", "strategy_key", "order_role"]).reset_index(drop=True)
    return DetectionResult(
        notification_candidates=notification_df,
        order_payloads=order_df,
        latest_closed={
            "m5": _timestamp_text(m5_raw.iloc[-1]["time"]),
            "m15": _timestamp_text(m15_raw.iloc[-1]["time"]),
            "h4": _timestamp_text(h4_raw.iloc[-1]["time"]),
        },
        synthetic_entry_times={"btc4": _timestamp_text(s4), "btc5": _timestamp_text(s5), "btc6": _timestamp_text(s6)},
        counts={BTC4_ID: len(n4), BTC5_ID: len(n5), BTC6_ID: len(n6)},
    )


def validate_order_group(order_payloads: pd.DataFrame) -> list[str]:
    errors: list[str] = []
    if order_payloads.empty:
        return errors
    unknown = sorted(set(order_payloads["strategy_id"].astype(str)) - {BTC4_ID, BTC5_ID})
    if unknown:
        errors.append(f"order payload contains non-trade candidates: {unknown}")
    for signal_key, group in order_payloads.groupby("parent_signal_key", sort=False):
        candidate = str(group.iloc[0]["strategy_id"])
        if candidate == BTC4_ID:
            roles = sorted(group["order_role"].astype(str).tolist())
            lots = sorted(round(float(v), 8) for v in group["lot"])
            magics = sorted(int(v) for v in group["magic_number"])
            if len(group) != 2 or roles != ["TP1", "TP2"]:
                errors.append(f"{signal_key}: BTC4 must have TP1 and TP2 rows")
            if lots != [BTC4_LEG_LOT, BTC4_LEG_LOT]:
                errors.append(f"{signal_key}: BTC4 lots must be 0.01 + 0.01")
            if magics != sorted([BTC4_TP1_MAGIC, BTC4_TP2_MAGIC]):
                errors.append(f"{signal_key}: BTC4 magic contract mismatch")
            if group["sl_price"].nunique(dropna=False) != 1:
                errors.append(f"{signal_key}: BTC4 split legs must share SL")
        elif candidate == BTC5_ID:
            if len(group) != 1 or str(group.iloc[0]["order_role"]) != "FULL":
                errors.append(f"{signal_key}: BTC5 must have exactly one FULL row")
            if abs(float(group.iloc[0]["lot"]) - BTC5_LOT) > 1e-9:
                errors.append(f"{signal_key}: BTC5 lot must be 0.01")
            if int(group.iloc[0]["magic_number"]) != BTC5_MAGIC:
                errors.append(f"{signal_key}: BTC5 magic contract mismatch")
    if len(order_payloads) > 3:
        errors.append("maximum three order rows per cycle exceeded")
    return errors
