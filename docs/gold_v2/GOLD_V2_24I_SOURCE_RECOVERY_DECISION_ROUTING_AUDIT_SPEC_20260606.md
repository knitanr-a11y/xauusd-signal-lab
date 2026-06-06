# GOLD V2 24I decision routing audit-only spec

Date: 2026-06-06
Step: `24I_SOURCE_RECOVERY_EXECUTION_DECISION_ROUTING_AUDIT_ONLY`
Mode: audit-only

## Purpose

24I reads the validated 24H human decision and routes it to the next audit-only gate.

24I is a routing step only. It does not run recovery, does not finalize identity, and does not enable live or external actions.

## Inputs

Input folder:

`FX_OUTPUTS/gold_v2_24h_source_recovery_execution_decision_intake_audit_only`

Required files:

- `GOLD_V2_24H_SOURCE_RECOVERY_EXECUTION_DECISION_INTAKE_AUDIT_ONLY_REPORT.md`
- `gold_v2_24h_source_recovery_execution_decision_intake_summary.json`
- `gold_v2_24h_human_decision_input.json`
- `gold_v2_24h_input_audit.csv`
- `gold_v2_24h_human_decision_intake_result.csv`
- `gold_v2_24h_integrated_checks.csv`
- `gold_v2_24h_required_next_gates.csv`
- `gold_v2_24h_safety_matrix.csv`

Expected 24H status:

`SOURCE_RECOVERY_EXECUTION_DECISION_INTAKE_VALIDATED_AUDIT_ONLY_SOURCE_RECOVERY_EXECUTION_STILL_BLOCKED`

## Route map

| 24H selected value | 24I route | next audit-only gate |
| --- | --- | --- |
| `KEEP_SOURCE_RECOVERY_BLOCKED` | `ROUTE_KEEP_BLOCKED` | `24J_SOURCE_RECOVERY_BLOCKED_STATE_RECORD_AUDIT_ONLY` |
| `REQUEST_MORE_SOURCE_RECOVERY_AUDIT` | `ROUTE_REQUEST_MORE_AUDIT` | `24J_SOURCE_RECOVERY_REQUEST_MORE_AUDIT_RESOLUTION_AUDIT_ONLY` |
| `REJECT_SOURCE_RECOVERY_EXECUTION` | `ROUTE_REJECT_EXECUTION` | `24J_SOURCE_RECOVERY_REJECTION_RECORD_AUDIT_ONLY` |
| `APPROVE_SOURCE_RECOVERY_EXECUTION` | `ROUTE_APPROVE_TO_PLAN_AUDIT_ONLY` | `24J_SOURCE_RECOVERY_EXECUTION_PLAN_AUDIT_ONLY` |

The approve route still does not run anything. It only allows a later plan/preflight audit.

## Outputs

Output folder:

`FX_OUTPUTS/gold_v2_24i_source_recovery_execution_decision_routing_audit_only`

Outputs:

- `gold_v2_24i_input_audit.csv`
- `gold_v2_24i_decision_route.csv`
- `gold_v2_24i_integrated_checks.csv`
- `gold_v2_24i_required_next_gates.csv`
- `gold_v2_24i_safety_matrix.csv`
- `gold_v2_24i_source_recovery_execution_decision_routing_summary.json`
- `GOLD_V2_24I_SOURCE_RECOVERY_EXECUTION_DECISION_ROUTING_AUDIT_ONLY_REPORT.md`

## Success status

`SOURCE_RECOVERY_EXECUTION_DECISION_ROUTED_AUDIT_ONLY_SOURCE_RECOVERY_EXECUTION_STILL_BLOCKED`

## Stop status

`24I_STOP_SOURCE_RECOVERY_EXECUTION_DECISION_ROUTING_INPUTS_OR_SAFETY`

## Required safety

24I keeps all non-audit actions blocked:

- source recovery run: false
- source identity finalization: false
- live evaluator/final signal: false
- Discord/MT5/AI/live hook: false
- old GOLD/DISC8 remains quarantined
