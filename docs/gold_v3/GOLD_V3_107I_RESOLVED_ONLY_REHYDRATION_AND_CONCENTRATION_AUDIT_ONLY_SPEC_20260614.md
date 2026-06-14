# GOLD V3 Stage107I Spec — RESOLVED_ONLY_REHYDRATION_AND_CONCENTRATION_AUDIT_ONLY

Created JST: `2026-06-14`

Stage:

```text
GOLD_V3_107I_RESOLVED_ONLY_REHYDRATION_AND_CONCENTRATION_AUDIT_ONLY
```

## Purpose

Stage107H produced multiple primary 65% OOS score gates:

```text
primary_65_gate_count: 8
review_63_gate_count: 6
small_65_gate_count: 16
```

However, the summary-best row was a small 22-trade, single-day-looking pocket. A practical 63-trade row exists in the frontier:

```text
OOS trades: 63
OOS WR: 82.54%
OOS PF: 6.78
OOS density: 3.5/day
```

Stage107I verifies the Stage107H score gate by replaying it from entry-time features and train-derived bin scores, then checks concentration risk.

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

```text
FX_OUTPUTS/gold_v3/107hc/gold_v3_107h_score_frontier.csv
FX_OUTPUTS/gold_v3/107hc/gold_v3_107h_feature_bin_scores.csv
FX_OUTPUTS/gold_v3/107guc/gold_v3_107gu_selected_candidate_keys.csv
```

Exact candidate ledgers and OHLC files are used for rehydration. No broad scans.

## Method

1. Load 107H score frontier and train-derived feature bins.
2. Prefer primary_65_gate rows over summary-best rows.
3. Rebuild entry-time features from exact OHLC files.
4. Re-score OOS entries using only train-derived bins.
5. Apply the stored score threshold.
6. Recompute WR/PF/trades/density.
7. Check date concentration:
   - unique trade days
   - max day trade share
   - date span
   - max day win rate
8. Decide whether the score gate is ready for rolling health-gate audit.

## Pass gates

Primary rehydration gate:

```text
WR >= 65%
PF >= 1.50
trades >= 30
```

Concentration gate:

```text
unique_trade_days >= 4
max_day_trade_share <= 0.45
date_span_days >= 7
```

## Outputs

```text
FX_OUTPUTS/gold_v3/107ic/
```

Mandatory paste file:

```text
FX_OUTPUTS/gold_v3/107ic/paste_me.txt
```

## Status

READY:

```text
GOLD_V3_107I_RESOLVED_ONLY_REHYDRATION_AND_CONCENTRATION_READY_AUDIT_ONLY
```

BLOCKED:

```text
GOLD_V3_107I_RESOLVED_ONLY_REHYDRATION_AND_CONCENTRATION_BLOCKED_INPUT_INCOMPLETE_AUDIT_ONLY
```
