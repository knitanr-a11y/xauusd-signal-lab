# GOLD V3 Stage107R4 Spec — RESOLVED_LEDGER_SOURCE_CONTRACT_BUILDER_AUDIT_ONLY

Created JST: `2026-06-14`

Stage:

```text
GOLD_V3_107R4_RESOLVED_LEDGER_SOURCE_CONTRACT_BUILDER_AUDIT_ONLY
```

## Why this stage exists

Stage107R3 exhausted safe join rescue:

```text
strict_join_pass_count: 0
resolved_rows: 0
decision: EXIT_DT_ALIAS_SYNTHETIC_KEY_RECONSTRUCTION_BLOCKED_NEED_RESOLVED_SOURCE_LEDGER
```

This confirms that the current 107Q best-family ledger cannot be made strict-resolved by joining existing output CSVs.

The next safe step is to generate a formal resolved ledger source contract and locate the current GOLD V3 outcome-resolution code path that should emit it.

## Purpose

Stage107R4 is a contract-builder and source-path locator. It does not approximate TP/SL replay.

It must:

1. Read the 107R3 contract requirement.
2. Read the 107Q best-family ledger header.
3. Search only current GOLD V3 runtime scripts for likely outcome-resolution code paths.
4. Produce an implementation contract for a resolved source ledger.
5. Produce a patch plan, not a live change.

## Required resolved ledger contract

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

Recommended additional fields:

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

## Critical correctness rule

The resolved ledger must be produced by the same TP/SL outcome-resolution process that produced `result_usd`.

Do not manually approximate `exit_dt` from OHLC in this stage.

Do not use a new hand-written TP/SL resolver unless a later stage proves parity against the existing audited result_usd ledger.

## Inputs

Required:

```text
FX_OUTPUTS/gold_v3/107r3c/gold_v3_107r3_resolved_ledger_contract_requirement.csv
FX_OUTPUTS/gold_v3/107qc/gold_v3_107q_best_family_trade_ledger.csv
```

Optional:

```text
FX_OUTPUTS/gold_v3/107r3c/gold_v3_107r3_synthetic_key_join_attempts.csv
```

## Script source search scope

Search only repo paths matching:

```text
scripts/gold_v3_runtime/*.py
scripts/gold_v3_runtime/**/*.py
```

Do not inspect GOLD V2, old GOLD, DISC8, or Stage41 as trading source.

## Outputs

```text
FX_OUTPUTS/gold_v3/107r4c/gold_v3_107r4_contract_gap_matrix.csv
FX_OUTPUTS/gold_v3/107r4c/gold_v3_107r4_runtime_source_locator.csv
FX_OUTPUTS/gold_v3/107r4c/gold_v3_107r4_resolved_ledger_contract.md
FX_OUTPUTS/gold_v3/107r4c/gold_v3_107r4_patch_plan.csv
FX_OUTPUTS/gold_v3/107r4c/gold_v3_107r4_blocker_matrix.csv
FX_OUTPUTS/gold_v3/107r4c/gold_v3_107r4_validation_matrix.csv
FX_OUTPUTS/gold_v3/107r4c/gold_v3_107r4_summary.json
FX_OUTPUTS/gold_v3/107r4c/GOLD_V3_107R4_RESOLVED_LEDGER_SOURCE_CONTRACT_BUILDER_AUDIT_ONLY_REPORT.md
FX_OUTPUTS/gold_v3/107r4c/paste_me.txt
```

## Decisions

Allowed decisions:

```text
RESOLVED_LEDGER_SOURCE_CONTRACT_READY_FOR_PATCH_IMPLEMENTATION
RESOLVED_LEDGER_SOURCE_CONTRACT_BLOCKED_RESOLVER_SOURCE_NOT_LOCATED
RESOLVED_LEDGER_SOURCE_CONTRACT_BLOCKED_INPUT_INCOMPLETE
```

## Next stage

If 107R4 locates a likely resolver source, next stage should implement a minimal audit-only patch that adds resolved ledger output with the contract above.

Suggested next stage:

```text
107R5_RESOLVED_LEDGER_OUTPUT_PATCH_AUDIT_ONLY
```

107R5 must still avoid live changes and must not change candidate selection or scoring.

## Guardrails

GOLD V3 remains audit-only.

Do not mutate source CSVs, CSV contract, candidate pool, Stage45 runtime, Stage69 runtime, live evaluator, live hook, final signal, Discord, MT5, or AI API.

Do not read/use/reference/fallback to GOLD V2, old GOLD, DISC8, or Stage41 feature-only snapshot as a trading source.
