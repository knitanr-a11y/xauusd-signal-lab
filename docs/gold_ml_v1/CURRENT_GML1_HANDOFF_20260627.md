# Current GML1 Handoff

## Critical baseline correction

The Active Event Core v1 four-channel result recorded in PR #57 is not the user-requested original-candidate baseline.

Do not use the following as the project baseline or as a completed ML-synergy result:

- Active Event Core v1 no-ML 517-trade result;
- Active Event Core v1 score-sizing result;
- `config/gold_ml_v1/gml1_active_core_no_ml_baseline_and_score_sizing_v1_20260627.json`.

Those figures describe only the later four-channel Active Event Core research layer. The user refers to the retired multi-candidate pool that existed before PR #51 removed the old candidate definitions from the current tree.

## Required recovery order

1. Recover the retired candidate IDs, definitions, proposal registry and label join from Git history.
2. Determine which retired pool is the actual original baseline; do not infer this from approximate candidate count alone.
3. Reproduce its no-ML OOS result with the original deduplication, conflict and one-position contract.
4. Freeze candidate count, IDs, SHA, trades, annualized trades, WR, Strong/Extreme PF and R, DD, fold, direction and candidate breakdown.
5. Only then compare ML filtering, ML sizing or new candidate families against that baseline.

No further candidate or ML result may be called an improvement until this recovery is complete.

## Confirmed historical pools under review

Git history currently shows at least:

- MLR1 ML-05A/05B: 12 candidate IDs across six families, 4,263 raw events;
- MLR2 v1: 10 candidate IDs across five families, 3,156 raw proposals;
- later Active Event Core v1: four event channels, which is not the requested original pool.

The first two remain historical audit objects only until the exact user-referenced original pool is established.

## Time and safety contracts

CSV `time` is bar-open time. M15 decision is open plus 15 minutes. Entry requires an exact M1 open. Higher-timeframe bars must be closed. Audit-only remains active. No model, shadow, live, Discord or MT5 output is enabled.
