# NEXT CHAT HANDOFF — BTC AI V1 OHLC 2026 root cause complete; state-transition research next

- repository: `knitanr-a11y/xauusd-signal-lab`
- branch: `feature/btc-ai-v1-data-acquisition`
- date: `2026-08-03`
- status: `BTC_AI_V1_OHLC_2026_FAILURE_ROOT_CAUSE_IDENTIFIED_STATE_TRANSITION_RESEARCH_NEXT`

## User authority correction

The user rejected unsolicited Binance and other external data. External-data work is non-authoritative and must not be used. The only source authority is the accepted XM `BTCUSD#` closed-bar snapshot.

Read:

`docs/btc_ai_v1/USER_SCOPE_CORRECTION_EXTERNAL_DATA_REJECTED_OHLC_AUTHORITY_20260803.md`

## Completed forensic

Read first:

1. `docs/btc_ai_v1/BTC_AI_V1_OHLC_2026_FAILURE_ROOT_CAUSE_FORENSIC_20260803.md`
2. `config/btc_ai_v1/ohlc_2026_failure_root_cause_20260803.json`
3. `config/btc_ai_v1/current_state_20260803.json`
4. `config/btc_ai_v1/next_action_20260803.json`

## Root cause

`OHLC_STATE_TRANSITION_AND_CONDITIONAL_MEANING_SHIFT_CAUSED_LATE_SHORT_SELECTION`

Key evidence:

- SHORT base-label rate remained 36.53% in 2026, so downside opportunity did not disappear.
- D1-up share fell from 44.60% in 2024–2025 to 15.10% in 2026; D1-down share rose from 25.71% to 46.69%.
- mean D1 EMA20 slope / ATR changed from +0.1243 to -0.1232.
- finalist events moved from mean D1 trend +0.654 to -0.052.
- event one-bar return changed from -0.191 ATR to -0.493 ATR.
- event 32-bar return changed from -0.150 ATR to -1.154 ATR.
- event distance below EMA50 changed from -0.280 ATR to -0.876 ATR.
- event range expansion rose from 2.31 to 2.91.
- models therefore selected deeper and more mature selloffs in 2026.
- MTF model AUC fell to about 0.508; score distribution itself remained stable.
- four of five frozen event sets had SHORT-label hit rates below the unconditional 2026 rate.
- stop-first rate increased by roughly ten percentage points for the main 2R candidates.
- fixed spread burden increased, but four of five candidates still lost with zero spread.

Regime composition was not the full explanation. Reusing 2024–2025 conditional average PnL with actual 2026 D1-state counts predicted approximately +45,765 USD across candidate ledgers, while actual was -70,522 USD. Conditional drift residual was approximately -116,287 USD.

Do not rescue with a simple `D1 up only` filter.

## Current next stage

`BTC_AI_V1_OHLC_STATE_TRANSITION_REPRESENTATION_AND_LEAVE_ONE_REGIME_OUT_DESIGN`

Build causal OHLC representations for:

- early impulse;
- mature extension;
- pullback;
- continuation;
- exhaustion;
- reversal;
- swing age and distance;
- range-break age and distance;
- slope acceleration/deceleration;
- post-expansion acceptance/rejection;
- higher-timeframe phase interactions.

Before candidate outcomes, freeze leave-one-regime-out and leave-one-transition-type-out validation. Aggregate PF alone is insufficient; minimum performance across coarse D1/H4 states must be reported.

## Hard boundaries

- XM BTCUSD# only;
- MT5 broker-server time;
- closed bars and exact M1 execution;
- fixed spread 22.50 USD;
- no external data;
- no D1-only rescue;
- no threshold, side, month, exit or horizon rescue;
- 2026 is diagnostic, not untouched support;
- no portfolio, Shadow, Discord, MT5 orders, live-ready or final signal;
- do not modify GOLD V19, Challenger C1, P75 or MOCHIPOYO.
