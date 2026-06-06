# GOLD V2 20Z pre-change backup manifest

Date: 2026-06-06
Repo: `knitanr-a11y/xauusd-signal-lab`
Purpose: record pre-20Z references before adding selected-value final audit files.

## Verified pre-20Z files

| role | path | blob sha |
| --- | --- | --- |
| 20Y spec | `docs/gold_v2/GOLD_V2_20Y_SELECTED_VALUE_DRAFT_RECONCILIATION_SPEC_20260606.md` | `f823858d5dcbd26d2083d7377719fafa5786aa67` |
| 20Y script | `scripts/gold_v2_runtime/audit_gold_v2_20y_selected_value_draft_reconciliation.py` | `39cb2c2007dd8ec6a4c8a707889f88981104280b` |
| 20Y BAT | `scripts/gold_v2_runtime/bat/20Y_RECONCILIATION.bat` | `48a6957565d6bc727ed05623dfdc39199011dec2` |

## Boundary

20Z may only final-audit the reconciled `REQUEST_MORE_AUDIT` selected-value chain.

20Z must not execute source recovery, finalize source identity, enable live evaluator, emit final signals, send Discord, place MT5 orders, call AI APIs, or enable live hooks.
