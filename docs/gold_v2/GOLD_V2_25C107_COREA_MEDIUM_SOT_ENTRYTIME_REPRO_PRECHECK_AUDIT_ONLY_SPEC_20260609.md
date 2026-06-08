# GOLD V2 25C107 CoreA/MEDIUM SOT entry-time reproducibility precheck audit-only spec

Created: 2026-06-09

Status: `COREA_MEDIUM_SOT_ENTRYTIME_REPRO_PRECHECK_SPEC_READY_AUDIT_ONLY`

## Purpose

25C105/25C106 showed broad and scoped risk markers for CoreA/MEDIUM, but they were still text/token triage and included audit docs and safety wording.

25C107 is a fast artifact-level precheck. It scans actual GOLD V2 CSV/JSON artifacts, focusing on CoreA/MEDIUM SOT, selected rows, source rows, final rows, and arbitration files. It does not replay OHLC and does not implement live logic.

The goal is to answer quickly:

```text
Do CoreA/MEDIUM SOT/final/selected artifacts visibly depend on post-entry outcome/profit/final-arbitration columns?
Can they plausibly be reproduced from entry-time features only without a deeper replay?
```

This is audit-only and cannot approve source recovery.

## Candidate artifact scope

Scan local repository and `Files/FX_OUTPUTS` for `.csv` and `.json` files whose paths contain GOLD V2 and at least one of:

```text
corea, core_a, medium, arbitration, final_sot, selected_source_rows, source_rows, frozen_core, live_evaluator_mapping
```

Exclude:

```text
docs
bat
__pycache__
25c105
25c106
```

## Artifact roles

Classify each candidate file into one or more roles:

```text
corea_source_or_selected
corea_mapping_or_frozen
medium_source_or_selected
medium_final_sot
medium_arbitration
medium_mapping_or_frozen
unknown_gold_v2_artifact
```

## Column/key risk scan

For CSV columns and JSON flattened keys, classify tokens:

Hard future/outcome columns:

```text
exit_time, exit_price, close_time, close_price, outcome, result, win, loss, tp_hit, sl_hit, hit, mae, mfe, duration, holding, realized
```

Profit/representative columns:

```text
profit, profit_r, selected_profit, selected_profit_r, top_profit, pnl, best_profit, max_profit, min_profit, representative_profit
```

Selection/arbitration columns:

```text
selected, top_candidate, top_variant, top_direction, best, rank, sort, argmax, argmin, arbitration, final_sot, priority, chosen, prefer
```

Entry-time candidate columns:

```text
entry_time, top_entry_time, direction, side, strategy_id, dataset, regime, range, ret, trend, tr_mean, count, feature, condition, filter, score
```

## Risk interpretation

- SOT/final/selected artifacts with hard future/outcome columns are `HIGH_RISK_REPLAY_REQUIRED`.
- SOT/final/selected artifacts with profit/representative columns are `HIGH_RISK_PROFIT_BINDING_REVIEW` unless clearly labelled historical outcome only.
- MEDIUM arbitration/final SOT artifacts with profit/selected_profit/top_candidate columns are `HIGH_RISK_ARBITRATION_REVIEW`.
- Mapping/frozen JSON with only condition definitions and safety flags is `LOWER_RISK_BUT_REPLAY_REQUIRED`.
- Absence of risky columns does not approve source recovery.

## Outputs

Write to:

```text
Files/FX_OUTPUTS/gold_v2_25c107_corea_medium_sot_entrytime_repro_precheck_audit_only
```

Output files:

```text
GOLD_V2_25C107_COREA_MEDIUM_SOT_ENTRYTIME_REPRO_PRECHECK_AUDIT_ONLY_REPORT.md
25c107_summary.json
25c107_artifact_inventory.csv
25c107_column_key_risk_rows.csv
25c107_component_artifact_risk_summary.csv
25c107_decision_matrix.csv
25c107_blocker_matrix.csv
```

A zip package may also be written to:

```text
Files/FX_OUTPUTS/gold_v2_25c107_corea_medium_sot_entrytime_repro_precheck_audit_only.zip
```

## Status names

If no candidate artifact files are found:

```text
COREA_MEDIUM_SOT_PRECHECK_NO_ARTIFACTS_FOUND_AUDIT_ONLY_LIVE_BLOCKED
```

If CoreA or MEDIUM SOT/final/selected/arbitration artifacts contain hard future/profit/selection risk columns:

```text
COREA_MEDIUM_SOT_PRECHECK_RISK_FOUND_AUDIT_ONLY_LIVE_BLOCKED
```

If only mapping/frozen files are found and no obvious risky columns appear:

```text
COREA_MEDIUM_SOT_PRECHECK_NO_OBVIOUS_ARTIFACT_RISK_AUDIT_ONLY_LIVE_BLOCKED
```

Even no-obvious-risk remains audit-only and live blocked.

## Guardrails

- GOLD V2 remains audit-only.
- `REQUEST_MORE_AUDIT` is not source recovery approval.
- Old GOLD/DISC8 remains quarantined due suspected HTF open-time mismatch.
- Approximate reimplementation is prohibited.
- A002 is auxiliary-only and must not be used for CoreB/CoreA/MEDIUM metrics.
- No Discord, MT5, AI API, live hook, live evaluator, or final signal.
- Do not infer source recovery from artifact-column inspection alone.
