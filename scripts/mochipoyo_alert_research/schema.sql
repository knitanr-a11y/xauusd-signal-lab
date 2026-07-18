PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS collector_state (
    state_key TEXT PRIMARY KEY,
    state_value TEXT NOT NULL,
    updated_at_utc TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS raw_alerts (
    cloudflare_id INTEGER PRIMARY KEY,
    event_key TEXT NOT NULL UNIQUE,
    event_key_origin TEXT NOT NULL DEFAULT 'WORKER'
        CHECK (event_key_origin IN ('WORKER', 'DERIVED_CLOUDFLARE_ID')),
    received_at_utc TEXT NOT NULL,
    source TEXT NOT NULL,
    strategy TEXT NOT NULL,
    event TEXT NOT NULL
        CHECK (event IN ('LONG', 'SHORT', 'LONG_EXIT', 'SHORT_EXIT')),
    exchange_name TEXT,
    ticker TEXT NOT NULL
        CHECK (ticker IN ('XAUUSD', 'BTCUSD')),
    timeframe TEXT,
    bar_time_utc TEXT NOT NULL,
    fired_at_utc TEXT NOT NULL,
    open_price REAL,
    high_price REAL,
    low_price REAL,
    close_price REAL,
    message TEXT,
    worker_raw_json TEXT NOT NULL,
    worker_raw_json_origin TEXT NOT NULL DEFAULT 'WORKER_FIELD'
        CHECK (worker_raw_json_origin IN ('WORKER_FIELD', 'COLLECTOR_SOURCE_ROW_FALLBACK')),
    collector_source_row_json TEXT NOT NULL,
    payload_sha256 TEXT NOT NULL,
    downloaded_at_utc TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_mochipoyo_raw_ticker_time
ON raw_alerts (ticker, bar_time_utc);

CREATE INDEX IF NOT EXISTS idx_mochipoyo_raw_event_time
ON raw_alerts (event, fired_at_utc);

CREATE TABLE IF NOT EXISTS collection_runs (
    run_id TEXT PRIMARY KEY,
    started_at_utc TEXT NOT NULL,
    finished_at_utc TEXT NOT NULL,
    after_id_before INTEGER NOT NULL,
    requested_limit INTEGER NOT NULL,
    response_count INTEGER NOT NULL,
    inserted_count INTEGER NOT NULL,
    duplicate_count INTEGER NOT NULL,
    max_response_id INTEGER,
    cursor_after INTEGER NOT NULL,
    status TEXT NOT NULL
        CHECK (status IN ('PASS', 'PASS_EMPTY', 'FAIL')),
    source_mode TEXT NOT NULL
        CHECK (source_mode IN ('CLOUDFLARE', 'FIXTURE')),
    events_url_redacted TEXT,
    error_type TEXT,
    error_message_redacted TEXT
);

CREATE TABLE IF NOT EXISTS episodes (
    episode_id TEXT PRIMARY KEY,
    ticker TEXT NOT NULL,
    direction TEXT NOT NULL CHECK (direction IN ('LONG', 'SHORT')),
    primary_alert_id INTEGER NOT NULL REFERENCES raw_alerts(cloudflare_id),
    started_at_utc TEXT NOT NULL,
    exit_alert_id INTEGER REFERENCES raw_alerts(cloudflare_id),
    exited_at_utc TEXT,
    episode_status TEXT NOT NULL CHECK (episode_status IN ('OPEN', 'CLOSED')),
    exit_missing INTEGER NOT NULL DEFAULT 0 CHECK (exit_missing IN (0, 1)),
    sequence_anomaly INTEGER NOT NULL DEFAULT 0 CHECK (sequence_anomaly IN (0, 1))
);

CREATE INDEX IF NOT EXISTS idx_mochipoyo_episodes_ticker_start
ON episodes (ticker, started_at_utc);

CREATE INDEX IF NOT EXISTS idx_mochipoyo_episodes_status
ON episodes (episode_status, ticker, direction);

CREATE TABLE IF NOT EXISTS episode_events (
    episode_id TEXT NOT NULL REFERENCES episodes(episode_id),
    raw_alert_id INTEGER NOT NULL REFERENCES raw_alerts(cloudflare_id),
    event_role TEXT NOT NULL CHECK (
        event_role IN (
            'PRIMARY_ALERT',
            'REENTRY_ALERT',
            'EXIT_ALERT',
            'OPPOSITE_ALERT_IGNORED',
            'OPPOSITE_EXIT_IGNORED'
        )
    ),
    reentry_index INTEGER,
    PRIMARY KEY (episode_id, raw_alert_id)
);

CREATE INDEX IF NOT EXISTS idx_mochipoyo_episode_events_raw
ON episode_events (raw_alert_id);

CREATE TABLE IF NOT EXISTS episode_build_anomalies (
    anomaly_id INTEGER PRIMARY KEY AUTOINCREMENT,
    raw_alert_id INTEGER NOT NULL UNIQUE REFERENCES raw_alerts(cloudflare_id),
    ticker TEXT NOT NULL,
    event TEXT NOT NULL,
    state_before TEXT NOT NULL,
    reason TEXT NOT NULL,
    related_episode_id TEXT REFERENCES episodes(episode_id),
    created_at_utc TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_mochipoyo_episode_anomaly_reason
ON episode_build_anomalies (reason, ticker);

CREATE TABLE IF NOT EXISTS episode_build_runs (
    build_id INTEGER PRIMARY KEY AUTOINCREMENT,
    built_at_utc TEXT NOT NULL,
    raw_alert_count INTEGER NOT NULL,
    episode_count INTEGER NOT NULL,
    closed_episode_count INTEGER NOT NULL,
    open_episode_count INTEGER NOT NULL,
    reentry_count INTEGER NOT NULL,
    anomaly_count INTEGER NOT NULL,
    ignored_opposite_count INTEGER NOT NULL,
    latest_raw_id INTEGER NOT NULL,
    audit_only INTEGER NOT NULL CHECK (audit_only = 1),
    future_entry_fields_used INTEGER NOT NULL CHECK (future_entry_fields_used = 0)
);

CREATE TABLE IF NOT EXISTS mt5_alignment (
    raw_alert_id INTEGER NOT NULL REFERENCES raw_alerts(cloudflare_id),
    timeframe TEXT NOT NULL,
    tv_event_time_utc TEXT NOT NULL,
    mt5_server_time TEXT,
    estimated_mt5_time_utc TEXT,
    selected_offset_hours REAL,
    time_diff_seconds REAL,
    tv_close_price REAL,
    mt5_close_price REAL,
    price_diff REAL,
    alignment_status TEXT NOT NULL,
    diagnostics_json TEXT NOT NULL,
    PRIMARY KEY (raw_alert_id, timeframe)
);

CREATE TABLE IF NOT EXISTS feature_snapshots (
    snapshot_id TEXT PRIMARY KEY,
    source_event_id INTEGER NOT NULL REFERENCES raw_alerts(cloudflare_id),
    episode_id TEXT REFERENCES episodes(episode_id),
    snapshot_time_utc TEXT NOT NULL,
    knowledge_cutoff_utc TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    latest_closed_bar_time TEXT NOT NULL,
    features_json TEXT NOT NULL,
    future_fields_present INTEGER NOT NULL DEFAULT 0
        CHECK (future_fields_present = 0)
);

CREATE TABLE IF NOT EXISTS virtual_entries (
    entry_id TEXT PRIMARY KEY,
    episode_id TEXT NOT NULL REFERENCES episodes(episode_id),
    entry_type TEXT NOT NULL,
    entry_index INTEGER NOT NULL,
    setup_detected_at_utc TEXT NOT NULL,
    entry_time_utc TEXT NOT NULL,
    entry_price REAL NOT NULL,
    sl_price REAL,
    tp_price REAL,
    status TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS outcomes (
    entry_id TEXT PRIMARY KEY REFERENCES virtual_entries(entry_id),
    exit_dt TEXT NOT NULL,
    exit_price REAL,
    exit_reason TEXT,
    mfe REAL,
    mae REAL,
    result_r REAL,
    result_usd REAL,
    resolved_at_utc TEXT NOT NULL
);
