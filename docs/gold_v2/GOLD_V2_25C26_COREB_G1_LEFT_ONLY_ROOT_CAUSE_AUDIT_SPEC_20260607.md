# GOLD V2 25C26 CoreB G1 left-only root cause audit spec

Date: 2026-06-07
Step: `25C26_COREB_G1_LEFT_ONLY_ROOT_CAUSE_AUDIT_ONLY`
Mode: audit-only root cause review

## Purpose

25C25 confirmed G1 left-only dominance:

```text
g1_both = 168
g1_left_only = 813
g1_right_only = 78
left_to_right_ratio = 10.423077
```

25C26 reviews why replay-side G1 entries exist without matching target-side G1 entries.

## Review dimensions

```text
1. left-only filter family profile
2. left-only replay signal multiplicity by G1 key
3. sample enrichment for left-only G1 keys
4. next audit-only contract revision target
```

## Outputs

```text
00_不要_25c26_file_request_list.csv
01_25c26_GOLD_V2_COREB_G1_LEFT_ONLY_ROOT_CAUSE_AUDIT_ONLY_REPORT.md
02_25c26_coreb_g1_left_only_root_cause_summary.json
03_25c26_input_audit.csv
04_25c26_left_only_filter_family_profile.csv
05_25c26_left_only_signal_multiplicity_profile.csv
06_25c26_left_only_sample_enrichment.csv
07_25c26_left_only_root_cause_decision_matrix.csv
08_25c26_next_step_plan.csv
```

Expected status:

```text
COREB_G1_LEFT_ONLY_ROOT_CAUSE_COMPLETED_AUDIT_ONLY_REPLAY_OVERGENERATION_CONTRACT_REVIEW_REQUIRED
```
