# BTC FF03 BTC7R causality and selection-leak audit contract

- repository: `knitanr-a11y/xauusd-signal-lab`
- base: `main`
- working branch: `feature/btc-fresh-forward-research`
- stage: `BTC_FF03_BTC7R_CAUSALITY_AND_SELECTION_LEAK_AUDIT_READ_ONLY`
- candidate: `BTC7R_M15_IMPULSE_HIGH_WIN_24_96_M22_R110`

## 1. Why FF03 exists

FF02 produced six genuinely fresh BTC7R entries and all six lost. The historical candidate had been described as a high-win candidate, so the historical score cannot be used without checking two separate risks:

1. direct look-ahead or append instability in the signal implementation;
2. selection leakage / multiple-testing overfit in the way the final filters were chosen.

Passing the first does not pass the second.

## 2. Immediate trust status

Until FF03 is reviewed:

- the old `73.77%` pre-2026 combined score is not accepted as independently unseen validation;
- the old 22-trade 2026 result is a retrospective replay, not independently prospective evidence;
- the FF02 six trades are the first independently verifiable prospective evidence;
- BTC7R is quarantined from promotion, lot design and live use;
- no rescue filter or replacement is selected from the six losses.

This does not claim deliberate leakage. It means the repository does not contain sufficient pre-validation immutable evidence to prove blinding.

## 3. Direct causality audit

Use the currently available stable M5/M15/H1 snapshots.

Generate the complete BTC7R plan set once on the full snapshot. For every available plan:

- truncate M15 at the signal bar;
- truncate H1 so that only H1 bars whose close decision time is known at the signal are present;
- truncate M5 at the exact entry bar open;
- recompute indicators, base plans and BTC7R refinement from the truncated inputs;
- compare the entire plan set through that entry boundary against the full-run plan set through the same boundary.

Compare exact keys and entry-known values:

- signal time
- entry time
- direction
- entry bid
- stop and target
- risk, reward and RR
- H1 trend separation
- M15 impulse ATR multiple
- close location
- trend age

Any missing plan, extra plan, changed direction or material numeric change fails direct causality.

## 4. Legacy 2026 parity

The frozen reproduction reference records 22 BTC7R trades, 11 wins and 11 losses through the old cutoff.

The historical implementation compared naive CSV timestamps directly, while later work established that current MT5 CSV timestamps are broker-server wall clock. FF03 does not silently rewrite the historical test. It reproduces the legacy raw-time boundary:

`2026-01-01 00:00:00 <= raw entry time <= 2026-07-02 02:15:00`

Expected metrics:

- trades: 22
- wins: 11
- losses: 11
- win rate: 50.0%
- PF: 1.044792
- total pips: 35.508909
- max DD: 347.374394 pips

Mismatch means the old score is not reproduced by the current local suffix and current frozen code.

## 5. Selection-provenance audit

Documented selection claim:

- TRAIN: 2024-08-01 to before 2025-02-01
- DEV: 2025-02-01 to before 2025-07-01
- VALIDATION: 2025-07-01 to before 2026-01-01
- claimed rule freeze before opening VALIDATION

Repository evidence:

- earliest immutable BTC7R candidate-contract commit: `780eccd93f85a087633f90a8e4d016f215b126d0`
- commit time: `2026-07-02 08:29:16 UTC`
- reproducible refinement script commit: `6177de49be57c33b76b455a8ccfbb066bceac8aa`

The immutable repository evidence is after the claimed validation ended. No complete trial ledger containing every tested feature, threshold and target setting was found.

Therefore FF03 classifies the old validation as:

`HISTORICAL_VALIDATION_NOT_PROVEN_BLIND_RECLASSIFY_RETROSPECTIVE`

This classification remains even when prefix causality passes.

## 6. First independently verifiable prospective boundary

The strict evidence boundary is after:

`2026-07-02 08:29:16 UTC`

The six FF02 entries all occur after this boundary. They remain prospective observations and are not used to tune a repair.

## 7. Inputs and snapshots

FF03 requires:

- reviewed FF01 summary with all five READY;
- completed FF02 summary with BTC7R 6 planned, 6 resolved, 0 wins, 6 losses;
- M5/M15/H1 source paths selected by FF01.

Source files remain read-only. FF03 hashes source before copy, snapshot and source after copy and accepts only a stable exact copy. Internal snapshots are deleted after audit and excluded from the upload package.

## 8. Possible formal outcomes

- `DIRECT_CAUSALITY_FAIL_INVALIDATE_BTC7R`
- `LEGACY_PARITY_FAIL_HISTORICAL_SCORE_INVALID`
- `DIRECT_CAUSALITY_PASS_SELECTION_PROVENANCE_FAIL`

The expected safe interpretation when prefix causality and legacy parity pass is still:

`QUARANTINED_REBUILD_REQUIRED`

because independent validation blindness is not proven.

## 9. Rebuild rule

FF03 does not build the replacement.

A future clean rebuild must:

- explicitly label all old BTC7R periods as retrospective research;
- record the complete hypothesis and threshold grid before outcomes are opened;
- use deterministic expanding or nested walk-forward evaluation with purge where required;
- preserve all trial counts, rejected cells and multiplicity corrections;
- never tune against the six FF02 losses;
- freeze the final rule in Git before the next prospective observation;
- use future-only observations for promotion evidence.

## 10. Output

`%LOCALAPPDATA%\xauusd_signal_lab\btc_ml_v1\outputs\03_btc7r_causality_selection_audit\LATEST\`

- `00_READ_ME_FIRST.txt`
- `01_audit_summary.json`
- `02_audit_report.txt`
- `03_prefix_invariance.csv`
- `04_legacy_period_parity.csv`
- `05_selection_provenance.json`
- `06_input_manifest.csv`
- `99_UPLOAD_PACKAGE.zip`

## 11. Safety and stop

No candidate-rule change, fresh-loss-driven optimization, replacement candidate, lot design, monetary DD, source mutation, M7C mixing, GOLD/MOCHIPOYO change, Discord, MT5 order, live-ready or final signal.

Stop after uploading the ZIP. A clean rebuild stage requires explicit user review of FF03 results.
