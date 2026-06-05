# GOLD V2 14D CoreB original clustering candidate review audit-only spec

Created: 2026-06-05

## Purpose

14C safely froze CoreB as historical-only. 14D reviews whether any candidate file is a real original clustering generator that can produce `cluster_id` and `same_count` from raw RR125 signals.

This step is stricter than keyword search. Files that only read `rr125_top_ledgers.csv` are not accepted as live algorithms.

## Inputs

```text
FX_OUTPUTS/gold_v2_14c_coreb_historical_sot_candidate_mapping_audit_only/gold_v2_14c_coreb_historical_sot_candidate_mapping_summary.json
FX_OUTPUTS/gold_v2_13c5_coreb_review_restored_clustering_script_parity_audit_only/gold_v2_13c5_review_restored_clustering_script_parity_summary.json
repo scripts/docs scan
```

## Strict live-candidate criteria

A true original clustering candidate must be a Python file that:

```text
reads raw RR125 signal ledger
assigns cluster_id
assigns same_count
has groupby or equivalent membership construction
writes or constructs top-ledger output
is not a generated audit/freeze helper
```

## Outputs

```text
FX_OUTPUTS/gold_v2_14d_coreb_original_clustering_candidate_review_audit_only
```

## Expected status

Most likely safe status:

```text
COREB_ORIGINAL_CLUSTERING_CANDIDATE_NOT_CONFIRMED_LIVE_BLOCKED_AUDIT_ONLY
```

If a strict original candidate is found, it must still go to replay parity before live use.

## Prohibitions

No Discord, no MT5, no AI API, no live hook, no final signal, no CoreB live enablement.
