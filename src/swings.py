from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class SwingSettings:
    left: int = 3
    right: int = 2
    strict: bool = True

    def validate(self) -> None:
        if self.left <= 0:
            raise ValueError(f"left must be positive: {self.left}")
        if self.right <= 0:
            raise ValueError(f"right must be positive: {self.right}")


def _is_pivot_high(values: pd.Series, index: int, left: int, right: int, strict: bool) -> bool:
    center = values.iloc[index]
    if pd.isna(center):
        return False

    left_values = values.iloc[index - left:index]
    right_values = values.iloc[index + 1:index + right + 1]

    if left_values.isna().any() or right_values.isna().any():
        return False

    if strict:
        return bool((center > left_values.max()) and (center > right_values.max()))
    return bool((center >= left_values.max()) and (center >= right_values.max()))


def _is_pivot_low(values: pd.Series, index: int, left: int, right: int, strict: bool) -> bool:
    center = values.iloc[index]
    if pd.isna(center):
        return False

    left_values = values.iloc[index - left:index]
    right_values = values.iloc[index + 1:index + right + 1]

    if left_values.isna().any() or right_values.isna().any():
        return False

    if strict:
        return bool((center < left_values.min()) and (center < right_values.min()))
    return bool((center <= left_values.min()) and (center <= right_values.min()))


def add_swing_points(
    df: pd.DataFrame,
    left: int = 3,
    right: int = 2,
    strict: bool = True,
    high_col: str = "high",
    low_col: str = "low",
    macd_col: str = "macd_line",
) -> pd.DataFrame:
    """Add confirmed swing high/low information without look-ahead.

    Pivot rule:
        swing high: high is greater than left N highs and right N highs
        swing low : low is lower than left N lows and right N lows

    Important timing rule:
        If the pivot is at index i and right=2, the pivot is only known after
        the two right-side bars have closed. Since each row time is candle open,
        the first row allowed to use that swing is i + right + 1.
    """
    settings = SwingSettings(left=left, right=right, strict=strict)
    settings.validate()

    required = ["time", high_col, low_col]
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required swing columns: {missing}")

    out = df.copy().sort_values("time", kind="mergesort").reset_index(drop=True)
    n = len(out)

    out["swing_high"] = False
    out["swing_low"] = False
    out["swing_high_price"] = pd.NA
    out["swing_low_price"] = pd.NA
    out["swing_high_confirm_time"] = pd.NaT
    out["swing_low_confirm_time"] = pd.NaT
    out["swing_high_usable_time"] = pd.NaT
    out["swing_low_usable_time"] = pd.NaT

    high_event_price = pd.Series(pd.NA, index=out.index, dtype="Float64")
    high_event_time = pd.Series(pd.NaT, index=out.index, dtype="datetime64[ns]")
    high_event_confirm_time = pd.Series(pd.NaT, index=out.index, dtype="datetime64[ns]")
    high_event_macd = pd.Series(pd.NA, index=out.index, dtype="Float64")

    low_event_price = pd.Series(pd.NA, index=out.index, dtype="Float64")
    low_event_time = pd.Series(pd.NaT, index=out.index, dtype="datetime64[ns]")
    low_event_confirm_time = pd.Series(pd.NaT, index=out.index, dtype="datetime64[ns]")
    low_event_macd = pd.Series(pd.NA, index=out.index, dtype="Float64")

    for i in range(left, n - right):
        confirm_index = i + right
        usable_index = i + right + 1

        if usable_index >= n:
            continue

        confirm_time = out.at[confirm_index, "time"]
        usable_time = out.at[usable_index, "time"]

        if _is_pivot_high(out[high_col], i, left, right, strict):
            pivot_time = out.at[i, "time"]
            pivot_price = float(out.at[i, high_col])
            pivot_macd = float(out.at[i, macd_col]) if macd_col in out.columns and pd.notna(out.at[i, macd_col]) else pd.NA

            out.at[i, "swing_high"] = True
            out.at[i, "swing_high_price"] = pivot_price
            out.at[i, "swing_high_confirm_time"] = confirm_time
            out.at[i, "swing_high_usable_time"] = usable_time

            high_event_price.iloc[usable_index] = pivot_price
            high_event_time.iloc[usable_index] = pivot_time
            high_event_confirm_time.iloc[usable_index] = confirm_time
            high_event_macd.iloc[usable_index] = pivot_macd

        if _is_pivot_low(out[low_col], i, left, right, strict):
            pivot_time = out.at[i, "time"]
            pivot_price = float(out.at[i, low_col])
            pivot_macd = float(out.at[i, macd_col]) if macd_col in out.columns and pd.notna(out.at[i, macd_col]) else pd.NA

            out.at[i, "swing_low"] = True
            out.at[i, "swing_low_price"] = pivot_price
            out.at[i, "swing_low_confirm_time"] = confirm_time
            out.at[i, "swing_low_usable_time"] = usable_time

            low_event_price.iloc[usable_index] = pivot_price
            low_event_time.iloc[usable_index] = pivot_time
            low_event_confirm_time.iloc[usable_index] = confirm_time
            low_event_macd.iloc[usable_index] = pivot_macd

    out["last_confirmed_swing_high_price"] = high_event_price.ffill()
    out["last_confirmed_swing_high_time"] = high_event_time.ffill()
    out["last_confirmed_swing_high_confirm_time"] = high_event_confirm_time.ffill()
    out["last_confirmed_swing_high_macd"] = high_event_macd.ffill()

    out["last_confirmed_swing_low_price"] = low_event_price.ffill()
    out["last_confirmed_swing_low_time"] = low_event_time.ffill()
    out["last_confirmed_swing_low_confirm_time"] = low_event_confirm_time.ffill()
    out["last_confirmed_swing_low_macd"] = low_event_macd.ffill()

    return out


def swing_summary(df: pd.DataFrame) -> dict[str, object]:
    required = ["swing_high", "swing_low", "last_confirmed_swing_high_price", "last_confirmed_swing_low_price"]
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"Missing swing summary columns: {missing}")

    rows = len(df)
    high_count = int(df["swing_high"].sum())
    low_count = int(df["swing_low"].sum())
    rows_with_confirmed_high = int(df["last_confirmed_swing_high_price"].notna().sum())
    rows_with_confirmed_low = int(df["last_confirmed_swing_low_price"].notna().sum())

    high_lookahead = 0
    low_lookahead = 0

    if "last_confirmed_swing_high_confirm_time" in df.columns:
        high_mask = (
            df["last_confirmed_swing_high_confirm_time"].notna()
            & (df["last_confirmed_swing_high_confirm_time"] >= df["time"])
        )
        high_lookahead = int(high_mask.sum())

    if "last_confirmed_swing_low_confirm_time" in df.columns:
        low_mask = (
            df["last_confirmed_swing_low_confirm_time"].notna()
            & (df["last_confirmed_swing_low_confirm_time"] >= df["time"])
        )
        low_lookahead = int(low_mask.sum())

    return {
        "rows": rows,
        "swing_high_count": high_count,
        "swing_low_count": low_count,
        "rows_with_confirmed_high": rows_with_confirmed_high,
        "rows_with_confirmed_low": rows_with_confirmed_low,
        "high_lookahead_violations": high_lookahead,
        "low_lookahead_violations": low_lookahead,
    }
