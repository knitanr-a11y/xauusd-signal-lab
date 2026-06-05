# GOLD V2 20J pre-change backup manifest

Date: 2026-06-06
Repo: `knitanr-a11y/xauusd-signal-lab`
Purpose: backup manifest before adding 20J value capture draft load-smoke audit-only files.

## Backup policy

This 20J change set must not overwrite existing 20I or earlier files. It may only add new 20J files and this backup manifest.

GitHub commit history remains the primary rollback mechanism. This manifest records the verified pre-20J source files and blob SHAs that were read immediately before adding 20J.

## Verified pre-20J files

| role | path | observed blob sha | note |
| --- | --- | --- | --- |
| 20I spec | `docs/gold_v2/GOLD_V2_20I_VALUE_CAPTURE_DRAFT_SPEC_20260606.md` | `17b8900f5a7208b949ee918be43e0354ee480479` | 20I value-capture draft-only spec. |
| 20I script | `scripts/gold_v2_runtime/audit_gold_v2_20i_value_capture_draft.py` | `efccd4d1713d81045773918a01db96e5e0d11b0d` | 20I script. |
| 20I BAT | `scripts/gold_v2_runtime/bat/20I_VALUE_CAPTURE_DRAFT.bat` | `3dd3db336bfd3403558a5240765269000d481037` | Runs 20I only. |

## User-uploaded runtime evidence checked before 20J

20I runtime report status was:

`TIER2_SOURCE_IDENTITY_HUMAN_DECISION_VALUE_CAPTURE_DRAFT_READY_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

20I confirmed:

- draft is ready but still unset
- no actual decision value was collected
- no approval was made
- allowed value rows: 4
- required field rows: 7
- restricted draft flags: 0
- source recovery/finalization/live/final/Discord/MT5/AI/live hook all false
- next step is `20J_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_VALUE_CAPTURE_DRAFT_LOAD_SMOKE_AUDIT_ONLY`

## 20J change boundary

20J may add only:

- `docs/gold_v2/GOLD_V2_20J_VALUE_CAPTURE_DRAFT_LOAD_SMOKE_SPEC_20260606.md`
- `scripts/gold_v2_runtime/audit_gold_v2_20j_value_capture_draft_load_smoke.py`
- `scripts/gold_v2_runtime/bat/20J_VALUE_CAPTURE_DRAFT_LOAD_SMOKE.bat`

20J must not modify existing rule/source/signal/live files.

## Explicit no-change scope

20J must not change signal conditions, candidate sets, source ledger, source-of-truth status, TP/SL, entry/exit logic, live evaluator logic, Discord notification logic, MT5 order logic, or AI API logic.

## Prohibitions retained

20J must not collect a decision value, infer a decision value, approve source recovery, execute source recovery, finalize/recover source identity, promote any ledger to source-of-truth, run OHLC replay, enable live evaluator/live hook/final signal, send Discord/NO_SIGNAL Discord, place MT5 orders, or call AI APIs.
