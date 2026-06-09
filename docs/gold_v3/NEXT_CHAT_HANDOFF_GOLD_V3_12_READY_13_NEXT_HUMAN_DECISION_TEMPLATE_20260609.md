# NEXT CHAT HANDOFF - GOLD V3 12 READY / 13 NEXT HUMAN DECISION TEMPLATE

Created: 2026-06-09

Repository: `knitanr-a11y/xauusd-signal-lab`

## Read this first in the next chat

This document is the handoff source-of-truth for the next chat.

The next assistant should **not** ask the user to approve/reject the 8 candidates immediately. The next assistant should first create the stage 13 audit-only human decision template artifacts.

Immediate next implementation task:

```text
Create GOLD_V3_13_HUMAN_DECISION_TEMPLATE_AUDIT_ONLY spec/script/BAT.
```

Do not create stage 14, do not run replay, and do not perform any live/signal action until explicitly requested later.

## Current position

GOLD V3 has reached:

```text
GOLD_V3_12_DEPLOYABILITY_REVIEW_PACKET_READY_AUDIT_ONLY
```

The latest completed stage is 12:

```text
GOLD_V3_12_DEPLOYABILITY_REVIEW_PACKET_AUDIT_ONLY
```

The next stage should be 13:

```text
GOLD_V3_13_HUMAN_DECISION_TEMPLATE_AUDIT_ONLY
```

Stage 13 has not been created yet.

## Non-negotiable guardrails

- GOLD V3 remains audit-only.
- No source recovery has been approved.
- No final candidate approval has been given.
- No threshold finalization has been done.
- No model training has been done.
- No signal generation has been done.
- No live hook has been enabled.
- No live evaluator has been enabled.
- No Discord notification has been enabled.
- No MT5 order path has been enabled.
- No AI API call has been enabled.
- No ZIP output should be created.
- External actions remain OFF.
- `APPROVE_FOR_NEXT_AUDIT_ONLY_REPLAY` is not final approval and not live deployment approval.
- `REQUEST_MORE_AUDIT` is not approval.
- Old GOLD/DISC8 remains quarantined.
- GOLD V2 source/final/arbitration artifacts remain historical/audit references only, not live source-of-truth.
- Future/profit/exit data is label/evaluation only and must never be used as a live feature selector.
- A002 is auxiliary-only and must not become the main path.

## Recent correction note

The assistant previously said "13" had been added, but that was incorrect. Only stage 12 spec/script/BAT had been added at that point. Stage 13 still needs to be implemented.

## Stage 12 outputs

Expected local output directory:

```text
Files/FX_OUTPUTS/gold_v3/12_deployability_review_packet_audit_only/
```

Uploaded/observed output files from stage 12:

```text
gold_v3_12_blocker_matrix.csv
gold_v3_12_decision_matrix.csv
gold_v3_12_deferred_candidate_diagnostics.csv
gold_v3_12_deployability_review_packet.csv
GOLD_V3_12_DEPLOYABILITY_REVIEW_PACKET_AUDIT_ONLY_REPORT.md
gold_v3_12_input_inventory.csv
gold_v3_12_readiness_summary.csv
gold_v3_12_summary.json
```

Stage 12 summary:

```text
status = GOLD_V3_12_DEPLOYABILITY_REVIEW_PACKET_READY_AUDIT_ONLY
input_preview_rows = 151
deployability_review_packet_rows = 8
deferred_rows = 143
readiness_summary_rows = 10
packet_readiness_counts:
  REVIEW_READY = 7
  REVIEW_READY_WITH_NEGATIVE_FOLD_RISK = 1
deferred_readiness_counts:
  MANUAL_REVIEW_BUCKET_UNSTABLE = 85
  REVIEW_ONLY_NOT_DEPLOYABLE_RAW_PRICE_LEVEL = 58
human_decision_required = true
auto_approval = false
final_candidate_approval = false
threshold_finalization = false
model_training = false
signals_generated = false
zip_output_created = false
external_actions all false
```

Stage 12 blocker status:

```text
G3-12-001 11 inputs: CLOSED
G3-12-002 review packet: CLOSED
G3-12-003 human decision: OPEN_HUMAN_ACTION_REQUIRED
G3-12-004 final approval: CLOSED_BLOCKED_BY_POLICY
G3-12-005 threshold finalization: CLOSED_BLOCKED_BY_POLICY
G3-12-006 signal/live: CLOSED_BLOCKED_BY_POLICY
G3-12-007 zip output: CLOSED_DISABLED
G3-12-008 external actions: CLOSED
```

## The 8 packet rows are rule candidates, not trade points

Important explanation already given to the user:

The 8 rows are not 8 individual trades. They are 8 rule candidates, each representing a rule condition applied to many historical entry rows. The next audit-only replay should examine all historical entries matching approved rule candidates, not just 8 trade timestamps.

In stage 13, do not replay those entries yet. Stage 13 only creates a human decision template.

## Stage 12 deployability review packet rows

The 8 rows are:

### 1. USDPRICE_TP80_SL30_H64 / LONG / m15_atr28

```text
feature_family = volatility_atr
readiness_label = REVIEW_READY
rule_expression_preview = 3.59086 <= m15_atr28 <= 4.29321
folds = 8
positive_test_folds = 8
positive_test_fold_rate = 1.0
test_avg_result_mean = 6.892652639855571
test_avg_result_min = 0.3091566265060442
test_avg_result_max = 16.10069444444444
test_lift_mean = 2.864605130428605
test_rows_total = 3141
dominant_bucket_id = B4
dominant_bucket_count = 5
dominant_bucket_rate = 0.625
risk_flags = absolute_volatility_regime_risk
human_decision = PENDING_HUMAN_REVIEW
```

### 2. USDPRICE_TP150_SL60_H128 / LONG / h4_ret4

```text
feature_family = momentum_return
readiness_label = REVIEW_READY
rule_expression_preview = h4_ret4 >= 0.00751699
folds = 10
positive_test_folds = 10
positive_test_fold_rate = 1.0
test_avg_result_mean = 7.728223796443498
test_avg_result_min = 0.316084452975031
test_avg_result_max = 15.514715639810412
test_lift_mean = 2.102157116320144
test_rows_total = 3819
dominant_bucket_id = B5
dominant_bucket_count = 6
dominant_bucket_rate = 0.6
risk_flags = none
human_decision = PENDING_HUMAN_REVIEW
```

### 3. USDPRICE_TP100_SL40_H96 / LONG / h1_atr56

```text
feature_family = volatility_atr
readiness_label = REVIEW_READY
rule_expression_preview = h1_atr56 >= 9.95812
folds = 6
positive_test_folds = 6
positive_test_fold_rate = 1.0
test_avg_result_mean = 7.351682710734553
test_avg_result_min = 0.6891465863453691
test_avg_result_max = 13.621934984520095
test_lift_mean = 1.365362369391602
test_rows_total = 9013
dominant_bucket_id = B5
dominant_bucket_count = 4
dominant_bucket_rate = 0.6666666666666666
risk_flags = absolute_volatility_regime_risk
human_decision = PENDING_HUMAN_REVIEW
```

### 4. USDPRICE_TP80_SL30_H64 / LONG / h1_atr56

```text
feature_family = volatility_atr
readiness_label = REVIEW_READY
rule_expression_preview = h1_atr56 >= 9.95812
folds = 6
positive_test_folds = 6
positive_test_fold_rate = 1.0
test_avg_result_mean = 5.271711486260258
test_avg_result_min = 2.145853413654619
test_avg_result_max = 9.308730650154782
test_lift_mean = 1.173423603190347
test_rows_total = 9013
dominant_bucket_id = B5
dominant_bucket_count = 4
dominant_bucket_rate = 0.6666666666666666
risk_flags = absolute_volatility_regime_risk
human_decision = PENDING_HUMAN_REVIEW
```

### 5. USDPRICE_TP50_SL20_H48 / LONG / h1_atr56

```text
feature_family = volatility_atr
readiness_label = REVIEW_READY
rule_expression_preview = h1_atr56 >= 9.95812
folds = 6
positive_test_folds = 6
positive_test_fold_rate = 1.0
test_avg_result_mean = 4.037770160407927
test_avg_result_min = 1.5866315261044177
test_avg_result_max = 6.89236842105262
test_lift_mean = 1.0155894430155834
test_rows_total = 9013
dominant_bucket_id = B5
dominant_bucket_count = 4
dominant_bucket_rate = 0.6666666666666666
risk_flags = absolute_volatility_regime_risk
human_decision = PENDING_HUMAN_REVIEW
```

### 6. USDPRICE_TP30_SL10_H32 / LONG / h1_atr56

```text
feature_family = volatility_atr
readiness_label = REVIEW_READY
rule_expression_preview = h1_atr56 >= 9.95812
folds = 6
positive_test_folds = 6
positive_test_fold_rate = 1.0
test_avg_result_mean = 2.2886220039735554
test_avg_result_min = 1.2917469879518084
test_avg_result_max = 3.792852598091202
test_lift_mean = 0.531516236449394
test_rows_total = 9013
dominant_bucket_id = B5
dominant_bucket_count = 4
dominant_bucket_rate = 0.6666666666666666
risk_flags = absolute_volatility_regime_risk
human_decision = PENDING_HUMAN_REVIEW
```

### 7. USDPRICE_TP20_SL10_H28 / LONG / h1_atr56

```text
feature_family = volatility_atr
readiness_label = REVIEW_READY
rule_expression_preview = h1_atr56 >= 9.95812
folds = 6
positive_test_folds = 6
positive_test_fold_rate = 1.0
test_avg_result_mean = 1.6256413871307902
test_avg_result_min = 0.8728212851405631
test_avg_result_max = 2.9713043478260883
test_lift_mean = 0.3872731101709543
test_rows_total = 9013
dominant_bucket_id = B5
dominant_bucket_count = 4
dominant_bucket_rate = 0.6666666666666666
risk_flags = absolute_volatility_regime_risk
human_decision = PENDING_HUMAN_REVIEW
```

### 8. USDPRICE_TP50_SL20_H48 / LONG / h1_ret16

```text
feature_family = momentum_return
readiness_label = REVIEW_READY_WITH_NEGATIVE_FOLD_RISK
rule_expression_preview = h1_ret16 >= 0.00707975
folds = 10
positive_test_folds = 9
positive_test_fold_rate = 0.9
test_avg_result_mean = 4.936223511086762
test_avg_result_min = -0.2232227488151849
test_avg_result_max = 10.426721804511269
test_lift_mean = 2.07059108748608
test_rows_total = 4942
dominant_bucket_id = B5
dominant_bucket_count = 6
dominant_bucket_rate = 0.6
risk_flags = has_negative_test_fold
human_decision = PENDING_HUMAN_REVIEW
```

## Key interpretation for next chat

The packet is dominated by one shared condition:

```text
h1_atr56 >= 9.95812
```

This same condition appears across five TP/SL profiles:

```text
TP100_SL40_H96
TP80_SL30_H64
TP50_SL20_H48
TP30_SL10_H32
TP20_SL10_H28
```

Do not treat those as five independent signal ideas without checking overlap. They are one feature-condition family with different exit profiles.

Other distinct candidates:

```text
m15_atr28 range: 3.59086 <= m15_atr28 <= 4.29321
h4_ret4 momentum: h4_ret4 >= 0.00751699
h1_ret16 momentum: h1_ret16 >= 0.00707975, but negative fold risk exists
```

## Recommended next stage 13

Create stage 13 as:

```text
GOLD_V3_13_HUMAN_DECISION_TEMPLATE_AUDIT_ONLY
```

Suggested purpose:

- Read stage 12 deployability review packet.
- Create a human decision template CSV/Markdown.
- Group same feature-condition family rows together, especially h1_atr56 shared condition.
- Provide empty decision fields only.
- Do not auto-approve anything.
- Do not finalize thresholds.
- Do not run replay yet.
- Do not ask the user for manual decisions before creating the template.

Suggested outputs:

```text
Files/FX_OUTPUTS/gold_v3/13_human_decision_template_audit_only/
GOLD_V3_13_HUMAN_DECISION_TEMPLATE_AUDIT_ONLY_REPORT.md
gold_v3_13_summary.json
gold_v3_13_input_inventory.csv
gold_v3_13_human_decision_template.csv
gold_v3_13_candidate_family_group_summary.csv
gold_v3_13_decision_matrix.csv
gold_v3_13_blocker_matrix.csv
```

Suggested decision fields:

```text
human_decision = PENDING_HUMAN_REVIEW
allowed_decisions = APPROVE_FOR_NEXT_AUDIT_ONLY_REPLAY | REJECT | REQUEST_MORE_AUDIT
human_note = ""
reviewer = ""
reviewed_at_utc = ""
```

Suggested stage 13 blocker logic:

```text
G3-13-001 12 inputs: CLOSED if 12 READY and packet exists
G3-13-002 template rows: CLOSED if template rows > 0
G3-13-003 human decision: OPEN_HUMAN_ACTION_REQUIRED
G3-13-004 replay execution: CLOSED_BLOCKED_BY_POLICY
G3-13-005 final approval: CLOSED_BLOCKED_BY_POLICY
G3-13-006 threshold finalization: CLOSED_BLOCKED_BY_POLICY
G3-13-007 signal/live: CLOSED_BLOCKED_BY_POLICY
G3-13-008 zip output: CLOSED_DISABLED
G3-13-009 external actions: CLOSED
```

## Next chat start prompt - Japanese recommended

```text
repo: knitanr-a11y/xauusd-signal-lab

まず以下を読んで、続きからお願いします。
docs/gold_v3/NEXT_CHAT_HANDOFF_GOLD_V3_12_READY_13_NEXT_HUMAN_DECISION_TEMPLATE_20260609.md

GOLD V3は現在audit-onlyです。
12は完了済みで、statusは以下です。
GOLD_V3_12_DEPLOYABILITY_REVIEW_PACKET_READY_AUDIT_ONLY

13はまだ作成されていません。
次にやることは、GOLD_V3_13_HUMAN_DECISION_TEMPLATE_AUDIT_ONLY のspec/script/BAT作成です。

重要:
- 8 packet rowsは8個のトレードポイントではなく、8個のルール候補です。
- 13では人間判断テンプレートを作るだけで、判断値を自動入力しないでください。
- 人間判断をユーザーに求めるのは、13テンプレート作成後です。
- 自動承認は禁止です。
- final candidate approvalは禁止です。
- threshold finalizationは禁止です。
- replay実行はまだ禁止です。
- model trainingは禁止です。
- signal generationは禁止です。
- ZIP outputは禁止です。
- Discord / MT5 / AI API / live hook / live evaluator / final signal はOFFです。
- APPROVE_FOR_NEXT_AUDIT_ONLY_REPLAY はfinal承認でもlive承認でもありません。
- REQUEST_MORE_AUDIT は承認ではありません。
- 旧GOLD/DISC8は隔離継続です。
- GOLD V2 artifactはhistorical/audit referenceのみで、live SOTではありません。
```

## Next chat start prompt - English fallback

```text
repo: knitanr-a11y/xauusd-signal-lab

Please read and continue from:
docs/gold_v3/NEXT_CHAT_HANDOFF_GOLD_V3_12_READY_13_NEXT_HUMAN_DECISION_TEMPLATE_20260609.md

GOLD V3 is currently audit-only.
Stage 12 is complete and READY:
GOLD_V3_12_DEPLOYABILITY_REVIEW_PACKET_READY_AUDIT_ONLY.

Stage 13 has not been created yet.
Next task is to create GOLD_V3_13_HUMAN_DECISION_TEMPLATE_AUDIT_ONLY.

Important:
- The 8 packet rows are rule candidates, not 8 trade points.
- In stage 13, create the human decision template only; do not auto-fill decisions.
- Ask for human decisions only after stage 13 template is created.
- Do not auto-approve anything.
- Do not finalize thresholds.
- Do not run replay yet.
- Do not train models.
- Do not generate signals.
- Do not create ZIP output.
- Discord / MT5 / AI API / live hook / live evaluator / final signal remain OFF.
- APPROVE_FOR_NEXT_AUDIT_ONLY_REPLAY is not final approval and not live deployment approval.
- REQUEST_MORE_AUDIT is not approval.
- Old GOLD/DISC8 remains quarantined.
- GOLD V2 artifacts remain historical/audit references only, not live SOT.
```
