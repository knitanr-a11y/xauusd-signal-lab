# GOLD V3 42 -> 43 stage 1-40 read-check addendum

Created JST: 2026-06-10

## Purpose

This addendum records the important Stage1-40 context that was missing from the first two Stage42 handoff files. It is a read-check map, not a replacement for source-of-truth artifacts.

Required companion handoff files:

```text
docs/gold_v3/NEXT_CHAT_HANDOFF_GOLD_V3_42_DONE_43_NEXT_EXACT_ENTRY_PRUNE_HONMEI_20260610.md
docs/gold_v3/NEXT_CHAT_HANDOFF_GOLD_V3_42_DONE_43_MUST_READ_SOURCE_CHECK_ADDENDUM_20260610.md
```

## Hard correction

Do not create live candidates from `goldsharp_m5.csv`, `goldsharp_h1.csv`, or `goldsharp_h4.csv` by feature approximation.

The valid order is:

```text
Stage15 base entry family
-> Stage21 / Stage22 / Stage30 / Stage35 / Stage36 prune filters
-> Stage42 human honmei decision
-> Stage43 exact entry and prune contract
-> later dry-run evaluator planning
```

Stage43 must create only an audit-only exact contract. No live connector, no runtime sender, no trading bridge, and no final signal enablement.

## Stage1-13 availability

Stage1-13 source files are not present in the current uploaded file set. Do not reconstruct them from memory.

Known context only:

- Stage13 was completed with status `GOLD_V3_13_RANKING_DECISION_TEMPLATE_READY_AUDIT_ONLY`.
- Stage13 ranking was proxy-only.
- The 8 rows were 8 rule candidates, not 8 trade points.
- `h1_atr56 >= 9.95812` shared one entry family across 5 TP/SL profiles.
- Stage14 began from human ranking decision intake.

If Stage43 needs details from Stage1-13, first read actual Stage1-13 artifacts. If they are not available, stop with a blocker.

## Stage14-36 status map

| Stage | Status |
| ---: | --- |
| 14 | `GOLD_V3_14_HUMAN_RANKING_DECISION_INTAKE_INPUT_REVIEW_REQUIRED_AUDIT_ONLY` |
| 15 | `GOLD_V3_15_AUDIT_ONLY_REPLAY_EXECUTION_READY_AUDIT_ONLY` |
| 16 | `GOLD_V3_16_ALL_REPLAY_RESULT_REVIEW_AND_NARROWING_EXCEPTION_AUDIT_ONLY` |
| 17 | `GOLD_V3_17_OVERLAP_COOLDOWN_SPACING_READY_AUDIT_ONLY` |
| 18 | `GOLD_V3_18_MONTHLY_STABILITY_FINAL_AUDIT_SHORTLIST_READY_AUDIT_ONLY` |
| 19 | `GOLD_V3_19_FINAL_AUDIT_SHORTLIST_HUMAN_DECISION_TEMPLATE_READY_AUDIT_ONLY` |
| 20 | `GOLD_V3_20_LOSS_FEATURE_PRUNING_PF_UPLIFT_READY_AUDIT_ONLY` |
| 21 | `GOLD_V3_21_SELECTED_PRUNING_RULE_VALIDATION_READY_AUDIT_ONLY` |
| 22 | `GOLD_V3_22_WITHIN_CANDIDATE_LOSS_FEATURE_PRUNING_READY_AUDIT_ONLY` |
| 23 | `GOLD_V3_23_FURTHER_PRUNED_SHORTLIST_HUMAN_INTAKE_READY_AUDIT_ONLY` |
| 24 | `GOLD_V3_24_FURTHER_PRUNED_DECISION_PROPOSAL_READY_AUDIT_ONLY` |
| 25 | `GOLD_V3_25_RETAINED_PACKET_ROBUSTNESS_REVIEW_READY_AUDIT_ONLY` |
| 26 | `GOLD_V3_26_CLEAR_PACKET_VALIDATION_BUNDLE_READY_AUDIT_ONLY` |
| 27 | `GOLD_V3_27_CLEAR_BUNDLE_PAIRWISE_REVIEW_READY_AUDIT_ONLY` |
| 28 | `GOLD_V3_28_PRIMARY_REVIEW_FILTER_CONTRACT_READY_AUDIT_ONLY` |
| 29 | `GOLD_V3_29_MULTI_PRIMARY_CLEAR_SET_CONTRACT_READY_AUDIT_ONLY` |
| 30 | `GOLD_V3_30_ALL_RETAINED_CANDIDATE_SET_RESTORE_READY_AUDIT_ONLY` |
| 31 | `GOLD_V3_31_ALL_ACTIVE_CANDIDATE_UPLIFT_QUEUE_READY_AUDIT_ONLY` |
| 32 | `GOLD_V3_32_REQUESTED_ACTIVE_CANDIDATE_LOSS_FEATURE_PRUNING_READY_AUDIT_ONLY` |
| 33 | `GOLD_V3_33_FEATURE_BAND_REVIEW_READY_AUDIT_ONLY` |
| 34 | `GOLD_V3_34_SELECTED_BAND_PRUNING_READY_AUDIT_ONLY` |
| 35 | `GOLD_V3_35_CUMULATIVE_SELECTED_BAND_PRUNING_WITH_PACKET9_READY_AUDIT_ONLY` |
| 36 | `GOLD_V3_36_FINAL_RANKED_CANDIDATE_CONTRACT_READY_AUDIT_ONLY` |

## Stage15 source facts to recheck

Stage15 is the key source for base entry families and replay ledger.

Required files:

```text
GOLD_V3_15_AUDIT_ONLY_REPLAY_EXECUTION_REPORT.md
gold_v3_15_replay_candidate_metrics.csv
gold_v3_15_replay_trade_ledger.csv
gold_v3_15_replay_family_metrics.csv
gold_v3_15_replay_monthly_metrics.csv
```

Known source facts to re-verify:

```text
source_rank 1:
  GROUP_H4_RET4_MOMENTUM
  direction LONG
  h4_ret4 >= 0.00751699
  profile USDPRICE_TP150_SL60_H128

source_rank 2:
  GROUP_M15_ATR28_MID_VOL_RANGE
  direction LONG
  3.59086 <= m15_atr28 <= 4.29321
  profile USDPRICE_TP80_SL30_H64
```

Do not include source_rank 3/4/6/7/8 h1_atr56 candidates in Stage43 unless the user explicitly adds them.

## Stage21 / Stage22 prune facts to recheck

Stage21 required file:

```text
gold_v3_21_filter_traceability.csv
```

Known filters to re-verify:

```text
R1_ONLY_CD60_PRUNE_111:
  F002: rank 1 h4_ret4 in [0.0200540794, 0.0375731465)
  F003: jst_hour = 23
  F004: jst_weekday = Friday

R1_ONLY_CD60_PRUNE_115:
  F002: rank 1 h4_ret4 in [0.0200540794, 0.0375731465)
  F004: jst_weekday = Friday
  F006: jst_hour = 0

R1_ONLY_CD90_PRUNE_050:
  F004: jst_weekday = Friday
  F006: jst_hour = 0
```

Stage22 required files:

```text
gold_v3_22_further_pruned_candidate_metrics.csv
gold_v3_22_filter_traceability.csv
```

Known Stage22 restore candidate facts to re-verify:

```text
R1_ONLY_CD90_PRUNE_050__R1_ONLY_CD90_PRUNE_050_S030__R1_ONLY_CD90_PRUNE_050_S024:
  S030: rank 1 h4_ret4 in [0.013348824, 0.0156019094)
  S024: jst_weekday = Wednesday
  PF: 2.8726383868
  WR: 0.6418219462
  trades/day: 1.3529411765
  negative_months: 0
  flag: REQUEST_MORE_AUDIT_LOW_FREQUENCY
```

## Stage30 / Stage35 / Stage36 facts to recheck

Stage30 required files:

```text
gold_v3_30_all_retained_candidate_set.csv
gold_v3_30_all_retained_filter_contract.csv
```

Use Stage30 to reconstruct retained filter chains for R03 and R04 if Stage21/22 rows are insufficient.

Stage35 required files:

```text
gold_v3_35_before_after_metrics.csv
gold_v3_35_selected_cut_plan.csv
```

Important context: P7/P8 PF improved after Stage35 selected band pruning, but their negative month count remained 1. They are not the newly selected honmei-first candidates.

Stage36 required files:

```text
gold_v3_36_ranked_candidate_contract.csv
gold_v3_36_final_filter_contract.csv
GOLD_V3_36_FINAL_RANKED_CANDIDATE_CONTRACT_AUDIT_ONLY_REPORT.md
```

Stage36 final active rows for context:

```text
R01 P7   R1_ONLY_CD60_PRUNE_015      PF 2.9225  negative_months 1
R02 P8   R1_ONLY_CD60_PRUNE_015      PF 2.7660  negative_months 1
R03 P1   R1_ONLY_CD60_PRUNE_111      PF 2.6083  negative_months 0
R04 P4   R1_ONLY_CD60_PRUNE_115      PF 2.5517  negative_months 0
R05 P9   MAIN_R1_R2_CD90_PRUNE_133   PF 2.3377  negative_months 0
R06 P11  MAIN_R1_R2_CD90_PRUNE_132   PF 2.2304  negative_months 0
R07 P13  MAIN_R1_R2_CD120_PRUNE_122  PF 2.2101  negative_months 0
```

Current honmei set:

```text
R03_P1_R1_ONLY_CD60_PRUNE_111
R04_P4_R1_ONLY_CD60_PRUNE_115
R1_ONLY_CD90_PRUNE_050__R1_ONLY_CD90_PRUNE_050_S030__R1_ONLY_CD90_PRUNE_050_S024
```

Stage36 final Saturday filter applies to R03 packet 1 and R04 packet 4. Do not automatically apply Stage36 final filters to the Stage22 restore candidate unless Stage43 explicitly validates that restore contract.

## Stage37-40 runtime/log meaning

Stage37 uploaded runtime status:

```text
GOLD_V3_37_RANKED_LIVE_DISCORD_NOTIFY_BLOCKED
blocked_reason: missing Stage36 output or live snapshot
```

Meaning: Stage37 did not produce a valid trading signal. It was blocked because the live snapshot expected by that runtime path was missing.

Stage38 uploaded runtime status:

```text
GOLD_V3_38_LIVE_MINUTE_LOOP_EXCEPTION
last Stage37 return_code: 2
error_discord_status: ERROR_NOTIFY_BLOCKED_NO_WEBHOOK
```

Meaning: Stage38 called a blocked Stage37. The webhook was not available in that runtime attempt.

Stage39 purpose:

```text
create live_runtime/current
create live_runtime/logs
create live_runtime/state
initialize latest status/signal files and dedupe state
```

No Stage39 uploaded output was present in the current attachment set. Do not assume it exists locally unless checked.

Stage40 uploaded runtime status:

```text
GOLD_V3_40_MT5_DEMO_EXECUTOR_LOOP_READY
last_result: GOLD_V3_40_MT5_DEMO_EXECUTOR_LOOP_NO_SIGNAL
reason: no executable signal status=NO_SIGNAL
```

Meaning: the uploaded log showed no bridge action because latest_signal.json was NO_SIGNAL.

The unsafe Stage40 BAT was removed from repo:

```text
scripts/gold_v3_runtime/bat/GOLD_V3_40_MT5_DEMO_EXECUTOR_LOOP.bat
```

Removed commit:

```text
ba4f122eb835e493d564eec1fe61f341d5454c80
```

Do not recreate it before exact SOT verification.

## Stage41 caution

Stage41 experimental script exists:

```text
scripts/gold_v3_runtime/gold_v3_41_goldsharp_candle_snapshot_builder.py
```

It is not approved as a trading source. It is only a feature snapshot experiment from the previous mistake.

The Stage41 loop BAT was removed:

```text
scripts/gold_v3_runtime/bat/GOLD_V3_41_GOLDSHARP_CANDLE_SNAPSHOT_BUILDER_LOOP.bat
```

Removed commit:

```text
e1bef6d21457f7e4ca26dee581c484c25a2a6880
```

## Stage43 mandatory output

Stage43 must create only audit-only contract files, for example:

```text
gold_v3_43_honmei_exact_entry_prune_contract.csv
gold_v3_43_honmei_exact_entry_prune_contract.json
GOLD_V3_43_EXACT_ENTRY_AND_PRUNE_CONTRACT_FOR_HONMEI_SET_AUDIT_ONLY_REPORT.md
gold_v3_43_input_inventory.csv
gold_v3_43_blocker_matrix.csv
gold_v3_43_summary.json
```

Stage43 must stop with a blocker if any required Stage15/21/22/30/35/36 artifact cannot be read or verified.

## Updated next-chat must-read list

The next chat must read all three handoff docs:

```text
docs/gold_v3/NEXT_CHAT_HANDOFF_GOLD_V3_42_DONE_43_NEXT_EXACT_ENTRY_PRUNE_HONMEI_20260610.md
docs/gold_v3/NEXT_CHAT_HANDOFF_GOLD_V3_42_DONE_43_MUST_READ_SOURCE_CHECK_ADDENDUM_20260610.md
docs/gold_v3/NEXT_CHAT_HANDOFF_GOLD_V3_42_DONE_43_STAGE01_40_READCHECK_ADDENDUM_20260610.md
```

## Final safety line

Do not proceed to live code, live connector enablement, runtime bridge creation, or final signal behavior until the Stage43 exact entry/prune contract is created and reviewed.
