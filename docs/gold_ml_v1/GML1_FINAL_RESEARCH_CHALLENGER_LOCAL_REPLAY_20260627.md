# GML1 final research challenger local replay

Date: 2026-06-27  
Mode: audit-only

## Frozen endpoint

The package reproduces the endpoint in this order:

1. `completion_challenger_v1`: A_CORE, B_STATE, P16, P18 and P19.
2. `GML1-WATCH-022-C` replaces WATCH-022-B inside A_CORE. It is not added as a parallel sleeve.
3. `GML1-WATCH-024-A` is added as the final independent SHORT sleeve.

No later candidate or rule is inserted.

## Local files

- Manifest: `config/gold_ml_v1/research_challenger/final_20260627/manifest.json`
- Frozen artifacts: `config/gold_ml_v1/research_challenger/final_20260627/artifacts/`
- Verifier: `scripts/gold_ml_v1/research_challenger/verify_final_research_challenger.py`
- Windows runner: `scripts/gold_ml_v1/research_challenger/run_verify_final_research_challenger.bat`
- Test: `tests/gold_ml_v1/test_final_research_challenger_replay.py`

Run on Windows:

```bat
scripts\gold_ml_v1\research_challenger\run_verify_final_research_challenger.bat
```

The verifier writes only to:

```text
outputs/gold_ml_v1/research_challenger_final_replay/
```

It does not change candidate definitions, train a model, generate a signal, send Discord output or place an MT5 order.

## What is verified

- Every committed input artifact has the local SHA-256 recorded in the manifest.
- The completion-stage annual and component metrics match its summary.
- All non-A_CORE rows remain unchanged when WATCH-022-C replaces WATCH-022-B.
- WATCH-022-C rows are a stricter subset of the prior WATCH-022-B A_CORE rows.
- All WATCH-022-C-stage rows remain unchanged when WATCH-024-A is added.
- WATCH-024-A portfolio rows exactly match the 2024–2026 rows of its 46-trade exact candidate registry using Base R.
- No other row is added at the final stage.
- The final annual metrics match the recorded endpoint.

Final parity target:

| Period | Trades | WR | PF | R | DD |
|---|---:|---:|---:|---:|---:|
| 2024 | 271 | 65.6827% | 2.494489 | 137.480836 | 5.907692 |
| 2025 | 402 | 59.2040% | 2.012162 | 148.092790 | 7.384615 |
| 2026 partial | 101 | 61.3861% | 1.877287 | 42.055775 | 6.799792 |

## Machine-learning lineage finding

The following existing ML work is not the ML used by this final challenger:

- `ml_synergy_result_20260626.json`: an all-valid-M15 P15/P20 search that froze zero candidates.
- the Active Event Core score-sizing result: explicitly invalidated as the wrong baseline.
- the MLR1 Meta Core: a different candidate universe and research lane.

The final challenger instead records candidate-local controls:

- eight stable compound loss-leaf rules: P16 three, P18 one and P19 four;
- a P16 validation-score lower-tail removal;
- a P19 lower validation-support boundary;
- fixed risk multipliers by component.

The loss-leaf rules and final post-filter trades are present. The candidate-local model/scaler/score artifacts and the exact P16/P19 score boundaries are not present. Therefore this package deliberately treats P16/P18/P19 as frozen `-APPROX` post-filter trade artifacts and does not retrain, infer, or substitute a different ML system.

## Source artifact corrections

The WATCH-022-C and final WATCH-024-A CSVs have blank `candidate_id` and `w` fields only for A_CORE. The source files are preserved unchanged. The verifier writes normalized derived files that fill:

```text
candidate_id = GML1-WATCH-022-C
w = 1.0
```

Several CSV byte hashes differ from older recorded hashes even though row-level transformation and performance parity pass. Both the local hashes and historical recorded hashes are retained in the manifest. No hash is silently replaced.

## Safety

`audit_only`, `model_promoted`, `shadow_ready`, `live_ready`, `final_signal`, `discord` and `mt5_order` remain disabled.
