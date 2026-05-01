from __future__ import annotations

import pandas as pd


JST_UTC_OFFSET_HOURS = 9
DEFAULT_MT5_SERVER_UTC_OFFSET_HOURS = 3


def add_time_columns(
    df: pd.DataFrame,
    time_col: str = "time",
    server_utc_offset_hours: int = DEFAULT_MT5_SERVER_UTC_OFFSET_HOURS,
) -> pd.DataFrame:
    """Add UTC/JST helper columns from MT5 server time.

    Current project assumption:
        JST 14:10 = MT5 server 08:10
        Therefore MT5 server time = UTC+3, because JST = UTC+9.

    This function treats the source `time` column as naive MT5 server time.
    It does not localize with timezone-aware timestamps yet; it adds practical
    naive datetime columns for grouping and backtest summaries.
    """
    if time_col not in df.columns:
        raise ValueError(f"Missing time column: {time_col}")

    out = df.copy()
    server_time = pd.to_datetime(out[time_col])

    out["server_time"] = server_time
    out["server_hour"] = server_time.dt.hour
    out["server_weekday"] = server_time.dt.day_name()

    out["utc_time"] = server_time - pd.to_timedelta(server_utc_offset_hours, unit="h")
    out["utc_hour"] = out["utc_time"].dt.hour
    out["utc_weekday"] = out["utc_time"].dt.day_name()

    jst_delta_hours = JST_UTC_OFFSET_HOURS - server_utc_offset_hours
    out["jst_time"] = server_time + pd.to_timedelta(jst_delta_hours, unit="h")
    out["jst_hour"] = out["jst_time"].dt.hour
    out["jst_weekday"] = out["jst_time"].dt.day_name()
    out["jst_month"] = out["jst_time"].dt.to_period("M").astype(str)

    return out


def server_to_jst_delta_hours(server_utc_offset_hours: int) -> int:
    return JST_UTC_OFFSET_HOURS - server_utc_offset_hours
