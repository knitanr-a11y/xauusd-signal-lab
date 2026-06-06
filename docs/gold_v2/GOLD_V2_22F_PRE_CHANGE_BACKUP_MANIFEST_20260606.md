# GOLD V2 22F pre-change backup manifest

Date: 2026-06-06
Repo: `knitanr-a11y/xauusd-signal-lab`
Purpose: record pre-22F references before adding read-only final audit files.

## Verified pre-22F files

| role | path | blob sha |
| --- | --- | --- |
| 22E spec | `docs/gold_v2/GOLD_V2_22E_ADDITIONAL_AUDIT_READ_ONLY_SCOPE_RECONCILIATION_SPEC_20260606.md` | `e9c41f05c95247a3f3f25adbd17e4461e6b59e2e` |
| 22E script | `scripts/gold_v2_runtime/audit_gold_v2_22e_additional_audit_read_only_scope_reconciliation.py` | `575e2600ec5a5ade1e86d4269050c689333e54f2` |
| 22E BAT | `scripts/gold_v2_runtime/bat/22E_SCOPE_RECONCILE.bat` | `f864a603d9b4f221e206bb3f800e74bedbc7ade6` |

## Boundary

22F is audit-only final audit after 22E.

No live, final, external, or recovery path is enabled by this step.
