from __future__ import annotations

import argparse
import csv
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_M15_CSV = PROJECT_ROOT / "data" / "raw" / "goldsharp_m15.csv"
DEFAULT_H1_CSV = PROJECT_ROOT / "data" / "raw" / "goldsharp_h1.csv"
DEFAULT_OUT_SUMMARY = PROJECT_ROOT / "data" / "results" / "gold_value_width_edge_summary.csv"
DEFAULT_OUT_TRADES = PROJECT_ROOT / "data" / "results" / "gold_value_width_edge_trades.csv"

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
    if "spread" not in out.columns:
        out["spread"] = 0.0
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
    out["upper_wick_ratio"] = (high - pd.concat([open_, close], axis=1).max(axis=1)) / candle_range
    out["lower_wick_ratio"] = (pd.concat([open_, close], axis=1).min(axis=1) - low) / candle_range
    out["close_change_3_atr"] = (close - close.shift(3)) / out["atr14"].replace(0, np.nan)
    out["close_ema20_gap_atr"] = (close - out["ema20"]) / out["atr14"].replace(0, np.nan)
    out["close_ema50_gap_atr"] = (close - out["ema50"]) / out["atr14"].replace(0, np.nan)
    out["range20_atr"] = (high.rolling(20, min_periods=1).max() - low.rolling(20, min_periods=1).min()) / out[
        "atr14"
    ].replace(0, np.nan)
    out["prev_high20"] = high.shift(1).rolling(20, min_periods=5).max()
    out["prev_low20"] = low.shift(1).rolling(20, min_periods=5).min()
    out["break_high20_atr"] = (close - out["prev_high20"]) / out["atr14"].replace(0, np.nan)
    out["break_low20_atr"] = (close - out["prev_low20"]) / out["atr14"].replace(0, np.nan)

    for period in [9, 26, 52]:
        out[f"rci{period}"] = rci_series(close, period)
        out[f"rci{period}_delta"] = out[f"rci{period}"].diff()

    return out


def join_h1(m15: pd.DataFrame, h1: pd.DataFrame) -> pd.DataFrame:
    h1_cols = [
        "time",
        "ema_align",
        "macd_hist",
        "macd_delta3",
        "rci26",
        "rci26_delta",
        "rci52",
        "rci52_delta",
        "close_ema20_gap_atr",
        "range20_atr",
    ]
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
    trades: list[dict[str, object]] = []
    blocked_until = -1

    for signal_idx in range(start_bar, len(df) - 1):
        side = None
        if buy[signal_idx]:
            side = "BUY"
        elif sell[signal_idx]:
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


def summarize_trades(trades: pd.DataFrame, *, rule_name: str, description: str, rr: float, risk_atr: float) -> dict[str, object]:
    if trades.empty:
        return {
            "rule_name": rule_name,
            "description": description,
            "rr": rr,
            "risk_atr": risk_atr,
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
            "trades_per_month": None,
        }
    r = pd.to_numeric(trades["r"], errors="coerce")
    wins = int((r > 0).sum())
    losses = int((r < 0).sum())
    buy = trades[trades["side"] == "BUY"]
    sell = trades[trades["side"] == "SELL"]
    months = max(1.0, (pd.Timestamp(trades["entry_time"].max()) - pd.Timestamp(trades["entry_time"].min())).days / 30.4375)
    spread_to_risk = trades["entry_spread_price"] / trades["risk"].replace(0, np.nan)
    return {
        "rule_name": rule_name,
        "description": description,
        "rr": rr,
        "risk_atr": risk_atr,
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
        "avg_spread_to_risk": float(spread_to_risk.mean()),
        "trades_per_month": float(len(trades) / months),
    }


def build_gold_edge_rules(df: pd.DataFrame) -> list[tuple[str, str, pd.Series, pd.Series]]:
    h1_bull = df["h1_ema_align"].eq("bull")
    h1_bear = df["h1_ema_align"].eq("bear")
    h1_macd_buy = df["h1_macd_delta3"] > 0
    h1_macd_sell = df["h1_macd_delta3"] < 0

    m15_macd_buy = (df["macd_delta"] > 0) & (df["macd_delta3"] > 0)
    m15_macd_sell = (df["macd_delta"] < 0) & (df["macd_delta3"] < 0)

    ema20_pull_buy = (df["low"] <= df["ema20"] + 0.30 * df["atr14"]) & (df["close"] > df["ema20"])
    ema20_pull_sell = (df["high"] >= df["ema20"] - 0.30 * df["atr14"]) & (df["close"] < df["ema20"])

    rci_pull_buy = (df["rci9"] <= 0) & (df["rci9_delta"] > 0) & (df["rci26"] >= -70)
    rci_pull_sell = (df["rci9"] >= 0) & (df["rci9_delta"] < 0) & (df["rci26"] <= 70)

    rci_cross_buy = (df["rci9"].shift(1) < -60) & (df["rci9"] > -60) & (df["rci9_delta"] > 0) & (df["rci26"] >= -70)
    rci_cross_sell = (df["rci9"].shift(1) > 60) & (df["rci9"] < 60) & (df["rci9_delta"] < 0) & (df["rci26"] <= 70)

    not_extended = df["close_change_3_atr"].abs() <= 1.20
    gap_buy = df["close_ema20_gap_atr"].between(-0.30, 0.70)
    gap_sell = df["close_ema20_gap_atr"].between(-0.70, 0.30)

    trend_pull_buy = h1_bull & h1_macd_buy & ema20_pull_buy & m15_macd_buy & rci_pull_buy & not_extended & gap_buy
    trend_pull_sell = h1_bear & h1_macd_sell & ema20_pull_sell & m15_macd_sell & rci_pull_sell & not_extended & gap_sell

    trend_cross_buy = h1_bull & h1_macd_buy & ema20_pull_buy & m15_macd_buy & rci_cross_buy & not_extended & gap_buy
    trend_cross_sell = h1_bear & h1_macd_sell & ema20_pull_sell & m15_macd_sell & rci_cross_sell & not_extended & gap_sell

    # Gold-specific mean-reversion diagnostics. These are intentionally stricter than BTC because XAUUSD often spikes.
    mr_buy = (
        (df["close_ema20_gap_atr"] < -1.60)
        & (df["rci9"].shift(1) < -80)
        & (df["rci9"] > -80)
        & (df["rci9_delta"] > 0)
        & (df["lower_wick_ratio"] > 0.25)
        & (df["macd_delta"] > 0)
        & (df["h1_rci26"] > -85)
    )
    mr_sell = (
        (df["close_ema20_gap_atr"] > 1.60)
        & (df["rci9"].shift(1) > 80)
        & (df["rci9"] < 80)
        & (df["rci9_delta"] < 0)
        & (df["upper_wick_ratio"] > 0.25)
        & (df["macd_delta"] < 0)
        & (df["h1_rci26"] < 85)
    )

    breakout_buy = (
        h1_bull
        & h1_macd_buy
        & (df["break_high20_atr"] > 0.05)
        & (df["rci26"] > 0)
        & (df["rci9_delta"] > 0)
        & df["close_ema20_gap_atr"].between(0.0, 1.20)
        & (df["range20_atr"] > 2.0)
    )
    breakout_sell = (
        h1_bear
        & h1_macd_sell
        & (df["break_low20_atr"] < -0.05)
        & (df["rci26"] < 0)
        & (df["rci9_delta"] < 0)
        & df["close_ema20_gap_atr"].between(-1.20, 0.0)
        & (df["range20_atr"] > 2.0)
    )

    return [
        (
            "gold_trend_pull_rci",
            "H1方向 + EMA20押し戻し + MACD再加速 + RCI9反転。BTC runnerのGOLD版。",
            trend_pull_buy,
            trend_pull_sell,
        ),
        (
            "gold_trend_pull_rci_cross",
            "H1方向 + EMA20押し戻し + MACD再加速 + RCI9 -60/+60反転クロス。勝率重視候補。",
            trend_cross_buy,
            trend_cross_sell,
        ),
        (
            "gold_mean_reversion_extreme_rci",
            "逆張り診断用。EMA20から1.6ATR以上乖離 + RCI9極端反転 + ヒゲ確認。",
            mr_buy,
            mr_sell,
        ),
        (
            "gold_breakout_runner",
            "ブレイク伸び診断用。H1方向 + M15 20本ブレイク + RCI/MACD方向。",
            breakout_buy,
            breakout_sell,
        ),
    ]


def write_csv(path: Path, df: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig", quoting=csv.QUOTE_MINIMAL)


def print_table(title: str, df: pd.DataFrame) -> None:
    print("\n" + "=" * 120)
    print(title)
    print("=" * 120)
    print(df.to_string(index=False) if not df.empty else "No data.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Search GOLD/XAUUSD value-width and high-reproducibility edges.")
    parser.add_argument("--m15-csv", type=Path, default=DEFAULT_M15_CSV)
    parser.add_argument("--h1-csv", type=Path, default=DEFAULT_H1_CSV)
    parser.add_argument("--out-summary", type=Path, default=DEFAULT_OUT_SUMMARY)
    parser.add_argument("--out-trades", type=Path, default=DEFAULT_OUT_TRADES)
    parser.add_argument("--rr-values", default="1.5,2.0,2.5,3.0")
    parser.add_argument("--risk-atr-values", default="0.8,1.0,1.2,1.5")
    parser.add_argument("--max-bars", type=int, default=192)
    parser.add_argument("--cooldown-bars", type=int, default=4)
    parser.add_argument("--start-bar", type=int, default=220)
    parser.add_argument("--point-size", type=float, default=0.01)
    parser.add_argument("--spread-multiplier", type=float, default=1.0)
    args = parser.parse_args()

    m15_csv = resolve_path(args.m15_csv)
    h1_csv = resolve_path(args.h1_csv)
    out_summary = resolve_path(args.out_summary)
    out_trades = resolve_path(args.out_trades)

    rr_values = [float(x.strip()) for x in args.rr_values.split(",") if x.strip()]
    risk_values = [float(x.strip()) for x in args.risk_atr_values.split(",") if x.strip()]

    m15 = add_indicators(read_ohlc(m15_csv))
    h1 = add_indicators(read_ohlc(h1_csv))
    df = join_h1(m15, h1)

    summary_rows: list[dict[str, object]] = []
    trade_frames: list[pd.DataFrame] = []

    for base_rule_name, description, buy_mask, sell_mask in build_gold_edge_rules(df):
        for rr in rr_values:
            for risk_atr in risk_values:
                rule_name = f"{base_rule_name}_rr{rr}_risk{risk_atr}"
                trades = backtest_mask(
                    df,
                    buy_mask,
                    sell_mask,
                    rule_name=rule_name,
                    rr=rr,
                    risk_atr=risk_atr,
                    max_bars=args.max_bars,
                    cooldown_bars=args.cooldown_bars,
                    start_bar=args.start_bar,
                    point_size=args.point_size,
                    spread_multiplier=args.spread_multiplier,
                )
                summary_rows.append(
                    summarize_trades(trades, rule_name=rule_name, description=description, rr=rr, risk_atr=risk_atr)
                )
                if not trades.empty:
                    trade_frames.append(trades)

    summary = pd.DataFrame(summary_rows).sort_values(["total_r", "pf", "trades"], ascending=[False, False, False], kind="mergesort")
    trades_out = pd.concat(trade_frames, ignore_index=True) if trade_frames else pd.DataFrame()

    write_csv(out_summary, summary)
    write_csv(out_trades, trades_out)

    print("M15 rows:", len(m15), m15_csv, m15["time"].min(), "to", m15["time"].max())
    print("H1 rows:", len(h1), h1_csv, h1["time"].min(), "to", h1["time"].max())
    print("RR values:", rr_values)
    print("Risk ATR values:", risk_values)
    print("Spread:", "point_size", args.point_size, "multiplier", args.spread_multiplier)
    print("Saved summary:", out_summary)
    print("Saved trades:", out_trades)

    display_cols = [
        "rule_name",
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
        "trades_per_month",
        "avg_spread_to_risk",
    ]
    print_table("GOLD VALUE-WIDTH EDGE SUMMARY", summary[display_cols])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
