# GOLD V3 28 primary review filter contract audit-only spec

Created: 2026-06-09

Status: `GOLD_V3_28_PRIMARY_REVIEW_FILTER_CONTRACT_SPEC_READY_AUDIT_ONLY`

## Purpose

GOLD V3 28 converts the Stage27 primary review row into a compact filter contract packet.

Primary review row:

```text
R1_ONLY_CD60_PRUNE_111__R1_ONLY_CD60_PRUNE_111_S021__R1_ONLY_CD60_PRUNE_111_S022
```

This is audit-only. It is not a production rule and not a final signal.

## Required upstream

```text
GOLD_V3_27_CLEAR_BUNDLE_PAIRWISE_REVIEW_READY_AUDIT_ONLY
```

## Required inputs

```text
Files/FX_OUTPUTS/gold_v3/27_clear_bundle_pairwise_review_audit_only/gold_v3_27_summary.json
Files/FX_OUTPUTS/gold_v3/27_clear_bundle_pairwise_review_audit_only/gold_v3_27_rank_proposal.csv
Files/FX_OUTPUTS/gold_v3/27_clear_bundle_pairwise_review_audit_only/gold_v3_27_filter_delta_review.csv
Files/FX_OUTPUTS/gold_v3/26_clear_packet_validation_bundle_audit_only/gold_v3_26_clear_validation_bundle.csv
Files/FX_OUTPUTS/gold_v3/26_clear_packet_validation_bundle_audit_only/gold_v3_26_clear_filter_traceability.csv
```

## Output directory

```text
Files/FX_OUTPUTS/gold_v3/28_primary_review_filter_contract_audit_only/
```

## Outputs

```text
gold_v3_28_summary.json
gold_v3_28_input_inventory.csv
gold_v3_28_primary_filter_contract.csv
gold_v3_28_primary_candidate_metrics.csv
gold_v3_28_comparison_rows.csv
gold_v3_28_review_matrix.csv
gold_v3_28_blocker_matrix.csv
GOLD_V3_28_PRIMARY_REVIEW_FILTER_CONTRACT_AUDIT_ONLY_REPORT.md
```

## Ready status

```text
GOLD_V3_28_PRIMARY_REVIEW_FILTER_CONTRACT_READY_AUDIT_ONLY
```

## Safety

Audit-only. No switching rule, no month filter, no daily cap, no production behavior.
