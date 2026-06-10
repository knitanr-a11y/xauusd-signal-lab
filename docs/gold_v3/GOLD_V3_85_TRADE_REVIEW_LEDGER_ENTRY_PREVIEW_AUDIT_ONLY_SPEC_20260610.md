# GOLD V3 Stage85 — Trade Review Ledger Entry Preview Audit-Only Spec

Created JST: `2026-06-10`

Stage name:

`GOLD_V3_85_TRADE_REVIEW_LEDGER_ENTRY_PREVIEW_AUDIT_ONLY`

Expected READY status:

`GOLD_V3_85_TRADE_REVIEW_LEDGER_ENTRY_PREVIEW_READY_AUDIT_ONLY`

Blocked status:

`GOLD_V3_85_TRADE_REVIEW_LEDGER_ENTRY_PREVIEW_BLOCKED_AUDIT_ONLY`

## 1. Purpose

Stage85 verifies that the runtime pipeline can create a compact trade-review ledger row preview when a real SIGNAL exists, while avoiding ledger bloat from NO_SIGNAL heartbeats.

Human retention priority:

- old notification errors and heartbeat logs are not long-term learning material,
- trade history and why a trade won/lost are long-term learning material,
- future signal improvement and possible AI API review should use trade review records, not giant runtime logs.

Stage85 is audit-only and does not append to the durable ledger by default.

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

## 4. Ledger behavior

### If current decision is NO_SIGNAL

- do not create an appendable trade ledger row,
- write a suppression reason:

`NO_SIGNAL_NOT_A_TRADE_REVIEW_LEDGER_ROW`

- keep status READY if safety checks pass.

### If current decision is SIGNAL

- create one preview ledger row using the Stage84 schema,
- fill signal time, decision, direction, candidate/profile key, TP/SL/horizon, evidence path, and outcome placeholders,
- set outcome fields to `PENDING`,
- set `manual_review_required=true`,
- do not append it to long-term ledger automatically in Stage85.

If a SIGNAL lacks required candidate/profile fields, Stage85 should BLOCK because the record would not be useful for later review.

## 5. Candidate key order

Must remain exactly:

`candidate_label+base_candidate_label+source_profile_id+profile_id+hv_profile+tp_usd+sl_usd+horizon_m15+horizon_m5_bars`

## 6. Inputs

Default Stage76 summary:

`Files/FX_OUTPUTS/gold_v3/76_full_audit_monitor_with_payload_preview_audit_only/gold_v3_76_full_audit_monitor_with_payload_preview_summary.json`

Default Stage80 summary:

`Files/FX_OUTPUTS/gold_v3/80_immutable_runtime_monitor_audit_only/gold_v3_80_immutable_runtime_monitor_summary.json`

Stage84 schema:

`Files/FX_OUTPUTS/gold_v3/trade_review_ledger/trade_review_ledger_schema.csv`

## 7. Outputs

Output folder:

`Files/FX_OUTPUTS/gold_v3/85_trade_review_ledger_entry_preview_audit_only/`

Outputs:

- `gold_v3_85_trade_review_entry_preview.csv`
- `gold_v3_85_ledger_suppression_matrix.csv`
- `gold_v3_85_blocker_matrix.csv`
- `gold_v3_85_validation_matrix.csv`
- `gold_v3_85_trade_review_ledger_entry_preview_summary.json`
- `gold_v3_85_PASTE_ME_TRADE_REVIEW_LEDGER_ENTRY_PREVIEW_SUMMARY.txt`
- `GOLD_V3_85_REPORT.md`

## 8. READY conditions

Stage85 is READY if:

- Stage76 summary exists,
- Stage80 summary exists,
- Stage84 schema exists,
- candidate key order is exact,
- NO_SIGNAL is suppressed from the ledger or SIGNAL preview row is complete,
- no live/external flags are enabled,
- blocker_count is zero.

READY does not append to the durable ledger and does not approve live release.

## 9. Runner and BAT

Script:

`scripts/gold_v3_runtime/gold_v3_85_trade_review_ledger_entry_preview_audit.py`

BAT:

`scripts/gold_v3_runtime/bat/run_gold_v3_85_trade_review_ledger_entry_preview_audit.bat`
