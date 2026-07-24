# NEXT CHAT HANDOFF — M9Z DONE / M10A IMPLEMENTED / USER-LOCAL REPRODUCTION PENDING

Date: 2026-07-25  
Repo: `knitanr-a11y/xauusd-signal-lab`  
Branch: `feature/mochipoyo-alert-research`

## Current state

M9Z assistant-side GOLD multi-timeframe payoff research is complete for M5 -> H1 -> H4.

M10A has now been implemented as an independent deterministic reproduction stage:

`M10A_GOLD_MULTI_TIMEFRAME_PAYOFF_DETERMINISTIC_REPRODUCTION`

Assistant-side self-verification on the same six immutable hashed GOLD CSVs passed exactly.

User-local reproduction is the next required step. No fresh prospective payoff-extension stage has started yet.

## Forward monitors — KEEP UNCHANGED

Keep running:

1. genuine source collector
2. M7C
3. M8C
4. M9V
5. M9Y

Immutable starts:

- M9V: `2026.07.24 11:04:00` MT5 server time
- M9Y: `2026.07.24 12:45:00` MT5 server time

Never reset, backfill, move a start, or rerun their initializers.

Forced reboot recovery remains the dedicated recovery BAT only.

## M10A frozen historical references

Raw frozen reproduction:

- M5 S1 = 1256 / PF 1.3336981886264172
- M15 S2 = 1495 / PF 1.365884145048126
- H1 S3 = 191 / PF 1.7802349633701025
- H4 S4 = 70 / PF 3.295562620459433

M9Z payoff references to reproduce:

- M5 entry = 842 / PF 1.5373384445763516
- M5 75% runner one-position = 837 / PF 1.6651962763806496 / overlap skips 5
- H1 entry = 171 / PF 2.814130403928734
- H1 50% runner one-position = 159 / PF 2.8303858342555084 / overlap skips 12
- H4 entry = 57 / PF 4.668798744063922

These are historical research-exposed references only.

## M10A implementation

Python:

`scripts/mochipoyo_alert_research/m10a/python/run_gold_multitimeframe_payoff_reproduction.py`

It is self-contained for the frozen replay and does not import M9P/M9U runtime logic to obtain the result.

User BAT folder:

`scripts/mochipoyo_alert_research/m10a/bat/`

Run exactly once:

`01_run_gold_multitimeframe_payoff_reproduction.bat`

After PASS:

`02_open_latest_results.bat`

Submit only:

`%LOCALAPPDATA%\xauusd_signal_lab\mochipoyo_alert_research\outputs\M10A\LATEST\99_UPLOAD_PACKAGE.zip`

Expected success prefix:

`[M10A PASS]`

If `[M10A BLOCKED]` appears, stop M10A only and submit the full console output. Do not touch M9V/M9Y/M7C/M8C/collector.

## Causality contract

M10A must preserve:

- newest CSV row is CLOSED by contract
- only fully closed higher-timeframe bars at each decision
- no future TP/SL/native-exit outcome in entry/candidate logic
- runner context evaluated only when native EXIT becomes known
- one-position state handled chronologically
- no nearest-M1 fallback
- historical outcomes used only for scoring/assertion after decisions

## After user-local M10A PASS

Only then may the next stage freeze a **separate new fresh prospective payoff-extension contract**.

Required order:

1. M10A user-local deterministic reproduction PASS
2. explicit new prospective contract
3. independent fresh future start
4. no backfill

Never retrofit historical M9Z/M10A findings into M9V or M9Y and never reuse their frozen starts.

All live/real actions remain OFF:

- Discord send = false
- MT5 orders = false
- live_ready = false
- final_signal = false
- real entry gate = false
