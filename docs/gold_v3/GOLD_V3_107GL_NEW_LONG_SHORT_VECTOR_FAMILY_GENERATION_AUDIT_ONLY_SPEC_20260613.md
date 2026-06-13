# GOLD V3 Stage107GL Spec — NEW_LONG_SHORT_VECTOR_FAMILY_GENERATION_AUDIT_ONLY

Created JST: `2026-06-13`

Stage:

```text
GOLD_V3_107GL_NEW_LONG_SHORT_VECTOR_FAMILY_GENERATION_AUDIT_ONLY
```

## Purpose

Stage107GK confirmed that both sides need additional independent vectors:

```text
LONG:  needs_new_vector=true, weak_failed_split_count=2, train_good_test_bad_candidate_count=1
SHORT: needs_new_vector=true, weak_failed_split_count=3, train_good_test_bad_candidate_count=4
BOTH:  NEXT_STAGE_SHOULD_GENERATE_NEW_LONG_AND_SHORT_VECTOR_FAMILIES_NOT_ONLY_RETUNE_GATES
```

Stage107GL creates and evaluates new LONG/SHORT vector families beyond the earlier trend/pullback/session candidates.

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

The latest CSV row is contractually closed; do not exclude it as open/as-of.

Pool policy:

```text
poolから外さない。rolling health gateに判断させる。
```

## Runtime estimate

Expected runtime:

```text
中〜重: 30〜90分程度
1時間半を超えたら停止して報告
```

Reason: Stage107GL evaluates multiple vector families, TP/SL profiles, and cooldowns against M5 outcomes.

## Inputs

Primary OHLC input directory:

```text
FX_INPUTS/gold_v3/107g/
```

Fallback, exact MT5 Files root only:

```text
MQL5/Files/
```

Allowed exact filenames:

```text
gold#_m15.csv / goldsharp_m15.csv
gold#_m5.csv  / goldsharp_m5.csv
gold#_h1.csv  / goldsharp_h1.csv
gold#_h4.csv  / goldsharp_h4.csv
gold#_d1.csv  / goldsharp_d1.csv
```

No broad scan is allowed.

## New vector families

### LONG

```text
LONG_TREND_CONTINUATION
LONG_VOL_EXPANSION_BREAKOUT
LONG_FAILED_BREAKDOWN_RECLAIM
LONG_SELL_EXHAUSTION_REVERSAL
LONG_SESSION_CONTINUATION
LONG_HTF_UP_M15_MOMENTUM
```

### SHORT

```text
SHORT_BEARISH_CONTINUATION
SHORT_VOL_EXPANSION_BREAKDOWN
SHORT_FAILED_BREAKOUT_REJECT
SHORT_BUY_EXHAUSTION_REVERSAL
SHORT_SESSION_SELL_PRESSURE
SHORT_HTF_DOWN_M15_MOMENTUM
```

Each family may produce several named variants using live-knowable filters:

```text
HTF alignment
M15 momentum
ATR/high-vol state
session bucket
range reclaim / failed break
RSI exhaustion
wick/body structure
```

## TP/SL profiles

Stage107GL evaluates both fixed and dynamic TP/SL profiles.

Fixed:

```text
TP5_SL2.5_RR2_H64
TP10_SL5_RR2_H64
TP15_SL7.5_RR2_H64
TP20_SL10_RR2_H64
```

Dynamic:

```text
TPmax5_ATR0.50_RR1.5_H64
TPmax5_ATR0.75_RR2.0_H64
TPmax5_ATR1.00_RR2.0_H64
TPmax5_ATR1.25_RR2.5_H64
```

Dynamic rule:

```text
TP = max(5.0, m15_atr28 * atr_multiplier)
SL = TP / RR
```

Important:

```text
TP has a 5 USD minimum.
SL does not have a 5 USD minimum.
```

## Evaluation

Use M15 entries and M5 outcome evaluation.

```text
entry price: closed M15 close
M5 horizon: 64 M15 bars = 192 M5 bars
SL priority if TP and SL are touched in the same M5 bar
cooldown_bars: 0, 2, 4
```

## Output directory

```text
FX_OUTPUTS/gold_v3/107glc/
```

Mandatory continuation file:

```text
FX_OUTPUTS/gold_v3/107glc/paste_me.txt
```

## Outputs

```text
gold_v3_107gl_input_coverage.csv
gold_v3_107gl_feature_coverage.csv
gold_v3_107gl_vector_candidate_summary.csv
gold_v3_107gl_top_long_vectors.csv
gold_v3_107gl_top_short_vectors.csv
gold_v3_107gl_top_vector_trade_ledger.csv
gold_v3_107gl_side_family_summary.csv
gold_v3_107gl_monthly_summary.csv
gold_v3_107gl_anchored_split_summary.csv
gold_v3_107gl_recommended_next_actions.csv
gold_v3_107gl_blocker_matrix.csv
gold_v3_107gl_validation_matrix.csv
gold_v3_107gl_summary.json
GOLD_V3_107GL_NEW_LONG_SHORT_VECTOR_FAMILY_GENERATION_AUDIT_ONLY_REPORT.md
paste_me.txt
```

## Success indicators

This stage is not live approval. It is promising if:

```text
LONG has at least one new family with >=150 trades, PF>=2.0, WR>=0.55, negative_month_count<=2
SHORT has at least one new family with >=150 trades, PF>=2.0, WR>=0.55, negative_month_count<=2
At least one anchored split remains positive for each side
```

## Status

READY:

```text
GOLD_V3_107GL_NEW_LONG_SHORT_VECTOR_FAMILY_GENERATION_READY_AUDIT_ONLY
```

BLOCKED:

```text
GOLD_V3_107GL_NEW_LONG_SHORT_VECTOR_FAMILY_GENERATION_BLOCKED_INPUT_INCOMPLETE_AUDIT_ONLY
```
