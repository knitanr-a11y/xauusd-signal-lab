# BTC BCR17 — B5 shared retrospective value-gate implementation ready

- repository: `knitanr-a11y/xauusd-signal-lab`
- branch: `feature/btc-fresh-forward-research`
- recorded: `2026-07-31T00:45:00+09:00`
- status: `IMPLEMENTATION_AND_LOCAL_TESTS_READY_FROZEN_INPUT_LOCAL_RUN_PENDING`
- actual value result: pending
- automatic promotion: forbidden

## 1. Frozen contract

- `docs/btc_ml_v1/BTC_BCR17_B5_SHARED_RETROSPECTIVE_VALUE_GATE_CONTRACT_20260731.md`
- `configs/btc_ml_v1/btc_bcr17_b5_shared_retrospective_value_gate_contract_20260731.json`

The execution, cost, multiple-testing and classification rules were frozen before the actual B5 value replay.

## 2. Implementation

- Python:
  `scripts/btc_ml_v1/BCR17_b5_shared_retrospective_value_gate/python/run_bcr17_b5_shared_value_gate.py`
- tests:
  `tests/btc_ml_v1/test_bcr17_b5_shared_value_gate.py`
- BAT:
  `scripts/btc_ml_v1/BCR17_b5_shared_retrospective_value_gate/01_run_BCR17.bat`
- output opener:
  `scripts/btc_ml_v1/BCR17_b5_shared_retrospective_value_gate/02_open_latest_results.bat`

## 3. Hard gates

The implementation verifies:

- exact frozen BTC M15 SHA and row count;
- exact accepted BCR16 inner package SHA;
- exact eight-machine inventory;
- all BCR16 source machines passed capability;
- all BCR16 episodes are closed;
- BCR16 episode counts match machine metrics;
- exact entry and exit M15 timestamps;
- no duplicate machine entry;
- no nearest/next/interpolation/sorting fallback.

## 4. Value outputs

For every frozen machine, the package reports:

- C0 and C2 PF, net, expectancy, win rate and drawdown;
- complete trade-level entry/exit pricing;
- C0 and C2 MFE/MAE;
- LONG and SHORT results;
- entry-month results;
- same-server-date and rollover-exposed results;
- exit-reason results;
- exact monthly Wilcoxon raw p-values;
- Holm-adjusted p-values;
- preregistered classification.

MFE/MAE, direction subsets, rollover subsets and exit-reason subsets are diagnostic and cannot be used to silently delete trials.

## 5. Local validation

Six tests passed:

1. exact LONG/SHORT C0 and C2 fill arithmetic;
2. MFE/MAE path excludes exit-bar future high/low;
3. exact Wilcoxon and Holm adjustment;
4. frozen classification ladder;
5. BCR16 package SHA hard gate;
6. deterministic ZIP output.

The actual 30,661-row BCR17 result has not been executed in this environment because the frozen source CSV is on the user's Windows machine.

## 6. Standard output workflow

Run:

`scripts\btc_ml_v1\BCR17_b5_shared_retrospective_value_gate\01_run_BCR17.bat`

Output:

`C:\Users\regen\AppData\Local\xauusd_signal_lab\btc_ml_v1\outputs\BCR17_b5_shared_retrospective_value_gate\LATEST`

After success, Explorer selects:

`99_UPLOAD_PACKAGE.zip`

Upload only that selected ZIP.

## 7. Current boundary

Until the uploaded result is audited:

- no automatic promotion;
- no portfolio;
- no prospective start or shadow;
- no Discord or MT5 order;
- no Collector/M7C/M8C/M9/M10 change;
- no GOLD/MOCHIPOYO writeback.
