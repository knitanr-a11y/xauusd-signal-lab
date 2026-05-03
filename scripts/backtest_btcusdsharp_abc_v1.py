from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_M15_CSV = PROJECT_ROOT / "data" / "raw" / "btcusdsharp_m15.csv"
DEFAULT_H1_CSV = PROJECT_ROOT / "data" / "raw" / "btcusdsharp_h1.csv"
DEFAULT_OUT_CSV = PROJECT_ROOT / "data" / "results" / "btcusdsharp_abc_v1_backtest_trades.csv"
DEFAULT_SUMMARY_CSV = PROJECT_ROOT / "data" / "results" / "btcusdsharp_abc_v1_backtest_summary.csv"

MACD_FAST = 6
MACD_SLOW = 13
MACD_SIGNAL = 4

Side = Literal["BUY", "SELL"]
Source = Literal["A", "B", "C"]


@dataclass(frozen=True)
class Signal:
    signal_idx: int
    signal_time: pd.Timestamp
    source: Source
    side: Side
    reason: str
    swing_ref_price: float | None = None


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
    out["time"] = pd.to_datetime(out["time"], errors="coerce")
    out = out.dropna(subset=["time"]).sort_values("time", kind="mergesort").reset_index(drop=True)
    for col in ["open", "high", "low", "close", "volume", "spread"]:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")
    return out


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    close = out["close"]
    high = out["high"]
    low = out["low"]
    open_ = out["open"]

    out["ema20"] = close.ewm(span=20, adjust=False).mean()
    out["ema50"] = close.ewm(span=50, adjust=False).mean()
    out["ema200"] = close.ewm(span=200, adjust=False).mean()

    prev_close = close.shift(1)
    tr = pd.concat([(high - low).abs(), (high - prev_close).abs(), (low - prev_close).abs()], axis=1).max(axis=1)
    out["atr14"] = tr.rolling(14, min_periods=1).mean()

    ema_fast = close.ewm(span=MACD_FAST, adjust=False).mean()
    ema_slow = close.ewm(span=MACD_SLOW, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    macd_signal = macd_line.ewm(span=MACD_SIGNAL, adjust=False).mean()
    macd_hist = macd_line - macd_signal
    out["macd_line"] = macd_line
    out["macd_signal"] = macd_signal
    out["macd_hist"] = macd_hist
    out["macd_hist_delta"] = macd_hist.diff()
    out["macd_hist_delta_3"] = macd_hist - macd_hist.shift(3)

    out["ema_alignment"] = "mixed"
    out.loc[(out["ema20"] > out["ema50"]) & (out["ema50"] > out["ema200"]), "ema_alignment"] = "bullish"
    out.loc[(out["ema20"] < out["ema50"]) & (out["ema50"] < out["ema200"]), "ema_alignment"] = "bearish"

    candle_range = (high - low).replace(0, pd.NA)
    body = (close - open_).abs()
    out["body_ratio"] = body / candle_range
    out["close_change_3_atr"] = (close - close.shift(3)) / out["atr14"].replace(0, pd.NA)
    out["close_vs_prev_high_atr"] = (close - high.shift(1)) / out["atr14"].replace(0, pd.NA)
    out["close_vs_prev_low_atr"] = (close - low.shift(1)) / out["atr14"].replace(0, pd.NA)
    out["pullback_from_high_5_atr"] = (high.rolling(5, min_periods=1).max() - close) / out["atr14"].replace(0, pd.NA)
    out["rebound_from_low_5_atr"] = (close - low.rolling(5, min_periods=1).min()) / out["atr14"].replace(0, pd.NA)
    return out


def join_h1_to_m15(m15: pd.DataFrame, h1: pd.DataFrame) -> pd.DataFrame:
    h1_cols = [
        "time",
        "open",
        "high",
        "low",
        "close",
        "ema20",
        "ema50",
        "ema200",
        "atr14",
        "macd_hist",
        "macd_hist_delta",
        "macd_hist_delta_3",
        "ema_alignment",
        "close_change_3_atr",
    ]
    h1_subset = h1[[col for col in h1_cols if col in h1.columns]].copy()
    h1_subset = h1_subset.rename(columns={col: f"h1_{col}" for col in h1_subset.columns if col != "time"})
    h1_subset = h1_subset.rename(columns={"time": "h1_time"})
    merged = pd.merge_asof(
        m15.sort_values("time"),
        h1_subset.sort_values("h1_time"),
        left_on="time",
        right_on="h1_time",
        direction="backward",
    )
    return merged.reset_index(drop=True)


def side_supported_by_h1(row: pd.Series, side: Side, *, strict: bool) -> bool:
    align = str(row.get("h1_ema_alignment", "mixed"))
    hist = float(row.get("h1_macd_hist", 0.0) or 0.0)
    delta3 = float(row.get("h1_macd_hist_delta_3", 0.0) or 0.0)
    if side == "BUY":
        if strict:
            return align == "bullish" and hist >= 0
        return align != "bearish" and (hist >= 0 or delta3 > 0)
    if strict:
        return align == "bearish" and hist <= 0
    return align != "bullish" and (hist <= 0 or delta3 < 0)


def find_confirmed_swings(df: pd.DataFrame, *, depth: int) -> tuple[pd.Series, pd.Series]:
    lows = df["low"]
    highs = df["high"]
    swing_low = pd.Series(False, index=df.index)
    swing_high = pd.Series(False, index=df.index)
    for i in range(depth, len(df) - depth):
        low_window = lows.iloc[i - depth : i + depth + 1]
        high_window = highs.iloc[i - depth : i + depth + 1]
        if lows.iloc[i] == low_window.min():
            swing_low.iloc[i] = True
        if highs.iloc[i] == high_window.max():
            swing_high.iloc[i] = True
    return swing_low, swing_high


def generate_a_hidden_divergence_signals(df: pd.DataFrame, *, depth: int) -> list[Signal]:
    swing_low, swing_high = find_confirmed_swings(df, depth=depth)
    signals: list[Signal] = []

    last_low_idx: int | None = None
    last_high_idx: int | None = None

    for pivot_idx in range(depth, len(df) - depth):
        confirm_idx = pivot_idx + depth
        if confirm_idx >= len(df) - 1:
            break

        if bool(swing_low.iloc[pivot_idx]):
            if last_low_idx is not None:
                price_higher_low = df.at[pivot_idx, "low"] > df.at[last_low_idx, "low"]
                macd_lower_low = df.at[pivot_idx, "macd_hist"] < df.at[last_low_idx, "macd_hist"]
                enough_gap = abs(df.at[pivot_idx, "low"] - df.at[last_low_idx, "low"]) / max(df.at[pivot_idx, "atr14"], 1e-9) >= 0.15
                if price_higher_low and macd_lower_low and enough_gap and side_supported_by_h1(df.iloc[confirm_idx], "BUY", strict=False):
                    signals.append(
                        Signal(
                            signal_idx=confirm_idx,
                            signal_time=df.at[confirm_idx, "time"],
                            source="A",
                            side="BUY",
                            reason="bullish_hidden_divergence_confirmed_swing_low",
                            swing_ref_price=float(df.at[pivot_idx, "low"]),
                        )
                    )
            last_low_idx = pivot_idx

        if bool(swing_high.iloc[pivot_idx]):
            if last_high_idx is not None:
                price_lower_high = df.at[pivot_idx, "high"] < df.at[last_high_idx, "high"]
                macd_higher_high = df.at[pivot_idx, "macd_hist"] > df.at[last_high_idx, "macd_hist"]
                enough_gap = abs(df.at[pivot_idx, "high"] - df.at[last_high_idx, "high"]) / max(df.at[pivot_idx, "atr14"], 1e-9) >= 0.15
                if price_lower_high and macd_higher_high and enough_gap and side_supported_by_h1(df.iloc[confirm_idx], "SELL", strict=False):
                    signals.append(
                        Signal(
                            signal_idx=confirm_idx,
                            signal_time=df.at[confirm_idx, "time"],
                            source="A",
                            side="SELL",
                            reason="bearish_hidden_divergence_confirmed_swing_high",
                            swing_ref_price=float(df.at[pivot_idx, "high"]),
                        )
                    )
            last_high_idx = pivot_idx

    return signals


def generate_b_ema_macd_signals(df: pd.DataFrame) -> list[Signal]:
    signals: list[Signal] = []
    for i in range(220, len(df) - 1):
        row = df.iloc[i]
        atr = float(row["atr14"])
        if atr <= 0:
            continue

        touched_ema_buy = row["low"] <= row["ema20"] + 0.15 * atr and row["close"] > row["ema20"]
        macd_reaccel_buy = row["macd_hist_delta"] > 0 and row["macd_hist_delta_3"] > 0 and row["close_change_3_atr"] > -0.10
        if touched_ema_buy and macd_reaccel_buy and side_supported_by_h1(row, "BUY", strict=True):
            signals.append(Signal(i, row["time"], "B", "BUY", "ema20_bounce_macd_reacceleration_buy"))

        touched_ema_sell = row["high"] >= row["ema20"] - 0.15 * atr and row["close"] < row["ema20"]
        macd_reaccel_sell = row["macd_hist_delta"] < 0 and row["macd_hist_delta_3"] < 0 and row["close_change_3_atr"] < 0.10
        if touched_ema_sell and macd_reaccel_sell and side_supported_by_h1(row, "SELL", strict=True):
            signals.append(Signal(i, row["time"], "B", "SELL", "ema20_bounce_macd_reacceleration_sell"))

    return signals


def generate_c_continuation_signals(df: pd.DataFrame) -> list[Signal]:
    signals: list[Signal] = []
    for i in range(220, len(df) - 1):
        row = df.iloc[i]
        if row["ema_alignment"] == "bullish" and side_supported_by_h1(row, "BUY", strict=True):
            if row["close_vs_prev_high_atr"] > 0.05 and row["macd_hist"] > 0 and row["macd_hist_delta_3"] > 0:
                if row["pullback_from_high_5_atr"] < 0.75:
                    signals.append(Signal(i, row["time"], "C", "BUY", "trend_continuation_break_prev_high_buy"))

        if row["ema_alignment"] == "bearish" and side_supported_by_h1(row, "SELL", strict=True):
            if row["close_vs_prev_low_atr"] < -0.05 and row["macd_hist"] < 0 and row["macd_hist_delta_3"] < 0:
                if row["rebound_from_low_5_atr"] < 0.75:
                    signals.append(Signal(i, row["time"], "C", "SELL", "trend_continuation_break_prev_low_sell"))

    return signals


def stop_for_signal(df: pd.DataFrame, signal: Signal, entry_idx: int, *, atr_buffer: float, min_risk_atr: float) -> tuple[float, float] | None:
    entry = float(df.at[entry_idx, "open"])
    atr = float(df.at[signal.signal_idx, "atr14"])
    buffer = atr * atr_buffer

    lookback = 8 if signal.source in {"A", "C"} else 5
    start = max(0, signal.signal_idx - lookback + 1)
    recent = df.iloc[start : signal.signal_idx + 1]

    if signal.side == "BUY":
        anchor = min(float(recent["low"].min()), signal.swing_ref_price if signal.swing_ref_price is not None else float("inf"))
        sl = anchor - buffer
        risk = entry - sl
    else:
        anchor = max(float(recent["high"].max()), signal.swing_ref_price if signal.swing_ref_price is not None else float("-inf"))
        sl = anchor + buffer
        risk = sl - entry

    if risk <= 0 or risk / max(atr, 1e-9) < min_risk_atr:
        return None
    return sl, risk


def backtest_signal(
    df: pd.DataFrame,
    signal: Signal,
    *,
    rr: float,
    atr_buffer: float,
    min_risk_atr: float,
    max_risk_atr: float,
    max_bars: int,
) -> dict[str, object] | None:
    entry_idx = signal.signal_idx + 1
    if entry_idx >= len(df):
        return None

    stop = stop_for_signal(df, signal, entry_idx, atr_buffer=atr_buffer, min_risk_atr=min_risk_atr)
    if stop is None:
        return None
    sl, risk = stop

    atr = float(df.at[signal.signal_idx, "atr14"])
    risk_atr = risk / max(atr, 1e-9)
    if risk_atr > max_risk_atr:
        return None

    entry_price = float(df.at[entry_idx, "open"])
    if signal.side == "BUY":
        tp = entry_price + rr * risk
    else:
        tp = entry_price - rr * risk

    exit_idx = min(entry_idx + max_bars, len(df) - 1)
    exit_price = float(df.at[exit_idx, "close"])
    exit_reason = "timeout"
    r_value = (exit_price - entry_price) / risk if signal.side == "BUY" else (entry_price - exit_price) / risk

    for j in range(entry_idx, min(entry_idx + max_bars, len(df) - 1) + 1):
        high = float(df.at[j, "high"])
        low = float(df.at[j, "low"])
        if signal.side == "BUY":
            # Conservative order if both happen in one candle: SL first.
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

    result = "win" if r_value > 0 else "loss" if r_value < 0 else "breakeven"
    entry_time = df.at[entry_idx, "time"]
    exit_time = df.at[exit_idx, "time"]

    return {
        "combined_signal_source": signal.source,
        "signal_reason": signal.reason,
        "side": signal.side,
        "signal_time": signal.signal_time,
        "entry_time": entry_time,
        "jst_entry_time": entry_time,
        "jst_entry_month": pd.Timestamp(entry_time).to_period("M").strftime("%Y-%m"),
        "jst_entry_hour": int(pd.Timestamp(entry_time).hour),
        "entry_price": entry_price,
        "sl": float(sl),
        "tp": float(tp),
        "risk": float(risk),
        "exit_time": exit_time,
        "exit_price": float(exit_price),
        "exit_reason": exit_reason,
        "bars_held": int(exit_idx - entry_idx + 1),
        "result": result,
        "r": float(r_value),
        "entry_risk_atr_ratio_raw": float(risk_atr),
        "m15_atr14_at_signal": float(atr),
        "source_signal_idx": int(signal.signal_idx),
        "entry_idx": int(entry_idx),
        "exit_idx": int(exit_idx),
    }


def collect_signals(df: pd.DataFrame, *, swing_depth: int) -> list[Signal]:
    signals = []
    signals.extend(generate_a_hidden_divergence_signals(df, depth=swing_depth))
    signals.extend(generate_b_ema_macd_signals(df))
    signals.extend(generate_c_continuation_signals(df))
    signals = sorted(signals, key=lambda s: (s.signal_idx, s.source, s.side))

    # Avoid exact duplicate source/side/time combinations.
    seen: set[tuple[int, Source, Side]] = set()
    unique: list[Signal] = []
    for sig in signals:
        key = (sig.signal_idx, sig.source, sig.side)
        if key in seen:
            continue
        seen.add(key)
        unique.append(sig)
    return unique


def run_backtest(
    df: pd.DataFrame,
    *,
    rr: float,
    atr_buffer: float,
    min_risk_atr: float,
    max_risk_atr: float,
    max_bars: int,
    cooldown_bars: int,
    swing_depth: int,
) -> pd.DataFrame:
    signals = collect_signals(df, swing_depth=swing_depth)
    trades: list[dict[str, object]] = []
    blocked_until_idx = -1

    for sig in signals:
        if sig.signal_idx <= blocked_until_idx:
            continue
        trade = backtest_signal(
            df,
            sig,
            rr=rr,
            atr_buffer=atr_buffer,
            min_risk_atr=min_risk_atr,
            max_risk_atr=max_risk_atr,
            max_bars=max_bars,
        )
        if trade is None:
            continue
        trades.append(trade)
        blocked_until_idx = int(trade["exit_idx"]) + cooldown_bars

    return pd.DataFrame(trades)


def summarize(trades: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    groups = [("all", []), ("source", ["combined_signal_source"]), ("source_side", ["combined_signal_source", "side"])]
    for group_name, cols in groups:
        if cols:
            iterator = trades.groupby(cols, dropna=False)
        else:
            iterator = [("all", trades)]
        for key, group in iterator:
            if not isinstance(key, tuple):
                key = (key,)
            r = pd.to_numeric(group["r"], errors="coerce")
            wins = r[r > 0]
            losses = r[r < 0]
            gross_win = float(wins.sum()) if len(wins) else 0.0
            gross_loss_abs = float(abs(losses.sum())) if len(losses) else 0.0
            row = {
                "group": group_name,
                "trades": int(len(group)),
                "wins": int((r > 0).sum()),
                "losses": int((r < 0).sum()),
                "win_rate": float((r > 0).sum() / len(group)) if len(group) else 0.0,
                "total_r": float(r.sum()) if len(group) else 0.0,
                "avg_r": float(r.mean()) if len(group) else 0.0,
                "pf": gross_win / gross_loss_abs if gross_loss_abs else None,
                "max_bars_held": int(group["bars_held"].max()) if len(group) else 0,
            }
            for col, value in zip(cols, key):
                row[col] = value
            rows.append(row)
    return pd.DataFrame(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="Exploratory BTCUSD# ABC v1 backtest from M15/H1 candles.")
    parser.add_argument("--m15-csv", type=Path, default=DEFAULT_M15_CSV)
    parser.add_argument("--h1-csv", type=Path, default=DEFAULT_H1_CSV)
    parser.add_argument("--out-csv", type=Path, default=DEFAULT_OUT_CSV)
    parser.add_argument("--summary-csv", type=Path, default=DEFAULT_SUMMARY_CSV)
    parser.add_argument("--rr", type=float, default=1.5)
    parser.add_argument("--atr-buffer", type=float, default=0.05)
    parser.add_argument("--min-risk-atr", type=float, default=0.20)
    parser.add_argument("--max-risk-atr", type=float, default=3.00)
    parser.add_argument("--max-bars", type=int, default=96)
    parser.add_argument("--cooldown-bars", type=int, default=4)
    parser.add_argument("--swing-depth", type=int, default=5)
    args = parser.parse_args()

    m15_csv = resolve_path(args.m15_csv)
    h1_csv = resolve_path(args.h1_csv)
    out_csv = resolve_path(args.out_csv)
    summary_csv = resolve_path(args.summary_csv)

    m15 = add_indicators(read_ohlc(m15_csv))
    h1 = add_indicators(read_ohlc(h1_csv))
    df = join_h1_to_m15(m15, h1)

    trades = run_backtest(
        df,
        rr=args.rr,
        atr_buffer=args.atr_buffer,
        min_risk_atr=args.min_risk_atr,
        max_risk_atr=args.max_risk_atr,
        max_bars=args.max_bars,
        cooldown_bars=args.cooldown_bars,
        swing_depth=args.swing_depth,
    )

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    summary_csv.parent.mkdir(parents=True, exist_ok=True)
    trades.to_csv(out_csv, index=False, encoding="utf-8-sig")
    summary = summarize(trades) if not trades.empty else pd.DataFrame()
    summary.to_csv(summary_csv, index=False, encoding="utf-8-sig")

    print("M15 rows:", len(m15), m15_csv, m15["time"].min(), "to", m15["time"].max())
    print("H1 rows:", len(h1), h1_csv, h1["time"].min(), "to", h1["time"].max())
    print("Trades:", len(trades))
    print("Saved trades:", out_csv)
    print("Saved summary:", summary_csv)
    if not summary.empty:
        print("\nSummary:")
        print(summary.to_string(index=False))
    if not trades.empty:
        print("\nPreview:")
        preview_cols = [
            "combined_signal_source",
            "side",
            "signal_time",
            "entry_time",
            "entry_price",
            "sl",
            "tp",
            "result",
            "r",
            "exit_reason",
            "bars_held",
        ]
        print(trades[preview_cols].head(20).to_string(index=False))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
