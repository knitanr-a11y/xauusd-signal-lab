# GOLD V3 Stage217 Live Retention Writer Dry-Run To Staging Audit

Date: 2026-06-16  
Stage: `GOLD_V3_217_LIVE_RETENTION_WRITER_DRY_RUN_TO_STAGING_AUDIT_ONLY`  
Status: `AUDIT_ONLY / STAGING_ONLY / NO_SEND / NO_ORDER / NO_LIVE_HOOK`

## Purpose

Stage217 validates the retention writer mechanics against staging files only.

It writes the same file shapes expected by the retention path, but under:

```text
MQL5\Files\FX_OUTPUTS\gold_v3\217\staging_retention\
```

It must not mutate production/live retention files.

## Inputs

Stage217 is based only on the current handoff context and the Stage216 reviewed result.

Stage216 reviewed result:

```text
STAGE216_FEATURE_DRIFT_MONITORING_RULE_READY_AUDIT_ONLY
validation_pass=True
blocker_count=0
current_drift_case=FEATURE_DRIFT_ROUTE_PARITY_PASS
current_drift_severity=WARN
current_drift_blocks_live_review=False
```

Recent canonical replay rows used by this dry-run:

```text
SIGNAL replay:
  signal_id: 20260615_163000_SECONDARY_AUDIT_CANDIDATE_SCALP_024_tp15_sl5_hz64_SHORT
  short_signal_id: G3SD01960980A23107A65AE
  latest_closed_m15_dt / entry_dt: 2026-06-15 16:30:00
  route: SECONDARY_AUDIT_CANDIDATE
  candidate_id: SCALP_024_tp15_sl5_hz64_SHORT
  direction: SHORT
  entry_price: 4363.24
  TP15 SL5 horizon64

NO_SIGNAL replay:
  latest_closed_m15_dt: 2026-06-16 16:45:00
  final_route: NO_SIGNAL
```

No future TP/SL, exit result, unresolved horizon result, actual execution result, or theoretical resolver output is used by Stage217 writer decisions.

## Output files

Stage217 creates only staging outputs:

```text
FX_OUTPUTS\gold_v3\217\staging_retention\latest_state.json
FX_OUTPUTS\gold_v3\217\staging_retention\trade_signal_ledger.csv
FX_OUTPUTS\gold_v3\217\staging_retention\notification_events_rolling_30d.csv
FX_OUTPUTS\gold_v3\217\staging_retention\no_signal_counters_daily_hourly.csv
FX_OUTPUTS\gold_v3\217\staging_retention\health_rollup.json
FX_OUTPUTS\gold_v3\217\staging_retention\debug_tail_snapshot.csv
FX_OUTPUTS\gold_v3\217\gold_v3_217_live_retention_writer_staging_summary.json
FX_OUTPUTS\gold_v3\217\paste_me.txt
```

## Writer rules

```text
latest_state.json:
  overwrite on every cycle

trade_signal_ledger.csv:
  append SIGNAL rows only
  do not append NO_SIGNAL full rows
  duplicate signal_id would be skipped

notification_events_rolling_30d.csv:
  append SIGNAL notification preview rows only
  no Discord send
  no webhook
  duplicate signal_id / short_signal_id would be skipped

no_signal_counters_daily_hourly.csv:
  increment/write only NO_SIGNAL counter rows
  do not notify Discord on NO_SIGNAL

health_rollup.json:
  summarize staging writer counts and safety flags

debug_tail_snapshot.csv:
  replace rolling debug snapshot
```

## Hard OFF flags

The script must keep these disabled:

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

## Validation checks

Stage217 passes only if:

```text
STG001 staging output path is under FX_OUTPUTS/gold_v3/217/staging_retention
STG002 production/live retention paths are not written
STG003 latest_state.json exists and is overwritten by the last replay cycle
STG004 trade_signal_ledger.csv contains exactly one SIGNAL row
STG005 notification_events_rolling_30d.csv contains exactly one preview row and no send
STG006 no_signal_counters_daily_hourly.csv contains exactly one NO_SIGNAL counter row
STG007 health_rollup.json exists
STG008 debug_tail_snapshot.csv exists
STG009 all send/order/import/payload/live-hook/autotrade flags remain OFF
STG010 theoretical/future result and actual execution data are not used as writer inputs
```

## Stop conditions

Block Stage217 if any of these occurs:

```text
production/live retention file mutation is attempted
Discord send / MT5 order / actual import / payload / live hook / autotrade is enabled
NO_SIGNAL notification is attempted
SIGNAL ledger includes future TP/SL/exit/horizon result as an input
candidate pool is removed
F002 exclusion is bypassed
CSV latest row is treated as open/as-of
JST conversion is introduced into detector/writer logic
```

## Expected decision

If all checks pass:

```text
STAGE217_LIVE_RETENTION_WRITER_STAGING_DRY_RUN_READY_AUDIT_ONLY
```

Live release remains blocked after Stage217.
