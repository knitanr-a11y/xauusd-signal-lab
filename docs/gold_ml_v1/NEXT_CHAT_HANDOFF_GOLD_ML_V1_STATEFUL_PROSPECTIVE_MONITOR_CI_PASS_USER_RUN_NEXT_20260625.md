# GOLD_ML_V1 Stateful Prospective Monitor CI PASS — User Run Next

Date: 2026-06-25

Formal status:

`GOLD_ML_V1_024_STATEFUL_PROSPECTIVE_MONITOR_ONE_CLICK_USER_RUN_READY_AUDIT_ONLY`

## Completed and verified

The first fresh prospective run completed successfully from closed goldsharp bars strictly after the frozen cutoff:

- cutoff: `2026-06-23 18:15:00` MT5 server close
- exit code: 0
- observation: `NO_CANDIDATE_YET`
- candidate rows: 0
- unresolved rows: 0
- accepted parent events: 0
- error: none

Machine-readable record:

`config/gold_ml_v1/fresh_prospective_first_run_pass_20260625.json`

The zero-candidate result is a valid observation. It is not permission to alter thresholds, candidate rules, horizons or IDs.

## New phase

Stateful audit-only prospective monitoring is implemented:

- `scripts/gold_ml_v1/monitoring/prospective_monitor_state.py`
- `scripts/gold_ml_v1/monitoring/run_prospective_monitor_cycle.py`
- `scripts/gold_ml_v1/monitoring/windows/run_prospective_monitor_cycle.bat`
- `config/gold_ml_v1/prospective_monitoring_20260625.json`
- `tests/gold_ml_v1/test_prospective_monitor_state.py`

CI record:

`config/gold_ml_v1/prospective_monitoring_ci_pass_20260625.json`

Validation workflow run `28166897114`, job `83421022660`, passed:

- Python compilation
- governance guardrails
- cost-stress contract
- cost-stress core registry
- fresh prospective engine
- stateful prospective monitor tests

The temporary validation PR was closed without merge.

## What one monitoring cycle does

Each root-BAT run:

1. reads the current closed M1, M15, H1, H4 and D1 goldsharp files;
2. verifies that all previously observed closed-bar rows remain unchanged and that the files were not truncated;
3. causally replays the frozen nine candidates from the fixed cutoff;
4. compares the full replay with the persisted cumulative ledgers;
5. adds only candidate keys not previously recorded;
6. allows an existing candidate only to remain unresolved or move from `UNRESOLVED` to `RESOLVED`;
7. allows a parent event previously suppressed by frozen non-overlap to become accepted after the earlier unresolved parent is later resolved;
8. rejects candidate disappearance, duplicate keys, resolved-result rewrites, historical-bar mutation and time regression;
9. updates all ledgers transactionally after every staged output file is complete;
10. creates a timestamped snapshot and backup.

## Persistent output

Output directory:

`outputs/gold_ml_v1/prospective_monitoring`

Primary state files:

- `monitor_state.json`
- `monitor_candidate_ledger.csv`
- `monitor_parent_event_ledger.csv`
- `monitor_candidate_summary.csv`
- `monitor_run_history.csv`
- `monitor_new_candidates_latest.csv`
- `monitor_resolved_transitions_latest.csv`
- `monitor_new_parent_events_latest.csv`
- `monitor_parent_admission_transitions_latest.csv`
- `input_provenance.json`
- `monitor_latest_snapshot_summary.json`
- `LATEST_RUN_SUMMARY.txt`
- `MONITOR_RUN_ERROR.txt`
- `UPLOAD_THIS_GOLD_ML_V1.txt`

## Important scope

This is not a background service yet.

`RUN_GOLD_ML_V1_NEXT.bat` performs one monitoring cycle. Running it again after newer closed bars are available advances the same cumulative ledger.

No Windows scheduled task is installed. No MT5 order, final signal, Discord notification, API call, promotion, registration or new candidate exploration occurs.

## User action

1. Pull `main` in GitHub Desktop.
2. Double-click repository-root `RUN_GOLD_ML_V1_NEXT.bat`.
3. Explorer opens with this selected:

`outputs/gold_ml_v1/prospective_monitoring/UPLOAD_THIS_GOLD_ML_V1.txt`

4. Drag that file into ChatGPT.

Do not run the internal phase BAT directly. The root launcher supplies the MQL5 Files path and frozen monitoring config.
