# GOLD_ML_V1 Cost Stress Implemented - User Run Next

Date: 2026-06-25  
Repository: `knitanr-a11y/xauusd-signal-lab`  
Mode: **AUDIT ONLY**

## Current status

`GOLD_ML_V1_017_COST_STRESS_IMPLEMENTED_ONE_CLICK_USER_RUN_READY_AUDIT_ONLY`

The cost-stress implementation is committed and the common one-click dispatcher is configured. No cost-stress result is claimed yet because the user has not run the local action after pulling this implementation.

## Frozen candidate pool

Accumulated audit-only candidates remain exactly:

- GML1-PROV-007
- GML1-PROV-008
- GML1-WATCH-022-B
- GML1-PROV-010
- GML1-PROV-015
- GML1-PROV-020
- GML1-WATCH-021-A
- GML1-WATCH-021-B
- GML1-WATCH-021-C

Research-only candidates remain unchanged:

- GML1-WATCH-014-A
- GML1-WATCH-022-A
- GML1-WATCH-023-A

No candidate was added, removed, replaced, renamed, promoted or demoted.

## Predeclared cost-stress contract

Frozen config:

`config/gold_ml_v1/cost_stress_raw_reconstructed_20260625.json`

Primary population:

`RAW_RECONSTRUCTED`

Separately reported historical audit population:

`WARMUP_BRIDGE_EXACT`

The bridge rows are not raw-only parity and remain forbidden for exploration, tuning, model selection, promotion, prospective decisions, live signals, MT5 orders and Discord notifications.

The fixed grid contains **12 scenarios**, declared before local execution:

- spread 1.0x with slippage 0, 5, 10 and 20 points per side
- spread 1.5x with slippage 0, 5, 10 and 20 points per side
- spread 2.0x with slippage 0, 5, 10 and 20 points per side

The grid is a full Cartesian product. It must not be changed after results are seen.

## Execution-stress method

The implementation reads the already verified nine exact-schema warmup-bridge registries. It does not rerun replay V1-V5 and does not call a ZIP replay an original generator.

For every frozen registry row it:

1. verifies the exact entry exists in the frozen M1 raw snapshot;
2. recovers the frozen one-risk-unit price distance from registry entry price, exit price and R;
3. replays the registered trade over its frozen lineage horizon;
4. uses only M1 bars from the registered entry through the frozen horizon for outcome evaluation;
5. preserves same-M1 SL priority;
6. applies the scenario spread multiplier to the long entry reference;
7. applies fixed adverse slippage per side to entry and exit fills;
8. holds the registered candidate trade membership fixed;
9. never uses stressed outcomes to alter candidate conditions or candidate membership.

Baseline spread 1.0x / slippage 0 must reproduce every registry entry price, exit price, exit time and R. Any mismatch fails closed with a nonzero exit code.

## Predeclared stress gate

For `RAW_RECONSTRUCTED`, each candidate/scenario is marked PASS only when:

- trade count is at least 30;
- profit factor is at least 1.0;
- mean R is greater than 0.

A candidate overall stress gate is PASS only when all 12 predeclared scenarios pass.

`WARMUP_BRIDGE_EXACT` is always `NOT_ELIGIBLE_AUDIT_ONLY`; it is reported but never used for promotion.

The runner exit code has a separate meaning:

- exit code 0: provenance, baseline parity, validation and report generation PASS;
- nonzero: validation or report-generation failure;
- candidate stress-gate FAIL is preserved as a valid result and does not cause retuning or automatic rescue.

## Lineage handling

The two frozen lineages are reported separately:

- `M15_H4_BREAKOUT_FILTER_LINEAGE`
- `H1_D1_BREAKOUT_FILTER_LINEAGE`

Same-lineage candidates are not treated as independent evidence. Lineage tables use candidate-level ranges and medians. Trades, profit and PF are not pooled or summed across same-lineage candidates.

## Implemented files

- `config/gold_ml_v1/cost_stress_raw_reconstructed_20260625.json`
- `scripts/gold_ml_v1/cost_stress/cost_stress_contract.py`
- `scripts/gold_ml_v1/cost_stress/cost_stress_engine.py`
- `scripts/gold_ml_v1/cost_stress/cost_stress_reports.py`
- `scripts/gold_ml_v1/cost_stress/run_cost_stress_raw_reconstructed.py`
- `scripts/gold_ml_v1/cost_stress/run_cost_stress_raw_reconstructed.bat`
- `tests/gold_ml_v1/test_cost_stress_contract.py`
- `config/gold_ml_v1/next_local_action.json`
- this handoff

The stable user-facing launcher remains:

`RUN_GOLD_ML_V1_NEXT.bat`

## Fail-closed provenance checks

The local runner verifies:

- all six frozen raw CSV SHA256 values;
- verified Batch023 ZIP SHA256 recorded in local metadata;
- warmup-bridge local metadata status PASS and exit code 0;
- warmup-bridge summary and parity CSV status;
- exact set of nine registry files;
- exact candidate IDs and directions;
- frozen RAW/bridge/total row counts for each candidate;
- registry file hashes for the new run provenance artifact;
- baseline entry, exit, exit-time and R parity for every row;
- all required output files.

A validation failure writes an error trace and exits nonzero.

## Output contract

The runner safely backs up a previous non-empty output folder and writes to:

`outputs/gold_ml_v1/cost_stress_raw_reconstructed`

Required outputs include:

- candidate results for `RAW_RECONSTRUCTED`;
- candidate results for `WARMUP_BRIDGE_EXACT`;
- yearly results for each population;
- lineage results for each population;
- candidate overall PASS/FAIL table;
- trade-level scenario audit CSV;
- input provenance JSON;
- complete summary JSON;
- `LATEST_RUN_SUMMARY.txt`;
- `COST_STRESS_RUN_ERROR.txt`.

Candidate and yearly tables include trade count, win rate, PF, mean R, median R, worst year or month, baseline deltas, spread 1.5x, spread 2.0x and every fixed-slippage condition.

## One-click next action

`config/gold_ml_v1/next_local_action.json` is now `mode=bat` and points only to the frozen cost-stress runner.

The user instruction is exactly:

**GitHub DesktopでPullして、RUN_GOLD_ML_V1_NEXT.batをダブルクリックしてください**

After the run, stop and review the generated summary. The runner must not automatically begin fresh prospective confirmation.

## Still blocked after cost stress

Even if all candidate stress gates pass, the following remain required:

1. review and record the local cost-stress result;
2. implement a separate fail-closed fresh prospective confirmation phase;
3. use only goldsharp closed bars after `2026-06-23 18:15:00` MT5 server close;
4. obtain an explicit audit record and explicit user approval before any new exploration batch;
5. obtain explicit manual authorization before registration or any live function.

## Switches that remain OFF

- new exploration
- live_ready
- final_signal
- MT5 order
- Discord
- AI API
- live hook
- automatic promotion
- automatic registration

## Test honesty

Syntax and repository governance tests may be run before commit. A GitHub Actions CI result must not be claimed PASS unless an actual workflow result is observed for the commit.
