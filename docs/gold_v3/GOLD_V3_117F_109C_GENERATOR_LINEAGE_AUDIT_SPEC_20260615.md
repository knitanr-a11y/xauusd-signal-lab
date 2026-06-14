# GOLD V3 Stage117F Spec — 109C_GENERATOR_LINEAGE_AUDIT

Created JST: `2026-06-15`

## Purpose

Find the exact local generator or handoff path that produced:

```text
FX_OUTPUTS/gold_v3/109c/gold_v3_109_selected_base_policy_ledger.csv
```

This stage exists because Stage117B proved that the selected ledger ends before June while M15 CSV has June rows.

## Method

Stage117F scans local repository text files and GOLD V3 output metadata for references to:

```text
109c
109_selected_base_policy_ledger
gold_v3_109_selected_base_policy_ledger.csv
KEEP_107Q_BASE
107Q_BASE_RESOLVED_PASS_THROUGH
```

It also audits the 109c output directory itself and records file mtimes, sizes, row counts, min/max entry_dt, and summary hints.

## Outputs

```text
FX_OUTPUTS/gold_v3/117f/gold_v3_117f_repo_reference_hits.csv
FX_OUTPUTS/gold_v3/117f/gold_v3_117f_109c_output_inventory.csv
FX_OUTPUTS/gold_v3/117f/gold_v3_117f_summary_json_inventory.csv
FX_OUTPUTS/gold_v3/117f/gold_v3_117f_decision.csv
FX_OUTPUTS/gold_v3/117f/gold_v3_117f_summary.json
FX_OUTPUTS/gold_v3/117f/paste_me.txt
```

## Guardrails

```text
source_csv_mutated: false
contract_mutated: false
open_asof_allowed: false
approximate_reconstruction: false
```

This stage does not regenerate 109c. It only finds the generator lineage.
