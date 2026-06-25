# GOLD_ML_V1 Cost-Stress Core-Registry Fix - User Rerun Next

Date: 2026-06-25  
Repository: `knitanr-a11y/xauusd-signal-lab`  
Mode: **AUDIT ONLY**

## Current formal status

`GOLD_ML_V1_018_COST_STRESS_CORE_REGISTRY_FIX_ONE_CLICK_USER_RERUN_READY_AUDIT_ONLY`

## Failed local attempt preserved

The first cost-stress local attempt stopped fail-closed with exit code 4 before any candidate stress result was produced.

Observed error:

`GML1-PROV-010_warmup_bridge_exact_schema_registry.csv missing columns: ['entry_price', 'exit_price']`

Classification:

`INPUT_SCHEMA_ASSUMPTION_BUG_BEFORE_ANY_COST_STRESS_RESULT`

No threshold, feature, direction, TP, SL, horizon, eligibility, exclusion, onset, execution grid, candidate ID, candidate membership, year split, slippage grid or pass/fail gate was changed in response to a result. There was no valid cost-stress result to tune against.

## Root cause

The original cost-stress loader incorrectly required `entry_price` and `exit_price` in every `*_warmup_bridge_exact_schema_registry.csv`.

That assumption is invalid because the exact-schema files preserve the source registry schema. `GML1-PROV-010` and related H1-D1 registries do not necessarily contain those price columns, even though their verified core fields are present and Batch023 parity is PASS.

The authoritative warmup-bridge contract is the verified core registry:

`*_warmup_bridge_core_registry.csv`

Required fields are only:

- candidate_id
- decision_close_time
- entry_time
- exit_time
- r_value
- direction
- trade_core_source

## Corrected RAW_RECONSTRUCTED method

The corrected runner uses only `RAW_RECONSTRUCTED` rows for the 12 cost scenarios.

For each RAW row it:

1. uses the verified core registry row;
2. requires the exact M1 entry bar;
3. derives entry price from frozen M1 open plus recorded spread;
4. recovers the frozen risk distance from the entry-time closed decision bar using the recovered lineage contract;
5. uses M15 simple rolling TR14 for the M15-H4 lineage;
6. uses H1 Wilder ATR14 for the H1-D1 lineage;
7. replays the frozen horizon on M1;
8. preserves same-M1 SL priority;
9. compares baseline R and exit time to the verified core registry;
10. compares entry or exit prices only when the source registry actually supplies those fields;
11. fails closed on any baseline mismatch.

No open bar, future higher-timeframe value, future candidate result or post-result rule change is used.

## Corrected WARMUP_BRIDGE_EXACT method

`WARMUP_BRIDGE_EXACT` remains completely separate from the RAW primary population.

Because pre-2023 indicator state and complete price/risk fields are unavailable, the runner does not invent spread or slippage results for bridge rows.

Bridge output contains:

- exact core baseline trade count;
- exact core win rate;
- exact core PF;
- exact core mean R;
- exact core median R;
- exact core worst year and period where applicable;
- `stress_replay_status=NOT_CALCULATED_AUDIT_ONLY`;
- `stress_gate_status=NOT_ELIGIBLE_AUDIT_ONLY`;
- an explicit blocker explaining why exact cost replay is unavailable.

This satisfies the separate-reporting requirement without presenting proxy or synthetic bridge results as exact.

## Frozen cost grid remains unchanged

The 12 RAW scenarios remain exactly:

- spread 1.0x with slippage 0, 5, 10 and 20 points per side;
- spread 1.5x with slippage 0, 5, 10 and 20 points per side;
- spread 2.0x with slippage 0, 5, 10 and 20 points per side.

The RAW pass gate remains unchanged:

- trade count at least 30;
- PF at least 1.0;
- mean R greater than 0;
- overall candidate PASS only if all 12 scenarios PASS.

Candidate FAIL remains a preserved result and is not permission to retune.

## BAT placement

The phase BAT is now stored in a dedicated folder:

`scripts/gold_ml_v1/cost_stress/windows/run_cost_stress_raw_reconstructed.bat`

The previous phase BAT located directly under `scripts/gold_ml_v1/cost_stress/` was removed.

The repository-root file remains intentionally present as the stable one-click dispatcher required by the project contract:

`RUN_GOLD_ML_V1_NEXT.bat`

The user only starts the repository-root dispatcher. It reads `next_local_action.json` and launches the phase BAT from the dedicated `windows` folder.

## Corrected files

- `scripts/gold_ml_v1/cost_stress/cost_stress_contract.py`
- `scripts/gold_ml_v1/cost_stress/cost_stress_engine.py`
- `scripts/gold_ml_v1/cost_stress/cost_stress_reports.py`
- `scripts/gold_ml_v1/cost_stress/run_cost_stress_raw_reconstructed.py`
- `scripts/gold_ml_v1/cost_stress/windows/run_cost_stress_raw_reconstructed.bat`
- `config/gold_ml_v1/cost_stress_raw_reconstructed_20260625.json`
- `config/gold_ml_v1/next_local_action.json`
- `config/gold_ml_v1/current_state_snapshot_20260624.json`
- `tests/gold_ml_v1/test_cost_stress_core_registry_fix.py`
- `.github/workflows/gold_ml_v1_cost_stress_tests.yml`
- this handoff

## Outputs and failure handling

The corrected runner continues to:

- create the output folder before writing;
- move a prior non-empty output folder to a timestamped backup;
- verify all six frozen raw SHA256 values;
- verify Batch023 ZIP provenance recorded in local metadata;
- verify warmup-bridge PASS metadata and nine-candidate parity;
- verify exact RAW/bridge row counts;
- write CSV, JSON, `LATEST_RUN_SUMMARY.txt` and `COST_STRESS_RUN_ERROR.txt`;
- return 0 only when validation and report generation complete;
- stop without starting fresh prospective confirmation, registration or live operation.

## Next user action

**GitHub DesktopでPullして、RUN_GOLD_ML_V1_NEXT.batをダブルクリックしてください**

After the rerun, upload or paste:

`outputs/gold_ml_v1/cost_stress_raw_reconstructed/LATEST_RUN_SUMMARY.txt`

Do not manually run Python, PowerShell or the phase BAT.

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

Fresh prospective confirmation remains a later, separately implemented and reviewed phase.
