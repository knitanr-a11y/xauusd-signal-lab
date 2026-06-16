# GOLD V3 Stage228 Queue Refresh And Alert-Only Loop Integrated Local Spec

Date: 2026-06-17  
Stage: `GOLD_V3_228_QUEUE_REFRESH_AND_ALERT_ONLY_LOOP_INTEGRATED_LOCAL`  
Status: `DEMO_ALERT_ONLY / LOCAL_INTEGRATED_RUNNER / USER_APPROVED_STAGE226_SCOPE / NO_MT5_ORDER / NO_LIVE_HOOK / NO_AUTOTRADE`

## Purpose

Stage228 combines the Stage227 queue refresh step and the Stage226 alert-only loop step into one local runner.

The integrated runner performs the following cycle:

```text
minute boundary + 5 seconds
↓
read local GOLD V3 source state
↓
refresh FX_OUTPUTS/gold_v3/runtime/alert_only_queue.csv
↓
read refreshed runtime queue
↓
notify only unsent SIGNAL rows through demo alert-only channel
↓
record local ledgers and paste_me evidence
```

## Basis

Stage225 succeeded in sending exactly one demo Discord alert-only message:

```text
STAGE225_DEMO_DISCORD_ALERT_ONLY_ONE_SEND_SENT_READY
send_status=SENT
http_status=204
```

Stage226 loop restarted successfully and proved duplicate skip with minute+5 second timing:

```text
STAGE226_DEMO_DISCORD_ALERT_ONLY_LOOP_READY_LOCAL
read_delay_seconds=5
sent_count_total=0
duplicate_skipped_count=1
```

Stage227 queue binding succeeded and proved NO_SIGNAL suppresses queue output:

```text
STAGE227_ALERT_ONLY_RUNTIME_QUEUE_BINDING_READY_AUDIT_ONLY
source_final_route=NO_SIGNAL
sendable_queue_rows=0
suppression_rows=1
```

## Timing

CSV/source read must occur at:

```text
HH:MM:05
```

That means each minute boundary plus five seconds.

## Input source

Default source directory:

```text
%APPDATA%\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files\FX_OUTPUTS\gold_v3\217\staging_retention
```

Local override:

```text
GOLD_V3_RETENTION_SOURCE_DIR=<path>
```

Expected source files:

```text
latest_state.json
trade_signal_ledger.csv
```

## Webhook and secret policy

Webhook URL is read only from local/private runtime `.env` or process environment. It must not be committed to git. Output artifacts must contain only a redacted URL and short hash.

## Send policy

```text
SIGNAL: eligible only if signal_id exists and was not sent before
NO_SIGNAL: never notify
Duplicate signal_id: skip
```

## Forbidden actions

Stage228 does not approve:

```text
MT5 order
real account
actual execution import
payload activation for trading
live hook
final live
autotrade
NO_SIGNAL notification
```

## Output files

```text
FX_OUTPUTS\gold_v3\228\integrated_alert_only_loop\integrated_status.json
FX_OUTPUTS\gold_v3\228\integrated_alert_only_loop\integrated_runtime_log.csv
FX_OUTPUTS\gold_v3\228\integrated_alert_only_loop\integrated_send_attempts.csv
FX_OUTPUTS\gold_v3\228\integrated_alert_only_loop\integrated_sent_ledger.csv
FX_OUTPUTS\gold_v3\228\integrated_alert_only_loop\no_signal_suppression.csv
FX_OUTPUTS\gold_v3\228\paste_me.txt
```

## Validation checks

```text
I228001 Stage225/226/227 basis recorded
I228002 read timing is minute + 5 seconds
I228003 source state read uses CLOSED row contract and no open/as-of
I228004 MT5/CSV timestamp basis; no JST detector conversion
I228005 runtime queue refreshed before send check in each cycle
I228006 SIGNAL sends only if not duplicate
I228007 NO_SIGNAL never notifies
I228008 secret URL redacted in outputs
I228009 MT5/order/import/payload/live/autotrade flags remain OFF
I228010 source/contract/production retention files are not mutated
I228011 candidate pool is not removed and F002 exclusion is not bypassed
I228012 no future result or actual execution result is used as input
```

## Implementation note

The executable integrated runner is local VSCode code because the assistant GitHub connector cannot commit webhook-send code. This document and safe launch wrapper may be committed.
