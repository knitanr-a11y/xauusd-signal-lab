# GOLD V2 20H pre-change backup manifest

Date: 2026-06-06
Repo: `knitanr-a11y/xauusd-signal-lab`
Purpose: backup manifest before adding 20H authorization-gate audit-only files.

## Backup policy

This 20H change set must not overwrite existing 20G or earlier files. It may only add new 20H files and this backup manifest.

GitHub commit history remains the primary rollback mechanism. This manifest records the verified pre-20H source files and blob SHAs that were read immediately before adding 20H.

## Verified pre-20H files

| role | path | observed blob sha | note |
| --- | --- | --- | --- |
| 20G spec | `docs/gold_v2/GOLD_V2_20G_DRAFT_FINAL_HANDOFF_SPEC_20260606.md` | `09b569509b530443671601ce32f5fe1ab632a0a7` | 20G handoff-only spec; no decision collection. |
| 20G script | `scripts/gold_v2_runtime/audit_gold_v2_20g_draft_final_handoff.py` | `52bc1da7cfc6931824f64358e84479c6bde8850f` | 20G handoff-only implementation. |
| 20G BAT | `scripts/gold_v2_runtime/bat/20G_DRAFT_FINAL_HANDOFF.bat` | `70c7348ef2f424e13e6d47f01b783722bcf1f09e` | Runs 20G only. |

## User-uploaded runtime evidence checked before 20H

20G runtime report status was:

`TIER2_SOURCE_IDENTITY_HUMAN_DECISION_INTAKE_DRAFT_FINAL_HANDOFF_READY_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED`

20G confirmed:

- draft package still unset
- no actual decision value collected
- no approval granted
- actual decision collection still blocked
- source recovery still blocked
- source identity finalization/recovery still blocked
- live/final paths still blocked
- Discord/MT5/AI API/live hook/NO_SIGNAL Discord still blocked
- next state is `AWAIT_EXPLICIT_HUMAN_AUTHORIZATION_FOR_ACTUAL_DECISION_VALUE_CAPTURE`

## 20H change boundary

20H may add only:

- `docs/gold_v2/GOLD_V2_20H_VALUE_CAPTURE_AUTH_GATE_SPEC_20260606.md`
- `scripts/gold_v2_runtime/audit_gold_v2_20h_value_capture_auth_gate.py`
- `scripts/gold_v2_runtime/bat/20H_VALUE_CAPTURE_AUTH_GATE.bat`

20H must not modify existing rule/source/signal/live files.

## Explicit no-change scope

20H must not change:

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

20H must not:

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

Because 20H is new-file-only, rollback is simple:

1. Remove the 20H files listed above.
2. Keep or remove this manifest depending on whether audit history is desired.
3. The pre-20H 20G files remain identified by the blob SHAs in this manifest.
