# GOLD V2 AI tag Phase 2 design

Created: 2026-06-03
Status: Phase 2 design / execution package prepared outside repository

## 1. Purpose

Phase 2 expands the AI tag audit from the 30-row Phase 1 smoke test to the full upper-bound uncapped reference set.

```text
Target: upper_bound_uncapped_lowvol_foldbest full 174 rows
Goal: classify BLOCK / REPRESENTATIVE_ONLY / CAP_1 / CAP_2 / CAP_3 / ALLOW_STACKED_AUDIT_ONLY
Primary question: can AI reduce stacked tail-risk while preserving enough TotalR?
```

## 2. Why Phase 2 is needed

Phase 1 confirmed:

```text
API success: 30/30
latency: acceptable
JSON stability: acceptable
issue: stack_permission collapsed to CAP_2 for all rows
```

Therefore Phase 2 changes the prompt rubric before scaling to 174 rows.

## 3. Prompt change from Phase 1

Phase 1 was too conservative and pushed all rows into CAP_2.

Phase 2 prompt explicitly defines:

```text
CAP_3 = normal maximum when context is acceptable
CAP_2 = moderate crowding or risk
CAP_1 = high risk but not a full veto
REPRESENTATIVE_ONLY = direction may be OK but stacking is unsafe
BLOCK = avoid the trade
```

The model should not treat CAP_2 as the default. CAP_3 is the normal cap unless risk evidence exists.

## 4. Input policy

AI receives only live-like signal-time data.

```text
Do not send selected_profit_r
Do not send win/loss
Do not send exit result
Do not send post-entry price path
Do not send future candles
```

The hidden truth file is used only after tagging.

## 5. Local output package

The Phase 2 files are generated under:

```text
gold_v2_ai_tag_phase2_design_outputs.zip
```

Expected user-side placement:

```text
Files\FX_OUTPUTS\gold_v2_ai_tag_phase2\
```

Main files:

```text
gold_v2_ai_phase2_input_snapshots.csv
  174 live-like prompts. Outcome hidden.

gold_v2_ai_phase2_eval_truth_hidden.csv
  Hidden truth and profit columns. Never send to AI.

gold_v2_ai_tag_schema_v2.json
  Structured JSON output schema.

run_gold_v2_ai_tag_phase2.py
  Runner. Writes progress logs and output CSV.

evaluate_gold_v2_ai_tag_phase2.py
  Evaluates tags and stack permissions.

bat\01_INSTALL_REQUIREMENTS_PHASE2.bat
bat\02_RUN_AI_TAG_PHASE2.bat
bat\03_EVALUATE_AI_TAG_PHASE2.bat
```

## 6. Phase 2 source set

Source file:

```text
gold_v2_low_vol_dedicated_combined_clusters_strict_no_overlap.csv
```

Count:

```text
174 rows
```

Bucket counts:

```text
win: 94
loss: 47
large_win: 18
flat: 11
large_loss_tail: 4
```

Direction counts:

```text
SELL: 118
BUY: 56
```

Regime counts:

```text
MID_MIXED: 71
HIGH_VOL_TREND: 46
LOW_VOL_RANGE: 31
HIGH_VOL_CHOP: 26
```

## 7. Baseline profit models in hidden truth

Phase 2 truth includes these replay columns:

```text
representative_profit_r
cap1_profit_r
cap2_profit_r
cap3_profit_r
uncapped_profit_r
```

Pre-AI baseline summaries:

| profit model | TotalR | PF | win rate | worst cluster |
|---|---:|---:|---:|---:|
| representative / CAP_1 | +74.0R | 2.19 | 64.37% | -1.0R |
| CAP_2 | +136.5R | 2.41 | 59.77% | -2.0R |
| CAP_3 | +174.0R | 2.51 | 64.37% | -3.0R |
| uncapped | +263.0R | 2.99 | 64.37% | -11.0R |

## 8. Evaluation logic after AI run

For each AI result:

```text
BLOCK -> 0R
REPRESENTATIVE_ONLY -> representative_profit_r
CAP_1 -> cap1_profit_r
CAP_2 -> cap2_profit_r
CAP_3 -> cap3_profit_r
ALLOW_STACKED_AUDIT_ONLY -> uncapped_profit_r
```

Then compare:

```text
uncapped baseline
CAP_3 fixed baseline
CAP_2 fixed baseline
representative baseline
AI stack_permission replay
AI BLOCK-only replay
```

## 9. Success criteria

Phase 2 is useful if:

```text
1. stack_permission is distributed, not all CAP_2.
2. AI stack replay reduces worst cluster from -11R materially.
3. TotalR remains competitive vs fixed CAP_2/CAP_3.
4. BLOCK is rare and reserved for severe contexts.
5. risk tags correlate with weaker PF or worse tail risk.
```

## 10. Stop conditions

Do not promote to live/dry-run policy if:

```text
AI returns mostly one stack_permission again.
JSON failure rate is material.
Latency is too high.
AI misses obvious high-confluence tail risk.
AI blocks too many high-profit contexts.
```

## 11. Runtime status

```text
MT5 order_send: disabled
Discord send: disabled
dispatch_ready: false
AI tags are audit-only until replay validates them.
```
