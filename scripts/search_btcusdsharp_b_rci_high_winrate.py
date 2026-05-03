from __future__ import annotations

import argparse
import csv
from itertools import product
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_M15_CSV = PROJECT_ROOT / "data" / "raw" / "btcusdsharp_m15.csv"
DEFAULT_H1_CSV = PROJECT_ROOT / "data" / "raw" / "btcusdsharp_h1.csv"
DEFAULT_OUT_SUMMARY = PROJECT_ROOT / "data" / "results" / "btcusdsharp_b_rci_high_winrate_search_summary.csv"
DEFAULT_OUT_TRADES = PROJECT_ROOT / "data" / "results" / "btcusdsharp_b_rci_high_winrate_search_trades.csv"

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
    out["upper_wick_ratio"] = (high - pd.concat([open_, close], axis=1).max(axis=1)) / candle_range
    out["lower_wick_ratio"] = (pd.concat([open_, close], axis=1).min(axis=1) - low) / candle_range
    out["close_change_1_atr"] = close.diff() / out["atr14"].replace(0, np.nan)
    out["close_change_3_atr"] = (close - close.shift(3)) / out["atr14"].replace(0, np.nan)
    out["close_ema20_gap_atr"] = (close - out["ema20"]) / out["atr14"].replace(0, np.nan)
    out["close_ema50_gap_atr"] = (close - out["ema50"]) / out["atr14"].replace(0, np.nan)
    out["range20_atr"] = (high.rolling(20, min_periods=1).max() - low.rolling(20, min_periods=1).min()) / out[
        "atr14"
    ].replace(0, np.nan)

    for period in [9, 26, 52]:
        out[f"rci{period}"] = rci_series(close, period)
        out[f"rci{period}_delta"] = out[f"rci{period}"].diff()

    return out


def join_h1(m15: pd.DataFrame, h1: pd.DataFrame) -> pd.DataFrame:
    h1_cols = [
        "time",
        "ema_align",
        "macd_hist",
        "macd_delta",
        "macd_delta3",
        "rci9",
        "rci26",
        "rci52",
        "rci9_delta",
        "rci26_delta",
        "rci52_delta",
        "close_change_3_atr",
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
) -> pd.DataFrame:
    buy = buy_mask.fillna(False).to_numpy(dtype=bool)
    sell = sell_mask.fillna(False).to_numpy(dtype=bool)
    signals: list[tuple[int, str]] = []
    for i in range(start_bar, len(df) - 1):
        if buy[i]:
            signals.append((i, "BUY"))
        if sell[i]:
            signals.append((i, "SELL"))

    trades: list[dict[str, object]] = []
    blocked_until = -1
    for signal_idx, side in signals:
        if signal_idx <= blocked_until:
            continue
        entry_idx = signal_idx + 1
        if entry_idx >= len(df):
            continue
        entry = float(df.at[entry_idx, "open"])
        atr = float(df.at[signal_idx, "atr14"])
        if not np.isfinite(entry) or not np.isfinite(atr) or atr <= 0:
            continue

        if side == "BUY":
            sl = entry - risk_atr * atr
            tp = entry + rr * risk_atr * atr
        else:
            sl = entry + risk_atr * atr
            tp = entry - rr * risk_atr * atr

        exit_idx = min(entry_idx + max_bars, len(df) - 1)
        exit_price = float(df.at[exit_idx, "close"])
        exit_reason = "timeout"
        risk = abs(entry - sl)
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
                "rule_name": rule_name,
                "signal_idx": int(signal_idx),
                "signal_time": df.at[signal_idx, "time"],
                "entry_idx": int(entry_idx),
                "entry_time": df.at[entry_idx, "time"],
                "exit_idx": int(exit_idx),
                "exit_time": df.at[exit_idx, "time"],
                "side": side,
                "entry_price": entry,
                "sl": sl,
                "tp": tp,
                "exit_price": exit_price,
                "exit_reason": exit_reason,
                "bars_held": int(exit_idx - entry_idx + 1),
                "r": float(r_value),
                "result": "win" if r_value > 0 else "loss" if r_value < 0 else "breakeven",
                "jst_entry_hour": int(pd.Timestamp(df.at[entry_idx, "time"]).hour),
                "h1_ema_align": df.at[signal_idx, "h1_ema_align"],
                "h1_macd_delta3": df.at[signal_idx, "h1_macd_delta3"],
                "h1_rci26": df.at[signal_idx, "h1_rci26"],
                "h1_rci26_delta": df.at[signal_idx, "h1_rci26_delta"],
                "m15_rci9": df.at[signal_idx, "rci9"],
                "m15_rci26": df.at[signal_idx, "rci26"],
                "m15_gap20_atr": df.at[signal_idx, "close_ema20_gap_atr"],
                "m15_close_change_3_atr": df.at[signal_idx, "close_change_3_atr"],
            }
        )
        blocked_until = exit_idx + cooldown_bars

    return pd.DataFrame(trades)


def summarize_trades(trades: pd.DataFrame, *, rule_name: str, description: str, raw_buy: int, raw_sell: int) -> dict[str, object]:
    if trades.empty:
        return {
            "rule_name": rule_name,
            "description": description,
            "raw_buy_signals": raw_buy,
            "raw_sell_signals": raw_sell,
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
            "trades_per_month": None,
        }
    r = pd.to_numeric(trades["r"], errors="coerce")
    wins = int((r > 0).sum())
    losses = int((r < 0).sum())
    buy = trades[trades["side"] == "BUY"]
    sell = trades[trades["side"] == "SELL"]
    months = max(1.0, (pd.Timestamp(trades["entry_time"].max()) - pd.Timestamp(trades["entry_time"].min())).days / 30.4375)
    return {
        "rule_name": rule_name,
        "description": description,
        "raw_buy_signals": raw_buy,
        "raw_sell_signals": raw_sell,
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
        "trades_per_month": float(len(trades) / months),
    }


def build_rule_masks(
    df: pd.DataFrame,
    *,
    ema_touch_atr: float,
    buy_gap_min: float,
    buy_gap_max: float,
    sell_gap_min: float,
    sell_gap_max: float,
    rci9_buy_max: float,
    rci9_sell_min: float,
    rci26_buy_min: float,
    rci26_sell_max: float,
    require_rci26_delta: bool,
    require_h1_rci26_side: bool,
    max_abs_close_change3: float | None,
    min_body_ratio: float | None,
) -> tuple[pd.Series, pd.Series, str]:
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

    if require_rci26_delta:
        rci_buy &= df["rci26_delta"] > 0
        rci_sell &= df["rci26_delta"] < 0

    if require_h1_rci26_side:
        rci_buy &= (df["h1_rci26"] > 0) & (df["h1_rci26_delta"] > 0)
        rci_sell &= (df["h1_rci26"] < 0) & (df["h1_rci26_delta"] < 0)

    extension_ok_buy = pd.Series(True, index=df.index)
    extension_ok_sell = pd.Series(True, index=df.index)
    if max_abs_close_change3 is not None:
        extension_ok_buy &= df["close_change_3_atr"].abs() <= max_abs_close_change3
        extension_ok_sell &= df["close_change_3_atr"].abs() <= max_abs_close_change3

    body_ok = pd.Series(True, index=df.index)
    if min_body_ratio is not None:
        body_ok &= df["body_ratio"] >= min_body_ratio

    buy = h1_bull & h1_macd_buy & near_ema20_buy & m15_macd_buy & gap_buy & rci_buy & extension_ok_buy & body_ok
    sell = h1_bear & h1_macd_sell & near_ema20_sell & m15_macd_sell & gap_sell & rci_sell & extension_ok_sell & body_ok

    rule = (
        f"touch{ema_touch_atr}_gapB{buy_gap_min}:{buy_gap_max}_gapS{sell_gap_min}:{sell_gap_max}"
        f"_rci9B<={rci9_buy_max}_rci9S>={rci9_sell_min}"
        f"_rci26B>={rci26_buy_min}_rci26S<={rci26_sell_max}"
        f"_rci26delta{int(require_rci26_delta)}_h1rci{int(require_h1_rci26_side)}"
        f"_chg3{max_abs_close_change3}_body{min_body_ratio}"
    )
    return buy, sell, rule


def grid_search(
    df: pd.DataFrame,
    *,
    rr: float,
    risk_atr: float,
    max_bars: int,
    cooldown_bars: int,
    start_bar: int,
    min_trades: int,
    min_win_rate: float,
    min_pf: float,
    keep_top: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows: list[dict[str, object]] = []
    trade_frames: list[pd.DataFrame] = []

    ema_touch_values = [0.10, 0.15, 0.20, 0.30]
    buy_gap_ranges = [(-0.20, 0.50), (-0.10, 0.60), (0.00, 0.70), (-0.20, 0.80)]
    sell_gap_ranges = [(-0.50, 0.20), (-0.60, 0.10), (-0.70, 0.00), (-0.80, 0.20)]
    rci9_pairs = [(20, -20), (10, -10), (0, 0), (-20, 20), (-40, 40)]
    rci26_pairs = [(-80, 80), (-60, 60), (-40, 40), (-20, 20), (0, 0)]
    require_rci26_delta_values = [False, True]
    require_h1_rci26_side_values = [False, True]
    max_abs_close_change3_values: list[float | None] = [None, 1.20, 0.90, 0.70]
    min_body_ratio_values: list[float | None] = [None, 0.20, 0.30]

    tested = 0
    for (
        ema_touch,
        buy_gap,
        sell_gap,
        rci9_pair,
        rci26_pair,
        require_rci26_delta,
        require_h1_rci26_side,
        max_abs_close_change3,
        min_body_ratio,
    ) in product(
        ema_touch_values,
        buy_gap_ranges,
        sell_gap_ranges,
        rci9_pairs,
        rci26_pairs,
        require_rci26_delta_values,
        require_h1_rci26_side_values,
        max_abs_close_change3_values,
        min_body_ratio_values,
    ):
        tested += 1
        buy, sell, rule_name = build_rule_masks(
            df,
            ema_touch_atr=ema_touch,
            buy_gap_min=buy_gap[0],
            buy_gap_max=buy_gap[1],
            sell_gap_min=sell_gap[0],
            sell_gap_max=sell_gap[1],
            rci9_buy_max=rci9_pair[0],
            rci9_sell_min=rci9_pair[1],
            rci26_buy_min=rci26_pair[0],
            rci26_sell_max=rci26_pair[1],
            require_rci26_delta=require_rci26_delta,
            require_h1_rci26_side=require_h1_rci26_side,
            max_abs_close_change3=max_abs_close_change3,
            min_body_ratio=min_body_ratio,
        )
        raw_buy = int(buy.fillna(False).sum())
        raw_sell = int(sell.fillna(False).sum())
        if raw_buy + raw_sell < min_trades:
            continue

        trades = backtest_mask(
            df,
            buy,
            sell,
            rule_name=rule_name,
            rr=rr,
            risk_atr=risk_atr,
            max_bars=max_bars,
            cooldown_bars=cooldown_bars,
            start_bar=start_bar,
        )
        summary = summarize_trades(trades, rule_name=rule_name, description="grid_search_candidate", raw_buy=raw_buy, raw_sell=raw_sell)
        if summary["trades"] < min_trades:
            continue
        if summary["win_rate"] is None or float(summary["win_rate"]) < min_win_rate:
            continue
        if summary["pf"] is None or float(summary["pf"]) < min_pf:
            continue

        summary.update(
            {
                "ema_touch_atr": ema_touch,
                "buy_gap_min": buy_gap[0],
                "buy_gap_max": buy_gap[1],
                "sell_gap_min": sell_gap[0],
                "sell_gap_max": sell_gap[1],
                "rci9_buy_max": rci9_pair[0],
                "rci9_sell_min": rci9_pair[1],
                "rci26_buy_min": rci26_pair[0],
                "rci26_sell_max": rci26_pair[1],
                "require_rci26_delta": require_rci26_delta,
                "require_h1_rci26_side": require_h1_rci26_side,
                "max_abs_close_change3": max_abs_close_change3,
                "min_body_ratio": min_body_ratio,
                "tested_rules": tested,
            }
        )
        rows.append(summary)
        if not trades.empty:
            trade_frames.append(trades.assign(search_rule_name=rule_name))

    summary_df = pd.DataFrame(rows)
    if not summary_df.empty:
        summary_df = summary_df.sort_values(
            ["win_rate", "pf", "total_r", "trades"],
            ascending=[False, False, False, False],
            kind="mergesort",
        ).head(keep_top)
        keep_names = set(summary_df["rule_name"].tolist())
        if trade_frames:
            trades_df = pd.concat(trade_frames, ignore_index=True)
            trades_df = trades_df[trades_df["search_rule_name"].isin(keep_names)].copy()
        else:
            trades_df = pd.DataFrame()
    else:
        trades_df = pd.DataFrame()

    return summary_df, trades_df


def write_csv(path: Path, df: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig", quoting=csv.QUOTE_MINIMAL)


def print_table(title: str, df: pd.DataFrame) -> None:
    print("\n" + "=" * 120)
    print(title)
    print("=" * 120)
    print(df.to_string(index=False) if not df.empty else "No data.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Search BTCUSD# B/RCI high win-rate candidates.")
    parser.add_argument("--m15-csv", type=Path, default=DEFAULT_M15_CSV)
    parser.add_argument("--h1-csv", type=Path, default=DEFAULT_H1_CSV)
    parser.add_argument("--out-summary", type=Path, default=DEFAULT_OUT_SUMMARY)
    parser.add_argument("--out-trades", type=Path, default=DEFAULT_OUT_TRADES)
    parser.add_argument("--rr", type=float, default=1.5)
    parser.add_argument("--risk-atr", type=float, default=1.0)
    parser.add_argument("--max-bars", type=int, default=96)
    parser.add_argument("--cooldown-bars", type=int, default=4)
    parser.add_argument("--start-bar", type=int, default=220)
    parser.add_argument("--min-trades", type=int, default=70)
    parser.add_argument("--min-win-rate", type=float, default=0.60)
    parser.add_argument("--min-pf", type=float, default=2.0)
    parser.add_argument("--keep-top", type=int, default=50)
    args = parser.parse_args()

    m15_csv = resolve_path(args.m15_csv)
    h1_csv = resolve_path(args.h1_csv)
    out_summary = resolve_path(args.out_summary)
    out_trades = resolve_path(args.out_trades)

    m15 = add_indicators(read_ohlc(m15_csv))
    h1 = add_indicators(read_ohlc(h1_csv))
    df = join_h1(m15, h1)

    summary, trades = grid_search(
        df,
        rr=args.rr,
        risk_atr=args.risk_atr,
        max_bars=args.max_bars,
        cooldown_bars=args.cooldown_bars,
        start_bar=args.start_bar,
        min_trades=args.min_trades,
        min_win_rate=args.min_win_rate,
        min_pf=args.min_pf,
        keep_top=args.keep_top,
    )

    write_csv(out_summary, summary)
    write_csv(out_trades, trades)

    print("M15 rows:", len(m15), m15_csv, m15["time"].min(), "to", m15["time"].max())
    print("H1 rows:", len(h1), h1_csv, h1["time"].min(), "to", h1["time"].max())
    print("RR:", args.rr, "risk_atr:", args.risk_atr, "max_bars:", args.max_bars)
    print("Filters:", "min_trades", args.min_trades, "min_win_rate", args.min_win_rate, "min_pf", args.min_pf)
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
        "ema_touch_atr",
        "rci9_buy_max",
        "rci9_sell_min",
        "rci26_buy_min",
        "rci26_sell_max",
        "require_rci26_delta",
        "require_h1_rci26_side",
        "max_abs_close_change3",
        "min_body_ratio",
    ]
    display_cols = [col for col in display_cols if col in summary.columns]
    print_table("BTCUSD# B/RCI HIGH WIN-RATE SEARCH TOP", summary[display_cols].head(20) if not summary.empty else summary)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
