# GOLD V2 20V pre-change backup manifest

Date: 2026-06-06
Repo: `knitanr-a11y/xauusd-signal-lab`
Purpose: record pre-20V references before adding the selected-value draft audit-only files.

## Verified pre-20V files

| role | path | blob sha |
| --- | --- | --- |
| 20U spec | `docs/gold_v2/GOLD_V2_20U_VALUE_SELECTION_INTAKE_GATE_SPEC_20260606.md` | `3c8c4f303b5e270241b868526813d5ce5a9ce762` |
| 20U script | `scripts/gold_v2_runtime/audit_gold_v2_20u_value_selection_intake_gate.py` | `53259a3123132fea418c9e0df44feddcf96e6b76` |
| 20U BAT | `scripts/gold_v2_runtime/bat/20U_VALUE_SELECTION_GATE.bat` | `a6f2c51ce4e610b63c40ddd312cd4be9b406e5ed` |

## Human selected value for 20V draft

Operator selected:

`REQUEST_MORE_AUDIT`

Meaning: request additional audit; do not approve source recovery.

## Boundary

20V may create a selected-value draft record for `REQUEST_MORE_AUDIT` only.

20V must not execute source recovery, finalize source identity, enable live evaluator, emit final signals, send Discord, place MT5 orders, call AI APIs, or enable live hooks.
