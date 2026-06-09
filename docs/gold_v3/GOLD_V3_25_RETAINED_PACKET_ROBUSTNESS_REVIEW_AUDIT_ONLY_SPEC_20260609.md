# GOLD V3 25 retained packet robustness review audit-only spec

Created: 2026-06-09

Status: `GOLD_V3_25_RETAINED_PACKET_ROBUSTNESS_REVIEW_SPEC_READY_AUDIT_ONLY`

## Purpose

GOLD V3 25 reviews only the retained Stage24 packet rows.

The goal is to verify the retained 7 rows against Stage22 full-period and monthly metrics before any later human decision intake.

This stage is audit-only. It does not turn on production behavior.

## Required upstream

```text
GOLD_V3_24_FURTHER_PRUNED_DECISION_PROPOSAL_READY_AUDIT_ONLY
GOLD_V3_22_WITHIN_CANDIDATE_LOSS_FEATURE_PRUNING_READY_AUDIT_ONLY
```

## Required inputs

```text
Files/FX_OUTPUTS/gold_v3/24_further_pruned_decision_proposal_audit_only/gold_v3_24_summary.json
Files/FX_OUTPUTS/gold_v3/24_further_pruned_decision_proposal_audit_only/gold_v3_24_retained_packet.csv
Files/FX_OUTPUTS/gold_v3/24_further_pruned_decision_proposal_audit_only/gold_v3_24_filter_traceability_retained.csv
Files/FX_OUTPUTS/gold_v3/22_within_candidate_loss_feature_pruning_audit_only/gold_v3_22_further_pruned_candidate_metrics.csv
Files/FX_OUTPUTS/gold_v3/22_within_candidate_loss_feature_pruning_audit_only/gold_v3_22_further_pruned_monthly_metrics.csv
```

## Output directory

```text
Files/FX_OUTPUTS/gold_v3/25_retained_packet_robustness_review_audit_only/
```

## Outputs

```text
gold_v3_25_summary.json
gold_v3_25_input_inventory.csv
gold_v3_25_retained_robustness_review.csv
gold_v3_25_retained_monthly_review.csv
gold_v3_25_filter_traceability_review.csv
gold_v3_25_review_matrix.csv
gold_v3_25_blocker_matrix.csv
GOLD_V3_25_RETAINED_PACKET_ROBUSTNESS_REVIEW_AUDIT_ONLY_REPORT.md
```

## Review policy

The review keeps the Stage24 roles:

```text
PRIMARY
COMPARE_R1
JULY_REVIEW
COMPARE_MAIN
```

It flags rows with:

```text
negative months > 0
worst month below 0
July PF below 1.1
fewer than 2 trades/day
```

## Ready status

```text
GOLD_V3_25_RETAINED_PACKET_ROBUSTNESS_REVIEW_READY_AUDIT_ONLY
```

## Safety

Audit-only. No switching rule, no month filter, no daily cap, no production behavior.
