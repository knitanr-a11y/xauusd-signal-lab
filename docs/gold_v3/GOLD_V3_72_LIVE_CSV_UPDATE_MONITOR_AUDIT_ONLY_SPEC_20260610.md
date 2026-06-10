# GOLD V3 Stage72 — Live CSV Update Monitor Audit-Only Spec

Created JST: `2026-06-10`

Stage name:

`GOLD_V3_72_LIVE_CSV_UPDATE_MONITOR_AUDIT_ONLY`

Expected READY status:

`GOLD_V3_72_LIVE_CSV_UPDATE_MONITOR_READY_AUDIT_ONLY`

Blocked status:

`GOLD_V3_72_LIVE_CSV_UPDATE_MONITOR_BLOCKED_AUDIT_ONLY`

## 1. Purpose

Stage72 provides an audit-only CSV update monitor.

It keeps a local console process open, watches `goldsharp_m15.csv`, and when the latest closed M15 timestamp changes it automatically runs the already-audited Stage69 -> Stage70 -> Stage71 pipeline.

This removes the need for the human to manually run the pipeline after every CSV update during audit testing.

Stage72 does not trade, notify, or enable final signals.

## 2. Non-negotiable constraints

- GOLD V3 only.
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

The human clarified:

`open中の足はCSVには入りません`

Stage72 must preserve:

- `csv_contract: open/in-progress candles are not written to CSV`
- `csv_open_bar_exclusion_required: false`

The latest row in `goldsharp_m15.csv` is treated as the latest closed M15 row.

## 4. Required inputs

Default Files directory:

`Files`

Required CSV:

- `goldsharp_m15.csv`

Required scripts:

- `scripts/gold_v3_runtime/gold_v3_69_live_csv_condition_detector_audit.py`
- `scripts/gold_v3_runtime/gold_v3_70_live_csv_signal_decision_preview_audit.py`
- `scripts/gold_v3_runtime/gold_v3_71_live_csv_signal_audit_pipeline_package.py`

Stage72 runs these Python scripts directly. It must not call the Stage69/70/71 BAT files because those BAT files pause for manual inspection.

## 5. Monitor behavior

- Poll `goldsharp_m15.csv` every configured interval.
- Default interval: 30 seconds.
- On startup, run the pipeline once unless disabled by argument.
- After startup, run the pipeline only when the latest closed M15 timestamp changes.
- Write a heartbeat summary every loop.
- Write an event log row for every check and every pipeline run.
- Continue running until the user closes the console or presses `Ctrl+C`.

## 6. Outputs

Output folder:

`Files/FX_OUTPUTS/gold_v3/72_live_csv_update_monitor_audit_only`

Required outputs:

- `gold_v3_72_monitor_state.json`
- `gold_v3_72_monitor_event_log.csv`
- `gold_v3_72_latest_pipeline_snapshot.csv`
- `gold_v3_72_latest_pipeline_snapshot.json`
- `gold_v3_72_blocker_matrix.csv`
- `gold_v3_72_validation_matrix.csv`
- `gold_v3_72_live_csv_update_monitor_summary.json`
- `gold_v3_72_PASTE_ME_LIVE_CSV_UPDATE_MONITOR_SUMMARY.txt`
- `GOLD_V3_72_REPORT.md`

## 7. READY conditions

Stage72 is READY if:

- Required CSV exists.
- Required Stage69/70/71 scripts exist.
- Monitor reads latest M15 time successfully.
- Pipeline is run successfully on startup or on the first detected change.
- Stage71 latest snapshot is available after the run.
- All safety flags remain false.
- `csv_open_bar_exclusion_required=false` is preserved.

A deterministic `NO_SIGNAL` remains READY.

## 8. BLOCKED conditions

Stage72 must BLOCK if:

- Required CSV is missing.
- Required Stage69/70/71 script is missing.
- Latest M15 time cannot be read.
- Stage69/70/71 pipeline returns a nonzero exit code.
- Stage71 latest snapshot cannot be found after pipeline execution.
- Any live/MT5/Discord/AI/final-signal flag is true.

## 9. Runner and BAT

Script:

`scripts/gold_v3_runtime/gold_v3_72_live_csv_update_monitor_audit.py`

BAT:

`scripts/gold_v3_runtime/bat/run_gold_v3_72_live_csv_update_monitor_audit.bat`

The BAT starts the monitor. The console window must remain open for monitoring to continue. Closing the console stops monitoring.
