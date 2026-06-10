# GOLD V3 Stage67 — Health Gate Rehydration Audit-Only Spec

Created JST: `2026-06-10`

Stage name:

`GOLD_V3_67_HEALTH_GATE_REHYDRATION_AUDIT_ONLY`

Expected READY status:

`GOLD_V3_67_HEALTH_GATE_REHYDRATION_READY_AUDIT_ONLY`

Blocked status:

`GOLD_V3_67_HEALTH_GATE_REHYDRATION_BLOCKED_AUDIT_ONLY`

## 1. Purpose

Stage67 rehydrates candidate-level rolling health gate state from existing audited GOLD V3 outcome artifacts and the Stage66 virtual monitoring key contract.

This is not a live evaluator, not final signal generation, not Discord notification, not MT5 execution, and not AI analysis.

## 2. Non-negotiable constraints

- GOLD V3 only.
- Do not read, use, reference, compare against, or fallback to GOLD V2, old GOLD, or DISC8.
- Do not use Stage41 feature-only snapshot as trading source.
- Do not create MT5 order BATs.
- Do not send Discord notifications.
- Do not call AI APIs.
- Do not enable live hook, live evaluator, or final signal.
- Do not manually remove or demote candidates/profiles.
- Keep every observed candidate in the pool.
- Required pool policy:

`poolから外さない。rolling health gateに判断させる。`

## 3. CSV closed-row contract

The human clarified:

`open中の足はCSVには入りません`

Therefore Stage67 must preserve:

- `csv_contract: open/in-progress candles are not written to CSV`
- `csv_open_bar_exclusion_required: false`

No open-bar exclusion filter should be introduced.

## 4. Required inputs

Default GOLD V3 output root:

`Files\\FX_OUTPUTS\\gold_v3`

Required Stage66 inputs:

- `66_virtual_monitoring_state_audit_only/gold_v3_66_virtual_monitoring_summary.json`
- `66_virtual_monitoring_state_audit_only/gold_v3_66_virtual_opportunity_q70_joined_ledger.csv`
- `66_virtual_monitoring_state_audit_only/gold_v3_66_candidate_virtual_monitoring_state.csv`

Stage66 must be READY:

`GOLD_V3_66_VIRTUAL_MONITORING_STATE_READY_AUDIT_ONLY`

## 5. Audited outcome source discovery order

Stage67 must not approximate outcomes from OHLC.

It must search existing GOLD V3 audit artifacts in this order:

1. Stage53 outputs, especially closed/shadow adjudication ledgers.
2. Stage52 outputs, especially health-gate state or selected trade ledgers.
3. Stage51 virtual opportunity ledger only if it already contains outcome/PnL/result columns.

No GOLD V2 / old GOLD / DISC8 fallback is allowed.

## 6. Outcome-source acceptance criteria

A candidate artifact is acceptable only if all are true:

1. The artifact is under the GOLD V3 output tree or explicitly supplied as a GOLD V3 Stage51/52/53 directory.
2. It contains all ordered Stage66 candidate-key columns.
3. It has a parseable timestamp compatible with Stage66 virtual opportunities.
4. It has numeric outcome data sufficient for rolling health calculations, preferably `result_usd`.
5. It covers all Stage66 virtual opportunities by `opportunity_id`; if no `opportunity_id` exists, by `candidate_key + timestamp`.
6. It does not require OHLC re-adjudication or approximate outcome reconstruction.

If no acceptable artifact is found, Stage67 must output BLOCKED with blocker matrix.

## 7. Candidate key reconstruction contract

Use this exact ordered column list:

`candidate_label+base_candidate_label+source_profile_id+profile_id+hv_profile+tp_usd+sl_usd+horizon_m15+horizon_m5_bars`

Do not omit profile fields.

Do not merge high-vol sibling profiles.

Do not use a looser candidate label only key.

If any required column is missing in the outcome source, Stage67 must reject that source. If all candidate sources are rejected, Stage67 must BLOCK.

## 8. Health gate contract

Unless a future audited source artifact explicitly freezes a different contract, Stage67 uses the established Stage52 health gate configuration:

- rolling window: `30` realized virtual outcomes
- minimum history: `20`
- PF threshold: `1.10`
- loss streak must be `< 3`
- virtual monitoring updates every candidate result after all candidates at the same timestamp have been assessed
- insufficient history is a warm-up pass-through state, recorded as `INSUFFICIENT_HISTORY`

The output must separate pool retention from health gate state:

- `candidate_retained`: always true for observed candidates
- `health_gate_pass`: calculated boolean
- `health_gate_reason`: `INSUFFICIENT_HISTORY`, `PASS`, `PF_BELOW_THRESHOLD`, `LOSS_STREAK_LIMIT`, or combined failure reason

## 9. Outputs

Output folder:

`Files\\FX_OUTPUTS\\gold_v3\\67_health_gate_rehydration_audit_only`

Required outputs:

- `gold_v3_67_health_gate_rehydrated_candidate_state.csv`
- `gold_v3_67_health_gate_event_ledger.csv`
- `gold_v3_67_health_gate_inventory.csv`
- `gold_v3_67_blocker_matrix.csv`
- `gold_v3_67_validation_matrix.csv`
- `gold_v3_67_health_gate_rehydration_summary.json`
- `gold_v3_67_PASTE_ME_HEALTH_GATE_REHYDRATION_SUMMARY.txt`
- `GOLD_V3_67_REPORT.md`

## 10. READY conditions

Stage67 is READY only if:

- Stage66 summary is READY.
- Stage66 joined ledger and candidate state exist.
- An acceptable audited GOLD V3 outcome source is identified.
- Candidate key is reconstructed from the exact ordered columns.
- Outcome source covers all Stage66 virtual opportunities.
- Numeric outcome values exist for all rehydrated events.
- Rolling PF and loss streak are calculated deterministically.
- All observed candidates are retained.
- No live / MT5 / Discord / AI / final-signal flag is enabled.
- `csv_open_bar_exclusion_required=false` is preserved.

## 11. BLOCKED conditions

Stage67 must BLOCK if any of these occurs:

- Stage66 is missing or not READY.
- No acceptable audited GOLD V3 Stage51/52/53 outcome source is found.
- Candidate key cannot be reconstructed from the exact ordered columns.
- Outcome source does not cover all Stage66 virtual opportunities.
- Numeric rolling result values are missing.
- Any OHLC re-adjudication would be required.
- Any candidate/profile is manually removed or demoted.
- Any live/MT5/Discord/AI/final-signal flag is true.

## 12. Runner

Script:

`scripts/gold_v3_runtime/gold_v3_67_health_gate_rehydration_audit.py`

BAT:

`scripts/gold_v3_runtime/bat/run_gold_v3_67_health_gate_rehydration_audit.bat`

The BAT is a no-argument local audit runner only.
