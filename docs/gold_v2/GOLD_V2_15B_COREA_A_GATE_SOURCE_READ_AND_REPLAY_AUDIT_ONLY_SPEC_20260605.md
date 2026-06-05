# GOLD V2 15B CoreA A-gate source read and replay audit-only spec

Created: 2026-06-05

## Purpose

15A found CoreA A-gate source candidates. 15B reads the local CoreA config and 13B outputs to decide whether the A-gate is executable or still historical/ledger-only.

This step does not enable CoreA live evaluator.

## Inputs

```text
configs/gold_v2/frozen_coreA_fold4_ABC_CAP5_rules_20260603.json
configs/gold_v2/live_evaluator_mapping_coreA_20260603.json
FX_OUTPUTS/gold_v2_13b_corea_executable_mapping_freeze_audit_only/gold_v2_13b_corea_mapping_summary.json
FX_OUTPUTS/gold_v2_13b_corea_executable_mapping_freeze_audit_only/gold_v2_13b_corea_selected_source_rows.csv
FX_OUTPUTS/gold_v2_13b_corea_executable_mapping_freeze_audit_only/gold_v2_13b_corea_abc_gate_inventory.csv
FX_OUTPUTS/gold_v2_13b_corea_executable_mapping_freeze_audit_only/gold_v2_13b_corea_candidateA_top5_inventory.csv
```

## Checks

```text
13B summary exists
selected source rows exist
ABC gate inventory exists
frozen CoreA config exists when available locally
live evaluator mapping config exists when available locally
A-gate executable formula exists or remains blocked
B_rr15/C_fixed known formulas are detected as partial only
CoreA live evaluator remains false
final signal remains false
external actions false
```

## Expected safe status

Most likely:

```text
COREA_A_GATE_SOURCE_READABLE_BUT_LIVE_MAPPING_BLOCKED_AUDIT_ONLY
```

If the frozen config actually contains executable A-gate predicates, a later 15C replay parity audit is still required before live use.

## Prohibitions

No Discord, no MT5, no AI API, no live hook, no final signal, no CoreA live enablement.
