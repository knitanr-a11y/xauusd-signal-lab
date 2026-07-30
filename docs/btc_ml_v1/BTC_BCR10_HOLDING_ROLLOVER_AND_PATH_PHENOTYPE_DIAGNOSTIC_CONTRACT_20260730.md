# BTC BCR10 — holding, rollover and path-phenotype diagnostic contract

- repository: `knitanr-a11y/xauusd-signal-lab`
- branch: `feature/btc-fresh-forward-research`
- recorded: `2026-07-30T20:00:00+09:00`
- status: `OUTCOME_EXPOSED_DIAGNOSTIC_CONTRACT_FROZEN`
- candidate promotion: forbidden

## 1. Purpose and exposure

BCR09 rejected seven base machines and placed one B4 machine on cost-sensitive HOLD. It also revealed that Track A and B4 same-server-date subsets were positive while their rollover-exposed subsets caused large losses.

That split is already outcome-exposed. BCR10 is therefore a development diagnostic, not validation. It may explain loss paths and define a small later overlay family, but no result may be called OOS, prospective, supported or deployable.

## 2. Frozen input

- BCR09 accepted package SHA256: `92b989ce7b0b76acab0bb6205c1d8e5cfdd9d2f86c42e74781e38177c79c45fa`
- BTC M15 SHA256: `b8de00d117a119f9bf2f417b6228fe0ca0779c88f71a80b134bb9244d6768148`
- cost scenario for path attribution: `C0_OBSERVED_SPREAD`
- secondary stress display: `C2_25PCT_SPREAD_PER_FILL`

## 3. Diagnostic population

Include exactly:

- Track A F1, F2, F3 and F4;
- Track B B4 E0 and B4 E1.

Exclude B1 E0 and E1 from rescue design. B1 failed C0 and its same-server-date subset; it remains audit history and may be reconsidered only as a materially new mechanism family.

## 4. Fixed bins

### Holding duration in M15 bars

- `H01_04`: 1–4
- `H05_08`: 5–8
- `H09_16`: 9–16
- `H17_32`: 17–32
- `H33_64`: 33–64
- `H65_128`: 65–128
- `H129_PLUS`: 129 or more

### Calendar-date crossings

- `D0`: same MT5 server date
- `D1`: one server-date boundary crossed
- `D2`: two boundaries crossed
- `D3_PLUS`: three or more

### Entry and exit hour

Fixed four-hour server-time bins:

- `00_03`, `04_07`, `08_11`, `12_15`, `16_19`, `20_23`

### Direction and family

LONG and SHORT remain separate. Track A members and B4 members remain separate; pooled summaries are secondary only.

No bin boundary may be changed after output.

## 5. Path metrics

For each closed episode, use the actual M15 BID OHLC rows from entry through exit, without interpolation.

Report:

- gross and C0/C2 net PnL;
- MFE and MAE in USD price units per 1 lot;
- MFE and MAE normalized by entry ATR14;
- bar of first MFE and first MAE;
- peak favorable excursion before the first server-date crossing;
- adverse excursion before the first server-date crossing;
- favorable-excursion giveback at actual exit;
- whether the trade was positive immediately before the first date crossing;
- PnL at the exact `23:45` server-open boundary when available;
- spread cost share relative to absolute gross move.

For LONG, path values use BID high/low against the spread-adjusted entry ask. For SHORT, path values use BID low/high and apply the contemporaneous spread when estimating a buy-to-cover ask. All formulas must be recorded.

MFE/MAE are retrospective diagnostics and never signal inputs in this stage.

## 6. Required aggregate reports

For each machine and direction:

- count, PF, net and expectancy by fixed holding bin;
- count, PF, net and expectancy by date-crossing bin;
- entry-hour and exit-hour matrices;
- median/IQR MFE, MAE and giveback;
- fraction of rollover-exposed losers that were positive before first crossing;
- fraction of rollover-exposed losses attributable to giveback after a positive MFE;
- loss concentration by holding and crossing bins;
- month coverage for each important phenotype.

No p-value-driven threshold search is used. Descriptive bootstrap intervals may use a fixed seed and 5,000 episode-level resamples, but they do not validate a filter.

## 7. Integrity restrictions

- no signal formula changes;
- no removal of losses;
- no outcome-selected redefinition of bins;
- no TP/SL, trailing-stop or time-stop evaluation;
- no forced-flat overlay PnL in BCR10;
- no portfolio combination;
- no use of GOLD/MOCHIPOYO outputs;
- no runtime, Collector or M7C change.

## 8. Later overlay-family rules

After BCR10, at most the following finite causal overlay types may be preregistered as new trials:

1. maximum holding at fixed `16`, `32` or `64` M15 bars;
2. server-day flat at the exact `23:45` server-open boundary;
3. one combination of server-day flat with one fixed maximum-holding level;
4. no overlay baseline.

No ATR threshold, direction filter, entry-hour filter, weekday filter, TP/SL or discretionary condition may be added in the first overlay family.

Any overlay selected using this exposed history must remain a development proposal and must enter a new prospective shadow family. Retrospective improvement alone cannot promote it.

## 9. Acceptance gate

BCR10 passes only if:

- all six diagnostic machines and every BCR09 closed episode for them are represented exactly once;
- fixed bins are used unchanged;
- OHLC path rows are exact and gap cases are explicit;
- MFE/MAE formulas are directionally correct and tested;
- no overlay PnL or candidate selection is produced;
- the output clearly distinguishes description from validation.

## 10. Decision boundary

BCR10 authorizes diagnosis only. BCR11 may preregister and replay a finite overlay family, but the resulting family remains outcome-exposed and requires prospective shadow evidence before any deployment claim.