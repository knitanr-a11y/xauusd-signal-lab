# NEXT CHAT HANDOFF — BTC BCR13 implementation ready, frozen-input local run pending

- repository: `knitanr-a11y/xauusd-signal-lab`
- authoritative branch: `feature/btc-fresh-forward-research`
- verified at: `2026-07-30T22:11:00+09:00`
- status: `BTC_REDESIGN_BCR13_IMPLEMENTATION_READY_FROZEN_INPUT_LOCAL_RUN_PENDING_NO_OUTCOME_OPENED`
- current stage: `BCR13_B3_OUTCOME_BLIND_DENSITY_AND_STATE_MACHINE_AUDIT`
- actual frozen-input result: pending
- BCR14 authorization: `NOT_AUTHORIZED`

## 1. Current formal decision

`ACCEPT_BCR13_IMPLEMENTATION_READY_AWAIT_USER_LOCAL_FROZEN_INPUT_PACKAGE_NO_PROMOTION`

The exact eight B3 machines are implemented and synthetic/exact-path tests pass. The formal 30,661-row density/state-machine result has not been run in this environment because the authoritative CSV exists on the user's Windows machine, not in GitHub or the current execution environment.

No B3 value outcome has been opened.

## 2. BCR13 implementation authority

Implementation readiness document:

`docs/btc_ml_v1/BTC_BCR13_B3_OUTCOME_BLIND_DENSITY_IMPLEMENTATION_READY_20260730.md`

Machine-readable readiness record:

`configs/btc_ml_v1/btc_bcr13_b3_outcome_blind_density_implementation_ready_20260730.json`

Implementation:

`scripts/btc_ml_v1/BCR13_b3_outcome_blind_density_audit/python/run_bcr13_b3_density_audit.py`

Runner:

`scripts/btc_ml_v1/BCR13_b3_outcome_blind_density_audit/01_run_BCR13.bat`

Tests:

`tests/btc_ml_v1/test_bcr13_b3_density_audit.py`

## 3. Completed implementation facts

- exactly `8` B3 machines;
- `L = 32 / 64`;
- `D = 0.25 / 0.50 ATR`;
- `W = 4 / 8 M15 bars`;
- LONG and SHORT retained in every machine;
- current-bar high/low/close not used;
- exact previous closed M15 only;
- no future bar, future return or future-exit result;
- no nearest/next/interpolation/similar-file fallback;
- no H1/H4/D1, M7C state or source label;
- no Track A/B1/B2/B4 rescue;
- no value fields in output;
- deterministic two-build package comparison;
- local synthetic/exact-path tests: `6 passed`.

## 4. Frozen-input rehydration boundary

Required frozen input:

- SHA256: `b8de00d117a119f9bf2f417b6228fe0ca0779c88f71a80b134bb9244d6768148`
- rows: `30,661`
- symbol: `BTCUSD#`

The default MT5 source is append-only and may now contain more rows. The runner may use a prefix only when the exact first 30,661 data rows, preserved at the byte level, reproduce the frozen SHA exactly. Otherwise it fails closed.

## 5. Conflict clarification

If both LONG and SHORT breakout predicates are simultaneously true, the implementation records:

`SIMULTANEOUS_BREAKOUT_NO_TRANSITION`

It remains `IDLE` and selects neither side. This is a fail-closed implementation clarification; it does not add a threshold or a trial.

## 6. User action now

Run:

`scripts/btc_ml_v1/BCR13_b3_outcome_blind_density_audit/01_run_BCR13.bat`

After a successful deterministic repeat, upload:

1. `BCR13_B3_OUTCOME_BLIND_DENSITY_AUDIT_20260730.zip`
2. `deterministic_repeat.json`
3. `package_sha256.txt`

Expected output directory:

`outputs/btc_ml_v1/BCR13_b3_outcome_blind_density_audit/latest/`

If the BAT fails, provide the complete console error. Do not substitute another CSV or modify the expected SHA/row count.

## 7. What the package may contain

Only label-free capability evidence:

- breakout/retest/re-acceleration counts;
- entries, structural exits and cancellations;
- LONG/SHORT counts;
- monthly entry density;
- holding and occupancy;
- pending age;
- gap and exact-entry-missing counts;
- simultaneous conflicts;
- state/gate integrity;
- deterministic manifest and package SHA.

It must not contain return, win/loss, PF, PnL, MFE, MAE, entry price, exit price or future-exit result.

## 8. Authorization boundary

Currently authorized:

- run the frozen BCR13 implementation on the exact frozen input;
- upload and audit its label-free package;
- report all eight machines without rescue.

Not authorized:

- BCR14 value/PnL evaluation;
- another B3 parameter, ninth machine or side deletion;
- Track A/B1/B2/B4 retune or rescue;
- portfolio selection;
- prospective start or shadow;
- Discord, MT5 order, live-ready or final signal;
- Collector/M7C/M8C/M9/M10 changes;
- GOLD/MOCHIPOYO writeback.

## 9. Runtime protection

Collector, M7C, M8C, M9 and M10 remain unchanged and running. BCR13 reads no MOCHIPOYO runtime files.

## 10. Restart rules

Read the files listed by `START_HERE_BTC_CANDIDATE_RESEARCH_NEXT_CHAT.md` in exact order using ref:

`feature/btc-fresh-forward-research`

Do not use main/default branch, AGENTS.md, GOLD documents, old BTC handoffs, FF05 recovery V3-V11 or unreferenced state/action/handoff as restart authority.
