# NEXT CHAT HANDOFF — GOLD V3 Stage67 implemented / local run next

Created JST: `2026-06-10`

Current expected prior status:

`GOLD_V3_66_VIRTUAL_MONITORING_STATE_READY_AUDIT_ONLY`

Implemented stage:

`GOLD_V3_67_HEALTH_GATE_REHYDRATION_AUDIT_ONLY`

Expected READY status if local run passes:

`GOLD_V3_67_HEALTH_GATE_REHYDRATION_READY_AUDIT_ONLY`

Expected BLOCKED status if no acceptable audited outcome source or exact candidate-key match exists:

`GOLD_V3_67_HEALTH_GATE_REHYDRATION_BLOCKED_AUDIT_ONLY`

## 0. Global constraints preserved

GOLD V3 remains audit-only.

Do **not** read, use, reference, fallback to, or compare against:

- GOLD V2
- old GOLD
- DISC8
- Stage41 feature-only snapshot as trading source

The following remain OFF:

- MT5 orders
- MT5 execution BAT
- Discord live notification
- AI API call
- live hook
- live evaluator enablement
- final signal

Candidate/profile policy remains:

`poolから外さない。rolling health gateに判断させる。`

No candidate/profile may be manually removed or demoted.

## 1. CSV contract preserved

The human clarified:

`open中の足はCSVには入りません`

Stage67 preserves:

- `csv_contract: open/in-progress candles are not written to CSV`
- `csv_open_bar_exclusion_required: false`

No open-bar exclusion filter was introduced.

## 2. Files added in this chat

Spec:

`docs/gold_v3/GOLD_V3_67_HEALTH_GATE_REHYDRATION_AUDIT_ONLY_SPEC_20260610.md`

Runner:

`scripts/gold_v3_runtime/gold_v3_67_health_gate_rehydration_audit.py`

BAT:

`scripts/gold_v3_runtime/bat/run_gold_v3_67_health_gate_rehydration_audit.bat`

This handoff:

`docs/gold_v3/NEXT_CHAT_HANDOFF_GOLD_V3_67_IMPLEMENTED_RUN_NEXT_20260610.md`

## 3. Stage67 implementation summary

Stage67 runner:

1. Verifies Stage66 summary/status and required Stage66 outputs.
2. Searches existing GOLD V3 audited outcome artifacts in the required order:
   - Stage53
   - Stage52
   - Stage51
3. Inventories every candidate CSV found in those directories.
4. Accepts a source only if it contains:
   - all exact Stage66 candidate key columns
   - parseable time column
   - numeric outcome column such as `result_usd`
5. Reconstructs candidate_key using exactly this ordered column list:

`candidate_label+base_candidate_label+source_profile_id+profile_id+hv_profile+tp_usd+sl_usd+horizon_m15+horizon_m5_bars`

6. Requires Stage66 virtual opportunities to be covered by either:
   - `opportunity_id`, with candidate_key parity, or
   - `candidate_key + timestamp`
7. Rehydrates rolling health gate state without OHLC re-adjudication.
8. Keeps every observed candidate retained; health gate only sets pass/fail state.

## 4. Health gate contract implemented

- rolling window: `30`
- min history: `20`
- PF threshold: `1.10`
- loss streak must be `< 3`
- warm-up state: `INSUFFICIENT_HISTORY`
- pass state: `PASS`
- fail states include:
  - `PF_BELOW_THRESHOLD`
  - `LOSS_STREAK_LIMIT`
  - combined `PF_BELOW_THRESHOLD+LOSS_STREAK_LIMIT`

## 5. Intended local run

Run:

`scripts/gold_v3_runtime/bat/run_gold_v3_67_health_gate_rehydration_audit.bat`

The BAT is a no-argument local audit runner.

It should write to:

`Files\\FX_OUTPUTS\\gold_v3\\67_health_gate_rehydration_audit_only`

Expected outputs:

- `gold_v3_67_health_gate_rehydrated_candidate_state.csv`
- `gold_v3_67_health_gate_event_ledger.csv`
- `gold_v3_67_health_gate_inventory.csv`
- `gold_v3_67_blocker_matrix.csv`
- `gold_v3_67_validation_matrix.csv`
- `gold_v3_67_health_gate_rehydration_summary.json`
- `gold_v3_67_PASTE_ME_HEALTH_GATE_REHYDRATION_SUMMARY.txt`
- `GOLD_V3_67_REPORT.md`

## 6. Important behavior on local run

If an acceptable audited source is found and Stage66 coverage/key parity succeeds, Stage67 should become READY.

If no acceptable audited source is found, or exact candidate_key/coverage cannot be proven, Stage67 must end as BLOCKED.

This BLOCKED outcome is valid and expected under the handoff rules; it is not a reason to approximate from OHLC.

## 7. Next assistant should do

After the user runs the BAT and pastes/upload the PASTE_ME summary, inspect:

`gold_v3_67_PASTE_ME_HEALTH_GATE_REHYDRATION_SUMMARY.txt`

Then decide:

- If READY: proceed to Stage68 `GOLD_V3_68_RANK_DEDUP_SELECTION_REPRO_AUDIT_ONLY`.
- If BLOCKED: inspect `gold_v3_67_blocker_matrix.csv` and inventory; do not approximate outcomes.

## 8. New chat start prompt

```text
repo: knitanr-a11y/xauusd-signal-lab

まず以下を読んで、続きからお願いします。

docs/gold_v3/NEXT_CHAT_HANDOFF_GOLD_V3_67_IMPLEMENTED_RUN_NEXT_20260610.md

GOLD V3は現在audit-onlyです。
GOLD V2 / 旧GOLD / DISC8 は隔離中です。
読まない・使わない・参照しない・fallbackにしないでください。
Stage41 feature-only snapshotもtrading sourceにしないでください。

Stage67はspec/script/BAT作成済みです。
まだローカル実行結果は未確認です。

次にやること:
scripts/gold_v3_runtime/bat/run_gold_v3_67_health_gate_rehydration_audit.bat を実行し、
Files\\FX_OUTPUTS\\gold_v3\\67_health_gate_rehydration_audit_only\\gold_v3_67_PASTE_ME_HEALTH_GATE_REHYDRATION_SUMMARY.txt
を確認してください。

重要:
- open中の足はCSVには入りません。CSVの最新行はCSV契約上closedです。
- csv_open_bar_exclusion_required=false の契約を維持してください。
- live/MT5/Discord/AI API/final signalはOFFです。
- candidate/profileを手動で外さないでください。
- poolから外さない。rolling health gateに判断させる。
- Stage67ではoutcome sourceを近似せず、既存の監査済みGOLD V3 Stage52/53/51 artifactのみを使ってください。
- candidate_keyはStage66と同じ ordered columns で再構成してください。
- sourceが見つからない、またはcandidate_keyが再現できない場合はBLOCKEDのままにしてください。
```

## 9. Final reminder

This handoff does not approve live trading.

All generated stages remain audit-only and local-run only.
