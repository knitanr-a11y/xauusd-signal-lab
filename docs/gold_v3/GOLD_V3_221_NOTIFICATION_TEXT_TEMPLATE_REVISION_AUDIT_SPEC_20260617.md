# GOLD V3 Stage221 Notification Text Template Revision Audit

Date: 2026-06-17  
Stage: `GOLD_V3_221_NOTIFICATION_TEXT_TEMPLATE_REVISION_AUDIT_ONLY`  
Status: `AUDIT_ONLY / TEXT_TEMPLATE_PREVIEW_ONLY / NO_SEND / NO_WEBHOOK / PAYLOAD_OFF / NO_ORDER / NO_LIVE_HOOK`

## Purpose

Stage221 revises the notification text template for future practical use.

Stage219 proved the text-preview path was safe, but its message was too technical for practical reading. Stage221 replaces the user-visible message layout with a concise trading alert format.

Revision note:

```text
The full signal_id should be displayed at the very bottom of the user-visible message.
Other technical fields remain in history metadata only.
```

No send path is enabled.

## Stage220 basis

Stage220 passed after the no-send approval gate fix:

```text
STAGE220_NOTIFICATION_NO_SEND_APPROVAL_GATE_READY_AUDIT_ONLY
signal_no_approval_decision=NO_SEND_AUDIT_ONLY
no_signal_decision=NO_MESSAGE_NO_SEND_NO_SIGNAL
partial_approval_decision=NO_SEND_APPROVAL_INCOMPLETE
blocker_count=0
```

## User-visible message requirements

The user-visible message should be short and intuitive:

```text
SELL -> red circle before GOLD
BUY -> green circle before GOLD
Title: GOLD SELL/BUY SCALP when scalp strategy
No separate symbol line
Direction appears in the title / first line
Entry time, entry price, TP/SL near the top
Full signal_id appears as the final line
Do not show route, strategy_role, candidate_id, or short_signal_id as separate body fields
Keep history-required identifiers in metadata CSV/JSON
```

## Final user-visible template

For SELL scalp:

```text
🔴 GOLD SELL SCALP
Entry Time: 2026-06-15 16:30 MT5/CSV
Entry Price: 4363.24
TP / SL: 15 / 5
Horizon: 64 M5 bars

[AUDIT_ONLY / NO_SEND]
Signal ID: 20260615_163000_SECONDARY_AUDIT_CANDIDATE_SCALP_024_tp15_sl5_hz64_SHORT
```

For BUY scalp:

```text
🟢 GOLD BUY SCALP
Entry Time: <entry_dt> MT5/CSV
Entry Price: <entry_price>
TP / SL: <tp_usd> / <sl_usd>
Horizon: <horizon_m5_bars> M5 bars

[AUDIT_ONLY / NO_SEND]
Signal ID: <signal_id>
```

The audit/no-send marker remains until the user explicitly approves any future alert-only live path.

## History metadata policy

The following should be retained in metadata CSV/JSON:

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
send_action
payload_action
webhook_action
```

## Forbidden as separate user-visible body fields

```text
symbol line
route field
strategy_role field
candidate_id field
short_signal_id field
actual execution / fill / slippage
future result / win / loss / exit
webhook URL / token / secret
account balance / position size
```

The full `signal_id` is allowed only as the final line.

## Output files

```text
FX_OUTPUTS\gold_v3\221\notification_template_revision\notification_text_revised_preview.txt
FX_OUTPUTS\gold_v3\221\notification_template_revision\notification_text_revised_preview.csv
FX_OUTPUTS\gold_v3\221\notification_template_revision\notification_history_metadata.csv
FX_OUTPUTS\gold_v3\221\notification_template_revision\notification_template_policy.json
FX_OUTPUTS\gold_v3\221\gold_v3_221_notification_text_template_revision_summary.json
FX_OUTPUTS\gold_v3\221\paste_me.txt
```

## Validation checks

Stage221 passes only if:

```text
TR001 output path is under FX_OUTPUTS/gold_v3/221/notification_template_revision
TR002 Stage220 basis is PASS
TR003 SELL title begins with red circle + GOLD SELL SCALP
TR004 BUY title rule is green circle + GOLD BUY SCALP
TR005 user-visible body contains entry time, entry price, TP/SL, and horizon near the top
TR006 user-visible body does not contain symbol line, route field, strategy_role field, candidate_id field, or short_signal_id field
TR007 history metadata retains signal_id, short_signal_id, route, strategy_role, and candidate_id
TR008 no send/webhook/payload/order/live/autotrade flags are enabled
TR009 NO_SIGNAL notification remains disabled
TR010 future TP/SL result, exit result, horizon outcome, and actual execution result are not used as message input
TR011 CSV latest row remains contractually CLOSED; open/as-of is not introduced
TR012 MT5/CSV timestamp basis is used; no JST detector conversion
TR013 final user-visible line starts with Signal ID and contains the full signal_id
```

## Expected decision

If all checks pass:

```text
STAGE221_NOTIFICATION_TEXT_TEMPLATE_REVISION_READY_AUDIT_ONLY
```

Live release remains blocked after Stage221.
