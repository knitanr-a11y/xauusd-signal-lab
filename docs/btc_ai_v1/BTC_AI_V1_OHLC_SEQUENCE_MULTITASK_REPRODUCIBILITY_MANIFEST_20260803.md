# BTC AI V1 — OHLC Sequence Multi-task Reproducibility Manifest

Date: 2026-08-03

## Conversation package

- file: `BTC_AI_V1_OHLC_SEQUENCE_MULTITASK_RESEARCH_20260803.zip`
- SHA256: `532b37a89c0b1365af04288a3cc47e83462d990dd7d40b5c825d9c8b8bbcf7ca`
- files: 57
- compressed size: approximately 108 KB
- expansion test: passed

The package excludes:

- raw XM candle CSV files;
- GOLD files;
- external-market data;
- large derived feature arrays;
- model binary files.

## Included code

- OHLC sequence and exact-M1 target preparation;
- LightGBM lag/summary baseline preparation;
- LightGBM path and hazard model tasks;
- chunked 300-round LightGBM hazard execution;
- checkpointed GRU multi-task training;
- candidate conversion and exact-M1 development evaluation;
- top-configuration ledger reconstruction;
- sequence-tail failure forensic.

## Included results

- 32-candidate registry and capability audit;
- all 256 exact-M1 configurations;
- top-10 configurations;
- monthly, half-year and D1-regime decompositions;
- score-tail forensic;
- model diagnostics JSON files;
- formal Markdown and JSON result;
- internal SHA256SUMS.

## Authoritative GitHub files

- `config/btc_ai_v1/ohlc_sequence_transition_hazard_multitask_contract_20260803.json`
- `docs/btc_ai_v1/BTC_AI_V1_OHLC_SEQUENCE_MULTITASK_RESULT_20260803.md`
- `config/btc_ai_v1/ohlc_sequence_multitask_result_20260803.json`

## Boundaries

- XM `BTCUSD#` OHLC only;
- development covers exactly 24 months, 2024-01 through 2025-12;
- fixed spread 22.50 USD per BTC;
- closed M15 decisions and exact M1 execution;
- 2026 was not opened;
- formal supported candidates: 0.
