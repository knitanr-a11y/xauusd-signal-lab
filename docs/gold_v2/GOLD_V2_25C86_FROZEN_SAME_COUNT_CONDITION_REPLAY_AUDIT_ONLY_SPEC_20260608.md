# GOLD V2 25C86 frozen same-count condition replay audit-only spec

Created: 2026-06-08

Status: `FROZEN_SAME_COUNT_CONDITION_REPLAY_SPEC_READY_AUDIT_ONLY`

## Purpose

25C84 showed raw row-count / time-window approaches do not reproduce CoreB `same_count` or representative profit.

25C85 showed local partial logic/configs exist, especially:

```text
configs/gold_v2/frozen_coreB_combined_evaluator_definition_20260604.json
configs/gold_v2/frozen_coreB_same_count_source_universe_20260604.json
scripts/gold_v2_runtime/audit_gold_v2_13c2_coreb_source_ledger_to_feature_snapshot_parity_audit_only.py
```

25C86 tests the next most likely interpretation:

```text
same_count = number of frozen same-count source rules that pass on the feature snapshot row
```

This is still audit-only and does not approve live use.

## Inputs

The script resolves locally from repository root and `Files/FX_OUTPUTS`:

```text
25c85_summary.json
rr125_top_ledgers.csv
gold_v2_13c_coreb_rr125_selected_top_ledgers.csv
frozen_coreB_combined_evaluator_definition_20260604.json
frozen_coreB_same_count_source_universe_20260604.json
frozen_coreB_rr125_source_rule_conditions_20260603.json
gold_v2_coreb_combined_required_feature_snapshot.csv
gold_v2_coreb_combined_selected_conditions.csv
gold_v2_coreb_combined_same_count_conditions.csv
```

CSV condition files are preferred if present. JSON config condition objects are used as fallback.

## Replay logic

For each feature snapshot row:

```text
selected_rule_hit_count = count of selected rules where all conditions pass
same_count_source_hit_count = count of same-count source rules where all conditions pass
```

For CoreB top 125 rows, join by:

```text
entry_time == feature_snapshot time
```

Then compare:

```text
same_count_source_hit_count vs top.same_count
same_count_source_hit_count vs top.source_rule_count
```

## Success definition

A meaningful replay candidate requires:

```text
125 / 125 exact same_count or source_rule_count match
```

If successful, status must still require human review before any live step:

```text
FROZEN_SAME_COUNT_CONDITION_REPLAY_MATCHED_TOP125_AUDIT_ONLY_HUMAN_REVIEW_REQUIRED_LIVE_BLOCKED
```

If not matched:

```text
FROZEN_SAME_COUNT_CONDITION_REPLAY_NOT_MATCHED_AUDIT_ONLY_LIVE_BLOCKED
```

## Guardrails

- Do not use A002.
- Do not approve source recovery.
- Do not enable live evaluator.
- No Discord/MT5/AI/live/final actions.
