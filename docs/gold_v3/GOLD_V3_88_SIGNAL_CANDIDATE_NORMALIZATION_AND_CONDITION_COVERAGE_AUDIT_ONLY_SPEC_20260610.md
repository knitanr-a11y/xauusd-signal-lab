# GOLD V3 Stage88 — Signal Candidate Normalization and Condition Coverage Audit-Only Spec

Created JST: `2026-06-10`

Stage name:

`GOLD_V3_88_SIGNAL_CANDIDATE_NORMALIZATION_AND_CONDITION_COVERAGE_AUDIT_ONLY`

Expected READY status:

`GOLD_V3_88_SIGNAL_CANDIDATE_NORMALIZATION_AND_CONDITION_COVERAGE_READY_AUDIT_ONLY`

Blocked status:

`GOLD_V3_88_SIGNAL_CANDIDATE_NORMALIZATION_AND_CONDITION_COVERAGE_BLOCKED_AUDIT_ONLY`

## 1. Purpose

Stage88 normalizes the Stage87 44-row candidate catalog into human-facing groups:

- 8 base signal candidates,
- high-volatility expansion profiles (`HV_*__HV_TP*_SL*_H*`),
- duplicated profile rows are deduplicated,
- condition text coverage is measured and never guessed.

The human asked whether the candidates are "8 plus high-volatility" and requested candidate names/conditions in the runtime manual.

Stage88 creates a safe manual-ready candidate section. If exact conditions cannot be recovered from current GOLD V3 artifacts, the section must explicitly state that conditions are not yet restored, instead of inventing them.

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

## 4. Input source priority

Primary input:

`Files/FX_OUTPUTS/gold_v3/87_runtime_chain_and_signal_candidate_catalog_audit_only/gold_v3_87_signal_candidate_catalog.csv`

Secondary input:

`Files/FX_OUTPUTS/gold_v3/69_live_csv_condition_detector_audit_only/gold_v3_69_candidate_condition_summary.csv`

Optional same-folder search:

`Files/FX_OUTPUTS/gold_v3/69_live_csv_condition_detector_audit_only/*.csv`

Stage88 must not read quarantined systems.

## 5. Normalization rule

For each candidate label:

- `HV_` prefix means high-volatility expansion.
- Trailing `__HV_TPxxx_SLyyy_Hzzz` means high-volatility TP/SL/horizon profile.
- Remove `HV_` and trailing `__HV_TP...` to get the normalized base candidate name.
- Deduplicate exact repeated labels.
- Group all high-volatility expansions under their normalized base candidate.

Expected normalized base candidate count is 8.

If normalized base count is not 8, Stage88 BLOCKS because the manual would misrepresent the candidate set.

## 6. Condition recovery rule

Stage88 searches current GOLD V3 artifact columns for condition-like fields:

- `condition`
- `conditions`
- `condition_text`
- `rule_condition`
- `entry_condition`
- `detected_condition`
- `rule_text`
- any column containing `condition`, `rule`, `filter`, `threshold`, `feature`, `operator`, or `value`

If no condition text can be extracted, write:

`CONDITION_NOT_RESTORED_FROM_CURRENT_ARTIFACTS`

This does not block Stage88 if candidate grouping is correct, but the manual section must mark condition coverage as incomplete.

## 7. Outputs

Output folder:

`Files/FX_OUTPUTS/gold_v3/88_signal_candidate_normalization_and_condition_coverage_audit_only/`

Outputs:

- `gold_v3_88_candidate_expansion_catalog.csv`
- `gold_v3_88_base_candidate_catalog.csv`
- `gold_v3_88_condition_coverage_matrix.csv`
- `gold_v3_88_manual_candidate_section.md`
- `gold_v3_88_blocker_matrix.csv`
- `gold_v3_88_validation_matrix.csv`
- `gold_v3_88_signal_candidate_normalization_and_condition_coverage_summary.json`
- `gold_v3_88_PASTE_ME_SIGNAL_CANDIDATE_NORMALIZATION_AND_CONDITION_COVERAGE_SUMMARY.txt`
- `GOLD_V3_88_REPORT.md`

## 8. READY conditions

Stage88 is READY if:

- Stage87 candidate catalog exists,
- candidate rows can be read,
- normalized base candidate count is exactly 8,
- manual candidate section is written,
- no live/external flags are enabled,
- blocker_count is zero.

Condition text coverage may be incomplete. If incomplete, Stage88 remains READY but `condition_coverage_complete=false` and the manual section must mark conditions as unresolved.

## 9. Runner and BAT

Script:

`scripts/gold_v3_runtime/gold_v3_88_signal_candidate_normalization_and_condition_coverage_audit.py`

BAT:

`scripts/gold_v3_runtime/bat/run_gold_v3_88_signal_candidate_normalization_and_condition_coverage_audit.bat`
