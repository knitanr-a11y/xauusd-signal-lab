# Mochipoyo Alert Research

Status: `MOCHIPOYO_M3_EPISODE_BUILDER_AUDIT_ONLY`

This directory is the independent research path for real TradingView Mochipoyo
alerts. It must not modify or share runtime state with the existing GOLD or BTC
operational systems.

## Fixed safety controls

- `audit_only = true`
- `dry_run = true`
- `live_ready = false`
- `final_signal = false`
- `discord_send = false`
- `mt5_order = false`
- No broker order code is imported or called.
- No Discord sender is imported or called.
- No existing GOLD/BTC state, output, ledger, or `.env` is reused.
- Future outcomes never participate in entry-time filtering.
- MT5/CSV latest rows are treated as closed by contract, but future exits,
  MFE, MAE, TP/SL outcomes, and future higher-timeframe states remain unknown.

## Current scope

Stage M1 completed:

1. Reads `GET /events?after_id=...&limit=...` with `Bearer READ_TOKEN`.
2. Validates the Cloudflare event contract.
3. Stores each returned row immutably in a local SQLite database.
4. Advances `last_successful_id` only inside the same successful transaction.
5. Records a redacted collection-run audit.
6. Supports an offline JSON fixture for repeatable tests.
7. Verified the real Worker with 42 stored rows and a restart-safe empty resume.

Stage M2 completed:

1. A 60-second read-only collection loop.
2. An exclusive lock that blocks a second collector process.
3. A stop file checked at least once per second while waiting.
4. Continued polling after a failed cycle; the one-shot collector still
   preserves the cursor on each failure.
5. A local append-only loop log and latest loop-status JSON.
6. A three-cycle real-Worker smoke test completed with three successful
   `PASS_EMPTY` cycles from cursor 42.

Stage M3 adds:

1. Deterministic source-alert episode construction from immutable raw rows.
2. Separate state machines for `XAUUSD` and `BTCUSD`.
3. Repeated same-direction entries before exit as `REENTRY_ALERT`.
4. Opposite-direction alerts before the active exit are recorded but do not
   switch the source state.
5. Orphan and opposite events are retained as explicit build anomalies.
6. Derived episode tables are rebuilt atomically; raw alerts are never changed.
7. Build-run history records that no future entry fields were used.

Not implemented yet:

- MT5 M5/M15/H1/H4 alignment
- feature snapshots
- virtual entries
- MFE/MAE/outcomes
- candidate gates
- Discord notifications
- MT5 orders

## Independent local storage

Default local root:

```text
%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research
```

Default files:

```text
.env
mochipoyo_alerts.sqlite3
collector_loop.lock
STOP_COLLECTOR_LOOP
logs\latest_collection_result.json
logs\latest_collection_error.json
logs\latest_loop_status.json
logs\collector_forever.log
logs\latest_episode_build_result.json
```

The database, secrets, lock, stop request, and logs are local-only. Repository
`.gitignore` patterns already exclude `.env`, SQLite databases, and logs.

## Offline verification

Double-click:

```text
scripts\mochipoyo_alert_research\run_collect_events_fixture_test.bat
```

The fixture test writes only to a temporary test database under `%TEMP%`; it
does not write fixture rows into the real Mochipoyo database. It checks:

1. initial insert and cursor advancement
2. restart-safe cursor resume
3. exact duplicate replay suppression

## Configure the real Cloudflare read-only source

Do not paste the Worker URL or `READ_TOKEN` into ChatGPT, GitHub, source code,
issues, screenshots, or commit messages.

Double-click:

```text
scripts\mochipoyo_alert_research\run_configure_cloudflare.bat
```

The helper asks for:

- the Worker root URL or full `/events` URL
- `READ_TOKEN` using hidden console input

It writes only to:

```text
%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\.env
```

The helper never prints `READ_TOKEN`. It normalizes the Worker URL to `/events`
and rejects non-HTTPS URLs, query parameters, fragments, or embedded
credentials.

## Run one real Cloudflare collection

Double-click:

```text
scripts\mochipoyo_alert_research\run_collect_events_cloudflare_once.bat
```

This performs one read-only request and then stops. It does not send Discord
notifications and does not call MT5. The local SQLite database is:

```text
%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\mochipoyo_alerts.sqlite3
```

The verified real run stored 42 rows, advanced the cursor from 0 to 42, and the
second run returned `PASS_EMPTY` from cursor 42.

## Test the repeated collector

Before starting the permanent loop, double-click:

```text
scripts\mochipoyo_alert_research\run_collect_events_cloudflare_loop_test.bat
```

This runs exactly three read-only cycles at ten-second intervals and exits. The
verified test completed three successful `PASS_EMPTY` cycles from cursor 42.

## Start the permanent read-only collector

After the three-cycle test succeeds, double-click:

```text
scripts\mochipoyo_alert_research\run_collect_events_cloudflare_forever.bat
```

Behavior:

- immediate first collection
- one collection every 60 seconds
- one active process only
- no cursor advancement on a failed collection
- failed cycles are logged and later cycles continue
- Discord, MT5 orders, `live_ready`, and `final_signal` remain OFF

Do not close this window while continuous collection is required. Before a
future GitHub pull that changes Mochipoyo collector files, stop this loop safely,
pull the branch, and restart it.

## Stop the permanent collector safely

Double-click:

```text
scripts\mochipoyo_alert_research\stop_collect_events_cloudflare_forever.bat
```

This creates the local `STOP_COLLECTOR_LOOP` file. The loop detects it while
waiting and exits cleanly. If an HTTP request is currently active, shutdown can
take until that request finishes or reaches its timeout.

Closing the collector window forcibly can leave `collector_loop.lock`. A stale
lock must only be deleted after confirming that no Mochipoyo collector window
or Python collector process is still running. Never delete the lock merely to
start a second collector.

## Build source-alert episodes once

After collecting the latest rows, double-click:

```text
scripts\mochipoyo_alert_research\run_build_episodes_once.bat
```

The builder reads `raw_alerts` in ascending Cloudflare ID order. It never edits
or deletes raw rows. It atomically rebuilds only the derived episode tables.

State is independent for each ticker:

```text
IDLE + LONG       -> ACTIVE_LONG
ACTIVE_LONG + LONG -> REENTRY_ALERT
ACTIVE_LONG + LONG_EXIT -> IDLE
IDLE + SHORT      -> ACTIVE_SHORT
ACTIVE_SHORT + SHORT -> REENTRY_ALERT
ACTIVE_SHORT + SHORT_EXIT -> IDLE
```

An opposite-direction alert or exit does not switch the active source state
before the matching exit. It is attached to the current episode as an ignored
opposite event and recorded in `episode_build_anomalies`. An exit while idle is
recorded as an orphan anomaly. An episode still active at the newest raw row is
stored as `OPEN` with `exit_missing = 1`.

The latest redacted summary is written to:

```text
%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\logs\latest_episode_build_result.json
```

Episode construction labels chronology only. Later exit information must not be
used by entry-time filters, feature snapshots, or candidate gates.

## Response contract accepted by the collector

The endpoint may return a direct JSON array or a JSON object containing one of:

```text
rows
events
data
results
```

The verified Worker returns:

```json
{"ok": true, "rows": [...]}
```

Rows must be in strict ascending `id` order, must be unique, and must be greater
than the requested `after_id`. ID gaps are allowed because D1 AUTOINCREMENT
values are not required to be contiguous.

## Immutable raw-event contract

The real Worker projection includes the D1 row ID and event fields but omits
`event_key` and `raw_json`. Therefore:

- the D1 `id` remains the immutable primary source identity
- the collector derives `event_key` as `cloudflare:<id>` when the Worker omits it
- `event_key_origin` records `DERIVED_CLOUDFLARE_ID` or `WORKER`
- the complete returned row is always stored as canonical source JSON
- when `raw_json` is absent, that canonical row is stored as the fallback and
  `worker_raw_json_origin` records `COLLECTOR_SOURCE_ROW_FALLBACK`
- a SHA-256 digest detects any later content change for an existing ID/key

Re-downloading an identical row is idempotent. Reusing an existing Cloudflare
ID or event key for different content fails closed and does not advance the
cursor.
