# NEXT CHAT HANDOFF — BTC BCR17 implementation ready, frozen-input local value run pending

- repository: `knitanr-a11y/xauusd-signal-lab`
- authoritative branch: `feature/btc-fresh-forward-research`
- verified at: `2026-07-31T00:45:00+09:00`
- status: `BTC_REDESIGN_BCR17_IMPLEMENTATION_READY_FROZEN_INPUT_LOCAL_RUN_PENDING_VALUE_ACCESS_AUTHORIZED_NO_RESULT_YET`
- current stage: `BCR17_B5_SHARED_RETROSPECTIVE_VALUE_GATE`
- actual value result: pending
- automatic promotion: forbidden

## 1. Current formal decision

`ACCEPT_BCR17_CONTRACT_AND_IMPLEMENTATION_READY_AWAIT_USER_LOCAL_99_UPLOAD_PACKAGE_NO_AUTOMATIC_PROMOTION`

The user explicitly authorized BCR17. The shared execution/cost, multiple-testing and classification contract was frozen before the actual B5 value replay. The evaluator and standard LocalAppData BAT are ready. No actual B5 return, PF or PnL result has been produced yet.

## 2. BCR16 accepted source

B5 family:

`B5_CAUSAL_H1_IMPULSE_M15_PULLBACK_RECLAIM`

BCR16 accepted result:

- capability pass: `8 / 8`;
- closed episode rows: `844`;
- endpoint-open: `0`;
- accepted inner package SHA256:
  `c469be9455bd5639de336684e0fdcaebf6a72dc6f0bae623acefa5e0cb506653`;
- B5 value fields before BCR17: unopened;
- deployable candidates: `0`.

BCR13/B3 remains closed with `0 / 8` capability survivors and no rescue.

## 3. BCR17 frozen contract

Authority:

1. `docs/btc_ml_v1/BTC_BCR17_B5_SHARED_RETROSPECTIVE_VALUE_GATE_CONTRACT_20260731.md`
2. `configs/btc_ml_v1/btc_bcr17_b5_shared_retrospective_value_gate_contract_20260731.json`

Contract commits:

- Markdown: `a5f8c3261f9c1b86f5b80ff30fc0bde49ac91b92`
- JSON: `ca17ea0f82b6f58d4f20352e578354234412cb11`

Common execution/cost:

- BTCUSD# BID M15;
- spread price = CSV spread points × `0.01`;
- commission `0`;
- swap not included;
- C0 observed spread only;
- C2 adds `25%` of contemporaneous spread adversely on each fill;
- same-server-date = full-known-cost/no-rollover;
- date-crossing = `PRE_SWAP_ONLY`.

## 4. Frozen classification

- `VALUE_SUPPORTED_RETROSPECTIVE`:
  C0 and C2 net positive/PF greater than 1, plus C2 Holm-adjusted monthly one-sided p-value at most `0.05`.
- `VALUE_PROMISING_RETROSPECTIVE`:
  C0 and C2 positive/PF greater than 1, but C2 Holm p-value above `0.05`.
- `HOLD_COST_SENSITIVE`:
  C0 positive/PF greater than 1 but C2 does not remain positive.
- `REJECT_RETROSPECTIVE_VALUE`:
  C0 not positive or PF not greater than 1.

Classification is not automatic promotion.

## 5. BCR17 implementation

Python:

`scripts/btc_ml_v1/BCR17_b5_shared_retrospective_value_gate/python/run_bcr17_b5_shared_value_gate.py`

Tests:

`tests/btc_ml_v1/test_bcr17_b5_shared_value_gate.py`

Readiness:

1. `docs/btc_ml_v1/BTC_BCR17_B5_SHARED_RETROSPECTIVE_VALUE_GATE_IMPLEMENTATION_READY_20260731.md`
2. `configs/btc_ml_v1/btc_bcr17_b5_shared_retrospective_value_gate_implementation_ready_20260731.json`

Commits:

- Python: `ac77a39188c946199c2fcbee9184822afbd36310`
- tests: `1cc4b614df1b8577aeb93be1f679fa52ccd7f025`
- README: `aba0cd8daeff774133b7730ef145e3f2b34afec2`
- runner BAT: `672374e7b8167c2e0d6f000e5b78ed63d95c077e`
- output opener BAT: `e540e95491f6c677062641936ef295cc25335de3`
- readiness Markdown: `a150a6560cf6e81cad8c1b67a59c18702ab081ea`
- readiness JSON: `269ab681f3da929b0e6b662a9444a90144d5915b`
- local tests: `6 passed`.

## 6. Hard gates

The evaluator requires:

- frozen BTC M15 SHA:
  `b8de00d117a119f9bf2f417b6228fe0ca0779c88f71a80b134bb9244d6768148`;
- rows: `30,661`;
- accepted BCR16 inner package exact SHA;
- all eight machines;
- BCR16 episode-count parity;
- closed episodes only;
- exact entry and exit M15 opens;
- no nearest/next/interpolation/sorting/repair fallback.

## 7. Mandatory reporting

Every B5 machine and both directions are reported under:

- C0 and C2;
- PF, net, expectancy, win rate and drawdown;
- trade-level entry/exit prices and PnL;
- MFE/MAE;
- LONG/SHORT;
- monthly results;
- same-server-date and rollover-exposed subsets;
- exit-reason subsets;
- exact monthly Wilcoxon;
- Holm adjustment across all eight machines.

MFE/MAE and subsets are diagnostic only. Result-driven machine deletion, side deletion, threshold rescue and exit rescue are forbidden.

## 8. User action now

Pull:

`feature/btc-fresh-forward-research`

Run:

`scripts\btc_ml_v1\BCR17_b5_shared_retrospective_value_gate\01_run_BCR17.bat`

Output:

`C:\Users\regen\AppData\Local\xauusd_signal_lab\btc_ml_v1\outputs\BCR17_b5_shared_retrospective_value_gate\LATEST`

After success, Explorer selects:

`99_UPLOAD_PACKAGE.zip`

Upload only that selected ZIP.

If the BAT fails, provide the complete console error. Do not substitute another CSV or BCR16 ledger and do not change the SHA, row count, machine inventory or cost contract.

## 9. Authorization boundary

Currently authorized:

- exact frozen-input BCR17 value replay;
- audit of the selected `99_UPLOAD_PACKAGE.zip`;
- reporting of all eight machines and both directions without rescue.

Not authorized:

- automatic candidate promotion;
- post-result machine or side deletion;
- portfolio construction;
- prospective start;
- shadow;
- Discord;
- MT5 orders;
- live-ready;
- final signal;
- Collector/M7C/M8C/M9/M10 changes;
- GOLD/MOCHIPOYO writeback.

Any stage after the BCR17 result requires another explicit user authorization.
