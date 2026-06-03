# GOLD V2 12H_CONSOLIDATE_LIVE_EVALUATOR_MAPPING_STATUS_AUDIT_ONLY specification

Date: 2026-06-03  
Repo: `knitanr-a11y/xauusd-signal-lab`

## 1. Purpose

12H runs after 12G.

12G can make CoreB mapping-ready in an audit-only final-signal-blocked state:

```text
CoreB status = MAPPING_READY_AUDIT_ONLY_FINAL_SIGNAL_BLOCKED
CoreB unmapped_condition_count = 0
CoreB live_evaluator_ready = true
CoreB final_signal_allowed = false
```

12H consolidates the current CoreA/CoreB/MEDIUM mapping JSONs into one status report.

This is a read-only audit step. It does not modify any mapping JSON and does not connect step 13.

## 2. Inputs

Default inputs:

```text
configs/gold_v2/gold_v2_coreA_coreB_medium_policy_20260603.json
configs/gold_v2/live_evaluator_mapping_coreA_20260603.json
configs/gold_v2/live_evaluator_mapping_coreB_20260603.json
configs/gold_v2/live_evaluator_mapping_medium_20260603.json
configs/gold_v2/frozen_coreB_live_evaluator_source_definition_20260603.json
```

## 3. Output folder

Default:

```text
Files/FX_OUTPUTS/gold_v2_live_evaluator_mapping_consolidated_status_audit_only
```

Generated files:

```text
GOLD_V2_LIVE_EVALUATOR_MAPPING_CONSOLIDATED_STATUS_AUDIT_ONLY_REPORT.md
gold_v2_live_evaluator_mapping_consolidated_status_summary.json
gold_v2_live_evaluator_mapping_component_status.csv
gold_v2_live_evaluator_mapping_remaining_blockers.csv
gold_v2_live_evaluator_mapping_consolidated_audit_checks.csv
```

## 4. Expected current result

Expected current consolidated status after 12G:

```text
PARTIAL_MAPPING_COREB_READY_COREA_MEDIUM_BLOCKED_AUDIT_ONLY
```

Expected component state:

```text
CoreA  = blocked / not ready
CoreB  = audit mapping-ready but final-signal blocked
MEDIUM = feature-gate-only / blocked by high arbitration
```

Expected global state:

```text
live_evaluator_connection_allowed = false
final_signal_allowed = false
step13_allowed = false
notification_should_send = false
```

## 5. Remaining blockers

12H must report blockers including at least:

```text
CoreA still has unmapped conditions or is not live-evaluator-ready.
MEDIUM cannot become final signal before CoreA/CoreB arbitration.
CoreB is audit mapping-ready only and cannot independently enable final signal.
External actions remain OFF.
Step 13 remains blocked.
```

## 6. Non-negotiable guards

12H must not:

```text
modify CoreA/CoreB/MEDIUM mapping JSON
connect step 13
create final signals
send Discord notifications
place MT5 orders
call AI API
call live hooks
notify on NO_SIGNAL
```

## 7. BAT specification

BAT:

```text
scripts\gold_v2_runtime\bat\12H_CONSOLIDATE_LIVE_EVALUATOR_MAPPING_STATUS_AUDIT_ONLY.bat
```

Executed command:

```text
python scripts\gold_v2_runtime\consolidate_gold_v2_live_evaluator_mapping_status_audit_only.py %*
```

Exit codes:

| Code | Meaning |
|---:|---|
| 0 | Consolidated audit completed and outputs were written. |
| 2 | Required mapping/policy file missing or policy safety failure. |
| other | Unexpected runtime error. |

## 8. Next step after 12H

After 12H, do not connect step 13.

The next correct engineering branch is either:

1. Resolve CoreA source definition gaps, or
2. Create a live evaluator preflight that proves mapped CoreB predicates can be evaluated against current feature columns without producing signals.

Final signal remains blocked until CoreA/arbitration/preflight are explicitly resolved.
