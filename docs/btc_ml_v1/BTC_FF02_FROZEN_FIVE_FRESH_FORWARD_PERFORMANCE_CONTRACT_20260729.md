# BTC FF02 frozen-five fresh-forward performance contract

- repository: `knitanr-a11y/xauusd-signal-lab`
- base: `main`
- working branch: `feature/btc-fresh-forward-research`
- stage: `BTC_FF02_FROZEN_FIVE_CANDIDATE_FRESH_FORWARD_PERFORMANCE_EVALUATION`
- boundary: `entry_time_utc > 2026-07-02 02:15:00`
- FF01 gate: `READY_ALL_FIVE_CANDIDATES`

## Objective

Evaluate only the frozen BTC4/BTC5/BTC6/BTC7R/BTC9R candidates after the exclusive cutoff. FF02 is research-only and does not authorize live use.

## FF01 gate

FF02 reads `%LOCALAPPDATA%\xauusd_signal_lab\btc_ml_v1\outputs\01_fresh_forward_availability\LATEST\01_availability_summary.json` and blocks unless all five candidates are READY and the canonical broker offset still agrees.

## Frozen implementation reuse

Candidate engines remain unchanged:

- `run_btc3_video_ema_user_contract.py`
- `btc5_video_5m_ema200_nwave_candidate.py`
- `btc6_video_m15_ema200_nwave_candidate.py`
- `btc7r_m15_impulse_high_win_candidate.py`
- `btc9r_m15_prevday_breakout_high_win_candidate.py`

Outcome functions are imported from `reproduce_btc_stacking_portfolio.py`; that script is not executed as the fresh evaluator and `--skip-input-hash-check` is not used.

## Time contract

Engines run on raw MT5 broker-server wall-clock timestamps so original H4 decisions, D1 broker-day boundaries and exact lower-timeframe matching are preserved. Engine inputs are not shifted to UTC.

The canonical main conversion is used only for strict fresh filtering, entry/exit UTC fields and UTC monthly grouping. Equality with the cutoff is excluded.

## Deterministic snapshot

For M5/M15/H1/D1/H4, FF02 hashes source before copy, copies to a private run snapshot, hashes snapshot and source after copy, and accepts only exact size/hash equality. It validates required columns, strict order and duplicates. Snapshots are deleted after evaluation and excluded from the ZIP.

## Outcome and portfolio contract

- `$10 = 1 pip`, spread `$30`
- simple same-bar order: SL first
- BTC4 after TP1: break-even first
- BTC4 risk cap: 400 pips
- no global one-position cap
- no exact-time overlap deduplication
- open trades excluded from realized WR/PF/pips/DD and reported separately
- no lot or monetary DD

Outputs include unified trades, candidate/month/direction metrics, input manifest and engine manifest.

## Paths

`scripts/btc_ml_v1/fresh_forward_performance/python/evaluate_btc_fresh_forward_performance.py`

User BATs:

- `00_READ_ME_FIRST.txt`
- `01_run_fresh_forward_evaluation.bat`
- `02_open_latest_results.bat`

Output root:

`%LOCALAPPDATA%\xauusd_signal_lab\btc_ml_v1\outputs\02_fresh_forward_performance`

## Prohibitions

No rule/threshold/TP/SL/exit/spread/pip/overlap change, fresh optimization, candidate replacement, BTC10R, lot design, monetary DD, source mutation, M7C mixing, collector/M7C/M8C/GOLD/M10W changes, Discord, MT5 orders, live-ready or final signal.

## Stop

Stop after `LATEST/99_UPLOAD_PACKAGE.zip` is uploaded for review. No later stage is automatically authorized.
