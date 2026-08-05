# BTC AI V1 — OHLC Anchor-Age Path-Shape Reproducibility Manifest

Date: 2026-08-03

## Conversation artifact

- package: `BTC_AI_V1_OHLC_ANCHOR_AGE_PATH_SHAPE_RESEARCH_20260803.zip`
- SHA256: `f53707cb09eb6656075d788d8dcc920084b666a1dd982a4bd158e0f87c135f35`
- files: 116
- compressed size: approximately 51 MB
- ZIP expansion test: passed

Raw XM candles, GOLD files and external-market data are not included.

## Included

- stage contract summary and links to all authoritative GitHub contracts/addenda;
- preparation and accepted LightGBM training scripts;
- prerequisite state-feature and anchor-generation code;
- accepted model text files for four folds and four targets;
- baseline and residual NPZ predictions;
- all accepted fold metrics;
- full direction cross-fit predictions and selected P90 rows;
- monthly, half-year, D1, family, subtype and age decompositions;
- feature importance;
- formal Markdown and JSON results;
- invalidated wrappers and an explicit explanation of why they must not be used;
- reproduction instructions and SHA256SUMS.

## Accepted-result boundary

Only the rerun using zero-origin MFE/MAE and LightGBM `bagging_freq=1` is authoritative. The initial negative-excursion dry run, initial no-bagging fold results and incomplete large-CSV aggregator are invalid.

Formal supported candidates: **0**. Candidate PnL and 2026 were not opened.