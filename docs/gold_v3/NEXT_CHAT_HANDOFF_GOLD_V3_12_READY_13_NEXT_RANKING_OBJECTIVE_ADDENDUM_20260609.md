# NEXT CHAT HANDOFF ADDENDUM - GOLD V3 RANKING OBJECTIVE

Created: 2026-06-09

Repository: `knitanr-a11y/xauusd-signal-lab`

This addendum must be read together with:

```text
docs/gold_v3/NEXT_CHAT_HANDOFF_GOLD_V3_12_READY_13_NEXT_HUMAN_DECISION_TEMPLATE_20260609.md
```

## User clarification after the main handoff

The user clarified the desired candidate-selection objective:

```text
人間が読めなくてもいいので候補を勝率・PFが高そうなものか、勝率は悪いけど件数を絞れば高くなりそうなものを選んでほしいです。日に2トレード以上あれば助かります。
```

Interpretation:

- Human readability is not the top priority.
- Candidate selection should prioritize measurable trading quality.
- Prefer candidates that appear likely to have high win rate and high PF.
- Also keep candidates that do not yet have good win rate, if further narrowing may plausibly improve win rate/PF.
- Trade frequency matters; target at least about 2 trades per day if possible.
- Do not over-optimize by choosing candidates with too few trades.

## Important implication for stage 13

The previously suggested stage 13 name can remain:

```text
GOLD_V3_13_HUMAN_DECISION_TEMPLATE_AUDIT_ONLY
```

But its purpose should be adjusted.

Stage 13 should not only make a human-readable template. It should produce an **audit-only ranking/decision template** that emphasizes:

```text
win-rate proxy
PF proxy
trade-count density / trades per day
narrowing potential
risk flags
same-condition overlap
```

The output can be machine-oriented. It does not need to be beautiful for manual reading.

## Recommended stage 13 objective

Create stage 13 as:

```text
GOLD_V3_13_RANKING_DECISION_TEMPLATE_AUDIT_ONLY
```

Acceptable filename family:

```text
gold_v3_13_ranking_decision_template_audit_only.py
GOLD_V3_13_RANKING_DECISION_TEMPLATE_AUDIT_ONLY.bat
GOLD_V3_13_RANKING_DECISION_TEMPLATE_AUDIT_ONLY_SPEC_20260609.md
```

If retaining the prior name for continuity, explicitly state in the spec that it is a ranking-oriented human decision template.

## Inputs for stage 13

Use stage 12 outputs:

```text
Files/FX_OUTPUTS/gold_v3/12_deployability_review_packet_audit_only/gold_v3_12_summary.json
Files/FX_OUTPUTS/gold_v3/12_deployability_review_packet_audit_only/gold_v3_12_deployability_review_packet.csv
Files/FX_OUTPUTS/gold_v3/12_deployability_review_packet_audit_only/gold_v3_12_deferred_candidate_diagnostics.csv
```

Do not use GOLD V2 selected/final/source/arbitration artifacts as live SOT.

## Ranking logic guidance

Stage 13 should not pretend to know true final win rate or PF unless those values are directly available. If exact win rate/PF are not available at this stage, create proxy fields and label them clearly.

Suggested fields:

```text
candidate_group_id
profile_id
direction
feature_column
rule_expression_preview
readiness_label
risk_flags
folds
positive_test_folds
positive_test_fold_rate
test_avg_result_mean
test_avg_result_min
test_avg_result_max
test_lift_mean
test_sum_result_total
test_rows_total
estimated_trade_days
estimated_trades_per_day
frequency_bucket
pf_winrate_priority_score
narrowing_potential_score
recommended_review_bucket
human_decision
allowed_decisions
human_note
```

### Trades per day estimate

If exact date span is not available in stage 12 rows, estimate using the known GOLD V3 source period only as a clearly labeled approximation.

Prefer exact calculation in later replay stages.

Suggested target:

```text
estimated_trades_per_day >= 2.0
```

But do not reject otherwise promising candidates solely because this proxy is uncertain.

### Priority buckets

Suggested review buckets:

```text
PRIORITY_A_HIGH_QUALITY_AND_FREQUENCY
PRIORITY_B_HIGH_QUALITY_LOW_FREQUENCY_OR_RISK
PRIORITY_C_NARROWING_POTENTIAL
DEFER_LOW_PRIORITY
DEFER_RAW_PRICE_LEVEL_RISK
DEFER_BUCKET_UNSTABLE
```

### Scoring direction

Higher score should prefer:

- positive_test_fold_rate close to 1.0
- higher test_avg_result_mean
- higher test_lift_mean
- higher test_sum_result_total
- enough test_rows_total / estimated_trades_per_day
- no negative fold risk
- no absolute price level risk

Lower score / narrowing potential should flag:

- negative test fold exists but average/lift still strong
- bucket instability but top score is strong
- broad condition that may need a second filter

## Specific interpretation of the 8 stage 12 packet rows

The 8 rows are rule candidates, not trade points.

The five `h1_atr56 >= 9.95812` rows are the same condition family with different TP/SL profiles. They should be grouped before any selection.

Group candidates:

```text
GROUP_H1_ATR56_HIGH_VOL:
  condition = h1_atr56 >= 9.95812
  profiles = TP100_SL40_H96, TP80_SL30_H64, TP50_SL20_H48, TP30_SL10_H32, TP20_SL10_H28

GROUP_M15_ATR28_MID_VOL_RANGE:
  condition = 3.59086 <= m15_atr28 <= 4.29321
  profiles = TP80_SL30_H64

GROUP_H4_RET4_MOMENTUM:
  condition = h4_ret4 >= 0.00751699
  profiles = TP150_SL60_H128

GROUP_H1_RET16_MOMENTUM_NEG_FOLD:
  condition = h1_ret16 >= 0.00707975
  profiles = TP50_SL20_H48
  risk = has_negative_test_fold
```

## Likely initial ranking hypothesis, not final approval

Based only on stage 12 packet metrics:

1. `GROUP_M15_ATR28_MID_VOL_RANGE` may be strong because positive fold rate is 1.0, average result is high, and it is not just a high-volatility one-sided condition.
2. `GROUP_H4_RET4_MOMENTUM` may be strong because positive fold rate is 1.0, risk flags are none, and average result is high.
3. `GROUP_H1_ATR56_HIGH_VOL` may have frequency and consistency, but it carries absolute volatility regime risk and multiple TP/SL profiles share the same entry condition. It should be compared by exit profile, not counted as five independent entry ideas.
4. `GROUP_H1_RET16_MOMENTUM_NEG_FOLD` may be a narrowing-potential candidate because positive fold rate is 0.9 and average result is positive, but it has negative fold risk.

This is not an approval decision.

## What stage 13 must not do

- Do not approve candidates.
- Do not finalize thresholds.
- Do not run replay.
- Do not generate trades/signals.
- Do not train models.
- Do not create ZIP output.
- Do not notify Discord.
- Do not place MT5 orders.
- Do not call AI API.
- Do not enable live hooks/evaluators.

## Next chat prompt addendum

Add this to the next chat prompt after the main handoff prompt:

```text
Additional user objective:
Human readability is not important. Please prioritize candidate ranking by likely high win rate / high PF, or candidates where win rate may improve by further narrowing. Trade frequency matters; about 2 trades/day or more would be helpful. Stage 13 should therefore be a ranking-oriented audit-only decision template, not just a pretty human-readable template. Do not auto-approve, finalize, replay, train, or generate signals.
```
