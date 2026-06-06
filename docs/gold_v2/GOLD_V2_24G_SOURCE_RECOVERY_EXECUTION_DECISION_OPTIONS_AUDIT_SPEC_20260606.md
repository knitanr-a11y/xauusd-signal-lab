# GOLD V2 24G source recovery execution decision options audit-only spec

Date: 2026-06-06
Repo: `knitanr-a11y/xauusd-signal-lab`
Step: `24G_SOURCE_RECOVERY_EXECUTION_DECISION_OPTIONS_AUDIT_ONLY`
Mode: audit-only

## Purpose

24G reads the successful 24F artifact-list review and prepares exact human decision options for the later source recovery execution decision.

24G does not choose any option.

24G does not execute source recovery.

24G does not approve source recovery.

24G only writes an options matrix and a fillable human decision template for a later intake step.

## Boundary

24G must not execute, enable, prepare, approve, or finalize:

- source recovery execution
- source recovery approval
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

`FX_OUTPUTS/gold_v2_24f_source_recovery_artifact_list_review_audit_only`

Required 24F files:

| role | file | expected |
| --- | --- | --- |
| 24F report | `GOLD_V2_24F_SOURCE_RECOVERY_ARTIFACT_LIST_REVIEW_AUDIT_ONLY_REPORT.md` | exists |
| 24F summary | `gold_v2_24f_source_recovery_artifact_list_review_summary.json` | status is `SOURCE_RECOVERY_ARTIFACT_LIST_REVIEW_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_EXECUTION_STILL_BLOCKED` |
| 24F input audit | `gold_v2_24f_input_audit.csv` | exists and required inputs present |
| 24F artifact reference review | `gold_v2_24f_artifact_reference_review.csv` | 3 reviewable artifact rows |
| 24F content review checks | `gold_v2_24f_artifact_content_review_checks.csv` | zero STOP rows |
| 24F integrated checks | `gold_v2_24f_integrated_checks.csv` | zero STOP rows |
| 24F required next gates | `gold_v2_24f_required_next_gates.csv` | only `24G_SOURCE_RECOVERY_EXECUTION_DECISION_OPTIONS_AUDIT_ONLY` allowed |
| 24F safety matrix | `gold_v2_24f_safety_matrix.csv` | zero STOP rows |

## Decision values prepared by 24G

Allowed values for the later human decision intake:

| value | meaning | execution_allowed_now |
| --- | --- | --- |
| `KEEP_SOURCE_RECOVERY_BLOCKED` | Keep all source recovery execution blocked. | false |
| `REQUEST_MORE_SOURCE_RECOVERY_AUDIT` | Request additional audit evidence before any execution decision. | false |
| `REJECT_SOURCE_RECOVERY_EXECUTION` | Explicitly reject source recovery execution. | false |
| `APPROVE_SOURCE_RECOVERY_EXECUTION` | Candidate exact approval value for a later intake/routing step. 24G does not apply it. | false in 24G |

Important: `REQUEST_MORE_SOURCE_RECOVERY_AUDIT` is not approval.

Important: `APPROVE_SOURCE_RECOVERY_EXECUTION` written in the 24G options matrix is not approval by itself. It becomes meaningful only if the user independently places that exact value into the later 24H human decision input and 24H/24I routing audits accept it.

## Outputs

Output folder:

`FX_OUTPUTS/gold_v2_24g_source_recovery_execution_decision_options_audit_only`

Required outputs:

| output | purpose |
| --- | --- |
| `gold_v2_24g_input_audit.csv` | required 24F input file existence |
| `gold_v2_24g_decision_options.csv` | allowed decision values and consequences |
| `gold_v2_24g_human_decision_input_template.json` | fillable later-decision input template |
| `gold_v2_24g_integrated_checks.csv` | upstream and 24G boundary checks |
| `gold_v2_24g_required_next_gates.csv` | audit-only next-step gates; all forbidden actions blocked |
| `gold_v2_24g_safety_matrix.csv` | safety gates and external action proof |
| `gold_v2_24g_source_recovery_execution_decision_options_summary.json` | machine summary |
| `GOLD_V2_24G_SOURCE_RECOVERY_EXECUTION_DECISION_OPTIONS_AUDIT_ONLY_REPORT.md` | human report |

## Success status

If all 24F upstream checks pass and 24G writes decision options:

`SOURCE_RECOVERY_EXECUTION_DECISION_OPTIONS_READY_AUDIT_ONLY_SOURCE_RECOVERY_EXECUTION_STILL_BLOCKED`

If required 24F files or safety gates fail:

`24G_STOP_SOURCE_RECOVERY_EXECUTION_DECISION_OPTIONS_INPUTS_OR_SAFETY`

## Next step policy

After 24G success, the only allowed next audit step is:

`24H_SOURCE_RECOVERY_EXECUTION_DECISION_INTAKE_AUDIT_ONLY`

24H may read a human-filled decision input and validate whether it exactly matches one allowed value.

24H still must not execute source recovery.

Actual source recovery execution, if ever allowed, requires a later routing/execution audit step and an exact explicit human approval value. 24G does not grant it.

## Non-actions

24G does not implement:

- source recovery execution
- source recovery approval
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
