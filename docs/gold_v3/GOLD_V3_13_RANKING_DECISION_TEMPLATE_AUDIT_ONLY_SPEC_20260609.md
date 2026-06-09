# GOLD V3 13 ranking decision template audit-only spec

Created: 2026-06-09

Status: `GOLD_V3_13_RANKING_DECISION_TEMPLATE_SPEC_READY_AUDIT_ONLY`

## Purpose

GOLD V3 13 creates an audit-only ranking/decision template from the GOLD V3 12 deployability review packet.

This stage ranks the 8 stage-12 rule candidates by measurable quality proxies so the next human decision can prioritize candidates that may have high win rate / high PF, or candidates that may improve after further narrowing.

This stage does **not** approve candidates, finalize thresholds, run replay, train models, generate signals, create ZIP output, call AI APIs, enable live hooks/evaluators, notify Discord, or place MT5 orders.

## Required upstream

```text
GOLD_V3_12_DEPLOYABILITY_REVIEW_PACKET_READY_AUDIT_ONLY
```

## Inputs

Stage 13 uses only GOLD V3 12 audit outputs as source-of-truth inputs:

```text
Files/FX_OUTPUTS/gold_v3/12_deployability_review_packet_audit_only/gold_v3_12_summary.json
Files/FX_OUTPUTS/gold_v3/12_deployability_review_packet_audit_only/gold_v3_12_deployability_review_packet.csv
Files/FX_OUTPUTS/gold_v3/12_deployability_review_packet_audit_only/gold_v3_12_deferred_candidate_diagnostics.csv
```

Expected input conditions:

```text
summary.status = GOLD_V3_12_DEPLOYABILITY_REVIEW_PACKET_READY_AUDIT_ONLY
packet rows = 8
packet rows are rule candidates, not individual trade points
```

GOLD V2 artifacts may be referenced only as historical/audit context and are not live source-of-truth.
Old GOLD/DISC8 remains quarantined.

## Output directory

```text
Files/FX_OUTPUTS/gold_v3/13_ranking_decision_template_audit_only/
```

## Outputs

```text
GOLD_V3_13_RANKING_DECISION_TEMPLATE_AUDIT_ONLY_REPORT.md
gold_v3_13_summary.json
gold_v3_13_input_inventory.csv
gold_v3_13_ranking_decision_template.csv
gold_v3_13_candidate_family_group_summary.csv
gold_v3_13_decision_matrix.csv
gold_v3_13_blocker_matrix.csv
```

ZIP output is disabled.

## Candidate family grouping

The 8 packet rows are grouped before review because several rows can share the same entry condition with different TP/SL profiles.

Expected group examples from stage 12:

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

The h1_atr56 rows must not be counted as five independent entry ideas without overlap disclosure.

## Ranking fields

Stage 13 does not claim exact win rate or exact PF unless those columns already exist in the stage-12 packet. If exact values are absent, the script creates clearly labeled proxy fields.

Required template fields include:

```text
rank
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
estimated_trade_days_source
estimated_trades_per_day
frequency_bucket
pf_winrate_priority_score
narrowing_potential_score
recommended_review_bucket
same_condition_overlap
same_condition_overlap_note
ranking_is_proxy_only
human_decision
allowed_decisions
human_note
reviewer
reviewed_at_utc
```

## Ranking logic

Higher `pf_winrate_priority_score` should prefer:

```text
positive_test_fold_rate close to 1.0
higher test_avg_result_mean
higher test_lift_mean
higher test_sum_result_total
enough test_rows_total / estimated_trades_per_day
no negative fold risk
no absolute volatility / absolute price regime risk
```

`narrowing_potential_score` should highlight candidates where a broad or risky rule may still deserve later audit-only narrowing:

```text
negative fold risk with positive average/lift
absolute volatility regime risk
same-condition family overlap
large test_rows_total suggesting room for a second filter
positive average result with imperfect fold stability
```

The script may estimate trades/day using a clearly labeled fallback only when exact date span is not present in stage-12 outputs. This estimate is proxy-only and must be recomputed exactly during a later replay stage.

Target frequency guidance:

```text
estimated_trades_per_day >= 2.0 preferred when possible
```

Do not reject an otherwise strong candidate solely because this estimate is approximate.

## Review buckets

```text
PRIORITY_A_HIGH_QUALITY_AND_FREQUENCY
PRIORITY_B_HIGH_QUALITY_LOW_FREQUENCY_OR_RISK
PRIORITY_C_NARROWING_POTENTIAL
DEFER_LOW_PRIORITY
DEFER_RAW_PRICE_LEVEL_RISK
DEFER_BUCKET_UNSTABLE
```

These buckets are audit priorities only. They are not approvals.

## Human decision fields

Every output candidate row must keep human decision fields empty/pending:

```text
human_decision = PENDING_HUMAN_REVIEW
allowed_decisions = APPROVE_FOR_NEXT_AUDIT_ONLY_REPLAY | REJECT | REQUEST_MORE_AUDIT
human_note = ""
reviewer = ""
reviewed_at_utc = ""
```

`APPROVE_FOR_NEXT_AUDIT_ONLY_REPLAY` is not final candidate approval and not live deployment approval.
`REQUEST_MORE_AUDIT` is not approval.

## Blocker logic

```text
G3-13-001 12 inputs: CLOSED if summary READY, packet exists, deferred diagnostics exists, and packet row count = 8
G3-13-002 ranking template rows: CLOSED if ranking template rows = 8
G3-13-003 family grouping: CLOSED if group summary rows > 0 and h1_atr56 overlap is disclosed when present
G3-13-004 human decision: OPEN_HUMAN_ACTION_REQUIRED
G3-13-005 replay execution: CLOSED_BLOCKED_BY_POLICY
G3-13-006 final approval: CLOSED_BLOCKED_BY_POLICY
G3-13-007 threshold finalization: CLOSED_BLOCKED_BY_POLICY
G3-13-008 model training: CLOSED_BLOCKED_BY_POLICY
G3-13-009 signal/live: CLOSED_BLOCKED_BY_POLICY
G3-13-010 zip output: CLOSED_DISABLED
G3-13-011 external actions: CLOSED
```

## Success conditions

Stage 13 succeeds only if:

```text
all required stage-12 inputs are readable
stage-12 summary status is GOLD_V3_12_DEPLOYABILITY_REVIEW_PACKET_READY_AUDIT_ONLY
stage-12 packet row count is exactly 8
ranking decision template row count is exactly 8
candidate family group summary is written
blocker matrix keeps human decision OPEN_HUMAN_ACTION_REQUIRED
all approval/live/external-action flags remain false
no replay/model/signal/ZIP/AI/Discord/MT5/live artifact is created or enabled
```

Successful status:

```text
GOLD_V3_13_RANKING_DECISION_TEMPLATE_READY_AUDIT_ONLY
```

## Stop conditions

Stop as blocked and do not treat the template as ready if:

```text
stage-12 summary is missing or status is not READY
stage-12 packet is missing or row count is not 8
stage-12 deferred diagnostics is missing
ranking template row count is not 8
required metrics cannot be parsed enough to rank rows
any decision is auto-filled with an approval/rejection/request value
any replay/model/signal/ZIP/AI/Discord/MT5/live action would be enabled
```

Blocked status:

```text
GOLD_V3_13_RANKING_DECISION_TEMPLATE_BLOCKED_AUDIT_ONLY
```

## Audit and execution order

Run order:

```text
1. Confirm stage 12 has already completed locally.
2. Run GOLD_V3_13_RANKING_DECISION_TEMPLATE_AUDIT_ONLY.bat.
3. Inspect gold_v3_13_summary.json.
4. Inspect gold_v3_13_ranking_decision_template.csv.
5. Inspect gold_v3_13_candidate_family_group_summary.csv.
6. Inspect GOLD_V3_13_RANKING_DECISION_TEMPLATE_AUDIT_ONLY_REPORT.md.
```

Success check:

```text
summary.status = GOLD_V3_13_RANKING_DECISION_TEMPLATE_READY_AUDIT_ONLY
auto_approval = false
final_candidate_approval = false
threshold_finalization = false
replay_executed = false
model_training = false
signals_generated = false
zip_output_created = false
ai_api_called = false
discord_enabled = false
mt5_enabled = false
live_hook_enabled = false
live_evaluator_enabled = false
```

## AI API

```text
AI API is not called in stage 13.
```

## Prohibited in stage 13

```text
final candidate approval
threshold finalization
replay execution
model training
signal generation
ZIP output
Discord notification
MT5 order path
AI API call
live hook
live evaluator
final signal
GOLD V2 live SOT use
old GOLD/DISC8 source recovery
```
