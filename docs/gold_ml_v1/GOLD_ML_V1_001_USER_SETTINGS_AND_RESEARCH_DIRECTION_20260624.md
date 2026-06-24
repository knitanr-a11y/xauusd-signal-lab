# GOLD ML V1 — Phase001 User Settings and Research Direction

Date: 2026-06-24  
Status: `GOLD_ML_V1_001_METHOD_SETTINGS_RECORDED`  
Decision: `DISCOVER_AND_ACCUMULATE_INDEPENDENT_CANDIDATES_WITHOUT_ALERT_REPLICATION`

## Confirmed market and indicator inputs

Symbol:

`GOLD#`

RCI periods:

- short: 9
- medium: 14
- long: 18

The user wrote RSI, but the Mochipoyo guide and the surrounding discussion consistently concern RCI. The new-project contract therefore records RCI 9/14/18. If RSI was actually intended, this must be corrected explicitly by superseding the settings contract.

TORYS MACD inputs:

- Fast EMA Length: 6
- Slow EMA Length: 13
- Signal Length: 4
- all other TORYS settings: user reports unchanged defaults

The exact custom TORYS source formula has not been supplied. The project must not claim exact TORYS replication.

The allowed starting interpretation is:

`MACD line = EMA(close, 6) - EMA(close, 13)`

The signal smoothing cannot be silently guessed. Until the TORYS defaults are confirmed, EMA4 and SMA4 signal implementations may be evaluated only as separate feature-set variants with distinct feature-set IDs. The raw 6-13 MACD line may be used independently.

EMA context remains:

- EMA20
- EMA30
- EMA40

Features may include ordering, slope, separation, compression, and price distance.

## Research direction

The objective is not to reproduce the Mochipoyo alert formula. The objective is to let machine learning and systematic testing find profitable shapes inspired by the guide.

Mochipoyo is one source of candidate ideas, not the only source.

Additional independent candidate sources may include:

- pure price action and volatility;
- trend continuation;
- reversal;
- session specialists;
- volatility-regime specialists;
- other future methods supplied by the user.

Every passing setup remains a separate immutable candidate. A new candidate is added; it does not replace the previous candidate.

## Enabled independent timeframe lanes

The initial research includes all four supplied main/context relationships:

1. M1 with H1;
2. M5 with H4;
3. M15 with H4;
4. H1 with D1.

Each lane is independent. LONG and SHORT are also independent. Combining them later creates a portfolio ID, never a replacement candidate ID.

## Initial setup families

No candidate is registered yet. The initial research families are:

- higher-timeframe trend plus lower-timeframe pullback continuation;
- higher-timeframe RCI reversal plus lower-timeframe trend formation;
- hidden-divergence continuation;
- regular-divergence reversal;
- EMA-ordered pullback;
- roll-reversal retest;
- high-volatility trend continuation;
- round-number context;
- data-driven non-Mochipoyo discovery.

A family, direction, timeframe lane, label, entry rule, or exit rule change requires a new candidate ID.

## Delegated label design

The user delegated the initial label/exit design.

The primary discovery family will use ATR-normalized triple barriers because it gives comparable outcomes across changing GOLD price levels and volatility regimes without embedding future discretionary interpretation into the entry features.

Frozen starting design:

- decision moment: close of the decision-timeframe bar;
- entry: next available M1 open at or after that close moment;
- LONG and SHORT labels generated separately;
- stop distance: 1.0 ATR of the decision timeframe, calculated from closed past bars only;
- reward targets: 1.0R, 1.5R, and 2.0R as separate label IDs;
- same-M1 TP/SL touch: SL priority;
- spread and estimated execution cost included;
- every reward multiple is a separate label, model, and candidate lineage.

The three target labels are not mixed into one candidate.

After the primary family is audited, separate secondary label families may test:

- structural swing stop plus fixed-R target;
- RCI opposite-side exit;
- fixed-horizon directional return.

No final holdout period may be used to select among label families.

## Candidate accumulation objective

Trade count will be increased by accumulating independently validated candidates, for example:

- M1-H1 LONG continuation candidate;
- M1-H1 SHORT continuation candidate;
- M5-H4 hidden-divergence candidate;
- M15-H4 roll-reversal candidate;
- H1-D1 trend candidate;
- non-Mochipoyo volatility candidate.

It will not be increased by loosening one candidate until its identity and win rate change.

## One remaining TORYS detail

A screenshot of the TORYS settings panel or its Pine/source code would allow exact confirmation of:

- input price source;
- signal-line smoothing type;
- any extra normalization, color-state, or divergence behavior.

This does not block the raw-data contract or the 6-13 MACD-line features. It only blocks claiming exact TORYS signal/histogram replication.

## Current boundary

Recorded:

- GOLD# symbol;
- RCI 9/14/18;
- TORYS lengths 6/13/4;
- discovery rather than alert replication;
- all four independent timeframe lanes;
- multiple independent candidate accumulation;
- Mochipoyo and non-Mochipoyo candidate sources;
- initial multi-label design.

Still required before training:

- exact dataset splits and embargo;
- exact ATR calculation contract;
- cost conversion for GOLD# spread points;
- feature-set registry;
- label ID registry;
- candidate and portfolio registry schemas;
- local dataset audit outputs.
