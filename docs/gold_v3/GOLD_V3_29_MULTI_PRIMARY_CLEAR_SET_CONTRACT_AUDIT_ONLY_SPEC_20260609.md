# GOLD V3 29 multi-primary clear set contract audit-only spec

Created: 2026-06-09

Status: `GOLD_V3_29_MULTI_PRIMARY_CLEAR_SET_CONTRACT_SPEC_READY_AUDIT_ONLY`

## Purpose

GOLD V3 29 corrects the Stage28 over-narrowing.

The user explicitly allows multiple candidates. Therefore the Stage26 CLEAR bundle should be treated as a multi-primary audit candidate set, not as a single winner.

CLEAR set:

```text
R1_ONLY_CD60_PRUNE_111
R1_ONLY_CD60_PRUNE_115
MAIN_R1_R2_CD120_PRUNE_122
```

This is audit-only. It is not live approval.

## Required upstream

```text
GOLD_V3_26_CLEAR_PACKET_VALIDATION_BUNDLE_READY_AUDIT_ONLY
GOLD_V3_27_CLEAR_BUNDLE_PAIRWISE_REVIEW_READY_AUDIT_ONLY
GOLD_V3_28_PRIMARY_REVIEW_FILTER_CONTRACT_READY_AUDIT_ONLY
```

## Required inputs

```text
Files/FX_OUTPUTS/gold_v3/26_clear_packet_validation_bundle_audit_only/gold_v3_26_summary.json
Files/FX_OUTPUTS/gold_v3/26_clear_packet_validation_bundle_audit_only/gold_v3_26_clear_validation_bundle.csv
Files/FX_OUTPUTS/gold_v3/26_clear_packet_validation_bundle_audit_only/gold_v3_26_clear_filter_traceability.csv
Files/FX_OUTPUTS/gold_v3/27_clear_bundle_pairwise_review_audit_only/gold_v3_27_rank_proposal.csv
Files/FX_OUTPUTS/gold_v3/28_primary_review_filter_contract_audit_only/gold_v3_28_summary.json
```

## Output directory

```text
Files/FX_OUTPUTS/gold_v3/29_multi_primary_clear_set_contract_audit_only/
```

## Outputs

```text
gold_v3_29_summary.json
gold_v3_29_input_inventory.csv
gold_v3_29_multi_primary_contract.csv
gold_v3_29_multi_primary_metrics.csv
gold_v3_29_candidate_role_matrix.csv
gold_v3_29_review_matrix.csv
gold_v3_29_blocker_matrix.csv
GOLD_V3_29_MULTI_PRIMARY_CLEAR_SET_CONTRACT_AUDIT_ONLY_REPORT.md
```

## Set role policy

```text
R1_ONLY_CD60_PRUNE_111 -> MULTI_PRIMARY_SET
R1_ONLY_CD60_PRUNE_115 -> MULTI_PRIMARY_SET
MAIN_R1_R2_CD120_PRUNE_122 -> MULTI_PRIMARY_SET_COMPARE
```

The role names do not enable production behavior. They only preserve the fact that multiple strong candidates can continue together.

## Ready status

```text
GOLD_V3_29_MULTI_PRIMARY_CLEAR_SET_CONTRACT_READY_AUDIT_ONLY
```

## Safety

Audit-only. No switching rule, no month filter, no daily cap, no production behavior.
