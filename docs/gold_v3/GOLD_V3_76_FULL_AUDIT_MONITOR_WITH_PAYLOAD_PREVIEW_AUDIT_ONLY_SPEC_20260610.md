# GOLD V3 Stage76 — Full Audit Monitor With Payload Preview Audit-Only Spec

Created JST: `2026-06-10`

Stage name:

`GOLD_V3_76_FULL_AUDIT_MONITOR_WITH_PAYLOAD_PREVIEW_AUDIT_ONLY`

Expected READY status:

`GOLD_V3_76_FULL_AUDIT_MONITOR_WITH_PAYLOAD_PREVIEW_READY_AUDIT_ONLY`

Blocked status:

`GOLD_V3_76_FULL_AUDIT_MONITOR_WITH_PAYLOAD_PREVIEW_BLOCKED_AUDIT_ONLY`

## 1. Purpose

Stage76 is the first end-to-end audit-only monitor that includes payload preview.

It keeps one local console process open, watches `goldsharp_m15.csv`, and when the latest closed M15 timestamp changes it automatically runs:

1. Stage74 guarded live CSV monitor in one-shot mode,
2. Stage75 external action payload preview.

Stage74 itself runs Stage69 -> Stage70 -> Stage71 -> Stage73.

So the full chain is:

`Stage69 -> Stage70 -> Stage71 -> Stage73 -> Stage74 wrapper -> Stage75 payload preview -> Stage76 monitor summary`

Stage76 does not trade, notify, call AI, or enable final signals.

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

Stage76 must preserve:

- `csv_contract: open/in-progress candles are not written to CSV`
- `csv_open_bar_exclusion_required: false`

The latest row in `goldsharp_m15.csv` is treated as the latest closed M15 row.

## 4. Required inputs

Default Files directory:

`Files`

Required CSV:

- `goldsharp_m15.csv`

Required scripts:

- `scripts/gold_v3_runtime/gold_v3_74_guarded_live_csv_monitor_audit.py`
- `scripts/gold_v3_runtime/gold_v3_75_external_action_payload_preview_audit.py`

Stage76 calls Stage74 with `--once` so it completes and returns to Stage76. Stage76 must not call Stage74 BAT because the BAT pauses.

## 5. Monitor behavior

- Poll `goldsharp_m15.csv` every configured interval.
- Default interval: 30 seconds.
- On startup, run the full audit chain once unless disabled by argument.
- After startup, run the full audit chain only when the latest closed M15 timestamp changes.
- Write a heartbeat summary every loop.
- Write an event log row for every check and every stage run.
- Continue running until the user closes the console or presses `Ctrl+C`.

## 6. READY conditions

Stage76 is READY if:

- Required CSV exists.
- Required Stage74 and Stage75 scripts exist.
- Monitor reads latest M15 time successfully.
- Stage74 returns READY in one-shot mode.
- Stage75 returns READY after Stage74.
- Stage75 latest closed M15 time matches the current CSV latest M15 time.
- Payload action is deterministic.
- Discord send flag remains false.
- MT5 order flag remains false.
- AI API flag remains false.
- final signal flag remains false.
- `csv_open_bar_exclusion_required=false` is preserved.

A deterministic `NO_SIGNAL` remains READY.

## 7. BLOCKED conditions

Stage76 must BLOCK if:

- Required CSV is missing.
- Required Stage74 or Stage75 script is missing.
- Latest M15 time cannot be read.
- Stage74 or Stage75 returns nonzero.
- Stage75 summary is missing after run.
- Stage75 latest closed M15 time does not match the current CSV latest M15 time.
- Any external side-effect flag is true.

## 8. Outputs

Output folder:

`Files/FX_OUTPUTS/gold_v3/76_full_audit_monitor_with_payload_preview_audit_only`

Required outputs:

- `gold_v3_76_monitor_state.json`
- `gold_v3_76_monitor_event_log.csv`
- `gold_v3_76_latest_payload_preview.csv`
- `gold_v3_76_latest_payload_preview.json`
- `gold_v3_76_blocker_matrix.csv`
- `gold_v3_76_validation_matrix.csv`
- `gold_v3_76_full_audit_monitor_with_payload_preview_summary.json`
- `gold_v3_76_PASTE_ME_FULL_AUDIT_MONITOR_WITH_PAYLOAD_PREVIEW_SUMMARY.txt`
- `GOLD_V3_76_REPORT.md`

## 9. Runner and BAT

Script:

`scripts/gold_v3_runtime/gold_v3_76_full_audit_monitor_with_payload_preview_audit.py`

BAT:

`scripts/gold_v3_runtime/bat/run_gold_v3_76_full_audit_monitor_with_payload_preview_audit.bat`

The BAT starts the full audit monitor. The console window must remain open for monitoring to continue. Closing the console stops monitoring.
