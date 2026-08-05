# BTC AI V1 — Second-Cycle Final-Test Translation Addendum

Date: 2026-08-03  
Status: `FROZEN_BEFORE_ROBUSTNESS_OUTPUT_AND_BEFORE_FINAL_TEST_ACCESS`

This addendum defines the deterministic continuation from the four development folds to the untouched test. It applies only if a second-cycle candidate passes every frozen robustness gate.

- model training: 2023-01-01 through 2025-06-30;
- past-only calibration: 2025-07-01 through 2025-12-31;
- untouched test: 2026-01-01 through 2026-07-31, exactly seven calendar months;
- same model, feature set, direction, percentile and event policy;
- same development-selected stop, target and horizon;
- fixed 22.50 USD spread and exact-M1 replay;
- final-test events are frozen before PnL is computed;
- no 2026 labels may train or calibrate the model;
- no second attempt or post-result rescue.

Every final-test count must be reported as seven-calendar-month activity, not as a total count alone.