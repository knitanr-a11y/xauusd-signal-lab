# GOLD V2 25B CoreB cluster source recovery audit spec

Date: 2026-06-07
Step: `25B_COREB_CLUSTER_SOURCE_RECOVERY_AUDIT_ONLY`
Mode: audit-only source evidence inventory

## 1. Purpose

25B searches the repository and known `Files/FX_OUTPUTS` artifacts for original CoreB `same_count` / `cluster_id` / row-level membership source-of-truth evidence.

The goal is **not** to reconstruct or approximate CoreB clustering.

The goal is to produce an auditable candidate inventory that clearly separates:

```text
ORIGINAL_ALGORITHM_CANDIDATE
ROW_LEVEL_MEMBERSHIP_CANDIDATE
SOURCE_UNIVERSE_CANDIDATE
SUMMARY_ONLY_NOT_ENOUGH
AUDIT_GENERATED_OR_POST_HOC
MENTIONS_KEYWORDS_ONLY
DOC_ONLY
NOT_RELEVANT / SCAN_ERROR
```

## 2. Non-goals

25B must not:

```text
run source recovery execution
mutate source artifacts
finalize source identity
enable live evaluator final signals
send Discord messages
place MT5 orders
call AI APIs
connect live hooks
approximate same_count
fit cluster_id / membership after seeing target SOT rows
continue 24AG
```

NO_SIGNAL Discord notification remains forbidden.

## 3. Input sources

25B reads only local repository and artifact files:

```text
repo root:        knitanr-a11y/xauusd-signal-lab
artifact root:    Files/FX_OUTPUTS
```

It scans text-like files only:

```text
.py .bat .ps1 .md .txt .json .yaml .yml .csv .tsv .ini .cfg
```

Default scan size limit:

```text
max_file_bytes = 8,000,000
```

## 4. Search terms

```text
same_count
cluster_id
membership
cluster_membership
confluence
RR125
RR1.25
BUY_CONFLUENCE
same_count_source_universe
source_universe
cluster ledger
top cluster
top_ledgers
```

## 5. Output folder

```text
Files/FX_OUTPUTS/gold_v2_25b_coreb_cluster_source_recovery_audit_only/
```

## 6. Required output files

```text
GOLD_V2_25B_COREB_CLUSTER_SOURCE_RECOVERY_AUDIT_ONLY_REPORT.md
gold_v2_25b_coreb_cluster_candidate_inventory.csv
gold_v2_25b_coreb_cluster_evidence_matrix.csv
gold_v2_25b_coreb_replay_requirements.csv
gold_v2_25b_coreb_cluster_recovery_summary.json
```

## 7. Candidate inventory fields

The candidate inventory includes:

```text
scope
relative_path
absolute_path
suffix
bytes
sha256
matched_keywords
candidate_bucket
classification_reason
has_row_level_membership_terms
has_source_universe_terms
has_original_algorithm_terms
summary_only
csv_readable
sampled_rows
columns
snippet
```

## 8. Evidence gates

25B may only identify evidence candidates. It does not unblock CoreB.

CoreB remains blocked until a later replay/parity gate proves:

```text
expected CoreB RR125 rows = 125
replayed rows = 125
missing source keys = 0
extra replay keys = 0
same_count exact match rows = 125
cluster_id or membership exact match rows = 125, if cluster_id is part of source truth
```

## 9. Stop conditions

25B must stop or remain blocked if:

```text
no original algorithm candidate is found
only audit-generated/post-hoc files are found
only summary-level cluster data exists without row membership
candidate algorithm cannot replay to 125 rows
same_count exact parity cannot be proven
any step tries to fit/approximate the cluster after seeing SOT rows
```

## 10. Safety flags

All outputs must keep:

```text
source_recovery_execution_allowed_now = false
source_mutation_allowed = false
source_identity_finalization_allowed_now = false
live_evaluator_final_signal_allowed = false
final_signal_allowed = false
discord_send_allowed = false
mt5_order_allowed = false
ai_api_allowed = false
live_hook_allowed = false
no_signal_discord_notification_allowed = false
old_gold_disc8_quarantined = true
source_recovery_chain_status = PAUSED_AT_24AF
```

## 11. Implementation files

```text
scripts/gold_v2_runtime/audit_gold_v2_25b_coreb_cluster_source_recovery_audit_only.py
scripts/gold_v2_runtime/bat/25B_COREB_CLUSTER_SOURCE_RECOVERY_AUDIT_ONLY.bat
```

## 12. Execution order

Run 25A first, then 25B:

```text
scripts/gold_v2_runtime/bat/25A_COREA_COREB_MEDIUM_LIVE_EVALUATOR_READINESS_AUDIT_ONLY.bat
scripts/gold_v2_runtime/bat/25B_COREB_CLUSTER_SOURCE_RECOVERY_AUDIT_ONLY.bat
```

## 13. Success condition

25B succeeds as an audit package when all required output files are written and the candidate inventory/evidence matrix clearly report whether any original evidence candidate exists.

This success does **not** mean CoreB live evaluator is unblocked.

## 14. CoreB unblock condition

CoreB live evaluator remains blocked unless a later audited replay proves exact source-of-truth parity for the original cluster/same_count/membership semantics.
