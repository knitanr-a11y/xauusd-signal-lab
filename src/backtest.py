from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class BacktestSettings:
    rr: float = 1.5
    sl_buffer_atr_multiplier: float = 0.05
    atr_col: str = "atr_14"
    conservative_same_bar: bool = True
    max_bars_in_trade: int | None = None

    def validate(self) -> None:
        if self.rr <= 0:
            raise ValueError(f"rr must be positive: {self.rr}")
        if self.sl_buffer_atr_multiplier < 0:
            raise ValueError(f"sl_buffer_atr_multiplier must be >= 0: {self.sl_buffer_atr_multiplier}")
        if self.max_bars_in_trade is not None and self.max_bars_in_trade <= 0:
            raise ValueError(f"max_bars_in_trade must be positive or None: {self.max_bars_in_trade}")


def _profit_factor(r_values: list[float]) -> float | None:
    gross_win = sum(r for r in r_values if r > 0)
    gross_loss = -sum(r for r in r_values if r < 0)
    if gross_loss == 0:
        return None if gross_win == 0 else float("inf")
    return gross_win / gross_loss


def _max_consecutive_losses(r_values: list[float]) -> int:
    max_losses = 0
    current = 0
    for r in r_values:
        if r < 0:
            current += 1
            max_losses = max(max_losses, current)
        else:
            current = 0
    return max_losses


def _max_drawdown_r(r_values: list[float]) -> float:
    equity = 0.0
    peak = 0.0
    max_dd = 0.0
    for r in r_values:
        equity += r
        peak = max(peak, equity)
        dd = peak - equity
        max_dd = max(max_dd, dd)
    return max_dd


def _build_trade_record(
    *,
    side: str,
    signal_index: int,
    entry_index: int,
    exit_index: int,
    df: pd.DataFrame,
    entry_price: float,
    sl: float,
    tp: float,
    risk: float,
    result: str,
    r_value: float,
    exit_reason: str,
) -> dict[str, object]:
    signal_row = df.iloc[signal_index]
    entry_row = df.iloc[entry_index]
    exit_row = df.iloc[exit_index]

    return {
        "side": side,
        "signal_index": signal_index,
        "entry_index": entry_index,
        "exit_index": exit_index,
        "signal_time": signal_row["time"],
        "entry_time": entry_row["time"],
        "exit_time": exit_row["time"],
        "entry_price": entry_price,
        "sl": sl,
        "tp": tp,
        "risk": risk,
        "result": result,
        "r": r_value,
        "exit_reason": exit_reason,
        "bars_held": exit_index - entry_index + 1,
        "h1_time": signal_row.get("h1_time", pd.NaT),
        "h1_trend": signal_row.get("h1_trend", ""),
        "signal_close": signal_row.get("close", pd.NA),
        "signal_macd": signal_row.get("macd_line", pd.NA),
        "signal_atr": signal_row.get("atr_14", pd.NA),
        "last_swing_low_time": signal_row.get("last_confirmed_swing_low_time", pd.NaT),
        "last_swing_low_price": signal_row.get("last_confirmed_swing_low_price", pd.NA),
        "last_swing_high_time": signal_row.get("last_confirmed_swing_high_time", pd.NaT),
        "last_swing_high_price": signal_row.get("last_confirmed_swing_high_price", pd.NA),
    }


def run_simple_hidden_divergence_backtest(
    df: pd.DataFrame,
    settings: BacktestSettings | None = None,
) -> pd.DataFrame:
    settings = settings or BacktestSettings()
    settings.validate()

    required = [
        "time",
        "open",
        "high",
        "low",
        "close",
        settings.atr_col,
        "hidden_bullish_divergence",
        "hidden_bearish_divergence",
        "last_confirmed_swing_low_price",
        "last_confirmed_swing_high_price",
    ]
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required backtest columns: {missing}")

    data = df.copy().sort_values("time", kind="mergesort").reset_index(drop=True)
    trades: list[dict[str, object]] = []

    i = 0
    n = len(data)

    while i < n - 1:
        row = data.iloc[i]

        side: str | None = None
        if bool(row["hidden_bullish_divergence"]):
            side = "BUY"
        elif bool(row["hidden_bearish_divergence"]):
            side = "SELL"

        if side is None:
            i += 1
            continue

        entry_index = i + 1
        if entry_index >= n:
            break

        entry_price = float(data.at[entry_index, "open"])
        atr_value = data.at[i, settings.atr_col]
        if pd.isna(atr_value):
            i += 1
            continue

        buffer = float(atr_value) * settings.sl_buffer_atr_multiplier

        if side == "BUY":
            swing_low = row["last_confirmed_swing_low_price"]
            if pd.isna(swing_low):
                i += 1
                continue
            sl = float(swing_low) - buffer
            risk = entry_price - sl
            if risk <= 0:
                i += 1
                continue
            tp = entry_price + risk * settings.rr
        else:
            swing_high = row["last_confirmed_swing_high_price"]
            if pd.isna(swing_high):
                i += 1
                continue
            sl = float(swing_high) + buffer
            risk = sl - entry_price
            if risk <= 0:
                i += 1
                continue
            tp = entry_price - risk * settings.rr

        exit_index = entry_index
        result = "open"
        r_value = 0.0
        exit_reason = "not_closed"

        max_exit_index = n - 1
        if settings.max_bars_in_trade is not None:
            max_exit_index = min(max_exit_index, entry_index + settings.max_bars_in_trade - 1)

        for j in range(entry_index, max_exit_index + 1):
            high = float(data.at[j, "high"])
            low = float(data.at[j, "low"])

            if side == "BUY":
                hit_sl = low <= sl
                hit_tp = high >= tp
            else:
                hit_sl = high >= sl
                hit_tp = low <= tp

            if hit_sl and hit_tp:
                exit_index = j
                if settings.conservative_same_bar:
                    result = "loss"
                    r_value = -1.0
                    exit_reason = "same_bar_sl_tp_loss"
                else:
                    result = "win"
                    r_value = settings.rr
                    exit_reason = "same_bar_sl_tp_win"
                break
            if hit_sl:
                exit_index = j
                result = "loss"
                r_value = -1.0
                exit_reason = "sl"
                break
            if hit_tp:
                exit_index = j
                result = "win"
                r_value = settings.rr
                exit_reason = "tp"
                break
        else:
            exit_index = max_exit_index
            result = "timeout" if settings.max_bars_in_trade is not None else "open_end"
            exit_reason = result
            final_close = float(data.at[exit_index, "close"])
            if side == "BUY":
                r_value = (final_close - entry_price) / risk
            else:
                r_value = (entry_price - final_close) / risk

        trades.append(
            _build_trade_record(
                side=side,
                signal_index=i,
                entry_index=entry_index,
                exit_index=exit_index,
                df=data,
                entry_price=entry_price,
                sl=sl,
                tp=tp,
                risk=risk,
                result=result,
                r_value=r_value,
                exit_reason=exit_reason,
            )
        )

        i = max(exit_index + 1, i + 1)

    return pd.DataFrame(trades)


def summarize_trades(trades: pd.DataFrame) -> dict[str, object]:
    if trades.empty:
        return {
            "trades": 0,
            "closed_trades": 0,
            "wins": 0,
            "losses": 0,
            "win_rate": 0.0,
            "average_r": 0.0,
            "total_r": 0.0,
            "profit_factor": None,
            "max_consecutive_losses": 0,
            "max_drawdown_r": 0.0,
        }

    closed = trades[trades["result"].isin(["win", "loss"])]
    r_values = closed["r"].astype(float).tolist()
    wins = int((closed["result"] == "win").sum())
    losses = int((closed["result"] == "loss").sum())
    closed_count = len(closed)

    return {
        "trades": int(len(trades)),
        "closed_trades": int(closed_count),
        "wins": wins,
        "losses": losses,
        "win_rate": wins / closed_count if closed_count else 0.0,
        "average_r": sum(r_values) / closed_count if closed_count else 0.0,
        "total_r": sum(r_values),
        "profit_factor": _profit_factor(r_values),
        "max_consecutive_losses": _max_consecutive_losses(r_values),
        "max_drawdown_r": _max_drawdown_r(r_values),
    }


def summarize_by_side(trades: pd.DataFrame) -> pd.DataFrame:
    if trades.empty:
        return pd.DataFrame()

    rows = []
    for side, group in trades.groupby("side", dropna=False):
        summary = summarize_trades(group)
        summary["side"] = side
        rows.append(summary)
    return pd.DataFrame(rows)[[
        "side",
        "trades",
        "closed_trades",
        "wins",
        "losses",
        "win_rate",
        "average_r",
        "total_r",
        "profit_factor",
        "max_consecutive_losses",
        "max_drawdown_r",
    ]]


def summarize_by_month(trades: pd.DataFrame, time_col: str = "entry_time", label: str = "entry_month") -> pd.DataFrame:
    if trades.empty:
        return pd.DataFrame()

    out = trades.copy()
    if time_col not in out.columns:
        raise ValueError(f"Missing time column for monthly summary: {time_col}")
    out[label] = pd.to_datetime(out[time_col]).dt.to_period("M").astype(str)
    rows = []
    for month, group in out.groupby(label, dropna=False):
        summary = summarize_trades(group)
        summary[label] = month
        rows.append(summary)
    return pd.DataFrame(rows).sort_values(label)


def summarize_by_entry_hour(trades: pd.DataFrame) -> pd.DataFrame:
    return summarize_by_hour(trades, time_col="entry_time", label="entry_hour")


def summarize_by_hour(trades: pd.DataFrame, time_col: str, label: str) -> pd.DataFrame:
    if trades.empty:
        return pd.DataFrame()

    out = trades.copy()
    if time_col not in out.columns:
        raise ValueError(f"Missing time column for hourly summary: {time_col}")
    out[label] = pd.to_datetime(out[time_col]).dt.hour
    rows = []
    for hour, group in out.groupby(label, dropna=False):
        summary = summarize_trades(group)
        summary[label] = int(hour)
        rows.append(summary)
    return pd.DataFrame(rows).sort_values(label)
