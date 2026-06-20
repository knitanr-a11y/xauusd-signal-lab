from __future__ import annotations

from pathlib import Path
import pandas as pd

CALENDAR_COLUMNS = [
    'calendar_id','broker_or_server_id','symbol_group','server_timezone','session_date',
    'session_open_time','session_close_time','is_holiday_closed','is_short_session',
    'published_at','source_name','source_version',
]
TICK_COLUMNS = [
    'broker_or_server_id','symbol','time_utc','bid','ask','last','tick_volume_delta',
    'source_available_at','source_version',
]
EXTERNAL_COLUMNS = [
    'source_name','symbol','time_utc','source_available_at','open','high','low','close',
    'source_version',
]
MACRO_COLUMNS = [
    'event_id','event_name','scheduled_time_utc','importance','country','currency',
    'published_at','source_name','source_version',
]
BROKER_METADATA_COLUMNS = [
    'broker_or_server_id','broker_name','server_name','symbol','symbol_group',
    'server_timezone','price_digits','contract_description','source_name','source_version',
]


def _require(df: pd.DataFrame, columns: list[str], name: str) -> None:
    missing=[c for c in columns if c not in df.columns]
    if missing:
        raise ValueError(f'{name} missing columns: {missing}')


def validate_calendar(df: pd.DataFrame) -> pd.DataFrame:
    _require(df,CALENDAR_COLUMNS,'calendar')
    out=df.copy()
    for c in ['session_open_time','session_close_time','published_at']:
        out[c]=pd.to_datetime(out[c],errors='raise',utc=True)
    if (out.session_close_time<=out.session_open_time).any():
        raise ValueError('calendar close must be after open')
    if out.calendar_id.duplicated().any():
        raise ValueError('calendar_id must be unique')
    return out


def validate_ticks(df: pd.DataFrame) -> pd.DataFrame:
    _require(df,TICK_COLUMNS,'ticks')
    out=df.copy()
    for c in ['time_utc','source_available_at']:
        out[c]=pd.to_datetime(out[c],errors='raise',utc=True)
    if (out.source_available_at<out.time_utc).any():
        raise ValueError('source_available_at cannot precede tick time')
    if (pd.to_numeric(out.ask,errors='raise')<pd.to_numeric(out.bid,errors='raise')).any():
        raise ValueError('ask must be >= bid')
    return out.sort_values(['broker_or_server_id','symbol','time_utc']).reset_index(drop=True)


def validate_external(df: pd.DataFrame) -> pd.DataFrame:
    _require(df,EXTERNAL_COLUMNS,'external markets')
    out=df.copy()
    for c in ['time_utc','source_available_at']:
        out[c]=pd.to_datetime(out[c],errors='raise',utc=True)
    if (out.source_available_at<out.time_utc).any():
        raise ValueError('source_available_at cannot precede bar time')
    return out


def validate_macro(df: pd.DataFrame) -> pd.DataFrame:
    _require(df,MACRO_COLUMNS,'macro calendar')
    out=df.copy()
    for c in ['scheduled_time_utc','published_at']:
        out[c]=pd.to_datetime(out[c],errors='raise',utc=True)
    if (out.published_at>out.scheduled_time_utc).any():
        raise ValueError('macro schedule published after event cannot be pre-known')
    return out


def write_templates(directory: str | Path) -> None:
    p=Path(directory); p.mkdir(parents=True,exist_ok=True)
    pd.DataFrame(columns=CALENDAR_COLUMNS).to_csv(p/'stage262_broker_session_calendar_template.csv',index=False)
    pd.DataFrame(columns=TICK_COLUMNS).to_csv(p/'stage262_tick_data_template.csv',index=False)
    pd.DataFrame(columns=EXTERNAL_COLUMNS).to_csv(p/'stage262_external_market_template.csv',index=False)
    pd.DataFrame(columns=MACRO_COLUMNS).to_csv(p/'stage262_macro_calendar_template.csv',index=False)
    pd.DataFrame(columns=BROKER_METADATA_COLUMNS).to_csv(p/'stage262_broker_metadata_template.csv',index=False)
