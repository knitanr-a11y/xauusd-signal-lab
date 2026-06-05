# GOLD V2 20K pre-change backup manifest

Date: 2026-06-06
Repo: `knitanr-a11y/xauusd-signal-lab`
Purpose: record pre-20K references before adding 20K audit-only files.

## Verified pre-20K files

| role | path | blob sha |
| --- | --- | --- |
| 20J spec | `docs/gold_v2/GOLD_V2_20J_VALUE_CAPTURE_DRAFT_LOAD_SMOKE_SPEC_20260606.md` | `a9414a0af26abd0c239052a018213fc2caf3df28` |
| 20J script | `scripts/gold_v2_runtime/audit_gold_v2_20j_value_capture_draft_load_smoke.py` | `d8a9baf879729e9acb89e65a121f9051699790b6` |
| 20J BAT | `scripts/gold_v2_runtime/bat/20J_VALUE_CAPTURE_DRAFT_LOAD_SMOKE.bat` | `a2886f7dc4f41e4d4dd0ba0ac95182c6506b0242` |

## Runtime evidence summary

20J uploaded report status:

`TIER2_SOURCE_IDENTITY_HUMAN_DECISION_VALUE_CAPTURE_DRAFT_LOAD_SMOKE_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

20J uploaded artifacts showed STOP rows 0, decision value `UNSET`, allowed values 4, required fields 7, and restricted flags 0.

## 20K boundary

20K adds only new 20K audit-only files. It must not update existing strategy, signal, source, live, notification, order, or AI files.

20K is draft content audit only. It does not collect a decision value and does not enable downstream action.
