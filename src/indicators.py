from __future__ import annotations

import pandas as pd


OHLC_REQUIRED_COLUMNS = ["open", "high", "low", "close"]


def validate_ohlc_columns(df: pd.DataFrame) -> None:
    missing = [col for col in OHLC_REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(f"Missing OHLC columns: {missing}")


def ema(series: pd.Series, period: int) -> pd.Series:
    """Calculate EMA using pandas ewm.

    This follows the common EMA formula used by many charting platforms:
        alpha = 2 / (period + 1)

    Notes:
        TradingView/Pine ta.ema also uses EMA with alpha = 2 / (length + 1),
        but exact early-bar values can differ depending on initialization and
        available history. For MACD comparison, compare values after enough warmup bars.
    """
    if period <= 0:
        raise ValueError(f"EMA period must be positive: {period}")
    return series.ewm(span=period, adjust=False, min_periods=period).mean()


def add_ema_columns(
    df: pd.DataFrame,
    periods: tuple[int, ...] = (20, 50),
    price_col: str = "close",
) -> pd.DataFrame:
    if price_col not in df.columns:
        raise ValueError(f"Missing price column: {price_col}")

    out = df.copy()
    for period in periods:
        out[f"ema_{period}"] = ema(out[price_col], period)
    return out


def macd(
    close: pd.Series,
    fast: int = 6,
    slow: int = 13,
    signal: int = 4,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Calculate MACD line, signal line and histogram.

    Initial project default is MACD 6,13,4 to match the TradingView/Pine settings
    used for this project.
    """
    if fast <= 0 or slow <= 0 or signal <= 0:
        raise ValueError("MACD periods must be positive")
    if fast >= slow:
        raise ValueError(f"MACD fast period must be smaller than slow period: fast={fast}, slow={slow}")

    fast_ema = ema(close, fast)
    slow_ema = ema(close, slow)
    macd_line = fast_ema - slow_ema
    signal_line = ema(macd_line, signal)
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def add_macd_columns(
    df: pd.DataFrame,
    fast: int = 6,
    slow: int = 13,
    signal: int = 4,
    price_col: str = "close",
) -> pd.DataFrame:
    if price_col not in df.columns:
        raise ValueError(f"Missing price column: {price_col}")

    out = df.copy()
    macd_line, signal_line, histogram = macd(out[price_col], fast=fast, slow=slow, signal=signal)
    out["macd_line"] = macd_line
    out["macd_signal"] = signal_line
    out["macd_hist"] = histogram
    out["macd_hist_diff"] = out["macd_hist"].diff()
    return out


def true_range(df: pd.DataFrame) -> pd.Series:
    validate_ohlc_columns(df)

    high_low = df["high"] - df["low"]
    high_prev_close = (df["high"] - df["close"].shift(1)).abs()
    low_prev_close = (df["low"] - df["close"].shift(1)).abs()

    tr = pd.concat([high_low, high_prev_close, low_prev_close], axis=1).max(axis=1)
    return tr


def atr(df: pd.DataFrame, period: int = 14, method: str = "wilder") -> pd.Series:
    """Calculate ATR.

    method:
        - "wilder": RMA-like smoothing, commonly used for ATR
        - "sma": simple moving average of true range
        - "ema": EMA of true range
    """
    if period <= 0:
        raise ValueError(f"ATR period must be positive: {period}")

    tr = true_range(df)
    method_lower = method.lower()

    if method_lower == "wilder":
        return tr.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    if method_lower == "sma":
        return tr.rolling(window=period, min_periods=period).mean()
    if method_lower == "ema":
        return tr.ewm(span=period, adjust=False, min_periods=period).mean()

    raise ValueError(f"Unsupported ATR method: {method}")


def add_atr_columns(
    df: pd.DataFrame,
    period: int = 14,
    method: str = "wilder",
) -> pd.DataFrame:
    out = df.copy()
    out["true_range"] = true_range(out)
    out[f"atr_{period}"] = atr(out, period=period, method=method)
    return out


def add_basic_indicators(
    df: pd.DataFrame,
    ema_periods: tuple[int, ...] = (20, 50),
    macd_fast: int = 6,
    macd_slow: int = 13,
    macd_signal: int = 4,
    atr_period: int = 14,
    atr_method: str = "wilder",
) -> pd.DataFrame:
    """Add the initial indicator set used by the project.

    Adds:
        - EMA columns for ema_periods
        - MACD 6,13,4 by default
        - MACD histogram diff
        - True range
        - ATR 14 by default
    """
    validate_ohlc_columns(df)

    out = df.copy()
    out = add_ema_columns(out, periods=ema_periods)
    out = add_macd_columns(out, fast=macd_fast, slow=macd_slow, signal=macd_signal)
    out = add_atr_columns(out, period=atr_period, method=atr_method)
    return out


def indicator_null_summary(df: pd.DataFrame) -> dict[str, int]:
    indicator_cols = [
        col
        for col in df.columns
        if col.startswith("ema_")
        or col.startswith("macd_")
        or col.startswith("atr_")
        or col == "true_range"
    ]
    return {col: int(df[col].isna().sum()) for col in indicator_cols}
