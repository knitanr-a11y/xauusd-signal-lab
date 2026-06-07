# NEXT CHAT HANDOFF ADDENDUM — strict guardrails for 25A/25B CoreB cluster recovery

Date: 2026-06-07
Repo: `knitanr-a11y/xauusd-signal-lab`

## 1. Why this addendum exists

This addendum is a drift-prevention guardrail for the next chat.

The main handoff is:

```text
docs/gold_v2/NEXT_CHAT_HANDOFF_GOLD_V2_24AF_DONE_25B_COREB_CLUSTER_RECOVERY_PRIORITY_20260607.md
```

Read this addendum immediately after the main handoff.

The purpose is to prevent the next chat from accidentally:

```text
continuing 24AG
implementing Medium first and forgetting CoreB
approximating CoreB same_count
turning historical SOT rows into live signals
creating a live evaluator without CoreB cluster parity
sending Discord / MT5 / AI / live hook actions
```

## 2. Non-negotiable current state

```text
24-series source recovery chain = PAUSED_AT_24AF
24AF completed = true
24AG started = false
GOLD V2 mode = audit-only
old GOLD/DISC8 = quarantined
external actions = disabled
final signal = disabled
```

24AF routed to:

```text
24AG_SOURCE_RECOVERY_DRY_RUN_EXECUTION_PLAN_AUDIT_ONLY
```

But this route is **not** permission to continue 24AG now.

The next chat must not continue 24AG unless the user explicitly asks to resume the source-recovery dry-run branch.

## 3. Main objective now

The user clarified the real goal:

```text
Make CoreA / CoreB / MEDIUM conditions usable by a live evaluator.
```

The user also clarified:

```text
If CoreB is included, the original CoreB cluster / same_count / membership must be reproduced accurately.
Proceeding without this makes the full live evaluator path meaningless.
```

Therefore the full-portfolio live evaluator path is blocked until CoreB cluster recovery is solved or the user later explicitly decides to exclude CoreB from live.

## 4. Correct next order

Do this:

```text
1. 25A_COREA_COREB_MEDIUM_LIVE_EVALUATOR_READINESS_AUDIT_ONLY
2. 25B_COREB_CLUSTER_SOURCE_RECOVERY_AUDIT_ONLY
```

25A is only a readiness / blocker / safety matrix package.

25A must not become a detour into Medium implementation.

25A expected recommendation must keep:

```text
Primary next = 25B_COREB_CLUSTER_SOURCE_RECOVERY_AUDIT_ONLY
Secondary = 25C_MEDIUM_FEATURE_ASOF_PARITY_AND_TIER2_RECONCILIATION_AUDIT_ONLY
Parallel = 25D_COREA_A_GATE_EXECUTABLE_SOURCE_FREEZE_AUDIT_ONLY
```

## 5. CoreB is the critical blocker

CoreB current state:

```text
historical backtest = reproduced
historical SOT reporting = allowed
live evaluator generation from OHLC = blocked
```

Reason:

```text
same_count / cluster_id / row-level membership source-of-truth generation evidence is missing or insufficient.
```

CoreB RR125_BUY_CONFLUENCE depends on:

```text
same_count >= 15
cluster_id / row-level cluster membership semantics
RR125 BUY confluence source universe
```

## 6. Forbidden CoreB shortcuts

The next chat must not replace original CoreB clustering with:

```text
static time windows
raw exact entry_time counts
interval cover counts
connected interval components
heuristic confluence counts
feature-rule hit counts pretending to be same_count
post-hoc fitting to 125 rows
manual reconstruction after seeing target SOT rows
```

Any such implementation must be classified as:

```text
APPROXIMATE_REIMPLEMENTATION_FORBIDDEN
```

## 7. Valid CoreB recovery evidence

25B may only unblock CoreB if it finds source-of-truth evidence such as:

```text
1. Original CoreB same_count / clustering script
2. Original cluster_id / cluster membership generator
3. Row-level cluster membership ledger
4. same_count_source_universe intermediate CSV with sufficient membership semantics
5. Complete per-CoreB-row evidence package explaining same_count / cluster_id / membership derivation
```

If evidence is found, do not immediately trust it.

It must be reviewed as:

```text
original source vs audit-generated/post-hoc
contains row-level membership vs summary-only
can replay exact same_count semantics
can reproduce CoreB RR125 target rows
```

## 8. CoreB parity gate

CoreB live evaluator remains blocked unless parity passes:

```text
expected CoreB RR125 rows = 125
replayed rows = 125
missing source keys = 0
extra replay keys = 0
same_count exact match rows = 125
cluster_id or membership exact match rows = 125, if cluster_id is part of source truth
```

If any of these fail, output status must remain blocked.

## 9. 25B expected artifacts

25B should produce:

```text
GOLD_V2_25B_COREB_CLUSTER_SOURCE_RECOVERY_AUDIT_ONLY_REPORT.md
gold_v2_25b_coreb_cluster_candidate_inventory.csv
gold_v2_25b_coreb_cluster_evidence_matrix.csv
gold_v2_25b_coreb_replay_requirements.csv
gold_v2_25b_coreb_cluster_recovery_summary.json
```

Candidate inventory should classify every hit into clear buckets such as:

```text
ORIGINAL_ALGORITHM_CANDIDATE
ROW_LEVEL_MEMBERSHIP_CANDIDATE
SOURCE_UNIVERSE_CANDIDATE
SUMMARY_ONLY_NOT_ENOUGH
AUDIT_GENERATED_OR_POST_HOC
MENTIONS_KEYWORDS_ONLY
DOC_ONLY
NOT_RELEVANT
```

## 10. CoreA and Medium handling while CoreB is blocked

CoreA:

```text
historical SOT = ready
live evaluator = blocked
reason = A gate not executable/frozen
forbidden = approximate tail_hard/top5/all-consensus/stack KEEP
```

Medium:

```text
historical SOT replay = OK
live evaluator = blocked
reason = TIER2_HVT mismatch + feature/asof parity + HIGH arbitration dependency
```

Medium work may continue later, but not as a substitute for CoreB recovery if the user wants the full CoreA/CoreB/MEDIUM portfolio live.

## 11. Safety flags that must remain false

Every 25A/25B output must keep:

```text
source_recovery_execution_allowed_now = false
source_mutation_allowed = false
source_identity_finalization_allowed_now = false
live_evaluator_final_signal_allowed = false
discord_send_allowed = false
mt5_order_allowed = false
ai_api_allowed = false
live_hook_allowed = false
```

## 12. Correct first prompt for next chat

Use this exact starter in the next chat:

```text
repo: knitanr-a11y/xauusd-signal-lab

Please read these first and continue from them:
1. docs/gold_v2/NEXT_CHAT_HANDOFF_GOLD_V2_24AF_DONE_25B_COREB_CLUSTER_RECOVERY_PRIORITY_20260607.md
2. docs/gold_v2/NEXT_CHAT_HANDOFF_GOLD_V2_24AF_DONE_25B_COREB_CLUSTER_RECOVERY_PRIORITY_GUARDRAILS_ADDENDUM_20260607.md
3. docs/gold_v2/GOLD_V2_COREB_CLUSTER_RECOVERY_STRICT_PLAN_20260607.md
4. docs/gold_v2/GOLD_V2_25A_COREA_COREB_MEDIUM_LIVE_EVALUATOR_READINESS_AUDIT_SPEC_20260607.md

GOLD V2 remains audit-only.
24-series source recovery chain is paused at 24AF.
Do not proceed to 24AG unless explicitly requested.
Old GOLD/DISC8 remains quarantined.
Approximate reimplementation is prohibited.
Discord / MT5 / AI API / live hook / final signal remain OFF.
NO_SIGNAL must not notify Discord.

The user clarified that CoreB clustering must be accurately reproduced before the full CoreA/CoreB/MEDIUM live evaluator path is meaningful.
CoreB historical backtest is reproduced, but live evaluator remains blocked until same_count / cluster_id / membership source-of-truth is recovered.

Next task:
Implement 25A_COREA_COREB_MEDIUM_LIVE_EVALUATOR_READINESS_AUDIT_ONLY as a readiness package only.
Then implement 25B_COREB_CLUSTER_SOURCE_RECOVERY_AUDIT_ONLY.
For 25B, search repo/artifacts for original CoreB same_count/cluster/membership source evidence and do not approximate.
```
