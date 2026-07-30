# NEXT CHAT HANDOFF — BTC BCR16 implementation ready, frozen-input local run pending

- repository: `knitanr-a11y/xauusd-signal-lab`
- authoritative branch: `feature/btc-fresh-forward-research`
- verified at: `2026-07-31T00:03:00+09:00`
- status: `BTC_REDESIGN_BCR16_B5_IMPLEMENTATION_READY_FROZEN_INPUT_LOCAL_RUN_PENDING_NO_OUTCOME_OPENED`
- current stage: `BCR16_B5_OUTCOME_BLIND_DENSITY_AND_STATE_MACHINE_AUDIT`
- actual frozen-input result: pending
- value-stage authorization: `NOT_AUTHORIZED`

## 1. Honest traction assessment

Candidate-level traction is still weak: BCR13 produced zero B3 capability survivors.

Research-process traction is positive. B3 was rejected before PnL access, and no threshold/side/exit rescue was performed. BCR15/BCR16 now test a materially different H1-event/M15-execution mechanism with a finite pre-frozen lifecycle.

## 2. BCR13 remains closed

- accepted BCR13 inner package SHA256: `cc1483c0e8b538eb32b67dce0a10df8733c5e7f5f924c9080f945ebddc72e51d`
- capability pass/fail: `0 / 8`
- B3: `CLOSED_NO_CAPABILITY_SURVIVOR_NO_RESCUE`
- BCR14: `NOT_APPLICABLE_ZERO_SURVIVORS`
- B3 value fields: unopened

## 3. BCR15 frozen family

Family:

`B5_CAUSAL_H1_IMPULSE_M15_PULLBACK_RECLAIM`

Contract:

1. `docs/btc_ml_v1/BTC_BCR15_CAUSAL_H1_IMPULSE_M15_PULLBACK_RECLAIM_DESIGN_CONTRACT_20260731.md`
2. `configs/btc_ml_v1/btc_bcr15_causal_h1_impulse_m15_pullback_reclaim_design_contract_20260731.json`

Contract commits:

- Markdown: `2d82bd7071a21864d41a7dfc3aa524d92080b131`
- JSON: `c9da755c5750b7e46a64993aaa7dd157c8e5c3cf`

Exactly eight machines:

- prior H1 range `R = 6 / 12`;
- H1 impulse body `B = 0.75 / 1.00 ATR`;
- M15 first-pullback deadline `W = 8 / 16 bars`.

## 4. Causal mechanism

- H1 is built only from exact M15 bars at minutes `00, 15, 30, 45`;
- incomplete or current-forming H1 is unavailable;
- a closed H1 range-expansion impulse arms the setup;
- a later M15 bar must pull back into the frozen 38.2%–61.8% impulse range zone;
- a later M15 bar must reclaim the near boundary and previous exact M15 high/low;
- entry is the next exact M15 open;
- exit is structural success, structural failure or fixed 32-M15-bar thesis expiry.

No return or price outcome is exported.

## 5. BCR16 implementation

Python:

`scripts/btc_ml_v1/BCR16_b5_h1_impulse_m15_reclaim_capability_audit/python/run_bcr16_b5_capability_audit.py`

Tests:

`tests/btc_ml_v1/test_bcr16_b5_capability_audit.py`

Readiness:

1. `docs/btc_ml_v1/BTC_BCR16_B5_OUTCOME_BLIND_CAPABILITY_IMPLEMENTATION_READY_20260731.md`
2. `configs/btc_ml_v1/btc_bcr16_b5_outcome_blind_capability_implementation_ready_20260731.json`

Commits:

- Python: `4325fce64eff5bbaa234bc3f401125a64f2250dc`
- tests: `007ef3620d2f3af9df3f2d03c9339fe53a5ba2c3`
- readiness Markdown: `cb39535dacacfed7b12215139baa63f86084c635`
- readiness JSON: `726805d593e1d71fb4a3662268bd8ddf9ba63447`
- local synthetic/exact-path tests: `6 passed`

## 6. Local run

Pull branch:

`feature/btc-fresh-forward-research`

Run:

`scripts\btc_ml_v1\BCR16_b5_h1_impulse_m15_reclaim_capability_audit\01_run_BCR16.bat`

Output:

`C:\Users\regen\AppData\Local\xauusd_signal_lab\btc_ml_v1\outputs\BCR16_b5_h1_impulse_m15_reclaim_capability_audit\LATEST`

After success, Explorer selects:

`99_UPLOAD_PACKAGE.zip`

Upload only that ZIP.

## 7. Frozen-input gate

- BTC M15 SHA256: `b8de00d117a119f9bf2f417b6228fe0ca0779c88f71a80b134bb9244d6768148`
- rows: `30,661`
- symbol: `BTCUSD#`
- append-only prefix allowed only on exact byte SHA match
- no alternate CSV, sorting, repair, nearest/next or interpolation

## 8. Capability gate

All eight machines are reported against the unchanged gate:

- at least 50 closed episodes;
- at least 20 closed LONG and 20 closed SHORT;
- at least six entry months;
- maximum month share at most 35%;
- p90 holding at most 384 bars;
- maximum holding at most 1,500 bars;
- at most one endpoint-open episode;
- state integrity;
- no fallback/interpolation.

No result-driven rescue follows.

## 9. Authorization boundary

Currently authorized:

- exact frozen-input BCR16 label-free run;
- upload and audit of its `99_UPLOAD_PACKAGE.zip`;
- report all eight machines without rescue.

Not authorized:

- B5 return, win/loss, PF, PnL, MFE or MAE;
- value evaluation;
- machine/side deletion or threshold rescue;
- portfolio, prospective start or shadow;
- Discord, MT5 order, live-ready or final signal;
- Collector/M7C/M8C/M9/M10 changes;
- GOLD/MOCHIPOYO writeback.

## 10. Current formal decision

`ACCEPT_BCR16_IMPLEMENTATION_READY_AWAIT_EXACT_FROZEN_INPUT_99_UPLOAD_PACKAGE_NO_OUTCOME_OPENED_NO_PROMOTION`
