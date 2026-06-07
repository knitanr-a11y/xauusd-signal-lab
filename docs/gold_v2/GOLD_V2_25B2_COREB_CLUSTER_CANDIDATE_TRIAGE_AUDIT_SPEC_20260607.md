# GOLD V2 25B2 CoreB cluster candidate triage audit spec

Date: 2026-06-07
Step: `25B2_COREB_CLUSTER_CANDIDATE_TRIAGE_AUDIT_ONLY`
Mode: audit-only candidate triage

## 1. Purpose

25B found many candidate files for CoreB `same_count` / `cluster_id` / membership source recovery, but the first-pass classifier intentionally favored recall and produced many false positives.

25B2 is a second-pass triage over the 25B candidate inventory. It does not search OHLC, does not reconstruct CoreB, and does not replay same_count.

The goal is to separate:

```text
true source-universe candidates
CoreB target ledgers
combined evaluator / replay attempts
prior audit search records
audit-generated or self-generated files
docs / handoffs
CoreA / MEDIUM non-CoreB ledgers
unresolved manual-review candidates
```

## 2. Input files

25B2 uses 25B outputs as source-of-truth inputs:

```text
Files/FX_OUTPUTS/gold_v2_25b_coreb_cluster_source_recovery_audit_only/gold_v2_25b_coreb_cluster_candidate_inventory.csv
Files/FX_OUTPUTS/gold_v2_25b_coreb_cluster_source_recovery_audit_only/gold_v2_25b_coreb_cluster_recovery_summary.json
Files/FX_OUTPUTS/gold_v2_25b_coreb_cluster_source_recovery_audit_only/gold_v2_25b_coreb_cluster_evidence_matrix.csv
Files/FX_OUTPUTS/gold_v2_25b_coreb_cluster_source_recovery_audit_only/gold_v2_25b_coreb_replay_requirements.csv
```

The inventory row count must match the 25B summary `candidate_rows` value.

From the uploaded 25B run, the expected current value is:

```text
candidate_rows = 430
valid_candidate_rows_requiring_review = 116
```

If the summary reports different values, 25B2 uses the summary as source-of-truth and records the observed values.

## 3. Output folder

```text
Files/FX_OUTPUTS/gold_v2_25b2_coreb_cluster_candidate_triage_audit_only/
```

## 4. Required output files

```text
GOLD_V2_25B2_COREB_CLUSTER_CANDIDATE_TRIAGE_AUDIT_ONLY_REPORT.md
gold_v2_25b2_candidate_triage.csv
gold_v2_25b2_priority_shortlist.csv
gold_v2_25b2_false_positive_buckets.csv
gold_v2_25b2_next_review_plan.csv
gold_v2_25b2_coreb_cluster_candidate_triage_summary.json
```

## 5. Triage classes

25B2 may assign classes such as:

```text
RAW_SIGNAL_LEDGER_SOURCE_UNIVERSE_CANDIDATE
FROZEN_SOURCE_UNIVERSE_CONFIG_OR_FREEZER
COMBINED_EVALUATOR_DEFINITION_OR_REPLAY
COREB_TARGET_TOP_LEDGER_NOT_MEMBERSHIP
PRIOR_COREB_SEARCH_AUDIT_RECORD
AUDIT_SCRIPT_NOT_ORIGINAL
AUDIT_OUTPUT_OR_POST_HOC
DOC_OR_HANDOFF_NOT_ORIGINAL
COREA_OR_MEDIUM_LEDGER_NOT_COREB_CLUSTER_SOURCE
AI_TAG_SNAPSHOT_DOWNSTREAM_NOT_CLUSTER_SOURCE
UNRESOLVED_MANUAL_REVIEW_CANDIDATE
MENTION_ONLY_NOT_ENOUGH
```

## 6. CoreB unblock policy

25B2 must keep CoreB blocked.

Even a high-priority shortlist candidate is only a review target. It does not prove:

```text
replayed CoreB RR125 rows = 125
missing source keys = 0
extra replay keys = 0
same_count exact match rows = 125
cluster_id or membership exact match rows = 125
```

## 7. Non-goals

25B2 must not:

```text
implement CoreB same_count approximation
fit cluster/membership to the 125 SOT rows
run source recovery execution
mutate artifacts
finalize source identity
enable live evaluator final signal
send Discord
place MT5 orders
call AI API
connect live hook
continue 24AG
```

NO_SIGNAL Discord notification remains forbidden.

## 8. Success condition

25B2 succeeds when:

```text
25B inventory exists
25B inventory row count matches 25B summary candidate_rows
every 25B row receives a second-pass triage class
a priority shortlist is produced
CoreB remains blocked
all safety flags remain false/off
```

## 9. Stop condition

25B2 stops if:

```text
25B candidate inventory is missing
25B summary is missing
inventory rows do not match summary candidate_rows
candidate inventory required columns are missing
any safety flag would be enabled
```

## 10. Expected next action after 25B2

If the priority shortlist identifies plausible source-universe files, inspect those exact files manually first.

Do not write a replay/parity implementation until a candidate is accepted as original/source-of-truth evidence rather than audit-generated, post-hoc, summary-only, or downstream generated.
