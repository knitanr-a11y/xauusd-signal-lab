# GOLD V3 Stage84 — Trade Review Ledger Policy Audit-Only Spec

Created JST: `2026-06-10`

Stage name:

`GOLD_V3_84_TRADE_REVIEW_LEDGER_POLICY_AUDIT_ONLY`

Expected READY status:

`GOLD_V3_84_TRADE_REVIEW_LEDGER_POLICY_READY_AUDIT_ONLY`

Blocked status:

`GOLD_V3_84_TRADE_REVIEW_LEDGER_POLICY_BLOCKED_AUDIT_ONLY`

## 1. Purpose

Stage84 pivots runtime retention priority away from keeping every operational log forever and toward keeping durable trade review history.

Human clarification:

`確実にいるのはトレード履歴だけかもしれません。なんで負けたか勝ったのかがあとから振り返ってわかればシグナルの向上やAIAPIにも役立つと思います`

Stage84 therefore defines the durable trade review ledger policy and schema.

## 2. Non-negotiable constraints

- GOLD V3 only.
- GOLD V2, old GOLD, and DISC8 remain quarantined.
- Do not read, use, reference, compare against, or fallback to GOLD V2, old GOLD, or DISC8.
- Do not use Stage41 feature-only snapshot as a trading source.
- GOLD V3 remains audit-only.
- Do not send Discord notifications.
- Do not place MT5 orders.
- Do not call AI APIs.
- Do not enable live hook, live evaluator, or final signal.
- Do not manually remove or demote candidates/profiles.
- Required pool policy:

`poolから外さない。rolling health gateに判断させる。`

## 3. CSV closed-row contract

Preserve:

- `csv_contract: open/in-progress candles are not written to CSV`
- `csv_open_bar_exclusion_required: false`

## 4. Retention priority

### Keep long-term

- trade review ledger rows,
- per-trade compact evidence packet,
- signal decision context,
- candidate/profile key,
- reason/cause snapshot,
- outcome and post-trade result,
- notes for why the trade won/lost,
- compact features useful for future model/AI review.

### Do not treat as long-term primary evidence

- old notification errors,
- old heartbeat logs,
- old full timing/event CSV logs,
- full monitor scratch files,
- repeated NO_SIGNAL heartbeat entries.

These may be kept short-term for debugging, but they are not the primary learning record.

## 5. Trade review ledger field schema

Required key fields:

- `trade_id`
- `source_stage`
- `signal_time_m15`
- `signal_time_utc`
- `decision`
- `direction`
- `candidate_label`
- `base_candidate_label`
- `source_profile_id`
- `profile_id`
- `hv_profile`
- `tp_usd`
- `sl_usd`
- `horizon_m15`
- `horizon_m5_bars`
- `candidate_key`
- `health_gate_status`
- `payload_action`
- `entry_ref_price`
- `spread_or_cost_note`
- `expected_tp_price`
- `expected_sl_price`
- `outcome_status`
- `exit_time`
- `exit_reason`
- `realized_usd`
- `realized_r_multiple`
- `mfe_usd`
- `mae_usd`
- `bars_to_exit_m5`
- `bars_to_exit_m15`
- `why_win_loss_hypothesis`
- `post_trade_review_note`
- `evidence_run_dir`
- `evidence_paste_path`
- `manual_review_required`

Candidate key order must remain:

`candidate_label+base_candidate_label+source_profile_id+profile_id+hv_profile+tp_usd+sl_usd+horizon_m15+horizon_m5_bars`

## 6. Output model

Durable ledger root:

`Files/FX_OUTPUTS/gold_v3/trade_review_ledger/`

Files:

- `trade_review_ledger_schema.csv`
- `trade_review_retention_policy_matrix.csv`
- `trade_review_current_template.csv`
- `trade_review_manual_outcome_template.csv`
- `README_TRADE_REVIEW_LEDGER.md`

Stage84 audit output folder:

`Files/FX_OUTPUTS/gold_v3/84_trade_review_ledger_policy_audit_only/`

## 7. READY conditions

Stage84 is READY if:

- ledger root exists,
- schema CSV is written,
- retention policy matrix is written,
- manual outcome template is written,
- candidate key order is documented exactly,
- long-term retention focuses on trade history, not giant logs,
- live/external flags remain false,
- blocker_count is zero.

READY does not enable live release or AI API.

## 8. Runner and BAT

Script:

`scripts/gold_v3_runtime/gold_v3_84_trade_review_ledger_policy_audit.py`

BAT:

`scripts/gold_v3_runtime/bat/run_gold_v3_84_trade_review_ledger_policy_audit.bat`

## 9. Future direction

After live or shadow signals are explicitly approved, a later stage may append one row per actual emitted signal/trade. Until then, Stage84 only prepares schema, retention rules, and manual review templates.
