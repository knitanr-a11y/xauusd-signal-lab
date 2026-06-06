# GOLD V2 24A pre-change backup manifest

Date: 2026-06-06
Repo: `knitanr-a11y/xauusd-signal-lab`
Purpose: record pre-24A references before adding the source recovery precheck audit-only step.

## Verified pre-24A files

| role | path | blob sha |
| --- | --- | --- |
| 23D pre-change manifest | `docs/gold_v2/GOLD_V2_23D_PRE_CHANGE_BACKUP_MANIFEST_20260606.md` | `5b35403033afcd849e11a853d8a96d68bb94361c` |
| 23D spec | `docs/gold_v2/GOLD_V2_23D_REQUEST_MORE_AUDIT_DECISION_ROUTING_AUDIT_SPEC_20260606.md` | `192bb03721632e1e567b9505aa5088c291107180` |
| 23D script | `scripts/gold_v2_runtime/audit_gold_v2_23d_request_more_audit_decision_routing.py` | `4f670c2886620886ef7cbd104385a7b51c5827d0` |
| 23D BAT | `scripts/gold_v2_runtime/bat/23D_DECISION_ROUTING.bat` | `e01208014773b8a3f13fd30227cb554deeb5ffae` |

## Uploaded 23D output review summary

The uploaded 23D output package was checked before creating 24A.

- 23D status: `REQUEST_MORE_AUDIT_DECISION_ROUTED_TO_SOURCE_RECOVERY_PRECHECK_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`
- 23D total STOP rows: `0`
- 23D validated decision value: `REQUEST_SOURCE_RECOVERY_PRECHECK_AUDIT_ONLY`
- 23D route target: `24A_SOURCE_RECOVERY_PRECHECK_AUDIT_ONLY`
- 23D route target allowed: `true`
- Source recovery approved: `false`
- Source recovery executed: `false`
- Source identity finalization/recovery, live/final behavior, Discord, MT5, AI API, and live hook remained blocked.

## Boundary

24A must remain audit-only. It may inventory prerequisites, evidence, blockers, and future approval values for source recovery, but it must not execute, approve, prepare execution, or finalize any source recovery or source identity path.

Old GOLD/DISC8 remain quarantined because of suspected HTF open-time mismatch.
