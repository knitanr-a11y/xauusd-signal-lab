# GOLD V3 42 -> 43 must-read source check addendum

Created JST: 2026-06-10

## Purpose

This addendum exists because the next chat must not rely only on the handoff summary. It must re-check the source-of-truth artifacts for the honmei candidate set before creating Stage43.

Main handoff:

- `docs/gold_v3/NEXT_CHAT_HANDOFF_GOLD_V3_42_DONE_43_NEXT_EXACT_ENTRY_PRUNE_HONMEI_20260610.md`

## Critical repo/search note

The Stage15/21/22/30/35/36 outputs referenced by the handoff are runtime/output artifacts from `FX_OUTPUTS/gold_v3`, not guaranteed to be committed as ordinary repository docs.

If GitHub code search does not find files such as `gold_v3_15_replay_candidate_metrics.csv` or `gold_v3_36_ranked_candidate_contract.csv`, do not assume they do not exist. They may exist only under the user's local MT5 Files root:

`C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files\FX_OUTPUTS\gold_v3`

Stage43 must therefore either:

1. read the locally available FX_OUTPUTS artifacts if the environment has them, or
2. ask the user to upload the required artifacts, or
3. stop with a blocker.

Do not reconstruct missing source data.

## Must-read source artifacts before Stage43

Read these in this order:

1. Main handoff
   - `docs/gold_v3/NEXT_CHAT_HANDOFF_GOLD_V3_42_DONE_43_NEXT_EXACT_ENTRY_PRUNE_HONMEI_20260610.md`

2. Stage42 decision record
   - `docs/gold_v3/gold_v3_42_primary_plus_restore_candidate_decision.csv`
   - `docs/gold_v3/GOLD_V3_42_PRIMARY_PLUS_RESTORE_CANDIDATE_DECISION_AUDIT_ONLY_20260610.md`

3. Stage15 base entry/replay source
   - `GOLD_V3_15_AUDIT_ONLY_REPLAY_EXECUTION_REPORT.md`
   - `gold_v3_15_replay_candidate_metrics.csv`
   - `gold_v3_15_replay_trade_ledger.csv`

4. Stage21 initial selected prune validation
   - `GOLD_V3_21_SELECTED_PRUNING_RULE_VALIDATION_AUDIT_ONLY_REPORT.md`
   - `gold_v3_21_filter_traceability.csv`

5. Stage22 within-candidate prune outputs
   - `GOLD_V3_22_WITHIN_CANDIDATE_LOSS_FEATURE_PRUNING_AUDIT_ONLY_REPORT.md`
   - `gold_v3_22_further_pruned_candidate_metrics.csv`
   - `gold_v3_22_filter_traceability.csv`

6. Stage24/26/27/28 decision context for R03/R04
   - `GOLD_V3_24_FURTHER_PRUNED_DECISION_PROPOSAL_AUDIT_ONLY_REPORT.md`
   - `GOLD_V3_26_CLEAR_PACKET_VALIDATION_BUNDLE_AUDIT_ONLY_REPORT.md`
   - `GOLD_V3_27_CLEAR_BUNDLE_PAIRWISE_REVIEW_AUDIT_ONLY_REPORT.md`
   - `GOLD_V3_28_PRIMARY_REVIEW_FILTER_CONTRACT_AUDIT_ONLY_REPORT.md`

7. Stage30 retained contract if available
   - `gold_v3_30_all_retained_candidate_set.csv`
   - `gold_v3_30_all_retained_filter_contract.csv`
   - `GOLD_V3_30_ALL_RETAINED_CANDIDATE_SET_RESTORE_AUDIT_ONLY_REPORT.md`

8. Stage35/36 final ranking and final added filters
   - `gold_v3_35_before_after_metrics.csv`
   - `gold_v3_35_selected_cut_plan.csv`
   - `gold_v3_36_ranked_candidate_contract.csv`
   - `gold_v3_36_final_filter_contract.csv`
   - `GOLD_V3_36_FINAL_RANKED_CANDIDATE_CONTRACT_AUDIT_ONLY_REPORT.md`

## Confirmed source facts from the re-check

These facts must still be rechecked from the files before coding, but they were confirmed from the uploaded reports in the prior chat:

### Stage15 base families

- source_rank 1:
  - `GROUP_H4_RET4_MOMENTUM`
  - direction `LONG`
  - feature `h4_ret4`
  - rule `h4_ret4 >= 0.00751699`
  - profile `USDPRICE_TP150_SL60_H128`

- source_rank 2:
  - `GROUP_M15_ATR28_MID_VOL_RANGE`
  - direction `LONG`
  - feature `m15_atr28`
  - rule `3.59086 <= m15_atr28 <= 4.29321`
  - profile `USDPRICE_TP80_SL30_H64`

Do not add h1_atr56 high-vol candidates to the Stage43 honmei contract unless explicitly requested.

### Stage21 filters relevant to the three honmei candidates

- `R1_ONLY_CD60_PRUNE_111`
  - F002: exclude rank 1 `h4_ret4 in [0.0200540794, 0.0375731465)`
  - F003: exclude `jst_hour = 23`
  - F004: exclude `jst_weekday = Friday`

- `R1_ONLY_CD60_PRUNE_115`
  - F002: exclude rank 1 `h4_ret4 in [0.0200540794, 0.0375731465)`
  - F004: exclude `jst_weekday = Friday`
  - F006: exclude `jst_hour = 0`

- `R1_ONLY_CD90_PRUNE_050`
  - F004: exclude `jst_weekday = Friday`
  - F006: exclude `jst_hour = 0`

### Stage22 added filters relevant to the three honmei candidates

- `R1_ONLY_CD60_PRUNE_111__R1_ONLY_CD60_PRUNE_111_S021__R1_ONLY_CD60_PRUNE_111_S022`
  - S021: exclude `jst_hour = 21`
  - S022: exclude `jst_hour = 22`

- `R1_ONLY_CD60_PRUNE_115__R1_ONLY_CD60_PRUNE_115_S020__R1_ONLY_CD60_PRUNE_115_S022`
  - S020: exclude `jst_hour = 21`
  - S022: exclude `jst_hour = 23`

- `R1_ONLY_CD90_PRUNE_050__R1_ONLY_CD90_PRUNE_050_S030__R1_ONLY_CD90_PRUNE_050_S024`
  - S030: exclude rank 1 `h4_ret4 in [0.013348824, 0.0156019094)`
  - S024: exclude `jst_weekday = Wednesday`

### Stage36 final filters for R03/R04

- R03 packet 1:
  - `GLOBAL_SATURDAY`: exclude `jst_weekday = Saturday`

- R04 packet 4:
  - `GLOBAL_SATURDAY`: exclude `jst_weekday = Saturday`

Do not automatically apply Stage36 final filters to the Stage22 restore candidate `R1_ONLY_CD90_PRUNE_050` unless Stage43 explicitly validates such a restore contract.

## Stage43 stopping conditions

Stop with a blocker if any of these cannot be verified from files:

- base entry family for source_rank 1
- direction LONG for R1-only candidates
- profile `USDPRICE_TP150_SL60_H128`
- cooldown 60 for R03/R04
- cooldown 90 for the restore candidate
- F002/F003/F004/F006 definitions
- S021/S022/S020/S030/S024 definitions
- Stage36 final Saturday filter for packet 1 and packet 4
- Stage22 low-frequency warning for the restore candidate

## Safety reminders

- Do not create live code in Stage43.
- Do not create MT5 BAT.
- Do not recreate Stage41 as live generator.
- Do not use OHLC-only approximation.
- Do not treat this addendum as proof; treat it as a must-read checklist and verify against source artifacts.
