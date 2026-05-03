from __future__ import annotations

import argparse
import csv
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_M15_CSV = PROJECT_ROOT / "data" / "raw" / "btcusdsharp_m15.csv"
DEFAULT_H1_CSV = PROJECT_ROOT / "data" / "raw" / "btcusdsharp_h1.csv"
DEFAULT_OUT_SUMMARY = PROJECT_ROOT / "data" / "results" / "btcusdsharp_b_rci_tier_swing_sl_summary.csv"
DEFAULT_OUT_TRADES = PROJECT_ROOT / "data" / "results" / "btcusdsharp_b_rci_tier_swing_sl_trades.csv"
DEFAULT_OUT_RULES = PROJECT_ROOT / "data" / "results" / "btcusdsharp_b_rci_tier_swing_sl_rules.md"

MACD_FAST = 6
MACD_SLOW = 13
MACD_SIGNAL = 4


def resolve_path(path: Path) -> Path:
    return path if path.is_absolute() else PROJECT_ROOT / path


def read_ohlc(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    df = pd.read_csv(path)
    required = ["time", "open", "high", "low", "close"]
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"Missing columns in {path}: {missing}")
    out = df.copy()
    out["time"] = pd.to_datetime(out["time"], format="%Y.%m.%d %H:%M", errors="coerce")
    if out["time"].isna().mean() > 0.5:
        out["time"] = pd.to_datetime(df["time"], errors="coerce")
    out = out.dropna(subset=["time"]).sort_values("time", kind="mergesort").reset_index(drop=True)
    for col in ["open", "high", "low", "close", "volume", "spread"]:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")
    return out


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
    macd_hist = macd_line - macd_signal
    out["macd_hist"] = macd_hist
    out["macd_delta"] = macd_hist.diff()
    out["macd_delta3"] = macd_hist - macd_hist.shift(3)

    out["ema_align"] = "mixed"
    out.loc[(out["ema20"] > out["ema50"]) & (out["ema50"] > out["ema200"]), "ema_align"] = "bull"
    out.loc[(out["ema20"] < out["ema50"]) & (out["ema50"] < out["ema200"]), "ema_align"] = "bear"

    candle_range = (high - low).replace(0, np.nan)
    out["body_ratio"] = (close - open_).abs() / candle_range
    out["close_change_3_atr"] = (close - close.shift(3)) / out["atr14"].replace(0, np.nan)
    out["close_ema20_gap_atr"] = (close - out["ema20"]) / out["atr14"].replace(0, np.nan)

    for period in [9, 26, 52]:
        out[f"rci{period}"] = rci_series(close, period)
        out[f"rci{period}_delta"] = out[f"rci{period}"].diff()

    return out


def join_h1(m15: pd.DataFrame, h1: pd.DataFrame) -> pd.DataFrame:
    h1_cols = ["time", "ema_align", "macd_delta3", "rci26", "rci26_delta"]
    h1_feat = h1[[col for col in h1_cols if col in h1.columns]].copy()
    h1_feat = h1_feat.rename(columns={col: f"h1_{col}" for col in h1_feat.columns if col != "time"})
    h1_feat = h1_feat.rename(columns={"time": "h1_time"})
    return pd.merge_asof(
        m15.sort_values("time"),
        h1_feat.sort_values("h1_time"),
        left_on="time",
        right_on="h1_time",
        direction="backward",
    ).reset_index(drop=True)


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


def base_masks(df: pd.DataFrame, *, ema_touch_atr: float, buy_gap_min: float, buy_gap_max: float, sell_gap_min: float, sell_gap_max: float, rci9_buy_max: float, rci9_sell_min: float, rci26_buy_min: float, rci26_sell_max: float, max_abs_close_change3: float | None) -> tuple[pd.Series, pd.Series]:
    h1_bull = df["h1_ema_align"].eq("bull")
    h1_bear = df["h1_ema_align"].eq("bear")
    h1_macd_buy = df["h1_macd_delta3"] > 0
    h1_macd_sell = df["h1_macd_delta3"] < 0

    near_ema20_buy = (df["low"] <= df["ema20"] + ema_touch_atr * df["atr14"]) & (df["close"] > df["ema20"])
    near_ema20_sell = (df["high"] >= df["ema20"] - ema_touch_atr * df["atr14"]) & (df["close"] < df["ema20"])

    m15_macd_buy = (df["macd_delta"] > 0) & (df["macd_delta3"] > 0)
    m15_macd_sell = (df["macd_delta"] < 0) & (df["macd_delta3"] < 0)

    gap_buy = df["close_ema20_gap_atr"].between(buy_gap_min, buy_gap_max)
    gap_sell = df["close_ema20_gap_atr"].between(sell_gap_min, sell_gap_max)

    rci_buy = (df["rci9"] <= rci9_buy_max) & (df["rci9_delta"] > 0) & (df["rci26"] >= rci26_buy_min)
    rci_sell = (df["rci9"] >= rci9_sell_min) & (df["rci9_delta"] < 0) & (df["rci26"] <= rci26_sell_max)

    if max_abs_close_change3 is not None:
        not_extended = df["close_change_3_atr"].abs() <= max_abs_close_change3
    else:
        not_extended = pd.Series(True, index=df.index)

    buy = h1_bull & h1_macd_buy & near_ema20_buy & m15_macd_buy & gap_buy & rci_buy & not_extended
    sell = h1_bear & h1_macd_sell & near_ema20_sell & m15_macd_sell & gap_sell & rci_sell & not_extended
    return buy, sell


def tier_masks(df: pd.DataFrame) -> dict[str, tuple[pd.Series, pd.Series, str]]:
    high_buy, high_sell = base_masks(
        df,
        ema_touch_atr=0.30,
        buy_gap_min=-0.20,
        buy_gap_max=0.50,
        sell_gap_min=-0.50,
        sell_gap_max=0.20,
        rci9_buy_max=-20,
        rci9_sell_min=20,
        rci26_buy_min=-60,
        rci26_sell_max=60,
        max_abs_close_change3=1.20,
    )
    standard_buy, standard_sell = base_masks(
        df,
        ema_touch_atr=0.30,
        buy_gap_min=-0.20,
        buy_gap_max=0.50,
        sell_gap_min=-0.50,
        sell_gap_max=0.20,
        rci9_buy_max=0,
        rci9_sell_min=0,
        rci26_buy_min=-60,
        rci26_sell_max=60,
        max_abs_close_change3=1.20,
    )
    wide_buy, wide_sell = base_masks(
        df,
        ema_touch_atr=0.30,
        buy_gap_min=-0.20,
        buy_gap_max=0.80,
        sell_gap_min=-0.80,
        sell_gap_max=0.20,
        rci9_buy_max=0,
        rci9_sell_min=0,
        rci26_buy_min=-80,
        rci26_sell_max=80,
        max_abs_close_change3=1.20,
    )
    return {
        "HIGH": (high_buy, high_sell, "highest win-rate candidate: deeper RCI9 pullback, not overextended"),
        "STANDARD": (standard_buy, standard_sell, "balanced candidate: RCI9 neutral-side pullback, RCI26 not strongly adverse"),
        "WIDE": (wide_buy, wide_sell, "total-R candidate: wider EMA gap and RCI26 allowance"),
    }


def collect_hierarchical_signals(df: pd.DataFrame, *, start_bar: int) -> list[tuple[int, str, str, str]]:
    masks = tier_masks(df)
    signals: list[tuple[int, str, str, str]] = []
    for i in range(start_bar, len(df) - 1):
        matched: tuple[str, str, str] | None = None
        for tier in ["HIGH", "STANDARD", "WIDE"]:
            buy_mask, sell_mask, reason = masks[tier]
            if bool(buy_mask.iloc[i]):
                matched = (tier, "BUY", reason)
                break
            if bool(sell_mask.iloc[i]):
                matched = (tier, "SELL", reason)
                break
        if matched:
            tier, side, reason = matched
            signals.append((i, side, tier, reason))
    return signals


def swing_stop(df: pd.DataFrame, *, signal_idx: int, entry_idx: int, side: str, lookback: int, atr_buffer: float, min_risk_atr: float, max_risk_atr: float) -> tuple[float, float, str] | None:
    entry = float(df.at[entry_idx, "open"])
    atr = float(df.at[signal_idx, "atr14"])
    if not np.isfinite(entry) or not np.isfinite(atr) or atr <= 0:
        return None

    start = max(0, signal_idx - lookback + 1)
    recent = df.iloc[start : signal_idx + 1]
    buffer = atr * atr_buffer

    if side == "BUY":
        anchor = float(recent["low"].min())
        sl = anchor - buffer
        risk = entry - sl
        anchor_col = "recent_swing_low"
    else:
        anchor = float(recent["high"].max())
        sl = anchor + buffer
        risk = sl - entry
        anchor_col = "recent_swing_high"

    if not np.isfinite(risk) or risk <= 0:
        return None
    risk_atr = risk / atr
    if risk_atr < min_risk_atr or risk_atr > max_risk_atr:
        return None
    return sl, risk, anchor_col


def backtest_tier_signals(df: pd.DataFrame, *, rr: float, swing_lookback: int, atr_buffer: float, min_risk_atr: float, max_risk_atr: float, max_bars: int, cooldown_bars: int, start_bar: int) -> pd.DataFrame:
    signals = collect_hierarchical_signals(df, start_bar=start_bar)
    trades: list[dict[str, object]] = []
    blocked_until = -1

    for signal_idx, side, tier, reason in signals:
        if signal_idx <= blocked_until:
            continue
        entry_idx = signal_idx + 1
        if entry_idx >= len(df):
            continue

        stop = swing_stop(
            df,
            signal_idx=signal_idx,
            entry_idx=entry_idx,
            side=side,
            lookback=swing_lookback,
            atr_buffer=atr_buffer,
            min_risk_atr=min_risk_atr,
            max_risk_atr=max_risk_atr,
        )
        if stop is None:
            continue

        sl, risk, stop_anchor_type = stop
        entry = float(df.at[entry_idx, "open"])
        atr = float(df.at[signal_idx, "atr14"])
        risk_atr = risk / atr

        if side == "BUY":
            tp = entry + rr * risk
        else:
            tp = entry - rr * risk

        exit_idx = min(entry_idx + max_bars, len(df) - 1)
        exit_price = float(df.at[exit_idx, "close"])
        exit_reason = "timeout"
        r_value = (exit_price - entry) / risk if side == "BUY" else (entry - exit_price) / risk

        for j in range(entry_idx, min(entry_idx + max_bars, len(df) - 1) + 1):
            high = float(df.at[j, "high"])
            low = float(df.at[j, "low"])
            if side == "BUY":
                if low <= sl:
                    exit_idx = j
                    exit_price = sl
                    exit_reason = "sl"
                    r_value = -1.0
                    break
                if high >= tp:
                    exit_idx = j
                    exit_price = tp
                    exit_reason = "tp"
                    r_value = rr
                    break
            else:
                if high >= sl:
                    exit_idx = j
                    exit_price = sl
                    exit_reason = "sl"
                    r_value = -1.0
                    break
                if low <= tp:
                    exit_idx = j
                    exit_price = tp
                    exit_reason = "tp"
                    r_value = rr
                    break

        trades.append(
            {
                "notify_tier": tier,
                "tier_reason": reason,
                "signal_idx": int(signal_idx),
                "signal_time": df.at[signal_idx, "time"],
                "entry_idx": int(entry_idx),
                "entry_time": df.at[entry_idx, "time"],
                "exit_idx": int(exit_idx),
                "exit_time": df.at[exit_idx, "time"],
                "side": side,
                "entry_price": entry,
                "sl": float(sl),
                "tp": float(tp),
                "risk": float(risk),
                "risk_atr_ratio": float(risk_atr),
                "stop_anchor_type": stop_anchor_type,
                "exit_price": float(exit_price),
                "exit_reason": exit_reason,
                "bars_held": int(exit_idx - entry_idx + 1),
                "r": float(r_value),
                "result": "win" if r_value > 0 else "loss" if r_value < 0 else "breakeven",
                "jst_entry_hour": int(pd.Timestamp(df.at[entry_idx, "time"]).hour),
                "h1_ema_align": df.at[signal_idx, "h1_ema_align"],
                "h1_macd_delta3": df.at[signal_idx, "h1_macd_delta3"],
                "h1_rci26": df.at[signal_idx, "h1_rci26"],
                "m15_rci9": df.at[signal_idx, "rci9"],
                "m15_rci26": df.at[signal_idx, "rci26"],
                "m15_gap20_atr": df.at[signal_idx, "close_ema20_gap_atr"],
                "m15_close_change_3_atr": df.at[signal_idx, "close_change_3_atr"],
            }
        )
        blocked_until = exit_idx + cooldown_bars

    return pd.DataFrame(trades)


def summarize_group(trades: pd.DataFrame, *, group_name: str, group_value: str) -> dict[str, object]:
    if trades.empty:
        return {
            "group_name": group_name,
            "group_value": group_value,
            "trades": 0,
            "wins": 0,
            "losses": 0,
            "win_rate": None,
            "total_r": 0.0,
            "avg_r": None,
            "pf": None,
            "max_consecutive_losses": 0,
            "buy_trades": 0,
            "sell_trades": 0,
            "buy_win_rate": None,
            "sell_win_rate": None,
            "avg_risk_atr_ratio": None,
            "median_risk_atr_ratio": None,
            "trades_per_month": None,
        }
    r = pd.to_numeric(trades["r"], errors="coerce")
    wins = int((r > 0).sum())
    losses = int((r < 0).sum())
    buy = trades[trades["side"] == "BUY"]
    sell = trades[trades["side"] == "SELL"]
    months = max(1.0, (pd.Timestamp(trades["entry_time"].max()) - pd.Timestamp(trades["entry_time"].min())).days / 30.4375)
    return {
        "group_name": group_name,
        "group_value": group_value,
        "trades": int(len(trades)),
        "wins": wins,
        "losses": losses,
        "win_rate": wins / len(trades),
        "total_r": float(r.sum()),
        "avg_r": float(r.mean()),
        "pf": profit_factor(r),
        "max_consecutive_losses": max_consecutive_losses(trades["result"]),
        "buy_trades": int(len(buy)),
        "sell_trades": int(len(sell)),
        "buy_win_rate": float((buy["r"] > 0).sum() / len(buy)) if len(buy) else None,
        "sell_win_rate": float((sell["r"] > 0).sum() / len(sell)) if len(sell) else None,
        "avg_risk_atr_ratio": float(trades["risk_atr_ratio"].mean()),
        "median_risk_atr_ratio": float(trades["risk_atr_ratio"].median()),
        "trades_per_month": float(len(trades) / months),
    }


def summarize_tiers(trades: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    rows.append(summarize_group(trades, group_name="all", group_value="HIGH+STANDARD+WIDE"))
    for tier in ["HIGH", "STANDARD", "WIDE"]:
        rows.append(summarize_group(trades[trades["notify_tier"] == tier].copy(), group_name="tier", group_value=tier))
    rows.append(summarize_group(trades[trades["notify_tier"].isin(["HIGH", "STANDARD"])].copy(), group_name="combo", group_value="HIGH+STANDARD"))
    rows.append(summarize_group(trades[trades["notify_tier"].isin(["HIGH"])].copy(), group_name="combo", group_value="HIGH_ONLY"))
    return pd.DataFrame(rows)


def write_rules(path: Path, *, rr: float, swing_lookback: int, atr_buffer: float, min_risk_atr: float, max_risk_atr: float) -> None:
    content = f"""# BTCUSD# B/RCI Tier Swing SL Backtest Rules

This backtest uses the same BTC B/RCI notification tier conditions as the fixed ATR tier analysis,
but changes stop loss placement to a recent swing-style stop.

## Entry rules

Hierarchy:

```text
HIGH first
else STANDARD
else WIDE
else no notification
```

All tiers require:

```text
H1 EMA direction agrees with side
H1 MACD delta3 agrees with side
M15 EMA20 pullback/rebound
M15 MACD delta and delta3 re-accelerate in side direction
M15 RCI9 turns from pullback/rebound area
M15 RCI26 is not strongly adverse
abs(M15 close_change_3_atr) <= 1.20
```

## Stop / target

```text
swing_lookback = {swing_lookback}
atr_buffer = ATR14 * {atr_buffer}
min_risk_atr = {min_risk_atr}
max_risk_atr = {max_risk_atr}
RR = {rr}

BUY SL  = recent {swing_lookback}-bar low - ATR14 * {atr_buffer}
SELL SL = recent {swing_lookback}-bar high + ATR14 * {atr_buffer}
TP      = entry +/- RR * risk
```

Same-candle SL/TP conflict is treated conservatively: SL first.
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def write_csv(path: Path, df: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig", quoting=csv.QUOTE_MINIMAL)


def print_table(title: str, df: pd.DataFrame) -> None:
    print("\n" + "=" * 120)
    print(title)
    print("=" * 120)
    print(df.to_string(index=False) if not df.empty else "No data.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Backtest BTCUSD# B/RCI tiers using recent swing low/high SL.")
    parser.add_argument("--m15-csv", type=Path, default=DEFAULT_M15_CSV)
    parser.add_argument("--h1-csv", type=Path, default=DEFAULT_H1_CSV)
    parser.add_argument("--out-summary", type=Path, default=DEFAULT_OUT_SUMMARY)
    parser.add_argument("--out-trades", type=Path, default=DEFAULT_OUT_TRADES)
    parser.add_argument("--out-rules", type=Path, default=DEFAULT_OUT_RULES)
    parser.add_argument("--rr", type=float, default=1.5)
    parser.add_argument("--swing-lookback", type=int, default=8)
    parser.add_argument("--atr-buffer", type=float, default=0.05)
    parser.add_argument("--min-risk-atr", type=float, default=0.20)
    parser.add_argument("--max-risk-atr", type=float, default=3.00)
    parser.add_argument("--max-bars", type=int, default=96)
    parser.add_argument("--cooldown-bars", type=int, default=4)
    parser.add_argument("--start-bar", type=int, default=220)
    args = parser.parse_args()

    m15_csv = resolve_path(args.m15_csv)
    h1_csv = resolve_path(args.h1_csv)
    out_summary = resolve_path(args.out_summary)
    out_trades = resolve_path(args.out_trades)
    out_rules = resolve_path(args.out_rules)

    m15 = add_indicators(read_ohlc(m15_csv))
    h1 = add_indicators(read_ohlc(h1_csv))
    df = join_h1(m15, h1)

    trades = backtest_tier_signals(
        df,
        rr=args.rr,
        swing_lookback=args.swing_lookback,
        atr_buffer=args.atr_buffer,
        min_risk_atr=args.min_risk_atr,
        max_risk_atr=args.max_risk_atr,
        max_bars=args.max_bars,
        cooldown_bars=args.cooldown_bars,
        start_bar=args.start_bar,
    )
    summary = summarize_tiers(trades) if not trades.empty else pd.DataFrame()

    write_csv(out_summary, summary)
    write_csv(out_trades, trades)
    write_rules(
        out_rules,
        rr=args.rr,
        swing_lookback=args.swing_lookback,
        atr_buffer=args.atr_buffer,
        min_risk_atr=args.min_risk_atr,
        max_risk_atr=args.max_risk_atr,
    )

    print("M15 rows:", len(m15), m15_csv, m15["time"].min(), "to", m15["time"].max())
    print("H1 rows:", len(h1), h1_csv, h1["time"].min(), "to", h1["time"].max())
    print(
        "RR:",
        args.rr,
        "swing_lookback:",
        args.swing_lookback,
        "atr_buffer:",
        args.atr_buffer,
        "risk_atr range:",
        args.min_risk_atr,
        "to",
        args.max_risk_atr,
        "max_bars:",
        args.max_bars,
    )
    print("Saved summary:", out_summary)
    print("Saved trades:", out_trades)
    print("Saved rules:", out_rules)

    display_cols = [
        "group_name",
        "group_value",
        "trades",
        "buy_trades",
        "sell_trades",
        "wins",
        "losses",
        "win_rate",
        "total_r",
        "avg_r",
        "pf",
        "max_consecutive_losses",
        "avg_risk_atr_ratio",
        "median_risk_atr_ratio",
        "trades_per_month",
    ]
    print_table("BTCUSD# B/RCI TIER SWING SL SUMMARY", summary[display_cols] if not summary.empty else summary)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
