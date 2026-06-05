# GOLD V2 15A CoreA A-gate source reconstruction audit-only spec

Created: 2026-06-05

## Purpose

CoreB has been frozen as historical-only. The next unresolved component is CoreA.

13B showed that CoreA historical SOT rows exist, but live CoreA is blocked because the underlying A-gate logic behind `is_A` / `signal_ABC=A` has not been converted to executable live conditions.

15A is a source-locator audit. It does not implement CoreA live evaluator.

## Priority source areas

```text
FX_OUTPUTS/gold_v2_ABC_stack_cap_2025_2026_validation_outputs
FX_OUTPUTS/gold_v2_13b_corea_executable_mapping_freeze_audit_only
configs/gold_v2
scripts/gold_v2_runtime
docs/gold_v2
```

## Evidence to locate

```text
is_A
signal_ABC
signal_fixed_ABC
candidateA_top5_by_month
chosen_names
tail_hard
top5
all-consensus
stack
KEEP
fold4_rules
abc_stack_cap
CAP5
CAP3
```

## Outputs

```text
FX_OUTPUTS/gold_v2_15a_corea_a_gate_source_reconstruction_audit_only
```

```text
GOLD_V2_15A_COREA_A_GATE_SOURCE_RECONSTRUCTION_AUDIT_ONLY_REPORT.md
gold_v2_15a_input_audit.csv
gold_v2_15a_csv_file_inventory.csv
gold_v2_15a_corea_column_inventory.csv
gold_v2_15a_code_keyword_hits.csv
gold_v2_15a_candidate_scores.csv
gold_v2_15a_decision_matrix.csv
gold_v2_15a_blockers.csv
gold_v2_15a_corea_a_gate_source_reconstruction_summary.json
```

## Expected status

```text
COREA_A_GATE_SOURCE_CANDIDATES_FOUND_AUDIT_ONLY
```

or, if evidence is incomplete:

```text
COREA_A_GATE_SOURCE_CANDIDATES_PARTIAL_AUDIT_ONLY
```

## Prohibitions

No Discord, no MT5, no AI API, no live hook, no final signal, no CoreA live enablement.
