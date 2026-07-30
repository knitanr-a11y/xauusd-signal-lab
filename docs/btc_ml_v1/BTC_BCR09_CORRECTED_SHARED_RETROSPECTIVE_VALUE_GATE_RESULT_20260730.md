# BTC BCR09 — corrected shared retrospective value-gate result

- repository: `knitanr-a11y/xauusd-signal-lab`
- branch: `feature/btc-fresh-forward-research`
- recorded: `2026-07-30T19:50:00+09:00`
- status: `READY_CORRECTED_RETROSPECTIVE_VALUE_RESULT_NO_SUPPORTED_MACHINE`
- prospective evidence: no
- portfolio selected: no
- shadow authorized: no

## 1. Integrity and correction history

BCR09 opened value outcomes only after the shared execution/cost contract was committed.

The first local replay was invalidated because its Track A warm-up did not reproduce the frozen BCR06 outcome-blind reference counts. That run is audit history only.

The corrected replay used:

- first `500` physical M15 rows as common warm-up;
- exact 15-minute continuity over the preceding 50 bars;
- no gap interpolation or nearest/next fallback;
- state persistence through feature-unavailable rows.

Corrected Track A entry-count parity is exact for all eight direction/member counts. The corrected evaluator also reproduced all BCR07 Track B episode counts exactly.

Integrity totals:

- machines: `8`
- closed trade rows: `8,474`
- endpoint-open episodes: `3`
- missing exact entry/exit rows: `0`
- current-bar high/low/close used for signals: no
- commission: `0`
- swap included: no
- rollover-exposed episodes: labeled `PRE_SWAP_ONLY`

## 2. Accepted package and reproduction

- result package: `BCR09_SHARED_RETROSPECTIVE_VALUE_GATE_20260730.zip`
- accepted SHA256: `92b989ce7b0b76acab0bb6205c1d8e5cfdd9d2f86c42e74781e38177c79c45fa`
- deterministic second-run SHA match: true
- evaluator script SHA256: `997a93537f73bfaf6d587c2079d0d0186c34209ae2b5ae99553a276f890bf474`
- unit tests: `4 passed`

The earlier local package SHA `19b8e209...` is not the accepted deterministic artifact. Its aggregate result tables matched, but formatting/metadata differed. The GitHub reproducer output above is the authority.

## 3. Shared execution and cost basis

All eight machines used identical assumptions:

- BID-based M15 open;
- LONG enters at BID open plus observed spread and exits at BID open;
- SHORT enters at BID open and exits at BID open plus observed spread;
- historical spread field interpreted as points and multiplied by `0.01`;
- no separate commission;
- C0 observed spread only;
- C2 adds `25%` of contemporaneous spread as slippage on each fill.

Results are USD profit-currency values per `1.00` lot. They are not converted into historical JPY account-currency PnL.

## 4. C0 base results

| machine | closed | PF | net USD/1 lot | expectancy | classification |
|---|---:|---:|---:|---:|---|
| `TRACK_A_F1_COVERAGE_FIRST` | 1,561 | 0.8881 | -40,703.30 | -26.08 | REJECT |
| `TRACK_A_F2_HIGH_COVERAGE_INTERMEDIATE` | 1,229 | 0.9078 | -26,262.73 | -21.37 | REJECT |
| `TRACK_A_F3_STATE_FIDELITY` | 812 | 0.9319 | -12,490.33 | -15.38 | REJECT |
| `TRACK_A_F4_MINIMUM_EXTRA_PARETO` | 768 | 0.9070 | -16,766.03 | -21.83 | REJECT |
| `TRACK_B_B1_E0_EMA30_CROSS` | 1,980 | 0.7729 | -62,395.43 | -31.51 | REJECT |
| `TRACK_B_B1_E1_STACK_BREAK` | 519 | 0.9178 | -15,978.65 | -30.79 | REJECT |
| `TRACK_B_B4_E0_EMA20_TOUCH` | 773 | 1.0006 | +108.97 | +0.14 | HOLD / COST-SENSITIVE |
| `TRACK_B_B4_E1_EXTENSION_CONTRACT` | 832 | 0.9988 | -201.97 | -0.24 | REJECT |

Classification totals:

- `VALUE_SUPPORTED_RETROSPECTIVE`: `0`
- `VALUE_PROMISING_RETROSPECTIVE`: `0`
- `HOLD_INSUFFICIENT_OR_COST_SENSITIVE`: `1`
- `REJECT_RETROSPECTIVE_VALUE`: `7`

No base machine is promoted.

## 5. Fixed C2 stress

Under 25%-of-spread slippage on each fill:

| machine | C2 PF | C2 net USD/1 lot |
|---|---:|---:|
| Track A F1 | 0.8407 | -58,905.80 |
| Track A F2 | 0.8599 | -40,598.98 |
| Track A F3 | 0.8821 | -21,996.58 |
| Track A F4 | 0.8595 | -25,747.28 |
| Track B B1 E0 | 0.7066 | -85,568.56 |
| Track B B1 E1 | 0.8890 | -22,051.78 |
| Track B B4 E0 | 0.9497 | -8,951.03 |
| Track B B4 E1 | 0.9404 | -9,955.72 |

The only C0-positive machine, B4 E0, becomes clearly negative under the preregistered C2 stress. It is therefore HOLD, not supported or promising.

## 6. Same-server-date versus rollover-exposed phenotype

The full-known-cost same-server-date subset showed a sharp split.

### Track A same-server-date C0

- F1: `1,300` trades, PF `1.5130`, net `+101,272.56`
- F2: `1,023`, PF `1.6233`, net `+91,037.43`
- F3: `660`, PF `1.6775`, net `+62,314.04`
- F4: `611`, PF `1.8920`, net `+68,871.64`

### Track B same-server-date C0

- B1 E0: PF `0.4399`, net `-142,958.64`
- B1 E1: PF `0.0397`, net `-138,348.04`
- B4 E0: `675` trades, PF `1.4596`, net `+51,177.87`
- B4 E1: `749`, PF `1.3695`, net `+41,739.98`

This does **not** validate a same-day filter. Same-server-date membership depends on the future exit time and is therefore not an entry-time predicate. It reveals a holding-path phenotype that requires a separately preregistered causal risk/exit study.

Swap was not included. Consequently, rollover-exposed losses cannot be attributed solely to financing. They may reflect price-path failure, excessive holding, adverse time-of-day exposure, financing, or several factors together.

B1 fails even in the same-server-date subset and is not a rescue priority under its current mechanism definitions.

## 7. Time stability

All machines had 11 active calendar months. The one-sided monthly Wilcoxon tests, Holm-adjusted across eight machines, produced adjusted p-values of `1.0` under both C0 and C2.

There is no familywise-corrected monthly sign evidence supporting any machine.

## 8. Decision

1. No Track A or Track B base machine passes the retrospective value gate.
2. B1 current mechanisms are rejected from the active rescue path.
3. B4 E0 remains HOLD solely because C0 is marginally positive; it is highly cost-sensitive.
4. Track A and B4 show a strong same-server-date versus rollover-exposed phenotype, but no filter or forced-flat rule is accepted from this result.
5. The next stage is an outcome-exposed **diagnostic** stage, not promotion: freeze BCR10 loss/holding phenotype bins and causal candidate-overlay rules before further analysis.
6. Any overnight avoidance, maximum-holding or rollover-flat overlay becomes a new trial and requires evaluation outside the data used to design it, followed by prospective shadow evidence.

No TP/SL search, portfolio construction, shadow start, Discord or MT5 order is authorized.