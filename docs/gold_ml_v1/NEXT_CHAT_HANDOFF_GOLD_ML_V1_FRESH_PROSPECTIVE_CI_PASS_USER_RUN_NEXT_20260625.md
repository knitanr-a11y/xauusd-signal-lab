# GOLD_ML_V1 Fresh Prospective CI PASS — User Run Next

Date: 2026-06-25

Formal status:

`GOLD_ML_V1_023_FRESH_PROSPECTIVE_CI_PASS_ONE_CLICK_USER_RUN_READY_AUDIT_ONLY`

## Completed prior phases

Batch023 warmup bridge remains verified PASS for all nine frozen candidates with zero missing/extra, entry, exit, R or direction mismatch.

The corrected frozen cost-stress run remains verified PASS:

- RAW baseline parity checks: 1687
- candidate gate PASS: 9
- candidate gate FAIL: 0
- all nine candidates passed all twelve predeclared cost scenarios
- no post-result retuning or candidate replacement
- no automatic next phase was run

Do not rerun cost stress.

## Fresh prospective implementation

Production implementation exists on main:

- `scripts/gold_ml_v1/prospective/fresh_prospective_engine.py`
- `scripts/gold_ml_v1/prospective/run_fresh_prospective_confirmation.py`
- `scripts/gold_ml_v1/prospective/windows/run_fresh_prospective_confirmation.bat`
- `config/gold_ml_v1/fresh_prospective_confirmation_20260625.json`
- `tests/gold_ml_v1/test_fresh_prospective_engine.py`

The root user launcher remains:

`RUN_GOLD_ML_V1_NEXT.bat`

The root launcher calls the dedicated internal phase BAT with the MQL5 Files directory and frozen config path. The internal BAT must not be run directly by the user.

## CI verification

Machine-readable record:

`config/gold_ml_v1/fresh_prospective_ci_pass_20260625.json`

Implementation validation:

- validated main commit: `8cdb858f56288a5cc6e3ad4a49fa25beaf8a6f3a`
- temporary PR: 26
- workflow run: `28165292690`
- job: `83415630145`
- PR merged: no

Final current-state validation after status and governance updates:

- validated main commit: `3ac2634dc76b6847583517e4afdf05fbbd866229`
- temporary PR: 29
- validation head: `8e7b126d76fd9088a58c58b2ceb4f2cf568c5f55`
- workflow run: `28165730901`
- job: `83417103397`
- PR merged: no

All relevant steps passed in the final validation:

- prospective and cost-stress Python compilation
- governance guardrails
- cost-stress frozen contract
- cost-stress core-registry correction
- fresh prospective reader, cutoff, SL priority, unresolved handling and frozen-nine tests

The validation branches added only temporary test-path trigger files. They were closed without merge and supplied no production changes.

## Prospective contract

Only decisions with:

`decision_close_time > 2026-06-23 18:15:00`

in MT5 server time are included. A decision exactly at the cutoff is excluded.

Authoritative closed-bar inputs are:

- `goldsharp_m1.csv`
- `goldsharp_m15.csv`
- `goldsharp_h1.csv`
- `goldsharp_h4.csv`
- `goldsharp_d1.csv`

Candidate generation is causal and uses no future exit information. The nine candidate IDs, rules, thresholds, horizons and lineage assignments remain frozen.

Unresolved candidates remain explicit. No synthetic future exit or R is fabricated. Parent events suppressed by the frozen non-overlap rule remain in the audit output. `NO_CANDIDATE_YET` is a valid observation and not a runner error.

## One-click output

Output directory:

`outputs/gold_ml_v1/fresh_prospective_confirmation`

The file to upload is:

`outputs/gold_ml_v1/fresh_prospective_confirmation/UPLOAD_THIS_GOLD_ML_V1.txt`

After the root BAT completes, Explorer opens with this file selected.

## User action

1. Pull `main` in GitHub Desktop.
2. Double-click repository-root `RUN_GOLD_ML_V1_NEXT.bat`.
3. Drag the selected `UPLOAD_THIS_GOLD_ML_V1.txt` file into ChatGPT.

## Still forbidden

- new candidate exploration
- prospective retuning
- live_ready
- final signal
- MT5 order
- Discord
- AI API
- live hook
- automatic promotion
- automatic registration

A successful local prospective report is an audit observation only and does not authorize live use.
