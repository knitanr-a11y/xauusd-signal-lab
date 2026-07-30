# BTC BCR17 — B5 shared retrospective value-gate result

- repository: `knitanr-a11y/xauusd-signal-lab`
- branch: `feature/btc-fresh-forward-research`
- recorded: `2026-07-31T01:30:00+09:00`
- status: `BCR17_COMPLETE_ONE_PROMISING_ONE_HOLD_SIX_REJECT_NO_SUPPORTED`
- automatic candidate promotion: forbidden
- deployable candidates: `0`

## 1. Accepted package and deterministic audit

Received outer upload:

- file: `99_UPLOAD_PACKAGE(106).zip`
- outer SHA256: `7e157046a11f65c18a030cc1a18665d0de737f652b0e02ca32b260b7edb3b1b8`
- outer members: exact expected three
- outer ZIP CRC: passed

Accepted inner package:

- file: `BCR17_B5_SHARED_RETROSPECTIVE_VALUE_GATE_20260731.zip`
- inner SHA256: `dc8420a6edb104799919a51195cc03b7023377bca2c1d1eb75b0792164337ec7`
- `package_sha256.txt`: exact match
- deterministic run A/B SHA match: true
- inner ZIP CRC: passed
- manifest member SHA256 and byte counts: exact for all eight data/result files

## 2. Frozen source integrity

- BTC M15 rows: `30,661`
- BTC M15 frozen SHA256: `b8de00d117a119f9bf2f417b6228fe0ca0779c88f71a80b134bb9244d6768148`
- first time: `2025-09-13 08:00:00`
- last time: `2026-07-30 06:15:00`
- append-only source prefix rehydration: exact byte-SHA match
- accepted BCR16 package SHA256: `c469be9455bd5639de336684e0fdcaebf6a72dc6f0bae623acefa5e0cb506653`
- BCR16 closed episode rows: `844`
- all eight machines and both directions: reported
- missing exact entry/exit M15 rows: `0`
- nearest/next/interpolation/sorting/repair fallback: none

Independent audit recalculated all `844` trade fill prices and PnL values. C0/C2 entry/exit prices, machine net, PF and maximum drawdown matched the package within floating-point precision.

The exact monthly Wilcoxon signed-rank statistics and Holm adjustments were independently reproduced.

## 3. Frozen execution and cost contract

All eight machines used the same contract:

- symbol/bar: `BTCUSD#` BID M15
- spread price: CSV spread points × `0.01`
- LONG C0: entry BID open plus entry spread, exit BID open
- SHORT C0: entry BID open, exit BID open plus exit spread
- C0: observed spread only
- C2: C0 plus `25%` of contemporaneous spread adversely at each fill
- commission: `0`
- swap: not included
- same-server-date: `FULL_KNOWN_COST_NO_ROLLOVER`
- date-crossing: `PRE_SWAP_ONLY`
- result currency: USD per `1.00` lot

## 4. Complete machine result

| machine | trades | C0 WR | C0 PF | C0 net | C0 expectancy | C0 DD | C2 PF | C2 net | C2 expectancy | C2 DD | Holm C2 p | classification |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `R06_B075_W08` | 131 | 61.83% | 0.9347 | -2,519.63 | -19.23 | 13,042.93 | 0.8960 | -4,072.13 | -31.08 | 13,942.93 | 1.0 | REJECT |
| `R06_B075_W16` | 130 | 63.08% | 0.9978 | -80.64 | -0.62 | 10,583.63 | 0.9571 | -1,618.14 | -12.45 | 11,427.38 | 1.0 | REJECT |
| `R06_B100_W08` | 100 | 63.00% | 0.9465 | -1,636.68 | -16.37 | 9,853.33 | 0.9090 | -2,821.68 | -28.22 | 10,550.83 | 1.0 | REJECT |
| `R06_B100_W16` | 103 | 63.11% | 0.9286 | -2,312.29 | -22.45 | 9,704.33 | 0.8924 | -3,531.04 | -34.28 | 10,390.58 | 1.0 | REJECT |
| `R12_B075_W08` | 105 | 61.90% | 0.9528 | -1,510.50 | -14.39 | 10,724.40 | 0.9151 | -2,755.50 | -26.24 | 11,376.90 | 1.0 | REJECT |
| `R12_B075_W16` | 107 | 64.49% | 1.0495 | +1,509.24 | +14.11 | 9,128.00 | 1.0079 | +245.49 | +2.29 | 9,803.00 | 1.0 | PROMISING |
| `R12_B100_W08` | 82 | 62.20% | 0.9807 | -477.65 | -5.83 | 7,299.40 | 0.9424 | -1,448.90 | -17.67 | 7,839.40 | 1.0 | REJECT |
| `R12_B100_W16` | 86 | 63.95% | 1.0384 | +961.99 | +11.19 | 6,635.50 | 0.9979 | -54.26 | -0.63 | 7,186.75 | 1.0 | HOLD / COST-SENSITIVE |

Classification totals:

- `VALUE_SUPPORTED_RETROSPECTIVE`: `0`
- `VALUE_PROMISING_RETROSPECTIVE`: `1`
- `HOLD_COST_SENSITIVE`: `1`
- `REJECT_RETROSPECTIVE_VALUE`: `6`

No machine is automatically promoted.

## 5. Promising research survivor

The only preregistered `VALUE_PROMISING_RETROSPECTIVE` machine is:

`TRACK_B_B5_R12_B075_W16_H1_IMPULSE_M15_RECLAIM`

Parameters:

- prior H1 range: `12`
- minimum H1 impulse body: `0.75 ATR`
- first M15 pullback deadline: `16` bars
- fixed thesis expiry: `32` M15 bars

Overall:

- trades: `107`
- C0 wins/losses: `69 / 38`
- C0 PF/net/expectancy: `1.0495 / +1,509.24 / +14.11`
- C2 PF/net/expectancy: `1.0079 / +245.49 / +2.29`
- C2 maximum drawdown: `9,803.00`
- C2 exact monthly raw p: `0.55078125`
- C2 Holm-adjusted p: `1.0`
- positive C2 entry months: `5 / 11`
- negative C2 entry months: `6 / 11`

This is only a weak positive retrospective result. Its C2 edge is very small relative to drawdown and is not supported by familywise-corrected monthly evidence.

## 6. Direction asymmetry

For `R12_B075_W16`:

### LONG

- trades: `54`
- C0 PF/net: `0.9322 / -1,017.40`
- C2 PF/net: `0.8915 / -1,654.90`

### SHORT

- trades: `53`
- C0 PF/net: `1.1629 / +2,526.64`
- C2 PF/net: `1.1210 / +1,900.39`

The total positive result is carried by SHORT. This does not authorize deleting LONG, creating a SHORT-only candidate, or retuning the direction rules. Both directions remain part of the frozen machine unless a separately preregistered future trial is explicitly authorized.

## 7. Same-server-date versus rollover-exposed phenotype

For `R12_B075_W16`:

### Same-server-date — full known cost

- trades: `84`
- C0 PF/net: `1.4636 / +8,967.19`
- C2 PF/net: `1.4062 / +7,965.94`

### Rollover-exposed — pre-swap only

- trades: `23`
- C0 PF/net: `0.3325 / -7,457.95`
- C2 PF/net: `0.3196 / -7,720.45`

The same pattern appeared across all eight machines: the same-server-date subset was positive and the date-crossing subset was strongly negative.

This is a diagnostic phenotype, not an accepted entry filter. Same-server-date membership depends on the future exit date. Swap was not included, so rollover losses cannot be attributed solely to financing. No retrospective same-day filter, forced-flat rule, maximum-holding change or side deletion is accepted from this result.

## 8. Exit-path diagnostic

For `R12_B075_W16` under C2:

- structural success: `66` trades, net `+30,012.79`, PF `401.44`
- structural failure: `21` trades, net `-22,297.25`, PF `0`
- 32-bar expiry: `20` trades, net `-7,470.05`, PF `0.1298`

These categories follow the already frozen state-machine exit definitions. They are diagnostic only and do not authorize changing exits on the same retrospective sample.

## 9. Interpretation

BCR17 provides the first positive value indication in the current Track B redesign, but not a supported or deployable result.

Positive evidence:

- one preregistered machine remains positive under C2;
- 107 closed trades across 11 entry months;
- balanced original LONG/SHORT inventory;
- deterministic and exact source reproduction.

Material weaknesses:

- C2 PF only `1.0079`;
- C2 net only `+245.49` versus `9,803.00` maximum drawdown;
- five positive months and six negative months;
- Holm-adjusted p-value `1.0`;
- aggregate edge is carried by SHORT while LONG is negative;
- date-crossing episodes are strongly negative and swap remains unresolved.

Therefore:

- candidate-level traction: `MODEST_FIRST_POSITIVE_SIGNAL_NOT_ROBUST`
- supported retrospective machine: `0`
- deployable candidate: `0`
- portfolio/shadow/live authorization: none

## 10. Formal decision and next boundary

Formal decision:

`ACCEPT_BCR17_DETERMINISTIC_VALUE_RESULT_FREEZE_R12_B075_W16_AS_PROMISING_RESEARCH_SURVIVOR_R12_B100_W16_AS_COST_SENSITIVE_HOLD_NO_PROMOTION`

Recommended next stage, requiring new explicit user authorization:

`BCR18_B5_PROMISING_SURVIVOR_PROSPECTIVE_PREREGISTRATION`

A BCR18 contract must preserve:

- exact `R12_B075_W16` machine;
- both LONG and SHORT;
- no threshold or exit change;
- no retrospective same-day or rollover filter;
- fixed future start after contract freeze;
- the BCR17 C0/C2 execution-cost contract;
- no automatic promotion;
- no Discord or MT5 order;
- no GOLD/MOCHIPOYO runtime changes.

Until explicit BCR18 authorization:

- no prospective start or shadow;
- no candidate promotion;
- no machine or direction deletion;
- no rollover-flat or maximum-holding rescue;
- no portfolio construction;
- no Discord, MT5 order, live-ready or final signal;
- no Collector/M7C/M8C/M9/M10 changes;
- no GOLD/MOCHIPOYO writeback.
