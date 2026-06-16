# GOLD V3 Stage219 Notification Message Text Preview Audit

Date: 2026-06-16  
Stage: `GOLD_V3_219_NOTIFICATION_MESSAGE_TEXT_PREVIEW_AUDIT_ONLY`  
Status: `AUDIT_ONLY / TEXT_PREVIEW_ONLY / NO_SEND / NO_WEBHOOK / PAYLOAD_OFF / NO_ORDER / NO_LIVE_HOOK`

## Purpose

Stage219 validates the human-readable notification message text for the known SIGNAL replay case without sending anything.

This stage creates text preview artifacts only under:

```text
MQL5\Files\FX_OUTPUTS\gold_v3\219\notification_text_preview\
```

It must not:

```text
send Discord messages
call webhooks
create or activate payloads
place MT5 orders
import actual executions
enable final live / live hook / autotrade
notify on NO_SIGNAL
```

## Stage218 basis

Stage218 passed:

```text
STAGE218_STAGING_RETENTION_REPLAY_MULTI_CYCLE_READY_AUDIT_ONLY
blocker_count=0
replay_attempts=4
latest_state_write_count=4
trade_signal_ledger_rows=1
notification_event_rows=1
no_signal_counter_rows=1
duplicate_signal_skip_count=1
duplicate_notification_skip_count=1
duplicate_no_signal_counter_skip_count=1
```

## Preview fixture

Stage219 uses the known Stage215 SIGNAL fixture only for SIGNAL message preview:

```text
signal_id: 20260615_163000_SECONDARY_AUDIT_CANDIDATE_SCALP_024_tp15_sl5_hz64_SHORT
short_signal_id: G3SD01960980A23107A65AE
latest_closed_m15_dt / entry_dt: 2026-06-15 16:30:00
route: SECONDARY_AUDIT_CANDIDATE
strategy_role: SCALP_SECONDARY_CANDIDATE
candidate_id: SCALP_024_tp15_sl5_hz64_SHORT
direction: SHORT
entry_price: 4363.24
TP15 SL5 horizon64
```

NO_SIGNAL fixture is included only to prove no message is generated:

```text
latest_closed_m15_dt: 2026-06-16 16:45:00
final_route: NO_SIGNAL
expected_message_action: NO_MESSAGE_NO_SIGNAL
```

## Forbidden inputs

The message text must not include or depend on:

```text
future TP/SL result
exit_dt
outcome/win/loss
unresolved horizon result
actual execution result
actual fill/slippage
account balance / risk sizing
webhook URL / token / secret
```

The text may describe the requested TP/SL parameters because they are part of the candidate contract at entry time.

## Output files

```text
FX_OUTPUTS\gold_v3\219\notification_text_preview\notification_message_text_preview.csv
FX_OUTPUTS\gold_v3\219\notification_text_preview\notification_message_text_preview.txt
FX_OUTPUTS\gold_v3\219\notification_text_preview\no_signal_message_preview.csv
FX_OUTPUTS\gold_v3\219\notification_text_preview\message_policy.json
FX_OUTPUTS\gold_v3\219\gold_v3_219_notification_message_text_preview_summary.json
FX_OUTPUTS\gold_v3\219\paste_me.txt
```

## Message text policy

Required SIGNAL text fields:

```text
AUDIT_ONLY / NO_SEND marker
symbol
route
strategy_role
candidate_id
direction
entry_dt / latest_closed_m15_dt on MT5/CSV basis
entry_price
TP/SL/horizon parameters
short_signal_id
explicit no-order/no-send wording
```

Required NO_SIGNAL behavior:

```text
NO_SIGNAL does not generate Discord message text for sending
NO_SIGNAL may be recorded as a no-message preview row only
```

## Validation checks

Stage219 passes only if:

```text
NT001 output path is under FX_OUTPUTS/gold_v3/219/notification_text_preview
NT002 exactly one SIGNAL message text preview row exists
NT003 NO_SIGNAL generated zero sendable messages
NT004 message text contains AUDIT_ONLY and NO_SEND markers
NT005 message text contains signal_id/short_signal_id and candidate details
NT006 message text does not contain outcome/result/exit/fill/account/webhook/token fields
NT007 message preview files are text/csv/json only and are not payload activation files
NT008 all send/order/import/payload/live-hook/autotrade flags remain OFF
NT009 source CSV/contract/production retention files are not mutated
NT010 CSV latest row remains contractually closed; open/as-of is not introduced
NT011 MT5/CSV timestamp basis is used; detector logic does not convert to JST
```

## Expected decision

If all checks pass:

```text
STAGE219_NOTIFICATION_MESSAGE_TEXT_PREVIEW_READY_AUDIT_ONLY
```

Live release remains blocked after Stage219.
