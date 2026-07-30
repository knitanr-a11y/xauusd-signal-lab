# BTC BCR13 — B3 outcome-blind density implementation ready

- repository: `knitanr-a11y/xauusd-signal-lab`
- branch: `feature/btc-fresh-forward-research`
- recorded: `2026-07-30T23:05:00+09:00`
- status: `BCR13_IMPLEMENTATION_AND_SYNTHETIC_TESTS_READY_FROZEN_INPUT_LOCAL_RUN_PENDING`
- B3 outcome access: no
- actual frozen-input density result: pending
- candidate promotion: forbidden

## 1. Authorization used

The user explicitly authorized:

`BCR13_B3_OUTCOME_BLIND_DENSITY_AND_STATE_MACHINE_AUDIT`

This work implemented the exact eight B3 machines frozen by BCR12 and prepared the deterministic local runner. It did not authorize or perform BCR14 value evaluation.

## 2. Created implementation

Python implementation:

`scripts/btc_ml_v1/BCR13_b3_outcome_blind_density_audit/python/run_bcr13_b3_density_audit.py`

Commit:

`be03d9a8e38d9424642653fcf488b177193579c3`

Tests:

`tests/btc_ml_v1/test_bcr13_b3_density_audit.py`

Commit:

`8195dc0b77675e27aff9d95ad8c398eed0259354`

Local runner files:

- `scripts/btc_ml_v1/BCR13_b3_outcome_blind_density_audit/00_READ_ME_FIRST.txt`
- `scripts/btc_ml_v1/BCR13_b3_outcome_blind_density_audit/01_run_BCR13.bat`
- `scripts/btc_ml_v1/BCR13_b3_outcome_blind_density_audit/02_open_latest_results.bat`

Corrected workflow commits:

- README: `e281ff1ef9f1c3fc3dcbae91520fd9584d1f0e48`
- runner BAT: `5ae358ab06c3183da2486d31ffa8d4f1721c57f4`
- result opener: `5809d2a09ed8d31aab646901a0716c028ce0480e`

The earlier runner commits remain Git history only for the output-workflow incident.

## 3. Output-workflow incident and correction

The initial BCR13 runner incorrectly wrote to a repository-relative output directory and requested three separate uploads. This departed from the established BTC BCR BAT convention.

The authoritative correction is recorded in:

- `docs/btc_ml_v1/BTC_BCR13_LOCALAPPDATA_SINGLE_UPLOAD_ZIP_WORKFLOW_CORRECTION_20260730.md`
- `configs/btc_ml_v1/btc_bcr13_localappdata_single_upload_zip_workflow_correction_20260730.json`

This was an implementation mistake, not an intentional specification change.

The corrected standard output directory is:

`C:\Users\regen\AppData\Local\xauusd_signal_lab\btc_ml_v1\outputs\BCR13_b3_outcome_blind_density_audit\LATEST`

The sole user upload file is:

`C:\Users\regen\AppData\Local\xauusd_signal_lab\btc_ml_v1\outputs\BCR13_b3_outcome_blind_density_audit\LATEST\99_UPLOAD_PACKAGE.zip`

After success, the BAT opens Explorer with that ZIP selected and pauses. Upload only the selected ZIP.

## 4. Frozen-machine fidelity

The implementation accepts only the eight BCR12 machines:

- `L ∈ {32,64}`
- `D ∈ {0.25,0.50}` frozen pre-break ATR
- `W ∈ {4,8}` theoretical M15 bars
- LONG and SHORT both retained in every machine

It validates the machine inventory against the BCR12 machine-readable contract before running. No ninth machine, threshold change, side deletion or old-family rescue is present.

## 5. Causal boundary implemented

At decision boundary `t`, the runner uses only:

- the exact fully closed M15 bar at `t-15m`;
- earlier exact fully closed M15 bars;
- deterministic ATR/range values built from those bars;
- the current exact M15 open only for an entry or exit already determined from closed history.

It does not use current-bar high/low/close, future bars, future return, future exit result, nearest/next rows, interpolation, H1/H4/D1, source labels or source state.

## 6. Frozen-input hard gate

Required input:

- rows: `30,661`
- SHA256: `b8de00d117a119f9bf2f417b6228fe0ca0779c88f71a80b134bb9244d6768148`

The default MT5 CSV is append-only and may have grown. The runner may reconstruct a prefix only when the exact first `30,661` rows, preserved at the byte level, reproduce the frozen SHA exactly. Otherwise it stops. This is not similar-file fallback and does not permit sorting, interpolation or approximate matching.

## 7. State and gap behavior

Implemented states:

- `IDLE`
- `LONG_BREAKOUT_ARMED`
- `SHORT_BREAKOUT_ARMED`
- `LONG_RETEST_SEEN`
- `SHORT_RETEST_SEEN`
- `ACTIVE_LONG`
- `ACTIVE_SHORT`

Implemented gap policy:

- pending setup with a gap before entry: `CANCEL_GAP_IN_SEQUENCE`;
- valid re-acceleration followed by a missing exact next open: `NO_TRADE_EXACT_ENTRY_MISSING`;
- active position with unavailable exact previous bar: `ACTIVE_DECISION_UNAVAILABLE_GAP`, position persists;
- no synthetic exit or fallback.

## 8. Conflict clarification

BCR12 required simultaneous-conflict counts but did not explicitly choose a side when both breakout predicates are true.

BCR13 implements the fail-closed policy:

`SIMULTANEOUS_BREAKOUT_NO_TRANSITION`

The machine remains `IDLE`; it never chooses LONG or SHORT. This adds no threshold, no side preference and no additional trial. The count is reported.

## 9. Output isolation

The inner deterministic evidence ZIP contains only label-free capability evidence:

- machine metrics;
- event counts;
- monthly entry counts;
- gate checks;
- transition ledger;
- episode timing/holding ledger;
- summary and manifest.

The runner forbids output columns named return, win/loss, PF, PnL, MFE, MAE, future exit result, entry price and exit price.

`99_UPLOAD_PACKAGE.zip` contains:

1. `BCR13_B3_OUTCOME_BLIND_DENSITY_AUDIT_20260730.zip`
2. `deterministic_repeat.json`
3. `package_sha256.txt`

No value metric is calculated or exported.

## 10. Validation completed

Local synthetic/exact-path tests:

`6 passed`

Covered:

1. LONG breakout → retest → later re-acceleration → exact-next-open entry → structural failure exit;
2. current-bar high/low/close not used at the current decision boundary;
3. pending gap cancellation without fallback;
4. simultaneous conflict remains IDLE;
5. two deterministic builds produce the same package SHA and no forbidden value columns;
6. append-only prefix rehydration is accepted only on exact SHA match.

This is implementation validation only. It is not the formal 30,661-row BCR13 result.

## 11. Deterministic real-data run

Run:

`scripts\btc_ml_v1\BCR13_b3_outcome_blind_density_audit\01_run_BCR13.bat`

Expected output directory:

`C:\Users\regen\AppData\Local\xauusd_signal_lab\btc_ml_v1\outputs\BCR13_b3_outcome_blind_density_audit\LATEST`

The runner performs two independent builds, requires identical inner package SHA256 values, creates `99_UPLOAD_PACKAGE.zip`, and opens Explorer with that ZIP selected.

Required upload after success:

`99_UPLOAD_PACKAGE.zip`

## 12. Current decision

`ACCEPT_BCR13_IMPLEMENTATION_READY_STANDARD_LOCALAPPDATA_SINGLE_UPLOAD_ZIP_RESTORED_AWAIT_FROZEN_INPUT_LOCAL_RUN_NO_OUTCOME_OPENED`

BCR13 is not complete until the exact frozen-input output is received and audited. BCR14, candidate promotion, portfolio selection, prospective start, shadow, Discord, MT5 order, live-ready and final signal remain unauthorized.
