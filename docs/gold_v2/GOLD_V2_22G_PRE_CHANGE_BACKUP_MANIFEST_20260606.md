# GOLD V2 22G pre-change backup manifest

Date: 2026-06-06
Repo: `knitanr-a11y/xauusd-signal-lab`
Purpose: record pre-22G references before adding final read-only handoff files.

## Verified pre-22G files

| role | path | blob sha |
| --- | --- | --- |
| 22F spec | `docs/gold_v2/GOLD_V2_22F_ADDITIONAL_AUDIT_READ_ONLY_FINAL_AUDIT_SPEC_20260606.md` | `4cb4eeebbf19e78f0f6200c030aa7a59e5ede260` |
| 22F script | `scripts/gold_v2_runtime/audit_gold_v2_22f_additional_audit_read_only_final_audit.py` | `522e4061b3086e6ec0425721095f90abd30d663d` |
| 22F BAT | `scripts/gold_v2_runtime/bat/22F_FINAL_AUDIT.bat` | `d880398ae5ecc7b34f0133da0262db78a115b760` |

## Boundary

22G is audit-only final handoff after 22F.

No live, final, external, or recovery path is enabled by this step.
