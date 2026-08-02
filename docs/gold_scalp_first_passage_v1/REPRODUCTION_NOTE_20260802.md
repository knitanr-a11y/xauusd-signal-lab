# GOLD SCALP FIRST-PASSAGE V1 — Reproduction Note

Date: 2026-08-02

## Retrospective source data

The research used the retained GOLD candle CSVs covering 2023-01-03 through 2026-07-31. No external market data, tick order book, V19 runtime output or Challenger C1 runtime state was used as a candidate input.

## Main scripts in the downloadable result package

- `gold_scalp_first_passage_v1.py`
- `gold_scalp_first_passage_specialists_v1.py`
- `gold_scalp_first_passage_hazard_v1.py`

The package also contains the frozen preregistration, compute amendment, pseudo-forward block choices, specialist trades and metrics, hazard results, observation catalog and SHA256 manifest.

## Result package

File:

`GOLD_SCALP_FIRST_PASSAGE_V1_RESULT_20260802.zip`

SHA256:

`c048fbccd3be594640e1bfb54f5745b7ce9a462a910f3aea795611aa52262a6f`

## Execution contract

- MT5 broker-server naive time;
- closed candle rows only;
- exact M1 entry and outcome resolution;
- spread 0.30 USD once;
- recorded entry spread gate 30 points where applicable;
- protective stop first for same-M1 ambiguity;
- one-position non-overlap;
- SL no greater than 5 USD;
- TP no lower than 5 USD;
- breakeven allowed.

## Audit warning

This is retrospective exploratory research. Historical periods have now been examined repeatedly. Observation catalog entries cannot be treated as untouched validation or deployed candidates.

No Shadow, Discord notifier, MT5 order path, live trading, promotion or merge is authorized.