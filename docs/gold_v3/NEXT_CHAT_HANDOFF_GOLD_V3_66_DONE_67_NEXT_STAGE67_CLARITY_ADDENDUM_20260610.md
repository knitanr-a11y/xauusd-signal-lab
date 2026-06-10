# NEXT CHAT HANDOFF ADDENDUM — GOLD V3 Stage67 health-gate clarity

Created JST: `2026-06-10`

Read after:

`docs/gold_v3/NEXT_CHAT_HANDOFF_GOLD_V3_66_DONE_67_NEXT_HEALTH_GATE_REHYDRATION_AUDIT_ONLY_20260610.md`

## Purpose of this addendum

The main handoff is valid and contains the Stage62B-66 chain. This addendum removes possible ambiguity for the next assistant before implementing Stage67.

Next stage remains:

`GOLD_V3_67_HEALTH_GATE_REHYDRATION_AUDIT_ONLY`

## Do not change these constraints

- GOLD V3 remains audit-only.
- Do not read/use/reference/fallback to GOLD V2, old GOLD, or DISC8.
- Do not use Stage41 feature-only snapshot as trading source.
- Do not create MT5 order BATs.
- Do not send Discord notifications.
- Do not call AI APIs.
- Do not enable live hook or final signal.
- Do not manually remove/demote candidates.
- Keep all candidate profiles in pool, including high-vol siblings.
- Let rolling health gate decide pass/fail.

Required phrase/logic:

`poolから外さない。rolling health gateに判断させる。`

## Confirmed CSV contract

The user clarified in this chat:

`open中の足はCSVには入りません`

Therefore:

- CSV latest row is considered closed by CSV contract.
- Do not implement open-bar exclusion.
- Preserve `csv_open_bar_exclusion_required=false`.

## Exact current local chain

Current local READY chain:

1. Stage62B: `GOLD_V3_62B_LIVE_READINESS_PLAN_CANONICALIZATION_READY_AUDIT_ONLY`
2. Stage63: `GOLD_V3_63_H4_CLOSED_BAR_LIVE_STATE_BUILDER_READY_AUDIT_ONLY`
3. Stage64: `GOLD_V3_64_M15_M5_ALIGNMENT_STATE_BUILDER_READY_AUDIT_ONLY`
4. Stage65: `GOLD_V3_65_ROLLING_PRIOR_60D_Q70_STATE_READY_AUDIT_ONLY`
5. Stage66: `GOLD_V3_66_VIRTUAL_MONITORING_STATE_READY_AUDIT_ONLY`

Important Stage66 facts:

- `virtual_opportunity_rows: 6848`
- `candidate_count: 44`
- `q70_attached_count: 6848`
- `q70_missing_count: 0`
- `high_vol_q70_opportunity_count: 1550`
- `latest_high_vol_candidate_count: 0`
- `candidate_key_source: candidate_label+base_candidate_label+source_profile_id+profile_id+hv_profile+tp_usd+sl_usd+horizon_m15+horizon_m5_bars`

Stage66 key path:

`Files\\FX_OUTPUTS\\gold_v3\\66_virtual_monitoring_state_audit_only\\gold_v3_66_candidate_virtual_monitoring_state.csv`

Stage66 joined ledger:

`Files\\FX_OUTPUTS\\gold_v3\\66_virtual_monitoring_state_audit_only\\gold_v3_66_virtual_opportunity_q70_joined_ledger.csv`

## Stage67 input discovery order

Stage67 must not guess outcomes from OHLC. It must search existing GOLD V3 audit artifacts.

Search under:

`Files\\FX_OUTPUTS\\gold_v3`

Recommended discovery order:

1. Stage53 outputs, because Stage53 was the shadow adjudication stage.
2. Stage52 outputs, because Stage52 was health-gate selection / health-state related.
3. Stage51 virtual opportunity ledger only if it already contains outcome/PnL/result columns.
4. If no audited outcome source is found, Stage67 must be BLOCKED.

Do not use GOLD V2 / old GOLD / DISC8 as fallback.

## Outcome-source acceptance criteria

An artifact is acceptable as Stage67 outcome source only if it satisfies all of these:

1. It is under GOLD V3 output tree.
2. It contains or can deterministically reconstruct the same candidate key used by Stage66.
3. It has a timestamp compatible with Stage66 virtual opportunities.
4. It has outcome data sufficient for rolling health calculations, for example:
   - `outcome`
   - `result`
   - `pnl`
   - `profit`
   - `tp/sl/timeout`
   - win/loss flag
5. It does not require OHLC re-adjudication or approximate outcome reconstruction.

If the candidate key cannot be exactly matched or reconstructed from explicit columns, Stage67 must be BLOCKED.

## Candidate key reconstruction rule

Stage66 candidate key source is:

`candidate_label+base_candidate_label+source_profile_id+profile_id+hv_profile+tp_usd+sl_usd+horizon_m15+horizon_m5_bars`

Stage67 should first try to use an existing `candidate_key` column if present.

If absent, reconstruct using exactly the same ordered columns above. Do not omit profile fields. Do not merge HV siblings.

If one or more required columns are missing, record the missing columns in blocker matrix and stop as BLOCKED.

## Health gate calculation contract

Unless an audited source artifact explicitly states a different frozen contract, use:

- rolling window: 30 realized virtual outcomes
- min history: 20
- PF threshold: 1.10
- loss streak must be < 3
- candidate remains in pool even when health gate fails

Health-gate output should separate:

- `candidate_retained`: always true for observed candidates
- `health_gate_pass`: calculated boolean
- `health_gate_reason`: e.g. `PASS`, `INSUFFICIENT_HISTORY`, `PF_BELOW_THRESHOLD`, `LOSS_STREAK_LIMIT`

Do not name failed gate candidates as removed.

## Stage67 recommended outputs

Folder:

`Files\\FX_OUTPUTS\\gold_v3\\67_health_gate_rehydration_audit_only`

Files:

- `gold_v3_67_health_gate_rehydrated_candidate_state.csv`
- `gold_v3_67_health_gate_event_ledger.csv`
- `gold_v3_67_health_gate_inventory.csv`
- `gold_v3_67_blocker_matrix.csv`
- `gold_v3_67_validation_matrix.csv`
- `gold_v3_67_health_gate_rehydration_summary.json`
- `gold_v3_67_PASTE_ME_HEALTH_GATE_REHYDRATION_SUMMARY.txt`
- `GOLD_V3_67_REPORT.md`

## Stage67 blocker conditions

Stage67 must be BLOCKED if any of these occurs:

- Stage66 is not READY.
- No acceptable GOLD V3 audited outcome source is found.
- Outcome source has no deterministic candidate-key match.
- Outcome source requires approximate OHLC re-adjudication.
- Rolling PF/loss-streak cannot be calculated.
- Any live/MT5/Discord/AI/final-signal flag is true.
- Any candidate is manually removed/demoted.

## Stage67 READY conditions

Stage67 READY only if:

- Stage66 READY is verified.
- Audited outcome source is identified and documented.
- Candidate key match/reconstruction succeeds.
- All observed candidates are retained.
- Rolling PF and loss streak are calculated deterministically.
- Health gate pass/fail is produced without changing pool membership.
- Safety flags remain false.

## Updated next-chat prompt

Use both files in the next chat:

```text
repo: knitanr-a11y/xauusd-signal-lab

まず以下を読んで、続きからお願いします。

docs/gold_v3/NEXT_CHAT_HANDOFF_GOLD_V3_66_DONE_67_NEXT_HEALTH_GATE_REHYDRATION_AUDIT_ONLY_20260610.md
docs/gold_v3/NEXT_CHAT_HANDOFF_GOLD_V3_66_DONE_67_NEXT_STAGE67_CLARITY_ADDENDUM_20260610.md

GOLD V3は現在audit-onlyです。
GOLD V2 / 旧GOLD / DISC8 は隔離中です。
読まない・使わない・参照しない・fallbackにしないでください。
Stage41 feature-only snapshotもtrading sourceにしないでください。

このチャットではStage62B〜66まで完了しました。
現在statusは以下です。
GOLD_V3_66_VIRTUAL_MONITORING_STATE_READY_AUDIT_ONLY

次はStage67:
GOLD_V3_67_HEALTH_GATE_REHYDRATION_AUDIT_ONLY

重要:
- open中の足はCSVには入りません。CSVの最新行はCSV契約上closedです。
- csv_open_bar_exclusion_required=false の契約を維持してください。
- live/MT5/Discord/AI API/final signalはOFFです。
- candidate/profileを手動で外さないでください。
- poolから外さない。rolling health gateに判断させる。
- Stage67ではoutcome sourceを近似せず、既存の監査済みGOLD V3 Stage52/53等のartifactを探して使ってください。
- candidate_keyはStage66と同じ ordered columns で再構成してください。
- sourceが見つからない、またはcandidate_keyが再現できない場合はBLOCKEDにしてください。
```
