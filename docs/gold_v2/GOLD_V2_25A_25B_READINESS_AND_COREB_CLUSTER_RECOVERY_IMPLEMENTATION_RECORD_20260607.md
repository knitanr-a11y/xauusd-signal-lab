# GOLD V2 25A/25B readiness and CoreB cluster recovery implementation record

Date: 2026-06-07
Repo: `knitanr-a11y/xauusd-signal-lab`
Mode: audit-only

## 1. What was implemented

Implemented the 25A readiness package:

```text
scripts/gold_v2_runtime/audit_gold_v2_25a_corea_coreb_medium_live_evaluator_readiness_audit_only.py
scripts/gold_v2_runtime/bat/25A_COREA_COREB_MEDIUM_LIVE_EVALUATOR_READINESS_AUDIT_ONLY.bat
```

Implemented the 25B CoreB cluster source recovery audit package:

```text
scripts/gold_v2_runtime/audit_gold_v2_25b_coreb_cluster_source_recovery_audit_only.py
scripts/gold_v2_runtime/bat/25B_COREB_CLUSTER_SOURCE_RECOVERY_AUDIT_ONLY.bat
```

Added the 25B strict audit specification:

```text
docs/gold_v2/GOLD_V2_25B_COREB_CLUSTER_SOURCE_RECOVERY_AUDIT_SPEC_20260607.md
```

## 2. Files to look at after running

### 25A output folder

```text
Files/FX_OUTPUTS/gold_v2_25a_corea_coreb_medium_live_evaluator_readiness_audit_only/
```

First files:

```text
GOLD_V2_25A_COREA_COREB_MEDIUM_LIVE_EVALUATOR_READINESS_AUDIT_ONLY_REPORT.md
gold_v2_25a_corea_coreb_medium_live_evaluator_readiness_summary.json
```

Supporting files:

```text
gold_v2_25a_input_audit.csv
gold_v2_25a_reference_doc_audit.csv
gold_v2_25a_final_sot_count_audit.csv
gold_v2_25a_core_component_readiness_matrix.csv
gold_v2_25a_live_evaluator_blocker_matrix.csv
gold_v2_25a_recommended_next_steps.csv
gold_v2_25a_safety_matrix.csv
```

### 25B output folder

```text
Files/FX_OUTPUTS/gold_v2_25b_coreb_cluster_source_recovery_audit_only/
```

First files:

```text
GOLD_V2_25B_COREB_CLUSTER_SOURCE_RECOVERY_AUDIT_ONLY_REPORT.md
gold_v2_25b_coreb_cluster_recovery_summary.json
```

Supporting files:

```text
gold_v2_25b_coreb_cluster_candidate_inventory.csv
gold_v2_25b_coreb_cluster_evidence_matrix.csv
gold_v2_25b_coreb_replay_requirements.csv
```

## 3. BAT execution order

Run 25A first:

```text
scripts/gold_v2_runtime/bat/25A_COREA_COREB_MEDIUM_LIVE_EVALUATOR_READINESS_AUDIT_ONLY.bat
```

Then run 25B:

```text
scripts/gold_v2_runtime/bat/25B_COREB_CLUSTER_SOURCE_RECOVERY_AUDIT_ONLY.bat
```

Do not run 24AG unless the user explicitly asks to resume the paused 24-series branch.

## 4. 25A success condition

25A succeeds only when:

```text
status = COREA_COREB_MEDIUM_LIVE_EVALUATOR_READINESS_REVIEW_READY_AUDIT_ONLY_COREB_CLUSTER_RECOVERY_REQUIRED
total_stop_rows = 0
final SOT total rows = 529
2025 rows = 346
2026 rows = 183
source breakdown matches the frozen final SOT expectations
safety matrix keeps all external/live/source-recovery actions disabled
primary next = 25B_COREB_CLUSTER_SOURCE_RECOVERY_AUDIT_ONLY
```

25A success does not enable live evaluator or final signal.

## 5. 25A stop condition

25A stops if:

```text
required reference docs are missing
final SOT ledger is missing
final SOT total rows do not equal 529
2025/2026 row counts do not match 346/183
source breakdown does not match the frozen final SOT expectations
any safety flag is changed away from audit-only disabled state
```

## 6. 25B success condition

25B succeeds as an audit package when:

```text
candidate inventory is written
evidence matrix is written
replay requirements are written
summary/report are written
all candidates are classified without approximating same_count or cluster membership
```

25B package success does not mean CoreB live evaluator is unblocked.

## 7. 25B stop / blocked conditions

CoreB remains blocked if:

```text
no original algorithm candidate is found
only audit-generated/post-hoc files are found
only summary-level cluster data exists without row membership
candidate algorithm cannot replay to 125 rows
same_count exact parity cannot be proven
any step tries to fit/approximate the cluster after seeing SOT rows
```

## 8. Output status expectations

25A expected status:

```text
COREA_COREB_MEDIUM_LIVE_EVALUATOR_READINESS_REVIEW_READY_AUDIT_ONLY_COREB_CLUSTER_RECOVERY_REQUIRED
```

25B expected status before replay parity is proven:

```text
COREB_CLUSTER_SOURCE_RECOVERY_BLOCKED_OR_INSUFFICIENT_AUDIT_ONLY
```

A stronger 25B package status can only be used if original evidence candidates are found, human-reviewed, and a later replay/parity gate proves exact 125-row same_count/membership parity.

## 9. Actions still forbidden

```text
source recovery execution
source artifact mutation
source identity finalization
24AG continuation without explicit request
live evaluator final signal
Discord send
MT5 order
AI API
live hook
NO_SIGNAL Discord notification
CoreB same_count approximation
CoreA A gate approximation
MEDIUM-only final signal substitution
```
