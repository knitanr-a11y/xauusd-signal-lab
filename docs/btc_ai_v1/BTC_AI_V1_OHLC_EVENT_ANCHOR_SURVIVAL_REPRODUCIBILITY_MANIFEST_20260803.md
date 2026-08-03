# BTC AI V1 — OHLC Event-Anchor Survival Reproducibility Manifest

Date: 2026-08-03

## Conversation package

- name: `BTC_AI_V1_OHLC_EVENT_ANCHOR_SURVIVAL_RESEARCH_20260803.zip`
- SHA256: `029ec01079d59f52511eae46c1d0b960e1a44223e46a111e8c8b7add505c253e`
- expansion test: passed
- package size: approximately 21 MB compressed
- raw XM candles: not included
- GOLD files: not included
- external-market data: not included

## Included implementation

- `run_event_anchor_survival.py`
- `run_matched_baseline_correction.py`
- full anchor registry with trajectories
- matched baseline universe
- raw survival summaries
- corrected support evaluation
- half-year and D1 incremental-effect tables
- cause-specific hazard table
- checkpoint MFE/MAE/displacement/pullback summaries
- formal Markdown and JSON result
- SHA256SUMS

## Frozen GitHub authority

- `config/btc_ai_v1/ohlc_event_anchor_survival_forensic_contract_20260803.json`
- `config/btc_ai_v1/ohlc_event_anchor_survival_bin_addendum_20260803.json`
- `config/btc_ai_v1/ohlc_event_anchor_matched_baseline_correction_20260803.json`
- `docs/btc_ai_v1/BTC_AI_V1_OHLC_EVENT_ANCHOR_SURVIVAL_RESULT_20260803.md`
- `config/btc_ai_v1/ohlc_event_anchor_survival_result_20260803.json`

## Important correction

The initial raw support count of 13 is invalid because asymmetric continuation/reversal barriers and reversal-first collisions create structural raw reversal dominance. Only the matched-baseline corrected result is authoritative.

Corrected forensic support survivors: **0**.

Candidate PnL and 2026 were not opened.
