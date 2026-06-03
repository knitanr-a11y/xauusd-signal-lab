# GOLD V2 Phase3 rule-rubric OOS validation

Created: 2026-06-03
Status: audit-only / not runtime approved

## API use

No API is required for this validation.

Phase3 is no longer an AI free-judgement test. It is a deterministic numeric rule table. Therefore it should be evaluated directly in code.

AI may later be used only as a rule-applier/explainer, not as the source of the decision.

## Validation A: earlier separate period

Dataset:

```text
WF_REBUILD_TOP2_PER_ORIGIN
fold_id = 1
period = TRAIN
months = 2025-12 to 2026-02
rows = 271
```

This is a separate earlier period from the Phase2 174-row audit window.

| Policy | Count | Win rate | PF | TotalR | Worst | MaxDD | Max loss streak |
|---|---:|---:|---:|---:|---:|---:|---:|
| representative | 271 | 72.69% | 3.39 | +177.0R | -1.0R | 5.0R | 5 |
| CAP3 fixed | 271 | 73.80% | 4.71 | +319.0R | -3.0R | 7.0R | 5 |
| uncapped fixed | 271 | 73.43% | 5.28 | +394.0R | -8.0R | 8.0R | 5 |
| Phase3 rubric | 271 | 73.43% | 5.07 | +370.0R | -8.0R | 8.0R | 5 |

## Monthly detail for earlier separate period

| Month | Policy | Count | Win rate | PF | TotalR | Worst | MaxDD |
|---|---|---:|---:|---:|---:|---:|---:|
| 2025-12 | CAP3 fixed | 11 | 81.82% | 9.50 | +17.0R | -1.0R | 1.0R |
| 2025-12 | uncapped fixed | 11 | 81.82% | 11.00 | +20.0R | -1.0R | 1.0R |
| 2025-12 | Phase3 rubric | 11 | 81.82% | 10.00 | +18.0R | -1.0R | 1.0R |
| 2026-01 | CAP3 fixed | 138 | 75.36% | 4.73 | +175.5R | -3.0R | 7.0R |
| 2026-01 | uncapped fixed | 138 | 74.64% | 5.05 | +214.5R | -8.0R | 8.0R |
| 2026-01 | Phase3 rubric | 138 | 74.64% | 4.70 | +192.5R | -8.0R | 8.0R |
| 2026-02 | CAP3 fixed | 122 | 71.31% | 4.42 | +126.5R | -2.0R | 7.0R |
| 2026-02 | uncapped fixed | 122 | 71.31% | 5.31 | +159.5R | -2.0R | 7.0R |
| 2026-02 | Phase3 rubric | 122 | 71.31% | 5.31 | +159.5R | -2.0R | 7.0R |

## Interpretation

The Phase3 rubric does not beat uncapped TotalR on the earlier separate period.

However, it still beats fixed CAP3:

```text
Phase3 rubric: +370.0R / PF 5.07
CAP3 fixed:    +319.0R / PF 4.71
```

Therefore, the rubric is not pure overfit garbage, but the very strong +285.5R from the Phase2 174-row audit is likely optimistic.

## Validation B: unused rows in same calendar test period

This is not a true separate-period test, but it checks unused TOP2 test clusters that were not part of the Phase2 174-row audit.

Rows:

```text
207
```

| Policy | Count | Win rate | PF | TotalR | Worst | MaxDD | Max loss streak |
|---|---:|---:|---:|---:|---:|---:|---:|
| representative | 207 | 55.07% | 1.44 | +40.5R | -1.0R | 8.0R | 6 |
| CAP3 fixed | 207 | 55.07% | 1.37 | +43.5R | -3.0R | 11.0R | 6 |
| uncapped fixed | 207 | 55.07% | 1.36 | +49.0R | -10.0R | 17.0R | 6 |
| Phase3 rubric | 207 | 55.07% | 1.37 | +45.5R | -5.0R | 11.0R | 6 |

The rubric reduces tail risk versus uncapped but does not materially improve PF on this unused same-period set.

## Final judgement

```text
API is not needed for this rubric.
The rule can be evaluated directly.
The rubric is promising but not runtime-approved.
It should be converted to deterministic code and tested with proper walk-forward threshold selection.
```

Current recommendation:

```text
Do not use AI free judgement.
Do not use the Phase3 thresholds as live-final yet.
Use Phase3 rubric as a candidate for deterministic WF validation.
Fixed CAP3 remains the safer baseline.
```
