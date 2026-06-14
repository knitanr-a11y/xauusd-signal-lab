# GOLD V3 Stage107H Spec — TRAIN_ONLY_FEATURE_SCORE_GATE_AUDIT_ONLY

Created JST: `2026-06-14`

Stage:

```text
GOLD_V3_107H_TRAIN_ONLY_FEATURE_SCORE_GATE_AUDIT_ONLY
```

## Purpose

Stage107GY reached a useful but insufficient plateau:

```text
WR 61.46%
PF 2.397
trades 96
density 3.2/day
```

Stage107GZ attempted two-condition feature pairs, but worsened:

```text
WR 60.0%
PF 2.45
trades 15
density 0.75/day
primary_65_gate_count 0
```

Therefore, the next test should not be another hard AND-filter. Stage107H instead creates a train-only feature score gate:

```text
Each entry receives points from multiple live-knowable feature bins.
Only entries with high combined score pass.
```

This is a deterministic audit-only meta-gate, not an AI API call and not live trading.

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

## Live-knowable feature policy

Allowed:

```text
entry-time M15/H1/H4/D1 ATR, RSI, EMA direction, EMA distance, range state
train-only feature-bin statistics
```

Forbidden:

```text
future TP/SL
exit result as a live feature
future high/low/close
future ATR/H4/D1 state
unresolved future horizon
open/incomplete candles
```

## Method

1. Load exact candidate ledgers.
2. Load exact OHLC files.
3. Compute closed-row as-of features at entry time.
4. Use 107GY best frontier region as the candidate universe.
5. On train only, build feature-bin win-rate/PF scores.
6. Score train and OOS entries using only entry-time features and train-derived bin scores.
7. Evaluate score thresholds on OOS.
8. Select the best stack by OOS quality.

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
FX_OUTPUTS/gold_v3/107hc/
```

Mandatory paste file:

```text
FX_OUTPUTS/gold_v3/107hc/paste_me.txt
```

## Status

READY:

```text
GOLD_V3_107H_TRAIN_ONLY_FEATURE_SCORE_GATE_READY_AUDIT_ONLY
```

BLOCKED:

```text
GOLD_V3_107H_TRAIN_ONLY_FEATURE_SCORE_GATE_BLOCKED_INPUT_INCOMPLETE_AUDIT_ONLY
```
