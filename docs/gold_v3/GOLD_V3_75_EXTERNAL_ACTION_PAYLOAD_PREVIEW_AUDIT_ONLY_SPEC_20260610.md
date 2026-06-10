# GOLD V3 Stage75 — External Action Payload Preview Audit-Only Spec

Created JST: `2026-06-10`

Stage name:

`GOLD_V3_75_EXTERNAL_ACTION_PAYLOAD_PREVIEW_AUDIT_ONLY`

Expected READY status:

`GOLD_V3_75_EXTERNAL_ACTION_PAYLOAD_PREVIEW_READY_AUDIT_ONLY`

Blocked status:

`GOLD_V3_75_EXTERNAL_ACTION_PAYLOAD_PREVIEW_BLOCKED_AUDIT_ONLY`

## 1. Purpose

Stage75 prepares external action payload previews after the Stage74 guarded monitor.

It answers:

- If Discord notification were later enabled, what message would be sent?
- If MT5 order routing were later enabled, what order-intent payload would be produced?

Stage75 does not send Discord notifications, does not place MT5 orders, and does not enable final signals.

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

Stage75 must preserve:

- `csv_contract: open/in-progress candles are not written to CSV`
- `csv_open_bar_exclusion_required: false`

## 4. Required inputs

Default GOLD V3 output root:

`Files/FX_OUTPUTS/gold_v3`

Required Stage74 inputs:

- `74_guarded_live_csv_monitor_audit_only/gold_v3_74_guarded_live_csv_monitor_summary.json`
- `74_guarded_live_csv_monitor_audit_only/gold_v3_74_latest_guarded_snapshot.json`

Stage74 must be READY:

`GOLD_V3_74_GUARDED_LIVE_CSV_MONITOR_READY_AUDIT_ONLY`

## 5. Payload policy

If Stage74/73 decision is `NO_SIGNAL`:

- `payload_action=SUPPRESS_NO_SIGNAL_PAYLOAD`
- Discord payload preview must be empty or marked suppressed.
- MT5 order intent preview must be empty or marked suppressed.
- `should_notify_discord=false`
- `should_place_mt5_order=false`

If Stage74/73 decision is `SIGNAL` and emission action is `ALLOW_AUDIT_SIGNAL_EVENT`:

- `payload_action=BUILD_AUDIT_PAYLOAD_PREVIEW`
- Build a Discord message preview text.
- Build an MT5 order-intent preview JSON.
- Keep `should_notify_discord=false`.
- Keep `should_place_mt5_order=false`.

If Stage74/73 emission action is `SUPPRESS_DUPLICATE_SIGNAL`:

- `payload_action=SUPPRESS_DUPLICATE_PAYLOAD`
- Do not build sendable payloads.
- Keep all external action flags false.

## 6. Outputs

Output folder:

`Files/FX_OUTPUTS/gold_v3/75_external_action_payload_preview_audit_only`

Required outputs:

- `gold_v3_75_payload_preview.csv`
- `gold_v3_75_discord_message_preview.txt`
- `gold_v3_75_mt5_order_intent_preview.json`
- `gold_v3_75_blocker_matrix.csv`
- `gold_v3_75_validation_matrix.csv`
- `gold_v3_75_external_action_payload_preview_summary.json`
- `gold_v3_75_PASTE_ME_EXTERNAL_ACTION_PAYLOAD_PREVIEW_SUMMARY.txt`
- `GOLD_V3_75_REPORT.md`

## 7. READY conditions

Stage75 is READY if:

- Stage74 is READY.
- Stage74 latest guarded snapshot exists.
- Stage74 latest M15 time matches Stage73 latest closed M15 time.
- Stage73 source stage is `stage71`.
- Payload action is deterministic.
- Discord send flag remains false.
- MT5 order flag remains false.
- AI API flag remains false.
- final signal flag remains false.
- `csv_open_bar_exclusion_required=false` is preserved.

A deterministic `NO_SIGNAL` remains READY.

## 8. BLOCKED conditions

Stage75 must BLOCK if:

- Stage74 is missing or not READY.
- Stage74 latest guarded snapshot is missing.
- Snapshot latest time is stale.
- Stage73 source stage is not `stage71`.
- Any external side-effect flag is true.

## 9. Runner and BAT

Script:

`scripts/gold_v3_runtime/gold_v3_75_external_action_payload_preview_audit.py`

BAT:

`scripts/gold_v3_runtime/bat/run_gold_v3_75_external_action_payload_preview_audit.bat`

The BAT is a no-argument audit runner only. It does not send notifications or place trades.
