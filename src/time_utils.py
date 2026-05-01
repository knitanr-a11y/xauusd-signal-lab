from __future__ import annotations

from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import pandas as pd


JST_TIMEZONE = "Asia/Tokyo"
DEFAULT_MT5_SERVER_TIMEZONE = "Europe/Athens"
DEFAULT_MT5_SERVER_UTC_OFFSET_HOURS = 3


def _localize_naive_series(
    series: pd.Series,
    timezone_name: str,
) -> pd.Series:
    """Localize a naive datetime series to a real timezone.

    MT5 broker server time is often EET/EEST:
        winter: UTC+2
        summer: UTC+3

    `Europe/Athens` is a practical default because it has that DST behavior.

    Notes:
        - ambiguous='infer' handles repeated times around DST end when possible.
        - nonexistent='shift_forward' handles skipped times around DST start.
        - FX/CFD markets are usually closed during the weekend DST switch, so this
          should normally not affect M15/H1 trading data.
    """
    try:
        ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as exc:
        raise ValueError(
            f"Timezone not found: {timezone_name}. "
            "Use an IANA timezone name like Europe/Athens or Asia/Tokyo."
        ) from exc

    dt = pd.to_datetime(series)
    try:
        return dt.dt.tz_localize(timezone_name, ambiguous="infer", nonexistent="shift_forward")
    except Exception:
        # Fallback for rare cases where pandas cannot infer repeated DST times.
        return dt.dt.tz_localize(timezone_name, ambiguous="NaT", nonexistent="shift_forward")


def add_time_columns(
    df: pd.DataFrame,
    time_col: str = "time",
    server_timezone: str = DEFAULT_MT5_SERVER_TIMEZONE,
    fallback_server_utc_offset_hours: int = DEFAULT_MT5_SERVER_UTC_OFFSET_HOURS,
    use_fixed_offset: bool = False,
) -> pd.DataFrame:
    """Add server/UTC/JST helper columns from MT5 server time.

    Recommended mode:
        use_fixed_offset=False
        server_timezone="Europe/Athens"

    Why:
        The user confirmed that JST 14:10 = MT5 server 08:10 during summer time.
        That means MT5 server time is UTC+3 in summer. Many FX brokers use
        EET/EEST server time, which is UTC+2 in winter and UTC+3 in summer.
        Using a real timezone avoids a 1-hour error after DST changes.

    Fallback mode:
        use_fixed_offset=True
        fallback_server_utc_offset_hours=3

    The returned datetime columns are timezone-naive for easier CSV output and grouping,
    but the conversion itself is timezone-aware when use_fixed_offset=False.
    """
    if time_col not in df.columns:
        raise ValueError(f"Missing time column: {time_col}")

    out = df.copy()
    server_time = pd.to_datetime(out[time_col])

    out["server_time"] = server_time
    out["server_hour"] = server_time.dt.hour
    out["server_weekday"] = server_time.dt.day_name()

    if use_fixed_offset:
        out["utc_time"] = server_time - pd.to_timedelta(fallback_server_utc_offset_hours, unit="h")
        out["jst_time"] = out["utc_time"] + pd.to_timedelta(9, unit="h")
    else:
        server_aware = _localize_naive_series(server_time, server_timezone)
        utc_aware = server_aware.dt.tz_convert("UTC")
        jst_aware = server_aware.dt.tz_convert(JST_TIMEZONE)

        out["utc_time"] = utc_aware.dt.tz_localize(None)
        out["jst_time"] = jst_aware.dt.tz_localize(None)

    out["utc_hour"] = out["utc_time"].dt.hour
    out["utc_weekday"] = out["utc_time"].dt.day_name()

    out["jst_hour"] = out["jst_time"].dt.hour
    out["jst_weekday"] = out["jst_time"].dt.day_name()
    out["jst_month"] = out["jst_time"].dt.to_period("M").astype(str)

    return out


def convert_server_time_to_jst(
    value: pd.Series | pd.Timestamp,
    server_timezone: str = DEFAULT_MT5_SERVER_TIMEZONE,
    fallback_server_utc_offset_hours: int = DEFAULT_MT5_SERVER_UTC_OFFSET_HOURS,
    use_fixed_offset: bool = False,
) -> pd.Series | pd.Timestamp:
    """Convert MT5 server time to JST.

    Accepts either a pandas Series or a single Timestamp-like value.
    """
    if isinstance(value, pd.Series):
        temp = pd.DataFrame({"time": value})
        return add_time_columns(
            temp,
            time_col="time",
            server_timezone=server_timezone,
            fallback_server_utc_offset_hours=fallback_server_utc_offset_hours,
            use_fixed_offset=use_fixed_offset,
        )["jst_time"]

    series = pd.Series([value])
    return convert_server_time_to_jst(
        series,
        server_timezone=server_timezone,
        fallback_server_utc_offset_hours=fallback_server_utc_offset_hours,
        use_fixed_offset=use_fixed_offset,
    ).iloc[0]


def server_to_jst_delta_hours(server_utc_offset_hours: int) -> int:
    """Fixed-offset helper kept for backwards compatibility.

    Prefer timezone-aware conversion via `server_timezone` for DST-safe analysis.
    """
    return 9 - server_utc_offset_hours
