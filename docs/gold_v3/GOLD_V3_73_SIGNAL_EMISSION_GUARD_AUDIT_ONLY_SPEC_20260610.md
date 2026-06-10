# GOLD V3 Stage73 — Signal Emission Guard Audit-Only Spec

Created JST: `2026-06-10`

Stage name:

`GOLD_V3_73_SIGNAL_EMISSION_GUARD_AUDIT_ONLY`

Expected READY status:

`GOLD_V3_73_SIGNAL_EMISSION_GUARD_READY_AUDIT_ONLY`

Blocked status:

`GOLD_V3_73_SIGNAL_EMISSION_GUARD_BLOCKED_AUDIT_ONLY`

## 1. Purpose

Stage73 adds an audit-only emission guard after Stage72.

It reads the latest Stage72 pipeline snapshot and decides whether the current preview would be:

- `NO_ACTION` for `NO_SIGNAL`,
- `ALLOW_AUDIT_SIGNAL_EVENT` for a new `SIGNAL`, or
- `SUPPRESS_DUPLICATE_SIGNAL` when the same signal UID was already observed.

Stage73 does not notify Discord, does not place MT5 orders, and does not enable final signals.

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

Stage73 must preserve:

- `csv_contract: open/in-progress candles are not written to CSV`
- `csv_open_bar_exclusion_required: false`

## 4. Required inputs

Default GOLD V3 output root:

`Files/FX_OUTPUTS/gold_v3`

Required Stage72 inputs:

- `72_live_csv_update_monitor_audit_only/gold_v3_72_live_csv_update_monitor_summary.json`
- `72_live_csv_update_monitor_audit_only/gold_v3_72_latest_pipeline_snapshot.json`

Stage72 must be READY:

`GOLD_V3_72_LIVE_CSV_UPDATE_MONITOR_READY_AUDIT_ONLY`

## 5. Signal UID

For duplicate suppression, Stage73 builds a signal UID from:

- latest closed M15 time
- decision
- selected candidate label

If `selected_candidate_label` is blank, it remains blank in the UID.

Example:

`2026-06-10 15:45:00|SIGNAL|HV_R01...`

## 6. Routing decision contract

If Stage72 decision is `NO_SIGNAL`:

- `emission_action=NO_ACTION`
- `should_notify_discord=false`
- `should_place_mt5_order=false`
- `no_signal_notification_suppressed=true`

If Stage72 decision is `SIGNAL` and signal UID has not been emitted before:

- `emission_action=ALLOW_AUDIT_SIGNAL_EVENT`
- `should_notify_discord=false`
- `should_place_mt5_order=false`
- `audit_signal_event_allowed=true`
- record signal UID in guard state

If Stage72 decision is `SIGNAL` and signal UID was already emitted before:

- `emission_action=SUPPRESS_DUPLICATE_SIGNAL`
- `duplicate_signal_suppressed=true`
- `should_notify_discord=false`
- `should_place_mt5_order=false`

## 7. Outputs

Output folder:

`Files/FX_OUTPUTS/gold_v3/73_signal_emission_guard_audit_only`

Required outputs:

- `gold_v3_73_emission_decision.csv`
- `gold_v3_73_signal_emission_guard_state.json`
- `gold_v3_73_signal_emission_event_ledger.csv`
- `gold_v3_73_blocker_matrix.csv`
- `gold_v3_73_validation_matrix.csv`
- `gold_v3_73_signal_emission_guard_summary.json`
- `gold_v3_73_PASTE_ME_SIGNAL_EMISSION_GUARD_SUMMARY.txt`
- `GOLD_V3_73_REPORT.md`

## 8. READY conditions

Stage73 is READY if:

- Stage72 is READY.
- Stage72 latest snapshot exists.
- Stage72 snapshot time matches Stage72 summary latest M15 time.
- Decision is either `SIGNAL` or `NO_SIGNAL`.
- NO_SIGNAL produces `NO_ACTION`.
- SIGNAL produces either `ALLOW_AUDIT_SIGNAL_EVENT` or `SUPPRESS_DUPLICATE_SIGNAL`.
- Discord notification remains false.
- MT5 order placement remains false.
- AI API remains false.
- final signal remains false.
- `csv_open_bar_exclusion_required=false` is preserved.

## 9. BLOCKED conditions

Stage73 must BLOCK if:

- Stage72 is missing or not READY.
- Stage72 latest snapshot is missing.
- Snapshot latest M15 time does not match Stage72 summary latest M15 time.
- Decision is neither `SIGNAL` nor `NO_SIGNAL`.
- Any external side-effect flag is true.

## 10. Runner and BAT

Script:

`scripts/gold_v3_runtime/gold_v3_73_signal_emission_guard_audit.py`

BAT:

`scripts/gold_v3_runtime/bat/run_gold_v3_73_signal_emission_guard_audit.bat`

The BAT is a no-argument audit runner only. It does not place trades or send notifications.
