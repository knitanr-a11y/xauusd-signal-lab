# GOLD V3 Stage319 — Mochipoyo Dual-Tier Prospective Watch

## Purpose

Stage318 found a higher-win-rate primary Mochipoyo SHORT subset and a smaller premium subset. Stage319 freezes both exact rules and begins future-only collection from the first run cutoff.

No historical threshold is changed inside Stage319.

## Frozen source

Stage319 accepts only the exact Stage318 result:

- Stage318 status: `GOLD_V3_318_MOCHIPOYO_HIGH_CONFIDENCE_REFINEMENT_COMPLETE`
- Stage318 decision: `MOCHIPOYO_HIGHER_WIN_RATE_PRIMARY_FOUND`
- source candidate: `M5_H4|MOCHI_UNION|SHORT|RR1_5|ATR_GE_1_AND_NO_ROUND`
- primary profile: `ATR_STEADY_1_10_TO_1_45`
- premium profile: `TREND_FLOW_COMPRESSION_GE_0_95`

The Stage318 JSON, primary CSV, and premium CSV SHA256 values are verified before freezing or updating the watch.

## Base signal family

The following Mochipoyo alert tracks are pooled as one underlying M5/H4 SHORT method:

- `MOCHI_EARLY_PULLBACK`
- `MOCHI_HIDDEN_PULLBACK`
- `MOCHI_HTF_RCI_RESUME`
- `MOCHI_ROLL_RETEST`

Base filter:

- M5/H4
- SHORT
- ATR ratio at least 1.0
- round-number-near excluded
- RR1.5

Signals from multiple tracks at the same closed M5 decision time are one unique trade. Their numeric context must agree within `1e-12`; every contributing track is recorded and the maximum quality score is retained.

## Watch tiers

### PRIMARY

- ATR ratio from 1.10 through 1.45 inclusive
- historical 2024–2025 reference only: 24 trades, 62.5% win rate, PF 1.981, +10.748R, DD 3.173R

### PREMIUM

- compression ratio at least 0.95
- historical 2024–2025 reference only: 14 trades, 78.57% win rate, PF 4.079, +12.684R, DD 2.098R

A signal can qualify for both tiers. It remains one unique trade and is labelled `PRIMARY+PREMIUM`.

## Prospective cutoff

On the first run, Stage319 freezes:

- latest closed M1 open and close time
- latest closed M5 open and close time
- latest closed H4 open and close time
- prospective rule: `decision_dt` must be strictly later than the frozen latest closed M5 close time

The contract cutoff must never move. Do not delete or recreate the contract file.

## Entry, risk, and resolution

- entry: next exact M5 open after the closed M5 decision bar
- structural stop: confirmed ZigZag level with 0.10 ATR buffer
- minimum stop: 0.75 ATR
- maximum stop: 2.0 ATR
- target: 1.5R
- maximum holding time: 720 minutes
- M1 first-touch resolution
- same-M1 TP/SL collision: SL priority
- one position at a time
- no preemption
- pending trades have no as-of PnL
- only resolved trades contribute to metrics

## Future human-review gates

### PRIMARY

- at least 30 resolved accepted trades
- win rate at least 60%
- PF at least 1.35
- positive total R
- DD no more than 6R
- largest winner share no more than 35%

### PREMIUM

- at least 15 resolved accepted trades
- win rate at least 68%
- PF at least 1.50
- positive total R
- DD no more than 6R
- largest winner share no more than 35%

### Combined unique

- at least 30 resolved accepted trades
- win rate at least 58%
- PF at least 1.25
- positive total R
- DD no more than 8R
- largest winner share no more than 35%

Passing a gate only opens a human audit. It never promotes automatically.

## Outputs

- `stage319_mochipoyo_dual_tier_prospective_watch_contract.json`
- `stage319_mochipoyo_dual_tier_prospective_watch.json`
- `stage319_mochipoyo_dual_tier_prospective_signals.csv`
- `stage319_mochipoyo_dual_tier_prospective_resolved.csv`
- `stage319_mochipoyo_dual_tier_prospective_pending.csv`

## Preserved state

- GOLD V3 audit-only
- Stage314 prospective watch unchanged and active
- Stage317 research watch unchanged
- Stage318 research result unchanged
- Stage315 independent research unchanged
- Stage280 exact recovery remains blocked
- Stage307 candidate unchanged
- Stage292 candidate pool unchanged
- final signal unchanged
- MT5 automatic order OFF
- Discord OFF
- partial close OFF
