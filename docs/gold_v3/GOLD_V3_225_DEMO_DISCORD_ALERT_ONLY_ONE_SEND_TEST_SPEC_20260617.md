# GOLD V3 Stage225 Demo Discord Alert-Only One Send Test

Date: 2026-06-17  
Stage: `GOLD_V3_225_DEMO_DISCORD_ALERT_ONLY_ONE_SEND_TEST`  
Status: `DEMO_ALERT_ONLY / ONE_SEND_ONLY / USER_APPROVED / NO_MT5_ORDER / NO_LIVE_HOOK / NO_AUTOTRADE`

## Explicit user approval

The user explicitly approved:

```text
Stage225として、demo Discord alert-only送信テストを1件だけ許可します。
MT5発注・実口座・payload activation・live hook・final live・autotrade・NO_SIGNAL通知は許可しません。
```

This approval is limited to exactly one demo Discord alert-only send test for one SIGNAL message.

It does not approve:

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

## Stage224 basis

Stage224 passed:

```text
STAGE224_DEMO_ALERT_ONLY_DISPATCHER_GATE_READY_APPROVAL_REQUIRED_AUDIT_ONLY
queue_rows=1
no_signal_suppression_rows=1
future_send_requires_explicit_approval=True
blocker_count=0
```

## Message to send

```text
🔴 GOLD SELL SCALP
Entry Time: 2026-06-15 16:30 MT5/CSV
Entry Price: 4363.24
TP / SL: 15 / 5
Horizon: 64 M5 bars

[DEMO ALERT ONLY / NO ORDER]
Signal ID: 20260615_163000_SECONDARY_AUDIT_CANDIDATE_SCALP_024_tp15_sl5_hz64_SHORT
```

## Webhook source

Stage225 may read a Discord webhook URL only from local/private runtime sources, never from git-tracked files:

```text
Environment variable: GOLD_V3_DEMO_DISCORD_WEBHOOK_URL
Fallback environment variable: GOLD_V3_DISCORD_WEBHOOK_URL
Optional local file: %APPDATA%\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files\FX_CONFIG\gold_v3\demo_discord_webhook_url.txt
```

The webhook URL must never be printed in full. Only a redacted URL may be written to output artifacts.

If no webhook URL is available, Stage225 must BLOCK without sending.

## One-send idempotency

Stage225 must send at most one Discord message for the approved SIGNAL.

If the same `signal_id` is already present in the Stage225 send ledger with `send_status=SENT`, rerunning the script must not send again.

## Output files

```text
FX_OUTPUTS\gold_v3\225\demo_discord_alert_only_one_send\discord_send_attempts.csv
FX_OUTPUTS\gold_v3\225\demo_discord_alert_only_one_send\demo_alert_only_sent_ledger.csv
FX_OUTPUTS\gold_v3\225\demo_discord_alert_only_one_send\discord_send_receipt.json
FX_OUTPUTS\gold_v3\225\demo_discord_alert_only_one_send\demo_alert_only_message_sent.txt
FX_OUTPUTS\gold_v3\225\demo_discord_alert_only_one_send\no_signal_suppression.csv
FX_OUTPUTS\gold_v3\225\gold_v3_225_demo_discord_alert_only_one_send_summary.json
FX_OUTPUTS\gold_v3\225\paste_me.txt
```

## Validation checks

Stage225 passes only if:

```text
S225001 output path is under FX_OUTPUTS/gold_v3/225/demo_discord_alert_only_one_send
S225002 Stage224 basis is PASS
S225003 explicit user approval is recorded and scoped to demo Discord alert-only one-send only
S225004 webhook URL is found from private runtime source and is a Discord webhook URL
S225005 webhook URL is redacted in all output artifacts
S225006 exactly one SIGNAL message is selected for send
S225007 message title starts with 🔴 GOLD SELL SCALP
S225008 final message line is Signal ID with full signal_id
S225009 NO_SIGNAL creates no Discord send
S225010 duplicate signal guard prevents more than one send per signal_id
S225011 Discord HTTP response is 200 or 204 for first send, or duplicate rerun is skipped without sending
S225012 MT5 order, real account, actual import, payload activation, live hook, final live, autotrade remain OFF
S225013 source CSV/contract/production retention files are not mutated
S225014 candidate pool is not removed and F002 exclusion is not bypassed
S225015 future TP/SL result, exit result, horizon outcome, and actual execution result are not used
S225016 CSV latest row remains contractually CLOSED; open/as-of is not introduced
S225017 MT5/CSV timestamp basis is used; no JST detector conversion
```

## Expected decisions

First successful send:

```text
STAGE225_DEMO_DISCORD_ALERT_ONLY_ONE_SEND_SENT_READY
```

Duplicate rerun without sending again:

```text
STAGE225_DEMO_DISCORD_ALERT_ONLY_DUPLICATE_SKIPPED_READY
```

Blocked before send:

```text
STAGE225_DEMO_DISCORD_ALERT_ONLY_ONE_SEND_BLOCKED
```
