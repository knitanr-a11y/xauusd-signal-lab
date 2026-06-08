# GOLD V2 25C111 CoreA/MEDIUM time-ID ablation audit-only spec

Created: 2026-06-09

Status: `COREA_MEDIUM_TIME_ID_ABLATION_SPEC_READY_AUDIT_ONLY`

## Purpose

25C110 found that CoreA and MEDIUM selected rows map uniquely to their source universe when using the current entry-time signature:

```text
status = COREA_MEDIUM_ENTRYTIME_SELECTION_UNIQUE_CANDIDATE_AUDIT_ONLY_HUMAN_REVIEW_REQUIRED_LIVE_BLOCKED
CoreA selected_rows = 325, unique matches = 325
MEDIUM selected_rows = 87, unique matches = 87
```

However, the 25C110 signature includes possible historical identifiers/time keys such as:

```text
top_entry_time
entry_time
cluster_id
fold_id
entry_month
test_month
cluster_start
cluster_end
```

25C111 ablates time and id-like columns from the 25C110 signature and reruns the same selected-vs-universe contrast. This checks whether 25C110 uniqueness was genuine entry-time rule reproducibility or merely row/time/id memorization.

This is audit-only. It does not replay OHLC and does not implement live logic.

## Inputs

Use local 25C110 outputs:

```text
25c110_summary.json
25c110_pair_inventory.csv
25c110_entry_signature_columns.csv
25c110_entrytime_contrast_summary.csv
```

Required upstream status:

```text
25c110_summary.status = COREA_MEDIUM_ENTRYTIME_SELECTION_UNIQUE_CANDIDATE_AUDIT_ONLY_HUMAN_REVIEW_REQUIRED_LIVE_BLOCKED
```

## Signature variants

For each component, build these signatures from the 25C110 entry_signature_columns list:

```text
full_25c110_signature
no_time_columns
no_time_or_id_columns
feature_only_no_time_id_cluster_month_fold
coarse_feature_family_only
```

### Exclusion groups

Time columns:

```text
entry_time, top_entry_time, cluster_start, cluster_end, close_time, exit_time
```

Month/fold/test identifiers:

```text
entry_month, test_month, fold_id, period, scenario, view
```

ID-like columns:

```text
cluster_id, candidate_id, origin_id, variant_id, rule_id, component_id
unique_same_direction_origins, unique_same_direction_variants, unique_origins_from_members
```

Selection/future/profit columns remain excluded as in 25C110.

### Feature-only columns

Feature-only keeps columns that are plausible live/entry-time features:

```text
atr14, tr_mean_32, range96, range192, trend_eff96, adx14, ret96, regime,
is_A, rr, is_B_rr15_fixed, is_C_fixed, signal_ABC,
same_direction_count, opposite_direction_count,
same_direction_score_sum, opposite_direction_score_sum,
same_direction_count_from_members,
has_opposite_conflict, no_opposite, signal_fixed_ABC, signal, signal_trainC_ABC,
dataset, direction, ruleset, component, component_desc
```

`coarse_feature_family_only` groups numeric columns into coarse bins where possible and keeps categorical strings as-is.

## Metrics

For each component and signature variant:

```text
signature_columns
selected_rows
universe_rows
selected_unique_matches
selected_ambiguous_matches
selected_no_matches
ambiguous_ratio
no_match_ratio
selected_signature_groups
selected_groups_multi_selected
```

## Interpretation

- If full signature is unique but no-time/no-id variants become ambiguous, 25C110 uniqueness is likely dependent on historical row/time/id keys.
- If feature-only remains unique, proceed to a human review of whether the feature set is actually live-computable and not HTF/asof leaking.
- Even feature-only uniqueness does not approve source recovery.

## Outputs

Write to:

```text
Files/FX_OUTPUTS/gold_v2_25c111_corea_medium_time_id_ablation_audit_only
```

Output files:

```text
GOLD_V2_25C111_COREA_MEDIUM_TIME_ID_ABLATION_AUDIT_ONLY_REPORT.md
25c111_summary.json
25c111_pair_inventory.csv
25c111_ablation_summary.csv
25c111_ablation_signature_columns.csv
25c111_ablation_ambiguous_rows.csv
25c111_decision_matrix.csv
25c111_blocker_matrix.csv
```

A zip package may also be written to:

```text
Files/FX_OUTPUTS/gold_v2_25c111_corea_medium_time_id_ablation_audit_only.zip
```

## Status names

If inputs are missing or upstream fails:

```text
COREA_MEDIUM_TIME_ID_ABLATION_INPUT_REVIEW_REQUIRED_AUDIT_ONLY
```

If any component loses uniqueness after no-time/no-id/feature-only ablation:

```text
COREA_MEDIUM_TIME_ID_ABLATION_AMBIGUITY_FOUND_AUDIT_ONLY_LIVE_BLOCKED
```

If both components remain unique through feature-only signatures:

```text
COREA_MEDIUM_FEATURE_ONLY_UNIQUENESS_CANDIDATE_AUDIT_ONLY_HUMAN_REVIEW_REQUIRED_LIVE_BLOCKED
```

Even uniqueness candidate remains audit-only and live blocked.

## Guardrails

- GOLD V2 remains audit-only.
- `REQUEST_MORE_AUDIT` is not source recovery approval.
- Old GOLD/DISC8 remains quarantined due suspected HTF open-time mismatch.
- Approximate reimplementation is prohibited.
- A002 is auxiliary-only and must not be used for CoreB/CoreA/MEDIUM metrics.
- No Discord, MT5, AI API, live hook, live evaluator, or final signal.
- Do not treat feature-only uniqueness as source recovery approval.
