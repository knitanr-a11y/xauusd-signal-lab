# BTC BCR17 — B5 shared retrospective value-gate contract

- repository: `knitanr-a11y/xauusd-signal-lab`
- authoritative branch: `feature/btc-fresh-forward-research`
- authorized at: `2026-07-31T00:45:00+09:00`
- status: `CONTRACT_FROZEN_BEFORE_B5_VALUE_ACCESS`
- automatic promotion: forbidden

## 1. Authorization and scope

The user explicitly authorized BCR17.

BCR17 opens retrospective value fields for the eight B5 machines that passed BCR16. It does not authorize portfolio selection, prospective start, shadow, Discord, MT5 orders, live-ready or final-signal status.

All eight frozen machines and both directions must be reported. Result-driven machine deletion, side deletion, threshold rescue and exit rescue are forbidden.

## 2. Frozen sources

BTC M15:

- SHA256: `b8de00d117a119f9bf2f417b6228fe0ca0779c88f71a80b134bb9244d6768148`
- rows: `30,661`
- symbol: `BTCUSD#`
- side: BID
- latest row: closed

Accepted BCR16 capability package:

- file: `BCR16_B5_OUTCOME_BLIND_CAPABILITY_AUDIT_20260731.zip`
- SHA256: `c469be9455bd5639de336684e0fdcaebf6a72dc6f0bae623acefa5e0cb506653`
- closed episode rows: `844`
- capability survivors: `8`
- endpoint-open episodes: `0`

The BCR16 package SHA is a hard gate. Reconstructed, edited or similar episode ledgers are forbidden.

## 3. Frozen machine inventory

Exactly eight machines:

1. `TRACK_B_B5_R06_B075_W08_H1_IMPULSE_M15_RECLAIM`
2. `TRACK_B_B5_R06_B075_W16_H1_IMPULSE_M15_RECLAIM`
3. `TRACK_B_B5_R06_B100_W08_H1_IMPULSE_M15_RECLAIM`
4. `TRACK_B_B5_R06_B100_W16_H1_IMPULSE_M15_RECLAIM`
5. `TRACK_B_B5_R12_B075_W08_H1_IMPULSE_M15_RECLAIM`
6. `TRACK_B_B5_R12_B075_W16_H1_IMPULSE_M15_RECLAIM`
7. `TRACK_B_B5_R12_B100_W08_H1_IMPULSE_M15_RECLAIM`
8. `TRACK_B_B5_R12_B100_W16_H1_IMPULSE_M15_RECLAIM`

No ninth machine or parameter expansion is allowed.

## 4. Shared execution and cost contract

The BCR08/BCR09 execution interpretation is reused unchanged.

Common constants:

- profit currency: USD;
- result unit: USD per `1.00` lot;
- point: `0.01`;
- spread price: `CSV spread points × 0.01`;
- commission: `0`;
- swap: not included.

C0:

- LONG enters at BID open plus entry spread and exits at BID open;
- SHORT enters at BID open and exits at BID open plus exit spread;
- observed spread only.

C2:

- starts from C0;
- each entry and exit fill is worsened by `25%` of the contemporaneous spread.

Rollover:

- same-server-date episodes are labeled `FULL_KNOWN_COST_NO_ROLLOVER`;
- date-crossing episodes are labeled `PRE_SWAP_ONLY`;
- a rollover-exposed result cannot establish full-cost profitability because swap is not included.

No historical USDJPY conversion is invented.

## 5. Exact timestamp and path contract

Entry and exit must match exact M15 open timestamps in the frozen CSV.

No nearest row, next row, interpolation, sorting or repair is allowed.

MFE/MAE are opened for diagnosis but are not selection criteria.

- LONG excursions use BID intrabar high/low relative to the entry ask-equivalent;
- SHORT excursions use BID intrabar high/low plus the contemporaneous spread as an ask approximation;
- the exit bar contributes only its exact exit open, not its later high or low.

## 6. Multiple-testing contract

For each machine and cost case:

1. aggregate net USD by entry month;
2. exclude exactly-zero monthly values from the signed-rank calculation;
3. apply an exact one-sided Wilcoxon signed-rank test for monthly net greater than zero;
4. apply Holm adjustment across the eight frozen machines;
5. adjust C0 and C2 families separately;
6. use `alpha = 0.05`.

All raw and adjusted p-values must be reported.

## 7. Preregistered classifications

`VALUE_SUPPORTED_RETROSPECTIVE`

- C0 net positive and PF greater than 1;
- C2 net positive and PF greater than 1;
- C2 Holm-adjusted monthly one-sided p-value at most `0.05`.

`VALUE_PROMISING_RETROSPECTIVE`

- C0 and C2 net positive with PF greater than 1;
- C2 Holm-adjusted p-value above `0.05`.

`HOLD_COST_SENSITIVE`

- C0 net positive with PF greater than 1;
- C2 fails positive-net or PF-greater-than-1.

`REJECT_RETROSPECTIVE_VALUE`

- C0 net is not positive or C0 PF is not greater than 1.

Classification is reported, not automatically promoted.

## 8. Mandatory reports

The deterministic package must include:

- complete trade ledger;
- machine C0/C2 summary;
- LONG/SHORT summary;
- monthly summary;
- same-server-date and rollover-exposed summary;
- exit-reason summary;
- multiple-testing table;
- JSON summary;
- manifest and package SHA.

The following must remain false:

- automatic candidate promotion;
- portfolio selection;
- prospective start;
- shadow;
- Discord;
- MT5 orders;
- live-ready;
- final signal.

## 9. Decision boundary after BCR17

After the BCR17 result is audited, any further stage requires a new explicit user authorization.

A positive retrospective result does not by itself authorize deployment or prospective monitoring.
