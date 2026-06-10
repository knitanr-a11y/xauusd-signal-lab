# GOLD V3 Stage74 — Guarded Live CSV Monitor Audit-Only Spec

Created JST: `2026-06-10`

Stage name:

`GOLD_V3_74_GUARDED_LIVE_CSV_MONITOR_AUDIT_ONLY`

Expected READY status:

`GOLD_V3_74_GUARDED_LIVE_CSV_MONITOR_READY_AUDIT_ONLY`

Blocked status:

`GOLD_V3_74_GUARDED_LIVE_CSV_MONITOR_BLOCKED_AUDIT_ONLY`

## 1. Purpose

Stage74 is the audit-only guarded live CSV monitor package.

It keeps one local console process open, watches `goldsharp_m15.csv`, and when the latest closed M15 timestamp changes it automatically runs:

1. Stage69 live CSV condition detector,
2. Stage70 signal decision preview,
3. Stage71 latest signal snapshot package,
4. Stage73 signal emission guard.

This makes Stage73 part of the automatic audit loop, so the human does not need to run Stage73 manually after every CSV update.

Stage74 does not trade, notify, or enable final signals.

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

Stage74 must preserve:

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
- `scripts/gold_v3_runtime/gold_v3_73_signal_emission_guard_audit.py`

Stage74 runs these Python scripts directly. It must not call the Stage69/70/71/73 BAT files because those BAT files pause for manual inspection.

## 5. Monitor behavior

- Poll `goldsharp_m15.csv` every configured interval.
- Default interval: 30 seconds.
- On startup, run the guarded pipeline once unless disabled by argument.
- After startup, run the guarded pipeline only when the latest closed M15 timestamp changes.
- Write a heartbeat summary every loop.
- Write an event log row for every check and every stage run.
- Continue running until the user closes the console or presses `Ctrl+C`.

## 6. Guard behavior

Stage74 treats Stage73 as the final audit guard for the loop.

Expected no-side-effect outputs:

- `should_notify_discord=false`
- `should_place_mt5_order=false`
- `should_call_ai_api=false`
- `should_enable_final_signal=false`

For `NO_SIGNAL`, Stage73 must output:

- `emission_action=NO_ACTION`
- `no_signal_notification_suppressed=true`

For `SIGNAL`, Stage73 must output either:

- `ALLOW_AUDIT_SIGNAL_EVENT`, or
- `SUPPRESS_DUPLICATE_SIGNAL`

## 7. Outputs

Output folder:

`Files/FX_OUTPUTS/gold_v3/74_guarded_live_csv_monitor_audit_only`

Required outputs:

- `gold_v3_74_monitor_state.json`
- `gold_v3_74_monitor_event_log.csv`
- `gold_v3_74_latest_guarded_snapshot.csv`
- `gold_v3_74_latest_guarded_snapshot.json`
- `gold_v3_74_blocker_matrix.csv`
- `gold_v3_74_validation_matrix.csv`
- `gold_v3_74_guarded_live_csv_monitor_summary.json`
- `gold_v3_74_PASTE_ME_GUARDED_LIVE_CSV_MONITOR_SUMMARY.txt`
- `GOLD_V3_74_REPORT.md`

## 8. READY conditions

Stage74 is READY if:

- Required CSV exists.
- Required Stage69/70/71/73 scripts exist.
- Monitor reads latest M15 time successfully.
- Guarded pipeline is run successfully on startup or on the first detected change.
- Stage73 latest emission decision is available after the run.
- Stage73 latest closed M15 time matches the current CSV latest M15 time.
- Stage73 is READY.
- All external side-effect flags remain false.
- `csv_open_bar_exclusion_required=false` is preserved.

A deterministic `NO_SIGNAL` remains READY.

## 9. BLOCKED conditions

Stage74 must BLOCK if:

- Required CSV is missing.
- Required Stage69/70/71/73 script is missing.
- Latest M15 time cannot be read.
- Stage69/70/71/73 pipeline returns a nonzero exit code.
- Stage73 summary or emission decision cannot be found after pipeline execution.
- Stage73 latest closed M15 time does not match the current CSV latest M15 time.
- Any external side-effect flag is true.

## 10. Runner and BAT

Script:

`scripts/gold_v3_runtime/gold_v3_74_guarded_live_csv_monitor_audit.py`

BAT:

`scripts/gold_v3_runtime/bat/run_gold_v3_74_guarded_live_csv_monitor_audit.bat`

The BAT starts the guarded monitor. The console window must remain open for monitoring to continue. Closing the console stops monitoring.
