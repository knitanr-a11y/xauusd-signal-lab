# NEXT CHAT HANDOFF — GOLD V2 25A/25B implemented audit-only

Date: 2026-06-07
Repo: `knitanr-a11y/xauusd-signal-lab`

## 1. Current state

GOLD V2 remains audit-only.

24-series source recovery chain remains paused at 24AF.

Do not proceed to 24AG unless explicitly requested.

Old GOLD/DISC8 remains quarantined.

Approximate reimplementation is prohibited.

External/live actions remain OFF:

```text
Discord send = false
MT5 order = false
AI API = false
live hook = false
final signal = false
NO_SIGNAL Discord notification = false
```

## 2. What was implemented in this chat

Implemented 25A readiness package:

```text
scripts/gold_v2_runtime/audit_gold_v2_25a_corea_coreb_medium_live_evaluator_readiness_audit_only.py
scripts/gold_v2_runtime/bat/25A_COREA_COREB_MEDIUM_LIVE_EVALUATOR_READINESS_AUDIT_ONLY.bat
```

Implemented 25B CoreB cluster source recovery audit package:

```text
scripts/gold_v2_runtime/audit_gold_v2_25b_coreb_cluster_source_recovery_audit_only.py
scripts/gold_v2_runtime/bat/25B_COREB_CLUSTER_SOURCE_RECOVERY_AUDIT_ONLY.bat
```

Added/updated docs:

```text
docs/gold_v2/GOLD_V2_25A_COREA_COREB_MEDIUM_LIVE_EVALUATOR_READINESS_AUDIT_SPEC_20260607.md
docs/gold_v2/GOLD_V2_25B_COREB_CLUSTER_SOURCE_RECOVERY_AUDIT_SPEC_20260607.md
docs/gold_v2/GOLD_V2_25A_25B_READINESS_AND_COREB_CLUSTER_RECOVERY_IMPLEMENTATION_RECORD_20260607.md
docs/gold_v2/NEXT_CHAT_HANDOFF_GOLD_V2_25A_25B_IMPLEMENTED_AUDIT_ONLY_20260607.md
```

## 3. 25A purpose

25A is a readiness package only.

It creates:

```text
GOLD_V2_25A_COREA_COREB_MEDIUM_LIVE_EVALUATOR_READINESS_AUDIT_ONLY_REPORT.md
gold_v2_25a_input_audit.csv
gold_v2_25a_reference_doc_audit.csv
gold_v2_25a_final_sot_count_audit.csv
gold_v2_25a_core_component_readiness_matrix.csv
gold_v2_25a_live_evaluator_blocker_matrix.csv
gold_v2_25a_recommended_next_steps.csv
gold_v2_25a_safety_matrix.csv
gold_v2_25a_corea_coreb_medium_live_evaluator_readiness_summary.json
```

Expected output folder:

```text
Files/FX_OUTPUTS/gold_v2_25a_corea_coreb_medium_live_evaluator_readiness_audit_only/
```

Expected passing status:

```text
COREA_COREB_MEDIUM_LIVE_EVALUATOR_READINESS_REVIEW_READY_AUDIT_ONLY_COREB_CLUSTER_RECOVERY_REQUIRED
```

## 4. 25A stop conditions

25A stops if:

```text
required reference docs are missing
final SOT ledger is missing
final SOT total rows do not equal 529
2025/2026 rows do not equal 346/183
source breakdown does not match frozen expected counts
any safety flag is not audit-only/off
```

## 5. 25B purpose

25B searches repo and `Files/FX_OUTPUTS` artifacts for original CoreB clustering evidence.

It inventories and classifies hits for:

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

25B does not approximate same_count and does not replay CoreB.

Expected output folder:

```text
Files/FX_OUTPUTS/gold_v2_25b_coreb_cluster_source_recovery_audit_only/
```

Expected files:

```text
GOLD_V2_25B_COREB_CLUSTER_SOURCE_RECOVERY_AUDIT_ONLY_REPORT.md
gold_v2_25b_coreb_cluster_candidate_inventory.csv
gold_v2_25b_coreb_cluster_evidence_matrix.csv
gold_v2_25b_coreb_replay_requirements.csv
gold_v2_25b_coreb_cluster_recovery_summary.json
```

## 6. 25B expected status

Before exact replay/parity is proven, the expected status is:

```text
COREB_CLUSTER_SOURCE_RECOVERY_BLOCKED_OR_INSUFFICIENT_AUDIT_ONLY
```

This is not a script failure. It means CoreB remains blocked because evidence inventory alone does not prove live evaluator readiness.

## 7. 25B candidate buckets

25B classifies hits into buckets such as:

```text
ORIGINAL_ALGORITHM_CANDIDATE
ROW_LEVEL_MEMBERSHIP_CANDIDATE
SOURCE_UNIVERSE_CANDIDATE
SUMMARY_ONLY_NOT_ENOUGH
AUDIT_GENERATED_OR_POST_HOC
MENTIONS_KEYWORDS_ONLY
DOC_ONLY
SCAN_ERROR
```

Candidate existence alone does not unblock CoreB. Any candidate must be human-reviewed and later replayed.

## 8. CoreB unblock gate remains future work

CoreB live evaluator remains blocked until a later audited replay proves:

```text
expected CoreB RR125 rows = 125
replayed rows = 125
missing source keys = 0
extra replay keys = 0
same_count exact match rows = 125
cluster_id or membership exact match rows = 125, if cluster_id is part of source truth
```

## 9. BAT execution order

Run:

```text
scripts/gold_v2_runtime/bat/25A_COREA_COREB_MEDIUM_LIVE_EVALUATOR_READINESS_AUDIT_ONLY.bat
```

Then run:

```text
scripts/gold_v2_runtime/bat/25B_COREB_CLUSTER_SOURCE_RECOVERY_AUDIT_ONLY.bat
```

## 10. Next recommended work

After the user runs 25A and 25B and provides outputs:

```text
1. Review 25A summary/report for total_stop_rows and final SOT count parity.
2. Review 25B candidate inventory and evidence matrix.
3. If 25B finds original algorithm / row-level membership / source universe candidates, inspect those files manually before any replay plan.
4. If evidence is insufficient, keep CoreB historical-only and live blocked.
5. Do not implement a replay/parity script until the candidate source evidence is accepted as original/source-of-truth evidence.
```

## 11. Do not do next

Do not:

```text
continue 24AG
run source recovery
mutate source artifacts
finalize source identity
enable live evaluator final signal
send Discord
place MT5 orders
call AI API
connect live hook
notify Discord on NO_SIGNAL
approximate CoreB same_count
fit cluster_id / membership to the 125 SOT rows
substitute MEDIUM-only work for the full CoreA/CoreB/MEDIUM portfolio without a later explicit CoreB-exclusion decision
```
