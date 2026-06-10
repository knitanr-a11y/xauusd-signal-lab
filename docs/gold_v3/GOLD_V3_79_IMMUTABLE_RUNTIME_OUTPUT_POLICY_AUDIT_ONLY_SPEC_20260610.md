# GOLD V3 Stage79 — Immutable Runtime Output Policy Audit-Only Spec

Created JST: `2026-06-10`

Stage name:

`GOLD_V3_79_IMMUTABLE_RUNTIME_OUTPUT_POLICY_AUDIT_ONLY`

Expected READY status:

`GOLD_V3_79_IMMUTABLE_RUNTIME_OUTPUT_POLICY_READY_AUDIT_ONLY`

Blocked status:

`GOLD_V3_79_IMMUTABLE_RUNTIME_OUTPUT_POLICY_BLOCKED_AUDIT_ONLY`

## 1. Purpose

Stage79 prepares and audits an immutable runtime output policy for future real operation.

The human preference is:

`実運用するときは上書きもやめたほうがいい`

Stage79 therefore creates a run-id based immutable evidence snapshot instead of relying on overwritten latest files.

## 2. Non-negotiable constraints

- GOLD V3 only.
- GOLD V2, old GOLD, and DISC8 remain quarantined.
- Do not read, use, reference, compare against, or fallback to GOLD V2, old GOLD, or DISC8.
- Do not use Stage41 feature-only snapshot as a trading source.
- Do not create MT5 order BATs.
- Do not send Discord notifications.
- Do not call AI APIs.
- Do not enable live hook, live evaluator, or final signal.
- Do not manually remove or demote candidates/profiles.
- Keep every observed candidate in the pool.
- Required pool policy:

`poolから外さない。rolling health gateに判断させる。`

## 3. CSV closed-row contract

Preserve:

- `csv_contract: open/in-progress candles are not written to CSV`
- `csv_open_bar_exclusion_required: false`

The latest row in `goldsharp_m15.csv` is the latest closed M15 row.

## 4. Immutable output model

For real operation, evidence files should be written under a unique `run_id` directory:

`Files/FX_OUTPUTS/gold_v3/runtime_immutable/YYYYMMDD/<run_id>/`

Recommended run_id shape:

`YYYYMMDDTHHMMSSZ_m15_<YYYYMMDD_HHMMSS>_<decision>`

Example:

`20260610T141500Z_m15_20260610_164500_NO_SIGNAL`

If a duplicate run_id exists, the writer must append a deterministic suffix:

`_retry01`, `_retry02`, ...

The writer must never overwrite an existing evidence file inside a run_id directory.

## 5. Required Stage79 behavior

Stage79 is audit-only. It must:

1. read the current Stage76 summary,
2. derive a unique immutable `run_id`,
3. create a new immutable snapshot directory,
4. copy selected Stage76 evidence files into the snapshot directory without overwriting,
5. write a SHA256 manifest,
6. write an immutable output policy matrix,
7. write a paste-me summary inside the run_id directory.

Stage79 may create new files. It must not modify or delete existing evidence snapshots.

## 6. Required inputs

Default Files directory:

`Files`

Required Stage76 summary:

`Files/FX_OUTPUTS/gold_v3/76_full_audit_monitor_with_payload_preview_audit_only/gold_v3_76_full_audit_monitor_with_payload_preview_summary.json`

Recommended source files to snapshot if present:

- `gold_v3_76_monitor_state.json`
- `gold_v3_76_monitor_event_log.csv`
- `gold_v3_76_runtime_timing_log.csv`
- `gold_v3_76_latest_payload_preview.csv`
- `gold_v3_76_latest_payload_preview.json`
- `gold_v3_76_blocker_matrix.csv`
- `gold_v3_76_validation_matrix.csv`
- `gold_v3_76_full_audit_monitor_with_payload_preview_summary.json`
- `gold_v3_76_PASTE_ME_FULL_AUDIT_MONITOR_WITH_PAYLOAD_PREVIEW_SUMMARY.txt`
- `GOLD_V3_76_REPORT.md`

## 7. READY conditions

Stage79 is READY if:

- Stage76 summary exists,
- Stage76 status is READY,
- immutable run directory was newly created,
- no source evidence file was overwritten,
- manifest was written,
- all copied files have SHA256 hashes,
- live flags remain false,
- `csv_open_bar_exclusion_required=false` is preserved,
- blocker_count is zero.

READY does not approve live release.

## 8. Outputs

Immutable snapshot directory:

`Files/FX_OUTPUTS/gold_v3/runtime_immutable/YYYYMMDD/<run_id>/`

Required outputs inside the immutable run directory:

- `gold_v3_79_immutable_manifest.json`
- `gold_v3_79_immutable_manifest.csv`
- `gold_v3_79_output_policy_matrix.csv`
- `gold_v3_79_blocker_matrix.csv`
- `gold_v3_79_validation_matrix.csv`
- `gold_v3_79_immutable_runtime_output_policy_summary.json`
- `gold_v3_79_PASTE_ME_IMMUTABLE_RUNTIME_OUTPUT_POLICY_SUMMARY.txt`
- `GOLD_V3_79_REPORT.md`
- `stage76_snapshot/` copied evidence files

No fixed latest summary is required for Stage79. The BAT prints the exact paste-me path for the newly-created immutable run.

## 9. Runner and BAT

Script:

`scripts/gold_v3_runtime/gold_v3_79_immutable_runtime_output_policy_audit.py`

BAT:

`scripts/gold_v3_runtime/bat/run_gold_v3_79_immutable_runtime_output_policy_audit.bat`
