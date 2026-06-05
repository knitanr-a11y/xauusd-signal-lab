# GOLD V2 20I pre-change backup manifest

Date: 2026-06-06
Repo: `knitanr-a11y/xauusd-signal-lab`
Purpose: backup manifest before adding 20I decision value capture draft audit-only files.

## Backup policy

This 20I change set must not overwrite existing 20H or earlier files. It may only add new 20I files and this backup manifest.

GitHub commit history remains the primary rollback mechanism. This manifest records the verified pre-20I source files and blob SHAs that were read immediately before adding 20I.

## Verified pre-20I files

| role | path | observed blob sha | note |
| --- | --- | --- | --- |
| 20H spec | `docs/gold_v2/GOLD_V2_20H_VALUE_CAPTURE_AUTH_GATE_SPEC_20260606.md` | `38065d6f4e6953bea4bcdb2935f7f34d79c63db8` | 20H authorization-gate-only spec. |
| 20H script | `scripts/gold_v2_runtime/audit_gold_v2_20h_value_capture_auth_gate.py` | `a3e6090b734c29aca6ff9bd7497cff17af1d7309` | 20H script after next_gates hotfix. |
| 20H BAT | `scripts/gold_v2_runtime/bat/20H_VALUE_CAPTURE_AUTH_GATE.bat` | `89f15aeb56a6003bc8a91eb93207ca2a4d351ce6` | Runs 20H only. |

## User-uploaded runtime evidence checked before 20I

20H runtime report status was:

`TIER2_SOURCE_IDENTITY_HUMAN_DECISION_VALUE_CAPTURE_AUTHORIZATION_GATE_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

20H confirmed:

- authorization gate passed
- authorization scope was `ACTUAL_DECISION_VALUE_CAPTURE_AUDIT_ONLY_PREPARATION_ONLY`
- decision value remains `UNSET`
- no decision value collected
- no approval granted
- actual decision collection not completed
- signal conditions changed false
- source recovery/finalization/live/final/Discord/MT5/AI/live hook all false
- next step is `20I_TIER2_SOURCE_IDENTITY_HUMAN_DECISION_VALUE_CAPTURE_DRAFT_AUDIT_ONLY`

## 20I change boundary

20I may add only:

- `docs/gold_v2/GOLD_V2_20I_VALUE_CAPTURE_DRAFT_SPEC_20260606.md`
- `scripts/gold_v2_runtime/audit_gold_v2_20i_value_capture_draft.py`
- `scripts/gold_v2_runtime/bat/20I_VALUE_CAPTURE_DRAFT.bat`

20I must not modify existing rule/source/signal/live files.

## Explicit no-change scope

20I must not change:

- signal conditions
- candidate sets
- source ledger
- source-of-truth status
- TP/SL
- entry/exit logic
- live evaluator logic
- Discord notification logic
- MT5 order logic
- AI API logic

## Prohibitions retained

20I must not:

- collect a decision value
- infer a decision value
- approve source recovery
- execute source recovery
- finalize/recover source identity
- promote any ledger to source-of-truth
- run OHLC replay
- enable live evaluator/live hook/final signal
- send Discord or NO_SIGNAL Discord
- place MT5 orders
- call AI APIs

## Rollback note

Because 20I is new-file-only, rollback is simple:

1. Remove the 20I files listed above.
2. Keep or remove this manifest depending on whether audit history is desired.
3. The pre-20I 20H files remain identified by the blob SHAs in this manifest.
