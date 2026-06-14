# GOLD V3 Stage117E Spec — STRICT_EXTENSION_SOURCE_REVIEW

Created JST: `2026-06-15`

## Purpose

Stage117D found June extension rows, but some sources are too broad.

Stage117E ranks the Stage117D sources by strict May parity:

```text
selected_may_entry_recall
selected_may_entry_precision
projected_extra_may_entries
projected_june_rows
```

This stage does not adopt a source automatically. It creates a review packet.

## Inputs

```text
FX_OUTPUTS/gold_v3/117d/gold_v3_117d_source_parity_matrix.csv
FX_OUTPUTS/gold_v3/117d/gold_v3_117d_june_extension_candidates.csv
```

## Outputs

```text
FX_OUTPUTS/gold_v3/117e/gold_v3_117e_strict_source_ranking.csv
FX_OUTPUTS/gold_v3/117e/gold_v3_117e_review_extension_candidates.csv
FX_OUTPUTS/gold_v3/117e/gold_v3_117e_decision.csv
FX_OUTPUTS/gold_v3/117e/gold_v3_117e_summary.json
FX_OUTPUTS/gold_v3/117e/paste_me.txt
```

## Guardrails

```text
source_csv_mutated: false
contract_mutated: false
open_asof_allowed: false
approximate_reconstruction: false
```
