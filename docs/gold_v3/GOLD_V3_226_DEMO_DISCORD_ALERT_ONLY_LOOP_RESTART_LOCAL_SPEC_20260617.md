# GOLD V3 Stage226 Demo Discord Alert-Only Loop Restart Local Spec

Date: 2026-06-17  
Stage: `GOLD_V3_226_DEMO_DISCORD_ALERT_ONLY_LOOP_RESTART_LOCAL`  
Status: `DEMO_ALERT_ONLY / LOOP_RESTART_TEST / USER_APPROVED / LOCAL_CODE / NO_MT5_ORDER / NO_LIVE_HOOK / NO_AUTOTRADE`

## Explicit user approval

The user explicitly approved:

```text
Stage226として、demo Discord alert-only loop の再開テストを許可します。
MT5発注・実口座・payload activation・live hook・final live・autotrade・NO_SIGNAL通知は許可しません。
CSV読みに行くのは毎分00秒にラグをプラス5秒つけてください。
```

This approval is limited to demo Discord alert-only loop restart testing.

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

## Stage225 basis

Stage225 local one-send succeeded:

```text
STAGE225_DEMO_DISCORD_ALERT_ONLY_ONE_SEND_SENT_READY
send_status=SENT
http_status=204
discord_response_ok=True
sent_rows_for_signal_before=0
sent_rows_for_signal_after=1
blocker_count=0
```

## Required timing

The loop must read CSV once per minute at:

```text
minute boundary + 5 seconds
example: 12:00:05, 12:01:05, 12:02:05
```

This timing is intended to avoid reading while external writers are still updating CSV files at the minute boundary.

## Input policy

The loop may read an alert queue CSV from local runtime path. Default input:

```text
%APPDATA%\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files\FX_OUTPUTS\gold_v3\223\alert_only_readiness_consolidated\alert_only_queue_preview.csv
```

For real restart testing, the user may later set:

```text
GOLD_V3_ALERT_ONLY_QUEUE_CSV=<local queue csv path>
```

## Webhook policy

Webhook URL is read only from local/private runtime `.env` in MQL5 Files or process environment. It must not be committed to git and must be redacted in outputs.

## Send policy

```text
Only rows with final_route != NO_SIGNAL are eligible.
NO_SIGNAL rows are never sent.
Deduplicate by signal_id.
Reruns do not resend already-sent signal_id.
```

## Output files

```text
FX_OUTPUTS\gold_v3\226\demo_discord_alert_only_loop_restart\loop_send_attempts.csv
FX_OUTPUTS\gold_v3\226\demo_discord_alert_only_loop_restart\loop_sent_ledger.csv
FX_OUTPUTS\gold_v3\226\demo_discord_alert_only_loop_restart\loop_status.json
FX_OUTPUTS\gold_v3\226\demo_discord_alert_only_loop_restart\loop_runtime_log.csv
FX_OUTPUTS\gold_v3\226\demo_discord_alert_only_loop_restart\no_signal_suppression.csv
FX_OUTPUTS\gold_v3\226\paste_me.txt
```

## Validation checks

Stage226 local loop should report:

```text
L226001 Stage225 basis is PASS
L226002 user approval scope recorded
L226003 read timing is minute + 5 seconds
L226004 webhook URL found and redacted
L226005 queue CSV exists
L226006 NO_SIGNAL notification remains disabled
L226007 duplicate signal_id is skipped
L226008 MT5/order/import/payload/live/autotrade flags remain OFF
L226009 CSV latest row remains CLOSED; open/as-of is not introduced
L226010 MT5/CSV timestamp basis is used; no JST detector conversion
```

## Notes

The executable Python code is provided as local VSCode code because webhook send code is not committed by the assistant GitHub connector.
