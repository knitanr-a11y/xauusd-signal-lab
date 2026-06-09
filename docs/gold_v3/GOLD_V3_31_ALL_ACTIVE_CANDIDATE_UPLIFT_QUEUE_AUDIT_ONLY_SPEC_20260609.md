# GOLD V3 31 all active candidate uplift queue audit-only spec

Created: 2026-06-09

Status: `GOLD_V3_31_ALL_ACTIVE_CANDIDATE_UPLIFT_QUEUE_SPEC_READY_AUDIT_ONLY`

## Purpose

GOLD V3 31 corrects Stage30 terminology.

All 7 Stage24 retained candidates are active audit candidates. None are watchlist candidates. Diagnostic flags are used only to identify where win-rate and PF uplift should continue.

This stage is still in the win-rate/PF uplift phase.

## Required upstream

```text
GOLD_V3_30_ALL_RETAINED_CANDIDATE_SET_RESTORE_READY_AUDIT_ONLY
```

## Required inputs

```text
Files/FX_OUTPUTS/gold_v3/30_all_retained_candidate_set_restore_audit_only/gold_v3_30_summary.json
Files/FX_OUTPUTS/gold_v3/30_all_retained_candidate_set_restore_audit_only/gold_v3_30_all_retained_candidate_set.csv
Files/FX_OUTPUTS/gold_v3/30_all_retained_candidate_set_restore_audit_only/gold_v3_30_all_retained_filter_contract.csv
```

## Output directory

```text
Files/FX_OUTPUTS/gold_v3/31_all_active_candidate_uplift_queue_audit_only/
```

## Outputs

```text
gold_v3_31_summary.json
gold_v3_31_input_inventory.csv
gold_v3_31_all_active_candidate_set.csv
gold_v3_31_all_active_filter_contract.csv
gold_v3_31_uplift_queue.csv
gold_v3_31_review_matrix.csv
gold_v3_31_blocker_matrix.csv
GOLD_V3_31_ALL_ACTIVE_CANDIDATE_UPLIFT_QUEUE_AUDIT_ONLY_REPORT.md
```

## Candidate rule

Every restored Stage24 retained row becomes:

```text
ACTIVE_CANDIDATE
```

No candidate is demoted to watchlist.

Diagnostic flags remain only as `uplift_diagnostic` text.

## Uplift phase policy

Candidates with weaker months, low July PF, or negative months are not removed. They are placed in the uplift queue for further loss-feature pruning.

## Ready status

```text
GOLD_V3_31_ALL_ACTIVE_CANDIDATE_UPLIFT_QUEUE_READY_AUDIT_ONLY
```

## Safety

Audit-only. No order sending, no alert sending, no model training, no daily cap, no month filter, no switching rule.
