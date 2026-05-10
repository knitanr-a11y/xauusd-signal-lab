# NEXT CHAT HANDOFF - GOLD multi-strategy combined dry-run verify flow

Last updated: 2026-05-10

## Start here next chat

Read these first:

```text
docs/NEXT_CHAT_HANDOFF_GOLD_MULTI_STRATEGY_COMBINED_DRY_RUN_VERIFY.md
docs/NEXT_CHAT_HANDOFF_GOLD_MULTI_STRATEGY_COMBINED_DRY_RUN_VERIFY_BAT_ADDENDUM.md
docs/NEXT_CHAT_HANDOFF_GOLD_MULTI_STRATEGY_SENDER_DRY_RUN_REGISTRY_PREVIEW_CYCLE_ADDENDUM.md
docs/GOLD_MULTI_STRATEGY_FRESH_SENDER_REGISTRY_POLICY_FULL_CYCLE_VALIDATION.md
docs/GOLD_MULTI_STRATEGY_SENDER_DISABLED_BY_DEFAULT_REGISTRY_PREVIEW_HOOK_DESIGN.md
```

Optional background docs:

```text
docs/NEXT_CHAT_HANDOFF_GOLD_MULTI_STRATEGY_DEMO_AUTOTRADE.md
docs/NEXT_CHAT_HANDOFF_GOLD_MULTI_STRATEGY_DEMO_AUTOTRADE_LONGPATH_ADDENDUM.md
docs/GOLD_MULTI_STRATEGY_SENDER_REGISTRY_PREVIEW_FROM_REPORT_VALIDATION.md
docs/GOLD_MULTI_STRATEGY_FRESH_SENDER_DRY_RUN_REGISTRY_PREVIEW_VALIDATION.md
```

## Current project state

We are building GOLD BUY/SELL multi-strategy demo dry-run / guarded demo send flow outside the existing Mochipoyo production flow.

Current strategy slots:

```text
BUY_C_ENV_RR2_72H
  strategy_id=GOLD_C_ENV_H1_REGULAR_BULLISH_M15_BREAK_RR2_12H_BO8_SL_H1_PIVOT_HOLD_72H

SELL_H1H4_BEAR_AB
  strategy_id=GOLD_H1H4_BEAR_M15_LOW_BREAK_AB_CLASSIFIER_FIXED10_RR2_12H
```

The current work is about sender / registry / policy integration safety, not strategy signal discovery.

## Important safety boundary

Do not modify yet:

```text
production position_registry.csv
existing Mochipoyo ledgers
existing trigger-state files
scripts/run_mochipoyo_gold_demo_autotrade_forever_aligned.bat
close intent MT5 execution
BTC router/send integration
```

The real sender is still not modified for production registry writes:

```text
scripts/send_mt5_order_from_payload.py
```

The disabled-by-default sender registry preview hook is design-only at this point:

```text
docs/GOLD_MULTI_STRATEGY_SENDER_DISABLED_BY_DEFAULT_REGISTRY_PREVIEW_HOOK_DESIGN.md
```

## Current canonical validation command

The latest canonical validation command is a single BAT:

```cmd
scripts\run_gold_multi_strategy_fresh_sender_registry_policy_full_cycle_dry_run_with_verify.bat
```

This BAT runs:

```text
1. scripts/run_gold_multi_strategy_fresh_sender_registry_policy_full_cycle_dry_run.bat
2. scripts/verify_gold_multi_strategy_fresh_sender_registry_policy_full_cycle_summary.py
```

It replaces the earlier two-step routine validation command for normal use.

The earlier two-step sequence is still useful for debugging:

```cmd
scripts\run_gold_multi_strategy_fresh_sender_registry_policy_full_cycle_dry_run.bat
python scripts\verify_gold_multi_strategy_fresh_sender_registry_policy_full_cycle_summary.py --summary-json data\r\ff\summary.json --out-json data\r\ff\summary_verify.json --out-csv data\r\ff\summary_verify_checks.csv
```

## What the canonical BAT validates

The one-command BAT validates this whole chain:

```text
fresh MT5 tick payload
→ real send_mt5_order_from_payload.py dry-run
→ DRY_RUN_ORDER_CHECK_OK
→ sender registry preview row
→ registry-derived mock position
→ exact reconcile
→ registry-aware policy preview
→ same_strategy BLOCK
→ read-only summary verification
```

Output root:

```text
data/r/ff
```

Key files:

```text
data/r/ff/summary.json
data/r/ff/summary_verify.json
data/r/ff/summary_verify_checks.csv
data/r/ff/f/order_payloads.csv
data/r/ff/c/sender_registry_preview/sender_registry_preview.csv
data/r/ff/mp.csv
data/r/ff/r/position_registry_reconcile_dry_run.csv
data/r/ff/p/registry_policy_preview.csv
```

## Latest observed PASS result

Validated command:

```cmd
scripts\run_gold_multi_strategy_fresh_sender_registry_policy_full_cycle_dry_run_with_verify.bat
```

Observed top-level result:

```text
full-cycle dry-run exit code: 0
verifier exit code: 0
```

Full-cycle summary:

```text
cycle_ok=true
reason=FRESH_SENDER_REGISTRY_POLICY_FULL_CYCLE_PASS
summary_json=data/r/ff/summary.json
```

Verifier summary:

```text
verify_ok=true
reason=SUMMARY_VERIFY_PASS
checks_total=26
checks_failed=0
failed_check_names=[]
```

Observed sender metrics:

```text
rows_in=1
rows_out=1
dry_run_check_ok_rows=1
sent_rows=0
blocked_position_policy_rows=0
error_rows=0
order_send_called_count=0
```

Observed registry / reconcile / policy checks:

```text
registry_preview_rows=1
mock_positions.rows_out=1
reconcile.matched_active_registry_rows=1
reconcile.matched_with_mismatch_rows=0
reconcile.missing_position_rows=0
reconcile.unregistered_position_rows=0
policy_preview.same_strategy_blocked_rows=1
policy_preview.registry_inconsistency_blocked_rows=0
policy_preview.allow_rows=0
policy_preview.blocked_rows=1
```

Verifier safety:

```text
read_only=true
mt5_imported=false
order_check_called=false
order_send_called=false
ledger_mutated=false
registry_mutated=false
trigger_state_mutated=false
```

Decision:

```text
PASS.
```

## Files added in this phase

Wrappers / BATs / verifier:

```text
scripts/run_gold_multi_strategy_sender_dry_run_registry_preview_cycle.py
scripts/build_gold_multi_strategy_fresh_sender_valid_payload_from_mt5_tick.py
scripts/run_gold_multi_strategy_fresh_sender_registry_policy_full_cycle.py
scripts/run_gold_multi_strategy_fresh_sender_registry_policy_full_cycle_dry_run.bat
scripts/verify_gold_multi_strategy_fresh_sender_registry_policy_full_cycle_summary.py
scripts/run_gold_multi_strategy_fresh_sender_registry_policy_full_cycle_dry_run_with_verify.bat
```

Validation / design / handoff docs:

```text
docs/GOLD_MULTI_STRATEGY_FRESH_SENDER_REGISTRY_POLICY_FULL_CYCLE_VALIDATION.md
docs/GOLD_MULTI_STRATEGY_SENDER_DISABLED_BY_DEFAULT_REGISTRY_PREVIEW_HOOK_DESIGN.md
docs/NEXT_CHAT_HANDOFF_GOLD_MULTI_STRATEGY_COMBINED_DRY_RUN_VERIFY_BAT_ADDENDUM.md
docs/NEXT_CHAT_HANDOFF_GOLD_MULTI_STRATEGY_SENDER_DRY_RUN_REGISTRY_PREVIEW_CYCLE_ADDENDUM.md
docs/NEXT_CHAT_HANDOFF_GOLD_MULTI_STRATEGY_COMBINED_DRY_RUN_VERIFY.md
```

## Relevant recent commits

```text
05d3c4d6eb2b6cf789e944072cb44f00775fde8d
  Add dry-run BAT for fresh sender registry policy full cycle

2620a396927fbb15e76700dd2a329c6d8b8b4dd8
  Add verifier for fresh sender registry policy full-cycle summary

0730df19b0d0bec09689c4a4df9545a0113b466f
  Add dry-run BAT with summary verifier

4ee26b7621818073be7fe4d0821972b6109d2833
  Document dry-run with verify BAT PASS

47cd747dc44d91840f7a19c88c8b8d345c853da1
  Add handoff addendum for combined dry-run verify BAT PASS

06a4a562a22117d091ee02d6ada203391e383990
  Add design for disabled-by-default sender registry preview hook
```

## Known issue encountered and current handling

A direct handoff update once failed because an accidental `encoding` argument was sent to the GitHub update_file tool. No repo damage occurred.

Resulting mitigation:

```text
Instead of forcing a large overwrite, the combined BAT PASS was recorded as a separate addendum:
docs/NEXT_CHAT_HANDOFF_GOLD_MULTI_STRATEGY_COMBINED_DRY_RUN_VERIFY_BAT_ADDENDUM.md
```

## Disabled-by-default sender registry preview hook design

Design doc:

```text
docs/GOLD_MULTI_STRATEGY_SENDER_DISABLED_BY_DEFAULT_REGISTRY_PREVIEW_HOOK_DESIGN.md
```

Important status:

```text
send_mt5_order_from_payload.py has not been modified yet.
This is design-only.
```

Proposed future sender flags:

```text
--registry-preview-out-csv <path>
--registry-preview-out-json <path>
--registry-preview-position-status ACTIVE
--registry-preview-position-ticket-start 990001
--registry-preview-order-ticket-start 880001
--registry-preview-deal-ticket-start 770001
--registry-preview-include-dry-run-check-ok
--registry-preview-include-sent
```

Safety rules for future hook:

```text
If no registry preview flags are provided, sender behavior must be unchanged.
The hook must never write production position_registry.csv.
The hook must not mutate existing ledgers or trigger-state files.
The hook must not affect order validation, order_check, or order_send decisions.
Preview export runs only after sender result rows are already determined.
DRY_RUN_ORDER_CHECK_OK rows are eligible for dry-run preview rows.
Blocked/error rows must not create preview rows.
SENT rows may be supported later only with explicit --registry-preview-include-sent.
```

Post-implementation tests required if sender hook is implemented later:

```text
1. no flags regression: no preview files, same sender behavior
2. fresh payload + preview flags: registry_preview_rows=1
3. blocked payload + preview flags: registry_preview_rows=0
4. compare sender-native preview CSV with external builder fields
5. exact reconcile + same_strategy BLOCK using sender-native preview CSV
```

## Recommended next step

Recommended immediate next step in the next chat:

```text
1. Pull latest.
2. Run the canonical combined BAT once:
   scripts\run_gold_multi_strategy_fresh_sender_registry_policy_full_cycle_dry_run_with_verify.bat
3. Confirm PASS.
4. Then decide whether to:
   A. keep wrapper/BAT/verifier-only integration for another round, or
   B. implement disabled-by-default registry preview flags in send_mt5_order_from_payload.py.
```

Do not move to production registry writing yet.

Do not touch existing production Mochipoyo BAT yet.
