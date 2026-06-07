# NEXT CHAT HANDOFF — GOLD V2 24AF done / 25B CoreB cluster recovery priority

Date: 2026-06-07
Repo: `knitanr-a11y/xauusd-signal-lab`

## 0. Purpose of this handoff

This handoff summarizes the work completed in the current chat and prepares the next chat to continue without losing state.

The key change in this chat is:

```text
The 24-series source recovery audit chain reached 24AF and is paused.
The focus returns to CoreA/CoreB/MEDIUM live evaluator work.
CoreB cluster/same_count/membership recovery is now the top priority before any full-portfolio live evaluator path.
```

## 1. Absolute rules to carry forward

GOLD V2 remains audit-only.

Do not enable:

```text
source recovery execution
source artifact mutation
source identity finalization
live evaluator final signal
Discord send
MT5 order
AI API
live hook
```

Old GOLD/DISC8 remains quarantined due suspected HTF open-time inconsistency.

Approximate reimplementation is prohibited.

NO_SIGNAL must not send Discord notification.

## 2. What happened in this chat

### 2.1 24AE was completed

The user approved the 24AE value:

```text
APPROVE_SOURCE_RECOVERY_PRE_EXECUTION_FOR_DRY_RUN_AUDIT_ONLY
```

The helper was created:

```text
scripts/gold_v2_runtime/write_24ae_choice4.py
```

The choice write BAT was created:

```text
scripts/gold_v2_runtime/bat/24AE_WRITE_CHOICE.bat
```

The user ran 24AE again and uploaded the outputs.

Confirmed 24AE status:

```text
SOURCE_RECOVERY_PRE_EXECUTION_FINAL_DECISION_INTAKE_VALIDATED_AUDIT_ONLY_SOURCE_RECOVERY_EXECUTION_STILL_BLOCKED
```

Confirmed 24AE facts:

```text
total_stop_rows = 0
decision_supplied = true
decision_validated = true
selected_decision_value = APPROVE_SOURCE_RECOVERY_PRE_EXECUTION_FOR_DRY_RUN_AUDIT_ONLY
required_next_allowed = 24AF_SOURCE_RECOVERY_PRE_EXECUTION_FINAL_DECISION_ROUTING_AUDIT_ONLY
```

### 2.2 24AF was implemented and completed

Created:

```text
docs/gold_v2/GOLD_V2_24AF_SOURCE_RECOVERY_PRE_EXECUTION_FINAL_DECISION_ROUTING_AUDIT_SPEC_20260607.md
scripts/gold_v2_runtime/audit_gold_v2_24af_route_audit_only.py
scripts/gold_v2_runtime/bat/24AF_AUDIT.bat
```

The user ran 24AF and uploaded outputs.

Confirmed 24AF status:

```text
SOURCE_RECOVERY_PRE_EXECUTION_FINAL_DECISION_ROUTED_AUDIT_ONLY_SOURCE_RECOVERY_EXECUTION_STILL_BLOCKED
```

Confirmed 24AF route:

```text
selected_decision_value = APPROVE_SOURCE_RECOVERY_PRE_EXECUTION_FOR_DRY_RUN_AUDIT_ONLY
route_id = ROUTE_APPROVE_TO_DRY_RUN_EXECUTION_PLAN_AUDIT_ONLY
routed_next_audit_step = 24AG_SOURCE_RECOVERY_DRY_RUN_EXECUTION_PLAN_AUDIT_ONLY
total_stop_rows = 0
```

Important:

```text
24AG is not started.
Do not proceed to 24AG unless explicitly requested.
```

### 2.3 24-series was intentionally paused

Created:

```text
docs/gold_v2/GOLD_V2_24AF_PAUSE_AND_CORE_LIVE_EVALUATOR_REFOCUS_20260607.md
docs/gold_v2/NEXT_CHAT_HANDOFF_GOLD_V2_24AF_PAUSED_25A_COREA_COREB_MEDIUM_LIVE_EVALUATOR_20260607.md
```

Reason:

```text
The user clarified that the real goal is not to continue source recovery audit gates, but to make CoreA/CoreB/MEDIUM conditions usable in a live evaluator.
```

The pause is safe because all 24-series artifacts remain audit-only and all forbidden actions remain false.

### 2.4 CoreB blocker was confirmed from prior chat

The user checked a prior chat and received the same conclusion as our repository audits:

```text
CoreB historical backtest is reproduced.
However, CoreB RR125_BUY_CONFLUENCE cannot be regenerated from OHLC as a live evaluator because same_count / cluster_id / membership source-of-truth generation evidence is insufficient.
```

Created:

```text
docs/gold_v2/GOLD_V2_COREB_LIVE_EVALUATOR_BLOCKER_CONFIRMATION_20260607.md
```

Confirmed CoreB status:

```text
historical SOT/backtest = reproduced / allowed for reporting
live evaluator = blocked
same_count approximation = forbidden
```

### 2.5 CoreB cluster recovery was promoted to the top priority

The user correctly pointed out that proceeding without accurately reproducing CoreB clustering would make the full live evaluator work meaningless.

Created:

```text
docs/gold_v2/GOLD_V2_COREB_CLUSTER_RECOVERY_STRICT_PLAN_20260607.md
```

Updated:

```text
docs/gold_v2/GOLD_V2_25A_COREA_COREB_MEDIUM_LIVE_EVALUATOR_READINESS_AUDIT_SPEC_20260607.md
```

Updated policy:

```text
Primary next: 25B_COREB_CLUSTER_SOURCE_RECOVERY_AUDIT_ONLY
Secondary: 25C_MEDIUM_FEATURE_ASOF_PARITY_AND_TIER2_RECONCILIATION_AUDIT_ONLY
Parallel: 25D_COREA_A_GATE_EXECUTABLE_SOURCE_FREEZE_AUDIT_ONLY
```

## 3. Current project state after this chat

### 3.1 24-series state

```text
state = PAUSED_AT_24AF
last_completed_step = 24AF_SOURCE_RECOVERY_PRE_EXECUTION_FINAL_DECISION_ROUTING_AUDIT_ONLY
24AG_not_started = true
```

24AF routed to 24AG, but this must not be interpreted as approval to run source recovery.

The route only means:

```text
A later dry-run execution plan audit branch exists.
It is not source recovery execution.
```

### 3.2 CoreA state

```text
historical SOT = ready
live evaluator = blocked
```

Known blockers:

```text
A gate is not executable/frozen:
  tail_hard
  top5
  all-consensus
  stack KEEP

B/C need:
  live feature/asof parity
  CoreA rejected ordering
  fold4/A gate ordering
```

Do not approximate CoreA A gate.

### 3.3 CoreB state

```text
historical SOT/backtest = reproduced
live evaluator = blocked
full portfolio live path = blocked until cluster/same_count/membership recovered
```

CoreB depends on:

```text
same_count >= 15
cluster_id / row-level cluster membership semantics
RR125 BUY confluence source universe
```

Forbidden substitutes:

```text
static time windows
raw exact entry_time counts
interval cover counts
connected interval components
heuristic confluence counts
feature-rule hit counts pretending to be same_count
post-hoc fitting to 125 rows
```

### 3.4 MEDIUM state

```text
historical SOT replay = OK
live evaluator = blocked
partial live path = possible after feature/asof parity and TIER2 reconciliation
full portfolio dependency = CoreB and CoreA HIGH arbitration unresolved
```

Known positives:

```text
MEDIUM arbitration replay matched final SOT.
final_medium_rows = 87
recomputed_medium_rows = 87
missing_final_keys = 0
extra_recomputed_keys = 0
```

Known blockers:

```text
TIER2_HVT manifest mismatch:
  source rows 31, mismatch rows 12
  final SOT TIER2 rows 13, mismatch rows 11

feature/asof parity unproven:
  range96
  trend_eff96
  ret96
  tr_mean_32
  regime

HIGH arbitration dependency remains because CoreA/CoreB live status is incomplete.
```

## 4. How to reproduce the original CoreB cluster

Do not attempt to infer it from OHLC by heuristics.

The only acceptable path is source-of-truth recovery:

```text
Find original script and/or original row-level artifacts that generated same_count / cluster_id / membership.
Then replay them and prove exact parity against CoreB historical SOT.
```

Valid evidence includes at least one of:

```text
1. Original CoreB same_count / clustering script
2. Original cluster_id / cluster membership generator
3. Row-level cluster membership ledger
4. same_count_source_universe intermediate CSV with sufficient membership semantics
5. Complete per-CoreB-row evidence package explaining same_count / cluster_id / membership derivation
```

Expected parity if recovered:

```text
expected CoreB RR125 rows = 125
replayed rows = 125
missing source keys = 0
extra replay keys = 0
same_count exact match rows = 125
cluster_id or membership exact match rows = 125, if cluster_id is part of source truth
```

If this cannot be proven, CoreB remains historical-only and must not be used by a live evaluator.

## 5. Next work in the new chat

Start with 25A only as a readiness package, then proceed to 25B.

### 5.1 25A

Step:

```text
25A_COREA_COREB_MEDIUM_LIVE_EVALUATOR_READINESS_AUDIT_ONLY
```

Expected output folder:

```text
Files/FX_OUTPUTS/gold_v2_25a_corea_coreb_medium_live_evaluator_readiness_audit_only/
```

Expected artifacts:

```text
GOLD_V2_25A_COREA_COREB_MEDIUM_LIVE_EVALUATOR_READINESS_AUDIT_ONLY_REPORT.md
gold_v2_25a_core_component_readiness_matrix.csv
gold_v2_25a_live_evaluator_blocker_matrix.csv
gold_v2_25a_recommended_next_steps.csv
gold_v2_25a_safety_matrix.csv
gold_v2_25a_corea_coreb_medium_live_evaluator_readiness_summary.json
```

Expected status:

```text
COREA_COREB_MEDIUM_LIVE_EVALUATOR_READINESS_REVIEW_READY_AUDIT_ONLY_COREB_CLUSTER_RECOVERY_REQUIRED
```

### 5.2 25B

Step:

```text
25B_COREB_CLUSTER_SOURCE_RECOVERY_AUDIT_ONLY
```

Purpose:

```text
Search repository and known artifacts for original CoreB cluster/same_count/membership source-of-truth evidence.
```

Search terms:

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

Expected artifacts:

```text
GOLD_V2_25B_COREB_CLUSTER_SOURCE_RECOVERY_AUDIT_ONLY_REPORT.md
gold_v2_25b_coreb_cluster_candidate_inventory.csv
gold_v2_25b_coreb_cluster_evidence_matrix.csv
gold_v2_25b_coreb_replay_requirements.csv
gold_v2_25b_coreb_cluster_recovery_summary.json
```

Stop conditions:

```text
no original algorithm candidate is found
only audit-generated/post-hoc files are found
only summary-level cluster data exists without row membership
candidate algorithm cannot replay to 125 rows
same_count exact parity cannot be proven
any step tries to fit/approximate the cluster after seeing SOT rows
```

## 6. Do not do next

Do not proceed to 24AG now.
Do not run source recovery.
Do not mutate sources.
Do not finalize source identity.
Do not enable live evaluator final signal.
Do not send Discord.
Do not place MT5 orders.
Do not call AI API.
Do not connect live hook.
Do not approximate CoreB same_count.
Do not approximate CoreA A gate.
Do not treat MEDIUM feature hits as final signal before HIGH arbitration is resolved.

## 7. Suggested prompt for the next chat

```text
repo: knitanr-a11y/xauusd-signal-lab

Please read and continue from:
docs/gold_v2/NEXT_CHAT_HANDOFF_GOLD_V2_24AF_DONE_25B_COREB_CLUSTER_RECOVERY_PRIORITY_20260607.md

GOLD V2 remains audit-only.
Old GOLD/DISC8 remains quarantined.
Approximate reimplementation is prohibited.
Discord / MT5 / AI API / live hook / final signal remain OFF.
NO_SIGNAL must not notify Discord.

24-series source recovery chain is paused at 24AF.
Do not proceed to 24AG unless explicitly requested.

The user clarified that CoreB clustering must be accurately reproduced before the full CoreA/CoreB/MEDIUM live evaluator path is meaningful.
CoreB historical backtest is reproduced, but live evaluator remains blocked until same_count / cluster_id / membership source-of-truth is recovered.

Next task:
Implement 25A_COREA_COREB_MEDIUM_LIVE_EVALUATOR_READINESS_AUDIT_ONLY, then 25B_COREB_CLUSTER_SOURCE_RECOVERY_AUDIT_ONLY.
For 25B, search repo/artifacts for original CoreB same_count/cluster/membership source evidence and do not approximate.
```
