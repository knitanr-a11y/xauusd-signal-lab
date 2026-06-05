# GOLD V2 14A CoreB cluster source reconstruction audit-only spec

Created: 2026-06-05

## Purpose

CoreB remains live-blocked because the original `cluster_id` / `same_direction_count` source chain has not been reconstructed.

14A is a source-locator audit. It does not rebuild the CoreB evaluator yet.

## Scope

Search local repository scripts/docs and targeted FX_OUTPUTS folders for CoreB cluster-source evidence.

Priority targets:

```text
FX_OUTPUTS/gold_v2_coreb_refined_probe_outputs
FX_OUTPUTS/gold_v2_rr125_second_core_probe_outputs
scripts/gold_v2_runtime
docs/gold_v2
```

## Evidence to locate

```text
cluster_id
same_direction_count
same_count
top_candidate_id
top_variant
component
CoreB / coreb / rr125 / refined
```

## Outputs

```text
Files/FX_OUTPUTS/gold_v2_14a_coreb_cluster_source_reconstruction_audit_only
```

```text
GOLD_V2_14A_COREB_CLUSTER_SOURCE_RECONSTRUCTION_AUDIT_ONLY_REPORT.md
gold_v2_14a_input_audit.csv
gold_v2_14a_csv_file_inventory.csv
gold_v2_14a_cluster_column_inventory.csv
gold_v2_14a_code_keyword_hits.csv
gold_v2_14a_coreb_candidate_scores.csv
gold_v2_14a_decision_matrix.csv
gold_v2_14a_blockers.csv
gold_v2_14a_coreb_cluster_source_reconstruction_summary.json
```

## Expected status

```text
COREB_CLUSTER_SOURCE_CANDIDATES_FOUND_AUDIT_ONLY
```

or, if evidence is incomplete:

```text
COREB_CLUSTER_SOURCE_CANDIDATES_PARTIAL_AUDIT_ONLY
```

## Prohibitions

No Discord, no MT5, no AI API, no live hook, no final signal, no live enablement.
