# NEXT CHAT HANDOFF ADDENDUM - sender dry-run registry preview cycle

Last updated: 2026-05-10

## Read this together with

```text
docs/NEXT_CHAT_HANDOFF_GOLD_MULTI_STRATEGY_DEMO_AUTOTRADE.md
docs/NEXT_CHAT_HANDOFF_GOLD_MULTI_STRATEGY_DEMO_AUTOTRADE_LONGPATH_ADDENDUM.md
docs/GOLD_MULTI_STRATEGY_SENDER_REGISTRY_PREVIEW_FROM_REPORT_VALIDATION.md
```

## Why this addendum exists

After the sender-registry preview validation doc was updated, an additional one-command wrapper validation was completed.

New wrapper:

```text
scripts/run_gold_multi_strategy_sender_dry_run_registry_preview_cycle.py
```

Purpose:

```text
send_mt5_order_from_payload.py dry-run
→ sender report/results
→ sender-adjacent registry preview from report
```

Important safety boundary:

```text
The wrapper never passes --send.
The real sender script remains unchanged.
Production position_registry.csv is not written.
Existing Mochipoyo ledger files are not mutated by helper scripts.
Trigger-state files are not mutated.
Existing Mochipoyo BAT files are not modified.
```

## Implementation update

Initial wrapper behavior stopped when `send_mt5_order_from_payload.py` returned non-zero.

However, the sender returns non-zero when rows are blocked by local validation or position policy even when it still writes valid outputs:

```text
mt5_order_send_report.json
mt5_order_send_results.csv
```

The wrapper was updated so that:

```text
If sender returncode != 0 but report/results exist,
continue to registry-preview evaluation.
```

This allows safe blocked-output validation such as:

```text
BLOCKED_LOCAL_VALIDATION
→ NO_ELIGIBLE_SENDER_ROWS
```

Implementation commit:

```text
16fe4a9216dc432d5afe7c0d297dc5c2ea930618
```

## Validated command

```cmd
python scripts\run_gold_multi_strategy_sender_dry_run_registry_preview_cycle.py --input-csv data\research_results\gold_multi_strategy_mochipoyo_payload_bridge_dry_run_time_exit\order_payloads.csv --order-ledger-csv data\research_results\gold_multi_strategy_mochipoyo_payload_bridge_dry_run_time_exit\dry_run_order_ledger.csv --out-dir data\research_results\gold_multi_strategy_sender_registry_preview\cycle_real_payload_allow_any --symbol GOLD# --max-orders 1 --select-symbol --expected-login 75539039 --require-demo-account --position-policy allow_any_until_max --max-symbol-positions 5 --max-symbol-lot 0.05
```

## Observed result

```text
cycle_ok=true
reason=SENDER_DRY_RUN_BLOCKED_BUT_REGISTRY_PREVIEW_EVALUATED
send_requested=false
sender_outputs_exist=true
```

Sender metrics:

```text
rows_in=1
rows_out=1
dry_run_check_ok_rows=0
sent_rows=0
blocked_position_policy_rows=0
error_rows=1
order_send_called_count=0
```

Registry preview result:

```text
registry_preview_ok=true
registry_preview_reason=NO_ELIGIBLE_SENDER_ROWS
registry_preview_rows=0
```

Step table:

```text
sender_dry_run: ok=false, returncode=1
sender_registry_preview_from_report: ok=true, returncode=0
```

Interpretation:

```text
The real stale payload was still blocked by sender local validation.
The wrapper correctly consumed the generated sender report/results.
The registry-preview builder correctly produced no rows.
The cycle was considered evaluated and safe.
```

Decision:

```text
PASS.
```

## Safety observations

```text
wrapper_passed_send_flag=false
production_registry_mutated=false
trigger_state_mutated=false
existing_sender_modified=false
```

Decision:

```text
PASS.
```

## Current implication

The project now has a one-command, sender-adjacent dry-run registry preview validation path:

```text
scripts/run_gold_multi_strategy_sender_dry_run_registry_preview_cycle.py
```

This is safer than modifying the real sender immediately.

Recommended next step:

```text
Keep using this wrapper for one more validation round, preferably with a fresh non-stale payload that reaches DRY_RUN_ORDER_CHECK_OK naturally from the real sender.
```

Do not modify yet:

```text
production position_registry.csv
scripts/run_mochipoyo_gold_demo_autotrade_forever_aligned.bat
existing Mochipoyo ledgers
existing trigger-state files
close intent MT5 execution
BTC router/send integration
```
