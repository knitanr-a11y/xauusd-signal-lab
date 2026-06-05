# GOLD V2 15C CoreA historical SOT mapping audit-only spec

Created: 2026-06-05

## Purpose

15B confirmed that CoreA selected source rows are readable, but the A-gate is still `is_A` ledger-flag based and not live-executable.

15C creates an audit-only historical SOT mapping for CoreA. This mapping records the historical source rows and ABC/CAP policy while explicitly forbidding live use.

## Inputs

```text
FX_OUTPUTS/gold_v2_15b_corea_a_gate_source_read_and_replay_audit_only/gold_v2_15b_corea_a_gate_read_replay_summary.json
FX_OUTPUTS/gold_v2_15b_corea_a_gate_source_read_and_replay_audit_only/gold_v2_15b_selected_signal_counts.csv
FX_OUTPUTS/gold_v2_15b_corea_a_gate_source_read_and_replay_audit_only/gold_v2_15b_a_gate_inventory_rows.csv
FX_OUTPUTS/gold_v2_15b_corea_a_gate_source_read_and_replay_audit_only/gold_v2_15b_a_gate_unmapped_rows.csv
```

## Checks

```text
15B status is COREA_A_GATE_SOURCE_READABLE_BUT_LIVE_MAPPING_BLOCKED_AUDIT_ONLY
selected source rows == 325
A selected rows == 173
A gate executable == false
CoreA live evaluator allowed == false
final signal allowed == false
external actions false
```

## Outputs

```text
FX_OUTPUTS/gold_v2_15c_corea_historical_sot_mapping_audit_only
```

```text
GOLD_V2_15C_COREA_HISTORICAL_SOT_MAPPING_AUDIT_ONLY_REPORT.md
gold_v2_15c_input_audit.csv
gold_v2_15c_corea_historical_sot_mapping.json
gold_v2_15c_mapping_checks.csv
gold_v2_15c_decision_matrix.csv
gold_v2_15c_blockers.csv
gold_v2_15c_corea_historical_sot_mapping_summary.json
```

## Expected status

```text
COREA_HISTORICAL_SOT_MAPPING_BUILT_AUDIT_ONLY_LIVE_BLOCKED
```

## Prohibitions

No Discord, no MT5, no AI API, no live hook, no final signal, no CoreA live enablement.
