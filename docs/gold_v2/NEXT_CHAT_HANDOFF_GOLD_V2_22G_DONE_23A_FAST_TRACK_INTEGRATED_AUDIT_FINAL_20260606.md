# NEXT CHAT HANDOFF - GOLD V2 22G done / 23A fast-track integrated audit FINAL

Date: 2026-06-06
Repo: `knitanr-a11y/xauusd-signal-lab`

## Read this first

This is the single recommended handoff document for the next chat.

The next chat should not continue the fragmented 21A-22G meta-audit pattern.

The next chat should implement one integrated audit-only step:

`23A_REQUEST_MORE_AUDIT_RESOLUTION_MATRIX_INTEGRATED_AUDIT_ONLY`

## Current position

GOLD V2 is still audit-only.

Latest completed step:

`22G_ADDITIONAL_AUDIT_READ_ONLY_FINAL_HANDOFF_AUDIT_ONLY`

Latest completed status:

`ADDITIONAL_AUDIT_READ_ONLY_FINAL_HANDOFF_READY_REQUEST_MORE_AUDIT_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

Current review state:

`HUMAN_REVIEW_REQUEST_MORE_AUDIT_COMPLETE_AUDIT_ONLY`

Selected value / decision value:

`REQUEST_MORE_AUDIT`

Important: `REQUEST_MORE_AUDIT` is not source recovery approval.

## User preference and change in operating style

The user noticed that progress was too slow.

The user agreed to a faster approach:

- Keep safety checks.
- Stop splitting every audit into planning / draft / load / content / reconciliation / final / handoff.
- Use one integrated audit-only script when no real blocker requires a split.
- Prefer practical resolution outputs over self-referential meta-audit chains.

Therefore, do not create another 7-step chain for 23A.

## Hard prohibitions still active

Do not enable, execute, or prepare live use for any of the following unless a later explicit allowed value/gate and user instruction permits it:

- source recovery execution
- source identity finalization
- source identity recovery
- live evaluator
- live hook
- final signal
- Discord notification
- MT5 order
- AI API call

NO_SIGNAL must not send Discord.

Old GOLD / DISC8 remain quarantined because of suspected HTF open-time mismatch.

Approximate reimplementation is prohibited.

Source-of-truth audited artifacts must be preferred over approximation.

Do not treat silence, upload-only turns, or vague phrases such as `進めて` as source recovery approval.

Do not treat `REQUEST_MORE_AUDIT` as approval.

## Completed chain summary

The REQUEST_MORE_AUDIT additional audit package reached a read-only final handoff.

Completed steps:

- 21A additional audit planning
- 21B execution draft
- 21C draft load check
- 21D draft content check
- 21E scope reconciliation
- 21F scope final audit
- 21G read-only report
- 21H handoff
- 22A read-only planning
- 22B read-only execution draft
- 22C draft load check
- 22D draft content check
- 22E scope reconciliation
- 22F read-only final audit
- 22G final handoff

This chain remained audit-only and did not approve source recovery.

## 22G output state to rely on

Use 22G as the immediate upstream source.

Expected 22G output folder:

`FX_OUTPUTS/gold_v2_22g_additional_audit_read_only_final_handoff_audit_only`

Expected 22G files:

- `GOLD_V2_22G_ADDITIONAL_AUDIT_READ_ONLY_FINAL_HANDOFF_AUDIT_ONLY_REPORT.md`
- `GOLD_V2_22G_FINAL_HANDOFF_REQUEST_MORE_AUDIT_AUDIT_ONLY.md`
- `gold_v2_22g_additional_audit_read_only_final_handoff_summary.json`
- `gold_v2_22g_input_audit.csv`
- `gold_v2_22g_handoff_checks.csv`
- `gold_v2_22g_required_next_gates.csv`
- `gold_v2_22g_safety_matrix.csv`

Expected upstream status:

`ADDITIONAL_AUDIT_READ_ONLY_FINAL_HANDOFF_READY_REQUEST_MORE_AUDIT_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

Expected upstream summary conditions:

- `audit_only == true`
- `selected_value == REQUEST_MORE_AUDIT`
- `decision_value == REQUEST_MORE_AUDIT`
- `final_handoff_ready == true`
- `source_recovery_approved == false`
- `source_recovery_executed == false`
- `source_identity_finalized == false`
- `source_identity_recovered == false`
- `live_or_final_implementation_allowed == false`
- `live_enabled == false`
- `final_signal_allowed == false`
- all external actions false
- `total_stop_rows == 0`

## Next step: 23A

Step name:

`23A_REQUEST_MORE_AUDIT_RESOLUTION_MATRIX_INTEGRATED_AUDIT_ONLY`

Goal:

Create one human-readable resolution matrix that answers:

1. What uncertainty remains?
2. What evidence is missing?
3. What evidence already exists?
4. What is still blocked and why?
5. What exact human decision values would be required later?
6. What can be closed as complete from the REQUEST_MORE_AUDIT chain?
7. What is the fastest safe next move?

23A must not execute source recovery.

23A must not finalize identity.

23A must not create live/final signal behavior.

23A must not call Discord, MT5, AI API, or live hooks.

## Required 23A implementation style

Create one integrated audit-only script.

Do not create a new 23A planning -> 23B draft -> 23C load -> 23D content chain unless a real blocker appears.

23A should output all of the following in one run:

- input audit CSV
- resolution matrix CSV
- integrated checks CSV
- safety matrix CSV
- required next gates CSV
- summary JSON
- human-readable Markdown report
- optional next-chat handoff note only if needed

Suggested 23A output folder:

`FX_OUTPUTS/gold_v2_23a_request_more_audit_resolution_matrix_integrated_audit_only`

Suggested 23A output files:

- `GOLD_V2_23A_REQUEST_MORE_AUDIT_RESOLUTION_MATRIX_INTEGRATED_AUDIT_ONLY_REPORT.md`
- `gold_v2_23a_request_more_audit_resolution_matrix_summary.json`
- `gold_v2_23a_input_audit.csv`
- `gold_v2_23a_resolution_matrix.csv`
- `gold_v2_23a_integrated_checks.csv`
- `gold_v2_23a_required_next_gates.csv`
- `gold_v2_23a_safety_matrix.csv`

Suggested 23A success status:

`REQUEST_MORE_AUDIT_RESOLUTION_MATRIX_READY_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

## 23A minimum checks

The 23A script must check and fail with STOP if any of the following fail:

- required 22G input files exist
- 22G status matches expected status
- 22G final handoff is ready
- selected value remains `REQUEST_MORE_AUDIT`
- total upstream STOP rows are zero
- forbidden gates remain false
- forbidden summary flags remain false
- source recovery approval remains false
- source recovery execution remains false
- source identity finalization/recovery remains false
- live/final/external actions remain false

## 23A resolution matrix suggested columns

Use a practical matrix, not another meta-audit table.

Suggested columns:

- `item_id`
- `question`
- `current_answer`
- `evidence_available`
- `evidence_missing`
- `risk_if_ignored`
- `allowed_current_action`
- `blocked_actions`
- `required_human_decision_value_later`
- `recommended_next_step`
- `status`

The matrix should be understandable to the user without reading all scripts.

## Suggested 23A matrix rows

At minimum include rows for:

- `REQUEST_MORE_AUDIT meaning`
- `source recovery approval state`
- `source identity finalization state`
- `live/final signal state`
- `external action state`
- `old GOLD/DISC8 quarantine state`
- `remaining uncertainty`
- `missing evidence`
- `fastest safe next move`

## Suggested 23A next gates

Allowed after 23A success:

- `23B_REQUEST_MORE_AUDIT_HUMAN_DECISION_OPTIONS_AUDIT_ONLY`

Still blocked after 23A:

- `SOURCE_IDENTITY_FINALIZATION`
- `SOURCE_RECOVERY`
- `LIVE`
- `FINAL_SIGNAL`
- `DISCORD_SEND`
- `MT5_ORDER`
- `AI_API`
- `LIVE_HOOK`

Do not proceed to 23B automatically in the same response after creating 23A files.

The user should run 23A and upload outputs first.

## Recommended repo changes in next chat

Before adding 23A files:

1. Fetch and record current 22G spec/script/BAT SHAs.
2. Create `docs/gold_v2/GOLD_V2_23A_PRE_CHANGE_BACKUP_MANIFEST_20260606.md`.
3. Create one 23A spec.
4. Create one 23A script.
5. Create one 23A BAT.
6. Read back the BAT and important files before claiming success.

Expected new files:

- `docs/gold_v2/GOLD_V2_23A_PRE_CHANGE_BACKUP_MANIFEST_20260606.md`
- `docs/gold_v2/GOLD_V2_23A_REQUEST_MORE_AUDIT_RESOLUTION_MATRIX_INTEGRATED_AUDIT_SPEC_20260606.md`
- `scripts/gold_v2_runtime/audit_gold_v2_23a_request_more_audit_resolution_matrix_integrated.py`
- `scripts/gold_v2_runtime/bat/23A_RESOLUTION_MATRIX.bat`

## Coding requirements

Do not provide skeleton code.

Implement full runnable code.

Do not silently simplify logic.

Do not use approximate reimplementation of source recovery or live evaluator.

Do not edit unrelated live trading, Discord, MT5, or AI API paths.

Prefer adding audit-only files under:

- `docs/gold_v2/`
- `scripts/gold_v2_runtime/`
- `scripts/gold_v2_runtime/bat/`

## GitHub tooling note

Previous GitHub `create_file` calls sometimes returned success and later an unrelated delayed 422 appeared.

Always fetch/read back important files before saying they are persisted.

## New chat response style

Japanese response preferred.

Keep the user updated, but do not flood with low-level details.

Be direct if something is only procedural and not substantive.

The user explicitly wants faster progress, so keep integrated steps compact and meaningful.
