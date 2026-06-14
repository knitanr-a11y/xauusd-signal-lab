# GOLD V3 Stage107R6 Spec — PARITY_VERIFIED_RESOLVED_CONTRACT_BUILDER_AUDIT_ONLY

Created JST: `2026-06-14`

Stage:

```text
GOLD_V3_107R6_PARITY_VERIFIED_RESOLVED_CONTRACT_BUILDER_AUDIT_ONLY
```

## Why this stage exists

107R5 identified active patch targets:

```text
best_family_rows: 5571
active_patch_target_rows: 4
needs_patch_count: 4
missing_producer_count: 0
```

The dominant source is:

```text
broad_candidate_107GB: 5165 / 5571 rows
```

Manual source review showed 107GB/107GN already contain the TP/SL outcome process that created `result_usd`, but those functions only output numeric result and not `exit_dt`.

Examples:

- `gold_v3_107gb_dual_edge_walkforward_density_and_conflict_audit.py` has `one()` returning only result, and `eval_cond()` writes ledger rows without `exit_dt`.
- `gold_v3_107gn_atomic_vector_discovery_v2_audit.py` has `result_idx()` returning only result, and `eval_seed()` writes ledger rows without `exit_dt`.

107R6 adds a separate audit-only resolved contract builder without changing the producer scripts or live paths.

## Purpose

107R6 builds resolved contract ledgers for the active 107Q best-family sources by replaying the same TP/SL profile semantics and proving parity against the existing `result_usd`.

It must:

1. Load current input ledgers from 107GO/GN/GD/GB.
2. Load exact M15/M5 OHLC.
3. Recompute TP/SL result and exit time for each row.
4. Compare recomputed result to existing `result_usd`.
5. Accept rows only when parity passes within tolerance.
6. Produce a combined resolved input ledger.
7. Join it back to 107Q best-family ledger.
8. Only if coverage is 100%, mark ready for 107S resolved-only health gate replay.

## Not a live patch

107R6 does **not** mutate producer scripts.

It writes new audit-only outputs under:

```text
FX_OUTPUTS/gold_v3/107r6c
```

## Required input ledgers

```text
107goc/gold_v3_107go_portfolio_ledger.csv
107gnc/gold_v3_107gn_top_candidate_trade_ledger.csv
107gdc/gold_v3_107gd_diversified_portfolio_ledger.csv
107gbc/gold_v3_107gb_top_candidate_trade_ledger.csv
107qc/gold_v3_107q_best_family_trade_ledger.csv
```

## Required OHLC

```text
goldsharp_m15.csv or gold#_m15.csv
goldsharp_m5.csv or gold#_m5.csv
```

## Result parity rule

For a row to be accepted:

```text
abs(recomputed_result_usd - result_usd) <= 1e-8
exit_dt >= entry_dt
exit_dt is non-null
```

Timeout rows with result `0.0` are resolved at the horizon-end M5 candle if enough M5 bars exist.

## Outputs

```text
FX_OUTPUTS/gold_v3/107r6c/gold_v3_107r6_resolved_input_ledgers_combined.csv
FX_OUTPUTS/gold_v3/107r6c/gold_v3_107r6_resolved_107q_best_family_ledger.csv
FX_OUTPUTS/gold_v3/107r6c/gold_v3_107r6_source_parity_matrix.csv
FX_OUTPUTS/gold_v3/107r6c/gold_v3_107r6_join_coverage_matrix.csv
FX_OUTPUTS/gold_v3/107r6c/gold_v3_107r6_blocker_matrix.csv
FX_OUTPUTS/gold_v3/107r6c/gold_v3_107r6_validation_matrix.csv
FX_OUTPUTS/gold_v3/107r6c/gold_v3_107r6_summary.json
FX_OUTPUTS/gold_v3/107r6c/GOLD_V3_107R6_PARITY_VERIFIED_RESOLVED_CONTRACT_BUILDER_AUDIT_ONLY_REPORT.md
FX_OUTPUTS/gold_v3/107r6c/paste_me.txt
```

## Decisions

Allowed decisions:

```text
PARITY_VERIFIED_RESOLVED_CONTRACT_READY_FOR_107S
PARITY_VERIFIED_RESOLVED_CONTRACT_PARTIAL_NEED_PRODUCER_PATCH
PARITY_VERIFIED_RESOLVED_CONTRACT_BLOCKED_INPUT_INCOMPLETE
```

## Guardrails

GOLD V3 remains audit-only.

Do not mutate source CSVs, CSV contract, candidate pool, Stage45 runtime, Stage69 runtime, live evaluator, live hook, final signal, Discord, MT5, or AI API.

Do not read/use/reference/fallback to GOLD V2, old GOLD, DISC8, or Stage41 feature-only snapshot as a trading source.
