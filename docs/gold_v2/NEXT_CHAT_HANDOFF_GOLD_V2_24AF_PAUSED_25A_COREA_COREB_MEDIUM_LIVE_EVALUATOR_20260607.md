# NEXT CHAT HANDOFF — GOLD V2 24AF paused / 25A CoreA-CoreB-MEDIUM live evaluator refocus

Date: 2026-06-07
Repo: `knitanr-a11y/xauusd-signal-lab`

## 0. Start here

Read these documents first:

```text
docs/gold_v2/GOLD_V2_24AF_PAUSE_AND_CORE_LIVE_EVALUATOR_REFOCUS_20260607.md
docs/gold_v2/GOLD_V2_25A_COREA_COREB_MEDIUM_LIVE_EVALUATOR_READINESS_AUDIT_SPEC_20260607.md
docs/gold_v2/NEXT_CHAT_HANDOFF_GOLD_V2_COREA_COREB_MEDIUM_LIVE_RULES_20260603.md
docs/gold_v2/NEXT_CHAT_HANDOFF_GOLD_V2_13A_13D_MEDIUM_TIER2_RECONCILIATION_20260605.md
```

## 1. Absolute rules

GOLD V2 remains audit-only.

Do not enable:

```text
source recovery execution
source artifact mutation
source identity finalization
live final signal
Discord send
MT5 order
AI API
live hook
```

Old GOLD/DISC8 remains quarantined due suspected HTF open-time inconsistency.

Approximate reimplementation is prohibited.

NO_SIGNAL must not send Discord notification.

## 2. 24-series source-recovery chain status

24-series is paused at 24AF.

Last confirmed status:

```text
24AF_SOURCE_RECOVERY_PRE_EXECUTION_FINAL_DECISION_ROUTING_AUDIT_ONLY
SOURCE_RECOVERY_PRE_EXECUTION_FINAL_DECISION_ROUTED_AUDIT_ONLY_SOURCE_RECOVERY_EXECUTION_STILL_BLOCKED
```

Confirmed route:

```text
selected_decision_value = APPROVE_SOURCE_RECOVERY_PRE_EXECUTION_FOR_DRY_RUN_AUDIT_ONLY
route_id = ROUTE_APPROVE_TO_DRY_RUN_EXECUTION_PLAN_AUDIT_ONLY
routed_next_audit_step = 24AG_SOURCE_RECOVERY_DRY_RUN_EXECUTION_PLAN_AUDIT_ONLY
```

Important:

```text
24AG is not started.
Do not continue 24AG unless the user explicitly asks to resume source-recovery dry-run audit planning.
```

This pause is safe because every 24-series artifact remains audit-only and all forbidden actions remain false.

## 3. Refocus target

The user asked to return to the real goal:

```text
Make CoreA / CoreB / MEDIUM conditions usable by a live evaluator.
```

Therefore the next step is:

```text
25A_COREA_COREB_MEDIUM_LIVE_EVALUATOR_READINESS_AUDIT_ONLY
```

Purpose:

```text
Create a fresh readiness matrix for CoreA, CoreB, MEDIUM, and global arbitration/safety.
Do not implement live trading.
Do not approximate missing algorithms.
Do not use old GOLD/DISC8 as source of truth.
```

## 4. Current CoreA/CoreB/MEDIUM status

### Final SOT

```text
gold_v2_final_portfolio_2025_2026_sot_ledger.csv
total rows = 529
2025 rows = 346
2026 rows = 183
```

Breakdown:

```text
CORE_A_CORE_B_CONFLUENCE       8
CORE_A_ONLY                  317
CORE_B_ONLY                  117
MEDIUM_RANGE96_REFINED        51
MEDIUM_TIER2_HVT              13
MEDIUM_VOL_TRMEAN32_REFINED   23
```

### CoreA

Current state:

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

Do not approximate the A gate.

### CoreB

Current state:

```text
historical SOT = allowed
live evaluator = blocked
```

Known blockers:

```text
same_count / cluster_id semantics are unrecovered.
Original clustering algorithm or row-level membership ledger is missing.
Candidate replay produced 7 rows instead of expected 125.
Approximate same_count is forbidden.
```

CoreB can remain historical-SOT-only until original cluster membership evidence is found.

### MEDIUM

Current state:

```text
historical SOT replay = OK
live evaluator = blocked
```

Known positives:

```text
MEDIUM arbitration replay matched final SOT.
final rows = 87
recomputed rows = 87
missing final keys = 0
extra recomputed keys = 0
```

Known blockers:

```text
TIER2_HVT manifest mismatch:
  source rows 31, mismatch rows 12
  final SOT TIER2 rows 13, mismatch rows 11

Feature/asof parity unproven:
  range96
  trend_eff96
  ret96
  tr_mean_32
  regime

HIGH arbitration dependency remains because CoreA/CoreB live status is incomplete.
```

## 5. Recommended next work

### 25A

Create a readiness audit output package:

```text
Files/FX_OUTPUTS/gold_v2_25a_corea_coreb_medium_live_evaluator_readiness_audit_only/
```

Expected outputs:

```text
GOLD_V2_25A_COREA_COREB_MEDIUM_LIVE_EVALUATOR_READINESS_AUDIT_ONLY_REPORT.md
gold_v2_25a_core_component_readiness_matrix.csv
gold_v2_25a_live_evaluator_blocker_matrix.csv
gold_v2_25a_recommended_next_steps.csv
gold_v2_25a_safety_matrix.csv
gold_v2_25a_corea_coreb_medium_live_evaluator_readiness_summary.json
```

Expected high-level recommendation:

```text
Primary next:
  25B_MEDIUM_FEATURE_ASOF_PARITY_AND_TIER2_RECONCILIATION_AUDIT_ONLY

Secondary:
  25C_COREA_A_GATE_EXECUTABLE_SOURCE_FREEZE_AUDIT_ONLY

Blocked:
  CoreB live evaluator until original clustering / row-level membership evidence exists
```

## 6. What not to do next

Do not continue 24AG now.
Do not turn any signal live.
Do not send Discord.
Do not place MT5 orders.
Do not call AI API.
Do not invent CoreB same_count.
Do not approximate CoreA A gate.
Do not treat MEDIUM feature hits as final signal before HIGH arbitration policy is resolved.

## 7. Suggested opening instruction for a new chat

```text
repo: knitanr-a11y/xauusd-signal-lab

Please read:
1. docs/gold_v2/GOLD_V2_24AF_PAUSE_AND_CORE_LIVE_EVALUATOR_REFOCUS_20260607.md
2. docs/gold_v2/GOLD_V2_25A_COREA_COREB_MEDIUM_LIVE_EVALUATOR_READINESS_AUDIT_SPEC_20260607.md
3. docs/gold_v2/NEXT_CHAT_HANDOFF_GOLD_V2_24AF_PAUSED_25A_COREA_COREB_MEDIUM_LIVE_EVALUATOR_20260607.md

24-series source recovery chain is paused at 24AF.
Do not proceed to 24AG unless explicitly requested.
Return to CoreA/CoreB/MEDIUM live evaluator body work.
GOLD V2 remains audit-only.
Old GOLD/DISC8 remains quarantined.
Approximate reimplementation is prohibited.
Discord/MT5/AI/live hook/final signal remain OFF.
NO_SIGNAL must not notify Discord.

Next task:
Implement 25A_COREA_COREB_MEDIUM_LIVE_EVALUATOR_READINESS_AUDIT_ONLY.
Start by writing/using the 25A spec and generate readiness/blocker/recommended-next-step/safety artifacts.
```
