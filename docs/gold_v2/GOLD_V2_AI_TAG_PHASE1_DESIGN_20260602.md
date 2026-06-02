# GOLD V2 AI tag Phase 1 design

Created: 2026-06-02
Status: PHASE 1 DESIGN / API NOT EXECUTED IN THIS STEP

## 1. Purpose

This document defines the first live-like AI tag audit for GOLD V2 signals.

The goal is to test whether a short AI tagger can identify risky signal contexts before entry, especially uncapped/stacked high-confluence failure clusters.

This is not a live trading integration.

```text
MT5 order_send: disabled
Discord send: disabled
dispatch_ready: false
AI/API in this step: not executed
```

## 2. Main idea

The AI input must match live conditions:

```text
Use only signal-time fields.
Do not include future path.
Do not include exit result.
Do not include selected_profit_r.
Do not include win/loss.
Do not include post-entry candle movement.
```

The model returns only a compact JSON tag result.

## 3. Phase 1 sample count

Phase 1 uses 30 snapshots from the upper-bound uncapped combined set:

```text
source_universe: upper_bound_uncapped_lowvol_foldbest
sample size: 30
```

Sample buckets:

```text
10 strong/clear losses
10 strong wins
10 edge/danger/boundary contexts
```

The sampling intentionally includes high-confluence and MID_MIXED/LOW_VOL risk contexts, but the AI input file hides outcome and profit.

## 4. Files generated locally

Local output bundle:

```text
gold_v2_ai_tag_phase1_design_outputs.zip
```

Contents:

```text
gold_v2_ai_phase1_input_snapshots.csv
  30 live-like AI input snapshots.
  Contains prompt_text per row.
  Does not contain profit or outcome fields.

gold_v2_ai_phase1_eval_truth_hidden.csv
  Hidden truth/evaluation file.
  Contains selected_profit_r, top_profit_r, stacked/capped profit fields.
  Must not be sent to AI.

gold_v2_ai_tag_schema.json
  Strict JSON schema for AI tag output.

gold_v2_ai_tag_prompt_spec.md
  Prompt and evaluation design.

run_gold_v2_ai_tag_phase1.py
  API runner script. Uses OPENAI_API_KEY from environment.
  Does not send MT5 orders or Discord messages.

evaluate_gold_v2_ai_tag_phase1.py
  Joins AI tags with hidden truth and summarizes tag performance.

gold_v2_ai_phase1_ai_tags_EMPTY_TEMPLATE.csv
  Empty output template for API results.

gold_v2_ai_phase1_prompt_preview_first3.txt
  First 3 prompt previews.

gold_v2_ai_phase1_input_audit.json
  Audit metadata for the generated inputs.
```

## 5. AI input fields

Each AI prompt uses a short snapshot like:

```text
LIVE_LIKE_GOLD_V2_SIGNAL_SNAPSHOT
snapshot_id=...
symbol=XAUUSD
signal_time=...
direction=...
regime=...
candidate_id=...
variant=...
tp_usd=...
sl_usd=...
policy=...
mode=...
same_direction_count=...
opposite_direction_count=...
unique_same_direction_origins=...
unique_same_direction_variants=...
has_opposite_conflict=...
same_direction_score_sum=...
opposite_direction_score_sum=...
features:
atr14=...
tr_mean_32=...
range96=...
range192=...
trend_eff96=...
adx14=...
ret96=...
task=assign live-tradable AI risk tags only; do not infer from future outcome; return JSON only.
```

## 6. AI output schema

The model must return:

```json
{
  "snapshot_id": "GOLDV2_AI_PHASE1_001",
  "decision": "ALLOW",
  "stack_permission": "CAP_3",
  "risk_score": 2,
  "confidence": 0.72,
  "quality_tags": ["CONFLUENCE_STRONG"],
  "risk_tags": ["MID_MIXED_SELL_CAUTION"],
  "block_tags": [],
  "reason_code": "ALLOW_BUT_CAP_STACK",
  "reason_short": "Confluence is strong but stack should be capped."
}
```

Allowed decision values:

```text
ALLOW
BLOCK
REVIEW
```

Allowed stack_permission values:

```text
BLOCK
REPRESENTATIVE_ONLY
CAP_1
CAP_2
CAP_3
ALLOW_STACKED_AUDIT_ONLY
```

Important runtime note:

```text
ALLOW_STACKED_AUDIT_ONLY is not live permission.
For real dry-run/live policy, maximum stack should remain capped unless replay proves otherwise.
```

## 7. Initial tag enums

Quality tags:

```text
CONFLUENCE_STRONG
REGIME_ALIGNED
TREND_CONTINUATION_OK
PULLBACK_CLEAN
LOW_VOL_BRANCH_OK
BALANCED_DIRECTION_CONTEXT
CLEAN_NO_CONFLICT
ENOUGH_ORIGIN_DIVERSITY
```

Risk tags:

```text
MID_MIXED_SELL_CAUTION
OVEREXTENDED_ENTRY
LATE_CHASE
NEAR_RECENT_HIGH
NEAR_RECENT_LOW
LOW_VOL_NOISE
FAKE_CONFLUENCE
OPPOSITE_PRESSURE
RANGE_CENTER_ENTRY
STACK_TOO_DENSE
VOLATILITY_CONTRACTION_RISK
HIGH_CONFLUENCE_CROWDING
TREND_EXHAUSTION_RISK
WIDE_RANGE_AFTER_MOVE
LOW_ORIGIN_DIVERSITY
DIRECTION_REGIME_MISMATCH
```

Block tags:

```text
BLOCK_MID_MIXED_SELL_TAIL
BLOCK_OVEREXTENDED_CHASE
BLOCK_LOW_VOL_NOISE
BLOCK_OPPOSITE_PRESSURE
BLOCK_FAKE_CONFLUENCE
BLOCK_STACK_CROWDING
BLOCK_REGIME_MISMATCH
```

## 8. What Phase 1 tests

Phase 1 does not judge strategy performance. It tests:

```text
1. JSON stability
2. tag distribution
3. latency per snapshot
4. whether tags are too conservative or too permissive
5. whether catastrophic uncapped/high-confluence cases receive risk/cap/block tags
```

## 9. Evaluation after API run

After API tags are generated, join:

```text
gold_v2_ai_phase1_ai_tags.csv
+
gold_v2_ai_phase1_eval_truth_hidden.csv
```

Then summarize:

```text
- decision distribution
- stack_permission distribution
- decision x selected_profit_r
- risk_tag x win rate / PF / total_R
- block_tag x avoided loss_R and missed win_R
- whether the -11R class cluster was blocked or capped
```

## 10. Phase progression

Recommended progression:

```text
Phase 1:
  30 snapshots
  Validate prompt/schema/API stability.

Phase 2:
  Full uncapped upper-bound set, about 174 snapshots.
  Test whether AI can reduce large stacked losses without killing TotalR.

Phase 3:
  Deduplicate across uncapped, fully capped3, representative-only.
  Compare AI tag value across runtime risk models.
```

## 11. Stop conditions

Do not proceed to Phase 2 if any of these happen:

```text
JSON failure rate is material.
Average latency is too high for live loop.
Most results are BLOCK or most results are ALLOW with no useful tag variation.
The model uses outcome-like language despite outcome being hidden.
Tag distribution is nonsensical or unstable.
```

## 12. Runtime timeout policy draft

When eventually used live:

```text
API timeout: 7-8 seconds
API error: BLOCK / NO_TRADE
JSON parse error: BLOCK / NO_TRADE
rate limit: BLOCK / NO_TRADE
```

This keeps the trading engine safe when the API is slow or unavailable.

## 13. Current decision

Proceed with Phase 1 only.

Do not connect to MT5 or Discord.

Do not use AI tags for trading decisions until historical replay shows that the tags improve risk-adjusted performance.
