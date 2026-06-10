# GOLD V3 Stage82 — Runtime Doc Sync and Operator Checklist Audit-Only Spec

Created JST: `2026-06-10`

Stage name:

`GOLD_V3_82_RUNTIME_DOC_SYNC_AND_OPERATOR_CHECKLIST_AUDIT_ONLY`

Expected READY status:

`GOLD_V3_82_RUNTIME_DOC_SYNC_AND_OPERATOR_CHECKLIST_READY_AUDIT_ONLY`

Blocked status:

`GOLD_V3_82_RUNTIME_DOC_SYNC_AND_OPERATOR_CHECKLIST_BLOCKED_AUDIT_ONLY`

## 1. Purpose

Stage82 verifies that the human-facing runtime operation manual and operator checklist match the current audit-only runtime files.

The human requested:

`随時ドキュメントを更新してください。トリセツみたいな感じで、エラーはこのファイルを見てとか`

Stage82 therefore creates and audits:

- runtime operation manual presence,
- operator checklist presence,
- current Stage80 BAT reference,
- error-first `upload_first.txt` rule,
- no-first-upload for huge CSV logs,
- current Stage80/81 local output status if available.

## 2. Non-negotiable constraints

- GOLD V3 only.
- GOLD V2, old GOLD, and DISC8 remain quarantined.
- Do not read, use, reference, compare against, or fallback to GOLD V2, old GOLD, or DISC8.
- Do not use Stage41 feature-only snapshot as a trading source.
- GOLD V3 remains audit-only.
- Do not send Discord notifications.
- Do not place MT5 orders.
- Do not call AI APIs.
- Do not enable live hook, live evaluator, or final signal.
- Do not manually remove or demote candidates/profiles.
- Required pool policy:

`poolから外さない。rolling health gateに判断させる。`

## 3. CSV closed-row contract

Preserve:

- `csv_contract: open/in-progress candles are not written to CSV`
- `csv_open_bar_exclusion_required: false`

## 4. Required documentation files

Runtime manual:

`docs/gold_v3/GOLD_V3_RUNTIME_OPERATION_MANUAL_AUDIT_ONLY_20260610.md`

Operator checklist:

`docs/gold_v3/GOLD_V3_RUNTIME_OPERATOR_CHECKLIST_AUDIT_ONLY_20260610.md`

Handoff:

`docs/gold_v3/NEXT_CHAT_HANDOFF_GOLD_V3_81_RUNTIME_OPERATION_MANUAL_READY_82_NEXT_AUDIT_ONLY_20260610.md`

## 5. Required runtime files

BATs:

- `scripts/gold_v3_runtime/bat/run_gold_v3_80_immutable_runtime_monitor_audit.bat`
- `scripts/gold_v3_runtime/bat/run_gold_v3_81_compact_support_bundle_audit.bat`

Scripts:

- `scripts/gold_v3_runtime/gold_v3_76_full_audit_monitor_with_payload_preview_audit.py`
- `scripts/gold_v3_runtime/gold_v3_79_immutable_runtime_output_policy_audit.py`
- `scripts/gold_v3_runtime/gold_v3_80_immutable_runtime_monitor_audit.py`
- `scripts/gold_v3_runtime/gold_v3_81_compact_support_bundle_audit.py`

## 6. READY conditions

Stage82 is READY if:

- required documentation files exist,
- required runtime scripts/BATs exist,
- manual mentions Stage80 BAT,
- manual mentions Stage81 `upload_first.txt`,
- manual says not to upload full large logs first,
- operator checklist says start Stage80 and upload `upload_first.txt` on error,
- Stage80 summary exists and is READY if local outputs are present,
- Stage80 summary confirms `auto_support_bundle_enabled=True`,
- live/external flags remain false,
- blocker_count is zero.

If local Stage80 summary is absent, Stage82 may record this as a blocker only when Stage80 output folder is expected for the run. Default behavior expects local Stage80 summary because Stage80 has been run in the current workflow.

## 7. Outputs

Output folder:

`Files/FX_OUTPUTS/gold_v3/82_runtime_doc_sync_and_operator_checklist_audit_only/`

Outputs:

- `gold_v3_82_doc_reference_matrix.csv`
- `gold_v3_82_file_presence_matrix.csv`
- `gold_v3_82_blocker_matrix.csv`
- `gold_v3_82_validation_matrix.csv`
- `gold_v3_82_runtime_doc_sync_and_operator_checklist_summary.json`
- `gold_v3_82_PASTE_ME_RUNTIME_DOC_SYNC_AND_OPERATOR_CHECKLIST_SUMMARY.txt`
- `GOLD_V3_82_REPORT.md`

## 8. Runner and BAT

Script:

`scripts/gold_v3_runtime/gold_v3_82_runtime_doc_sync_and_operator_checklist_audit.py`

BAT:

`scripts/gold_v3_runtime/bat/run_gold_v3_82_runtime_doc_sync_and_operator_checklist_audit.bat`
