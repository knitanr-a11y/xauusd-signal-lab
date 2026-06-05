# GOLD V2 20L pre-change backup manifest

Date: 2026-06-06
Repo: `knitanr-a11y/xauusd-signal-lab`
Purpose: record pre-20L references before adding 20L audit-only files.

## Verified pre-20L files

| role | path | blob sha |
| --- | --- | --- |
| 20K spec | `docs/gold_v2/GOLD_V2_20K_VALUE_CAPTURE_DRAFT_CONTENT_AUDIT_SPEC_20260606.md` | `5e74d9e68dbcc15337920c9c2f1e4df3ee4adc34` |
| 20K script | `scripts/gold_v2_runtime/audit_gold_v2_20k_value_capture_draft_content_audit.py` | `b6f4d38f3cfe03716f61d7b1a243d029a8df60f8` |
| 20K BAT | `scripts/gold_v2_runtime/bat/20K_VALUE_CAPTURE_DRAFT_CONTENT_AUDIT.bat` | `48396150907a73230f8cc4d8ac591582e299fb05` |

## Runtime evidence summary

20K uploaded report status:

`TIER2_SOURCE_IDENTITY_HUMAN_DECISION_VALUE_CAPTURE_DRAFT_CONTENT_AUDIT_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

20K uploaded artifacts showed STOP rows 0, decision value `UNSET`, allowed audit failed rows 0, field audit failed rows 0, and restricted flags 0.

## 20L boundary

20L adds only new 20L reconciliation audit-only files. It must not update existing strategy, signal, source, live, notification, order, or AI files.

20L reconciles existing audit outputs only. It does not collect a decision value and does not enable downstream action.
