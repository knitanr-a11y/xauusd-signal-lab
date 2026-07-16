# Mochipoyo Alert Research

Status: `MOCHIPOYO_M1_RAW_COLLECTOR_AUDIT_ONLY`

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

## Current Stage M1 scope

Stage M1 only:

1. Reads `GET /events?after_id=...&limit=...` with `Bearer READ_TOKEN`.
2. Validates the Cloudflare event contract.
3. Stores the original row immutably in a local SQLite database.
4. Advances `last_successful_id` only inside the same successful transaction.
5. Records a redacted collection-run audit.
6. Supports an offline JSON fixture for repeatable tests.

Not implemented yet:

- episode construction
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
logs\
```

The database and secrets are local-only and are already covered by the
repository `.gitignore` patterns for `.env`, `*.sqlite3`, and logs.

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

After local configuration, double-click:

```text
scripts\mochipoyo_alert_research\run_collect_events_cloudflare_once.bat
```

This performs one read-only request and then stops. It does not start a
permanent loop. It does not send Discord notifications and does not call MT5.
The local SQLite database is:

```text
%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\mochipoyo_alerts.sqlite3
```

Expected first real run with the three known events:

```text
source_mode: CLOUDFLARE
after_id_before: 0
response_count: 3
inserted_count: 3
duplicate_count: 0
cursor_after: 4
```

The exact count may be larger if additional alerts have already accumulated.
A second run should start from the saved cursor and normally return either new
rows or `PASS_EMPTY`.

The production BAT does not start a permanent loop. A loop will be added only
after the one-shot collector has been verified against real `/events` data.

## Response contract accepted by the collector

The endpoint may return either:

```json
{"ok": true, "events": [...]}
```

or a direct JSON array:

```json
[...]
```

`events`, `data`, and `results` are accepted list keys. Event rows must be in
strict ascending `id` order, must be unique, and must be greater than the
requested `after_id`. ID gaps are allowed because D1 AUTOINCREMENT values are
not required to be contiguous.

## Immutable raw-event contract

`raw_alerts` stores:

- Cloudflare row ID and `event_key`
- event/ticker/timeframe/timestamps/prices
- the Worker `raw_json` field without semantic rewriting
- the complete returned event row as canonical JSON
- a SHA-256 digest used to detect ID/key collisions

Re-downloading the exact same row is idempotent. Reusing an existing
Cloudflare ID or `event_key` for different content fails closed and does not
advance the cursor.
