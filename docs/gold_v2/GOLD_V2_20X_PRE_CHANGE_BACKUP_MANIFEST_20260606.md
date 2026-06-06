# GOLD V2 20X pre-change backup manifest

Date: 2026-06-06
Repo: `knitanr-a11y/xauusd-signal-lab`
Purpose: record pre-20X references before adding selected-value draft content-audit files.

## Verified pre-20X files

| role | path | blob sha |
| --- | --- | --- |
| 20W spec | `docs/gold_v2/GOLD_V2_20W_SELECTED_VALUE_DRAFT_LOAD_SMOKE_SPEC_20260606.md` | `29cda8a201d456d74d07d157ba2b6cbe160e7016` |
| 20W script | `scripts/gold_v2_runtime/audit_gold_v2_20w_selected_value_draft_load_smoke.py` | `319fe2d86928dcda998f79c8147d18deb9284bef` |
| 20W BAT | `scripts/gold_v2_runtime/bat/20W_DRAFT_LOAD_SMOKE.bat` | `54f7da672888a0aca7e4cd3c9dca5acd5b63b12f` |

## Boundary

20X may only content-audit the loaded 20V/20W selected-value draft for `REQUEST_MORE_AUDIT`.

20X must not execute source recovery, finalize source identity, enable live evaluator, emit final signals, send Discord, place MT5 orders, call AI APIs, or enable live hooks.
