# GOLD V3 14 human ranking decision intake audit-only spec

Created: 2026-06-09

Status: `GOLD_V3_14_HUMAN_RANKING_DECISION_INTAKE_SPEC_READY_AUDIT_ONLY`

## Purpose

GOLD V3 14 accepts human decisions for the GOLD V3 13 proxy-ranked rule candidates and prepares an audit-only replay-plan preview for rows explicitly marked:

```text
APPROVE_FOR_NEXT_AUDIT_ONLY_REPLAY
```

This stage is an intake and planning stage only.

It does **not** execute replay, approve final candidates, finalize thresholds, train models, generate signals, create ZIP output, call AI APIs, notify Discord, place MT5 orders, enable live hooks/evaluators, or create final signals.

## Current upstream

Stage 14 requires the completed Stage 13 status:

```text
GOLD_V3_13_RANKING_DECISION_TEMPLATE_READY_AUDIT_ONLY
```

Stage 13 ranking values are proxy-only. They are not true PF, true win rate, or true trades per day.

## Quarantine boundary

Stage 14 must use only GOLD V3 Stage 13 outputs as source-of-truth inputs.

GOLD V2, old GOLD, DISC8, and related legacy artifacts remain quarantined and must not be read, imported, compared, merged, recovered from, copied from, backfilled from, used as fallback, used as validation, used as replay input, used as feature source, used as rule source, used as candidate source, or used as source-of-truth.

The only acceptable legacy-related fields in Stage 14 outputs are safety flags confirming that quarantined artifacts were not used.

## Required inputs

Stage 14 reads these Stage 13 outputs from the selected GOLD V3 output root:

```text
Files/FX_OUTPUTS/gold_v3/13_ranking_decision_template_audit_only/gold_v3_13_summary.json
Files/FX_OUTPUTS/gold_v3/13_ranking_decision_template_audit_only/gold_v3_13_decision_template.csv
Files/FX_OUTPUTS/gold_v3/13_ranking_decision_template_audit_only/gold_v3_13_ranked_rule_candidate_rows.csv
Files/FX_OUTPUTS/gold_v3/13_ranking_decision_template_audit_only/gold_v3_13_ranked_candidate_family_groups.csv
Files/FX_OUTPUTS/gold_v3/13_ranking_decision_template_audit_only/gold_v3_13_deferred_narrowing_candidates.csv
Files/FX_OUTPUTS/gold_v3/13_ranking_decision_template_audit_only/gold_v3_13_blocker_matrix.csv
```

Expected input checks:

```text
gold_v3_13_summary.status == GOLD_V3_13_RANKING_DECISION_TEMPLATE_READY_AUDIT_ONLY
gold_v3_13_ranked_rule_candidate_rows rows == 8
gold_v3_13_decision_template rows == 8
gold_v3_13_ranked_candidate_family_groups rows == 4
gold_v3_13_summary.human_decision_required == true
```

## Optional human decision input

The runtime supports two intake modes:

1. First run / blank template mode:
   - If no Stage 14 intake template exists and no `--human-decision-input` is supplied, Stage 14 copies Stage 13 pending decision rows into a Stage 14 intake template.
   - This is expected to remain `INPUT_REVIEW_REQUIRED` because no human decision has been provided yet.

2. Edited decision mode:
   - The user edits `gold_v3_14_human_decision_intake_template.csv` and reruns the script, or passes a CSV path via `--human-decision-input`.
   - The script validates `human_decision` values and prepares a replay-plan preview for approved-for-replay rows.

Allowed human decisions:

```text
APPROVE_FOR_NEXT_AUDIT_ONLY_REPLAY
REJECT
REQUEST_MORE_AUDIT
```

`APPROVE_FOR_NEXT_AUDIT_ONLY_REPLAY` is not final approval and not live approval.

`REQUEST_MORE_AUDIT` is not approval.

Blank, `PENDING`, `PENDING_REVIEW`, or `PENDING_HUMAN_REVIEW` values are treated as pending human review.

## Output directory

The runtime must write to:

```text
Files/FX_OUTPUTS/gold_v3/14_human_ranking_decision_intake_audit_only/
```

The script follows the repaired Stage 13 output-root convention:

1. Prefer the existing GOLD V3 output root that already contains Stage 13 outputs.
2. Fall back to the legacy repo-root `Files/FX_OUTPUTS/gold_v3` path only if no existing Stage 13 output root is found.

The output directory must be created with:

```python
output_dir.mkdir(parents=True, exist_ok=True)
```

## Required outputs

The script must always write these files, including when inputs are missing, invalid, or an exception occurs:

```text
gold_v3_14_summary.json
gold_v3_14_input_inventory.csv
gold_v3_14_human_decision_intake_template.csv
gold_v3_14_replay_plan_preview.csv
gold_v3_14_decision_matrix.csv
gold_v3_14_blocker_matrix.csv
GOLD_V3_14_HUMAN_RANKING_DECISION_INTAKE_AUDIT_ONLY_REPORT.md
```

Exception runs may additionally write:

```text
gold_v3_14_exception.txt
```

ZIP output is disabled.

## Human decision intake template fields

The Stage 14 template preserves Stage 13 candidate context and adds explicit validation status:

```text
rank
source_packet_row_number
candidate_group_id
profile_id
direction
feature_column
rule_expression_preview
readiness_label
risk_flags
recommended_review_bucket
same_condition_overlap
same_condition_overlap_note
ranking_is_proxy_only
estimated_trades_per_day_proxy
estimated_trades_per_day_source
pf_winrate_priority_score_proxy
narrowing_potential_score_proxy
human_decision
allowed_decisions
human_note
reviewer
reviewed_at_utc
decision_validation_status
decision_validation_detail
approval_semantics
```

The `*_proxy` suffixes are deliberate. Stage 13 ranking values must not be treated as final replay metrics.

## Replay-plan preview

The replay-plan preview contains only rows whose validated `human_decision` is:

```text
APPROVE_FOR_NEXT_AUDIT_ONLY_REPLAY
```

Replay-plan preview rows are planning records only. Stage 14 must not execute replay.

Each preview row must include:

```text
replay_execution_allowed_in_stage14 = False
required_next_stage = separate explicit audit-only replay execution instruction required
true_metrics_to_recompute = true trade frequency; true win rate; true PF; drawdown; execution behavior; fold/date stability
```

## Candidate family rule

The 8 Stage 13 rows are rule candidates, not individual trade points.

`GROUP_H1_ATR56_HIGH_VOL` contains multiple TP/SL/horizon profiles sharing the same entry condition:

```text
h1_atr56 >= 9.95812
```

These rows must not be counted as independent entry ideas. Stage 14 deduplicates approved entry families by candidate group, direction, feature, and rule expression, while still preserving profile-level rows for later replay comparison.

## Status values

Use this status only when all required Stage 13 inputs are valid, at least one non-pending valid human decision has been supplied, and the intake template / replay-plan preview / matrices / report have been written:

```text
GOLD_V3_14_HUMAN_RANKING_DECISION_INTAKE_READY_AUDIT_ONLY
```

Use this status when Stage 13 inputs are valid but human decisions are missing, pending, or invalid:

```text
GOLD_V3_14_HUMAN_RANKING_DECISION_INTAKE_INPUT_REVIEW_REQUIRED_AUDIT_ONLY
```

Use this status when required inputs are missing or upstream row/status checks fail:

```text
GOLD_V3_14_HUMAN_RANKING_DECISION_INTAKE_BLOCKED_AUDIT_ONLY
```

Use this status if an unhandled exception occurs after the script starts:

```text
GOLD_V3_14_HUMAN_RANKING_DECISION_INTAKE_EXCEPTION_AUDIT_ONLY
```

## Blocker matrix

Stage 14 blocker logic:

```text
G3-14-001 stage-13 inputs: CLOSED only if required Stage 13 files exist and Stage 13 status is READY
G3-14-002 stage-13 row counts: CLOSED only if ranked rows = 8, decision template rows = 8, family rows = 4
G3-14-003 human decision intake: CLOSED only if at least one valid non-pending human decision is present; otherwise OPEN_HUMAN_ACTION_REQUIRED or OPEN_INVALID_HUMAN_DECISION
G3-14-004 approval semantics: CLOSED; APPROVE_FOR_NEXT_AUDIT_ONLY_REPLAY is not final/live approval and REQUEST_MORE_AUDIT is not approval
G3-14-005 replay plan preview: CLOSED only when inputs and decision validation are clean; preview only
G3-14-006 replay execution: CLOSED_BLOCKED_BY_POLICY
G3-14-007 final approval: CLOSED_BLOCKED_BY_POLICY
G3-14-008 threshold finalization: CLOSED_BLOCKED_BY_POLICY
G3-14-009 model training: CLOSED_BLOCKED_BY_POLICY
G3-14-010 signal/live: CLOSED_BLOCKED_BY_POLICY
G3-14-011 zip output: CLOSED_DISABLED
G3-14-012 external actions: CLOSED
G3-14-013 quarantined legacy artifacts: CLOSED only if Stage 14 reads only GOLD V3 Stage 13 outputs
```

## Safety flags

Every summary must keep these false:

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
quarantined_legacy_artifacts_read = false
gold_v2_live_sot_used = false
```

## Runtime script

```text
scripts/gold_v3_runtime/gold_v3_14_human_ranking_decision_intake_audit_only.py
```

CLI:

```text
python scripts/gold_v3_runtime/gold_v3_14_human_ranking_decision_intake_audit_only.py --repo-root <repo-root>
python scripts/gold_v3_runtime/gold_v3_14_human_ranking_decision_intake_audit_only.py --repo-root <repo-root> --human-decision-input <csv>
```

## BAT contract

The BAT must be placed under:

```text
scripts/gold_v3_runtime/bat/GOLD_V3_14_HUMAN_RANKING_DECISION_INTAKE_AUDIT_ONLY.bat
```

Because the BAT is under `scripts/gold_v3_runtime/bat/`, it must return to repo root with:

```bat
cd /d "%~dp0\..\..\.."
```

It must run:

```bat
python scripts\gold_v3_runtime\gold_v3_14_human_ranking_decision_intake_audit_only.py
```

or `py -3` fallback with the same script path.

The BAT must not call replay, training, signal, Discord, MT5, AI API, live hook, live evaluator, final signal, or ZIP processes.

## Success conditions

Stage 14 implementation is acceptable when:

```text
the spec exists at docs/gold_v3/GOLD_V3_14_HUMAN_RANKING_DECISION_INTAKE_AUDIT_ONLY_SPEC_20260609.md
the script exists at scripts/gold_v3_runtime/gold_v3_14_human_ranking_decision_intake_audit_only.py
the BAT exists at scripts/gold_v3_runtime/bat/GOLD_V3_14_HUMAN_RANKING_DECISION_INTAKE_AUDIT_ONLY.bat
the script creates the output directory with parents=True, exist_ok=True
the script writes all required output files even when inputs are missing
the script reads only Stage 13 GOLD V3 outputs as source-of-truth
the script does not execute replay
the script does not approve final candidates
the script does not finalize thresholds
the script does not train models
the script does not generate signals
the script does not create ZIP output
the script does not call AI API / Discord / MT5 / live hook / live evaluator / final signal
```

## Next action after this stage

After Stage 14 is run locally and a human decision CSV has been provided, the next stage may prepare a separate audit-only replay execution stage only if the user explicitly instructs it.

That later instruction is still not final approval, not live approval, and not threshold finalization.
