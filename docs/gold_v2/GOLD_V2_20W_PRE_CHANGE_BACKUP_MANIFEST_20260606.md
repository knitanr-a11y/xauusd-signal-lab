# GOLD V2 20W pre-change backup manifest

Date: 2026-06-06
Repo: `knitanr-a11y/xauusd-signal-lab`
Purpose: record pre-20W references before adding selected-value draft load-smoke audit-only files.

## Verified pre-20W files

| role | path | blob sha |
| --- | --- | --- |
| 20V spec | `docs/gold_v2/GOLD_V2_20V_SELECTED_VALUE_DRAFT_SPEC_20260606.md` | `5bb86dfb78363baf1868dad95f6a4d27c992fec1` |
| 20V script | `scripts/gold_v2_runtime/audit_gold_v2_20v_selected_value_draft.py` | `f7a82e24823b87f66ed989315e65f8f5eb22a3bc` |
| 20V BAT | `scripts/gold_v2_runtime/bat/20V_SELECTED_VALUE_DRAFT.bat` | `f77110548538667f8cbf32c6143eb15e7e10c49d` |

## Boundary

20W may only load-smoke the 20V selected-value draft for `REQUEST_MORE_AUDIT`.

20W must not execute source recovery, finalize source identity, enable live evaluator, emit final signals, send Discord, place MT5 orders, call AI APIs, or enable live hooks.
