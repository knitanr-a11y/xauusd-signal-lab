# GOLD V3 Stage222 Notification Event Staging Template Integration Audit

Date: 2026-06-17  
Stage: `GOLD_V3_222_NOTIFICATION_EVENT_STAGING_TEMPLATE_INTEGRATION_AUDIT_ONLY`  
Status: `AUDIT_ONLY / STAGING_ONLY / TEMPLATE_INTEGRATION_ONLY / NO_SEND / NO_WEBHOOK / PAYLOAD_OFF / NO_ORDER / NO_LIVE_HOOK`

## Purpose

Stage222 verifies that the Stage221 revised notification text can be written into a staging notification-event ledger row while keeping all send, webhook, payload, order, and live paths disabled.

This stage does not create a Discord payload and does not call a webhook. It only writes CSV/JSON/TXT evidence under:

```text
MQL5\Files\FX_OUTPUTS\gold_v3\222\notification_event_template_integration\
```

## Stage221 basis

Stage221 passed with the revised user-visible template:

```text
STAGE221_NOTIFICATION_TEXT_TEMPLATE_REVISION_READY_AUDIT_ONLY
message_template_version=GOLD_V3_NOTIFY_TEMPLATE_V3_SCALP_COMPACT_SIGNAL_ID_BOTTOM_20260617
title=🔴 GOLD SELL SCALP
buy_title_sample=🟢 GOLD BUY SCALP
signal_id_visible_bottom=True
blocker_count=0
```

## User-visible message to integrate

```text
🔴 GOLD SELL SCALP
Entry Time: 2026-06-15 16:30 MT5/CSV
Entry Price: 4363.24
TP / SL: 15 / 5
Horizon: 64 M5 bars

[AUDIT_ONLY / NO_SEND]
Signal ID: 20260615_163000_SECONDARY_AUDIT_CANDIDATE_SCALP_024_tp15_sl5_hz64_SHORT
```

## Integration target

Stage222 writes a staging-only notification event ledger with:

```text
notification_action=NO_SEND_AUDIT_ONLY
webhook_action=NO_WEBHOOK_AUDIT_ONLY
payload_action=NO_PAYLOAD_ACTIVATION_AUDIT_ONLY
message_text=<Stage221 revised message>
```

It also writes a history metadata row preserving:

```text
signal_id
short_signal_id
final_route
strategy_role
candidate_id
direction
latest_closed_m15_dt
entry_dt
entry_price
tp_usd
sl_usd
horizon_m5_bars
message_template_version
```

## Required behavior

```text
SIGNAL row -> one staging notification-event row with the revised message text
NO_SIGNAL row -> no notification-event row, no Discord message, no webhook, no payload
Duplicate SIGNAL replay -> no duplicate event row
```

## Output files

```text
FX_OUTPUTS\gold_v3\222\notification_event_template_integration\notification_events_staging.csv
FX_OUTPUTS\gold_v3\222\notification_event_template_integration\notification_event_history_metadata.csv
FX_OUTPUTS\gold_v3\222\notification_event_template_integration\no_signal_notification_suppression.csv
FX_OUTPUTS\gold_v3\222\notification_event_template_integration\notification_event_policy.json
FX_OUTPUTS\gold_v3\222\notification_event_template_integration\message_text_integrated_preview.txt
FX_OUTPUTS\gold_v3\222\gold_v3_222_notification_event_staging_template_integration_summary.json
FX_OUTPUTS\gold_v3\222\paste_me.txt
```

## Validation checks

Stage222 passes only if:

```text
TI001 output path is under FX_OUTPUTS/gold_v3/222/notification_event_template_integration
TI002 Stage221 basis is PASS
TI003 exactly one SIGNAL notification-event staging row exists
TI004 duplicate SIGNAL replay is skipped
TI005 NO_SIGNAL creates zero sendable notification-event rows
TI006 staged message begins with red circle + GOLD SELL SCALP
TI007 staged message final line is Signal ID with full signal_id
TI008 notification_action/webhook_action/payload_action remain NO_SEND/NO_WEBHOOK/NO_PAYLOAD
TI009 no send/webhook/payload/order/import/live/autotrade flags are enabled
TI010 source CSV/contract/production retention files are not mutated
TI011 candidate pool is not removed and F002 exclusion is not bypassed
TI012 future TP/SL result, exit result, horizon outcome, and actual execution result are not used as integration input
TI013 CSV latest row remains contractually CLOSED; open/as-of is not introduced
TI014 MT5/CSV timestamp basis is used; no JST detector conversion
```

## Expected decision

If all checks pass:

```text
STAGE222_NOTIFICATION_EVENT_STAGING_TEMPLATE_INTEGRATION_READY_AUDIT_ONLY
```

Live release remains blocked after Stage222.
