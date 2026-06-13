# GOLD V3 Stage107GL Spec — NEW_LONG_SHORT_VECTOR_FAMILY_EXPANSION_AUDIT_ONLY

Created JST: `2026-06-13`

Stage:

```text
GOLD_V3_107GL_NEW_LONG_SHORT_VECTOR_FAMILY_EXPANSION_AUDIT_ONLY
```

## Purpose

Stage107GK confirmed that both LONG and SHORT need additional independent vector families:

```text
LONG needs_new_vector: true
SHORT needs_new_vector: true
BOTH recommendation: NEXT_STAGE_SHOULD_GENERATE_NEW_LONG_AND_SHORT_VECTOR_FAMILIES_NOT_ONLY_RETUNE_GATES
```

The weak points were:

```text
TRAIN_2025H1_TEST_2025H2 SHORT: PF 1.25 / WR 40.0%
2026 short splits: low trade count / weak PF in 2026_03_plus
LONG short-period splits: good PF but too few trades
```

Stage107GL generates and evaluates new LONG/SHORT vector families from live-knowable OHLC features.

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

## Runtime estimate

Expected runtime:

```text
中: 10〜45分程度
1時間を超えたら停止して報告
```

This stage reads OHLC CSVs and evaluates new vector candidates. It is heavier than 107GK/107GI, but should be lighter than 107GF initial exhaustive walk-forward.

## Inputs

Required exact input directory:

```text
FX_INPUTS/gold_v3/107g/
```

The script checks exact known filenames only:

```text
goldsharp_m15.csv
goldsharp_m5.csv
goldsharp_h1.csv
goldsharp_h4.csv
gold#_m15.csv
gold#_m5.csv
gold#_h1.csv
gold#_h4.csv
```

At minimum, M15, M5, H1 and H4 must be available from either `goldsharp_*` or `gold#_*` files.

## New vector families

LONG examples:

```text
L_BREAKOUT_TREND
L_BREAKOUT_SESSION
L_PULLBACK_RECLAIM
L_EMA_STACK_RECLAIM
L_OVERSOLD_TREND_REVERT
L_VOL_EXPANSION_UP
L_COUNTER_SQUEEZE_UP
```

SHORT examples:

```text
S_BREAKDOWN_TREND
S_BREAKDOWN_SESSION
S_PULLBACK_REJECT
S_EMA_STACK_REJECT
S_OVERBOUGHT_TREND_REVERT
S_VOL_EXPANSION_DOWN
S_COUNTER_SQUEEZE_DOWN
```

These are not trading approvals. They are candidate vector families for audit-only comparison.

## TP/SL profiles

Dynamic TP/SL keeps the user clarification:

```text
TP = max(5.0, m15_atr28 * multiplier)
SL = TP / RR
No 5 USD floor is applied to SL.
```

Fast-mode profiles:

```text
TPmax5_ATR0.5_RR1.5_H64
TPmax5_ATR0.75_RR1.5_H64
TPmax5_ATR1.0_RR2.0_H64
TPmax5_ATR1.25_RR2.5_H64
```

Fixed reference profile:

```text
TP10_SL5_RR2_H64
```

M5 judgment uses SL priority if TP and SL touch in the same M5 bar.

## Outputs

Runtime output directory:

```text
FX_OUTPUTS/gold_v3/107glc/
```

Mandatory continuation file:

```text
FX_OUTPUTS/gold_v3/107glc/paste_me.txt
```

Detailed outputs:

```text
gold_v3_107gl_new_vector_candidate_summary.csv
gold_v3_107gl_new_vector_monthly_summary.csv
gold_v3_107gl_new_vector_split_summary.csv
gold_v3_107gl_top_new_vector_trade_ledger.csv
gold_v3_107gl_top_long_short_candidates.csv
gold_v3_107gl_vector_family_recommendations.csv
gold_v3_107gl_quality_gate_matrix.csv
gold_v3_107gl_limitations.csv
gold_v3_107gl_blocker_matrix.csv
gold_v3_107gl_validation_matrix.csv
gold_v3_107gl_summary.json
GOLD_V3_107GL_NEW_LONG_SHORT_VECTOR_FAMILY_EXPANSION_AUDIT_ONLY_REPORT.md
paste_me.txt
```

## Quality gates

Stage107GL is promising if:

```text
At least one LONG vector has trades >= 80, PF >= 1.8, WR >= 0.55.
At least one SHORT vector has trades >= 80, PF >= 1.8, WR >= 0.55.
At least one anchored split has PF >= 1.8 and WR >= 0.55 for each side, where sample size is not trivial.
```

## Status

READY:

```text
GOLD_V3_107GL_NEW_LONG_SHORT_VECTOR_FAMILY_EXPANSION_READY_AUDIT_ONLY
```

BLOCKED:

```text
GOLD_V3_107GL_NEW_LONG_SHORT_VECTOR_FAMILY_EXPANSION_BLOCKED_INPUT_INCOMPLETE_AUDIT_ONLY
```
