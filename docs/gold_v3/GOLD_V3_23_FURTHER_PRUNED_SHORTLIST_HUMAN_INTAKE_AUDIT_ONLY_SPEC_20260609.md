# GOLD V3 23 further-pruned shortlist human intake audit-only spec

Created: 2026-06-09

Status: `GOLD_V3_23_FURTHER_PRUNED_SHORTLIST_HUMAN_INTAKE_SPEC_READY_AUDIT_ONLY`

## Purpose

GOLD V3 23 converts Stage22 within-candidate pruning recommendations into a compact human decision packet/template.

Stage22 produced many similar variants. Stage23 does not auto-approve them. It deduplicates and organizes the best further-pruned candidates by source scenario so a human can decide which candidates should proceed to the next audit-only validation.

This stage is audit-only. It does not approve final candidates and does not enable live behavior.

## Required upstream

```text
GOLD_V3_22_WITHIN_CANDIDATE_LOSS_FEATURE_PRUNING_READY_AUDIT_ONLY
```

## Required inputs

```text
Files/FX_OUTPUTS/gold_v3/22_within_candidate_loss_feature_pruning_audit_only/gold_v3_22_summary.json
Files/FX_OUTPUTS/gold_v3/22_within_candidate_loss_feature_pruning_audit_only/gold_v3_22_recommendation.csv
Files/FX_OUTPUTS/gold_v3/22_within_candidate_loss_feature_pruning_audit_only/gold_v3_22_further_pruned_candidate_metrics.csv
Files/FX_OUTPUTS/gold_v3/22_within_candidate_loss_feature_pruning_audit_only/gold_v3_22_filter_traceability.csv
Files/FX_OUTPUTS/gold_v3/22_within_candidate_loss_feature_pruning_audit_only/gold_v3_22_base_candidate_metrics.csv
```

## Required inclusion

The packet must preserve:

```text
R1_ONLY_CD60_PRUNE_111 best further-pruned variants
R1_ONLY_CD60_PRUNE_115 best further-pruned variants
R1_ONLY_CD60_PRUNE_015 further-pruned variants, because the user explicitly wanted it as a candidate
MAIN_R1_R2_CD90_PRUNE_133 further-pruned variants
MAIN_R1_R2_CD90_PRUNE_132 further-pruned variants
MAIN_R1_R2_CD120_PRUNE_122 further-pruned variants if present
```

## Not allowed

```text
seasonal switching
month as a live filter
daily cap
final candidate approval
threshold finalization
model training
signal generation
live enablement
ZIP output
external action
```

## Human decision values

```text
APPROVE_FOR_NEXT_AUDIT_ONLY_FINAL_VALIDATION
APPROVE_AS_AUXILIARY_COMPARISON_ONLY
KEEP_JULY_RESCUE_REVIEW
REQUEST_MORE_AUDIT
REJECT_FROM_SHORTLIST
```

Any approval in this template is only permission for the next audit-only validation, not final or live approval.

## Required outputs

Output directory:

```text
Files/FX_OUTPUTS/gold_v3/23_further_pruned_shortlist_human_intake_audit_only/
```

Files:

```text
gold_v3_23_summary.json
gold_v3_23_input_inventory.csv
gold_v3_23_compact_decision_packet.csv
gold_v3_23_human_decision_template.csv
gold_v3_23_source_group_review.csv
gold_v3_23_filter_traceability_packet.csv
gold_v3_23_decision_matrix.csv
gold_v3_23_blocker_matrix.csv
GOLD_V3_23_FURTHER_PRUNED_SHORTLIST_HUMAN_INTAKE_AUDIT_ONLY_REPORT.md
```

Exception runs may additionally write:

```text
gold_v3_23_exception.txt
```

## Ready status

```text
GOLD_V3_23_FURTHER_PRUNED_SHORTLIST_HUMAN_INTAKE_READY_AUDIT_ONLY
```

## Safety

- Audit-only.
- No switching logic.
- No month filter.
- No daily cap.
- No final approval.
- No live enablement.
- No model training.
- No signal generation.
- No ZIP output.
- No external action.
- GOLD V2 / old GOLD / DISC8 remain quarantined.
