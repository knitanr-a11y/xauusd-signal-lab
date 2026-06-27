# GML1 final research challenger local replay

Date: 2026-06-27  
Mode: audit-only

## Frozen endpoint

This package reproduces exactly this endpoint:

1. `completion_challenger_v1`: A_CORE, B_STATE, P16, P18 and P19.
2. `GML1-WATCH-022-C` replaces WATCH-022-B inside A_CORE. It is not a parallel sleeve.
3. `GML1-WATCH-024-A` is added as the final independent SHORT sleeve.

No later candidate or rule is inserted. Historical documents may explain lineage but may not override the uploaded final artifacts.

## Installation and run

The separately delivered local audit ZIP contains the verifier and all 15 frozen source artifacts. Extract it at the repository root, then run:

```bat
scripts\gold_ml_v1\research_challenger\run_verify_final_research_challenger.bat
```

Outputs are written only to:

```text
outputs/gold_ml_v1/research_challenger_final_replay/
```

The verifier is fail-closed: missing files, hash differences, row differences, unexpected sleeve changes or performance differences return a non-zero exit code.

## Verified transformations

- Completion-stage annual and component metrics match the frozen summary.
- Non-A_CORE rows do not change during WATCH-022-C replacement.
- WATCH-022-C is a stricter subset of the previous WATCH-022-B A_CORE rows.
- WATCH-022-C-stage rows are preserved when WATCH-024-A is added.
- WATCH-024-A additions match its exact candidate registry using Base R.
- No other final-stage rows are introduced.

| Period | Trades | WR | PF | R | DD |
|---|---:|---:|---:|---:|---:|
| 2024 | 271 | 65.6827% | 2.494489 | 137.480836 | 5.907692 |
| 2025 | 402 | 59.2040% | 2.012162 | 148.092790 | 7.384615 |
| 2026 partial | 101 | 61.3861% | 1.877287 | 42.055775 | 6.799792 |

## Machine-learning lineage audit

The final challenger does **not** use the all-M15 `ml_synergy_result_20260626`, the invalidated Active Event Core score-sizing baseline, or the separate MLR1 Meta Core lane.

The frozen final artifacts reflect candidate-local controls:

- stable loss-leaf rules: P16 three, P18 one, P19 four;
- P16 validation-score lower-tail removal;
- P19 validation-support lower boundary;
- fixed sleeve risk multipliers.

The candidate-local model/scaler/score artifacts and exact P16/P19 score boundaries were not recovered. Therefore P16/P18/P19 remain frozen `-APPROX` post-filter trade artifacts. This implementation does not retrain them, invent missing thresholds or substitute another ML system.

## Source preservation

The WATCH-022-C and WATCH-024-A portfolio CSVs omit `candidate_id` and `w` only for A_CORE. Source artifacts remain unchanged. Normalized output fills only:

```text
candidate_id = GML1-WATCH-022-C
w = 1.0
```

Older recorded byte hashes differ for several CSV files, while row-level stage transformations and performance parity pass. Both local and historical hashes are retained in the local audit package; no hash is silently rewritten.

## Safety

`audit_only`, `model_promoted`, `shadow_ready`, `live_ready`, `final_signal`, `discord` and `mt5_order` remain disabled.
