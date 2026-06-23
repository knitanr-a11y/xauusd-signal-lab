# Stage289 exact model directory

This directory is local runtime state and is not a model-download or fallback location.

## Stage281

`gold_v3_301_prepare_exact_models.py` may reproduce and save Stage281 locally because its threshold and fixture score match exactly from the audited closed history.

Generated Stage281 files:

- `stage281_med4h_cont_long_2026_model.txt`
- `stage281_med4h_cont_long_2026_contract.json`

## Stage280

Stage280 must **not** be reconstructed approximately. The original PR6 committed aggregate audit outputs but did not commit the original training source, model artifact, workflow artifact, or model parameters. Stage300 evaluated 335 reconstruction variants and found zero exact matches.

Stage280 is accepted only when both files are present:

- `stage280_rev_long_2026_model.txt`
- `stage280_rev_long_2026_contract.json`

The Stage280 contract must include:

- the exact model SHA-256;
- `score_threshold = 0.5927349103795366`;
- `fixture_time = 2026-06-19 08:00:00`;
- `fixture_score = 0.5949591748604749`;
- verified source provenance identifying an original artifact or exact training reproduction.

Until then, the formal state is `BLOCKED_STAGE280_EXACT_SOURCE_MISSING`.

Substitute models, threshold relaxation, candidate removal, and fallback thresholds are prohibited. Final signal, MT5 order, Discord notification, and partial close remain disabled.
