# GOLD_ML_V1 Fresh Prospective Implemented — User Run Next

Date: 2026-06-25

Formal status:

`GOLD_ML_V1_022_FRESH_PROSPECTIVE_ONE_CLICK_USER_RUN_READY_AUDIT_ONLY`

## Prior phase

The corrected frozen cost-stress run passed:

- RAW baseline parity checks: 1687
- candidate gate PASS: 9
- candidate gate FAIL: 0
- all nine frozen candidates passed all twelve frozen cost scenarios
- no automatic next phase was run

Do not rerun cost stress.

## Fresh prospective phase

Implementation files:

- `scripts/gold_ml_v1/prospective/fresh_prospective_engine.py`
- `scripts/gold_ml_v1/prospective/run_fresh_prospective_confirmation.py`
- `scripts/gold_ml_v1/prospective/windows/run_fresh_prospective_confirmation.bat`
- `config/gold_ml_v1/fresh_prospective_confirmation_20260625.json`

User-facing entrypoint remains:

`RUN_GOLD_ML_V1_NEXT.bat`

The root BAT reads the active upload path from:

`outputs/gold_ml_v1/next_action/CURRENT_UPLOAD_PATH.txt`

It no longer hardcodes the cost-stress output folder. After the phase finishes, Explorer opens with the current phase upload file selected.

## Frozen prospective cutoff

Only decisions with:

`decision_close_time > 2026-06-23 18:15:00`

in MT5 server time are included.

A decision exactly at the cutoff is excluded.

## Authoritative live candle inputs

The phase reads closed bars from the MQL5 Files directory:

- `goldsharp_m1.csv`
- `goldsharp_m15.csv`
- `goldsharp_h1.csv`
- `goldsharp_h4.csv`
- `goldsharp_d1.csv`

CSV time is bar-open time in MT5 server time. The latest valid row is closed by contract.

The reader supports comma, semicolon or tab-separated files, removes only incomplete trailing append rows, blocks incomplete non-trailing rows, duplicate timestamps and out-of-order timestamps, and never silently sorts time.

## Candidate and causality contract

Frozen candidates remain exactly:

- GML1-PROV-007
- GML1-PROV-008
- GML1-WATCH-022-B
- GML1-PROV-010
- GML1-PROV-015
- GML1-PROV-020
- GML1-WATCH-021-A
- GML1-WATCH-021-B
- GML1-WATCH-021-C

No candidate rule, threshold, ID, period or lineage was changed.

Candidate generation uses only information available at the decision close. Future exit information is not used to decide whether the current candidate exists.

Previously accepted parent trades affect later non-overlap admission only through whether they were still open at that later decision time. Suppressed parent events are written to the audit output instead of being silently discarded.

## Resolution handling

M15/H4 parent contract:

- horizon: 6 hours
- TP/SL: 1 ATR
- same-M1 TP/SL priority: SL
- hit and time exit timestamp: M1 close

H1/D1 parent contract:

- horizon: 48 hours
- TP/SL: 1 ATR
- same-M1 TP/SL priority: SL
- hit and time exit timestamp: M1 open

If enough M1 bars already exist, the outcome is recorded as resolved.

If the horizon is incomplete and neither TP nor SL has occurred, the row remains:

`UNRESOLVED`

No synthetic future exit or R value is created. Current R is diagnostic only and unresolved rows are excluded from resolved performance metrics.

`NO_CANDIDATE_YET` is a valid prospective observation and does not make the runner fail.

## Outputs

Output directory:

`outputs/gold_ml_v1/fresh_prospective_confirmation`

Files:

- `fresh_prospective_candidate_registry.csv`
- `fresh_prospective_parent_event_audit.csv`
- `fresh_prospective_candidate_summary.csv`
- `input_provenance.json`
- `fresh_prospective_summary.json`
- `LATEST_RUN_SUMMARY.txt`
- `FRESH_PROSPECTIVE_RUN_ERROR.txt`
- `UPLOAD_THIS_GOLD_ML_V1.txt`

Previous nonempty output is moved to a timestamped sibling backup before each run.

The upload file combines the dispatcher status, console tail, prospective summary, error trace, candidate summary, candidate registry and parent-event audit.

## PASS meaning

Runner PASS means:

- required closed-bar inputs were present;
- each timeframe had closed coverage strictly after the cutoff;
- time/order/schema checks passed;
- indicator state was available;
- candidate and parent-event reports were generated.

PASS does not require a candidate to appear and does not authorize promotion or live use.

## User action

1. Pull main in GitHub Desktop.
2. Double-click repository-root `RUN_GOLD_ML_V1_NEXT.bat`.
3. When Explorer opens, drag `UPLOAD_THIS_GOLD_ML_V1.txt` into ChatGPT.

Do not run the phase BAT directly; the root launcher supplies the MQL5 Files directory and frozen config path.

## Switches remain OFF

- new exploration
- live_ready
- final_signal
- MT5 order
- Discord
- AI API
- live hook
- automatic promotion
- automatic registration
