# GOLD multi-strategy registry policy preview long-path validation

Last updated: 2026-05-10

## Purpose

This document records validation for the Windows-long-path hardened registry policy preview wrapper.

The wrapper keeps the already validated policy logic unchanged and only hardens file IO for deep MT5/MQL5/Files paths.

Validated script:

```text
scripts/run_gold_multi_strategy_registry_policy_preview_longpath.py
```

Base logic reused from:

```text
scripts/run_gold_multi_strategy_registry_policy_preview.py
```

## Safety boundary

This remains preview-only.

```text
No MetaTrader5 import.
No mt5.order_check.
No mt5.order_send.
No registry mutation.
No ledger mutation.
No trigger-state mutation.
```

## Implementation commit

```text
bad367d69dbe5cf21cf85050f0068a475f998042
```

## Validation command

```cmd
python scripts\run_gold_multi_strategy_registry_policy_preview_longpath.py --input-csv data\research_results\gold_multi_strategy_controlled_send_report_with_tickets\payload_bridge_send_controlled\order_payloads.csv --positions-csv data\research_results\gold_multi_strategy_position_policy_preflight\mock_positions_same_strategy_buy_c.csv --registry-csv data\research_results\gold_multi_strategy_send_report_registry_preview_controlled_payload_with_tickets\position_registry_from_send_report_preview.csv --order-ledger-csv data\research_results\gold_multi_strategy_mochipoyo_payload_bridge_dry_run\dry_run_order_ledger.csv --out-dir data\research_results\gold_multi_strategy_send_report_registry_preview_controlled_payload_with_tickets --output-csv data\research_results\gold_multi_strategy_send_report_registry_preview_controlled_payload_with_tickets\registry_policy_preview_from_send_report_longpath.csv --output-json data\research_results\gold_multi_strategy_send_report_registry_preview_controlled_payload_with_tickets\registry_policy_preview_from_send_report_longpath.json --reconcile-csv data\research_results\gold_multi_strategy_send_report_registry_preview_controlled_payload_with_tickets\registry_policy_preview_reconcile_from_send_report_longpath.csv --symbol GOLD# --max-orders 1 --max-total-positions 5 --max-lot-per-order 0.02
```

## Observed result

Observed summary:

```text
preview_ok: true
reason: POLICY_PREVIEW_EVALUATED
rows_in: 1
rows_out: 1
allow_rows: 0
blocked_rows: 1
same_strategy_blocked_rows: 1
registry_inconsistency_blocked_rows: 0
opposite_direction_blocked_rows: 0
total_position_cap_blocked_rows: 0
per_order_lot_blocked_rows: 0
duplicate_key_blocked_rows: 0
```

Policy:

```text
policy_name=block_same_strategy_and_opposite_direction
```

Reconcile status counts:

```text
REGISTRY_ACTIVE_MATCHED: 1
```

Decision:

```text
PASS.
```

## Final policy row

Observed row:

```text
requested_strategy_key=BUY_C_ENV_RR2_72H
requested_symbol=GOLD#
requested_direction=BUY
requested_lot=0.01
existing_total_positions=1
existing_symbol_positions=1
existing_symbol_directions=BUY
registry_matched_rows=1
registry_missing_position_rows=0
unregistered_position_rows=0
same_strategy_blocked=true
opposite_direction_blocked=false
total_position_cap_blocked=false
per_order_lot_blocked=false
duplicate_key_blocked=false
registry_inconsistency_blocked=false
final_policy_decision=BLOCK
```

Final policy reason:

```text
same_strategy: ACTIVE matched registry position already exists for strategy=BUY_C_ENV_RR2_72H; tickets=['990001']
```

Decision:

```text
PASS.
```

## Output paths validated

The long-path wrapper successfully wrote outputs under the deeper research result path:

```text
data/research_results/gold_multi_strategy_send_report_registry_preview_controlled_payload_with_tickets/registry_policy_preview_from_send_report_longpath.csv
data/research_results/gold_multi_strategy_send_report_registry_preview_controlled_payload_with_tickets/registry_policy_preview_from_send_report_longpath.json
data/research_results/gold_multi_strategy_send_report_registry_preview_controlled_payload_with_tickets/registry_policy_preview_reconcile_from_send_report_longpath.csv
```

This confirms the logic does not require the short `data/r/ticket_preview` workaround for the standalone policy preview stage.

## Safety output

Observed safety counters:

```text
mt5_imported: false
order_check_called_count: 0
order_send_called_count: 0
registry_mutated: false
ledger_mutated: false
trigger_state_mutated: false
```

Decision:

```text
PASS.
```

## Validation matrix

```text
long-path wrapper imports validated base policy logic: PASS
deep input paths read successfully: PASS
deep output CSV written successfully: PASS
deep output JSON written successfully: PASS
deep reconcile CSV written successfully: PASS
same_strategy BLOCK result preserved: PASS
registry inconsistency remains 0: PASS
read-only safety counters: PASS
```

## Current implication

The following chain is now validated:

```text
controlled send report with tickets
→ registry preview row
→ reconcile
→ registry policy preview
→ same_strategy BLOCK
```

And the standalone policy preview stage can now write to deep MT5/MQL5/Files-derived output paths via:

```text
scripts/run_gold_multi_strategy_registry_policy_preview_longpath.py
```

## Remaining note

The wrapper was added to avoid changing policy logic while hardening IO.

A later cleanup can either:

```text
1. keep this longpath wrapper as the Windows-safe entrypoint, or
2. fold the same long-path IO helpers directly into scripts/run_gold_multi_strategy_registry_policy_preview.py.
```

Do not modify yet:

```text
scripts/send_mt5_order_from_payload.py
scripts/run_mochipoyo_gold_demo_autotrade_forever_aligned.bat
existing Mochipoyo ledgers
existing trigger-state files
```
