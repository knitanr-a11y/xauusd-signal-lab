# GOLD V3 Stage115B Spec — QUEUE_SENDER_LOCAL_ENV

Created JST: `2026-06-14`

Stage:

```text
GOLD_V3_115B_QUEUE_SENDER_LOCAL_ENV
```

## Current state

Stage115A completed:

```text
status: GOLD_V3_115A_QUEUE_LOOP_STORAGE_ONLY_READY
ready: true
target_second: 5
retention_days: 31
source_csv_mutated: false
contract_mutated: false
open_asof_allowed: false
```

Stage115A creates queue files only. Stage115B sends queued messages using a local `.env` value.

## Scope

Allowed:

```text
- read queue files from FX_OUTPUTS/gold_v3/115a/queue/YYYY-MM/*.jsonl
- read local .env for endpoint URL
- mark sent items in state
- write sender journal
- never print or commit secret value
```

Still not allowed:

```text
- MT5 order execution
- real account execution
- automatic position open/close
- source CSV mutation
- CSV contract mutation
- open/as-of logic
- candidate pool removal
```

## Env keys

Search these keys in order:

```text
GOLD_V3_DISCORD_WEBHOOK_URL
DISCORD_WEBHOOK_URL
DISCORD_WEBHOOK
GOLD_DISCORD_WEBHOOK_URL
```

## Outputs

```text
FX_OUTPUTS/gold_v3/115b/current/latest_sender_result.json
FX_OUTPUTS/gold_v3/115b/state/sender_state.json
FX_OUTPUTS/gold_v3/115b/journal/YYYY-MM/gold_v3_115b_sender_YYYY-MM-DD.jsonl
FX_OUTPUTS/gold_v3/115b/gold_v3_115b_summary.json
FX_OUTPUTS/gold_v3/115b/paste_me.txt
```

## Run style

One-shot:

```text
py -3 scripts/gold_v3_runtime/gold_v3_115b_queue_sender.py
```

Loop every minute at second 05:

```text
py -3 scripts/gold_v3_runtime/gold_v3_115b_queue_sender.py --loop --target-second 5
```

## Secret handling

The endpoint value must not be printed. The output may show only whether a supported key exists and which key name was used.
