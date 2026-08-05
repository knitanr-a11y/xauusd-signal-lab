# BTC AI V1 — Full95 All-Q20 Prospective Shadow V1

Date: 2026-08-06  
Repository: `knitanr-a11y/xauusd-signal-lab`  
Branch: `feature/btc-ai-v1-data-acquisition`

## Formal status

`IMPLEMENTED_IN_GITHUB_READY_FOR_ONE_TIME_USER_PC_ACTIVATION_NOT_ACTIVE`

This is an observation-only matched-pair prospective Shadow. It does not place MT5 orders and is not a final signal.

## Compared arms

1. `CONTROL_LOCK_0P25ATR`
2. `AI_FULL95_ALL_Q20`

Both arms use the same parent H4-close-versus-broker-D1-open rule, exact decision-time M1 open, 4 ATR initial stop, +2 ATR lock trigger, +0.25 ATR locked stop, and 22.50 USD round-trip cost per completed 1 BTC trade.

The only difference is that the AI arm skips a complete new LONG or SHORT state episode when the frozen LightGBM score is below the frozen Q20 threshold.

## Research-integrity interpretation

Historical results are consumed and post-hoc. They are not formal evidence and are not promotion gates. Only observations after the one-time user-PC activation watermark count toward the prospective comparison.

The following are frozen during observation:

- model file;
- 95-feature order;
- frozen imputation medians;
- Q20 threshold;
- parent entry and exit rules;
- Control/AI arm definitions;
- no-backfill activation;
- review gates.

No LONG-only or Top30 challenger is included. No automatic retraining or candidate switching exists.

## Isolation from Stage55

Stage55 remains active and frozen at cutoff `2026-08-04 10:52:00` MT5. This package has separate scripts, model, configuration, launchers, runtime state and Discord outbox. It does not read, update, delete or reset the Stage55 runtime directory.

Package root:

`runtime/btc_ai_v1/full95_all_q20_shadow_v1`

Default local state created after activation:

`runtime/btc_ai_v1/full95_all_q20_shadow_v1/runtime/full95_all_q20_v1`

## Activation boundary

GitHub implementation does not activate the Shadow. Activation occurs only when the user runs `launchers/02_INIT_ONCE.bat` on the user PC after configuring exact CSV paths.

- pre-activation trades: context construction only, excluded from evaluation;
- post-activation exact-M1 gap: abort, no fallback;
- orders/live trading/live-ready/final signal: OFF.

## Review gates

- 30 days: technical/data-quality review only;
- 3 calendar months + 50 Control closes + 10 AI skips: early futility review only;
- 6 calendar months + 100 Control closes + 20 AI skips + skips in at least two quarters: first primary comparison;
- no automatic promotion.

## Validation completed before GitHub commit

- frozen package manifest verification passed;
- package tests passed;
- research/runtime 95-feature parity artifact retained;
- temporary `init -> process -> status` smoke artifact retained;
- no user-PC activation claimed.
