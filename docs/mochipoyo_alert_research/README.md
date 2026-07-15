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

## Setup

Copy the example values into the local file:

```text
%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\.env
```

Required values:

```text
MOCHIPOYO_EVENTS_URL=https://YOUR_WORKER.workers.dev/events
MOCHIPOYO_READ_TOKEN=SET_LOCALLY_ONLY
```

Never commit the real Worker URL when it contains secret information, and never
commit or paste `READ_TOKEN`.

## Run once on Windows

From the repository root:

```bat
scripts\mochipoyo_alert_research\run_collect_events_once.bat
```

For offline verification:

```bat
scripts\mochipoyo_alert_research\run_collect_events_once.bat --fixture tests\mochipoyo_alert_research\fixtures\events_page_1.json --after-id 0
```

The BAT does not start a permanent loop. A loop will be added only after the
one-shot collector has been verified against real `/events` data.

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
