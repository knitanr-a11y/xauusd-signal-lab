# GOLD V3 24 further-pruned decision proposal audit-only spec

Created: 2026-06-09

Status: `GOLD_V3_24_FURTHER_PRUNED_DECISION_PROPOSAL_SPEC_READY_AUDIT_ONLY`

## Purpose

GOLD V3 24 converts the Stage23 compact packet into an audit-only decision proposal.

Stage23 has 13 rows, many of which are near-duplicates. Stage24 proposes which variants should proceed to the next audit-only final validation and which should remain auxiliary, July-rescue review, or rejected as redundant.

This is not final approval and not live approval.

## Required upstream

```text
GOLD_V3_23_FURTHER_PRUNED_SHORTLIST_HUMAN_INTAKE_READY_AUDIT_ONLY
```

## Required inputs

```text
Files/FX_OUTPUTS/gold_v3/23_further_pruned_shortlist_human_intake_audit_only/gold_v3_23_summary.json
Files/FX_OUTPUTS/gold_v3/23_further_pruned_shortlist_human_intake_audit_only/gold_v3_23_compact_decision_packet.csv
Files/FX_OUTPUTS/gold_v3/23_further_pruned_shortlist_human_intake_audit_only/gold_v3_23_filter_traceability_packet.csv
Files/FX_OUTPUTS/gold_v3/23_further_pruned_shortlist_human_intake_audit_only/gold_v3_23_source_group_review.csv
```

## Decision proposal policy

The proposal should prefer:

```text
highest PF and win-rate within source group
2+ trades/day where possible
negative months = 0 where possible
less redundant variants
R1_ONLY primary strength
MAIN_R1_R2 auxiliary comparison
R1_ONLY_CD60_PRUNE_015 retained only as July-rescue review unless full-period robustness is resolved
```

## Proposed retained structure

```text
PRIMARY_NEXT_AUDIT_ONLY:
- best R1_ONLY_CD60_PRUNE_111 variant

AUXILIARY_COMPARISON_ONLY:
- best R1_ONLY_CD60_PRUNE_115 sibling variant
- best MAIN_R1_R2_CD90_PRUNE_133 variant
- MAIN_R1_R2_CD120_PRUNE_122 stable low-frequency variant

JULY_RESCUE_REVIEW:
- selected R1_ONLY_CD60_PRUNE_015 variants

REJECT_FROM_SHORTLIST:
- redundant weaker siblings
```

## Required outputs

Output directory:

```text
Files/FX_OUTPUTS/gold_v3/24_further_pruned_decision_proposal_audit_only/
```

Files:

```text
gold_v3_24_summary.json
gold_v3_24_input_inventory.csv
gold_v3_24_decision_proposal.csv
gold_v3_24_retained_packet.csv
gold_v3_24_rejected_redundant_packet.csv
gold_v3_24_filter_traceability_retained.csv
gold_v3_24_decision_matrix.csv
gold_v3_24_blocker_matrix.csv
GOLD_V3_24_FURTHER_PRUNED_DECISION_PROPOSAL_AUDIT_ONLY_REPORT.md
```

Exception runs may additionally write:

```text
gold_v3_24_exception.txt
```

## Ready status

```text
GOLD_V3_24_FURTHER_PRUNED_DECISION_PROPOSAL_READY_AUDIT_ONLY
```

## Safety

- Audit-only.
- No final approval.
- No live approval.
- No switching logic.
- No month filter.
- No daily cap.
- No model training.
- No signal generation.
- No ZIP output.
- No external action.
- GOLD V2 / old GOLD / DISC8 remain quarantined.
