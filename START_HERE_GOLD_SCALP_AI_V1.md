# START HERE — GOLD SCALP AI V1

Date: 2026-08-02  
Branch: `feature/gold-scalp-ai-v1-research`

## Formal status

`RETROSPECTIVE_SCALP_AI_RESEARCH_COMPLETE_NO_FORMAL_CANDIDATE`

## Purpose

This branch records an isolated research study for fixed-dollar GOLD scalping:

- TP5 / SL3 / 120 exact M1 minutes;
- TP7.5 / SL4 / 180 exact M1 minutes;
- TP10 / SL5 / 240 exact M1 minutes;
- desired positive-PnL win rate at least 60%;
- LightGBM LONG/SHORT models with local and higher-timeframe causal candle features;
- V19-inspired 60-day directional rank and semiannual expanding-update diagnostics.

## Decision

No corrected 2024H2 calibration threshold passed. Corrected win rates were approximately 22% to 36%, pooled PF was below 1.0 for every row and every net result was negative.

Do not start Shadow, Discord, AI discretionary judgement, MT5 orders or live trading from this study.

## Isolation

The study did not modify:

- `feature/gold-v19-wave-shadow`;
- `feature/gold-v19-challenger-c1-audit`;
- `C:\gold-v19-shadow`;
- `C:\gold-challenger-c1`;
- either local runtime state directory.

Frozen V19 scores, models, wave states, episodes, candidate rows, trades and runtime state were not used as candidate inputs. Only the known V19 normalization/update concepts were reproduced independently.

## Important incident

An early period-partition bug mixed the 2023–2024H1 training interval into the intended 2024H2 calibration interval and produced misleading interim 60% figures. Those figures and candidate files are invalid.

The corrected partition is:

- TRAIN: before 2024-07-01;
- CAL: 2024-07-01 through 2024-12-31;
- later blocks: 2025H1, 2025H2, 2026H1 and 2026JUL.

Both absolute-score and rolling-rank studies were rerun from scratch after the fix. All corrected thresholds failed.

## Authoritative read order

1. `docs/gold_scalp_ai_v1/GOLD_SCALP_AI_V1_CONSOLIDATED_RESEARCH_AUDIT_20260802.md`
2. `config/gold_scalp_ai_v1/formal_status_20260802.json`
3. `config/gold_scalp_ai_v1/period_partition_incident_20260802.json`
4. `config/gold_scalp_ai_v1/verification_20260802.json`
5. `config/gold_scalp_ai_v1/calibration_summary_20260802.csv`

## Next research boundary

Do not rescue this every-M5 classifier with post-result hour, month, volatility or side filters. Any next study must be a newly preregistered sparse event-first family and must remain research-only until fresh prospective data exists.
