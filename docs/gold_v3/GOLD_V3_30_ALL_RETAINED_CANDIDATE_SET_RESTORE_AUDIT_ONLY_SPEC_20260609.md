# GOLD V3 30 all retained candidate set restore audit-only spec

Created: 2026-06-09

Status: `GOLD_V3_30_ALL_RETAINED_CANDIDATE_SET_RESTORE_SPEC_READY_AUDIT_ONLY`

## Purpose

GOLD V3 30 corrects the over-narrowing that happened after Stage24.

The user allowed multiple candidates. Therefore the Stage24 retained rows must remain as the active audit candidate set. Later robustness flags can be attached, but they must not remove candidates unless the user explicitly asks.

This stage restores all Stage24 retained rows.

## Source of restored candidate set

```text
Files/FX_OUTPUTS/gold_v3/24_further_pruned_decision_proposal_audit_only/gold_v3_24_retained_packet.csv
```

Expected retained rows: 7.

## Required upstream

```text
GOLD_V3_24_FURTHER_PRUNED_DECISION_PROPOSAL_READY_AUDIT_ONLY
GOLD_V3_25_RETAINED_PACKET_ROBUSTNESS_REVIEW_READY_AUDIT_ONLY
```

## Required inputs

```text
Files/FX_OUTPUTS/gold_v3/24_further_pruned_decision_proposal_audit_only/gold_v3_24_summary.json
Files/FX_OUTPUTS/gold_v3/24_further_pruned_decision_proposal_audit_only/gold_v3_24_retained_packet.csv
Files/FX_OUTPUTS/gold_v3/24_further_pruned_decision_proposal_audit_only/gold_v3_24_filter_traceability_retained.csv
Files/FX_OUTPUTS/gold_v3/25_retained_packet_robustness_review_audit_only/gold_v3_25_retained_robustness_review.csv
```

## Output directory

```text
Files/FX_OUTPUTS/gold_v3/30_all_retained_candidate_set_restore_audit_only/
```

## Outputs

```text
gold_v3_30_summary.json
gold_v3_30_input_inventory.csv
gold_v3_30_all_retained_candidate_set.csv
gold_v3_30_all_retained_filter_contract.csv
gold_v3_30_candidate_role_matrix.csv
gold_v3_30_review_matrix.csv
gold_v3_30_blocker_matrix.csv
GOLD_V3_30_ALL_RETAINED_CANDIDATE_SET_RESTORE_AUDIT_ONLY_REPORT.md
```

## Restore policy

All Stage24 retained rows are kept.

Robustness flags are advisory labels only:

```text
CLEAR -> RETAINED_CLEAR
non-CLEAR -> RETAINED_WATCH
```

Both roles remain inside the candidate set.

## Ready status

```text
GOLD_V3_30_ALL_RETAINED_CANDIDATE_SET_RESTORE_READY_AUDIT_ONLY
```

## Safety

Audit-only. No order sending, no alert sending, no model training, no daily cap, no month filter, no switching rule.
