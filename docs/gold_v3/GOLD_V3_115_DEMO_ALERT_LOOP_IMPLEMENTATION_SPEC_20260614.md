# GOLD V3 Stage115 Spec — DEMO_ALERT_LOOP_IMPLEMENTATION

Created JST: `2026-06-14`

Stage:

```text
GOLD_V3_115_DEMO_ALERT_LOOP_IMPLEMENTATION
```

## Background

Stage114 authorized only:

```text
DEMO_LIVE_EVALUATOR_DISCORD_ALERT_ONLY
```

Stage114 explicitly kept execution and real-account use disabled.

User requirements added after Stage114:

```text
- Discord webhook is in a local .env file.
- Loop should run at every minute second 05, i.e. 00 seconds plus 5 seconds lag.
- Keep output folders tidy.
- Make later win/loss history easy to trace.
- Notification history older than about one month may be discarded.
```

## Scope

Stage115 implements the alert loop shell and storage contract.

Allowed:

```text
- read local .env for Discord webhook URL
- run once or loop
- loop target second defaults to 5
- write tidy month/day journal files
- keep alert notification history for 31 days
- keep virtual signal / outcome ledger separately for longer analysis
- suppress duplicate alerts
- NO_SIGNAL writes evaluation journal but sends no alert
```

Still not allowed:

```text
- order execution
- real account use
- source CSV mutation
- CSV contract mutation
- open/as-of candle logic
- candidate pool removal
```

## Env key support

The script must search these keys, in this order:

```text
GOLD_V3_DISCORD_WEBHOOK_URL
DISCORD_WEBHOOK_URL
DISCORD_WEBHOOK
GOLD_DISCORD_WEBHOOK_URL
```

Secrets must never be committed or printed.

## Loop timing

Default loop timing:

```text
target_second: 5
interval: every minute
```

Meaning:

```text
HH:MM:05
HH:MM+1:05
HH:MM+2:05
...
```

## Folder layout

```text
FX_OUTPUTS/gold_v3/115c/
  current/
    latest_evaluation.json
  state/
    alert_state.json
  journal/
    evaluations/YYYY-MM/gold_v3_115_evaluations_YYYY-MM-DD.jsonl
    alerts/YYYY-MM/gold_v3_115_alerts_YYYY-MM-DD.jsonl
  trade_history/
    gold_v3_115_virtual_signal_ledger.csv
  inbox/
    latest_signal.json
  paste_me.txt
```

`journal/alerts` may be pruned after 31 days.

`trade_history` should not be pruned by the alert retention rule.

## Signal input contract for Stage115

Stage115 does not fake signals.

It reads an optional current signal file:

```text
FX_OUTPUTS/gold_v3/115c/inbox/latest_signal.json
```

Expected fields:

```json
{
  "signal_id": "unique-id",
  "entry_dt": "2026-06-14T21:50:00+09:00",
  "symbol": "XAUUSD",
  "side": "LONG or SHORT or NO_SIGNAL or STOP_REVIEW",
  "entry_price": 0,
  "tp": 0,
  "sl": 0,
  "reason": "text"
}
```

If this file is missing, Stage115 records an evaluation as `NO_SIGNAL_INPUT_MISSING` and sends no alert.

## Outputs

```text
FX_OUTPUTS/gold_v3/115c/gold_v3_115_runtime_contract_summary.csv
FX_OUTPUTS/gold_v3/115c/gold_v3_115_folder_layout_matrix.csv
FX_OUTPUTS/gold_v3/115c/gold_v3_115_env_key_matrix.csv
FX_OUTPUTS/gold_v3/115c/gold_v3_115_retention_policy.csv
FX_OUTPUTS/gold_v3/115c/gold_v3_115_quality_gate_matrix.csv
FX_OUTPUTS/gold_v3/115c/gold_v3_115_blocker_matrix.csv
FX_OUTPUTS/gold_v3/115c/gold_v3_115_validation_matrix.csv
FX_OUTPUTS/gold_v3/115c/gold_v3_115_summary.json
FX_OUTPUTS/gold_v3/115c/GOLD_V3_115_DEMO_ALERT_LOOP_IMPLEMENTATION_REPORT.md
FX_OUTPUTS/gold_v3/115c/paste_me.txt
```

## Decision

Allowed decisions:

```text
DEMO_ALERT_LOOP_IMPLEMENTATION_READY
DEMO_ALERT_LOOP_IMPLEMENTATION_BLOCKED
```

## Important

This stage can test connectivity with `--send-test`, but the default should not spam Discord.
