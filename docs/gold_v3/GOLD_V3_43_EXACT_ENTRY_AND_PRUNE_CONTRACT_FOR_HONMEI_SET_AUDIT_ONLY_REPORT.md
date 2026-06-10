# GOLD V3 43 exact entry and prune contract for honmei set audit-only report

Created JST: 2026-06-10

## Status

`GOLD_V3_43_EXACT_ENTRY_AND_PRUNE_CONTRACT_FOR_8_HONMEI_CANDIDATES_READY_AUDIT_ONLY`

This replaces the earlier blocked Stage43 packet after the required Stage15/21/22/30/35/36 source-of-truth artifacts were uploaded and read.

## Honmei set clarification

The original Stage42 decision file contained three honmei-review rows. In this chat, the user explicitly clarified the current honmei set as:

1. Stage36 R01-R07 active candidates.
2. Stage22 restore candidate `R1_ONLY_CD90_PRUNE_050__R1_ONLY_CD90_PRUNE_050_S030__R1_ONLY_CD90_PRUNE_050_S024`.

Therefore this Stage43 contract covers 8 candidates.

## Safety state

- GOLD V3 remains source-of-truth constrained.
- GOLD V2 / old GOLD / DISC8 were not read, used, referenced, or used as fallback.
- No OHLC-only approximation was used.
- Stage41 feature-only snapshot was not used as a trading source.
- No live code was created.
- No Discord live enablement was created.
- No MT5 BAT was created.
- No MT5 order path was enabled.
- `live_allowed` remains `False`.

## Source-of-truth artifacts verified

- Stage15: base entry families / source_rank / direction / profile / replay source.
- Stage21: initial selected prune filters.
- Stage22: within-candidate added filters and CD90 restore candidate metrics.
- Stage30: retained candidate set and retained filter contract.
- Stage35: cumulative selected band pruning context.
- Stage36: final ranked active candidate contract and final filters.

## Base entry families used

| source_rank | candidate_group_id | entry_family_key | direction | live_side_if_later_enabled | feature_column | rule_expression | profile_id | tp_usd | sl_usd | horizon_profile_detail |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | GROUP_H4_RET4_MOMENTUM | `GROUP_H4_RET4_MOMENTUM||LONG||h4_ret4||h4_ret4 >= 0.00751699` | LONG | BUY | h4_ret4 | `h4_ret4 >= 0.00751699` | USDPRICE_TP150_SL60_H128 | 150 | 60 | H128 |
| 2 | GROUP_M15_ATR28_MID_VOL_RANGE | `GROUP_M15_ATR28_MID_VOL_RANGE||LONG||m15_atr28||3.59086 <= m15_atr28 <= 4.29321` | LONG | BUY | m15_atr28 | `3.59086 <= m15_atr28 <= 4.29321` | USDPRICE_TP80_SL30_H64 | 80 | 30 | H64 |

Only source_rank 1 and source_rank 2 are used. Stage15 h1_atr56 ranks 3/4/6/7/8 remain excluded from this Stage43 honmei contract.

## Stage36 active honmei candidates

| ranked_candidate_name | packet_row | source_scenario_key | variant_key | cooldown_minutes | trades_per_day_final | win_rate_final | profit_factor_final | negative_months_final | july_pf_final |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| R01_P7_R1_ONLY_CD60_PRUNE_015 | 7 | R1_ONLY_CD60_PRUNE_015 | R1_ONLY_CD60_PRUNE_015__R1_ONLY_CD60_PRUNE_015_S025__R1_ONLY_CD60_PRUNE_015_S001 | 60 | 1.7338935574 | 0.6736672052 | 2.9225153473 | 1 | 5.5883848011 |
| R02_P8_R1_ONLY_CD60_PRUNE_015 | 8 | R1_ONLY_CD60_PRUNE_015 | R1_ONLY_CD60_PRUNE_015__R1_ONLY_CD60_PRUNE_015_S025__R1_ONLY_CD60_PRUNE_015_S027 | 60 | 1.8179271709 | 0.6656394453 | 2.7660260417 | 1 | 5.5883848011 |
| R03_P1_R1_ONLY_CD60_PRUNE_111 | 1 | R1_ONLY_CD60_PRUNE_111 | R1_ONLY_CD60_PRUNE_111__R1_ONLY_CD60_PRUNE_111_S021__R1_ONLY_CD60_PRUNE_111_S022 | 60 | 2.0784313725 | 0.6684636119 | 2.6083250034 | 0 | 1.2486063766 |
| R04_P4_R1_ONLY_CD60_PRUNE_115 | 4 | R1_ONLY_CD60_PRUNE_115 | R1_ONLY_CD60_PRUNE_115__R1_ONLY_CD60_PRUNE_115_S020__R1_ONLY_CD60_PRUNE_115_S022 | 60 | 2.0980392157 | 0.6688918558 | 2.5517460463 | 0 | 1.2416950739 |
| R05_P9_MAIN_R1_R2_CD90_PRUNE_133 | 9 | MAIN_R1_R2_CD90_PRUNE_133 | MAIN_R1_R2_CD90_PRUNE_133__MAIN_R1_R2_CD90_PRUNE_133_S023__MAIN_R1_R2_CD90_PRUNE_133_S034 | 90 | 2.5083798883 | 0.6436525612 | 2.3377268732 | 0 | 1.0834451496 |
| R06_P11_MAIN_R1_R2_CD90_PRUNE_132 | 11 | MAIN_R1_R2_CD90_PRUNE_132 | MAIN_R1_R2_CD90_PRUNE_132__MAIN_R1_R2_CD90_PRUNE_132_S034__MAIN_R1_R2_CD90_PRUNE_132_S001 | 90 | 2.5223463687 | 0.634551495 | 2.2303988979 | 0 | 1.0365994862 |
| R07_P13_MAIN_R1_R2_CD120_PRUNE_122 | 13 | MAIN_R1_R2_CD120_PRUNE_122 | MAIN_R1_R2_CD120_PRUNE_122__MAIN_R1_R2_CD120_PRUNE_122_S030__MAIN_R1_R2_CD120_PRUNE_122_S035 | 120 | 1.9337016575 | 0.6514285714 | 2.2100676969 | 0 | 1.2909532639 |

## Stage22 restore honmei candidate

| candidate_label | source_scenario_key | cooldown_minutes | trades_per_day | win_rate | profit_factor | negative_months | july_pf | audit_recommendation |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| R1_ONLY_CD90_PRUNE_050__R1_ONLY_CD90_PRUNE_050_S030__R1_ONLY_CD90_PRUNE_050_S024 | R1_ONLY_CD90_PRUNE_050 | 90 | 1.3529411765 | 0.6418219462 | 2.8726383868 | 0 | 5.5905567301 | REQUEST_MORE_AUDIT_LOW_FREQUENCY |

The restore candidate remains a Stage22 restore/low-frequency review candidate. It is not treated as a Stage36 packet, and Stage36 final filters are not automatically applied to it.

## Contract row mode

`gold_v3_43_honmei_exact_entry_prune_contract.csv` is one row per honmei candidate. Each row contains:

- base entry contract,
- Stage21/22/30 prune filter chain,
- Stage36 final filter chain when applicable,
- metrics context,
- live safety flags.

## Important warnings

1. R01 and R02 are included because of the user's explicit honmei-set clarification, but both have `negative_months_final = 1` in Stage36.
2. The CD90 restore candidate has high Stage22 PF but remains `REQUEST_MORE_AUDIT_LOW_FREQUENCY`.
3. Stage36 final filters are applied only to Stage36 R01-R07 candidates, not automatically to the Stage22 restore candidate.
4. This is an audit-only exact entry/prune contract. It is not live approval.

## Output files

- `gold_v3_43_honmei_exact_entry_prune_contract.csv`
- `gold_v3_43_honmei_exact_entry_prune_contract.json`
- `GOLD_V3_43_EXACT_ENTRY_AND_PRUNE_CONTRACT_FOR_HONMEI_SET_AUDIT_ONLY_REPORT.md`
- `gold_v3_43_input_inventory.csv`
- `gold_v3_43_blocker_matrix.csv`
- `gold_v3_43_summary.json`

## Next allowed action

Review this exact contract and prepare an audit-only dry-run evaluator plan. Do not enable live connector, Discord live, MT5 BAT, MT5 execution, or final signal behavior.
