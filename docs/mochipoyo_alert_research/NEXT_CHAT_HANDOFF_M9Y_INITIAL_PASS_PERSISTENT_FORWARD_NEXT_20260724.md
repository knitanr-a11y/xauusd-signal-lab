# NEXT CHAT HANDOFF — M9Y INITIAL PASS / PERSISTENT FORWARD NEXT

Date: 2026-07-24  
Repo: `knitanr-a11y/xauusd-signal-lab`  
Branch: `feature/mochipoyo-alert-research`

## Current operating state

- M7C unchanged, audit-only.
- M8C running; never reset.
- Genuine source collector running.
- M9V v2 running unchanged with immutable MT5 server-time start `2026.07.24 11:04:00`.
- Never rerun M9V BAT00/BAT01 and never reset/backfill M9V.
- M9Y is a separate fresh payoff shadow with independent immutable start `2026.07.24 12:45:00`.
- M9Y runtime contract = `M9Y_RUNTIME_V1_APPEND_SAFE_PREFIX`.
- M9Y initial local one-shot PASSed.
- Never rerun M9Y BAT01 and never delete/reset/backfill M9Y.
- Discord / MT5 orders / live-ready / final signal / real entry gate remain OFF.

## Objective

Final objective is robust multi-timeframe/multi-asset trading edge with useful frequency and positive reward/risk (損小利大), not merely high win rate.

Current GOLD payoff architecture:
- better entry location via reclaim confirmation,
- N6 risk zone reduces size only,
- native M7C EXIT becomes a profit-management event,
- selective runner keeps a portion open while higher-timeframe momentum remains favorable.

## M9X historical exact reproduction

Formal result:
`config/mochipoyo_alert_research/m9x_gold_payoff_decoupling_local_reproduction_result_20260724.json`

Historical/research-exposed only, NOT forward validation.

Key results:
- canonical N3 = 1495
- W1 reclaim = 1054
- W1 entry-only PF = 1.587529
- runner50 + N6 one-position corrected count = 1008, PF = 1.662892, avg win +17.404 bps, avg loss -15.079 bps, payoff ~1.154:1, +2bps PF 1.327745
- runner75 + N6 one-position corrected count = 1008, PF = 1.648327, avg win +18.951 bps, avg loss -15.268 bps, payoff ~1.241:1, +2bps PF 1.330257
- 46 candidate entries overlapped an existing runner and must be skipped under one-position accounting.

Formal overlap addendum:
`config/mochipoyo_alert_research/m9x_one_position_runner_overlap_addendum_20260724.json`

## M9Y architecture

Contract:
`config/mochipoyo_alert_research/m9y_gold_payoff_fresh_prospective_shadow_contract_20260724.json`

Self-test:
`config/mochipoyo_alert_research/m9y_implementation_self_test_result_20260724.json`

Initial local result:
`config/mochipoyo_alert_research/m9y_initial_local_pass_20260724.json`

M9Y reads M9V v2 S2_M15 candidate ledger READ-ONLY to avoid duplicate M15-N3 implementation/parity drift.

Important:
- M9Y has its own fresh start; M9V start is NOT reused.
- Eligibility requires `proxy_primary_time > M9Y prospective_start_server_time`.
- M9Y freezes raw CSV prefixes and the SHA/start of the M9V runtime manifest.
- If M9V runtime manifest changes/reset occurs, M9Y blocks fail-closed.
- No historical backfill.

Arms:
- `Y0_W1_NATIVE_EXIT`: W1 reclaim, 1.0x, native exit.
- `Y1_W1_N6_NATIVE_EXIT`: W1 reclaim, N6 0.5x size only, native exit.
- `Y2_W1_N6_RUNNER50`: W1 reclaim, N6 sizing, 50% selective runner.
- `Y3_W1_N6_RUNNER75`: W1 reclaim, N6 sizing, 75% selective runner.

One position per arm. Later W1 candidates while a runner/native trade remains active are skipped/recorded metadata, not pyramiding.

## M9Y initial local PASS

Uploaded ZIP: `99_UPLOAD_PACKAGE(21).zip`  
SHA256: `d58233d6dd360b6fbbdffdb02d8bbfa287c657fdea8166c555bc5476d04fd224`

Initial one-shot:
- status = `PASS_FRESH_PROSPECTIVE_AUDIT_ONLY`
- M9Y start = MT5 server time `2026.07.24 12:45:00`
- built at UTC `2026-07-24T09:47:18Z`
- latest M1 = `2026.07.24 12:46:00`
- upstream S2 post-start = 0
- W1 candidates = 0
- Y0/Y1/Y2/Y3 accepted = 0
- overlap skips = 0

This zero-count result is EXPECTED because the one-shot was run about one M1 minute after the fresh start. It is a bootstrap/integrity PASS, not a performance result.

Verified guardrails:
- prefix integrity true
- historical_backfill false
- pre-start PRIMARY eligibility false
- one-position-per-arm true
- M9V modified/reset false
- Discord false
- MT5 order false
- live-ready false
- final signal false

## Current user action

Keep M8C / M7C / genuine source collector / M9V 03 running unchanged.

Pull latest `feature/mochipoyo-alert-research` if needed.

Now start:

`scripts/mochipoyo_alert_research/m9y/bat/03_run_shadow_forever.bat`

Keep that window open.

Never rerun:
- M9V BAT00/BAT01
- M9Y BAT01

Never reset/delete M9V or M9Y runtime/start receipts.

Use `04_stop_shadow_forever.bat` only for intentional safe stop.

At checkpoints use `05_open_latest_results.bat` and submit current M9Y `99_UPLOAD_PACKAGE.zip`.

Review gates:
- operational: Y0 accepted >=20
- interim: Y0 accepted >=60
- risk review: N6 flagged >=10
- formal: Y0 accepted >=120

These are review checkpoints, not statistical guarantees.

## Next-chat prompt

```text
repo: knitanr-a11y/xauusd-signal-lab
branch: feature/mochipoyo-alert-research

もちぽよアラート期待値・発火条件研究の続きです。
まず次を順番どおり読んでください。

1. docs/mochipoyo_alert_research/NEXT_CHAT_HANDOFF_M9Y_INITIAL_PASS_PERSISTENT_FORWARD_NEXT_20260724.md
2. config/mochipoyo_alert_research/current_state_20260723.json
3. config/mochipoyo_alert_research/next_action_20260723.json
4. config/mochipoyo_alert_research/m9y_initial_local_pass_20260724.json
5. config/mochipoyo_alert_research/m9y_gold_payoff_fresh_prospective_shadow_contract_20260724.json
6. config/mochipoyo_alert_research/m9x_gold_payoff_decoupling_local_reproduction_result_20260724.json
7. config/mochipoyo_alert_research/m9x_one_position_runner_overlap_addendum_20260724.json

M8C / M7C / genuine source collector / M9V v2 / M9Yを変更・reset・backfillしないでください。
M9V startはMT5 server time 2026.07.24 11:04:00、M9Y startは2026.07.24 12:45:00でimmutableです。
M9V BAT00/BAT01とM9Y BAT01は再実行禁止です。

M9Y初回one-shotはPASS済みで、現在は03_run_shadow_forever.batを常時稼働させる段階です。
損小利大研究はY0/Y1/Y2/Y3をfresh forwardで比較してください。
```
