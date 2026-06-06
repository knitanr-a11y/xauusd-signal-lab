# GOLD V2 21B pre-change backup manifest

Date: 2026-06-06
Repo: `knitanr-a11y/xauusd-signal-lab`
Purpose: record pre-21B references before adding additional audit draft files.

## Verified pre-21B files

| role | path | blob sha |
| --- | --- | --- |
| 21A spec | `docs/gold_v2/GOLD_V2_21A_ADDITIONAL_AUDIT_PLANNING_SPEC_20260606.md` | `75af1f12b8a0225f5f2591e3550cd52e164efcfd` |
| 21A script | `scripts/gold_v2_runtime/audit_gold_v2_21a_additional_audit_planning.py` | `de9d20f8b7821951c36ea84477dd5fcb546378ad` |
| 21A BAT | `scripts/gold_v2_runtime/bat/21A_ADDITIONAL_AUDIT_PLANNING.bat` | `bb2d5e1cdef5d3f40f7bffd02278a3c987c92a8c` |

## Boundary

21B may only create a read-only additional audit draft from the 21A plan.

21B must not perform source recovery, finalize source identity, enable live evaluator, emit final signals, send Discord, place MT5 orders, call AI APIs, or enable live hooks.
