# BTC BCR16 — B5 outcome-blind capability result

- repository: `knitanr-a11y/xauusd-signal-lab`
- branch: `feature/btc-fresh-forward-research`
- recorded: `2026-07-31T00:33:00+09:00`
- status: `BCR16_COMPLETE_EIGHT_OF_EIGHT_B5_MACHINES_PASS_CAPABILITY`
- value access: not opened
- candidate promotion: forbidden

## 1. Accepted package

- received outer upload SHA256: `2504c83c0e1cd6b9c336420cb8435f4c599493c076a5bed0028f3717e834229f`
- accepted inner package: `BCR16_B5_OUTCOME_BLIND_CAPABILITY_AUDIT_20260731.zip`
- accepted inner package SHA256: `c469be9455bd5639de336684e0fdcaebf6a72dc6f0bae623acefa5e0cb506653`
- deterministic run A/B match: true
- outer ZIP CRC: passed
- inner ZIP CRC: passed
- manifest hashes and byte counts: exact

## 2. Frozen input

- BTC M15 frozen SHA256: `b8de00d117a119f9bf2f417b6228fe0ca0779c88f71a80b134bb9244d6768148`
- rows: `30,661`
- first time: `2025-09-13 08:00:00`
- last time: `2026-07-30 06:15:00`
- complete causal H1 bars built: `7,630`
- append-only source SHA observed at run: `9cb2db4f2d4ffaeaa4bdbedb9a0db620bde30397e093f2c0694280c6032bdd7f`
- frozen prefix rehydration: exact byte-SHA match
- fallback, sorting, repair, nearest/next and interpolation: none

## 3. Complete gate result

All eight frozen B5 machines passed every unchanged BCR07 capability check.

- capability pass: `8`
- capability fail: `0`
- all eight reported: yes
- endpoint-open episodes: `0` in every machine
- state integrity: passed in every machine
- simultaneous conflicts: `0`
- exact-entry-missing events: `0`
- fallback/interpolation used: no

The unchanged gate required:

- at least `50` closed episodes total;
- at least `20` closed LONG and `20` closed SHORT;
- at least `6` entry months;
- maximum month share at most `35%`;
- p90 holding at most `384` M15 bars;
- maximum holding at most `1,500` M15 bars;
- at most one endpoint-open episode;
- state integrity;
- no fallback/interpolation.

## 4. Machine results

| machine | H1 impulses | entries / closed | LONG / SHORT | months | max month share | p50 / p90 / max holding | occupancy | pass |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| `R06_B075_W08` | 421 | 131 / 131 | 67 / 64 | 11 | 11.45% | 9 / 32 / 33 | 5.63% | PASS |
| `R06_B075_W16` | 398 | 130 / 130 | 64 / 66 | 11 | 11.54% | 10 / 32 / 33 | 5.68% | PASS |
| `R06_B100_W08` | 332 | 100 / 100 | 50 / 50 | 11 | 13.00% | 12 / 32 / 32 | 4.67% | PASS |
| `R06_B100_W16` | 316 | 103 / 103 | 50 / 53 | 11 | 11.65% | 12 / 32 / 32 | 4.82% | PASS |
| `R12_B075_W08` | 320 | 105 / 105 | 55 / 50 | 11 | 11.43% | 9 / 32 / 32 | 4.71% | PASS |
| `R12_B075_W16` | 305 | 107 / 107 | 54 / 53 | 11 | 11.21% | 10 / 32 / 32 | 4.83% | PASS |
| `R12_B100_W08` | 264 | 82 / 82 | 42 / 40 | 11 | 12.20% | 11.5 / 32 / 32 | 3.87% | PASS |
| `R12_B100_W16` | 253 | 86 / 86 | 42 / 44 | 11 | 10.47% | 11 / 32 / 32 | 4.02% | PASS |

Observed ranges across the eight machines:

- H1 impulses: `253–421`;
- pullbacks: `166–281`;
- entries and closed episodes: `82–131`;
- closed LONG: `42–67`;
- closed SHORT: `40–66`;
- distinct entry months: `11` in every machine;
- maximum month share: `10.47%–13.00%`;
- median holding: `9–12` bars;
- p90 holding: `32` bars in every machine;
- maximum holding: `32–33` bars;
- occupancy: `3.87%–5.68%`.

Two machines had one active decision unavailable at a clock gap. Their one affected episode exited at the next exact available boundary and therefore recorded `33` theoretical bars rather than `32`. No synthetic boundary or fallback was used.

## 5. Label-free structural path categories

The complete state machine recorded structural exit categories needed to close episodes:

- structural-success exits: `49–79` per machine;
- structural-failure exits: `15–28` per machine;
- 32-bar thesis-expiry exits: `18–24` per machine.

These categories are not trading wins or losses. They do not include entry/exit prices, spread, commission, slippage, return, PF, PnL, MFE or MAE. They must not be interpreted as profitability.

## 6. Outcome-isolation audit

The package contains no columns for:

- entry price;
- exit price;
- return;
- win/loss;
- PF;
- PnL;
- MFE;
- MAE;
- future value result.

The package explicitly records:

- `outcome_fields_opened = false`;
- `value_evaluation_performed = false`;
- `candidate_promoted = false`;
- `portfolio_selected = false`;
- `prospective_start_set = false`;
- `shadow_started = false`;
- `discord_sent = false`;
- `mt5_order_sent = false`.

## 7. Interpretation

This is the first new Track B family in the current redesign to demonstrate adequate label-free capability across every frozen machine.

It establishes that B5 has:

- sufficient historical event density;
- balanced LONG and SHORT representation;
- broad monthly coverage;
- controlled, finite holding duration;
- low occupancy;
- complete deterministic state-machine behavior.

It does not establish positive expectancy or deployability.

## 8. Decision and next boundary

Current decision:

`ACCEPT_BCR16_DETERMINISTIC_LABEL_FREE_RESULT_FREEZE_EIGHT_B5_CAPABILITY_SURVIVORS_AWAIT_EXPLICIT_BCR17_VALUE_GATE_AUTHORIZATION`

B5 capability survivors: all eight frozen machines.

BCR17, if explicitly authorized, may perform one shared retrospective value gate using the already frozen BCR08 execution and cost provenance, with C0 and C2, all eight trials reported, no post-result machine or side deletion, and appropriate multiple-testing control.

Until that authorization:

- no B5 return, win/loss, PF, PnL, MFE or MAE;
- no candidate promotion;
- no portfolio construction;
- no prospective boundary or shadow;
- no Discord, MT5 order, live-ready or final signal;
- no Collector/M7C/M8C/M9/M10 changes;
- no GOLD/MOCHIPOYO writeback.
