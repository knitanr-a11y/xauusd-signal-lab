# GOLD V2 24B pre-change backup manifest

Date: 2026-06-06
Repo: `knitanr-a11y/xauusd-signal-lab`
Purpose: record pre-24B references before adding the source recovery evidence inventory audit-only step.

## Verified pre-24B files

| role | path | blob sha |
| --- | --- | --- |
| 24A pre-change manifest | `docs/gold_v2/GOLD_V2_24A_PRE_CHANGE_BACKUP_MANIFEST_20260606.md` | `ab8e7c281c8670a980289caeab3062054913eed7` |
| 24A spec | `docs/gold_v2/GOLD_V2_24A_SOURCE_RECOVERY_PRECHECK_AUDIT_SPEC_20260606.md` | `c5fd38d47d7712bbc209ad0cdcb2779cfbf210e9` |
| 24A script | `scripts/gold_v2_runtime/audit_gold_v2_24a_source_recovery_precheck.py` | `744e5a81c7e4c722af48578baa9bac18295ff1a3` |
| 24A BAT | `scripts/gold_v2_runtime/bat/24A_SOURCE_RECOVERY_PRECHECK.bat` | `a8ab3164de458b9071b88890dabaaeed97c25975` |

## Uploaded 24A output review summary

The uploaded 24A output package was checked before creating 24B.

- 24A status: `SOURCE_RECOVERY_PRECHECK_READY_AUDIT_ONLY_SOURCE_RECOVERY_EXECUTION_STILL_BLOCKED`
- 24A total STOP rows: `0`
- 24A required 23D inputs: all present
- 24A integrated checks: 14 PASS rows, 0 STOP rows
- 24A safety matrix: 26 PASS rows, 0 STOP rows
- 24A precheck matrix rows: `12`
- 24A evidence request rows: `10`
- 24A required next allowed: `24B_SOURCE_RECOVERY_EVIDENCE_INVENTORY_AUDIT_ONLY`
- Source recovery approved: `false`
- Source recovery executed: `false`
- Source identity finalization/recovery, live/final behavior, Discord, MT5, AI API, and live hook remained blocked.

## Boundary

24B must remain audit-only. It may inventory evidence availability and gaps, but it must not execute source recovery, approve source recovery, finalize identity, reconstruct from OHLC, call AI APIs, notify Discord, place MT5 orders, or enable live hooks.

Old GOLD/DISC8 remain quarantined because of suspected HTF open-time mismatch.
