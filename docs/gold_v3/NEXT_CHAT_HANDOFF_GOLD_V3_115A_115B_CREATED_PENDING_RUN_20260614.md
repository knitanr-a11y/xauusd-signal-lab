# NEXT CHAT HANDOFF — GOLD V3 115A / 115B created, pending local run

Created JST: `2026-06-14`

## Confirmed

Stage115A user paste:

```text
status: GOLD_V3_115A_QUEUE_LOOP_STORAGE_ONLY_READY
ready: true
target_second: 5
retention_days: 31
source_csv_mutated: false
contract_mutated: false
open_asof_allowed: false
blocker_count: 0
```

## Created files

```text
docs/gold_v3/GOLD_V3_115A_QUEUE_LOOP_STORAGE_ONLY_SPEC_20260614.md
scripts/gold_v3_runtime/gold_v3_115a_queue_loop.py
docs/gold_v3/GOLD_V3_115B_QUEUE_SENDER_LOCAL_ENV_SPEC_20260614.md
scripts/gold_v3_runtime/gold_v3_115b_queue_sender.py
docs/gold_v3/NEXT_CHAT_HANDOFF_GOLD_V3_115A_115B_CREATED_PENDING_RUN_20260614.md
```

BAT writes were blocked by platform safety check, so run scripts directly from repo root.

## 115A run

One-shot:

```text
py -3 scripts/gold_v3_runtime/gold_v3_115a_queue_loop.py
```

Loop every minute at second 05:

```text
py -3 scripts/gold_v3_runtime/gold_v3_115a_queue_loop.py --loop --target-second 5 --retention-days 31
```

Paste:

```text
FX_OUTPUTS/gold_v3/115a/paste_me.txt
```

## 115B run

Dry-run sender, no external send:

```text
py -3 scripts/gold_v3_runtime/gold_v3_115b_queue_sender.py --no-send
```

Send once using local .env:

```text
py -3 scripts/gold_v3_runtime/gold_v3_115b_queue_sender.py
```

Loop every minute at second 05:

```text
py -3 scripts/gold_v3_runtime/gold_v3_115b_queue_sender.py --loop --target-second 5
```

Paste:

```text
FX_OUTPUTS/gold_v3/115b/paste_me.txt
```

## Env keys supported

```text
GOLD_V3_DISCORD_WEBHOOK_URL
DISCORD_WEBHOOK_URL
DISCORD_WEBHOOK
GOLD_DISCORD_WEBHOOK_URL
```

Secret value is not printed.

## Current design

- 115A writes queue/outbox and tracking history.
- 115B reads queue and sends only unsent queue ids.
- sent ids are stored in `115b/state/sender_state.json`.
- evaluation and notice folders are month-based.
- notice history older than 31 days can be pruned by 115A.
- trade history is not pruned by notice retention.

## Guardrails

No MT5 order execution. No real account execution. No automatic position open/close. No source CSV mutation. No CSV contract mutation. No open/as-of logic. No candidate pool removal.

Do not read/use/reference/fallback to GOLD V2, old GOLD, DISC8, or Stage41 feature-only snapshot as a trading source.
