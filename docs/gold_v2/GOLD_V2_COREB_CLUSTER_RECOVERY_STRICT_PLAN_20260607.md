# GOLD V2 CoreB cluster recovery strict plan

Date: 2026-06-07
Repo: `knitanr-a11y/xauusd-signal-lab`

## 1. User direction

The user correctly pointed out that proceeding without reproducing the original CoreB cluster / same_count semantics would make the live evaluator work meaningless for the full CoreA/CoreB/MEDIUM portfolio.

Therefore, CoreB cluster recovery must become a hard prerequisite for any full-portfolio live evaluator path that includes CoreB.

## 2. Current facts

CoreB RR125_BUY_CONFLUENCE historical backtest / historical SOT is reproduced.

However, OHLC-derived live evaluator regeneration is blocked because the source-of-truth generation basis for:

```text
same_count
cluster_id
row-level cluster membership
```

is missing or insufficient.

## 3. What must not be done

Do not approximate CoreB clustering.

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

A live evaluator using any of the above as replacement would not be source-of-truth compliant.

## 4. What would count as valid recovery

CoreB can only be unblocked if at least one of the following is found and audited:

```text
1. Original script that generated same_count / cluster_id / cluster membership
2. Original intermediate CSV with row-level cluster membership
3. Original same_count_source_universe with enough fields to reconstruct membership exactly
4. Original cluster ledger mapping each CoreB candidate row to cluster_id and member rows
5. A commit/file path that proves the exact algorithm and lets it replay to the 125 CoreB historical rows
```

The recovery must prove parity against historical CoreB SOT:

```text
expected CoreB RR125 rows = 125
replayed rows = 125
missing source keys = 0
extra replay keys = 0
same_count exact match rows = 125
cluster_id or membership exact match rows = 125, if cluster_id is part of source truth
```

If cluster_id is not available but same_count is derived exactly from a recovered algorithm, the recovered algorithm and its membership semantics must be documented and replayable.

## 5. New priority policy

Previous 25A draft recommended MEDIUM first because MEDIUM arbitration replay already matched SOT.

That is useful for partial live evaluator work, but not sufficient for the full portfolio if CoreB remains part of the desired live system.

Updated priority:

```text
Primary: 25B_COREB_CLUSTER_SOURCE_RECOVERY_AUDIT_ONLY
Secondary: 25C_MEDIUM_FEATURE_ASOF_PARITY_AND_TIER2_RECONCILIATION_AUDIT_ONLY
Parallel: 25D_COREA_A_GATE_EXECUTABLE_SOURCE_FREEZE_AUDIT_ONLY
```

CoreB cannot be live-mapped until cluster recovery passes.

## 6. Expected 25B scope

25B should be a focused CoreB cluster source recovery audit.

It should search for and inventory candidate evidence artifacts using names / keywords such as:

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

It should produce:

```text
GOLD_V2_25B_COREB_CLUSTER_SOURCE_RECOVERY_AUDIT_ONLY_REPORT.md
gold_v2_25b_coreb_cluster_candidate_inventory.csv
gold_v2_25b_coreb_cluster_evidence_matrix.csv
gold_v2_25b_coreb_replay_requirements.csv
gold_v2_25b_coreb_cluster_recovery_summary.json
```

## 7. Stop conditions

25B must stop if:

```text
no original algorithm candidate is found
only audit-generated/post-hoc files are found
only summary-level cluster data exists without row membership
candidate algorithm cannot replay to 125 rows
same_count exact parity cannot be proven
any step tries to fit/approximate the cluster after seeing SOT rows
```

## 8. Safety

This is still audit-only.

Still forbidden:

```text
source recovery execution
source mutation
source identity finalization
live final signal
Discord send
MT5 order
AI API
live hook
```
