# Challenger C1 research path configuration

The research code is not a runtime and does not touch the running V19 clone.

Set these variables in the separate research clone before reproduction:

```bat
set GOLD_C1_SOURCE_ROOT=C:\path\to\data_v3_sources
set GOLD_C1_RESEARCH_ROOT=C:\gold-challenger-c1\research_output
set GOLD_C1_V10_REFERENCE=C:\path\to\V10_E40_signal_ledger.csv.gz
set GOLD_C1_V19_REFERENCE_ROOT=C:\path\to\GOLD_FIRST_P90_IMPULSE_EARLY_EPISODE_ROBUSTNESS_V19_20260801
set PYTHONPATH=scripts
```

Required files under `GOLD_C1_SOURCE_ROOT` and `GOLD_C1_RESEARCH_ROOT` must match `config/gold_challenger_c1/source_manifest.json` and its derived-source hashes.

Commands:

```bat
python -m compileall scripts\gold_challenger_c1
python -m pytest -q tests\gold_challenger_c1
python -m gold_challenger_c1.run_reproduction
python -m gold_challenger_c1.run_robustness
```

`run_robustness` is a path-configuration wrapper around the frozen audited robustness implementation. It does not alter candidate conditions or results.
