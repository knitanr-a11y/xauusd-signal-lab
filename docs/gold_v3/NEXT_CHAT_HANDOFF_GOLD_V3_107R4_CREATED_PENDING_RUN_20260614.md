# NEXT CHAT HANDOFF — GOLD V3 107R4 created / pending local run

Created JST: `2026-06-14`

Repository:

```text
knitanr-a11y/xauusd-signal-lab
```

Current status:

```text
GOLD_V3_107R4_RESOLVED_LEDGER_SOURCE_CONTRACT_BUILDER_CREATED_PENDING_LOCAL_RUN_AUDIT_ONLY
```

## Current context

107R3 completed and blocked:

```text
status: GOLD_V3_107R3_EXIT_DT_ALIAS_SYNTHETIC_KEY_RECONSTRUCTION_BLOCKED_AUDIT_ONLY
decision: EXIT_DT_ALIAS_SYNTHETIC_KEY_RECONSTRUCTION_BLOCKED_NEED_RESOLVED_SOURCE_LEDGER
best_family_rows: 5571
source_detail_rows: 19
alias_map_rows: 209
synthetic_join_attempt_rows: 154
strict_join_pass_count: 0
resolved_rows: 0
```

This means existing CSV join rescue is exhausted. Do not keep trying arbitrary joins.

## What 107R4 does

107R4 is a contract-builder and runtime source locator. It does not approximate TP/SL replay.

It reads:

```text
FX_OUTPUTS/gold_v3/107r3c/gold_v3_107r3_resolved_ledger_contract_requirement.csv
FX_OUTPUTS/gold_v3/107qc/gold_v3_107q_best_family_trade_ledger.csv
```

It writes:

```text
gold_v3_107r4_contract_gap_matrix.csv
gold_v3_107r4_runtime_source_locator.csv
gold_v3_107r4_resolved_ledger_contract.md
gold_v3_107r4_patch_plan.csv
```

It searches only:

```text
scripts/gold_v3_runtime/**/*.py
```

for likely current GOLD V3 outcome-resolution code paths using terms such as:

```text
result_usd, exit_dt, tp, sl, horizon, outcome, ledger
```

## Required contract for next implementation

The resolved source ledger must include:

```text
entry_dt
exit_dt
side
result_usd
profile_id
candidate_key or global_candidate_key
family
condition
source_name
```

Recommended:

```text
entry_price
exit_price
exit_reason
tp_usd
sl_usd
horizon_bars
result_source
resolver_script
csv_contract
```

The resolved ledger must be emitted by the same TP/SL outcome-resolution process that produced `result_usd`.

Do not manually approximate `exit_dt` from OHLC in 107R4.

## Files created

```text
docs/gold_v3/GOLD_V3_107R4_RESOLVED_LEDGER_SOURCE_CONTRACT_BUILDER_AUDIT_ONLY_SPEC_20260614.md
scripts/gold_v3_runtime/gold_v3_107r4_resolved_ledger_source_contract_builder_audit.py
scripts/gold_v3_runtime/bat/run_gold_v3_107r4_resolved_ledger_source_contract_builder.bat
docs/gold_v3/NEXT_CHAT_HANDOFF_GOLD_V3_107R4_CREATED_PENDING_RUN_20260614.md
```

## Run next

Run:

```text
scripts/gold_v3_runtime/bat/run_gold_v3_107r4_resolved_ledger_source_contract_builder.bat
```

Then paste:

```text
FX_OUTPUTS/gold_v3/107r4c/paste_me.txt
```

## If 107R4 is ready

Next stage should be:

```text
107R5_RESOLVED_LEDGER_OUTPUT_PATCH_AUDIT_ONLY
```

107R5 should add an audit-only output to the identified resolver path without changing candidate selection, scoring, runtime/live hooks, MT5, Discord, or AI API.

## Hard guardrails

GOLD V3 remains audit-only.

Do not read/use/reference/fallback to:

- GOLD V2
- old GOLD
- DISC8
- Stage41 feature-only snapshot as a trading source

Do not mutate:

- source CSVs
- CSV contract
- candidate pool
- Stage45 runtime
- Stage69 runtime
- live evaluator
- live hook
- final signal
- Discord
- MT5 execution
- AI API

CSV contract:

```text
open/in-progress candles are not written to CSV
CSV latest row is contractually closed
csv_open_bar_exclusion_required=false
```

Pool policy:

```text
poolから外さない。rolling health gateに判断させる。
```
