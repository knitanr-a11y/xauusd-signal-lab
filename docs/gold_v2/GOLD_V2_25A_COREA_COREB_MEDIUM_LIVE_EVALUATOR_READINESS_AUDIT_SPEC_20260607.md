# GOLD V2 25A CoreA/CoreB/MEDIUM live evaluator readiness audit spec

Date: 2026-06-07
Step: `25A_COREA_COREB_MEDIUM_LIVE_EVALUATOR_READINESS_AUDIT_ONLY`
Mode: audit-only readiness review

## 1. Purpose

25A returns the project focus from the paused 24-series source-recovery chain to the CoreA/CoreB/MEDIUM live evaluator body work.

The goal is not to enable live trading yet.

The goal is to create a clear, auditable readiness matrix for:

```text
CoreA
CoreB
MEDIUM
GLOBAL arbitration / feature parity / safety
```

and decide which component can be safely mapped to live evaluator work next without approximate reimplementation.

Important update:

```text
CoreB cluster recovery is now the primary blocker for the full CoreA/CoreB/MEDIUM live evaluator path.
Proceeding with Medium-only work is still possible as a partial evaluator, but the full portfolio cannot be considered meaningful if CoreB same_count / cluster_id / membership semantics remain unrecovered.
```

## 2. Non-goals

25A must not:

```text
run source recovery
mutate source artifacts
finalize source identity
enable live evaluator as final signal
send Discord
place MT5 orders
call AI API
connect live hook
```

NO_SIGNAL Discord notification remains forbidden.

## 3. Required reference documents

25A must use these as current context:

```text
docs/gold_v2/GOLD_V2_24AF_PAUSE_AND_CORE_LIVE_EVALUATOR_REFOCUS_20260607.md
docs/gold_v2/GOLD_V2_COREB_LIVE_EVALUATOR_BLOCKER_CONFIRMATION_20260607.md
docs/gold_v2/GOLD_V2_COREB_CLUSTER_RECOVERY_STRICT_PLAN_20260607.md
docs/gold_v2/NEXT_CHAT_HANDOFF_GOLD_V2_COREA_COREB_MEDIUM_LIVE_RULES_20260603.md
docs/gold_v2/NEXT_CHAT_HANDOFF_GOLD_V2_13A_13D_MEDIUM_TIER2_RECONCILIATION_20260605.md
```

## 4. Current known status

### Final portfolio SOT

```text
gold_v2_final_portfolio_2025_2026_sot_ledger.csv
total_rows = 529
2025_rows = 346
2026_rows = 183
```

Source breakdown:

```text
CORE_A_CORE_B_CONFLUENCE       8
CORE_A_ONLY                  317
CORE_B_ONLY                  117
MEDIUM_RANGE96_REFINED        51
MEDIUM_TIER2_HVT              13
MEDIUM_VOL_TRMEAN32_REFINED   23
```

External actions remain off.

### CoreA

Current status:

```text
historical_sot = ready
live_evaluator = blocked
```

Known blockers:

```text
A gate not executable/frozen:
  tail_hard
  top5
  all-consensus
  stack KEEP

B/C are partially executable but require:
  live feature/asof parity
  CoreA rejected ordering
  fold4/A gate ordering
```

25A must not approximate A gate.

### CoreB

Current status:

```text
historical_sot = reproduced / allowed
live_evaluator = blocked
full_portfolio_live_path = blocked_until_cluster_recovered
```

The prior-chat review confirmed the same conclusion as the repository audits:

```text
CoreB historical backtest is reproduced.
However, regenerating CoreB RR125_BUY_CONFLUENCE from OHLC as a live evaluator remains blocked because same_count / cluster_id / membership source-of-truth generation evidence is insufficient.
```

Known blockers:

```text
same_count / cluster_id semantics are not recovered.
Original clustering algorithm or row-level membership ledger is required.
Candidate replay produced 7 rows instead of 125.
Approximate same_count is forbidden.
```

25A must not reconstruct same_count by guessing windows/components.

CoreB 25A classification should be:

```text
component = CoreB RR125_BUY_CONFLUENCE
historical_status = REPRODUCED_HISTORICAL_SOT_ALLOWED
live_evaluator_status = BLOCKED_SOURCE_CLUSTER_MEMBERSHIP_REQUIRED
recommended_action = PRIORITIZE_25B_COREB_CLUSTER_SOURCE_RECOVERY_AUDIT_ONLY
```

### MEDIUM

Current status:

```text
historical_sot_replay = OK
live_evaluator = blocked
partial_live_path = possible_after_feature_asof_and_tier2_reconciliation
full_portfolio_dependency = CoreB and CoreA HIGH arbitration unresolved
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

## 5. 25A outputs

25A should produce:

```text
Files/FX_OUTPUTS/gold_v2_25a_corea_coreb_medium_live_evaluator_readiness_audit_only/
```

Required artifacts:

```text
GOLD_V2_25A_COREA_COREB_MEDIUM_LIVE_EVALUATOR_READINESS_AUDIT_ONLY_REPORT.md
gold_v2_25a_core_component_readiness_matrix.csv
gold_v2_25a_live_evaluator_blocker_matrix.csv
gold_v2_25a_recommended_next_steps.csv
gold_v2_25a_safety_matrix.csv
gold_v2_25a_corea_coreb_medium_live_evaluator_readiness_summary.json
```

## 6. Success status

Expected status:

```text
COREA_COREB_MEDIUM_LIVE_EVALUATOR_READINESS_REVIEW_READY_AUDIT_ONLY_COREB_CLUSTER_RECOVERY_REQUIRED
```

This does not mean live evaluator is enabled.
It only means the readiness matrix is complete and the CoreB cluster recovery priority is explicit.

## 7. Expected recommendation

Based on current evidence and the user direction, 25A is expected to recommend:

```text
Primary next: 25B_COREB_CLUSTER_SOURCE_RECOVERY_AUDIT_ONLY
Secondary: 25C_MEDIUM_FEATURE_ASOF_PARITY_AND_TIER2_RECONCILIATION_AUDIT_ONLY
Parallel: 25D_COREA_A_GATE_EXECUTABLE_SOURCE_FREEZE_AUDIT_ONLY
Blocked: full CoreA/CoreB/MEDIUM live evaluator until CoreB cluster/same_count/membership source-of-truth is recovered or CoreB is explicitly removed from the live portfolio by a later human decision.
```

Rationale:

```text
CoreB historical SOT is reproduced, but live regeneration is blocked by unrecovered same_count/cluster/membership semantics.
A full-portfolio live evaluator that includes CoreB is not meaningful without exact CoreB cluster recovery.
MEDIUM remains promising but is only a partial path unless HIGH/CoreB dependencies are resolved.
CoreA needs A gate executable freeze before live mapping.
```

## 8. Safety conditions

All outputs must explicitly keep:

```text
source_recovery_chain_status = PAUSED_AT_24AF
source_recovery_execution_allowed_now = false
source_mutation_allowed = false
source_identity_finalization_allowed_now = false
live_evaluator_final_signal_allowed = false
external_actions_allowed = false
old_gold_disc8_quarantined = true
```
