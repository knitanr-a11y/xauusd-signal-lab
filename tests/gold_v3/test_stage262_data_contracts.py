import pandas as pd
import pytest
from stage262_data_contracts import validate_calendar, validate_ticks, validate_macro


def test_calendar_valid():
    df=pd.DataFrame([{
        'calendar_id':'C1','broker_or_server_id':'S1','symbol_group':'GOLD','server_timezone':'UTC',
        'session_date':'2025-01-02','session_open_time':'2025-01-02T01:00:00Z','session_close_time':'2025-01-02T23:59:00Z',
        'is_holiday_closed':False,'is_short_session':False,'published_at':'2024-12-01T00:00:00Z',
        'source_name':'BROKER','source_version':'V1'}])
    assert len(validate_calendar(df))==1


def test_tick_ask_bid_guard():
    df=pd.DataFrame([{
        'broker_or_server_id':'S1','symbol':'GOLD','time_utc':'2025-01-02T10:00:00Z','bid':101,'ask':100,
        'last':100.5,'tick_volume_delta':1,'source_available_at':'2025-01-02T10:00:00Z','source_version':'V1'}])
    with pytest.raises(ValueError): validate_ticks(df)


def test_macro_must_be_preknown():
    df=pd.DataFrame([{
        'event_id':'E1','event_name':'NFP','scheduled_time_utc':'2025-01-03T13:30:00Z','importance':'HIGH',
        'country':'US','currency':'USD','published_at':'2025-01-03T14:00:00Z','source_name':'X','source_version':'V1'}])
    with pytest.raises(ValueError): validate_macro(df)
