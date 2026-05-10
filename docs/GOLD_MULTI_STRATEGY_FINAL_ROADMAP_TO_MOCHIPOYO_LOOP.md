# GOLD multi-strategy final roadmap to Mochipoyo loop

Last updated: 2026-05-10

## Purpose

This document is a high-level roadmap for the GOLD multi-strategy work.

The purpose is to prevent the project from drifting into sender / registry / BAT details without keeping sight of the real goal.

The real goal is not just to build registry previews.

The real goal is:

```text
Find and program high-quality GOLD BUY/SELL signal conditions
→ run them as independent multi-strategy candidates
→ connect them safely to the Mochipoyo signal loop
→ notify / dry-run / guarded demo-send without breaking the existing Mochipoyo production flow
```

## Original trading idea

The project came from two chart-driven ideas.

### 1. H4 divergence rise capture

The first target was a GOLD rise after an H4 divergence area.

The intended trading logic was roughly:

```text
H4 hidden / continuation-style bullish divergence area
→ M15 reversal confirmation
→ M5 pullback / EMA20 re-acceleration
→ BUY entry candidate
```

This led to the BUY-side strategy slot:

```text
BUY_C_ENV_RR2_72H
  GOLD_C_ENV_H1_REGULAR_BULLISH_M15_BREAK_RR2_12H_BO8_SL_H1_PIVOT_HOLD_72H
```

The current BUY-side concept is not just "buy because divergence exists".

It is meant to capture a higher-quality continuation / reversal zone by combining:

```text
higher-timeframe bullish environment
H1 regular bullish divergence / structure context
M15 break confirmation
RR2 style target / stop design
bounded holding window
```

### 2. H1 down move capture

The second target was a GOLD H1 down move that the user pointed out later.

The intended trading logic was roughly:

```text
H1/H4 bearish context
→ M15 low break / continuation confirmation
→ AB classifier / fixed target-risk design
→ SELL entry candidate
```

This led to the SELL-side strategy slot:

```text
SELL_H1H4_BEAR_AB
  GOLD_H1H4_BEAR_M15_LOW_BREAK_AB_CLASSIFIER_FIXED10_RR2_12H
```

The current SELL-side concept is not just "sell because price falls".

It is meant to capture a higher-quality bearish continuation zone by combining:

```text
H1/H4 bearish structure
M15 low-break confirmation
AB-style classifier filter
fixed10 / RR2 style outcome design
bounded holding window
```

## Current strategic slots

The active GOLD multi-strategy slots are:

```text
BUY_C_ENV_RR2_72H
SELL_H1H4_BEAR_AB
```

These are not intended to be mixed directly into the existing Mochipoyo core immediately.

They should first run as an independent demo dry-run / guarded demo-send flow.

## Why the sender / registry work exists

The sender / registry work is not the trading signal itself.

It exists because once multiple strategies produce orders, the system needs safety around:

```text
whether an order would be valid
whether the account / symbol / lot / SL / TP are safe
whether the same strategy already has an active position
whether an opposite-direction conflict exists
whether a payload can become a registry row
whether registry-aware policy can block duplicates
```

The sender / registry layer is therefore a safety bridge between:

```text
strategy signal generation
```

and:

```text
notification / dry-run / guarded demo send
```

It should not replace the signal research work.

It should not become the main project by itself.

## Current validated sender / registry status

As of the latest validation, the following dry-run path is validated:

```text
fresh MT5 tick payload
→ real send_mt5_order_from_payload.py dry-run
→ DRY_RUN_ORDER_CHECK_OK
→ sender-native registry preview CSV/JSON
→ registry-derived mock position
→ exact reconcile
→ registry-aware policy preview
→ same_strategy BLOCK
```

Validated safety boundary:

```text
--send is not passed
order_send_called_count=0
sent_rows=0
production position_registry.csv is not written
existing Mochipoyo ledgers are not intentionally mutated
trigger-state files are not intentionally mutated
existing Mochipoyo production BATs are not modified
```

The important result is:

```text
The sender can now emit a disabled-by-default registry preview row.
That preview row can be consumed by mock-position, reconcile, and registry-aware policy tools.
The policy layer can block same-strategy duplicate exposure.
```

This is useful, but it is only a support layer.

## Critical reminder

Do not confuse these two things:

```text
Signal edge work:
  Find conditions that have trading value.

Execution safety work:
  Make sure valid signals can be sent / blocked / tracked safely.
```

The final system needs both.

But the project must keep returning to the signal path:

```text
BUY/SELL signal logic
→ multi-strategy scanner/router
→ Mochipoyo loop integration
```

## Big-picture architecture

The intended final architecture is:

```text
MT5 / MQL5 CSV export
  ↓
Independent GOLD multi-strategy scanner
  ↓
BUY_C_ENV_RR2_72H candidate generation
SELL_H1H4_BEAR_AB candidate generation
  ↓
Multi-strategy router / candidate selector
  ↓
Mochipoyo-compatible payload builder
  ↓
Notification / AI review / dry-run send layer
  ↓
Guarded sender
  ↓
Registry preview / future registry write
  ↓
Position policy / duplicate prevention
  ↓
Eventually: guarded demo send lifecycle
```

The current work is mainly around the lower half:

```text
payload builder
→ guarded sender
→ registry preview
→ policy preview
```

The next planning work must reconnect this lower half to the upper half:

```text
BUY/SELL scanner/router
→ Mochipoyo loop
```

## What is done

### A. BUY/SELL strategy concepts exist

The two current slots are known:

```text
BUY_C_ENV_RR2_72H
SELL_H1H4_BEAR_AB
```

### B. Independent dry-run / guarded sender path exists

The system can create a fresh payload and send it through the real sender in dry-run mode.

### C. Sender-native registry preview hook exists

`send_mt5_order_from_payload.py` can emit preview registry CSV/JSON only when preview output flags are explicitly passed.

This is disabled-by-default behavior.

### D. Registry-aware policy preview works on sender-native preview rows

The preview registry row can be converted into a mock open position, reconciled, and used to block same-strategy duplicates.

### E. A one-command validation BAT exists

The following BAT validates the sender-native preview hook path:

```cmd
scripts\run_gold_multi_strategy_sender_native_registry_preview_hook_validation.bat
```

## What is not done yet

The following are not complete and should not be assumed complete:

```text
Production position_registry.csv write
Actual demo order send with --send
Real MT5 position reconciliation after an actual send
Close intent / lifecycle management
Existing Mochipoyo live loop integration
Existing Mochipoyo production BAT modification
BTC router / sender integration
Full end-to-end live notification loop for these new GOLD strategies
```

## Important safety rule

Until explicitly decided, do not modify:

```text
production position_registry.csv
existing Mochipoyo ledgers
existing trigger-state files
scripts/run_mochipoyo_gold_demo_autotrade_forever_aligned.bat
close intent MT5 execution
BTC router/send integration
```

## Roadmap from here

### Phase 0: Freeze current state mentally

Goal:

```text
Confirm that the current sender / registry preview work is only a safety bridge,
not the final trading system.
```

Expected command:

```cmd
scripts\run_gold_multi_strategy_sender_native_registry_preview_hook_validation.bat
```

Expected result:

```text
GOLD sender-native registry preview hook validation PASS
```

No new trading behavior should be added in this phase.

### Phase 1: Reconnect to signal source

Goal:

```text
Trace where BUY_C_ENV_RR2_72H and SELL_H1H4_BEAR_AB are generated.
Confirm which script creates the candidates.
Confirm which columns identify strategy slot, strategy id, direction, entry, SL, TP, signal key, and order key.
```

Questions to answer:

```text
Which script scans BUY_C_ENV_RR2_72H?
Which script scans SELL_H1H4_BEAR_AB?
Which output CSV is the canonical candidate table?
Does each candidate already contain router_strategy_slot?
Does each candidate already contain strategy_id / condition_id?
Does each candidate have stable signal_key / order_key behavior?
```

This phase is about reading and mapping, not adding new send behavior.

### Phase 2: Reconnect to Mochipoyo loop without mixing into production

Goal:

```text
Build or confirm an independent GOLD multi-strategy demo loop that runs beside Mochipoyo,
not inside the existing production Mochipoyo loop.
```

Expected flow:

```text
Read MT5 CSVs
→ scan BUY/SELL multi-strategy candidates
→ router chooses eligible candidates
→ build Mochipoyo-compatible payloads
→ dry-run / preview / policy validation
```

Safety:

```text
No production ledger mutation
No production trigger-state mutation
No production registry write
No existing live BAT modification
```

### Phase 3: Notification-level integration

Goal:

```text
Send Discord-style notifications or dry-run notification payloads for the new GOLD strategies,
while still not placing real orders.
```

Expected checks:

```text
duplicate signal prevention
strategy slot labels visible in notification
direction / entry / SL / TP visible
AI review payload compatibility, if used
ledger dry-run / no-row skip behavior
```

This phase should happen before demo send.

### Phase 4: Guarded demo-send preparation

Goal:

```text
Allow an explicitly guarded demo-send path only after notification/dry-run behavior is stable.
```

Required before this phase:

```text
sender-native registry preview validation PASS
same_strategy BLOCK validation PASS
opposite-direction policy behavior validated
position cap behavior validated
lot cap behavior validated
account guard validated
symbol guard validated
```

Still do not write production registry unless explicitly approved.

### Phase 5: Actual demo-send lifecycle design

Goal:

```text
Define what happens after a real demo order is sent.
```

Must define before implementation:

```text
How to derive actual position ticket / order ticket / deal ticket
How to write production or demo registry safely
How to reconcile against real MT5 positions
How to handle partially missing MT5 ticket metadata
How to close or mark positions inactive
How close intent is represented
How duplicate prevention works after real sends
```

This phase is not complete yet.

### Phase 6: Existing Mochipoyo loop integration

Goal:

```text
Only after the independent demo flow is stable,
connect the new GOLD multi-strategy flow into the Mochipoyo loop in a controlled way.
```

Rules:

```text
Do not directly modify existing production BAT first.
Create a guarded demo BAT or wrapper first.
Keep a rollback path.
Keep old Mochipoyo strategies unaffected.
Make new strategies disabled-by-default if possible.
```

### Phase 7: Production-like operation decision

Goal:

```text
Decide whether the flow remains notification-only,
dry-run only,
guarded demo-send,
or eventually production-capable.
```

This is a user decision point, not an automatic coding step.

## Current recommended next step

Do not continue deeper into registry implementation right now.

Recommended next step:

```text
Trace and verify the path from the two strategy slots to the candidate/router/payload layer.
```

Specifically, read the scripts/docs that define:

```text
BUY_C_ENV_RR2_72H
SELL_H1H4_BEAR_AB
multi-strategy router
Mochipoyo-compatible payload builder
independent demo dry-run loop
```

The next useful output should be a map like:

```text
Script A reads CSVs and generates BUY candidate rows.
Script B reads CSVs and generates SELL candidate rows.
Script C combines/routes them.
Script D builds order_payloads.csv.
Script E sends dry-run / preview.
Script F would later be called by Mochipoyo loop wrapper.
```

Only after that map is verified should implementation continue.

## Success definition for the final project

The final project is successful when:

```text
1. The BUY and SELL strategy conditions are clearly implemented and testable.
2. Their candidate outputs are reproducible.
3. They are routed through a multi-strategy selector.
4. They produce Mochipoyo-compatible payloads.
5. They can run in an independent demo dry-run loop.
6. The sender can validate payloads without --send.
7. Registry-aware policy can block duplicate strategy exposure.
8. Notifications or dry-run send outputs are stable.
9. Existing Mochipoyo production behavior remains unchanged unless explicitly enabled.
10. Only after explicit approval, guarded demo-send and lifecycle registry write are introduced.
```

## Do not lose sight of this

The center of the project is not the BAT files.

The center of the project is:

```text
High-quality GOLD BUY/SELL signals
→ safely integrated into Mochipoyo flow
```

The BAT files, sender hooks, registry previews, and policy checks exist only to make that integration safe and reproducible.
