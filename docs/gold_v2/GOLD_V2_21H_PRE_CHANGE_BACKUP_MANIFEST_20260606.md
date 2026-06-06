# GOLD V2 21H pre-change backup manifest

Date: 2026-06-06
Repo: `knitanr-a11y/xauusd-signal-lab`
Purpose: record pre-21H references before adding audit-only handoff files.

## Verified pre-21H files

| role | path | blob sha |
| --- | --- | --- |
| 21G spec | `docs/gold_v2/GOLD_V2_21G_ADDITIONAL_AUDIT_READ_ONLY_REPORT_SPEC_20260606.md` | `a0e1372c326d93192cbb7277f1b9a980830681fc` |
| 21G script | `scripts/gold_v2_runtime/audit_gold_v2_21g_additional_audit_read_only_report.py` | `28edbd893a3b86e1ba4fc3b41ec265d12ae5558d` |
| 21G BAT | `scripts/gold_v2_runtime/bat/21G_READ_ONLY_REPORT.bat` | `b01e4c1aafb0cbffec26e4b65e6793dfe753d03f` |

## Boundary

21H is audit-only handoff after 21G.

No live, final, external, or recovery path is enabled by this step.
