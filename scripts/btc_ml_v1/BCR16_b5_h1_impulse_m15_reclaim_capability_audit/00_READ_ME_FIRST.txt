BTC BCR16 — B5 H1 impulse / M15 pullback-reclaim capability audit

Repository branch:
  feature/btc-fresh-forward-research

Purpose:
  Build complete causal H1 bars only from exact four-bar M15 groups, replay the exact eight B5 machines frozen in BCR15, and produce label-free capability evidence.

This stage DOES NOT calculate or export:
  return, win/loss, PF, PnL, MFE, MAE, entry price, exit price, or future-exit outcome labels.

Input hard gate:
  SHA256: b8de00d117a119f9bf2f417b6228fe0ca0779c88f71a80b134bb9244d6768148
  rows:   30,661
  symbol: BTCUSD#
  bars:   BID M15, latest row contractually closed

H1 contract:
  Only exact M15 bars at minute 00, 15, 30 and 45 form one H1 bar. Partial H1, nearest/next rows and interpolation are forbidden.

Run:
  01_run_BCR16.bat

Output directory:
  C:\Users\regen\AppData\Local\xauusd_signal_lab\btc_ml_v1\outputs\BCR16_b5_h1_impulse_m15_reclaim_capability_audit\LATEST

After success, Explorer selects:
  99_UPLOAD_PACKAGE.zip

Upload only that selected ZIP. It contains:
  1. BCR16_B5_OUTCOME_BLIND_CAPABILITY_AUDIT_20260731.zip
  2. deterministic_repeat.json
  3. package_sha256.txt

The runner builds the core package twice and requires identical ZIP SHA256 values.

The default MT5 source may have grown. A prefix is accepted only if the first 30,661 data rows reproduce the frozen SHA exactly. No similar-file fallback, row sorting, repair or interpolation is permitted.

Still forbidden:
  B5 PnL/value evaluation, machine or side deletion, threshold rescue, portfolio selection, prospective start, shadow, Discord, MT5 order, live-ready/final signal, and any modification of Collector/M7C/M8C/M9/M10 or GOLD/MOCHIPOYO files.
