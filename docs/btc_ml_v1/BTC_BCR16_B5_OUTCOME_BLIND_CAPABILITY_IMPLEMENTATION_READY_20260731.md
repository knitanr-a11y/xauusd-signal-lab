# BTC BCR16 — B5 outcome-blind capability implementation ready

- repository: `knitanr-a11y/xauusd-signal-lab`
- branch: `feature/btc-fresh-forward-research`
- recorded: `2026-07-31T00:03:00+09:00`
- status: `BCR16_B5_IMPLEMENTATION_AND_SYNTHETIC_TESTS_READY_FROZEN_INPUT_LOCAL_RUN_PENDING`
- B5 outcome access: no
- candidate promotion: forbidden

## 1. Research assessment

Candidate-level traction is not yet established. BCR13 rejected all B3 machines before value access.

The process-level traction is real: the research is eliminating mechanisms without post-result rescue. B5 is a materially new H1-event/M15-execution family with an explicitly finite active lifecycle, so it directly tests a different hypothesis rather than repairing B3.

## 2. Frozen BCR15 family

`B5_CAUSAL_H1_IMPULSE_M15_PULLBACK_RECLAIM`

Eight machines:

- prior H1 range `R = 6 / 12`;
- H1 impulse body `B = 0.75 / 1.00 ATR`;
- first M15 pullback deadline `W = 8 / 16 bars`.

All directions remain present in every machine.

## 3. Implementation

Python:

`scripts/btc_ml_v1/BCR16_b5_h1_impulse_m15_reclaim_capability_audit/python/run_bcr16_b5_capability_audit.py`

Commit:

`4325fce64eff5bbaa234bc3f401125a64f2250dc`

Tests:

`tests/btc_ml_v1/test_bcr16_b5_capability_audit.py`

Commit:

`007ef3620d2f3af9df3f2d03c9339fe53a5ba2c3`

Local synthetic/exact-path result:

`6 passed`

## 4. H1 causal boundary

H1 is derived only from exact M15 bars. A valid H1 requires all four constituent open times at minutes `00, 15, 30, 45`.

Partial H1, current forming H1, nearest/next rows, sorting and interpolation are forbidden.

## 5. State lifecycle

Implemented path:

1. fully closed H1 impulse;
2. later M15 pullback into the frozen 38.2%–61.8% impulse range zone;
3. later M15 reclaim with pre-bar M15 ATR and previous exact M15 high/low;
4. entry at next exact M15 open;
5. structural success, structural failure or fixed 32-M15-bar thesis expiry.

The 32-bar expiry is a fixed part of the new family, not an outcome-driven rescue dimension.

## 6. Validation coverage

The six tests verify:

1. incomplete H1 groups are excluded;
2. complete LONG impulse → pullback → reclaim → exact-open entry → structural-success exit;
3. fixed 32-bar expiry closes an otherwise unresolved episode;
4. pending gap cancellation without fallback;
5. deterministic two-build package and no forbidden value columns;
6. append-only prefix accepted only on exact frozen SHA match.

## 7. Output workflow

Run:

`scripts\btc_ml_v1\BCR16_b5_h1_impulse_m15_reclaim_capability_audit\01_run_BCR16.bat`

Output:

`C:\Users\regen\AppData\Local\xauusd_signal_lab\btc_ml_v1\outputs\BCR16_b5_h1_impulse_m15_reclaim_capability_audit\LATEST`

The BAT creates and selects:

`99_UPLOAD_PACKAGE.zip`

Upload only that ZIP.

Runner commits:

- main BAT: `ffa8baeb84a7691bde814fefa1966399ba95fc8b`
- result opener: `87fb80243e93dc74a8a36ae4a805e6f421c85dae`
- README: `231e6629521d1e91cf7a7d735d9ca619a274326c`

## 8. Authorization boundary

The current broad instruction authorizes BCR15 contract creation and BCR16 label-free implementation/run preparation.

It does not authorize:

- B5 return, win/loss, PF, PnL, MFE or MAE;
- value evaluation;
- outcome-driven machine or side deletion;
- threshold rescue;
- portfolio, prospective start or shadow;
- Discord, MT5 order, live-ready or final signal.

## 9. Current decision

`ACCEPT_BCR16_IMPLEMENTATION_READY_AWAIT_EXACT_FROZEN_INPUT_99_UPLOAD_PACKAGE_NO_OUTCOME_OPENED_NO_PROMOTION`
