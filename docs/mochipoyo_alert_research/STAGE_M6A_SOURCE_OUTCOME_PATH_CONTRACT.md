# Mochipoyo Stage M6A Source Outcome Path Contract

Status: `MOCHIPOYO_M6A_SOURCE_OUTCOME_PATHS_AUDIT_ONLY`

## Scope

Stage M6A creates a descriptive outcome ledger for the source alert chronology already
built in Stage M3. It does not approve an entry gate or trading rule.

Implemented entry references:

- `SOURCE_PRIMARY_ALERT_IMMEDIATE`
- `SOURCE_REENTRY_ALERT_IMMEDIATE`

Implemented exit reference:

- `SOURCE_EXIT_ALERT`

The source TradingView alert close is retained as the entry reference. The source
TradingView EXIT close is retained as the terminal exit reference. MT5 M1 bars are
used only for the path between them.

## Resolved and open entries

- Every source `PRIMARY_ALERT` produces one deterministic virtual-entry row.
- Every source `REENTRY_ALERT` produces one independent deterministic virtual-entry
  row ending at the same source EXIT as its parent episode.
- A closed episode produces an `outcomes` row and an `outcome_path_metrics` row.
- An open episode remains `OPEN_SOURCE_EPISODE` and does not produce a resolved
  outcome.
- Open entries must not participate in resolved-only health or expected-value
  calculations.

## M1 path boundary contract

M1 OHLC cannot reveal whether an intraminute high or low occurred before or after an
alert that fired inside that minute. Therefore Stage M6A is conservative:

1. Floor the source entry and source EXIT timestamps to UTC minutes.
2. Convert the minute boundaries to MT5 server time with the audited Stage M4 offset.
3. Use only M1 bars whose server open is strictly after the entry minute and strictly
   before the EXIT minute.
4. Exclude the complete entry minute.
5. Exclude the complete EXIT minute.
6. Include the source EXIT close as a terminal price point.

An entry and its source EXIT must have the same audited offset. If they differ, the
build fails closed rather than guessing across a DST transition.

## MFE and MAE

For LONG:

- source return = EXIT close - entry close
- MFE = highest favorable path/terminal price - entry close
- MAE = entry close - lowest adverse path/terminal price

For SHORT, signs are reversed so favorable movement remains positive.

Stored units:

- source price units
- basis points relative to source entry price
- M5 ATR14 multiples
- M15 ATR14 multiples

The `outcomes.mfe` and `outcomes.mae` columns contain source price units. The explicit
normalizations and path audit fields are stored in `outcome_path_metrics`.

## Deliberately undefined

Stage M6A does not invent a stop, target, position size, contract size, or commission
model. Therefore:

- `result_r` remains NULL
- `result_usd` remains NULL
- `sl_price` remains NULL
- `tp_price` remains NULL

Those values become valid only after a separate, explicit policy contract is frozen.

Not implemented yet:

- M5 structure-turn entry
- second-bottom/second-top entry
- fixed-R exit
- M5 opposite-RCI exit
- recent-high/recent-low exit

## Causality and safety

- Stage M3, M4, and M5 must exactly cover the current eligible raw-alert set.
- A newly collected but unaligned/unfeatured alert causes a fail-closed stop.
- Post-entry data is used only to measure a resolved outcome.
- Post-entry data is never used to select or reject the entry.
- Connection-test alert ID 1 remains excluded through its user-confirmed annotation.
- Raw alerts, episodes, Stage M4 alignment, Stage M5 features, and source CSV files are
  not modified.
- Discord, MT5 orders, `live_ready`, and `final_signal` remain OFF.

## Sample-size warning

Current results are descriptive initial-observation data. The project handoff requires
completed episodes rather than notification rows for milestones. High-expectancy rule
design begins only after the required sample and subgroup coverage are reached.
