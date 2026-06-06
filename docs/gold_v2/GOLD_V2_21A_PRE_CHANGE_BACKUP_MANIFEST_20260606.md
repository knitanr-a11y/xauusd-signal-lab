# GOLD V2 21A pre-change backup manifest

Date: 2026-06-06
Repo: `knitanr-a11y/xauusd-signal-lab`
Purpose: record pre-21A references before adding additional-audit planning files.

## Verified pre-21A files

| role | path | blob sha |
| --- | --- | --- |
| 20Z spec | `docs/gold_v2/GOLD_V2_20Z_SELECTED_VALUE_FINAL_AUDIT_SPEC_20260606.md` | `5a4693d0765c7705d9120716b80a418a75b8b339` |
| 20Z script | `scripts/gold_v2_runtime/audit_gold_v2_20z_selected_value_final_audit.py` | `6a363dd2f72b5145f4041456678cd668df8b1ee8` |
| 20Z BAT | `scripts/gold_v2_runtime/bat/20Z_FINAL_AUDIT.bat` | `882803903e0bc644ca62db91c78ab0b8f3aec895` |

## Boundary

21A may only plan additional audit requested by `REQUEST_MORE_AUDIT`.

21A must not execute source recovery, finalize source identity, enable live evaluator, emit final signals, send Discord, place MT5 orders, call AI APIs, or enable live hooks.
