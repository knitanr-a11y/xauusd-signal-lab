# GOLD V2 24H source recovery execution decision intake audit-only spec

Date: 2026-06-06
Repo: `knitanr-a11y/xauusd-signal-lab`
Step: `24H_SOURCE_RECOVERY_EXECUTION_DECISION_INTAKE_AUDIT_ONLY`
Mode: audit-only

## Purpose

24H reads 24G audited decision options and, if supplied, a human/operator decision input.

24H only validates whether `selected_decision_value` exactly matches one value from the 24G allowed decision values.

24H does not choose a value.

24H does not execute source recovery.

24H does not approve source recovery by itself.

## Modes

### Template/wait mode

If the user/operator decision input file is missing, 24H writes a copyable template and stays blocked/waiting.

### Validation mode

If `gold_v2_24h_human_decision_input.json` exists in the 24H output folder, 24H validates:

- it contains `selected_decision_value`
- the value is exactly one of the 24G allowed values
- it does not set any forbidden execution/live/external flags to true

## Boundary

24H must not execute, enable, prepare, approve, or finalize:

- source recovery execution
- source identity finalization
- source identity recovery
- live evaluator
- live hook
- final signal
- Discord notification
- MT5 order
- AI API call
- OHLC replay/reconstruction
- approximate reimplementation

Old GOLD/DISC8 remain quarantined.

NO_SIGNAL must not send Discord.

## Inputs

Source-of-truth input folder:

`FX_OUTPUTS/gold_v2_24g_source_recovery_execution_decision_options_audit_only`

Required 24G files:

| role | file | expected |
| --- | --- | --- |
| 24G report | `GOLD_V2_24G_SOURCE_RECOVERY_EXECUTION_DECISION_OPTIONS_AUDIT_ONLY_REPORT.md` | exists |
| 24G summary | `gold_v2_24g_source_recovery_execution_decision_options_summary.json` | status is `SOURCE_RECOVERY_EXECUTION_DECISION_OPTIONS_READY_AUDIT_ONLY_SOURCE_RECOVERY_EXECUTION_STILL_BLOCKED` |
| 24G input audit | `gold_v2_24g_input_audit.csv` | exists and required inputs present |
| 24G decision options | `gold_v2_24g_decision_options.csv` | exactly 4 allowed options |
| 24G human decision template | `gold_v2_24g_human_decision_input_template.json` | exists |
| 24G integrated checks | `gold_v2_24g_integrated_checks.csv` | zero STOP rows |
| 24G required next gates | `gold_v2_24g_required_next_gates.csv` | only `24H_SOURCE_RECOVERY_EXECUTION_DECISION_INTAKE_AUDIT_ONLY` allowed |
| 24G safety matrix | `gold_v2_24g_safety_matrix.csv` | zero STOP rows |

Optional 24H user/operator input file:

`FX_OUTPUTS/gold_v2_24h_source_recovery_execution_decision_intake_audit_only/gold_v2_24h_human_decision_input.json`

## Allowed selected values

24H must derive these from 24G outputs, not hard-code an approval decision:

- `KEEP_SOURCE_RECOVERY_BLOCKED`
- `REQUEST_MORE_SOURCE_RECOVERY_AUDIT`
- `REJECT_SOURCE_RECOVERY_EXECUTION`
- `APPROVE_SOURCE_RECOVERY_EXECUTION`

Important: `REQUEST_MORE_SOURCE_RECOVERY_AUDIT` is not approval.

Important: `APPROVE_SOURCE_RECOVERY_EXECUTION` is only an intake value in 24H. It still must not execute recovery. Later routing/audit is required before any execution.

## Outputs

Output folder:

`FX_OUTPUTS/gold_v2_24h_source_recovery_execution_decision_intake_audit_only`

Required outputs:

| output | purpose |
| --- | --- |
| `gold_v2_24h_input_audit.csv` | required 24G input file existence plus optional user decision file state |
| `gold_v2_24h_human_decision_input_template.json` | copyable/fillable template for the human decision |
| `gold_v2_24h_human_decision_intake_result.csv` | validation result for the selected decision value |
| `gold_v2_24h_integrated_checks.csv` | upstream and 24H boundary checks |
| `gold_v2_24h_required_next_gates.csv` | audit-only next-step gates; all forbidden actions blocked |
| `gold_v2_24h_safety_matrix.csv` | safety gates and external action proof |
| `gold_v2_24h_source_recovery_execution_decision_intake_summary.json` | machine summary |
| `GOLD_V2_24H_SOURCE_RECOVERY_EXECUTION_DECISION_INTAKE_AUDIT_ONLY_REPORT.md` | human report |

## Status values

Template/wait mode:

`SOURCE_RECOVERY_EXECUTION_DECISION_INTAKE_TEMPLATE_READY_AUDIT_ONLY_DECISION_NOT_SUPPLIED_SOURCE_RECOVERY_EXECUTION_STILL_BLOCKED`

Valid decision supplied:

`SOURCE_RECOVERY_EXECUTION_DECISION_INTAKE_VALIDATED_AUDIT_ONLY_SOURCE_RECOVERY_EXECUTION_STILL_BLOCKED`

Invalid decision supplied:

`SOURCE_RECOVERY_EXECUTION_DECISION_INTAKE_INVALID_AUDIT_ONLY_SOURCE_RECOVERY_EXECUTION_STILL_BLOCKED`

Required 24G files or safety gate failure:

`24H_STOP_SOURCE_RECOVERY_EXECUTION_DECISION_INTAKE_INPUTS_OR_SAFETY`

## Next step policy

24H must not execute source recovery.

If no decision is supplied, the only allowed next step is:

`WAIT_FOR_24H_HUMAN_DECISION_INPUT`

If a valid decision is supplied, the only allowed next audit step is:

`24I_SOURCE_RECOVERY_EXECUTION_DECISION_ROUTING_AUDIT_ONLY`

24I still must not execute source recovery. It may only route the human decision to a later audit-only path.

## Non-actions

24H does not implement:

- source recovery execution
- source recovery approval by itself
- source identity finalization
- source identity recovery
- semantic acceptance as final source-of-truth
- live evaluator
- final signal
- Discord notification
- MT5 order
- AI API call
- live hook
- OHLC replay
- strategy/trade evaluation
