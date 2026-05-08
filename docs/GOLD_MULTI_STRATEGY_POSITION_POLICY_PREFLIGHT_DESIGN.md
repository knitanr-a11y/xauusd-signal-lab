# GOLD multi-strategy position policy preflight design

Last updated: 2026-05-09

## Purpose

This document records the design status for the future GOLD multi-strategy MT5 position policy before modifying the real order sender.

The current goal is to move beyond the existing sender-level `block_any` policy and prepare a safer strategy-aware policy:

```text
block_same_strategy_and_opposite_direction
```

The key decision is:

```text
Do not modify send_mt5_order_from_payload.py yet.
Validate the future position policy with a preflight-only checker first.
```

## Safety boundary

The preflight layer must remain non-executing:

```text
No mt5.order_send.
No mt5.order_check.
No existing Mochipoyo ledger mutation.
No trigger-state mutation.
No existing BAT mutation.
No close-position execution.
```

The existing sender is still the only script that can eventually call order_check/order_send, and it must not be changed until the strategy-aware policy behavior is validated.

## Current existing sender limitation

Current script:

```text
scripts/send_mt5_order_from_payload.py
```

Current supported position policies:

```text
block_any
allow_same_direction
allow_any_until_max
```

The following policy is not yet implemented in the sender:

```text
block_same_strategy_and_opposite_direction
```

Therefore, all strategy-aware validation is currently done outside the sender.

## Implemented preflight scripts

### v1 preflight

Script:

```text
scripts/run_gold_multi_strategy_position_policy_preflight.py
```

Status:

```text
Created.
Safe, but v1 exits early when order_payloads.csv has no rows.
Because of that, v1 does not read MT5 positions on empty-payload cycles.
```

### v2 preflight

Script:

```text
scripts/run_gold_multi_strategy_position_policy_preflight_v2.py
```

Status:

```text
PASS.
```

Important v2 improvement:

```text
Even when order_payloads.csv is missing or empty, v2 still initializes MT5,
checks the expected account guard,
checks the demo account guard,
reads current open positions,
and writes the current MT5 position snapshot.
```

Primary outputs:

```text
data/research_results/gold_multi_strategy_position_policy_preflight/strategy_position_policy_preflight.csv
data/research_results/gold_multi_strategy_position_policy_preflight/strategy_position_policy_preflight.json
data/research_results/gold_multi_strategy_position_policy_preflight/strategy_position_policy_preflight_positions.csv
```

Default command:

```cmd
python scripts\run_gold_multi_strategy_position_policy_preflight_v2.py --input-csv data\research_results\gold_multi_strategy_mochipoyo_payload_bridge_dry_run\order_payloads.csv --out-dir data\research_results\gold_multi_strategy_position_policy_preflight --order-ledger-csv data\research_results\gold_multi_strategy_mochipoyo_payload_bridge_dry_run\dry_run_order_ledger.csv --symbol GOLD# --expected-login 75539039 --require-demo-account --select-symbol --max-total-positions 5 --max-lot-per-order 0.02
```

## Implemented controlled payload builder

Script:

```text
scripts/build_gold_multi_strategy_position_policy_test_payload.py
```

Status:

```text
PASS.
```

Purpose:

Create controlled local `order_payloads.csv` files for policy preflight validation.

Safety:

```text
No MT5 import.
No order_check.
No order_send.
No ledger write.
```

Supported scenarios:

```text
opposite_sell
same_direction_buy
over_lot_sell
duplicate_pair
```

## Policy candidate

Policy name:

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

Initial sizing assumptions:

```text
GOLD_H1H4_BEAR_AB / CORE_AB_CONFIRM => 0.02 lot
GOLD_H1H4_BEAR_AB / B_ONLY_SAFE => 0.01 lot
BUY C_ENV => 0.01 lot
BTC strategy family, future => 0.01 lot
```

Position caps:

```text
Per strategy: max 1 open position
Same symbol opposite direction: blocked
Total account positions: max 5
Total account lot cap: none for now
Per order lot cap: 0.02
```

## Current MT5 snapshot validation

Validated account:

```text
login: 75539039
server: XMTrading-MT5 3
name: Demo Account
symbol: GOLD#
```

Latest known open position during validation:

```text
GOLD# BUY 0.01
magic: 26050601
comment: mochipoyo GOLD B
```

Important observation:

```text
The current MT5 position comment does not contain a stable strategy key.
detected_strategy is empty.
```

This means exact same-strategy detection is not reliable from current MT5 comments alone.

## Validated preflight paths

### Empty payload with MT5 position snapshot

Command:

```cmd
python scripts\run_gold_multi_strategy_position_policy_preflight_v2.py --input-csv data\research_results\gold_multi_strategy_mochipoyo_payload_bridge_dry_run\order_payloads.csv --out-dir data\research_results\gold_multi_strategy_position_policy_preflight --order-ledger-csv data\research_results\gold_multi_strategy_mochipoyo_payload_bridge_dry_run\dry_run_order_ledger.csv --symbol GOLD# --expected-login 75539039 --require-demo-account --select-symbol --max-total-positions 5 --max-lot-per-order 0.02
```

Observed:

```text
preflight_ok: true
reason: NO_INPUT_ROWS
no_payload_snapshot_ok: true
initialize_ok: true
account_login: 75539039
existing_total_positions: 1
existing_snapshot_symbol_positions: 1
existing_snapshot_symbol_directions: BUY
existing_snapshot_symbol_lot: 0.01
order_send_called_count: 0
order_check_called_count: 0
```

Decision:

```text
PASS.
```

### Opposite direction block

Build controlled payload:

```cmd
python scripts\build_gold_multi_strategy_position_policy_test_payload.py --scenario opposite_sell --out-dir data\research_results\gold_multi_strategy_position_policy_preflight --broker-symbol GOLD# --entry-price 4727.67
```

Run preflight:

```cmd
python scripts\run_gold_multi_strategy_position_policy_preflight_v2.py --input-csv data\research_results\gold_multi_strategy_position_policy_preflight\order_payloads_policy_test_opposite_sell.csv --out-dir data\research_results\gold_multi_strategy_position_policy_preflight --order-ledger-csv data\research_results\gold_multi_strategy_mochipoyo_payload_bridge_dry_run\dry_run_order_ledger.csv --symbol GOLD# --expected-login 75539039 --require-demo-account --select-symbol --max-total-positions 5 --max-lot-per-order 0.02
```

Observed:

```text
rows_in: 1
rows_out: 1
blocked_rows: 1
opposite_direction_blocked_rows: 1
per_order_lot_blocked_rows: 0
final_policy_decision: BLOCK
order_send_called_count: 0
order_check_called_count: 0
```

Reason:

```text
opposite_direction: existing same-symbol opposite direction position(s): requested=SELL; existing_directions=['BUY']
```

Decision:

```text
PASS.
```

### Per-order lot cap block

Build controlled payload:

```cmd
python scripts\build_gold_multi_strategy_position_policy_test_payload.py --scenario over_lot_sell --out-dir data\research_results\gold_multi_strategy_position_policy_preflight --broker-symbol GOLD# --entry-price 4727.67
```

Run preflight:

```cmd
python scripts\run_gold_multi_strategy_position_policy_preflight_v2.py --input-csv data\research_results\gold_multi_strategy_position_policy_preflight\order_payloads_policy_test_over_lot_sell.csv --out-dir data\research_results\gold_multi_strategy_position_policy_preflight --order-ledger-csv data\research_results\gold_multi_strategy_mochipoyo_payload_bridge_dry_run\dry_run_order_ledger.csv --symbol GOLD# --expected-login 75539039 --require-demo-account --select-symbol --max-total-positions 5 --max-lot-per-order 0.02
```

Observed:

```text
rows_in: 1
rows_out: 1
blocked_rows: 1
opposite_direction_blocked_rows: 1
per_order_lot_blocked_rows: 1
final_policy_decision: BLOCK
order_send_called_count: 0
order_check_called_count: 0
```

Reason includes:

```text
per_order_lot: requested lot exceeds per-order cap: requested_lot=0.03; max_lot_per_order=0.02
```

Decision:

```text
PASS.
```

### Duplicate signal_key / order_key block

Build controlled payload:

```cmd
python scripts\build_gold_multi_strategy_position_policy_test_payload.py --scenario duplicate_pair --out-dir data\research_results\gold_multi_strategy_position_policy_preflight --broker-symbol GOLD# --entry-price 4727.67
```

Run preflight:

```cmd
python scripts\run_gold_multi_strategy_position_policy_preflight_v2.py --input-csv data\research_results\gold_multi_strategy_position_policy_preflight\order_payloads_policy_test_duplicate_pair.csv --out-dir data\research_results\gold_multi_strategy_position_policy_preflight --order-ledger-csv data\research_results\gold_multi_strategy_mochipoyo_payload_bridge_dry_run\dry_run_order_ledger.csv --symbol GOLD# --expected-login 75539039 --require-demo-account --select-symbol --max-total-positions 5 --max-lot-per-order 0.02
```

Observed:

```text
rows_in: 2
rows_out: 2
blocked_rows: 2
duplicate_key_blocked_rows: 1
opposite_direction_blocked_rows: 2
order_send_called_count: 0
order_check_called_count: 0
```

Row behavior:

```text
row 1: opposite_direction BLOCK
row 2: duplicate_key BLOCK + opposite_direction BLOCK
```

Decision:

```text
PASS.
```

## Remaining policy validations

Not yet fully validated:

```text
total open positions >= 5 block
same strategy max 1 position block
```

### Total open positions cap

This can be validated later either by:

```text
1. creating a test mode that injects mocked position rows into preflight, or
2. waiting until a demo environment has >=5 open positions, which is not recommended just for testing.
```

Recommended next implementation for testing only:

```text
Add optional --mock-positions-csv to preflight v2 or a v3 script.
```

This would allow total-position-cap tests without opening real positions.

### Same strategy max 1 position

Current blocker:

```text
MT5 position comment currently has no stable strategy key.
Example current comment: mochipoyo GOLD B
```

Therefore, preflight cannot reliably know which strategy owns an existing position from MT5 alone.

Do not implement sender same-strategy blocking until position ownership metadata is defined.

## Strategy ownership design options

### Option A: MT5 comment only

Use MT5 order comment to encode strategy key.

Pros:

```text
Simple.
Visible in MT5 terminal.
No separate registry required.
```

Cons:

```text
MT5 comment is short and broker/platform dependent.
Existing sender already truncates comments to 31 chars.
Long strategy IDs do not fit.
Comments may be altered by broker/server.
Hard to encode strategy_id + signal_key safely.
```

Assessment:

```text
Not recommended as the sole source of truth.
```

### Option B: Dedicated position registry CSV

Create an isolated registry written only after successful send.

Possible file:

```text
data/research_results/gold_multi_strategy_position_registry/position_registry.csv
```

Minimum columns:

```text
created_at_utc
account_login
account_server
broker_symbol
symbol
position_ticket
order_ticket
deal_ticket
magic_number
direction
lot
entry_price
sl_price
tp_price
strategy_key
strategy_id
condition_id
signal_key
order_key
payload_key
router_strategy_slot
router_strategy_id
candidate_rank
source_payload_csv
sender_report_json
position_status
last_seen_utc
close_status
close_reason
```

Pros:

```text
Stable.
Can store full strategy_id and signal_key.
Can support same_strategy max 1 logic.
Can support future close intent matching.
Can support resolved-position cleanup.
Avoids MT5 comment length limits.
```

Cons:

```text
Requires careful write timing.
Must only write after confirmed successful order_send.
Must reconcile with MT5 open positions on each cycle.
Needs handling for manual close or missing ticket.
```

Assessment:

```text
Recommended as the primary source of truth.
```

### Option C: Hybrid comment + registry

Use short MT5 comment plus dedicated registry.

Example short comment:

```text
ms BUY_C 26050601
ms SELL_AB 26050601
```

Registry stores full metadata.

Pros:

```text
Human-readable MT5 terminal comment.
Full metadata preserved in registry.
Still allows rough fallback if registry is missing.
```

Cons:

```text
Still requires registry for reliable logic.
```

Assessment:

```text
Recommended final approach.
```

## Recommended design decision

Use a hybrid design:

```text
MT5 comment: short human-readable strategy alias only.
Position registry CSV: full strategy ownership and signal metadata.
```

Recommended aliases:

```text
BUY_C_ENV_RR2_72H => BUY_C
SELL_H1H4_BEAR_AB => SELL_AB
BTC future strategies => BTC_<short_alias>
```

The actual same-strategy block should use the registry, not the MT5 comment.

## Future sender integration plan

Do not implement all at once.

Recommended sequence:

```text
1. Keep preflight v2 as the validation layer.
2. Add optional mocked position input to preflight for total-cap and same-strategy tests.
3. Design position_registry.csv schema and reconciliation rules.
4. Add registry write only after successful sender SENT result.
5. Add sender policy block_same_strategy_and_opposite_direction in dry-run mode first.
6. Validate sender WITHOUT --send using controlled payloads.
7. Validate sender WITH --send only after explicit approval and demo account guard.
```

## Future sender policy logic

When implemented in sender, the policy should evaluate:

```text
existing MT5 open positions
+ strategy ownership registry
+ current payload candidate
+ sent-order ledger duplicate keys
```

Rules should be evaluated in this order:

```text
1. Account guard
2. Payload local validation
3. Duplicate order_key / signal_key
4. Registry reconciliation with current MT5 positions
5. Same strategy max 1
6. Same symbol opposite direction
7. Total account positions max 5
8. Per-order lot max 0.02
9. Symbol info / volume step / price sanity
10. order_check
11. order_send only if --send
```

## Close intent note

Close intent execution is still not implemented.

The same registry will likely be required for future close execution because close intents need to match:

```text
strategy_id
signal_key
position_ticket
broker_symbol
direction
lot
```

Do not implement MT5 close execution before the registry/matching rules are finalized.

## Current recommendation

Next safe step:

```text
Add mocked-position support to preflight, or create a v3 preflight, so same_strategy and total_position_cap can be tested without opening real demo positions.
```

Do not modify:

```text
scripts/send_mt5_order_from_payload.py
scripts/run_mochipoyo_gold_demo_autotrade_forever_aligned.bat
existing Mochipoyo ledgers
existing trigger-state files
```
