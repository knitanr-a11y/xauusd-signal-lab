# NEXT CHAT HANDOFF - GOLD multi-strategy demo autotrade

Last updated: 2026-05-08

## Repository

```text
knitanr-a11y/xauusd-signal-lab
```

## Start by reading these docs

Read these first in the next chat:

```text
docs/GOLD_MULTI_STRATEGY_DEMO_DRY_RUN_INTEGRATION_DESIGN.md
docs/GOLD_MULTI_STRATEGY_ROUTER_TO_AUTOTRADE_DRY_RUN_DESIGN.md
docs/GOLD_H1H4_BEAR_AB_DRY_RUN_VALIDATION_NOTES.md
docs/GOLD_SIGNAL_INTEGRATION_ROADMAP_BUY_C_ENV_AND_H1_SELL.md
docs/NEXT_CHAT_HANDOFF_GOLD_MULTI_STRATEGY_INTEGRATION.md
```

## High-level current state

We are integrating two GOLD strategies toward demo autotrade, but still keeping the new multi-strategy flow separate from the existing Mochipoyo live/demo autotrade BAT.

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

## Important safety boundary

Do not immediately modify the existing Mochipoyo BAT/loop.

Do not immediately switch the active sender from `block_any` to the new strategy-aware policy.

Do not implement close execution yet.

Current safe path is:

```text
router
  ↓
adapter preview
  ↓
Mochipoyo-compatible payload bridge
  ↓
MT5 sender dry-run or guarded one-cycle demo send
```

## Completed components

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

Purpose:

```text
Read router combined order/close intents.
Validate BUY/SELL price direction.
Create adapter_order_preview.csv/jsonl.
Create adapter_close_preview.csv/jsonl.
Maintain adapter_preview_ledger.csv for duplicate preview prevention.
No MT5 calls.
No existing Mochipoyo ledger writes.
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

Purpose:

```text
Read adapter_order_preview.csv.
Write Mochipoyo-compatible order_payloads.csv.
Write order_payloads.json.
Write payload_bridge_rejects.csv.
```

Status:

```text
bridge from adapter preview to order_payloads.csv: PASS
empty adapter preview handling: PASS
```

Important current limitation:

```text
Bridge currently defaults to fixed_lot=0.01 and use_adapter_lot=false.
This was intentional for early safety.
Next policy decision requires moving toward adapter effective_lot after preflight validation.
```

### 6. MT5 sender dry-run

Existing sender:

```text
scripts/send_mt5_order_from_payload.py
```

Current supported position policies in the existing sender:

```text
block_any
allow_same_direction
allow_any_until_max
```

Current sender does NOT yet support strategy-aware position policy.

Validated dry-run command WITHOUT `--send` using generated order_payloads.csv:

```text
position_policy: block_any
expected_login: 75539039
require_demo_account: true
broker_symbol: GOLD#
max_symbol_positions: 1
max_symbol_lot: 0.01
```

Observed with existing GOLD# demo position:

```text
send_requested: False
order_send_called_count: 0
sent_rows: 0
blocked_position_policy_rows: 1
order_status: BLOCKED_POSITION_POLICY
```

Status:

```text
MT5 connection/account check: PASS
existing-position block_any guard: PASS
order_send not called: PASS
```

### 7. One-cycle multi-strategy demo dry-run runner

Script:

```text
scripts/run_gold_multi_strategy_demo_dry_run_cycle.py
```

Flow:

```text
1. run_gold_multi_strategy_dry_run_cycle.py
2. run_gold_multi_strategy_autotrade_adapter_dry_run.py
3. build_gold_multi_strategy_mochipoyo_order_payloads_dry_run.py
4. send_mt5_order_from_payload.py WITHOUT --send
5. write combined result/log
```

Status:

```text
latest no-signal cycle: PASS
safe_no_send: PASS
mt5_order_send_called_count: 0
mt5_sent_rows: 0
```

### 8. Multi-strategy demo dry-run aligned loop

Script:

```text
scripts/run_gold_multi_strategy_demo_dry_run_loop_aligned.py
```

BAT:

```text
scripts/run_gold_multi_strategy_demo_dry_run_aligned.bat
```

Status:

```text
2-cycle finite loop: PASS
lock acquire/release: PASS
no-signal/no-payload path: PASS
safe_no_send: PASS
BAT loop confirmed with ITERATIONS=0 / align-to-minute / align-to-second 2
```

### 9. Guarded one-cycle demo autotrade send runner

Script:

```text
scripts/run_gold_multi_strategy_demo_autotrade_send_cycle.py
```

Purpose:

```text
Run one cycle and call send_mt5_order_from_payload.py with --send only if --enable-demo-send is explicitly provided.
```

Safety guard requires:

```text
--enable-demo-send
expected_login = 75539039
require_demo_account = true
broker_symbol = GOLD#
fixed_lot = 0.01
position_policy = block_any
max_symbol_positions = 1
max_symbol_lot = 0.01
max_orders = 1
```

Validated behavior:

```text
without --enable-demo-send: refused by safety guard / PASS
with --enable-demo-send and no latest signal: no payload / no send / PASS
```

Observed latest send-enabled no-signal result:

```text
send_enabled: true
send_requested: false
safe_send_guard_ok: true
payload_rows_out: 0
mt5_send: SKIPPED_NO_PAYLOAD_ROWS
mt5_order_send_called_count: 0
mt5_sent_rows: 0
```

## Key user decision at end of chat

The user wants to move beyond `block_any` eventually.

Final agreed future position policy:

```text
Each strategy: max 1 open position.
Different strategy: can be an additional entry candidate.
Same symbol opposite direction: block.
Total account positions across GOLD/BTC etc.: max 5.
No total-lot cap for now.
Per-order lot cap: 0.02.
Use adapter effective_lot instead of fixed_lot.
```

Lot expectations:

```text
GOLD_H1H4_BEAR_AB / CORE_AB_CONFIRM -> 0.02 lot
GOLD_H1H4_BEAR_AB / B_ONLY_SAFE     -> 0.01 lot
BUY C_ENV                           -> 0.01 lot initially
BTC strategies                       -> 0.01 lot initially unless later specified
```

Suggested policy name:

```text
block_same_strategy_and_opposite_direction
```

Suggested rules:

```text
1. same signal_key is blocked by order_key / adapter preview ledger
2. same strategy is limited to 1 open position
3. same symbol opposite direction is blocked
4. total open positions across GOLD/BTC etc. is capped at 5
5. no total-lot cap for now
6. per-order lot cap remains 0.02
7. payload should use adapter effective_lot, not fixed_lot
```

## Important implementation note

An attempt was made to directly modify `scripts/send_mt5_order_from_payload.py` to add the strategy-aware position policy, but the tool safety check blocked that update. Therefore, do not continue by forcing direct sender changes.

Next recommended step is safer:

```text
Implement a separate dry-run/preflight checker first.
```

Recommended script:

```text
scripts/run_gold_multi_strategy_position_policy_preflight.py
```

Purpose:

```text
Read current MT5 positions.
Read the current order_payloads.csv candidate.
Do NOT call order_send.
Evaluate the future policy:
  same strategy block
  same-symbol opposite direction block
  total positions >= 5 block
  requested lot > 0.02 block
  otherwise allow
Write CSV/JSON report.
```

Suggested outputs:

```text
strategy_position_policy_preflight.csv
strategy_position_policy_preflight.json
```

Suggested report fields:

```text
requested_strategy_key
requested_symbol
requested_direction
requested_lot
existing_total_positions
existing_symbol_positions
existing_symbol_directions
same_strategy_blocked
opposite_direction_blocked
total_position_cap_blocked
per_order_lot_blocked
final_policy_decision
final_policy_reason
```

Only after this preflight passes should the actual sender be modified to support strategy-aware policy in send mode.

## Known current limitations

```text
1. Existing active send cycle still uses block_any.
2. Payload bridge currently uses fixed_lot=0.01 by default.
3. Adapter effective_lot is not yet wired into live send payloads.
4. Strategy-aware position policy is not yet implemented in the sender.
5. Close intent execution is not implemented.
6. BTC is mentioned in the future global position policy, but BTC integration into this router/send chain is not yet implemented in this chat.
```

## Commands recently used / useful

Safety guard refusal test:

```cmd
python scripts\run_gold_multi_strategy_demo_autotrade_send_cycle.py --csv-dir "C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files"
```

Expected:

```text
cycle_ok: false
safe_send_guard_ok: false
--enable-demo-send is required
```

Send-enabled one-cycle test:

```cmd
python scripts\run_gold_multi_strategy_demo_autotrade_send_cycle.py --csv-dir "C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files" --enable-demo-send
```

Current latest result had no signal and no send.

Dry-run BAT:

```cmd
scripts\run_gold_multi_strategy_demo_dry_run_aligned.bat
```

Default BAT behavior:

```text
ITERATIONS=0 means continuous loop until Ctrl+C.
No --send.
Aligns to minute + second 2.
```

## Recommended next task in new chat

Start by implementing the preflight only:

```text
scripts/run_gold_multi_strategy_position_policy_preflight.py
```

Do not alter `send_mt5_order_from_payload.py` yet.

After preflight, validate using current demo account positions and a controlled payload file.

Then update docs and only then revisit sender support for:

```text
--position-policy block_same_strategy_and_opposite_direction
--max-total-positions 5
--max-lot-per-order 0.02
--use-adapter-lot path in bridge/send flow
```
