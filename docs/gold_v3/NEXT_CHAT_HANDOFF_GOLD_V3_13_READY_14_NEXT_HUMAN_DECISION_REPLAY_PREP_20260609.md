# CANONICAL NEXT CHAT HANDOFF - GOLD V3 13 READY / 14 HUMAN DECISION REPLAY PREP

Created: 2026-06-09

Repository: `knitanr-a11y/xauusd-signal-lab`

## IMPORTANT - this document is the only primary handoff now

This is the canonical handoff document for the next chat.

It supersedes all earlier GOLD V3 12-ready / 13-next handoff documents, including:

```text
docs/gold_v3/NEXT_CHAT_HANDOFF_GOLD_V3_12_READY_13_NEXT_CANONICAL_RANKING_DECISION_TEMPLATE_20260609.md
docs/gold_v3/NEXT_CHAT_HANDOFF_GOLD_V3_12_READY_13_NEXT_HUMAN_DECISION_TEMPLATE_20260609.md
docs/gold_v3/NEXT_CHAT_HANDOFF_GOLD_V3_12_READY_13_NEXT_RANKING_OBJECTIVE_ADDENDUM_20260609.md
```

If any instruction conflicts, this document wins.

## GOLD V2 / old GOLD quarantine

GOLD V3 is the only active audit chain for the next task.

GOLD V2, old GOLD, DISC8, and any related legacy artifacts are quarantined.

For Stage 14, do **not** read, import, compare, merge, recover from, copy from, backfill from, or use GOLD V2 / old GOLD / DISC8 artifacts as source-of-truth, fallback, reference logic, replay input, feature source, rule source, candidate source, or validation source.

The next chat should use only GOLD V3 Stage 13 outputs as the immediate source-of-truth inputs for Stage 14.

The only acceptable mention of GOLD V2 in this handoff is this quarantine warning and the already-recorded safety flag that V2 live SOT was not used.

## Current status

GOLD V3 remains audit-only.

Latest completed stage:

```text
GOLD_V3_13_RANKING_DECISION_TEMPLATE_AUDIT_ONLY
```

Current status:

```text
GOLD_V3_13_RANKING_DECISION_TEMPLATE_READY_AUDIT_ONLY
```

Stage 13 produced a ranking-oriented human decision template from the GOLD V3 12 deployability packet.

No final candidate approval has been given.
No replay has been executed.
No threshold finalization has been executed.
No model training has been executed.
No signal generation has been executed.
No ZIP output has been created.
Discord / MT5 / AI API / live hook / live evaluator / final signal remain OFF.

## Files checked from local stage-13 run

The local run output directory selected by the stage-13 script was:

```text
C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files\FX_OUTPUTS\gold_v3
```

Stage 13 output files inspected:

```text
gold_v3_13_summary.json
gold_v3_13_input_inventory.csv
gold_v3_13_ranked_rule_candidate_rows.csv
gold_v3_13_ranked_candidate_family_groups.csv
gold_v3_13_decision_template.csv
gold_v3_13_deferred_narrowing_candidates.csv
gold_v3_13_decision_matrix.csv
gold_v3_13_blocker_matrix.csv
gold_v3_13_ranking_decision_template.csv
gold_v3_13_candidate_family_group_summary.csv
GOLD_V3_13_RANKING_DECISION_TEMPLATE_AUDIT_ONLY_REPORT.md
```

## Stage-13 validation summary

Mechanical checks passed:

```text
summary.status == GOLD_V3_13_RANKING_DECISION_TEMPLATE_READY_AUDIT_ONLY
stage12_status == GOLD_V3_12_DEPLOYABILITY_REVIEW_PACKET_READY_AUDIT_ONLY
packet_rows == 8
ranking_template_rows == 8
candidate_family_group_rows == 4
deferred_rows == 143
deferred_narrowing_rows == 143
h1_atr56_overlap_disclosed == true
all ranked rows have human_decision == PENDING_HUMAN_REVIEW
all ranked rows have ranking_is_proxy_only == true
all ranked rows have allowed_decisions == APPROVE_FOR_NEXT_AUDIT_ONLY_REPLAY | REJECT | REQUEST_MORE_AUDIT
input inventory files all exist
ranked rows aliases match decision_template and ranking_decision_template
ranked family aliases match candidate_family_group_summary
```

Safety flags checked false:

```text
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
final_signal_enabled = false
gold_v2_live_sot_used = false
```

## Stage-13 blockers

Closed / blocked as expected:

```text
G3-13-001 12 inputs: CLOSED
G3-13-002 ranking template rows: CLOSED
G3-13-003 family grouping: CLOSED
G3-13-005 replay execution: CLOSED_BLOCKED_BY_POLICY
G3-13-006 final approval: CLOSED_BLOCKED_BY_POLICY
G3-13-007 threshold finalization: CLOSED_BLOCKED_BY_POLICY
G3-13-008 model training: CLOSED_BLOCKED_BY_POLICY
G3-13-009 signal/live: CLOSED_BLOCKED_BY_POLICY
G3-13-010 zip output: CLOSED_DISABLED
G3-13-011 external actions: CLOSED
```

Still open by design:

```text
G3-13-004 human decision: OPEN_HUMAN_ACTION_REQUIRED
```

This is the correct stopping point. Do not bypass it.

## Stage-13 top proxy-ranked candidates

Important: ranking values are proxy-only. They are not true PF and not true win rate.
Exact replay must recompute true trade frequency, win rate, PF, drawdown, and execution behavior.

| Rank | Group | Profile | Feature | Bucket | Risk |
|---:|---|---|---|---|---|
| 1 | GROUP_H4_RET4_MOMENTUM | USDPRICE_TP150_SL60_H128 | h4_ret4 >= 0.00751699 | PRIORITY_A_HIGH_QUALITY_AND_FREQUENCY | none |
| 2 | GROUP_M15_ATR28_MID_VOL_RANGE | USDPRICE_TP80_SL30_H64 | 3.59086 <= m15_atr28 <= 4.29321 | PRIORITY_A_HIGH_QUALITY_AND_FREQUENCY | absolute_volatility_regime_risk |
| 3 | GROUP_H1_ATR56_HIGH_VOL | USDPRICE_TP100_SL40_H96 | h1_atr56 >= 9.95812 | PRIORITY_A_HIGH_QUALITY_AND_FREQUENCY | absolute_volatility_regime_risk |
| 4 | GROUP_H1_ATR56_HIGH_VOL | USDPRICE_TP80_SL30_H64 | h1_atr56 >= 9.95812 | PRIORITY_B_HIGH_QUALITY_LOW_FREQUENCY_OR_RISK | absolute_volatility_regime_risk |
| 5 | GROUP_H1_RET16_MOMENTUM_NEG_FOLD | USDPRICE_TP50_SL20_H48 | h1_ret16 >= 0.00707975 | PRIORITY_B_HIGH_QUALITY_LOW_FREQUENCY_OR_RISK | has_negative_test_fold |
| 6 | GROUP_H1_ATR56_HIGH_VOL | USDPRICE_TP50_SL20_H48 | h1_atr56 >= 9.95812 | PRIORITY_C_NARROWING_POTENTIAL | absolute_volatility_regime_risk |
| 7 | GROUP_H1_ATR56_HIGH_VOL | USDPRICE_TP30_SL10_H32 | h1_atr56 >= 9.95812 | PRIORITY_C_NARROWING_POTENTIAL | absolute_volatility_regime_risk |
| 8 | GROUP_H1_ATR56_HIGH_VOL | USDPRICE_TP20_SL10_H28 | h1_atr56 >= 9.95812 | PRIORITY_C_NARROWING_POTENTIAL | absolute_volatility_regime_risk |

## Candidate family interpretation

There are 4 family groups:

```text
GROUP_H4_RET4_MOMENTUM
GROUP_M15_ATR28_MID_VOL_RANGE
GROUP_H1_ATR56_HIGH_VOL
GROUP_H1_RET16_MOMENTUM_NEG_FOLD
```

Critical overlap rule:

```text
GROUP_H1_ATR56_HIGH_VOL has 5 rows using the same entry condition:
h1_atr56 >= 9.95812
```

These 5 rows are different TP/SL/Horizon profiles of the same entry family. Do not count them as 5 independent entry ideas.

## Deferred candidates

Stage 13 produced 143 deferred narrowing candidates.

Deferred next-audit buckets:

```text
REQUEST_MORE_AUDIT_BOUNDARY_OR_BUCKET_STABILITY: 85
DEFER_RAW_PRICE_LEVEL_DO_NOT_DEPLOY: 58
```

These are not approvals.

## Important caution about frequency

`estimated_trades_per_day` is proxy-only. It is derived from stage-12 row counts using:

```text
proxy_from_stage12_input_preview_rows; not_exact_calendar_days; recompute_exactly_in_replay
```

Do not treat these numbers as true expected trades per day.
True trade frequency must be recomputed in the next audit-only replay planning/replay stage.

## Repository repairs completed before this handoff

The following repairs were made before stage-13 output validation:

```text
03 spec placeholder replaced with formal spec
03 BAT added under scripts/gold_v3_runtime/bat/
06 BAT added under scripts/gold_v3_runtime/bat/
01B ZIP output disabled
13 runtime script path contract repaired to use the GOLD V3 output root convention
13 runtime BAT repaired under scripts/gold_v3_runtime/bat/
misplaced root 13 BAT deleted
obsolete scripts/ root 13 wrapper deleted
```

Relevant fixed runtime paths:

```text
docs/gold_v3/GOLD_V3_13_RANKING_DECISION_TEMPLATE_AUDIT_ONLY_SPEC_20260609.md
scripts/gold_v3_runtime/gold_v3_13_ranking_decision_template_audit_only.py
scripts/gold_v3_runtime/bat/GOLD_V3_13_RANKING_DECISION_TEMPLATE_AUDIT_ONLY.bat
```

## Next stage

Next stage should be:

```text
GOLD_V3_14_HUMAN_RANKING_DECISION_INTAKE_AUDIT_ONLY
```

Purpose:

```text
Accept the human decision for one or more stage-13 ranked candidates.
Prepare an audit-only replay plan for approved-for-replay candidates.
Do not execute replay yet unless explicitly instructed.
```

Allowed human decisions remain:

```text
APPROVE_FOR_NEXT_AUDIT_ONLY_REPLAY
REJECT
REQUEST_MORE_AUDIT
```

`APPROVE_FOR_NEXT_AUDIT_ONLY_REPLAY` is not final approval and not live approval.
`REQUEST_MORE_AUDIT` is not approval.

## Stage-14 implementation target paths

Stage 14 has not been implemented yet. The next chat must create exactly these files unless the user explicitly instructs otherwise:

```text
docs/gold_v3/GOLD_V3_14_HUMAN_RANKING_DECISION_INTAKE_AUDIT_ONLY_SPEC_20260609.md
scripts/gold_v3_runtime/gold_v3_14_human_ranking_decision_intake_audit_only.py
scripts/gold_v3_runtime/bat/GOLD_V3_14_HUMAN_RANKING_DECISION_INTAKE_AUDIT_ONLY.bat
```

Do not create a root-level BAT.
Do not create a root-level Python wrapper.
Do not create files outside `docs/gold_v3/` and `scripts/gold_v3_runtime/` unless explicitly needed for audit documentation.

## Stage-14 BAT contract

The BAT must be placed here:

```text
scripts/gold_v3_runtime/bat/GOLD_V3_14_HUMAN_RANKING_DECISION_INTAKE_AUDIT_ONLY.bat
```

Because the BAT is inside `scripts/gold_v3_runtime/bat/`, it must return to the repository root with:

```bat
cd /d "%~dp0\..\..\.."
```

The BAT must then run:

```bat
python scripts\gold_v3_runtime\gold_v3_14_human_ranking_decision_intake_audit_only.py
```

or use `py -3` fallback first, but the script path must still be the runtime script path above.

The BAT must not call any replay script, training script, signal script, Discord script, MT5 script, AI API script, live hook, live evaluator, or ZIP process.

## Stage-14 script path and output contract

The Stage-14 script must create this output directory:

```text
Files/FX_OUTPUTS/gold_v3/14_human_ranking_decision_intake_audit_only/
```

Use the same output-root convention as the repaired stage-13 runtime script: prefer the existing GOLD V3 output root selected from the stage-13/stage-12 outputs, with the legacy repo-root `Files/FX_OUTPUTS` path only as fallback.

The script must create the output directory with:

```python
p.mkdir(parents=True, exist_ok=True)
```

Required outputs even when inputs are missing:

```text
gold_v3_14_summary.json
gold_v3_14_input_inventory.csv
gold_v3_14_human_decision_intake_template.csv
gold_v3_14_replay_plan_preview.csv
gold_v3_14_decision_matrix.csv
gold_v3_14_blocker_matrix.csv
GOLD_V3_14_HUMAN_RANKING_DECISION_INTAKE_AUDIT_ONLY_REPORT.md
```

If inputs are missing or invalid, write these files with a blocked/input-review status. Do not stop before writing `input_inventory`, `summary`, `decision_matrix`, `blocker_matrix`, and report.

## Stage-14 required inputs

Stage 14 must read Stage 13 outputs as source-of-truth inputs:

```text
Files/FX_OUTPUTS/gold_v3/13_ranking_decision_template_audit_only/gold_v3_13_summary.json
Files/FX_OUTPUTS/gold_v3/13_ranking_decision_template_audit_only/gold_v3_13_decision_template.csv
Files/FX_OUTPUTS/gold_v3/13_ranking_decision_template_audit_only/gold_v3_13_ranked_rule_candidate_rows.csv
Files/FX_OUTPUTS/gold_v3/13_ranking_decision_template_audit_only/gold_v3_13_ranked_candidate_family_groups.csv
Files/FX_OUTPUTS/gold_v3/13_ranking_decision_template_audit_only/gold_v3_13_deferred_narrowing_candidates.csv
Files/FX_OUTPUTS/gold_v3/13_ranking_decision_template_audit_only/gold_v3_13_blocker_matrix.csv
```

Stage 14 must require:

```text
gold_v3_13_summary.status == GOLD_V3_13_RANKING_DECISION_TEMPLATE_READY_AUDIT_ONLY
ranking_template_rows == 8
candidate_family_group_rows == 4
human_decision_required == true
```

## Stage-14 purpose guardrails

Stage 14 is an intake/planning stage only.

It may:

```text
- read stage-13 ranked candidates
- create a blank or user-filled human decision intake template
- validate human decision values if provided by a local CSV/input file
- map APPROVE_FOR_NEXT_AUDIT_ONLY_REPLAY candidates to a replay-plan preview
- keep REJECT and REQUEST_MORE_AUDIT rows separated
- write blocker and decision matrices
```

It must not:

```text
- execute replay
- calculate final true PF/win rate as final proof
- approve candidates for live
- finalize thresholds
- train models
- generate signals
- create ZIP output
- call AI API
- notify Discord
- place MT5 orders
- enable live hook
- enable live evaluator
- create final signal
- read or use GOLD V2, old GOLD, or DISC8 artifacts
```

## Stage-14 success status

Use this status only when input files are present, Stage 13 is READY, and the stage-14 intake template / replay-plan preview / matrices are written:

```text
GOLD_V3_14_HUMAN_RANKING_DECISION_INTAKE_READY_AUDIT_ONLY
```

Use a blocked/input-review status if human decision content is missing, invalid, or not yet provided. This is acceptable because Stage 14 may be a template/intake stage.

## Recommended next chat prompt

Use this for the next chat if you want to proceed:

```text
repo: knitanr-a11y/xauusd-signal-lab

まず以下を読んで、続きからお願いします。

docs/gold_v3/NEXT_CHAT_HANDOFF_GOLD_V3_13_READY_14_NEXT_HUMAN_DECISION_REPLAY_PREP_20260609.md

GOLD V3は現在audit-onlyです。
GOLD V2 / 旧GOLD / DISC8 は隔離中です。14では読まない・使わない・参照しない・fallbackにしないでください。
13は完了済みで、statusは以下です。
GOLD_V3_13_RANKING_DECISION_TEMPLATE_READY_AUDIT_ONLY

次は14:
GOLD_V3_14_HUMAN_RANKING_DECISION_INTAKE_AUDIT_ONLY

重要:
- 13のランキングはproxy-onlyです。true PF / true win rate / true trades per dayではありません。
- 8 rowsは8個のトレードポイントではなく、8個のルール候補です。
- h1_atr56 >= 9.95812 は5つのTP/SL profileで共有される同一entry familyです。独立候補として数えないでください。
- 次にやることはhuman decision intakeとaudit-only replay planの準備です。
- 14のspec/script/BATはhandoff記載の正しいrepo pathに作成してください。
- BATは scripts/gold_v3_runtime/bat/ に置き、cd /d "%~dp0\..\..\.." でrepo rootへ戻してください。
- 14 scriptは出力フォルダを mkdir(parents=True, exist_ok=True) で必ず作ってください。
- 入力不足でも input_inventory / summary / decision_matrix / blocker_matrix / report を必ず出してください。
- replay executionはまだ禁止です。実行する場合は別途明示指示が必要です。
- final candidate approvalは禁止です。
- threshold finalizationは禁止です。
- model trainingは禁止です。
- signal generationは禁止です。
- ZIP outputは禁止です。
- Discord / MT5 / AI API / live hook / live evaluator / final signal はOFFです。
- APPROVE_FOR_NEXT_AUDIT_ONLY_REPLAY はfinal承認でもlive承認でもありません。
- REQUEST_MORE_AUDIT は承認ではありません。
- 旧GOLD/DISC8は隔離継続です。
- GOLD V2 artifactは参照禁止です。Stage 14では使用しないでください。

13 outputsを確認して、14のspec/script/BATを作ってください。
ただし、replay実行はまだしないでください。
```
