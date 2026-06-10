# GOLD V3 Stage83 — Runtime Housekeeping Size Audit-Only Spec

Created JST: `2026-06-10`

Stage name:

`GOLD_V3_83_RUNTIME_HOUSEKEEPING_SIZE_AUDIT_ONLY`

Expected READY status:

`GOLD_V3_83_RUNTIME_HOUSEKEEPING_SIZE_READY_AUDIT_ONLY`

Blocked status:

`GOLD_V3_83_RUNTIME_HOUSEKEEPING_SIZE_BLOCKED_AUDIT_ONLY`

## 1. Purpose

Stage83 audits runtime folder/log growth so the human can avoid:

- confusing folders,
- unknown required troubleshooting files,
- upload files that are too large,
- giant event/timing CSVs.

Stage83 is audit-only. It does not delete, move, compress, or modify existing evidence.

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

## 4. Audit scope

Default scan root:

`Files/FX_OUTPUTS/gold_v3/`

Important runtime folders:

- `76_full_audit_monitor_with_payload_preview_audit_only/`
- `79i/`
- `80_immutable_runtime_monitor_audit_only/`
- `81c/`
- `82_runtime_doc_sync_and_operator_checklist_audit_only/`

Stage83 creates a size inventory and a housekeeping recommendation matrix.

## 5. Thresholds

Default warning thresholds:

- single file warning: `5 MiB`,
- single file blocker: `50 MiB`,
- folder warning: `100 MiB`,
- folder blocker: `500 MiB`,
- 79i run folder count warning: `200`,
- 81c bundle count warning: `100`.

These are audit thresholds only. They do not delete anything.

## 6. READY conditions

Stage83 is READY if:

- scan root exists,
- file inventory was written,
- folder inventory was written,
- recommendation matrix was written,
- no file/folder exceeds blocker thresholds,
- safety flags remain false,
- blocker_count is zero.

Warnings do not block READY.

## 7. Outputs

Output folder:

`Files/FX_OUTPUTS/gold_v3/83_runtime_housekeeping_size_audit_only/`

Outputs:

- `gold_v3_83_file_inventory.csv`
- `gold_v3_83_folder_inventory.csv`
- `gold_v3_83_housekeeping_recommendation_matrix.csv`
- `gold_v3_83_blocker_matrix.csv`
- `gold_v3_83_validation_matrix.csv`
- `gold_v3_83_runtime_housekeeping_size_summary.json`
- `gold_v3_83_PASTE_ME_RUNTIME_HOUSEKEEPING_SIZE_SUMMARY.txt`
- `GOLD_V3_83_REPORT.md`

## 8. Runner and BAT

Script:

`scripts/gold_v3_runtime/gold_v3_83_runtime_housekeeping_size_audit.py`

BAT:

`scripts/gold_v3_runtime/bat/run_gold_v3_83_runtime_housekeeping_size_audit.bat`

## 9. Human rule

If troubleshooting is needed, still upload Stage81 `upload_first.txt` first. Stage83 is for periodic folder-size review, not first-line error diagnosis.
