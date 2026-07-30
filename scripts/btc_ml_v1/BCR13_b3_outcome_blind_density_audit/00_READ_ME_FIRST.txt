BTC BCR13 — B3 outcome-blind density and state-machine audit

Repository branch:
  feature/btc-fresh-forward-research

Purpose:
  Implement the exact eight B3_BREAKOUT_RETEST_REACCELERATION machines frozen in BCR12 and produce label-free capability evidence only.

This stage DOES NOT calculate or export:
  return, win/loss, PF, PnL, MFE, MAE, entry price, exit price, or future-exit outcome labels.

Input hard gate:
  SHA256: b8de00d117a119f9bf2f417b6228fe0ca0779c88f71a80b134bb9244d6768148
  rows:   30,661
  symbol: BTCUSD#
  bars:   BID M15, latest row contractually closed

The BAT defaults to the live append-only MT5 CSV path. If that file has grown, the runner may rehydrate only a byte-exact 30,661-row prefix whose SHA equals the frozen SHA. If no exact prefix matches, it stops. It never selects a similar file, sorts rows, interpolates gaps, or uses nearest/next rows.

Run:
  01_run_BCR13.bat

Optional input override before running:
  set BTC_BCR13_INPUT=C:\exact\path\to\btcusdsharp_m15.csv

Standard output root:
  C:\Users\regen\AppData\Local\xauusd_signal_lab\btc_ml_v1\outputs\BCR13_b3_outcome_blind_density_audit\LATEST\

Upload file:
  99_UPLOAD_PACKAGE.zip

The BAT creates the deterministic BCR13 evidence files, bundles the required upload set into 99_UPLOAD_PACKAGE.zip, and then opens Explorer with that ZIP selected. Upload only that selected ZIP.

99_UPLOAD_PACKAGE.zip contains:
  1. BCR13_B3_OUTCOME_BLIND_DENSITY_AUDIT_20260730.zip
  2. deterministic_repeat.json
  3. package_sha256.txt

The separate 02_open_latest_results.bat opens the same LocalAppData output location and selects 99_UPLOAD_PACKAGE.zip when it exists.

State conflict policy:
  If LONG and SHORT breakout predicates are simultaneously true, the implementation records SIMULTANEOUS_BREAKOUT_NO_TRANSITION and remains IDLE. It never chooses a side. All conflict counts are reported.

Still forbidden:
  BCR14 value evaluation, candidate promotion, portfolio selection, prospective start, shadow, Discord, MT5 order, live-ready/final signal, and any modification of Collector/M7C/M8C/M9/M10 or GOLD/MOCHIPOYO files.
