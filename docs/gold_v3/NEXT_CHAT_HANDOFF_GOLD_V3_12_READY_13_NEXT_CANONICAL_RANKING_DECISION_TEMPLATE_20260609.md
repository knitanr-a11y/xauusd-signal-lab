# CANONICAL NEXT CHAT HANDOFF - GOLD V3 12 READY / 13 RANKING DECISION TEMPLATE

Created: 2026-06-09

Repository: `knitanr-a11y/xauusd-signal-lab`

## IMPORTANT - this document is the only primary handoff

This is the canonical handoff document for the next chat.

It supersedes these earlier handoff drafts:

```text
docs/gold_v3/NEXT_CHAT_HANDOFF_GOLD_V3_12_READY_13_NEXT_HUMAN_DECISION_TEMPLATE_20260609.md
docs/gold_v3/NEXT_CHAT_HANDOFF_GOLD_V3_12_READY_13_NEXT_RANKING_OBJECTIVE_ADDENDUM_20260609.md
```

If any instruction conflicts, this canonical document wins.

## What went wrong before

The earlier handoff was bad because it split the objective across two files and made stage 13 sound like a readability-focused human template.

That is not the user's intent.

The user wants ranking by likely trading quality:

```text
勝率/PFが高そうな候補、または絞れば勝率/PFが上がりそうな候補を優先。
日に2トレード以上あると助かる。
人間が読みやすいことは重要ではない。
```

Also, the handoff was not strict enough about paths. This caused risk of:

- output folder not being created
- BAT being created in the wrong directory
- BAT `cd` target being wrong
- scripts stopping before writing audit files when inputs are missing

Stage 13 must fix this with an explicit path/run contract.

## Current position

GOLD V3 has reached:

```text
GOLD_V3_12_DEPLOYABILITY_REVIEW_PACKET_READY_AUDIT_ONLY
```

The latest completed stage is 12:

```text
GOLD_V3_12_DEPLOYABILITY_REVIEW_PACKET_AUDIT_ONLY
```

Stage 13 has not been created yet.

The next implementation task is exactly:

```text
Create GOLD_V3_13_RANKING_DECISION_TEMPLATE_AUDIT_ONLY spec/script/BAT.
```

Do not create a plain readability-focused `GOLD_V3_13_HUMAN_DECISION_TEMPLATE_AUDIT_ONLY` and stop.

## Hard implementation path contract for stage 13

Create exactly these repository files:

```text
docs/gold_v3/GOLD_V3_13_RANKING_DECISION_TEMPLATE_AUDIT_ONLY_SPEC_20260609.md
scripts/gold_v3_runtime/gold_v3_13_ranking_decision_template_audit_only.py
scripts/gold_v3_runtime/bat/GOLD_V3_13_RANKING_DECISION_TEMPLATE_AUDIT_ONLY.bat
```

Do not place the BAT directly under `scripts/gold_v3_runtime/`.

Do not place the BAT under `docs/`.

Do not create a local-only patch instead of committing these files through GitHub.

## Hard output folder contract for stage 13

The script must create the output directory at runtime with `mkdir(parents=True, exist_ok=True)`.

Expected local runtime output directory:

```text
Files/FX_OUTPUTS/gold_v3/13_ranking_decision_template_audit_only/
```

This folder is not created by GitHub file creation. It is created only when the BAT/script is run locally.

The script must create this folder even if required input files are missing. If inputs are missing, still write at least:

```text
gold_v3_13_input_inventory.csv
gold_v3_13_summary.json
gold_v3_13_decision_matrix.csv
gold_v3_13_blocker_matrix.csv
GOLD_V3_13_RANKING_DECISION_TEMPLATE_AUDIT_ONLY_REPORT.md
```

with a blocked/input-review status.

## Required runtime path helper contract

Use the same path convention as previous GOLD V3 runtime scripts.

The script should include this pattern or an equivalent that resolves the same locations:

```python
from pathlib import Path

def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]

def files_root() -> Path:
    r = repo_root()
    return r.parents[1] if len(r.parents) >= 2 else r.parent

def v3_output_root() -> Path:
    return files_root() / "FX_OUTPUTS" / "gold_v3"

def out_dir() -> Path:
    p = v3_output_root() / "13_ranking_decision_template_audit_only"
    p.mkdir(parents=True, exist_ok=True)
    return p
```

Do not use the repository root itself as the output root.

Do not write outputs into `docs/` or `scripts/`.

Do not rely on an already-existing output folder.

## Required BAT contract

Create the BAT exactly here:

```text
scripts/gold_v3_runtime/bat/GOLD_V3_13_RANKING_DECISION_TEMPLATE_AUDIT_ONLY.bat
```

The BAT should run from the repository root. Because it lives in `scripts/gold_v3_runtime/bat/`, it must go up three levels.

Recommended BAT contents:

```bat
@echo off
setlocal
cd /d "%~dp0\..\..\.."
python scripts\gold_v3_runtime\gold_v3_13_ranking_decision_template_audit_only.py
if errorlevel 1 (
  echo [ERROR] GOLD V3 13 failed.
  pause
  exit /b 1
)
echo [OK] GOLD V3 13 completed.
pause
endlocal
```

Do not use only two `..` segments from the BAT folder.

Do not assume the user's current working directory is already the repo root.

## Non-negotiable guardrails

- GOLD V3 remains audit-only.
- No source recovery has been approved.
- No final candidate approval has been given.
- No threshold finalization has been done.
- No replay execution should be done in stage 13.
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

## Stage 12 outputs

Expected local output directory:

```text
Files/FX_OUTPUTS/gold_v3/12_deployability_review_packet_audit_only/
```

Observed stage 12 output files:

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

## Critical interpretation: 8 rows are rule candidates, not trade points

The 8 packet rows are not 8 trades.

They are 8 rule candidates, each representing:

```text
TP/SL/Horizon profile + direction + feature condition
```

Each candidate may match many historical entries. The next replay stage, not stage 13, should later inspect all entries matching any approved candidate/family.

Stage 13 only creates ranking/decision artifacts.

## Stage 12 deployability review packet rows

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

## Required grouping in stage 13

Do not rank all 8 rows as if they were independent entry ideas.

Group them first:

```text
GROUP_H1_ATR56_HIGH_VOL:
  condition = h1_atr56 >= 9.95812
  profiles = TP100_SL40_H96, TP80_SL30_H64, TP50_SL20_H48, TP30_SL10_H32, TP20_SL10_H28
  risk = absolute_volatility_regime_risk

GROUP_M15_ATR28_MID_VOL_RANGE:
  condition = 3.59086 <= m15_atr28 <= 4.29321
  profiles = TP80_SL30_H64
  risk = absolute_volatility_regime_risk

GROUP_H4_RET4_MOMENTUM:
  condition = h4_ret4 >= 0.00751699
  profiles = TP150_SL60_H128
  risk = none

GROUP_H1_RET16_MOMENTUM_NEG_FOLD:
  condition = h1_ret16 >= 0.00707975
  profiles = TP50_SL20_H48
  risk = has_negative_test_fold
```

## Stage 13 ranking objective

Stage 13 should produce both row-level and group-level ranking outputs.

Ranking should prioritize:

1. likely high win rate / high PF
2. enough frequency, ideally around 2 trades/day or more
3. positive fold consistency
4. strong average result/lift
5. risk flags that may require narrowing
6. candidates with narrowing potential even if not immediately clean

If exact win rate/PF is not available at stage 13, create clearly named proxy fields:

```text
winrate_proxy
pf_proxy
quality_score
frequency_score
narrowing_potential_score
ranking_score
```

Do not present proxies as true win rate or true PF.

## Stage 13 input files

Use:

```text
Files/FX_OUTPUTS/gold_v3/12_deployability_review_packet_audit_only/gold_v3_12_summary.json
Files/FX_OUTPUTS/gold_v3/12_deployability_review_packet_audit_only/gold_v3_12_deployability_review_packet.csv
Files/FX_OUTPUTS/gold_v3/12_deployability_review_packet_audit_only/gold_v3_12_deferred_candidate_diagnostics.csv
```

Do not use GOLD V2 selected/final/source/arbitration artifacts as live SOT.

## Stage 13 suggested outputs

Write to:

```text
Files/FX_OUTPUTS/gold_v3/13_ranking_decision_template_audit_only/
```

Output files:

```text
GOLD_V3_13_RANKING_DECISION_TEMPLATE_AUDIT_ONLY_REPORT.md
gold_v3_13_summary.json
gold_v3_13_input_inventory.csv
gold_v3_13_ranked_rule_candidate_rows.csv
gold_v3_13_ranked_candidate_family_groups.csv
gold_v3_13_decision_template.csv
gold_v3_13_deferred_narrowing_candidates.csv
gold_v3_13_decision_matrix.csv
gold_v3_13_blocker_matrix.csv
```

## Stage 13 decision template fields

Required decision fields should remain empty/pending:

```text
human_decision = PENDING_HUMAN_REVIEW
allowed_decisions = APPROVE_FOR_NEXT_AUDIT_ONLY_REPLAY | REJECT | REQUEST_MORE_AUDIT
human_note = ""
reviewer = ""
reviewed_at_utc = ""
```

Add ranking fields before those decision fields.

## Stage 13 blocker logic

Suggested blocker matrix:

```text
G3-13-001 12 inputs: CLOSED if 12 READY and packet exists
G3-13-002 ranked candidate rows: CLOSED if rows > 0
G3-13-003 ranked family groups: CLOSED if groups > 0
G3-13-004 human decision: OPEN_HUMAN_ACTION_REQUIRED
G3-13-005 replay execution: CLOSED_BLOCKED_BY_POLICY
G3-13-006 final approval: CLOSED_BLOCKED_BY_POLICY
G3-13-007 threshold finalization: CLOSED_BLOCKED_BY_POLICY
G3-13-008 signal/live: CLOSED_BLOCKED_BY_POLICY
G3-13-009 zip output: CLOSED_DISABLED
G3-13-010 external actions: CLOSED
```

## Common failure modes to avoid

- Do not ask the user to approve/reject the 8 rows before creating stage 13 artifacts.
- Do not create a plain readability-focused `HUMAN_DECISION_TEMPLATE` and stop.
- Do not treat the 8 rows as 8 trade points.
- Do not count the five `h1_atr56 >= 9.95812` profiles as five independent entry ideas without grouping.
- Do not claim true PF or true win rate if only proxies are available.
- Do not run replay in stage 13.
- Do not approve anything automatically.
- Do not create ZIP output.
- Do not put BAT in the wrong folder.
- Do not write output files into the repository tree.
- Do not fail silently when inputs are missing; write audit files with blocked status.

## Next chat start prompt

Use this prompt in the next chat. Do not include the superseded docs unless needed for audit history.

```text
repo: knitanr-a11y/xauusd-signal-lab

まず以下を読んで、続きからお願いします。

docs/gold_v3/NEXT_CHAT_HANDOFF_GOLD_V3_12_READY_13_NEXT_CANONICAL_RANKING_DECISION_TEMPLATE_20260609.md

GOLD V3は現在audit-onlyです。
12は完了済みで、statusは以下です。
GOLD_V3_12_DEPLOYABILITY_REVIEW_PACKET_READY_AUDIT_ONLY

13はまだ作成されていません。
次にやることは、GOLD_V3_13_RANKING_DECISION_TEMPLATE_AUDIT_ONLY のspec/script/BAT作成です。

重要:
- このcanonical handoffが正本です。旧handoff/addendumと矛盾したら、このドキュメントを優先してください。
- 8 packet rowsは8個のトレードポイントではなく、8個のルール候補です。
- 人間が読みやすいことより、勝率/PFが高そうな候補、または絞れば勝率/PFが上がりそうな候補を優先してください。
- 日に2トレード以上を狙えるなら助かります。
- h1_atr56 >= 9.95812 は5つのTP/SL profileで共有される同一条件familyなので、独立候補として雑に数えないでください。
- 13ではranking-oriented audit-only decision templateを作るだけで、自動承認しないでください。
- true PF/true win rateがまだ無い場合は proxy と明記してください。
- spec/script/BATは以下の正しいrepo pathに作成してください:
  docs/gold_v3/GOLD_V3_13_RANKING_DECISION_TEMPLATE_AUDIT_ONLY_SPEC_20260609.md
  scripts/gold_v3_runtime/gold_v3_13_ranking_decision_template_audit_only.py
  scripts/gold_v3_runtime/bat/GOLD_V3_13_RANKING_DECISION_TEMPLATE_AUDIT_ONLY.bat
- BATは scripts/gold_v3_runtime/bat/ から repo root へ cd /d "%~dp0\..\..\.." してください。
- scriptは Files/FX_OUTPUTS/gold_v3/13_ranking_decision_template_audit_only/ を mkdir(parents=True, exist_ok=True) で必ず生成してください。
- 入力不足でもフォルダと input_inventory / summary / decision_matrix / blocker_matrix / report を必ず出力してください。
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
