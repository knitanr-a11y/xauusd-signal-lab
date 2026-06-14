# GOLD V3 Stage115A Spec — QUEUE_LOOP_STORAGE_ONLY

Created JST: `2026-06-14`

Stage:

```text
GOLD_V3_115A_QUEUE_LOOP_STORAGE_ONLY
```

## Purpose

Stage115A separates the storage/loop part from external message delivery.

It implements only:

```text
- every-minute loop timing at second 05
- month-based output folders
- queue/outbox records
- evaluation journal
- duplicate suppression state
- later win/loss tracking ledger
- 31-day pruning for notice history only
```

It does not implement external delivery.

## User requirements reflected

```text
loop time: every minute at HH:MM:05
folders: organized under FX_OUTPUTS/gold_v3/115a/
win/loss tracking: trade_history is separate and not pruned
notice history: older than 31 days may be pruned
```

## Output layout

```text
FX_OUTPUTS/gold_v3/115a/
  inbox/latest_signal.json
  queue/YYYY-MM/*.jsonl
  current/latest_evaluation.json
  state/loop_state.json
  journal/evaluations/YYYY-MM/*.jsonl
  journal/notices/YYYY-MM/*.jsonl
  trade_history/gold_v3_115a_virtual_signal_ledger.csv
  paste_me.txt
```

## Input signal file

Optional:

```text
FX_OUTPUTS/gold_v3/115a/inbox/latest_signal.json
```

If missing, the loop writes `NO_SIGNAL_INPUT_MISSING` and no queue item is created.

## Stage115B handoff

Stage115B may later read queue files and send them externally using the local `.env` secret.

Stage115A does not read or print the secret.
