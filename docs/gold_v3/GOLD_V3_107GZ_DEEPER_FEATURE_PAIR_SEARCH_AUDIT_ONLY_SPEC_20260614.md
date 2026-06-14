# GOLD V3 Stage107GZ Spec — DEEPER_FEATURE_PAIR_SEARCH_AUDIT_ONLY

Created JST: `2026-06-14`

Stage:

```text
GOLD_V3_107GZ_DEEPER_FEATURE_PAIR_SEARCH_AUDIT_ONLY
```

## Purpose

Stage107GY completed successfully, but did not reach the requested 65% OOS win-rate gate.

Observed Stage107GY best:

```text
WR 61.46%
PF 2.397
trades 96
density 3.2/day
primary_65_gate_count 0
volume_65_gate_count 0
```

The result is close enough to justify targeted deeper search, but broad all-combination search is not justified.

107GZ therefore focuses only on the best 107GY frontier region and tests two-condition live-knowable feature pairs.

Examples:

```text
h4_up + m15_rsi14_le45
h1_up + m15_dist_atr_lowq
m15_close_gt_ema20 + h4_dist_atr_highq
```

## Guardrails

GOLD V3 remains audit-only.

Do not read/use/reference/fallback to GOLD V2, old GOLD, DISC8, or Stage41 as trading sources.

Do not mutate source CSVs, CSV contract, candidate pool, Stage45 runtime behavior, Stage69 runtime behavior, live evaluator, final signal, Discord, MT5 execution, or AI API.

CSV contract:

```text
open/in-progress candles are not written to CSV
CSV latest row is contractually closed
open/as-of treatment is forbidden
```

Pool policy:

```text
poolから外さない。rolling health gateに判断させる。
```

## Inputs

Use Stage107GY result to narrow the search:

```text
FX_OUTPUTS/gold_v3/107gyc/gold_v3_107gy_stack_frontier.csv
```

Use candidate keys:

```text
FX_OUTPUTS/gold_v3/107guc/gold_v3_107gu_selected_candidate_keys.csv
```

Use exact candidate ledgers and exact OHLC files only. No broad scans.

## Method

1. Load exact prior candidate ledgers.
2. Load exact OHLC CSVs and compute as-of live-knowable M15/H1/H4/D1 features.
3. Read top rows from 107GY frontier.
4. For candidate keys in those rows, generate single feature filters.
5. Select top train-performing single filters.
6. Build pair filters from those single filters.
7. Select train-only high-WR/pF pair filters.
8. Stack selected pair filters and evaluate OOS.
9. Deduplicate same entry time by train score.

## Gates

Primary:

```text
OOS WR >= 65%
OOS PF >= 1.50
OOS trades >= 30
```

Review:

```text
OOS WR >= 63%
OOS PF >= 1.80
OOS trades >= 50
```

## Outputs

```text
FX_OUTPUTS/gold_v3/107gzc/
```

Mandatory paste file:

```text
FX_OUTPUTS/gold_v3/107gzc/paste_me.txt
```

## Status

READY:

```text
GOLD_V3_107GZ_DEEPER_FEATURE_PAIR_SEARCH_READY_AUDIT_ONLY
```

BLOCKED:

```text
GOLD_V3_107GZ_DEEPER_FEATURE_PAIR_SEARCH_BLOCKED_INPUT_INCOMPLETE_AUDIT_ONLY
```
