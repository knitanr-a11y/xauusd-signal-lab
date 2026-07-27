# MOCHIPOYO Alert Research handoff — M10W19 started / wait for fresh gates

repo: `knitanr-a11y/xauusd-signal-lab`
branch: `feature/mochipoyo-alert-research`

## Current formal state

`M10W19_FRESH_START_PASS_RUNNING_WAIT_FOR_PREDECLARED_GATES_AUDIT_ONLY`

M10W19 is now initialized and its fresh prospective start is immutable:

`2026.07.28 02:31:00` MT5 server time

Do **not** rerun M10W19 BAT01. Restart/recovery is BAT03-only after this point.

## M10W19 initial package

- package: `99_UPLOAD_PACKAGE(58).zip`
- SHA256: `b375b80577e1db4d07ae9f89430d71b680a682e0b07ecb6842a5203553b8e5fb`
- result: `config/mochipoyo_alert_research/m10w19_user_local_initial_fresh_start_result_20260728.json`
- built at UTC: `2026-07-27T23:34:12Z`

The initial first cycle was a clean zero baseline:

- W0 baseline BLC1: candidate 0 / accepted 0 / resolved 0 / open 0
- W1 ATR-filtered BLC1: candidate 0 / accepted 0 / resolved 0 / open 0
- entry gaps 0 / exit gaps 0 in both arms
- prefix integrity PASS
- current observed-feed health PASS
- historical backfill false

These zero counts are not performance evidence. They only prove that the new forward comparison started cleanly from the frozen start.

## Frozen two-arm comparison

W0:
- exact frozen BLC1 baseline
- no ATR gate

W1:
- exact same BLC1 formula
- accept only when `h1_atr_pct100 < 0.67`
- exclude `>=0.67` or unavailable

Both arms:
- LONG
- M15 close -> next M15-open decision
- fully closed causal D1/H4/H1 inputs
- exact M1 entry/exit
- 240-minute horizon
- one position per arm
- actual spread, fixed $0.20, +1/+2bps metrics

No formula/gate/start/horizon/refit changes are permitted after this start.

## Review gates

Filtered W1 resolved count:

- 20: operational read-only review
- 60: interim read-only review
- 120: formal read-only review

20 or 60 never authorizes promotion. 120 is review only, not automatic promotion.

An integrity/feed/runtime anomaly may trigger an immediate read-only diagnostic before those gates.

## Operator state

Keep running:

`scripts/mochipoyo_alert_research/m10w19/bat/03_run_shadow_forever.bat`

Never rerun:

`scripts/mochipoyo_alert_research/m10w19/bat/01_initialize_fresh_shadow_once.bat`

Existing collector/M7C/M8C/M9V/M9Y/M10B/M10E/M10P/M10P2 remain unchanged and continue running.

M10P BAT01 / M10P2 BAT01 remain forbidden.
M10V remains forbidden until M10P and M10P2 are both >=20 resolved with integrity PASS.

## Safety

- GOLD/XAUUSD only for new M10 research
- audit-only
- no Discord send
- no MT5 orders
- no historical backfill
- no start reset
- no runtime reset
- no threshold/gate refit
- no live_ready/final_signal
- no automatic live promotion
