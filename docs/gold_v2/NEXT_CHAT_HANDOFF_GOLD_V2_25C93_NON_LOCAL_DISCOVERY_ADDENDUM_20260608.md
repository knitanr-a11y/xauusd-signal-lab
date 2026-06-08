# NEXT CHAT HANDOFF ADDENDUM - GOLD V2 25C93 non-local / chat-side discovery notes

Created: 2026-06-08

Repo: `knitanr-a11y/xauusd-signal-lab`

## Why this addendum exists

The main handoff:

```text
docs/gold_v2/NEXT_CHAT_HANDOFF_GOLD_V2_25C93_DONE_25C94_NEXT_NON_ORACLE_SELECTOR_REVIEW_AUDIT_ONLY_20260608.md
```

contains the current state and next step. This addendum captures information that may not exist in the user's local working tree unless GitHub has been pulled, plus discoveries made in the chat-side recovery path.

The next chat should read both the main handoff and this addendum.

## Guardrails repeated

- GOLD V2 remains audit-only.
- `REQUEST_MORE_AUDIT` is not source recovery approval.
- Old GOLD/DISC8 remains quarantined due suspected HTF open-time mismatch.
- Approximate reimplementation is prohibited.
- A002 is auxiliary-only and must not be used for CoreB metrics.
- Discord / MT5 / AI API / live hook / live evaluator / final signal remain OFF unless explicitly approved.
- NO_SIGNAL must not notify Discord.
- Do not treat non-local/chat-side exploration as live-ready source recovery.

## GitHub-only files added during this chat

These files were added through GitHub directly. A local checkout may not contain them until pulled.

### 25C84

```text
docs/gold_v2/GOLD_V2_25C84_DEEP_CLUSTER_REPRESENTATIVE_RECONSTRUCTION_AUDIT_ONLY_SPEC_20260608.md
scripts/gold_v2_runtime/audit_gold_v2_25c84_deep_cluster_representative_reconstruction_audit_only.py
scripts/gold_v2_runtime/bat/25C84_DEEP_CLUSTER_REPRESENTATIVE_RECONSTRUCTION_AUDIT_ONLY.bat
```

Purpose: broad numerical reconstruction search using time windows, candidate/origin mapping, profit aggregations, cluster-id sequence hypotheses, and repository keyword scan.

Result: no full reconstruction.

### 25C85

```text
docs/gold_v2/GOLD_V2_25C85_LOCAL_SOURCE_CANDIDATE_CONTENT_REVIEW_AUDIT_ONLY_SPEC_20260608.md
scripts/gold_v2_runtime/audit_gold_v2_25c85_local_source_candidate_content_review_audit_only.py
scripts/gold_v2_runtime/bat/25C85_LOCAL_SOURCE_CANDIDATE_CONTENT_REVIEW_AUDIT_ONLY.bat
```

Purpose: inspect local candidate files from 25C84 keyword scan and classify whether they contain actual raw-to-top generator logic.

Result: no true generator found; partial configs/scripts found.

Important local partial candidates from 25C85:

```text
configs/gold_v2/frozen_coreB_combined_evaluator_definition_20260604.json
configs/gold_v2/frozen_coreB_same_count_source_universe_20260604.json
scripts/gold_v2_runtime/audit_gold_v2_13c2_coreb_source_ledger_to_feature_snapshot_parity_audit_only.py
scripts/gold_v2_runtime/audit_gold_v2_13c3_coreb_reconstruct_source_cluster_membership_audit_only.py
```

### 25C86

```text
docs/gold_v2/GOLD_V2_25C86_FROZEN_SAME_COUNT_CONDITION_REPLAY_AUDIT_ONLY_SPEC_20260608.md
scripts/gold_v2_runtime/audit_gold_v2_25c86_frozen_same_count_condition_replay_audit_only.py
scripts/gold_v2_runtime/bat/25C86_FROZEN_SAME_COUNT_CONDITION_REPLAY_AUDIT_ONLY.bat
```

Purpose: test whether same_count equals count of fully passing frozen source rules on feature snapshot rows.

Result: not matched.

Important condition inventory observed:

```text
selected_csv: 65 conditions / 12 rules
same_count_csv: 181 conditions / 33 rules
selected_json: 106 conditions / 12 rules
same_count_json: 296 conditions / 33 rules
```

### 25C87

```text
docs/gold_v2/GOLD_V2_25C87_CONDITION_OBJECT_AND_TIME_ALIGNMENT_REPLAY_AUDIT_ONLY_SPEC_20260608.md
scripts/gold_v2_runtime/audit_gold_v2_25c87_condition_object_and_time_alignment_replay_audit_only.py
scripts/gold_v2_runtime/bat/25C87_CONDITION_OBJECT_AND_TIME_ALIGNMENT_REPLAY_AUDIT_ONLY.bat
```

Purpose: test individual condition-object hit counts and feature time offsets.

Result: not matched.

Best result:

```text
best_exact_rows = 4 / 125
best_non_null_predictions = 91 / 125
```

### 25C88

```text
docs/gold_v2/GOLD_V2_25C88_SOURCE_UNIVERSE_FILTERED_COMPONENT_RECONSTRUCTION_AUDIT_ONLY_SPEC_20260608.md
scripts/gold_v2_runtime/audit_gold_v2_25c88_source_universe_filtered_component_reconstruction_audit_only.py
scripts/gold_v2_runtime/bat/25C88_SOURCE_UNIVERSE_FILTERED_COMPONENT_RECONSTRUCTION_AUDIT_ONLY.bat
```

Purpose: filter raw rows by independent source-universe IDs/values, then build interval components.

Result: not matched.

Important observation:

```text
best_mode = all_rr125_raw_baseline
best_same_count_exact = 10 / 125
best_source_rule_count_exact = 10 / 125
```

All independent value filters effectively retained the same broad RR125 raw universe.

### 25C89

```text
docs/gold_v2/GOLD_V2_25C89_SOURCE_UNIVERSE_RULE_TUPLE_MEMBERSHIP_AUDIT_ONLY_SPEC_20260608.md
scripts/gold_v2_runtime/audit_gold_v2_25c89_source_universe_rule_tuple_membership_audit_only.py
scripts/gold_v2_runtime/bat/25C89_SOURCE_UNIVERSE_RULE_TUPLE_MEMBERSHIP_AUDIT_ONLY.bat
```

Purpose: filter raw rows by source-universe rule tuples instead of independent sets.

Result: not matched.

Important observation:

```text
source_rule_rows = 66
best_mode = added_filter_text
best_same_count_exact = 10 / 125
best_source_rule_count_exact = 10 / 125
```

### 25C90

```text
docs/gold_v2/GOLD_V2_25C90_BASE_CONDITION_RULE_MEMBERSHIP_AUDIT_ONLY_SPEC_20260608.md
scripts/gold_v2_runtime/audit_gold_v2_25c90_base_condition_rule_membership_audit_only.py
scripts/gold_v2_runtime/bat/25C90_BASE_CONDITION_RULE_MEMBERSHIP_AUDIT_ONLY.bat
```

Purpose: add `base_condition` normalization to source-universe membership tests.

Result: not matched.

Important observation:

```text
source_rule_rows = 33
best_mode = base_condition_norm
best_style = interval_component
best_same_count_exact = 10 / 125
best_source_rule_count_exact = 10 / 125
```

### 25C91

```text
docs/gold_v2/GOLD_V2_25C91_RAW_CLUSTER_PARAMETER_SWEEP_AUDIT_ONLY_SPEC_20260608.md
scripts/gold_v2_runtime/audit_gold_v2_25c91_raw_cluster_parameter_sweep_audit_only.py
scripts/gold_v2_runtime/bat/25C91_RAW_CLUSTER_PARAMETER_SWEEP_AUDIT_ONLY.bat
```

Purpose: raw-only cluster parameter sweep over entry-gap, interval-gap, and calendar-bucket families.

Result: not matched, but strongest non-oracle precursor.

Important observation:

```text
best_family = entry_gap
best_gap_min = 15
best_same_count_exact = 66 / 125
best_source_rule_count_exact = 66 / 125
```

### 25C92

```text
docs/gold_v2/GOLD_V2_25C92_NEARBY_COMPONENT_ORACLE_BOUNDARY_AUDIT_ONLY_SPEC_20260608.md
scripts/gold_v2_runtime/audit_gold_v2_25c92_nearby_component_oracle_boundary_audit_only.py
scripts/gold_v2_runtime/bat/25C92_NEARBY_COMPONENT_ORACLE_BOUNDARY_AUDIT_ONLY.bat
```

Purpose: oracle boundary test to determine whether correct components exist among covering/nearby components.

Result:

```text
NEARBY_COMPONENT_ORACLE_FULL_COUNT_FOUND_AUDIT_ONLY_NOT_LIVE_LOGIC
```

Important observation:

```text
family = entry_gap
gap_min = 15
nearby_min = 0
same_count_oracle_exact = 125 / 125
source_rule_count_oracle_exact = 125 / 125
unique_origins_oracle_exact = 125 / 125
```

Interpretation: component generation is close; the remaining issue is non-oracle selector / representative binding. Oracle matching is not live logic.

### 25C93

```text
docs/gold_v2/GOLD_V2_25C93_NON_ORACLE_COMPONENT_SELECTOR_AUDIT_ONLY_SPEC_20260608.md
scripts/gold_v2_runtime/audit_gold_v2_25c93_non_oracle_component_selector_audit_only.py
scripts/gold_v2_runtime/bat/25C93_NON_ORACLE_COMPONENT_SELECTOR_AUDIT_ONLY.bat
```

Purpose: test non-oracle component selectors over `entry_gap=15m` covering components.

Result:

```text
NON_ORACLE_COMPONENT_SELECTOR_CANDIDATE_FOUND_AUDIT_ONLY_HUMAN_REVIEW_REQUIRED_LIVE_BLOCKED
```

Important observation:

```text
latest_start:
  selected_rows = 125 / 125
  same_count_exact = 125 / 125
  source_rule_count_exact = 125 / 125
  unique_origins_exact = 125 / 125
  profit_sum_exact = 0 / 125
  status = FULL

closest_start:
  selected_rows = 125 / 125
  same_count_exact = 125 / 125
  source_rule_count_exact = 125 / 125
  unique_origins_exact = 125 / 125
  profit_sum_exact = 0 / 125
  status = FULL
```

This is the main discovery to carry forward.

## Important interpretation updates from non-local discovery

### 1. same_count is not raw entry group count

Repeated attempts show same_count is not explained by:

```text
same entry_time raw row count
same entry_time + RR/policy count
time-window count
feature rule pass count
condition object pass count
source-universe independent filter count
source-universe rule tuple count
base_condition tuple count
```

### 2. entry_gap=15m is the key recovered component family

The strongest recovered structure is:

```text
raw_rr125_rows = 6834
component family = entry_gap
component gap = 15 minutes
```

This does not by itself select the correct component for every row, but the correct component is present among covering components for every top row.

### 3. latest_start / closest_start are the first full non-oracle count selectors

The first full non-oracle component count match occurs at 25C93:

```text
entry_gap=15m
selector=latest_start or closest_start
same_count/source_rule_count/unique_origins = 125/125
```

This is a candidate requiring human review, not approval.

### 4. representative profit remains unresolved

Even though count fields match, component profit aggregation does not match:

```text
profit_sum_exact = 0 / 125
```

Do not claim full CoreB live replay until representative profit/top_candidate binding is solved.

## Most likely next technical direction

The next step is not another broad count search. It should focus on representative profit binding after selected component recovery:

```text
25C94_NON_ORACLE_SELECTOR_CANDIDATE_REVIEW_AUDIT_ONLY
```

Recommended 25C94 logic:

1. Rebuild `entry_gap=15m` components.
2. For each CoreB top row, select component via `latest_start` and `closest_start`.
3. Confirm both selectors select the same component for all rows.
4. Within the selected component, test representative row/profit selectors:
   - `candidate_id == top_candidate_id`
   - `origin_id == top_candidate_id`
   - candidate/origin contains top_candidate_id
   - latest raw entry within component
   - earliest raw entry within component
   - max profit raw row
   - min profit raw row
   - max/min/median/mean/sum profit aggregations
   - top row's stored `profit` as selected representative value
5. Compare representative profit against top `profit` for all 125 rows.
6. If representative profit fails, CoreB remains historical SOT / live blocked.
7. If representative profit succeeds, still require human review before live evaluator.

## Recommended next prompt addition

Add this line to the next-chat prompt:

```text
Also read docs/gold_v2/NEXT_CHAT_HANDOFF_GOLD_V2_25C93_NON_LOCAL_DISCOVERY_ADDENDUM_20260608.md because it contains GitHub-only and chat-side recovery findings that may not be in the local working tree.
```

## Current next-chat prompt, updated

```text
repo: knitanr-a11y/xauusd-signal-lab

Please read and continue from:
docs/gold_v2/NEXT_CHAT_HANDOFF_GOLD_V2_25C93_DONE_25C94_NEXT_NON_ORACLE_SELECTOR_REVIEW_AUDIT_ONLY_20260608.md
docs/gold_v2/NEXT_CHAT_HANDOFF_GOLD_V2_25C93_NON_LOCAL_DISCOVERY_ADDENDUM_20260608.md

GOLD V2 remains audit-only.
REQUEST_MORE_AUDIT is not source recovery approval.
Old GOLD/DISC8 remains quarantined due suspected HTF open-time mismatch.
Approximate reimplementation is prohibited.
A002 is auxiliary-only and must not be used for CoreB metrics.
Discord / MT5 / AI API / live hook / live evaluator / final signal remain OFF unless explicitly approved.
NO_SIGNAL must not notify Discord.

25C93 found a non-oracle selector candidate:
- component_family = entry_gap
- gap_min = 15
- best selectors = latest_start and closest_start
- same_count/source_rule_count/unique_origins exact = 125/125
- profit_sum exact = 0/125
- status = NON_ORACLE_COMPONENT_SELECTOR_CANDIDATE_FOUND_AUDIT_ONLY_HUMAN_REVIEW_REQUIRED_LIVE_BLOCKED

Next step:
25C94_NON_ORACLE_SELECTOR_CANDIDATE_REVIEW_AUDIT_ONLY

Goal:
Review whether latest_start/closest_start are stable and recover representative profit/top_candidate_id binding without oracle logic. Do not unlock live.
```
