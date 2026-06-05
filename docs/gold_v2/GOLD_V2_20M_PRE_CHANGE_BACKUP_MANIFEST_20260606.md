# GOLD V2 20M pre-change backup manifest

Date: 2026-06-06
Repo: `knitanr-a11y/xauusd-signal-lab`
Purpose: record pre-20M references before adding 20M audit-only files.

## Verified pre-20M files

| role | path | blob sha |
| --- | --- | --- |
| 20L spec | `docs/gold_v2/GOLD_V2_20L_VALUE_CAPTURE_DRAFT_RECON_SPEC_20260606.md` | `9eb2e3954b074c350bc3b99d5b928238169f525f` |
| 20L script | `scripts/gold_v2_runtime/audit_gold_v2_20l_value_capture_draft_recon.py` | `b60954191c22c3bae0c26f0e9fb7fd74775d0ccf` |
| 20L BAT | `scripts/gold_v2_runtime/bat/20L_VALUE_CAPTURE_DRAFT_RECON.bat` | `d2b4a60b1c90a53f085471e6c726718d0f02e723` |

## Runtime evidence summary

20L uploaded report status:

`TIER2_SOURCE_IDENTITY_HUMAN_DECISION_VALUE_CAPTURE_DRAFT_RECONCILIATION_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

20L uploaded artifacts showed STOP rows 0, decision value `UNSET`, and next gate 20M only.

## 20M boundary

20M adds only new final-audit audit-only files. It must not update existing strategy, signal, source, live, notification, order, or AI files.

20M final-audits existing audit outputs only. It does not collect a decision value and does not enable downstream action.
