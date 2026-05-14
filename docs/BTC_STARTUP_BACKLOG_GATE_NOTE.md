# BTC_STARTUP_BACKLOG_GATE_NOTE

## Purpose

This note records the BTC multi-strategy startup backlog rule added after the May 14, 2026 incident.

## Core rule

A BTC candidate that already exists on the first loop cycle is treated as startup backlog.

The key is `payload_key`.

The runner must block only the startup backlog key, not all candidates for a fixed number of minutes.

## Why

A fixed warmup window is wrong because a fresh candidate can appear right after startup. Fresh keys must be allowed to follow the normal guarded path.

## Current files

- `scripts/run_btc_multi_strategy_guarded_demo_send_forever_aligned_weekly_state.py`
- `scripts/run_btc_multi_strategy_guarded_demo_send_once.py`
- `scripts/run_btc_multi_strategy_guarded_demo_send_forever_aligned_weekly_state.bat`

## State files

- `data/runtime_state/btc/multi_strategy/startup_backlog_payload_ledger.csv`
- `data/runtime_state/btc/multi_strategy/guarded_demo_order_ledger.csv`

## Current behavior

1. Parent runner first performs a no-action preview cycle.
2. It reads produced `payload_key` values.
3. On cycle 1, existing keys are written to the startup backlog ledger.
4. Later appearances of those keys are blocked.
5. New keys after startup can proceed through the normal Discord signal gate and guarded demo path.

## BAT status

The BTC BAT has `--allow-demo-send` and `--send` restored.

## Check fields

Review the parent summary fields:

- `payload_keys`
- `startup_backlog_capture_cycle`
- `startup_backlog_blocked`
- `startup_backlog_payload_keys`
- `send_stage_ran`
- `guarded_sender_order_send_called_count`
- `guarded_sender_sent_rows`

## Next chat

Read this note together with:

- `docs/NEXT_CHAT_HANDOFF_BTC_AFTER_GOLD_WEEKLY_RUNTIME.md`
- `scripts/run_btc_multi_strategy_guarded_demo_send_forever_aligned_weekly_state.py`
- `scripts/run_btc_multi_strategy_guarded_demo_send_once.py`
