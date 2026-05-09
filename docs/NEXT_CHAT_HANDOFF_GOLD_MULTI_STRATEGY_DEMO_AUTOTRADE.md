# NEXT CHAT HANDOFF - GOLD multi-strategy demo autotrade

Last updated: 2026-05-10

## Repository

```text
knitanr-a11y/xauusd-signal-lab
```

## Start by reading these docs

Read this handoff first, then read the validation/design docs below as needed:

```text
docs/NEXT_CHAT_HANDOFF_GOLD_MULTI_STRATEGY_DEMO_AUTOTRADE.md

docs/GOLD_MULTI_STRATEGY_POSITION_POLICY_PREFLIGHT_DESIGN.md
docs/GOLD_MULTI_STRATEGY_POSITION_REGISTRY_RECONCILE_VALIDATION.md
docs/GOLD_MULTI_STRATEGY_REGISTRY_POLICY_PREVIEW_VALIDATION.md
docs/GOLD_MULTI_STRATEGY_REGISTRY_FROM_PAYLOAD_PREVIEW_VALIDATION.md
docs/GOLD_MULTI_STRATEGY_DEMO_SEND_REGISTRY_PREVIEW_CYCLE_VALIDATION.md
docs/GOLD_MULTI_STRATEGY_SEND_REPORT_REGISTRY_PREVIEW_VALIDATION.md
docs/GOLD_MULTI_STRATEGY_CONTROLLED_SEND_REPORT_REGISTRY_PREVIEW_VALIDATION.md

docs/GOLD_MULTI_STRATEGY_DEMO_DRY_RUN_INTEGRATION_DESIGN.md
docs/GOLD_MULTI_STRATEGY_ROUTER_TO_AUTOTRADE_DRY_RUN_DESIGN.md
docs/GOLD_H1H4_BEAR_AB_DRY_RUN_VALIDATION_NOTES.md
docs/GOLD_SIGNAL_INTEGRATION_ROADMAP_BUY_C_ENV_AND_H1_SELL.md
docs/NEXT_CHAT_HANDOFF_GOLD_MULTI_STRATEGY_INTEGRATION.md
```

## High-level current state

We are integrating GOLD BUY/SELL multi-strategy toward demo autotrade, while keeping it separate from the existing Mochipoyo live/demo autotrade BAT.

Current strategy slots:

```text
BUY_C_ENV_RR2_72H
  strategy_id / condition_id:
  GOLD_C_ENV_H1_REGULAR_BULLISH_M15_BREAK_RR2_12H_BO8_SL_H1_PIVOT_HOLD_72H

SELL_H1H4_BEAR_AB
  strategy family:
  GOLD_H1H4_BEAR_M15_LOW_BREAK_AB_CLASSIFIER_FIXED10_RR2_12H
```

Existing Mochipoyo BAT is still intentionally untouched:

```text
scripts/run_mochipoyo_gold_demo_autotrade_forever_aligned.bat
```

The real sender is also still intentionally not modified for strategy-aware policy:

```text
scripts/send_mt5_order_from_payload.py
```

## Important safety boundary

Do not immediately modify the existing Mochipoyo BAT/loop.

Do not immediately switch the active sender from `block_any` to the new strategy-aware policy.

Do not implement close execution yet.

Do not write production `position_registry.csv` from real sender yet.

Everything added in this phase is preflight / dry-run / preview only:

```text
No mt5.order_send from registry scripts.
No mt5.order_check from registry scripts.
No existing Mochipoyo ledger mutation.
No trigger-state mutation.
No production registry mutation by default.
```

## Current safe path

Current live-ish guarded path still remains:

```text
router
  ↓
adapter preview
  ↓
Mochipoyo-compatible payload bridge
  ↓
MT5 sender dry-run or guarded one-cycle demo send
```

New registry/sender-adjacent preview path now validated separately:

```text
payload / send report
  ↓
preview position_registry row
  ↓
registry reconciliation
  ↓
registry-aware policy preview
  ↓
ALLOW/BLOCK report only
```

## Completed base components

### 1. BUY isolated dry-run

BUY strategy:

```text
GOLD_C_ENV_H1_REGULAR_BULLISH_M15_BREAK_RR2_12H_BO8_SL_H1_PIVOT_HOLD_72H
```

Status:

```text
isolated dry-run: PASS
no-signal/latest scan path: PASS
position monitor path: PASS
existing Mochipoyo/demo autotrade: NOT directly connected
```

### 2. SELL H1/H4 Bear A/B isolated dry-run

SELL family:

```text
GOLD_H1H4_BEAR_M15_LOW_BREAK_AB_CLASSIFIER_FIXED10_RR2_12H
```

Ranks:

```text
CORE_AB_CONFIRM = A and B
  trade_enabled = true
  intended lot multiplier = 2.0

B_ONLY_SAFE = B and not A
  trade_enabled = true
  intended lot multiplier = 1.0

A_ONLY_OBSERVE = A and not B
  trade_enabled = false
```

Important intended lot behavior:

```text
CORE_AB_CONFIRM -> 0.02 lot in final adapter-lot mode
B_ONLY_SAFE     -> 0.01 lot
A_ONLY_OBSERVE  -> no entry
```

Status:

```text
TP path: PASS
SL path: PASS
TIME_EXIT close intent path: PASS
duplicate signal_key path: PASS
resolved position ledger path: PASS
duplicate order intent safety path: PASS
2-cycle SELL isolated dry-run loop: PASS
```

### 3. Multi-strategy router

Script:

```text
scripts/run_gold_multi_strategy_dry_run_cycle.py
```

Validated outputs:

```text
latest_multi_strategy_cycle_result.json
multi_strategy_cycle_log.csv
strategy_status_latest.csv
combined_order_intent_dry_run.jsonl
combined_close_intent_dry_run.jsonl
```

Status:

```text
BUY/SELL no-signal aggregation: PASS
strategy status aggregation: PASS
order intent aggregation: PASS
close intent aggregation: PASS
aggregate-only mode: PASS
```

### 4. Autotrade adapter dry-run

Script:

```text
scripts/run_gold_multi_strategy_autotrade_adapter_dry_run.py
```

Status:

```text
adapter preview creation: PASS
adapter duplicate preview ledger: PASS
adapter empty ledger CSV handling: PASS
OPEN_POSITION preview: PASS
CLOSE_POSITION preview: PASS
```

### 5. Mochipoyo-compatible payload bridge

Script:

```text
scripts/build_gold_multi_strategy_mochipoyo_order_payloads_dry_run.py
```

Status:

```text
bridge from adapter preview to order_payloads.csv: PASS
empty adapter preview handling: PASS
```

Current limitation:

```text
Bridge currently defaults to fixed_lot=0.01 and use_adapter_lot=false.
Later, after sender policy integration, payload should use adapter effective_lot.
```

### 6. MT5 sender dry-run / guarded send runner

Existing sender:

```text
scripts/send_mt5_order_from_payload.py
```

Current supported position policies in sender:

```text
block_any
allow_same_direction
allow_any_until_max
```

Current sender does NOT yet support:

```text
block_same_strategy_and_opposite_direction
```

Guarded one-cycle demo autotrade send runner:

```text
scripts/run_gold_multi_strategy_demo_autotrade_send_cycle.py
```

Validated behavior:

```text
without --enable-demo-send: refused by safety guard / PASS
with --enable-demo-send and no latest signal: no payload / no send / PASS
```

Observed no-signal send-enabled result:

```text
send_enabled: true
send_requested: false
safe_send_guard_ok: true
payload_rows_out: 0
mt5_send: SKIPPED_NO_PAYLOAD_ROWS
mt5_order_send_called_count: 0
mt5_sent_rows: 0
```

## User's agreed future position policy

The user wants to move beyond `block_any` eventually.

Future policy name:

```text
block_same_strategy_and_opposite_direction
```

Rules:

```text
1. same signal_key / order_key duplicate => BLOCK
2. same strategy already has an open position => BLOCK
3. same symbol opposite direction exists => BLOCK
4. total open positions >= 5 => BLOCK
5. requested lot > 0.02 => BLOCK
6. otherwise => ALLOW
```

Position caps:

```text
Per strategy: max 1 open position
Same symbol opposite direction: blocked
Total account positions: max 5
Total account lot cap: none for now
Per order lot cap: 0.02
```

Lot expectations:

```text
GOLD_H1H4_BEAR_AB / CORE_AB_CONFIRM -> 0.02 lot
GOLD_H1H4_BEAR_AB / B_ONLY_SAFE     -> 0.01 lot
BUY C_ENV                           -> 0.01 lot initially
BTC strategies                       -> 0.01 lot initially unless later specified
```

## Why registry is needed

Current real MT5 position comments do not reliably contain full strategy ownership metadata. Example observed real position comment:

```text
mochipoyo GOLD B
```

Therefore, same-strategy max-1 should not rely only on MT5 comments.

Recommended ownership model:

```text
MT5 comment: short human-readable alias, e.g. BUY_C or SELL_AB
position_registry.csv: full source of truth for strategy_key / strategy_id / signal_key / order_key / tickets
```

## New completed preflight / registry / preview components

### 10. Position policy preflight v1/v2/v3

Scripts:

```text
scripts/run_gold_multi_strategy_position_policy_preflight.py
scripts/run_gold_multi_strategy_position_policy_preflight_v2.py
scripts/run_gold_multi_strategy_position_policy_preflight_v3.py
```

Status:

```text
v1: created, but superseded because empty payload exits before MT5 snapshot
v2: PASS, payload empty still reads MT5 position snapshot
v3: PASS, supports --mock-positions-csv for same_strategy and total_cap tests
```

Validation matrix:

```text
payloadなしでもMT5 position snapshot取得: PASS
same symbol opposite direction block: PASS
per-order lot > 0.02 block: PASS
same signal_key / order_key duplicate block: PASS
same strategy max 1 block: PASS via v3 mock positions
total open positions >= 5 block: PASS via v3 mock positions
```

Related helper scripts:

```text
scripts/build_gold_multi_strategy_position_policy_test_payload.py
scripts/build_gold_multi_strategy_mock_positions.py
```

### 11. Position registry reconciliation dry-run

Scripts:

```text
scripts/build_gold_multi_strategy_position_registry_test_data.py
scripts/run_gold_multi_strategy_position_registry_reconcile_dry_run.py
```

Status:

```text
ACTIVE registry row matched current position: PASS
ACTIVE registry row missing from current positions: PASS
Current position without ACTIVE registry row: PASS
Empty registry with current position: PASS
Read-only safety counters: PASS
```

Important reconciliation statuses:

```text
REGISTRY_ACTIVE_MATCHED
REGISTRY_ACTIVE_MATCHED_WITH_MISMATCH
REGISTRY_ACTIVE_MISSING_POSITION
POSITION_WITHOUT_ACTIVE_REGISTRY
```

Initial interpretation:

```text
REGISTRY_ACTIVE_MATCHED:
  valid owned open position; usable for same_strategy max 1

REGISTRY_ACTIVE_MATCHED_WITH_MISMATCH:
  unsafe; block new sends until inspected

REGISTRY_ACTIVE_MISSING_POSITION:
  registry cleanup/reconciliation required; do not mutate automatically yet

POSITION_WITHOUT_ACTIVE_REGISTRY:
  unmanaged existing position; still counts for symbol conflict and total cap
```

### 12. Registry-aware policy preview

Script:

```text
scripts/run_gold_multi_strategy_registry_policy_preview.py
```

Status:

```text
ACTIVE matched same-strategy registry position blocks new same-strategy payload: PASS
Registry ACTIVE missing-position inconsistency blocks new payload by default: PASS
Unregistered current position is surfaced through reconciliation output: PASS
Read-only safety counters: PASS
```

### 13. Registry row builder from payload preview

Script:

```text
scripts/build_gold_multi_strategy_position_registry_from_payload_preview.py
```

Status:

```text
Payload row converted to registry preview row: PASS
Synthetic ticket/order/deal metadata stored: PASS
strategy_key and strategy_alias inferred correctly: PASS
Preview registry row reconciles with matching mock position: PASS
Generated registry row feeds registry-aware policy preview: PASS
same_strategy BLOCK from generated registry row: PASS
Read-only safety counters: PASS
```

Validated chain:

```text
controlled payload
→ synthetic successful send result
→ preview position_registry row
→ registry reconciliation
→ registry-aware policy preview
→ same_strategy BLOCK
```

### 14. One-command demo send registry preview cycle

Script:

```text
scripts/run_gold_multi_strategy_demo_send_registry_preview_cycle.py
```

Status:

```text
payload detected: PASS
registry preview row generated from payload + synthetic send result: PASS
registry preview row reconciles with mock position: PASS
registry-aware policy preview consumes generated registry: PASS
same_strategy BLOCK from generated registry row: PASS
summary JSON/CSV generated: PASS
all child steps returncode 0: PASS
read-only safety counters: PASS
```

Validated one-command chain:

```text
controlled payload
→ synthetic successful send result
→ preview registry row
→ registry reconcile
→ registry policy preview
→ same_strategy BLOCK
→ combined summary JSON/CSV
```

### 15. Send-report registry preview wrapper

Script:

```text
scripts/run_gold_multi_strategy_send_report_registry_preview.py
```

Purpose:

```text
Read existing guarded demo send-cycle JSON.
Locate its payload_out_dir/order_payloads.csv.
Extract account/send/ticket metadata if present.
Use fallback synthetic tickets if no real tickets exist.
Build preview registry row.
Reconcile.
Run registry-aware policy preview.
```

Validated no-payload guarded report path:

```text
guarded send report exists and is readable: PASS
payload CSV path extracted from report payload_out_dir: PASS
no-payload safe early exit: PASS
source send-cycle metrics extracted: PASS
fallback ticket metadata selected for no-send report: PASS
child registry preview stages skipped when payload_rows=0: PASS
read-only safety counters: PASS
```

### 16. Controlled payload-bearing send-report path

Script:

```text
scripts/build_gold_multi_strategy_controlled_send_report.py
```

Then consumed by:

```text
scripts/run_gold_multi_strategy_send_report_registry_preview.py
```

Status:

```text
controlled payload-bearing send report generated: PASS
payload CSV copied and discoverable via payload_out_dir: PASS
send-report wrapper reads payload-bearing report: PASS
fallback synthetic tickets selected for no-real-send report: PASS
registry preview row generated from send report: PASS
registry row reconciles with mock position: PASS
registry-aware policy preview consumes generated registry: PASS
same_strategy BLOCK from generated registry row: PASS
all child steps returncode 0: PASS
read-only safety counters: PASS
```

Validated chain:

```text
controlled payload-bearing send-style report
→ payload CSV extraction
→ send metadata extraction
→ fallback ticket selection
→ registry preview row generation
→ registry reconciliation
→ registry-aware policy preview
→ same_strategy BLOCK
```

## Important generated docs

```text
docs/GOLD_MULTI_STRATEGY_POSITION_POLICY_PREFLIGHT_DESIGN.md
docs/GOLD_MULTI_STRATEGY_POSITION_REGISTRY_RECONCILE_VALIDATION.md
docs/GOLD_MULTI_STRATEGY_REGISTRY_POLICY_PREVIEW_VALIDATION.md
docs/GOLD_MULTI_STRATEGY_REGISTRY_FROM_PAYLOAD_PREVIEW_VALIDATION.md
docs/GOLD_MULTI_STRATEGY_DEMO_SEND_REGISTRY_PREVIEW_CYCLE_VALIDATION.md
docs/GOLD_MULTI_STRATEGY_SEND_REPORT_REGISTRY_PREVIEW_VALIDATION.md
docs/GOLD_MULTI_STRATEGY_CONTROLLED_SEND_REPORT_REGISTRY_PREVIEW_VALIDATION.md
```

## Important generated scripts

```text
scripts/run_gold_multi_strategy_position_policy_preflight.py
scripts/run_gold_multi_strategy_position_policy_preflight_v2.py
scripts/run_gold_multi_strategy_position_policy_preflight_v3.py
scripts/build_gold_multi_strategy_position_policy_test_payload.py
scripts/build_gold_multi_strategy_mock_positions.py
scripts/build_gold_multi_strategy_position_registry_test_data.py
scripts/run_gold_multi_strategy_position_registry_reconcile_dry_run.py
scripts/run_gold_multi_strategy_registry_policy_preview.py
scripts/build_gold_multi_strategy_position_registry_from_payload_preview.py
scripts/run_gold_multi_strategy_demo_send_registry_preview_cycle.py
scripts/run_gold_multi_strategy_send_report_registry_preview.py
scripts/build_gold_multi_strategy_controlled_send_report.py
```

## Known current limitations

```text
1. Existing active guarded send cycle still uses block_any.
2. Payload bridge currently uses fixed_lot=0.01 by default.
3. Adapter effective_lot is not yet wired into live send payloads.
4. Strategy-aware position policy is not yet implemented in send_mt5_order_from_payload.py.
5. Production position_registry.csv is not written by the real sender yet.
6. Registry cleanup/reconciliation is report-only; no automatic mutation yet.
7. Close intent MT5 execution is not implemented.
8. BTC is mentioned in future global position policy, but BTC integration into this router/send chain is not yet implemented here.
```

## Useful commands

### Preflight v2 real MT5 snapshot, payload may be empty

```cmd
python scripts\run_gold_multi_strategy_position_policy_preflight_v2.py --input-csv data\research_results\gold_multi_strategy_mochipoyo_payload_bridge_dry_run\order_payloads.csv --out-dir data\research_results\gold_multi_strategy_position_policy_preflight --order-ledger-csv data\research_results\gold_multi_strategy_mochipoyo_payload_bridge_dry_run\dry_run_order_ledger.csv --symbol GOLD# --expected-login 75539039 --require-demo-account --select-symbol --max-total-positions 5 --max-lot-per-order 0.02
```

### Controlled payload-bearing send-report validation

```cmd
python scripts\build_gold_multi_strategy_controlled_send_report.py --payload-csv data\research_results\gold_multi_strategy_position_policy_preflight\order_payloads_policy_test_same_direction_buy.csv --out-dir data\research_results\gold_multi_strategy_controlled_send_report --broker-symbol GOLD# --account-login 75539039 --account-server "XMTrading-MT5 3" --account-name "Demo Account"
```

```cmd
python scripts\run_gold_multi_strategy_send_report_registry_preview.py --send-report-json data\research_results\gold_multi_strategy_controlled_send_report\latest_multi_strategy_demo_autotrade_send_cycle_result_controlled_payload.json --positions-csv data\research_results\gold_multi_strategy_position_policy_preflight\mock_positions_same_strategy_buy_c.csv --out-dir data\research_results\gold_multi_strategy_send_report_registry_preview_controlled_payload --order-ledger-csv data\research_results\gold_multi_strategy_mochipoyo_payload_bridge_dry_run\dry_run_order_ledger.csv --symbol GOLD# --max-orders 1 --max-total-positions 5 --max-lot-per-order 0.02 --fallback-position-ticket-start 990001 --fallback-order-ticket-start 880001 --fallback-deal-ticket-start 770001 --fallback-account-login 75539039 --fallback-account-server "XMTrading-MT5 3" --position-status ACTIVE
```

Expected:

```text
cycle_ok: true
reason: SEND_REPORT_REGISTRY_PREVIEW_EVALUATED
payload_rows: 1
registry_builder.preview_ok: true
reconcile.matched_active_registry_rows: 1
policy_preview.same_strategy_blocked_rows: 1
policy_preview.final_policy_decision: BLOCK
```

### Real guarded send report no-payload wrapper

```cmd
python scripts\run_gold_multi_strategy_send_report_registry_preview.py --send-report-json data\research_results\gold_multi_strategy_demo_autotrade_send_cycle\latest_multi_strategy_demo_autotrade_send_cycle_result.json --positions-csv data\research_results\gold_multi_strategy_position_policy_preflight\mock_positions_same_strategy_buy_c.csv --out-dir data\research_results\gold_multi_strategy_send_report_registry_preview --order-ledger-csv data\research_results\gold_multi_strategy_mochipoyo_payload_bridge_dry_run\dry_run_order_ledger.csv --symbol GOLD# --max-orders 1 --max-total-positions 5 --max-lot-per-order 0.02 --fallback-position-ticket-start 990001 --fallback-order-ticket-start 880001 --fallback-deal-ticket-start 770001 --fallback-account-login 75539039 --fallback-account-server "XMTrading-MT5 3" --position-status ACTIVE
```

Expected for current no-signal report:

```text
cycle_ok: true
reason: NO_PAYLOAD_ROWS_IN_SEND_REPORT_PAYLOAD_CSV
payload_rows: 0
steps: []
```

## Recommended next task in new chat

Do not modify the real sender yet.

Next safest step:

```text
Design sender-side dry-run-only registry write preview hook,
or continue keeping registry preview as a separate post-send-report wrapper.
```

Before touching the real sender, decide explicitly:

```text
A. Keep registry preview as external post-send-report wrapper for one more round, or
B. Add sender-side dry-run-only registry preview output without --send, or
C. Add real registry write only after confirmed demo order_send success.
```

Recommended order:

```text
1. Keep separate wrapper for now.
2. Add tests for payload-bearing report with ticket fields included, not fallback tickets.
3. Only then consider a sender-side dry-run-only registry preview hook.
4. Only after that consider production registry write after real successful demo send.
```

Do not modify yet:

```text
scripts/send_mt5_order_from_payload.py
scripts/run_mochipoyo_gold_demo_autotrade_forever_aligned.bat
existing Mochipoyo ledgers
existing trigger-state files
```
