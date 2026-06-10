# GOLD V3 42 primary plus restore candidate decision audit-only

Created JST: 2026-06-10

## Status

`GOLD_V3_42_PRIMARY_PLUS_RESTORE_CANDIDATE_DECISION_RECORDED_AUDIT_ONLY`

This document records the human decision to add the following three candidates to the honmei review set:

1. `R03_P1_R1_ONLY_CD60_PRUNE_111`
2. `R04_P4_R1_ONLY_CD60_PRUNE_115`
3. `R1_ONLY_CD90_PRUNE_050__R1_ONLY_CD90_PRUNE_050_S030__R1_ONLY_CD90_PRUNE_050_S024`

This is a decision record only. It does not enable Discord live signals, MT5 execution, AI API, live hooks, or final signal behavior.

## Human decision

The honmei set must include the two stable Stage36 active candidates `R03` and `R04`, plus the Stage22 restore candidate `R1_ONLY_CD90_PRUNE_050`.

Reason:

- `R03` and `R04` are Stage36 active candidates with `negative_months_final = 0`.
- `R1_ONLY_CD90_PRUNE_050` had high PF and zero negative months in Stage22, but remains flagged as low frequency and must be treated as a restore candidate requiring additional exact-contract verification.
- None of these are live-approved until the exact base entry rules and all prune filters are reconciled from source-of-truth artifacts.

## Candidate decision rows

| decision_role | candidate_label | packet_row | source_scenario_key | variant_key | cooldown | source_stage | PF | WR | trades/day | negative_months | July PF | live_allowed |
| --- | --- | ---: | --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | --- |
| HONMEI_ADD | `R03_P1_R1_ONLY_CD60_PRUNE_111` | 1 | `R1_ONLY_CD60_PRUNE_111` | `R1_ONLY_CD60_PRUNE_111__R1_ONLY_CD60_PRUNE_111_S021__R1_ONLY_CD60_PRUNE_111_S022` | 60 | Stage36 | 2.6083250034 | 0.6684636119 | 2.0784313725 | 0 | 1.2486063766 | False |
| HONMEI_ADD | `R04_P4_R1_ONLY_CD60_PRUNE_115` | 4 | `R1_ONLY_CD60_PRUNE_115` | `R1_ONLY_CD60_PRUNE_115__R1_ONLY_CD60_PRUNE_115_S020__R1_ONLY_CD60_PRUNE_115_S022` | 60 | Stage36 | 2.5517460463 | 0.6688918558 | 2.0980392157 | 0 | 1.2416950739 | False |
| HONMEI_RESTORE | `R1_ONLY_CD90_PRUNE_050_RESTORE` | TBD | `R1_ONLY_CD90_PRUNE_050` | `R1_ONLY_CD90_PRUNE_050__R1_ONLY_CD90_PRUNE_050_S030__R1_ONLY_CD90_PRUNE_050_S024` | 90 | Stage22 | 2.8726383868 | 0.6418219462 | 1.3529411765 | 0 | 5.5905567301 | False |

## Required source-of-truth checks before any live use

Before these candidates can be connected to Stage37/Stage40, the next audit stage must confirm:

1. The base entry family for `R1_ONLY` from Stage15/source ledger.
2. The exact direction. Current known direction is LONG for the relevant R1 source family, but this must be re-confirmed in the source ledger.
3. The exact TP/SL profile for each candidate.
4. The exact cooldown handling for CD60 and CD90.
5. The existing Stage21 filters.
6. The added Stage22 filters.
7. The Stage35/36 final filters for Stage36 candidates.
8. Whether `R1_ONLY_CD90_PRUNE_050` has any later-stage filter contract equivalent to Stage36, or whether it requires a new restore contract.
9. Whether the low-frequency flag is acceptable for live monitoring.
10. That no month filter, daily cap, candidate switching, old GOLD, GOLD V2, or DISC8 artifact is introduced.

## Safety

- GOLD V3 remains source-of-truth constrained.
- No approximate live implementation is approved.
- No MT5 order BAT is approved from this decision.
- No Stage41 feature-only snapshot is approved for trade generation.
- Stage40 MT5 order BAT was removed separately after the unsafe path was identified.
- Stage41 loop BAT was removed separately after the unsafe path was identified.

## Output files

- `docs/gold_v3/gold_v3_42_primary_plus_restore_candidate_decision.csv`

## Next stage

`GOLD_V3_43_EXACT_ENTRY_AND_PRUNE_CONTRACT_FOR_HONMEI_SET_AUDIT_ONLY`

This next stage should build a machine-readable contract for the honmei set only, using source-of-truth artifacts rather than reconstructed or inferred rules.
