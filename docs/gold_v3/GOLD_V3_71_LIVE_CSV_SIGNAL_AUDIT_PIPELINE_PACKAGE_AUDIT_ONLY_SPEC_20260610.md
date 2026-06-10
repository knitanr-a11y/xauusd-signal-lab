# GOLD V3 Stage71 — Live CSV Signal Audit Pipeline Package Audit-Only Spec

Created JST: `2026-06-10`

Stage name:

`GOLD_V3_71_LIVE_CSV_SIGNAL_AUDIT_PIPELINE_PACKAGE_AUDIT_ONLY`

Expected READY status:

`GOLD_V3_71_LIVE_CSV_SIGNAL_AUDIT_PIPELINE_PACKAGE_READY_AUDIT_ONLY`

Blocked status:

`GOLD_V3_71_LIVE_CSV_SIGNAL_AUDIT_PIPELINE_PACKAGE_BLOCKED_AUDIT_ONLY`

## 1. Purpose

Stage71 packages the audit-only live CSV signal flow into a repeatable local pipeline:

1. Stage69 detects GOLD V3 candidate conditions from latest closed CSV rows.
2. Stage70 converts the latest closed condition candidates into one deterministic `SIGNAL` or `NO_SIGNAL` preview row.
3. Stage71 reads Stage69/70 outputs and writes a stable latest signal snapshot for manual inspection.

Stage71 is not live trading and does not enable final signals.

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

Stage71 must preserve:

- `csv_contract: open/in-progress candles are not written to CSV`
- `csv_open_bar_exclusion_required: false`

## 4. Required inputs

Default GOLD V3 output root:

`Files/FX_OUTPUTS/gold_v3`

Required Stage69 inputs:

- `69_live_csv_condition_detector_audit_only/gold_v3_69_live_csv_condition_detector_summary.json`

Required Stage70 inputs:

- `70_live_csv_signal_decision_preview_audit_only/gold_v3_70_live_csv_signal_decision_preview_summary.json`
- `70_live_csv_signal_decision_preview_audit_only/gold_v3_70_latest_closed_signal_decision.csv`

Stage69 must be READY:

`GOLD_V3_69_LIVE_CSV_CONDITION_DETECTOR_READY_AUDIT_ONLY`

Stage70 must be READY:

`GOLD_V3_70_LIVE_CSV_SIGNAL_DECISION_PREVIEW_READY_AUDIT_ONLY`

## 5. Outputs

Output folder:

`Files/FX_OUTPUTS/gold_v3/71_live_csv_signal_audit_pipeline_package_audit_only`

Required outputs:

- `gold_v3_71_latest_signal_snapshot.csv`
- `gold_v3_71_latest_signal_snapshot.json`
- `gold_v3_71_blocker_matrix.csv`
- `gold_v3_71_validation_matrix.csv`
- `gold_v3_71_live_csv_signal_audit_pipeline_package_summary.json`
- `gold_v3_71_PASTE_ME_LIVE_CSV_SIGNAL_AUDIT_PIPELINE_PACKAGE_SUMMARY.txt`
- `GOLD_V3_71_REPORT.md`

## 6. READY conditions

Stage71 is READY if:

- Stage69 is READY.
- Stage70 is READY.
- Stage70 decision CSV exists and has exactly one decision row.
- Decision is either `SIGNAL` or `NO_SIGNAL`.
- All safety flags remain false.
- `csv_open_bar_exclusion_required=false` is preserved.

`NO_SIGNAL` is allowed and is READY when produced deterministically.

## 7. BLOCKED conditions

Stage71 must BLOCK if:

- Stage69 is missing or not READY.
- Stage70 is missing or not READY.
- Stage70 decision CSV is missing, empty, or has multiple rows.
- Decision is not `SIGNAL` or `NO_SIGNAL`.
- Any live/MT5/Discord/AI/final-signal flag is true.

## 8. Runner and BAT

Script:

`scripts/gold_v3_runtime/gold_v3_71_live_csv_signal_audit_pipeline_package.py`

BAT:

`scripts/gold_v3_runtime/bat/run_gold_v3_71_live_csv_signal_audit_pipeline_package.bat`

The BAT is a no-argument local audit runner that runs Stage69, Stage70, then Stage71. It does not place trades or send notifications.
