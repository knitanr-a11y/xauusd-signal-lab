# GML1 Loss-Feature Pruning V2 Mining Specification

Date: 2026-06-28
Mode: audit-only

This file is frozen before rule-search results are calculated.

## Time contract

CSV `time` is MT5 server bar-open time. M15 decision time is bar-open plus 15 minutes. Exact M1 is mandatory and next-M1 fallback is forbidden. All rule inputs come from the closed decision bar or earlier closed bars. 2026 is excluded from rule generation, validation and subset selection.

## Hour buckets

`server_hour_bucket = floor(server_hour / 4) * 4` with six buckets: H00_03, H04_07, H08_11, H12_15, H16_19 and H20_23.

## Numeric thresholds

Candidates with at least 80 resolved rows in 2023 use candidate-specific 2023 quantiles. Smaller candidates use the matching-direction 2023 pool quantiles. Direction-pooled rules use matching-direction quantiles. Quantiles are 0.20, 0.40, 0.60 and 0.80.

## Atomic conditions

For every numeric threshold create `feature <= threshold` and `feature > threshold`. Categorical conditions use equality. An atomic condition may enter composite construction only when its 2023 scope has at least 20 hits, Strong loss rate at least 0.55, Strong PF at most 1.10 and negative total Strong R.

## Composite construction

Rules contain exactly two or three conditions on different features. A composite discovery rule requires at least 20 hits, Strong loss rate at least 0.70, Strong PF at most 0.60 and negative total Strong R in 2023. Triples extend discovery-passing pairs with one retained atom from a third feature.

Candidate-specific rules apply only to one candidate ID. Direction-pooled rules apply only to one direction. Rules with the same 2023 hit mask are deduplicated by fewer conditions, then larger support, then lexical expression. Rule IDs use the first 12 hexadecimal characters of SHA256 over scope and canonical expression.

## 2024 validation

An unchanged rule survives only with at least 12 hits, Strong loss rate at least 0.60, Strong PF at most 0.90 and negative total Strong R.

## Subset selection

Start with no exclusions. At each step test every surviving rule on 2024. Rules are combined by union. Evaluation uses cross-family deduplication followed by candidate-level one-position handling. A step is allowed only when both Strong positive rate and Strong PF strictly improve. At least 100 rows and 25 percent of the unfiltered 2024 rows must remain. Stop after 12 rules or when no eligible step exists.

The final selected rules are frozen before 2025 confirmation and the 2026 closed-bar diagnostic replay.
