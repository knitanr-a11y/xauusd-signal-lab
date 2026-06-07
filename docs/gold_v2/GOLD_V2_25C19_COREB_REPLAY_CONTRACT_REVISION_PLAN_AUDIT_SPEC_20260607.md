# GOLD V2 25C19 CoreB replay contract revision plan audit spec

Date: 2026-06-07
Step: `25C19_COREB_REPLAY_CONTRACT_REVISION_PLAN_AUDIT_ONLY`
Mode: audit-only revision plan, no replay execution

## Purpose

25C18 rejected the current replay contract as exact. 25C19 defines safe revision candidates before any further dry-run.

## Non-negotiable boundaries

```text
Do not change CoreB conditions.
Do not infer membership from target rows.
Do not use target rows to tune thresholds.
Do not execute source recovery.
Do not enable live evaluator or final signal.
```

## Revision candidates

```text
R1: filter-family comparison review
R2: entry_time multiplicity review
R3: target selected-scope adoption review
R4: source-count aggregation contract review
```

## Outputs

```text
00_不要_25c19_file_request_list.csv
01_25c19_GOLD_V2_COREB_REPLAY_CONTRACT_REVISION_PLAN_AUDIT_ONLY_REPORT.md
02_25c19_coreb_replay_contract_revision_plan_summary.json
03_25c19_input_audit.csv
04_25c19_revision_candidate_matrix.csv
05_25c19_contract_boundary_matrix.csv
06_25c19_acceptance_gate_matrix.csv
07_25c19_next_step_plan.csv
```

Expected status:

```text
COREB_REPLAY_CONTRACT_REVISION_PLAN_READY_AUDIT_ONLY_EXECUTION_BLOCKED
```
