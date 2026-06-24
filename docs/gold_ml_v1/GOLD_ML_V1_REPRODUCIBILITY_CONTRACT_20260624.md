# GOLD ML V1 — Local Reproducibility Contract

Date: 2026-06-24  
Status: `LOCAL_REPRODUCIBILITY_REQUIRED`

Any exploration performed outside the user's PC is provisional until the same result is reproduced on the user's local Windows environment.

## Required local package for every search or candidate

Each search stage must provide:

- a one-click Windows BAT runner;
- a Python entrypoint;
- frozen JSON configuration;
- dependency lock information;
- SHA256 manifest for all input candle files;
- Git commit SHA;
- all random seeds;
- environment report;
- complete attempt log, including failed trials;
- exact candidate trade registry;
- metrics recalculated from that registry;
- SHA256 manifest for generated outputs.

## Determinism rules

- Python, NumPy, and PyTorch seeds are fixed and recorded.
- CUDA deterministic settings are enabled where supported.
- Stable sorting and explicit tie-break rules are mandatory.
- Decisions must not depend on unordered iteration.
- Parallel nondeterminism must be disabled or explicitly documented.
- Same-bar TP/SL, duplicate signals, simultaneous candidates, and threshold ties must have frozen deterministic rules.

## Data identity

The local program must hash and inspect the actual files in `MQL5\Files` before running.

It must stop when:

- an expected input file is missing;
- a SHA, schema, or overlap contract fails;
- timestamps are duplicated or out of order;
- higher-timeframe data would be used before its close time.

The latest row is retained because the user confirmed it is closed. Its availability time is `time + timeframe duration`.

## Result identity

The primary reproducibility object is the exact trade registry, not a summary percentage.

A local replay must match:

- candidate ID;
- selected timestamps;
- direction;
- entry, TP, SL, and exit values;
- outcome;
- trade count;
- trade-registry hash;
- metrics recalculated from those trades.

When identical binary model hashes cannot be guaranteed across CPU and GPU libraries, the frozen prediction-vector hash and final trade-registry hash must match instead.

## Acceptance gate

A result found by the assistant is reported as provisional until local replay passes.

No candidate may be registered, promoted, or added to a portfolio before the local replay report confirms parity.

The local replay program and configuration must be committed to GitHub before the user is asked to run it.

Machine-readable contract:

`config/gold_ml_v1/reproducibility_contract_20260624.json`
