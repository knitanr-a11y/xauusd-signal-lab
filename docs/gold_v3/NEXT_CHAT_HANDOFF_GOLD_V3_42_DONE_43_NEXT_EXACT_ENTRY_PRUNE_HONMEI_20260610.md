# NEXT CHAT HANDOFF - GOLD V3 42 done / 43 next exact entry prune honmei audit-only

Created JST: 2026-06-10

## 0. Read this first

This is the current handoff for the GOLD V3 live-candidate work.

The most important correction from the previous chat is:

- Do **not** create live candidates from OHLC/feature rows by approximation.
- Do **not** use a feature-only snapshot builder as a substitute for the original candidate entry source-of-truth.
- The candidate PF/win-rate pruning only remains meaningful if the live evaluator reproduces the original entry families and then applies the exact prune filters.

The user explicitly rejected approximate live implementation. Treat this as a hard guardrail.

## 1. Current status

Status:

`GOLD_V3_42_PRIMARY_PLUS_RESTORE_CANDIDATE_DECISION_RECORDED_AUDIT_ONLY`

Next stage:

`GOLD_V3_43_EXACT_ENTRY_AND_PRUNE_CONTRACT_FOR_HONMEI_SET_AUDIT_ONLY`

Purpose of Stage43:

Build a machine-readable exact contract for the honmei candidate set only, using source-of-truth artifacts. This is still audit-only. It must not enable live Discord signals or MT5 execution.

## 2. Hard prohibitions

Do not do any of the following:

- Do not use GOLD V2.
- Do not use old GOLD.
- Do not use DISC8.
- Do not use quarantined artifacts as fallback.
- Do not approximate entry rules from OHLC.
- Do not infer BUY/SELL direction when the source-of-truth does not provide it.
- Do not use Stage41 feature-only snapshot as a trading signal source.
- Do not enable MT5 order execution.
- Do not create a new MT5 order BAT until exact entry/prune reproduction is verified.
- Do not use month filters, daily caps, candidate switching, or trade-count caps unless the user explicitly reverses the prior decision.

## 3. Important safety cleanup already performed

The following unsafe loop BATs were removed from the repository after the approximation mistake was identified:

- `scripts/gold_v3_runtime/bat/GOLD_V3_40_MT5_DEMO_EXECUTOR_LOOP.bat`
  - removed commit: `ba4f122eb835e493d564eec1fe61f341d5454c80`
  - reason: it previously passed `--enable-mt5-demo-order`; live entry SOT was not verified.

- `scripts/gold_v3_runtime/bat/GOLD_V3_41_GOLDSHARP_CANDLE_SNAPSHOT_BUILDER_LOOP.bat`
  - removed commit: `e1bef6d21457f7e4ca26dee581c484c25a2a6880`
  - reason: Stage41 feature-only snapshot must not be used as a trading signal source.

Important local warning:

If the user's local machine already has old BAT files or old BAT windows running, repository deletion does not stop those running processes. In the next chat, first instruct the user to stop any existing Stage40 and Stage41 BAT windows before further live work.

## 4. Latest decision: honmei set expansion

The user decided to add the following three candidates to the honmei review set:

1. `R03_P1_R1_ONLY_CD60_PRUNE_111`
2. `R04_P4_R1_ONLY_CD60_PRUNE_115`
3. `R1_ONLY_CD90_PRUNE_050__R1_ONLY_CD90_PRUNE_050_S030__R1_ONLY_CD90_PRUNE_050_S024`

This was recorded in:

- `docs/gold_v3/gold_v3_42_primary_plus_restore_candidate_decision.csv`
  - commit: `7cf1cd482719ef6a7e9ef9e550ed72ee4e4cef98`

- `docs/gold_v3/GOLD_V3_42_PRIMARY_PLUS_RESTORE_CANDIDATE_DECISION_AUDIT_ONLY_20260610.md`
  - commit: `a45710874182e3514a40811d70c3314ca06b0d07`

This is a decision record only. It is not live approval.

## 5. Source-of-truth artifact locations to use in Stage43

The source root from GOLD V3 summaries is:

`C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files\FX_OUTPUTS\gold_v3`

The exact output directory names may vary by script constant, but the file basenames below are confirmed from uploaded outputs and should be searched under the GOLD V3 output root if not directly visible.

Use these artifacts:

### Stage15 - base entry families and raw replay SOT

Files:

- `gold_v3_15_replay_candidate_metrics.csv`
- `gold_v3_15_replay_trade_ledger.csv`
- `gold_v3_15_replay_family_metrics.csv`
- `gold_v3_15_replay_monthly_metrics.csv`
- `gold_v3_15_summary.json`
- `GOLD_V3_15_AUDIT_ONLY_REPLAY_EXECUTION_REPORT.md`

Use Stage15 for:

- base entry family
- source_rank
- direction
- feature column
- rule expression
- TP/SL profile
- raw candidate replay metrics
- trade-level ledger

### Stage21 - existing selected prune filters

Files:

- `gold_v3_21_filter_traceability.csv`
- `gold_v3_21_selected_candidate_validation.csv`
- `gold_v3_21_selected_candidate_monthly_validation.csv`
- `GOLD_V3_21_SELECTED_PRUNING_RULE_VALIDATION_AUDIT_ONLY_REPORT.md`

Use Stage21 for:

- existing prune filters per source_scenario_key
- filter_id Fxxx definitions
- rank_scope
- column / values / low / high

### Stage22 - further pruning and restore candidate details

Files:

- `gold_v3_22_further_pruned_candidate_metrics.csv`
- `gold_v3_22_filter_traceability.csv`
- `gold_v3_22_further_pruned_monthly_metrics.csv`
- `gold_v3_22_recommendation.csv`
- `GOLD_V3_22_WITHIN_CANDIDATE_LOSS_FEATURE_PRUNING_AUDIT_ONLY_REPORT.md`

Use Stage22 for:

- `R1_ONLY_CD90_PRUNE_050` restore candidate exact variant
- S030 / S024 added filter definitions
- low frequency audit flag
- within-candidate pruning metrics

### Stage30 - all retained filter contract

Files:

- `gold_v3_30_all_retained_candidate_set.csv`
- `gold_v3_30_all_retained_filter_contract.csv`
- `GOLD_V3_30_ALL_RETAINED_CANDIDATE_SET_RESTORE_AUDIT_ONLY_REPORT.md`

Use Stage30 for:

- retained candidate set
- existing + added filter contract for Stage24 retained rows
- packet_row 1 and 4 filter contracts
- packet_row 7/8/9/11/13 retained contracts if needed for comparison

### Stage35/36 - final active ranking and final added filters

Files:

- `gold_v3_35_before_after_metrics.csv`
- `gold_v3_35_selected_cut_plan.csv`
- `gold_v3_36_ranked_candidate_contract.csv`
- `gold_v3_36_final_filter_contract.csv`
- `GOLD_V3_36_FINAL_RANKED_CANDIDATE_CONTRACT_AUDIT_ONLY_REPORT.md`

Use Stage36 for:

- final active candidate rows
- ranked names R01-R07
- Stage36 final filters, especially global Saturday and final band cuts

### Stage42 - human decision record

Files:

- `docs/gold_v3/gold_v3_42_primary_plus_restore_candidate_decision.csv`
- `docs/gold_v3/GOLD_V3_42_PRIMARY_PLUS_RESTORE_CANDIDATE_DECISION_AUDIT_ONLY_20260610.md`

Use Stage42 for:

- human decision to add R03/R04/CD90 restore candidate to honmei review set
- live_allowed=False state

## 6. Base entry families confirmed from Stage15

Stage15 base entry families confirmed from `gold_v3_15_replay_candidate_metrics.csv` and `gold_v3_15_replay_trade_ledger.csv`:

### source_rank 1 - R1 base family

- `source_rank`: `1`
- `candidate_group_id`: `GROUP_H4_RET4_MOMENTUM`
- `entry_family_key`: `GROUP_H4_RET4_MOMENTUM||LONG||h4_ret4||h4_ret4 >= 0.00751699`
- `direction`: `LONG`
- live side if converted later: `BUY`
- `feature_column`: `h4_ret4`
- `rule_expression_preview`: `h4_ret4 >= 0.00751699`
- `profile_id`: `USDPRICE_TP150_SL60_H128`

### source_rank 2 - R2 base family

- `source_rank`: `2`
- `candidate_group_id`: `GROUP_M15_ATR28_MID_VOL_RANGE`
- `entry_family_key`: `GROUP_M15_ATR28_MID_VOL_RANGE||LONG||m15_atr28||3.59086 <= m15_atr28 <= 4.29321`
- `direction`: `LONG`
- live side if converted later: `BUY`
- `feature_column`: `m15_atr28`
- `rule_expression_preview`: `3.59086 <= m15_atr28 <= 4.29321`
- `profile_id`: `USDPRICE_TP80_SL30_H64`

### source_rank 3/4/6/7/8 warning

Stage15 also contains `GROUP_H1_ATR56_HIGH_VOL` entries using `h1_atr56 >= 9.95812`, but these are not part of the current Stage36 active R01-R07 honmei decision and must not be pulled into the R03/R04/CD90 live contract unless a new human decision explicitly adds them.

## 7. Honmei candidates and exact known filters

### A. R03 - `R03_P1_R1_ONLY_CD60_PRUNE_111`

Source:

- Stage36 active candidate
- packet_row `1`
- source_scenario_key `R1_ONLY_CD60_PRUNE_111`
- variant_key `R1_ONLY_CD60_PRUNE_111__R1_ONLY_CD60_PRUNE_111_S021__R1_ONLY_CD60_PRUNE_111_S022`
- cooldown `60`

Base entry:

- source_rank `1` only
- LONG / BUY
- `h4_ret4 >= 0.00751699`
- profile `USDPRICE_TP150_SL60_H128`

Stage30 existing/added prune filters for packet 1:

1. `existing_stage21 F002`: exclude rank 1 `h4_ret4 in [0.0200540794, 0.0375731465)`
2. `existing_stage21 F003`: exclude `jst_hour = 23`
3. `existing_stage21 F004`: exclude `jst_weekday = Friday`
4. `added_stage22 R1_ONLY_CD60_PRUNE_111_S021`: exclude `jst_hour = 21`
5. `added_stage22 R1_ONLY_CD60_PRUNE_111_S022`: exclude `jst_hour = 22`

Stage36 final prune for packet 1:

6. `GLOBAL_SATURDAY`: exclude `jst_weekday = Saturday`

Stage36 final metrics:

- `profit_factor_final`: `2.6083250034`
- `win_rate_final`: `0.6684636119`
- `trades_per_day_final`: `2.0784313725`
- `negative_months_final`: `0`
- `july_pf_final`: `1.2486063766`

### B. R04 - `R04_P4_R1_ONLY_CD60_PRUNE_115`

Source:

- Stage36 active candidate
- packet_row `4`
- source_scenario_key `R1_ONLY_CD60_PRUNE_115`
- variant_key `R1_ONLY_CD60_PRUNE_115__R1_ONLY_CD60_PRUNE_115_S020__R1_ONLY_CD60_PRUNE_115_S022`
- cooldown `60`

Base entry:

- source_rank `1` only
- LONG / BUY
- `h4_ret4 >= 0.00751699`
- profile `USDPRICE_TP150_SL60_H128`

Stage30 existing/added prune filters for packet 4:

1. `existing_stage21 F002`: exclude rank 1 `h4_ret4 in [0.0200540794, 0.0375731465)`
2. `existing_stage21 F004`: exclude `jst_weekday = Friday`
3. `existing_stage21 F006`: exclude `jst_hour = 0`
4. `added_stage22 R1_ONLY_CD60_PRUNE_115_S020`: exclude `jst_hour = 21`
5. `added_stage22 R1_ONLY_CD60_PRUNE_115_S022`: exclude `jst_hour = 23`

Stage36 final prune for packet 4:

6. `GLOBAL_SATURDAY`: exclude `jst_weekday = Saturday`

Stage36 final metrics:

- `profit_factor_final`: `2.5517460463`
- `win_rate_final`: `0.6688918558`
- `trades_per_day_final`: `2.0980392157`
- `negative_months_final`: `0`
- `july_pf_final`: `1.2416950739`

### C. Restore candidate - `R1_ONLY_CD90_PRUNE_050`

Source:

- Stage22 restore candidate
- source_scenario_key `R1_ONLY_CD90_PRUNE_050`
- exact variant selected by user for honmei review:
  - `R1_ONLY_CD90_PRUNE_050__R1_ONLY_CD90_PRUNE_050_S030__R1_ONLY_CD90_PRUNE_050_S024`
- cooldown `90`
- status: `REQUEST_MORE_AUDIT_LOW_FREQUENCY`

Base entry:

- source_rank `1` only
- LONG / BUY
- `h4_ret4 >= 0.00751699`
- profile `USDPRICE_TP150_SL60_H128`

Stage22 exact filters for the selected variant:

1. `existing_stage21 F004`: exclude `jst_weekday = Friday`
2. `existing_stage21 F006`: exclude `jst_hour = 0`
3. `added_stage22 R1_ONLY_CD90_PRUNE_050_S030`: exclude rank 1 `h4_ret4 in [0.013348824, 0.0156019094)`
4. `added_stage22 R1_ONLY_CD90_PRUNE_050_S024`: exclude `jst_weekday = Wednesday`

Stage22 metrics for selected variant:

- `rows_after_spacing`: `483`
- `trades_per_calendar_day`: `1.3529411765`
- `win_rate_result_positive`: `0.6418219462`
- `profit_factor`: `2.8726383868`
- `sum_result_usd`: `8967.26`
- `negative_months`: `0`
- `positive_months`: `12`
- `worst_month`: `2025-02`
- `worst_month_sum`: `24.15`
- `july_profit_factor`: `5.5905567301`
- `july_sum_result_usd`: `521.12`
- `max_drawdown_usd`: `986.37`
- `max_consecutive_losses`: `14`
- `audit_recommendation`: `REQUEST_MORE_AUDIT_LOW_FREQUENCY`
- `audit_reason`: `pruning improved quality but dropped below frequency objective`

Stage36 final filters do not automatically apply to this Stage22 restore candidate unless Stage43 explicitly creates a restore contract. Do not assume a Stage36 packet_row exists for it.

## 8. Other Stage36 candidates retained for context, not honmei-first

These exist in Stage36 but are not the newly selected honmei-first set:

- R01/P7 `R1_ONLY_CD60_PRUNE_015`: PF highest but negative_months=1; previously watch-style candidate.
- R02/P8 `R1_ONLY_CD60_PRUNE_015`: PF high but negative_months=1; previously watch-style candidate.
- R05/P9 `MAIN_R1_R2_CD90_PRUNE_133`: July PF low-ish.
- R06/P11 `MAIN_R1_R2_CD90_PRUNE_132`: July PF low-ish.
- R07/P13 `MAIN_R1_R2_CD120_PRUNE_122`: negative_months=0 but PF lower.

Do not delete them unless the user explicitly decides. For next stage, the focus is R03/R04/CD90 restore.

## 9. Current runtime scripts and caution

Existing runtime scripts in repo may still include earlier experimental work:

- `scripts/gold_v3_runtime/gold_v3_37_ranked_live_discord_notify.py`
- `scripts/gold_v3_runtime/gold_v3_38_live_minute_loop.py`
- `scripts/gold_v3_runtime/gold_v3_39_live_runtime_layout.py`
- `scripts/gold_v3_runtime/gold_v3_40_mt5_demo_executor_loop.py`
- `scripts/gold_v3_runtime/gold_v3_41_goldsharp_candle_snapshot_builder.py`

Do not use Stage40 or Stage41 for live trading. Stage40 script may exist, but the dangerous Stage40 BAT was removed. Stage41 script may exist, but its loop BAT was removed. Stage41 is not an exact evaluator and must not be connected to Stage37/40 as a trading source.

Stage38 and Stage40 were modified to read Files-root `.env` for `GOLD_V3_DISCORD_WEBHOOK_URL`, but this does not make them live-approved.

## 10. Required Stage43 output

Stage43 should create a machine-readable audit-only contract such as:

- `gold_v3_43_honmei_exact_entry_prune_contract.csv`
- `gold_v3_43_honmei_exact_entry_prune_contract.json`
- `GOLD_V3_43_EXACT_ENTRY_AND_PRUNE_CONTRACT_FOR_HONMEI_SET_AUDIT_ONLY_REPORT.md`
- `gold_v3_43_input_inventory.csv`
- `gold_v3_43_blocker_matrix.csv`
- `gold_v3_43_summary.json`

Required columns should include at least:

- candidate_label
- decision_role
- source_stage
- source_scenario_key
- variant_key
- packet_row if applicable
- cooldown_minutes
- base_source_ranks
- direction
- live_side
- profile_id
- tp_usd
- sl_usd
- horizon_m5_bars or horizon profile detail
- base_rule_expression
- base_feature_column
- base_low
- base_high
- filter_order
- filter_origin
- filter_id
- filter_description
- filter_type
- rank_scope
- feature_column
- values
- low
- high
- entry_pre_known_only
- applies_to_live
- live_allowed=false

Stage43 must not create live signal code. It only creates the exact contract.

## 11. Next-chat start prompt

Use the following prompt in the next chat:

```text
repo: knitanr-a11y/xauusd-signal-lab

Please read this handoff first and continue from it:

docs/gold_v3/NEXT_CHAT_HANDOFF_GOLD_V3_42_DONE_43_NEXT_EXACT_ENTRY_PRUNE_HONMEI_20260610.md

GOLD V3 is source-of-truth constrained.
GOLD V2 / old GOLD / DISC8 remain quarantined and must not be used.
Do not approximate live entry logic.
Do not use Stage41 feature-only snapshot as a trading signal source.
Do not enable MT5 execution.
The next task is Stage43:
GOLD_V3_43_EXACT_ENTRY_AND_PRUNE_CONTRACT_FOR_HONMEI_SET_AUDIT_ONLY

Honmei set for Stage43:
- R03_P1_R1_ONLY_CD60_PRUNE_111
- R04_P4_R1_ONLY_CD60_PRUNE_115
- R1_ONLY_CD90_PRUNE_050__R1_ONLY_CD90_PRUNE_050_S030__R1_ONLY_CD90_PRUNE_050_S024

Use Stage15 for base entry families, Stage21/22/30/36 for prune filters, and Stage42 for the human decision record.
Create only the exact entry/prune contract and report. No live code, no MT5, no Discord live enablement.
```

## 12. Final warning

The previous approximation mistake was: trying to build a live candidate snapshot from `goldsharp_m5/h1/h4` feature rows without first reproducing the original entry families and prune chain. Do not repeat that.

The correct order is:

1. Source-of-truth contract
2. Contract audit
3. Exact live evaluator plan
4. Dry-run evaluator
5. Compare dry-run outputs with known replay rows where possible
6. Only then consider Discord/MT5 integration
