from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_M5_CSV = PROJECT_ROOT / "data" / "raw" / "btcusdsharp_m5.csv"
DEFAULT_M15_CSV = PROJECT_ROOT / "data" / "raw" / "btcusdsharp_m15.csv"
DEFAULT_H1_CSV = PROJECT_ROOT / "data" / "raw" / "btcusdsharp_h1.csv"
DEFAULT_H4_CSV = PROJECT_ROOT / "data" / "raw" / "btcusdsharp_h4.csv"
DEFAULT_OUT_SUMMARY = PROJECT_ROOT / "data" / "results" / "btc_mtf_extra_edge_summary.csv"
DEFAULT_OUT_TRADES = PROJECT_ROOT / "data" / "results" / "btc_mtf_extra_edge_trades.csv"

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

    for col in ["open", "high", "low", "close", "volume", "tick_volume", "spread", "real_volume"]:
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

    for span in [8, 20, 50, 100, 200]:
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
    out["ema20_gt_ema50"] = out["ema20"] > out["ema50"]
    out["ema20_lt_ema50"] = out["ema20"] < out["ema50"]

    candle_range = (high - low).replace(0, np.nan)
    body = (close - open_).abs()
    out["body_ratio"] = body / candle_range
    out["close_pos"] = (close - low) / candle_range
    out["upper_wick_ratio"] = (high - pd.concat([open_, close], axis=1).max(axis=1)) / candle_range
    out["lower_wick_ratio"] = (pd.concat([open_, close], axis=1).min(axis=1) - low) / candle_range
    out["is_bull"] = close > open_
    out["is_bear"] = close < open_
    out["strong_bull_close"] = out["is_bull"] & (out["body_ratio"] >= 0.55) & (out["close_pos"] >= 0.70)
    out["strong_bear_close"] = out["is_bear"] & (out["body_ratio"] >= 0.55) & (out["close_pos"] <= 0.30)

    out["close_change_3_atr"] = (close - close.shift(3)) / out["atr14"].replace(0, np.nan)
    out["close_change_6_atr"] = (close - close.shift(6)) / out["atr14"].replace(0, np.nan)
    out["close_ema8_gap_atr"] = (close - out["ema8"]) / out["atr14"].replace(0, np.nan)
    out["close_ema20_gap_atr"] = (close - out["ema20"]) / out["atr14"].replace(0, np.nan)
    out["close_ema50_gap_atr"] = (close - out["ema50"]) / out["atr14"].replace(0, np.nan)
    out["range20_atr"] = (high.rolling(20, min_periods=5).max() - low.rolling(20, min_periods=5).min()) / out[
        "atr14"
    ].replace(0, np.nan)
    out["prev_high20"] = high.shift(1).rolling(20, min_periods=5).max()
    out["prev_low20"] = low.shift(1).rolling(20, min_periods=5).min()
    out["break_high20_atr"] = (close - out["prev_high20"]) / out["atr14"].replace(0, np.nan)
    out["break_low20_atr"] = (close - out["prev_low20"]) / out["atr14"].replace(0, np.nan)

    out["rsi14"] = rsi_series(close, 14)
    out["rsi14_delta"] = out["rsi14"].diff()
    out["stoch14"] = stoch_k(close, high, low, 14)
    out["stoch14_delta"] = out["stoch14"].diff()
    for period in [9, 26, 52]:
        out[f"rci{period}"] = rci_series(close, period)
        out[f"rci{period}_delta"] = out[f"rci{period}"].diff()

    return out


def prefix_for_join(df: pd.DataFrame, prefix: str) -> pd.DataFrame:
    cols = [
        "time",
        "open",
        "high",
        "low",
        "close",
        "ema8",
        "ema20",
        "ema50",
        "ema100",
        "ema200",
        "ema_align",
        "ema20_gt_ema50",
        "ema20_lt_ema50",
        "atr14",
        "macd_hist",
        "macd_delta",
        "macd_delta3",
        "close_change_3_atr",
        "close_change_6_atr",
        "close_ema8_gap_atr",
        "close_ema20_gap_atr",
        "close_ema50_gap_atr",
        "rsi14",
        "rsi14_delta",
        "stoch14",
        "stoch14_delta",
        "rci9",
        "rci9_delta",
        "rci26",
        "rci26_delta",
        "rci52",
        "rci52_delta",
    ]
    use_cols = [c for c in cols if c in df.columns]
    out = df[use_cols].copy().rename(columns={"time": f"{prefix}_time"})
    out = out.rename(columns={c: f"{prefix}_{c}" for c in out.columns if c != f"{prefix}_time"})
    return out


def join_context(base: pd.DataFrame, contexts: list[tuple[pd.DataFrame, str]]) -> pd.DataFrame:
    out = base.sort_values("time").reset_index(drop=True)
    for ctx, prefix in contexts:
        ctx_pref = prefix_for_join(ctx, prefix).sort_values(f"{prefix}_time")
        out = pd.merge_asof(
            out.sort_values("time"),
            ctx_pref,
            left_on="time",
            right_on=f"{prefix}_time",
            direction="backward",
        ).reset_index(drop=True)
    return out


def spread_price(row: pd.Series, *, point_size: float, spread_multiplier: float) -> float:
    return max(0.0, float(row.get("spread", 0.0) or 0.0) * point_size * spread_multiplier)


def profit_factor(r: pd.Series) -> float | None:
    wins = r[r > 0]
    losses = r[r < 0]
    gross_win = float(wins.sum()) if len(wins) else 0.0
    gross_loss_abs = float(abs(losses.sum())) if len(losses) else 0.0
    if gross_loss_abs <= 0:
        return None
    return gross_win / gross_loss_abs


def max_consecutive_losses(results: pd.Series) -> int:
    max_streak = 0
    streak = 0
    for value in results.astype(str):
        if value == "loss":
            streak += 1
            max_streak = max(max_streak, streak)
        else:
            streak = 0
    return max_streak


def max_drawdown_r(r_values: pd.Series) -> float:
    if r_values.empty:
        return 0.0
    equity = r_values.cumsum()
    peak = equity.cummax()
    dd = equity - peak
    return float(abs(dd.min()))


def backtest_mask(
    df: pd.DataFrame,
    buy_mask: pd.Series,
    sell_mask: pd.Series,
    *,
    rule_name: str,
    rr: float,
    risk_atr: float,
    max_bars: int,
    cooldown_bars: int,
    start_bar: int,
    point_size: float,
    spread_multiplier: float,
) -> pd.DataFrame:
    buy = buy_mask.fillna(False).to_numpy(dtype=bool)
    sell = sell_mask.fillna(False).to_numpy(dtype=bool)
    trades: list[dict[str, Any]] = []
    blocked_until = -1

    for signal_idx in range(start_bar, len(df) - 1):
        side = None
        if buy[signal_idx] and not sell[signal_idx]:
            side = "BUY"
        elif sell[signal_idx] and not buy[signal_idx]:
            side = "SELL"
        else:
            continue
        if signal_idx <= blocked_until:
            continue

        entry_idx = signal_idx + 1
        entry_row = df.iloc[entry_idx]
        entry_mid = float(entry_row["open"])
        spread = spread_price(entry_row, point_size=point_size, spread_multiplier=spread_multiplier)
        atr = float(df.at[signal_idx, "atr14"])
        if not np.isfinite(entry_mid) or not np.isfinite(atr) or atr <= 0:
            continue

        if side == "BUY":
            entry = entry_mid + spread / 2
            risk = atr * risk_atr
            sl = entry - risk
            tp = entry + rr * risk
        else:
            entry = entry_mid - spread / 2
            risk = atr * risk_atr
            sl = entry + risk
            tp = entry - rr * risk

        exit_idx = min(entry_idx + max_bars, len(df) - 1)
        exit_mid = float(df.at[exit_idx, "close"])
        exit_spread = spread_price(df.iloc[exit_idx], point_size=point_size, spread_multiplier=spread_multiplier)
        exit_price = exit_mid - exit_spread / 2 if side == "BUY" else exit_mid + exit_spread / 2
        r_value = (exit_price - entry) / risk if side == "BUY" else (entry - exit_price) / risk
        exit_reason = "timeout"

        for j in range(entry_idx, min(entry_idx + max_bars, len(df) - 1) + 1):
            high_mid = float(df.at[j, "high"])
            low_mid = float(df.at[j, "low"])
            current_spread = spread_price(df.iloc[j], point_size=point_size, spread_multiplier=spread_multiplier)
            bid_high = high_mid - current_spread / 2
            bid_low = low_mid - current_spread / 2
            ask_high = high_mid + current_spread / 2
            ask_low = low_mid + current_spread / 2

            if side == "BUY":
                if bid_low <= sl:
                    exit_idx = j
                    exit_price = sl
                    exit_reason = "sl"
                    r_value = -1.0
                    break
                if bid_high >= tp:
                    exit_idx = j
                    exit_price = tp
                    exit_reason = "tp"
                    r_value = rr
                    break
            else:
                if ask_high >= sl:
                    exit_idx = j
                    exit_price = sl
                    exit_reason = "sl"
                    r_value = -1.0
                    break
                if ask_low <= tp:
                    exit_idx = j
                    exit_price = tp
                    exit_reason = "tp"
                    r_value = rr
                    break

        trades.append(
            {
                "rule_name": rule_name,
                "side": side,
                "signal_idx": int(signal_idx),
                "signal_time": df.at[signal_idx, "time"],
                "entry_idx": int(entry_idx),
                "entry_time": df.at[entry_idx, "time"],
                "exit_idx": int(exit_idx),
                "exit_time": df.at[exit_idx, "time"],
                "entry_price": float(entry),
                "entry_mid_price": float(entry_mid),
                "entry_spread_price": float(spread),
                "sl": float(sl),
                "tp": float(tp),
                "risk": float(risk),
                "risk_atr_ratio": float(risk_atr),
                "exit_price": float(exit_price),
                "exit_reason": exit_reason,
                "bars_held": int(exit_idx - entry_idx + 1),
                "r": float(r_value),
                "result": "win" if r_value > 0 else "loss" if r_value < 0 else "breakeven",
                "entry_hour": int(pd.Timestamp(df.at[entry_idx, "time"]).hour),
                "spread_to_risk": float(spread / risk) if risk > 0 else np.nan,
            }
        )
        blocked_until = exit_idx + cooldown_bars

    return pd.DataFrame(trades)


def summarize_trades(trades: pd.DataFrame, *, rule_name: str, description: str, base_tf: str, rr: float, risk_atr: float, max_bars: int) -> dict[str, Any]:
    if trades.empty:
        return {
            "rule_name": rule_name,
            "description": description,
            "base_tf": base_tf,
            "rr": rr,
            "risk_atr": risk_atr,
            "max_bars": max_bars,
            "trades": 0,
            "wins": 0,
            "losses": 0,
            "win_rate": None,
            "total_r": 0.0,
            "avg_r": None,
            "pf": None,
            "max_consecutive_losses": 0,
            "max_dd_r": 0.0,
            "buy_trades": 0,
            "sell_trades": 0,
            "trades_per_month": None,
            "avg_spread_to_risk": None,
        }
    r = pd.to_numeric(trades["r"], errors="coerce")
    wins = int((r > 0).sum())
    losses = int((r < 0).sum())
    buy = trades[trades["side"] == "BUY"]
    sell = trades[trades["side"] == "SELL"]
    span_days = max(1, (pd.Timestamp(trades["entry_time"].max()) - pd.Timestamp(trades["entry_time"].min())).days)
    months = max(1.0, span_days / 30.4375)
    return {
        "rule_name": rule_name,
        "description": description,
        "base_tf": base_tf,
        "rr": rr,
        "risk_atr": risk_atr,
        "max_bars": max_bars,
        "trades": int(len(trades)),
        "wins": wins,
        "losses": losses,
        "win_rate": float(wins / len(trades)),
        "total_r": float(r.sum()),
        "avg_r": float(r.mean()),
        "pf": profit_factor(r),
        "max_consecutive_losses": max_consecutive_losses(trades["result"]),
        "max_dd_r": max_drawdown_r(r),
        "buy_trades": int(len(buy)),
        "sell_trades": int(len(sell)),
        "buy_win_rate": float((buy["r"] > 0).sum() / len(buy)) if len(buy) else None,
        "sell_win_rate": float((sell["r"] > 0).sum() / len(sell)) if len(sell) else None,
        "trades_per_month": float(len(trades) / months),
        "avg_spread_to_risk": float(pd.to_numeric(trades["spread_to_risk"], errors="coerce").mean()),
    }


def build_rules_m15(df: pd.DataFrame) -> list[tuple[str, str, pd.Series, pd.Series]]:
    h4_bull = (df["h4_ema20"] > df["h4_ema50"]) & ((df["h4_macd_hist"] > 0) | (df["h4_macd_delta3"] > 0))
    h4_bear = (df["h4_ema20"] < df["h4_ema50"]) & ((df["h4_macd_hist"] < 0) | (df["h4_macd_delta3"] < 0))
    h1_bull = (df["h1_ema20"] > df["h1_ema50"]) & (df["h1_macd_delta3"] > 0)
    h1_bear = (df["h1_ema20"] < df["h1_ema50"]) & (df["h1_macd_delta3"] < 0)

    m15_macd_buy = (df["macd_delta"] > 0) & (df["macd_delta3"] > 0)
    m15_macd_sell = (df["macd_delta"] < 0) & (df["macd_delta3"] < 0)
    ema20_pull_buy = (df["low"] <= df["ema20"] + 0.40 * df["atr14"]) & (df["close"] > df["ema20"])
    ema20_pull_sell = (df["high"] >= df["ema20"] - 0.40 * df["atr14"]) & (df["close"] < df["ema20"])
    rci_reaccel_buy = (df["rci9"] <= 20) & (df["rci9_delta"] > 0) & (df["rci26"] >= -70)
    rci_reaccel_sell = (df["rci9"] >= -20) & (df["rci9_delta"] < 0) & (df["rci26"] <= 70)
    not_extended = df["close_change_3_atr"].abs() <= 1.45

    h4_trend_pull_buy = h4_bull & h1_bull & ema20_pull_buy & m15_macd_buy & rci_reaccel_buy & not_extended & df[
        "close_ema20_gap_atr"
    ].between(-0.30, 0.85)
    h4_trend_pull_sell = h4_bear & h1_bear & ema20_pull_sell & m15_macd_sell & rci_reaccel_sell & not_extended & df[
        "close_ema20_gap_atr"
    ].between(-0.85, 0.30)

    h4_breakout_buy = (
        h4_bull
        & (df["h1_macd_delta3"] > 0)
        & (df["break_high20_atr"] > 0.05)
        & (df["rci26"] > -20)
        & (df["rci9_delta"] > 0)
        & df["close_ema20_gap_atr"].between(0.0, 1.35)
        & (df["range20_atr"] >= 2.0)
    )
    h4_breakout_sell = (
        h4_bear
        & (df["h1_macd_delta3"] < 0)
        & (df["break_low20_atr"] < -0.05)
        & (df["rci26"] < 20)
        & (df["rci9_delta"] < 0)
        & df["close_ema20_gap_atr"].between(-1.35, 0.0)
        & (df["range20_atr"] >= 2.0)
    )

    h4_m15_fast_buy = h4_bull & (df["h1_ema20"] > df["h1_ema50"]) & (df["close"] > df["ema8"]) & (df["macd_delta"] > 0) & (
        df["rsi14_delta"] > 0
    ) & df["close_ema8_gap_atr"].between(-0.15, 0.65) & (df["close_change_3_atr"] > -0.20) & (df["close_change_3_atr"] < 1.20)
    h4_m15_fast_sell = h4_bear & (df["h1_ema20"] < df["h1_ema50"]) & (df["close"] < df["ema8"]) & (df["macd_delta"] < 0) & (
        df["rsi14_delta"] < 0
    ) & df["close_ema8_gap_atr"].between(-0.65, 0.15) & (df["close_change_3_atr"] < 0.20) & (df["close_change_3_atr"] > -1.20)

    return [
        (
            "BTC_TREND_H4_M15_PULLBACK",
            "H4大方向 + H1確認 + M15 EMA20押し戻し/MACD再加速。RUNNERより少し広め。",
            h4_trend_pull_buy,
            h4_trend_pull_sell,
        ),
        (
            "BTC_BREAKOUT_H4_M15",
            "H4大方向 + M15 20本ブレイク。BTCの走る相場を狙う候補。",
            h4_breakout_buy,
            h4_breakout_sell,
        ),
        (
            "BTC_FAST_H4_M15_EMA8",
            "H4大方向 + M15 EMA8再加速。EMA20まで戻らない強いBTC用候補。",
            h4_m15_fast_buy,
            h4_m15_fast_sell,
        ),
    ]


def build_rules_m5(df: pd.DataFrame) -> list[tuple[str, str, pd.Series, pd.Series]]:
    h4_bull = (df["h4_ema20"] > df["h4_ema50"]) & ((df["h4_macd_hist"] > 0) | (df["h4_macd_delta3"] > 0))
    h4_bear = (df["h4_ema20"] < df["h4_ema50"]) & ((df["h4_macd_hist"] < 0) | (df["h4_macd_delta3"] < 0))
    h1_bull = (df["h1_ema20"] > df["h1_ema50"]) & ((df["h1_macd_hist"] > 0) | (df["h1_macd_delta3"] > 0))
    h1_bear = (df["h1_ema20"] < df["h1_ema50"]) & ((df["h1_macd_hist"] < 0) | (df["h1_macd_delta3"] < 0))
    m15_ok_buy = (df["m15_close"] >= df["m15_ema20"] - 0.25 * df["m15_atr14"]) & (df["m15_macd_delta3"] > -0.02)
    m15_ok_sell = (df["m15_close"] <= df["m15_ema20"] + 0.25 * df["m15_atr14"]) & (df["m15_macd_delta3"] < 0.02)

    m5_macd_buy = (df["macd_delta"] > 0) & (df["macd_delta3"] > 0)
    m5_macd_sell = (df["macd_delta"] < 0) & (df["macd_delta3"] < 0)
    m5_rci_buy = (df["rci9"] <= 30) & (df["rci9_delta"] > 0) & (df["rci26"] >= -75)
    m5_rci_sell = (df["rci9"] >= -30) & (df["rci9_delta"] < 0) & (df["rci26"] <= 75)
    ema8_reclaim_buy = (df["low"] <= df["ema8"] + 0.30 * df["atr14"]) & (df["close"] > df["ema8"])
    ema8_reclaim_sell = (df["high"] >= df["ema8"] - 0.30 * df["atr14"]) & (df["close"] < df["ema8"])
    not_extended_m5 = df["close_change_6_atr"].abs() <= 1.60

    h1_m5_reentry_buy = h1_bull & m15_ok_buy & ema8_reclaim_buy & m5_macd_buy & m5_rci_buy & not_extended_m5 & df[
        "close_ema8_gap_atr"
    ].between(-0.20, 0.70)
    h1_m5_reentry_sell = h1_bear & m15_ok_sell & ema8_reclaim_sell & m5_macd_sell & m5_rci_sell & not_extended_m5 & df[
        "close_ema8_gap_atr"
    ].between(-0.70, 0.20)

    h4_h1_m5_pull_buy = h4_bull & h1_bull & m15_ok_buy & (df["close"] > df["ema20"]) & m5_macd_buy & (df["rsi14_delta"] > 0) & df[
        "close_ema20_gap_atr"
    ].between(-0.10, 0.95) & (df["close_change_3_atr"] > -0.25)
    h4_h1_m5_pull_sell = h4_bear & h1_bear & m15_ok_sell & (df["close"] < df["ema20"]) & m5_macd_sell & (df["rsi14_delta"] < 0) & df[
        "close_ema20_gap_atr"
    ].between(-0.95, 0.10) & (df["close_change_3_atr"] < 0.25)

    m5_breakout_buy = h1_bull & m15_ok_buy & (df["break_high20_atr"] > 0.03) & m5_macd_buy & (df["rci26"] > -20) & df[
        "close_ema20_gap_atr"
    ].between(0.0, 1.40)
    m5_breakout_sell = h1_bear & m15_ok_sell & (df["break_low20_atr"] < -0.03) & m5_macd_sell & (df["rci26"] < 20) & df[
        "close_ema20_gap_atr"
    ].between(-1.40, 0.0)

    return [
        (
            "BTC_SCALP_H1_M5_REENTRY",
            "H1方向 + M15簡易確認 + M5 EMA8再取得。件数増加狙い。AI評価必須候補。",
            h1_m5_reentry_buy,
            h1_m5_reentry_sell,
        ),
        (
            "BTC_PULLBACK_H4_H1_M5",
            "H4/H1方向一致 + M5 EMA20押し戻し。M15 RUNNERより早い再入場候補。",
            h4_h1_m5_pull_buy,
            h4_h1_m5_pull_sell,
        ),
        (
            "BTC_BREAKOUT_H1_M5",
            "H1方向 + M5 20本ブレイク。短期ブレイク検証候補。",
            m5_breakout_buy,
            m5_breakout_sell,
        ),
    ]


def write_csv(path: Path, df: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig", quoting=csv.QUOTE_MINIMAL)


def print_table(title: str, df: pd.DataFrame) -> None:
    print("\n" + "=" * 140)
    print(title)
    print("=" * 140)
    print(df.to_string(index=False) if not df.empty else "No data.")


def run_rule_grid(
    *,
    df: pd.DataFrame,
    base_tf: str,
    rules: list[tuple[str, str, pd.Series, pd.Series]],
    rr_values: list[float],
    risk_values: list[float],
    max_bars_values: list[int],
    cooldown_bars: int,
    start_bar: int,
    point_size: float,
    spread_multiplier: float,
) -> tuple[list[dict[str, Any]], list[pd.DataFrame]]:
    summaries: list[dict[str, Any]] = []
    frames: list[pd.DataFrame] = []
    for base_rule_name, description, buy_mask, sell_mask in rules:
        for rr in rr_values:
            for risk_atr in risk_values:
                for max_bars in max_bars_values:
                    rule_name = f"{base_rule_name}_rr{rr}_risk{risk_atr}_max{max_bars}"
                    trades = backtest_mask(
                        df,
                        buy_mask,
                        sell_mask,
                        rule_name=rule_name,
                        rr=rr,
                        risk_atr=risk_atr,
                        max_bars=max_bars,
                        cooldown_bars=cooldown_bars,
                        start_bar=start_bar,
                        point_size=point_size,
                        spread_multiplier=spread_multiplier,
                    )
                    summaries.append(
                        summarize_trades(
                            trades,
                            rule_name=rule_name,
                            description=description,
                            base_tf=base_tf,
                            rr=rr,
                            risk_atr=risk_atr,
                            max_bars=max_bars,
                        )
                    )
                    if not trades.empty:
                        trades["base_tf"] = base_tf
                        trades["description"] = description
                        frames.append(trades)
    return summaries, frames


def main() -> int:
    parser = argparse.ArgumentParser(description="Search BTC multi-timeframe extra edges using M5/M15/H1/H4 CSV files.")
    parser.add_argument("--m5-csv", type=Path, default=DEFAULT_M5_CSV)
    parser.add_argument("--m15-csv", type=Path, default=DEFAULT_M15_CSV)
    parser.add_argument("--h1-csv", type=Path, default=DEFAULT_H1_CSV)
    parser.add_argument("--h4-csv", type=Path, default=DEFAULT_H4_CSV)
    parser.add_argument("--out-summary", type=Path, default=DEFAULT_OUT_SUMMARY)
    parser.add_argument("--out-trades", type=Path, default=DEFAULT_OUT_TRADES)
    parser.add_argument("--rr-values-m15", default="1.5,2.0,2.5")
    parser.add_argument("--risk-atr-values-m15", default="1.0,1.2,1.5")
    parser.add_argument("--max-bars-values-m15", default="96,192,288")
    parser.add_argument("--rr-values-m5", default="1.2,1.5,2.0")
    parser.add_argument("--risk-atr-values-m5", default="0.8,1.0,1.2")
    parser.add_argument("--max-bars-values-m5", default="72,144,288")
    parser.add_argument("--cooldown-bars-m15", type=int, default=4)
    parser.add_argument("--cooldown-bars-m5", type=int, default=12)
    parser.add_argument("--start-bar", type=int, default=300)
    parser.add_argument("--point-size", type=float, default=0.01)
    parser.add_argument("--spread-multiplier", type=float, default=1.0)
    parser.add_argument("--min-trades", type=int, default=30)
    args = parser.parse_args()

    m5_csv = resolve_path(args.m5_csv)
    m15_csv = resolve_path(args.m15_csv)
    h1_csv = resolve_path(args.h1_csv)
    h4_csv = resolve_path(args.h4_csv)
    out_summary = resolve_path(args.out_summary)
    out_trades = resolve_path(args.out_trades)

    rr_values_m15 = [float(x.strip()) for x in args.rr_values_m15.split(",") if x.strip()]
    risk_values_m15 = [float(x.strip()) for x in args.risk_atr_values_m15.split(",") if x.strip()]
    max_bars_m15 = [int(x.strip()) for x in args.max_bars_values_m15.split(",") if x.strip()]
    rr_values_m5 = [float(x.strip()) for x in args.rr_values_m5.split(",") if x.strip()]
    risk_values_m5 = [float(x.strip()) for x in args.risk_atr_values_m5.split(",") if x.strip()]
    max_bars_m5 = [int(x.strip()) for x in args.max_bars_values_m5.split(",") if x.strip()]

    m5 = add_indicators(read_ohlc(m5_csv))
    m15 = add_indicators(read_ohlc(m15_csv))
    h1 = add_indicators(read_ohlc(h1_csv))
    h4 = add_indicators(read_ohlc(h4_csv))

    m15_ctx = join_context(m15, [(h1, "h1"), (h4, "h4")])
    m5_ctx = join_context(m5, [(m15, "m15"), (h1, "h1"), (h4, "h4")])

    summary_rows: list[dict[str, Any]] = []
    trade_frames: list[pd.DataFrame] = []

    s1, f1 = run_rule_grid(
        df=m15_ctx,
        base_tf="M15",
        rules=build_rules_m15(m15_ctx),
        rr_values=rr_values_m15,
        risk_values=risk_values_m15,
        max_bars_values=max_bars_m15,
        cooldown_bars=args.cooldown_bars_m15,
        start_bar=args.start_bar,
        point_size=args.point_size,
        spread_multiplier=args.spread_multiplier,
    )
    summary_rows.extend(s1)
    trade_frames.extend(f1)

    s2, f2 = run_rule_grid(
        df=m5_ctx,
        base_tf="M5",
        rules=build_rules_m5(m5_ctx),
        rr_values=rr_values_m5,
        risk_values=risk_values_m5,
        max_bars_values=max_bars_m5,
        cooldown_bars=args.cooldown_bars_m5,
        start_bar=args.start_bar,
        point_size=args.point_size,
        spread_multiplier=args.spread_multiplier,
    )
    summary_rows.extend(s2)
    trade_frames.extend(f2)

    summary = pd.DataFrame(summary_rows)
    summary = summary.sort_values(["total_r", "pf", "trades"], ascending=[False, False, False], kind="mergesort")
    trades_out = pd.concat(trade_frames, ignore_index=True) if trade_frames else pd.DataFrame()

    write_csv(out_summary, summary)
    write_csv(out_trades, trades_out)

    display_cols = [
        "rule_name",
        "base_tf",
        "trades",
        "buy_trades",
        "sell_trades",
        "win_rate",
        "total_r",
        "avg_r",
        "pf",
        "max_consecutive_losses",
        "max_dd_r",
        "trades_per_month",
        "avg_spread_to_risk",
        "description",
    ]
    viable = summary[
        (summary["trades"] >= args.min_trades)
        & (summary["total_r"] > 0)
        & (summary["pf"].fillna(0) >= 1.4)
    ].copy()

    print("M5 rows:", len(m5), m5_csv, m5["time"].min(), "to", m5["time"].max())
    print("M15 rows:", len(m15), m15_csv, m15["time"].min(), "to", m15["time"].max())
    print("H1 rows:", len(h1), h1_csv, h1["time"].min(), "to", h1["time"].max())
    print("H4 rows:", len(h4), h4_csv, h4["time"].min(), "to", h4["time"].max())
    print("Spread:", "point_size", args.point_size, "multiplier", args.spread_multiplier)
    print("Saved summary:", out_summary)
    print("Saved trades:", out_trades)

    print_table("BTC MTF EXTRA EDGE SUMMARY TOP 30", summary[display_cols].head(30))
    print_table("BTC MTF EXTRA EDGE VIABLE TOP 30", viable[display_cols].head(30))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
