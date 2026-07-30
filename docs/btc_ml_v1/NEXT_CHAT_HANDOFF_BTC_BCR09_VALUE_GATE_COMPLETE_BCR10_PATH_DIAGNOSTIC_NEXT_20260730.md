# NEXT CHAT HANDOFF — BTC BCR09 value gate complete, BCR10 path diagnostic next

- repository: `knitanr-a11y/xauusd-signal-lab`
- authoritative branch: `feature/btc-fresh-forward-research`
- recorded: `2026-07-30T20:00:00+09:00`
- status: `BTC_REDESIGN_BCR09_COMPLETE_NO_SUPPORTED_BASE_MACHINE_BCR10_DIAGNOSTIC_NEXT`

## 1. Mandatory startup boundary

Read only the files listed by `START_HERE_BTC_CANDIDATE_RESEARCH_NEXT_CHAT.md`, in the stated order and with the branch explicitly set to `feature/btc-fresh-forward-research`.

Do not begin with `AGENTS.md`, `main`, default branch, repo-wide search, an old handoff, GOLD V3, GOLD_ML_V1, old GOLD, DISC8, Stage41, FF05 recovery V3–V11, or broad MOCHIPOYO exploration.

Collector, M7C, M8C, M9 and M10 remain running and unchanged. No BTC result is written back to GOLD/MOCHIPOYO.

## 2. System objective

Build a BTC system with:

- Track A: actual M7C/Collector source alerts used as read-only teacher evidence;
- Track B: genuinely independent mechanisms;
- strict separation of fidelity, value, risk overlays, shadow and live;
- causal/backtest/live parity, drift monitoring and fail-closed stopping.

A profitable-looking retrospective slice is not sufficient for promotion.

## 3. Frozen data and market contract

BTC M15 frozen input:

- exact origin path: `C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files\btcusdsharp_m15.csv`
- SHA256: `b8de00d117a119f9bf2f417b6228fe0ca0779c88f71a80b134bb9244d6768148`
- rows: `30,661`

BCR08 package:

- SHA256: `2b5df4bcdf0f2c07c0d246a3cfe057f05ef4751f7ab3e3c71e8f993cd24cbbf7`
- exact symbol: `BTCUSD#`
- symbol path: `Cryptocurrencies\KIWAMI\BTCUSD#`
- BID bars, digits `2`, point/tick size `0.01`, contract size `1.0`
- spread field is points: `2250/3000` -> USD `22.50/30.00` price per one-lot BTC contract
- KIWAMI commission: frozen at zero by separate official account contract
- swap/history financing: unresolved; rollover-exposed results are pre-swap only

The live CSV had grown after the snapshot and did not replace the frozen input.

## 4. Frozen machines entering BCR09

### Track A

1. `TRACK_A_F1_COVERAGE_FIRST`
2. `TRACK_A_F2_HIGH_COVERAGE_INTERMEDIATE`
3. `TRACK_A_F3_STATE_FIDELITY`
4. `TRACK_A_F4_MINIMUM_EXTRA_PARETO`

All value replays start IDLE and never read source state.

### Track B

5. `TRACK_B_B1_E0_EMA30_CROSS`
6. `TRACK_B_B1_E1_STACK_BREAK`
7. `TRACK_B_B4_E0_EMA20_TOUCH`
8. `TRACK_B_B4_E1_EXTENSION_CONTRACT`

B2 compression remains blocked for insufficient density. Do not rescue its threshold.

## 5. BCR09 execution/cost contract

- LONG entry: BID open + contemporaneous spread; exit: BID open.
- SHORT entry: BID open; exit: BID open + contemporaneous spread.
- commission: zero.
- C0: observed spread only.
- C2: observed spread plus 25% of spread slippage on each fill.
- exact boundary only; no nearest/next/interpolation.
- same execution and cost assumptions for all machines.
- results reported in USD profit currency per 1.00 lot and 0.01 lot; no invented historical USDJPY conversion.

## 6. BCR09 pre-acceptance incident

The first local Track A replay used an incorrect warm-up and did not reproduce BCR06 outcome-blind reference counts. It is invalid audit history and must never be used.

Corrected rule:

- first 500 physical rows reserved as common warm-up;
- decisions begin at row index 500 or later;
- exact previous boundary and contiguous 50-bar segment required;
- active state persists through unavailable rows.

This reproduces all BCR06 Track A entry counts and the common `27,861` eligible rows exactly. The correction was selected without PnL.

## 7. Accepted BCR09 result

Accepted deterministic package:

- `BCR09_SHARED_RETROSPECTIVE_VALUE_GATE_20260730.zip`
- SHA256: `92b989ce7b0b76acab0bb6205c1d8e5cfdd9d2f86c42e74781e38177c79c45fa`
- two independent local runs: same SHA
- tests: `4 passed`

Totals:

- closed trades: `8,474`
- endpoint-open episodes: `3`
- integrity failures: `0`
- supported: `0`
- promising: `0`
- hold/cost-sensitive: `1`
- rejected: `7`

C0 base results:

| machine | PF | net USD/1 lot | decision |
|---|---:|---:|---|
| Track A F1 | 0.8881 | -40,703.30 | REJECT |
| Track A F2 | 0.9078 | -26,262.73 | REJECT |
| Track A F3 | 0.9319 | -12,490.33 | REJECT |
| Track A F4 | 0.9070 | -16,766.03 | REJECT |
| Track B B1 E0 | 0.7729 | -62,395.43 | REJECT |
| Track B B1 E1 | 0.9178 | -15,978.65 | REJECT |
| Track B B4 E0 | 1.0006 | +108.97 | HOLD / COST-SENSITIVE |
| Track B B4 E1 | 0.9988 | -201.97 | REJECT |

Under C2, every machine is negative. B4 E0 falls to PF `0.9497`, net `-8,951.03`.

Monthly one-sided Wilcoxon/Holm evidence across 11 active months supports no machine; all adjusted p-values are `1.0`.

No machine is promoted. No portfolio or shadow exists.

## 8. Important loss phenotype

Same-server-date C0 subsets:

- Track A F1–F4 PF: `1.5130`, `1.6233`, `1.6775`, `1.8920`
- B4 E0/E1 PF: `1.4596`, `1.3695`
- B1 E0/E1 PF: `0.4399`, `0.0397`

This is not a validated same-day filter because the classification uses the future exit date. It is an outcome-exposed holding/path phenotype only.

Swap was not included, so rollover-exposed losses must not be attributed solely to swap. Price-path failure, long holding, time exposure and financing remain separate hypotheses.

B1 is removed from the current rescue path because it fails even in same-server-date trades.

## 9. Current next stage

`BCR10_HOLDING_ROLLOVER_AND_PATH_PHENOTYPE_DIAGNOSTIC`

Contract:

`docs/btc_ml_v1/BTC_BCR10_HOLDING_ROLLOVER_AND_PATH_PHENOTYPE_DIAGNOSTIC_CONTRACT_20260730.md`

BCR10 includes Track A F1–F4 and B4 E0/E1 only. It uses fixed holding bins, date-crossing bins, four-hour server-time bins and direction-specific MFE/MAE/giveback diagnostics.

BCR10 must not evaluate a time stop, forced-flat overlay, TP/SL or filter PnL. It diagnoses only.

After BCR10, a finite new overlay family may contain only:

- no overlay;
- max holding 16, 32 or 64 M15 bars;
- server-day flat at exact 23:45 server open;
- one preregistered combination.

Any such overlay is outcome-exposed and requires a new prospective shadow family. Retrospective improvement cannot promote it.

## 10. Current prohibitions

- do not rescue or retune the eight base machines on BCR09 outcomes;
- do not lower B2 thresholds;
- do not add ATR, hour, weekday, direction or regime filters;
- do not perform TP/SL, trailing-stop or time-stop search;
- do not create a portfolio;
- do not set a prospective start or shadow before the overlay family and monitor contract are frozen;
- do not modify/stop/restart Collector, M7C, M8C, M9 or M10;
- no Discord, MT5 order, live-ready or automatic promotion.

## 11. User action

No BAT or upload is currently required. Implement and audit BCR10 locally from the accepted frozen inputs, then update every handoff layer in the same work.