from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from gold_regime_guard import evaluate_from_history_csv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT_DIR = PROJECT_ROOT / "data" / "results" / "live_payloads"
DEFAULT_HISTORY_CSV = PROJECT_ROOT / "data" / "results" / "gold_btc_final_portfolio_trades.csv"

MACD_FAST = 6
MACD_SLOW = 13
MACD_SIGNAL = 4


def resolve_path(path: Path) -> Path:
    return path if path.is_absolute() else PROJECT_ROOT / path


def read_ohlc(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    df = pd.read_csv(path).copy()
    required = ["time", "open", "high", "low", "close"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns in {path}: {missing}")
    df["time"] = pd.to_datetime(df["time"], format="%Y.%m.%d %H:%M", errors="coerce")
    if df["time"].isna().mean() > 0.5:
        df["time"] = pd.to_datetime(df["time"], errors="coerce")
    df = df.dropna(subset=["time"]).sort_values("time", kind="mergesort").reset_index(drop=True)
    for col in ["open", "high", "low", "close", "volume", "spread"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    if "spread" not in df.columns:
        df["spread"] = 0.0
    return df


def rsi_series(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / period, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / period, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def stoch_k(close: pd.Series, high: pd.Series, low: pd.Series, period: int = 14) -> pd.Series:
    lowest = low.rolling(period, min_periods=period).min()
    highest = high.rolling(period, min_periods=period).max()
    return (close - lowest) / (highest - lowest).replace(0, np.nan) * 100


def rci_series(close: pd.Series, period: int) -> pd.Series:
    x_rank = np.arange(1, period + 1, dtype=float)
    x_centered = x_rank - x_rank.mean()
    x_norm = np.sqrt((x_centered**2).sum())
    values = close.to_numpy(dtype=float)
    out = np.full(len(values), np.nan)
    for i in range(period - 1, len(values)):
        window = values[i - period + 1 : i + 1]
        if np.isnan(window).any():
            continue
        y_rank = pd.Series(window).rank(method="average").to_numpy(dtype=float)
        y_centered = y_rank - y_rank.mean()
        y_norm = np.sqrt((y_centered**2).sum())
        denom = x_norm * y_norm
        if denom > 0:
            out[i] = float((x_centered * y_centered).sum() / denom * 100.0)
    return pd.Series(out, index=close.index)


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    close = out["close"]
    high = out["high"]
    low = out["low"]
    open_ = out["open"]

    for span in [20, 50, 100, 200]:
        out[f"ema{span}"] = close.ewm(span=span, adjust=False).mean()

    prev_close = close.shift(1)
    tr = pd.concat([(high - low).abs(), (high - prev_close).abs(), (low - prev_close).abs()], axis=1).max(axis=1)
    out["atr14"] = tr.rolling(14, min_periods=1).mean()

    ema_fast = close.ewm(span=MACD_FAST, adjust=False).mean()
    ema_slow = close.ewm(span=MACD_SLOW, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    macd_signal = macd_line.ewm(span=MACD_SIGNAL, adjust=False).mean()
    out["macd_hist"] = macd_line - macd_signal
    out["macd_delta"] = out["macd_hist"].diff()
    out["macd_delta3"] = out["macd_hist"] - out["macd_hist"].shift(3)

    out["ema_align"] = "mixed"
    out.loc[(out["ema20"] > out["ema50"]) & (out["ema50"] > out["ema200"]), "ema_align"] = "bull"
    out.loc[(out["ema20"] < out["ema50"]) & (out["ema50"] < out["ema200"]), "ema_align"] = "bear"

    candle_range = (high - low).replace(0, np.nan)
    body = (close - open_).abs()
    out["body_ratio"] = body / candle_range
    out["upper_wick_ratio"] = (high - pd.concat([open_, close], axis=1).max(axis=1)) / candle_range
    out["lower_wick_ratio"] = (pd.concat([open_, close], axis=1).min(axis=1) - low) / candle_range
    out["close_pos"] = (close - low) / candle_range
    out["is_bull"] = close > open_
    out["is_bear"] = close < open_
    out["prev_body"] = body.shift(1)

    prev_is_bear = out["is_bear"].shift(1).fillna(False).astype(bool)
    prev_is_bull = out["is_bull"].shift(1).fillna(False).astype(bool)
    out["bull_engulf"] = out["is_bull"] & prev_is_bear & (close >= open_.shift(1)) & (open_ <= close.shift(1)) & (body >= out["prev_body"] * 0.80)
    out["bear_engulf"] = out["is_bear"] & prev_is_bull & (open_ >= close.shift(1)) & (close <= open_.shift(1)) & (body >= out["prev_body"] * 0.80)
    out["bull_pin"] = (out["lower_wick_ratio"] >= 0.45) & (out["upper_wick_ratio"] <= 0.25) & (out["close_pos"] >= 0.55)
    out["bear_pin"] = (out["upper_wick_ratio"] >= 0.45) & (out["lower_wick_ratio"] <= 0.25) & (out["close_pos"] <= 0.45)
    out["strong_bull_close"] = out["is_bull"] & (out["body_ratio"] >= 0.55) & (out["close_pos"] >= 0.70)
    out["strong_bear_close"] = out["is_bear"] & (out["body_ratio"] >= 0.55) & (out["close_pos"] <= 0.30)

    out["close_change_3_atr"] = (close - close.shift(3)) / out["atr14"].replace(0, np.nan)
    out["close_ema20_gap_atr"] = (close - out["ema20"]) / out["atr14"].replace(0, np.nan)
    out["rsi14"] = rsi_series(close, 14)
    out["rsi14_delta"] = out["rsi14"].diff()
    out["stoch14"] = stoch_k(close, high, low, 14)
    out["stoch14_delta"] = out["stoch14"].diff()

    mid = close.rolling(20, min_periods=20).mean()
    std = close.rolling(20, min_periods=20).std()
    out["bb_upper20"] = mid + 2 * std
    out["bb_lower20"] = mid - 2 * std
    out["bb_pos20"] = (close - out["bb_lower20"]) / (out["bb_upper20"] - out["bb_lower20"]).replace(0, np.nan)

    for period in [9, 26, 52]:
        out[f"rci{period}"] = rci_series(close, period)
        out[f"rci{period}_delta"] = out[f"rci{period}"].diff()

    return out


def join_h1(m15: pd.DataFrame, h1: pd.DataFrame) -> pd.DataFrame:
    h1_cols = ["time", "ema_align", "macd_delta3", "rsi14", "rci26", "rci52"]
    h1_feat = h1[[c for c in h1_cols if c in h1.columns]].copy()
    h1_feat = h1_feat.rename(columns={c: f"h1_{c}" for c in h1_feat.columns if c != "time"})
    h1_feat = h1_feat.rename(columns={"time": "h1_time"})
    return pd.merge_asof(
        m15.sort_values("time"),
        h1_feat.sort_values("h1_time"),
        left_on="time",
        right_on="h1_time",
        direction="backward",
    ).reset_index(drop=True)


def bool_value(value: Any) -> bool:
    try:
        return bool(value)
    except Exception:
        return False


def detect_btc_runner(row: pd.Series) -> dict[str, Any] | None:
    h1_bull = row.get("h1_ema_align") == "bull"
    h1_bear = row.get("h1_ema_align") == "bear"
    h1_macd_buy = row.get("h1_macd_delta3", np.nan) > 0
    h1_macd_sell = row.get("h1_macd_delta3", np.nan) < 0
    m15_macd_buy = row.get("macd_delta", np.nan) > 0 and row.get("macd_delta3", np.nan) > 0
    m15_macd_sell = row.get("macd_delta", np.nan) < 0 and row.get("macd_delta3", np.nan) < 0
    ema20_pull_buy = row.get("low", np.nan) <= row.get("ema20", np.nan) + 0.30 * row.get("atr14", np.nan) and row.get("close", np.nan) > row.get("ema20", np.nan)
    ema20_pull_sell = row.get("high", np.nan) >= row.get("ema20", np.nan) - 0.30 * row.get("atr14", np.nan) and row.get("close", np.nan) < row.get("ema20", np.nan)
    rci_buy = row.get("rci9", np.nan) <= 0 and row.get("rci9_delta", np.nan) > 0 and row.get("rci26", np.nan) >= -60
    rci_sell = row.get("rci9", np.nan) >= 0 and row.get("rci9_delta", np.nan) < 0 and row.get("rci26", np.nan) <= 60
    not_extended = abs(row.get("close_change_3_atr", np.nan)) <= 1.20
    gap_buy = -0.20 <= row.get("close_ema20_gap_atr", np.nan) <= 0.50
    gap_sell = -0.50 <= row.get("close_ema20_gap_atr", np.nan) <= 0.20
    if h1_bull and h1_macd_buy and ema20_pull_buy and m15_macd_buy and rci_buy and not_extended and gap_buy:
        return {"side": "BUY", "signal_model": "BTC_RUNNER", "strategy_label": "BTC_RUNNER_RR2_RISK1", "portfolio_rank": "BTC_RUNNER", "rr": 2.0, "risk_atr": 1.0}
    if h1_bear and h1_macd_sell and ema20_pull_sell and m15_macd_sell and rci_sell and not_extended and gap_sell:
        return {"side": "SELL", "signal_model": "BTC_RUNNER", "strategy_label": "BTC_RUNNER_RR2_RISK1", "portfolio_rank": "BTC_RUNNER", "rr": 2.0, "risk_atr": 1.0}
    return None


def detect_gold_extra(row: pd.Series) -> dict[str, Any] | None:
    h1_bull = row.get("h1_ema_align") == "bull"
    h1_bear = row.get("h1_ema_align") == "bear"
    h1_macd_buy = row.get("h1_macd_delta3", np.nan) > 0
    h1_macd_sell = row.get("h1_macd_delta3", np.nan) < 0
    m15_macd_buy = row.get("macd_delta", np.nan) > 0 and row.get("macd_delta3", np.nan) > 0
    m15_macd_sell = row.get("macd_delta", np.nan) < 0 and row.get("macd_delta3", np.nan) < 0
    ema20_pull_buy = row.get("low", np.nan) <= row.get("ema20", np.nan) + 0.25 * row.get("atr14", np.nan) and row.get("close", np.nan) > row.get("ema20", np.nan)
    ema20_pull_sell = row.get("high", np.nan) >= row.get("ema20", np.nan) - 0.25 * row.get("atr14", np.nan) and row.get("close", np.nan) < row.get("ema20", np.nan)
    not_extended = abs(row.get("close_change_3_atr", np.nan)) <= 1.0
    gap_buy = -0.20 <= row.get("close_ema20_gap_atr", np.nan) <= 0.50
    gap_sell = -0.50 <= row.get("close_ema20_gap_atr", np.nan) <= 0.20
    bull_candle = bool_value(row.get("bull_engulf")) or bool_value(row.get("bull_pin")) or bool_value(row.get("strong_bull_close"))
    bear_candle = bool_value(row.get("bear_engulf")) or bool_value(row.get("bear_pin")) or bool_value(row.get("strong_bear_close"))

    rsi_rebound_buy = row.get("rsi14", np.nan) > 45 and row.get("rsi14_delta", np.nan) > 0
    rsi_rebound_sell = row.get("rsi14", np.nan) < 55 and row.get("rsi14_delta", np.nan) < 0
    stoch_rebound_buy = row.get("stoch14", np.nan) > 35 and row.get("stoch14_delta", np.nan) > 0
    stoch_rebound_sell = row.get("stoch14", np.nan) < 65 and row.get("stoch14_delta", np.nan) < 0
    bb_reject_buy = row.get("bb_pos20", np.nan) > 0.25 and bull_candle
    bb_reject_sell = row.get("bb_pos20", np.nan) < 0.75 and bear_candle

    if h1_bull and h1_macd_buy and ema20_pull_buy and m15_macd_buy and rsi_rebound_buy and stoch_rebound_buy and not_extended and gap_buy:
        return {"side": "BUY", "signal_model": "GOLD_EXTRA_HIGH", "strategy_label": "GOLD_EXTRA_HIGH_RSI_STOCH", "portfolio_rank": "GOLD_EXTRA_HIGH", "rr": 1.5, "risk_atr": 1.5}
    if h1_bear and h1_macd_sell and ema20_pull_sell and m15_macd_sell and rsi_rebound_sell and stoch_rebound_sell and not_extended and gap_sell:
        return {"side": "SELL", "signal_model": "GOLD_EXTRA_HIGH", "strategy_label": "GOLD_EXTRA_HIGH_RSI_STOCH", "portfolio_rank": "GOLD_EXTRA_HIGH", "rr": 1.5, "risk_atr": 1.5}
    if h1_bull and h1_macd_buy and ema20_pull_buy and m15_macd_buy and bb_reject_buy and gap_buy:
        return {"side": "BUY", "signal_model": "GOLD_EXTRA_STANDARD", "strategy_label": "GOLD_EXTRA_BB_BALANCE", "portfolio_rank": "GOLD_EXTRA_STANDARD", "rr": 1.5, "risk_atr": 1.5}
    if h1_bear and h1_macd_sell and ema20_pull_sell and m15_macd_sell and bb_reject_sell and gap_sell:
        return {"side": "SELL", "signal_model": "GOLD_EXTRA_STANDARD", "strategy_label": "GOLD_EXTRA_BB_BALANCE", "portfolio_rank": "GOLD_EXTRA_STANDARD", "rr": 1.5, "risk_atr": 1.5}
    counter_buy = row.get("close_ema20_gap_atr", np.nan) < -1.4 and row.get("rsi14", np.nan) > 30 and row.get("stoch14", np.nan) > 20 and bull_candle and row.get("h1_rsi14", np.nan) > 25
    if counter_buy:
        return {"side": "BUY", "signal_model": "GOLD_EXTRA_HIGH", "strategy_label": "GOLD_COUNTER_BUY_ONLY", "portfolio_rank": "GOLD_EXTRA_HIGH", "rr": 1.2, "risk_atr": 0.8}
    return None


def detect_signal(symbol: str, row: pd.Series) -> dict[str, Any] | None:
    return detect_btc_runner(row) if symbol == "BTC" else detect_gold_extra(row)


def build_payload(symbol_group: str, row: pd.Series, signal: dict[str, Any] | None, history_csv: Path, *, selection_mode: str) -> dict[str, Any]:
    base: dict[str, Any] = {
        "payload_type": "latest_csv_signal_check",
        "symbol_group": symbol_group,
        "signal_found": signal is not None,
        "selection_mode": selection_mode,
        "time": row.get("time").strftime("%Y-%m-%d %H:%M:%S") if pd.notna(row.get("time")) else "",
    }
    if signal is None:
        base["message"] = "No final-rule signal on selected M15 bar."
        return base

    current = {
        "symbol_group": symbol_group,
        "portfolio_rank": signal["portfolio_rank"],
        "strategy_label": signal["strategy_label"],
        "signal_model": signal["signal_model"],
        "side": signal["side"],
        "entry_time": base["time"],
        "time": base["time"],
        "close": float(row.get("close")),
        "atr14": float(row.get("atr14")),
        "rr": signal["rr"],
        "risk_atr": signal["risk_atr"],
    }
    base["current_signal_snapshot"] = current
    base["regime_guard"] = evaluate_from_history_csv(current, history_csv=history_csv)
    base["ai_review_required"] = bool(base["regime_guard"].get("gold_abc_buy_danger_regime"))
    base["discord_priority"] = "warning" if base["regime_guard"].get("gold_abc_buy_danger_regime") else "normal"
    return base


def select_target_row(df: pd.DataFrame, *, symbol: str, bar_offset: int, bar_time: str | None, scan_recent_bars: int | None) -> tuple[pd.Series, dict[str, Any] | None, str, int, list[dict[str, Any]]]:
    if bar_time:
        target_time = pd.to_datetime(bar_time, errors="coerce")
        if pd.isna(target_time):
            raise ValueError(f"Invalid --bar-time: {bar_time}")
        matches = df.index[df["time"].eq(pd.Timestamp(target_time))].tolist()
        if not matches:
            nearest_idx = int((df["time"] - pd.Timestamp(target_time)).abs().idxmin())
            nearest_time = df.at[nearest_idx, "time"]
            raise ValueError(f"No exact bar for --bar-time {bar_time}. Nearest bar is {nearest_time} at index {nearest_idx}.")
        idx = int(matches[-1])
        row = df.iloc[idx]
        return row, detect_signal(symbol, row), "bar_time", idx, []

    if scan_recent_bars is not None and scan_recent_bars > 0:
        end_idx = len(df) - 1 - bar_offset
        start_idx = max(220, end_idx - scan_recent_bars + 1)
        found: list[dict[str, Any]] = []
        for idx in range(start_idx, end_idx + 1):
            row = df.iloc[idx]
            signal = detect_signal(symbol, row)
            if signal is not None:
                found.append({
                    "idx": int(idx),
                    "time": row.get("time").strftime("%Y-%m-%d %H:%M:%S") if pd.notna(row.get("time")) else "",
                    "strategy_label": signal.get("strategy_label"),
                    "side": signal.get("side"),
                    "rr": signal.get("rr"),
                    "risk_atr": signal.get("risk_atr"),
                })
        if found:
            last = found[-1]
            idx = int(last["idx"])
            row = df.iloc[idx]
            return row, detect_signal(symbol, row), f"scan_recent_bars_{scan_recent_bars}", idx, found
        idx = int(end_idx)
        row = df.iloc[idx]
        return row, None, f"scan_recent_bars_{scan_recent_bars}_no_signal", idx, found

    idx = len(df) - 1 - bar_offset
    row = df.iloc[idx]
    return row, detect_signal(symbol, row), "bar_offset", int(idx), []


def main() -> int:
    parser = argparse.ArgumentParser(description="Build selected-bar signal payload from M15/H1 CSV for GOLD or BTC.")
    parser.add_argument("--symbol", choices=["GOLD", "BTC"], required=True)
    parser.add_argument("--m15-csv", type=Path, required=True)
    parser.add_argument("--h1-csv", type=Path, required=True)
    parser.add_argument("--history-csv", type=Path, default=DEFAULT_HISTORY_CSV)
    parser.add_argument("--out-json", type=Path, default=None)
    parser.add_argument("--bar-offset", type=int, default=1, help="1 means latest closed bar if CSV may include current forming bar; 0 means last row.")
    parser.add_argument("--bar-time", default=None, help="Exact M15 bar time to inspect, e.g. 2026-04-01 12:15:00")
    parser.add_argument("--scan-recent-bars", type=int, default=None, help="Scan recent N bars and build payload for the latest detected signal.")
    args = parser.parse_args()

    m15_csv = resolve_path(args.m15_csv)
    h1_csv = resolve_path(args.h1_csv)
    history_csv = resolve_path(args.history_csv)
    out_json = resolve_path(args.out_json) if args.out_json else DEFAULT_OUT_DIR / f"latest_{args.symbol.lower()}_signal_payload.json"

    m15 = add_indicators(read_ohlc(m15_csv))
    h1 = add_indicators(read_ohlc(h1_csv))
    df = join_h1(m15, h1)
    if len(df) < 250:
        raise ValueError("Not enough rows. Need at least about 250 M15 bars for indicators.")

    row, signal, selection_mode, target_idx, found = select_target_row(
        df,
        symbol=args.symbol,
        bar_offset=args.bar_offset,
        bar_time=args.bar_time,
        scan_recent_bars=args.scan_recent_bars,
    )
    if target_idx < 220:
        raise ValueError(f"Selected target_idx too early for indicators: target_idx={target_idx}")

    payload = build_payload(args.symbol, row, signal, history_csv, selection_mode=selection_mode)
    if found:
        payload["scan_found_count"] = len(found)
        payload["scan_found_preview_last_10"] = found[-10:]
    elif args.scan_recent_bars:
        payload["scan_found_count"] = 0
        payload["scan_found_preview_last_10"] = []

    out_json.parent.mkdir(parents=True, exist_ok=True)
    with out_json.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2, default=str)

    print("Symbol:", args.symbol)
    print("M15 CSV:", m15_csv)
    print("H1 CSV:", h1_csv)
    print("Selection mode:", selection_mode)
    print("Target idx:", target_idx)
    print("Target bar:", row.get("time"))
    if args.scan_recent_bars:
        print("Scan recent bars:", args.scan_recent_bars)
        print("Signals found in scan:", len(found))
        if found:
            print("Last scan signal:", found[-1])
    print("Signal found:", payload.get("signal_found"))
    if payload.get("signal_found"):
        cur = payload["current_signal_snapshot"]
        print("Signal:", cur.get("strategy_label"), cur.get("side"), "rr", cur.get("rr"), "risk_atr", cur.get("risk_atr"))
        print("Regime guard:", payload.get("regime_guard", {}).get("gold_abc_buy_danger_regime"), payload.get("regime_guard", {}).get("reason"))
    print("Saved JSON:", out_json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
