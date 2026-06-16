# GOLD V3 Stage218 Staging Retention Replay Multi-Cycle Audit

Date: 2026-06-16  
Stage: `GOLD_V3_218_STAGING_RETENTION_REPLAY_MULTI_CYCLE_AUDIT_ONLY`  
Status: `AUDIT_ONLY / STAGING_ONLY / NO_SEND / NO_ORDER / NO_LIVE_HOOK`

## Purpose

Stage218 validates that the Stage217-style retention writer remains safe and idempotent across repeated replay cycles.

This stage writes only to a fresh Stage218 staging directory:

```text
MQL5\Files\FX_OUTPUTS\gold_v3\218\staging_retention_replay\
```

It must not mutate production/live retention files or Stage217 outputs.

## Stage217 basis

Stage217 passed:

```text
STAGE217_LIVE_RETENTION_WRITER_STAGING_DRY_RUN_READY_AUDIT_ONLY
blocker_count=0
latest_state_write_count=2
trade_signal_ledger_rows=1
notification_event_rows=1
no_signal_counter_rows=1
health_rollup_ready=True
debug_tail_rows=2
```

## Replay fixture policy

Stage218 uses only known audit replay fixture rows from the current canonical path:

```text
SIGNAL replay row:
  signal_id: 20260615_163000_SECONDARY_AUDIT_CANDIDATE_SCALP_024_tp15_sl5_hz64_SHORT
  short_signal_id: G3SD01960980A23107A65AE
  latest_closed_m15_dt: 2026-06-15 16:30:00
  route: SECONDARY_AUDIT_CANDIDATE
  candidate_id: SCALP_024_tp15_sl5_hz64_SHORT
  direction: SHORT
  entry_price: 4363.24
  TP15 SL5 horizon64

NO_SIGNAL replay row:
  latest_closed_m15_dt: 2026-06-16 16:45:00
  final_route: NO_SIGNAL
```

The rows are replayed twice into the same staging directory.

Expected idempotency behavior:

```text
First SIGNAL replay: append trade_signal_ledger row and notification preview row
First NO_SIGNAL replay: append/increment no_signal counter row
Second SIGNAL replay: skip duplicate signal_id and duplicate notification event
Second NO_SIGNAL replay: skip duplicate latest_closed_m15_dt + final_route counter increment
latest_state.json: overwrite on every cycle, including duplicates
```

## Output files

```text
FX_OUTPUTS\gold_v3\218\staging_retention_replay\latest_state.json
FX_OUTPUTS\gold_v3\218\staging_retention_replay\trade_signal_ledger.csv
FX_OUTPUTS\gold_v3\218\staging_retention_replay\notification_events_rolling_30d.csv
FX_OUTPUTS\gold_v3\218\staging_retention_replay\no_signal_counters_daily_hourly.csv
FX_OUTPUTS\gold_v3\218\staging_retention_replay\health_rollup.json
FX_OUTPUTS\gold_v3\218\staging_retention_replay\debug_tail_snapshot.csv
FX_OUTPUTS\gold_v3\218\staging_retention_replay\idempotency_events.csv
FX_OUTPUTS\gold_v3\218\gold_v3_218_staging_retention_replay_multi_cycle_summary.json
FX_OUTPUTS\gold_v3\218\paste_me.txt
```

## Validation checks

Stage218 passes only if:

```text
MC001 staging output path is under FX_OUTPUTS/gold_v3/218/staging_retention_replay
MC002 production/live retention files are not written
MC003 Stage217 outputs are not mutated
MC004 latest_state.json exists and was overwritten once per replayed cycle
MC005 trade_signal_ledger.csv contains exactly one unique SIGNAL row after duplicate replay
MC006 notification_events_rolling_30d.csv contains exactly one unique preview row and no send
MC007 no_signal_counters_daily_hourly.csv contains exactly one unique NO_SIGNAL counter row after duplicate replay
MC008 duplicate signal replay produced SKIP_DUPLICATE_SIGNAL_ID
MC009 duplicate notification replay produced SKIP_DUPLICATE_NOTIFICATION_EVENT
MC010 duplicate NO_SIGNAL replay produced SKIP_DUPLICATE_COUNTER_INCREMENT
MC011 debug_tail_snapshot.csv records all replay attempts
MC012 health_rollup.json exists and reports audit-only/staging-only
MC013 all send/order/import/payload/live-hook/autotrade flags remain OFF
MC014 theoretical/future result and actual execution data are not used as writer inputs
```

## Hard OFF flags

These must remain disabled:

```text
send_enabled=False
execution_enabled=False
actual_order_import_enabled=False
discord_enabled=False
mt5_order_enabled=False
ai_api_enabled=False
payload_enabled=False
live_hook_enabled=False
final_live_enabled=False
autotrade_enabled=False
no_signal_discord_notify=False
```

## Stop conditions

Block Stage218 if any of these occurs:

```text
production/live retention mutation is attempted
Stage217 output mutation is attempted
Discord send / MT5 order / actual import / payload / live hook / autotrade is enabled
NO_SIGNAL notification is attempted
future TP/SL/exit/horizon results are used as writer inputs
actual execution data is used as writer input
candidate pool is removed
F002 exclusion is bypassed
CSV latest row is treated as open/as-of
JST conversion is introduced into detector/writer logic
```

## Expected decision

If all checks pass:

```text
STAGE218_STAGING_RETENTION_REPLAY_MULTI_CYCLE_READY_AUDIT_ONLY
```

Live release remains blocked after Stage218.
