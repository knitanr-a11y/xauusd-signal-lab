# BLOCKED REPORT — GOLD CHALLENGER C1 V2 DATA V3

Status: `RETROSPECTIVE_STRUCTURAL_ROBUSTNESS_FAILED`

The DATA_V3 candidate is research-only and is blocked from Shadow/runtime work.

First old-reference difference: `2024-07-02 01:15:00`, classified `DATA_VERSION_MISMATCH`. This is expected because the original `(2)` sources are unavailable.

Formal robustness failure: combined PF `1.977299391769` is below the preregistered minimum `1.979956319572` by `0.002656927803`.

No rescue adjustment is authorized. V19 is unchanged.

## Reproduction commands

Configure the four research paths described in `RESEARCH_PATH_CONFIGURATION.md`, then run:

```bat
python -m compileall scripts\gold_challenger_c1
set PYTHONPATH=scripts
python -m pytest -q tests\gold_challenger_c1
python -m gold_challenger_c1.run_reproduction
python -m gold_challenger_c1.run_robustness
```

These are research commands only. No BAT runtime, Shadow, Discord, AI, live CSV monitor, local state root, or MT5 order implementation exists in this branch.
