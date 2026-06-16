# GOLD V3 Stage227 Alert-Only Runtime Queue Binding Audit

Date: 2026-06-17  
Stage: `GOLD_V3_227_ALERT_ONLY_RUNTIME_QUEUE_BINDING_AUDIT_ONLY`  
Status: `AUDIT_ONLY / QUEUE_BINDING / NO_SEND / NO_MT5_ORDER / NO_LIVE_HOOK / NO_AUTOTRADE`

## Purpose

Stage226 restarted the demo Discord alert-only loop, but its default input was the fixed Stage223 readiness preview queue. Stage227 creates the runtime queue binding layer so the loop can read a stable local queue file instead of the fixed Stage223 preview.

Stage227 does not send Discord and does not call webhooks. It only converts a local GOLD V3 retention/source state into an alert-only queue CSV.

## Stage226 basis

Stage226 passed:

```text
STAGE226_DEMO_DISCORD_ALERT_ONLY_LOOP_READY_LOCAL
read_delay_seconds=5
queue_csv_exists=True
cycles_completed=1
sent_count_total=0
duplicate_skipped_count=1
blocker_count=0
```

The `sent_count_total=0` result is expected because the Stage223 preview signal was already sent once by Stage225 and was correctly duplicate-skipped by Stage226.

## Input source

Default retention source directory:

```text
%APPDATA%\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files\FX_OUTPUTS\gold_v3\217\staging_retention
```

The source directory can be overridden locally:

```text
GOLD_V3_RETENTION_SOURCE_DIR=<path>
```

Expected possible inputs:

```text
latest_state.json
trade_signal_ledger.csv
```

## Output queue

Stage227 writes:

```text
%APPDATA%\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files\FX_OUTPUTS\gold_v3\runtime\alert_only_queue.csv
```

This path is intended to be consumed by Stage226 via:

```text
GOLD_V3_ALERT_ONLY_QUEUE_CSV=<runtime alert_only_queue.csv path>
```

or by launching Stage226 with `--queue-csv <path>`.

## Queue row policy

```text
SIGNAL -> write/update one queue row
NO_SIGNAL -> write no sendable queue row, write no_signal_suppression evidence
Duplicate sending remains controlled by Stage226 sent ledgers
```

## Notification template

Stage227 uses the approved alert-only compact template:

```text
🔴 GOLD SELL SCALP
Entry Time: <entry_dt> MT5/CSV
Entry Price: <entry_price>
TP / SL: <tp_usd> / <sl_usd>
Horizon: <horizon_m5_bars> M5 bars

[DEMO ALERT ONLY / NO ORDER]
Signal ID: <signal_id>
```

## Validation checks

Stage227 passes only if:

```text
QB001 source directory exists or BLOCKED with clear reason
QB002 output queue path is under FX_OUTPUTS/gold_v3/runtime
QB003 source latest row is treated as CLOSED; open/as-of is not introduced
QB004 MT5/CSV timestamp basis is used; no JST detector conversion
QB005 SIGNAL route creates exactly one sendable queue row
QB006 NO_SIGNAL creates zero sendable queue rows and records suppression
QB007 queue message title starts with red/green marker + GOLD SELL/BUY SCALP
QB008 final message line is Signal ID with full signal_id
QB009 MT5/order/import/payload/live/autotrade flags remain OFF
QB010 source CSV/contract/production retention files are not mutated
QB011 candidate pool is not removed and F002 exclusion is not bypassed
QB012 future TP/SL result, exit result, horizon outcome, and actual execution result are not used
```

## Expected decision

```text
STAGE227_ALERT_ONLY_RUNTIME_QUEUE_BINDING_READY_AUDIT_ONLY
```

or if source is missing/invalid:

```text
STAGE227_ALERT_ONLY_RUNTIME_QUEUE_BINDING_BLOCKED_AUDIT_ONLY
```
